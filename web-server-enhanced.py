#!/usr/bin/env python3
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote

# 设置工作目录
BASE_DIR = '/var/www/html'
os.chdir(BASE_DIR)

class EnhancedHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def do_GET(self):
        """重写GET方法，根目录也显示文件列表"""
        # 如果是根路径，强制显示目录列表而不是index.html
        if self.path == '/' or self.path == '/index.html':
            self.path = '/'
            return self.list_directory(BASE_DIR)
        return super().do_GET()

    def list_directory(self, path):
        """重写目录列表方法，显示更好的文件列表"""
        try:
            # 获取目录下的所有文件和文件夹
            items = []
            for name in os.listdir(path):
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
                    else:
                        size_str = f"{size/(1024*1024):.1f} MB"
                else:
                    size_str = "-"

                # 获取修改时间
                mtime = os.path.getmtime(fullname)
                from datetime import datetime
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
    <title>文件列表 - {unquote(self.path)}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 20px auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .path {{ color: #666; margin-bottom: 20px; }}
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
    <div class="path">路径: {unquote(self.path)}</div>

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

    def _generate_parent_link(self, current_path):
        """生成返回上级目录的链接"""
        if current_path != BASE_DIR:
            relative_path = os.path.relpath(current_path, BASE_DIR)
            parent_path = os.path.dirname(relative_path)
            if parent_path == '.':
                parent_path = ''
            return f'<div class="parent-link"><a href="/{parent_path}">⬆ 返回上级目录</a></div>'
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

def run(port=80):
    server_address = ('', port)
    httpd = HTTPServer(server_address, EnhancedHTTPRequestHandler)
    print(f"Starting enhanced web server on port {port}...")
    print(f"Serving directory: {BASE_DIR}")
    httpd.serve_forever()

if __name__ == '__main__':
    import sys
    port = 80
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}, using default port 80")
    run(port)