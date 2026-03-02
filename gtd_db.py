#!/usr/bin/env python3
"""
Database layer for GTD module.
SQLite-based storage with connection pooling and thread safety.
"""

import sqlite3
import os
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

# Import configuration
from config import APP_DIR, GTD_DATA_DIR

# Database path
DATABASE_PATH = os.path.join(GTD_DATA_DIR, 'gtd.db')

# Connection pool settings
POOL_SIZE = 5
_pool = None
_pool_lock = threading.Lock()


class ConnectionPool:
    """Thread-safe SQLite connection pool."""
    
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self.pool = []
        self.lock = threading.Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool."""
        for _ in range(self.pool_size):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')
            conn.execute('PRAGMA journal_mode = WAL')  # Better concurrency
            conn.execute('PRAGMA synchronous = NORMAL')
            self.pool.append(conn)
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        conn = None
        with self.lock:
            if self.pool:
                conn = self.pool.pop()
            else:
                # Create new connection if pool is empty
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute('PRAGMA foreign_keys = ON')
        
        try:
            yield conn
        finally:
            with self.lock:
                if len(self.pool) < self.pool_size:
                    self.pool.append(conn)
                else:
                    conn.close()
    
    def close_all(self):
        """Close all connections in the pool."""
        with self.lock:
            for conn in self.pool:
                conn.close()
            self.pool = []


# Global connection pool
def get_pool() -> ConnectionPool:
    """Get or create the global connection pool."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ConnectionPool(DATABASE_PATH, POOL_SIZE)
    return _pool


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    pool = get_pool()
    with pool.get_connection() as conn:
        yield conn


def init_database():
    """Initialize the GTD database."""
    from gtd_db_schema import create_schema, verify_schema
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    # Create schema
    create_schema(DATABASE_PATH)
    
    # Verify schema
    if not verify_schema(DATABASE_PATH):
        raise Exception("Database schema verification failed")
    
    print(f"GTD Database initialized at {DATABASE_PATH}")


# ============== User Operations ==============

def create_user(user_id: str, email: str, name: Optional[str] = None, 
                avatar: Optional[str] = None, provider: Optional[str] = None,
                provider_uid: Optional[str] = None) -> Optional[Dict]:
    """Create a new user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (id, email, name, avatar, provider, provider_uid)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, email, name, avatar, provider, provider_uid))
            conn.commit()
            return get_user(user_id)
    except sqlite3.IntegrityError as e:
        print(f"User creation failed: {e}")
        return None


def get_user(user_id: str) -> Optional[Dict]:
    """Get user by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# ============== Task Operations ==============

def create_task(task_id: str, user_id: Optional[str], content: str, 
                category: str, priority: str = 'medium',
                due_date: Optional[str] = None) -> Optional[Dict]:
    """Create a new task."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO tasks (id, user_id, content, category, priority, due_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (task_id, user_id, content, category, priority, due_date, now, now))
            conn.commit()
            return get_task(task_id)
    except sqlite3.IntegrityError as e:
        print(f"Task creation failed: {e}")
        return None


def get_task(task_id: str) -> Optional[Dict]:
    """Get task by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_tasks(user_id: Optional[str] = None) -> List[Dict]:
    """Get all tasks, optionally filtered by user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute('SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        else:
            cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]


def get_tasks_by_category(category: str, user_id: Optional[str] = None) -> List[Dict]:
    """Get tasks by category."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE category = ? AND user_id = ?
                ORDER BY created_at DESC
            """, (category, user_id))
        else:
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE category = ?
                ORDER BY created_at DESC
            """, (category,))
        return [dict(row) for row in cursor.fetchall()]


def update_task(task_id: str, **kwargs) -> bool:
    """Update task fields."""
    allowed_fields = ['content', 'category', 'done', 'priority', 'due_date']
    updates = []
    values = []
    
    for field, value in kwargs.items():
        if field in allowed_fields:
            updates.append(f"{field} = ?")
            values.append(value)
    
    if not updates:
        return False
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(task_id)
    
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0


def delete_task(task_id: str) -> bool:
    """Delete a task (cascades to comments and subtasks)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        return cursor.rowcount > 0


def task_exists(task_id: str) -> bool:
    """Check if a task exists."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM tasks WHERE id = ?', (task_id,))
        return cursor.fetchone() is not None


# ============== Comment Operations ==============

