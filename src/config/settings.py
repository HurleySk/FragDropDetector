"""
Pydantic Settings Configuration
Type-safe configuration with environment variable support
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdvancedSettings(BaseSettings):
    """Advanced configuration settings"""
    max_retries: int = Field(default=3, ge=1, le=10)
    reddit_rate_limit_delay: int = Field(default=1, ge=0)
    retry_delay: int = Field(default=5, ge=1)
    user_agent: str = Field(default="FragDropDetector/1.0")

    model_config = SettingsConfigDict(env_prefix="ADVANCED_")


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    path: str = Field(default="data/fragdrop.db")
    retention_days: int = Field(default=30, ge=1)

    model_config = SettingsConfigDict(env_prefix="DB_")


class DetectionSettings(BaseSettings):
    """Drop detection configuration"""
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    primary_keywords: List[str] = Field(default=["drop", "restock"])
    secondary_keywords: List[str] = Field(default=["limited"])
    exclusion_keywords: List[str] = Field(
        default=["looking for", "where to buy", "wtb", "wts", "iso", "recommendation", "review"]
    )
    known_vendors: List[str] = Field(default=["montagneparfums", "montagne_parfums"])
    trusted_authors: List[str] = Field(
        default=["ayybrahamlmaocoln", "wide_parsley1799", "montagneparfums", "mpofficial"]
    )

    model_config = SettingsConfigDict(env_prefix="DETECTION_")


class DropWindowSettings(BaseSettings):
    """Drop window time configuration"""
    enabled: bool = Field(default=True)
    days_of_week: List[int] = Field(default=[4])  # Friday
    start_hour: int = Field(default=12, ge=0, le=23)
    start_minute: int = Field(default=0, ge=0, le=59)
    end_hour: int = Field(default=18, ge=0, le=23)
    end_minute: int = Field(default=0, ge=0, le=59)
    timezone: str = Field(default="America/New_York")

    model_config = SettingsConfigDict(env_prefix="DROP_WINDOW_")


class LogCleanupSettings(BaseSettings):
    """Log cleanup configuration"""
    enabled: bool = Field(default=True)
    cleanup_interval_hours: int = Field(default=24, ge=1)
    max_age_days: int = Field(default=30, ge=1)
    max_total_size_mb: int = Field(default=100, ge=1)
    compress_old_logs: bool = Field(default=True)
    clean_cache: bool = Field(default=True)
    cache_max_age_days: int = Field(default=7, ge=1)

    model_config = SettingsConfigDict(env_prefix="LOG_CLEANUP_")


class LoggingSettings(BaseSettings):
    """Logging configuration"""
    level: str = Field(default="INFO")
    file_enabled: bool = Field(default=True)
    file_path: str = Field(default="logs/fragdrop.log")
    max_file_size: int = Field(default=10, ge=1)
    backup_count: int = Field(default=5, ge=1)
    auto_cleanup: LogCleanupSettings = Field(default_factory=LogCleanupSettings)

    model_config = SettingsConfigDict(env_prefix="LOG_")


class MonitoringSettings(BaseSettings):
    """Health monitoring configuration"""
    health_check_enabled: bool = Field(default=False)
    health_check_port: int = Field(default=8080, ge=1024, le=65535)

    model_config = SettingsConfigDict(env_prefix="MONITORING_")


class DiscordNotificationSettings(BaseSettings):
    """Discord notification settings"""
    enabled: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix="DISCORD_")


class EmailNotificationSettings(BaseSettings):
    """Email notification settings"""
    enabled: bool = Field(default=False)

    model_config = SettingsConfigDict(env_prefix="EMAIL_")


class PushoverNotificationSettings(BaseSettings):
    """Pushover notification settings"""
    enabled: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix="PUSHOVER_")


class NotificationSettings(BaseSettings):
    """Notification configuration"""
    send_test_on_start: bool = Field(default=False)
    discord: DiscordNotificationSettings = Field(default_factory=DiscordNotificationSettings)
    email: EmailNotificationSettings = Field(default_factory=EmailNotificationSettings)
    pushover: PushoverNotificationSettings = Field(default_factory=PushoverNotificationSettings)

    model_config = SettingsConfigDict(env_prefix="NOTIFICATION_")


class ParfumoSettings(BaseSettings):
    """Parfumo scraping configuration"""
    enabled: bool = Field(default=True)
    auto_scrape_new: bool = Field(default=True)
    update_time: str = Field(default="02:00")
    last_update: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(env_prefix="PARFUMO_")


class RedditSettings(BaseSettings):
    """Reddit monitoring configuration"""
    subreddit: str = Field(default="MontagneParfums")
    check_interval: int = Field(default=300, ge=60, le=3600)
    post_limit: int = Field(default=50, ge=1, le=100)

    model_config = SettingsConfigDict(env_prefix="REDDIT_")


class StockNotificationSettings(BaseSettings):
    """Stock change notification preferences"""
    restocked_products: bool = Field(default=True)
    new_products: bool = Field(default=True)
    out_of_stock: bool = Field(default=False)
    price_changes: bool = Field(default=False)

    model_config = SettingsConfigDict(env_prefix="STOCK_NOTIF_")


class StockMonitoringSettings(BaseSettings):
    """Stock monitoring configuration"""
    enabled: bool = Field(default=True)
    watchlist: List[str] = Field(default=[])
    notifications: StockNotificationSettings = Field(default_factory=StockNotificationSettings)

    model_config = SettingsConfigDict(env_prefix="STOCK_MON_")


class StockScheduleSettings(BaseSettings):
    """Stock monitoring schedule"""
    enabled: bool = Field(default=True)
    window_enabled: bool = Field(default=False)
    check_interval: int = Field(default=900, ge=60)
    days_of_week: List[int] = Field(default=[])
    start_hour: int = Field(default=9, ge=0, le=23)
    start_minute: int = Field(default=0, ge=0, le=59)
    end_hour: int = Field(default=18, ge=0, le=23)
    end_minute: int = Field(default=0, ge=0, le=59)
    timezone: str = Field(default="America/New_York")

    model_config = SettingsConfigDict(env_prefix="STOCK_SCHEDULE_")


class AppSettings(BaseSettings):
    """Main application settings"""
    advanced: AdvancedSettings = Field(default_factory=AdvancedSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    detection: DetectionSettings = Field(default_factory=DetectionSettings)
    drop_window: DropWindowSettings = Field(default_factory=DropWindowSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    parfumo: ParfumoSettings = Field(default_factory=ParfumoSettings)
    reddit: RedditSettings = Field(default_factory=RedditSettings)
    stock_monitoring: StockMonitoringSettings = Field(default_factory=StockMonitoringSettings)
    stock_schedule: StockScheduleSettings = Field(default_factory=StockScheduleSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def to_dict(self) -> dict:
        """Convert settings to dictionary format compatible with legacy code"""
        return {
            'advanced': self.advanced.model_dump(),
            'database': self.database.model_dump(),
            'detection': self.detection.model_dump(),
            'drop_window': self.drop_window.model_dump(),
            'logging': {
                **self.logging.model_dump(exclude={'auto_cleanup'}),
                'auto_cleanup': self.logging.auto_cleanup.model_dump()
            },
            'monitoring': self.monitoring.model_dump(),
            'notifications': {
                **self.notifications.model_dump(exclude={'discord', 'email', 'pushover'}),
                'discord': self.notifications.discord.model_dump(),
                'email': self.notifications.email.model_dump(),
                'pushover': self.notifications.pushover.model_dump()
            },
            'parfumo': self.parfumo.model_dump(),
            'reddit': self.reddit.model_dump(),
            'stock_monitoring': {
                **self.stock_monitoring.model_dump(exclude={'notifications'}),
                'notifications': self.stock_monitoring.notifications.model_dump()
            },
            'stock_schedule': self.stock_schedule.model_dump()
        }


def get_settings() -> AppSettings:
    """Get application settings singleton"""
    return AppSettings()
