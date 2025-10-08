"""
Parfumo integration endpoints
"""

import sys
import os
import threading
from fastapi import APIRouter, HTTPException
import structlog

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from api.services.config_service import get_config_service

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["parfumo"])


@router.post("/api/parfumo/update")
async def trigger_parfumo_update():
    """Manually trigger Parfumo update"""
    try:
        from services.parfumo_updater import get_parfumo_updater
        from services.fragscrape_client import get_fragscrape_client

        # Check fragscrape availability first
        client = get_fragscrape_client()
        if not client.health_check():
            return {
                "success": False,
                "message": "fragscrape API is not available. Please ensure fragscrape is running."
            }

        updater = get_parfumo_updater()

        status = updater.get_status()
        if status.get('currently_updating'):
            return {
                "success": False,
                "message": "Update already in progress",
                "progress": status.get('update_progress', 0)
            }

        def run_update():
            # Manual updates force refresh ALL fragrances
            results = updater.update_all_ratings(force_refresh=True)
            logger.info(f"Parfumo update completed: {results}")

        thread = threading.Thread(target=run_update)
        thread.start()

        return {
            "success": True,
            "message": "Parfumo update started for all fragrances"
        }

    except Exception as e:
        logger.error("Failed to trigger Parfumo update", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/parfumo/status")
async def get_parfumo_status():
    """Get Parfumo update status"""
    try:
        from services.parfumo_updater import get_parfumo_updater
        from services.fragscrape_client import get_fragscrape_client

        updater = get_parfumo_updater()
        status = updater.get_status()

        # Check fragscrape availability
        client = get_fragscrape_client()
        fragscrape_available = client.health_check()

        # Get rate limit status
        rate_limit_status = client.get_rate_limit_status()

        config_service = get_config_service()
        parfumo_config = config_service.get_section('parfumo', {})

        # Get timezone from drop_window or stock_schedule
        timezone = (config_service.get_nested('drop_window.timezone') or
                   config_service.get_nested('stock_schedule.timezone') or
                   'America/New_York')

        return {
            **status,
            'config': parfumo_config,
            'fragscrape_available': fragscrape_available,
            'fragscrape_url': parfumo_config.get('fragscrape_url', 'http://localhost:3000'),
            'rate_limit': rate_limit_status,
            'timezone': timezone
        }

    except Exception as e:
        logger.error("Failed to get Parfumo status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/parfumo/unmatched")
async def get_unmatched_fragrances():
    """Get list of fragrances without Parfumo data that could use manual URLs"""
    try:
        from src.models.database import Database, FragranceStock

        db = Database()

        with db.session() as session:
            # Get fragrances without Parfumo ID but with extraction data
            unmatched = session.query(FragranceStock).filter(
                FragranceStock.parfumo_id.is_(None),
                FragranceStock.original_brand.isnot(None)
            ).order_by(FragranceStock.name).all()

            # Filter out blends (they legitimately won't have Parfumo entries)
            result = []
            for frag in unmatched:
                original_name_upper = (frag.original_name or '').upper()
                is_blend = ' AND ' in original_name_upper or original_name_upper.startswith('AND ')

                if not is_blend:
                    result.append({
                        'slug': frag.slug,
                        'name': frag.name,
                        'original_brand': frag.original_brand,
                        'original_name': frag.original_name,
                        'in_stock': frag.in_stock
                    })

            return {
                'success': True,
                'count': len(result),
                'fragrances': result
            }

    except Exception as e:
        logger.error("Failed to get unmatched fragrances", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/parfumo/manual-url")
async def set_manual_parfumo_url(request: dict):
    """Manually set Parfumo URL for a fragrance and fetch its rating"""
    try:
        slug = request.get('slug')
        parfumo_url = request.get('parfumo_url')

        if not slug or not parfumo_url:
            return {
                'success': False,
                'message': 'Missing required parameters: slug and parfumo_url'
            }
        from src.models.database import Database
        from services.fragscrape_client import get_fragscrape_client

        # Validate URL format
        if not parfumo_url.startswith('https://www.parfumo.com/'):
            return {
                'success': False,
                'message': 'Invalid Parfumo URL format. Must start with https://www.parfumo.com/'
            }

        db = Database()
        client = get_fragscrape_client()

        # Check if fragscrape is available
        if not client.health_check():
            return {
                'success': False,
                'message': 'fragscrape API is not available. Cannot fetch rating data.'
            }

        # Fetch rating data for the URL
        rating_data = client.fetch_rating(parfumo_url)

        if not rating_data or not rating_data.get('score'):
            # Save URL anyway but without rating
            db.update_fragrance_mapping(
                slug=slug,
                parfumo_id=parfumo_url
            )
            return {
                'success': True,
                'message': 'Parfumo URL saved, but no rating data available yet.',
                'has_rating': False
            }

        # Save URL and rating
        db.update_fragrance_rating(
            slug=slug,
            parfumo_id=parfumo_url,
            score=rating_data.get('score'),
            votes=rating_data.get('votes'),
            gender=rating_data.get('gender')
        )

        return {
            'success': True,
            'message': f'Parfumo data saved successfully. Rating: {rating_data.get("score")}/10',
            'has_rating': True,
            'rating': {
                'score': rating_data.get('score'),
                'votes': rating_data.get('votes'),
                'gender': rating_data.get('gender')
            }
        }

    except Exception as e:
        logger.error("Failed to set manual Parfumo URL", error=str(e), slug=slug)
        raise HTTPException(status_code=500, detail=str(e))
