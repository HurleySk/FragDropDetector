#!/usr/bin/env python3
"""
FragDropDetector - Main application runner
Monitors r/MontagneParfums for fragrance drops
"""

import os
import sys
import time
import yaml
from datetime import datetime, timezone, timedelta
import pytz
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.logger import setup_logger, get_logger
from services.reddit_client import RedditClient
from services.drop_detector import DropDetector
from services.notifiers import PushoverNotifier, DiscordWebhookNotifier, EmailNotifier, NotificationManager
from services.stock_monitor_enhanced import EnhancedStockMonitor, FragranceProduct
from services.log_manager import LogManager
from services.container import get_container
from services.parfumo_scheduler import get_parfumo_scheduler


class FragDropMonitor:
    """Main application class"""

    def __init__(self):
        """Initialize the monitor"""
        self.logger = get_logger(__name__)
        self.logger.info("Initializing FragDropMonitor...")

        # Load environment variables
        load_dotenv()

        # Get service container
        container = get_container()
        self.config = container.config
        self.db = container.database
        self.schedule_manager = container.schedule_manager
        self.detector = container.drop_detector
        self.parfumo_scheduler = get_parfumo_scheduler(self.config)

        # Initialize components
        self.reddit_client = None
        self.reddit_enabled = False  # Track if Reddit monitoring is active
        self.notification_manager = NotificationManager()
        self.stock_monitor = None  # Will be initialized asynchronously

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

        # Stock monitoring configuration
        self.stock_config = self.config.get('stock_monitoring', {})
        self.stock_enabled = self.stock_config.get('enabled', True)
        self.stock_notifications = self.stock_config.get('notifications', {})

        # Stock schedule configuration (separate from Reddit drop window)
        self.stock_schedule_config = self.config.get('stock_schedule', {})
        self.stock_schedule_enabled = self.stock_schedule_config.get('enabled', True)
        self.stock_check_interval = self.stock_schedule_config.get('check_interval', 1800)  # 30 minutes default
        self.stock_window_enabled = self.stock_schedule_config.get('window_enabled', False)
        self.stock_window_timezone = self.stock_schedule_config.get('timezone', 'America/New_York')
        self.stock_window_days = self.stock_schedule_config.get('days_of_week', [])  # Empty = all days
        self.stock_window_start_hour = self.stock_schedule_config.get('start_hour', 9)
        self.stock_window_start_minute = self.stock_schedule_config.get('start_minute', 0)
        self.stock_window_end_hour = self.stock_schedule_config.get('end_hour', 18)
        self.stock_window_end_minute = self.stock_schedule_config.get('end_minute', 0)

        self._setup_reddit_client()
        self._setup_notifications()

    def _setup_reddit_client(self):
        """Setup Reddit client"""
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        user_agent = os.getenv('REDDIT_USER_AGENT', 'FragDropDetector/1.0')
        refresh_token = os.getenv('REDDIT_REFRESH_TOKEN')
        username = os.getenv('REDDIT_USERNAME')

        if not client_id or not client_secret:
            self.logger.error("Reddit credentials not found in environment variables!")
            self.logger.error("Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
            sys.exit(1)

        # Check for user authentication - REQUIRED for Reddit monitoring
        if not refresh_token:
            self.logger.warning("=" * 70)
            self.logger.warning("REDDIT MONITORING DISABLED - Authentication Required")
            self.logger.warning("")
            self.logger.warning("r/MontagneParfums requires user authentication to see all posts.")
            self.logger.warning("Without authentication, you'll miss member-only content and")
            self.logger.warning("notification links may not work properly.")
            self.logger.warning("")
            self.logger.warning("To enable Reddit monitoring:")
            self.logger.warning("  1. SSH with port forwarding: ssh -L 8080:localhost:8080 pi@YOUR_IP")
            self.logger.warning("  2. Run: python generate_token_headless.py")
            self.logger.warning("  3. Follow the browser authentication steps")
            self.logger.warning("")
            self.logger.warning("Stock monitoring will continue to work normally.")
            self.logger.warning("=" * 70)
            self.reddit_client = None
            self.reddit_enabled = False
            return

        # Initialize with user authentication
        self.reddit_client = RedditClient(client_id, client_secret, user_agent, refresh_token)

        # Test connection
        if not self.reddit_client.test_connection():
            self.logger.error("Failed to connect to Reddit API!")
            self.logger.error("Your refresh token may have expired. Run: python generate_token_headless.py")
            sys.exit(1)

        self.reddit_enabled = True
        self.logger.info(f"Reddit monitoring ENABLED - Authenticated as u/{username}")
        self.logger.info("Full access to r/MontagneParfums including member-only posts")

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

    def check_for_drops(self):
        """Check for new drops"""
        # Skip if Reddit monitoring is disabled
        if not self.reddit_enabled:
            return

        # Check if we're in the drop window
        if not self.schedule_manager.is_drop_window():
            tz = pytz.timezone(self.drop_window_config.get('timezone', 'America/New_York'))
            now = datetime.now(tz)

            window_desc = self.schedule_manager.get_drop_window_description()
            self.logger.info(f"Outside drop window ({window_desc}). Current time: {now.strftime('%A %I:%M %p %Z')}")

            # Calculate time until next window
            seconds_until = self.schedule_manager.get_time_until_next_drop_window()
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

    def start_parfumo_scheduler(self):
        """Start the Parfumo scheduler service"""
        self.parfumo_scheduler.start()

    def run_parfumo_update(self):
        """Run a Parfumo update immediately"""
        return self.parfumo_scheduler.run_update()

    async def check_stock_changes(self):
        """Check for stock changes on Montagne Parfums website"""
        if not self.stock_enabled or not self.stock_schedule_enabled:
            return

        # Check if we're in the stock monitoring window (independent of Reddit drop window)
        if not (self.stock_schedule_enabled and self.stock_enabled and self.schedule_manager.is_stock_window()):
            if self.stock_window_enabled:
                tz = pytz.timezone(self.stock_schedule_config.get('timezone', 'America/New_York'))
                now = datetime.now(tz)

                window_desc = self.schedule_manager.get_stock_window_description()
                self.logger.info(f"Outside stock monitoring window ({window_desc}). Current time: {now.strftime('%A %I:%M %p %Z')}")
            return

        try:
            if self.stock_window_enabled:
                self.logger.info("STOCK WINDOW ACTIVE - Checking Montagne Parfums stock...")
            else:
                self.logger.info("Checking Montagne Parfums stock...")

            # Initialize stock monitor if needed
            if not self.stock_monitor:
                self.stock_monitor = EnhancedStockMonitor(headless=True, use_cache=True)
                # Load watchlist from config if available
                watchlist = self.config.get('stock_monitoring', {}).get('watchlist', [])
                if watchlist:
                    self.stock_monitor.add_to_watchlist(watchlist)
                    self.logger.info(f"Loaded {len(watchlist)} products to watchlist")

            # Get current stock from website
            current_stock = await self.stock_monitor.get_current_stock()
            if not current_stock:
                self.logger.warning("Failed to retrieve current stock")
                return

            # Get previous stock from database
            previous_stock_data = self.db.get_all_fragrances()

            # Convert database format to stock monitor format for comparison
            previous_stock = {}
            for slug, data in previous_stock_data.items():
                previous_stock[slug] = FragranceProduct(
                    name=data['name'],
                    slug=slug,
                    url=data['url'],
                    price=data['price'],
                    in_stock=data['in_stock']
                )

            # Save current stock to database
            for slug, product in current_stock.items():
                self.db.save_fragrance_stock(product.to_dict())

            # Compare and find changes
            if previous_stock:
                changes = self.stock_monitor.compare_stock(previous_stock, current_stock)

                if any(changes.values()):
                    summary_parts = []
                    if changes['new_products']:
                        summary_parts.append(f"{len(changes['new_products'])} new")
                    if changes['restocked']:
                        summary_parts.append(f"{len(changes['restocked'])} restocked")
                    if changes['out_of_stock']:
                        summary_parts.append(f"{len(changes['out_of_stock'])} out of stock")
                    if changes['price_changes']:
                        summary_parts.append(f"{len(changes['price_changes'])} price changes")

                    self.logger.info(f"Stock changes: {', '.join(summary_parts)}")

                    # Process and notify about changes
                    self._process_stock_changes(changes)
                else:
                    self.logger.info("No stock changes detected")
            else:
                self.logger.info(f"Initial stock scan complete - tracking {len(current_stock)} products")

        except Exception as e:
            self.logger.error(f"Error during stock check: {e}")

    def _process_stock_changes(self, changes):
        """Process stock changes and send notifications"""
        notifications_to_send = []

        # Watchlist restocks (always notify regardless of settings)
        if changes.get('watchlist_changes'):
            for change_type, product_or_info in changes['watchlist_changes']:
                if change_type == 'restocked':
                    product = product_or_info
                    self.db.save_stock_change({
                        'fragrance_slug': product.slug,
                        'change_type': 'restocked',
                        'new_value': 'In Stock (Watchlist)'
                    })
                    notifications_to_send.append({
                        'title': f'Watchlist Item Back in Stock!',
                        'url': product.url,
                        'price': product.price,
                        'change_type': 'watchlist_restock',
                        'message': f'{product.name} is now available'
                    })
                    self.logger.info(f"Watchlist item restocked: {product.name}")

        # New products
        if changes['new_products'] and self.stock_notifications.get('new_products', True):
            for product in changes['new_products']:
                self.db.save_stock_change({
                    'fragrance_slug': product.slug,
                    'change_type': 'new',
                    'new_value': product.name
                })
                notifications_to_send.append({
                    'title': f'New Fragrance: {product.name}',
                    'url': product.url,
                    'price': product.price,
                    'change_type': 'new_product'
                })

                # Auto-scrape Parfumo data for new products if enabled
                if self.config.get('parfumo', {}).get('auto_scrape_new', True):
                    try:
                        from src.services.parfumo_updater import get_parfumo_updater
                        updater = get_parfumo_updater()
                        if updater.update_single_fragrance(product.slug):
                            self.logger.info(f"Successfully fetched Parfumo data for new product: {product.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to fetch Parfumo data for {product.name}: {e}")

        # Restocked products
        if changes['restocked'] and self.stock_notifications.get('restocked_products', True):
            for product in changes['restocked']:
                self.db.save_stock_change({
                    'fragrance_slug': product.slug,
                    'change_type': 'restocked',
                    'new_value': 'In Stock'
                })
                notifications_to_send.append({
                    'title': f'Restocked: {product.name}',
                    'url': product.url,
                    'price': product.price,
                    'change_type': 'restock'
                })

        # Price changes
        if changes['price_changes'] and self.stock_notifications.get('price_changes', False):
            for change in changes['price_changes']:
                product = change['product']
                self.db.save_stock_change({
                    'fragrance_slug': product.slug,
                    'change_type': 'price_change',
                    'old_value': change['old_price'],
                    'new_value': change['new_price']
                })
                notifications_to_send.append({
                    'title': f'Price Change: {product.name}',
                    'url': product.url,
                    'price': f"{change['old_price']} → {change['new_price']}",
                    'change_type': 'price_change'
                })

        # Send notifications
        for notification in notifications_to_send:
            # Format as drop-like notification for compatibility
            drop_notification = {
                'title': notification['title'],
                'author': 'Stock Monitor',
                'url': notification['url'],
                'confidence': 1.0,
                'detection_metadata': {
                    'change_type': notification['change_type'],
                    'price': notification['price']
                }
            }
            self.notification_manager.send_notifications(drop_notification)

    def run(self):
        """Run the monitor"""
        self.logger.info("Starting FragDropMonitor...")
        self.logger.info(f"Monitoring r/{self.subreddit}")
        self.logger.info(f"Reddit check interval: {self.check_interval} seconds")
        if self.stock_schedule_enabled:
            self.logger.info(f"Stock check interval: {self.stock_check_interval} seconds")

        # Send test notification if requested
        if os.getenv('SEND_TEST_NOTIFICATION', '').lower() == 'true':
            self.logger.info("Sending test notification...")
            for notifier in self.notification_manager.notifiers:
                if hasattr(notifier, 'send_test'):
                    notifier.send_test()

        try:
            # Create async event loop for stock monitoring
            import asyncio
            loop = asyncio.new_event_loop()

            # Track last execution times for independent scheduling
            last_reddit_check = 0
            last_stock_check = 0

            # Start Parfumo daily update thread
            self.start_parfumo_scheduler()

            # Use minimum interval for main loop to ensure proper timing
            main_loop_interval = min(self.check_interval, self.stock_check_interval if self.stock_schedule_enabled else self.check_interval)

            while True:
                current_time = time.time()

                # Check Reddit based on its interval
                if current_time - last_reddit_check >= self.check_interval:
                    self.check_for_drops()
                    last_reddit_check = current_time

                # Check stock based on its interval (if enabled)
                if self.stock_schedule_enabled and current_time - last_stock_check >= self.stock_check_interval:
                    loop.run_until_complete(self.check_stock_changes())
                    last_stock_check = current_time

                # Sleep for the main loop interval
                time.sleep(main_loop_interval)

        except KeyboardInterrupt:
            self.logger.info("Shutting down FragDropMonitor...")
            if self.stock_monitor:
                loop.run_until_complete(self.stock_monitor.cleanup())
            loop.close()
            sys.exit(0)

    def run_once(self):
        """Run a single check (for testing)"""
        self.logger.info("Running single check...")
        self.check_for_drops()

        # Run async stock check
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.check_stock_changes())

        if self.stock_monitor:
            loop.run_until_complete(self.stock_monitor.cleanup())
        loop.close()

        self.logger.info("Single check complete")


def main():
    """Main entry point"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    logging_config = {}
    log_manager = None

    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)
            logging_config = full_config.get('logging', {})

    logger = setup_logger(
        name="main",
        level=logging_config.get('level', 'INFO'),
        file_path=logging_config.get('file_path') if logging_config.get('file_enabled') else None,
        max_bytes=logging_config.get('max_file_size', 10) * 1024 * 1024,
        backup_count=logging_config.get('backup_count', 5),
        use_colors=True
    )

    if logging_config.get('file_enabled'):
        log_manager = LogManager(logging_config)

    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        monitor = FragDropMonitor()
        monitor.log_manager = log_manager
        monitor.run_once()
    else:
        monitor = FragDropMonitor()
        monitor.log_manager = log_manager
        monitor.run()


if __name__ == '__main__':
    main()