"""
Database models and setup for FragDropDetector
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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


class Database:
    """Database manager class"""

    def __init__(self, db_path: str = None):
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
            connect_args={'check_same_thread': False}  # For SQLite
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

        # Create tables
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialized at {db_path}")

    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()

    def save_post(self, post_data: dict):
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

    def save_drop(self, drop_data: dict):
        """
        Save a detected drop

        Args:
            drop_data: Drop dictionary with detection metadata
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