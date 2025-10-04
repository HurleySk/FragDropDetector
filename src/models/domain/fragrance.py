"""
Domain model for Fragrance entities
Unified representation with conversion methods from different sources
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Fragrance:
    """Unified fragrance domain model"""

    slug: str
    name: str
    url: str
    price: str
    in_stock: bool

    # Optional fields
    image_url: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None

    # Original fragrance mapping
    original_brand: Optional[str] = None
    original_name: Optional[str] = None

    # Parfumo ratings
    parfumo_id: Optional[str] = None
    parfumo_score: Optional[float] = None
    parfumo_votes: Optional[int] = None
    parfumo_url: Optional[str] = None

    # Timestamps
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    rating_last_updated: Optional[datetime] = None

    @classmethod
    def from_db_model(cls, db_model) -> 'Fragrance':
        """
        Create Fragrance from SQLAlchemy FragranceStock model

        Args:
            db_model: FragranceStock SQLAlchemy instance

        Returns:
            Fragrance domain model
        """
        parfumo_url = None
        if db_model.parfumo_id:
            parfumo_url = f"https://www.parfumo.com/Perfumes/{db_model.parfumo_id}"

        return cls(
            slug=db_model.slug,
            name=db_model.name,
            url=db_model.url,
            price=db_model.price,
            in_stock=db_model.in_stock,
            original_brand=db_model.original_brand,
            original_name=db_model.original_name,
            parfumo_id=db_model.parfumo_id,
            parfumo_score=db_model.parfumo_score,
            parfumo_votes=db_model.parfumo_votes,
            parfumo_url=parfumo_url,
            first_seen=db_model.first_seen,
            last_seen=db_model.last_seen,
            last_updated=db_model.updated_at,
            rating_last_updated=db_model.rating_last_updated
        )

    @classmethod
    def from_product_dataclass(cls, product) -> 'Fragrance':
        """
        Create Fragrance from FragranceProduct dataclass

        Args:
            product: FragranceProduct instance from stock monitor

        Returns:
            Fragrance domain model
        """
        return cls(
            slug=product.slug,
            name=product.name,
            url=product.url,
            price=product.price,
            in_stock=product.in_stock,
            image_url=getattr(product, 'image_url', None),
            size=getattr(product, 'size', None),
            description=getattr(product, 'description', None),
            last_updated=getattr(product, 'last_updated', None)
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Fragrance':
        """
        Create Fragrance from dictionary

        Args:
            data: Dictionary with fragrance data

        Returns:
            Fragrance domain model
        """
        # Handle datetime strings
        datetime_fields = ['first_seen', 'last_seen', 'last_updated', 'rating_last_updated']
        for field in datetime_fields:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except (ValueError, TypeError):
                    data[field] = None

        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary

        Returns:
            Dictionary representation
        """
        data = asdict(self)

        # Convert datetime objects to ISO format strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

        return data

    def to_api_response(self, include_ratings: bool = True) -> Dict[str, Any]:
        """
        Convert to API response format

        Args:
            include_ratings: Whether to include Parfumo ratings

        Returns:
            Dictionary formatted for API response
        """
        response = {
            'slug': self.slug,
            'name': self.name,
            'url': self.url,
            'price': self.price,
            'in_stock': self.in_stock,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

        if include_ratings:
            if self.original_brand or self.original_name:
                response['original_brand'] = self.original_brand
                response['original_name'] = self.original_name

            if self.parfumo_id:
                response['parfumo_id'] = self.parfumo_id
                response['parfumo_score'] = self.parfumo_score
                response['parfumo_votes'] = self.parfumo_votes
                response['parfumo_url'] = self.parfumo_url

        return response

    def update_from_product(self, product) -> None:
        """
        Update fields from a FragranceProduct instance

        Args:
            product: FragranceProduct to update from
        """
        self.price = product.price
        self.in_stock = product.in_stock
        self.last_updated = getattr(product, 'last_updated', datetime.now())

        if hasattr(product, 'image_url') and product.image_url:
            self.image_url = product.image_url
        if hasattr(product, 'size') and product.size:
            self.size = product.size
        if hasattr(product, 'description') and product.description:
            self.description = product.description

    def update_rating(self, parfumo_id: str, score: Optional[float], votes: Optional[int]) -> None:
        """
        Update Parfumo rating information

        Args:
            parfumo_id: Parfumo ID
            score: Rating score (0-10)
            votes: Number of votes
        """
        self.parfumo_id = parfumo_id
        self.parfumo_score = score
        self.parfumo_votes = votes
        self.parfumo_url = f"https://www.parfumo.com/Perfumes/{parfumo_id}"
        self.rating_last_updated = datetime.now()
