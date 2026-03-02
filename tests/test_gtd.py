"""
Tests for GTD module.
"""

import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Import GTD module functions
from gtd import (
    get_user_tasks_dir, get_user_tasks_file,
    load_tasks, save_tasks, read_tasks, write_tasks, clear_tasks,
    extract_title_from_url, GTDHandler
)


class TestGTDUserDirectories:
    """Test user directory and file path functions."""
    
    def test_get_user_tasks_dir(self, temp_dir):
        """Test getting user tasks directory."""
        with patch('gtd.GTD_BASE_DIR', temp_dir):
            user_dir = get_user_tasks_dir(123)
            assert user_dir.endswith('users/123')
            assert os.path.exists(user_dir)
    
    def test_get_user_tasks_file(self, temp_dir):
        """Test getting user tasks file path."""
        with patch('gtd.GTD_BASE_DIR', temp_dir):
            tasks_file = get_user_tasks_file(456)
            assert tasks_file.endswith('users/456/tasks.json')
    
    def test_get_user_tasks_dir_creates_directory(self, temp_dir):
        """Test that get_user_tasks_dir creates directory if it doesn't exist."""
        with patch('gtd.GTD_BASE_DIR', temp_dir):
            user_dir = get_user_tasks_dir(999)
            assert os.path.isdir(user_dir)


class TestGTDCRUDOperations:
    """Test task CRUD operations."""
    
    def test_load_tasks_creates_default(self, temp_gtd_dir):
        """Test that load_tasks creates default structure if file doesn't exist."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            tasks = load_tasks(user_id='test_user')
            
            assert 'projects' in tasks
            assert 'next_actions' in tasks
            assert 'waiting_for' in tasks
            assert 'someday_maybe' in tasks
    
    def test_save_and_load_tasks(self, temp_gtd_dir):
        """Test saving and loading tasks."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            test_tasks = {
                'projects': [{'id': 'p1', 'text': 'Test project'}],
                'next_actions': [],
                'waiting_for': [],
                'someday_maybe': []
            }
            
            save_tasks(test_tasks, user_id='test_user')
            loaded = load_tasks(user_id='test_user')
            
            assert loaded['projects'][0]['text'] == 'Test project'
    
    def test_read_tasks_returns_json(self, temp_gtd_dir):
        """Test that read_tasks returns JSON string."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            json_str = read_tasks(user_id='test_user')
            tasks = json.loads(json_str)
            
            assert isinstance(tasks, dict)
            assert 'projects' in tasks
    
    def test_write_tasks(self, temp_gtd_dir):
        """Test write_tasks function."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            test_tasks = {
                'projects': [],
                'next_actions': [],
                'waiting_for': [],
                'someday_maybe': []
            }
            
            result = write_tasks(test_tasks, user_id='test_user')
            assert result is True
    
    def test_clear_tasks(self, temp_gtd_dir):
        """Test clearing all tasks."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            # First add some tasks
            test_tasks = {
                'projects': [{'id': 'p1', 'text': 'Project'}],
                'next_actions': [{'id': 'n1', 'text': 'Action'}],
                'waiting_for': [{'id': 'w1', 'text': 'Waiting'}],
                'someday_maybe': [{'id': 's1', 'text': 'Someday'}]
            }
            save_tasks(test_tasks, user_id='test_user')
            
            # Clear them
            clear_tasks(user_id='test_user')
            
            # Verify cleared
            loaded = load_tasks(user_id='test_user')
            assert len(loaded['projects']) == 0
            assert len(loaded['next_actions']) == 0
            assert len(loaded['waiting_for']) == 0
            assert len(loaded['someday_maybe']) == 0


class TestGTDTaskValidation:
    """Test task validation."""
    
    def test_load_nonexistent_user_creates_default(self, temp_dir):
        """Test loading tasks for non-existent user creates default."""
        with patch('gtd.GTD_BASE_DIR', temp_dir):
            tasks = load_tasks(user_id='new_user')
            
            assert tasks == {
                'projects': [],
                'next_actions': [],
                'waiting_for': [],
                'someday_maybe': []
            }
    
    def test_save_invalid_category(self, temp_gtd_dir):
        """Test saving tasks with invalid category is allowed (no validation at save)."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            test_tasks = {
                'invalid_category': [{'id': 'x1', 'text': 'Invalid'}],
                'next_actions': [],
                'waiting_for': [],
                'someday_maybe': []
            }
            
            # Should not raise error
            save_tasks(test_tasks, user_id='test_user')
    
    def test_task_with_comments(self, temp_gtd_dir):
        """Test saving and loading tasks with comments."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            test_tasks = {
                'projects': [{
                    'id': 'p1',
                    'text': 'Project with comments',
                    'comments': [
                        {'id': 'c1', 'text': 'Comment 1', 'createdAt': '2024-01-01'}
                    ]
                }],
                'next_actions': [],
                'waiting_for': [],
                'someday_maybe': []
            }
            
            save_tasks(test_tasks, user_id='test_user')
            loaded = load_tasks(user_id='test_user')
            
            assert len(loaded['projects'][0]['comments']) == 1
            assert loaded['projects'][0]['comments'][0]['text'] == 'Comment 1'


class TestGTDCategoryFiltering:
    """Test category filtering and operations."""
    
    def test_load_specific_category(self, temp_gtd_dir):
        """Test loading and accessing specific categories."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            test_tasks = {
                'projects': [{'id': 'p1', 'text': 'Project'}],
                'next_actions': [{'id': 'n1', 'text': 'Action'}],
                'waiting_for': [{'id': 'w1', 'text': 'Waiting'}],
                'someday_maybe': [{'id': 's1', 'text': 'Someday'}]
            }
            
            save_tasks(test_tasks, user_id='test_user')
            loaded = load_tasks(user_id='test_user')
            
            assert len(loaded['projects']) == 1
            assert len(loaded['next_actions']) == 1
            assert len(loaded['waiting_for']) == 1
            assert len(loaded['someday_maybe']) == 1
    
    def test_empty_category(self, temp_gtd_dir):
        """Test handling of empty categories."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            test_tasks = {
                'projects': [],
                'next_actions': [],
                'waiting_for': [],
                'someday_maybe': []
            }
            
            save_tasks(test_tasks, user_id='test_user')
            loaded = load_tasks(user_id='test_user')
            
            assert loaded['projects'] == []
    
    def test_multiple_tasks_in_category(self, temp_gtd_dir):
        """Test handling multiple tasks in same category."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            test_tasks = {
                'projects': [
                    {'id': 'p1', 'text': 'Project 1'},
                    {'id': 'p2', 'text': 'Project 2'},
                    {'id': 'p3', 'text': 'Project 3'}
                ],
                'next_actions': [],
                'waiting_for': [],
                'someday_maybe': []
            }
            
            save_tasks(test_tasks, user_id='test_user')
            loaded = load_tasks(user_id='test_user')
            
            assert len(loaded['projects']) == 3


