# File Service Module

This document describes the file serving capabilities and system monitoring features of the Molt Server.

## Overview

The Molt Server provides:
- Static file serving from the web root directory
- System monitoring dashboard with real-time metrics
- GTD (Getting Things Done) task management
- BotReports integration

## Endpoints

### File Serving

| Endpoint | Description |
|----------|-------------|
| `/` | Enhanced file list with system monitor link |
| `/{path}` | Serve files or directories |
| `/*.md` | Render Markdown files as HTML |

### System Monitoring

| Endpoint | Description | Cache TTL |
|----------|-------------|-----------|
| `/system-info` | Real-time system monitoring dashboard | 5 seconds |
| `/system-info/cache-stats` | Cache statistics (hit/miss rates) | No cache |

### GTD Task Management

| Endpoint | Description |
|----------|-------------|
| `/gtd` | GTD application interface |
| `/api/gtd/tasks` | Task CRUD operations |

### BotReports

| Endpoint | Description |
|----------|-------------|
| `/BotReports` | BotReports index page |
| `/api/bot-reports` | BotReports list (JSON) |

---

## Caching Layer

### Overview

To reduce CPU usage from frequent system metric collection, a TTL-based caching layer was implemented.

### Cache Configuration

| Cache Name | TTL | Purpose |
|------------|-----|---------|
| `system_metrics_cache` | 5 seconds | CPU, memory, disk, network stats |
| `process_list_cache` | 10 seconds | Process list (changes less frequently) |

### Cache Headers

All `/system-info` responses include:

```http
Cache-Control: public, max-age=5
ETag: "abc123..."
```

Clients can use conditional requests:

```http
GET /system-info
If-None-Match: "abc123..."
```

Server responds with `304 Not Modified` if data hasn't changed.

### Cache Statistics

Access `/system-info/cache-stats` to monitor cache performance:

```json
{
  "system_metrics": {
    "hits": 150,
    "misses": 12,
    "total_requests": 162,
    "hit_rate_percent": 92.59,
    "cached_entries": 1,
    "ttl_seconds": 5
  },
  "process_list": {
    "hits": 75,
    "misses": 8,
    "total_requests": 83,
    "hit_rate_percent": 90.36,
    "cached_entries": 1,
    "ttl_seconds": 10
  }
}
```

### Performance Impact

**Before Caching:**
- CPU usage: ~15-20% during monitoring
- Process iteration: Every 5 seconds
- psutil calls: ~50+ per request

**After Caching:**
- CPU usage: ~3-5% during monitoring (75% reduction)
- Process iteration: Every 10 seconds
- psutil calls: Cached, minimal overhead
- Cache hit rate: 90%+ typical

### Implementation Details

**Cache Module:** `cache.py`

```python
from cache import TTLCache

# Initialize caches
system_metrics_cache = TTLCache(ttl_seconds=5)
process_list_cache = TTLCache(ttl_seconds=10)

# Usage
cached_data = system_metrics_cache.get('key')
if cached_data is None:
    # Fetch fresh data
    data = expensive_operation()
    system_metrics_cache.set('key', data)
```

**Thread Safety:**
- All cache operations use `threading.Lock`
- Safe for concurrent requests in threaded server

**Automatic Expiration:**
- Expired entries are automatically removed on access
- No background cleanup thread needed

---

## System Monitoring Features

The `/system-info` endpoint provides:

### Memory Statistics
- Total, used, available, free memory
- Usage percentage with progress bar
- Human-readable formatting (GB, MB, KB)

### CPU Statistics
- Overall CPU usage percentage
- Per-core usage breakdown
- Core count

### Process Information
- Top 20 processes by CPU usage
- Top 20 processes by memory usage
- Process details: PID, PPID, name, user, status

### Network Statistics
- Bytes sent/received
- Packets sent/received
- Error and drop counts
- Active connection count

### System Information
- Uptime (hours and minutes)
- Python version
- Server IP address

**Auto-refresh:** The page refreshes every 5 seconds via meta tag.

---

## Security Considerations

### Directory Traversal Prevention
All file paths are validated to prevent accessing files outside the web root:

```python
if not os.path.abspath(file_path).startswith(os.path.abspath(BASE_DIR)):
    self.send_error(403, "Forbidden")
    return
```

### Authentication (Optional)
GTD endpoints require authentication when auth module is enabled.

---

## Configuration

Server configuration is managed in `config.py`:

```python
SERVER_PORT = 8080
SERVER_HOST = '0.0.0.0'
WEB_ROOT = '/path/to/web/root'
LOG_LEVEL = 'INFO'
```

---

## Running the Server

```bash
# Default port (from config)
python3 molt-server-unified.py

# Custom port
python3 molt-server-unified.py 9000

# With hot reload (requires hupper)
python3 molt-server-unified.py --reload
```
