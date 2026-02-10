#!/usr/bin/env python3
import os
import sys
import json
import psutil
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, urlparse, parse_qs
import subprocess
import threading
import socket
from socketserver import ThreadingMixIn
import requests
from bs4 import BeautifulSoup
import re

# 设置工作目录
BASE_DIR = '/var/www/html'
GTD_TASKS_FILE = os.path.join(BASE_DIR, 'gtd', 'tasks.md')
os.chdir(BASE_DIR)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads."""
    pass

class UnifiedHTTPRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # 系统信息页面
        if path == '/system-info':
            return self.serve_system_info()
        
        # GTD API endpoints
        elif path == '/api/gtd/tasks':
            return self.serve_gtd_tasks()
        elif path == '/api/gtd/title':
            return self.extract_title_api()
        
        # GTD app
        elif path == '/gtd' or path == '/gtd/':
            return self.serve_gtd_app()
        elif path.startswith('/gtd/'):
            return self.serve_gtd_static(path)
        
        # KodExplorer特殊处理 - proxy to Apache if needed
        elif path.startswith('/kodexplorer'):
            # Check if Apache is running on port 8080 (we'll move it there)
            if self.is_port_open('localhost', 8080):
                return self.proxy_to_apache(path)
            else:
                # If Apache isn't available, try to serve static files directly
                return self.serve_file_or_directory(path)
        
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
        else:
            self.send_error(404, "API endpoint not found")

    def do_PUT(self):
        """处理PUT请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # GTD API endpoints
        if path == '/api/gtd/tasks':
            return self.update_gtd_tasks()
        else:
            self.send_error(404, "API endpoint not found")

    def do_DELETE(self):
        """处理DELETE请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # GTD API endpoints
        if path == '/api/gtd/tasks':
            return self.clear_gtd_tasks()
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

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html.encode('utf-8'))))
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
        """获取系统信息"""
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
        
        # Process info (all non-system processes)
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
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"系统监控错误: {str(e)}")

    def serve_gtd_app(self):
        """Serve the GTD application"""
        try:
            gtd_index = os.path.join(BASE_DIR, 'gtd', 'index.html')
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
            self.send_error(500, f"Error serving GTD app: {str(e)}")

    def serve_gtd_static(self, path):
        """Serve static files from GTD directory"""
        try:
            # Clean up the path
            clean_path = path.lstrip('/')
            if clean_path == 'gtd/' or clean_path == 'gtd/index.html':
                return self.serve_gtd_app()
            
            file_path = os.path.join(BASE_DIR, clean_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return self.serve_file(file_path)
            else:
                return self.serve_gtd_app()
        except Exception as e:
            self.send_error(500, f"Error serving GTD static file: {str(e)}")

    def serve_gtd_tasks(self):
        """Serve the tasks.md file content"""
        try:
            with open(GTD_TASKS_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if client wants JSON
            accept_header = self.headers.get('Accept', '')
            if 'application/json' in accept_header:
                # Parse markdown to JSON
                tasks = self.parse_markdown_to_json(content)
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

    def parse_markdown_to_json(self, markdown):
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
            json_data = self.rfile.read(content_length).decode('utf-8')
            tasks = json.loads(json_data)
            
            # Generate markdown with comments
            markdown = self.generate_markdown_with_comments(tasks)
            
            with open(GTD_TASKS_FILE, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Tasks updated successfully"}).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error updating tasks: {str(e)}")

    def generate_markdown_with_comments(self, tasks):
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
            
            # Extract title using external script or direct fetch
            try:
                # Try to use the external script first
                result = subprocess.run([
                    sys.executable, 
                    '/home/admin/Code/web_server/gtd-title-extractor.py', 
                    url
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    title = result.stdout.strip()
                    response_data = {"title": title}
                else:
                    # Fallback to simple extraction
                    response_data = {"title": url}
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Fallback to simple extraction
                response_data = {"title": url}
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            response_json = json.dumps(response_data)
            self.send_header("Content-Length", str(len(response_json)))
            self.end_headers()
            self.wfile.write(response_json.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error extracting title: {str(e)}")

def run(port=8081):
    server_address = ('', port)
    httpd = ThreadedHTTPServer(server_address, UnifiedHTTPRequestHandler)
    print(f"Starting unified web server with comments support on port {port}...")
    print(f"Serving directory: {BASE_DIR}")
    print(f"GTD app available at: http://bot.xjbcode.fun:{port}/gtd")
    print(f"System monitor available at: http://bot.xjbcode.fun:{port}/system-info")
    print(f"KodExplorer should be accessible at: http://bot.xjbcode.fun:{port}/kodexplorer/")
    print(f"Moltbot WebUI available at: http://bot.xjbcode.fun:18789")
    httpd.serve_forever()

if __name__ == '__main__':
    import sys
    port = 8081
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}, using default port 80")
    run(port)