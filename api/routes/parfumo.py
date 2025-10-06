"""
Parfumo integration endpoints
"""

import sys
import os
import threading
from pathlib import Path
from fastapi import APIRouter, HTTPException
import structlog
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["parfumo"])


@router.post("/api/parfumo/update")
async def trigger_parfumo_update():
    """Manually trigger Parfumo update"""
    try:
        from services.parfumo_updater import get_parfumo_updater
        from services.fragscrape_client import get_fragscrape_client

        # Check fragscrape availability first
        client = get_fragscrape_client()
        if not client.health_check():
            return {
                "success": False,
                "message": "fragscrape API is not available. Please ensure fragscrape is running."
            }

        updater = get_parfumo_updater()

        status = updater.get_status()
        if status.get('currently_updating'):
            return {
                "success": False,
                "message": "Update already in progress",
                "progress": status.get('update_progress', 0)
            }

        def run_update():
            # Manual updates force refresh ALL fragrances
            results = updater.update_all_ratings(force_refresh=True)
            logger.info(f"Parfumo update completed: {results}")

        thread = threading.Thread(target=run_update)
        thread.start()

        return {
            "success": True,
            "message": "Parfumo update started for all fragrances"
        }

    except Exception as e:
        logger.error("Failed to trigger Parfumo update", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/parfumo/status")
async def get_parfumo_status():
    """Get Parfumo update status"""
    try:
        from services.parfumo_updater import get_parfumo_updater
        from services.fragscrape_client import get_fragscrape_client

        updater = get_parfumo_updater()
        status = updater.get_status()

        # Check fragscrape availability
        client = get_fragscrape_client()
        fragscrape_available = client.health_check()

        # Get rate limit status
        rate_limit_status = client.get_rate_limit_status()

        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        parfumo_config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f)
                parfumo_config = full_config.get('parfumo', {})

        return {
            **status,
            'config': parfumo_config,
            'fragscrape_available': fragscrape_available,
            'fragscrape_url': parfumo_config.get('fragscrape_url', 'http://localhost:3000'),
            'rate_limit': rate_limit_status
        }

    except Exception as e:
        logger.error("Failed to get Parfumo status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
