#!/usr/bin/env python3
"""
Fixed Reddit refresh token generator via SSH tunnel
Handles common redirect issues
"""

import os
import sys
import praw
import random
import socket
import subprocess
import signal
import select
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv


def timeout_handler(signum, frame):
    raise TimeoutError("Timed out waiting for Reddit redirect")


def is_ssh_session():
    """Check if running in an SSH session"""
    return 'SSH_CONNECTION' in os.environ or 'SSH_CLIENT' in os.environ


def get_ssh_client_ip():
    """Get the IP address of the SSH client"""
    ssh_connection = os.environ.get('SSH_CONNECTION', '')
    if ssh_connection:
        return ssh_connection.split()[0]
    return None


def test_port_8080():
    """Test if port 8080 is available"""
    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        test_socket.bind(("localhost", 8080))
        test_socket.close()
        return True
    except OSError:
        return False


def receive_connection_with_timeout(timeout=120):
    """Wait for redirect with timeout and better error handling"""

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("localhost", 8080))
    server.listen(1)
    server.setblocking(False)  # Non-blocking mode

    print("\nWaiting for Reddit authorization...")
    print(f"Timeout in {timeout} seconds...")
    print("\nTROUBLESHOOTING:")
    print("- If this hangs, the redirect isn't reaching the Pi")
    print("- Make sure you're using SSH with: ssh -L 8080:localhost:8080 pi@IP")
    print("- After clicking Allow, check the URL bar - does it say localhost:8080?")
    print("\nPress Ctrl+C to cancel if stuck\n")

    start_time = os.times()[4]

    while True:
        # Check timeout
        elapsed = os.times()[4] - start_time
        if elapsed > timeout:
            server.close()
            raise TimeoutError("Timed out waiting for Reddit redirect")

        # Use select to wait for connection with timeout
        ready = select.select([server], [], [], 1.0)

        if ready[0]:
            try:
                client, addr = server.accept()
                print(f"Connection received from {addr}")

                # Receive data
                data = client.recv(4096).decode("utf-8")

                # Send response immediately
                response = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
                response += b"""<html>
<head>
<title>Success</title>
<style>
body { font-family: sans-serif; text-align: center; padding: 50px; }
h1 { color: #00AA00; }
</style>
</head>
<body>
<h1>Success!</h1>
<p>Authorization received. You can close this window.</p>
<p>Return to your terminal to complete the setup.</p>
</body>
</html>"""
                client.send(response)
                client.close()
                server.close()

                # Extract URL from request
                if data:
                    lines = data.split("\n")
                    if lines:
                        get_line = lines[0]
                        parts = get_line.split(" ")
                        if len(parts) >= 2:
                            url = parts[1]
                            return f"http://localhost:8080{url}"

                return None

            except socket.error:
                continue

        # Show progress
        remaining = int(timeout - elapsed)
        if remaining % 10 == 0:
            print(f"  ... still waiting ({remaining}s remaining)")


