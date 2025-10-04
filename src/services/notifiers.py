"""
Notification services for FragDropDetector
"""

import logging
import requests
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NotificationService(ABC):
    """
    Base notification service class with retry logic and error handling
    """

    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize base notification service

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._last_error: Optional[str] = None

    @abstractmethod
    def _send_notification(self, drop: Dict) -> bool:
        """
        Internal method to send notification (must be implemented by subclasses)

        Args:
            drop: Drop dictionary

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def send_test(self) -> bool:
        """
        Send a test notification (must be implemented by subclasses)

        Returns:
            True if successful, False otherwise
        """
        pass

    def send(self, drop: Dict) -> bool:
        """
        Send notification with retry logic

        Args:
            drop: Drop dictionary

        Returns:
            True if successful, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                success = self._send_notification(drop)
                if success:
                    self._last_error = None
                    return True

                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"{self.__class__.__name__}: Attempt {attempt + 1} failed, "
                        f"retrying in {self.retry_delay}s..."
                    )
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff

            except Exception as e:
                self._last_error = str(e)
                logger.error(f"{self.__class__.__name__} error on attempt {attempt + 1}: {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return False

        logger.error(f"{self.__class__.__name__}: All {self.max_retries} attempts failed")
        return False

    def get_last_error(self) -> Optional[str]:
        """Get the last error message"""
        return self._last_error

    def validate_config(self) -> bool:
        """
        Validate notifier configuration (can be overridden by subclasses)

        Returns:
            True if configuration is valid
        """
        return True


class PushoverNotifier(NotificationService):
    """Pushover notification service - Best for iOS"""

    def __init__(self, app_token: str, user_key: str, max_retries: int = 3, retry_delay: int = 2):
        """Initialize Pushover notifier"""
        super().__init__(max_retries, retry_delay)
        self.app_token = app_token
        self.user_key = user_key
        logger.info("Pushover notifier initialized")

    def validate_config(self) -> bool:
        """Validate Pushover configuration"""
        return bool(self.app_token and self.user_key)

    def _send_notification(self, drop: Dict) -> bool:
        """Internal method to send notification via Pushover"""
        title = f"🚨 FragDrop: {drop.get('author', 'Unknown')}"
        message = f"{drop['title'][:100]}\n\nConfidence: {drop.get('confidence', 0) * 100:.0f}%"

        data = {
            "token": self.app_token,
            "user": self.user_key,
            "title": title,
            "message": message,
            "url": drop.get("url", ""),
            "url_title": "View on Reddit",
            "priority": 1,
            "sound": "cashregister"
        }

        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            data=data,
            timeout=10
        )

        if response.status_code == 200:
            logger.info(f"Pushover notification sent for: {drop['title'][:50]}...")
            return True
        else:
            logger.error(f"Pushover API error: {response.text}")
            return False

    def send_test(self) -> bool:
        """Send a test notification via Pushover"""
        test_drop = {
            'title': 'Test Notification - FragDropDetector',
            'author': 'System',
            'confidence': 1.0,
            'url': 'https://reddit.com/r/MontagneParfums'
        }
        return self.send(test_drop)


