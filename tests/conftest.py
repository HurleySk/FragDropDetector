import pytest
import tempfile
import os
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, MagicMock

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Mock configuration for testing"""
    return {
        'reddit': {
            'subreddit': 'test',
            'check_interval': 300
        },
        'drop_window': {
            'enabled': True,
            'timezone': 'America/New_York',
            'days_of_week': [4],
            'start_hour': 12,
            'start_minute': 0,
            'end_hour': 17,
            'end_minute': 0
        },
        'stock_schedule': {
            'enabled': True,
            'window_enabled': False,
            'check_interval': 1800
        },
        'detection': {
            'keywords': ['drop', 'restock'],
            'confidence_threshold': 0.8
        },
        'database': {
            'path': 'test.db'
        },
        'notifications': {
            'enabled': True
        }
    }

@pytest.fixture
def sample_fragrance_data():
    """Sample fragrance data for testing"""
    return {
        'slug': 'test-fragrance',
        'name': 'Test Fragrance',
        'url': 'https://example.com/test',
        'price': '$99.99',
        'in_stock': True,
        'original_brand': 'Test Brand',
        'original_name': 'Original Fragrance',
        'parfumo_id': 'test-123',
        'parfumo_score': 8.5,
        'parfumo_votes': 100,
        'parfumo_url': 'https://www.parfumo.com/Perfumes/test-123'
    }

@pytest.fixture
def sample_drop_data():
    """Sample drop data for testing"""
    return {
        'post_id': 'test123',
        'title': 'Friday Drop: Test Fragrance',
        'url': 'https://reddit.com/r/test/comments/test123',
        'author': 'testuser',
        'created_utc': datetime.now().timestamp(),
        'confidence': 0.95,
        'matched_keywords': ['drop']
    }

@pytest.fixture
def mock_reddit_client():
    """Mock Reddit client for testing"""
    mock = MagicMock()
    mock.get_new_posts.return_value = []
    return mock

@pytest.fixture
def mock_notification_manager():
    """Mock notification manager for testing"""
    mock = MagicMock()
    mock.send_notification.return_value = True
    return mock

@pytest.fixture
def mock_stock_monitor():
    """Mock stock monitor for testing"""
    mock = MagicMock()
    mock.scan_products.return_value = []
    return mock
