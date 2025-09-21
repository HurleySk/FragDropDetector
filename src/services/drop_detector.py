"""
Drop detection engine for identifying fragrance drops in Reddit posts
"""

import re
import logging
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DropDetector:
    """Detects potential fragrance drops from Reddit posts"""

    def __init__(self):
        """Initialize the drop detector with keywords and patterns"""

        # Primary keywords that strongly indicate a drop
        self.primary_keywords = [
            'restock',  # Most common!
            'restocked', 'restocking',
            'drop', 'dropped', 'dropping', 'drops',
            'release', 'released', 'releasing',
            'available', 'availability',
            'launch', 'launched', 'launching',
            'in stock', 'back in stock',
            'now live', 'live now',
            'new fragrance', 'new perfume',
            'new cologne', 'new scent'
        ]

        # Secondary keywords that support drop detection
        self.secondary_keywords = [
            'limited', 'exclusive', 'special',
            'pre-order', 'preorder',
            'sale', 'discount',
            'batch', 'decant',
            'split', 'sample',
            'bottle', 'ml',
            'price', 'pricing',
            'order', 'ordering',
            'link', 'website'
        ]

        # Known vendor/brand patterns
        self.vendor_patterns = [
            r'montagne\s*parfums',
            r'montagne\s*family',  # Common greeting in posts
            r'montagne',
            r'MP\b',
            r'official',
            r'announcement'
        ]

        # Time patterns that indicate drops
        self.time_patterns = [
            r'\d{1,2}\s*pm\s*est',  # "5pm EST", "5 PM EST"
            r'\d{1,2}\s*pm\s*et',   # Eastern Time variants
            r'today\s*@',            # "today @"
            r'today\s*at',           # "today at"
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # Date format MM/DD/YY
        ]

        # Known restock authors (high confidence)
        self.trusted_authors = [
            'ayybrahamlmaocoln',
            'wide_parsley1799',
            'montagneparfums',  # Official account if exists
            'mpofficial'
        ]

        # Exclusion patterns (false positives)
        self.exclusion_patterns = [
            r'looking\s+for',
            r'where\s+to\s+buy',
            r'anyone\s+have',
            r'wtb',  # want to buy
            r'wts',  # want to sell (individual sales, not official)
            r'iso',  # in search of
            r'recommendation',
            r'review',
            r'thoughts\s+on',
            r'\[wtb\]',
            r'\[wts\]'  # Exclude personal sales
        ]

    def detect_drop(self, post: Dict) -> Tuple[bool, float, Dict]:
        """
        Analyze a post to determine if it's a fragrance drop

        Args:
            post: Post dictionary from Reddit client

        Returns:
            Tuple of (is_drop, confidence_score, metadata)
        """
        title = post.get('title', '').lower()
        text = post.get('selftext', '').lower()
        author = post.get('author', '').lower()
        flair = (post.get('link_flair_text') or '').lower()

        # Combine all text for analysis
        full_text = f"{title} {text} {flair}"

        # Check for exclusion patterns first
        if self._has_exclusion_patterns(full_text):
            logger.debug(f"Post excluded due to exclusion patterns: {title[:50]}")
            return False, 0.0, {'reason': 'exclusion_pattern'}

        # Calculate confidence score
        score = 0.0
        metadata = {
            'primary_matches': [],
            'secondary_matches': [],
            'vendor_match': False,
            'author_reputation': False,
            'time_match': False,
            'flair_match': None
        }

        # HIGHEST PRIORITY: Check if author is trusted
        if author in self.trusted_authors:
            score += 0.6  # Very high confidence for trusted authors
            metadata['author_reputation'] = True
            metadata['trusted_author'] = author

        # Check for 'restock' in title (extremely strong signal)
        if 'restock' in title:
            score += 0.5
            metadata['primary_matches'].append('RESTOCK IN TITLE')

        # Check for time patterns (strong signal for drops)
        if self._has_time_patterns(full_text):
            score += 0.3
            metadata['time_match'] = True

        # Check primary keywords (high weight)
        primary_matches = self._find_keyword_matches(full_text, self.primary_keywords)
        if primary_matches:
            score += 0.2 * min(len(primary_matches), 3)  # Reduced weight since we check restock separately
            metadata['primary_matches'].extend(primary_matches)

        # Check secondary keywords (lower weight)
        secondary_matches = self._find_keyword_matches(full_text, self.secondary_keywords)
        if secondary_matches:
            score += 0.1 * min(len(secondary_matches), 5)  # Cap at 5 matches
            metadata['secondary_matches'] = secondary_matches

        # Check vendor patterns
        if self._has_vendor_patterns(full_text):
            score += 0.3
            metadata['vendor_match'] = True

        # Additional vendor check if not already caught by trusted authors
        if not metadata['author_reputation'] and self._is_known_vendor(author):
            score += 0.2
            metadata['author_reputation'] = True

        # Check for flair indicators (especially ⭐️RESTOCK⭐️)
        if flair:
            if 'restock' in flair:
                score += 0.4  # High weight for restock flair
                metadata['flair_match'] = flair
            elif any(word in flair for word in ['drop', 'release', 'news', 'announcement']):
                score += 0.2
                metadata['flair_match'] = flair

        # Check for links (drops often include purchase links)
        if self._has_purchase_links(text):
            score += 0.1
            metadata['has_links'] = True

        # Normalize score to 0-1 range
        confidence = min(score, 1.0)

        # Determine if it's a drop (threshold of 0.4)
        is_drop = confidence >= 0.4

        if is_drop:
            logger.info(f"Drop detected: {title[:50]}... (confidence: {confidence:.2f})")
        else:
            logger.debug(f"Not a drop: {title[:50]}... (confidence: {confidence:.2f})")

        return is_drop, confidence, metadata

    def _find_keyword_matches(self, text: str, keywords: List[str]) -> List[str]:
        """Find which keywords are present in the text"""
        matches = []
        for keyword in keywords:
            if keyword in text:
                matches.append(keyword)
        return matches

    def _has_exclusion_patterns(self, text: str) -> bool:
        """Check if text contains exclusion patterns"""
        for pattern in self.exclusion_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_vendor_patterns(self, text: str) -> bool:
        """Check if text contains vendor patterns"""
        for pattern in self.vendor_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_time_patterns(self, text: str) -> bool:
        """Check if text contains time-related patterns for drops"""
        for pattern in self.time_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _is_known_vendor(self, author: str) -> bool:
        """Check if author is a known vendor account"""
        # This is now mostly handled by trusted_authors
        # Keep this for backward compatibility
        return author in self.trusted_authors

    def _has_purchase_links(self, text: str) -> bool:
        """Check if text contains purchase-related links"""
        link_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
            r'\[.*\]\(.*\)',  # Reddit markdown links
        ]
        for pattern in link_patterns:
            if re.search(pattern, text):
                return True
        return False

    def batch_detect(self, posts: List[Dict]) -> List[Dict]:
        """
        Process multiple posts and return drop candidates

        Args:
            posts: List of post dictionaries

        Returns:
            List of posts identified as drops with metadata
        """
        drops = []

        for post in posts:
            is_drop, confidence, metadata = self.detect_drop(post)

            if is_drop:
                drop_info = {
                    **post,
                    'is_drop': True,
                    'confidence': confidence,
                    'detection_metadata': metadata,
                    'detected_at': datetime.utcnow().isoformat()
                }
                drops.append(drop_info)

        logger.info(f"Detected {len(drops)} drops out of {len(posts)} posts")
        return drops

    def get_drop_summary(self, drop: Dict) -> str:
        """
        Generate a summary of a detected drop for notifications

        Args:
            drop: Drop dictionary with detection metadata

        Returns:
            Formatted summary string
        """
        title = drop.get('title', 'Unknown')
        author = drop.get('author', 'Unknown')
        confidence = drop.get('confidence', 0)
        url = drop.get('url', '')

        metadata = drop.get('detection_metadata', {})
        primary = metadata.get('primary_matches', [])

        summary = f"**{title}**\n"
        summary += f"Author: {author}\n"
        summary += f"Confidence: {confidence:.0%}\n"

        if primary:
            summary += f"Keywords: {', '.join(primary[:3])}\n"

        if url:
            summary += f"Link: {url}"

        return summary