class DiscordWebhookNotifier(NotificationService):
    """Discord webhook notification service"""

    def __init__(self, webhook_url: str, max_retries: int = 3, retry_delay: int = 2):
        """Initialize Discord notifier"""
        super().__init__(max_retries, retry_delay)
        self.webhook_url = webhook_url
        logger.info("Discord webhook notifier initialized")

    def validate_config(self) -> bool:
        """Validate Discord configuration"""
        return bool(self.webhook_url and self.webhook_url.startswith('https://'))

    def _send_notification(self, drop: Dict) -> bool:
        """Internal method to send notification to Discord"""
        # Build embed
        confidence = drop.get('confidence', 0) * 100
        metadata = drop.get('detection_metadata', {})
        keywords = ', '.join(metadata.get('primary_matches', [])[:3]) if metadata.get('primary_matches') else 'N/A'

        embed = {
            "title": f"🚨 {drop['title'][:100]}",
            "url": drop.get('url', ''),
            "color": 16725806,
            "author": {
                "name": f"u/{drop.get('author', 'Unknown')}",
                "url": f"https://reddit.com/u/{drop.get('author', '')}"
            },
            "fields": [
                {
                    "name": "Confidence",
                    "value": f"{confidence:.0f}%",
                    "inline": True
                },
                {
                    "name": "Keywords",
                    "value": keywords,
                    "inline": True
                }
            ],
            "footer": {
                "text": "FragDropDetector"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        payload = {
            "content": "@everyone New fragrance drop detected!",
            "embeds": [embed]
        }

        response = requests.post(
            self.webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code in [200, 204]:
            logger.info(f"Discord notification sent for: {drop['title'][:50]}...")
            return True
        else:
            logger.error(f"Discord webhook error: {response.status_code} - {response.text}")
            return False

    def send_test(self) -> bool:
        """Send a test notification to Discord"""
        test_drop = {
            'title': 'Test Notification - FragDropDetector',
            'author': 'System',
            'confidence': 1.0,
            'url': 'https://reddit.com/r/MontagneParfums',
            'detection_metadata': {
                'primary_matches': ['test', 'notification']
            }
        }
        return self.send(test_drop)


class EmailNotifier(NotificationService):
    """Email notification service"""

    def __init__(self, smtp_server: str, smtp_port: int, sender: str, password: str,
                 recipients: List[str], max_retries: int = 3, retry_delay: int = 2):
        """Initialize email notifier"""
        super().__init__(max_retries, retry_delay)
        import smtplib
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password
        self.recipients = recipients
        logger.info(f"Email notifier initialized with {len(recipients)} recipients")

    def validate_config(self) -> bool:
        """Validate email configuration"""
        return bool(
            self.smtp_server and
            self.smtp_port and
            self.sender and
            self.password and
            self.recipients
        )

    def _send_notification(self, drop: Dict) -> bool:
        """Internal method to send email notification"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚨 FragDrop Alert: {drop['title'][:50]}..."
        msg['From'] = self.sender
        msg['To'] = ', '.join(self.recipients)

        html_content = self._format_email_html(drop)
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.sender, self.password)
            server.send_message(msg)

        logger.info(f"Email notification sent for: {drop['title'][:50]}...")
        return True

    def _format_email_html(self, drop: Dict) -> str:
        """Format drop as HTML for email"""
        metadata = drop.get('detection_metadata', {})
        keywords = ', '.join(metadata.get('primary_matches', [])[:3])

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #FF6B6B;">🚨 Fragrance Drop Alert!</h2>
            <h3>{drop['title']}</h3>
            <p><strong>Author:</strong> {drop.get('author', 'Unknown')}</p>
            <p><strong>Confidence:</strong> {drop.get('confidence', 0) * 100:.0f}%</p>
            <p><strong>Keywords:</strong> {keywords}</p>
            <p>{drop.get('selftext', '')[:500]}</p>
            <p><a href="{drop.get('url', '')}" style="background-color: #FF6B6B; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View on Reddit</a></p>
            <hr>
            <p style="color: #666; font-size: 12px;">FragDropDetector - Automated Fragrance Drop Monitoring</p>
        </body>
        </html>
        """
        return html

    def send_test(self) -> bool:
        """Send a test email notification"""
        test_drop = {
            'title': 'Test Notification - FragDropDetector',
            'author': 'System',
            'confidence': 1.0,
            'url': 'https://reddit.com/r/MontagneParfums',
            'detection_metadata': {
                'primary_matches': ['test', 'notification']
            },
            'selftext': 'This is a test notification from FragDropDetector.'
        }
        return self.send(test_drop)


class NotificationManager:
    """Manages multiple notification services"""

    def __init__(self):
        """Initialize notification manager"""
        self.notifiers = []
        logger.info("Notification manager initialized")

    def add_notifier(self, notifier: NotificationService):
        """Add a notification service"""
        self.notifiers.append(notifier)
        logger.info(f"Added {notifier.__class__.__name__} to notification manager")

    def send_notifications(self, drop: Dict) -> Dict[str, bool]:
        """
        Send notifications through all configured services

        Args:
            drop: Drop dictionary

        Returns:
            Dictionary of service names and success status
        """
        results = {}

        for notifier in self.notifiers:
            service_name = notifier.__class__.__name__
            try:
                success = notifier.send(drop)
                results[service_name] = success
            except Exception as e:
                logger.error(f"Error with {service_name}: {e}")
                results[service_name] = False

        return results