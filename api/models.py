"""
Pydantic models for API validation
"""

import sys
import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
from config import constants


class RedditConfig(BaseModel):
    client_id: str = Field(..., min_length=1, description="Reddit API client ID")
    client_secret: str = Field(..., min_length=1, description="Reddit API client secret")
    user_agent: str = Field(default="FragDropDetector/1.0", min_length=1)
    subreddit: str = Field(default="MontagneParfums", min_length=1)
    check_interval: int = Field(
        default=constants.MonitoringConfig.REDDIT_CHECK_INTERVAL_SECONDS,
        ge=constants.ValidationLimits.MIN_CHECK_INTERVAL,
        le=constants.ValidationLimits.MAX_CHECK_INTERVAL,
        description="Check interval in seconds"
    )
    post_limit: int = Field(
        default=constants.MonitoringConfig.POST_LIMIT,
        ge=constants.ValidationLimits.MIN_DROPS_LIMIT,
        le=constants.ValidationLimits.MAX_DROPS_LIMIT
    )


class NotificationConfig(BaseModel):
    pushover_app_token: Optional[str] = Field(default=None)
    pushover_user_key: Optional[str] = Field(default=None)
    discord_webhook_url: Optional[str] = Field(default=None)


class DetectionConfig(BaseModel):
    primary_keywords: List[str] = Field(default_factory=list, min_items=1)
    secondary_keywords: List[str] = Field(default_factory=list)
    confidence_threshold: float = Field(
        default=constants.DetectionConfig.DEFAULT_CONFIDENCE_THRESHOLD,
        ge=constants.ValidationLimits.MIN_CONFIDENCE,
        le=constants.ValidationLimits.MAX_CONFIDENCE
    )
    known_vendors: List[str] = Field(default_factory=list)
    exclusion_keywords: List[str] = Field(default_factory=list)
    trusted_authors: List[str] = Field(default_factory=list)


class DropWindowConfig(BaseModel):
    enabled: bool = Field(default=constants.DropWindowConfig.ENABLED)
    timezone: str = Field(default=constants.DropWindowConfig.TIMEZONE)
    days_of_week: List[int] = Field(default_factory=lambda: constants.DropWindowConfig.DEFAULT_DAYS, min_items=1, max_items=7)
    start_hour: int = Field(
        default=constants.DropWindowConfig.START_HOUR,
        ge=constants.ValidationLimits.MIN_HOUR,
        le=constants.ValidationLimits.MAX_HOUR
    )
    start_minute: int = Field(
        default=constants.DropWindowConfig.START_MINUTE,
        ge=constants.ValidationLimits.MIN_MINUTE,
        le=constants.ValidationLimits.MAX_MINUTE
    )
    end_hour: int = Field(
        default=constants.DropWindowConfig.END_HOUR,
        ge=constants.ValidationLimits.MIN_HOUR,
        le=constants.ValidationLimits.MAX_HOUR
    )
    end_minute: int = Field(
        default=constants.DropWindowConfig.END_MINUTE,
        ge=constants.ValidationLimits.MIN_MINUTE,
        le=constants.ValidationLimits.MAX_MINUTE
    )

    @field_validator('days_of_week')
    @classmethod
    def validate_days(cls, v):
        if not all(constants.ValidationLimits.MIN_DAYS_OF_WEEK <= day <= constants.ValidationLimits.MAX_DAYS_OF_WEEK for day in v):
            raise ValueError('Days of week must be between 0-6 (Monday-Sunday)')
        return list(set(v))


class StockMonitoringConfig(BaseModel):
    enabled: bool = Field(default=True)
    new_products: bool = Field(default=True)
    restocked_products: bool = Field(default=True)
    price_changes: bool = Field(default=False)
    out_of_stock: bool = Field(default=False)


class StockScheduleConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable stock schedule monitoring")
    check_interval: int = Field(default=1800, ge=60, le=86400, description="Check interval in seconds (1 min - 24 hours)")
    window_enabled: bool = Field(default=False, description="Enable time window restrictions")
    timezone: str = Field(default="America/New_York", description="Timezone for window checking")
    days_of_week: List[int] = Field(default_factory=list, description="Days of week (0=Monday, 6=Sunday), empty=all days")
    start_hour: int = Field(default=9, ge=0, le=23, description="Start hour (24h format)")
    start_minute: int = Field(default=0, ge=0, le=59, description="Start minute")
    end_hour: int = Field(default=18, ge=0, le=23, description="End hour (24h format)")
    end_minute: int = Field(default=0, ge=0, le=59, description="End minute")

    @field_validator('days_of_week')
    @classmethod
    def validate_days(cls, v):
        if not all(0 <= day <= 6 for day in v):
            raise ValueError('Days of week must be between 0-6 (Monday-Sunday)')
        return list(set(v))


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    file_enabled: bool = Field(default=True)
    file_path: str = Field(default="logs/fragdrop.log")
    max_file_size: int = Field(default=10, ge=1, le=100, description="Max file size in MB")
    backup_count: int = Field(default=5, ge=0, le=20)
    auto_cleanup: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "max_age_days": 30,
        "max_total_size_mb": 100,
        "cleanup_interval_hours": 24,
        "compress_old_logs": True,
        "clean_cache": True,
        "cache_max_age_days": 7
    })


class StatusResponse(BaseModel):
    running: bool
    last_check: Optional[str] = None
    drops_detected: int = 0
    posts_processed: int = 0
    fragrances_tracked: int = 0
    recent_stock_changes: int = 0
    next_window: Optional[str] = None
    notifications_enabled: Dict[str, bool] = Field(default_factory=dict)
    reddit_status: Dict[str, Any] = Field(default_factory=dict)
