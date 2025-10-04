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

        updater = get_parfumo_updater()

        status = updater.get_status()
        if status.get('currently_updating'):
            return {
                "success": False,
                "message": "Update already in progress",
                "progress": status.get('update_progress', 0)
            }

        def run_update():
            results = updater.update_all_ratings()
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

        updater = get_parfumo_updater()
        status = updater.get_status()

        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        parfumo_config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f)
                parfumo_config = full_config.get('parfumo', {})

        return {
            **status,
            'config': parfumo_config
        }

    except Exception as e:
        logger.error("Failed to get Parfumo status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