def create_comment(comment_id: str, task_id: str, user_id: Optional[str], 
                   content: str) -> Optional[Dict]:
    """Create a new comment."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO comments (id, task_id, user_id, content, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (comment_id, task_id, user_id, content))
            conn.commit()
            return get_comment(comment_id)
    except sqlite3.IntegrityError as e:
        print(f"Comment creation failed: {e}")
        return None


def get_comment(comment_id: str) -> Optional[Dict]:
    """Get comment by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM comments WHERE id = ?', (comment_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_comments_by_task(task_id: str) -> List[Dict]:
    """Get all comments for a task."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM comments 
            WHERE task_id = ?
            ORDER BY created_at ASC
        """, (task_id,))
        return [dict(row) for row in cursor.fetchall()]


def update_comment(comment_id: str, content: str) -> bool:
    """Update comment content."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE comments 
            SET content = ?, created_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (content, comment_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_comment(comment_id: str) -> bool:
    """Delete a comment."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
        conn.commit()
        return cursor.rowcount > 0


# ============== Subtask Operations ==============

def create_subtask(subtask_id: str, task_id: str, content: str, 
                   done: int = 0, sort_order: int = 0) -> Optional[Dict]:
    """Create a new subtask."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO subtasks (id, task_id, content, done, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (subtask_id, task_id, content, done, sort_order))
            conn.commit()
            return get_subtask(subtask_id)
    except sqlite3.IntegrityError as e:
        print(f"Subtask creation failed: {e}")
        return None


def get_subtask(subtask_id: str) -> Optional[Dict]:
    """Get subtask by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subtasks WHERE id = ?', (subtask_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_subtasks_by_task(task_id: str) -> List[Dict]:
    """Get all subtasks for a task."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM subtasks 
            WHERE task_id = ?
            ORDER BY sort_order ASC, created_at ASC
        """, (task_id,))
        return [dict(row) for row in cursor.fetchall()]


def update_subtask(subtask_id: str, **kwargs) -> bool:
    """Update subtask fields."""
    allowed_fields = ['content', 'done', 'sort_order']
    updates = []
    values = []
    
    for field, value in kwargs.items():
        if field in allowed_fields:
            updates.append(f"{field} = ?")
            values.append(value)
    
    if not updates:
        return False
    
    values.append(subtask_id)
    query = f"UPDATE subtasks SET {', '.join(updates)} WHERE id = ?"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0


def delete_subtask(subtask_id: str) -> bool:
    """Delete a subtask."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM subtasks WHERE id = ?', (subtask_id,))
        conn.commit()
        return cursor.rowcount > 0


# ============== Utility Functions ==============

def get_task_statistics(user_id: Optional[str] = None) -> Dict:
    """Get task statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN done = 0 THEN 1 ELSE 0 END) as pending
                FROM tasks WHERE user_id = ?
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN done = 0 THEN 1 ELSE 0 END) as pending
                FROM tasks
            """)
        
        row = cursor.fetchone()
        return {
            'total': row['total'] or 0,
            'completed': row['completed'] or 0,
            'pending': row['pending'] or 0
        }


def backup_to_json(backup_path: str, user_id: Optional[str] = None) -> bool:
    """Export all data to JSON format for backup."""
    import json
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get tasks
        if user_id:
            cursor.execute('SELECT * FROM tasks WHERE user_id = ?', (user_id,))
        else:
            cursor.execute('SELECT * FROM tasks')
        tasks = [dict(row) for row in cursor.fetchall()]
        
        # Organize by category
        data = {
            'projects': [],
            'next_actions': [],
            'waiting_for': [],
            'someday_maybe': [],
            'comments': {},
            'subtasks': {}
        }
        
        category_map = {
            'Projects': 'projects',
            'Next Actions': 'next_actions',
            'Waiting For': 'waiting_for',
            'Someday/Maybe': 'someday_maybe'
        }
        
        for task in tasks:
            category = category_map.get(task['category'], 'projects')
            task_data = {
                'id': task['id'],
                'text': task['content'],
                'completed': bool(task['done']),
                'createdAt': task['created_at'],
                'updatedAt': task['updated_at'],
                'priority': task['priority'],
                'due_date': task['due_date'],
                'comments': []
            }
            data[category].append(task_data)
            
            # Get comments for this task
            cursor.execute('SELECT * FROM comments WHERE task_id = ?', (task['id'],))
            comments = [dict(row) for row in cursor.fetchall()]
            if comments:
                data['comments'][task['id']] = comments
            
            # Get subtasks for this task
            cursor.execute('SELECT * FROM subtasks WHERE task_id = ?', (task['id'],))
            subtasks = [dict(row) for row in cursor.fetchall()]
            if subtasks:
                data['subtasks'][task['id']] = subtasks
        
        # Write to file
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True


if __name__ == '__main__':
    # Test database initialization
    init_database()
    print("Database module loaded successfully")
