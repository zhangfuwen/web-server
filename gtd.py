#!/usr/bin/env python3
"""GTD (Getting Things Done) task management module"""

import os
import json
import re
from urllib.parse import urlparse, parse_qs
import subprocess
import sys

# Optional imports for URL title extraction
# These are imported inside the function with try/except to avoid hard dependency

# GTD tasks file path
BASE_DIR = os.getcwd()
GTD_TASKS_FILE = os.path.join(BASE_DIR, 'gtd', 'tasks.md')
STATIC_DIR = os.path.join(BASE_DIR, 'static')


def parse_markdown_to_json(markdown):
    """Parse markdown tasks file to JSON structure with comments support"""
    tasks = {
        'projects': [],
        'next_actions': [],
        'waiting_for': [],
        'someday_maybe': []
    }
    
    lines = markdown.split('\n')
    current_category = None
    current_task = None
    
    for line in lines:
        line = line.rstrip()  # Keep leading spaces for comment detection
        
        if line == '# Projects':
            current_category = 'projects'
        elif line == '# Next Actions':
            current_category = 'next_actions'
        elif line == '# Waiting For':
            current_category = 'waiting_for'
        elif line == '# Someday/Maybe':
            current_category = 'someday_maybe'
        elif line.startswith('- ') and current_category:
            # End previous task if exists
            if current_task:
                tasks[current_category].append(current_task)
            
            # Start new task
            task_text = line[2:].strip()
            completed = False
            actual_text = task_text
            
            if task_text.startswith('[x] '):
                completed = True
                actual_text = task_text[4:].strip()
            elif task_text.startswith('[ ] '):
                actual_text = task_text[4:].strip()
            
            current_task = {
                'text': actual_text,
                'completed': completed,
                'comments': []
            }
        elif line.strip().startswith('<!-- Comment:') and current_task:
            # Extract comment content
            comment_match = re.match(r'^\s*<!-- Comment:\s*(.*?)\s*-->\s*$', line)
            if comment_match:
                comment_text = comment_match.group(1)
                current_task['comments'].append(comment_text)
        elif line.strip().startswith('• Comment:') and current_task:
            # Extract bullet comment
            comment_text = line.strip()[10:].strip()  # Remove "• Comment:" prefix
            current_task['comments'].append(comment_text)
        elif line.strip().startswith('• Note:') and current_task:
            # Extract note as comment
            note_text = line.strip()[8:].strip()  # Remove "• Note:" prefix
            current_task['comments'].append(note_text)
        elif line.strip() == '' and current_task:
            # Empty line might end a task block
            tasks[current_category].append(current_task)
            current_task = None
    
    # Add the last task if it exists
    if current_task and current_category:
        tasks[current_category].append(current_task)
    
    return tasks


def generate_markdown_with_comments(tasks):
    """Generate markdown from tasks object with comments"""
    markdown = ''
    
    # Projects
    markdown += '# Projects\n'
    for task in tasks.get('projects', []):
        prefix = '[x] ' if task.get('completed', False) else '[ ] '
        markdown += f'- {prefix}{task.get("text", "")}\n'
        for comment in task.get('comments', []):
            markdown += f'  <!-- Comment: {comment} -->\n'
    markdown += '\n'
    
    # Next Actions
    markdown += '# Next Actions\n'
    for task in tasks.get('next_actions', []):
        prefix = '[x] ' if task.get('completed', False) else '[ ] '
        markdown += f'- {prefix}{task.get("text", "")}\n'
        for comment in task.get('comments', []):
            markdown += f'  <!-- Comment: {comment} -->\n'
    markdown += '\n'
    
    # Waiting For
    markdown += '# Waiting For\n'
    for task in tasks.get('waiting_for', []):
        prefix = '[x] ' if task.get('completed', False) else '[ ] '
        markdown += f'- {prefix}{task.get("text", "")}\n'
        for comment in task.get('comments', []):
            markdown += f'  <!-- Comment: {comment} -->\n'
    markdown += '\n'
    
    # Someday/Maybe
    markdown += '# Someday/Maybe\n'
    for task in tasks.get('someday_maybe', []):
        prefix = '[x] ' if task.get('completed', False) else '[ ] '
        markdown += f'- {prefix}{task.get("text", "")}\n'
        for comment in task.get('comments', []):
            markdown += f'  <!-- Comment: {comment} -->\n'
    
    return markdown


