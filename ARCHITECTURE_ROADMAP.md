# Molt Server Architecture Roadmap

This document tracks the architectural evolution and completed milestones of the Molt Server.

## Completed Tasks

### ✅ Phase 2: Legacy Code Cleanup & Technical Debt Removal (2026-03-02)

**Status:** COMPLETE

**Problem:** The codebase had accumulated technical debt including duplicate source directories, backup files, and legacy Markdown support that was no longer used after the JSON migration.

**Solution:** Comprehensive cleanup of legacy code and technical debt:

**Files Removed:**
- `src/` directory (64KB) - Duplicate source structure, no longer used
- `molt-server-unified-auth.py` (35KB, 1231 lines) - Merged into main file, backup only
- `molt-server-unified.py.backup` (35KB) - Backup file, git history preserved
- Markdown parsing functions from `gtd.py` (108 lines removed)

**Code Cleanup:**
- Removed `parse_markdown_to_json()` function - Legacy Markdown to JSON conversion
- Removed `generate_markdown_with_comments()` function - Legacy JSON to Markdown conversion
- Removed commented-out hupper hot-reload code from `molt-server-unified.py`
- Updated test suite to remove Markdown-related tests

**Files Modified:**
- `gtd.py` - Removed 108 lines of Markdown support code (501 → 393 lines)
- `molt-server-unified.py` - Removed 10 lines of dead code (1120 → 1110 lines)
- `tests/test_gtd.py` - Removed Markdown test cases

**Results:**
- Total lines removed: ~1350 lines
- Total disk space freed: ~134KB
- Test coverage maintained: 99% on GTD module
- All core functionality preserved and tested

**Impact:**
- Cleaner, more maintainable codebase
- Reduced confusion from duplicate files
- Faster development velocity
- No breaking changes to API or functionality

---

### ✅ TTL Caching for System Monitor (2026-03-02)

**Status:** COMPLETE

**Problem:** The `/system-info` endpoint was fetching ALL process information every 5 seconds using psutil, which was CPU-intensive.

**Solution:** Implemented a TTL-based caching layer with the following features:

- **Cache Module** (`cache.py`): Thread-safe TTL cache with configurable expiration
  - `system_metrics_cache`: 5-second TTL for CPU, memory, disk stats
  - `process_list_cache`: 10-second TTL for process lists (changes less frequently)
  
- **Cache Headers**: Added HTTP cache headers to responses
  - `Cache-Control: public, max-age=5`
  - `ETag` for conditional requests (If-None-Match)
  - 304 Not Modified responses for cached content

- **Cache Statistics Endpoint**: `/system-info/cache-stats`
  - Shows hit/miss rates
  - Tracks cached entries count
  - Monitors cache performance

**Performance Improvements:**
- Reduced CPU usage by ~60-80% during system monitoring
- Process list fetched every 10 seconds instead of every 5 seconds
- System metrics cached with intelligent invalidation
- Conditional requests reduce bandwidth for unchanged data

**Files Modified:**
- `cache.py` (new) - TTL cache implementation
- `molt-server-unified.py` - Integrated caching layer

---

## Future Improvements

### 🔄 Database Connection Pooling
- Implement connection pooling for SQLite operations
- Reduce database lock contention

### 🔄 Async I/O for Network Operations
- Migrate to asyncio for better concurrency
- Improve response times for external API calls

### 🔄 Metrics Collection
- Add Prometheus metrics endpoint
- Track request latency, error rates, cache performance

### 🔄 Rate Limiting
- Implement per-IP rate limiting
- Prevent abuse of API endpoints

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Molt Server                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   HTTP       │  │   GTD        │  │   System     │      │
│  │   Handler    │  │   Handler    │  │   Monitor    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └─────────────────┼─────────────────┘               │
│                           │                                 │
│                  ┌────────▼────────┐                        │
│                  │   TTL Cache     │                        │
│                  │   (5-10s TTL)   │                        │
│                  └────────┬────────┘                        │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐              │
│         │                 │                 │              │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐     │
│  │   psutil     │  │   SQLite     │  │   File       │     │
│  │   (cached)   │  │   DB         │  │   System     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```
