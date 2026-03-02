# Molt Server Logging Guide

## Overview

Molt Server uses Python's built-in `logging` module with structured, rotating file logs for production-ready logging.

## Configuration

### Setup

Logging is automatically initialized when the server starts via `logging_config.py`.

```python
from logging_config import setup_logging
logger = setup_logging()
```

### Log Location

- **Default directory:** `/var/log/molt-server/`
- **Log file:** `/var/log/molt-server/molt-server.log`
- **Permissions:** 755 (readable by all, writable by root)

### Log Rotation

- **Max file size:** 10MB
- **Backup count:** 5 rotated files
- **Format:** `%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s`

## Log Levels

| Level | Usage |
|-------|-------|
| `logger.info()` | General operational events (server start, requests, etc.) |
| `logger.warning()` | Unexpected events that don't stop operation |
| `logger.error()` | Errors that prevent operation (auth failures, file errors) |
| `logger.debug()` | Detailed diagnostic information (development only) |

## Usage Examples

### Basic Logging

```python
logger.info("Server started on port 8081")
logger.error(f"Failed to load config: {error_message}")
logger.warning("Deprecated API endpoint accessed")
```

### Custom Log Level

```python
from logging_config import setup_logging
import logging

# Set to DEBUG for development
logger = setup_logging(level=logging.DEBUG)
```

### Custom Log Directory

```python
logger = setup_logging(log_dir='/custom/log/path')
```

## Viewing Logs

### Real-time Monitoring

```bash
# Follow live logs
sudo tail -f /var/log/molt-server/molt-server.log

# View last 100 lines
sudo tail -n 100 /var/log/molt-server/molt-server.log

# Search for errors
sudo grep "ERROR" /var/log/molt-server/molt-server.log
```

### Rotated Logs

Old logs are rotated with numeric suffixes:
- `molt-server.log` (current)
- `molt-server.log.1` (most recent rotated)
- `molt-server.log.2` (older)
- ... up to `molt-server.log.5`

## Console Output

During development, logs are also output to the console with the same format. This helps with debugging without needing to check log files.

## Best Practices

1. **Use appropriate log levels:** Don't log everything as INFO
2. **Include context:** Add relevant details (user IDs, file paths, etc.)
3. **Avoid sensitive data:** Never log passwords, tokens, or PII
4. **Use structured messages:** Keep log messages consistent and searchable

## Troubleshooting

### Logs Not Appearing

1. Check directory permissions: `ls -la /var/log/molt-server/`
2. Verify the logger is initialized before use
3. Check log level settings

### Disk Space Issues

If logs are consuming too much space:
1. Check rotation is working: `ls -lh /var/log/molt-server/`
2. Manually archive old logs: `sudo tar -czf molt-logs-backup.tar.gz /var/log/molt-server/`
3. Clear old backups if needed

## Integration

The logging system integrates with:
- **Authentication module:** Logs auth successes/failures
- **GTD module:** Logs task operations
- **HTTP server:** Logs server startup and errors
- **System monitor:** Logs monitoring events
