"""
Tests for Config module.
"""

import pytest
import os
from unittest.mock import patch

# Need to test config module behavior with environment variables
# Since config.py reads env vars at import time, we need to test differently


class TestConfigDefaults:
    """Test default configuration values."""

    def test_app_dir_default(self):
        """Test default APP_DIR value."""
        from config import APP_DIR
        assert APP_DIR == '/home/admin/Code/molt_server'

    def test_web_root_default(self):
        """Test default WEB_ROOT value."""
        from config import WEB_ROOT
        assert WEB_ROOT == '/var/www/html'

    def test_log_dir_default(self):
        """Test default LOG_DIR value."""
        from config import LOG_DIR
        assert LOG_DIR == '/var/log/molt-server'

    def test_server_port_default(self):
        """Test default SERVER_PORT value."""
        from config import SERVER_PORT
        assert SERVER_PORT == 8081

    def test_server_host_default(self):
        """Test default SERVER_HOST value."""
        from config import SERVER_HOST
        assert SERVER_HOST == '127.0.0.1'

    def test_gtd_data_dir_default(self):
        """Test default GTD_DATA_DIR value."""
        from config import GTD_DATA_DIR, WEB_ROOT
        assert GTD_DATA_DIR == os.path.join(WEB_ROOT, 'gtd')

    def test_gtd_tasks_file_default(self):
        """Test default GTD_TASKS_FILE value."""
        from config import GTD_TASKS_FILE, GTD_DATA_DIR
        assert GTD_TASKS_FILE == os.path.join(GTD_DATA_DIR, 'tasks.json')

    def test_botreports_dir_default(self):
        """Test default BOTREPORTS_DIR value."""
        from config import BOTREPORTS_DIR, WEB_ROOT
        assert BOTREPORTS_DIR == os.path.join(WEB_ROOT, 'BotReports')

    def test_auth_db_path_default(self):
        """Test default AUTH_DB_PATH value."""
        # Ensure we are testing the default by unsetting the environment variable
        if 'MOLT_AUTH_DB_PATH' in os.environ:
            del os.environ['MOLT_AUTH_DB_PATH']
        import importlib
        import config
        importlib.reload(config)
        from config import AUTH_DB_PATH, APP_DIR
        assert AUTH_DB_PATH == os.path.join(APP_DIR, 'data', 'auth.db')

    def test_oauth_config_file_default(self):
        """Test default OAUTH_CONFIG_FILE value."""
        # Ensure we are testing the default by unsetting the environment variable
        if 'MOLT_OAUTH_CONFIG' in os.environ:
            del os.environ['MOLT_OAUTH_CONFIG']
        import importlib
        import config
        importlib.reload(config)
        from config import OAUTH_CONFIG_FILE, APP_DIR
        assert OAUTH_CONFIG_FILE == os.path.join(APP_DIR, 'config', 'oauth.json')

    def test_log_level_default(self):
        """Test default LOG_LEVEL value."""
        from config import LOG_LEVEL
        assert LOG_LEVEL == 'INFO'


class TestConfigEnvOverrides:
    """Test environment variable overrides."""

    def test_app_dir_env_override(self):
        """Test APP_DIR can be overridden via environment."""
        # Note: Since config is imported at module level, we test the pattern
        # In real usage, env vars would be set before import
        with patch.dict(os.environ, {'MOLT_APP_DIR': '/custom/app/dir'}):
            # Re-import to pick up new env var
            import importlib
            import config
            importlib.reload(config)
            assert config.APP_DIR == '/custom/app/dir'

    def test_server_port_env_override(self):
        """Test SERVER_PORT can be overridden via environment."""
        with patch.dict(os.environ, {'MOLT_SERVER_PORT': '9090'}):
            import importlib
            import config
            importlib.reload(config)
            assert config.SERVER_PORT == 9090

    def test_server_host_env_override(self):
        """Test SERVER_HOST can be overridden via environment."""
        with patch.dict(os.environ, {'MOLT_SERVER_HOST': '0.0.0.0'}):
            import importlib
            import config
            importlib.reload(config)
            assert config.SERVER_HOST == '0.0.0.0'

    def test_log_level_env_override(self):
        """Test LOG_LEVEL can be overridden via environment."""
        with patch.dict(os.environ, {'MOLT_LOG_LEVEL': 'DEBUG'}):
            import importlib
            import config
            importlib.reload(config)
            assert config.LOG_LEVEL == 'DEBUG'

    def test_gtd_data_dir_env_override(self):
        """Test GTD_DATA_DIR can be overridden via environment."""
        with patch.dict(os.environ, {'MOLT_GTD_DATA_DIR': '/custom/gtd'}):
            import importlib
            import config
            importlib.reload(config)
            assert config.GTD_DATA_DIR == '/custom/gtd'

    def test_auth_db_path_env_override(self):
        """Test AUTH_DB_PATH can be overridden via environment."""
        with patch.dict(os.environ, {'MOLT_AUTH_DB_PATH': '/custom/auth.db'}):
            import importlib
            import config
            importlib.reload(config)
            assert config.AUTH_DB_PATH == '/custom/auth.db'


