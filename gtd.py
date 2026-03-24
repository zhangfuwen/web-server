#!/usr/bin/env python3
"""
GTD (Getting Things Done) task management module with multi-user support.
Each user has their own isolated task data.
"""

import os
import json
import re
from urllib.parse import urlparse, parse_qs
import subprocess
import sys
from datetime import datetime
import uuid

# Import configuration
from config import APP_DIR, WEB_ROOT, GTD_DATA_DIR, GTD_TASKS_FILE

# Import schema validation
from schema import validate_task, validate_url, get_validation_error_response

# GTD tasks file path - now supports per-user directories
BASE_DIR = APP_DIR
GTD_BASE_DIR = GTD_DATA_DIR
STATIC_DIR = os.path.join(WEB_ROOT, 'static')

# Default tasks file (for backwards compatibility)
# GTD_TASKS_FILE is now imported from config


def get_user_tasks_dir(user_id):
    """Get the tasks directory for a specific user."""
    user_dir = os.path.join(GTD_BASE_DIR, 'users', str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def get_user_tasks_file(user_id):
    """Get the tasks file path for a specific user."""
    return os.path.join(get_user_tasks_dir(user_id), 'tasks.json')


def load_tasks(user_id=None):
    """Load tasks from JSON file. If user_id provided, load user-specific tasks."""
    if user_id:
        tasks_file = get_user_tasks_file(user_id)
    else:
        tasks_file = GTD_TASKS_FILE
    
    if not os.path.exists(tasks_file):
        # Create default structure if file doesn't exist
        default_tasks = {
            'projects': [],
            'next_actions': [],
            'waiting_for': [],
            'someday_maybe': []
        }
        save_tasks(default_tasks, user_id)
        return default_tasks
    
    with open(tasks_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_tasks(tasks, user_id=None):
    """Save tasks to JSON file. If user_id provided, save to user-specific file."""
    if user_id:
        tasks_file = get_user_tasks_file(user_id)
        # Ensure user directory exists
        os.makedirs(os.path.dirname(tasks_file), exist_ok=True)
    else:
        tasks_file = GTD_TASKS_FILE
    
    with open(tasks_file, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def read_tasks(user_id=None):
    """Read tasks from JSON file"""
    try:
        tasks = load_tasks(user_id)
        return json.dumps(tasks, ensure_ascii=False)
    except Exception as e:
        raise Exception(f"Error reading tasks file: {str(e)}")


def write_tasks(tasks, user_id=None):
    """Write tasks to JSON file"""
    try:
        save_tasks(tasks, user_id)
        return True
    except Exception as e:
        raise Exception(f"Error writing tasks file: {str(e)}")


def clear_tasks(user_id=None):
    """Clear all tasks"""
    try:
        default_tasks = {
            'projects': [],
            'next_actions': [],
            'waiting_for': [],
            'someday_maybe': []
        }
        save_tasks(default_tasks, user_id)
        return True
    except Exception as e:
        raise Exception(f"Error clearing tasks: {str(e)}")


def extract_title_from_url(url):
    """Extract title from URL using multiple strategies"""
    try:
        # Strategy 1: Try to fetch webpage and extract title
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            title_tag = soup.find('title')
            
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                if title:
                    return title
        except Exception as e:
            # If fetch fails and URL looks malformed (no scheme, not an absolute/relative path), return as is
            if '://' not in url and not url.startswith('/') and not url.startswith('./') and not url.startswith('../'):
                return url
            # Otherwise, fall through to path processing
            pass
        
        # Strategy 2: Extract meaningful name from URL path
        parsed_url = urlparse(url)
        
        if parsed_url.path and parsed_url.path != '/':
            path_parts = [p for p in parsed_url.path.split('/') if p]
            if path_parts:
                last_part = path_parts[-1]
                last_part = re.sub(r'\.[a-zA-Z0-9]+$', '', last_part)
                last_part = re.sub(r'[-_]+', ' ', last_part)
                last_part = last_part.replace('%20', ' ')
                
                words = last_part.split()
                if len(words) <= 5:
                    title = ' '.join(word.capitalize() for word in words)
                    if title:
                        return title
        
        # Strategy 3: Use domain name with path
        if parsed_url.netloc:
            domain = parsed_url.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            domain_part = domain.split('.')[0]
            
            if parsed_url.path and parsed_url.path != '/':
                simple_path = parsed_url.path.replace('/', ' › ')
                title = f"{domain_part.capitalize()}{simple_path}"
            else:
                title = domain_part.capitalize()
            
            return title
        
        # Strategy 4: Return the URL itself (last resort)
        return url
        
    except Exception as e:
        return url


class GTDHandler:
    """GTD request handler mixin with multi-user support"""
    
    def serve_gtd_app(self):
        """Serve the GTD application"""
        try:
            gtd_index = os.path.join(STATIC_DIR, 'gtd', 'index.html')
            if os.path.exists(gtd_index):
                with open(gtd_index, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content.encode('utf-8'))))
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                return self.list_directory(os.path.join(BASE_DIR, 'gtd'))
        except Exception as e:
            self.send_error(500, f"Error serving GTD app: {repr(e)}")
    
    def serve_gtd_static(self, path):
        """Serve static files from GTD directory"""
        try:
            clean_path = path.lstrip('/')
            if clean_path == 'gtd/' or clean_path == 'gtd/index.html':
                return self.serve_gtd_app()
            
            if clean_path.startswith('gtd/'):
                static_file_path = os.path.join(STATIC_DIR, clean_path)
            else:
                static_file_path = os.path.join(STATIC_DIR, 'gtd', clean_path)
            
            if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
                return self.serve_file(static_file_path)
            else:
                return self.serve_gtd_app()
        except Exception as e:
            self.send_error(500, f"Error serving GTD static file: {repr(e)}")
    
    def serve_gtd_tasks(self):
        """Serve GTD tasks as JSON (with user isolation)"""
        try:
            user_id = getattr(self, 'current_user_id', None)
            tasks_json = read_tasks(user_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(tasks_json.encode('utf-8'))))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(tasks_json.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error reading tasks: {str(e)}")
    
    def add_gtd_task(self):
        """Add a new GTD task (with user isolation)"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            # Validate incoming task data
            is_valid, error_message = validate_task(data, schema_type="create")
            if not is_valid:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = get_validation_error_response(error_message)
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
            
            user_id = getattr(self, 'current_user_id', None)
            tasks = load_tasks(user_id)
            
            category = data.get('category', 'next_actions')
            if category not in tasks:
                category = 'next_actions'
            
            now = datetime.now().isoformat()
            new_task = {
                'id': str(uuid.uuid4())[:8],
                'text': data.get('text', '') or data.get('content', ''),
                'completed': False,
                'createdAt': now,
                'updatedAt': now,
                'comments': []
            }
            
            tasks[category].append(new_task)
            save_tasks(tasks, user_id)
            
            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(new_task).encode('utf-8'))
            
        except json.JSONDecodeError as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = {"success": False, "error": "Invalid JSON", "message": str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error adding task: {str(e)}")
    
    def update_gtd_tasks(self):
        """Update GTD tasks (with user isolation)"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            # Validate incoming bulk task data
            is_valid, error_message = validate_task(data, schema_type="bulk")
            if not is_valid:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = get_validation_error_response(error_message)
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
            
            user_id = getattr(self, 'current_user_id', None)
            tasks = load_tasks(user_id)
            
            # Update tasks based on the data
            for category in ['projects', 'next_actions', 'waiting_for', 'someday_maybe']:
                if category in data:
                    tasks[category] = data[category]
            
            save_tasks(tasks, user_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode('utf-8'))
            
        except json.JSONDecodeError as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = {"success": False, "error": "Invalid JSON", "message": str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error updating tasks: {str(e)}")
    
    def clear_gtd_tasks(self):
        """Clear all GTD tasks (with user isolation)"""
        try:
            user_id = getattr(self, 'current_user_id', None)
            clear_tasks(user_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error clearing tasks: {str(e)}")
    
    def extract_title_api(self):
        """API endpoint to extract title from URL"""
        try:
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            url = query_params.get('url', [None])[0]
            
            if not url:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"success": False, "error": "Validation failed", "message": "URL parameter required"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
            
            # Validate URL format
            is_valid, error_message = validate_url({"url": url})
            if not is_valid:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = get_validation_error_response(error_message)
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
            
            title = extract_title_from_url(url)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'title': title, 'url': url}).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error extracting title: {str(e)}")
    
    def serve_gtd_schedules(self):
        """Serve all scheduled tasks as JSON"""
        try:
            from gtd_db import get_scheduled_tasks
            user_id = getattr(self, 'current_user_id', None)
            schedules = get_scheduled_tasks(user_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(json.dumps(schedules).encode('utf-8'))))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(schedules).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error reading schedules: {str(e)}")
    
    def add_gtd_schedule(self):
        """Add a new schedule for a task"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            task_id = data.get('task_id')
            scheduled_at = data.get('scheduled_at')
            recurrence = data.get('recurrence', 'none')
            
            if not task_id or not scheduled_at:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"success": False, "error": "task_id and scheduled_at are required"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
            
            from gtd_db import add_schedule, task_exists
            if not task_exists(task_id):
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"success": False, "error": "Task not found"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
            
            schedule = add_schedule(task_id, scheduled_at, recurrence)
            
            if schedule:
                self.send_response(201)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(schedule).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"success": False, "error": "Failed to create schedule"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
            
        except json.JSONDecodeError as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = {"success": False, "error": "Invalid JSON", "message": str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error adding schedule: {str(e)}")
    
    def update_gtd_schedule(self):
        """Update a schedule (mark reminder as sent or update recurrence)"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            schedule_id = data.get('id')
            reminder_sent = data.get('reminder_sent')
            recurrence = data.get('recurrence')
            
            if not schedule_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"success": False, "error": "schedule id is required"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
            
            from gtd_db import update_schedule_reminder_sent, get_schedule
            if reminder_sent is not None:
                success = update_schedule_reminder_sent(schedule_id, reminder_sent)
            else:
                success = True
            
            if success:
                schedule = get_schedule(schedule_id)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(schedule).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"success": False, "error": "Schedule not found"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
            
        except json.JSONDecodeError as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = {"success": False, "error": "Invalid JSON", "message": str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error updating schedule: {str(e)}")
    
    def delete_gtd_schedule(self):
        """Delete/cancel a schedule"""
        try:
            # Get schedule ID from query string
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            schedule_id = query_params.get('id', [None])[0]
            
            if not schedule_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"success": False, "error": "schedule id is required"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
            
            from gtd_db import cancel_schedule
            success = cancel_schedule(schedule_id)
            
            if success:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"success": False, "error": "Schedule not found"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error deleting schedule: {str(e)}")


# Backwards compatibility
if __name__ == '__main__':
    # Test the module
    print("GTD Module loaded successfully")
    print(f"Base directory: {BASE_DIR}")
    print(f"Default tasks file: {GTD_TASKS_FILE}")
    
    # Test loading tasks
    tasks = load_tasks()
    print(f"Loaded {sum(len(tasks[k]) for k in tasks)} tasks")
