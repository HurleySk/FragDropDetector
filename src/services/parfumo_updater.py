"""
Parfumo Update Service
Handles periodic updates of Parfumo ratings and automatic scraping of new products
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
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
            self.status_file = os.path.join(os.getcwd(), 'data', 'parfumo_status.json')
            self.status = self.load_status()

    def load_status(self) -> Dict:
        """Load status from file"""
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading Parfumo status: {e}")

        return {
            'last_full_update': None,
            'total_mapped': 0,
            'total_not_found': 0,
            'total_with_ratings': 0,
            'currently_updating': False,
            'update_progress': 0,
            'last_error': None
        }

    def save_status(self):
        """Save status to file"""
        try:
            os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
            with open(self.status_file, 'w') as f:
                json.dump(self.status, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving Parfumo status: {e}")

    def update_all_ratings(self) -> Dict:
        """Update Parfumo ratings for all mapped fragrances"""
        from .fragrance_mapper import get_fragrance_mapper
        from .parfumo_scraper import get_parfumo_scraper

        mapper = get_fragrance_mapper()
        scraper = get_parfumo_scraper()

        # Set status
        self.status['currently_updating'] = True
        self.status['update_progress'] = 0
        self.save_status()

        results = {
            'updated': 0,
            'failed': 0,
            'not_found': 0,
            'skipped': 0,
            'errors': []
        }

        try:
            # Get all mappings - always update all
            mappings = mapper.mappings
            total = len(mappings)
            items_to_update = list(mappings.items())

            for idx, (slug, mapping) in enumerate(items_to_update):
                # Update progress
                self.status['update_progress'] = int((idx + 1) / len(items_to_update) * 100)
                self.save_status()

                # Skip if marked as not found recently
                if mapping.get('parfumo_not_found'):
                    last_searched = mapping.get('last_searched')
                    if last_searched:
                        last_date = datetime.fromisoformat(last_searched)
                        if datetime.now() - last_date < timedelta(days=90):
                            results['skipped'] += 1
                            continue

                # Skip if no original brand/name
                if not mapping.get('original_brand') or not mapping.get('original_name'):
                    results['skipped'] += 1
                    continue

                # Try to get Parfumo ID if not present
                if not mapping.get('parfumo_id'):
                    parfumo_id = mapper.get_parfumo_id(
                        mapping['original_brand'],
                        mapping['original_name']
                    )

                    if parfumo_id:
                        mapping['parfumo_id'] = parfumo_id
                        mapper.mappings[slug] = mapping
                        mapper.save_mappings()
                    else:
                        # Mark as not found
                        mapping['parfumo_not_found'] = True
                        mapping['last_searched'] = datetime.now().isoformat()
                        mapper.mappings[slug] = mapping
                        mapper.save_mappings()
                        results['not_found'] += 1
                        continue

                # Fetch latest rating
                if mapping.get('parfumo_id'):
                    try:
                        # Force refresh by clearing cache for this item
                        if mapping['parfumo_id'] in scraper.cache:
                            del scraper.cache[mapping['parfumo_id']]
                            scraper.save_cache()

                        rating_data = scraper.fetch_rating(mapping['parfumo_id'])
                        if rating_data:
                            results['updated'] += 1
                        else:
                            results['failed'] += 1

                    except Exception as e:
                        logger.error(f"Error updating {slug}: {e}")
                        results['failed'] += 1
                        results['errors'].append(str(e))

                # Rate limiting
                sleep(1)  # 1 second between requests

            # Update status
            self.status['last_full_update'] = datetime.now().isoformat()
            self.status['total_mapped'] = len([m for m in mappings.values() if m.get('parfumo_id')])
            self.status['total_not_found'] = len([m for m in mappings.values() if m.get('parfumo_not_found')])

            # Count items with ratings in cache
            rating_count = 0
            for mapping in mappings.values():
                if mapping.get('parfumo_id') and mapping['parfumo_id'] in scraper.cache:
                    if scraper.cache[mapping['parfumo_id']].get('score'):
                        rating_count += 1
            self.status['total_with_ratings'] = rating_count

        except Exception as e:
            logger.error(f"Error during Parfumo update: {e}")
            self.status['last_error'] = str(e)
            results['errors'].append(str(e))

        finally:
            self.status['currently_updating'] = False
            self.status['update_progress'] = 100
            self.save_status()

        return results

    def update_single_fragrance(self, slug: str) -> bool:
        """Update Parfumo data for a single fragrance"""
        from .fragrance_mapper import get_fragrance_mapper
        from .parfumo_scraper import get_parfumo_scraper

        mapper = get_fragrance_mapper()
        scraper = get_parfumo_scraper()

        # Get or create mapping
        mapping = mapper.get_mapping(slug)
        if not mapping:
            # Try to create mapping from database
            from src.models.database import Database
            db = Database()
            fragrances = db.get_all_fragrances()

            if slug in fragrances:
                product = fragrances[slug]
                mapping = mapper.update_mapping(slug, product['name'], '')

        if not mapping:
            logger.warning(f"No mapping found for {slug}")
            return False

        # Try to get Parfumo ID if not present
        if not mapping.get('parfumo_id'):
            if mapping.get('original_brand') and mapping.get('original_name'):
                parfumo_id = mapper.get_parfumo_id(
                    mapping['original_brand'],
                    mapping['original_name']
                )

                if parfumo_id:
                    mapping['parfumo_id'] = parfumo_id
                    mapper.mappings[slug] = mapping
                    mapper.save_mappings()
                else:
                    # Mark as not found
                    mapping['parfumo_not_found'] = True
                    mapping['last_searched'] = datetime.now().isoformat()
                    mapper.mappings[slug] = mapping
                    mapper.save_mappings()
                    return False

        # Fetch rating
        if mapping.get('parfumo_id'):
            try:
                rating_data = scraper.fetch_rating(mapping['parfumo_id'])
                return rating_data is not None
            except Exception as e:
                logger.error(f"Error fetching rating for {slug}: {e}")
                return False

        return False

    def get_status(self) -> Dict:
        """Get current update status"""
        return self.status.copy()

    def get_last_update_date(self, config: Dict) -> Optional[datetime]:
        """Get the last update date from config"""
        last_update = config.get('parfumo', {}).get('last_update')
        if last_update:
            try:
                return datetime.fromisoformat(last_update)
            except:
                pass
        return None


def get_parfumo_updater() -> ParfumoUpdater:
    """Get singleton instance of ParfumoUpdater"""
    return ParfumoUpdater()