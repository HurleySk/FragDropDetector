"""
Notification services for FragDropDetector
"""

import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime
from discord_webhook import DiscordWebhook, DiscordEmbed

logger = logging.getLogger(__name__)


class NotificationService:
    """Base notification service class"""

    def send(self, drop: Dict) -> bool:
        """Send notification for a drop"""
        raise NotImplementedError


class DiscordNotifier(NotificationService):
    """Discord webhook notification service"""

    def __init__(self, webhook_url: str):
        """
        Initialize Discord notifier

        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url
        logger.info("Discord notifier initialized")

    def send(self, drop: Dict) -> bool:
        """
        Send Discord notification for a drop

        Args:
            drop: Drop dictionary with metadata

        Returns:
            True if notification sent successfully
        """
        try:
            webhook = DiscordWebhook(url=self.webhook_url)

            # Create embed
            embed = DiscordEmbed(
                title=drop['title'],
                description=self._format_description(drop),
                color='FF6B6B',  # Nice red color for drops
                url=drop.get('url', ''),
                timestamp=datetime.utcnow().isoformat()
            )

            # Add fields
            embed.add_embed_field(
                name='Author',
                value=drop.get('author', 'Unknown'),
                inline=True
            )
            embed.add_embed_field(
                name='Confidence',
                value=f"{drop.get('confidence', 0) * 100:.0f}%",
                inline=True
            )

            # Add keywords if available
            metadata = drop.get('detection_metadata', {})
            if metadata.get('primary_matches'):
                keywords = ', '.join(metadata['primary_matches'][:3])
                embed.add_embed_field(
                    name='Keywords',
                    value=keywords,
                    inline=False
                )

            # Set footer
            embed.set_footer(
                text='FragDropDetector',
                icon_url='https://www.redditstatic.com/desktop2x/img/favicon/apple-icon-180x180.png'
            )

            # Add to webhook and send
            webhook.add_embed(embed)
            response = webhook.execute()

            if response.status_code == 200:
                logger.info(f"Discord notification sent for: {drop['title'][:50]}...")
                return True
            else:
                logger.error(f"Discord webhook failed with status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False

    def _format_description(self, drop: Dict) -> str:
        """Format drop description for Discord embed"""
        text = drop.get('selftext', '')
        if len(text) > 200:
            text = text[:197] + '...'
        return text if text else 'Click the link for more details.'

    def send_test(self) -> bool:
        """Send a test notification"""
        test_drop = {
            'title': 'Test Drop Alert',
            'author': 'FragDropDetector',
            'url': 'https://reddit.com',
            'selftext': 'This is a test notification from FragDropDetector.',
            'confidence': 1.0,
            'detection_metadata': {
                'primary_matches': ['test', 'notification']
            }
        }
        return self.send(test_drop)


class TelegramNotifier(NotificationService):
    """Telegram bot notification service"""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID to send notifications to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        logger.info("Telegram notifier initialized")

    def send(self, drop: Dict) -> bool:
        """
        Send Telegram notification for a drop

        Args:
            drop: Drop dictionary with metadata

        Returns:
            True if notification sent successfully
        """
        try:
            message = self._format_telegram_message(drop)

            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }

            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload
            )

            if response.status_code == 200:
                logger.info(f"Telegram notification sent for: {drop['title'][:50]}...")
                return True
            else:
                logger.error(f"Telegram API failed with status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False

    def _format_telegram_message(self, drop: Dict) -> str:
        """Format drop for Telegram message"""
        message = f"*🚨 FRAGRANCE DROP ALERT*\n\n"
        message += f"*{drop['title']}*\n"
        message += f"Author: {drop.get('author', 'Unknown')}\n"
        message += f"Confidence: {drop.get('confidence', 0) * 100:.0f}%\n"

        metadata = drop.get('detection_metadata', {})
        if metadata.get('primary_matches'):
            keywords = ', '.join(metadata['primary_matches'][:3])
            message += f"Keywords: {keywords}\n"

        message += f"\n[View on Reddit]({drop.get('url', '')})"

        return message


class EmailNotifier(NotificationService):
    """Email notification service"""

    def __init__(self, smtp_server: str, smtp_port: int, sender: str,
                 password: str, recipients: List[str]):
        """
        Initialize email notifier

        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            sender: Sender email address
            password: Sender email password
            recipients: List of recipient email addresses
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password
        self.recipients = recipients
        logger.info("Email notifier initialized")

    def send(self, drop: Dict) -> bool:
        """
        Send email notification for a drop

        Args:
            drop: Drop dictionary with metadata

        Returns:
            True if notification sent successfully
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"FragDrop Alert: {drop['title'][:50]}"
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.recipients)

            # Create HTML content
            html = self._format_email_html(drop)
            part = MIMEText(html, 'html')
            msg.attach(part)

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