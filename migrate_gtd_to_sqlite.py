#!/usr/bin/env python3
"""
Migration script to migrate GTD data from JSON to SQLite.
Creates backup before migration and validates data integrity.
"""

import os
import sys
import json
import shutil
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_DIR, GTD_DATA_DIR, GTD_TASKS_FILE
from gtd_db_schema import create_schema, verify_schema
import gtd_db as db

# Use APP_DIR-based GTD data (where the actual tasks.json is)
ACTUAL_GTD_DIR = os.path.join(APP_DIR, 'gtd')
ACTUAL_TASKS_FILE = os.path.join(ACTUAL_GTD_DIR, 'tasks.json')

# Database path - store in APP_DIR for easier management
DATABASE_PATH = os.path.join(ACTUAL_GTD_DIR, 'gtd.db')
BACKUP_DIR = os.path.join(ACTUAL_GTD_DIR, 'backups')

# Override config for this migration
GTD_DATA_DIR = ACTUAL_GTD_DIR
GTD_TASKS_FILE = ACTUAL_TASKS_FILE
db.DATABASE_PATH = DATABASE_PATH


def create_backup():
    """Create backup of existing JSON data."""
    if not os.path.exists(GTD_TASKS_FILE):
        print("No existing JSON file found, skipping backup")
        return None
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'tasks_backup_{timestamp}.json')
    
    shutil.copy2(GTD_TASKS_FILE, backup_path)
    print(f"Backup created: {backup_path}")
    return backup_path


def migrate_json_to_sqlite(json_path: str) -> dict:
    """Migrate JSON data to SQLite database."""
    stats = {
        'tasks_migrated': 0,
        'comments_migrated': 0,
        'subtasks_migrated': 0,
        'errors': []
    }
    
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Category mapping
    category_map = {
        'projects': 'Projects',
        'next_actions': 'Next Actions',
        'waiting_for': 'Waiting For',
        'someday_maybe': 'Someday/Maybe'
    }
    
    # Migrate tasks
    for json_category, db_category in category_map.items():
        tasks = data.get(json_category, [])
        
        for task in tasks:
            try:
                task_id = task.get('id', str(uuid.uuid4())[:8])
                content = task.get('text', task.get('content', ''))
                done = 1 if task.get('completed', False) else 0
                
                # Extract priority from comments if present
                priority = 'medium'
                due_date = task.get('due_date', None)
                
                # Process comments to extract metadata
                comments = task.get('comments', [])
                
                # Create task - note: create_task doesn't accept 'done' parameter, set it after
                task_result = db.create_task(
                    task_id=task_id,
                    user_id=None,  # Single user mode for now
                    content=content,
                    category=db_category,
                    priority=priority,
                    due_date=due_date
                )
                
                # Update done status
                if task_result and done:
                    db.update_task(task_id, done=done)
                stats['tasks_migrated'] += 1
                
                # Migrate comments
                if comments:
                    for comment in comments:
                        try:
                            comment_id = comment.get('id', str(uuid.uuid4())[:8])
                            comment_content = comment.get('text', comment.get('content', ''))
                            
                            # Check if it's a subtask
                            if comment_content.strip().startswith('[ ]') or comment_content.strip().startswith('[x]'):
                                # It's a subtask
                                subtask_done = 1 if comment_content.strip().startswith('[x]') else 0
                                subtask_content = comment_content[3:].strip()
                                
                                db.create_subtask(
                                    subtask_id=comment_id,
                                    task_id=task_id,
                                    content=subtask_content,
                                    done=subtask_done
                                )
                                stats['subtasks_migrated'] += 1
                            else:
                                # Regular comment
                                db.create_comment(
                                    comment_id=comment_id,
                                    task_id=task_id,
                                    user_id=None,
                                    content=comment_content
                                )
                                stats['comments_migrated'] += 1
                        except Exception as e:
                            stats['errors'].append(f"Comment migration error: {e}")
                
            except Exception as e:
                stats['errors'].append(f"Task migration error for {task.get('id', 'unknown')}: {e}")
    
    return stats


def verify_migration():
    """Verify migrated data."""
    print("\nVerifying migration...")
    
    # Check database exists
    if not os.path.exists(DATABASE_PATH):
        print("❌ Database file not found")
        return False
    
    # Verify schema
    if not verify_schema(DATABASE_PATH):
        print("❌ Schema verification failed")
        return False
    
    # Check data
    stats = db.get_task_statistics()
    print(f"✓ Database contains {stats['total']} tasks")
    print(f"  - Completed: {stats['completed']}")
    print(f"  - Pending: {stats['pending']}")
    
    # Check each category
    categories = ['Projects', 'Next Actions', 'Waiting For', 'Someday/Maybe']
    for category in categories:
        tasks = db.get_tasks_by_category(category)
        print(f"  - {category}: {len(tasks)} tasks")
    
    return True


def rollback(backup_path: str):
    """Rollback migration by restoring backup."""
    if backup_path and os.path.exists(backup_path):
        shutil.copy2(backup_path, GTD_TASKS_FILE)
        print(f"Rolled back to backup: {backup_path}")
        
        # Remove database
        if os.path.exists(DATABASE_PATH):
            os.remove(DATABASE_PATH)
            print("Database removed")
        
        return True
    return False


def main():
    """Run migration."""
    print("=" * 60)
    print("GTD JSON to SQLite Migration")
    print("=" * 60)
    print(f"Source: {GTD_TASKS_FILE}")
    print(f"Target: {DATABASE_PATH}")
    print()
    
    # Step 1: Create backup
    print("Step 1: Creating backup...")
    backup_path = create_backup()
    
    # Step 2: Initialize database
    print("\nStep 2: Initializing database...")
    create_schema(DATABASE_PATH)
    
    # Step 3: Migrate data
    print("\nStep 3: Migrating data...")
    if os.path.exists(GTD_TASKS_FILE):
        stats = migrate_json_to_sqlite(GTD_TASKS_FILE)
        print(f"✓ Tasks migrated: {stats['tasks_migrated']}")
        print(f"✓ Comments migrated: {stats['comments_migrated']}")
        print(f"✓ Subtasks migrated: {stats['subtasks_migrated']}")
        
        if stats['errors']:
            print(f"⚠ Errors: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
    else:
        print("No JSON file found, creating empty database")
    
    # Step 4: Verify migration
    print("\nStep 4: Verification...")
    if verify_migration():
        print("\n✅ Migration completed successfully!")
        print(f"\nBackup saved at: {backup_path}")
        print("\nNext steps:")
        print("1. Test the application with new database")
        print("2. Update gtd.py to use database instead of JSON")
        print("3. Keep backup for 7 days before deletion")
        return True
    else:
        print("\n❌ Migration verification failed!")
        print("Attempting rollback...")
        if rollback(backup_path):
            print("✅ Rollback successful")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
