"""
Notification services for FragDropDetector
"""

import logging
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationService:
    """Base notification service class"""

    def send(self, drop: Dict) -> bool:
        """Send notification for a drop"""
        raise NotImplementedError


class PushoverNotifier(NotificationService):
    """Pushover notification service - Best for iOS"""

    def __init__(self, app_token: str, user_key: str):
        """Initialize Pushover notifier"""
        self.app_token = app_token
        self.user_key = user_key
        logger.info("Pushover notifier initialized")

    def send(self, drop: Dict) -> bool:
        """Send notification via Pushover"""
        try:
            title = f"🚨 FragDrop: {drop.get('author', 'Unknown')}"
            message = f"{drop['title'][:100]}\n\nConfidence: {drop.get('confidence', 0) * 100:.0f}%"

            data = {
                "token": self.app_token,
                "user": self.user_key,
                "title": title,
                "message": message,
                "url": drop.get("url", ""),
                "url_title": "View on Reddit",
                "priority": 1,  # High priority (bypasses quiet hours)
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

        except Exception as e:
            logger.error(f"Error sending Pushover notification: {e}")
            return False


class DiscordWebhookNotifier(NotificationService):
    """Discord webhook notification service"""

    def __init__(self, webhook_url: str):
        """Initialize Discord notifier"""
        self.webhook_url = webhook_url
        logger.info("Discord webhook notifier initialized")

    def send(self, drop: Dict) -> bool:
        """Send notification to Discord"""
        try:
            # Build embed
            confidence = drop.get('confidence', 0) * 100
            metadata = drop.get('detection_metadata', {})
            keywords = ', '.join(metadata.get('primary_matches', [])[:3]) if metadata.get('primary_matches') else 'N/A'

            embed = {
                "title": f"🚨 {drop['title'][:100]}",
                "url": drop.get('url', ''),
                "color": 16725806,  # Red color
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

            # Build message
            payload = {
                "content": "@everyone New fragrance drop detected!",
                "embeds": [embed]
            }

            # Send webhook
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

        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False


class EmailNotifier(NotificationService):
    """Email notification service"""

    def __init__(self, smtp_server: str, smtp_port: int, sender: str, password: str, recipients: List[str]):
        """Initialize email notifier"""
        import smtplib
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password
        self.recipients = recipients
        logger.info(f"Email notifier initialized with {len(recipients)} recipients")

    def send(self, drop: Dict) -> bool:
        """Send email notification"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚨 FragDrop Alert: {drop['title'][:50]}..."
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.recipients)

            # Create HTML content
            html_content = self._format_email_html(drop)

            # Attach HTML
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg)

            logger.info(f"Email notification sent for: {drop['title'][:50]}...")
            return True

        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False

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