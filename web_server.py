#!/usr/bin/env python3
"""
FragDropDetector Web Server
Refactored modular architecture with separated routes and improved organization
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
import yaml
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.log_manager import LogManager
from config.constants import WebServerConfig
from api.routes import health, status, drops, stock, config, logs, test, parfumo


def setup_logging():
    """Setup structured logging with rotation and memory-conscious settings"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "web_server.log"

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )

    console_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

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

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)

    return structlog.get_logger(__name__)


logger = setup_logging()

app = FastAPI(
    title="FragDropDetector",
    description="Fragrance drop monitoring and notification system",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize log manager on startup"""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    yaml_config = {}
    if config_path.exists():
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f) or {}

    app.state.log_manager = LogManager(yaml_config.get('logging', {}))
    logger.info("Log manager initialized")


app.add_middleware(
    CORSMiddleware,
    allow_origins=WebServerConfig.ALLOW_ORIGINS,
    allow_credentials=WebServerConfig.ALLOW_CREDENTIALS,
    allow_methods=WebServerConfig.ALLOW_METHODS,
    allow_headers=WebServerConfig.ALLOW_HEADERS,
    expose_headers=["*"],
    max_age=3600,
)

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

app.include_router(health.router)
app.include_router(status.router)
app.include_router(drops.router)
app.include_router(stock.router)
app.include_router(config.router)
app.include_router(logs.router)
app.include_router(test.router)
app.include_router(parfumo.router)


@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    """Serve the main UI using templates"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error("Failed to serve UI template", error=str(e))
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
        host=WebServerConfig.HOST,
        port=WebServerConfig.PORT,
        reload=WebServerConfig.RELOAD,
        log_config=None,
        access_log=WebServerConfig.ACCESS_LOG
    )