class TestGTDExtractTitle:
    """Test URL title extraction."""
    
    def test_extract_title_from_url(self):
        """Test extracting title from URL (fallback to domain)."""
        # This will use fallback since we can't actually fetch in tests
        title = extract_title_from_url('https://example.com/path/to/page')
        
        # Should return something based on domain or path
        assert isinstance(title, str)
        assert len(title) > 0
    
    def test_extract_title_simple_url(self):
        """Test extracting title from simple URL."""
        title = extract_title_from_url('https://github.com')
        assert isinstance(title, str)
    
    def test_extract_title_with_path(self):
        """Test extracting title from URL with path."""
        title = extract_title_from_url('https://example.com/articles/my-article')
        assert isinstance(title, str)
    
    def test_extract_title_malformed_url(self):
        """Test extracting title from malformed URL."""
        title = extract_title_from_url('not-a-url')
        # Should return the input as fallback
        assert title == 'not-a-url'


class TestGTDHandler:
    """Test GTDHandler class."""
    
    def test_gtd_handler_exists(self):
        """Test that GTDHandler class exists."""
        assert GTDHandler is not None
    
    def test_gtd_handler_has_methods(self):
        """Test that GTDHandler has expected methods."""
        methods = [
            'serve_gtd_app',
            'serve_gtd_static',
            'serve_gtd_tasks',
            'add_gtd_task',
            'update_gtd_tasks',
            'clear_gtd_tasks',
            'extract_title_api'
        ]
        
        for method in methods:
            assert hasattr(GTDHandler, method)


class TestGTDEdgeCases:
    """Test edge cases in GTD module."""
    
    def test_user_id_zero(self, temp_gtd_dir):
        """Test handling user_id of 0."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            tasks = load_tasks(user_id=0)
            assert 'projects' in tasks
    
    def test_user_id_string(self, temp_gtd_dir):
        """Test handling string user_id."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            tasks = load_tasks(user_id='user-abc')
            assert 'projects' in tasks
    
    def test_unicode_task_content(self, temp_gtd_dir):
        """Test handling unicode in task content."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            test_tasks = {
                'projects': [{'id': 'p1', 'text': '任务测试 🚀'}],
                'next_actions': [],
                'waiting_for': [],
                'someday_maybe': []
            }
            
            save_tasks(test_tasks, user_id='test_user')
            loaded = load_tasks(user_id='test_user')
            
            assert loaded['projects'][0]['text'] == '任务测试 🚀'
    
    def test_very_long_task_content(self, temp_gtd_dir):
        """Test handling very long task content."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            long_text = 'x' * 10000
            test_tasks = {
                'projects': [{'id': 'p1', 'text': long_text}],
                'next_actions': [],
                'waiting_for': [],
                'someday_maybe': []
            }
            
            save_tasks(test_tasks, user_id='test_user')
            loaded = load_tasks(user_id='test_user')
            
            assert len(loaded['projects'][0]['text']) == 10000
    
    def test_special_characters_in_task(self, temp_gtd_dir):
        """Test handling special characters in task content."""
        with patch('gtd.GTD_BASE_DIR', os.path.dirname(os.path.dirname(temp_gtd_dir))):
            test_tasks = {
                'projects': [{'id': 'p1', 'text': 'Task with "quotes" and <tags>'}],
                'next_actions': [],
                'waiting_for': [],
                'someday_maybe': []
            }
            
            save_tasks(test_tasks, user_id='test_user')
            loaded = load_tasks(user_id='test_user')
            
            assert loaded['projects'][0]['text'] == 'Task with "quotes" and <tags>'
