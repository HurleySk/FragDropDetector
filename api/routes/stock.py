"""
Stock and watchlist management endpoints
"""

import os
import sys
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException
import structlog
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from api.dependencies import get_database
from models.database import StockChange

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["stock"])


def load_yaml_config():
    """Load configuration from YAML file"""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("Failed to load YAML config", error=str(e))
            return {}
    return {}


def save_yaml_config(config):
    """Save configuration to YAML file"""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        logger.info("Configuration saved successfully")
        return True
    except Exception as e:
        logger.error("Failed to save YAML config", error=str(e))
        return False


@router.get("/api/stock/changes")
async def get_stock_changes(limit: int = 10):
    """Get recent stock changes with validation"""
    if not (1 <= limit <= 100):
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    try:
        db = get_database()
        changes = db.get_recent_stock_changes(limit)
        return changes
    except Exception as e:
        logger.error("Failed to get stock changes", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve stock changes")


@router.delete("/api/stock/changes/{change_id}")
async def delete_stock_change(change_id: int):
    """Delete a stock change by ID"""
    try:
        db = get_database()
        session = db.get_session()
        try:
            change = session.query(StockChange).filter_by(id=change_id).first()
            if not change:
                raise HTTPException(status_code=404, detail="Stock change not found")

            session.delete(change)
            session.commit()
            logger.info(f"Deleted stock change {change_id}")
            return {"status": "success", "message": "Stock change deleted"}
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete stock change", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete stock change")


