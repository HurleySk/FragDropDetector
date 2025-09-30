#!/usr/bin/env python3
"""
FragDropDetector Web Server
Improved architecture with separated templates, static files, input validation,
structured logging, and health checks.
"""

import os
import sys
import logging
import logging.handlers
import time
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Third-party imports
import structlog
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import yaml
from dotenv import load_dotenv

# Add src to path for internal imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.database import Database
from services.reddit_client import RedditClient
from services.notifiers import PushoverNotifier, DiscordWebhookNotifier, EmailNotifier
from services.log_manager import LogManager

# Initialize logging
def setup_logging():
    """Setup structured logging with rotation and memory-conscious settings"""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure basic logging to avoid memory issues
    log_file = log_dir / "web_server.log"

    # Use RotatingFileHandler with memory-conscious settings
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB per file
        backupCount=3,              # Keep only 3 backup files
        encoding='utf-8'
    )

    # Console handler for development
    console_handler = logging.StreamHandler()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Reduce noise from libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)

    return structlog.get_logger(__name__)

# Initialize logging
logger = setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="FragDropDetector",
    description="Fragrance drop monitoring and notification system",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize log manager on startup"""
    yaml_config = load_yaml_config()
    app.state.log_manager = LogManager(yaml_config.get('logging', {}))
    logger.info("Log manager initialized")

# Add CORS middleware with explicit configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Mount static files and templates
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

if not static_dir.exists():
    static_dir.mkdir()
    logger.warning("Created missing static directory")

if not templates_dir.exists():
    templates_dir.mkdir()
    logger.warning("Created missing templates directory")

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Pydantic models for input validation
class RedditConfig(BaseModel):
    client_id: str = Field(..., min_length=1, description="Reddit API client ID")
    client_secret: str = Field(..., min_length=1, description="Reddit API client secret")
    user_agent: str = Field(default="FragDropDetector/1.0", min_length=1)
    subreddit: str = Field(default="MontagneParfums", min_length=1)
    check_interval: int = Field(default=300, ge=60, le=3600, description="Check interval in seconds")
    post_limit: int = Field(default=50, ge=1, le=100)

class NotificationConfig(BaseModel):
    pushover_app_token: Optional[str] = Field(default=None)
    pushover_user_key: Optional[str] = Field(default=None)
    discord_webhook_url: Optional[str] = Field(default=None)

class DetectionConfig(BaseModel):
    primary_keywords: List[str] = Field(default_factory=list, min_items=1)
    secondary_keywords: List[str] = Field(default_factory=list)
    confidence_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    known_vendors: List[str] = Field(default_factory=list)
    exclusion_keywords: List[str] = Field(default_factory=list)
    trusted_authors: List[str] = Field(default_factory=list)

class DropWindowConfig(BaseModel):
    enabled: bool = Field(default=True)
    timezone: str = Field(default="America/New_York")
    days_of_week: List[int] = Field(default_factory=lambda: [4], min_items=1, max_items=7)
    start_hour: int = Field(default=12, ge=0, le=23)
    start_minute: int = Field(default=0, ge=0, le=59)
    end_hour: int = Field(default=17, ge=0, le=23)
    end_minute: int = Field(default=0, ge=0, le=59)

    @field_validator('days_of_week')
    @classmethod
    def validate_days(cls, v):
        if not all(0 <= day <= 6 for day in v):
            raise ValueError('Days of week must be between 0-6 (Monday-Sunday)')
        return list(set(v))  # Remove duplicates

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
        return list(set(v))  # Remove duplicates

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

# Utility functions
def load_yaml_config() -> Dict[str, Any]:
    """Load configuration from YAML file"""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("Failed to load YAML config", error=str(e))
            return {}
    return {}

def save_yaml_config(config: Dict[str, Any]) -> bool:
    """Save configuration to YAML file"""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        logger.info("Configuration saved successfully")
        return True
    except Exception as e:
        logger.error("Failed to save YAML config", error=str(e))
        return False

def update_env_file(updates: Dict[str, str]) -> bool:
    """Update .env file with new key-value pairs, preserving existing entries"""
    env_path = Path(__file__).parent / ".env"

    try:
        # Read existing .env content
        existing_vars = {}
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_vars[key.strip()] = value.strip()

        # Update with new values
        existing_vars.update(updates)

        # Write back to .env
        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in existing_vars.items():
                f.write(f"{key}={value}\n")

        logger.info("Updated .env file", keys=list(updates.keys()))
        return True
    except Exception as e:
        logger.error("Failed to update .env file", error=str(e))
        return False

def get_database() -> Database:
    """Dependency to get database instance"""
    try:
        return Database()
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise HTTPException(status_code=500, detail="Database connection failed")

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/ready")
async def readiness_check():
    """Readiness check - verifies database and essential services"""
    checks = {
        "database": False,
        "config": False,
        "static_files": False,
        "templates": False
    }

    # Check database
    try:
        db = Database()
        db.get_last_check_time()  # Simple query
        checks["database"] = True
    except Exception as e:
        logger.warning("Database health check failed", error=str(e))

    # Check config
    try:
        config = load_yaml_config()
        checks["config"] = True
    except Exception as e:
        logger.warning("Config health check failed", error=str(e))

    # Check static files directory
    checks["static_files"] = static_dir.exists() and static_dir.is_dir()

    # Check templates directory
    checks["templates"] = templates_dir.exists() and templates_dir.is_dir()

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.get("/health/live")
async def liveness_check():
    """Liveness check - verifies the application is running"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

