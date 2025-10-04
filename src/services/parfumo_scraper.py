"""
Parfumo rating scraper for original fragrances
Fetches ratings from Parfumo.com for the fragrances that Montagne clones
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import json
import os
from time import sleep

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    logger.warning("rapidfuzz not available, using fallback string matching")


class ParfumoScraper:
    """Scrapes fragrance ratings from Parfumo.com"""

    def __init__(self):
        self.base_url = "https://www.parfumo.com/Perfumes/"
        self.cache_file = os.path.join(os.getcwd(), 'data', 'parfumo_cache.json')
        self.cache = self.load_cache()
        self.cache_duration_days = 7

        # Use session to maintain cookies and connection
        self.session = requests.Session()

        # Request headers to appear as a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

    def load_cache(self) -> Dict:
        """Load cached ratings"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
        return {}

    def save_cache(self):
        """Save ratings to cache"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def is_cache_valid(self, parfumo_id: str) -> bool:
        """Check if cached data is still valid"""
        if parfumo_id not in self.cache:
            return False

        cached_data = self.cache[parfumo_id]
        if 'cached_at' not in cached_data:
            return False

        cached_time = datetime.fromisoformat(cached_data['cached_at'])
        age = datetime.now() - cached_time

        return age < timedelta(days=self.cache_duration_days)

    def try_parfumo_urls(self, parfumo_id: str) -> Optional[Dict]:
        """
        Try multiple URL variations until one works

        Args:
            parfumo_id: Base Parfumo ID

        Returns:
            Rating data if found, None otherwise
        """
        # Generate URL variations
        variations = [
            parfumo_id,  # Original
            parfumo_id.replace('_', '-'),  # Underscores to dashes
            parfumo_id.replace('-', '_'),  # Dashes to underscores
        ]

        # Try removing year/ID suffix: "Brand/Name-2020-12345" -> "Brand/Name"
        parts = parfumo_id.split('/')
        if len(parts) >= 2:
            name_part = parts[-1]
            # Remove anything after the second dash (usually year-id)
            dash_parts = name_part.split('-')
            if len(dash_parts) > 2:
                clean_name = '-'.join(dash_parts[:2])
                variations.append(f"{parts[0]}/{clean_name}")

        logger.info(f"Trying {len(variations)} URL variations for {parfumo_id}")

        for variant in variations:
            if variant != parfumo_id:
                logger.debug(f"Trying variant: {variant}")

            rating = self._fetch_rating_single(variant)
            if rating and rating.get('score'):
                logger.info(f"Found rating using variant: {variant}")
                # Cache with original ID for future lookups
                self.cache[parfumo_id] = rating
                self.save_cache()
                return rating

        logger.warning(f"No working URL found for {parfumo_id}")
        return None

    def fetch_rating(self, parfumo_id: str) -> Optional[Dict]:
        """
        Fetch rating for a fragrance from Parfumo with automatic URL variation handling
        parfumo_id format: "Brand/Fragrance-Name-Year-ID" or just "Brand/Fragrance-Name"
        """
        if not parfumo_id:
            return None

        # Check cache first
        if self.is_cache_valid(parfumo_id):
            logger.info(f"Using cached Parfumo data for {parfumo_id}")
            return self.cache[parfumo_id]

        # Try URL variations
        return self.try_parfumo_urls(parfumo_id)

    def _fetch_rating_single(self, parfumo_id: str) -> Optional[Dict]:
        """
        Fetch rating for a single Parfumo ID without variations

        Args:
            parfumo_id: Parfumo ID to fetch

        Returns:
            Rating data if found, None otherwise
        """
        if not parfumo_id:
            return None

        try:
            # Construct full URL
            url = f"{self.base_url}{parfumo_id}"
            logger.info(f"Fetching Parfumo rating from: {url}")

            # Make request with retry logic
            for attempt in range(3):
                try:
                    response = self.session.get(url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        break
                    elif response.status_code == 404:
                        logger.warning(f"Fragrance not found on Parfumo: {parfumo_id}")
                        return None
                except requests.RequestException as e:
                    if attempt == 2:  # Last attempt
                        raise
                    logger.warning(f"Request failed, retrying... {e}")
                    sleep(2 ** attempt)  # Exponential backoff

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract overall rating (0-10 scale)
            rating_data = {}

            # Correct selector for main rating score
            rating_element = soup.find('span', {'itemprop': 'ratingValue'})
            if rating_element:
                try:
                    rating_text = rating_element.get_text().strip()
                    # Extract numeric value
                    rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                    if rating_match:
                        rating_data['score'] = float(rating_match.group(1))
                except ValueError:
                    logger.warning(f"Could not parse rating: {rating_element.get_text()}")

            # Correct selector for vote count
            votes_element = soup.find('span', {'itemprop': 'ratingCount'})
            if votes_element:
                try:
                    votes_text = votes_element.get_text().strip()
                    # Remove "Ratings" text and extract number
                    votes_match = re.search(r'(\d+)', votes_text.replace(',', ''))
                    if votes_match:
                        rating_data['votes'] = int(votes_match.group(1))
                except ValueError:
                    logger.warning(f"Could not parse votes: {votes_element.get_text()}")

            # Look for subcategory ratings from data-percentage attributes
            subcategories = {}
            barfiller_elements = soup.find_all('div', class_='barfiller_element rating-details')

            for elem in barfiller_elements:
                category = elem.get('data-type')
                if category:
                    # Map internal names to display names
                    category_map = {
                        'scent': 'scent',
                        'durability': 'longevity',
                        'sillage': 'sillage',
                        'bottle': 'bottle'
                    }
                    if category in category_map:
                        try:
                            percentage = float(elem.get('data-percentage', 0))
                            # Convert percentage to 0-10 scale
                            subcategories[category_map[category]] = round(percentage / 10, 1)
                        except (ValueError, TypeError):
                            pass

            if subcategories:
                rating_data['subcategories'] = subcategories

            # Add metadata
            rating_data['parfumo_id'] = parfumo_id
            rating_data['url'] = url
            rating_data['cached_at'] = datetime.now().isoformat()

            # Save to cache
            self.cache[parfumo_id] = rating_data
            self.save_cache()

            logger.info(f"Fetched Parfumo rating: {rating_data.get('score', 'N/A')} for {parfumo_id}")
            return rating_data

        except Exception as e:
            logger.error(f"Error fetching Parfumo rating for {parfumo_id}: {e}")
            return None

    def fetch_multiple_ratings(self, parfumo_ids: list) -> Dict:
        """Fetch ratings for multiple fragrances"""
        results = {}

        for parfumo_id in parfumo_ids:
            if parfumo_id:
                rating = self.fetch_rating(parfumo_id)
                if rating:
                    results[parfumo_id] = rating
                # Be nice to the server
                if not self.is_cache_valid(parfumo_id):
                    sleep(1)

        return results

    def search_fragrance(self, brand: str, fragrance_name: str) -> Optional[str]:
        """
        Search for a fragrance on Parfumo and return its ID
        """
        try:
            # Build search query using "brand - fragrance" format
            search_query = f"{brand} - {fragrance_name}".strip()
            logger.info(f"Searching Parfumo for: {search_query}")

            # Use Parfumo search page
            search_url = "https://www.parfumo.com/s_perfumes_x.php"
            params = {
                'in': '1',  # Search in perfume names
                'order': 'popular',  # Sort by popularity
                'filter': search_query
            }

            response = self.session.get(search_url, params=params, headers=self.headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Search failed with status {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for perfume links in search results
            # Find all links and filter for perfume pages
            all_links = soup.find_all('a', href=True)
            perfume_links = []

            logger.info(f"Found {len(all_links)} total links on search page")

            for link in all_links:
                href = str(link.get('href', ''))
                # Match perfume pages: /Perfumes/Brand/FragranceName
                if '/Perfumes/' in href and href != 'https://www.parfumo.com/Perfumes/':
                    # Exclude brand-only links (they don't end with a fragrance name)
                    if href.endswith('/Perfumes/'):
                        continue

                    # Extract the path after /Perfumes/
                    if 'parfumo.com/Perfumes/' in href:
                        # Full URL format
                        path_parts = href.split('/Perfumes/')
                        if len(path_parts) > 1 and path_parts[1]:
                            # Make sure it has both brand and fragrance
                            path = path_parts[1]
                            if '/' in path or path.count('_') > 0:  # Has brand/fragrance separator
                                perfume_links.append((link, path))
                                logger.debug(f"Found perfume link: {path}")
                    elif href.startswith('/Perfumes/'):
                        # Relative URL format
                        path = href[10:]  # Remove '/Perfumes/'
                        if path and ('/' in path or '_' in path):
                            perfume_links.append((link, path))
                            logger.debug(f"Found perfume link: {path}")

            logger.info(f"Found {len(perfume_links)} perfume links")

            if not perfume_links:
                logger.info(f"No results found for: {search_query}")
                return None

            # Try to find best match using fuzzy matching
            brand_lower = brand.lower()
            fragrance_lower = fragrance_name.lower()
            combined_search = f"{brand_lower} {fragrance_lower}"

            matches: List[Tuple[float, str]] = []

            if FUZZY_AVAILABLE:
                # Use fuzzy matching for better accuracy
                for link, path in perfume_links:
                    path_lower = path.lower()

                    # Calculate similarity scores
                    brand_score = fuzz.partial_ratio(brand_lower, path_lower)
                    fragrance_score = fuzz.partial_ratio(fragrance_lower, path_lower)
                    combined_score = fuzz.partial_ratio(combined_search, path_lower)

                    # Weighted average: brand and fragrance equally important
                    final_score = (brand_score + fragrance_score + combined_score) / 3

                    logger.debug(f"Fuzzy match {path}: brand={brand_score}, frag={fragrance_score}, combined={combined_score}, final={final_score}")

                    # Require minimum 70% similarity
                    if final_score >= 70:
                        matches.append((final_score, path))

                # Sort by score, best match first
                matches.sort(reverse=True, key=lambda x: x[0])

                if matches:
                    best_score, best_path = matches[0]
                    logger.info(f"Found Parfumo match with {best_score:.1f}% similarity: {best_path}")
                    return best_path

            else:
                # Fallback to substring matching
                for link, path in perfume_links:
                    id_lower = path.lower()
                    if brand_lower in id_lower and fragrance_lower in id_lower:
                        logger.info(f"Found Parfumo match (substring): {path}")
                        return path

            # If no good match found, don't return anything (better than wrong match)
            logger.info(f"No confident match found for: {brand} - {fragrance_name}")
            return None

        except Exception as e:
            logger.error(f"Error searching Parfumo for {brand} {fragrance_name}: {e}")
            return None


# Singleton instance
_scraper_instance = None

def get_parfumo_scraper() -> ParfumoScraper:
    """Get singleton ParfumoScraper instance"""
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = ParfumoScraper()
    return _scraper_instance