#!/usr/bin/env python3
"""
FragDropDetector Setup Validation Script
Checks if all required components are properly configured
"""

import os
import sys
from dotenv import load_dotenv

def print_header():
    print("=" * 70)
    print("FRAGDROPDETECTOR SETUP VALIDATION")
    print("=" * 70)
    print()

def check_reddit_credentials():
    """Check basic Reddit API credentials"""
    print("🔑 Reddit API Credentials")
    print("-" * 30)

    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("❌ Missing Reddit API credentials")
        print("   Add REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to .env")
        print("   Get them from https://www.reddit.com/prefs/apps")
        return False

    print(f"✅ Client ID: {client_id[:10]}...")
    print(f"✅ Client Secret: {'*' * len(client_secret)}")
    return True

def check_reddit_authentication():
    """Check Reddit user authentication"""
    print("\n👤 Reddit User Authentication")
    print("-" * 35)

    refresh_token = os.getenv('REDDIT_REFRESH_TOKEN')
    username = os.getenv('REDDIT_USERNAME')

    if not refresh_token:
        print("❌ Reddit authentication NOT configured")
        print("   Reddit monitoring is DISABLED")
        print("   Run: python generate_token_headless.py")
        print("")
        print("   Impact:")
        print("   • Will miss member-only posts in r/MontagneParfums")
        print("   • Notification links may not work")
        print("   • Incomplete drop detection")
        return False

    # Test the authentication
    try:
        import praw
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            user_agent="FragDropDetector/1.0"
        )

        user = reddit.user.me()
        print(f"✅ Authenticated as: u/{user.name}")

        # Check r/MontagneParfums access
        try:
            sub = reddit.subreddit("MontagneParfums")
            posts = list(sub.new(limit=1))
            if posts:
                print("✅ Can access r/MontagneParfums posts")
            else:
                print("⚠️  r/MontagneParfums appears empty (may be private)")
        except Exception as e:
            print(f"⚠️  Cannot access r/MontagneParfums: {e}")

        return True

    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        print("   Your refresh token may have expired")
        print("   Run: python generate_token_headless.py")
        return False

def check_notifications():
    """Check notification services"""
    print("\n📱 Notification Services")
    print("-" * 30)

    services_configured = 0

    # Pushover
    pushover_token = os.getenv('PUSHOVER_APP_TOKEN')
    pushover_user = os.getenv('PUSHOVER_USER_KEY')
    if pushover_token and pushover_user and pushover_token != 'your_app_token_here':
        print("✅ Pushover configured")
        services_configured += 1
    else:
        print("⚪ Pushover not configured")

    # Discord
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook and discord_webhook != 'paste_your_webhook_url_here':
        print("✅ Discord webhook configured")
        services_configured += 1
    else:
        print("⚪ Discord webhook not configured")

    # Email
    smtp_server = os.getenv('SMTP_SERVER')
    email_sender = os.getenv('EMAIL_SENDER')
    email_password = os.getenv('EMAIL_PASSWORD')
    if all([smtp_server, email_sender, email_password]) and smtp_server != 'smtp.gmail.com':
        print("✅ Email notifications configured")
        services_configured += 1
    else:
        print("⚪ Email notifications not configured")

    if services_configured == 0:
        print("\n❌ No notification services configured!")
        print("   You won't receive any drop alerts")
        print("   Configure at least one service in .env")
        return False
    else:
        print(f"\n✅ {services_configured} notification service(s) configured")
        return True

def check_system_status():
    """Check overall system status"""
    print("\n🖥️  System Status")
    print("-" * 20)

    try:
        # Check if main dependencies are available
        import praw
        print("✅ PRAW (Reddit API) available")
    except ImportError:
        print("❌ PRAW not installed (pip install praw)")
        return False

    try:
        import yaml
        print("✅ YAML parser available")
    except ImportError:
        print("❌ PyYAML not installed (pip install pyyaml)")
        return False

    # Check config file
    config_path = os.path.join('config', 'config.yaml')
    if os.path.exists(config_path):
        print("✅ Configuration file exists")
        try:
            with open(config_path, 'r') as f:
                yaml.safe_load(f)
            print("✅ Configuration file valid")
        except Exception as e:
            print(f"❌ Configuration file invalid: {e}")
            return False
    else:
        print("⚪ No config.yaml file (will use defaults)")

    return True

def print_summary(reddit_creds, reddit_auth, notifications, system):
    """Print setup summary"""
    print("\n" + "=" * 70)
    print("SETUP SUMMARY")
    print("=" * 70)

    if all([reddit_creds, reddit_auth, notifications, system]):
        print("🎉 SETUP COMPLETE!")
        print("")
        print("✅ Reddit API credentials configured")
        print("✅ Reddit user authentication active")
        print("✅ Notification services configured")
        print("✅ System dependencies available")
        print("")
        print("Your FragDropDetector is ready to monitor drops!")
        print("")
        print("Next steps:")
        print("• Start monitoring: python main.py")
        print("• Start web interface: python web_server.py")
        print("• Access dashboard: http://localhost:8000")

    elif reddit_creds and not reddit_auth and notifications and system:
        print("⚠️  PARTIAL SETUP - Reddit Authentication Missing")
        print("")
        print("✅ Reddit API credentials configured")
        print("❌ Reddit user authentication missing")
        print("✅ Notification services configured")
        print("✅ System dependencies available")
        print("")
        print("CRITICAL: Reddit monitoring is DISABLED!")
        print("")
        print("To enable Reddit monitoring:")
        print("1. SSH with port forwarding: ssh -L 8080:localhost:8080 pi@YOUR_IP")
        print("2. Run: python generate_token_headless.py")
        print("3. Follow browser authentication steps")
        print("")
        print("Stock monitoring will work, but you'll miss Reddit drops!")

    else:
        print("❌ SETUP INCOMPLETE")
        print("")
        print("Missing components:")
        if not reddit_creds:
            print("• Reddit API credentials")
        if not reddit_auth:
            print("• Reddit user authentication")
        if not notifications:
            print("• Notification services")
        if not system:
            print("• System dependencies")
        print("")
        print("Please fix the issues above before running FragDropDetector.")

def main():
    """Main setup check"""
    load_dotenv()

    print_header()

    reddit_creds = check_reddit_credentials()
    reddit_auth = check_reddit_authentication()
    notifications = check_notifications()
    system = check_system_status()

    print_summary(reddit_creds, reddit_auth, notifications, system)

if __name__ == "__main__":
    main()