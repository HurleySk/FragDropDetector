"""
Database models and setup for FragDropDetector
"""

import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class Post(Base):
    """Reddit post model"""
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    reddit_id = Column(String(10), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    author = Column(String(50))
    url = Column(String(500))
    selftext = Column(Text)
    link_flair_text = Column(String(100))
    score = Column(Integer, default=0)
    num_comments = Column(Integer, default=0)
    created_utc = Column(Float)
    processed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Drop(Base):
    """Detected drop model"""
    __tablename__ = 'drops'

    id = Column(Integer, primary_key=True)
    post_reddit_id = Column(String(10), nullable=False, index=True)
    confidence_score = Column(Float, nullable=False)
    detection_metadata = Column(Text)  # JSON string
    notified = Column(Boolean, default=False, index=True)
    notification_sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """Notification history model"""
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    drop_id = Column(Integer, nullable=False, index=True)
    method = Column(String(50))  # ntfy, telegram, email
    status = Column(String(50))  # sent, failed, pending
    error_message = Column(Text)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    """Application settings model"""
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FragranceStock(Base):
    """Fragrance stock tracking model"""
    __tablename__ = 'fragrance_stock'

    id = Column(Integer, primary_key=True)
    slug = Column(String(100), nullable=False, index=True)
    name = Column(String(300), nullable=False)
    url = Column(String(500), nullable=False)
    price = Column(String(20))
    in_stock = Column(Boolean, default=True, index=True)
    # Original fragrance info (what Montagne is cloning)
    original_brand = Column(String(100))
    original_name = Column(String(200))
    parfumo_id = Column(String(200))
    parfumo_score = Column(Float)  # 0-10 scale
    parfumo_votes = Column(Integer)
    original_rating = Column(Float)  # Rating from original brand site if available
    original_reviews_count = Column(Integer)
    rating_last_updated = Column(DateTime)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StockChange(Base):
    """Stock change history model"""
    __tablename__ = 'stock_changes'

    id = Column(Integer, primary_key=True)
    fragrance_slug = Column(String(100), nullable=False, index=True)
    change_type = Column(String(50), nullable=False)  # 'new', 'restocked', 'out_of_stock', 'price_change', 'removed'
    old_value = Column(String(500))  # Previous price or stock status
    new_value = Column(String(500))  # New price or stock status
    detected_at = Column(DateTime, default=datetime.utcnow)
    notified = Column(Boolean, default=False)


class Database:
    """Database manager class"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = os.path.join(os.getcwd(), 'data', 'fragdrop.db')

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.engine = create_engine(
            f'sqlite:///{db_path}',
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            connect_args={
                'check_same_thread': False,
                'timeout': 30
            }
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

        # Create tables
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialized at {db_path}")

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    @contextmanager
    def session(self):
        """
        Context manager for database sessions

        Usage:
            with db.session() as session:
                user = session.query(User).first()
                session.commit()

        Automatically handles rollback on exceptions and closes session
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def save_post(self, post_data: Dict[str, Any]) -> None:
        """
        Save a Reddit post to database

        Args:
            post_data: Post dictionary from Reddit client
        """
        session = self.get_session()
        try:
            # Check if post already exists
            existing = session.query(Post).filter_by(reddit_id=post_data['id']).first()

            if existing:
                # Update existing post
                existing.score = post_data.get('score', 0)
                existing.num_comments = post_data.get('num_comments', 0)
                existing.updated_at = datetime.utcnow()
            else:
                # Create new post
                post = Post(
                    reddit_id=post_data['id'],
                    title=post_data['title'],
                    author=post_data.get('author'),
                    url=post_data.get('url'),
                    selftext=post_data.get('selftext'),
                    link_flair_text=post_data.get('link_flair_text'),
                    score=post_data.get('score', 0),
                    num_comments=post_data.get('num_comments', 0),
                    created_utc=post_data.get('created_utc')
                )
                session.add(post)

            session.commit()
            logger.debug(f"Saved post: {post_data['title'][:50]}...")

        except Exception as e:
            logger.error(f"Error saving post: {e}")
            session.rollback()
        finally:
            session.close()

    def save_drop(self, drop_data: Dict[str, Any]) -> Optional[int]:
        """
        Save a detected drop

        Args:
            drop_data: Drop dictionary with detection metadata

        Returns:
            Drop ID if saved, None if already exists or on error
        """
        import json

        session = self.get_session()
        try:
            # Check if drop already exists for this post
            existing = session.query(Drop).filter_by(
                post_reddit_id=drop_data['id']
            ).first()

            if not existing:
                drop = Drop(
                    post_reddit_id=drop_data['id'],
                    confidence_score=drop_data['confidence'],
                    detection_metadata=json.dumps(drop_data.get('detection_metadata', {}))
                )
                session.add(drop)
                session.commit()
                logger.info(f"Saved new drop: {drop_data['title'][:50]}...")
                return drop.id
            else:
                logger.debug(f"Drop already exists for post {drop_data['id']}")
                return existing.id

        except Exception as e:
            logger.error(f"Error saving drop: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def get_unnotified_drops(self):
        """Get drops that haven't been notified yet"""
        session = self.get_session()
        try:
            drops = session.query(Drop).filter_by(notified=False).all()
            return drops
        finally:
            session.close()

    def mark_drop_notified(self, drop_id: int):
        """Mark a drop as notified"""
        session = self.get_session()
        try:
            drop = session.query(Drop).filter_by(id=drop_id).first()
            if drop:
                drop.notified = True
                drop.notification_sent_at = datetime.utcnow()
                session.commit()
                logger.debug(f"Marked drop {drop_id} as notified")
        except Exception as e:
            logger.error(f"Error marking drop as notified: {e}")
            session.rollback()
        finally:
            session.close()

    def get_last_check_time(self) -> float:
        """Get the timestamp of the last check"""
        session = self.get_session()
        try:
            setting = session.query(Setting).filter_by(key='last_check_time').first()
            if setting:
                return float(setting.value)
            return 0.0
        finally:
            session.close()

    def set_last_check_time(self, timestamp: float):
        """Set the timestamp of the last check"""
        session = self.get_session()
        try:
            setting = session.query(Setting).filter_by(key='last_check_time').first()
            if setting:
                setting.value = str(timestamp)
            else:
                setting = Setting(key='last_check_time', value=str(timestamp))
                session.add(setting)
            session.commit()
        except Exception as e:
            logger.error(f"Error setting last check time: {e}")
            session.rollback()
        finally:
            session.close()

    def get_drop_count(self) -> int:
        """Get total number of drops detected"""
        session = self.get_session()
        try:
            count = session.query(Drop).count()
            return count
        finally:
            session.close()

    def get_post_count(self) -> int:
        """Get total number of posts processed"""
        session = self.get_session()
        try:
            count = session.query(Post).count()
            return count
        finally:
            session.close()

    def get_recent_drops(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent drops with post information"""
        import json
        session = self.get_session()
        try:
            drops = session.query(Drop, Post).join(
                Post, Drop.post_reddit_id == Post.reddit_id
            ).order_by(Drop.created_at.desc()).limit(limit).all()

            result = []
            for drop, post in drops:
                result.append({
                    'id': drop.id,
                    'title': post.title,
                    'author': post.author,
                    'url': post.url,
                    'confidence': drop.confidence_score,
                    'created_at': drop.created_at.isoformat(),
                    'notified': drop.notified,
                    'metadata': json.loads(drop.detection_metadata) if drop.detection_metadata else {}
                })
            return result
        finally:
            session.close()

    def save_fragrance_stock(self, fragrance_data: dict):
        """Save or update fragrance stock data"""
        session = self.get_session()
        try:
            slug = fragrance_data['slug']
            existing = session.query(FragranceStock).filter_by(slug=slug).first()

            if existing:
                # Update existing record
                existing.name = fragrance_data['name']
                existing.url = fragrance_data['url']
                existing.price = fragrance_data['price']
                existing.in_stock = fragrance_data['in_stock']
                existing.last_seen = datetime.utcnow()
                existing.updated_at = datetime.utcnow()
            else:
                # Create new record
                fragrance = FragranceStock(
                    slug=slug,
                    name=fragrance_data['name'],
                    url=fragrance_data['url'],
                    price=fragrance_data['price'],
                    in_stock=fragrance_data['in_stock']
                )
                session.add(fragrance)

            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving fragrance stock: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def save_stock_change(self, change_data: dict):
        """Save a stock change event"""
        session = self.get_session()
        try:
            change = StockChange(
                fragrance_slug=change_data['fragrance_slug'],
                change_type=change_data['change_type'],
                old_value=change_data.get('old_value'),
                new_value=change_data.get('new_value')
            )
            session.add(change)
            session.commit()
            return change.id
        except Exception as e:
            logger.error(f"Error saving stock change: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def get_fragrance_count(self) -> int:
        """Get total number of fragrances tracked"""
        session = self.get_session()
        try:
            count = session.query(FragranceStock).count()
            return count
        finally:
            session.close()

    def get_recent_stock_changes(self, limit: int = 10) -> list:
        """Get recent stock changes"""
        session = self.get_session()
        try:
            changes = session.query(StockChange, FragranceStock).join(
                FragranceStock, StockChange.fragrance_slug == FragranceStock.slug
            ).order_by(StockChange.detected_at.desc()).limit(limit).all()

            result = []
            for change, fragrance in changes:
                result.append({
                    'id': change.id,
                    'fragrance_name': fragrance.name,
                    'fragrance_slug': fragrance.slug,
                    'change_type': change.change_type,
                    'old_value': change.old_value,
                    'new_value': change.new_value,
                    'detected_at': change.detected_at.isoformat(),
                    'notified': change.notified,
                    'product_url': fragrance.url
                })
            return result
        finally:
            session.close()

    def get_all_fragrances(self) -> dict:
        """Get all fragrances as dict keyed by slug"""
        session = self.get_session()
        try:
            fragrances = session.query(FragranceStock).all()
            return {
                f.slug: {
                    'name': f.name,
                    'url': f.url,
                    'price': f.price,
                    'in_stock': f.in_stock,
                    'last_seen': f.last_seen.isoformat()
                } for f in fragrances
            }
        finally:
            session.close()

    def bulk_save_fragrances(self, fragrance_list: List[Dict]) -> bool:
        """
        Bulk save/update multiple fragrances efficiently

        Args:
            fragrance_list: List of fragrance data dictionaries

        Returns:
            True if successful, False otherwise
        """
        if not fragrance_list:
            return True

        session = self.get_session()
        try:
            # Get all existing slugs for efficient lookup
            existing_slugs = {
                slug for (slug,) in session.query(FragranceStock.slug).all()
            }

            updates = []
            inserts = []
            now = datetime.utcnow()

            for frag_data in fragrance_list:
                slug = frag_data['slug']
                if slug in existing_slugs:
                    updates.append({
                        'slug': slug,
                        'name': frag_data['name'],
                        'url': frag_data['url'],
                        'price': frag_data['price'],
                        'in_stock': frag_data['in_stock'],
                        'last_seen': now,
                        'updated_at': now
                    })
                else:
                    inserts.append(FragranceStock(
                        slug=slug,
                        name=frag_data['name'],
                        url=frag_data['url'],
                        price=frag_data['price'],
                        in_stock=frag_data['in_stock']
                    ))

            # Bulk update existing records
            if updates:
                session.bulk_update_mappings(FragranceStock, updates)

            # Bulk insert new records
            if inserts:
                session.bulk_save_objects(inserts)

            session.commit()
            logger.info(f"Bulk saved {len(inserts)} new, {len(updates)} updated fragrances")
            return True

        except Exception as e:
            logger.error(f"Error bulk saving fragrances: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def bulk_save_stock_changes(self, changes_list: List[Dict]) -> int:
        """
        Bulk save multiple stock changes efficiently

        Args:
            changes_list: List of stock change data dictionaries

        Returns:
            Number of changes saved
        """
        if not changes_list:
            return 0

        session = self.get_session()
        try:
            change_objects = [
                StockChange(
                    fragrance_slug=change['fragrance_slug'],
                    change_type=change['change_type'],
                    old_value=change.get('old_value'),
                    new_value=change.get('new_value')
                )
                for change in changes_list
            ]

            session.bulk_save_objects(change_objects)
            session.commit()

            logger.info(f"Bulk saved {len(change_objects)} stock changes")
            return len(change_objects)

        except Exception as e:
            logger.error(f"Error bulk saving stock changes: {e}")
            session.rollback()
            return 0
        finally:
            session.close()