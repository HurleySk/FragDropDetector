"""
Error Handling Decorators and Utilities
"""

import logging
import functools
import traceback
from typing import Any, Callable, Optional, Type, Union, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def handle_errors(
    *,
    default_return: Any = None,
    log_traceback: bool = True,
    reraise: bool = False,
    error_message: Optional[str] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for comprehensive error handling

    Args:
        default_return: Value to return on error (default: None)
        log_traceback: Whether to log full traceback (default: True)
        reraise: Whether to reraise the exception after logging (default: False)
        error_message: Custom error message prefix (default: auto-generated)
        exceptions: Tuple of exception types to catch (default: all Exception)

    Usage:
        @handle_errors(default_return=[], log_traceback=True)
        def risky_operation():
            # code that might fail
            pass

        @handle_errors(reraise=True, error_message="Database connection failed")
        async def connect_to_db():
            # code that might fail
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                return _handle_exception(func, e, args, kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                return _handle_exception(func, e, args, kwargs)

        def _handle_exception(func, e, args, kwargs):
            msg = error_message or f"Error in {func.__name__}"

            if log_traceback:
                logger.error(f"{msg}: {e}", exc_info=True)
            else:
                logger.error(f"{msg}: {e}")

            if reraise:
                raise

            return default_return

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator to retry function on error with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff: Multiplier for delay on each retry (default: 2.0)
        exceptions: Tuple of exception types to retry on (default: all Exception)
        on_retry: Optional callback function(attempt, exception) called on each retry

    Usage:
        @retry_on_error(max_retries=5, delay=2.0)
        def fetch_data():
            # code that might fail temporarily
            pass

        @retry_on_error(max_retries=3, exceptions=(ConnectionError, TimeoutError))
        async def connect():
            # code that might fail with specific errors
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            import asyncio
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_delay}s..."
                        )

                        if on_retry:
                            on_retry(attempt + 1, e)

                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )

            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_delay}s..."
                        )

                        if on_retry:
                            on_retry(attempt + 1, e)

                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )

            raise last_exception

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_execution_time(log_level: int = logging.DEBUG):
    """
    Decorator to log function execution time

    Args:
        log_level: Logging level to use (default: DEBUG)

    Usage:
        @log_execution_time(log_level=logging.INFO)
        def slow_operation():
            # code that might be slow
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                logger.log(
                    log_level,
                    f"{func.__name__} completed in {elapsed:.3f}s"
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                logger.log(
                    log_level,
                    f"{func.__name__} completed in {elapsed:.3f}s"
                )

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class ErrorContext:
    """
    Context manager for error handling with automatic logging

    Usage:
        with ErrorContext("Database operation", default_return=[]):
            # code that might fail
            pass
    """
    def __init__(
        self,
        operation_name: str,
        default_return: Any = None,
        log_traceback: bool = True,
        reraise: bool = False
    ):
        self.operation_name = operation_name
        self.default_return = default_return
        self.log_traceback = log_traceback
        self.reraise = reraise
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            msg = f"Error in {self.operation_name}"

            if self.log_traceback:
                logger.error(f"{msg}: {exc_val}", exc_info=True)
            else:
                logger.error(f"{msg}: {exc_val}")

            if self.reraise:
                return False

            self.result = self.default_return
            return True

        return False
