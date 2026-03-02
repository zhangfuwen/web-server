# GTD Module Documentation

**Module:** GTD (Getting Things Done) Task Management  
**Location:** `/home/admin/Code/molt_server/gtd.py`  
**Frontend:** `/home/admin/Code/molt_server/static/gtd/index.html`  
**Data:** `/home/admin/Code/molt_server/gtd/tasks.json`  
**Version:** 1.0 (JSON-based)  
**Last Updated:** 2026-03-02

---

## Table of Contents

1. [Module Architecture Overview](#module-architecture-overview)
2. [Data Structures](#data-structures)
3. [API Endpoints Reference](#api-endpoints-reference)
4. [Frontend Components](#frontend-components)
5. [Known Issues & Technical Debt](#known-issues--technical-debt)
6. [Future Enhancement Ideas](#future-enhancement-ideas)

---

## Module Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
│                    (GTD Frontend UI)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP Requests
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              molt-server-unified.py (Port 8081)                  │
│                    UnifiedHTTPRequestHandler                     │
│                                                                  │
│  Routes:                                                         │
│  - GET  /gtd              → serve_gtd_app()                     │
│  - GET  /gtd/*            → serve_gtd_static()                  │
│  - GET  /api/gtd/tasks    → serve_gtd_tasks()                   │
│  - POST /api/gtd/tasks    → add_gtd_task()                      │
│  - PUT  /api/gtd/tasks    → update_gtd_tasks()                  │
│  - DELETE /api/gtd/tasks  → clear_gtd_tasks()                   │
│  - GET  /api/gtd/title    → extract_title_api()                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ File I/O
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    /home/admin/Code/molt_server/gtd/             │
│                         tasks.json                               │
│                    (JSON Task Storage)                           │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | File | Responsibility |
|-----------|------|----------------|
| **HTTP Handler** | `gtd.py` | Request routing, CRUD operations, data persistence |
| **Frontend** | `static/gtd/index.html` | UI rendering, user interactions, state management |
| **Data Storage** | `gtd/tasks.json` | Persistent task data in JSON format |
| **Main Server** | `molt-server-unified.py` | Integrates GTD module, handles request routing |

### GTD Methodology Implementation

The system implements David Allen's Getting Things Done methodology with four core categories:

1. **Projects** - Multi-step outcomes requiring more than one action
2. **Next Actions** - Immediate next physical steps for active projects
3. **Waiting For** - Items delegated or pending external input
4. **Someday/Maybe** - Future possibilities, not actionable now

### Key Design Decisions

- **JSON Storage**: Migrated from Markdown to JSON for better structure and API support
- **RESTful API**: Standard HTTP methods for CRUD operations
- **Vanilla JS Frontend**: No framework dependencies, single-file deployment
- **Kanban Board View**: Visual task management with column-based organization
- **Comment System**: Inline comments and subtasks supported per task

---

## Data Structures

### tasks.json Schema

```json
{
  "projects": [TaskObject, ...],
  "next_actions": [TaskObject, ...],
  "waiting_for": [TaskObject, ...],
  "someday_maybe": [TaskObject, ...]
}
```

### Task Object Structure

```typescript
interface Task {
  id: string;           // 8-character UUID prefix (e.g., "8e45c892")
  text: string;         // Task description
  completed: boolean;   // Completion status
  createdAt: string;    // ISO 8601 timestamp
  updatedAt: string;    // ISO 8601 timestamp
  comments: Comment[];  // Array of comments/subtasks
}
```

### Comment Object Structure

```typescript
interface Comment {
  id: string;           // 8-character UUID prefix or generated ID
  text: string;         // Comment text
  createdAt: string;    // ISO 8601 timestamp
}
```

### Special Comment Formats

Comments can encode additional metadata using special prefixes:

| Format | Purpose | Example |
|--------|---------|---------|
| `[ ] task text` | Subtask (incomplete) | `[ ] Research options` |
| `[x] task text` | Subtask (complete) | `[x] Initial research` |
| `due: YYYY-MM-DD` | Due date | `due: 2026-03-15` |
| `截止日期：YYYY-MM-DD` | Due date (Chinese) | `截止日期：2026-03-15` |
| `优先级高` | High priority flag | `优先级高` |

### Example tasks.json

```json
{
  "projects": [
    {
      "id": "8e45c892",
      "text": "完成 web 服务器改进",
      "completed": false,
      "createdAt": "2026-02-27T11:45:27.446971",
      "updatedAt": "2026-02-27T11:45:27.447466",
      "comments": [
        {
          "id": "c1234567",
          "text": "due: 2026-03-15",
          "createdAt": "2026-02-27T12:00:00.000000"
        },
        {
          "id": "c2345678",
          "text": "[ ] 测试性能优化",
          "createdAt": "2026-02-27T12:05:00.000000"
        }
      ]
    }
  ],
  "next_actions": [],
  "waiting_for": [],
  "someday_maybe": []
}
```

### Data Migration Note

**Phase 2 Cleanup (2026-03-02):** Legacy Markdown support has been removed. The system now exclusively uses JSON format for all task storage and API operations.

---

## API Endpoints Reference

### Base URL

```
http://localhost:8081/api/gtd
```

### GET /api/gtd/tasks

**Description:** Retrieve all tasks in JSON format.

**Request:**
```http
GET /api/gtd/tasks
Accept: application/json
```

**Response:** `200 OK`
```json
{
  "projects": [...],
  "next_actions": [...],
  "waiting_for": [...],
  "someday_maybe": [...]
}
```

**Errors:**
- `500 Internal Server Error` - File read error

---

### POST /api/gtd/tasks

**Description:** Add a new task to a category.

**Request:**
```http
POST /api/gtd/tasks
Content-Type: application/json

{
  "category": "projects",
  "text": "New task description"
}
```

**Request Body Fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `category` | string | No | `projects` | Target category |
| `text` | string | Yes | - | Task description |

**Response:** `201 Created`
```json
{
  "message": "Task added",
  "task": {
    "id": "abc12345",
    "text": "New task description",
    "completed": false,
    "createdAt": "2026-03-02T08:00:00.000000",
    "updatedAt": "2026-03-02T08:00:00.000000",
    "comments": []
  }
}
```

**Errors:**
- `400 Bad Request` - Invalid JSON or missing text field

---

### PUT /api/gtd/tasks

**Description:** Update all tasks (full replace). JSON format only.

**Request:**
```http
PUT /api/gtd/tasks
Content-Type: application/json

{
  "projects": [...],
  "next_actions": [...],
  "waiting_for": [...],
  "someday_maybe": [...]
}
```

**Response:** `200 OK`
```json
{
  "message": "Tasks updated successfully"
}
```

**Processing:**
- Updates `updatedAt` timestamp for all tasks
- Normalizes comment format (converts string comments to objects)
- Adds missing `createdAt` to comments

**Errors:**
- `500 Internal Server Error` - Parse or write error

---

### DELETE /api/gtd/tasks

**Description:** Clear all tasks and reset to empty structure.

**Request:**
```http
DELETE /api/gtd/tasks
```

**Response:** `200 OK`
```json
{
  "message": "Tasks cleared successfully"
}
```

**Errors:**
- `500 Internal Server Error` - File write error

---

### GET /api/gtd/title

**Description:** Extract webpage title from a URL (for adding link-based tasks).

**Request:**
```http
GET /api/gtd/title?url=https://example.com/page
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | URL to extract title from |

**Response:** `200 OK`
```json
{
  "title": "Example Page Title"
}
```

**Title Extraction Strategies:**

1. **Web Fetch**: Fetch page and extract `<title>` tag (requires `requests` and `beautifulsoup4`)
2. **Path Extraction**: Use last path segment, cleaned and capitalized
3. **Domain + Path**: Combine domain name with simplified path
4. **Fallback**: Return URL as-is

**Errors:**
- `400 Bad Request` - Missing URL parameter
- `500 Internal Server Error` - Extraction error

---

## Frontend Components

### File: `static/gtd/index.html`

**Size:** ~67KB (single-file application)  
**Dependencies:** Font Awesome 6.4.0, Google Fonts (Inter)  
**Browser Support:** Modern browsers (ES6+, CSS Grid, Flexbox)

### UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Mobile Header (visible <768px)                             │
│  [☰] GTD Desktop                                            │
├─────────────┬───────────────────────────────────────────────┤
│             │                                               │
│  Sidebar    │  Main Content                                 │
│  ┌────────┐ │  ┌─────────────────────────────────────────┐  │
│  │ Logo   │ │  │ Header: "My Tasks" [Add Task]          │  │
│  ├────────┤ │  ├─────────────────────────────────────────┤  │
│  │ Views  │ │  │ Quick Add (collapsible)                 │  │
│  │ - Board│ │  ├─────────────────────────────────────────┤  │
│  ├────────┤ │  │ Sort Controls                           │  │
│  │ Filters│ │  ├─────────────────────────────────────────┤  │
│  │ - Imp. │ │  │ Task Board (Kanban)                     │  │
│  ├────────┤ │  │ ┌─────────┐ ┌─────────┐ ┌─────────┐    │  │
│  │ Stats  │ │  │ │ To Do   │ │ In Prog │ │ Done    │    │  │
│  │ Total  │ │  │ │ (3)     │ │ (2)     │ │ (5)     │    │  │
│  │ Done   │ │  │ │         │ │         │ │         │    │  │
│  └────────┘ │  │ └─────────┘ └─────────┘ └─────────┘    │  │
│             │  └─────────────────────────────────────────┘  │
└─────────────┴───────────────────────────────────────────────┘
```

### Key Components

#### 1. Sidebar Navigation

- **Logo**: GTD Desktop branding with gradient icon
- **Views**: Board view (Kanban)
- **Filters**: Important tasks filter (high priority, incomplete)
- **Stats Card**: Total tasks and completed count

#### 2. Task Board (Kanban)

Three-column layout based on task status:

| Column | ID | Color | Icon |
|--------|-----|-------|------|
| To Do | `todo` | Gray (#64748b) | fa-circle |
| In Progress | `doing` | Amber (#f59e0b) | fa-spinner |
| Done | `done` | Green (#10b981) | fa-check-circle |

**Column Features:**
- Task count badge
- Empty state with icon
- Scrollable task list

#### 3. Task Card

```html
<div class="task-card priority-high completed">
  <div class="task-header">
    <div class="task-title" contenteditable="true">Task text</div>
    <div class="task-actions">
      <button class="complete-btn">✓</button>
      <button class="more-btn">⋯</button>
    </div>
  </div>
  <div class="task-meta">
    <span class="task-tag">📁 Category</span>
    <span class="task-tag">🚩 Priority</span>
    <span class="task-tag">📅 Due Date</span>
    <span class="task-tag">✓ 2/5 subtasks</span>
  </div>
  <div class="task-comments">
    <!-- Comments/subtasks rendered here -->
  </div>
</div>
```

**Task Card Features:**
- Priority border (red=high, amber=medium, green=low)
- Inline title editing (contenteditable)
- Hover-revealed action buttons
- Metadata tags (category, priority, due date, subtasks)
- Comment/subtask list with inline editing
- Completed state (strikethrough, reduced opacity)

#### 4. Quick Add

Collapsible input field for rapid task entry:
- Press Enter to add
- Esc or Cancel to close
- Defaults to "Projects" category

#### 5. Sort Controls

| Sort Option | Description |
|-------------|-------------|
| Default | Original order |
| Priority | Low → High (with due date secondary) |
| Priority (High→Low) | High → Low (with due date secondary) |
| Due Date | Far → Near (no date last) |
| Due Date (Near→Far) | Near → Far (no date last) |

#### 6. Edit Modal

Full task editing dialog:
- Task title
- Status (To Do / In Progress / Done)
- Priority (Low / Medium / High)
- Due date picker
- Comments (one per line)

### JavaScript Architecture

#### State Management

```javascript
let tasks = [];           // Parsed task objects for rendering
let rawGtdData = {};      // Raw JSON from server
let currentSort = 'none'; // Current sort mode
let columns = [...];      // Column definitions
```

#### Data Flow

```
1. loadTasks()
   ↓ fetch('/api/gtd/tasks')
   ↓ rawGtdData = response.json()
   ↓ parseGtdData()
   ↓ tasks = transformed objects
   ↓ renderBoard()
   
2. User Action (e.g., toggle complete)
   ↓ Update rawGtdData
   ↓ saveGtdData()
   ↓ fetch('/api/gtd/tasks', PUT)
   ↓ loadTasks() (refresh)
```

#### Key Functions

| Function | Purpose |
|----------|---------|
| `loadTasks()` | Fetch and parse tasks from API |
| `parseGtdData()` | Transform raw JSON to renderable objects |
| `renderBoard()` | Generate Kanban board HTML |
| `renderTaskCard(task)` | Generate individual task card HTML |
| `saveGtdData()` | Serialize and PUT to API as JSON |
| `addTask()` | Create new task in Projects |
| `toggleComplete(taskId)` | Toggle task completion |
| `updateTaskTitle(taskId, el)` | Inline title edit save |
| `addComment(taskId, input)` | Add comment/subtask |
| `toggleSubtaskComment(...)` | Toggle subtask checkbox |
| `deleteComment(...)` | Remove comment |
| `sortTasks(sortType)` | Apply sorting algorithm |

### CSS Architecture

#### CSS Variables

```css
:root {
  --primary: #6366f1;
  --primary-dark: #4f46e5;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --gray-900: #0f172a;
  /* ... more color tokens */
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
  --radius: 8px;
}
```

#### Responsive Breakpoints

- **Mobile**: `<768px` - Single column, collapsible sidebar
- **Desktop**: `≥768px` - Two-column layout, persistent sidebar

#### Animations

- Sidebar toggle: `transition: transform 0.3s ease`
- Task card hover: `transform: translateY(-2px)`
- Button hover: `transform: translateY(-2px)`

---

## Known Issues & Technical Debt

### ✅ Resolved Issues

#### 1. Data Format Inconsistency - RESOLVED (Phase 2, 2026-03-02)

**Problem:** Frontend saved as Markdown, backend stored as JSON.

**Resolution:** Markdown support removed from `gtd.py`. Frontend now saves directly as JSON.

**Impact:**
- Eliminated conversion overhead
- No data loss risk
- Comment metadata (IDs, timestamps) preserved correctly

---

### 🔴 Current Issues

#### 2. Task ID Generation Mismatch

**Problem:** Main `gtd.py` generates UUID-based IDs, but frontend uses index-based IDs (`proj-0`, `next-1`).

**Location:** 
- `gtd.py:add_gtd_task()` → `uuid.uuid4()[:8]`
- `index.html:parseGtdData()` → `id: \`proj-${idx}\``

**Impact:**
- Task IDs not persistent across sessions
- Breaks if task order changes
- Comment references may point to wrong tasks

**Fix Required:** Use server-generated IDs consistently.

---

#### 3. No Error Handling for Network Failures

**Problem:** API calls silently fail; no user feedback.

**Location:** All `fetch()` calls in `index.html`

**Impact:**
- Users don't know if save failed
- Data loss risk
- Poor UX

**Fix Required:** Add toast notifications or error modals.

---

### 🟡 Moderate Issues

#### 4. Inline Edit Race Conditions

**Problem:** Rapid inline edits may cause data loss.

**Location:** `updateTaskTitle()`, `updateComment()`

**Scenario:**
1. User edits title → blur triggers save
2. User immediately edits again before save completes
3. Second save may overwrite first

**Fix Required:** Debounce saves or queue edits.

---

#### 5. No Task Validation

**Problem:** Empty or whitespace-only tasks can be saved.

**Location:** `addTask()`, `saveTask()`

**Fix Required:** Add validation before save.

---

#### 6. Comment Object/String Inconsistency

**Problem:** Comments stored as both objects and strings.

**Location:** `parseGtdData()`, `update_gtd_tasks()`

**Impact:**
- Inconsistent data structure
- Rendering bugs possible
- Timestamps lost for string comments

**Fix Required:** Normalize all comments to objects.

---

#### 7. No Undo/Delete Confirmation

**Problem:** Task/comment deletion is immediate with no undo.

**Location:** `deleteComment()`

**Fix Required:** Add confirmation dialog or undo toast.

---

#### 8. Hardcoded API Paths

**Problem:** `/api/gtd/tasks` hardcoded in frontend.

**Location:** Multiple locations in `index.html`

**Fix Required:** Use base URL configuration.

---

### 🟢 Minor Issues

#### 9. Large Single-File Frontend

**Problem:** 67KB single HTML file (CSS + JS inline).

**Impact:**
- Hard to maintain
- No code splitting
- Full reload on any change

**Fix Required:** Split into modular files.

---

#### 10. No Search Functionality

**Problem:** Cannot search/filter tasks by text.

**Fix Required:** Add search input with real-time filtering.

---

#### 11. No Keyboard Shortcuts Documentation

**Problem:** Shortcuts exist but aren't documented.

**Current Shortcuts:**
- `Enter` in quick add → Add task
- `Enter` in inline edit → Save
- `Esc` in inline edit → Cancel

**Fix Required:** Add help modal or tooltip.

---

#### 12. Mobile Sidebar UX

**Problem:** Mobile sidebar overlay doesn't trap focus.

**Fix Required:** Implement focus trap for accessibility.

---

## Future Enhancement Ideas

### ✅ Completed Enhancements

#### 1. JSON-Native Save - COMPLETED (Phase 2, 2026-03-02)

**Description:** Save directly as JSON instead of Markdown conversion.

**Benefits:**
- Preserves all metadata (IDs, timestamps)
- Faster save operations
- Simpler code
- Reduced technical debt

**Status:** Implemented. Markdown support removed from `gtd.py`.

---

### Short-term (1-4 weeks)

#### 2. Task Search

**Description:** Add search input to filter tasks by text.

**UI:** Search bar above task board.

**Features:**
- Real-time filtering
- Highlight matches
- Clear button

---

#### 3. Drag-and-Drop Reordering

**Description:** Drag tasks to reorder within/between columns.

**Library:** Native HTML5 Drag & Drop API or lightweight library.

**Benefits:**
- Intuitive task management
- Visual reordering

---

#### 4. Toast Notifications

**Description:** Show feedback for actions (save, delete, error).

**Examples:**
- ✓ "Task saved"
- ✗ "Save failed - retry?"
- ⚠ "Task deleted" [Undo]

---

### Medium-term (1-3 months)

#### 5. Task Templates

**Description:** Predefined task templates for common workflows.

**Examples:**
- "Meeting prep" template
- "Code review" checklist
- "Deployment" steps

**UI:** Template picker in quick add.

---

#### 6. Recurring Tasks

**Description:** Support for repeating tasks.

**Schema Addition:**
```json
{
  "recurrence": {
    "type": "daily|weekly|monthly",
    "interval": 1,
    "nextDue": "2026-03-03"
  }
}
```

---

#### 7. Task Dependencies

**Description:** Link tasks as blocked by/blocking.

**UI:** Visual dependency arrows in board view.

**Use Case:** "Cannot start B until A is done."

---

#### 8. Export/Import

**Description:** Export tasks to JSON/CSV. (Markdown export removed in Phase 2)

**Features:**
- Backup creation
- Migration support
- Sharing workflows

---

### Long-term (3-6 months)

#### 9. WebSocket Real-Time Sync

**Description:** Real-time task updates across multiple clients.

**Benefits:**
- Multi-user collaboration
- Instant sync across devices

**Implementation:** Upgrade HTTP server to support WebSockets.

---

#### 10. Mobile App (PWA)

**Description:** Progressive Web App for mobile devices.

**Features:**
- Offline support
- Push notifications
- Home screen install

---

#### 11. Natural Language Processing

**Description:** Parse natural language task input.

**Examples:**
- "Call John tomorrow at 3pm" → Task + due date
- "High priority: finish report" → Priority flag

**Implementation:** Client-side NLP library.

---

#### 12. Analytics Dashboard

**Description:** Task completion analytics.

**Metrics:**
- Tasks completed per day/week
- Average completion time
- Category distribution
- Productivity trends

---

## Appendix

### A. File Locations

| File | Path | Purpose |
|------|------|---------|
| Main Handler | `/home/admin/Code/molt_server/gtd.py` | Backend logic, API endpoints |
| Frontend | `/home/admin/Code/molt_server/static/gtd/index.html` | UI, client-side logic |
| Data | `/home/admin/Code/molt_server/gtd/tasks.json` | Task storage |

**Removed in Phase 2 (2026-03-02):**
- `gtd/tasks.md` - Deprecated Markdown format
- `src/molt_server/gtd.py` - Deprecated module copy (entire `src/` directory removed)

### B. Dependencies

**Python (Backend):**
- `requests` (optional) - URL title extraction
- `beautifulsoup4` (optional) - HTML parsing for title extraction

**JavaScript (Frontend):**
- Font Awesome 6.4.0 (CDN) - Icons
- Google Fonts - Inter typeface

### C. Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Overall system architecture
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment instructions
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development guide

---

**Document Status:** ✅ Complete  
**Maintainer:** GTD Module Owner  
**Next Review:** 2026-06-02
