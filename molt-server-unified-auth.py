#!/usr/bin/env python3
"""
Molt Server - Unified HTTP Server with Authentication
Supports Google OAuth 2.0 and WeChat OAuth 2.0
"""

import os
import sys
import json
import psutil
import time
import hashlib
import secrets
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, urlparse, parse_qs, urlencode
import subprocess
import threading
import socket
from socketserver import ThreadingMixIn
import requests

# BeautifulSoup is optional, for URL title extraction
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

# Set working directory - supports WEB_ROOT environment variable, default /var/www/html
BASE_DIR = os.environ.get('WEB_ROOT', '/var/www/html')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Import GTD module
from gtd import GTDHandler, GTD_TASKS_FILE

# Import authentication module
try:
    from auth import (
        init_auth, get_session, create_session, delete_session,
        get_google_auth_url, get_wechat_auth_url, authenticate_user,
        SESSION_COOKIE_NAME, CSRF_COOKIE_NAME, CSRF_HEADER_NAME,
        set_session_cookie, set_csrf_cookie, clear_auth_cookies,
        generate_csrf_token, check_rate_limit, get_client_ip,
        login_required, api_login_required
    )
    AUTH_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Authentication module not available: {e}")
    AUTH_AVAILABLE = False

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads."""
    daemon_threads = True

class UnifiedHTTPRequestHandler(GTDHandler, BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    
    def __init__(self, *args, **kwargs):
        self.current_user = None
        self.current_user_id = None
        super().__init__(*args, **kwargs)
    
    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()
    
    def get_cookie_value(self, name):
        """Extract cookie value from Cookie header."""
        cookie_header = self.headers.get('Cookie', '')
        cookies = parse_qs(cookie_header, keep_blank_values=True)
        
        # parse_qs returns lists, get first value
        values = cookies.get(name, [])
        if values:
            return values[0]
        return None
    
    def send_json_response(self, data, status=200):
        """Send JSON response."""
        content = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content.encode('utf-8'))))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def redirect_to_login(self):
        """Redirect to login page."""
        self.send_response(302)
        self.send_header('Location', '/auth/login')
        self.end_headers()
    
    def send_error(self, code, message=None, explain=None):
        """Override to ensure UTF-8 encoding for error messages."""
        try:
            if message is None:
                if code in self.responses:
                    message = self.responses[code][0]
                else:
                    message = ''
            if explain is None:
                if code in self.responses:
                    explain = self.responses[code][1]
                else:
                    explain = ''
            
            msg = f"{code} {message}"
            if explain:
                msg += f": {explain}"
            
            self.log_error("code %d, message %s", code, message)
            
            self.send_response(code)
            self.send_header('Connection', 'close')
            
            content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{code} {message}</title>
</head>
<body>
    <h1>{code} {message}</h1>
    <p>{explain}</p>
</body>
</html>"""
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content.encode('utf-8'))))
            self.end_headers()
            if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
                self.wfile.write(content.encode('utf-8'))
        except Exception:
            super().send_error(code, message, explain)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # Favicon request
        if path == '/favicon.ico':
            return self.serve_favicon()
        
        # Authentication routes
        if AUTH_AVAILABLE:
            # Login page
            if path == '/auth/login':
                return self.serve_login_page()
            
            # Google OAuth
            elif path == '/auth/google/login':
                return self.handle_google_login()
            elif path == '/auth/google/callback':
                return self.handle_google_callback(query_params)
            
            # WeChat OAuth
            elif path == '/auth/wechat/login':
                return self.handle_wechat_login()
            elif path == '/auth/wechat/callback':
                return self.handle_wechat_callback(query_params)
            
            # Logout
            elif path == '/auth/logout':
                return self.handle_logout()
            
            # User profile
            elif path == '/api/auth/me':
                return self.handle_get_current_user()
        
        # System info page
        if path == '/system-info':
            return self.serve_system_info()
        
        # BotReports endpoints
        elif path == '/api/bot-reports':
            return self.serve_bot_reports_list()
        elif path == '/BotReports' or path == '/BotReports/':
            return self.serve_bot_reports_index()
        
        # GTD API endpoints - require authentication
        elif path == '/api/gtd/tasks':
            if not AUTH_AVAILABLE or not self.current_user:
                return self.redirect_to_login()
            return self.serve_gtd_tasks()
        elif path == '/api/gtd/title':
            return self.extract_title_api()
        
        # GTD app - require authentication
        elif path == '/gtd' or path == '/gtd/':
            if not AUTH_AVAILABLE or not self.current_user:
                return self.redirect_to_login()
            return self.serve_gtd_app()
        elif path.startswith('/gtd/'):
            if not AUTH_AVAILABLE or not self.current_user:
                return self.redirect_to_login()
            return self.serve_gtd_static(path)
        
        # KodExplorer special handling - proxy to Apache if needed
        elif path.startswith('/kodexplorer'):
            if self.is_port_open('localhost', 8080):
                return self.proxy_to_apache(path)
            else:
                return self.serve_file_or_directory(path)
        
        # Root path - show enhanced file list
        elif path == '/' or path == '/index.html':
            return self.serve_enhanced_file_list('/')
        
        # Other files/directories
        else:
            return self.serve_file_or_directory(path)
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # GTD API endpoints - require authentication
        if path == '/api/gtd/tasks':
            if not AUTH_AVAILABLE or not self.current_user:
                self.send_json_response({'error': 'Authentication required'}, 401)
                return
            return self.add_gtd_task()
        else:
            self.send_error(404, "API endpoint not found")
    
    def do_PUT(self):
        """Handle PUT requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # GTD API endpoints - require authentication
        if path == '/api/gtd/tasks':
            if not AUTH_AVAILABLE or not self.current_user:
                self.send_json_response({'error': 'Authentication required'}, 401)
                return
            return self.update_gtd_tasks()
        else:
            self.send_error(404, "API endpoint not found")
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # GTD API endpoints - require authentication
        if path == '/api/gtd/tasks':
            if not AUTH_AVAILABLE or not self.current_user:
                self.send_json_response({'error': 'Authentication required'}, 401)
                return
            return self.clear_gtd_tasks()
        else:
            self.send_error(404, "API endpoint not found")
    
    # ==================== Authentication Handlers ====================
    
    def serve_login_page(self):
        """Serve the login page."""
        login_html_path = os.path.join(STATIC_DIR, 'auth', 'login.html')
        
        if os.path.exists(login_html_path):
            with open(login_html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        else:
            self.send_error(500, "Login page not found")
    
    def handle_google_login(self):
        """Initiate Google OAuth flow."""
        if not AUTH_AVAILABLE:
            self.send_error(500, "Authentication not available")
            return
        
        # Check rate limit
        client_ip = get_client_ip(self)
        if not check_rate_limit(client_ip):
            self.send_error(429, "Too many requests. Please try again later.")
            return
        
        # Generate state token for CSRF protection
        state = generate_csrf_token()
        
        # Set state in cookie
        self.send_response(302)
        self.send_header('Set-Cookie', f'oauth_state={state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600')
        self.send_header('Location', get_google_auth_url(state))
        self.end_headers()
    
    def handle_google_callback(self, query_params):
        """Handle Google OAuth callback."""
        if not AUTH_AVAILABLE:
            self.send_error(500, "Authentication not available")
            return
        
        # Get code and state from query params
        code = query_params.get('code', [None])[0]
        state = query_params.get('state', [None])[0]
        error = query_params.get('error', [None])[0]
        
        if error:
            return self.redirect_with_error(f'/auth/login?error={error}')
        
        if not code:
            return self.redirect_with_error('/auth/login?error=oauth_failed')
        
        # Verify state token
        cookie_state = self.get_cookie_value('oauth_state')
        if not cookie_state or cookie_state != state:
            return self.redirect_with_error('/auth/login?error=invalid_state')
        
        # Authenticate user
        user, error_msg = authenticate_user('google', code)
        
        if error_msg or not user:
            return self.redirect_with_error(f'/auth/login?error=oauth_failed')
        
        # Create session
        client_ip = get_client_ip(self)
        user_agent = self.headers.get('User-Agent', '')
        session_token = create_session(user['id'], ip_address=client_ip, user_agent=user_agent)
        
        if not session_token:
            return self.redirect_with_error('/auth/login?error=session_error')
        
        # Set session cookie
        self.send_response(302)
        set_session_cookie(self, session_token)
        csrf_token = set_csrf_cookie(self, session_token)
        self.send_header('Location', '/gtd')
        self.end_headers()
    
    def handle_wechat_login(self):
        """Initiate WeChat OAuth flow."""
        if not AUTH_AVAILABLE:
            self.send_error(500, "Authentication not available")
            return
        
        # Check rate limit
        client_ip = get_client_ip(self)
        if not check_rate_limit(client_ip):
            self.send_error(429, "Too many requests. Please try again later.")
            return
        
        # Generate state token for CSRF protection
        state = generate_csrf_token()
        
        # Set state in cookie
        self.send_response(302)
        self.send_header('Set-Cookie', f'oauth_state={state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600')
        self.send_header('Location', get_wechat_auth_url(state))
        self.end_headers()
    
    def handle_wechat_callback(self, query_params):
        """Handle WeChat OAuth callback."""
        if not AUTH_AVAILABLE:
            self.send_error(500, "Authentication not available")
            return
        
        # Get code and state from query params
        code = query_params.get('code', [None])[0]
        state = query_params.get('state', [None])[0]
        error = query_params.get('error', [None])[0]
        
        if error:
            return self.redirect_with_error(f'/auth/login?error={error}')
        
        if not code:
            return self.redirect_with_error('/auth/login?error=oauth_failed')
        
        # Verify state token
        cookie_state = self.get_cookie_value('oauth_state')
        if not cookie_state or cookie_state != state:
            return self.redirect_with_error('/auth/login?error=invalid_state')
        
        # Authenticate user
        user, error_msg = authenticate_user('wechat', code)
        
        if error_msg or not user:
            return self.redirect_with_error(f'/auth/login?error=oauth_failed')
        
        # Create session
        client_ip = get_client_ip(self)
        user_agent = self.headers.get('User-Agent', '')
        session_token = create_session(user['id'], ip_address=client_ip, user_agent=user_agent)
        
        if not session_token:
            return self.redirect_with_error('/auth/login?error=session_error')
        
        # Set session cookie
        self.send_response(302)
        set_session_cookie(self, session_token)
        csrf_token = set_csrf_cookie(self, session_token)
        self.send_header('Location', '/gtd')
        self.end_headers()
    
    def handle_logout(self):
        """Handle logout."""
        if not AUTH_AVAILABLE:
            self.send_error(500, "Authentication not available")
            return
        
        # Get session token
        session_token = self.get_cookie_value(SESSION_COOKIE_NAME)
        
        if session_token:
            # Delete session from database
            delete_session(session_token)
        
        # Clear cookies
        self.send_response(302)
        clear_auth_cookies(self)
        self.send_header('Location', '/auth/login')
        self.end_headers()
    
    def handle_get_current_user(self):
        """Get current user info (API endpoint)."""
        if not AUTH_AVAILABLE:
            self.send_json_response({'error': 'Authentication not available'}, 500)
            return
        
        session_token = self.get_cookie_value(SESSION_COOKIE_NAME)
        
        if not session_token:
            self.send_json_response({'authenticated': False}, 200)
            return
        
        session = get_session(session_token)
        
        if not session:
            self.send_json_response({'authenticated': False}, 200)
            return
        
        # Return user info
        user_info = {
            'authenticated': True,
            'user_id': session['user_id'],
            'email': session['email'],
            'name': session['name'],
            'avatar': session.get('avatar'),
            'provider': session.get('provider')
        }
        
        self.send_json_response(user_info, 200)
    
    def redirect_with_error(self, location):
        """Redirect with error message."""
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()
    
    # ==================== Existing Methods (preserved) ====================
    
    def is_port_open(self, host, port):
        """Check if a port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def proxy_to_apache(self, path):
        """Proxy request to Apache running on port 8080"""
        try:
            import urllib.request
            import urllib.parse
            
            apache_url = f"http://localhost:8080{path}"
            if self.path.find('?') != -1:
                apache_url += self.path[self.path.find('?'):]
            
            req = urllib.request.Request(apache_url)
            for header in self.headers:
                if header.lower() not in ['host', 'connection']:
                    req.add_header(header, self.headers[header])

            with urllib.request.urlopen(req) as response:
                content = response.read()
                self.send_response(response.getcode())
                for header, value in response.info().items():
                    if header.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(header, value)
                self.end_headers()
                self.wfile.write(content)
                
        except Exception as e:
            self.send_error(502, f"Proxy error: {str(e)}")
    
    def serve_favicon(self):
        """Serve the favicon"""
        try:
            favicon_path = os.path.join(BASE_DIR, 'static', 'images', 'favicon-bot.ico')
            if os.path.exists(favicon_path):
                with open(favicon_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header("Content-type", "image/x-icon")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "Favicon not found")
        except Exception as e:
            self.send_error(500, f"Error serving favicon: {str(e)}")
    
    def serve_file_or_directory(self, path):
        """Serve files or directories directly"""
        clean_path = path.lstrip('/')
        if clean_path == '':
            clean_path = '.'
        
        file_path = os.path.join(BASE_DIR, clean_path)
        
        if not os.path.abspath(file_path).startswith(os.path.abspath(BASE_DIR)):
            self.send_error(403, "Forbidden")
            return
        
        if os.path.isdir(file_path):
            return self.list_directory(file_path)
        elif os.path.isfile(file_path):
            return self.serve_file(file_path)
        else:
            self.send_error(404, "File not found")
    
    def serve_enhanced_file_list(self, path):
        """Show enhanced file list page with system monitor link"""
        try:
            items = []
            dir_path = BASE_DIR + path
            for name in os.listdir(dir_path):
                fullname = os.path.join(dir_path, name)
                displayname = linkname = name

                if os.path.isdir(fullname):
                    displayname = name + "/"
                    linkname = name + "/"

                if os.path.isfile(fullname):
                    size = os.path.getsize(fullname)
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size/1024:.1f} KB"
                    else:
                        size_str = f"{size/(1024*1024):.1f} MB"
                else:
                    size_str = "-"

                mtime = os.path.getmtime(fullname)
                mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

                items.append({
                    'name': name,
                    'displayname': displayname,
                    'linkname': linkname,
                    'size': size_str,
                    'mtime': mtime_str,
                    'isdir': os.path.isdir(fullname)
                })

            items.sort(key=lambda x: (not x['isdir'], x['name'].lower()))

            # Check if user is logged in
            user_info = ''
            if AUTH_AVAILABLE and self.current_user:
                user_info = f'''
                <div style="margin-bottom: 20px; padding: 10px; background: #e8f5e9; border-radius: 5px;">
                    👤 Logged in as: <strong>{self.current_user.get('name', 'User')}</strong>
                    (<a href="/auth/logout" style="color: #c62828;">Logout</a>)
                </div>
                '''

            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>File List - {unquote(path)}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .path {{ color: #666; margin-bottom: 20px; }}
        .monitor-link {{ 
            background: #4CAF50; 
            color: white; 
            padding: 10px 15px; 
            text-decoration: none; 
            border-radius: 5px; 
            display: inline-block;
            margin-bottom: 20px;
        }}
        .webui-link {{
            background: #2196F3; 
            color: white; 
            padding: 10px 15px; 
            text-decoration: none; 
            border-radius: 5px; 
            display: inline-block;
            margin-bottom: 20px;
            margin-left: 10px;
        }}
        .gtd-link {{
            background: #FF9800; 
            color: white; 
            padding: 10px 15px; 
            text-decoration: none; 
            border-radius: 5px; 
            display: inline-block;
            margin-bottom: 20px;
            margin-left: 10px;
        }}
        .monitor-link:hover {{ background: #45a049; }}
        .webui-link:hover {{ background: #1976D2; }}
        .gtd-link:hover {{ background: #F57C00; }}
        .file-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .file-table th {{ background: #f5f5f5; padding: 12px; text-align: left; border-bottom: 2px solid #ddd; }}
        .file-table td {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .file-table tr:hover {{ background: #f9f9f9; }}
        .name {{ font-weight: bold; }}
        .dir {{ color: #0066cc; }}
        .file {{ color: #333; }}
        .size {{ color: #666; text-align: right; }}
        .mtime {{ color: #888; }}
        .parent-link {{ margin-bottom: 15px; display: inline-block; }}
        a {{ text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>📁 File List</h1>
    <div class="path">Path: {unquote(path)}</div>
    
    {user_info}
    
    <a href="/system-info" class="monitor-link">📊 System Monitor</a>
    <a href="http://bot.xjbcode.fun:18789" class="webui-link" target="_blank">🤖 Moltbot WebUI</a>
    <a href="/gtd" class="gtd-link">✅ GTD Task Management</a>

    {self._generate_parent_link(path)}

    <table class="file-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>Size</th>
                <th>Modified</th>
            </tr>
        </thead>
        <tbody>
            {self._generate_file_rows(items)}
        </tbody>
    </table>

    <footer style="margin-top: 30px; color: #999; font-size: 0.8em; border-top: 1px solid #eee; padding-top: 10px;">
        <p>Server running on port {self.server.server_address[1]} | {len(items)} items</p>
    </footer>
</body>
</html>"""

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))

        except Exception as e:
            self.send_error(404, f"Cannot list directory: {str(e)}")
    
    def list_directory(self, path):
        """List directory contents"""
        rel_path = os.path.relpath(path, BASE_DIR)
        if rel_path == '.':
            rel_path = ''
        
        return self.serve_enhanced_file_list('/' + rel_path)
    
    def serve_file(self, file_path):
        """Serve a single file"""
        try:
            if file_path.endswith('.md') or file_path.endswith('.markdown'):
                return self.serve_markdown_file(file_path)
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            content_type = self.guess_type(file_path)
            
            self.send_response(200)
            self.send_header("Content-type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            self.send_error(404, f"Cannot read file: {str(e)}")
    
    def serve_markdown_file(self, file_path):
        """Render Markdown file as HTML"""
        try:
            import markdown
            
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            html_content = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
            
            rel_path = os.path.relpath(file_path, BASE_DIR)
            parent_dir = os.path.dirname(rel_path)
            if parent_dir == '.':
                parent_dir = '/'
            else:
                parent_dir = '/' + parent_dir
            
            html_page = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{os.path.basename(file_path)}</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            max-width: 1200px; 
            margin: 20px auto; 
            padding: 20px; 
            line-height: 1.6;
            color: #333;
        }}
        h1, h2, h3, h4, h5, h6 {{ 
            color: #2c3e50; 
            margin-top: 1.5em; 
            margin-bottom: 0.8em;
        }}
        h1 {{ border-bottom: 2px solid #eee; padding-bottom: 0.3em; }}
        h2 {{ border-bottom: 1px solid #eee; padding-bottom: 0.3em; }}
        p {{ margin: 1em 0; }}
        a {{ color: #3498db; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        code {{ 
            background: #f8f9fa; 
            padding: 2px 4px; 
            border-radius: 3px; 
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 0.9em;
        }}
        pre {{ 
            background: #f8f9fa; 
            padding: 16px; 
            border-radius: 6px; 
            overflow-x: auto;
            margin: 1em 0;
        }}
        pre code {{ 
            background: none; 
            padding: 0; 
            border-radius: 0;
            font-size: 0.95em;
        }}
        blockquote {{ 
            border-left: 4px solid #ddd; 
            padding-left: 16px; 
            margin: 1em 0; 
            color: #666;
        }}
        table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin: 1em 0;
        }}
        th, td {{ 
            border: 1px solid #ddd; 
            padding: 12px; 
            text-align: left;
        }}
        th {{ background: #f8f9fa; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        ul, ol {{ padding-left: 2em; margin: 1em 0; }}
        li {{ margin: 0.5em 0; }}
        .nav-link {{ 
            background: #6c757d; 
            color: white; 
            padding: 8px 12px; 
            text-decoration: none; 
            border-radius: 4px; 
            display: inline-block;
            margin-bottom: 20px;
        }}
        .nav-link:hover {{ background: #5a6268; }}
    </style>
</head>
<body>
    <a href="{parent_dir}" class="nav-link">🏠 Back to Parent</a>
    <div class="markdown-content">
        {html_content}
    </div>
</body>
</html>"""
            
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_page.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html_page.encode('utf-8'))
            
        except ImportError:
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(404, f"Cannot read Markdown file: {str(e)}")
    
    def guess_type(self, path):
        """Simple MIME type guessing"""
        if path.endswith('.html') or path.endswith('.htm'):
            return 'text/html'
        elif path.endswith('.css'):
            return 'text/css'
        elif path.endswith('.js'):
            return 'application/javascript'
        elif path.endswith('.json'):
            return 'application/json'
        elif path.endswith('.png'):
            return 'image/png'
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            return 'image/jpeg'
        elif path.endswith('.gif'):
            return 'image/gif'
        elif path.endswith('.ico'):
            return 'image/x-icon'
        elif path.endswith('.txt'):
            return 'text/plain'
        elif path.endswith('.md') or path.endswith('.markdown'):
            return 'text/markdown'
        else:
            return 'application/octet-stream'
    
    def _generate_parent_link(self, current_path):
        """Generate parent directory link"""
        if current_path != '/':
            parent_path = os.path.dirname(current_path.rstrip('/'))
            if parent_path == '':
                parent_path = '/'
            return f'<div class="parent-link"><a href="{parent_path}">⬆ Back to Parent</a></div>'
        return ''
    
    def _generate_file_rows(self, items):
        """Generate file rows HTML"""
        rows = []
        for item in items:
            icon = "📁" if item['isdir'] else "📄"
            css_class = "dir" if item['isdir'] else "file"
            rows.append(f"""
            <tr>
                <td class="name {css_class}">
                    {icon} <a href="{item['linkname']}">{item['displayname']}</a>
                </td>
                <td class="size">{item['size']}</td>
                <td class="mtime">{item['mtime']}</td>
            </tr>
            """)
        return '\n'.join(rows)
    
    def get_system_info(self):
        """Get system information"""
        info = {}
        
        mem = psutil.virtual_memory()
        info['memory'] = {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'free': mem.free,
            'percent': mem.percent
        }
        
        info['cpu'] = {
            'percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
            'per_core': psutil.cpu_percent(interval=1, percpu=True)
        }
        
        processes = []
        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                if proc.info['username'] in ['root', 'system', 'SYSTEM'] and proc.info['pid'] < 1000:
                    continue
                if proc.info['name'] in ['kthreadd', 'migration', 'rcu_gp', 'idle_inject']:
                    continue
                    
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        processes_by_cpu = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:20]
        processes_by_memory = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:20]
        
        info['processes_by_cpu'] = processes_by_cpu
        info['processes_by_memory'] = processes_by_memory
        
        net_io = psutil.net_io_counters()
        info['network'] = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errin': net_io.errin,
            'errout': net_io.errout,
            'dropin': net_io.dropin,
            'dropout': net_io.dropout
        }
        
        connections = psutil.net_connections()
        info['connections'] = len(connections)
        
        info['uptime'] = time.time() - psutil.boot_time()
        
        return info
    
    def format_bytes(self, bytes_value):
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def serve_system_info(self):
        """Serve the system information page"""
        try:
            info = self.get_system_info()
            
            mem_total = self.format_bytes(info['memory']['total'])
            mem_used = self.format_bytes(info['memory']['used'])
            mem_available = self.format_bytes(info['memory']['available'])
            
            net_sent = self.format_bytes(info['network']['bytes_sent'])
            net_recv = self.format_bytes(info['network']['bytes_recv'])
            
            uptime_seconds = int(info['uptime'])
            uptime_hours = uptime_seconds // 3600
            uptime_minutes = (uptime_seconds % 3600) // 60
            uptime_formatted = f"{uptime_hours}h {uptime_minutes}m"
            
            cpu_process_rows = []
            for proc in info['processes_by_cpu']:
                if proc['cpu_percent'] is not None and proc['memory_percent'] is not None:
                    cpu_process_rows.append(f"""
                    <tr>
                        <td>{proc['pid']}</td>
                        <td>{proc['ppid']}</td>
                        <td>{proc['name']}</td>
                        <td>{proc['username']}</td>
                        <td>{proc['cpu_percent']:.1f}%</td>
                        <td>{proc['memory_percent']:.1f}%</td>
                        <td>{proc['status']}</td>
                    </tr>
                    """)
            
            memory_process_rows = []
            for proc in info['processes_by_memory']:
                if proc['cpu_percent'] is not None and proc['memory_percent'] is not None:
                    memory_process_rows.append(f"""
                    <tr>
                        <td>{proc['pid']}</td>
                        <td>{proc['ppid']}</td>
                        <td>{proc['name']}</td>
                        <td>{proc['username']}</td>
                        <td>{proc['cpu_percent']:.1f}%</td>
                        <td>{proc['memory_percent']:.1f}%</td>
                        <td>{proc['status']}</td>
                    </tr>
                    """)
            
            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="5">
    <title>System Monitor</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 20px;
            background: #f5f5f5;
        }}
        h1, h2 {{ color: #333; }}
        .stats-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin: 20px 0;
        }}
        .stat-card {{ 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{ 
            margin: 0 0 10px 0; 
            color: #666; 
            font-size: 14px;
            text-transform: uppercase;
        }}
        .stat-value {{ 
            font-size: 24px; 
            font-weight: bold; 
            color: #333;
        }}
        .process-table {{ 
            width: 100%; 
            border-collapse: collapse; 
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        .process-table th {{ 
            background: #f8f9fa; 
            padding: 12px; 
            text-align: left;
            font-weight: 600;
            color: #555;
        }}
        .process-table td {{ 
            padding: 12px; 
            border-bottom: 1px solid #eee;
        }}
        .process-table tr:hover {{ 
            background: #f9f9f9;
        }}
        .nav-link {{ 
            background: #6c757d; 
            color: white; 
            padding: 10px 15px; 
            text-decoration: none; 
            border-radius: 5px; 
            display: inline-block;
            margin-bottom: 20px;
        }}
        .nav-link:hover {{ background: #5a6268; }}
        footer {{ 
            margin-top: 30px; 
            color: #999; 
            font-size: 0.8em; 
            border-top: 1px solid #eee; 
            padding-top: 10px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <a href="/" class="nav-link">🏠 Back to Home</a>
    <h1>📊 System Monitor</h1>
    
    <div class="stats-grid">
        <div class="stat-card">
            <h3>Memory Total</h3>
            <div class="stat-value">{mem_total}</div>
        </div>
        <div class="stat-card">
            <h3>Memory Used</h3>
            <div class="stat-value">{mem_used}</div>
        </div>
        <div class="stat-card">
            <h3>Memory Available</h3>
            <div class="stat-value">{mem_available}</div>
        </div>
        <div class="stat-card">
            <h3>CPU Usage</h3>
            <div class="stat-value">{info['cpu']['percent']:.1f}%</div>
        </div>
        <div class="stat-card">
            <h3>Network Sent</h3>
            <div class="stat-value">{net_sent}</div>
        </div>
        <div class="stat-card">
            <h3>Network Received</h3>
            <div class="stat-value">{net_recv}</div>
        </div>
        <div class="stat-card">
            <h3>Uptime</h3>
            <div class="stat-value">{uptime_formatted}</div>
        </div>
        <div class="stat-card">
            <h3>Connections</h3>
            <div class="stat-value">{info['connections']}</div>
        </div>
    </div>
    
    <h2>📈 Top CPU Processes</h2>
    <table class="process-table">
        <thead>
            <tr>
                <th>PID</th>
                <th>PPID</th>
                <th>Name</th>
                <th>User</th>
                <th>CPU%</th>
                <th>Memory%</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {''.join(cpu_process_rows) if cpu_process_rows else '<tr><td colspan="7">No process data</td></tr>'}
        </tbody>
    </table>
    
    <h2>📈 Top Memory Processes</h2>
    <table class="process-table">
        <thead>
            <tr>
                <th>PID</th>
                <th>PPID</th>
                <th>Name</th>
                <th>User</th>
                <th>CPU%</th>
                <th>Memory%</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {''.join(memory_process_rows) if memory_process_rows else '<tr><td colspan="7">No process data</td></tr>'}
        </tbody>
    </table>
    
    <footer>
        <p>Auto-refresh every 5 seconds | Server IP: 47.254.68.82</p>
    </footer>
</body>
</html>"""
            
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"System monitor error: {str(e)}")
    
    def serve_bot_reports_list(self):
        """Serve BotReports list as JSON"""
        try:
            bot_reports_dir = os.path.join(BASE_DIR, 'BotReports')
            reports = []
            
            for filename in os.listdir(bot_reports_dir):
                if filename.endswith('.html') and filename != 'index.html':
                    file_path = os.path.join(bot_reports_dir, filename)
                    if os.path.isfile(file_path):
                        mtime = os.path.getmtime(file_path)
                        reports.append({
                            'filename': filename,
                            'date': str(int(mtime))
                        })
            
            reports.sort(key=lambda x: int(x['date']), reverse=True)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(reports, indent=4).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error loading BotReports: {str(e)}")
    
    def serve_bot_reports_index(self):
        """Serve BotReports index.html"""
        try:
            index_path = os.path.join(os.path.dirname(__file__), 'botreports', 'index.html')
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content.encode('utf-8'))))
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.send_error(404, "BotReports index not found")
        except Exception as e:
            self.send_error(500, f"Error serving BotReports: {str(e)}")


def run_server(port=8000):
    """Run the HTTP server"""
    # Initialize authentication
    if AUTH_AVAILABLE:
        init_auth()
    
    server_address = ('', port)
    httpd = ThreadedHTTPServer(server_address, UnifiedHTTPRequestHandler)
    
    print(f"🦎 Molt Server starting on port {port}...")
    print(f"   📁 Base directory: {BASE_DIR}")
    print(f"   🔐 Authentication: {'Enabled' if AUTH_AVAILABLE else 'Disabled'}")
    print(f"   📊 System monitor: http://localhost:{port}/system-info")
    print(f"   ✅ GTD app: http://localhost:{port}/gtd")
    if AUTH_AVAILABLE:
        print(f"   🔑 Login: http://localhost:{port}/auth/login")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🦎 Molt Server shutting down...")
        httpd.shutdown()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
