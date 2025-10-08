"""
Centralized timezone management for FragDropDetector
Provides timezone-aware datetime utilities
"""

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class TimezoneManager:
    """Manages timezone-aware datetime operations"""

    def __init__(self, timezone: str = 'America/New_York'):
        """
        Initialize timezone manager

        Args:
            timezone: IANA timezone name (e.g., 'America/New_York')
        """
        try:
            self.tz = ZoneInfo(timezone)
            self.timezone_name = timezone
        except Exception as e:
            logger.warning(f"Invalid timezone '{timezone}', falling back to UTC: {e}")
            self.tz = ZoneInfo('UTC')
            self.timezone_name = 'UTC'

    def now(self) -> datetime:
        """
        Get current time in configured timezone

        Returns:
            Timezone-aware datetime object
        """
        return datetime.now(self.tz)

    def utcnow(self) -> datetime:
        """
        Get current UTC time (timezone-aware)

        Returns:
            Timezone-aware datetime object in UTC
        """
        return datetime.now(ZoneInfo('UTC'))

    def to_iso_with_tz(self, dt: Optional[datetime]) -> Optional[str]:
        """
        Convert datetime to ISO string with timezone info

        Args:
            dt: Datetime object (naive or aware)

        Returns:
            ISO format string with timezone (e.g., '2025-10-08T15:28:01.722649+00:00')
            or None if input is None
        """
        if dt is None:
            return None

        # If naive, assume it's UTC (legacy compatibility)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo('UTC'))

        return dt.isoformat()

    def from_timestamp(self, ts: float) -> datetime:
        """
        Create timezone-aware datetime from Unix timestamp

        Args:
            ts: Unix timestamp in seconds

        Returns:
            Timezone-aware datetime in configured timezone
        """
        return datetime.fromtimestamp(ts, self.tz)

    def from_utc_timestamp(self, ts: float) -> datetime:
        """
        Create timezone-aware datetime from Unix timestamp (UTC)

        Args:
            ts: Unix timestamp in seconds

        Returns:
            Timezone-aware datetime in UTC
        """
        return datetime.fromtimestamp(ts, ZoneInfo('UTC'))

    def convert_naive_to_utc(self, dt: datetime) -> datetime:
        """
        Convert naive datetime to UTC timezone-aware datetime

        Args:
            dt: Naive datetime object (assumes UTC)

        Returns:
            Timezone-aware datetime in UTC
        """
        if dt.tzinfo is not None:
            return dt  # Already timezone-aware

        return dt.replace(tzinfo=ZoneInfo('UTC'))

    def convert_to_local(self, dt: datetime) -> datetime:
        """
        Convert datetime to configured local timezone

        Args:
            dt: Datetime object (naive or aware)

        Returns:
            Timezone-aware datetime in configured timezone
        """
        if dt.tzinfo is None:
            # Assume naive datetimes are UTC
            dt = dt.replace(tzinfo=ZoneInfo('UTC'))

        return dt.astimezone(self.tz)


# Singleton instance - will be initialized by ServiceContainer
_timezone_manager: Optional[TimezoneManager] = None


def get_timezone_manager(timezone: Optional[str] = None) -> TimezoneManager:
    """
    Get singleton timezone manager instance

    Args:
        timezone: Optional timezone name (only used on first call)

    Returns:
        TimezoneManager instance
    """
    global _timezone_manager
    if _timezone_manager is None:
        if timezone is None:
            timezone = 'America/New_York'  # Default
        _timezone_manager = TimezoneManager(timezone)
    return _timezone_manager


def reset_timezone_manager():
    """Reset singleton instance (for testing)"""
    global _timezone_manager
    _timezone_manager = None
