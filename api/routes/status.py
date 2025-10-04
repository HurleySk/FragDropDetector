"""
System status endpoints
"""

import os
import sys
import time
import subprocess
from typing import Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException
import structlog
import pytz
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from api.dependencies import get_database
from models.database import Database

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["status"])


def check_monitor_running() -> Dict[str, Any]:
    """Check if the main monitoring process is running"""
    result = {
        "running": False,
        "method": "unknown",
        "last_check": None,
        "last_reddit_check": None,
        "last_stock_check": None
    }

    try:
        check = subprocess.run(
            ['systemctl', 'is-active', 'fragdrop'],
            capture_output=True,
            text=True,
            timeout=2
        )
        is_active = check.stdout.strip() == 'active'
        result["running"] = is_active
        result["method"] = "systemd"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    if result["method"] == "unknown":
        try:
            db = Database()
            last_check = db.get_last_check_time()
            current_time = time.time()

            if last_check > 0:
                age_minutes = (current_time - last_check) / 60
                result["running"] = age_minutes < 10
                result["method"] = "timestamp"
                result["last_check"] = last_check
        except Exception as e:
            logger.warning("Failed to check monitor via timestamp", error=str(e))

    return result


def load_yaml_config() -> Dict[str, Any]:
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


def calculate_window_status(config: Dict[str, Any], window_type: str) -> Dict[str, Any]:
    """Calculate current window status for Reddit or Stock monitoring"""
    if window_type == "reddit":
        window_config = config.get('drop_window', {})
        schedule_enabled = window_config.get('enabled', True)
    else:
        window_config = config.get('stock_schedule', {})
        schedule_enabled = window_config.get('enabled', True)
        if not window_config.get('window_enabled', False):
            return {
                "active": schedule_enabled,
                "enabled": schedule_enabled,
                "mode": "24/7",
                "next_window_start": None,
                "next_window_end": None,
                "current_time": datetime.now(pytz.UTC).isoformat()
            }

    if not schedule_enabled:
        return {
            "active": False,
            "enabled": False,
            "mode": "disabled",
            "next_window_start": None,
            "next_window_end": None,
            "current_time": datetime.now(pytz.UTC).isoformat()
        }

    tz = pytz.timezone(window_config.get('timezone', 'America/New_York'))
    now = datetime.now(tz)

    days_of_week = window_config.get('days_of_week', [])
    start_hour = window_config.get('start_hour', 12)
    start_minute = window_config.get('start_minute', 0)
    end_hour = window_config.get('end_hour', 18)
    end_minute = window_config.get('end_minute', 0)

    if not days_of_week:
        days_of_week = [0, 1, 2, 3, 4, 5, 6]

    current_weekday = now.weekday()
    current_time = now.time()

    start_time = datetime.now().replace(
        hour=start_hour, minute=start_minute, second=0, microsecond=0
    ).time()
    end_time = datetime.now().replace(
        hour=end_hour, minute=end_minute, second=0, microsecond=0
    ).time()

    is_active = (current_weekday in days_of_week and
                 start_time <= current_time < end_time)

    if is_active:
        window_end = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        return {
            "active": True,
            "enabled": True,
            "mode": "scheduled",
            "window_end": window_end.isoformat(),
            "current_time": now.isoformat()
        }

    next_start = None
    for i in range(8):
        check_day = (current_weekday + i) % 7
        if check_day in days_of_week:
            days_ahead = i if i > 0 or current_time >= end_time else 0
            next_date = now + timedelta(days=days_ahead)
            next_start = next_date.replace(
                hour=start_hour, minute=start_minute, second=0, microsecond=0
            )
            next_end = next_date.replace(
                hour=end_hour, minute=end_minute, second=0, microsecond=0
            )

            if next_start > now:
                break

    return {
        "active": False,
        "enabled": True,
        "mode": "scheduled",
        "next_window_start": next_start.isoformat() if next_start else None,
        "next_window_end": next_end.isoformat() if next_start else None,
        "current_time": now.isoformat()
    }


def get_watchlist_alerts(db: Database, config: Dict[str, Any]) -> Dict[str, int]:
    """Get watchlist alert counts"""
    watchlist = config.get('stock_monitoring', {}).get('watchlist', [])

    if not watchlist:
        return {
            "total_watchlist": 0,
            "out_of_stock": 0,
            "recently_restocked": 0
        }

    all_fragrances = db.get_all_fragrances()
    out_of_stock_count = 0

    for slug in watchlist:
        if slug in all_fragrances and not all_fragrances[slug].get('in_stock', False):
            out_of_stock_count += 1

    return {
        "total_watchlist": len(watchlist),
        "out_of_stock": out_of_stock_count,
        "recently_restocked": 0
    }


@router.get("/api/monitor/status")
async def get_monitor_status():
    """Get detailed monitor process status"""
    try:
        monitor_status = check_monitor_running()
        return monitor_status
    except Exception as e:
        logger.error("Failed to get monitor status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve monitor status")


@router.get("/api/status")
async def get_status():
    """Get system status with enhanced window and watchlist information"""
    try:
        db = get_database()
        config = load_yaml_config()

        drops_count = len(db.get_recent_drops(limit=1000))
        posts_processed = 0
        fragrances_tracked = len(db.get_all_fragrances())
        recent_stock_changes = len(db.get_recent_stock_changes(limit=10))

        notifications_enabled = {
            "pushover": bool(os.getenv('PUSHOVER_APP_TOKEN')),
            "discord": bool(os.getenv('DISCORD_WEBHOOK_URL')),
            "email": bool(os.getenv('EMAIL_SENDER'))
        }

        refresh_token = os.getenv('REDDIT_REFRESH_TOKEN')
        username = os.getenv('REDDIT_USERNAME')

        reddit_status = {
            "authenticated": bool(refresh_token),
            "username": username,
            "enabled": bool(refresh_token),
            "message": f"Authenticated as u/{username}" if refresh_token else "Authentication required - monitoring disabled"
        }

        monitor_status = check_monitor_running()
        reddit_window = calculate_window_status(config, "reddit")
        stock_window = calculate_window_status(config, "stock")
        watchlist_alerts = get_watchlist_alerts(db, config)

        return {
            "running": monitor_status["running"],
            "monitor_status": monitor_status,
            "last_check": None,
            "drops_detected": drops_count,
            "posts_processed": posts_processed,
            "fragrances_tracked": fragrances_tracked,
            "recent_stock_changes": recent_stock_changes,
            "next_window": None,
            "notifications_enabled": notifications_enabled,
            "reddit_status": reddit_status,
            "reddit_window": reddit_window,
            "stock_window": stock_window,
            "watchlist_alerts": watchlist_alerts
        }

    except Exception as e:
        logger.error("Failed to get status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve status")
