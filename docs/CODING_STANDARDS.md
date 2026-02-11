# 编程规范

本文档定义了 Web Server 项目的编码标准和最佳实践。

## 目录

1. [代码风格](#代码风格)
2. [项目结构](#项目结构)
3. [Python 规范](#python-规范)
4. [文档规范](#文档规范)
5. [测试规范](#测试规范)
6. [提交规范](#提交规范)
7. [安全规范](#安全规范)

## 代码风格

### 通用原则
- **一致性**：保持代码风格一致
- **可读性**：代码应该易于理解和维护
- **简洁性**：避免不必要的复杂性
- **明确性**：命名和结构应该清晰表达意图

### Python 代码风格
- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范
- 使用 **4个空格**缩进（不要使用 Tab）
- 行长度限制在 **79个字符** 以内
- 使用 **snake_case** 命名变量和函数
- 使用 **CamelCase** 命名类
- 使用 **UPPER_CASE** 命名常量

### 示例
```python
# 好的示例
def calculate_user_score(user_id, weight=1.0):
    """计算用户得分"""
    base_score = get_base_score(user_id)
    return base_score * weight

MAX_RETRY_COUNT = 3

class UserManager:
    def __init__(self, config):
        self.config = config
    
    def get_active_users(self):
        """获取活跃用户列表"""
        return [u for u in self.users if u.is_active]

# 不好的示例
def calcUsrScr(uid, w=1.0):  # 缩写不清晰
    bs = getBaseScore(uid)   # 变量名不明确
    return bs*w              # 缺少空格
```

## 项目结构

### 目录组织
```
src/web_server/          # 主包目录
├── __init__.py         # 包初始化文件
├── server.py           # 主服务器逻辑
├── gtd.py              # GTD 功能模块
└── utils.py            # 工具函数（如果需要）

static/                 # 静态资源
├── css/               # 样式表
├── js/                # JavaScript
├── images/            # 图片资源
└── gtd/               # GTD 前端文件

tests/                  # 测试代码
├── __init__.py
├── test_server.py     # 服务器测试
└── test_gtd.py        # GTD 测试
```

### 模块组织原则
1. **单一职责**：每个模块/类应该只有一个主要职责
2. **低耦合**：模块间依赖应该最小化
3. **高内聚**：相关功能应该组织在一起
4. **明确接口**：模块间通过清晰定义的接口通信

## Python 规范

### 导入顺序
1. 标准库导入
2. 第三方库导入
3. 本地应用/库导入

每组导入之间用空行分隔，按字母顺序排序。

```python
# 标准库
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# 第三方库
import requests
from bs4 import BeautifulSoup

# 本地模块
from .gtd import GTDHandler, GTD_TASKS_FILE
```

### 类型提示
- 对新代码使用类型提示
- 对公共 API 必须使用类型提示
- 使用 Python 3.7+ 的 `typing` 模块

```python
from typing import Dict, List, Optional, Union

def parse_markdown_to_json(markdown: str) -> Dict[str, List[Dict]]:
    """解析 Markdown 为 JSON 结构
    
    Args:
        markdown: Markdown 格式的文本
        
    Returns:
        包含任务分类的字典
    """
    # 实现...
```

### 错误处理
1. **使用具体的异常**：不要捕获所有异常
2. **提供有意义的错误信息**
3. **记录错误**：使用 logging 模块
4. **资源清理**：使用 `try...finally` 或上下文管理器

```python
import logging

logger = logging.getLogger(__name__)

def read_config_file(filepath: str) -> Dict:
    """读取配置文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return json.loads(content)
    except FileNotFoundError:
        logger.error(f"配置文件不存在: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"配置文件格式错误: {filepath}, 错误: {e}")
        raise ConfigError(f"无效的 JSON 格式: {filepath}") from e
```

### 日志记录
- 使用 Python 的 `logging` 模块
- 配置适当的日志级别
- 包含上下文信息

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def process_request(request):
    logger.debug(f"处理请求: {request.path}")
    try:
        # 处理逻辑
        logger.info(f"请求处理成功: {request.path}")
    except Exception as e:
        logger.error(f"请求处理失败: {request.path}, 错误: {e}")
        raise
```

## 文档规范

### 文档字符串（Docstrings）
使用 Google 风格的文档字符串：

```python
def extract_title_from_url(url: str) -> str:
    """从 URL 提取标题，使用多级回退策略
    
    策略优先级：
    1. 获取网页标题（需要 requests + BeautifulSoup）
    2. 从 URL 路径提取有意义的名称
    3. 使用域名 + 路径组合
    4. 返回原始 URL（最后回退）
    
    Args:
        url: 要提取标题的 URL
        
    Returns:
        提取的标题字符串
        
    Raises:
        ValueError: 如果 URL 格式无效
        
    Examples:
        >>> extract_title_from_url('https://github.com/zhangfuwen/web-server')
        'Web Server'
    """
    # 实现...
```

### 注释
- **行内注释**：解释复杂的逻辑
- **TODO 注释**：标记需要完成的工作
- **FIXME 注释**：标记需要修复的问题

```python
# TODO: 添加缓存机制以提高性能
# FIXME: 这里有一个边界条件需要处理

def complex_algorithm(data):
    # 这个算法的时间复杂度是 O(n log n)
    # 因为使用了快速排序和二分查找
    sorted_data = quicksort(data)  # 快速排序 O(n log n)
    result = binary_search(sorted_data, target)  # 二分查找 O(log n)
    return result
```

### API 文档
- 为所有公共 API 提供文档
- 包含示例代码
- 说明参数和返回值

## 测试规范

### 测试结构
```
tests/
├── __init__.py
├── conftest.py          # 测试配置和固件
├── test_server.py       # 服务器功能测试
├── test_gtd.py          # GTD 功能测试
└── integration/         # 集成测试
    └── test_api.py
```

### 测试编写原则
1. **独立性**：测试之间不应该相互依赖
2. **可重复性**：测试应该在任何环境下都能运行
3. **全面性**：覆盖主要功能和边界条件
4. **可读性**：测试名称应该清晰表达测试意图

```python
import pytest
from web_server.gtd import parse_markdown_to_json

class TestGTDParser:
    """GTD 解析器测试"""
    
    def test_parse_empty_markdown(self):
        """测试解析空 Markdown"""
        result = parse_markdown_to_json("")
        assert result == {
            'projects': [],
            'next_actions': [],
            'waiting_for': [],
            'someday_maybe': []
        }
    
    def test_parse_simple_task(self):
        """测试解析简单任务"""
        markdown = "# Projects\n- [ ] 完成文档"
        result = parse_markdown_to_json(markdown)
        
        assert len(result['projects']) == 1
        task = result['projects'][0]
        assert task['text'] == '完成文档'
        assert task['completed'] is False
    
    @pytest.mark.parametrize("input_text,expected_count", [
        ("- [ ] 任务1", 1),
        ("- [x] 任务2", 1),
        ("- [ ] 任务1\n- [ ] 任务2", 2),
    ])
    def test_task_count(self, input_text, expected_count):
        """参数化测试任务计数"""
        markdown = f"# Projects\n{input_text}"
        result = parse_markdown_to_json(markdown)
        assert len(result['projects']) == expected_count
```

### 测试运行
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_server.py

# 运行特定测试类
pytest tests/test_gtd.py::TestGTDParser

# 生成测试覆盖率报告
pytest --cov=src/web_server --cov-report=html
```

## 提交规范

### 提交消息格式
使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<类型>[可选的作用域]: <描述>

[可选的正文]

[可选的脚注]
```

**类型**：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变动

**示例**：
```
feat(server): 添加文件上传功能

- 支持多文件上传
- 添加文件大小限制
- 添加文件类型验证

Closes #123
```

```
fix(gtd): 修复任务解析中的空行处理

当任务后面有空行时，解析器会错误地结束任务块。
现在正确处理空行作为任务分隔符。

Fixes #456
```

### 分支命名
- `feature/<功能名>`: 新功能开发
- `fix/<问题描述>`: bug 修复
- `docs/<文档主题>`: 文档更新
- `refactor/<重构内容>`: 代码重构
- `test/<测试内容>`: 测试相关

## 安全规范

### 输入验证
- 验证所有用户输入
- 使用白名单而不是黑名单
- 对文件路径进行规范化检查

```python
import os

def safe_file_path(user_path: str, base_dir: str) -> str:
    """安全地构建文件路径，防止目录遍历攻击"""
    # 规范化路径
    normalized = os.path.normpath(user_path)
    
    # 检查是否尝试访问上级目录
    full_path = os.path.join(base_dir, normalized)
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
        raise SecurityError("禁止访问上级目录")
    
    return full_path
```

### 敏感信息
- 不要将密码、密钥等硬编码在代码中
- 使用环境变量或配置文件
- 不要在日志中记录敏感信息

### 依赖管理
- 定期更新依赖包
- 使用固定版本号（在 requirements.txt 中）
- 检查依赖的安全漏洞

```txt
# requirements.txt
requests==2.28.1
beautifulsoup4==4.11.1
psutil==5.9.4
```

## 代码审查

### 审查清单
- [ ] 代码遵循项目规范
- [ ] 有适当的测试覆盖
- [ ] 文档已更新
- [ ] 没有引入安全漏洞
- [ ] 性能影响可接受
- [ ] 向后兼容性已考虑

### 审查意见
- 使用建设性的语言
- 解释为什么需要修改
- 提供具体的改进建议
- 尊重他人的工作

## 工具配置

### 开发工具
- **代码格式化**: black, isort
- **代码检查**: flake8, pylint
- **类型检查**: mypy
- **测试框架**: pytest

### 预提交钩子
在 `.pre-commit-config.yaml` 中配置：

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

## 更新记录

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.0 | 2024-01-01 | 初始版本 |
| 1.1 | 2024-01-15 | 添加测试规范和提交规范 |

---

**遵循这些规范将有助于保持代码质量，提高团队协作效率，并确保项目的长期可维护性。**