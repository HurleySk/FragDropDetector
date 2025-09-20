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
            'drop', 'dropped', 'dropping', 'drops',
            'release', 'released', 'releasing',
            'available', 'availability',
            'launch', 'launched', 'launching',
            'restock', 'restocked', 'restocking',
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
            r'montagne',
            r'MP\b',
            r'official',
            r'announcement'
        ]

        # Exclusion patterns (false positives)
        self.exclusion_patterns = [
            r'looking\s+for',
            r'where\s+to\s+buy',
            r'anyone\s+have',
            r'wtb',  # want to buy
            r'iso',  # in search of
            r'recommendation',
            r'review',
            r'thoughts\s+on'
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
            'author_reputation': False
        }

        # Check primary keywords (high weight)
        primary_matches = self._find_keyword_matches(full_text, self.primary_keywords)
        if primary_matches:
            score += 0.5 * min(len(primary_matches), 3)  # Cap at 3 matches
            metadata['primary_matches'] = primary_matches

        # Check secondary keywords (lower weight)
        secondary_matches = self._find_keyword_matches(full_text, self.secondary_keywords)
        if secondary_matches:
            score += 0.1 * min(len(secondary_matches), 5)  # Cap at 5 matches
            metadata['secondary_matches'] = secondary_matches

        # Check vendor patterns
        if self._has_vendor_patterns(full_text):
            score += 0.3
            metadata['vendor_match'] = True

        # Check if author is a known vendor (you can expand this)
        if self._is_known_vendor(author):
            score += 0.2
            metadata['author_reputation'] = True

        # Check for flair indicators
        if flair and any(word in flair for word in ['drop', 'release', 'news', 'announcement']):
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

    def _is_known_vendor(self, author: str) -> bool:
        """Check if author is a known vendor account"""
        known_vendors = [
            'montagneparfums',
            'montagne_parfums',
            # Add more known vendor accounts as discovered
        ]
        return author in known_vendors

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