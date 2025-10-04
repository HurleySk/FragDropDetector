"""
Parfumo Scheduler Service
Handles scheduled daily updates of Parfumo ratings
"""

import logging
import threading
import time
import pytz
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ParfumoScheduler:
    """Service for scheduling daily Parfumo updates"""

    def __init__(self, config: Dict, updater=None):
        """
        Initialize Parfumo scheduler

        Args:
            config: Configuration dictionary
            updater: ParfumoUpdater instance (optional, will be imported if not provided)
        """
        self.config = config
        self.updater = updater
        self.scheduler_thread = None
        self.running = False

    def start(self) -> bool:
        """
        Start the scheduler thread

        Returns:
            True if started successfully, False if disabled or already running
        """
        if not self.config.get('parfumo', {}).get('enabled', True):
            logger.info("Parfumo scheduler disabled in configuration")
            return False

        if self.running:
            logger.warning("Parfumo scheduler already running")
            return False

        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("Parfumo scheduler started")
        return True

    def stop(self):
        """Stop the scheduler thread"""
        self.running = False
        if self.scheduler_thread:
            logger.info("Parfumo scheduler stopping")

    def _scheduler_loop(self):
        """Main scheduler loop that runs in background thread"""
        while self.running:
            try:
                seconds_to_wait = self._calculate_next_update_delay()

                if seconds_to_wait > 0:
                    logger.info(
                        f"Next Parfumo update in {seconds_to_wait/3600:.1f} hours "
                        f"(at {self._get_next_scheduled_time().strftime('%Y-%m-%d %H:%M %Z')})"
                    )

                    # Sleep in smaller intervals to allow clean shutdown
                    while seconds_to_wait > 0 and self.running:
                        sleep_time = min(seconds_to_wait, 60)  # Check every minute
                        time.sleep(sleep_time)
                        seconds_to_wait -= sleep_time

                if self.running:
                    self.run_update()

            except Exception as e:
                logger.error(f"Error in Parfumo scheduler: {e}")
                # Wait an hour before trying again if there's an error
                time.sleep(3600)

    def _calculate_next_update_delay(self) -> float:
        """
        Calculate seconds until next scheduled update

        Returns:
            Number of seconds to wait
        """
        scheduled_time = self._get_next_scheduled_time()
        now = self._get_current_time()
        return (scheduled_time - now).total_seconds()

    def _get_next_scheduled_time(self) -> datetime:
        """
        Get the next scheduled update time

        Returns:
            datetime object for next scheduled update
        """
        update_time_str = self.config.get('parfumo', {}).get('update_time', '02:00')
        update_hour, update_minute = map(int, update_time_str.split(':'))

        # Use configured timezone
        drop_window_config = self.config.get('drop_window', {})
        timezone = drop_window_config.get('timezone', 'America/New_York')
        tz = pytz.timezone(timezone)

        now = self._get_current_time()
        scheduled_time = now.replace(hour=update_hour, minute=update_minute, second=0, microsecond=0)

        # If the scheduled time has already passed today, schedule for tomorrow
        if scheduled_time <= now:
            scheduled_time = scheduled_time + timedelta(days=1)

        return scheduled_time

    def _get_current_time(self) -> datetime:
        """Get current time in configured timezone"""
        drop_window_config = self.config.get('drop_window', {})
        timezone = drop_window_config.get('timezone', 'America/New_York')
        tz = pytz.timezone(timezone)
        return datetime.now(tz)

    def run_update(self) -> Optional[Dict]:
        """
        Run the Parfumo update immediately

        Returns:
            Update results dictionary or None if update failed/skipped
        """
        try:
            # Lazy import to avoid circular dependencies
            if self.updater is None:
                from src.services.parfumo_updater import get_parfumo_updater
                self.updater = get_parfumo_updater()

            # Check if not already updating
            status = self.updater.get_status()
            if status.get('currently_updating'):
                logger.info("Parfumo update already in progress, skipping")
                return None

            logger.info("Starting scheduled Parfumo update")

            # Run update
            results = self.updater.update_all_ratings()
            logger.info(f"Parfumo update completed: {results}")

            # Update config with last update time
            self._update_last_update_time()

            return results

        except Exception as e:
            logger.error(f"Error running Parfumo update: {e}")
            return None

    def _update_last_update_time(self):
        """Update the last update time in config file"""
        try:
            import yaml

            self.config['parfumo']['last_update'] = datetime.now().isoformat()

            # Save config
            with open('config/config.yaml', 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)

        except Exception as e:
            logger.error(f"Error saving last update time: {e}")


def get_parfumo_scheduler(config: Dict) -> ParfumoScheduler:
    """
    Factory function to create ParfumoScheduler instance

    Args:
        config: Configuration dictionary

    Returns:
        ParfumoScheduler instance
    """
    return ParfumoScheduler(config)
