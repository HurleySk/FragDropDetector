"""
Parfumo Update Service
Handles periodic updates of Parfumo ratings and automatic scraping of new products
"""

import logging
from typing import Dict
from time import sleep
from datetime import datetime

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

    def update_all_ratings(self, config: Dict = None, force_refresh: bool = False) -> Dict:
        """Update Parfumo ratings for all fragrances needing updates"""
        from .fragrance_mapper import get_fragrance_mapper
        from .fragscrape_client import get_fragscrape_client
        from src.models.database import Database
        import yaml
        from pathlib import Path

        mapper = get_fragrance_mapper()
        client = get_fragscrape_client()
        db = Database()

        # Check if fragscrape is available before proceeding
        if not client.health_check():
            logger.error("fragscrape API is not available - cannot update ratings")
            return {
                'updated': 0,
                'failed': 0,
                'not_found': 0,
                'skipped': 0,
                'extracted': 0,
                'rate_limited': 0,
                'errors': ['fragscrape API is not available']
            }

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
            'rate_limited': 0,
            'errors': []
        }

        # Track consecutive rate limits for backoff
        consecutive_rate_limits = 0
        max_consecutive_rate_limits = 5

        try:
            # First, extract brand/name for fragrances that don't have it
            session = db.get_session()
            from src.models.database import FragranceStock

            unextracted = session.query(FragranceStock).filter(
                FragranceStock.original_brand.is_(None)
            ).all()
            session.close()

            # Calculate total work (will update rating_count after extraction)
            extraction_count = len(unextracted) if unextracted else 0
            completed = 0

            if unextracted:
                from .fragscrape_client import RateLimitError

                logger.info(f"Extracting brand/name for {extraction_count} fragrances")
                for idx, frag in enumerate(unextracted):
                    # Progress during extraction phase (assume 50% for extraction, 50% for ratings)
                    self.update_progress = int((completed / (extraction_count * 2)) * 100)
                    self.update_message = f"Extracting {idx+1}/{extraction_count}"

                    try:
                        if mapper.update_mapping(frag.slug, frag.name, ''):
                            results['extracted'] += 1
                            consecutive_rate_limits = 0  # Reset on success
                        sleep(0.1)

                    except RateLimitError as rate_err:
                        consecutive_rate_limits += 1
                        results['rate_limited'] += 1

                        # Check if we're being rate limited too much
                        if consecutive_rate_limits >= max_consecutive_rate_limits:
                            logger.error(f"Hit {consecutive_rate_limits} consecutive rate limits during extraction - pausing update")
                            self.update_message = f"Rate limited - pausing"
                            results['errors'].append(f"Exceeded max consecutive rate limits during extraction ({max_consecutive_rate_limits})")
                            raise  # Exit the entire update

                        # Exponential backoff
                        backoff_delay = min(rate_err.retry_after or (2 ** consecutive_rate_limits), 30)
                        logger.warning(f"Rate limited during extraction, waiting {backoff_delay}s")
                        self.update_message = f"Rate limited - waiting {backoff_delay}s"
                        sleep(backoff_delay)

                    completed += 1

            # Query for fragrances needing ratings AFTER extraction completes
            # force_refresh=True for manual updates, False for scheduled
            fragrances = db.get_fragrances_needing_parfumo_update(
                skip_not_found_days=90,
                force_refresh_all=force_refresh,
                max_rating_age_days=7
            )

            rating_count = len(fragrances)
            total_work = extraction_count + rating_count

            logger.info(f"Found {rating_count} fragrances needing Parfumo updates")

            for idx, frag in enumerate(fragrances):
                slug = frag['slug']
                brand = frag['original_brand']
                name = frag['original_name']
                parfumo_id = frag['parfumo_id']

                # Update progress based on total work
                self.update_progress = int((completed / max(total_work, 1)) * 100)
                self.update_message = f"Updating {idx+1}/{rating_count}"

                logger.info(f"Processing {idx+1}/{rating_count}: {slug}")

                # Check if we should preemptively throttle
                if client.should_throttle(threshold=10):
                    status = client.get_rate_limit_status()
                    wait_time = status.get('reset_in_seconds', 60)
                    logger.warning(f"Preemptively throttling - {status['remaining']}/{status['limit']} requests remaining, waiting {wait_time}s")
                    self.update_message = f"Rate limit low - waiting {wait_time}s"
                    sleep(wait_time + 1)  # Wait for reset + 1 second buffer

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
                        completed += 1
                        continue

                # Fetch rating with retry on rate limiting
                try:
                    from .fragscrape_client import RateLimitError

                    max_retries = 3
                    retry_count = 0
                    rating_data = None

                    while retry_count <= max_retries:
                        try:
                            # Note: fragscrape has its own caching system
                            rating_data = client.fetch_rating(parfumo_id)
                            consecutive_rate_limits = 0  # Reset on success
                            break

                        except RateLimitError as rate_err:
                            retry_count += 1
                            consecutive_rate_limits += 1
                            results['rate_limited'] += 1

                            # Check if we're being rate limited too much
                            if consecutive_rate_limits >= max_consecutive_rate_limits:
                                logger.error(f"Hit {consecutive_rate_limits} consecutive rate limits - pausing update")
                                self.update_message = f"Rate limited - pausing"
                                results['errors'].append(f"Exceeded max consecutive rate limits ({max_consecutive_rate_limits})")
                                raise  # Exit the entire update

                            if retry_count > max_retries:
                                logger.warning(f"Max retries ({max_retries}) exceeded for {slug}")
                                results['errors'].append(f"{slug}: Rate limited after {max_retries} retries")
                                break

                            # Exponential backoff: 2s, 4s, 8s
                            backoff_delay = min(rate_err.retry_after or (2 ** retry_count), 30)
                            logger.warning(f"Rate limited on {slug}, retry {retry_count}/{max_retries} after {backoff_delay}s")
                            self.update_message = f"Rate limited - waiting {backoff_delay}s"
                            sleep(backoff_delay)

                    if rating_data and rating_data.get('score'):
                        # Save rating to database (use URL from rating_data)
                        db.update_fragrance_rating(
                            slug=slug,
                            parfumo_id=rating_data.get('parfumo_id', parfumo_id),
                            score=rating_data.get('score'),
                            votes=rating_data.get('votes'),
                            gender=rating_data.get('gender')
                        )
                        results['updated'] += 1
                    else:
                        results['failed'] += 1

                except Exception as e:
                    logger.error(f"Error updating {slug}: {e}")
                    results['failed'] += 1
                    results['errors'].append(str(e))

                # Only sleep normal delay if we weren't rate limited
                if consecutive_rate_limits == 0:
                    # Use dynamic delay based on current rate limit status
                    dynamic_delay = client.get_recommended_delay(rate_limit_delay)
                    if dynamic_delay > rate_limit_delay * 1.5:
                        logger.info(f"Auto-adjusted delay to {dynamic_delay:.1f}s based on rate limits")
                    sleep(dynamic_delay)

                # Increment progress after work is complete
                completed += 1

        except Exception as e:
            logger.error(f"Error during Parfumo update: {e}")
            results['errors'].append(str(e))

        finally:
            self.currently_updating = False
            self.update_progress = 100
            self.update_message = 'Complete'

        logger.info(f"Parfumo update complete: {results}")

        # Update last_update timestamp in config.yaml
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    full_config = yaml.safe_load(f)

                if 'parfumo' not in full_config:
                    full_config['parfumo'] = {}

                full_config['parfumo']['last_update'] = datetime.now().isoformat()

                with open(config_path, 'w') as f:
                    yaml.safe_dump(full_config, f, default_flow_style=False, sort_keys=False)

                logger.info(f"Updated last_update timestamp in config")
        except Exception as e:
            logger.error(f"Failed to update last_update in config: {e}")

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
        from .fragscrape_client import get_fragscrape_client
        from src.models.database import Database

        mapper = get_fragrance_mapper()
        client = get_fragscrape_client()
        db = Database()

        # Check if fragscrape is available
        if not client.health_check():
            logger.warning("fragscrape API is not available - skipping update")
            return False

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
                rating_data = client.fetch_rating(parfumo_id)

                if rating_data and rating_data.get('score'):
                    db.update_fragrance_rating(
                        slug=slug,
                        parfumo_id=rating_data.get('parfumo_id', parfumo_id),
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
        import yaml
        from pathlib import Path

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

            # Read last_update from config.yaml
            last_full_update = None
            try:
                config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                        last_full_update = config.get('parfumo', {}).get('last_update')
            except Exception as e:
                logger.debug(f"Error reading last_update from config: {e}")

            return {
                'currently_updating': self.currently_updating,
                'update_progress': self.update_progress,
                'update_message': self.update_message,
                'total_mapped': total_mapped,
                'total_not_found': total_not_found,
                'total_with_ratings': total_with_ratings,
                'last_full_update': last_full_update
            }

        finally:
            session.close()


def get_parfumo_updater() -> ParfumoUpdater:
    """Get singleton instance of ParfumoUpdater"""
    return ParfumoUpdater()