def read_tasks():
    """Read tasks from markdown file"""
    try:
        with open(GTD_TASKS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        raise Exception(f"Error reading tasks file: {str(e)}")


def write_tasks(tasks):
    """Write tasks to markdown file"""
    try:
        markdown = generate_markdown_with_comments(tasks)
        with open(GTD_TASKS_FILE, 'w', encoding='utf-8') as f:
            f.write(markdown)
        return True
    except Exception as e:
        raise Exception(f"Error writing tasks file: {str(e)}")


def clear_tasks():
    """Clear all tasks"""
    try:
        with open(GTD_TASKS_FILE, 'w', encoding='utf-8') as f:
            f.write("# Projects\n\n# Next Actions\n\n# Waiting For\n\n# Someday/Maybe\n")
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
            
            # Set a reasonable timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            # Parse HTML and extract title
            soup = BeautifulSoup(response.content, 'html.parser')
            title_tag = soup.find('title')
            
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                if title:  # Non-empty title
                    return title
        except Exception as e:
            # If fetching fails, continue to other strategies
            pass
        
        # Strategy 2: Extract meaningful name from URL path
        parsed_url = urlparse(url)
        
        # Try to get the last part of the path
        if parsed_url.path and parsed_url.path != '/':
            path_parts = [p for p in parsed_url.path.split('/') if p]
            if path_parts:
                last_part = path_parts[-1]
                # Clean up the filename (remove extensions, decode URL encoding)
                last_part = re.sub(r'\.[a-zA-Z0-9]+$', '', last_part)
                last_part = re.sub(r'[-_]+', ' ', last_part)
                last_part = last_part.replace('%20', ' ')
                
                # Capitalize first letter of each word
                words = last_part.split()
                if len(words) <= 5:  # Only use if not too long
                    title = ' '.join(word.capitalize() for word in words)
                    if title:
                        return title
        
        # Strategy 3: Use domain name with path
        if parsed_url.netloc:
            domain = parsed_url.netloc
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Get first part of domain (before first dot)
            domain_part = domain.split('.')[0]
            
            if parsed_url.path and parsed_url.path != '/':
                # Combine domain with simplified path
                simple_path = parsed_url.path.replace('/', ' › ')
                title = f"{domain_part.capitalize()}{simple_path}"
            else:
                title = domain_part.capitalize()
            
            return title
        
        # Strategy 4: Return the URL itself (last resort)
        return url
        
    except Exception as e:
        # If all strategies fail, return the URL
        return url


class GTDHandler:
    """GTD request handler mixin"""
    
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
                # Fallback to directory listing
                return self.list_directory(os.path.join(BASE_DIR, 'gtd'))
        except Exception as e:
            self.send_error(500, f"Error serving GTD app: {repr(e)}")
    
    def serve_gtd_static(self, path):
        """Serve static files from GTD directory"""
        try:
            # Clean up the path
            clean_path = path.lstrip('/')
            if clean_path == 'gtd/' or clean_path == 'gtd/index.html':
                return self.serve_gtd_app()
            
            # Map /gtd/xxx to static/gtd/xxx
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
        """Serve the tasks.md file content"""
        try:
            content = read_tasks()
            
            # Check if client wants JSON
            accept_header = self.headers.get('Accept', '')
            if 'application/json' in accept_header:
                # Parse markdown to JSON
                tasks = parse_markdown_to_json(content)
                json_content = json.dumps(tasks)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Content-Length", str(len(json_content)))
                self.end_headers()
                self.wfile.write(json_content.encode('utf-8'))
            else:
                # Return markdown
                self.send_response(200)
                self.send_header("Content-type", "text/markdown; charset=utf-8")
                self.send_header("Content-Length", str(len(content.encode('utf-8'))))
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error reading tasks file: {str(e)}")
    
    def add_gtd_task(self):
        """Add a new task (not used in current frontend, but available for API)"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            task_data = json.loads(post_data)
            
            # This would be implemented if needed
            self.send_response(201)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Task added"}).encode('utf-8'))
            
        except Exception as e:
            self.send_error(400, f"Error adding task: {str(e)}")
    
    def update_gtd_tasks(self):
        """Update the entire tasks.md file with comments support"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            content = self.rfile.read(content_length).decode('utf-8')
            
            # Check content type
            content_type = self.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                # JSON format - parse and convert to markdown
                tasks = json.loads(content)
                markdown = generate_markdown_with_comments(tasks)
            else:
                # Assume markdown format (text/markdown or text/plain)
                markdown = content
            
            # Write to file
            with open(GTD_TASKS_FILE, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Tasks updated successfully"}).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error updating tasks: {str(e)}")
    
    def clear_gtd_tasks(self):
        """Clear all tasks"""
        try:
            with open(GTD_TASKS_FILE, 'w', encoding='utf-8') as f:
                f.write("# Projects\n\n# Next Actions\n\n# Waiting For\n\n# Someday/Maybe\n")
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Tasks cleared successfully"}).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error clearing tasks: {str(e)}")
    
    def extract_title_api(self):
        """Extract title from URL for GTD tasks"""
        try:
            query = urlparse(self.path).query
            params = parse_qs(query)
            url = params.get('url', [None])[0]
            
            if not url:
                self.send_error(400, "Missing URL parameter")
                return
            
            title = extract_title_from_url(url)
            response_data = {"title": title}
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            response_json = json.dumps(response_data)
            self.send_header("Content-Length", str(len(response_json)))
            self.end_headers()
            self.wfile.write(response_json.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error extracting title: {str(e)}")