# API Endpoints
@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get system status"""
    try:
        db = get_database()

        # Get basic stats
        drops_count = len(db.get_recent_drops(limit=1000))  # Rough count
        posts_processed = 0  # Would need to track this
        fragrances_tracked = len(db.get_all_fragrances())
        recent_stock_changes = len(db.get_recent_stock_changes(limit=10))

        # Check notification services
        notifications_enabled = {
            "pushover": bool(os.getenv('PUSHOVER_APP_TOKEN')),
            "discord": bool(os.getenv('DISCORD_WEBHOOK_URL')),
            "email": bool(os.getenv('EMAIL_SENDER'))
        }

        # Check Reddit authentication status
        refresh_token = os.getenv('REDDIT_REFRESH_TOKEN')
        username = os.getenv('REDDIT_USERNAME')

        reddit_status = {
            "authenticated": bool(refresh_token),
            "username": username,
            "enabled": bool(refresh_token),
            "message": f"Authenticated as u/{username}" if refresh_token else "Authentication required - monitoring disabled"
        }

        return StatusResponse(
            running=True,
            drops_detected=drops_count,
            posts_processed=posts_processed,
            fragrances_tracked=fragrances_tracked,
            recent_stock_changes=recent_stock_changes,
            notifications_enabled=notifications_enabled,
            reddit_status=reddit_status
        )

    except Exception as e:
        logger.error("Failed to get status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve status")

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    try:
        load_dotenv()  # Reload environment variables
        yaml_config = load_yaml_config()

        # Reddit authentication status
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
            })
        }

    except Exception as e:
        logger.error("Failed to get config", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")

@app.post("/api/config/reddit")
async def update_reddit_config(config: RedditConfig):
    """Update Reddit configuration with validation"""
    try:
        yaml_config = load_yaml_config()

        # Update YAML config
        if "reddit" not in yaml_config:
            yaml_config["reddit"] = {}

        yaml_config["reddit"].update({
            "subreddit": config.subreddit,
            "check_interval": config.check_interval,
            "post_limit": config.post_limit
        })

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")

        # Persist credentials to .env file
        env_updates = {
            'REDDIT_CLIENT_ID': config.client_id,
            'REDDIT_CLIENT_SECRET': config.client_secret
        }
        if not update_env_file(env_updates):
            raise HTTPException(status_code=500, detail="Failed to save credentials to .env file")

        # Update environment variables in memory
        os.environ['REDDIT_CLIENT_ID'] = config.client_id
        os.environ['REDDIT_CLIENT_SECRET'] = config.client_secret

        logger.info("Reddit configuration updated", subreddit=config.subreddit)
        return {"success": True, "message": "Reddit configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update Reddit config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/notifications")
async def update_notification_config(config: NotificationConfig):
    """Update notification configuration with validation"""
    try:
        # Build env updates dict with only provided values
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

        # Persist to .env file
        if env_updates and not update_env_file(env_updates):
            raise HTTPException(status_code=500, detail="Failed to save credentials to .env file")

        logger.info("Notification configuration updated")
        return {"success": True, "message": "Notification configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update notification config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/detection")
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

@app.post("/api/config/drop-window")
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

@app.post("/api/config/stock-monitoring")
async def update_stock_monitoring_config(config: StockMonitoringConfig):
    """Update stock monitoring configuration with validation"""
    try:
        yaml_config = load_yaml_config()

        yaml_config["stock_monitoring"] = {
            "enabled": config.enabled,
            "notifications": {
                "new_products": config.new_products,
                "restocked_products": config.restocked_products,
                "price_changes": config.price_changes,
                "out_of_stock": config.out_of_stock
            }
        }

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save configuration")

        logger.info("Stock monitoring configuration updated", enabled=config.enabled)
        return {"success": True, "message": "Stock monitoring configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update stock monitoring config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/stock-schedule")
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

@app.post("/api/config/logging")
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

        # Update log manager if it exists
        if hasattr(app.state, 'log_manager'):
            app.state.log_manager.update_config(yaml_config['logging'])

        logger.info("Logging configuration updated", level=config.level)
        return {"success": True, "message": "Logging configuration updated successfully"}

    except Exception as e:
        logger.error("Failed to update logging config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/usage")
async def get_log_usage():
    """Get current log disk usage statistics"""
    try:
        if not hasattr(app.state, 'log_manager'):
            yaml_config = load_yaml_config()
            app.state.log_manager = LogManager(yaml_config.get('logging', {}))

        usage = app.state.log_manager.get_disk_usage()
        return usage

    except Exception as e:
        logger.error("Failed to get log usage", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/cleanup")
async def trigger_log_cleanup():
    """Manually trigger log cleanup"""
    try:
        if not hasattr(app.state, 'log_manager'):
            yaml_config = load_yaml_config()
            app.state.log_manager = LogManager(yaml_config.get('logging', {}))

        stats = app.state.log_manager.cleanup_logs()

        return {
            "success": True,
            "stats": stats,
            "message": f"Cleanup complete: {stats['deleted_files']} files deleted, "
                      f"{stats['compressed_files']} files compressed, "
                      f"{stats['space_freed_mb']:.2f} MB freed"
        }

    except Exception as e:
        logger.error("Failed to run log cleanup", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/download")
async def download_logs():
    """Download logs as zip archive"""
    try:
        if not hasattr(app.state, 'log_manager'):
            yaml_config = load_yaml_config()
            app.state.log_manager = LogManager(yaml_config.get('logging', {}))

        archive_path = app.state.log_manager.create_logs_archive()

        if not archive_path or not archive_path.exists():
            raise HTTPException(status_code=500, detail="Failed to create logs archive")

        from fastapi.responses import FileResponse

        return FileResponse(
            path=str(archive_path),
            filename=archive_path.name,
            media_type='application/zip'
        )

    except Exception as e:
        logger.error("Failed to download logs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drops")
async def get_recent_drops(limit: int = 10):
    """Get recent drops with validation"""
    if not (1 <= limit <= 100):
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    try:
        db = get_database()
        drops = db.get_recent_drops(limit)
        return drops
    except Exception as e:
        logger.error("Failed to get drops", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve drops")

@app.get("/api/stock/changes")
async def get_stock_changes(limit: int = 10):
    """Get recent stock changes with validation"""
    if not (1 <= limit <= 100):
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    try:
        db = get_database()
        changes = db.get_recent_stock_changes(limit)
        return changes
    except Exception as e:
        logger.error("Failed to get stock changes", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve stock changes")

@app.get("/api/stock/fragrances")
async def get_fragrances(
    search: Optional[str] = None,
    in_stock: Optional[bool] = None,
    sort_by: Optional[str] = "name",
    sort_order: Optional[str] = "asc",
    limit: Optional[int] = None,
    offset: Optional[int] = 0,
    watchlist_only: Optional[bool] = False
):
    """Get all tracked fragrances with search and filter support"""
    try:
        db = get_database()
        fragrances = db.get_all_fragrances()

        # Load watchlist from config - always reload for fresh data
        yaml_config = load_yaml_config()
        watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])
        logger.info(f"Loaded watchlist with {len(watchlist)} items: {watchlist}")

        # Convert to list for filtering
        result = []
        for slug, data in fragrances.items():
            item = {
                **data,
                'slug': slug,
                'is_watchlisted': slug in watchlist
            }
            result.append(item)

        # Apply search filter
        if search:
            search_lower = search.lower()
            result = [f for f in result if
                     search_lower in f['name'].lower() or
                     search_lower in f['slug'].lower()]

        # Apply stock filter
        if in_stock is not None:
            result = [f for f in result if f['in_stock'] == in_stock]

        # Apply watchlist filter
        if watchlist_only:
            result = [f for f in result if f['is_watchlisted']]

        # Apply sorting
        if sort_by in ['name', 'slug', 'price', 'in_stock']:
            reverse = sort_order == 'desc'
            if sort_by == 'price':
                # Special handling for price sorting
                def price_key(item):
                    price = item['price']
                    if price == 'N/A' or not price:
                        return float('inf') if not reverse else float('-inf')
                    try:
                        return float(price.replace('$', '').replace(',', ''))
                    except:
                        return float('inf') if not reverse else float('-inf')
                result.sort(key=price_key, reverse=reverse)
            else:
                result.sort(key=lambda x: x[sort_by], reverse=reverse)

        # Get total count before pagination
        total = len(result)

        # Apply pagination
        if limit:
            result = result[offset:offset + limit]

        return {
            "items": result,
            "total": total,
            "offset": offset,
            "limit": limit,
            "watchlist_slugs": watchlist
        }
    except Exception as e:
        logger.error("Failed to get fragrances", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve fragrances")

@app.post("/api/stock/watchlist/add/{slug}")
async def add_to_watchlist(slug: str):
    """Add a product to the watchlist"""
    try:
        yaml_config = load_yaml_config()
        watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])

        if slug not in watchlist:
            watchlist.append(slug)

            if 'stock_monitoring' not in yaml_config:
                yaml_config['stock_monitoring'] = {}
            yaml_config['stock_monitoring']['watchlist'] = watchlist

            if not save_yaml_config(yaml_config):
                raise HTTPException(status_code=500, detail="Failed to save watchlist")

            logger.info(f"Added {slug} to watchlist. New watchlist: {watchlist}")
            return {"success": True, "message": f"Added {slug} to watchlist", "watchlist": watchlist}
        else:
            return {"success": True, "message": f"{slug} already in watchlist", "watchlist": watchlist}

    except Exception as e:
        logger.error("Failed to add to watchlist", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stock/watchlist/remove/{slug}")
async def remove_from_watchlist(slug: str):
    """Remove a product from the watchlist"""
    try:
        yaml_config = load_yaml_config()
        watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])

        if slug in watchlist:
            watchlist.remove(slug)

            if 'stock_monitoring' not in yaml_config:
                yaml_config['stock_monitoring'] = {}
            yaml_config['stock_monitoring']['watchlist'] = watchlist

            if not save_yaml_config(yaml_config):
                raise HTTPException(status_code=500, detail="Failed to save watchlist")

            logger.info(f"Removed {slug} from watchlist. New watchlist: {watchlist}")
            return {"success": True, "message": f"Removed {slug} from watchlist", "watchlist": watchlist}
        else:
            return {"success": True, "message": f"{slug} not in watchlist", "watchlist": watchlist}

    except Exception as e:
        logger.error("Failed to remove from watchlist", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/watchlist/bulk")
async def bulk_add_to_watchlist(request: dict):
    """Add multiple products to watchlist"""
    try:
        slugs = request.get('slugs', [])
        if not slugs:
            raise HTTPException(status_code=400, detail="No slugs provided")

        yaml_config = load_yaml_config()
        watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])

        added = []
        for slug in slugs:
            if slug not in watchlist:
                watchlist.append(slug)
                added.append(slug)

        if 'stock_monitoring' not in yaml_config:
            yaml_config['stock_monitoring'] = {}
        yaml_config['stock_monitoring']['watchlist'] = watchlist

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save watchlist")

        logger.info(f"Added {len(added)} items to watchlist")
        return {
            "success": True,
            "message": f"Added {len(added)} items to watchlist",
            "added": added,
            "watchlist": watchlist
        }

    except Exception as e:
        logger.error("Failed to bulk add to watchlist", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/watchlist/bulk")
async def bulk_remove_from_watchlist(request: dict):
    """Remove multiple products from watchlist"""
    try:
        slugs = request.get('slugs', [])
        if not slugs:
            raise HTTPException(status_code=400, detail="No slugs provided")

        yaml_config = load_yaml_config()
        watchlist = yaml_config.get('stock_monitoring', {}).get('watchlist', [])

        removed = []
        for slug in slugs:
            if slug in watchlist:
                watchlist.remove(slug)
                removed.append(slug)

        if 'stock_monitoring' not in yaml_config:
            yaml_config['stock_monitoring'] = {}
        yaml_config['stock_monitoring']['watchlist'] = watchlist

        if not save_yaml_config(yaml_config):
            raise HTTPException(status_code=500, detail="Failed to save watchlist")

        logger.info(f"Removed {len(removed)} items from watchlist")
        return {
            "success": True,
            "message": f"Removed {len(removed)} items from watchlist",
            "removed": removed,
            "watchlist": watchlist
        }

    except Exception as e:
        logger.error("Failed to bulk remove from watchlist", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/reddit")
async def test_reddit_connection(config: RedditConfig):
    """Test Reddit connection with validation"""
    try:
        client = RedditClient(config.client_id, config.client_secret, config.user_agent)
        success = client.test_connection()

        if success:
            logger.info("Reddit connection test successful")
            return {"success": True, "message": "Reddit connection successful"}
        else:
            logger.warning("Reddit connection test failed")
            return {"success": False, "message": "Reddit connection failed"}

    except Exception as e:
        logger.error("Reddit connection test error", error=str(e))
        return {"success": False, "message": f"Connection test failed: {str(e)}"}

@app.post("/api/test/notifications")
async def test_notifications():
    """Test notification services"""
    results = {}

    # Test Pushover
    pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
    pushover_user = os.getenv('PUSHOVER_USER_KEY')
    if pushover_token and pushover_user:
        try:
            notifier = PushoverNotifier(pushover_token, pushover_user)
            success = notifier.send_test()
            results["pushover"] = {"success": success, "message": "Test sent" if success else "Failed"}
        except Exception as e:
            results["pushover"] = {"success": False, "message": str(e)}

    # Test Discord
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook:
        try:
            notifier = DiscordWebhookNotifier(discord_webhook)
            success = notifier.send_test()
            results["discord"] = {"success": success, "message": "Test sent" if success else "Failed"}
        except Exception as e:
            results["discord"] = {"success": False, "message": str(e)}

    logger.info("Notification test completed", results=results)
    return results

@app.post("/api/test/pushover")
async def test_pushover():
    """Test Pushover notification service"""
    pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
    pushover_user = os.getenv('PUSHOVER_USER_KEY')

    if not pushover_token or not pushover_user:
        return JSONResponse(
            status_code=400,
            content={"error": "Pushover credentials not configured"}
        )

    try:
        notifier = PushoverNotifier(pushover_token, pushover_user)
        success = notifier.send_test()

        if success:
            logger.info("Pushover test notification sent successfully")
            return {"success": True, "message": "Test notification sent successfully"}
        else:
            logger.warning("Pushover test notification failed")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to send test notification"}
            )
    except Exception as e:
        logger.error("Pushover test error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Test failed: {str(e)}"}
        )

@app.post("/api/test/discord")
async def test_discord():
    """Test Discord notification service"""
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')

    if not discord_webhook:
        return JSONResponse(
            status_code=400,
            content={"error": "Discord webhook URL not configured"}
        )

    try:
        notifier = DiscordWebhookNotifier(discord_webhook)
        success = notifier.send_test()

        if success:
            logger.info("Discord test notification sent successfully")
            return {"success": True, "message": "Test notification sent successfully"}
        else:
            logger.warning("Discord test notification failed")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to send test notification"}
            )
    except Exception as e:
        logger.error("Discord test error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Test failed: {str(e)}"}
        )

@app.post("/api/test/email")
async def test_email():
    """Test Email notification service"""
    email_sender = os.getenv('EMAIL_SENDER')

    if not email_sender:
        return JSONResponse(
            status_code=400,
            content={"error": "Email service not configured"}
        )

    try:
        # Email notifier would need to be implemented
        logger.info("Email test requested but service not implemented")
        return JSONResponse(
            status_code=501,
            content={"error": "Email service not yet implemented"}
        )
    except Exception as e:
        logger.error("Email test error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Test failed: {str(e)}"}
        )

@app.post("/api/test/all")
async def test_all_services():
    """Test all configured notification services"""
    return await test_notifications()

# Main UI endpoint
@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    """Serve the main UI using templates"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error("Failed to serve UI template", error=str(e))
        # Fallback to simple HTML if template fails
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>FragDropDetector - Error</title></head>
        <body>
            <h1>FragDropDetector</h1>
            <p>Template error. Please check logs.</p>
        </body>
        </html>
        """)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with logging"""
    logger.warning("HTTP exception",
                  path=request.url.path,
                  status_code=exc.status_code,
                  detail=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "timestamp": datetime.utcnow().isoformat()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler with logging"""
    logger.error("Unhandled exception",
                path=request.url.path,
                error=str(exc),
                exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "timestamp": datetime.utcnow().isoformat()}
    )

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FragDropDetector Web Server")

    uvicorn.run(
        "web_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_config=None,  # Use our custom logging
        access_log=False  # Disable access log to reduce memory usage
    )