"""
Notification services for FragDropDetector
"""

import logging
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)


class NotificationService:
    """Base notification service class"""

    def send(self, drop: Dict) -> bool:
        """Send notification for a drop"""
        raise NotImplementedError


class FCMNotifier(NotificationService):
    """Firebase Cloud Messaging notification service"""

    def __init__(self, service_account_path: str = None, topic: str = "fragdrops"):
        """
        Initialize FCM notifier

        Args:
            service_account_path: Path to Firebase service account JSON file
            topic: FCM topic name for subscribers (default: "fragdrops")
        """
        self.topic = topic
        self.initialized = False

        try:
            # Initialize Firebase Admin SDK if not already initialized
            if not firebase_admin._apps:
                if service_account_path and Path(service_account_path).exists():
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                else:
                    # Try default initialization (for environments with GOOGLE_APPLICATION_CREDENTIALS)
                    firebase_admin.initialize_app()

            self.initialized = True
            logger.info(f"FCM notifier initialized for topic: {topic}")
        except Exception as e:
            logger.error(f"Failed to initialize FCM: {e}")
            logger.error("Make sure you have set up Firebase service account credentials")

    def send(self, drop: Dict) -> bool:
        """
        Send FCM notification for a drop

        Args:
            drop: Drop dictionary with metadata

        Returns:
            True if notification sent successfully
        """
        if not self.initialized:
            logger.error("FCM not initialized, cannot send notification")
            return False

        try:
            confidence = drop.get('confidence', 0) * 100
            author = drop.get('author', 'Unknown')

            # Build notification title and body
            title = f"🚨 Restock Alert: {drop['title'][:50]}"

            body = f"Author: u/{author}\n"
            body += f"Confidence: {confidence:.0f}%\n"

            # Add keywords if available
            metadata = drop.get('detection_metadata', {})
            if metadata.get('primary_matches'):
                keywords = ', '.join(metadata['primary_matches'][:3])
                body += f"Keywords: {keywords}"

            # Create the message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data={
                    'url': drop.get('url', ''),
                    'author': author,
                    'confidence': str(confidence),
                    'drop_id': drop.get('id', ''),
                },
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        icon='shopping_cart',
                        color='#FF6B6B',
                        sound='default',
                        click_action='FLUTTER_NOTIFICATION_CLICK',
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=title,
                                body=body,
                            ),
                            badge=1,
                            sound='default',
                        ),
                    ),
                ),
                topic=self.topic,
            )

            # Send the message
            response = messaging.send(message)
            logger.info(f"FCM notification sent for: {drop['title'][:50]}... (ID: {response})")
            return True

        except Exception as e:
            logger.error(f"Error sending FCM notification: {e}")
            return False

    def send_test(self) -> bool:
        """
        Send a test notification

        Returns:
            True if test notification sent successfully
        """
        test_drop = {
            'title': 'Test Notification - FragDropDetector',
            'author': 'TestBot',
            'confidence': 1.0,
            'url': 'https://reddit.com/r/MontagneParfums',
            'detection_metadata': {
                'primary_matches': ['test', 'notification']
            }
        }

        logger.info("Sending FCM test notification...")
        return self.send(test_drop)


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