@router.get("/api/stock/fragrances")
async def get_fragrances(
    search: Optional[str] = None,
    in_stock: Optional[bool] = None,
    sort_by: Optional[str] = "name",
    sort_order: Optional[str] = "asc",
    limit: Optional[int] = None,
    offset: Optional[int] = 0,
    watchlist_only: Optional[bool] = False,
    include_ratings: Optional[bool] = True
):
    """Get all tracked fragrances with search and filter support"""
    try:
        from services.fragrance_mapper import get_fragrance_mapper
        from services.parfumo_scraper import get_parfumo_scraper

        db = get_database()
        fragrances = db.get_all_fragrances()

        yaml_config = load_yaml_config()
        watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])
        logger.info(f"Loaded watchlist with {len(watchlist)} items: {watchlist}")

        mapper = get_fragrance_mapper() if include_ratings else None
        scraper = get_parfumo_scraper() if include_ratings else None

        result = []

        for slug, data in fragrances.items():
            item = {
                **data,
                'slug': slug,
                'is_watchlisted': slug in watchlist
            }

            if include_ratings and mapper:
                mapping = mapper.get_mapping(slug)

                if mapping:
                    item['original_brand'] = mapping.get('original_brand')
                    item['original_name'] = mapping.get('original_name')

                    if scraper and mapping.get('parfumo_id'):
                        rating_data = scraper.fetch_rating(mapping['parfumo_id'])
                        if rating_data:
                            item['parfumo_score'] = rating_data.get('score')
                            item['parfumo_votes'] = rating_data.get('votes')
                        item['parfumo_url'] = f"https://www.parfumo.com/Perfumes/{mapping['parfumo_id']}"

            result.append(item)

        if search:
            search_lower = search.lower()
            result = [f for f in result if
                     search_lower in f['name'].lower() or
                     search_lower in f['slug'].lower()]

        if in_stock is not None:
            result = [f for f in result if f['in_stock'] == in_stock]

        if watchlist_only:
            result = [f for f in result if f['is_watchlisted']]

        if sort_by in ['name', 'slug', 'price', 'in_stock', 'parfumo_score', 'parfumo_votes']:
            reverse = sort_order == 'desc'
            if sort_by == 'price':
                def price_key(item):
                    price = item['price']
                    if price == 'N/A' or not price:
                        return float('inf') if not reverse else float('-inf')
                    try:
                        return float(price.replace('$', '').replace(',', ''))
                    except:
                        return float('inf') if not reverse else float('-inf')
                result.sort(key=price_key, reverse=reverse)
            elif sort_by == 'parfumo_score':
                def score_key(item):
                    score = item.get('parfumo_score')
                    if score is None:
                        return float('-inf') if reverse else float('inf')
                    return score
                result.sort(key=score_key, reverse=reverse)
            elif sort_by == 'parfumo_votes':
                def votes_key(item):
                    votes = item.get('parfumo_votes')
                    if votes is None:
                        return -1 if reverse else float('inf')
                    return votes
                result.sort(key=votes_key, reverse=reverse)
            else:
                result.sort(key=lambda x: x[sort_by], reverse=reverse)

        total = len(result)

        if limit:
            result = result[offset:offset + limit]

        return {
            "items": result,
            "total": total,
            "offset": offset,
            "limit": limit,
            "watchlist_slugs": watchlist
        }
    except Exception as e:
        logger.error("Failed to get fragrances", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve fragrances")


@router.post("/api/stock/watchlist/add/{slug}")
async def add_to_watchlist(slug: str):
    """Add a product to the watchlist"""
    try:
        yaml_config = load_yaml_config()
        watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])

        if slug not in watchlist:
            watchlist.append(slug)

            if 'stock_monitoring' not in yaml_config:
                yaml_config['stock_monitoring'] = {}
            yaml_config['stock_monitoring']['watchlist'] = watchlist

            if not save_yaml_config(yaml_config):
                raise HTTPException(status_code=500, detail="Failed to save watchlist")

            logger.info(f"Added {slug} to watchlist. New watchlist: {watchlist}")
            return {"success": True, "message": f"Added {slug} to watchlist", "watchlist": watchlist}
        else:
            return {"success": True, "message": f"{slug} already in watchlist", "watchlist": watchlist}

    except Exception as e:
        logger.error("Failed to add to watchlist", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/stock/watchlist/remove/{slug}")
async def remove_from_watchlist(slug: str):
    """Remove a product from the watchlist"""
    try:
        yaml_config = load_yaml_config()
        watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])

        if slug in watchlist:
            watchlist.remove(slug)

            if 'stock_monitoring' not in yaml_config:
                yaml_config['stock_monitoring'] = {}
            yaml_config['stock_monitoring']['watchlist'] = watchlist

            if not save_yaml_config(yaml_config):
                raise HTTPException(status_code=500, detail="Failed to save watchlist")

            logger.info(f"Removed {slug} from watchlist. New watchlist: {watchlist}")
            return {"success": True, "message": f"Removed {slug} from watchlist", "watchlist": watchlist}
        else:
            return {"success": True, "message": f"{slug} not in watchlist", "watchlist": watchlist}

    except Exception as e:
        logger.error("Failed to remove from watchlist", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/watchlist/bulk")
async def bulk_add_to_watchlist(request: dict):
    """Add multiple products to watchlist"""
    try:
        slugs = request.get('slugs', [])
        if not slugs:
            raise HTTPException(status_code=400, detail="No slugs provided")

        yaml_config = load_yaml_config()
        watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])

        added = []
        for slug in slugs:
            if slug not in watchlist:
                watchlist.append(slug)
                added.append(slug)

        if 'stock_monitoring' not in yaml_config:
            yaml_config['stock_monitoring'] = {}
        yaml_config['stock_monitoring']['watchlist'] = watchlist

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save watchlist")

        logger.info(f"Added {len(added)} items to watchlist")
        return {
            "success": True,
            "message": f"Added {len(added)} items to watchlist",
            "added": added,
            "watchlist": watchlist
        }

    except Exception as e:
        logger.error("Failed to bulk add to watchlist", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/watchlist/bulk")
async def bulk_remove_from_watchlist(request: dict):
    """Remove multiple products from watchlist"""
    try:
        slugs = request.get('slugs', [])
        if not slugs:
            raise HTTPException(status_code=400, detail="No slugs provided")

        yaml_config = load_yaml_config()
        watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])

        removed = []
        for slug in slugs:
            if slug in watchlist:
                watchlist.remove(slug)
                removed.append(slug)

        if 'stock_monitoring' not in yaml_config:
            yaml_config['stock_monitoring'] = {}
        yaml_config['stock_monitoring']['watchlist'] = watchlist

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save watchlist")

        logger.info(f"Removed {len(removed)} items from watchlist")
        return {
            "success": True,
            "message": f"Removed {len(removed)} items from watchlist",
            "removed": removed,
            "watchlist": watchlist
        }

    except Exception as e:
        logger.error("Failed to bulk remove from watchlist", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
