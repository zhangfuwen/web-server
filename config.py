import os

# Application settings
APP_DIR = os.getenv('MOLT_APP_DIR', '/home/admin/Code/molt_server')
WEB_ROOT = os.getenv('MOLT_WEB_ROOT', '/var/www/html')
LOG_DIR = os.getenv('MOLT_LOG_DIR', '/var/log/molt-server')

# Server settings
SERVER_PORT = int(os.getenv('MOLT_SERVER_PORT', '8081'))
SERVER_HOST = os.getenv('MOLT_SERVER_HOST', '127.0.0.1')

# GTD settings
GTD_DATA_DIR = os.getenv('MOLT_GTD_DATA_DIR', os.path.join(WEB_ROOT, 'gtd'))
GTD_TASKS_FILE = os.getenv('MOLT_GTD_TASKS_FILE', os.path.join(GTD_DATA_DIR, 'tasks.json'))

# BotReports settings
BOTREPORTS_DIR = os.getenv('MOLT_BOTREPORTS_DIR', os.path.join(WEB_ROOT, 'BotReports'))

# Auth settings
AUTH_DB_PATH = os.getenv('MOLT_AUTH_DB_PATH', os.path.join(APP_DIR, 'data', 'auth.db'))
OAUTH_CONFIG_FILE = os.getenv('MOLT_OAUTH_CONFIG', os.path.join(APP_DIR, 'config', 'oauth.json'))

# Clock-in settings
CLOCK_IN_DB_PATH = os.getenv('MOLT_CLOCK_IN_DB_PATH', os.path.join(APP_DIR, 'data', 'clock_in.db'))

# Logging
LOG_LEVEL = os.getenv('MOLT_LOG_LEVEL', 'INFO')
