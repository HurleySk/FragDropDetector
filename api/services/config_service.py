"""
Centralized configuration service for YAML config management
"""

from pathlib import Path
from typing import Dict, Any, Optional
import structlog
import yaml

logger = structlog.get_logger(__name__)


class ConfigService:
    """Service for managing YAML configuration files"""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config service with path to YAML file"""
        if config_path is None:
            # Default path: project_root/config/config.yaml
            self.config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        else:
            self.config_path = config_path

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file

        Returns:
            Dict containing configuration, or empty dict if file doesn't exist or on error
        """
        if not self.config_path.exists():
            logger.warning("Config file not found", path=str(self.config_path))
            return {}

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config if config is not None else {}
        except Exception as e:
            logger.error("Failed to load YAML config", error=str(e), path=str(self.config_path))
            return {}

    def save(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to YAML file

        Args:
            config: Configuration dictionary to save

        Returns:
            True if successful, False otherwise
        """
        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            logger.info("Configuration saved successfully", path=str(self.config_path))
            return True
        except Exception as e:
            logger.error("Failed to save YAML config", error=str(e), path=str(self.config_path))
            return False

    def get_section(self, section: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a specific section from the configuration

        Args:
            section: Section name (e.g., 'reddit', 'parfumo', 'stock_monitoring')
            default: Default value if section doesn't exist

        Returns:
            Section configuration or default value
        """
        config = self.load()
        return config.get(section, default if default is not None else {})

    def update_section(self, section: str, data: Dict[str, Any], merge: bool = True) -> bool:
        """
        Update a specific section in the configuration

        Args:
            section: Section name to update
            data: Data to set for this section
            merge: If True, merge with existing section; if False, replace entirely

        Returns:
            True if successful, False otherwise
        """
        config = self.load()

        if merge and section in config:
            # Merge with existing section
            if isinstance(config[section], dict):
                config[section].update(data)
            else:
                config[section] = data
        else:
            # Replace section entirely
            config[section] = data

        return self.save(config)

    def get_nested(self, path: str, default: Any = None) -> Any:
        """
        Get a nested configuration value using dot notation

        Args:
            path: Dot-separated path (e.g., 'stock_monitoring.watchlist')
            default: Default value if path doesn't exist

        Returns:
            Value at path or default

        Example:
            config.get_nested('parfumo.enabled') -> True
            config.get_nested('stock_monitoring.notifications.new_products') -> True
        """
        config = self.load()
        keys = path.split('.')

        current = config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def set_nested(self, path: str, value: Any) -> bool:
        """
        Set a nested configuration value using dot notation

        Args:
            path: Dot-separated path (e.g., 'parfumo.enabled')
            value: Value to set

        Returns:
            True if successful, False otherwise

        Example:
            config.set_nested('parfumo.enabled', True)
            config.set_nested('stock_monitoring.watchlist', ['item1', 'item2'])
        """
        config = self.load()
        keys = path.split('.')

        # Navigate to parent of target key
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the value
        current[keys[-1]] = value

        return self.save(config)


# Singleton instance
_config_service: Optional[ConfigService] = None


def get_config_service(config_path: Optional[Path] = None) -> ConfigService:
    """
    Get the singleton ConfigService instance

    Args:
        config_path: Optional path to config file (only used on first call)

    Returns:
        ConfigService instance
    """
    global _config_service
    if _config_service is None:
        _config_service = ConfigService(config_path)
    return _config_service
