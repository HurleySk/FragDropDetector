"""
Configuration management endpoints
"""

import os
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
import structlog
import yaml
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from api.models import (
    RedditConfig, NotificationConfig, DetectionConfig,
    DropWindowConfig, StockMonitoringConfig, StockScheduleConfig,
    LoggingConfig
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["config"])


def load_yaml_config():
    """Load configuration from YAML file"""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("Failed to load YAML config", error=str(e))
            return {}
    return {}


def save_yaml_config(config):
    """Save configuration to YAML file"""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        logger.info("Configuration saved successfully")
        return True
    except Exception as e:
        logger.error("Failed to save YAML config", error=str(e))
        return False


def update_env_file(updates):
    """Update .env file with new key-value pairs, preserving existing entries"""
    env_path = Path(__file__).parent.parent.parent / ".env"

    try:
        existing_vars = {}
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_vars[key.strip()] = value.strip()

        existing_vars.update(updates)

        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in existing_vars.items():
                f.write(f"{key}={value}\n")

        logger.info("Updated .env file", keys=list(updates.keys()))
        return True
    except Exception as e:
        logger.error("Failed to update .env file", error=str(e))
        return False


@router.get("/api/config")
async def get_config():
    """Get current configuration"""
    try:
        load_dotenv(override=True)
        yaml_config = load_yaml_config()

        refresh_token = os.getenv('REDDIT_REFRESH_TOKEN')
        username = os.getenv('REDDIT_USERNAME')

        return {
            "reddit": {
                "client_id": os.getenv('REDDIT_CLIENT_ID', ''),
                "client_secret": os.getenv('REDDIT_CLIENT_SECRET', ''),
                "subreddit": yaml_config.get('reddit', {}).get('subreddit', 'MontagneParfums'),
                "check_interval": yaml_config.get('reddit', {}).get('check_interval', 300),
                "authenticated": bool(refresh_token),
                "username": username,
                "auth_required": not bool(refresh_token)
            },
            "notifications": {
                "pushover_app_token": os.getenv('PUSHOVER_APP_TOKEN', ''),
                "pushover_user_key": os.getenv('PUSHOVER_USER_KEY', ''),
                "discord_webhook_url": os.getenv('DISCORD_WEBHOOK_URL', '')
            },
            "detection": yaml_config.get('detection', {
                "primary_keywords": ["drop", "dropped", "release", "available", "launch"],
                "secondary_keywords": ["limited", "exclusive", "sale", "batch", "decant"],
                "confidence_threshold": 0.4,
                "exclusion_keywords": []
            }),
            "drop_window": yaml_config.get('drop_window', {
                "enabled": True,
                "timezone": "America/New_York",
                "days_of_week": [4],
                "start_hour": 12,
                "start_minute": 0,
                "end_hour": 17,
                "end_minute": 0
            }),
            "stock_monitoring": yaml_config.get('stock_monitoring', {
                "enabled": True,
                "notifications": {
                    "new_products": True,
                    "restocked_products": True,
                    "price_changes": False,
                    "out_of_stock": False
                }
            }),
            "stock_schedule": yaml_config.get('stock_schedule', {
                "enabled": True,
                "check_interval": 1800,
                "window_enabled": False,
                "timezone": "America/New_York",
                "days_of_week": [],
                "start_hour": 9,
                "start_minute": 0,
                "end_hour": 18,
                "end_minute": 0
            }),
            "parfumo": yaml_config.get('parfumo', {
                "enabled": True,
                "update_interval": 168,
                "auto_scrape_new": True,
                "max_scrapes_per_run": 10,
                "last_update": None
            }),
            "logging": yaml_config.get('logging', {
                "level": "INFO",
                "file_enabled": True,
                "file_path": "logs/fragdrop.log",
                "max_file_size": 10,
                "backup_count": 5,
                "auto_cleanup": {
                    "enabled": True,
                    "max_age_days": 30,
                    "max_total_size_mb": 100,
                    "cleanup_interval_hours": 24,
                    "compress_old_logs": True,
                    "clean_cache": True,
                    "cache_max_age_days": 7
                }
            })
        }

    except Exception as e:
        logger.error("Failed to get config", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")


@router.post("/api/config/reddit")
async def update_reddit_config(config: RedditConfig):
    """Update Reddit configuration with validation"""
    try:
        yaml_config = load_yaml_config()

        if "reddit" not in yaml_config:
            yaml_config["reddit"] = {}

        yaml_config["reddit"].update({
            "subreddit": config.subreddit,
            "check_interval": config.check_interval,
            "post_limit": config.post_limit
        })

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")

        env_updates = {
            'REDDIT_CLIENT_ID': config.client_id,
            'REDDIT_CLIENT_SECRET': config.client_secret
        }
        if not update_env_file(env_updates):
            raise HTTPException(status_code=500, detail="Failed to save credentials to .env file")

        os.environ['REDDIT_CLIENT_ID'] = config.client_id
        os.environ['REDDIT_CLIENT_SECRET'] = config.client_secret

        logger.info("Reddit configuration updated", subreddit=config.subreddit)
        return {"success": True, "message": "Reddit configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update Reddit config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/notifications")
async def update_notification_config(config: NotificationConfig):
    """Update notification configuration with validation"""
    try:
        env_updates = {}
        if config.pushover_app_token is not None:
            env_updates['PUSHOVER_APP_TOKEN'] = config.pushover_app_token or ''
            os.environ['PUSHOVER_APP_TOKEN'] = config.pushover_app_token or ''
        if config.pushover_user_key is not None:
            env_updates['PUSHOVER_USER_KEY'] = config.pushover_user_key or ''
            os.environ['PUSHOVER_USER_KEY'] = config.pushover_user_key or ''
        if config.discord_webhook_url is not None:
            env_updates['DISCORD_WEBHOOK_URL'] = config.discord_webhook_url or ''
            os.environ['DISCORD_WEBHOOK_URL'] = config.discord_webhook_url or ''

        if env_updates and not update_env_file(env_updates):
            raise HTTPException(status_code=500, detail="Failed to save credentials to .env file")

        logger.info("Notification configuration updated")
        return {"success": True, "message": "Notification configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update notification config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/detection")
async def update_detection_config(config: DetectionConfig):
    """Update detection configuration with validation"""
    try:
        yaml_config = load_yaml_config()

        yaml_config["detection"] = {
            "primary_keywords": config.primary_keywords,
            "secondary_keywords": config.secondary_keywords,
            "confidence_threshold": config.confidence_threshold,
            "known_vendors": config.known_vendors,
            "exclusion_keywords": config.exclusion_keywords,
            "trusted_authors": config.trusted_authors
        }

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")

        logger.info("Detection configuration updated",
                   primary_keywords=len(config.primary_keywords),
                   confidence_threshold=config.confidence_threshold)
        return {"success": True, "message": "Detection configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update detection config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/drop-window")
async def update_drop_window_config(config: DropWindowConfig):
    """Update drop window configuration with validation"""
    try:
        yaml_config = load_yaml_config()

        yaml_config["drop_window"] = {
            "enabled": config.enabled,
            "timezone": config.timezone,
            "days_of_week": config.days_of_week,
            "start_hour": config.start_hour,
            "start_minute": config.start_minute,
            "end_hour": config.end_hour,
            "end_minute": config.end_minute
        }

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")

        logger.info("Drop window configuration updated",
                   enabled=config.enabled,
                   timezone=config.timezone,
                   days=config.days_of_week)
        return {"success": True, "message": "Drop window configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update drop window config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/stock-monitoring")
async def update_stock_monitoring_config(config: StockMonitoringConfig):
    """Update stock monitoring configuration with validation"""
    try:
        yaml_config = load_yaml_config()

        existing_watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])

        yaml_config["stock_monitoring"] = {
            "enabled": config.enabled,
            "notifications": {
                "new_products": config.new_products,
                "restocked_products": config.restocked_products,
                "price_changes": config.price_changes,
                "out_of_stock": config.out_of_stock
            },
            "watchlist": existing_watchlist
        }

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")

        logger.info("Stock monitoring configuration updated", enabled=config.enabled)
        return {"success": True, "message": "Stock monitoring configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update stock monitoring config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/stock-schedule")
