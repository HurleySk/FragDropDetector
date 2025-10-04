"""
Parfumo Update Service
Handles periodic updates of Parfumo ratings and automatic scraping of new products
"""

import logging
from typing import Dict
from time import sleep

logger = logging.getLogger(__name__)


class ParfumoUpdater:
    """Service for updating Parfumo ratings periodically"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.currently_updating = False
            self.update_progress = 0
            self.update_message = ''

    def update_all_ratings(self, config: Dict = None) -> Dict:
        """Update Parfumo ratings for all fragrances needing updates"""
        from .fragrance_mapper import get_fragrance_mapper
        from .parfumo_scraper import get_parfumo_scraper
        from src.models.database import Database
        import yaml
        from pathlib import Path

        mapper = get_fragrance_mapper()
        scraper = get_parfumo_scraper()
        db = Database()

        # Load config for rate limit delay
        if config is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

        rate_limit_delay = config.get('parfumo', {}).get('rate_limit_delay', 5.0)

        # Set status
        self.currently_updating = True

        results = {
            'updated': 0,
            'failed': 0,
            'not_found': 0,
            'skipped': 0,
            'extracted': 0,
            'errors': []
        }

        try:
            # First, extract brand/name for fragrances that don't have it
            session = db.get_session()
            from src.models.database import FragranceStock

            unextracted = session.query(FragranceStock).filter(
                FragranceStock.original_brand.is_(None)
            ).all()
            session.close()

            if unextracted:
                logger.info(f"Extracting brand/name for {len(unextracted)} fragrances")
                extraction_total = len(unextracted)
                for idx, frag in enumerate(unextracted):
                    self.update_progress = int((idx / extraction_total) * 50)  # Extraction is first 50%
                    self.update_message = f"Extracting {idx+1}/{extraction_total}"
                    if mapper.update_mapping(frag.slug, frag.name, ''):
                        results['extracted'] += 1
                    sleep(0.1)  # Small delay
                self.update_progress = 50  # Extraction complete

            # Get fragrances needing updates from database
            fragrances = db.get_fragrances_needing_parfumo_update(skip_not_found_days=90)
            total = len(fragrances)

            logger.info(f"Found {total} fragrances needing Parfumo updates")

            for idx, frag in enumerate(fragrances):
                slug = frag['slug']
                brand = frag['original_brand']
                name = frag['original_name']
                parfumo_id = frag['parfumo_id']

                # Update progress: 50% for extraction + 50% for rating fetch
                self.update_progress = 50 + int((idx / max(total, 1)) * 50)
                self.update_message = f"Updating {idx+1}/{total}"

                logger.info(f"Processing {idx+1}/{total}: {slug}")

                # If no parfumo_id, try to find one
                if not parfumo_id:
                    parfumo_id = mapper.get_parfumo_id(brand, name)

                    if parfumo_id:
                        # Save the parfumo_id
                        db.update_fragrance_mapping(
                            slug=slug,
                            parfumo_id=parfumo_id
                        )
                    else:
                        # Mark as not found
                        db.mark_parfumo_not_found(slug)
                        results['not_found'] += 1
                        continue

                # Fetch rating
                try:
                    # Force refresh by clearing cache for this item
                    if parfumo_id in scraper.cache:
                        del scraper.cache[parfumo_id]
                        scraper.save_cache()

                    rating_data = scraper.fetch_rating(parfumo_id)

                    if rating_data and rating_data.get('score'):
                        # Save rating to database
                        db.update_fragrance_rating(
                            slug=slug,
                            parfumo_id=parfumo_id,
                            score=rating_data.get('score'),
                            votes=rating_data.get('votes')
                        )
                        results['updated'] += 1
                    else:
                        results['failed'] += 1

                except Exception as e:
                    logger.error(f"Error updating {slug}: {e}")
                    results['failed'] += 1
                    results['errors'].append(str(e))

                # Rate limiting - be respectful to Parfumo's servers
                sleep(rate_limit_delay)

        except Exception as e:
            logger.error(f"Error during Parfumo update: {e}")
            results['errors'].append(str(e))

        finally:
            self.currently_updating = False
            self.update_progress = 100
            self.update_message = 'Complete'

        logger.info(f"Parfumo update complete: {results}")

        # Reset progress after short delay
        from threading import Timer
        def reset_progress():
            self.update_progress = 0
            self.update_message = ''
        Timer(2.0, reset_progress).start()

        return results

    def update_single_fragrance(self, slug: str) -> bool:
        """Update Parfumo data for a single fragrance"""
        from .fragrance_mapper import get_fragrance_mapper
        from .parfumo_scraper import get_parfumo_scraper
        from src.models.database import Database

        mapper = get_fragrance_mapper()
        scraper = get_parfumo_scraper()
        db = Database()

        # Get mapping from database
        mapping = mapper.get_mapping(slug)

        if not mapping:
            logger.warning(f"No mapping found for {slug}")
            return False

        brand = mapping.get('original_brand')
        name = mapping.get('original_name')
        parfumo_id = mapping.get('parfumo_id')

        # Try to get Parfumo ID if not present
        if not parfumo_id and brand and name:
            parfumo_id = mapper.get_parfumo_id(brand, name)

            if parfumo_id:
                db.update_fragrance_mapping(slug=slug, parfumo_id=parfumo_id)
            else:
                db.mark_parfumo_not_found(slug)
                return False

        # Fetch rating
        if parfumo_id:
            try:
                rating_data = scraper.fetch_rating(parfumo_id)

                if rating_data and rating_data.get('score'):
                    db.update_fragrance_rating(
                        slug=slug,
                        parfumo_id=parfumo_id,
                        score=rating_data.get('score'),
                        votes=rating_data.get('votes')
                    )
                    return True

            except Exception as e:
                logger.error(f"Error fetching rating for {slug}: {e}")
                return False

        return False

    def get_status(self) -> Dict:
        """Get current update status"""
        from src.models.database import Database

        db = Database()
        session = db.get_session()

        try:
            from src.models.database import FragranceStock
            from sqlalchemy import func

            # Count statistics from database
            total_mapped = session.query(func.count(FragranceStock.id)).filter(
                FragranceStock.parfumo_id.isnot(None)
            ).scalar()

            total_not_found = session.query(func.count(FragranceStock.id)).filter(
                FragranceStock.parfumo_not_found == True
            ).scalar()

            total_with_ratings = session.query(func.count(FragranceStock.id)).filter(
                FragranceStock.parfumo_score.isnot(None)
            ).scalar()

            return {
                'currently_updating': self.currently_updating,
                'update_progress': self.update_progress,
                'update_message': self.update_message,
                'total_mapped': total_mapped,
                'total_not_found': total_not_found,
                'total_with_ratings': total_with_ratings
            }

        finally:
            session.close()


def get_parfumo_updater() -> ParfumoUpdater:
    """Get singleton instance of ParfumoUpdater"""
    return ParfumoUpdater()
