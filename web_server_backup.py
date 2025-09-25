#!/usr/bin/env python3
"""
Web server for FragDropDetector configuration interface
Provides a local web UI for managing bot settings
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import pytz

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.database import Database
from services.reddit_client import RedditClient
from services.notifiers import PushoverNotifier, DiscordWebhookNotifier

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="FragDropDetector Configuration")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory if it exists
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuration models
class RedditConfig(BaseModel):
    client_id: str
    client_secret: str
    user_agent: str = "FragDropDetector/1.0"
    subreddit: str = "MontagneParfums"
    check_interval: int = 300
    post_limit: int = 50

class NotificationConfig(BaseModel):
    pushover_app_token: Optional[str] = None
    pushover_user_key: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    email_sender: Optional[str] = None
    email_password: Optional[str] = None
    email_recipients: Optional[str] = None

class DetectionConfig(BaseModel):
    primary_keywords: list[str]
    secondary_keywords: list[str]
    confidence_threshold: float = 0.4
    known_vendors: list[str]

class DropWindowConfig(BaseModel):
    enabled: bool = True
    timezone: str = "America/New_York"
    days_of_week: list[int]  # 0=Monday, 4=Friday, etc.
    start_hour: int = 12
    start_minute: int = 0
    end_hour: int = 17
    end_minute: int = 0

class StockMonitoringConfig(BaseModel):
    enabled: bool = True
    new_products: bool = True
    restocked_products: bool = True
    price_changes: bool = False
    out_of_stock: bool = False

class StatusResponse(BaseModel):
    running: bool
    last_check: Optional[str]
    next_window: Optional[str]
    notifications_enabled: Dict[str, bool]
    drops_detected: int
    posts_processed: int
    fragrances_tracked: int
    recent_stock_changes: int

# Helper functions
def load_yaml_config():
    """Load configuration from config.yaml"""
    config_path = Path("config/config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}

def save_yaml_config(config):
    """Save configuration to config.yaml"""
    config_path = Path("config/config.yaml")
    with open(config_path, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

def get_env_config():
    """Get current environment configuration"""
    return {
        "reddit": {
            "client_id": os.getenv('REDDIT_CLIENT_ID', ''),
            "client_secret": os.getenv('REDDIT_CLIENT_SECRET', ''),
            "user_agent": os.getenv('REDDIT_USER_AGENT', 'FragDropDetector/1.0'),
            "subreddit": os.getenv('SUBREDDIT', 'MontagneParfums'),
            "check_interval": int(os.getenv('CHECK_INTERVAL', '300')),
            "post_limit": int(os.getenv('POST_LIMIT', '50'))
        },
        "notifications": {
            "pushover_app_token": os.getenv('PUSHOVER_APP_TOKEN', ''),
            "pushover_user_key": os.getenv('PUSHOVER_USER_KEY', ''),
            "discord_webhook_url": os.getenv('DISCORD_WEBHOOK_URL', ''),
            "smtp_server": os.getenv('SMTP_SERVER', ''),
            "smtp_port": os.getenv('SMTP_PORT', ''),
            "email_sender": os.getenv('EMAIL_SENDER', ''),
            "email_password": os.getenv('EMAIL_PASSWORD', ''),
            "email_recipients": os.getenv('EMAIL_RECIPIENTS', '')
        }
    }

def get_next_window_time():
    """Calculate time until next Friday 12 PM ET"""
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)

    days_until_friday = (4 - now_et.weekday()) % 7
    if days_until_friday == 0 and now_et.hour >= 17:
        days_until_friday = 7

    next_window = now_et.replace(hour=12, minute=0, second=0, microsecond=0)
    if days_until_friday > 0:
        from datetime import timedelta
        next_window = next_window + timedelta(days=days_until_friday)
    elif now_et.hour >= 17:
        from datetime import timedelta
        next_window = next_window + timedelta(days=7)

    return next_window.isoformat()

# API Routes
@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get current bot status"""
    try:
        db = Database()

        # Get statistics
        drops_count = db.get_drop_count()
        posts_count = db.get_post_count()
        fragrances_count = db.get_fragrance_count()
        recent_changes = db.get_recent_stock_changes(limit=5)
        last_check = db.get_last_check_time()

        # Check notification services
        notifications = {
            "pushover": bool(os.getenv('PUSHOVER_APP_TOKEN') and os.getenv('PUSHOVER_USER_KEY')),
            "discord": bool(os.getenv('DISCORD_WEBHOOK_URL')),
            "email": bool(os.getenv('EMAIL_SENDER') and os.getenv('EMAIL_PASSWORD'))
        }

        # Format last check time
        last_check_str = None
        if last_check > 0:
            last_check_str = datetime.fromtimestamp(last_check).isoformat()

        return StatusResponse(
            running=False,  # Would need process checking to determine this
            last_check=last_check_str,
            next_window=get_next_window_time(),
            notifications_enabled=notifications,
            drops_detected=drops_count,
            posts_processed=posts_count,
            fragrances_tracked=fragrances_count,
            recent_stock_changes=len(recent_changes)
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    env_config = get_env_config()
    yaml_config = load_yaml_config()

    return {
        "reddit": env_config["reddit"],
        "notifications": env_config["notifications"],
        "detection": yaml_config.get("detection", {}),
        "drop_window": yaml_config.get("drop_window", {}),
        "stock_monitoring": yaml_config.get("stock_monitoring", {})
    }

@app.post("/api/config/reddit")
async def update_reddit_config(config: RedditConfig):
    """Update Reddit configuration"""
    try:
        env_path = Path(".env")

        # Test Reddit connection first
        reddit_client = RedditClient(
            config.client_id,
            config.client_secret,
            config.user_agent
        )
        if not reddit_client.test_connection():
            raise HTTPException(status_code=400, detail="Invalid Reddit credentials")

        # Update .env file
        set_key(env_path, "REDDIT_CLIENT_ID", config.client_id)
        set_key(env_path, "REDDIT_CLIENT_SECRET", config.client_secret)
        set_key(env_path, "REDDIT_USER_AGENT", config.user_agent)
        set_key(env_path, "SUBREDDIT", config.subreddit)
        set_key(env_path, "CHECK_INTERVAL", str(config.check_interval))
        set_key(env_path, "POST_LIMIT", str(config.post_limit))

        return {"message": "Reddit configuration updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating Reddit config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/notifications")
async def update_notification_config(config: NotificationConfig):
    """Update notification configuration"""
    try:
        env_path = Path(".env")

        # Update Pushover settings
        if config.pushover_app_token:
            set_key(env_path, "PUSHOVER_APP_TOKEN", config.pushover_app_token)
        if config.pushover_user_key:
            set_key(env_path, "PUSHOVER_USER_KEY", config.pushover_user_key)

        # Update Discord settings
        if config.discord_webhook_url:
            set_key(env_path, "DISCORD_WEBHOOK_URL", config.discord_webhook_url)

        # Update Email settings
        if config.smtp_server:
            set_key(env_path, "SMTP_SERVER", config.smtp_server)
        if config.smtp_port:
            set_key(env_path, "SMTP_PORT", str(config.smtp_port))
        if config.email_sender:
            set_key(env_path, "EMAIL_SENDER", config.email_sender)
        if config.email_password:
            set_key(env_path, "EMAIL_PASSWORD", config.email_password)
        if config.email_recipients:
            set_key(env_path, "EMAIL_RECIPIENTS", config.email_recipients)

        return {"message": "Notification configuration updated successfully"}
    except Exception as e:
        logger.error(f"Error updating notification config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/detection")
async def update_detection_config(config: DetectionConfig):
    """Update detection configuration"""
    try:
        yaml_config = load_yaml_config()

        # Update detection settings
        if "detection" not in yaml_config:
            yaml_config["detection"] = {}

        yaml_config["detection"]["primary_keywords"] = config.primary_keywords
        yaml_config["detection"]["secondary_keywords"] = config.secondary_keywords
        yaml_config["detection"]["confidence_threshold"] = config.confidence_threshold
        yaml_config["detection"]["known_vendors"] = config.known_vendors

        save_yaml_config(yaml_config)

        return {"message": "Detection configuration updated successfully"}
    except Exception as e:
        logger.error(f"Error updating detection config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/drop-window")
async def update_drop_window_config(config: DropWindowConfig):
    """Update drop window configuration"""
    try:
        yaml_config = load_yaml_config()

        # Update drop window settings
        if "drop_window" not in yaml_config:
            yaml_config["drop_window"] = {}

        yaml_config["drop_window"]["enabled"] = config.enabled
        yaml_config["drop_window"]["timezone"] = config.timezone
        yaml_config["drop_window"]["days_of_week"] = config.days_of_week
        yaml_config["drop_window"]["start_hour"] = config.start_hour
        yaml_config["drop_window"]["start_minute"] = config.start_minute
        yaml_config["drop_window"]["end_hour"] = config.end_hour
        yaml_config["drop_window"]["end_minute"] = config.end_minute

        save_yaml_config(yaml_config)

        return {"message": "Drop window configuration updated successfully"}
    except Exception as e:
        logger.error(f"Error updating drop window config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/reddit")
async def test_reddit_connection(config: RedditConfig):
    """Test Reddit API connection"""
    try:
        reddit_client = RedditClient(
            config.client_id,
            config.client_secret,
            config.user_agent
        )
        if reddit_client.test_connection():
            return {"success": True, "message": "Reddit connection successful"}
        else:
            return {"success": False, "message": "Failed to connect to Reddit"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/test/notifications")
async def test_notifications():
    """Send test notifications"""
    results = {}

    # Test Pushover
    pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
    pushover_user = os.getenv('PUSHOVER_USER_KEY')
    if pushover_token and pushover_user:
        try:
            notifier = PushoverNotifier(pushover_token, pushover_user)
            success = notifier.send_test()
            results["pushover"] = {"success": success, "message": "Test notification sent" if success else "Failed to send"}
        except Exception as e:
            results["pushover"] = {"success": False, "message": str(e)}

    # Test Discord
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook:
        try:
            notifier = DiscordWebhookNotifier(discord_webhook)
            success = notifier.send_test()
            results["discord"] = {"success": success, "message": "Test notification sent" if success else "Failed to send"}
        except Exception as e:
            results["discord"] = {"success": False, "message": str(e)}

    return results

@app.get("/api/drops")
async def get_recent_drops(limit: int = 10):
    """Get recent drops"""
    try:
        db = Database()
        drops = db.get_recent_drops(limit)
        return drops
    except Exception as e:
        logger.error(f"Error getting drops: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/changes")
async def get_stock_changes(limit: int = 10):
    """Get recent stock changes"""
    try:
        db = Database()
        changes = db.get_recent_stock_changes(limit)
        return changes
    except Exception as e:
        logger.error(f"Error getting stock changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/fragrances")
async def get_fragrances(limit: int = 50):
    """Get fragrance inventory"""
    try:
        db = Database()
        fragrances = db.get_all_fragrances()

        # Convert to list and limit results
        fragrance_list = []
        count = 0
        for slug, data in fragrances.items():
            if count >= limit:
                break
            fragrance_list.append({
                'slug': slug,
                **data
            })
            count += 1

        return {
            'total': len(fragrances),
            'fragrances': fragrance_list
        }
    except Exception as e:
        logger.error(f"Error getting fragrances: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/stock-monitoring")
async def update_stock_monitoring_config(config: StockMonitoringConfig):
    """Update stock monitoring configuration"""
    try:
        yaml_config = load_yaml_config()

        # Update stock monitoring configuration
        if "stock_monitoring" not in yaml_config:
            yaml_config["stock_monitoring"] = {}

        yaml_config["stock_monitoring"].update({
            "enabled": config.enabled,
            "notifications": {
                "new_products": config.new_products,
                "restocked_products": config.restocked_products,
                "price_changes": config.price_changes,
                "out_of_stock": config.out_of_stock
            }
        })

        save_yaml_config(yaml_config)
        return {"success": True, "message": "Stock monitoring configuration updated"}
    except Exception as e:
        logger.error(f"Error updating stock monitoring config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve the HTML interface
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main UI"""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <title>FragDropDetector Configuration</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 10px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
        }

        @media (min-width: 768px) {
            body {
                padding: 20px;
            }
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 20px;
        }

        .header h1 {
            font-size: 1.8em;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 0.95em;
            opacity: 0.9;
        }

        @media (min-width: 768px) {
            .header {
                margin-bottom: 30px;
            }
            .header h1 {
                font-size: 2.5em;
            }
            .header p {
                font-size: 1.1em;
            }
        }

        .status-bar {
            background: white;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }

        @media (min-width: 768px) {
            .status-bar {
                padding: 20px;
                margin-bottom: 20px;
            }
            .status-grid {
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
            }
        }

        .status-item {
            text-align: center;
        }

        .status-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }

        .status-label {
            color: #666;
            margin-top: 5px;
            font-size: 0.85em;
        }

        @media (min-width: 768px) {
            .status-value {
                font-size: 2em;
            }
            .status-label {
                font-size: 1em;
            }
        }

        .config-section {
            background: white;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .section-header {
            font-size: 1.2em;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }

        @media (min-width: 768px) {
            .config-section {
                padding: 25px;
                margin-bottom: 20px;
            }
            .section-header {
                font-size: 1.5em;
                margin-bottom: 20px;
            }
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 500;
        }

        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            -webkit-appearance: none;
        }

        @media (min-width: 768px) {
            .form-group input,
            .form-group textarea,
            .form-group select {
                padding: 10px;
                font-size: 14px;
            }
        }

        .form-group input:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr;
            gap: 15px;
        }

        @media (min-width: 768px) {
            .form-row {
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }
        }

        .btn {
            background: #667eea;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.3s;
            min-height: 44px;
            width: 100%;
            margin-bottom: 10px;
        }

        @media (min-width: 768px) {
            .btn {
                width: auto;
                padding: 10px 20px;
                margin-bottom: 0;
                margin-right: 10px;
            }
        }

        .btn:hover {
            background: #5a67d8;
        }

        .btn-secondary {
            background: #48bb78;
        }

        .btn-secondary:hover {
            background: #38a169;
        }

        .btn-danger {
            background: #f56565;
        }

        .btn-danger:hover {
            background: #e53e3e;
        }

        .alert {
            padding: 12px 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }

        .alert.success {
            background: #c6f6d5;
            color: #22543d;
            border: 1px solid #9ae6b4;
        }

        .alert.error {
            background: #fed7d7;
            color: #742a2a;
            border: 1px solid #fc8181;
        }

        .alert.info {
            background: #bee3f8;
            color: #2a4e7c;
            border: 1px solid #90cdf4;
        }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 5px;
        }

        @media (min-width: 768px) {
            .badge {
                font-size: 12px;
                margin-left: 10px;
            }
        }

        .badge.active {
            background: #c6f6d5;
            color: #22543d;
        }

        .badge.inactive {
            background: #fed7d7;
            color: #742a2a;
        }

        .drops-list {
            max-height: 300px;
            overflow-y: auto;
            -webkit-overflow-scrolling: touch;
        }

        .drop-item {
            padding: 12px;
            border: 1px solid #e2e8f0;
            border-radius: 5px;
            margin-bottom: 10px;
        }

        @media (min-width: 768px) {
            .drops-list {
                max-height: 400px;
            }
            .drop-item {
                padding: 15px;
            }
        }

        .drop-title {
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 5px;
        }

        .drop-meta {
            color: #718096;
            font-size: 14px;
        }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }

        input[type="checkbox"] {
            -webkit-appearance: checkbox !important;
            -moz-appearance: checkbox !important;
            appearance: checkbox !important;
            cursor: pointer;
            width: 18px;
            height: 18px;
            vertical-align: middle;
            opacity: 1 !important;
            visibility: visible !important;
            position: static !important;
        }

        input[type="time"],
        input[type="number"] {
            min-height: 44px;
        }

        select {
            background: white url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23333'%3E%3Cpath d='M8 11L3 6h10l-5 5z'/%3E%3C/svg%3E") no-repeat right 10px center;
            background-size: 16px;
            padding-right: 35px;
        }

        /* Ensure buttons don't overlap on mobile */
        .form-group {
            margin-bottom: 20px;
        }

        /* Better touch targets for mobile */
        @media (max-width: 767px) {
            input, select, textarea, button {
                min-height: 44px;
            }

            .btn + .btn {
                margin-top: 10px;
            }
        }

        /* Smooth scrolling for iOS */
        * {
            -webkit-tap-highlight-color: transparent;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>FragDropDetector</h1>
            <p>Configuration & Monitoring Dashboard</p>
        </div>

        <div id="alert" class="alert"></div>

        <div class="status-bar">
            <div class="status-grid">
                <div class="status-item">
                    <div class="status-value" id="status-drops">0</div>
                    <div class="status-label">Drops Detected</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="status-posts">0</div>
                    <div class="status-label">Posts Processed</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="status-fragrances">0</div>
                    <div class="status-label">Fragrances Tracked</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="status-stock-changes">0</div>
                    <div class="status-label">Recent Stock Changes</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="status-next">--</div>
                    <div class="status-label">Next Window</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="status-notifications">
                        <span id="notification-badges"></span>
                    </div>
                    <div class="status-label">Notifications</div>
                </div>
            </div>
        </div>

        <div class="config-section">
            <h2 class="section-header">Reddit Configuration</h2>
            <form id="reddit-form">
                <div class="form-row">
                    <div class="form-group">
                        <label>Client ID</label>
                        <input type="text" id="reddit-client-id" placeholder="Your Reddit App Client ID">
                    </div>
                    <div class="form-group">
                        <label>Client Secret</label>
                        <input type="password" id="reddit-client-secret" placeholder="Your Reddit App Client Secret">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Subreddit</label>
                        <input type="text" id="reddit-subreddit" value="MontagneParfums">
                    </div>
                    <div class="form-group">
                        <label>Check Interval (seconds)</label>
                        <input type="number" id="reddit-interval" value="300" min="60">
                    </div>
                </div>
                <div class="form-group">
                    <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                        <button type="button" class="btn" onclick="testRedditConnection()">Test Connection</button>
                        <button type="submit" class="btn btn-secondary">Save Reddit Settings</button>
                    </div>
                </div>
            </form>
        </div>

        <div class="config-section">
            <h2 class="section-header">Notification Services</h2>
            <form id="notification-form">
                <h3 style="margin-bottom: 15px; color: #4a5568;">Pushover (iOS)</h3>
                <div class="form-row">
                    <div class="form-group">
                        <label>App Token</label>
                        <input type="text" id="pushover-app-token" placeholder="Your Pushover App Token">
                    </div>
                    <div class="form-group">
                        <label>User Key</label>
                        <input type="text" id="pushover-user-key" placeholder="Your Pushover User Key">
                    </div>
                </div>

                <h3 style="margin: 20px 0 15px; color: #4a5568;">Discord Webhook</h3>
                <div class="form-group">
                    <label>Webhook URL</label>
                    <input type="text" id="discord-webhook" placeholder="https://discord.com/api/webhooks/...">
                </div>

                <div class="form-group">
                    <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                        <button type="button" class="btn" onclick="testNotifications()">Test Notifications</button>
                        <button type="submit" class="btn btn-secondary">Save Notification Settings</button>
                    </div>
                </div>
            </form>
        </div>

        <div class="config-section">
            <h2 class="section-header">Drop Window Schedule</h2>
            <form id="window-form">
                <div class="form-row">
                    <div class="form-group">
                        <label>Window Checking</label>
                        <select id="window-enabled">
                            <option value="true">Enabled (Check during specific times)</option>
                            <option value="false">Disabled (Check 24/7)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Timezone</label>
                        <select id="window-timezone">
                            <option value="America/New_York">Eastern Time (ET)</option>
                            <option value="America/Chicago">Central Time (CT)</option>
                            <option value="America/Denver">Mountain Time (MT)</option>
                            <option value="America/Los_Angeles">Pacific Time (PT)</option>
                            <option value="UTC">UTC</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Days of Week</label>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px;">
                        <label style="font-weight: normal; padding: 8px; display: block; cursor: pointer;"><input type="checkbox" id="day-0" value="0" style="margin-right: 8px;"> Monday</label>
                        <label style="font-weight: normal; padding: 8px; display: block; cursor: pointer;"><input type="checkbox" id="day-1" value="1" style="margin-right: 8px;"> Tuesday</label>
                        <label style="font-weight: normal; padding: 8px; display: block; cursor: pointer;"><input type="checkbox" id="day-2" value="2" style="margin-right: 8px;"> Wednesday</label>
                        <label style="font-weight: normal; padding: 8px; display: block; cursor: pointer;"><input type="checkbox" id="day-3" value="3" style="margin-right: 8px;"> Thursday</label>
                        <label style="font-weight: normal; padding: 8px; display: block; cursor: pointer;"><input type="checkbox" id="day-4" value="4" checked style="margin-right: 8px;"> Friday</label>
                        <label style="font-weight: normal; padding: 8px; display: block; cursor: pointer;"><input type="checkbox" id="day-5" value="5" style="margin-right: 8px;"> Saturday</label>
                        <label style="font-weight: normal; padding: 8px; display: block; cursor: pointer;"><input type="checkbox" id="day-6" value="6" style="margin-right: 8px;"> Sunday</label>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Start Time</label>
                        <input type="time" id="window-start-time" value="12:00">
                    </div>
                    <div class="form-group">
                        <label>End Time</label>
                        <input type="time" id="window-end-time" value="17:00">
                    </div>
                </div>
                <div class="form-group">
                    <button type="submit" class="btn btn-secondary">Save Drop Window Settings</button>
                </div>
            </form>
        </div>

        <div class="config-section">
            <h2 class="section-header">Detection Keywords</h2>
            <form id="detection-form">
                <div class="form-group">
                    <label>Primary Keywords (one per line)</label>
                    <textarea id="primary-keywords" rows="5">drop
dropped
release
available
launch</textarea>
                </div>
                <div class="form-group">
                    <label>Secondary Keywords (one per line)</label>
                    <textarea id="secondary-keywords" rows="5">limited
exclusive
sale
batch
decant</textarea>
                </div>
                <div class="form-group">
                    <label>Confidence Threshold</label>
                    <input type="number" id="confidence-threshold" value="0.4" min="0" max="1" step="0.1">
                </div>
                <div class="form-group">
                    <button type="submit" class="btn btn-secondary">Save Detection Settings</button>
                </div>
            </form>
        </div>

        <div class="config-section">
            <h2 class="section-header">Stock Monitoring</h2>
            <p class="info-text">Stock monitoring runs during the same drop window schedule as Reddit monitoring for simplicity.</p>
            <form id="stock-form">
                <div class="form-row">
                    <div class="form-group">
                        <label class="checkbox-container">
                            <input type="checkbox" id="stock-enabled" name="enabled">
                            <span class="checkmark"></span>
                            Enable Stock Monitoring
                        </label>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Notify on:</label>
                        <div class="checkbox-group">
                            <label class="checkbox-container">
                                <input type="checkbox" id="notify-new-products" name="new_products">
                                <span class="checkmark"></span>
                                New Products
                            </label>
                            <label class="checkbox-container">
                                <input type="checkbox" id="notify-restocked" name="restocked_products">
                                <span class="checkmark"></span>
                                Restocked Products
                            </label>
                            <label class="checkbox-container">
                                <input type="checkbox" id="notify-price-changes" name="price_changes">
                                <span class="checkmark"></span>
                                Price Changes
                            </label>
                            <label class="checkbox-container">
                                <input type="checkbox" id="notify-out-of-stock" name="out_of_stock">
                                <span class="checkmark"></span>
                                Out of Stock
                            </label>
                        </div>
                    </div>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-secondary">Save Stock Monitoring Settings</button>
                </div>
            </form>
        </div>

        <div class="config-section">
            <h2 class="section-header">Stock Changes</h2>
            <div class="drops-list" id="stock-changes-list">
                <p style="color: #718096;">Loading recent stock changes...</p>
            </div>
        </div>

        <div class="config-section">
            <h2 class="section-header">Recent Drops</h2>
            <div class="drops-list" id="drops-list">
                <p style="color: #718096;">Loading recent drops...</p>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = '';

        function showAlert(message, type = 'info') {
            const alert = document.getElementById('alert');
            alert.className = `alert ${type}`;
            alert.textContent = message;
            alert.style.display = 'block';

            setTimeout(() => {
                alert.style.display = 'none';
            }, 5000);
        }

        async function loadStatus() {
            try {
                const response = await fetch(`${API_BASE}/api/status`);
                const data = await response.json();

                document.getElementById('status-drops').textContent = data.drops_detected;
                document.getElementById('status-posts').textContent = data.posts_processed;
                document.getElementById('status-fragrances').textContent = data.fragrances_tracked;
                document.getElementById('status-stock-changes').textContent = data.recent_stock_changes;

                if (data.next_window) {
                    const nextDate = new Date(data.next_window);
                    const now = new Date();
                    const hours = Math.floor((nextDate - now) / (1000 * 60 * 60));
                    document.getElementById('status-next').textContent = `${hours}h`;
                }

                const badges = [];
                if (data.notifications_enabled.pushover) badges.push('<span class=\"badge active\">Pushover</span>');
                if (data.notifications_enabled.discord) badges.push('<span class=\"badge active\">Discord</span>');
                if (badges.length === 0) badges.push('<span class=\"badge inactive\">None</span>');
                document.getElementById('notification-badges').innerHTML = badges.join('');
            } catch (error) {
                console.error('Failed to load status:', error);
            }
        }

        async function loadConfig() {
            try {
                const response = await fetch(`${API_BASE}/api/config`);
                const data = await response.json();

                // Load Reddit settings
                document.getElementById('reddit-client-id').value = data.reddit.client_id || '';
                document.getElementById('reddit-client-secret').value = data.reddit.client_secret || '';
                document.getElementById('reddit-subreddit').value = data.reddit.subreddit || 'MontagneParfums';
                document.getElementById('reddit-interval').value = data.reddit.check_interval || 300;

                // Load notification settings
                document.getElementById('pushover-app-token').value = data.notifications.pushover_app_token || '';
                document.getElementById('pushover-user-key').value = data.notifications.pushover_user_key || '';
                document.getElementById('discord-webhook').value = data.notifications.discord_webhook_url || '';

                // Load detection settings
                if (data.detection.primary_keywords) {
                    document.getElementById('primary-keywords').value = data.detection.primary_keywords.join('\\n');
                }
                if (data.detection.secondary_keywords) {
                    document.getElementById('secondary-keywords').value = data.detection.secondary_keywords.join('\\n');
                }
                if (data.detection.confidence_threshold) {
                    document.getElementById('confidence-threshold').value = data.detection.confidence_threshold;
                }

                // Load drop window settings
                if (data.drop_window) {
                    document.getElementById('window-enabled').value = data.drop_window.enabled !== false ? 'true' : 'false';
                    if (data.drop_window.timezone) {
                        document.getElementById('window-timezone').value = data.drop_window.timezone;
                    }

                    // Clear all day checkboxes first
                    for (let i = 0; i < 7; i++) {
                        const checkbox = document.getElementById(`day-${i}`);
                        if (checkbox) {
                            checkbox.checked = false;
                        }
                    }

                    // Check the configured days
                    if (data.drop_window.days_of_week) {
                        data.drop_window.days_of_week.forEach(day => {
                            const checkbox = document.getElementById(`day-${day}`);
                            if (checkbox) {
                                checkbox.checked = true;
                            }
                        });
                    }

                    // Set times
                    if (data.drop_window.start_hour !== undefined && data.drop_window.start_minute !== undefined) {
                        const startTime = `${String(data.drop_window.start_hour).padStart(2, '0')}:${String(data.drop_window.start_minute).padStart(2, '0')}`;
                        document.getElementById('window-start-time').value = startTime;
                    }
                    if (data.drop_window.end_hour !== undefined && data.drop_window.end_minute !== undefined) {
                        const endTime = `${String(data.drop_window.end_hour).padStart(2, '0')}:${String(data.drop_window.end_minute).padStart(2, '0')}`;
                        document.getElementById('window-end-time').value = endTime;
                    }
                }

                // Load stock monitoring settings
                if (data.stock_monitoring) {
                    document.getElementById('stock-enabled').checked = data.stock_monitoring.enabled || false;

                    if (data.stock_monitoring.notifications) {
                        document.getElementById('notify-new-products').checked = data.stock_monitoring.notifications.new_products || false;
                        document.getElementById('notify-restocked').checked = data.stock_monitoring.notifications.restocked_products || false;
                        document.getElementById('notify-price-changes').checked = data.stock_monitoring.notifications.price_changes || false;
                        document.getElementById('notify-out-of-stock').checked = data.stock_monitoring.notifications.out_of_stock || false;
                    }
                }
            } catch (error) {
                console.error('Failed to load config:', error);
                showAlert('Failed to load configuration', 'error');
            }
        }

        async function loadDrops() {
            try {
                const response = await fetch(`${API_BASE}/api/drops?limit=10`);
                const drops = await response.json();

                const dropsList = document.getElementById('drops-list');
                if (drops.length === 0) {
                    dropsList.innerHTML = '<p style="color: #718096;">No drops detected yet</p>';
                } else {
                    dropsList.innerHTML = drops.map(drop => `
                        <div class="drop-item">
                            <div class="drop-title">${drop.title}</div>
                            <div class="drop-meta">
                                ${new Date(drop.created_at).toLocaleString()} •
                                Confidence: ${(drop.confidence * 100).toFixed(0)}%
                            </div>
                        </div>
                    `).join('');
                }
            } catch (error) {
                console.error('Failed to load drops:', error);
            }
        }

        async function loadStockChanges() {
            try {
                const response = await fetch(`${API_BASE}/api/stock/changes?limit=10`);
                const changes = await response.json();

                const changesList = document.getElementById('stock-changes-list');
                if (changes.length === 0) {
                    changesList.innerHTML = '<p style="color: #718096;">No stock changes detected yet</p>';
                } else {
                    changesList.innerHTML = changes.map(change => `
                        <div class="drop-item">
                            <div class="drop-title">${change.fragrance_name}</div>
                            <div class="drop-meta">
                                Type: ${change.change_type} |
                                ${change.old_value ? 'From: ' + change.old_value + ' | ' : ''}
                                ${change.new_value ? 'To: ' + change.new_value + ' | ' : ''}
                                ${new Date(change.detected_at).toLocaleString()}
                            </div>
                        </div>
                    `).join('');
                }
            } catch (error) {
                console.error('Failed to load stock changes:', error);
            }
        }

        async function testRedditConnection() {
            showAlert('Testing Reddit connection...', 'info');

            const config = {
                client_id: document.getElementById('reddit-client-id').value,
                client_secret: document.getElementById('reddit-client-secret').value,
                user_agent: 'FragDropDetector/1.0',
                subreddit: document.getElementById('reddit-subreddit').value,
                check_interval: parseInt(document.getElementById('reddit-interval').value),
                post_limit: 50
            };

            try {
                const response = await fetch(`${API_BASE}/api/test/reddit`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                const result = await response.json();
                showAlert(result.message, result.success ? 'success' : 'error');
            } catch (error) {
                showAlert('Failed to test connection', 'error');
            }
        }

        async function testNotifications() {
            showAlert('Sending test notifications...', 'info');

            try {
                const response = await fetch(`${API_BASE}/api/test/notifications`, {
                    method: 'POST'
                });

                const results = await response.json();
                let messages = [];

                for (const [service, result] of Object.entries(results)) {
                    if (result.success) {
                        messages.push(`${service}: Success`);
                    } else {
                        messages.push(`${service}: ${result.message}`);
                    }
                }

                showAlert(messages.join(', '), 'info');
            } catch (error) {
                showAlert('Failed to test notifications', 'error');
            }
        }

        // Form submissions
        document.getElementById('reddit-form').addEventListener('submit', async (e) => {
            e.preventDefault();

            const config = {
                client_id: document.getElementById('reddit-client-id').value,
                client_secret: document.getElementById('reddit-client-secret').value,
                user_agent: 'FragDropDetector/1.0',
                subreddit: document.getElementById('reddit-subreddit').value,
                check_interval: parseInt(document.getElementById('reddit-interval').value),
                post_limit: 50
            };

            try {
                const response = await fetch(`${API_BASE}/api/config/reddit`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                if (response.ok) {
                    showAlert('Reddit configuration saved successfully', 'success');
                } else {
                    showAlert('Failed to save Reddit configuration', 'error');
                }
            } catch (error) {
                showAlert('Failed to save configuration', 'error');
            }
        });

        document.getElementById('notification-form').addEventListener('submit', async (e) => {
            e.preventDefault();

            const config = {
                pushover_app_token: document.getElementById('pushover-app-token').value,
                pushover_user_key: document.getElementById('pushover-user-key').value,
                discord_webhook_url: document.getElementById('discord-webhook').value
            };

            try {
                const response = await fetch(`${API_BASE}/api/config/notifications`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                if (response.ok) {
                    showAlert('Notification configuration saved successfully', 'success');
                } else {
                    showAlert('Failed to save notification configuration', 'error');
                }
            } catch (error) {
                showAlert('Failed to save configuration', 'error');
            }
        });

        document.getElementById('detection-form').addEventListener('submit', async (e) => {
            e.preventDefault();

            const config = {
                primary_keywords: document.getElementById('primary-keywords').value.split('\\n').filter(k => k.trim()),
                secondary_keywords: document.getElementById('secondary-keywords').value.split('\\n').filter(k => k.trim()),
                confidence_threshold: parseFloat(document.getElementById('confidence-threshold').value),
                known_vendors: ['montagneparfums', 'montagne_parfums']
            };

            try {
                const response = await fetch(`${API_BASE}/api/config/detection`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                if (response.ok) {
                    showAlert('Detection configuration saved successfully', 'success');
                } else {
                    showAlert('Failed to save detection configuration', 'error');
                }
            } catch (error) {
                showAlert('Failed to save configuration', 'error');
            }
        });

        document.getElementById('window-form').addEventListener('submit', async (e) => {
            e.preventDefault();

            // Get selected days
            const days = [];
            for (let i = 0; i < 7; i++) {
                if (document.getElementById(`day-${i}`).checked) {
                    days.push(i);
                }
            }

            // Parse time values
            const startTime = document.getElementById('window-start-time').value.split(':');
            const endTime = document.getElementById('window-end-time').value.split(':');

            const config = {
                enabled: document.getElementById('window-enabled').value === 'true',
                timezone: document.getElementById('window-timezone').value,
                days_of_week: days,
                start_hour: parseInt(startTime[0]),
                start_minute: parseInt(startTime[1]),
                end_hour: parseInt(endTime[0]),
                end_minute: parseInt(endTime[1])
            };

            try {
                const response = await fetch(`${API_BASE}/api/config/drop-window`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                if (response.ok) {
                    showAlert('Drop window configuration saved successfully', 'success');
                } else {
                    showAlert('Failed to save drop window configuration', 'error');
                }
            } catch (error) {
                showAlert('Failed to save configuration', 'error');
            }
        });

        // Stock form handler
        document.getElementById('stock-form').addEventListener('submit', async (e) => {
            e.preventDefault();

            const config = {
                enabled: document.getElementById('stock-enabled').checked,
                new_products: document.getElementById('notify-new-products').checked,
                restocked_products: document.getElementById('notify-restocked').checked,
                price_changes: document.getElementById('notify-price-changes').checked,
                out_of_stock: document.getElementById('notify-out-of-stock').checked
            };

            try {
                const response = await fetch(`${API_BASE}/api/config/stock-monitoring`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                const result = await response.json();

                if (response.ok) {
                    showAlert('Stock monitoring configuration saved successfully', 'success');
                } else {
                    showAlert('Failed to save stock monitoring configuration', 'error');
                }
            } catch (error) {
                showAlert('Failed to save configuration', 'error');
            }
        });

        // Load initial data
        window.addEventListener('DOMContentLoaded', () => {
            loadStatus();
            loadConfig();
            loadDrops();
            loadStockChanges();
        });

        // Refresh status every 30 seconds
        setInterval(loadStatus, 30000);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('WEB_PORT', '8080'))
    logger.info(f"Starting FragDropDetector Web Server on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")