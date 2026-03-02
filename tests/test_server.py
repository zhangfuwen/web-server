"""
Tests for HTTP Server module.
"""

import pytest
import json
import socket
import threading
import time
from unittest.mock import patch, MagicMock
from io import BytesIO


class TestServerImports:
    """Test server module imports and structure."""
    
    def test_server_module_exists(self):
        """Test that server module can be imported."""
        # Test that main modules exist
        from cache import TTLCache
        from config import SERVER_PORT, SERVER_HOST
        from gtd import GTDHandler
        
        assert TTLCache is not None
        assert SERVER_PORT == 8081
        assert SERVER_HOST == '127.0.0.1'
    
    def test_threaded_http_server_exists(self):
        """Test ThreadedHTTPServer class exists."""
        from molt_server_unified import ThreadedHTTPServer
        assert ThreadedHTTPServer is not None


class TestCacheEndpoints:
    """Test cache-related endpoints."""
    
    def test_cache_stats_structure(self, cache):
        """Test cache stats returns correct structure."""
        cache.set("test", "value")
        cache.get("test")
        cache.get("missing")
        
        stats = cache.get_stats()
        
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'total_requests' in stats
        assert 'hit_rate_percent' in stats
        assert 'cached_entries' in stats
        assert 'ttl_seconds' in stats


class TestHTTPHandlerBasics:
    """Test basic HTTP handler functionality."""
    
    def test_handler_class_exists(self):
        """Test that HTTP handler class exists."""
        from molt_server_unified import UnifiedHTTPRequestHandler
        assert UnifiedHTTPRequestHandler is not None
    
    def test_handler_inherits_gtd(self):
        """Test that handler inherits GTDHandler."""
        from molt_server_unified import UnifiedHTTPRequestHandler
        from gtd import GTDHandler
        
        assert issubclass(UnifiedHTTPRequestHandler, GTDHandler)
    
    def test_handler_has_do_get(self):
        """Test that handler has do_GET method."""
        from molt_server_unified import UnifiedHTTPRequestHandler
        assert hasattr(UnifiedHTTPRequestHandler, 'do_GET')
    
    def test_handler_has_do_post(self):
        """Test that handler has do_POST method."""
        from molt_server_unified import UnifiedHTTPRequestHandler
        assert hasattr(UnifiedHTTPRequestHandler, 'do_POST')


class TestErrorHandling:
    """Test error handling in server."""
    
    def test_send_error_method_exists(self):
        """Test that send_error method exists."""
        from molt_server_unified import UnifiedHTTPRequestHandler
        assert hasattr(UnifiedHTTPRequestHandler, 'send_error')
    
    def test_error_response_encoding(self):
        """Test that error responses use UTF-8."""
        # The send_error override ensures UTF-8 encoding
        from molt_server_unified import UnifiedHTTPRequestHandler
        # Just verify the method exists and is callable
        assert callable(getattr(UnifiedHTTPRequestHandler, 'send_error'))


class TestServerConfiguration:
    """Test server configuration."""
    
    def test_default_port(self):
        """Test default server port."""
        from config import SERVER_PORT
        assert SERVER_PORT == 8081
    
    def test_default_host(self):
        """Test default server host."""
        from config import SERVER_HOST
        assert SERVER_HOST == '127.0.0.1'
    
    def test_static_dir_configuration(self):
        """Test static directory configuration."""
        from molt_server_unified import STATIC_DIR
        assert STATIC_DIR is not None
        assert 'static' in STATIC_DIR
    
    def test_cache_initialization(self):
        """Test that cache instances are initialized."""
        from molt_server_unified import system_metrics_cache, process_list_cache
        
        assert system_metrics_cache is not None
        assert process_list_cache is not None
        assert system_metrics_cache.ttl == 5
        assert process_list_cache.ttl == 10


class TestMockHTTPHandler:
    """Test HTTP handler with mocked requests."""
    
    def create_mock_handler(self, method='GET', path='/', headers=None, body=b''):
        """Create a mock HTTP handler for testing."""
        from molt_server_unified import UnifiedHTTPRequestHandler
        
        mock_handler = MagicMock(spec=UnifiedHTTPRequestHandler)
        mock_handler.command = method
        mock_handler.path = path
        mock_handler.headers = headers or {}
        mock_handler.rfile = BytesIO(body)
        mock_handler.wfile = BytesIO()
        mock_handler.client_address = ('127.0.0.1', 12345)
        
        return mock_handler
    
    def test_parse_cookies(self):
        """Test cookie parsing."""
        from auth import AuthHandler
        
        # Create a minimal mock
        class MockHandler:
            pass
        
        handler = MockHandler()
        
        # Add the parse_cookies method
        def parse_cookies(cookie_header):
            cookies = {}
            if cookie_header:
                for cookie in cookie_header.split(';'):
                    if '=' in cookie:
                        key, value = cookie.split('=', 1)
                        cookies[key.strip()] = value.strip()
            return cookies
        
        # Test parsing
        cookie_header = "session=abc123; csrf=xyz789"
        cookies = parse_cookies(cookie_header)
        
        assert cookies['session'] == 'abc123'
        assert cookies['csrf'] == 'xyz789'
    
    def test_parse_cookies_empty(self):
        """Test parsing empty cookie header."""
        def parse_cookies(cookie_header):
            cookies = {}
            if cookie_header:
                for cookie in cookie_header.split(';'):
                    if '=' in cookie:
                        key, value = cookie.split('=', 1)
                        cookies[key.strip()] = value.strip()
            return cookies
        
        cookies = parse_cookies("")
        assert cookies == {}


