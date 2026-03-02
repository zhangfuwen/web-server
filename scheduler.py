import threading
import time
import json
import sqlite3
from datetime import datetime
from websocket_handler import ws_server
from gtd_db import DATABASE_PATH, POOL_SIZE

class TaskScheduler:
    def __init__(self, db=None):
        self.db_path = DATABASE_PATH
        self.stop_event = threading.Event()
    
    def _get_connection(self):
        """Get a direct database connection for the scheduler thread."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    
    def check_due_tasks(self):
        now = datetime.now().isoformat()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.content, s.scheduled_at 
            FROM tasks t 
            JOIN schedules s ON t.id = s.task_id 
            WHERE s.scheduled_at <= ? AND s.reminder_sent = 0
        """, (now,))
        
        for row in cursor.fetchall():
            task_id, content, scheduled_at = row
            # Send WebSocket notification
            ws_server.broadcast(json.dumps({
                'type': 'task:reminder',
                'task_id': task_id,
                'content': content,
                'due_at': scheduled_at
            }))
            # Mark as sent
            cursor.execute("UPDATE schedules SET reminder_sent = 1 WHERE task_id = ?", (task_id,))
            conn.commit()
        conn.close()
    
    def run(self):
        while not self.stop_event.is_set():
            self.check_due_tasks()
            time.sleep(60)
    
    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

# Global instance
scheduler = None
