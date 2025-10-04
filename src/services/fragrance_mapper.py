"""
Automated fragrance mapping service to extract original fragrance info
from Montagne product names and descriptions
"""

import re
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FragranceMapper:
    """Maps Montagne fragrances to their original inspirations"""

    def __init__(self, database=None):
        """
        Initialize mapper with database connection

        Args:
            database: Database instance (if None, will import from container)
        """
        self.database = database
        if self.database is None:
            from src.models.database import Database
            self.database = Database()

        # Multi-word brands to detect before applying regex
        self.multi_word_brands = {
            'PARFUMS DE MARLY': 'Parfums de Marly',
            'MAISON FRANCIS KURKDJIAN': 'Maison Francis Kurkdjian',
            'YVES SAINT LAURENT': 'Yves Saint Laurent',
            'LOUIS VUITTON': 'Louis Vuitton',
            'FRAGRANCE DU BOIS': 'Fragrance Du Bois',
            'TOM FORD': 'Tom Ford',
            'LE LABO': 'Le Labo',
            'BY KILIAN': 'By Kilian',
            'MAISON MARGIELA': 'Maison Margiela',
            'MEMO PARIS': 'Memo Paris',
            'TIZIANA TERENZI': 'Tiziana Terenzi',
            'ORMONDE JAYNE': 'Ormonde Jayne',
            'BOND NO': 'Bond No. 9',
            'FREDERIC MALLE': 'Frederic Malle',
            'VILHELM PARFUMERIE': 'Vilhelm Parfumerie',
            'MARC ANTOINE BARROIS': 'Marc-Antoine Barrois',
            'MIND GAMES': 'Mind Games',
        }

        # Regex patterns to extract original info from product names
        # Using \w to support Unicode characters (e.g., ALTHAÏR, CÈDRE)
        self.patterns = [
            # "INSPIRED BY PARFUMS DE MARLY LAYTON" - try multi-word first
            re.compile(r'INSPIRED BY\s+([\w\s&\.\']+?)\s+([\w\s\-\']+?)(?:\s*$|\s*-)', re.IGNORECASE | re.UNICODE),
            # "INSPIRED BY BRAND'S NAME" pattern
            re.compile(r'INSPIRED BY\s+([\w\s&\.]+?)\'S\s+([\w\s]+)', re.IGNORECASE | re.UNICODE),
            # Alternative patterns for edge cases
            re.compile(r'inspired by:\s*([^-]+?)\s*-\s*(.+)', re.IGNORECASE),
            re.compile(r'clone of\s+([\w\s&\.]+?)\s+([\w\s]+)', re.IGNORECASE | re.UNICODE),
        ]

        # Brand name normalization
        self.brand_aliases = {
            'MFK': 'Maison Francis Kurkdjian',
            'PDM': 'Parfums de Marly',
            'YSL': 'Yves Saint Laurent',
            'TF': 'Tom Ford',
            'BVLGARI': 'Bvlgari',
            'BULGARI': 'Bvlgari',
        }

    def extract_from_name(self, product_name: str, product_description: str = "") -> Optional[Tuple[str, str]]:
        """
        Extract original brand and fragrance name from Montagne product info
        Returns: (brand, fragrance_name) or None if not found
        """
        # Combine name and description for better matching
        search_text = f"{product_name} {product_description}".upper()

        # First, check for known multi-word brands
        detected_brand = None
        brand_match_pos = -1
        for brand_key, brand_name in self.multi_word_brands.items():
            pos = search_text.find(brand_key)
            if pos != -1:
                # Use the earliest match if multiple brands found
                if brand_match_pos == -1 or pos < brand_match_pos:
                    detected_brand = brand_name
                    brand_match_pos = pos

        # Try regex patterns
        for pattern in self.patterns:
            match = pattern.search(search_text)
            if match:
                brand = match.group(1).strip()
                fragrance = match.group(2).strip()

                # If we detected a multi-word brand, use that instead and remove it from fragrance
                if detected_brand:
                    brand = detected_brand
                    # Remove brand words from the start of fragrance name
                    brand_words = set(brand.upper().split())
                    fragrance_words = fragrance.upper().split()

                    # Skip brand words at the start of fragrance
                    cleaned_words = []
                    skip_brand = True
                    for word in fragrance_words:
                        if skip_brand and word in brand_words:
                            continue
                        else:
                            skip_brand = False
                            cleaned_words.append(word)

                    if cleaned_words:
                        fragrance = ' '.join(cleaned_words)
                else:
                    # Normalize brand name
                    brand_upper = brand.upper()
                    if brand_upper in self.brand_aliases:
                        brand = self.brand_aliases[brand_upper]
                    elif brand_upper in self.multi_word_brands:
                        brand = self.multi_word_brands[brand_upper]
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

        scraper = get_parfumo_scraper()
        parfumo_id = scraper.search_fragrance(brand, fragrance_name)

        return parfumo_id

    def update_mapping(self, slug: str, product_name: str, product_description: str = "") -> bool:
        """
        Update or create mapping for a Montagne product in database
        Returns True if mapping was created/updated, False otherwise
        """
        # Try to extract original info
        extracted = self.extract_from_name(product_name, product_description)

        if extracted:
            brand, fragrance = extracted

            # Search for Parfumo ID
            parfumo_id = self.get_parfumo_id(brand, fragrance)

            # Update database
            if parfumo_id:
                return self.database.update_fragrance_mapping(
                    slug=slug,
                    original_brand=brand,
                    original_name=fragrance,
                    parfumo_id=parfumo_id
                )
            else:
                # Save mapping without parfumo_id, mark as not found
                self.database.update_fragrance_mapping(
                    slug=slug,
                    original_brand=brand,
                    original_name=fragrance
                )
                self.database.mark_parfumo_not_found(slug)
                return True

        return False

    def get_mapping(self, slug: str) -> Optional[dict]:
        """
        Get mapping for a specific Montagne product from database
        Returns dict with mapping info or None
        """
        session = self.database.get_session()
        try:
            from src.models.database import FragranceStock

            fragrance = session.query(FragranceStock).filter_by(slug=slug).first()
            if not fragrance:
                return None

            # Only return mapping if we have brand/name
            if not fragrance.original_brand and not fragrance.original_name:
                return None

            return {
                'original_brand': fragrance.original_brand,
                'original_name': fragrance.original_name,
                'parfumo_id': fragrance.parfumo_id,
                'parfumo_not_found': fragrance.parfumo_not_found,
                'last_searched': fragrance.last_searched.isoformat() if fragrance.last_searched else None
            }

        finally:
            session.close()


# Singleton instance
_mapper_instance = None

def get_fragrance_mapper() -> FragranceMapper:
    """Get singleton FragranceMapper instance"""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = FragranceMapper()
    return _mapper_instance
