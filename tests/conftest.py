"""
Pytest fixtures and configuration for Molt Server tests.
"""

import pytest
import os
import sys
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache import TTLCache
from config import *


@pytest.fixture
def cache():
    """Create a TTL cache with 1 second TTL for testing."""
    return TTLCache(ttl_seconds=1)


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return {
        "id": "test-123",
        "content": "Test task",
        "category": "Projects",
        "done": False
    }


@pytest.fixture
def sample_task_create():
    """Create a sample task for creation (without id)."""
    return {
        "content": "New test task",
        "category": "next_actions"
    }


@pytest.fixture
def sample_bulk_tasks():
    """Create sample bulk tasks data."""
    return {
        "projects": [
            {"id": "p1", "text": "Project 1", "completed": False, "comments": []}
        ],
        "next_actions": [
            {"id": "n1", "text": "Next action 1", "completed": False, "comments": []}
        ],
        "waiting_for": [],
        "someday_maybe": []
    }


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def temp_gtd_dir(temp_dir):
    """Create a temporary GTD directory structure."""
    gtd_dir = os.path.join(temp_dir, 'gtd', 'users', 'test_user')
    os.makedirs(gtd_dir, exist_ok=True)
    return gtd_dir


@pytest.fixture
def valid_url_data():
    """Create valid URL data for testing."""
    return {"url": "https://example.com/path/to/page"}


@pytest.fixture
def invalid_url_data():
    """Create invalid URL data for testing."""
    return {"url": "not-a-valid-url"}


@pytest.fixture
def oauth_state():
    """Create OAuth state for testing."""
    return "test_oauth_state_12345"


@pytest.fixture
def sample_user_info_google():
    """Sample Google user info."""
    return {
        "id": "google-123",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/avatar.jpg"
    }


@pytest.fixture
def sample_user_info_wechat():
    """Sample WeChat user info."""
    return {
        "openid": "wechat-456",
        "nickname": "WeChat User",
        "headimgurl": "https://example.com/wechat-avatar.jpg"
    }
