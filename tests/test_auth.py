"""
Tests for Authentication module.
"""

import pytest
import os
import json
import time
from unittest.mock import patch, MagicMock
from auth import (
    generate_csrf_token, validate_csrf_token,
    generate_oauth_state, validate_oauth_state, cleanup_oauth_states,
    get_google_auth_url, get_wechat_auth_url,
    get_google_user_info, get_wechat_user_info,
    OAuthError, AuthHandler,
    get_user_data_path, get_user_gtd_path, get_user_files_path
)


class TestCSRFToken:
    """Test CSRF token generation and validation."""
    
    def test_generate_csrf_token(self):
        """Test CSRF token generation."""
        token = generate_csrf_token()
        
        assert isinstance(token, str)
        assert len(token) >= 32
    
    def test_generate_csrf_token_unique(self):
        """Test that generated CSRF tokens are unique."""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        
        assert token1 != token2
    
    def test_validate_csrf_token_valid(self):
        """Test validating a valid CSRF token."""
        token = generate_csrf_token()
        session_token = generate_csrf_token()
        
        result = validate_csrf_token(token, session_token)
        assert result is True
    
    def test_validate_csrf_token_empty(self):
        """Test validating empty CSRF token."""
        result = validate_csrf_token("", "session_token")
        assert result is False
    
    def test_validate_csrf_token_none(self):
        """Test validating None CSRF token."""
        result = validate_csrf_token(None, "session_token")
        assert result is False
    
    def test_validate_csrf_token_short(self):
        """Test validating short CSRF token."""
        result = validate_csrf_token("short", "session_token")
        assert result is False


class TestOAuthState:
    """Test OAuth state parameter handling."""
    
    def test_generate_oauth_state(self):
        """Test OAuth state generation."""
        state = generate_oauth_state()
        
        assert isinstance(state, str)
        assert len(state) >= 32
    
    def test_generate_oauth_state_unique(self):
        """Test that generated OAuth states are unique."""
        state1 = generate_oauth_state()
        state2 = generate_oauth_state()
        
        assert state1 != state2
    
    def test_validate_oauth_state_valid(self):
        """Test validating a valid OAuth state."""
        state = generate_oauth_state()
        result = validate_oauth_state(state)
        
        assert result is True
    
    def test_validate_oauth_state_invalid(self):
        """Test validating an invalid OAuth state."""
        result = validate_oauth_state("invalid_state")
        assert result is False
    
    def test_validate_oauth_state_consumed(self):
        """Test that OAuth state is consumed after validation."""
        state = generate_oauth_state()
        
        # First validation should succeed
        assert validate_oauth_state(state) is True
        
        # Second validation should fail (consumed)
        assert validate_oauth_state(state) is False
    
    def test_oauth_state_expiration(self):
        """Test OAuth state expiration."""
        state = generate_oauth_state()
        
        # State should be valid immediately
        assert validate_oauth_state(state) is True
        
        # Generate another state for the test
        state2 = generate_oauth_state()
        
        # Manually expire it by modifying internal state
        import auth
        auth._oauth_states[state2]['expires_at'] = time.time() - 1
        
        result = validate_oauth_state(state2)
        assert result is False
    
    def test_cleanup_oauth_states(self):
        """Test cleanup of expired OAuth states."""
        import auth
        
        # Create a state
        state = generate_oauth_state()
        
        # Expire it manually
        auth._oauth_states[state]['expires_at'] = time.time() - 1
        
        # Cleanup
        cleanup_oauth_states()
        
        # Should be removed
        assert state not in auth._oauth_states