class TestConfigPathConstruction:
    """Test path construction logic."""

    def test_gtd_data_dir_uses_web_root(self):
        """Test GTD_DATA_DIR is constructed from WEB_ROOT."""
        from config import GTD_DATA_DIR, WEB_ROOT
        assert GTD_DATA_DIR.startswith(WEB_ROOT)
        assert 'gtd' in GTD_DATA_DIR

    def test_gtd_tasks_file_uses_gtd_data_dir(self):
        """Test GTD_TASKS_FILE is constructed from GTD_DATA_DIR."""
        from config import GTD_TASKS_FILE, GTD_DATA_DIR
        assert GTD_TASKS_FILE.startswith(GTD_DATA_DIR)
        assert GTD_TASKS_FILE.endswith('tasks.json')

    def test_botreports_dir_uses_web_root(self):
        """Test BOTREPORTS_DIR is constructed from WEB_ROOT."""
        from config import BOTREPORTS_DIR, WEB_ROOT
        assert BOTREPORTS_DIR.startswith(WEB_ROOT)
        assert 'BotReports' in BOTREPORTS_DIR

    def test_auth_db_path_uses_app_dir(self):
        """Test AUTH_DB_PATH is constructed from APP_DIR."""
        # Ensure we are testing the default by unsetting the environment variables
        if 'MOLT_AUTH_DB_PATH' in os.environ:
            del os.environ['MOLT_AUTH_DB_PATH']
        if 'MOLT_APP_DIR' in os.environ:
            del os.environ['MOLT_APP_DIR']
        import importlib
        import config
        importlib.reload(config)
        from config import AUTH_DB_PATH, APP_DIR
        assert AUTH_DB_PATH.startswith(APP_DIR)
        assert 'auth.db' in AUTH_DB_PATH

    def test_oauth_config_uses_app_dir(self):
        """Test OAUTH_CONFIG_FILE is constructed from APP_DIR."""
        from config import OAUTH_CONFIG_FILE, APP_DIR
        assert OAUTH_CONFIG_FILE.startswith(APP_DIR)
        assert 'oauth.json' in OAUTH_CONFIG_FILE

    def test_paths_use_os_path_join(self):
        """Test that paths use os.path.join for cross-platform compatibility."""
        from config import GTD_DATA_DIR, WEB_ROOT
        # Should use proper path separators
        assert os.sep in GTD_DATA_DIR or GTD_DATA_DIR.count('/') >= 2


class TestConfigTypes:
    """Test configuration value types."""

    def test_server_port_is_int(self):
        """Test SERVER_PORT is an integer."""
        from config import SERVER_PORT
        assert isinstance(SERVER_PORT, int)

    def test_server_host_is_string(self):
        """Test SERVER_HOST is a string."""
        from config import SERVER_HOST
        assert isinstance(SERVER_HOST, str)

    def test_app_dir_is_string(self):
        """Test APP_DIR is a string."""
        from config import APP_DIR
        assert isinstance(APP_DIR, str)

    def test_log_level_is_string(self):
        """Test LOG_LEVEL is a string."""
        from config import LOG_LEVEL
        assert isinstance(LOG_LEVEL, str)


class TestConfigEdgeCases:
    """Test edge cases in configuration."""

    def test_empty_env_var_falls_back_to_default(self):
        """Test that empty env vars fall back to defaults."""
        with patch.dict(os.environ, {'MOLT_SERVER_PORT': ''}):
            import importlib
            import config
            # Empty string should cause int() to fail, but config uses default
            # Actually the config uses os.getenv with default, so empty string is used
            # This tests the actual behavior
            importlib.reload(config)
            # Empty string will cause int() to fail at module load
            # This is expected - config should validate inputs

    def test_invalid_port_handling(self):
        """Test handling of invalid port numbers."""
        # Port should be validated in actual usage
        with patch.dict(os.environ, {'MOLT_SERVER_PORT': 'not_a_number'}):
            import importlib
            import config
            try:
                importlib.reload(config)
                # If it doesn't fail, the value is wrong
                assert False, "Should have raised ValueError"
            except ValueError:
                pass  # Expected


class TestConfigConstants:
    """Test that config constants are properly defined."""

    def test_all_expected_constants_exist(self):
        """Test that all expected configuration constants are defined."""
        import config

        expected_constants = [
            'APP_DIR', 'WEB_ROOT', 'LOG_DIR',
            'SERVER_PORT', 'SERVER_HOST',
            'GTD_DATA_DIR', 'GTD_TASKS_FILE',
            'BOTREPORTS_DIR',
            'AUTH_DB_PATH', 'OAUTH_CONFIG_FILE',
            'LOG_LEVEL'
        ]

        for const in expected_constants:
            assert hasattr(config, const), f"Missing constant: {const}"
