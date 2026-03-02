#!/usr/bin/env python3

import os
import sys
import json
import psutil
import time
import hashlib
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, urlparse, parse_qs
import subprocess
import threading
import socket
from socketserver import ThreadingMixIn
import requests
# BeautifulSoup 是可选的，用于 URL 标题提取
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

# Import configuration
from config import (
    APP_DIR, WEB_ROOT, LOG_DIR, SERVER_PORT, SERVER_HOST,
    GTD_DATA_DIR, GTD_TASKS_FILE, BOTREPORTS_DIR,
    AUTH_DB_PATH, OAUTH_CONFIG_FILE, LOG_LEVEL
)

# Import caching module
from cache import TTLCache

STATIC_DIR = os.path.join(WEB_ROOT, 'static')
BASE_DIR = WEB_ROOT  # For backward compatibility

# Initialize cache instances for system metrics
# System metrics (CPU, memory, disk) - 5 second TTL
system_metrics_cache = TTLCache(ttl_seconds=5)
# Process list - 10 second TTL (changes less frequently)
process_list_cache = TTLCache(ttl_seconds=10)

# 导入 GTD 模块
from gtd import GTDHandler

# Import logging
from logging_config import setup_logging
logger = setup_logging()

# Import WebSocket handler
from websocket_handler import ws_server

# Import task scheduler
from scheduler import TaskScheduler, scheduler

# 导入认证模块
try:
    from auth import AuthHandler, SESSION_COOKIE_NAME, get_user_data_path, get_user_gtd_path
    from server_auth_integration import serve_current_user, patch_gtd_for_auth
    AUTH_ENABLED = True
    # Patch GTD for multi-user support
    patch_gtd_for_auth()
    logger.info("Authentication module loaded successfully")
