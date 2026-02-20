# 代码编写标准

## 概述

本文档定义了项目代码的编写标准，所有自动生成的代码必须遵循这些规范。

## 核心原则

1. **类型注解**：所有函数必须包含参数和返回值类型注解
2. **Docstring**：使用 Google 风格 docstring
3. **配置驱动**：从 `config/settings.yaml` 读取配置
4. **单一职责**：每个类/函数只做一件事
5. **错误处理**：使用 try-except，记录详细错误信息

## 类型注解

### 函数定义

```python
from typing import List, Dict, Optional, Any

def process_documents(
    documents: List[Document],
    config: Optional[Dict[str, Any]] = None
) -> List[Chunk]:
    """处理文档列表，返回分块列表.

    Args:
        documents: 待处理的文档列表
        config: 可选配置字典

    Returns:
        分块后的文档列表
    """
    ...
```

### 类方法

```python
class VectorStore:
    def upsert(
        self,
        chunks: List[Chunk],
        collection: str
    ) -> int:
        """批量插入或更新向量数据.

        Args:
            chunks: 待插入的分块列表
            collection: 集合名称

        Returns:
            插入的记录数
        """
        ...
```

## Docstring 规范

### Google 风格

```python
def retrieve(
    query: str,
    top_k: int = 10,
    filter: Optional[Dict[str, Any]] = None
) -> List[Chunk]:
    """执行检索并返回最相关的分块.

    Args:
        query: 查询文本
        top_k: 返回结果数量，默认 10
        filter: 元数据过滤条件

    Returns:
        相关性最高的 top-k 个分块，按相关性降序排列

    Raises:
        ValueError: 当 query 为空时
        ConnectionError: 当向量库连接失败时
    """
    ...
```

### 类 Docstring

```python
class HybridRetriever:
    """混合检索器，结合稠密和稀疏检索.

    该检索器使用 RRF（Reciprocal Rank Fusion）算法融合稠密向量检索
    和稀疏 BM25 检索的结果，提供更准确的检索效果。

    Attributes:
        dense_retriever: 稠密向量检索器
        sparse_retriever: 稀疏检索器
        fusion_k: RRF 融合参数，默认 60

    Example:
        >>> retriever = HybridRetriever(dense, sparse)
        >>> results = retriever.retrieve("如何安装 Python？", top_k=5)
    """
```

## 配置驱动

### 配置文件结构

```yaml
# config/settings.yaml
llm:
  provider: azure
  model: gpt-4o
  api_key: ${AZURE_API_KEY}

embedding:
  provider: openai
  model: text-embedding-3-small

vector_store:
  backend: chroma
  path: ./data/db/chroma
```

### 配置加载

```python
from pathlib import Path
import yaml

class Settings:
    """配置管理类."""

    def __init__(self, config_path: str = "config/settings.yaml"):
        """初始化配置.

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def llm_config(self) -> Dict[str, Any]:
        """获取 LLM 配置."""
        return self._config.get("llm", {})
```

## 单一职责原则

### 反面示例

```python
# ❌ 错误：一个函数做太多事情
def process_and_store_and_notify(data: str) -> bool:
    # 处理数据
    processed = data.upper()
    # 存储到数据库
    db.save(processed)
    # 发送通知
    email.send("Done")
    return True
```

### 正面示例

```python
# ✅ 正确：每个函数只做一件事
def process_data(data: str) -> str:
    """处理数据."""
    return data.upper()

def store_to_db(data: str) -> bool:
    """存储到数据库."""
    return db.save(data)

def send_notification(message: str) -> bool:
    """发送通知."""
    return email.send(message)

def orchestrate(data: str) -> bool:
    """编排流程."""
    processed = process_data(data)
    if store_to_db(processed):
        return send_notification("Done")
    return False
```

## 错误处理

### 标准模式

```python
from typing import TypeVar, Generic
import logging

T = TypeVar('T')
logger = logging.getLogger(__name__)

def safe_operation(input_data: str) -> Optional[T]:
    """安全操作，包含错误处理.

    Args:
        input_data: 输入数据

    Returns:
        操作结果，失败时返回 None
    """
    try:
        result = _do_operation(input_data)
        return result
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return None
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        # 可选：尝试回退策略
        return _fallback_operation(input_data)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return None
```

### 自定义异常

```python
class IngestionError(Exception):
    """数据摄取错误."""

    def __init__(self, message: str, file_path: str, cause: Optional[Exception] = None):
        """初始化异常.

        Args:
            message: 错误消息
            file_path: 相关文件路径
            cause: 原始异常
        """
        super().__init__(f"{message}: {file_path}")
        self.file_path = file_path
        self.cause = cause
```

## 测试标准

### 单元测试结构

```python
import pytest
from unittest.mock import Mock, patch

class TestMyClass:
    """测试 MyClass."""

    @pytest.fixture
    def instance(self):
        """创建测试实例."""
        config = {"key": "value"}
        return MyClass(config)

    @pytest.fixture
    def mock_dependency(self):
        """创建模拟依赖."""
        with patch('module.Dependency') as mock:
            yield mock

    def test_method_success(self, instance, mock_dependency):
        """测试方法成功场景."""
        # Arrange
        mock_dependency.return_value = "expected"
        input_data = "test"

        # Act
        result = instance.method(input_data)

        # Assert
        assert result == "expected"
        mock_dependency.assert_called_once_with(input_data)

    def test_method_failure(self, instance):
        """测试方法失败场景."""
        with pytest.raises(ValueError):
            instance.method("")
```

## 导入顺序

```python
# 1. 标准库
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 2. 第三方库
import yaml
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 3. 本地模块
from src.core.types import Document, Chunk
from src.libs.llm.base_llm import BaseLLM
```

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `VectorStore`, `HybridRetriever` |
| 函数名 | snake_case | `upsert_chunks`, `retrieve_documents` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| 私有方法 | _leading_underscore | `_validate_config`, `_load_cache` |
| 模块名 | snake_case | `vector_store.py`, `query_processor.py` |
