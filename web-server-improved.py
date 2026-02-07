#!/usr/bin/env python3
import os
import sys
import mimetypes
import posixpath
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, urlparse, parse_qs
from datetime import datetime
import cgi
import shutil

# 设置工作目录 - 可以通过环境变量或命令行参数自定义
BASE_DIR = os.environ.get('WEB_SERVER_BASE_DIR', '/var/www/html')
PORT = int(os.environ.get('WEB_SERVER_PORT', '8080'))

class SecureHTTPRequestHandler(BaseHTTPRequestHandler):
    """增强的安全HTTP请求处理器"""
    
    def end_headers(self):
        # 添加安全相关的HTTP头
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def translate_path(self, path):
        """安全地转换URL路径为本地文件系统路径"""
        # 解析URL并获取查询参数
        parsed = urlparse(path)
        path = parsed.path
        
        # 确保路径以'/'开头
        trailing_slash = path.endswith('/')
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        
        # 解码URL编码的字符
        path = unquote(path)
        
        # 将Unix风格路径转换为当前系统的路径分隔符
        path = posixpath.normpath(path)
        words = path.split('/')
        words = [_f for _f in words if _f]
        
        # 构建绝对路径
        path = BASE_DIR
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        
        # 额外的安全检查：确保路径在BASE_DIR内
        if not path.startswith(BASE_DIR):
            return None  # 路径遍历攻击，返回None
        
        # 如果原始路径以/结尾或者这是一个目录，则添加索引文件
        if trailing_slash or os.path.isdir(path):
            for index in "index.html", "index.htm":
                index_path = os.path.join(path, index)
                if os.path.exists(index_path) and os.path.isfile(index_path):
                    path = index_path
                    break
        
        return path

    def do_GET(self):
        """处理GET请求"""
        # 解析查询参数
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)
        
        # 如果路径包含特定功能参数，处理特殊功能
        if 'search' in query_params:
            self.handle_search(query_params['search'][0])
        elif parsed.path == '/upload':
            self.show_upload_page()
        else:
            # 正常文件服务
            f = self.send_head()
            if f:
                try:
                    self.copyfile(f, self.wfile)
                finally:
                    f.close()

    def do_POST(self):
        """处理POST请求（主要用于文件上传）"""
        if self.path.startswith('/upload'):
            self.handle_file_upload()
        else:
            self.send_error(404, "Not Found")

    def send_head(self):
        """发送头部信息并返回文件对象"""
        path = self.translate_path(self.path)
        
        # 检查路径是否有效（防止路径遍历）
        if path is None:
            self.send_error(403, "Forbidden - Path traversal detected")
            return None
            
        # 检查路径是否存在
        if not os.path.exists(path):
            self.send_error(404, "File not found")
            return None

        # 如果是目录，显示目录列表
        if os.path.isdir(path):
            if self.path.endswith('/') or self.path.endswith('/index.html') or self.path.endswith('/index.htm'):
                return self.list_directory(path)
            else:
                # 目录没有尾随斜杠，重定向
                self.send_response(301)
                new_path = self.path + '/'
                if self.headers.get('Host'):
                    new_path = f"http://{self.headers.get('Host')}{new_path}"
                self.send_header("Location", new_path)
                self.end_headers()
                return None

        # 是文件，发送文件内容
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            self.send_response(200)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def list_directory(self, path):
        """列出目录内容"""
        try:
            # 获取目录项
            items = []
            for name in os.listdir(path):
                # 跳过隐藏文件（以.开头的文件）
                if name.startswith('.'):
                    continue
                    
                fullname = os.path.join(path, name)
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
                    elif size < 1024 * 1024 * 1024:
                        size_str = f"{size/(1024*1024):.1f} MB"
                    else:
                        size_str = f"{size/(1024*1024*1024):.1f} GB"
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
                    'isdir': os.path.isdir(fullname),
                    'ext': os.path.splitext(name)[1] if os.path.isfile(fullname) else ''
                })

            # 按目录优先排序
            items.sort(key=lambda x: (not x['isdir'], x['name'].lower()))

            # 计算相对路径用于生成正确的链接
            rel_path = os.path.relpath(path, BASE_DIR)
            if rel_path == '.':
                rel_path = ''
            
            # 生成HTML
            html = self.generate_directory_html(items, rel_path)

            # 发送响应
            encoded = html.encode('utf-8')
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return None

        except OSError:
            self.send_error(404, "No permission to list directory")
            return None

    def generate_directory_html(self, items, current_path):
        """生成目录列表HTML"""
        # 生成面包屑导航
        breadcrumb = self._generate_breadcrumb(current_path)
        
        # 生成父级链接
        parent_link = self._generate_parent_link(current_path)
        
        # 生成文件行
        file_rows = self._generate_file_rows(items)
        
        # 计算统计信息
        total_files = sum(1 for item in items if not item['isdir'])
        total_dirs = sum(1 for item in items if item['isdir'])
        total_items = len(items)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>文件浏览器 - {os.path.basename(BASE_DIR)}</title>
    <meta charset="utf-8">
    <style>
        :root {{
            --primary-color: #4a90e2;
            --secondary-color: #f5f5f5;
            --border-color: #ddd;
            --hover-bg: #f0f8ff;
            --text-color: #333;
            --header-bg: #f8f9fa;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #fff;
            color: var(--text-color);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        h1 {{
            margin: 0;
            color: var(--text-color);
            font-size: 1.8rem;
        }}
        
        .stats {{
            margin: 10px 0;
            color: #666;
            font-size: 0.9rem;
        }}
        
        .breadcrumb {{
            margin: 10px 0;
            padding: 8px 0;
            color: #666;
            font-size: 0.9rem;
        }}
        
        .breadcrumb a {{
            color: var(--primary-color);
            text-decoration: none;
        }}
        
        .breadcrumb a:hover {{
            text-decoration: underline;
        }}
        
        .controls {{
            margin: 15px 0;
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .search-box {{
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 0.9rem;
        }}
        
        .btn {{
            padding: 8px 16px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            text-decoration: none;
            display: inline-block;
        }}
        
        .btn:hover {{
            opacity: 0.9;
        }}
        
        .btn-upload {{
            background-color: #28a745;
        }}
        
        .file-table {{
            width: 100%;
            border-collapse: collapse;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .file-table th {{
            background-color: var(--header-bg);
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
            color: #555;
        }}
        
        .file-table td {{
            padding: 10px 15px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .file-table tr:last-child td {{
            border-bottom: none;
        }}
        
        .file-table tr:hover {{
            background-color: var(--hover-bg);
        }}
        
        .name-col {{
            width: 60%;
        }}
        
        .size-col {{
            width: 15%;
            text-align: right;
        }}
        
        .date-col {{
            width: 25%;
        }}
        
        .name a {{
            color: var(--text-color);
            text-decoration: none;
            font-weight: 500;
        }}
        
        .name a:hover {{
            text-decoration: underline;
        }}
        
        .icon {{
            margin-right: 8px;
        }}
        
        .dir {{
            color: #0066cc;
        }}
        
        .file {{
            color: var(--text-color);
        }}
        
        .size {{
            text-align: right;
            color: #666;
        }}
        
        .date {{
            color: #888;
        }}
        
        footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid var(--border-color);
            color: #999;
            font-size: 0.8rem;
            text-align: center;
        }}
        
        @media (max-width: 768px) {{
            .file-table {{
                font-size: 0.9rem;
            }}
            
            .file-table th, .file-table td {{
                padding: 8px;
            }}
            
            .controls {{
                flex-direction: column;
                align-items: stretch;
            }}
            
            .search-box {{
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📁 文件浏览器</h1>
            <div class="stats">共 {total_items} 个项目 ({total_dirs} 个文件夹, {total_files} 个文件)</div>
        </header>
        
        <div class="breadcrumb">
            {breadcrumb}
        </div>
        
        <div class="controls">
            <input type="text" class="search-box" id="searchInput" placeholder="搜索文件..." onkeypress="handleKeyPress(event)">
            <button class="btn" onclick="performSearch()">搜索</button>
            <a href="/upload" class="btn btn-upload">上传文件</a>
        </div>
        
        {parent_link}
        
        <table class="file-table">
            <thead>
                <tr>
                    <th class="name-col">名称</th>
                    <th class="size-col">大小</th>
                    <th class="date-col">修改时间</th>
                </tr>
            </thead>
            <tbody>
                {file_rows}
            </tbody>
        </table>

        <footer>
            <p>服务器运行在端口 {self.server.server_address[1]} | 基础目录: {BASE_DIR}</p>
        </footer>
    </div>
    
    <script>
        function handleKeyPress(event) {{
            if (event.key === 'Enter') {{
                performSearch();
            }}
        }}
        
        function performSearch() {{
            const query = document.getElementById('searchInput').value.trim();
            if (query) {{
                window.location.href = `/?search=\${encodeURIComponent(query)}`;
            }}
        }}
    </script>
</body>
</html>"""
        return html

    def _generate_breadcrumb(self, current_path):
        """生成面包屑导航"""
        if not current_path:
            return '<span>📁 /</span>'
        
        parts = current_path.strip('/').split('/')
        breadcrumb_parts = ['<a href="/">📁 /</a>']
        
        path_so_far = ''
        for i, part in enumerate(parts):
            if part:
                path_so_far += '/' + part
                if i == len(parts) - 1:
                    breadcrumb_parts.append(f'<span>{part}</span>')
                else:
                    breadcrumb_parts.append(f'<a href="{path_so_far}/">{part}</a>')
        
        return ' / '.join(breadcrumb_parts)

    def _generate_parent_link(self, current_path):
        """生成返回上级目录的链接"""
        if current_path:
            parent_path = os.path.dirname(current_path.rstrip('/'))
            if parent_path == '/':
                parent_path = ''
            return f'<div><a href="/{parent_path}/" class="btn" style="background-color: #6c757d;">⬆ 返回上级目录</a></div>'
        return ''

    def _generate_file_rows(self, items):
        """生成文件行的HTML"""
        rows = []
        for item in items:
            # 根据文件类型选择图标
            if item['isdir']:
                icon = "📁"
                css_class = "dir"
            else:
                ext = item['ext'].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                    icon = "🖼️"
                elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
                    icon = "🎬"
                elif ext in ['.mp3', '.wav', '.flac']:
                    icon = "🎵"
                elif ext in ['.pdf']:
                    icon = "📄"
                elif ext in ['.txt', '.md']:
                    icon = "📝"
                elif ext in ['.zip', '.rar', '.tar', '.gz']:
                    icon = "📦"
                else:
                    icon = "📄"
                css_class = "file"
                
            rows.append(f"""
            <tr>
                <td class="name name-col {css_class}">
                    <span class="icon">{icon}</span>
                    <a href="{item['linkname']}">{item['displayname']}</a>
                </td>
                <td class="size size-col">{item['size']}</td>
                <td class="date date-col">{item['mtime']}</td>
            </tr>
            """)
        return '\n'.join(rows)

    def show_upload_page(self):
        """显示文件上传页面"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>文件上传 - {os.path.basename(BASE_DIR)}</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .form-group {{
            margin-bottom: 20px;
        }}
        
        label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #555;
        }}
        
        input[type="file"] {{
            width: 100%;
            padding: 10px;
            border: 2px dashed #ddd;
            border-radius: 4px;
            background-color: #fafafa;
        }}
        
        .btn {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
            text-decoration: none;
        }}
        
        .btn:hover {{
            background-color: #218838;
        }}
        
        .btn-back {{
            background-color: #6c757d;
        }}
        
        .btn-back:hover {{
            background-color: #5a6268;
        }}
        
        .actions {{
            text-align: center;
            margin-top: 30px;
        }}
        
        .success {{
            color: #28a745;
            text-align: center;
            margin-top: 15px;
        }}
        
        .error {{
            color: #dc3545;
            text-align: center;
            margin-top: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📤 文件上传</h1>
        <form method="POST" enctype="multipart/form-data" action="/upload">
            <div class="form-group">
                <label for="file">选择要上传的文件:</label>
                <input type="file" name="file" id="file" required>
            </div>
            <div class="actions">
                <button type="submit" class="btn">上传文件</button>
                <a href="/" class="btn btn-back">返回首页</a>
            </div>
        </form>
    </div>
</body>
</html>"""
        
        encoded = html.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def handle_file_upload(self):
        """处理文件上传"""
        # 获取内容长度
        content_length = int(self.headers['Content-Length'])
        
        # 限制上传文件大小（例如100MB）
        if content_length > 100 * 1024 * 1024:
            self.send_error(413, "Request Entity Too Large - 文件过大")
            return
        
        # 解析表单数据
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type']}
        )
        
        # 获取上传的文件
        file_item = form['file'] if 'file' in form else None
        
        if file_item and file_item.filename:
            # 安全检查：确保文件名不包含危险字符
            filename = os.path.basename(file_item.filename)
            
            # 禁止上传可执行文件等潜在危险文件
            dangerous_exts = ['.exe', '.bat', '.sh', '.bin', '.cmd', '.com', '.scr', '.pif', '.lnk']
            _, ext = os.path.splitext(filename.lower())
            if ext in dangerous_exts:
                self.send_error(403, "Forbidden - 不允许上传此类型的文件")
                return
            
            # 确定保存路径（在当前目录下）
            current_dir = self.translate_path(self.path.replace('/upload', ''))
            if current_dir is None:
                self.send_error(403, "Forbidden - Path traversal detected")
                return
                
            save_path = os.path.join(current_dir, filename)
            
            # 写入文件
            try:
                with open(save_path, 'wb') as f:
                    shutil.copyfileobj(file_item.file, f)
                
                # 上传成功，重定向到目录页面
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return
            except Exception as e:
                self.send_error(500, f"Internal Server Error - 保存文件时出错: {str(e)}")
                return
        else:
            self.send_error(400, "Bad Request - 未选择文件")

    def handle_search(self, query):
        """处理搜索请求"""
        results = []
        
        # 在整个基础目录中递归搜索
        for root, dirs, files in os.walk(BASE_DIR):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for name in dirs + files:
                if query.lower() in name.lower():
                    full_path = os.path.join(root, name)
                    rel_path = os.path.relpath(full_path, BASE_DIR)
                    
                    # 获取文件信息
                    is_dir = os.path.isdir(full_path)
                    if os.path.isfile(full_path):
                        size = os.path.getsize(full_path)
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size/1024:.1f} KB"
                        elif size < 1024 * 1024 * 1024:
                            size_str = f"{size/(1024*1024):.1f} MB"
                        else:
                            size_str = f"{size/(1024*1024*1024):.1f} GB"
                    else:
                        size_str = "-"
                    
                    mtime = os.path.getmtime(full_path)
                    mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    
                    results.append({
                        'name': name,
                        'path': '/' + rel_path,
                        'size': size_str,
                        'mtime': mtime_str,
                        'isdir': is_dir
                    })
        
        # 生成搜索结果页面
        html = self.generate_search_results_html(query, results)
        
        encoded = html.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def generate_search_results_html(self, query, results):
        """生成搜索结果页面"""
        # 生成结果行
        result_rows = []
        for item in results:
            icon = "📁" if item['isdir'] else "📄"
            css_class = "dir" if item['isdir'] else "file"
            result_rows.append(f"""
            <tr>
                <td class="name name-col {css_class}">
                    <span class="icon">{icon}</span>
                    <a href="{item['path']}">{item['name']}</a>
                </td>
                <td class="size size-col">{item['size']}</td>
                <td class="date date-col">{item['mtime']}</td>
            </tr>
            """)
        
        results_html = '\n'.join(result_rows) if result_rows else "<tr><td colspan='3' style='text-align: center; color: #888;'>未找到匹配的结果</td></tr>"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>搜索结果 - {query} - {os.path.basename(BASE_DIR)}</title>
    <meta charset="utf-8">
    <style>
        :root {{
            --primary-color: #4a90e2;
            --secondary-color: #f5f5f5;
            --border-color: #ddd;
            --hover-bg: #f0f8ff;
            --text-color: #333;
            --header-bg: #f8f9fa;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #fff;
            color: var(--text-color);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        h1 {{
            margin: 0;
            color: var(--text-color);
            font-size: 1.8rem;
        }}
        
        .search-query {{
            margin: 10px 0;
            color: #666;
            font-size: 1rem;
        }}
        
        .result-count {{
            margin: 10px 0;
            color: #666;
            font-size: 0.9rem;
        }}
        
        .controls {{
            margin: 15px 0;
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        
        .search-box {{
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 0.9rem;
        }}
        
        .btn {{
            padding: 8px 16px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            text-decoration: none;
            display: inline-block;
        }}
        
        .btn:hover {{
            opacity: 0.9;
        }}
        
        .file-table {{
            width: 100%;
            border-collapse: collapse;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .file-table th {{
            background-color: var(--header-bg);
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
            color: #555;
        }}
        
        .file-table td {{
            padding: 10px 15px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .file-table tr:last-child td {{
            border-bottom: none;
        }}
        
        .file-table tr:hover {{
            background-color: var(--hover-bg);
        }}
        
        .name-col {{
            width: 60%;
        }}
        
        .size-col {{
            width: 15%;
            text-align: right;
        }}
        
        .date-col {{
            width: 25%;
        }}
        
        .name a {{
            color: var(--text-color);
            text-decoration: none;
            font-weight: 500;
        }}
        
        .name a:hover {{
            text-decoration: underline;
        }}
        
        .icon {{
            margin-right: 8px;
        }}
        
        .dir {{
            color: #0066cc;
        }}
        
        .file {{
            color: var(--text-color);
        }}
        
        .size {{
            text-align: right;
            color: #666;
        }}
        
        .date {{
            color: #888;
        }}
        
        footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid var(--border-color);
            color: #999;
            font-size: 0.8rem;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 搜索结果</h1>
            <div class="search-query">搜索关键词: <strong>{query}</strong></div>
            <div class="result-count">找到 {len(results)} 个结果</div>
        </header>
        
        <div class="controls">
            <input type="text" class="search-box" id="searchInput" placeholder="搜索文件..." value="{query}" onkeypress="handleKeyPress(event)">
            <button class="btn" onclick="performSearch()">搜索</button>
            <a href="/" class="btn" style="background-color: #6c757d;">返回首页</a>
        </div>
        
        <table class="file-table">
            <thead>
                <tr>
                    <th class="name-col">名称</th>
                    <th class="size-col">大小</th>
                    <th class="date-col">修改时间</th>
                </tr>
            </thead>
            <tbody>
                {results_html}
            </tbody>
        </table>

        <footer>
            <p>服务器运行在端口 {self.server.server_address[1]} | 基础目录: {BASE_DIR}</p>
        </footer>
    </div>
    
    <script>
        function handleKeyPress(event) {{
            if (event.key === 'Enter') {{
                performSearch();
            }}
        }}
        
        function performSearch() {{
            const query = document.getElementById('searchInput').value.trim();
            if (query) {{
                window.location.href = `/?search=\${encodeURIComponent(query)}`;
            }}
        }}
    </script>
</body>
</html>"""
        return html

    def guess_type(self, path):
        """猜测文件的MIME类型"""
        _, ext = os.path.splitext(path)
        if ext.lower() in ['.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.xml', '.html', '.htm', '.css', '.csv']:
            return 'text/plain'
        return mimetypes.guess_type(path)[0] or 'application/octet-stream'

    def copyfile(self, source, outputfile):
        """复制文件到输出"""
        shutil.copyfileobj(source, outputfile)


def run_server(port=8080, base_dir='/var/www/html'):
    """运行服务器"""
    global BASE_DIR
    BASE_DIR = base_dir
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, SecureHTTPRequestHandler)
    print(f"🚀 启动安全增强型Web服务器...")
    print(f"🌐 地址: http://localhost:{port}")
    print(f"📂 目录: {BASE_DIR}")
    print(f"🔐 特性: 安全路径验证、文件上传、搜索功能")
    print("按 Ctrl+C 停止服务器")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
        httpd.server_close()


if __name__ == '__main__':
    # 从命令行参数获取端口和基础目录
    port = PORT
    base_dir = BASE_DIR
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"⚠️ 无效的端口号: {sys.argv[1]}, 使用默认端口 {PORT}")
    
    if len(sys.argv) > 2:
        base_dir = sys.argv[2]
        if not os.path.isdir(base_dir):
            print(f"⚠️ 目录不存在: {base_dir}, 使用默认目录 {BASE_DIR}")
            base_dir = BASE_DIR
    
    run_server(port, base_dir)