"""
Testing and notification endpoints
"""

import os
import sys
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import structlog

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from api.models import RedditConfig
from services.reddit_client import RedditClient
from services.notifiers import PushoverNotifier, DiscordWebhookNotifier

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["test"])


@router.post("/api/test/reddit")
async def test_reddit_connection(config: RedditConfig):
    """Test Reddit connection with validation"""
    try:
        client = RedditClient(config.client_id, config.client_secret, config.user_agent)
        success = client.test_connection()

        if success:
            logger.info("Reddit connection test successful")
            return {"success": True, "message": "Reddit connection successful"}
        else:
            logger.warning("Reddit connection test failed")
            return {"success": False, "message": "Reddit connection failed"}

    except Exception as e:
        logger.error("Reddit connection test error", error=str(e))
        return {"success": False, "message": f"Connection test failed: {str(e)}"}


@router.post("/api/test/notifications")
async def test_notifications():
    """Test notification services"""
    results = {}

    pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
    pushover_user = os.getenv('PUSHOVER_USER_KEY')
    if pushover_token and pushover_user:
        try:
            notifier = PushoverNotifier(pushover_token, pushover_user)
            success = notifier.send_test()
            results["pushover"] = {"success": success, "message": "Test sent" if success else "Failed"}
        except Exception as e:
            results["pushover"] = {"success": False, "message": str(e)}

    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook:
        try:
            notifier = DiscordWebhookNotifier(discord_webhook)
            success = notifier.send_test()
            results["discord"] = {"success": success, "message": "Test sent" if success else "Failed"}
        except Exception as e:
            results["discord"] = {"success": False, "message": str(e)}

    logger.info("Notification test completed", results=results)
    return results


@router.post("/api/test/pushover")
async def test_pushover():
    """Test Pushover notification service"""
    pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
    pushover_user = os.getenv('PUSHOVER_USER_KEY')

    if not pushover_token or not pushover_user:
        return JSONResponse(
            status_code=400,
            content={"error": "Pushover credentials not configured"}
        )

    try:
        notifier = PushoverNotifier(pushover_token, pushover_user)
        success = notifier.send_test()

        if success:
            logger.info("Pushover test notification sent successfully")
            return {"success": True, "message": "Test notification sent successfully"}
        else:
            logger.warning("Pushover test notification failed")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to send test notification"}
            )
    except Exception as e:
        logger.error("Pushover test error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Test failed: {str(e)}"}
        )


@router.post("/api/test/discord")
async def test_discord():
    """Test Discord notification service"""
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')

    if not discord_webhook:
        return JSONResponse(
            status_code=400,
            content={"error": "Discord webhook URL not configured"}
        )

    try:
        notifier = DiscordWebhookNotifier(discord_webhook)
        success = notifier.send_test()

        if success:
            logger.info("Discord test notification sent successfully")
            return {"success": True, "message": "Test notification sent successfully"}
        else:
            logger.warning("Discord test notification failed")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to send test notification"}
            )
    except Exception as e:
        logger.error("Discord test error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Test failed: {str(e)}"}
        )


@router.post("/api/test/email")
async def test_email():
    """Test Email notification service"""
    email_sender = os.getenv('EMAIL_SENDER')

    if not email_sender:
        return JSONResponse(
            status_code=400,
            content={"error": "Email service not configured"}
        )

    try:
        logger.info("Email test requested but service not implemented")
        return JSONResponse(
            status_code=501,
            content={"error": "Email service not yet implemented"}
        )
    except Exception as e:
        logger.error("Email test error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Test failed: {str(e)}"}
        )


@router.post("/api/test/all")
async def test_all_services():
    """Test all configured notification services"""
    return await test_notifications()
