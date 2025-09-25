#!/usr/bin/env python3
"""Send a test notification simulating a real restock post"""

import os
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.notifiers import PushoverNotifier, DiscordWebhookNotifier
from datetime import datetime

def send_restock_notification():
    """Send notification for a real restock URL"""

    load_dotenv()

    # Use one of your actual restock URLs
    test_drop = {
        'title': 'RESTOCK Today 8pm EST',
        'author': 'ayybrahamlmaocoln',
        'url': 'https://www.reddit.com/r/MontagneParfums/comments/1hh6ziv/restock_today_8pm_est/',
        'selftext': 'Hey Montagne family! Restock is going live today at 8PM EST. Limited quantities on popular fragrances!',
        'confidence': 1.0,
        'link_flair_text': '⭐️RESTOCK⭐️',
        'detection_metadata': {
            'drop_time': {
                'hour': 20,
                'minute': 0,
                'is_today': True,
                'time_string': '8pm EST'
            },
            'primary_matches': ['RESTOCK IN TITLE', 'restock'],
            'trusted_author': 'ayybrahamlmaocoln',
            'vendor_match': True,
            'time_match': True,
            'flair_match': '⭐️RESTOCK⭐️'
        },
        'detected_at': datetime.utcnow().isoformat()
    }

    print("=" * 60)
    print("SENDING RESTOCK NOTIFICATION")
    print("=" * 60)
    print(f"\nSimulating detection of: {test_drop['title']}")
    print(f"Reddit URL: {test_drop['url']}")
    print(f"(This is one of your actual restock URLs)")
    print()

    # Send Pushover
    pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
    pushover_key = os.getenv('PUSHOVER_USER_KEY')

    if pushover_token and pushover_key:
        print("📱 Sending Pushover notification...")
        pushover = PushoverNotifier(app_token=pushover_token, user_key=pushover_key)
        result = pushover.send(test_drop)
        if result:
            print("✅ Pushover notification sent!")
            print("   Check your phone - this shows what you'd get for real restocks")

    # Send Discord
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')

    if discord_webhook:
        print("\n💬 Sending Discord notification...")
        discord = DiscordWebhookNotifier(webhook_url=discord_webhook)
        result = discord.send(test_drop)
        if result:
            print("✅ Discord notification sent!")
            print("   Check Discord - this is what real restock alerts look like")

    print("\n" + "=" * 60)
    print("NOTIFICATION SENT")
    print("=" * 60)
    print("\nThis notification includes:")
    print("• The actual Reddit URL (clickable)")
    print("• Drop time extracted from title")
    print("• High priority alert (bypasses quiet hours)")
    print("• Trusted author verification")
    print("\nWhen clicked, the Reddit URL may show 'deleted' if the")
    print("restock post was removed after the sale ended.")

if __name__ == "__main__":
    send_restock_notification()