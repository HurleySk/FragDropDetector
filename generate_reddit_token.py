#!/usr/bin/env python3
"""
Generate Reddit refresh token for user authentication

This script helps you obtain a refresh token that allows FragDropDetector
to access Reddit as YOUR account, seeing member-only content in r/MontagneParfums
"""

import praw
import random
import socket
import sys
import webbrowser
from urllib.parse import urlparse, parse_qs
import os
from dotenv import load_dotenv

def receive_connection():
    """Wait for and return the redirect URL from Reddit OAuth"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("localhost", 8080))
    server.listen(1)

    print("\n⏳ Waiting for Reddit authorization...")
    print("   (Your browser should open automatically)")

    client, _ = server.accept()
    data = client.recv(1024).decode("utf-8")

    # Send a response to the browser
    response = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
    response += b"<html><body><h1>Success!</h1>"
    response += b"<p>You can close this window and return to the terminal.</p>"
    response += b"</body></html>"
    client.send(response)
    client.close()
    server.close()

    # Extract the URL from the request
    get_line = data.split("\n")[0]
    url = get_line.split(" ")[1]
    return f"http://localhost:8080{url}"

def generate_refresh_token():
    """Generate a Reddit refresh token for user authentication"""

    print("=" * 70)
    print("REDDIT REFRESH TOKEN GENERATOR")
    print("=" * 70)
    print("\nThis script will help you generate a refresh token that allows")
    print("FragDropDetector to access Reddit as YOUR account.")
    print("\nThis is necessary to see member-only posts in r/MontagneParfums")
    print("that are not visible to anonymous users.")
    print("\n" + "=" * 70)

    # Load existing credentials
    load_dotenv()
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("\n❌ ERROR: Reddit API credentials not found in .env file")
        print("   Please ensure REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are set")
        return

    print(f"\n✅ Using existing Reddit App credentials")
    print(f"   Client ID: {client_id[:10]}...")

    # Generate state for security
    state = str(random.randint(0, 65000))

    # Define scopes we need
    scopes = ["identity", "read", "history", "mysubreddits", "subscribe"]

    # Create Reddit instance for OAuth
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8080",
        user_agent="FragDropDetector Token Generator"
    )

    # Get authorization URL
    auth_url = reddit.auth.url(scopes, state, "permanent")

    print("\n📋 INSTRUCTIONS:")
    print("1. Your browser will open to Reddit's authorization page")
    print("2. Log in with your Reddit account (if not already)")
    print("3. Click 'Allow' to grant FragDropDetector access")
    print("4. You'll be redirected back here automatically")
    print("\n" + "-" * 70)

    # Open browser
    print(f"\nOpening browser to: {auth_url[:50]}...")
    webbrowser.open(auth_url)

    # Wait for the redirect
    redirect_url = receive_connection()

    # Parse the authorization code
    parsed = urlparse(redirect_url)
    query_params = parse_qs(parsed.query)

    if "error" in query_params:
        print(f"\n❌ Authorization failed: {query_params['error'][0]}")
        return

    if "code" not in query_params:
        print("\n❌ No authorization code received")
        return

    if query_params.get("state", [None])[0] != state:
        print("\n❌ State mismatch - possible security issue")
        return

    auth_code = query_params["code"][0]

    print("\n✅ Authorization code received!")
    print("   Exchanging for refresh token...")

    # Exchange auth code for refresh token
    try:
        refresh_token = reddit.auth.authorize(auth_code)

        print("\n" + "=" * 70)
        print("SUCCESS! Refresh token generated")
        print("=" * 70)

        # Test the token
        print("\n🔍 Testing token access...")
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            user_agent="FragDropDetector/1.0"
        )

        # Get user info
        user = reddit.user.me()
        print(f"✅ Authenticated as: u/{user.name}")
        print(f"   Account karma: {user.link_karma + user.comment_karma:,}")

        # Check if user is subscribed to MontagneParfums
        subscribed = False
        for sub in reddit.user.subreddits(limit=None):
            if sub.display_name.lower() == "montagneparfums":
                subscribed = True
                break

        if subscribed:
            print("✅ Subscribed to r/MontagneParfums")
        else:
            print("⚠️  Not subscribed to r/MontagneParfums")
            print("   Consider subscribing for better access")

        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("\n1. Add this line to your .env file:")
        print(f"\n   REDDIT_REFRESH_TOKEN={refresh_token}")
        print(f"   REDDIT_USERNAME={user.name}")
        print("\n2. The FragDropDetector will now access Reddit as YOU")
        print("3. You'll be able to see the same posts you see in your browser")
        print("\n⚠️  Keep this token SECRET - it provides full access to your account!")

        # Offer to save automatically
        print("\n" + "-" * 70)
        save = input("\nWould you like to automatically update your .env file? (y/n): ")

        if save.lower() == 'y':
            env_path = '.env'

            # Read existing .env
            with open(env_path, 'r') as f:
                lines = f.readlines()

            # Check if refresh token already exists
            token_exists = False
            username_exists = False

            for i, line in enumerate(lines):
                if line.startswith('REDDIT_REFRESH_TOKEN='):
                    lines[i] = f'REDDIT_REFRESH_TOKEN={refresh_token}\n'
                    token_exists = True
                elif line.startswith('REDDIT_USERNAME='):
                    lines[i] = f'REDDIT_USERNAME={user.name}\n'
                    username_exists = True

            # Add if not exists
            if not token_exists:
                # Find where to insert (after other Reddit settings)
                insert_index = len(lines)
                for i, line in enumerate(lines):
                    if 'REDDIT_USER_AGENT' in line:
                        insert_index = i + 1
                        break
                lines.insert(insert_index, f'REDDIT_REFRESH_TOKEN={refresh_token}\n')

            if not username_exists:
                insert_index = len(lines)
                for i, line in enumerate(lines):
                    if 'REDDIT_REFRESH_TOKEN' in line:
                        insert_index = i + 1
                        break
                lines.insert(insert_index, f'REDDIT_USERNAME={user.name}\n')

            # Write back
            with open(env_path, 'w') as f:
                f.writelines(lines)

            print("\n✅ .env file updated successfully!")
            print("   FragDropDetector will now use user authentication")
        else:
            print("\nPlease manually add the refresh token to your .env file")

    except Exception as e:
        print(f"\n❌ Error exchanging code for token: {e}")
        return

if __name__ == "__main__":
    generate_refresh_token()