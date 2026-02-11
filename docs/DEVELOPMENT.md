# 开发指南

本文档为 Web Server 项目的开发人员提供详细的开发环境设置、工作流程和开发工具指南。

## 目录

1. [开发环境设置](#开发环境设置)
2. [项目结构](#项目结构)
3. [开发工作流程](#开发工作流程)
4. [代码质量工具](#代码质量工具)
5. [测试指南](#测试指南)
6. [调试技巧](#调试技巧)
7. [性能优化](#性能优化)
8. [常见问题](#常见问题)

## 开发环境设置

### 1. 系统要求
- **Python**: 3.7 或更高版本
- **操作系统**: Linux (推荐 Ubuntu 20.04+), macOS, Windows (WSL2)
- **内存**: 至少 2GB RAM
- **磁盘空间**: 至少 500MB 可用空间

### 2. 克隆项目
```bash
git clone https://github.com/zhangfuwen/web-server.git
cd web-server
```

### 3. 创建虚拟环境
```bash
# 使用 venv
python3 -m venv .venv

# 激活虚拟环境
# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 4. 安装依赖
```bash
# 安装基础依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install pytest black flake8 mypy
```

### 5. 环境变量配置
创建 `.env` 文件（可选）：
```bash
cp config/web-server.conf.example .env
```

编辑 `.env` 文件，设置必要的环境变量：
```bash
# 服务器配置
WEB_SERVER_PORT=8081
WEB_SERVER_HOST=0.0.0.0
WEB_SERVER_BASE_DIR=/var/www/html

# GTD 配置
GTD_TASKS_FILE=/var/www/html/gtd/tasks.md
GTD_STATIC_DIR=static/gtd

# 开发模式
DEV_MODE=true
RELOADER=true
```

## 项目结构

```
web-server/
├── src/                    # 源代码目录
│   └── web_server/        # Python 包
│       ├── __init__.py    # 包初始化
│       ├── server.py      # 主服务器逻辑
│       └── gtd.py         # GTD 功能模块
├── static/                # 静态资源
│   ├── css/              # 样式表
│   ├── js/               # JavaScript
│   ├── images/           # 图片
│   └── gtd/              # GTD 前端
├── tests/                 # 测试代码
├── docs/                  # 文档
├── config/                # 配置文件
├── data/                  # 数据文件
├── scripts/               # 脚本文件
├── requirements.txt       # Python 依赖
├── setup.py              # 包配置
└── README.md             # 项目说明
```

## 开发工作流程

### 1. 启动开发服务器
```bash
# 使用开发模式（支持热重载）
python -m src.web_server.server --reloader

# 或直接运行
python src/web_server/server.py

# 指定端口
python src/web_server/server.py --port 8081
```

### 2. 代码修改流程
1. **创建功能分支**：
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **编写代码**：
   - 遵循 [编程规范](CODING_STANDARDS.md)
   - 添加适当的测试
   - 更新文档

3. **运行测试**：
   ```bash
   pytest
   ```

4. **代码检查**：
   ```bash
   # 代码格式化
   black src/ tests/
   
   # 代码检查
   flake8 src/ tests/
   
   # 类型检查（可选）
   mypy src/
   ```

5. **提交代码**：
   ```bash
   git add .
   git commit -m "feat(module): description of changes"
   ```

6. **推送分支**：
   ```bash
   git push origin feature/your-feature-name
   ```

### 3. 热重载开发
服务器支持热重载，修改代码后会自动重启：
```bash
python -m src.web_server.server --reloader
```

## 代码质量工具

### 1. 代码格式化
- **Black**: 自动格式化 Python 代码
  ```bash
  black src/ tests/
  ```

- **isort**: 自动排序导入语句
  ```bash
  isort src/ tests/
  ```

### 2. 代码检查
- **flake8**: 检查代码风格和潜在问题
  ```bash
  flake8 src/ tests/
  ```

- **pylint**: 更全面的代码分析
  ```bash
  pylint src/web_server/
  ```

### 3. 类型检查
- **mypy**: 静态类型检查
  ```bash
  mypy src/web_server/
  ```

### 4. 预提交钩子
配置 `.pre-commit-config.yaml`：
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3
        
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
        args: ["--profile", "black"]
        
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
        args: ["--max-line-length=88"]
```

安装预提交钩子：
```bash
pre-commit install
```

## 测试指南

### 1. 测试结构
```
tests/
├── __init__.py
├── conftest.py          # 测试配置
├── test_server.py       # 服务器测试
├── test_gtd.py          # GTD 功能测试
└── integration/         # 集成测试
    └── test_api.py
```

### 2. 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_server.py

# 运行特定测试类
pytest tests/test_gtd.py::TestGTDParser

# 运行特定测试方法
pytest tests/test_gtd.py::TestGTDParser::test_parse_simple_task

# 生成测试覆盖率报告
pytest --cov=src/web_server --cov-report=html
```

### 3. 编写测试
参考示例：
```python
import pytest
from src.web_server.gtd import parse_markdown_to_json

class TestGTDFunctionality:
    """GTD 功能测试"""
    
    def test_parse_markdown(self):
        """测试 Markdown 解析"""
        markdown = "# Projects\n- [ ] 完成文档"
        result = parse_markdown_to_json(markdown)
        
        assert 'projects' in result
        assert len(result['projects']) == 1
        assert result['projects'][0]['text'] == '完成文档'
    
    @pytest.mark.parametrize("input_text,expected", [
        ("- [ ] 任务1", False),
        ("- [x] 任务2", True),
    ])
    def test_task_completion(self, input_text, expected):
        """参数化测试任务完成状态"""
        markdown = f"# Projects\n{input_text}"
        result = parse_markdown_to_json(markdown)
        
        task = result['projects'][0]
        assert task['completed'] == expected
```

### 4. 集成测试
```python
import requests

def test_gtd_api():
    """测试 GTD API 端点"""
    # 启动测试服务器
    # ...
    
    # 测试 API
    response = requests.get('http://localhost:8081/gtd/tasks')
    assert response.status_code == 200
    assert 'application/json' in response.headers['Content-Type']
```

## 调试技巧

### 1. 日志调试
服务器内置了详细的日志系统：
```python
import logging

# 设置日志级别
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 在代码中添加日志
logger = logging.getLogger(__name__)
logger.debug(f"处理请求: {request.path}")
```

### 2. 调试模式启动
```bash
# 启用调试日志
python src/web_server/server.py --debug

# 或设置环境变量
export WEB_SERVER_DEBUG=true
python src/web_server/server.py
```

### 3. 使用 pdb 调试
```python
import pdb

def some_function():
    # 设置断点
    pdb.set_trace()
    
    # 代码执行会在这里暂停
    # 可以使用命令：
    # n - 下一行
    # c - 继续
    # p variable - 打印变量
    # q - 退出
```

### 4. 网络调试
```bash
# 使用 curl 测试 API
curl -X GET http://localhost:8081/gtd/tasks
curl -X POST http://localhost:8081/gtd/tasks -d '{"text":"新任务"}'

# 使用 httpie（更友好）
http GET localhost:8081/gtd/tasks
```

## 性能优化

### 1. 性能分析
```python
import cProfile
import pstats

def profile_function():
    """性能分析示例"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 运行要分析的代码
    # ...
    
    profiler.disable()
    
    # 输出分析结果
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # 显示前10个最耗时的函数
```

### 2. 内存分析
```bash
# 使用 memory_profiler
pip install memory_profiler

# 在代码中添加装饰器
from memory_profiler import profile

@profile
def memory_intensive_function():
    # 内存密集型操作
    pass
```

### 3. 优化建议
1. **使用缓存**：对频繁访问的数据使用缓存
2. **异步处理**：对 I/O 密集型操作使用异步
3. **连接池**：数据库或网络连接使用连接池
4. **懒加载**：延迟加载不立即需要的资源

## 常见问题

### 1. 端口被占用
```bash
# 检查端口占用
sudo lsof -i :8081

# 杀死占用进程
sudo kill -9 <PID>

# 或使用其他端口
python src/web_server/server.py --port 8082
```

### 2. 导入错误
```bash
# 确保在项目根目录运行
cd /path/to/web-server

# 确保虚拟环境已激活
source .venv/bin/activate

# 确保 Python 路径正确
export PYTHONPATH=/path/to/web-server:$PYTHONPATH
```

### 3. 依赖问题
```bash
# 更新所有依赖
pip install --upgrade -r requirements.txt

# 清理并重新安装
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### 4. 权限问题
```bash
# 确保有文件读写权限
sudo chown -R $USER:$USER /var/www/html/gtd/

# 或使用用户目录
export GTD_TASKS_FILE=~/gtd/tasks.md
```

### 5. 热重载不工作
```bash
# 确保使用 --reloader 参数
python -m src.web_server.server --reloader

# 或设置环境变量
export RELOADER=true
python src/web_server/server.py
```

## 获取帮助

- **查看日志**：`tail -f /var/log/web-server.log`
- **查看文档**：`docs/` 目录下的文档
- **提交 Issue**：GitHub Issues 页面
- **调试建议**：使用 `--debug` 参数启动服务器

---

**Happy Coding!** 🚀

遵循本指南将帮助您高效地进行 Web Server 项目的开发工作。如有问题，请参考相关文档或联系项目维护者。