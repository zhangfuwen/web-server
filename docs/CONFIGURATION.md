# Molt Server Configuration

This document describes how to configure Molt Server using environment variables.

## Overview

Molt Server supports configuration through environment variables, allowing for flexible deployment across different environments without modifying source code.

## Environment Variables

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MOLT_APP_DIR` | `/home/admin/Code/molt_server` | Application root directory |
| `MOLT_WEB_ROOT` | `/var/www/html` | Web root directory for static files |
| `MOLT_LOG_DIR` | `/var/log/molt-server` | Directory for log files |

### Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MOLT_SERVER_PORT` | `8081` | HTTP server port |
| `MOLT_SERVER_HOST` | `127.0.0.1` | HTTP server bind address |

### GTD (Getting Things Done) Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MOLT_GTD_DATA_DIR` | `${MOLT_WEB_ROOT}/gtd` | GTD data directory |
| `MOLT_GTD_TASKS_FILE` | `${MOLT_GTD_DATA_DIR}/tasks.json` | GTD tasks JSON file path |

### BotReports Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MOLT_BOTREPORTS_DIR` | `${MOLT_WEB_ROOT}/BotReports` | BotReports directory |

### Authentication Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MOLT_AUTH_DB_PATH` | `${MOLT_APP_DIR}/data/auth.db` | SQLite database for authentication |
| `MOLT_OAUTH_CONFIG` | `${MOLT_APP_DIR}/config/oauth.json` | OAuth configuration file |

### Logging Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MOLT_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

### OAuth Credentials

These must be set for authentication to work:

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLIENT_ID` | Yes (for Google login) | Google OAuth 2.0 client ID |
| `GOOGLE_CLIENT_SECRET` | Yes (for Google login) | Google OAuth 2.0 client secret |
| `GOOGLE_REDIRECT_URI` | Yes (for Google login) | Google OAuth redirect URI |
| `WECHAT_APP_ID` | Yes (for WeChat login) | WeChat OAuth 2.0 app ID |
| `WECHAT_APP_SECRET` | Yes (for WeChat login) | WeChat OAuth 2.0 app secret |
| `WECHAT_REDIRECT_URI` | Yes (for WeChat login) | WeChat OAuth redirect URI |

## Configuration Files

### config/config.example

A template configuration file is provided at `config/config.example`. Copy this file to customize your environment:

```bash
cd /home/admin/Code/molt_server
cp config/config.example config/config.env
# Edit config/config.env with your settings
```

### Loading Configuration

To load environment variables from a config file, use:

```bash
# In systemd service (recommended)
EnvironmentFile=/home/admin/Code/molt_server/config/config.env

# Or manually source it
set -a
source /home/admin/Code/molt_server/config/config.env
set +a
```

## Systemd Service Configuration

The systemd service file should be configured to use environment variables:

```ini
[Unit]
Description=Molt Server with GTD Task Management
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/Code/molt_server
EnvironmentFile=/home/admin/Code/molt_server/config/config.env
ExecStart=/usr/bin/python3.11 /home/admin/Code/molt_server/molt-server-unified.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Example: Custom Deployment

For a custom deployment with different paths:

```bash
export MOLT_APP_DIR=/opt/molt_server
export MOLT_WEB_ROOT=/srv/www
export MOLT_LOG_DIR=/var/log/molt
export MOLT_SERVER_PORT=9000
export MOLT_SERVER_HOST=0.0.0.0

python3 /opt/molt_server/molt-server-unified.py
```

## Security Notes

- Never commit `config.env` or `oauth.json` to version control
- Use appropriate file permissions for configuration files containing secrets
- Consider using a secrets manager for production deployments
- Set `MOLT_SERVER_HOST=127.0.0.1` unless you need external access (use a reverse proxy instead)
