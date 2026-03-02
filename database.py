#!/usr/bin/env python3
"""
Database layer for Molt Server authentication system.
SQLite-based storage for users, sessions, and settings.
"""

import sqlite3
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import threading

# Database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'auth.db')

# Thread-local storage for database connections
_local = threading.local()

def get_connection() -> sqlite3.Connection:
    """Get a thread-local database connection."""
    if not hasattr(_local, 'connection') or _local.connection is None:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        _local.connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row
        # Enable foreign keys
        _local.connection.execute('PRAGMA foreign_keys = ON')
    return _local.connection

def init_database():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            avatar TEXT,
            provider TEXT NOT NULL,
            provider_uid TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create user_settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            theme TEXT DEFAULT 'light',
            language TEXT DEFAULT 'en',
            timezone TEXT DEFAULT 'UTC',
            notifications_enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create index for faster session lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)
    ''')
    
    # Create index for user provider lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_users_provider ON users(provider, provider_uid)
    ''')
    
    conn.commit()
    print(f"Database initialized at {DATABASE_PATH}")

def create_user(email: str, name: str, provider: str, provider_uid: str, avatar: Optional[str] = None) -> Optional[Dict]:
    """Create a new user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (email, name, avatar, provider, provider_uid)
            VALUES (?, ?, ?, ?, ?)
        ''', (email, name, avatar, provider, provider_uid))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # Create default settings for the user
        cursor.execute('''
            INSERT INTO user_settings (user_id)
            VALUES (?)
        ''', (user_id,))
        conn.commit()
        
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError as e:
        print(f"User creation failed: {e}")
        return None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,))
    row = cursor.fetchone()
    
    if row:
        return dict(row)
    return None

def get_user_by_provider(provider: str, provider_uid: str) -> Optional[Dict]:
    """Get user by OAuth provider and UID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM users 
        WHERE provider = ? AND provider_uid = ? AND is_active = 1
    ''', (provider, provider_uid))
    
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE email = ? AND is_active = 1', (email,))
    row = cursor.fetchone()
    
    if row:
        return dict(row)
    return None

def update_user(user_id: int, **kwargs) -> bool:
    """Update user information."""
    conn = get_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['email', 'name', 'avatar', 'is_active']
    updates = []
    values = []
    
    for field, value in kwargs.items():
        if field in allowed_fields:
            updates.append(f"{field} = ?")
            values.append(value)
    
    if not updates:
        return False
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(user_id)
    
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    
    return cursor.rowcount > 0

def create_session(user_id: int, ip_address: Optional[str] = None, user_agent: Optional[str] = None, 
                   expires_hours: int = 24) -> Optional[str]:
    """Create a new session token."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=expires_hours)
    
    cursor.execute('''
        INSERT INTO sessions (user_id, token, expires_at, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, token, expires_at, ip_address, user_agent))
    
    conn.commit()
    return token

def get_session(token: str) -> Optional[Dict]:
    """Get session by token."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.*, u.email, u.name, u.avatar, u.provider
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? 
        AND s.expires_at > CURRENT_TIMESTAMP
        AND u.is_active = 1
    ''', (token,))
    
    row = cursor.fetchone()
    if row:
        # Update last activity
        cursor.execute('''
            UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE token = ?
        ''', (token,))
        conn.commit()
        return dict(row)
    return None

def delete_session(token: str) -> bool:
    """Delete a session (logout)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
    conn.commit()
    
    return cursor.rowcount > 0

def delete_user_sessions(user_id: int) -> int:
    """Delete all sessions for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
    conn.commit()
    
    return cursor.rowcount

def cleanup_expired_sessions() -> int:
    """Remove expired sessions from database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP')
    conn.commit()
    
    return cursor.rowcount

def get_user_settings(user_id: int) -> Optional[Dict]:
    """Get user settings."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row:
        return dict(row)
    return None

def update_user_settings(user_id: int, **kwargs) -> bool:
    """Update user settings."""
    conn = get_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['theme', 'language', 'timezone', 'notifications_enabled']
    updates = []
    values = []
    
    for field, value in kwargs.items():
        if field in allowed_fields:
            updates.append(f"{field} = ?")
            values.append(value)
    
    if not updates:
        return False
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(user_id)
    
    query = f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = ?"
    cursor.execute(query, values)
    conn.commit()
    
    return cursor.rowcount > 0

def get_all_users() -> List[Dict]:
    """Get all active users."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, email, name, avatar, provider, created_at FROM users WHERE is_active = 1')
    return [dict(row) for row in cursor.fetchall()]

def get_user_count() -> int:
    """Get total number of active users."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
    return cursor.fetchone()[0]

# Initialize database on module load
if __name__ == '__main__':
    init_database()
    print("Database module loaded successfully")
