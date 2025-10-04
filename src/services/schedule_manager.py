"""
Schedule Management for Drop Windows and Stock Monitoring
Consolidates window checking logic used by main.py and API routes
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pytz

logger = logging.getLogger(__name__)


class ScheduleManager:
    """Manages monitoring schedules and time windows"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize schedule manager with configuration

        Args:
            config: Full configuration dict with drop_window and stock_schedule sections
        """
        self.config = config

    def is_drop_window(self) -> bool:
        """
        Check if current time is within configured Reddit drop window

        Returns:
            True if within drop window or window checking is disabled
        """
        drop_window_config = self.config.get('drop_window', {})

        if not drop_window_config.get('enabled', True):
            return True

        return self._is_within_window(
            timezone=drop_window_config.get('timezone', 'America/New_York'),
            days_of_week=drop_window_config.get('days_of_week', [4]),
            start_hour=drop_window_config.get('start_hour', 12),
            start_minute=drop_window_config.get('start_minute', 0),
            end_hour=drop_window_config.get('end_hour', 17),
            end_minute=drop_window_config.get('end_minute', 0)
        )

    def is_stock_window(self) -> bool:
        """
        Check if current time is within configured stock monitoring window

        Returns:
            True if within stock window or window checking is disabled
        """
        stock_schedule = self.config.get('stock_schedule', {})

        if not stock_schedule.get('enabled', True):
            return False

        if not stock_schedule.get('window_enabled', False):
            return True

        days_of_week = stock_schedule.get('days_of_week', [])
        if not days_of_week:
            days_of_week = [0, 1, 2, 3, 4, 5, 6]

        return self._is_within_window(
            timezone=stock_schedule.get('timezone', 'America/New_York'),
            days_of_week=days_of_week,
            start_hour=stock_schedule.get('start_hour', 9),
            start_minute=stock_schedule.get('start_minute', 0),
            end_hour=stock_schedule.get('end_hour', 18),
            end_minute=stock_schedule.get('end_minute', 0)
        )

    def get_time_until_next_drop_window(self) -> float:
        """
        Calculate time until next configured drop window

        Returns:
            Seconds until next window start, 0 if window checking is disabled
        """
        drop_window_config = self.config.get('drop_window', {})

        if not drop_window_config.get('enabled', True):
            return 0

        return self._get_time_until_next_window(
            timezone=drop_window_config.get('timezone', 'America/New_York'),
            days_of_week=drop_window_config.get('days_of_week', [4]),
            start_hour=drop_window_config.get('start_hour', 12),
            start_minute=drop_window_config.get('start_minute', 0),
            end_hour=drop_window_config.get('end_hour', 17),
            end_minute=drop_window_config.get('end_minute', 0)
        )

    def get_drop_window_description(self) -> str:
        """
        Get human-readable description of drop window

        Returns:
            Description string like "Fridays 12:00-17:00 America/New_York"
        """
        drop_window_config = self.config.get('drop_window', {})

        if not drop_window_config.get('enabled', True):
            return "Always active (no time restrictions)"

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        days = drop_window_config.get('days_of_week', [4])
        configured_days = ', '.join([day_names[d] for d in sorted(days)])

        start_hour = drop_window_config.get('start_hour', 12)
        start_minute = drop_window_config.get('start_minute', 0)
        end_hour = drop_window_config.get('end_hour', 17)
        end_minute = drop_window_config.get('end_minute', 0)
        timezone = drop_window_config.get('timezone', 'America/New_York')

        window_time = f"{start_hour:02d}:{start_minute:02d}-{end_hour:02d}:{end_minute:02d}"

        return f"{configured_days} {window_time} {timezone}"

    def get_stock_window_description(self) -> str:
        """
        Get human-readable description of stock window

        Returns:
            Description string
        """
        stock_schedule = self.config.get('stock_schedule', {})

        if not stock_schedule.get('enabled', True):
            return "Stock monitoring disabled"

        if not stock_schedule.get('window_enabled', False):
            return "24/7 monitoring (no time restrictions)"

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        days = stock_schedule.get('days_of_week', [])

        if not days:
            configured_days = "Daily"
        else:
            configured_days = ', '.join([day_names[d] for d in sorted(days)])

        start_hour = stock_schedule.get('start_hour', 9)
        start_minute = stock_schedule.get('start_minute', 0)
        end_hour = stock_schedule.get('end_hour', 18)
        end_minute = stock_schedule.get('end_minute', 0)
        timezone = stock_schedule.get('timezone', 'America/New_York')

        window_time = f"{start_hour:02d}:{start_minute:02d}-{end_hour:02d}:{end_minute:02d}"

        return f"{configured_days} {window_time} {timezone}"

    def _is_within_window(
        self,
        timezone: str,
        days_of_week: List[int],
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int
    ) -> bool:
        """
        Check if current time is within specified window

        Args:
            timezone: Timezone string (e.g., 'America/New_York')
            days_of_week: List of day numbers (0=Monday, 6=Sunday)
            start_hour: Window start hour (0-23)
            start_minute: Window start minute (0-59)
            end_hour: Window end hour (0-23)
            end_minute: Window end minute (0-59)

        Returns:
            True if current time is within the window
        """
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)

        if now.weekday() not in days_of_week:
            return False

        current_time = now.time()
        start_time = time(hour=start_hour, minute=start_minute)
        end_time = time(hour=end_hour, minute=end_minute)

        return start_time <= current_time < end_time

    def _get_time_until_next_window(
        self,
        timezone: str,
        days_of_week: List[int],
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int
    ) -> float:
        """
        Calculate seconds until next window start

        Args:
            timezone: Timezone string
            days_of_week: List of day numbers
            start_hour: Window start hour
            start_minute: Window start minute
            end_hour: Window end hour
            end_minute: Window end minute

        Returns:
            Seconds until next window start
        """
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)

        min_days_until = 7
        for day in days_of_week:
            days_until = (day - now.weekday()) % 7

            if days_until == 0:
                current_time = now.time()
                end_time = time(hour=end_hour, minute=end_minute)

                if current_time >= end_time:
                    days_until = 7

            min_days_until = min(min_days_until, days_until)

        next_window = now.replace(
            hour=start_hour,
            minute=start_minute,
            second=0,
            microsecond=0
        )

        if min_days_until == 0 and now.hour < start_hour:
            pass
        else:
            next_window = next_window + timedelta(days=min_days_until if min_days_until > 0 else 7)

        time_diff = next_window - now
        return time_diff.total_seconds()
