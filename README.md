# Molt Server with GTD Task Management

一个功能丰富的 Python HTTP 服务器，包含文件浏览、静态文件服务和完整的 GTD（Getting Things Done）任务管理系统。

## 功能特性

### 🚀 核心功能
- **文件浏览器**：美观的目录列表，支持文件上传
- **静态文件服务**：高效服务 CSS、JS、图片等静态资源
- **GTD 任务管理**：完整的 Getting Things Done 系统
- **系统监控**：实时显示 CPU、内存、磁盘使用情况
- **热重载支持**：开发时自动重启（可选）

### 📋 GTD 系统
- 四个标准类别：Projects、Next Actions、Waiting For、Someday/Maybe
- 任务完成状态标记（复选框）
- 任务评论/注释系统
- 自动 URL 标题提取
- 现代化的 Web 界面

### 🔧 技术特性
- 多线程处理，支持并发请求
- 安全的文件访问控制，防止路径遍历
- 可配置的端口和根目录
- 环境变量配置支持
- 系统服务集成（systemd）

## 项目结构

```
molt-server/
├── src/                    # 源代码
│   ├── molt_server/        # 主服务器模块
│   │   ├── __init__.py
│   │   ├── server.py      # 主服务器逻辑
│   │   └── gtd.py         # GTD 模块
│   └── scripts/           # 可执行脚本
│       └── molt-server     # 启动脚本
├── static/                # 静态文件
│   ├── css/
│   ├── js/
│   ├── images/
│   └── gtd/
│       └── index.html     # GTD 前端界面
├── config/                # 配置文件示例
│   └── molt-server.conf.example
├── data/                  # 示例数据文件
│   └── gtd/
│       └── tasks.md.example
├── docs/                  # 文档
│   ├── DEPLOYMENT.md      # 部署指南
│   └── CODING_STANDARDS.md # 编程规范
├── scripts/               # 部署脚本
│   ├── install.sh        # 安装脚本
│   └── uninstall.sh      # 卸载脚本
├── tests/                 # 测试目录
├── requirements.txt       # Python 依赖
├── setup.py              # Python 包配置
└── .gitignore
```

## 快速开始

### 环境要求
- Python 3.7+
- Linux/macOS/Windows（推荐 Linux）

### 安装依赖
```bash
pip install -r requirements.txt
```

### 开发运行
```bash
# 使用默认端口 8081
python3 src/scripts/molt-server

# 指定端口
python3 src/scripts/molt-server 8080

# 启用热重载（开发）
python3 src/scripts/molt-server --reload 8080
```

### 作为 Python 包安装
```bash
# 开发安装
pip install -e .

# 然后可以直接运行
molt-server 8080
```

## 配置

### 环境变量
```bash
export WEB_SERVER_PORT=8080
export WEB_SERVER_BASE_DIR=/var/www/html
export WEB_SERVER_LOG_LEVEL=INFO
export GTD_DATA_DIR=/var/www/html/gtd
```

### 配置文件
复制示例配置文件并修改：
```bash
cp config/molt-server.conf.example /etc/molt-server/molt-server.conf
```

配置文件格式：
```ini
[server]
port = 8080
host = 0.0.0.0
base_dir = /var/www/html
log_level = INFO

[gtd]
data_dir = /var/www/html/gtd
tasks_file = /var/www/html/gtd/tasks.md

[paths]
static_dir = /opt/molt-server/share/static
log_dir = /var/log/molt-server
pid_file = /var/run/molt-server.pid
```

## 生产部署

### 使用安装脚本（推荐）
```bash
# 1. 克隆项目
git clone https://github.com/zhangfuwen/molt-server.git
cd molt-server

# 2. 运行安装脚本
chmod +x scripts/install.sh
sudo ./scripts/install.sh
```

### 手动部署
```bash
# 创建目录结构
sudo mkdir -p /opt/molt-server/{bin,lib,etc,var/log,share/static}
sudo mkdir -p /var/www/html/gtd /etc/molt-server /var/log/molt-server

# 复制文件
sudo cp -r src/molt_server/* /opt/molt-server/lib/
sudo cp -r static/* /opt/molt-server/share/static/
sudo cp config/molt-server.conf.example /etc/molt-server/molt-server.conf

# 创建启动脚本
sudo tee /opt/molt-server/bin/molt-server << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/molt-server/lib')
from molt_server.server import main
if __name__ == '__main__':
    main()
EOF
sudo chmod +x /opt/molt-server/bin/molt-server
sudo ln -sf /opt/molt-server/bin/molt-server /usr/local/bin/molt-server
```

