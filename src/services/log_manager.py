"""
Log management service for FragDropDetector
Handles log rotation, cleanup, and disk space management
"""

import os
import logging
import logging.handlers
import gzip
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import threading

logger = logging.getLogger(__name__)


class LogManager:
    """Manages log files with rotation, cleanup, and compression"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the log manager

        Args:
            config: Logging configuration dictionary
        """
        self.config = config
        self.base_dir = Path(__file__).parent.parent.parent  # Project root
        self.logs_dir = self.base_dir / "logs"
        self.cache_dir = self.base_dir / "cache"

        # Ensure directories exist
        self.logs_dir.mkdir(exist_ok=True)

        # Cleanup configuration
        self.auto_cleanup = config.get('auto_cleanup', {})
        self.cleanup_enabled = self.auto_cleanup.get('enabled', True)
        self.max_age_days = self.auto_cleanup.get('max_age_days', 30)
        self.max_total_size_mb = self.auto_cleanup.get('max_total_size_mb', 100)
        self.cleanup_interval_hours = self.auto_cleanup.get('cleanup_interval_hours', 24)
        self.compress_old_logs = self.auto_cleanup.get('compress_old_logs', True)
        self.clean_cache = self.auto_cleanup.get('clean_cache', True)
        self.cache_max_age_days = self.auto_cleanup.get('cache_max_age_days', 7)

        # Cleanup thread
        self.cleanup_thread = None
        self.stop_cleanup = threading.Event()

        # Start automatic cleanup if enabled
        if self.cleanup_enabled:
            self.start_auto_cleanup()

    def get_file_handler(self, log_file: str = None) -> logging.handlers.RotatingFileHandler:
        """
        Get a configured rotating file handler

        Args:
            log_file: Optional log file name (defaults to config)

        Returns:
            Configured RotatingFileHandler
        """
        if not log_file:
            log_file = self.config.get('file_path', 'logs/fragdrop.log')

        log_path = self.base_dir / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)

        max_bytes = self.config.get('max_file_size', 10) * 1024 * 1024  # Convert MB to bytes
        backup_count = self.config.get('backup_count', 5)

        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )

        # Set formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        return handler

    def cleanup_logs(self) -> Dict[str, Any]:
        """
        Perform log cleanup based on configuration

        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            'deleted_files': 0,
            'compressed_files': 0,
            'space_freed_mb': 0,
            'errors': []
        }

        try:
            # Clean old log files
            if self.max_age_days > 0:
                cutoff_date = datetime.now() - timedelta(days=self.max_age_days)

                for log_file in self.logs_dir.glob('*.log*'):
                    try:
                        # Skip active log files (those without numeric extension)
                        if log_file.suffix == '.log':
                            continue

                        file_time = datetime.fromtimestamp(log_file.stat().st_mtime)

                        if file_time < cutoff_date:
                            size_mb = log_file.stat().st_size / (1024 * 1024)

                            if self.compress_old_logs and not log_file.suffix == '.gz':
                                # Compress the file
                                self._compress_file(log_file)
                                stats['compressed_files'] += 1
                                # Calculate space saved (approximately 90% compression)
                                stats['space_freed_mb'] += size_mb * 0.9
                            else:
                                # Delete the file
                                log_file.unlink()
                                stats['deleted_files'] += 1
                                stats['space_freed_mb'] += size_mb

                    except Exception as e:
                        stats['errors'].append(f"Error processing {log_file}: {e}")

            # Clean cache if enabled
            if self.clean_cache and self.cache_dir.exists():
                cache_cutoff = datetime.now() - timedelta(days=self.cache_max_age_days)

                for cache_file in self.cache_dir.rglob('*'):
                    if cache_file.is_file():
                        try:
                            file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                            if file_time < cache_cutoff:
                                size_mb = cache_file.stat().st_size / (1024 * 1024)
                                cache_file.unlink()
                                stats['deleted_files'] += 1
                                stats['space_freed_mb'] += size_mb
                        except Exception as e:
                            stats['errors'].append(f"Error cleaning cache {cache_file}: {e}")

            # Check total size limit
            if self.max_total_size_mb > 0:
                self._enforce_size_limit(stats)

        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
            stats['errors'].append(str(e))

        return stats

    def _compress_file(self, file_path: Path):
        """Compress a file using gzip"""
        gz_path = file_path.with_suffix(file_path.suffix + '.gz')

        with open(file_path, 'rb') as f_in:
            with gzip.open(gz_path, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove original file after successful compression
        file_path.unlink()

    def _enforce_size_limit(self, stats: Dict[str, Any]):
        """Enforce total size limit for logs directory"""
        total_size = 0
        log_files = []

        # Calculate total size and collect files
        for log_file in self.logs_dir.rglob('*.log*'):
            if log_file.is_file():
                size = log_file.stat().st_size
                total_size += size
                log_files.append((log_file, size, log_file.stat().st_mtime))

        total_size_mb = total_size / (1024 * 1024)

        if total_size_mb > self.max_total_size_mb:
            # Sort by modification time (oldest first)
            log_files.sort(key=lambda x: x[2])

            # Delete oldest files until under limit
            for file_path, size, _ in log_files:
                if total_size_mb <= self.max_total_size_mb:
                    break

                try:
                    # Skip the current active log file
                    if file_path.suffix == '.log' and 'fragdrop.log' in str(file_path):
                        continue

                    file_path.unlink()
                    size_mb = size / (1024 * 1024)
                    total_size_mb -= size_mb
                    stats['deleted_files'] += 1
                    stats['space_freed_mb'] += size_mb

                except Exception as e:
                    stats['errors'].append(f"Error deleting {file_path}: {e}")

    def get_disk_usage(self) -> Dict[str, Any]:
        """
        Get current disk usage statistics

        Returns:
            Dictionary with usage statistics
        """
        usage = {
            'logs_dir_mb': 0,
            'cache_dir_mb': 0,
            'total_mb': 0,
            'file_count': 0,
            'oldest_file': None,
            'newest_file': None
        }

        oldest_time = float('inf')
        newest_time = 0

        # Calculate logs directory size
        if self.logs_dir.exists():
            for log_file in self.logs_dir.rglob('*'):
                if log_file.is_file():
                    size = log_file.stat().st_size
                    mtime = log_file.stat().st_mtime

                    usage['logs_dir_mb'] += size / (1024 * 1024)
                    usage['file_count'] += 1

                    if mtime < oldest_time:
                        oldest_time = mtime
                        usage['oldest_file'] = {
                            'name': log_file.name,
                            'date': datetime.fromtimestamp(mtime).isoformat()
                        }

                    if mtime > newest_time:
                        newest_time = mtime
                        usage['newest_file'] = {
                            'name': log_file.name,
                            'date': datetime.fromtimestamp(mtime).isoformat()
                        }

        # Calculate cache directory size
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.rglob('*'):
                if cache_file.is_file():
                    usage['cache_dir_mb'] += cache_file.stat().st_size / (1024 * 1024)

        usage['total_mb'] = usage['logs_dir_mb'] + usage['cache_dir_mb']

        return usage

    def start_auto_cleanup(self):
        """Start automatic cleanup thread"""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            return

        self.stop_cleanup.clear()
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        logger.info(f"Started automatic log cleanup (interval: {self.cleanup_interval_hours} hours)")

    def stop_auto_cleanup(self):
        """Stop automatic cleanup thread"""
        self.stop_cleanup.set()
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        logger.info("Stopped automatic log cleanup")

    def _cleanup_worker(self):
        """Worker thread for automatic cleanup"""
        interval_seconds = self.cleanup_interval_hours * 3600

        while not self.stop_cleanup.is_set():
            # Wait for the interval or until stop is signaled
            if self.stop_cleanup.wait(timeout=interval_seconds):
                break

            # Perform cleanup
            logger.info("Running automatic log cleanup")
            stats = self.cleanup_logs()

            if stats['deleted_files'] > 0 or stats['compressed_files'] > 0:
                logger.info(
                    f"Cleanup complete: {stats['deleted_files']} deleted, "
                    f"{stats['compressed_files']} compressed, "
                    f"{stats['space_freed_mb']:.2f} MB freed"
                )

            if stats['errors']:
                for error in stats['errors']:
                    logger.error(f"Cleanup error: {error}")

    def create_logs_archive(self) -> Optional[Path]:
        """
        Create a zip archive of all log files

        Returns:
            Path to the created archive or None on error
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_path = self.base_dir / f'logs_backup_{timestamp}.zip'

            import zipfile
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for log_file in self.logs_dir.rglob('*'):
                    if log_file.is_file():
                        arcname = log_file.relative_to(self.base_dir)
                        zipf.write(log_file, arcname)

            return archive_path

        except Exception as e:
            logger.error(f"Error creating logs archive: {e}")
            return None

    def update_config(self, new_config: Dict[str, Any]):
        """Update configuration and restart cleanup if needed"""
        old_enabled = self.cleanup_enabled

        # Update configuration
        self.auto_cleanup = new_config.get('auto_cleanup', {})
        self.cleanup_enabled = self.auto_cleanup.get('enabled', True)
        self.max_age_days = self.auto_cleanup.get('max_age_days', 30)
        self.max_total_size_mb = self.auto_cleanup.get('max_total_size_mb', 100)
        self.cleanup_interval_hours = self.auto_cleanup.get('cleanup_interval_hours', 24)
        self.compress_old_logs = self.auto_cleanup.get('compress_old_logs', True)
        self.clean_cache = self.auto_cleanup.get('clean_cache', True)
        self.cache_max_age_days = self.auto_cleanup.get('cache_max_age_days', 7)

        # Restart cleanup thread if status changed
        if old_enabled and not self.cleanup_enabled:
            self.stop_auto_cleanup()
        elif not old_enabled and self.cleanup_enabled:
            self.start_auto_cleanup()
        elif self.cleanup_enabled:
            # Restart to apply new interval
            self.stop_auto_cleanup()
            self.start_auto_cleanup()