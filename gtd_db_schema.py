#!/usr/bin/env python3
"""
Database schema and migration scripts for GTD module.
Migrates from JSON file storage to SQLite database.
"""

import sqlite3
import os
from datetime import datetime

# Database schema SQL
SCHEMA_SQL = """
-- GTD Database Schema
-- Supports multi-user task management with ACID transactions

-- Users table (for multi-user support)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar TEXT,
    provider TEXT,
    provider_uid TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    content TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('Projects', 'Next Actions', 'Waiting For', 'Someday/Maybe')),
    done INTEGER NOT NULL DEFAULT 0,
    priority TEXT DEFAULT 'medium' CHECK(priority IN ('high', 'medium', 'low')),
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast filtering
CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);
CREATE INDEX IF NOT EXISTS idx_tasks_user_category ON tasks(user_id, category);
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comments_task_id ON comments(task_id);

-- Subtasks table (for structured subtasks, separate from comments)
CREATE TABLE IF NOT EXISTS subtasks (
    id TEXT PRIMARY KEY,
    task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subtasks_task_id ON subtasks(task_id);

-- Metadata table for storing migration info and version
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Schedules table for task reminders and recurring tasks
CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
    scheduled_at TIMESTAMP NOT NULL,
    reminder_sent INTEGER DEFAULT 0,
    recurrence TEXT CHECK(recurrence IN ('none', 'daily', 'weekly', 'monthly', 'yearly')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_schedules_task_id ON schedules(task_id);
CREATE INDEX IF NOT EXISTS idx_schedules_scheduled_at ON schedules(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_schedules_reminder_sent ON schedules(reminder_sent);
"""

def create_schema(db_path):
    """Create the database schema."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Execute schema
    cursor.executescript(SCHEMA_SQL)
    
    # Set metadata
    cursor.execute("""
        INSERT OR REPLACE INTO metadata (key, value, updated_at)
        VALUES ('schema_version', '1.0', CURRENT_TIMESTAMP)
    """)
    cursor.execute("""
        INSERT OR REPLACE INTO metadata (key, value, updated_at)
        VALUES ('migration_date', ?, CURRENT_TIMESTAMP)
    """, (datetime.now().isoformat(),))
    
    conn.commit()
    conn.close()
    
    print(f"Database schema created at {db_path}")
    return True

def verify_schema(db_path):
    """Verify the database schema is correct."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('users', 'tasks', 'comments', 'subtasks', 'metadata')
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = ['users', 'tasks', 'comments', 'subtasks', 'metadata']
    missing = set(expected_tables) - set(tables)
    
    if missing:
        print(f"Missing tables: {missing}")
        return False
    
    # Check indexes
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND tbl_name='tasks'
    """)
    indexes = [row[0] for row in cursor.fetchall()]
    
    expected_indexes = ['idx_tasks_category', 'idx_tasks_user_category', 'idx_tasks_done']
    missing_indexes = set(expected_indexes) - set(indexes)
    
    if missing_indexes:
        print(f"Missing indexes: {missing_indexes}")
        return False
    
    conn.close()
    print("Schema verification passed")
    return True

if __name__ == '__main__':
    # Test schema creation
    test_db = '/tmp/test_gtd.db'
    create_schema(test_db)
    verify_schema(test_db)
    print("Schema test completed successfully")
    os.remove(test_db)