class TestGoogleOAuth:
    """Test Google OAuth functionality."""
    
    @patch.dict(os.environ, {
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_REDIRECT_URI': 'http://test.com/callback'
    })
    def test_get_google_auth_url(self):
        """Test Google OAuth URL generation."""
        # Need to reload module to pick up env vars
        import importlib
        import auth
        importlib.reload(auth)
        
        state = "test-state"
        url = auth.get_google_auth_url(state)
        
        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        assert "client_id=test-client-id" in url
        assert "state=test-state" in url
        assert "redirect_uri=http%3A%2F%2Ftest.com%2Fcallback" in url
        assert "scope=openid+email+profile" in url
    
    @patch('auth.requests.post')
    @patch.dict(os.environ, {
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_CLIENT_SECRET': 'test-secret',
        'GOOGLE_REDIRECT_URI': 'http://test.com/callback'
    })
    def test_exchange_google_code_success(self, mock_post):
        """Test successful Google code exchange."""
        import importlib
        import auth
        importlib.reload(auth)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token'
        }
        mock_post.return_value = mock_response
        
        result = auth.exchange_google_code('test-code')
        
        assert result['access_token'] == 'test-access-token'
        assert mock_post.called
    
    @patch('auth.requests.post')
    @patch.dict(os.environ, {
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_CLIENT_SECRET': 'test-secret',
        'GOOGLE_REDIRECT_URI': 'http://test.com/callback'
    })
    def test_exchange_google_code_failure(self, mock_post):
        """Test failed Google code exchange."""
        import importlib
        import auth
        importlib.reload(auth)
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid code'
        mock_post.return_value = mock_response
        
        with pytest.raises(auth.OAuthError):
            auth.exchange_google_code('invalid-code')
    
    @patch('auth.requests.get')
    def test_get_google_user_info(self, mock_get):
        """Test getting Google user info."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '123',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        mock_get.return_value = mock_response
        
        result = get_google_user_info('test-token')
        
        assert result['id'] == '123'
        assert result['email'] == 'test@example.com'


class TestWeChatOAuth:
    """Test WeChat OAuth functionality."""
    
    @patch.dict(os.environ, {
        'WECHAT_APP_ID': 'test-app-id',
        'WECHAT_REDIRECT_URI': 'http://test.com/callback'
    })
    def test_get_wechat_auth_url(self):
        """Test WeChat OAuth URL generation."""
        import importlib
        import auth
        importlib.reload(auth)
        
        state = "test-state"
        url = auth.get_wechat_auth_url(state)
        
        assert url.startswith("https://open.weixin.qq.com/connect/qrconnect?")
        assert "appid=test-app-id" in url
        assert "state=test-state" in url
        assert "scope=snsapi_login" in url
    
    @patch('auth.requests.get')
    @patch.dict(os.environ, {
        'WECHAT_APP_ID': 'test-app-id',
        'WECHAT_APP_SECRET': 'test-secret'
    })
    def test_exchange_wechat_code_success(self, mock_get):
        """Test successful WeChat code exchange."""
        import importlib
        import auth
        importlib.reload(auth)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test-access-token',
            'openid': 'test-openid'
        }
        mock_get.return_value = mock_response
        
        result = auth.exchange_wechat_code('test-code')
        
        assert result['access_token'] == 'test-access-token'
        assert result['openid'] == 'test-openid'
    
    @patch('auth.requests.get')
    @patch.dict(os.environ, {
        'WECHAT_APP_ID': 'test-app-id',
        'WECHAT_APP_SECRET': 'test-secret'
    })
    def test_exchange_wechat_code_failure(self, mock_get):
        """Test failed WeChat code exchange."""
        import importlib
        import auth
        importlib.reload(auth)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'errcode': 40029,
            'errmsg': 'invalid code'
        }
        mock_get.return_value = mock_response
        
        with pytest.raises(auth.OAuthError):
            auth.exchange_wechat_code('invalid-code')


class TestUserIsolationHelpers:
    """Test user data isolation helper functions."""
    
    def test_get_user_data_path(self, temp_dir):
        """Test getting user data path."""
        with patch('auth.BASE_DIR', temp_dir):
            path = get_user_data_path(123)
            assert path.endswith('data/users/123')
            assert os.path.exists(path)
    
    def test_get_user_data_path_with_subpath(self, temp_dir):
        """Test getting user data path with subpath."""
        with patch('auth.BASE_DIR', temp_dir):
            path = get_user_data_path(123, 'gtd')
            assert path.endswith('data/users/123/gtd')
    
    def test_get_user_gtd_path(self, temp_dir):
        """Test getting user GTD path."""
        with patch('auth.BASE_DIR', temp_dir):
            path = get_user_gtd_path(456)
            assert path.endswith('data/users/456/gtd/tasks.json')
    
    def test_get_user_files_path(self, temp_dir):
        """Test getting user files path."""
        with patch('auth.BASE_DIR', temp_dir):
            path = get_user_files_path(789)
            assert path.endswith('data/users/789/files')
            assert os.path.exists(path)
    
    def test_get_user_files_path_with_subpath(self, temp_dir):
        """Test getting user files path with subpath."""
        with patch('auth.BASE_DIR', temp_dir):
            path = get_user_files_path(789, 'documents')
            assert path.endswith('data/users/789/files/documents')
    
    def test_get_user_files_path_traversal_prevention(self, temp_dir):
        """Test that directory traversal is prevented."""
        with patch('auth.BASE_DIR', temp_dir):
            with pytest.raises(ValueError):
                get_user_files_path(789, '../../../etc/passwd')


class TestAuthHandler:
    """Test AuthHandler class."""
    
    def test_auth_handler_exists(self):
        """Test that AuthHandler class exists."""
        assert AuthHandler is not None
    
    def test_auth_handler_has_methods(self):
        """Test that AuthHandler has expected methods."""
        methods = [
            'get_session_from_request',
            'parse_cookies',
            'require_auth',
            'get_csrf_token_from_request',
            'validate_csrf',
            'set_session_cookie',
            'set_csrf_cookie',
            'clear_auth_cookies',
            'send_login_page',
            'handle_google_callback',
            'handle_wechat_callback',
            'handle_logout'
        ]
        
        for method in methods:
            assert hasattr(AuthHandler, method)


class TestOAuthError:
    """Test OAuthError exception."""
    
    def test_oauth_error_creation(self):
        """Test creating OAuthError."""
        error = OAuthError("Test error message")
        assert str(error) == "Test error message"
    
    def test_oauth_error_inheritance(self):
        """Test that OAuthError inherits from Exception."""
        error = OAuthError("Test")
        assert isinstance(error, Exception)


class TestAuthEdgeCases:
    """Test edge cases in auth module."""
    
    def test_validate_csrf_with_none_session(self):
        """Test CSRF validation with None session token."""
        token = generate_csrf_token()
        result = validate_csrf_token(token, None)
        assert result is False
    
    def test_oauth_state_empty_string(self):
        """Test OAuth state validation with empty string."""
        result = validate_oauth_state("")
        assert result is False
    
    def test_get_user_data_path_zero(self, temp_dir):
        """Test user data path with user_id 0."""
        with patch('auth.BASE_DIR', temp_dir):
            path = get_user_data_path(0)
            assert 'users/0' in path
    
    def test_get_user_data_path_string(self, temp_dir):
        """Test user data path with string user_id."""
        with patch('auth.BASE_DIR', temp_dir):
            path = get_user_data_path("user-abc")
            assert 'users/user-abc' in path


class TestAuthEnvironment:
    """Test environment variable handling in auth."""
    
    @patch.dict(os.environ, {
        'GOOGLE_CLIENT_ID': '',
        'GOOGLE_CLIENT_SECRET': '',
        'WECHAT_APP_ID': '',
        'WECHAT_APP_SECRET': ''
    })
    def test_empty_env_vars(self):
        """Test handling of empty environment variables."""
        import importlib
        import auth
        importlib.reload(auth)
        
        # Should not crash, but URLs will have empty client IDs
        state = "test"
        url = auth.get_google_auth_url(state)
        assert "client_id=" in url
    
    def test_default_redirect_uri(self):
        """Test default redirect URI when not set."""
        # Default is used when env var not set
        import importlib
        import auth
        importlib.reload(auth)
        
        assert auth.GOOGLE_REDIRECT_URI == 'http://localhost:8000/auth/google/callback'
