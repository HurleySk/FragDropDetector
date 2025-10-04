"""
Automated fragrance mapping service to extract original fragrance info
from Montagne product names and descriptions
"""

import re
import json
import os
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class FragranceMapper:
    """Maps Montagne fragrances to their original inspirations"""

    def __init__(self):
        self.mapping_file = os.path.join(os.getcwd(), 'data', 'fragrance_mappings.json')
        self.mappings = self.load_mappings()

        # Regex patterns to extract original info from product names
        self.patterns = [
            # "INSPIRED BY BRAND NAME" pattern
            re.compile(r'INSPIRED BY\s+([A-Z][A-Z\s&\.]+?)\s+([A-Z][A-Z0-9\s]+)', re.IGNORECASE),
            # "INSPIRED BY BRAND'S NAME" pattern
            re.compile(r'INSPIRED BY\s+([A-Z][A-Z\s&\.]+?)\'S\s+([A-Z][A-Z0-9\s]+)', re.IGNORECASE),
            # Alternative patterns for edge cases
            re.compile(r'inspired by:\s*([^-]+?)\s*-\s*(.+)', re.IGNORECASE),
            re.compile(r'clone of\s+([A-Z][A-Z\s&\.]+?)\s+([A-Z][A-Z0-9\s]+)', re.IGNORECASE),
        ]

        # Brand name normalization
        self.brand_aliases = {
            'MFK': 'Maison Francis Kurkdjian',
            'PDM': 'Parfums de Marly',
            'YSL': 'Yves Saint Laurent',
            'TF': 'Tom Ford',
            'TOM FORD': 'Tom Ford',
            'PARFUMS DE MARLY': 'Parfums de Marly',
            'LE LABO': 'Le Labo',
            'BY KILIAN': 'By Kilian',
            'LOUIS VUITTON': 'Louis Vuitton',
            'BVLGARI': 'Bvlgari',
            'BULGARI': 'Bvlgari',
        }

    def load_mappings(self) -> Dict:
        """Load existing mappings from file"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading mappings: {e}")
        return {}

    def save_mappings(self):
        """Save mappings to file"""
        try:
            os.makedirs(os.path.dirname(self.mapping_file), exist_ok=True)
            with open(self.mapping_file, 'w') as f:
                json.dump(self.mappings, f, indent=2, sort_keys=True)
            logger.info(f"Saved {len(self.mappings)} fragrance mappings")
        except Exception as e:
            logger.error(f"Error saving mappings: {e}")

    def extract_from_name(self, product_name: str, product_description: str = "") -> Optional[Tuple[str, str]]:
        """
        Extract original brand and fragrance name from Montagne product info
        Returns: (brand, fragrance_name) or None if not found
        """
        # Combine name and description for better matching
        search_text = f"{product_name} {product_description}"

        for pattern in self.patterns:
            match = pattern.search(search_text)
            if match:
                brand = match.group(1).strip()
                fragrance = match.group(2).strip()

                # Normalize brand name
                brand_upper = brand.upper()
                if brand_upper in self.brand_aliases:
                    brand = self.brand_aliases[brand_upper]
                else:
                    # Title case for proper formatting
                    brand = ' '.join(word.capitalize() for word in brand.split())

                # Clean up fragrance name
                fragrance = ' '.join(word.capitalize() for word in fragrance.split())

                logger.info(f"Extracted mapping: '{product_name}' -> {brand} - {fragrance}")
                return brand, fragrance

        return None

    def get_parfumo_id(self, brand: str, fragrance_name: str) -> Optional[str]:
        """
        Get Parfumo ID for a fragrance by searching Parfumo
        """
        # Import here to avoid circular dependency
        from .parfumo_scraper import get_parfumo_scraper

        # First check if we have a cached mapping for this exact combination
        # This avoids repeated searches for the same fragrance
        cache_key = f"{brand}|{fragrance_name}"
        if hasattr(self, '_search_cache'):
            if cache_key in self._search_cache:
                return self._search_cache[cache_key]
        else:
            self._search_cache = {}

        # Use Parfumo scraper to search for the fragrance
        scraper = get_parfumo_scraper()
        parfumo_id = scraper.search_fragrance(brand, fragrance_name)

        # Cache the result (even if None) to avoid repeated searches
        self._search_cache[cache_key] = parfumo_id

        return parfumo_id

    def update_mapping(self, slug: str, product_name: str, product_description: str = "") -> Dict:
        """
        Update or create mapping for a Montagne product
        Returns the mapping info
        """
        # Check if we already have this mapping
        if slug in self.mappings:
            return self.mappings[slug]

        # Try to extract original info
        extracted = self.extract_from_name(product_name, product_description)

        if extracted:
            brand, fragrance = extracted
            mapping = {
                'original_brand': brand,
                'original_name': fragrance,
                'parfumo_id': self.get_parfumo_id(brand, fragrance)
            }

            self.mappings[slug] = mapping
            self.save_mappings()
            return mapping

        return {}

    def get_mapping(self, slug: str) -> Optional[Dict]:
        """Get mapping for a specific Montagne product"""
        return self.mappings.get(slug)

    def get_all_mappings(self) -> Dict:
        """Get all mappings"""
        return self.mappings.copy()


# Singleton instance
_mapper_instance = None

def get_fragrance_mapper() -> FragranceMapper:
    """Get singleton FragranceMapper instance"""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = FragranceMapper()
    return _mapper_instance