"""
Application constants and configuration defaults
Centralizes magic numbers and hardcoded values for easier maintenance
"""

from typing import List


class CacheConfig:
    """Cache-related constants"""
    STOCK_TTL_MINUTES = 15
    API_TTL_SECONDS = 30
    CACHE_DIR = "cache"


class MonitoringConfig:
    """Monitoring intervals and timeouts"""
    REDDIT_CHECK_INTERVAL_SECONDS = 300  # 5 minutes
    STOCK_CHECK_INTERVAL_SECONDS = 1800  # 30 minutes
    POST_LIMIT = 50

    # Timeouts
    PLAYWRIGHT_TIMEOUT_MS = 30000
    NETWORK_IDLE_TIMEOUT_MS = 10000

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY_SECONDS = 1.0
    MAX_RETRY_DELAY_SECONDS = 30.0


class DetectionConfig:
    """Drop detection configuration"""
    DEFAULT_CONFIDENCE_THRESHOLD = 0.4
    HIGH_CONFIDENCE_THRESHOLD = 0.8

    # Default primary keywords
    DEFAULT_PRIMARY_KEYWORDS: List[str] = [
        'restock', 'restocked', 'restocking',
        'drop', 'dropped', 'dropping', 'drops',
        'release', 'released', 'releasing',
        'available', 'availability',
        'launch', 'launched', 'launching',
        'in stock', 'back in stock',
        'now live', 'live now',
        'new fragrance', 'new perfume',
        'new cologne', 'new scent'
    ]

    # Default secondary keywords
    DEFAULT_SECONDARY_KEYWORDS: List[str] = [
        'limited', 'exclusive', 'special',
        'pre-order', 'preorder',
        'sale', 'discount',
        'batch', 'decant',
        'split', 'sample',
        'bottle', 'ml',
        'price', 'pricing',
        'order', 'ordering',
        'link', 'website'
    ]

    # Default exclusion patterns
    DEFAULT_EXCLUSION_PATTERNS: List[str] = [
        r'looking\s+for',
        r'where\s+to\s+buy',
        r'anyone\s+have',
        r'wtb',  # want to buy
        r'wts',  # want to sell
        r'iso',  # in search of
        r'recommendation',
        r'review',
        r'thoughts\s+on',
        r'\[wtb\]',
        r'\[wts\]'
    ]

    # Default trusted authors
    DEFAULT_TRUSTED_AUTHORS: List[str] = [
        'ayybrahamlmaocoln',
        'wide_parsley1799',
        'montagneparfums',
        'mpofficial'
    ]


class DropWindowConfig:
    """Default drop window configuration"""
    ENABLED = True
    TIMEZONE = 'America/New_York'
    DEFAULT_DAYS = [4]  # Friday
    START_HOUR = 12
    START_MINUTE = 0
    END_HOUR = 17
    END_MINUTE = 0


class StockWindowConfig:
    """Default stock monitoring window configuration"""
    ENABLED = True
    WINDOW_ENABLED = False  # 24/7 by default
    TIMEZONE = 'America/New_York'
    DEFAULT_DAYS: List[int] = []  # Empty = all days
    START_HOUR = 9
    START_MINUTE = 0
    END_HOUR = 18
    END_MINUTE = 0


class LoggingConfig:
    """Logging configuration defaults"""
    DEFAULT_LEVEL = 'INFO'
    DEFAULT_FILE_PATH = 'logs/fragdrop.log'
    MAX_FILE_SIZE_MB = 10
    BACKUP_COUNT = 5

    # Auto cleanup defaults
    AUTO_CLEANUP_ENABLED = True
    MAX_LOG_AGE_DAYS = 30
    MAX_TOTAL_SIZE_MB = 100
    CLEANUP_INTERVAL_HOURS = 24
    COMPRESS_OLD_LOGS = True
    CLEAN_CACHE = True
    CACHE_MAX_AGE_DAYS = 7


class WebServerConfig:
    """Web server configuration"""
    HOST = '0.0.0.0'
    PORT = 8000
    RELOAD = False
    ACCESS_LOG = False
    MAX_OUTPUT_CHARS = 30000  # Truncate output beyond this

    # CORS
    ALLOW_ORIGINS = ["*"]
    ALLOW_CREDENTIALS = True
    ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ALLOW_HEADERS = ["*"]


class DatabaseConfig:
    """Database configuration"""
    DEFAULT_PATH = 'data/fragdrop.db'
    CHECK_SAME_THREAD = False  # For SQLite with FastAPI


class NotificationConfig:
    """Notification service defaults"""
    # Notification types
    TYPE_DROP = 'drop'
    TYPE_RESTOCK = 'restock'
    TYPE_PRICE_CHANGE = 'price_change'
    TYPE_NEW_PRODUCT = 'new_product'
    TYPE_OUT_OF_STOCK = 'out_of_stock'


class ParfumoConfig:
    """Parfumo scraper configuration"""
    ENABLED = True
    UPDATE_INTERVAL_HOURS = 168  # 1 week
    AUTO_SCRAPE_NEW = True
    MAX_SCRAPES_PER_RUN = 10
    DEFAULT_UPDATE_TIME = '02:00'
    BASE_URL = 'https://www.parfumo.com'


class URLPatterns:
    """URL patterns and base URLs"""
    MONTAGNE_BASE_URL = 'https://www.montagneparfums.com'
    MONTAGNE_FRAGRANCE_URL = 'https://www.montagneparfums.com/fragrance'
    REDDIT_SUBREDDIT = 'MontagneParfums'

    # User agents
    DEFAULT_USER_AGENT = 'FragDropDetector/1.0'
    BROWSER_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


class UIConfig:
    """UI-related constants"""
    ACTIVITY_PAGE_SIZE = 20
    MAX_SEARCH_RESULTS = 100
    TOAST_DURATION_MS = 5000
    REFRESH_INTERVAL_MS = 30000  # 30 seconds

    # Date grouping labels
    DATE_TODAY = 'Today'
    DATE_YESTERDAY = 'Yesterday'


class ValidationLimits:
    """Input validation limits"""
    MIN_CHECK_INTERVAL = 60  # seconds
    MAX_CHECK_INTERVAL = 3600  # 1 hour

    MIN_DROPS_LIMIT = 1
    MAX_DROPS_LIMIT = 100

    MIN_CONFIDENCE = 0.0
    MAX_CONFIDENCE = 1.0

    MIN_DAYS_OF_WEEK = 0  # Monday
    MAX_DAYS_OF_WEEK = 6  # Sunday

    MIN_HOUR = 0
    MAX_HOUR = 23
    MIN_MINUTE = 0
    MAX_MINUTE = 59
