"""
Reddit client for monitoring r/MontagneParfums subreddit
"""

import praw
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)


class RedditClient:
    """Client for interacting with Reddit API using PRAW"""

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """
        Initialize Reddit client

        Args:
            client_id: Reddit app client ID
            client_secret: Reddit app client secret
            user_agent: User agent string for Reddit API
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        self.reddit.read_only = True
        logger.info(f"Reddit client initialized with user agent: {user_agent}")

    def get_subreddit_posts(
        self,
        subreddit_name: str,
        limit: int = 25,
        time_filter: str = 'hour'
    ) -> List[Dict]:
        """
        Fetch recent posts from a subreddit

        Args:
            subreddit_name: Name of the subreddit (without r/)
            limit: Maximum number of posts to fetch
            time_filter: Time filter for top posts (hour, day, week, etc.)

        Returns:
            List of post dictionaries
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []

            # Get new posts
            for submission in subreddit.new(limit=limit):
                post_data = self._extract_post_data(submission)
                posts.append(post_data)
                logger.debug(f"Fetched post: {post_data['title'][:50]}...")

            # Also check hot posts for pinned/important drops
            for submission in subreddit.hot(limit=10):
                if submission.id not in [p['id'] for p in posts]:
                    post_data = self._extract_post_data(submission)
                    posts.append(post_data)

            logger.info(f"Fetched {len(posts)} posts from r/{subreddit_name}")
            return posts

        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit_name}: {e}")
            raise

    def get_posts_since(
        self,
        subreddit_name: str,
        since_timestamp: float,
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch posts created after a specific timestamp

        Args:
            subreddit_name: Name of the subreddit
            since_timestamp: Unix timestamp to fetch posts after
            limit: Maximum number of posts to check

        Returns:
            List of new posts since timestamp
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            new_posts = []

            for submission in subreddit.new(limit=limit):
                if submission.created_utc > since_timestamp:
                    post_data = self._extract_post_data(submission)
                    new_posts.append(post_data)
                else:
                    # Posts are in reverse chronological order
                    break

            logger.info(f"Found {len(new_posts)} new posts since {datetime.fromtimestamp(since_timestamp)}")
            return new_posts

        except Exception as e:
            logger.error(f"Error fetching posts since timestamp: {e}")
            raise

    def _extract_post_data(self, submission) -> Dict:
        """
        Extract relevant data from a Reddit submission

        Args:
            submission: PRAW submission object

        Returns:
            Dictionary with post data
        """
        return {
            'id': submission.id,
            'title': submission.title,
            'author': str(submission.author) if submission.author else '[deleted]',
            'created_utc': submission.created_utc,
            'url': f"https://reddit.com{submission.permalink}",
            'selftext': submission.selftext,
            'link_flair_text': submission.link_flair_text,
            'score': submission.score,
            'num_comments': submission.num_comments,
            'stickied': submission.stickied,
            'is_self': submission.is_self,
            'domain': submission.domain if hasattr(submission, 'domain') else None,
            'created_datetime': datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
        }

    def test_connection(self) -> bool:
        """
        Test Reddit API connection

        Returns:
            True if connection successful
        """
        try:
            # Try to access the subreddit
            subreddit = self.reddit.subreddit('MontagneParfums')
            _ = subreddit.display_name
            logger.info("Reddit API connection test successful")
            return True
        except Exception as e:
            logger.error(f"Reddit API connection test failed: {e}")
            return False

    def get_user_posts(self, username: str, limit: int = 10) -> List[Dict]:
        """
        Get recent posts from a specific user

        Args:
            username: Reddit username
            limit: Number of posts to fetch

        Returns:
            List of user's posts
        """
        try:
            user = self.reddit.redditor(username)
            posts = []

            for submission in user.submissions.new(limit=limit):
                if submission.subreddit.display_name.lower() == 'montagneparfums':
                    post_data = self._extract_post_data(submission)
                    posts.append(post_data)

            logger.info(f"Fetched {len(posts)} posts from user {username}")
            return posts

        except Exception as e:
            logger.error(f"Error fetching posts from user {username}: {e}")
            return []