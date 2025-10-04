"""
Parfumo rating scraper for original fragrances
Fetches ratings from Parfumo.com for the fragrances that Montagne clones
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict
from datetime import datetime, timedelta
import json
import os
from time import sleep

logger = logging.getLogger(__name__)


class ParfumoScraper:
    """Scrapes fragrance ratings from Parfumo.com"""

    def __init__(self):
        self.base_url = "https://www.parfumo.com/Perfumes/"
        self.cache_file = os.path.join(os.getcwd(), 'data', 'parfumo_cache.json')
        self.cache = self.load_cache()
        self.cache_duration_days = 7

        # Request headers to appear as a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
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

    def fetch_rating(self, parfumo_id: str) -> Optional[Dict]:
        """
        Fetch rating for a fragrance from Parfumo
        parfumo_id format: "Brand/Fragrance-Name-Year-ID"
        """
        if not parfumo_id:
            return None

        # Check cache first
        if self.is_cache_valid(parfumo_id):
            logger.info(f"Using cached Parfumo data for {parfumo_id}")
            return self.cache[parfumo_id]

        try:
            # Construct full URL
            url = f"{self.base_url}{parfumo_id}"
            logger.info(f"Fetching Parfumo rating from: {url}")

            # Make request with retry logic
            for attempt in range(3):
                try:
                    response = requests.get(url, headers=self.headers, timeout=10)
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

            # Look for the main rating score
            rating_element = soup.find('span', class_='rating_value')
            if not rating_element:
                # Alternative selectors for rating
                rating_element = soup.find('div', {'itemprop': 'ratingValue'})

            if rating_element:
                try:
                    rating_text = rating_element.get_text().strip()
                    # Extract numeric value
                    rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                    if rating_match:
                        rating_data['score'] = float(rating_match.group(1))
                except ValueError:
                    logger.warning(f"Could not parse rating: {rating_element.get_text()}")

            # Look for vote count
            votes_element = soup.find('span', class_='rating_count')
            if not votes_element:
                votes_element = soup.find('div', {'itemprop': 'ratingCount'})

            if votes_element:
                try:
                    votes_text = votes_element.get_text().strip()
                    votes_match = re.search(r'(\d+)', votes_text.replace(',', ''))
                    if votes_match:
                        rating_data['votes'] = int(votes_match.group(1))
                except ValueError:
                    logger.warning(f"Could not parse votes: {votes_element.get_text()}")

            # Look for subcategory ratings (scent, longevity, sillage)
            subcategories = {}
            for category in ['scent', 'longevity', 'sillage', 'bottle', 'value']:
                category_element = soup.find('div', {'data-category': category})
                if category_element:
                    try:
                        score = category_element.find('span', class_='score')
                        if score:
                            subcategories[category] = float(score.get_text().strip())
                    except:
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
        This would require more complex scraping of search results
        """
        # This is a simplified version - full implementation would need
        # to search Parfumo and parse results
        logger.info(f"Searching Parfumo for: {brand} {fragrance_name}")

        # For now, return None - this would need actual search implementation
        return None


# Singleton instance
_scraper_instance = None

def get_parfumo_scraper() -> ParfumoScraper:
    """Get singleton ParfumoScraper instance"""
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = ParfumoScraper()
    return _scraper_instance