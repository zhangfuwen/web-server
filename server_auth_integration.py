#!/usr/bin/env python3
"""
Authentication integration patch for Molt Server.
This file provides methods to be added to the main server for auth support.
"""

import json
from urllib.parse import parse_qs

# Import AUTH_ENABLED from auth module
try:
    from auth import AUTH_ENABLED
except ImportError:
    AUTH_ENABLED = False

# Auth integration methods for UnifiedHTTPRequestHandler

def serve_current_user(self):
    """Serve current authenticated user info."""
    if not AUTH_ENABLED:
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'authenticated': False}).encode('utf-8'))
        return
    
    session = self.get_session_from_request()
    
    if not session:
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'authenticated': False}).encode('utf-8'))
        return
    
    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps({
        'authenticated': True,
        'user': {
            'id': session['user_id'],
            'email': session['email'],
            'name': session['name'],
            'avatar': session.get('avatar'),
            'provider': session.get('provider')
        }
    }).encode('utf-8'))


def get_user_gtd_tasks_file(self):
    """Get the GTD tasks file path for current user (if auth enabled)."""
    if not AUTH_ENABLED:
        return GTD_TASKS_FILE
    
    session = self.get_session_from_request()
    if not session:
        return GTD_TASKS_FILE
    
    return get_user_gtd_path(session['user_id'])


# Patch the handler methods to use user-specific paths
def patch_gtd_for_auth():
    """Patch GTD handler methods to use user-specific data paths by setting current_user_id."""
    from gtd import GTDHandler
    
    # Store original methods
    original_serve_gtd_tasks = GTDHandler.serve_gtd_tasks
    original_add_gtd_task = GTDHandler.add_gtd_task
    original_update_gtd_tasks = GTDHandler.update_gtd_tasks
    original_clear_gtd_tasks = GTDHandler.clear_gtd_tasks
    
    def set_current_user_id(self):
        """Set current_user_id from session if auth is enabled."""
        if AUTH_ENABLED:
            session = self.get_session_from_request()
            if session:
                self.current_user_id = session['user_id']
                return
        self.current_user_id = None
    
    def serve_gtd_tasks_patched(self):
        """Serve tasks for current user."""
        set_current_user_id(self)
        return original_serve_gtd_tasks(self)
    
    def add_gtd_task_patched(self):
        """Add task for current user."""
        set_current_user_id(self)
        return original_add_gtd_task(self)
    
    def update_gtd_tasks_patched(self):
        """Update tasks for current user."""
        set_current_user_id(self)
        return original_update_gtd_tasks(self)
    
    def clear_gtd_tasks_patched(self):
        """Clear tasks for current user."""
        set_current_user_id(self)
        return original_clear_gtd_tasks(self)
    
    GTDHandler.serve_gtd_tasks = serve_gtd_tasks_patched
    GTDHandler.add_gtd_task = add_gtd_task_patched
    GTDHandler.update_gtd_tasks = update_gtd_tasks_patched
    GTDHandler.clear_gtd_tasks = clear_gtd_tasks_patched
    
    print("GTD module patched for multi-user support")


# Apply patches when module is loaded
patch_gtd_for_auth()
print("Auth integration loaded successfully")