async def update_stock_schedule_config(config: StockScheduleConfig):
    """Update stock schedule configuration with validation"""
    try:
        yaml_config = load_yaml_config()

        yaml_config["stock_schedule"] = {
            "enabled": config.enabled,
            "check_interval": config.check_interval,
            "window_enabled": config.window_enabled,
            "timezone": config.timezone,
            "days_of_week": config.days_of_week,
            "start_hour": config.start_hour,
            "start_minute": config.start_minute,
            "end_hour": config.end_hour,
            "end_minute": config.end_minute
        }

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")

        logger.info("Stock schedule configuration updated",
                   enabled=config.enabled,
                   interval=config.check_interval,
                   window_enabled=config.window_enabled)
        return {"success": True, "message": "Stock schedule configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update stock schedule config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/parfumo")
async def update_parfumo_config(config: dict):
    """Update Parfumo configuration"""
    try:
        yaml_config = load_yaml_config()

        if 'parfumo' not in yaml_config:
            yaml_config['parfumo'] = {}

        yaml_config['parfumo'].update({
            'enabled': config.get('enabled', True),
            'update_time': config.get('update_time', '02:00'),
            'auto_scrape_new': config.get('auto_scrape_new', True)
        })

        if save_yaml_config(yaml_config):
            return {"success": True, "message": "Parfumo configuration updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration")

    except Exception as e:
        logger.error("Failed to update Parfumo config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config/logging")
async def update_logging_config(config: LoggingConfig):
    """Update logging configuration with validation"""
    try:
        yaml_config = load_yaml_config()
        yaml_config['logging'] = {
            'level': config.level,
            'file_enabled': config.file_enabled,
            'file_path': config.file_path,
            'max_file_size': config.max_file_size,
            'backup_count': config.backup_count,
            'auto_cleanup': config.auto_cleanup
        }

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")

        logger.info("Logging configuration updated", level=config.level)
        return {"success": True, "message": "Logging configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update logging config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