### 系统服务管理
```bash
# 启动服务
sudo systemctl start molt-server

# 停止服务
sudo systemctl stop molt-server

# 查看状态
sudo systemctl status molt-server

# 查看日志
sudo journalctl -u molt-server -f

# 开机自启
sudo systemctl enable molt-server
```

## 访问服务

服务器启动后，可以通过以下地址访问：

1. **文件浏览器**：`http://localhost:8080/`
2. **GTD 任务管理**：`http://localhost:8080/gtd`
3. **系统监控**：`http://localhost:8080/system-info`
4. **API 文档**：`http://localhost:8080/api-docs/` 🆕
5. **Bot Reports**：`http://localhost:8080/BotReports`
6. **静态文件**：`http://localhost:8080/static/`

## API 接口

### 📖 Interactive API Documentation

Complete API documentation with interactive testing is available at:

**Swagger UI:** `http://localhost:8081/api-docs/`

The documentation includes:
- All API endpoints with request/response schemas
- Interactive testing directly from the browser
- Authentication requirements
- Example requests and responses
- Downloadable OpenAPI specification

### GTD API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/gtd/tasks` | Get all tasks organized by category |
| `POST` | `/api/gtd/tasks` | Create a new task |
| `PUT` | `/api/gtd/tasks` | Update tasks (bulk operation) |
| `DELETE` | `/api/gtd/tasks` | Clear all tasks |
| `GET` | `/api/gtd/title?url=<URL>` | Extract page title from URL |

### System Info API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/system-info` | System metrics dashboard (HTML) |
| `GET` | `/system-info/cache-stats` | Cache statistics (JSON) |

### BotReports API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/bot-reports` | List all bot reports |
| `GET` | `/api/bot-reports/{name}` | Get specific report |
| `GET` | `/BotReports` | BotReports index page |

### Authentication API (when enabled)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/login` | Login page with OAuth options |
| `POST` | `/auth/login` | OAuth callback handler |
| `POST` | `/auth/logout` | Logout and clear session |
| `GET` | `/api/user` | Get current user info |

### API Documentation Files

- **OpenAPI Spec:** `docs/openapi.yaml`
- **Swagger UI:** `static/api-docs/index.html`

## 开发指南

### 代码结构
- `src/molt_server/server.py` - 主服务器逻辑，处理 HTTP 请求
- `src/molt_server/gtd.py` - GTD 功能模块，包含任务解析和 API
- `static/gtd/index.html` - GTD 前端界面（纯 HTML/JS/CSS）

### 添加新功能
1. 在 `server.py` 中添加新的请求处理器
2. 如果需要新模块，在 `src/molt_server/` 下创建
3. 更新前端界面（如果需要）
4. 添加测试到 `tests/` 目录

### 运行测试
```bash
# 运行单元测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_server.py
```

## 故障排除

### 常见问题
1. **端口被占用**：换一个端口或停止占用进程
   ```bash
   sudo lsof -i :8080
   sudo kill <PID>
   ```

2. **权限问题**：
   ```bash
   sudo chown -R webserver:webserver /opt/molt-server /var/www/html /var/log/molt-server
   ```

3. **依赖缺失**：
   ```bash
   pip install requests beautifulsoup4 psutil
   ```

4. **服务启动失败**：
   ```bash
   sudo journalctl -u molt-server -n 50
   sudo -u webserver molt-server  # 手动测试
   ```

### 日志位置
- 系统日志：`journalctl -u molt-server`
- 应用日志：`/var/log/molt-server/`（如果配置）
- 错误日志：`journalctl -u molt-server -p err`

## 安全建议

1. **不要使用 root 运行**：安装脚本会创建专用用户 `webserver`
2. **配置防火墙**：只开放必要的端口
3. **使用反向代理**：生产环境建议使用 nginx/apache 作为反向代理
4. **启用 HTTPS**：通过反向代理配置 SSL/TLS
5. **定期更新**：保持依赖包最新

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

请遵循项目中的 [编程规范](docs/CODING_STANDARDS.md)。

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 支持

- 问题报告：[GitHub Issues](https://github.com/zhangfuwen/molt-server/issues)
- 文档：[docs/](docs/) 目录
- 部署指南：[DEPLOYMENT.md](docs/DEPLOYMENT.md)