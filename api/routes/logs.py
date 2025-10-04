"""
Logging management endpoints
"""

import sys
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import structlog

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from services.log_manager import LogManager

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["logs"])


def get_log_manager():
    """Get log manager instance"""
    import yaml
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    logging_config = {}
    if config_path.exists():
        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)
            logging_config = full_config.get('logging', {})
    return LogManager(logging_config)


@router.get("/api/logs/usage")
async def get_log_usage():
    """Get current log disk usage statistics"""
    try:
        log_manager = get_log_manager()
        usage = log_manager.get_disk_usage()
        return usage

    except Exception as e:
        logger.error("Failed to get log usage", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/logs/cleanup")
async def trigger_log_cleanup():
    """Manually trigger log cleanup"""
    try:
        log_manager = get_log_manager()
        stats = log_manager.cleanup_logs()

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


@router.get("/api/logs/download")
async def download_logs():
    """Download logs as zip archive"""
    try:
        log_manager = get_log_manager()
        archive_path = log_manager.create_logs_archive()

        if not archive_path or not archive_path.exists():
            raise HTTPException(status_code=500, detail="Failed to create logs archive")

        return FileResponse(
            path=str(archive_path),
            filename=archive_path.name,
            media_type='application/zip'
        )

    except Exception as e:
        logger.error("Failed to download logs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
