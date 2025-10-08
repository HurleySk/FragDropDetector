"""
Dependency Injection Container
Manages service instances and their dependencies
"""

from typing import Optional, Dict, Any, Union
import os
import yaml
from pathlib import Path


class ServiceContainer:
    """
    Dependency injection container for managing service instances
    Implements lazy initialization and singleton pattern
    """

    def __init__(self, config_source: Optional[Union[str, Dict[str, Any]]] = None, use_pydantic: bool = True):
        """
        Initialize the service container

        Args:
            config_source: Path to YAML config file, dict config, or None for Pydantic settings
            use_pydantic: Use Pydantic settings (default) or YAML
        """
        self._config_source = config_source
        self._use_pydantic = use_pydantic
        self._config: Optional[Dict[str, Any]] = None
        self._instances: Dict[str, Any] = {}

    @property
    def config(self) -> Dict[str, Any]:
        """Get configuration, loading if necessary"""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from Pydantic settings or YAML file"""
        if self._use_pydantic:
            try:
                from config.settings import get_settings
                settings = get_settings()
                return settings.to_dict()
            except Exception as e:
                print(f"Failed to load Pydantic settings, falling back to YAML: {e}")
                self._use_pydantic = False

        if isinstance(self._config_source, dict):
            return self._config_source

        config_path = self._config_source or os.path.join(os.getcwd(), 'config', 'config.yaml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    @property
    def database(self):
        """Get Database instance"""
        if 'database' not in self._instances:
            from models.database import Database
            from config.constants import DatabaseConfig

            db_path = self.config.get('database', {}).get('path', DatabaseConfig.DEFAULT_PATH)
            # Inject timezone manager for timezone-aware datetime handling
            self._instances['database'] = Database(db_path, timezone_manager=self.timezone_manager)

        return self._instances['database']

    @property
    def schedule_manager(self):
        """Get ScheduleManager instance"""
        if 'schedule_manager' not in self._instances:
            from services.schedule_manager import ScheduleManager
            self._instances['schedule_manager'] = ScheduleManager(self.config)

        return self._instances['schedule_manager']

    @property
    def drop_detector(self):
        """Get DropDetector instance"""
        if 'drop_detector' not in self._instances:
            from services.drop_detector import DropDetector
            detection_config = self.config.get('detection', {})
            self._instances['drop_detector'] = DropDetector(detection_config)

        return self._instances['drop_detector']

    @property
    def reddit_client(self):
        """Get RedditClient instance"""
        if 'reddit_client' not in self._instances:
            from services.reddit_client import RedditClient

            reddit_config = self.config.get('reddit', {})
            client_id = os.getenv('REDDIT_CLIENT_ID')
            client_secret = os.getenv('REDDIT_CLIENT_SECRET')
            user_agent = os.getenv('REDDIT_USER_AGENT', 'FragDropDetector/1.0')

            if client_id and client_secret:
                self._instances['reddit_client'] = RedditClient(
                    client_id, client_secret, user_agent
                )
            else:
                self._instances['reddit_client'] = None

        return self._instances['reddit_client']

    @property
    def notification_manager(self):
        """Get NotificationManager instance"""
        if 'notification_manager' not in self._instances:
            from services.notifiers import NotificationManager
            self._instances['notification_manager'] = NotificationManager()

        return self._instances['notification_manager']

    @property
    def stock_monitor(self):
        """Get StockMonitor instance"""
        if 'stock_monitor' not in self._instances:
            from services.stock_monitor_enhanced import EnhancedStockMonitor
            self._instances['stock_monitor'] = EnhancedStockMonitor(
                headless=True,
                use_cache=True
            )

        return self._instances['stock_monitor']

    @property
    def log_manager(self):
        """Get LogManager instance"""
        if 'log_manager' not in self._instances:
            from services.log_manager import LogManager
            logging_config = self.config.get('logging', {})
            self._instances['log_manager'] = LogManager(logging_config)

        return self._instances['log_manager']

    @property
    def timezone_manager(self):
        """Get TimezoneManager instance"""
        if 'timezone_manager' not in self._instances:
            from utils.timezone import TimezoneManager
            timezone = self.config.get('drop_window', {}).get('timezone', 'America/New_York')
            self._instances['timezone_manager'] = TimezoneManager(timezone)

        return self._instances['timezone_manager']

    @property
    def fragrance_mapper(self):
        """Get FragranceMapper instance"""
        if 'fragrance_mapper' not in self._instances:
            from services.fragrance_mapper import get_fragrance_mapper
            self._instances['fragrance_mapper'] = get_fragrance_mapper()

        return self._instances['fragrance_mapper']

    @property
    def parfumo_scraper(self):
        """Get ParfumoScraper instance"""
        if 'parfumo_scraper' not in self._instances:
            from services.parfumo_scraper import get_parfumo_scraper
            self._instances['parfumo_scraper'] = get_parfumo_scraper()

        return self._instances['parfumo_scraper']

    def register(self, name: str, instance: Any) -> None:
        """
        Register a service instance

        Args:
            name: Service name
            instance: Service instance
        """
        self._instances[name] = instance

    def get(self, name: str) -> Optional[Any]:
        """
        Get a registered service instance

        Args:
            name: Service name

        Returns:
            Service instance or None if not found
        """
        return self._instances.get(name)

    def reset(self) -> None:
        """Clear all registered instances"""
        self._instances.clear()
        self._config = None


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container(config_path: Optional[str] = None) -> ServiceContainer:
    """
    Get or create the global service container

    Args:
        config_path: Optional path to configuration file

    Returns:
        ServiceContainer instance
    """
    global _container

    if _container is None:
        _container = ServiceContainer(config_path)

    return _container


def reset_container() -> None:
    """Reset the global container"""
    global _container
    if _container:
        _container.reset()
    _container = None
