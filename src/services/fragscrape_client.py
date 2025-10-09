"""
fragscrape API Client
Wraps the fragscrape API for fetching Parfumo data
"""

import logging
import requests
import re
from typing import Optional, Dict, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when fragscrape API returns 429 (rate limited)"""
    def __init__(self, message: str = "Rate limited by fragscrape API", retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message)


class FragscrapeClient:
    """Client for fragscrape API"""

    def __init__(self, base_url: str = "http://localhost:3000"):
        """
        Initialize fragscrape client

        Args:
            base_url: Base URL of fragscrape API (default: http://localhost:3000)
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.timeout = 30

        # Rate limit tracking from X-RateLimit headers
        self.rate_limit_max: Optional[int] = None
        self.rate_limit_remaining: Optional[int] = None
        self.rate_limit_reset: Optional[int] = None  # Unix timestamp

    def _parse_rate_limit_headers(self, response: requests.Response) -> None:
        """Extract rate limit info from response headers"""
        try:
            if 'X-RateLimit-Limit' in response.headers:
                self.rate_limit_max = int(response.headers['X-RateLimit-Limit'])
            if 'X-RateLimit-Remaining' in response.headers:
                self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
            if 'X-RateLimit-Reset' in response.headers:
                self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])

            if self.rate_limit_remaining is not None and self.rate_limit_remaining < 10:
                logger.warning(f"fragscrape rate limit low: {self.rate_limit_remaining}/{self.rate_limit_max} remaining")
        except (ValueError, KeyError) as e:
            logger.debug(f"Error parsing rate limit headers: {e}")

    def get_recommended_delay(self, configured_delay: float = 2.0) -> float:
        """
        Calculate recommended delay based on current rate limit status

        Args:
            configured_delay: Configured minimum delay (fallback)

        Returns:
            Recommended delay in seconds
        """
        if self.rate_limit_remaining and self.rate_limit_reset:
            seconds_until_reset = max(self.rate_limit_reset - time.time(), 0)

            if seconds_until_reset > 0 and self.rate_limit_remaining > 0:
                # Calculate optimal delay with 10% safety buffer
                optimal_delay = (seconds_until_reset / self.rate_limit_remaining) * 1.1
                # Use configured delay as minimum
                return max(optimal_delay, configured_delay, 0.5)

        # Fallback to configured delay
        return configured_delay

    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status for monitoring"""
        status = {
            'limit': self.rate_limit_max,
            'remaining': self.rate_limit_remaining,
            'reset': self.rate_limit_reset
        }

        if self.rate_limit_reset:
            status['reset_in_seconds'] = max(int(self.rate_limit_reset - time.time()), 0)

        return status

    def should_throttle(self, threshold: int = 10) -> bool:
        """
        Check if we should preemptively throttle to avoid hitting rate limit

        Args:
            threshold: Number of requests remaining to trigger throttle

        Returns:
            True if should pause and wait for reset
        """
        if self.rate_limit_remaining is not None:
            return self.rate_limit_remaining < threshold
        return False

    def health_check(self) -> bool:
        """
        Check if fragscrape API is available and healthy

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Use proxy status endpoint for health check
            response = self.session.get(
                f"{self.base_url}/api/proxy/status",
                timeout=5
            )

            # Parse rate limit headers
            self._parse_rate_limit_headers(response)

            # 429 means rate limited but API is running
            if response.status_code == 429:
                return True

            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check for successful response
                    if isinstance(data, dict) and data.get('success') is True:
                        return True
                    # If success is False, check for critical errors
                    if isinstance(data, dict) and data.get('success') is False:
                        error_msg = data.get('error', '')
                        if 'Chrome' in error_msg or 'puppeteer' in error_msg:
                            logger.warning(f"fragscrape API is running but not fully configured: {error_msg}")
                        return False
                except ValueError:
                    pass

            return False

        except requests.exceptions.RequestException as e:
            logger.debug(f"fragscrape health check failed: {e}")
            return False

    def _normalize_brand_name(self, brand: str) -> str:
        """
        Normalize brand name for better search matching

        Examples:
        - "By Kilian" → "Kilian"
        - "Bond No. 9" → "Bond No 9"
        - "Marc-Antoine Barrois" → "Marc Antoine Barrois"
        """
        normalized = brand

        # Remove "By " prefix
        if normalized.lower().startswith('by '):
            normalized = normalized[3:].strip()

        # Remove dots (Bond No. 9 → Bond No 9)
        normalized = normalized.replace('.', '')

        # Replace hyphens with spaces in brand names
        normalized = normalized.replace('-', ' ')

        return normalized.strip()

    def _normalize_fragrance_name(self, name: str) -> str:
        """
        Normalize fragrance name by removing common modifiers

        Examples:
        - "Ganymede Edp" → "Ganymede"
        - "Elysium Parfum Cologne" → "Elysium"
        - "Antoine Barrois Ganymede Edp" → "Ganymede"
        """
        normalized = name

        # Remove common suffixes (case insensitive) - but be conservative
        # Only remove clear concentration descriptors, not parts of compound names
        suffixes_to_remove = [
            'eau de parfum', 'eau de toilette', 'eau de cologne',
            'pure perfume', 'extrait'
        ]

        for suffix in suffixes_to_remove:
            # Remove from end
            pattern = r'\s+' + suffix + r'$'
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

        # Don't remove "edp", "edt", "parfum", "cologne", "city", "city exclusive", "intense", "absolu"
        # as these might be part of the actual fragrance name (e.g., "Elysium Parfum Cologne", "City Exclusive")

        # Brand name repetitions should already be handled in extraction phase
        # Don't try to guess here as it removes important words (e.g., "Gaiac 10 Tokyo City" → "Tokyo City" losing "Gaiac")

        return normalized.strip()

    def search_perfume(self, brand: str, name: str, limit: int = 5) -> Optional[str]:
        """
        Search for a perfume and return its Parfumo URL
        Uses multiple search strategies for better matching

        Args:
            brand: Brand name
            name: Perfume name
            limit: Number of results to return (default: 5)

        Returns:
            Full Parfumo URL or None if not found
        """
        # Try multiple search strategies
        normalized_brand = self._normalize_brand_name(brand)
        normalized_name = self._normalize_fragrance_name(name)

        # Additional variations for better matching
        name_no_apostrophe = name.replace("'", "").replace("'", "")
        name_no_numbers = re.sub(r'\b\d{4}\b', '', name).strip()  # Remove years like "2011"
        name_no_numbers_all = re.sub(r'\d+', '', name).strip()  # Remove all numbers

        # Remove concentration descriptors from end
        name_no_concentration = re.sub(r'\s+(edp|edt|parfum|cologne|extrait)$', '', name, flags=re.IGNORECASE).strip()

        # Try singular/plural variants
        name_singular = re.sub(r'\s+men$', ' man', name, flags=re.IGNORECASE).strip()

        # Combine removals
        name_clean = re.sub(r'\s+(edp|edt|parfum|cologne|extrait|city|exclusive)$', '', name, flags=re.IGNORECASE).strip()
        name_clean = re.sub(r'\b\d+\b', '', name_clean).strip()  # Also remove numbers

        search_strategies = [
            (f"{brand} {name}", brand),  # Original
            (f"{normalized_brand} {name}", normalized_brand),  # Normalized brand
            (f"{brand} {name_no_concentration}", brand),  # Without EDP/EDT/Parfum/Cologne
            (f"{normalized_brand} {name_no_concentration}", normalized_brand),  # Normalized + no concentration
            (f"{brand} {name_singular}", brand),  # Try singular (Men → Man)
            (f"{normalized_brand} {name_singular}", normalized_brand),  # Normalized + singular
            (f"{brand} {name_clean}", brand),  # Clean: no concentration, numbers, city
            (f"{normalized_brand} {name_clean}", normalized_brand),  # Normalized + clean
            (f"{normalized_brand} {normalized_name}", normalized_brand),  # Fully normalized
            (f"{brand} {normalized_name}", brand),  # Normalized name only
            (f"{brand} {name_no_apostrophe}", brand),  # Without apostrophes
            (f"{normalized_brand} {name_no_apostrophe}", normalized_brand),  # Normalized brand, no apostrophe
            (f"{brand} {name_no_numbers}", brand),  # Without years
            (f"{brand} {name_no_numbers_all}", brand),  # Without any numbers
            (normalized_name, None),  # Just normalized name as fallback
            (name, None),  # Just original name
            (name_no_apostrophe, None),  # Just name without apostrophes
            (name_clean, None)  # Just clean name
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_strategies = []
        for query, expected_brand in search_strategies:
            query_key = (query.strip().lower(), expected_brand)
            if query_key not in seen and query.strip():
                seen.add(query_key)
                unique_strategies.append((query.strip(), expected_brand))

        search_strategies = unique_strategies

        for query, expected_brand in search_strategies:
            try:
                query = query.strip()
                logger.info(f"Searching fragscrape for: {query}")

                response = self.session.get(
                    f"{self.base_url}/api/search",
                    params={'q': query, 'limit': limit, 'cache': 'true'},
                    timeout=self.timeout
                )

                # Parse rate limit headers
                self._parse_rate_limit_headers(response)

                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    retry_after_seconds = int(retry_after) if retry_after else None
                    logger.warning(f"Rate limited by fragscrape API during search (retry after: {retry_after_seconds}s)")
                    raise RateLimitError(retry_after=retry_after_seconds)

                if response.status_code != 200:
                    logger.warning(f"Search request failed with status {response.status_code}")
                    continue  # Try next strategy

                data = response.json()

                # Handle error responses
                if isinstance(data, dict) and not data.get('success', True):
                    error_msg = data.get('error', 'Unknown error')
                    logger.error(f"fragscrape search error: {error_msg}")
                    continue  # Try next strategy

                # Extract results - handle different possible response formats
                results = []
                if isinstance(data, dict):
                    results = data.get('results', data.get('data', []))
                elif isinstance(data, list):
                    results = data

                if not results:
                    logger.info(f"No results found for: {query}")
                    continue  # Try next strategy

                # Try to find best match based on brand name
                best_match = None

                if expected_brand:
                    brand_lower = expected_brand.lower()
                    for result in results:
                        result_brand = result.get('brand', '').lower()
                        if brand_lower in result_brand or result_brand in brand_lower:
                            best_match = result
                            break

                # If no brand match, use first result
                if not best_match:
                    best_match = results[0]
                    logger.debug(f"No exact brand match, using first result")

                # Extract the full Parfumo URL
                parfumo_url = best_match.get('url', '')

                if parfumo_url:
                    logger.info(f"Found Parfumo match: {parfumo_url} (strategy: {query})")
                    return parfumo_url

            except RateLimitError:
                raise  # Re-raise rate limit errors
            except requests.exceptions.RequestException as e:
                logger.error(f"Error searching fragscrape: {e}")
                continue  # Try next strategy
            except Exception as e:
                logger.error(f"Unexpected error in fragscrape search: {e}")
                continue  # Try next strategy

        # All strategies failed
        logger.warning(f"Could not find match for: {brand} {name}")
        return None

    def get_perfume_details(self, brand: str, name: str, year: Optional[str] = None) -> Optional[Dict]:
        """
        Get detailed perfume information including rating

        Args:
            brand: Brand name
            name: Perfume name
            year: Optional year variant

        Returns:
            Dictionary with perfume details or None if not found
        """
        try:
            url = f"{self.base_url}/api/perfume/{brand}/{name}"
            params = {'cache': 'true'}
            if year:
                params['year'] = year

            logger.info(f"Fetching perfume details from fragscrape: {brand}/{name}")

            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                logger.warning(f"Perfume not found: {brand}/{name}")
                return None

            if response.status_code != 200:
                logger.warning(f"Request failed with status {response.status_code}")
                return None

            data = response.json()

            # Handle error responses
            if isinstance(data, dict) and not data.get('success', True):
                error_msg = data.get('error', 'Unknown error')
                logger.error(f"fragscrape error: {error_msg}")
                return None

            # Extract the perfume data
            perfume_data = data if not isinstance(data, dict) or 'data' not in data else data.get('data', {})

            # Map to our internal format
            result = self._map_perfume_response(perfume_data, brand, name)

            if result and result.get('score'):
                logger.info(f"Fetched rating: {result.get('score', 'N/A')} for {brand}/{name}")
                return result

            logger.warning(f"No rating data found for {brand}/{name}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching perfume details: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching perfume details: {e}")
            return None

    def fetch_rating(self, parfumo_url: str) -> Optional[Dict]:
        """
        Fetch rating for a fragrance using its Parfumo URL

        Args:
            parfumo_url: Full Parfumo URL (e.g., https://www.parfumo.com/Perfumes/Creed/aventus)

        Returns:
            Rating data dictionary or None if not found
        """
        if not parfumo_url:
            return None

        # All parfumo_ids are now URLs after migration
        return self.fetch_rating_by_url(parfumo_url)

    def fetch_rating_by_url(self, url: str) -> Optional[Dict]:
        """
        Fetch rating for a fragrance using its Parfumo URL

        Args:
            url: Full Parfumo URL (e.g., https://www.parfumo.com/Perfumes/Creed/aventus)

        Returns:
            Rating data dictionary or None if not found
        """
        if not url:
            return None

        try:
            logger.info(f"Fetching perfume details by URL: {url}")

            # Always use fresh data (cache=false) to avoid stale ratings
            # fragscrape's cache can have outdated scores/votes
            response = self.session.post(
                f"{self.base_url}/api/perfume/by-url",
                json={'url': url},
                params={'cache': 'false'},
                timeout=self.timeout
            )

            # Parse rate limit headers
            self._parse_rate_limit_headers(response)

            if response.status_code == 404:
                logger.warning(f"Perfume not found: {url}")
                return None

            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                retry_after_seconds = int(retry_after) if retry_after else None
                logger.warning(f"Rate limited by fragscrape API (retry after: {retry_after_seconds}s)")
                raise RateLimitError(retry_after=retry_after_seconds)

            if response.status_code != 200:
                logger.warning(f"Request failed with status {response.status_code}")
                return None

            data = response.json()

            # Handle error responses
            if isinstance(data, dict) and not data.get('success', True):
                error_msg = data.get('error', 'Unknown error')
                logger.error(f"fragscrape error: {error_msg}")
                return None

            # Extract the perfume data
            perfume_data = data if not isinstance(data, dict) or 'data' not in data else data.get('data', {})

            # Extract brand/name from URL for mapping
            brand = ''
            name = ''
            if '/Perfumes/' in url:
                path = url.split('/Perfumes/')[-1]
                parts = path.split('/')
                if len(parts) >= 2:
                    brand = parts[0].replace('_', ' ')
                    name = parts[1].replace('_', ' ')

            # Map to our internal format
            result = self._map_perfume_response(perfume_data, brand, name)

            # Override parfumo_id with the URL
            if result:
                result['parfumo_id'] = url
                result['url'] = url

            if result and result.get('score'):
                logger.info(f"Fetched rating by URL: {result.get('score', 'N/A')}")
                return result
            else:
                logger.warning(f"No rating data found for URL: {url}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching perfume by URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching perfume by URL: {e}")
            return None

    def _map_perfume_response(self, data: Dict, brand: str, name: str) -> Optional[Dict]:
        """
        Map fragscrape response to our internal format

        Args:
            data: Response data from fragscrape
            brand: Brand name
            name: Perfume name

        Returns:
            Mapped dictionary or None
        """
        if not data:
            return None

        try:
            # Try different possible field names for rating
            score = (
                data.get('rating') or
                data.get('score') or
                data.get('parfumo_rating') or
                data.get('overall_rating')
            )

            # Try different possible field names for votes
            votes = (
                data.get('totalRatings') or
                data.get('votes') or
                data.get('ratings_count') or
                data.get('number_of_ratings') or
                data.get('vote_count')
            )

            # Convert score to float if it's a string
            if score is not None:
                try:
                    score = float(score)
                except (ValueError, TypeError):
                    score = None

            # Convert votes to int if it's a string
            if votes is not None:
                try:
                    votes = int(votes)
                except (ValueError, TypeError):
                    votes = None

            if score is None:
                logger.debug(f"No rating found in response: {data}")
                return None

            # Build result in format compatible with old scraper
            result = {
                'score': score,
                'votes': votes,
                'parfumo_id': f"{brand}/{name}",
                'url': data.get('url', f"https://www.parfumo.com/Perfumes/{brand}/{name}"),
                'cached_at': datetime.now().isoformat(),
                'gender': data.get('gender')
            }

            # Add subcategories if available
            subcategories = {}
            for key in ['scent', 'longevity', 'sillage', 'bottle']:
                if key in data:
                    try:
                        subcategories[key] = float(data[key])
                    except (ValueError, TypeError):
                        pass

            if subcategories:
                result['subcategories'] = subcategories

            return result

        except Exception as e:
            logger.error(f"Error mapping perfume response: {e}")
            return None


# Singleton instance
_client_instance = None


def get_fragscrape_client(base_url: str = None) -> FragscrapeClient:
    """
    Get singleton FragscrapeClient instance

    Args:
        base_url: Optional base URL (only used on first call)

    Returns:
        FragscrapeClient instance
    """
    global _client_instance
    if _client_instance is None:
        # Get URL from config if available
        if base_url is None:
            try:
                import yaml
                from pathlib import Path
                config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                        base_url = config.get('parfumo', {}).get('fragscrape_url', 'http://localhost:3000')
            except Exception:
                base_url = 'http://localhost:3000'

        _client_instance = FragscrapeClient(base_url)
    return _client_instance
