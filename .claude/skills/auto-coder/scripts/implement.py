#!/usr/bin/env python3
"""
Implement - 生成代码和测试文件

功能：
1. 读取任务和相关技术规范
2. 生成文件列表计划
3. 创建目录结构
4. 生成代码文件（遵循代码标准）
5. 生成对应测试文件

用法：
    python3 implement.py --task <task_json> --spec-dir specs/
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional


class CodeGenerator:
    """代码生成器"""

    # 代码标准模板
    CODE_TEMPLATE = '''"""{module_docstring}"""

{imports}


class {class_name}:
    """{class_docstring}"""

    def __init__(self{init_params}):
        """初始化 {class_name}.

        Args:
{init_args_docstring}
        """
{init_body}

    def {method_name}(self{method_params}) -> {return_type}:
        """{method_docstring}.

        Args:
{method_args_docstring}

        Returns:
{returns_docstring}

        Raises:
{raises_docstring}
        """
{method_body}
'''

    TEST_TEMPLATE = '''"""Tests for {module_name}."""

import pytest
from unittest.mock import Mock, patch
{test_imports}


class Test{class_name}:
    """Test {class_name}."""

    @pytest.fixture
    def {fixture_name}(self):
        """创建测试实例."""
        {fixture_body}
        return {fixture_return}

    def test_{test_case}_success(self, {fixture_name}):
        """测试 {test_case} 成功场景."""
        # Arrange
        {arrange}

        # Act
        {act}

        # Assert
        {assert_}
'''

    def __init__(self, project_root: str, spec_dir: str):
        self.project_root = Path(project_root)
        self.spec_dir = Path(spec_dir)
        self.created_files: List[Path] = []

    def generate(self, task: Dict) -> bool:
        """生成代码和测试文件"""
        print(f"\n🔨 实现任务: {task['title']}")

        # 1. 分析任务，确定文件列表
        files_to_create = self._analyze_task(task)
        print(f"   需要创建 {len(files_to_create)} 个文件")

        # 2. 创建目录结构
        for file_path in files_to_create:
            self._ensure_dir(file_path)

        # 3. 生成代码文件
        for file_info in files_to_create:
            if file_info["type"] == "source":
                self._generate_source_file(file_info, task)
            elif file_info["type"] == "test":
                self._generate_test_file(file_info, task)

        return True

    def _analyze_task(self, task: Dict) -> List[Dict]:
        """分析任务，确定需要创建的文件"""
        files = []
        source_file = task["file"]

        # 源文件
        files.append({
            "type": "source",
            "path": Path(source_file),
            "class_name": self._infer_class_name(source_file),
            "module_name": self._infer_module_name(source_file)
        })

        # 测试文件
        test_file = self._infer_test_path(source_file)
        files.append({
            "type": "test",
            "path": Path(test_file),
            "class_name": self._infer_class_name(source_file),
            "module_name": self._infer_module_name(source_file)
        })

        return files

    def _ensure_dir(self, file_info: Dict):
        """确保目录存在"""
        file_path = self.project_root / file_info["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)

    def _generate_source_file(self, file_info: Dict, task: Dict):
        """生成源代码文件"""
        file_path = self.project_root / file_info["path"]
        class_name = file_info["class_name"]
        module_name = file_info["module_name"]

        # 生成代码内容（这里使用模板，实际应该由 Claude AI 生成）
        content = self._generate_code_content(class_name, module_name, task)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.created_files.append(file_path)
        print(f"   ✅ 创建: {file_path}")

    def _generate_test_file(self, file_info: Dict, task: Dict):
        """生成测试文件"""
        file_path = self.project_root / file_info["path"]
        class_name = file_info["class_name"]
        module_name = file_info["module_name"]

        # 生成测试内容
        content = self._generate_test_content(class_name, module_name, task)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.created_files.append(file_path)
        print(f"   ✅ 创建: {file_path}")

    def _generate_code_content(self, class_name: str, module_name: str, task: Dict) -> str:
        """生成代码内容

        注意：这是一个简化版本。实际使用时，应该由 Claude AI 根据任务描述
        和技术规范生成完整的、符合业务逻辑的代码。
        """
        # 从任务描述中提取方法信息
        method_name = self._infer_method_name(task["title"])
        return_type = self._infer_return_type(task["file"])

        content = f'''"""{module_name} - {task['title']}.