def generate_ssh_token():
    """Generate Reddit token via SSH tunnel"""

    print("=" * 70)
    print("REDDIT TOKEN GENERATOR - SSH Tunnel Method (Fixed)")
    print("=" * 70)

    # Check port availability
    if not test_port_8080():
        print("\nERROR: Port 8080 is already in use!")
        print("Kill the process using: lsof -i :8080")
        print("Then: kill -9 <PID>")
        return

    # Check SSH session
    is_ssh = is_ssh_session()
    ssh_client_ip = get_ssh_client_ip()

    if not is_ssh:
        print("\nWARNING: Not running in SSH session")
        print("This script works best via SSH with port forwarding")
        print("\nFrom your computer, connect with:")
        print(f"  ssh -L 8080:localhost:8080 pi@YOUR_PI_IP")
    elif is_ssh:
        print(f"\nSSH session detected from: {ssh_client_ip}")
        print("\nMAKE SURE you connected with port forwarding:")
        print(f"  ssh -L 8080:localhost:8080 pi@YOUR_PI_IP")
        print("\nIf you didn't use -L flag, this won't work!")

    print("\n" + "-" * 70)

    load_dotenv()
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("\nERROR: Reddit API credentials not found in .env")
        return

    print(f"\nUsing Reddit App: {client_id[:10]}...")

    # Generate OAuth URL
    state = str(random.randint(0, 65000))
    scopes = ["identity", "read", "history", "mysubreddits", "subscribe"]

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8080",
        user_agent="FragDropDetector Token Generator"
    )

    auth_url = reddit.auth.url(scopes, state, "permanent")

    print("\n" + "=" * 70)
    print("INSTRUCTIONS")
    print("=" * 70)
    print("\n1. Copy this ENTIRE URL:")
    print(f"\n{auth_url}\n")
    print("2. Paste it in YOUR LOCAL browser (on your computer, not Pi)")
    print("3. Log into Reddit and click 'Allow'")
    print("4. You should be redirected automatically")
    print("\nIf you see an error page after clicking Allow:")
    print("  - Your SSH tunnel isn't set up correctly")
    print("  - Reconnect with: ssh -L 8080:localhost:8080 pi@IP")
    print("-" * 70)

    try:
        redirect_url = receive_connection_with_timeout(120)
    except TimeoutError:
        print("\n" + "=" * 70)
        print("TIMEOUT - No redirect received")
        print("=" * 70)
        print("\nCommon causes:")
        print("1. SSH tunnel not set up (missing -L flag)")
        print("2. Browser couldn't connect to localhost:8080")
        print("3. You closed the browser before completing auth")
        print("\nTry again with proper SSH tunnel:")
        print(f"  ssh -L 8080:localhost:8080 pi@{get_ssh_client_ip() or 'YOUR_PI_IP'}")
        return
    except KeyboardInterrupt:
        print("\nCancelled by user")
        return

    if not redirect_url:
        print("\nNo redirect URL received")
        return

    # Parse the redirect
    parsed = urlparse(redirect_url)
    query_params = parse_qs(parsed.query)

    if "error" in query_params:
        print(f"\nAuthorization failed: {query_params['error'][0]}")
        return

    if "code" not in query_params:
        print("\nNo authorization code in redirect")
        print("Redirect URL:", redirect_url)
        return

    auth_code = query_params["code"][0]
    print("\nAuthorization code received!")
    print("Exchanging for refresh token...")

    try:
        refresh_token = reddit.auth.authorize(auth_code)

        print("\n" + "=" * 70)
        print("SUCCESS! Refresh token generated")
        print("=" * 70)

        # Test the token
        reddit_test = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            user_agent="FragDropDetector/1.0"
        )

        user = reddit_test.user.me()
        print(f"\nAuthenticated as: u/{user.name}")

        # Check subscription
        subscribed = False
        for sub in reddit_test.user.subreddits(limit=None):
            if sub.display_name.lower() == "montagneparfums":
                subscribed = True
                break

        if subscribed:
            print("Subscribed to r/MontagneParfums")

        print("\n" + "=" * 70)
        print("Token ready to save:")
        print(f"  REDDIT_REFRESH_TOKEN={refresh_token}")
        print(f"  REDDIT_USERNAME={user.name}")
        print("=" * 70)

        save = input("\nSave to .env? (y/n): ")
        if save.lower() == 'y':
            # Read and update .env
            with open('.env', 'r') as f:
                lines = f.readlines()

            token_exists = False
            username_exists = False

            for i, line in enumerate(lines):
                if line.startswith('REDDIT_REFRESH_TOKEN='):
                    lines[i] = f'REDDIT_REFRESH_TOKEN={refresh_token}\n'
                    token_exists = True
                elif line.startswith('REDDIT_USERNAME='):
                    lines[i] = f'REDDIT_USERNAME={user.name}\n'
                    username_exists = True

            # CRITICAL FIX: Ensure last line has a newline before appending
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'

            if not token_exists:
                lines.append(f'REDDIT_REFRESH_TOKEN={refresh_token}\n')
            if not username_exists:
                lines.append(f'REDDIT_USERNAME={user.name}\n')

            with open('.env', 'w') as f:
                f.writelines(lines)

            print("\n.env updated successfully!")
            print("FragDropDetector will now use user authentication")

    except Exception as e:
        print(f"\nError exchanging code: {e}")
        print("\nThis might happen if:")
        print("- The code expired (try again quickly)")
        print("- Client ID/Secret mismatch")


if __name__ == "__main__":
    generate_ssh_token()