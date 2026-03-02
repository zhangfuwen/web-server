# Molt Server Architecture

**Version:** 1.0  
**Last Updated:** 2026-03-02  
**Author:** Molt Server Architecture Designer

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Deployment Architecture](#deployment-architecture)
5. [Data Flow](#data-flow)
6. [GTD System Architecture](#gtd-system-architecture)
7. [BotReports Integration](#botreports-integration)
8. [Frontend Architecture](#frontend-architecture)
9. [Current Issues & Technical Debt](#current-issues--technical-debt)
10. [Future Improvements](#future-improvements)

---

## Overview

This web server is a **unified Python HTTP server** built on Python's built-in `http.server` module with threading support. It provides:

- **File browsing** with enhanced directory listings
- **Static file serving** for web assets
- **GTD (Getting Things Done)** task management system
- **System monitoring** dashboard with real-time metrics
- **BotReports** integration for automated report generation
- **KodExplorer** file manager support

The server runs on **port 8081** and is fronted by **Apache** as a reverse proxy for production access.

### Key Technologies

| Component | Technology |
|-----------|------------|
| HTTP Server | Python `http.server` + `socketserver.ThreadingMixIn` |
| Reverse Proxy | Apache (mod_proxy) |
| Service Management | systemd |
| GTD Storage | JSON (migrated from Markdown) |
| Frontend | Vanilla HTML/CSS/JavaScript |
| System Monitoring | `psutil` library |

---

## Project Structure

```
/home/admin/Code/molt_server/
├── molt-server-unified.py      # Main server entry point (34KB)
├── gtd.py                     # GTD module with request handlers (15KB)
├── README.md                  # User-facing documentation
├── DEPLOYMENT.md              # Deployment instructions
├── requirements.txt           # Python dependencies
├── setup.py                   # Python package configuration
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # This file
│   ├── DEVELOPMENT.md         # Development guide
│   ├── DEPLOYMENT.md          # Deployment guide (duplicate)
│   ├── CODING_STANDARDS.md    # Code style guide
│   ├── COMMIT_GUIDELINES.md   # Git commit conventions
│   └── README.md              # Docs index
│
├── static/                    # Static assets served by Python server
│   ├── gtd/
│   │   └── index.html         # GTD frontend (67KB, modern UI)
│   └── images/
│       ├── favicon-bot.ico
│       ├── favicon-bot.png
│       └── favicon-bot.svg
│
├── gtd/                       # GTD data directory
│   ├── tasks.json             # Current task storage (JSON format)
│   └── tasks.md               # Legacy Markdown format (deprecated)
│
├── botreports/                # BotReports frontend
│   └── index.html             # Report listing interface (12KB)
│
├── src/                       # Alternative source structure (legacy)
│   └── molt_server/
│       ├── __init__.py
│       ├── server.py          # Legacy server module
│       └── gtd.py             # Legacy GTD module
│
├── config/                    # Configuration examples
├── data/                      # Example data files
├── scripts/                   # Deployment scripts
│   ├── install.sh
│   └── uninstall.sh
└── __pycache__/               # Python bytecode cache
```

### Web Root Structure (`/var/www/html/`)

```
/var/www/html/
├── index.html                 # Default landing page
├── BotReports/                # Bot reports storage & serving
│   ├── index.html             # Report browser frontend
│   ├── *.html                 # Generated reports (daily news, kernel patches, etc.)
│   ├── *.mp3                  # Audio versions of reports
│   ├── *.md                   # Markdown source files
│   └── audios/                # Audio archive
│
├── gtd/                       # GTD web-accessible data
│   ├── tasks.md               # Legacy task file
│   └── index.html             # Alternative GTD frontend
│
├── kodexplorer/               # KodExplorer file manager
│   └── ...                    # Full KodExplorer installation
│
├── audio/                     # Audio files
├── backups/                   # Backup storage
├── docs/                      # Web-accessible documentation
└── sop/                       # Standard Operating Procedures
```

---

## Core Components

### 1. Main Server (`molt-server-unified.py`)

**Purpose:** Unified HTTP request handler combining file serving, GTD, and system monitoring.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    ThreadedHTTPServer                        │
│              (ThreadingMixIn + HTTPServer)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              UnifiedHTTPRequestHandler                       │
│         (GTDHandler mixin + BaseHTTPRequestHandler)          │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  File Serving │   │   GTD Handlers  │   │ System Monitor  │
│  - serve_file │   │  - serve_gtd_*  │   │ - get_system_*  │
│  - list_dir   │   │  - add_gtd_*    │   │ - serve_system  │
│  - markdown   │   │  - update_gtd   │   │   _info         │
└───────────────┘   └─────────────────┘   └─────────────────┘
```

**Key Features:**
- **Threaded request handling** via `ThreadingMixIn`
- **UTF-8 error pages** with custom `send_error()` override
- **Markdown rendering** - converts `.md` files to HTML on-the-fly
- **Enhanced directory listings** with system monitor links
- **Proxy support** for KodExplorer (forwards to Apache on port 8080)

**Request Routing:**

| Path | Handler | Description |
|------|---------|-------------|
| `/` | `serve_enhanced_file_list()` | Enhanced directory browser |
| `/favicon.ico` | `serve_favicon()` | Site favicon |
| `/system-info` | `serve_system_info()` | Real-time system monitoring |
| `/gtd` | `serve_gtd_app()` | GTD task management UI |
| `/gtd/*` | `serve_gtd_static()` | GTD static assets |
| `/api/gtd/tasks` | `serve_gtd_tasks()` / `add_gtd_task()` | GTD REST API |
| `/api/gtd/title` | `extract_title_api()` | URL title extraction |
| `/BotReports` | `serve_bot_reports_index()` | BotReports browser |
| `/api/bot-reports` | `serve_bot_reports_list()` | BotReports JSON API |
| `/kodexplorer/*` | `proxy_to_apache()` | Proxy to Apache (port 8080) |

### 2. GTD Module (`gtd.py`)

**Purpose:** Getting Things Done task management system with JSON storage and REST API.

**Data Structure:**
```json
{
  "projects": [
    {
      "id": "8e45c892",
      "text": "Task description",
      "completed": false,
      "createdAt": "2026-02-27T11:45:27.446971",
      "updatedAt": "2026-02-27T11:45:27.447466",
      "comments": []
    }
  ],
  "next_actions": [...],
  "waiting_for": [...],
  "someday_maybe": [...]
}
```

**GTD Categories:**
1. **Projects** - Multi-step outcomes
2. **Next Actions** - Immediate next steps
3. **Waiting For** - Delegated/pending items
4. **Someday/Maybe** - Future possibilities

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/gtd/tasks` | Retrieve all tasks (JSON) |
| `POST` | `/api/gtd/tasks` | Add new task |
| `PUT` | `/api/gtd/tasks` | Update all tasks (JSON or Markdown) |
| `DELETE` | `/api/gtd/tasks` | Clear all tasks |
| `GET` | `/api/gtd/title?url=...` | Extract webpage title |

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `load_tasks()` | Load tasks from JSON file |
| `save_tasks()` | Persist tasks to disk |
| `parse_markdown_to_json()` | Convert legacy Markdown to JSON |
| `generate_markdown_with_comments()` | Export JSON to Markdown format |
| `extract_title_from_url()` | Multi-strategy URL title extraction |

**Comment System:**
- Comments stored as array within each task
- Each comment has `id`, `text`, `createdAt`
- Legacy format: `<!-- Comment: text -->` in Markdown

### 3. Static Files Structure

**Location:** `/home/admin/Code/molt_server/static/`

```
static/
├── gtd/
│   └── index.html         # Modern GTD UI (67KB)
│                          # - Vue.js-like reactive design
│                          # - Drag-and-drop task management
│                          # - Dark/light theme support
│                          # - Mobile responsive
│
└── images/
    ├── favicon-bot.ico    # Browser favicon (ICO)
    ├── favicon-bot.png    # PNG version
    └── favicon-bot.svg    # SVG version
```

**BotReports Static:**
```
botreports/
└── index.html             # Report browser (12KB)
                           # - Filter by report type
                           # - Date-based grouping
                           # - Direct links to reports/MP3s
```

---

## Deployment Architecture

### Network Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Internet                              │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Apache (Port 80/443)                       │
│                   Reverse Proxy / Load Balancer               │
│                                                              │
│  /kodexplorer/*  →  Direct filesystem (Alias)                │
│  /BotReports/*   →  Direct filesystem (Alias)                │
│  /system-info    →  Proxy to Python:8081                     │
│  /api/gtd/*      →  Proxy to Python:8081                     │
│  /gtd/*          →  Proxy to Python:8081                     │
│  /*              →  Proxy to Python:8081                     │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│              Python Molt Server (Port 8081)                    │
│              /home/admin/Code/molt_server/                     │
│                                                              │
│  - File serving from /var/www/html                           │
│  - GTD application                                           │
│  - System monitoring                                         │
│  - BotReports API                                            │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Filesystem                                 │
│                                                              │
│  /var/www/html/          - Web root                          │
│  /var/www/html/BotReports/ - Report storage                  │
│  /var/www/html/gtd/      - GTD data                          │
│  /var/www/html/kodexplorer/ - File manager                   │
└──────────────────────────────────────────────────────────────┘
```

### Apache Configuration (`/etc/httpd/conf.d/molt-server.conf`)

```apache
# Proxy modules
LoadModule proxy_module modules/mod_proxy.so
LoadModule proxy_http_module modules/mod_proxy_http.so

# Proxy settings
ProxyRequests Off
ProxyPreserveHost On

# Selective proxying
ProxyPass /kodexplorer/ !          # Exclude KodExplorer
ProxyPass /BotReports/ !           # Exclude BotReports
ProxyPass /system-info http://127.0.0.1:8081/system-info
ProxyPass /api/gtd/ http://127.0.0.1:8081/api/gtd/
ProxyPass / http://127.0.0.1:8081/

# Direct filesystem serving
Alias /kodexplorer /var/www/html/kodexplorer
Alias /BotReports /var/www/html/BotReports
```

### systemd Service (`/etc/systemd/system/molt-server.service`)

```ini
[Unit]
Description=Molt Server with GTD Task Management
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/Code/molt_server
Environment="WEB_ROOT=/var/www/html"
ExecStart=/usr/bin/python3.11 /home/admin/Code/molt_server/molt-server-unified.py 8081
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Service Commands:**
```bash
sudo systemctl start molt-server
sudo systemctl stop molt-server
sudo systemctl restart molt-server
sudo systemctl status molt-server
sudo journalctl -u molt-server -f  # View logs
```

### Environment Configuration

| Variable | Value | Purpose |
|----------|-------|---------|
| `WEB_ROOT` | `/var/www/html` | Base directory for file serving |
| `PORT` | `8081` | Python server port (command-line) |

---

## Data Flow

### Request Flow

```
Client Request
      │
      ▼
┌─────────────────┐
│   Apache        │  ← Port 80/443
│   (Reverse      │
│    Proxy)       │
└─────────────────┘
      │
      │ ProxyPass rules
      ▼
┌─────────────────┐
│   Python        │  ← Port 8081
│   HTTP Server   │
└─────────────────┘
      │
      ├─→ /system-info → serve_system_info() → psutil metrics
      ├─→ /api/gtd/*   → GTDHandler methods → tasks.json
      ├─→ /gtd/*       → serve_gtd_static() → static/gtd/
      ├─→ /BotReports  → serve_bot_reports_*() → /var/www/html/BotReports/
      ├─→ /kodexplorer → proxy_to_apache() → Apache:8080 (loopback)
      └─→ /*           → serve_file_or_directory() → /var/www/html/
```

### GTD Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│  REST API   │────▶│   gtd.py    │
│   (Frontend)│◀────│  (/api/gtd) │◀────│  (Handler)  │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │  tasks.json │
                                       │  (Storage)  │
                                       └─────────────┘
```

### System Monitoring Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│ /system-info│────▶│   psutil    │
│   (Auto-    │     │  (5s refresh)│     │  Library    │
│    refresh) │     └─────────────┘     └─────────────┘
└─────────────┘                                │
                                               ▼
                              ┌────────────────────────────────┐
                              │  - CPU usage (per core)        │
                              │  - Memory (total/used/free)    │
                              │  - Network I/O                 │
                              │  - Process list (top 20)       │
                              │  - System uptime               │
                              └────────────────────────────────┘
```

### BotReports Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Browser   │────▶│/BotReports  │────▶│ /var/www/html/  │
│             │     │  (index.html)│     │ BotReports/     │
└─────────────┘     └─────────────┘     │ *.html reports  │
                                        │ *.mp3 audio     │
                                        └─────────────────┘
                                               ▲
                                               │
                              ┌────────────────┴────────────────┐
                              │  Report Generation (External)   │
                              │  - Daily news                   │
                              │  - Kernel patches               │
                              │  - LLM memory briefings         │
                              │  - Personal task analysis       │
                              └─────────────────────────────────┘
```

---

## GTD System Architecture

### Migration History

**Previous State (Markdown-based):**
```markdown
# Projects
- [ ] Task 1
  <!-- Comment: Note about task -->
- [x] Completed task

# Next Actions
- [ ] Action item
```

**Current State (JSON-based):**
```json
{
  "projects": [
    {
      "id": "uuid-short",
      "text": "Task description",
      "completed": false,
      "createdAt": "ISO8601",
      "updatedAt": "ISO8601",
      "comments": [
        {"id": "uuid", "text": "Comment", "createdAt": "ISO8601"}
      ]
    }
  ]
}
```

### Migration Benefits

| Aspect | Markdown | JSON |
|--------|----------|------|
| Parsing | Line-by-line regex | Native `json.load()` |
| Comments | HTML comments (fragile) | Structured array |
| Timestamps | Not tracked | Full audit trail |
| Task IDs | None | UUID-based |
| API Support | Limited | Full REST API |
| Frontend Integration | Manual | Direct binding |

### GTD Frontend (`static/gtd/index.html`)

**Features:**
- **Modern UI** - Gradient background, card-based layout
- **Drag-and-drop** - Move tasks between categories
- **Inline editing** - Click to edit task text
- **Comments** - Add/view task comments
- **URL title extraction** - Auto-fetch titles from links
- **Keyboard shortcuts** - Quick task entry
- **Mobile responsive** - Collapsible sidebar
- **Theme support** - CSS variables for customization

**Technology Stack:**
- Vanilla JavaScript (no framework)
- CSS Grid + Flexbox
- Font Awesome icons
- Google Fonts (Inter)

---

## BotReports Integration

### Report Types

| Type | Description | Example Files |
|------|-------------|---------------|
| Daily News | AI-generated news summaries | `2026-03-02-daily-news.html` |
| LLM Memory | Agent memory briefings | `llm-agent-memory-briefing-*.html` |
| Kernel Patches | Linux kernel AI/ML patch analysis | `linux-kernel-ai-ml-patch-report-*.html` |
| Personal Tasks | Task analysis reports | `personal-task-analysis-*.html` |
| Nanobot | Nanobot project reports | `nanobot-daily-report.html` |

### Storage Structure

```
/var/www/html/BotReports/
├── index.html                    # Report browser (served directly by Apache)
├── 2026-03-02-daily-news.html    # HTML report
├── 2026-03-02-daily-news.mp3     # Audio version (TTS)
├── 2026-03-02-daily-news-text.txt # Plain text version
├── kernel-ai-patch-2026-03-02.json # Structured data
└── audios/                       # Audio archive
```

### API Integration

**Endpoint:** `GET /api/bot-reports`

**Response:**
```json
[
  {"filename": "2026-03-02-daily-news.html", "date": "1740902400"},
  {"filename": "2026-03-01-daily-news.html", "date": "1740816000"}
]
```

**Usage:** Frontend `botreports/index.html` fetches this list and renders filterable report browser.

---

## Frontend Architecture

### File Browser (`/`)

**Features:**
- Enhanced directory listing with icons
- File size and modification time
- Quick links to:
  - System Monitor (`/system-info`)
  - GTD App (`/gtd`)
  - Moltbot WebUI (external)
- Markdown rendering (auto-converts `.md` to HTML)

### System Monitor (`/system-info`)

**Metrics Displayed:**
- Memory usage (progress bar)
- CPU usage (overall + per-core)
- Network I/O statistics
- Active connections count
- System uptime
- Top 20 processes by CPU
- Top 20 processes by memory

**Auto-refresh:** 5 seconds via `<meta http-equiv="refresh">`

### GTD App (`/gtd`)

**UI Components:**
- Sidebar navigation (category filter)
- Task board (Kanban-style columns)
- Quick-add input field
- Modal for task details/comments
- Search functionality
- Mobile hamburger menu

### BotReports Browser (`/BotReports`)

**Features:**
- Filter buttons by report type
- Date-based grouping
- Report type badges (color-coded)
- Direct links to HTML and MP3
- Statistics display

---

## Current Issues & Technical Debt

### 1. **Dual Source Structure** ⚠️

**Problem:** Both `molt-server-unified.py` (root) and `src/molt_server/server.py` exist.

**Impact:**
- Confusion about which is canonical
- Potential for divergence
- Maintenance overhead

**Recommendation:** Consolidate to single source. Prefer `molt-server-unified.py` as it's actively used.

### 2. **Legacy Markdown Support** ⚠️

**Problem:** `gtd.py` still includes `parse_markdown_to_json()` and `generate_markdown_with_comments()`.

**Impact:**
- Code complexity
- Unused functionality (all tasks now JSON)
- Potential for format confusion

**Recommendation:** Deprecate Markdown support. Keep only JSON parsing.

### 3. **KodExplorer Proxy Loop** 🔴

**Problem:** `/kodexplorer` requests proxy from Python → Apache → filesystem, but Apache also serves KodExplorer directly.

**Impact:**
- Unnecessary network hop
- Potential for circular proxy
- Configuration complexity

**Recommendation:** Serve KodExplorer entirely through Apache. Remove Python proxy code.

### 4. **No Authentication/Authorization** 🔴

**Problem:** All endpoints are publicly accessible.

**Impact:**
- GTD tasks visible to anyone
- System metrics exposed
- File browsing unrestricted

**Recommendation:**
- Add basic auth for sensitive endpoints
- IP-based access control
- Session management for GTD

### 5. **No Input Validation** 🟡

**Problem:** GTD API accepts arbitrary JSON without schema validation.

**Impact:**
- Potential for malformed data
- No type safety
- Silent failures

**Recommendation:** Add JSON schema validation for API endpoints.

### 6. **Hardcoded Paths** 🟡

**Problem:** Paths like `/var/www/html` and `/home/admin/Code/molt_server` are hardcoded.

**Impact:**
- Difficult to relocate
- Environment-specific
- Deployment friction

**Recommendation:** Use environment variables for all paths.

### 7. **No Logging** 🟡

**Problem:** No structured logging; only `print()` statements.

**Impact:**
- Difficult debugging
- No audit trail
- Production monitoring impossible

**Recommendation:** Implement Python `logging` module with file rotation.

### 8. **Memory Usage in System Monitor** 🟡

**Problem:** `serve_system_info()` fetches ALL processes every request.

**Impact:**
- High CPU on process-heavy systems
- Memory allocation per request
- 5-second refresh amplifies issue

**Recommendation:** Cache process list with TTL (e.g., 10 seconds).

### 9. **No HTTPS Support** 🟡

**Problem:** Server only supports HTTP.

**Impact:**
- Credentials (if added) transmitted in clear
- MITM vulnerability
- Modern browser warnings

**Recommendation:** Rely on Apache for TLS termination (current best practice).

### 10. **GTD Frontend Size** 🟢

**Problem:** `static/gtd/index.html` is 67KB single file.

**Impact:**
- Initial load time
- Difficult to maintain
- No code splitting

**Recommendation:** Split into modular CSS/JS files.

---

## Future Improvements

### Short-term (1-3 months)

1. **Consolidate source structure** - Remove `src/` directory
2. **Add logging** - Implement structured logging with rotation
3. **Input validation** - Add JSON schema for GTD API
4. **Path configuration** - Move all paths to environment variables
5. **Remove Markdown support** - Clean up legacy code

### Medium-term (3-6 months)

1. **Authentication** - Add basic auth or token-based auth
2. **Caching layer** - Cache system metrics and process lists
3. **Frontend modularization** - Split GTD frontend into components
4. **API documentation** - OpenAPI/Swagger spec for GTD endpoints
5. **Unit tests** - Test coverage for GTD module

### Long-term (6-12 months)

1. **Database backend** - Migrate from JSON to SQLite/PostgreSQL
2. **WebSocket support** - Real-time system monitoring
3. **Task scheduling** - Cron-like task reminders
4. **Mobile app** - React Native GTD client
5. **Plugin system** - Extensible report generators

---

## Appendix

### A. Dependencies

**Python Packages:**
```
psutil          # System monitoring
requests        # HTTP client (URL title extraction)
beautifulsoup4  # HTML parsing (optional, for title extraction)
markdown        # Markdown rendering (optional)
```

**System Dependencies:**
```
python3.11      # Runtime
apache          # Reverse proxy
systemd         # Service management
```

### B. Port Allocation

| Port | Service | Purpose |
|------|---------|---------|
| 80/443 | Apache | Public HTTP/HTTPS |
| 8080 | Apache | KodExplorer (internal) |
| 8081 | Python | Main web server |
| 18789 | Moltbot | External WebUI (not managed here) |

### C. File Permissions

```
/var/www/html/          webserver:web   775
/var/www/html/BotReports/ admin:web     775
/home/admin/Code/molt_server/ admin:admin 755
/etc/systemd/system/molt-server.service root:root 644
```

### D. Related Documentation

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Installation and deployment guide
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development environment setup
- [CODING_STANDARDS.md](./CODING_STANDARDS.md) - Code style guide
- [COMMIT_GUIDELINES.md](./COMMIT_GUIDELINES.md) - Git commit conventions

---

**Document Status:** ✅ Complete  
**Next Review:** 2026-06-02
