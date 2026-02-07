# Web Server

一个简单而强大的 Python HTTP 服务器，用于文件浏览和静态文件服务。

## 功能特性

- 文件和目录浏览
- 文件大小和修改时间显示
- 安全的文件访问控制
- 支持自定义端口和根目录
- 优雅的 HTML 界面
- 支持文件上传功能
- 搜索功能
- 响应式设计

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
# 默认端口 80，根目录 /var/www/html
python3 web-server-improved.py

# 指定端口
python3 web-server-improved.py 8080

# 通过环境变量设置
export WEB_SERVER_BASE_DIR=/path/to/directory
export WEB_SERVER_PORT=8080
python3 web-server-improved.py
```

## 配置

- `WEB_SERVER_BASE_DIR`: 设置根目录，默认为 `/var/www/html`
- `WEB_SERVER_PORT`: 设置端口号，默认为 `8080`

## 安全说明

此服务器具有基本的安全措施，但不应在生产环境中直接暴露于公网。
仅允许访问指定目录内的文件，防止路径遍历攻击。