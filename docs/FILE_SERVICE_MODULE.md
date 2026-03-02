# File Service Module Documentation

**Module Owner:** File Service Module Owner  
**Version:** 1.0  
**Last Updated:** 2026-03-02  
**Location:** `/home/admin/Code/molt_server/molt-server-unified.py`

---

## Table of Contents

1. [Module Architecture Overview](#module-architecture-overview)
2. [Request Routing and Handler Flow](#request-routing-and-handler-flow)
3. [Security Measures](#security-measures)
4. [Static File Serving Strategy](#static-file-serving-strategy)
5. [File Browsing Features](#file-browsing-features)
6. [Known Issues and TODOs](#known-issues-and-todos)
7. [Future Enhancement Ideas](#future-enhancement-ideas)
8. [API Reference](#api-reference)

---

## Module Architecture Overview

### Purpose

The File Service Module provides comprehensive file browsing, static file serving, and directory listing capabilities for the Molt Server project. It serves as the primary interface for accessing files stored in the web root directory (`/var/www/html/`).

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    ThreadedHTTPServer                            │
│              (ThreadingMixIn + HTTPServer)                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│           UnifiedHTTPRequestHandler                              │
│  (GTDHandler mixin + BaseHTTPRequestHandler)                     │
└─────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  File Serving   │  │  GTD Handlers   │  │ System Monitor  │
│  (This Module)  │  │   (gtd.py)      │  │   (psutil)      │
│                 │  │                 │  │                 │
│ - serve_file    │  │ - serve_gtd_*   │  │ - serve_system  │
│ - list_dir      │  │ - add_gtd_task  │  │   _info         │
│ - serve_markdown│  │ - update_gtd    │  │ - get_system    │
│ - guess_type    │  │ - clear_gtd     │  │   _info         │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Key Files

| File | Purpose | Size |
|------|---------|------|
| `molt-server-unified.py` | Main server with file handlers | ~34KB |
| `gtd.py` | GTD task management module (mixin) | ~15KB |
| `static/gtd/index.html` | GTD frontend application | ~67KB |
| `static/images/` | Favicons and static assets | - |

### Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `WEB_ROOT` | `/var/www/html` | Base directory for file serving |
| `PORT` | `8081` | Server port (command-line argument) |

### Directory Structure

```
/home/admin/Code/molt_server/
├── molt-server-unified.py      # Main file service handlers
├── gtd.py                      # GTD module (mixin)
├── static/                     # Static assets
│   ├── gtd/
│   │   └── index.html          # GTD frontend
│   └── images/
│       ├── favicon-bot.ico
│       ├── favicon-bot.png
│       └── favicon-bot.svg
└── docs/
    ├── ARCHITECTURE.md         # System architecture
    └── FILE_SERVICE_MODULE.md  # This document

/var/www/html/                  # Web root (BASE_DIR)
├── BotReports/                 # Bot report storage
│   ├── index.html
│   ├── *.html (reports)
│   ├── *.mp3 (audio)
│   └── *.md (source)
├── kodexplorer/                # File manager (Apache-served)
├── gtd/                        # GTD data
│   └── tasks.json
├── audio/                      # Audio files
├── backups/                    # Backup storage
├── docs/                       # Web documentation
├── sop/                        # Standard Operating Procedures
└── index.html                  # Landing page
```

---

## Request Routing and Handler Flow

### Request Flow Diagram

```
Client Request (HTTP)
        │
        ▼
┌───────────────────┐
│    Apache         │  Port 80/443
│  (Reverse Proxy)  │
└───────────────────┘
        │
        │ ProxyPass Rules
        ▼
┌───────────────────┐
│   Python Server   │  Port 8081
│   (molt-server)   │
└───────────────────┘
        │
        ├─────────────────────────────────────────────────────┐
        │                                                     │
        ▼                                                     ▼
┌───────────────────┐                             ┌───────────────────┐
│  do_GET()         │                             │  do_POST/PUT/DEL  │
│  Path Matching    │                             │  GTD API Only     │
└───────────────────┘                             └───────────────────┘
        │
        ├─→ /favicon.ico      → serve_favicon()
        ├─→ /system-info      → serve_system_info()
        ├─→ /api/bot-reports  → serve_bot_reports_list()
        ├─→ /BotReports       → serve_bot_reports_index()
        ├─→ /api/gtd/tasks    → GTDHandler.serve_gtd_tasks()
        ├─→ /gtd              → GTDHandler.serve_gtd_app()
        ├─→ /gtd/*            → GTDHandler.serve_gtd_static()
        ├─→ /kodexplorer/*    → proxy_to_apache()
        ├─→ / or /index.html  → serve_enhanced_file_list()
        └─→ /*                → serve_file_or_directory()
```

### Handler Methods

#### Primary File Service Handlers

| Method | Purpose | Returns |
|--------|---------|---------|
| `do_GET(path)` | Route GET requests to appropriate handler | HTML/JSON/File |
| `serve_file_or_directory(path)` | Serve file or list directory | File content or HTML |
| `serve_enhanced_file_list(path)` | Generate enhanced directory listing | HTML |
| `serve_file(file_path)` | Serve individual file | Binary content |
| `serve_markdown_file(file_path)` | Render Markdown as HTML | HTML |
| `list_directory(path)` | List directory contents | HTML (via enhanced list) |
| `guess_type(path)` | Determine MIME type | Content-Type string |

#### Helper Methods

| Method | Purpose |
|--------|---------|
| `_generate_parent_link(current_path)` | Generate "up one level" navigation |
| `_generate_file_rows(items)` | Generate HTML table rows for files |
| `format_bytes(bytes_value)` | Convert bytes to human-readable format |
| `is_port_open(host, port)` | Check if a port is listening |
| `proxy_to_apache(path)` | Forward requests to Apache on port 8080 |

### Request Routing Table

| Path Pattern | Handler | Response Type |
|--------------|---------|---------------|
| `/` | `serve_enhanced_file_list('/')` | HTML directory listing |
| `/*` (directory) | `list_directory()` | HTML directory listing |
| `/*` (file) | `serve_file()` | File content |
| `/*.md` | `serve_markdown_file()` | Rendered HTML |
| `/favicon.ico` | `serve_favicon()` | ICO image |
| `/system-info` | `serve_system_info()` | HTML dashboard |
| `/gtd` | `serve_gtd_app()` | HTML application |
| `/gtd/*` | `serve_gtd_static()` | Static assets |
| `/api/gtd/tasks` | `serve_gtd_tasks()` | JSON |
| `/BotReports` | `serve_bot_reports_index()` | HTML |
| `/api/bot-reports` | `serve_bot_reports_list()` | JSON |
| `/kodexplorer/*` | `proxy_to_apache()` | Proxied content |

---

## Security Measures

### Current Security Implementations

#### 1. Path Traversal Prevention ✅

**Location:** `serve_file_or_directory()`

```python
# Security check - prevent directory traversal
if not os.path.abspath(file_path).startswith(os.path.abspath(BASE_DIR)):
    self.send_error(403, "Forbidden")
    return
```

**How it works:**
- Resolves the absolute path of the requested file
- Compares against the absolute path of `BASE_DIR` (`/var/www/html`)
- Rejects any request that resolves outside the web root
- Prevents `../` attacks and symlink-based escapes

**Effectiveness:** ✅ Strong - Uses `os.path.abspath()` which normalizes paths

#### 2. UTF-8 Error Pages ✅

**Location:** `send_error()` override

```python
# HTML error page with UTF-8 encoding
content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{code} {message}</title>
</head>
...
"""
```

**Purpose:** Prevents encoding issues and ensures error messages display correctly for international users.

#### 3. Content-Length Headers ✅

All responses include proper `Content-Length` headers to prevent response splitting attacks.

#### 4. Connection Management ✅

```python
self.send_header('Connection', 'close')
```

Ensures connections are properly closed after each response.

### Security Gaps and Concerns 🔴

#### 1. No Authentication/Authorization

**Risk:** HIGH  
**Impact:** All files and endpoints are publicly accessible

**Current State:**
- Anyone can browse `/var/www/html/`
- GTD tasks visible to anyone
- System metrics exposed at `/system-info`
- BotReports accessible without authentication

**Recommendation:**
```python
# Add basic auth decorator or middleware
def require_auth(handler):
    def wrapper(self, *args, **kwargs):
        auth = self.headers.get('Authorization')
        if not auth or not check_credentials(auth):
            self.send_error(401, "Unauthorized")
            return
        return handler(self, *args, **kwargs)
    return wrapper
```

#### 2. No Input Validation on API Endpoints

**Risk:** MEDIUM  
**Impact:** Malformed JSON could cause server errors

**Current State:**
```python
# GTD API accepts arbitrary JSON
post_data = self.rfile.read(content_length).decode('utf-8')
task_data = json.loads(post_data)  # No schema validation
```

**Recommendation:**
- Add JSON schema validation
- Limit field lengths
- Sanitize user input

#### 3. No Rate Limiting

**Risk:** MEDIUM  
**Impact:** Server vulnerable to DoS attacks

**Current State:** No rate limiting implemented

**Recommendation:**
```python
# Add simple rate limiting
from collections import defaultdict
import time

request_times = defaultdict(list)

def rate_limit(ip, max_requests=100, window=60):
    now = time.time()
    request_times[ip] = [t for t in request_times[ip] if now - t < window]
    if len(request_times[ip]) >= max_requests:
        return False
    request_times[ip].append(now)
    return True
```

#### 4. No HTTPS Support (Python Layer)

**Risk:** MEDIUM (mitigated by Apache)  
**Impact:** Data transmitted in cleartext if accessed directly

**Current State:** Python server only supports HTTP

**Mitigation:** Apache handles TLS termination (recommended approach)

**Recommendation:** Document that direct access to port 8081 should be blocked by firewall.

#### 5. Directory Listing Enabled by Default

**Risk:** LOW-MEDIUM  
**Impact:** Internal file structure exposed

**Current State:** All directories are listable

**Recommendation:**
- Add `.noindex` file support to disable listing
- Exclude sensitive directories (e.g., `backups/`, `.git/`)

#### 6. No File Upload Validation

**Risk:** HIGH (if upload feature added)  
**Impact:** Currently no upload feature, but if added:
- No file type validation
- No size limits
- No malware scanning

**Recommendation:** If upload feature is added:
- Whitelist allowed extensions
- Enforce file size limits
- Scan for malware
- Store uploads outside web root

#### 7. Symlink Following

**Risk:** MEDIUM  
**Impact:** Symlinks could escape web root

**Current State:** `os.path.isfile()` and `os.path.isdir()` follow symlinks

**Current Mitigation:** Path traversal check uses `os.path.abspath()` which resolves symlinks

**Recommendation:** Add explicit symlink detection:
```python
if os.path.islink(file_path):
    # Optionally reject symlinks or validate target
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(os.path.abspath(BASE_DIR)):
        self.send_error(403, "Forbidden")
```

### Security Checklist

| Security Measure | Status | Priority |
|-----------------|--------|----------|
| Path traversal prevention | ✅ Implemented | - |
| UTF-8 encoding | ✅ Implemented | - |
| Authentication | ❌ Missing | HIGH |
| Input validation | ❌ Missing | MEDIUM |
| Rate limiting | ❌ Missing | MEDIUM |
| HTTPS (Python layer) | ❌ Missing | LOW (Apache handles) |
| Symlink validation | ⚠️ Partial | MEDIUM |
| Directory listing control | ❌ Missing | LOW |
| Upload validation | N/A | - |

---

## Static File Serving Strategy

### Serving Approaches

The Molt Server uses a **hybrid approach** for static file serving:

#### 1. Python-Served Static Files

**Location:** `/home/admin/Code/molt_server/static/`

**Served via:**
- `serve_gtd_static()` - GTD frontend assets
- `serve_favicon()` - Favicon

**Characteristics:**
- Bundled with application code
- Version-controlled
- Served directly by Python server

#### 2. Web Root Static Files

**Location:** `/var/www/html/`

**Served via:**
- `serve_file_or_directory()` - General file serving
- `serve_markdown_file()` - Markdown rendering

**Characteristics:**
- User-generated content
- BotReports storage
- KodExplorer files
- Backups and archives

#### 3. Apache-Served Static Files

**Location:** `/var/www/html/kodexplorer/`, `/var/www/html/BotReports/`

**Served via:** Apache direct filesystem access (Aliased)

**Characteristics:**
- Large files (MP3s, archives)
- High-traffic content
- Bypasses Python for performance

### Apache Reverse Proxy Configuration

```apache
# Selective proxying - some paths served directly by Apache
ProxyPass /kodexplorer/ !          # Direct filesystem
ProxyPass /BotReports/ !           # Direct filesystem
ProxyPass /system-info http://127.0.0.1:8081/system-info
ProxyPass /api/gtd/ http://127.0.0.1:8081/api/gtd/
ProxyPass / http://127.0.0.1:8081/

# Direct filesystem serving for performance
Alias /kodexplorer /var/www/html/kodexplorer
Alias /BotReports /var/www/html/BotReports
```

### MIME Type Handling

**Location:** `guess_type()` method

```python
def guess_type(self, path):
    """Simple MIME type guessing"""
    if path.endswith('.html') or path.endswith('.htm'):
        return 'text/html'
    elif path.endswith('.css'):
        return 'text/css'
    elif path.endswith('.js'):
        return 'application/javascript'
    elif path.endswith('.json'):
        return 'application/json'
    elif path.endswith('.png'):
        return 'image/png'
    elif path.endswith('.jpg') or path.endswith('.jpeg'):
        return 'image/jpeg'
    elif path.endswith('.gif'):
        return 'image/gif'
    elif path.endswith('.ico'):
        return 'image/x-icon'
    elif path.endswith('.txt'):
        return 'text/plain'
    elif path.endswith('.md') or path.endswith('.markdown'):
        return 'text/markdown'
    else:
        return 'application/octet-stream'
```

**Limitations:**
- Limited MIME type support
- No `mimetypes` module usage
- Binary files default to `application/octet-stream`

**Recommendation:** Use Python's built-in `mimetypes` module:
```python
import mimetypes
content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
```

### Caching Strategy

| Content Type | Cache-Control | Rationale |
|--------------|---------------|-----------|
| Favicon | `public, max-age=86400` | Rarely changes, cache 24h |
| BotReports API | `no-cache` | Dynamic content |
| System Info | N/A (meta refresh) | Auto-refresh every 5s |
| Static files | None set | Should add caching headers |
| HTML pages | None set | Should add caching headers |

**Recommendation:** Add caching headers for static assets:
```python
# For static assets (CSS, JS, images)
if is_static_asset(file_path):
    self.send_header('Cache-Control', 'public, max-age=31536000')  # 1 year
    self.send_header('ETag', generate_etag(content))
```

### Markdown Rendering

**Feature:** `.md` and `.markdown` files are automatically rendered as HTML

**Implementation:**
```python
def serve_markdown_file(self, file_path):
    """Render Markdown file as HTML"""
    import markdown
    with open(file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    html_content = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
    # ... wrap in HTML template
```

**Extensions:**
- `fenced_code` - Code blocks with triple backticks
- `tables` - Markdown tables

**Fallback:** If `markdown` module not installed, serves as plain text

**Security:** Uses `markdown` library (safe by default, no raw HTML unless enabled)

---

## File Browsing Features

### Enhanced Directory Listing

**Features:**
- ✅ File/folder icons (📁 📄)
- ✅ File size (human-readable: B, KB, MB)
- ✅ Modification timestamps
- ✅ Directory-first sorting
- ✅ Case-insensitive alphabetical sorting
- ✅ Parent directory navigation
- ✅ Quick links to system tools

### Quick Links

Every directory listing includes:

```html
<a href="/system-info" class="monitor-link">📊 实时系统监控</a>
<a href="http://bot.xjbcode.fun:18789" class="webui-link">🤖 Moltbot WebUI</a>
<a href="/gtd" class="gtd-link">✅ GTD 任务管理</a>
```

### Responsive Design

- Max-width container (1200px)
- Clean table layout
- Hover effects on rows
- Mobile-friendly (basic)

### File Information Display

| Column | Format | Example |
|--------|--------|---------|
| Name | Icon + Link | 📁 `documents/` |
| Size | Human-readable | `2.5 MB`, `128 B`, `-` (dirs) |
| Modified | ISO format | `2026-03-02 08:42:15` |

---

## Known Issues and TODOs

### Critical Issues 🔴

#### 1. KodExplorer Proxy Loop

**Issue:** `/kodexplorer` requests proxy Python → Apache → filesystem, but Apache also serves KodExplorer directly.

**Impact:**
- Unnecessary network hop
- Potential for circular proxy
- Configuration complexity

**Current Code:**
```python
elif path.startswith('/kodexplorer'):
    if self.is_port_open('localhost', 8080):
        return self.proxy_to_apache(path)
    else:
        return self.serve_file_or_directory(path)
```

**TODO:** 
- [ ] Remove Python proxy code for KodExplorer
- [ ] Serve entirely through Apache
- [ ] Update Apache config to handle all KodExplorer traffic

#### 2. No Authentication

**Issue:** All endpoints publicly accessible

**Impact:** Security risk - anyone can access files, GTD tasks, system info

**TODO:**
- [ ] Implement basic auth or token-based auth
- [ ] Add IP whitelist option
- [ ] Create auth middleware

### Medium Priority Issues 🟡

#### 3. Hardcoded Paths

**Issue:** Paths like `/var/www/html` hardcoded in multiple places

**Impact:** Difficult to relocate, environment-specific

**Locations:**
- `BASE_DIR = os.environ.get('WEB_ROOT', '/var/www/html')`
- `GTD_TASKS_FILE = os.path.join(BASE_DIR, 'gtd', 'tasks.json')`

**TODO:**
- [ ] Move all paths to environment variables
- [ ] Create config file support (`.env` or JSON)
- [ ] Document required environment variables

#### 4. No Logging

**Issue:** Only `print()` statements, no structured logging

**Impact:** Difficult debugging, no audit trail

**TODO:**
- [ ] Implement Python `logging` module
- [ ] Add log file rotation
- [ ] Log all requests (access log)
- [ ] Log errors separately (error log)

#### 5. Limited MIME Type Support

**Issue:** Custom `guess_type()` with limited types

**Impact:** Some files served with wrong content type

**TODO:**
- [ ] Use `mimetypes` module
- [ ] Add custom MIME type overrides
- [ ] Support more file types

#### 6. No Caching for Static Assets

**Issue:** Static files served without cache headers

**Impact:** Poor performance, unnecessary bandwidth

**TODO:**
- [ ] Add `Cache-Control` headers
- [ ] Implement ETag support
- [ ] Add `Last-Modified` headers

#### 7. Memory Usage in System Monitor

**Issue:** Fetches ALL processes every request (5s refresh)

**Impact:** High CPU on process-heavy systems

**TODO:**
- [ ] Cache process list with TTL (10s)
- [ ] Paginate process lists
- [ ] Add filtering options

### Low Priority Issues 🟢

#### 8. Legacy Markdown Support in GTD

**Issue:** `gtd.py` includes unused Markdown parsing code

**Impact:** Code complexity, maintenance overhead

**TODO:**
- [ ] Deprecate Markdown support
- [ ] Remove `parse_markdown_to_json()`
- [ ] Remove `generate_markdown_with_comments()`

#### 9. Dual Source Structure

**Issue:** Both `molt-server-unified.py` and `src/molt_server/server.py` exist

**Impact:** Confusion, potential divergence

**TODO:**
- [ ] Remove `src/` directory
- [ ] Document canonical source location

#### 10. GTD Frontend Size

**Issue:** `static/gtd/index.html` is 67KB single file

**Impact:** Initial load time, maintainability

**TODO:**
- [ ] Split into CSS/JS files
- [ ] Minify for production
- [ ] Add code splitting

### Documentation TODOs

- [ ] Add API documentation (OpenAPI/Swagger)
- [ ] Document deployment troubleshooting
- [ ] Create security hardening guide
- [ ] Add performance tuning guide

---

## Future Enhancement Ideas

### Short-term (1-3 months)

#### 1. File Upload Support

**Feature:** Allow users to upload files via web interface

**Implementation:**
```python
def do_POST(self):
    if path.startswith('/upload'):
        return self.handle_file_upload()

def handle_file_upload(self):
    # Parse multipart form data
    # Validate file type and size
    # Save to designated upload directory
    # Return success/failure response
```

**Requirements:**
- File type whitelist
- Size limits (configurable)
- Virus scanning (ClamAV integration)
- Upload progress tracking

#### 2. Search Functionality

**Feature:** Search files by name/content

**Implementation:**
- Client-side search for file names
- Server-side search using `grep` or `ripgrep`
- Index-based search for large directories

#### 3. Batch Operations

**Feature:** Select multiple files for operations

**Operations:**
- Batch download (ZIP archive)
- Batch delete
- Batch move/copy

#### 4. Improved Caching

**Feature:** Smart caching for static assets

**Implementation:**
- ETag generation
- `If-None-Match` support
- Browser caching headers

### Medium-term (3-6 months)

#### 5. User Quotas

**Feature:** Limit disk usage per user

**Implementation:**
- Track directory sizes
- Enforce quotas on upload
- Warning notifications

#### 6. File Versioning

**Feature:** Keep history of file changes

**Implementation:**
- Automatic versioning on upload
- Version browser UI
- Restore previous versions

#### 7. Shareable Links

**Feature:** Generate temporary share links

**Implementation:**
- Token-based access
- Expiration dates
- Password protection option
- Download tracking

#### 8. WebDAV Support

**Feature:** Mount web root as network drive

**Implementation:**
- Add WebDAV protocol support
- Compatible with Windows/Mac/Linux
- Authentication integration

### Long-term (6-12 months)

#### 9. Real-time File Sync

**Feature:** WebSocket-based file change notifications

**Implementation:**
- WebSocket server integration
- Client-side auto-refresh
- Collaborative editing support

#### 10. Plugin System

**Feature:** Extensible file handlers

**Examples:**
- Image thumbnail generation
- Video transcoding
- Document preview (PDF, Office)
- Code syntax highlighting

#### 11. Database Backend

**Feature:** Replace JSON with SQLite/PostgreSQL

**Benefits:**
- Better query performance
- Transaction support
- Concurrent access
- Advanced search capabilities

#### 12. Mobile App

**Feature:** React Native mobile client

**Features:**
- Offline file access
- Camera upload
- Push notifications
- Biometric auth

---

## API Reference

### File Service Endpoints

#### GET `/`

List root directory contents.

**Response:** HTML directory listing

#### GET `/{path}`

List directory or serve file at `{path}`.

**Response:** HTML (directory) or file content

#### GET `/favicon.ico`

Serve favicon.

**Response:** ICO image

#### GET `/system-info`

Real-time system monitoring dashboard.

**Response:** HTML (auto-refreshes every 5s)

### BotReports Endpoints

#### GET `/BotReports`

Serve BotReports index page.

**Response:** HTML

#### GET `/api/bot-reports`

List available BotReports.

**Response:**
```json
[
  {"filename": "2026-03-02-daily-news.html", "date": "1740902400"},
  {"filename": "2026-03-01-daily-news.html", "date": "1740816000"}
]
```

### GTD Endpoints

#### GET `/api/gtd/tasks`

Retrieve all GTD tasks.

**Response:**
```json
{
  "projects": [...],
  "next_actions": [...],
  "waiting_for": [...],
  "someday_maybe": [...]
}
```

#### POST `/api/gtd/tasks`

Add new task.

**Request:**
```json
{
  "category": "projects",
  "text": "Task description"
}
```

**Response:** `201 Created`

#### PUT `/api/gtd/tasks`

Update all tasks.

**Request:** Full tasks JSON or Markdown

**Response:** `200 OK`

#### DELETE `/api/gtd/tasks`

Clear all tasks.

**Response:** `200 OK`

#### GET `/api/gtd/title?url={url}`

Extract title from URL.

**Response:**
```json
{"title": "Page Title"}
```

---

## Troubleshooting

### Common Issues

#### 1. "403 Forbidden" on File Access

**Cause:** Path traversal check blocked request

**Solution:**
- Ensure file is within `/var/www/html/`
- Check for symlinks pointing outside web root
- Verify file permissions

#### 2. Markdown Files Not Rendering

**Cause:** `markdown` module not installed

**Solution:**
```bash
pip install markdown
```

#### 3. KodExplorer Not Loading

**Cause:** Apache not running on port 8080

**Solution:**
```bash
sudo systemctl status httpd
sudo systemctl start httpd
```

#### 4. System Monitor Shows No Processes

**Cause:** Permission issues with `psutil`

**Solution:**
- Run server as user with process access
- Check `psutil` installation

### Log Locations

| Log Type | Location |
|----------|----------|
| Server stdout | `journalctl -u molt-server` |
| Apache access | `/var/log/httpd/access_log` |
| Apache error | `/var/log/httpd/error_log` |

### Performance Tuning

#### Increase Thread Pool

```python
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True  # Don't block on exit
```

#### Enable Compression

Add to Apache config:
```apache
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/plain text/css application/javascript
</IfModule>
```

#### Optimize Static File Serving

Move more static content to Apache direct serving (bypass Python proxy).

---

## Appendix

### A. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEB_ROOT` | `/var/www/html` | Base directory for file serving |
| `PORT` | `8081` | Server port (CLI argument) |

### B. File Permissions

```
/var/www/html/          webserver:web   775
/var/www/html/BotReports/ admin:web     775
/home/admin/Code/molt_server/ admin:admin 755
```

### C. Dependencies

**Python Packages:**
```
psutil          # System monitoring
requests        # HTTP client
beautifulsoup4  # HTML parsing (optional)
markdown        # Markdown rendering (optional)
```

### D. Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development guide

---

**Document Status:** ✅ Complete  
**Next Review:** 2026-06-02  
**Module Owner:** File Service Module Owner
