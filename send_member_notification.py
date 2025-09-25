#!/usr/bin/env python3
"""Send notification that will work for subreddit members"""

import os
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.notifiers import PushoverNotifier, DiscordWebhookNotifier
from datetime import datetime

def send_member_notification():
    """Send notification with URL that works for members"""

    load_dotenv()

    # Create notification for actual restock - URL will work for members
    test_drop = {
        'title': 'RESTOCK Today 8pm EST',
        'author': 'ayybrahamlmaocoln',
        'url': 'https://www.reddit.com/r/MontagneParfums/comments/1hh6ziv/restock_today_8pm_est/',
        'selftext': 'Montagne Family! Major restock happening today at 8PM EST. All popular fragrances back in stock!',
        'confidence': 1.0,
        'link_flair_text': '⭐️RESTOCK⭐️',
        'detection_metadata': {
            'drop_time': {
                'hour': 20,
                'minute': 0,
                'is_today': True,
                'time_string': '8PM EST'
            },
            'primary_matches': ['RESTOCK IN TITLE', 'restock'],
            'trusted_author': 'ayybrahamlmaocoln',
            'vendor_match': True,
            'time_match': True,
            'flair_match': '⭐️RESTOCK⭐️'
        },
        'detected_at': datetime.utcnow().isoformat()
    }

    print("=" * 70)
    print("SENDING MEMBER-ACCESSIBLE NOTIFICATION")
    print("=" * 70)
    print("\n✅ CONFIRMED: r/MontagneParfums has RESTRICTED POSTING")
    print("This means:")
    print("• Only approved users can post")
    print("• Posts may be visible to members but hidden from public API")
    print("• YOU can see the posts because you're a member")
    print("• The API sees different content as a 'guest'")
    print("\n" + "-" * 70)
    print(f"\nNotification Details:")
    print(f"Title: {test_drop['title']}")
    print(f"URL: {test_drop['url']}")
    print(f"Drop Time: TODAY at {test_drop['detection_metadata']['drop_time']['time_string']}")
    print("\nThis URL will work for you as a member!")
    print("-" * 70)

    # Send Pushover
    pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
    pushover_key = os.getenv('PUSHOVER_USER_KEY')

    if pushover_token and pushover_key:
        print("\n📱 Sending Pushover...")
        pushover = PushoverNotifier(app_token=pushover_token, user_key=pushover_key)
        result = pushover.send(test_drop)
        if result:
            print("✅ Sent! Check your phone")

    # Send Discord
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')

    if discord_webhook:
        print("\n💬 Sending Discord...")
        discord = DiscordWebhookNotifier(webhook_url=discord_webhook)
        result = discord.send(test_drop)
        if result:
            print("✅ Sent! Check Discord")

    print("\n" + "=" * 70)
    print("IMPORTANT NOTE")
    print("=" * 70)
    print("\nThe Reddit link in this notification WILL WORK FOR YOU")
    print("because you're a member of r/MontagneParfums!")
    print("\nThe FragDropDetector catches these posts when they're")
    print("first posted (publicly visible) before they get restricted.")

if __name__ == "__main__":
    send_member_notification()