此模块实现: {task['acceptance_criteria']}
"""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


class {class_name}:
    """{class_name}.

    {task['acceptance_criteria']}
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化 {class_name}.

        Args:
            config: 配置字典，从 config/settings.yaml 加载
        """
        self.config = config or {{}}
        self._validate_config()

    def _validate_config(self) -> None:
        """验证配置.

        Raises:
            ValueError: 当配置无效时
        """
        required_keys = []  # 根据实际需求添加
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {{key}}")

    def {method_name}(self, *args, **kwargs) -> {return_type}:
        """{task['title']}.

        {task['acceptance_criteria']}

        Returns:
            {return_type}: 返回值描述

        Raises:
            NotImplementedError: 此方法需要根据具体任务实现
        """
        # TODO: 根据 devspec.md 中的规范实现此方法
        raise NotImplementedError("Method implementation pending")

    def __repr__(self) -> str:
        """字符串表示."""
        return f"{self.__class__.__name__}(config={{self.config}})"
'''
        return content

    def _generate_test_content(self, class_name: str, module_name: str, task: Dict) -> str:
        """生成测试内容"""
        method_name = self._infer_method_name(task["title"])

        content = f'''"""Tests for {module_name}."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

{self._get_import_statement(module_name, class_name)}


class Test{class_name}:
    """Test {class_name}."""

    @pytest.fixture
    def config(self):
        """测试配置."""
        return {{
            # 添加测试配置
        }}

    @pytest.fixture
    def instance(self, config):
        """创建测试实例."""
        return {class_name}(config=config)

    def test_init_success(self, instance):
        """测试初始化成功."""
        assert instance is not None
        assert instance.config is not None

    def test_{method_name}_not_implemented(self, instance):
        """测试 {method_name} 尚未实现."""
        with pytest.raises(NotImplementedError):
            instance.{method_name}()

    # TODO: 根据验收标准添加更多测试用例
    # 参考 task['acceptance_criteria']
'''
        return content

    @staticmethod
    def _infer_class_name(file_path: str) -> str:
        """从文件路径推断类名"""
        # 例如：src/core/settings.py -> Settings
        # 例如：src/libs/llm/azure_llm.py -> AzureLLM
        name = Path(file_path).stem
        # 转换为 PascalCase
        parts = name.split("_")
        return "".join(p.title() for p in parts)

    @staticmethod
    def _infer_module_name(file_path: str) -> str:
        """从文件路径推断模块名"""
        return Path(file_path).stem

    @staticmethod
    def _infer_method_name(title: str) -> str:
        """从任务标题推断方法名"""
        # 例如：配置加载器 -> load_settings
        # 例如：LLM抽象基类 -> chat
        if "加载" in title:
            return "load"
        elif "查询" in title or "检索" in title:
            return "query"
        elif "存储" in title:
            return "upsert"
        else:
            return "execute"

    @staticmethod
    def _infer_return_type(file_path: str) -> str:
        """从文件路径推断返回类型"""
        if "loader" in file_path:
            return "Document"
        elif "splitter" in file_path:
            return "List[Chunk]"
        elif "retriever" in file_path:
            return "List[Chunk]"
        else:
            return "Any"

    @staticmethod
    def _infer_test_path(source_file: str) -> str:
        """从源文件路径推断测试文件路径"""
        # 例如：src/core/settings.py -> tests/unit/test_settings.py
        # 例如：src/libs/llm/azure_llm.py -> tests/unit/test_azure_llm.py
        parts = Path(source_file).parts
        if "src" in parts:
            idx = parts.index("src")
            test_path = Path("tests") / "/".join(parts[idx+1:])
        else:
            test_path = Path("tests") / "/".join(parts[1:])

        return f"tests/unit/test_{test_path.name}"

    @staticmethod
    def _get_import_statement(module_name: str, class_name: str) -> str:
        """生成导入语句"""
        # 根据模块路径生成正确的导入
        return f"from {module_name} import {class_name}"

    def rollback(self):
        """回滚已创建的文件"""
        print(f"\n🔄 回滚已创建的文件...")
        for file_path in self.created_files:
            if file_path.exists():
                file_path.unlink()
                print(f"   🗑️  删除: {file_path}")


def load_task(task_input: str) -> Dict:
    """加载任务数据

    Args:
        task_input: 任务 JSON 字符串或包含 JSON 的文件路径

    Returns:
        任务字典
    """
    # 尝试作为文件读取
    task_path = Path(task_input)
    if task_path.exists():
        with open(task_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 尝试作为 JSON 字符串解析
    try:
        return json.loads(task_input)
    except json.JSONDecodeError:
        print(f"❌ 错误：无法解析任务数据: {task_input}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="生成代码和测试文件")
    parser.add_argument("--task", required=True, help="任务 JSON（字符串或文件路径）")
    parser.add_argument("--spec-dir", default="specs", help="规格文档目录")
    parser.add_argument("--project-root", default=".", help="项目根目录")

    args = parser.parse_args()

    # 加载任务
    task = load_task(args.task)

    # 生成代码
    generator = CodeGenerator(args.project_root, args.spec_dir)
    try:
        success = generator.generate(task)
        if success:
            print(f"\n✅ 代码生成完成！")
            print(f"   创建了 {len(generator.created_files)} 个文件")
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ 代码生成失败: {e}")
        generator.rollback()
        return 1


if __name__ == "__main__":
    exit(main())
