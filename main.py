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
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.reddit_client import RedditClient
from services.drop_detector import DropDetector
from services.notifiers import DiscordNotifier, TelegramNotifier, EmailNotifier, NotificationManager
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

        # Initialize components
        self.reddit_client = None
        self.detector = DropDetector()
        self.db = Database()
        self.notification_manager = NotificationManager()

        # Configuration
        self.subreddit = os.getenv('SUBREDDIT', 'MontagneParfums')
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '300'))  # 5 minutes default
        self.post_limit = int(os.getenv('POST_LIMIT', '50'))

        self._setup_reddit_client()
        self._setup_notifications()

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
        # Discord
        discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        if discord_webhook:
            self.notification_manager.add_notifier(DiscordNotifier(discord_webhook))
            self.logger.info("Discord notifications enabled")

        # Telegram
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat = os.getenv('TELEGRAM_CHAT_ID')
        if telegram_token and telegram_chat:
            self.notification_manager.add_notifier(
                TelegramNotifier(telegram_token, telegram_chat)
            )
            self.logger.info("Telegram notifications enabled")

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
            self.logger.warning("Set DISCORD_WEBHOOK_URL or other notification credentials")

    def check_for_drops(self):
        """Check for new drops"""
        try:
            self.logger.info(f"Checking r/{self.subreddit} for drops...")

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