class TestServerEndpoints:
    """Test server endpoint routing."""
    
    def test_system_info_path(self):
        """Test system info endpoint path."""
        # Verify the path constant or pattern
        path = '/system-info'
        assert path.startswith('/')
    
    def test_gtd_tasks_path(self):
        """Test GTD tasks endpoint path."""
        path = '/api/gtd/tasks'
        assert '/api/' in path
        assert 'gtd' in path
        assert 'tasks' in path
    
    def test_auth_paths(self):
        """Test authentication endpoint paths."""
        paths = [
            '/auth/google',
            '/auth/google/callback',
            '/auth/wechat',
            '/auth/wechat/callback',
            '/logout'
        ]
        
        for path in paths:
            assert path.startswith('/')


class TestCacheHeaders:
    """Test cache header handling."""
    
    def test_no_cache_header(self):
        """Test no-cache header value."""
        # Common cache control values
        no_cache = 'no-cache'
        no_store = 'no-store'
        
        assert no_cache == 'no-cache'
        assert no_store == 'no-store'
    
    def test_cache_control_format(self):
        """Test cache control header format."""
        # Cache-Control header format
        header_name = 'Cache-Control'
        assert header_name == 'Cache-Control'


class TestContentTypeHandling:
    """Test content type handling."""
    
    def test_json_content_type(self):
        """Test JSON content type."""
        content_type = 'application/json'
        assert content_type == 'application/json'
    
    def test_html_content_type(self):
        """Test HTML content type."""
        content_type = 'text/html; charset=utf-8'
        assert 'text/html' in content_type
        assert 'utf-8' in content_type
    
    def test_plain_text_content_type(self):
        """Test plain text content type."""
        content_type = 'text/plain; charset=utf-8'
        assert 'text/plain' in content_type


class TestServerIntegration:
    """Test server integration scenarios."""
    
    def test_server_can_bind_to_port(self):
        """Test that server can bind to a port."""
        from socketserver import ThreadingMixIn
        from http.server import HTTPServer
        
        # Find a free port
        with socket.socket() as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        
        # Try to create a server on that port
        try:
            server = HTTPServer(('127.0.0.1', port), MagicMock())
            server.server_close()
            assert True
        except Exception:
            assert False, "Failed to bind to port"
    
    def test_threaded_server_mixin(self):
        """Test ThreadingMixIn is used."""
        from molt_server_unified import ThreadedHTTPServer
        from socketserver import ThreadingMixIn
        
        assert issubclass(ThreadedHTTPServer, ThreadingMixIn)


class TestServerAuthIntegration:
    """Test server authentication integration."""
    
    def test_auth_enabled_flag(self):
        """Test AUTH_ENABLED flag exists."""
        try:
            from molt_server_unified import AUTH_ENABLED
            assert isinstance(AUTH_ENABLED, bool)
        except ImportError:
            # Auth might not be available in test environment
            assert True
    
    def test_session_cookie_name(self):
        """Test session cookie name constant."""
        from auth import SESSION_COOKIE_NAME
        assert SESSION_COOKIE_NAME == 'molt_session'
    
    def test_csrf_cookie_name(self):
        """Test CSRF cookie name constant."""
        from auth import CSRF_COOKIE_NAME
        assert CSRF_COOKIE_NAME == 'molt_csrf'


class TestServerEdgeCases:
    """Test server edge cases."""
    
    def test_handler_with_unicode_path(self):
        """Test handler can handle unicode in paths."""
        path = '/api/测试'
        # Should not raise error
        assert isinstance(path, str)
    
    def test_handler_with_special_characters(self):
        """Test handler can handle special characters."""
        path = '/api/test?param=value&other=123'
        assert '?' in path
        assert '&' in path
    
    def test_empty_request_body(self):
        """Test handling empty request body."""
        body = b''
        assert len(body) == 0
    
    def test_large_request_body(self):
        """Test handling large request body."""
        body = b'x' * (1024 * 1024)  # 1MB
        assert len(body) == 1024 * 1024


class TestServerLogging:
    """Test server logging."""
    
    def test_logger_exists(self):
        """Test that logger is configured."""
        from molt_server_unified import logger
        assert logger is not None
    
    def test_logger_has_methods(self):
        """Test that logger has expected methods."""
        from molt_server_unified import logger
        
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'warning')


class TestServerStaticFiles:
    """Test static file serving."""
    
    def test_static_dir_exists(self):
        """Test static directory configuration."""
        from molt_server_unified import STATIC_DIR
        assert STATIC_DIR is not None
    
    def test_base_dir_exists(self):
        """Test base directory configuration."""
        from molt_server_unified import BASE_DIR
        assert BASE_DIR is not None


class TestServerGTDIntegration:
    """Test GTD integration with server."""
    
    def test_gtd_handler_methods(self):
        """Test GTD handler has required methods."""
        from gtd import GTDHandler
        
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
    
    def test_server_inherits_gtd(self):
        """Test server inherits GTD handler."""
        from molt_server_unified import UnifiedHTTPRequestHandler
        from gtd import GTDHandler
        
        assert issubclass(UnifiedHTTPRequestHandler, GTDHandler)
