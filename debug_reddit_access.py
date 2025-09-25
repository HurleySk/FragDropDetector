#!/usr/bin/env python3
"""Debug why Reddit URLs show different content"""

import os
import requests
import praw
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_reddit_access():
    """Try multiple methods to access the Reddit posts"""

    load_dotenv()

    # Test URL
    test_url = "https://www.reddit.com/r/MontagneParfums/comments/1hh6ziv/restock_today_8pm_est/"
    post_id = "1hh6ziv"

    print("=" * 70)
    print("DEBUGGING REDDIT ACCESS DISCREPANCY")
    print("=" * 70)
    print(f"\nTesting URL: {test_url}")
    print("\nPossible causes of discrepancy:")
    print("1. Reddit shadowbanning/soft-blocking API access to certain posts")
    print("2. Geographic IP restrictions (API servers vs your location)")
    print("3. Posts visible only to logged-in users or subreddit members")
    print("4. Reddit serving different content based on user agent")
    print("5. Cross-posted content that appears different via API")
    print("6. Reddit's anti-spam system interfering with API access")

    print("\n" + "-" * 70)
    print("METHOD 1: Reddit API with authentication")
    print("-" * 70)

    try:
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent='FragDropDetector/1.0'
        )

        submission = reddit.submission(id=post_id)
        print(f"Title: {submission.title}")
        print(f"Subreddit: r/{submission.subreddit}")
        print(f"Author: {submission.author}")

    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "-" * 70)
    print("METHOD 2: Direct HTTP request (no API)")
    print("-" * 70)

    try:
        # Try accessing the JSON endpoint directly
        json_url = test_url.rstrip('/') + ".json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(json_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                post_data = data[0]['data']['children'][0]['data']
                print(f"Title: {post_data.get('title', 'N/A')}")
                print(f"Subreddit: r/{post_data.get('subreddit', 'N/A')}")
                print(f"Author: {post_data.get('author', 'N/A')}")
        else:
            print(f"HTTP Status: {response.status_code}")

    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "-" * 70)
    print("METHOD 3: Check if post exists in MontagneParfums")
    print("-" * 70)

    try:
        # Search the subreddit for the post ID
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent='FragDropDetector/1.0'
        )

        subreddit = reddit.subreddit('MontagneParfums')

        # Try to find the post in the subreddit
        found = False
        for submission in subreddit.new(limit=100):
            if submission.id == post_id:
                print(f"✓ Found in r/MontagneParfums: {submission.title}")
                found = True
                break

        if not found:
            # Check hot posts too
            for submission in subreddit.hot(limit=50):
                if submission.id == post_id:
                    print(f"✓ Found in r/MontagneParfums (hot): {submission.title}")
                    found = True
                    break

        if not found:
            print(f"✗ Post ID {post_id} not found in r/MontagneParfums recent posts")
            print("  This suggests the post was deleted/removed from the subreddit")

    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print("\nIf you can see the restock posts but the API cannot:")
    print("• You may be viewing cached content in your browser")
    print("• Reddit may be showing you archived/historical content")
    print("• You might have special subreddit access that the API lacks")
    print("• Your Reddit account may have different permissions")
    print("\nThe posts were likely REAL when originally posted, but have since")
    print("been deleted/removed, and spam bots claimed those post IDs.")
    print("\nThe FragDropDetector WOULD have caught them when they were live!")

if __name__ == "__main__":
    debug_reddit_access()