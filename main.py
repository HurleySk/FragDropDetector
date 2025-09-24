#!/usr/bin/env python3
"""
FragDropDetector - Main application runner
Monitors r/MontagneParfums for fragrance drops
"""

import os
import sys
import time
import logging
import colorlog
import yaml
from datetime import datetime, timezone, timedelta
import pytz
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.reddit_client import RedditClient
from services.drop_detector import DropDetector
from services.notifiers import PushoverNotifier, DiscordWebhookNotifier, EmailNotifier, NotificationManager
from models.database import Database


def setup_logging():
    """Configure colored logging"""
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    )

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # Reduce noise from some libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('prawcore').setLevel(logging.WARNING)

    return logger


class FragDropMonitor:
    """Main application class"""

    def __init__(self):
        """Initialize the monitor"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing FragDropMonitor...")

        # Load environment variables
        load_dotenv()

        # Load YAML configuration
        self.config = self._load_yaml_config()

        # Initialize components
        self.reddit_client = None
        self.detector = DropDetector()
        self.db = Database()
        self.notification_manager = NotificationManager()

        # Configuration
        self.subreddit = os.getenv('SUBREDDIT', 'MontagneParfums')
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '300'))  # 5 minutes default
        self.post_limit = int(os.getenv('POST_LIMIT', '50'))

        # Drop window configuration
        self.drop_window_config = self.config.get('drop_window', {})
        self.drop_window_enabled = self.drop_window_config.get('enabled', True)
        self.drop_window_timezone = self.drop_window_config.get('timezone', 'America/New_York')
        self.drop_window_days = self.drop_window_config.get('days_of_week', [4])  # Default Friday
        self.drop_window_start_hour = self.drop_window_config.get('start_hour', 12)
        self.drop_window_start_minute = self.drop_window_config.get('start_minute', 0)
        self.drop_window_end_hour = self.drop_window_config.get('end_hour', 17)
        self.drop_window_end_minute = self.drop_window_config.get('end_minute', 0)

        self._setup_reddit_client()
        self._setup_notifications()

    def _load_yaml_config(self):
        """Load configuration from config.yaml"""
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def _setup_reddit_client(self):
        """Setup Reddit client"""
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        user_agent = os.getenv('REDDIT_USER_AGENT', 'FragDropDetector/1.0')

        if not client_id or not client_secret:
            self.logger.error("Reddit credentials not found in environment variables!")
            self.logger.error("Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
            sys.exit(1)

        self.reddit_client = RedditClient(client_id, client_secret, user_agent)

        # Test connection
        if not self.reddit_client.test_connection():
            self.logger.error("Failed to connect to Reddit API!")
            sys.exit(1)

        self.logger.info("Reddit client connected successfully")

    def _setup_notifications(self):
        """Setup notification services"""
        # Pushover (iOS)
        pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
        pushover_user = os.getenv('PUSHOVER_USER_KEY')
        if pushover_token and pushover_user and pushover_token != 'your_app_token_here':
            self.notification_manager.add_notifier(PushoverNotifier(pushover_token, pushover_user))
            self.logger.info("Pushover notifications enabled")

        # Discord Webhook
        discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        if discord_webhook and discord_webhook != 'paste_your_webhook_url_here':
            self.notification_manager.add_notifier(DiscordWebhookNotifier(discord_webhook))
            self.logger.info("Discord webhook notifications enabled")

        # Email
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = os.getenv('SMTP_PORT')
        email_sender = os.getenv('EMAIL_SENDER')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_recipients = os.getenv('EMAIL_RECIPIENTS')

        if all([smtp_server, smtp_port, email_sender, email_password, email_recipients]):
            recipients = [r.strip() for r in email_recipients.split(',')]
            self.notification_manager.add_notifier(
                EmailNotifier(
                    smtp_server, int(smtp_port), email_sender,
                    email_password, recipients
                )
            )
            self.logger.info("Email notifications enabled")

        if not self.notification_manager.notifiers:
            self.logger.warning("No notification services configured!")
            self.logger.warning("Set PUSHOVER or DISCORD credentials in .env")

    def is_drop_window(self):
        """Check if current time is within configured drop window"""
        # If window checking is disabled, always return True
        if not self.drop_window_enabled:
            return True

        tz = pytz.timezone(self.drop_window_timezone)
        now = datetime.now(tz)

        # Check if it's one of the configured days
        if now.weekday() not in self.drop_window_days:
            return False

        # Create time objects for comparison
        current_time = now.time()
        start_time = datetime.now().replace(
            hour=self.drop_window_start_hour,
            minute=self.drop_window_start_minute,
            second=0,
            microsecond=0
        ).time()
        end_time = datetime.now().replace(
            hour=self.drop_window_end_hour,
            minute=self.drop_window_end_minute,
            second=0,
            microsecond=0
        ).time()

        # Check if current time is within window
        return start_time <= current_time < end_time

    def get_time_until_next_window(self):
        """Calculate time until next configured drop window"""
        if not self.drop_window_enabled:
            return 0  # If disabled, window is always "now"

        tz = pytz.timezone(self.drop_window_timezone)
        now = datetime.now(tz)

        # Find the next occurrence of a configured day
        min_days_until = 7
        for day in self.drop_window_days:
            days_until = (day - now.weekday()) % 7

            # Check if it's today and we haven't passed the end time
            if days_until == 0:
                current_time = now.time()
                end_time = datetime.now().replace(
                    hour=self.drop_window_end_hour,
                    minute=self.drop_window_end_minute,
                    second=0,
                    microsecond=0
                ).time()

                if current_time >= end_time:
                    # Already passed today's window, look at next week
                    days_until = 7

            min_days_until = min(min_days_until, days_until)

        # Calculate the next window start time
        next_window = now.replace(
            hour=self.drop_window_start_hour,
            minute=self.drop_window_start_minute,
            second=0,
            microsecond=0
        )

        if min_days_until == 0 and now.hour < self.drop_window_start_hour:
            # Window is today but hasn't started yet
            pass
        else:
            next_window = next_window + timedelta(days=min_days_until if min_days_until > 0 else 7)

        time_diff = next_window - now
        return time_diff.total_seconds()

    def check_for_drops(self):
        """Check for new drops"""
        # Check if we're in the drop window
        if not self.is_drop_window():
            tz = pytz.timezone(self.drop_window_timezone)
            now = datetime.now(tz)

            # Format the days for display
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            configured_days = ', '.join([day_names[d] for d in sorted(self.drop_window_days)])

            window_time = f"{self.drop_window_start_hour:02d}:{self.drop_window_start_minute:02d}-{self.drop_window_end_hour:02d}:{self.drop_window_end_minute:02d}"

            self.logger.info(f"Outside drop window ({configured_days} {window_time} {self.drop_window_timezone}). Current time: {now.strftime('%A %I:%M %p %Z')}")

            # Calculate time until next window
            seconds_until = self.get_time_until_next_window()
            hours_until = seconds_until / 3600
            self.logger.info(f"Next drop window in {hours_until:.1f} hours")
            return

        try:
            self.logger.info(f"🔥 DROP WINDOW ACTIVE - Checking r/{self.subreddit} for drops...")

            # Get last check time
            last_check = self.db.get_last_check_time()
            current_time = time.time()

            # Fetch posts
            if last_check > 0:
                # Get posts since last check
                posts = self.reddit_client.get_posts_since(
                    self.subreddit, last_check, self.post_limit
                )
            else:
                # First run, get recent posts
                posts = self.reddit_client.get_subreddit_posts(
                    self.subreddit, self.post_limit
                )

            self.logger.info(f"Fetched {len(posts)} posts")

            # Save posts to database
            for post in posts:
                self.db.save_post(post)

            # Detect drops
            drops = self.detector.batch_detect(posts)

            if drops:
                self.logger.info(f"Detected {len(drops)} potential drops!")

                for drop in drops:
                    # Save drop to database
                    drop_id = self.db.save_drop(drop)

                    if drop_id:
                        # Send notifications
                        results = self.notification_manager.send_notifications(drop)

                        # Mark as notified if any service succeeded
                        if any(results.values()):
                            self.db.mark_drop_notified(drop_id)
                            self.logger.info(f"Notifications sent for: {drop['title'][:50]}...")
                        else:
                            self.logger.error(f"All notifications failed for: {drop['title'][:50]}...")
            else:
                self.logger.info("No drops detected in recent posts")

            # Update last check time
            self.db.set_last_check_time(current_time)

        except Exception as e:
            self.logger.error(f"Error during drop check: {e}")

    def run(self):
        """Run the monitor"""
        self.logger.info("Starting FragDropMonitor...")
        self.logger.info(f"Monitoring r/{self.subreddit}")
        self.logger.info(f"Check interval: {self.check_interval} seconds")

        # Send test notification if requested
        if os.getenv('SEND_TEST_NOTIFICATION', '').lower() == 'true':
            self.logger.info("Sending test notification...")
            for notifier in self.notification_manager.notifiers:
                if hasattr(notifier, 'send_test'):
                    notifier.send_test()

        try:
            while True:
                self.check_for_drops()
                self.logger.info(f"Next check in {self.check_interval} seconds...")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.logger.info("Shutting down FragDropMonitor...")
            sys.exit(0)

    def run_once(self):
        """Run a single check (for testing)"""
        self.logger.info("Running single check...")
        self.check_for_drops()
        self.logger.info("Single check complete")


def main():
    """Main entry point"""
    logger = setup_logging()

    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run once for testing
        monitor = FragDropMonitor()
        monitor.run_once()
    else:
        # Run continuously
        monitor = FragDropMonitor()
        monitor.run()


if __name__ == '__main__':
    main()