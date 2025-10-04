"""
Drop management endpoints
"""

import os
import sys
from fastapi import APIRouter, HTTPException
import structlog

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from api.dependencies import get_database
from models.database import Drop

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["drops"])


@router.get("/api/drops")
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


@router.delete("/api/drops/{drop_id}")
async def delete_drop(drop_id: int):
    """Delete a drop by ID"""
    try:
        db = get_database()
        session = db.get_session()
        try:
            drop = session.query(Drop).filter_by(id=drop_id).first()
            if not drop:
                raise HTTPException(status_code=404, detail="Drop not found")

            session.delete(drop)
            session.commit()
            logger.info(f"Deleted drop {drop_id}")
            return {"status": "success", "message": "Drop deleted"}
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete drop", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete drop")
