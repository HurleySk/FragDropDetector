"""
Centralized logging configuration using structlog
Provides consistent structured logging across the application
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import structlog


def setup_logger(
    name: str = __name__,
    level: str = "INFO",
    file_path: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    use_colors: bool = True
) -> structlog.BoundLogger:
    """
    Setup and return a configured structlog logger

    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file_path: Optional path to log file for file logging
        max_bytes: Maximum bytes per log file before rotation
        backup_count: Number of backup files to keep
        use_colors: Whether to use colored console output

    Returns:
        Configured structlog BoundLogger instance
    """

    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers = []

    if use_colors and sys.stdout.isatty():
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(
            logging.Formatter(
                '%(message)s'
            )
        )
        handlers.append(console_handler)
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        handlers.append(console_handler)

    if file_path:
        log_dir = Path(file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        handlers.append(file_handler)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in handlers:
        root_logger.addHandler(handler)

    if use_colors and sys.stdout.isatty():
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("prawcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)

    return structlog.get_logger(name)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """
    Get a logger instance with the given name

    Args:
        name: Logger name (usually __name__)

    Returns:
        structlog BoundLogger instance
    """
    return structlog.get_logger(name)
