#!/usr/bin/env python3
"""
Database layer for Clock-in system.
SQLite-based storage for employee clock-in records.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import threading

# Import configuration
from config import APP_DIR, CLOCK_IN_DB_PATH

# Database path
DATABASE_PATH = CLOCK_IN_DB_PATH

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
    
    # Create clock_in_records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clock_in_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT NOT NULL,
            clock_type TEXT NOT NULL CHECK(clock_type IN ('clock_in', 'clock_out')),
            clock_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            has_hat BOOLEAN DEFAULT 0,
            has_mask BOOLEAN DEFAULT 0,
            took_long_route BOOLEAN DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT
        )
    ''')
    
    # Create index for faster lookups by user and date
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_clock_in_user_time 
        ON clock_in_records(user_name, clock_time)
    ''')
    
    # Create index for date-based queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_clock_in_date 
        ON clock_in_records(date(clock_time))
    ''')
    
    conn.commit()
    print(f"Clock-in database initialized at {DATABASE_PATH}")


def add_clock_in_record(
    user_name: str,
    clock_type: str,
    has_hat: bool = False,
    has_mask: bool = False,
    took_long_route: bool = False,
    notes: str = None,
    ip_address: str = None,
    user_agent: str = None,
    user_id: int = None
) -> Optional[Dict]:
    """
    Add a new clock-in/clock-out record.
    
    Args:
        user_name: Name of the user clocking in/out
        clock_type: 'clock_in' or 'clock_out'
        has_hat: Whether user is wearing a hat
        has_mask: Whether user is wearing a mask
        took_long_route: Whether user took a long route
        notes: Optional notes/comments
        ip_address: IP address of the request
        user_agent: User agent string
        user_id: Optional user ID from auth system
    
    Returns:
        The created record as a dictionary, or None if failed
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO clock_in_records 
            (user_name, clock_type, has_hat, has_mask, took_long_route, notes, ip_address, user_agent, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_name, clock_type, has_hat, has_mask, took_long_route, notes, ip_address, user_agent, user_id))
        
        record_id = cursor.lastrowid
        conn.commit()
        
        return get_record_by_id(record_id)
    except Exception as e:
        print(f"Failed to add clock-in record: {e}")
        return None


def get_record_by_id(record_id: int) -> Optional[Dict]:
    """Get a clock-in record by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM clock_in_records WHERE id = ?', (record_id,))
    row = cursor.fetchone()
    
    if row:
        return dict(row)
    return None


def get_records_by_user(user_name: str, limit: int = 100) -> List[Dict]:
    """Get clock-in records for a specific user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM clock_in_records 
        WHERE user_name = ? 
        ORDER BY clock_time DESC 
        LIMIT ?
    ''', (user_name, limit))
    
    return [dict(row) for row in cursor.fetchall()]


def get_records_by_date(date_str: str) -> List[Dict]:
    """
    Get all clock-in records for a specific date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
    
    Returns:
        List of records for that date
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM clock_in_records 
        WHERE date(clock_time) = ? 
        ORDER BY clock_time DESC
    ''', (date_str,))
    
    return [dict(row) for row in cursor.fetchall()]


def get_all_records(limit: int = 1000) -> List[Dict]:
    """Get all clock-in records with optional limit."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM clock_in_records 
        ORDER BY clock_time DESC 
        LIMIT ?
    ''', (limit,))
    
    return [dict(row) for row in cursor.fetchall()]


def get_today_records() -> List[Dict]:
    """Get all clock-in records for today."""
    today = datetime.now().strftime('%Y-%m-%d')
    return get_records_by_date(today)


def get_user_today_record(user_name: str, clock_type: str = None) -> Optional[Dict]:
    """
    Get user's clock-in/clock-out record for today.
    
    Args:
        user_name: Name of the user
        clock_type: Optional filter for 'clock_in' or 'clock_out'
    
    Returns:
        Today's record if exists, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    if clock_type:
        cursor.execute('''
            SELECT * FROM clock_in_records 
            WHERE user_name = ? AND date(clock_time) = ? AND clock_type = ?
            ORDER BY clock_time DESC 
            LIMIT 1
        ''', (user_name, today, clock_type))
    else:
        cursor.execute('''
            SELECT * FROM clock_in_records 
            WHERE user_name = ? AND date(clock_time) = ?
            ORDER BY clock_time DESC 
            LIMIT 1
        ''', (user_name, today))
    
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None


def get_statistics(start_date: str = None, end_date: str = None) -> Dict:
    """
    Get clock-in statistics for a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (default: 30 days ago)
        end_date: End date in YYYY-MM-DD format (default: today)
    
    Returns:
        Dictionary with statistics
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if not start_date:
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Total records
    cursor.execute('''
        SELECT COUNT(*) as total FROM clock_in_records 
        WHERE date(clock_time) BETWEEN ? AND ?
    ''', (start_date, end_date))
    total = cursor.fetchone()['total']
    
    # Clock-in count
    cursor.execute('''
        SELECT COUNT(*) as count FROM clock_in_records 
        WHERE date(clock_time) BETWEEN ? AND ? AND clock_type = 'clock_in'
    ''', (start_date, end_date))
    clock_in_count = cursor.fetchone()['count']
    
    # Clock-out count
    cursor.execute('''
        SELECT COUNT(*) as count FROM clock_in_records 
        WHERE date(clock_time) BETWEEN ? AND ? AND clock_type = 'clock_out'
    ''', (start_date, end_date))
    clock_out_count = cursor.fetchone()['count']
    
    # Hat usage
    cursor.execute('''
        SELECT COUNT(*) as count FROM clock_in_records 
        WHERE date(clock_time) BETWEEN ? AND ? AND has_hat = 1
    ''', (start_date, end_date))
    hat_count = cursor.fetchone()['count']
    
    # Mask usage
    cursor.execute('''
        SELECT COUNT(*) as count FROM clock_in_records 
        WHERE date(clock_time) BETWEEN ? AND ? AND has_mask = 1
    ''', (start_date, end_date))
    mask_count = cursor.fetchone()['count']
    
    # Long route
    cursor.execute('''
        SELECT COUNT(*) as count FROM clock_in_records 
        WHERE date(clock_time) BETWEEN ? AND ? AND took_long_route = 1
    ''', (start_date, end_date))
    long_route_count = cursor.fetchone()['count']
    
    # Unique users
    cursor.execute('''
        SELECT COUNT(DISTINCT user_name) as count FROM clock_in_records 
        WHERE date(clock_time) BETWEEN ? AND ?
    ''', (start_date, end_date))
    unique_users = cursor.fetchone()['count']
    
    return {
        'total_records': total,
        'clock_in_count': clock_in_count,
        'clock_out_count': clock_out_count,
        'hat_usage': hat_count,
        'mask_usage': mask_count,
        'long_route_count': long_route_count,
        'unique_users': unique_users,
        'start_date': start_date,
        'end_date': end_date
    }


def delete_record(record_id: int) -> bool:
    """Delete a clock-in record by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM clock_in_records WHERE id = ?', (record_id,))
    conn.commit()
    
    return cursor.rowcount > 0


def cleanup_old_records(days: int = 365) -> int:
    """
    Remove clock-in records older than specified days.
    
    Args:
        days: Number of days to keep (default: 365)
    
    Returns:
        Number of records deleted
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    from datetime import timedelta
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    cursor.execute('DELETE FROM clock_in_records WHERE date(clock_time) < ?', (cutoff_date,))
    conn.commit()
    
    return cursor.rowcount


# Initialize database on module load
if __name__ == '__main__':
    init_database()
    print("Clock-in database module loaded successfully")