except ImportError as e:
    AUTH_ENABLED = False
    logger.error(f"Auth module not available, running without authentication: {e}")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads."""
    pass

class UnifiedHTTPRequestHandler(GTDHandler, AuthHandler if AUTH_ENABLED else object, BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()
    
    def get_current_user(self):
        """Get current authenticated user if auth is enabled."""
        if not AUTH_ENABLED:
            return None
        return self.get_session_from_request()
    
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

    def send_error(self, code, message=None, explain=None):
        """Override to ensure UTF-8 encoding for error messages."""
        try:
            # Use default error message if not provided
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
            
            # Ensure message and explain are strings
            msg = f"{code} {message}"
            if explain:
                msg += f": {explain}"
            
            # Log the error
            self.log_error("code %d, message %s", code, message)
            
            # Send response
            self.send_response(code)
            self.send_header('Connection', 'close')
            
            # HTML error page with UTF-8 encoding
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
            # If something goes wrong, fall back to parent implementation
            super().send_error(code, message, explain)

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Favicon 请求
        if path == '/favicon.ico':
            return self.serve_favicon()
        
        # 系统信息页面
        if path == '/system-info':
            return self.serve_system_info()
        
        # Cache statistics endpoint
        if path == '/system-info/cache-stats':
            return self.serve_cache_stats()
        
        # BotReports endpoints
        elif path == '/api/bot-reports':
            return self.serve_bot_reports_list()
        elif path == '/BotReports' or path == '/BotReports/':
            return self.serve_bot_reports_index()
        
        # API Documentation (Swagger UI)
        elif path == '/api-docs' or path == '/api-docs/':
            return self.serve_api_docs_index()
        elif path == '/api-docs/openapi.yaml':
            return self.serve_openapi_spec()
        
        # GTD API endpoints (auth required if enabled)
        elif path == '/api/gtd/tasks':
            if AUTH_ENABLED:
                session = self.get_session_from_request()
                if not session:
                    self.send_response(302)
                    self.send_header('Location', '/login')
                    self.end_headers()
                    return
            return self.serve_gtd_tasks()
        elif path == '/api/gtd/title':
            return self.extract_title_api()
        
        # GTD Schedule API endpoints
        elif path == '/api/gtd/schedule':
            if AUTH_ENABLED:
                session = self.get_session_from_request()
                if not session:
                    self.send_response(302)
                    self.send_header('Location', '/login')
                    self.end_headers()
                    return
            return self.serve_gtd_schedules()
        
        # GTD app
        elif path == '/gtd' or path == '/gtd/':
            return self.serve_gtd_app()
        elif path.startswith('/gtd/'):
            return self.serve_gtd_static(path)
        
        # KodExplorer - served directly by Apache (see molt-server.conf)
        # 根路径 - 显示增强的文件列表
        elif path == '/' or path == '/index.html':
            return self.serve_enhanced_file_list('/')
        
        # 其他文件/目录
        else:
            return self.serve_file_or_directory(path)

    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # GTD API endpoints
        if path == '/api/gtd/tasks':
            return self.add_gtd_task()
        elif path == '/api/gtd/schedule':
            return self.add_gtd_schedule()
        else:
            self.send_error(404, "API endpoint not found")

    def do_PUT(self):
        """处理PUT请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # GTD API endpoints
        if path == '/api/gtd/tasks':
            return self.update_gtd_tasks()
        elif path == '/api/gtd/schedule':
            return self.update_gtd_schedule()
        else:
            self.send_error(404, "API endpoint not found")

    def do_DELETE(self):
        """处理DELETE请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # GTD API endpoints
        if path == '/api/gtd/tasks':
            return self.clear_gtd_tasks()
        elif path == '/api/gtd/schedule':
            return self.delete_gtd_schedule()
        else:
            self.send_error(404, "API endpoint not found")

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
            
            # Reconstruct the full URL for Apache
            apache_url = f"http://localhost:8080{path}"
            if self.path.find('?') != -1:
                apache_url += self.path[self.path.find('?'):]
            
            # Forward the request headers
            req = urllib.request.Request(apache_url)
            for header in self.headers:
                if header.lower() not in ['host', 'connection']:
                    req.add_header(header, self.headers[header])
            
            # Get the response from Apache
            with urllib.request.urlopen(req) as response:
                content = response.read()
                self.send_response(response.getcode())
                for header, value in response.info().items():
                    if header.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(header, value)
                self.end_headers()
                self.wfile.write(content)
                
        except Exception as e:
            # Fallback to direct file serving if proxy fails
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
                self.send_header("Cache-Control", "public, max-age=86400")  # 缓存24小时
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "Favicon not found")
        except Exception as e:
            self.send_error(500, f"Error serving favicon: {str(e)}")

    def serve_file_or_directory(self, path):
        """Serve files or directories directly"""
        # Clean up the path
        clean_path = path.lstrip('/')
        if clean_path == '':
            clean_path = '.'
        
        # Resolve the actual file path
        file_path = os.path.join(BASE_DIR, clean_path)
        
        # Security check - prevent directory traversal
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
        """显示增强的文件列表页面，包含系统监控链接"""
        try:
            items = []
            dir_path = BASE_DIR + path
            for name in os.listdir(dir_path):
                fullname = os.path.join(dir_path, name)
                displayname = linkname = name

                # 如果是目录，添加斜杠
                if os.path.isdir(fullname):
                    displayname = name + "/"
                    linkname = name + "/"

                # 获取文件大小
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

                # 获取修改时间
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

            # 按目录优先排序
            items.sort(key=lambda x: (not x['isdir'], x['name'].lower()))

            # 生成HTML
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>文件列表 - {unquote(path)}</title>
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
    <h1>📁 文件列表</h1>
    <div class="path">路径: {unquote(path)}</div>
    
    <!-- System Monitor Link -->
    <a href="/system-info" class="monitor-link">📊 实时系统监控</a>
    <!-- Moltbot WebUI Link -->
    <a href="http://bot.xjbcode.fun:18789" class="webui-link" target="_blank">🤖 Moltbot WebUI</a>
    <!-- GTD Link -->
    <a href="/gtd" class="gtd-link">✅ GTD 任务管理</a>

    {self._generate_parent_link(path)}

    <table class="file-table">
        <thead>
            <tr>
                <th>名称</th>
                <th>大小</th>
                <th>修改时间</th>
            </tr>
        </thead>
        <tbody>
            {self._generate_file_rows(items)}
        </tbody>
    </table>

    <footer style="margin-top: 30px; color: #999; font-size: 0.8em; border-top: 1px solid #eee; padding-top: 10px;">
        <p>服务器运行在端口 {self.server.server_address[1]} | 共 {len(items)} 个项目</p>
    </footer>
</body>
</html>"""

            # Generate ETag based on content hash
            etag = f'"{hashlib.md5(html.encode()).hexdigest()}"'
            
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html.encode('utf-8'))))
            self.send_header('Cache-Control', 'public, max-age=5')
            self.send_header('ETag', etag)
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))

        except Exception as e:
            self.send_error(404, f"无法列出目录: {str(e)}")

    def list_directory(self, path):
        """列出目录内容"""
        rel_path = os.path.relpath(path, BASE_DIR)
        if rel_path == '.':
            rel_path = ''
        return self.serve_enhanced_file_list('/' + rel_path)

    def serve_file(self, file_path):
        """Serve a single file"""
        try:
            # Check if it's a Markdown file - render as HTML instead of downloading
            if file_path.endswith('.md') or file_path.endswith('.markdown'):
                return self.serve_markdown_file(file_path)
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determine content type
            content_type = self.guess_type(file_path)
            
            self.send_response(200)
            self.send_header("Content-type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            self.send_error(404, f"无法读取文件: {str(e)}")

    def serve_markdown_file(self, file_path):
        """Render Markdown file as HTML"""
        try:
            import markdown
            
            # Read the markdown file
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Convert to HTML
            html_content = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
            
            # Get relative path for navigation
            rel_path = os.path.relpath(file_path, BASE_DIR)
            parent_dir = os.path.dirname(rel_path)
            if parent_dir == '.':
                parent_dir = '/'
            else:
                parent_dir = '/' + parent_dir
            
            # Create HTML page with styling
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
    <a href="{parent_dir}" class="nav-link">🏠 返回上级目录</a>
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
            # Fallback to plain text if markdown module not available
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(404, f"无法读取Markdown文件: {str(e)}")

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
        """生成返回上级目录的链接"""
        if current_path != '/':
            parent_path = os.path.dirname(current_path.rstrip('/'))
            if parent_path == '':
                parent_path = '/'
            return f'<div class="parent-link"><a href="{parent_path}">⬆ 返回上级目录</a></div>'
        return ''

    def _generate_file_rows(self, items):
        """生成文件行的HTML"""
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
        """获取系统信息 (with TTL caching)"""
        # Try to get cached system metrics (5 second TTL)
        cached_info = system_metrics_cache.get('system_metrics')
        if cached_info is not None:
            return cached_info
        
        info = {}
        
        # Memory info
        mem = psutil.virtual_memory()
        info['memory'] = {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'free': mem.free,
            'percent': mem.percent
        }
        
        # CPU info
        info['cpu'] = {
            'percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
            'per_core': psutil.cpu_percent(interval=1, percpu=True)
        }
        
        # Process info (all non-system processes) - cached separately with 10s TTL
        cached_processes = process_list_cache.get('process_list')
        if cached_processes is not None:
            info['processes_by_cpu'] = cached_processes['by_cpu']
            info['processes_by_memory'] = cached_processes['by_memory']
        else:
            # Fetch process list (expensive operation)
            processes = []
            for proc in psutil.process_iter(['pid', 'ppid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    # Skip system/kernel processes
                    if proc.info['username'] in ['root', 'system', 'SYSTEM'] and proc.info['pid'] < 1000:
                        continue
                    if proc.info['name'] in ['kthreadd', 'migration', 'rcu_gp', 'idle_inject']:
                        continue
                        
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage (top 20)
            processes_by_cpu = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:20]
            # Sort by memory usage (top 20)
            processes_by_memory = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:20]
            
            info['processes_by_cpu'] = processes_by_cpu
            info['processes_by_memory'] = processes_by_memory
            
            # Cache the process list
            process_list_cache.set('process_list', {
                'by_cpu': processes_by_cpu,
                'by_memory': processes_by_memory
            })
        
        # Network info
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
        
        # Connections
        connections = psutil.net_connections()
        info['connections'] = len(connections)
        
        # Uptime
        info['uptime'] = time.time() - psutil.boot_time()
        
        # Cache the system metrics
        system_metrics_cache.set('system_metrics', info)
        
        return info

    def format_bytes(self, bytes_value):
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"

    def serve_system_info(self):
        """Serve the system information page with cache headers"""
        try:
            info = self.get_system_info()
            
            # Generate ETag based on cache timestamp
            cache_stats = system_metrics_cache.get_stats()
            etag = f'"{hashlib.md5(str(cache_stats["cached_entries"]).encode()).hexdigest()}"'
            
            # Check for conditional request (If-None-Match)
            if_none_match = self.headers.get('If-None-Match')
            if if_none_match and if_none_match == etag:
                self.send_response(304)  # Not Modified
                self.send_header('Cache-Control', 'public, max-age=5')
                self.send_header('ETag', etag)
                self.end_headers()
                return
            
            # Format memory
            mem_total = self.format_bytes(info['memory']['total'])
            mem_used = self.format_bytes(info['memory']['used'])
            mem_available = self.format_bytes(info['memory']['available'])
            
            # Format network
            net_sent = self.format_bytes(info['network']['bytes_sent'])
            net_recv = self.format_bytes(info['network']['bytes_recv'])
            
            # Format uptime
            uptime_seconds = int(info['uptime'])
            uptime_hours = uptime_seconds // 3600
            uptime_minutes = (uptime_seconds % 3600) // 60
            uptime_formatted = f"{uptime_hours}h {uptime_minutes}m"
            
            # Generate CPU-sorted process table
            cpu_process_rows = []
            for proc in info['processes_by_cpu']:
                if proc['cpu_percent'] is not None and proc['memory_percent'] is not None:
                    cpu_process_rows.append(f"""
                    <tr>
                        <td>{proc['pid']}</td>
                        <td>{proc['ppid']}</td>
                        <td>{proc['name']}</td>
                        <td>{proc['username'] or 'N/A'}</td>
                        <td>{proc['cpu_percent']:.1f}%</td>
                        <td>{proc['memory_percent']:.1f}%</td>
                        <td>{proc['status'] or 'N/A'}</td>
                    </tr>
                    """)
            
            # Generate memory-sorted process table
            memory_process_rows = []
            for proc in info['processes_by_memory']:
                if proc['cpu_percent'] is not None and proc['memory_percent'] is not None:
                    memory_process_rows.append(f"""
                    <tr>
                        <td>{proc['pid']}</td>
                        <td>{proc['ppid']}</td>
                        <td>{proc['name']}</td>
                        <td>{proc['username'] or 'N/A'}</td>
                        <td>{proc['cpu_percent']:.1f}%</td>
                        <td>{proc['memory_percent']:.1f}%</td>
                        <td>{proc['status'] or 'N/A'}</td>
                    </tr>
                    """)
            
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>📊 实时系统监控</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; margin-bottom: 15px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f9f9f9; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50; }}
        .stat-card h3 {{ margin: 0 0 10px 0; color: #333; }}
        .stat-value {{ font-size: 1.2em; font-weight: bold; color: #333; }}
        .progress-bar {{ height: 10px; background: #e0e0e0; border-radius: 5px; margin: 5px 0; }}
        .progress-fill {{ height: 100%; background: #4CAF50; border-radius: 5px; }}
        .process-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .process-table th {{ background: #f5f5f5; padding: 12px; text-align: left; border-bottom: 2px solid #ddd; }}
        .process-table td {{ padding: 8px; border-bottom: 1px solid #eee; }}
        .process-table tr:hover {{ background: #f9f9f9; }}
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
        .gtd-link:hover {{ background: #F57C00; }}
    </style>
</head>
<body>
    <h1>📊 实时系统监控</h1>
    <a href="/" class="nav-link">🏠 返回文件列表</a>
    <a href="/gtd" class="gtd-link">✅ GTD 任务管理</a>
    
    <div class="stats-grid">
        <!-- Memory Stats -->
        <div class="stat-card">
            <h3>💾 内存使用</h3>
            <div class="stat-value">已用: {mem_used} / {mem_total} ({info['memory']['percent']:.1f}%)</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {info['memory']['percent']}%"></div>
            </div>
            <div>可用: {mem_available}</div>
        </div>
        
        <!-- CPU Stats -->
        <div class="stat-card">
            <h3>⚙️ CPU 使用</h3>
            <div class="stat-value">总体: {info['cpu']['percent']:.1f}%</div>
            <div>核心数: {info['cpu']['count']}</div>
            <div>每核: {', '.join([f'{x:.1f}%' for x in info['cpu']['per_core'][:4]])}</div>
        </div>
        
        <!-- Network Stats -->
        <div class="stat-card">
            <h3>🌐 网络统计</h3>
            <div>已发送: {net_sent}</div>
            <div>已接收: {net_recv}</div>
            <div>连接数: {info['connections']}</div>
        </div>
        
        <!-- System Info -->
        <div class="stat-card">
            <h3>🖥️ 系统信息</h3>
            <div>运行时间: {uptime_formatted}</div>
            <div>进程数: {len(info['processes_by_cpu'])}</div>
            <div>Python版本: {sys.version.split()[0]}</div>
        </div>
    </div>
    
    <!-- Top Processes by CPU -->
    <h2>📈 高CPU进程 (Top 20)</h2>
    <table class="process-table">
        <thead>
            <tr>
                <th>PID</th>
                <th>PPID</th>
                <th>进程名</th>
                <th>用户</th>
                <th>CPU%</th>
                <th>内存%</th>
                <th>状态</th>
            </tr>
        </thead>
        <tbody>
            {''.join(cpu_process_rows) if cpu_process_rows else '<tr><td colspan="7">暂无进程数据</td></tr>'}
        </tbody>
    </table>
    
    <!-- Top Processes by Memory -->
    <h2>📈 高内存进程 (Top 20)</h2>
    <table class="process-table">
        <thead>
            <tr>
                <th>PID</th>
                <th>PPID</th>
                <th>进程名</th>
                <th>用户</th>
                <th>CPU%</th>
                <th>内存%</th>
                <th>状态</th>
            </tr>
        </thead>
        <tbody>
            {''.join(memory_process_rows) if memory_process_rows else '<tr><td colspan="7">暂无进程数据</td></tr>'}
        </tbody>
    </table>
    
    <footer style="margin-top: 30px; color: #999; font-size: 0.8em; border-top: 1px solid #eee; padding-top: 10px;">
        <p>数据自动刷新每5秒 | 服务器IP: 47.254.68.82</p>
    </footer>
</body>
</html>"""
            
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html.encode('utf-8'))))
            self.send_header('Cache-Control', 'public, max-age=5')
            self.send_header('ETag', etag)
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"系统监控错误: {str(e)}")

    def serve_cache_stats(self):
        """Serve cache statistics as JSON"""
        try:
            stats = {
                'system_metrics': system_metrics_cache.get_stats(),
                'process_list': process_list_cache.get_stats()
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(stats, indent=2).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Cache stats error: {str(e)}")

    def handle_websocket_upgrade(self):
        """Handle WebSocket upgrade request"""
        # Note: The built-in HTTP server doesn't support WebSocket protocol upgrade
        # This endpoint informs clients that WebSocket is available on port 8765
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {
            'status': 'WebSocket server running',
            'ws_url': f'ws://localhost:8765',
            'message': 'Connect to the WebSocket URL for real-time updates'
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def serve_bot_reports_list(self):
        """Serve BotReports list as JSON"""
        try:
            bot_reports_dir = os.path.join(BASE_DIR, 'BotReports')
            reports = []
            
            # Scan directory for HTML files (excluding index.html)
            for filename in os.listdir(bot_reports_dir):
                if filename.endswith('.html') and filename != 'index.html':
                    file_path = os.path.join(bot_reports_dir, filename)
                    if os.path.isfile(file_path):
                        mtime = os.path.getmtime(file_path)
                        reports.append({
                            'filename': filename,
                            'date': str(int(mtime))
                        })
            
            # Sort by date (newest first)
            reports.sort(key=lambda x: int(x['date']), reverse=True)
            
            # Send JSON response
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
            # Serve from molt_server project directory
            index_path = os.path.join(os.path.dirname(__file__), 'botreports', 'index.html')
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.send_error(404, "BotReports index.html not found")
        except Exception as e:
            self.send_error(500, f"Error serving BotReports: {str(e)}")

    def serve_api_docs_index(self):
        """Serve Swagger UI for API documentation"""
        try:
            index_path = os.path.join(STATIC_DIR, 'api-docs', 'index.html')
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'public, max-age=3600')  # Cache for 1 hour
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.send_error(404, "API documentation not found")
        except Exception as e:
            self.send_error(500, f"Error serving API docs: {str(e)}")

    def serve_openapi_spec(self):
        """Serve OpenAPI specification (YAML)"""
        try:
            spec_path = os.path.join(os.path.dirname(__file__), 'docs', 'openapi.yaml')
            if os.path.exists(spec_path):
                with open(spec_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/yaml; charset=utf-8')
                self.send_header('Cache-Control', 'public, max-age=3600')  # Cache for 1 hour
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.send_error(404, "OpenAPI specification not found")
        except Exception as e:
            self.send_error(500, f"Error serving OpenAPI spec: {str(e)}")


def run(port=None, reloader=False):
    """运行服务器
    
    Args:
        port: 端口号 (defaults to SERVER_PORT from config)
        reloader: 是否启用热重载
    """
    if port is None:
        port = SERVER_PORT
    
    # Start WebSocket server in background thread
    ws_server.start_thread()
    logger.info(f"WebSocket server started on ws://localhost:8765")
    
    # Initialize and start task scheduler
    from gtd_db import init_database
    init_database()
    global scheduler
    scheduler = TaskScheduler(None)  # DB is accessed via connection pool
    scheduler.start()
    logger.info(f"Task scheduler started")
    
    server_address = (SERVER_HOST, port)
    httpd = ThreadedHTTPServer(server_address, UnifiedHTTPRequestHandler)
    logger.info(f"Starting unified web server with comments support on port {port}...")
    logger.info(f"Serving directory: {BASE_DIR}")
    logger.info(f"GTD app available at: http://bot.xjbcode.fun:{port}/gtd")
    logger.info(f"System monitor available at: http://bot.xjbcode.fun:{port}/system-info")
    logger.info(f"KodExplorer should be accessible at: http://bot.xjbcode.fun:{port}/kodexplorer/")
    logger.info(f"Moltbot WebUI available at: http://bot.xjbcode.fun:18789")
    httpd.serve_forever()

if __name__ == '__main__':
    import sys
    port = SERVER_PORT  # Use config default
    reloader = False
    
    # 解析命令行参数
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--reload':
            reloader = True
        else:
            try:
                port = int(args[i])
            except ValueError:
                logger.error(f"Invalid port number: {args[i]}, using default port {SERVER_PORT}")
        i += 1
    
    run(port, reloader)