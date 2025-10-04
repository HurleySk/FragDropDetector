"""
Health check endpoints
"""

from datetime import datetime
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import structlog

from api.dependencies import get_database

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
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
        db = get_database()
        db.get_last_check_time()
        checks["database"] = True
    except Exception as e:
        logger.warning("Database health check failed", error=str(e))

    # Check config
    try:
        import yaml
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r') as f:
                yaml.safe_load(f)
        checks["config"] = True
    except Exception as e:
        logger.warning("Config health check failed", error=str(e))

    # Check static files directory
    static_dir = Path(__file__).parent.parent.parent / "static"
    checks["static_files"] = static_dir.exists() and static_dir.is_dir()

    # Check templates directory
    templates_dir = Path(__file__).parent.parent.parent / "templates"
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


@router.get("/health/live")
async def liveness_check():
    """Liveness check - verifies the application is running"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
