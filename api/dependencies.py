"""
Common dependencies for API routes
"""

import os
import sys
import structlog
from pathlib import Path

# Add src to path for internal imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from models.database import Database
from fastapi import HTTPException

logger = structlog.get_logger(__name__)


def get_database() -> Database:
    """Dependency to get database instance"""
    try:
        return Database()
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise HTTPException(status_code=500, detail="Database connection failed")
