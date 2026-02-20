#!/usr/bin/env python3
"""
Code Analyzer - 代码分析工具

使用 Python AST 模块提取源代码中的类、函数、导入等信息。

功能：
1. 分析单个文件，提取类和函数定义
2. 提取导入语句
3. 生成结构化的代码信息

用法：
    python3 code_analyzer.py --file <path> [--output json]
    or as a module:
        from code_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file("src/core/settings.py")
"""

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


class CodeAnalyzer:
    """代码分析器 - 使用 AST 分析 Python 源代码"""

    def __init__(self, project_root: Optional[str] = None):
        """初始化代码分析器

        Args:
            project_root: 项目根目录，用于计算相对路径
        """
        self.project_root = Path(project_root).resolve() if project_root else None

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """分析单个 Python 文件

        Args:
            file_path: 文件路径

        Returns:
            包含分析结果的字典:
            {
                "file": "相对路径",
                "classes": [{"name": "类名", "methods": [...], "docstring": "..."}],
                "functions": [{"name": "函数名", "docstring": "..."}],
                "imports": ["import语句"],
                "errors": ["错误信息"]
            }
        """
        path = Path(file_path).resolve()

        if not path.exists():
            return {
                "file": file_path,
                "error": f"File not found: {file_path}",
                "classes": [],
                "functions": [],
                "imports": []
            }

        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(path))
        except SyntaxError as e:
            return {
                "file": file_path,
                "error": f"Syntax error: {e}",
                "classes": [],
                "functions": [],
                "imports": []
            }
        except Exception as e:
            return {
                "file": file_path,
                "error": f"Parse error: {e}",
                "classes": [],
                "functions": [],
                "imports": []
            }

        result = {
            "file": str(path.relative_to(self.project_root)) if self.project_root else str(path),
            "classes": self._extract_classes(tree),
            "functions": self._extract_functions(tree),
            "imports": self._extract_imports(tree)
        }

        return result

    def analyze_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """分析多个文件

        Args:
            file_paths: 文件路径列表

        Returns:
            分析结果列表
        """
        results = []
        for file_path in file_paths:
            result = self.analyze_file(file_path)
            results.append(result)
        return results

    def _extract_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """提取类定义

        Args:
            tree: AST 树

        Returns:
            类信息列表
        """
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "lineno": node.lineno,
                    "docstring": ast.get_docstring(node),
                    "methods": [],
                    "bases": []
                }

                # 提取基类
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        class_info["bases"].append(base.id)
                    elif isinstance(base, ast.Attribute):
                        class_info["bases"].append(f"{base.value.id}.{base.attr}")

                # 提取方法
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = {
                            "name": item.name,
                            "lineno": item.lineno,
                            "docstring": ast.get_docstring(item),
                            "args": [arg.arg for arg in item.args.args],
                            "returns": ast.unparse(item.returns) if item.returns else None
                        }
                        class_info["methods"].append(method_info)

                classes.append(class_info)

        return classes

    def _extract_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """提取顶层函数定义

        Args:
            tree: AST 树

        Returns:
            函数信息列表
        """
        functions = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "lineno": node.lineno,
                    "docstring": ast.get_docstring(node),
                    "args": [arg.arg for arg in node.args.args],
                    "returns": ast.unparse(node.returns) if node.returns else None
                }
                functions.append(func_info)

        return functions

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """提取导入语句

        Args:
            tree: AST 树

        Returns:
            导入语句字符串列表
        """
        imports = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                imports.append(f"from {module} import {', '.join(names)}")

        return imports

    def format_markdown(self, analysis_result: Dict[str, Any]) -> str:
        """将分析结果格式化为 Markdown

        Args:
            analysis_result: analyze_file 返回的分析结果

        Returns:
            Markdown 格式的字符串
        """
        if "error" in analysis_result:
            return f"**Error**: {analysis_result['error']}"

        lines = []
        lines.append(f"#### 文件: `{analysis_result['file']}`")
        lines.append("")

        # 类
        if analysis_result["classes"]:
            lines.append("**类:**")
            for cls in analysis_result["classes"]:
                bases = f"({', '.join(cls['bases'])})" if cls['bases'] else ""
                lines.append(f"- **{cls['name']}**{bases}")

                if cls["docstring"]:
                    lines.append(f"  - *{cls['docstring'][:100]}...*")

                if cls["methods"]:
                    lines.append("  - 方法:")
                    for method in cls["methods"]:
                        args = ", ".join(method["args"])
                        returns = f" -> {method['returns']}" if method['returns'] else ""
                        lines.append(f"    - `{method['name']}({args}){returns}`")
            lines.append("")

        # 顶层函数
        if analysis_result["functions"]:
            lines.append("**函数:**")
            for func in analysis_result["functions"]:
                args = ", ".join(func["args"])
                returns = f" -> {func['returns']}" if func['returns'] else ""
                lines.append(f"- `{func['name']}({args}){returns}`")
                if func["docstring"]:
                    lines.append(f"  - *{func['docstring'][:100]}...*")
            lines.append("")

        # 导入
        if analysis_result["imports"]:
            lines.append("**导入:**")
            for imp in analysis_result["imports"][:10]:  # 限制显示数量
                lines.append(f"- `{imp}`")
            if len(analysis_result["imports"]) > 10:
                lines.append(f"- ... 和其他 {len(analysis_result['imports']) - 10} 个导入")
            lines.append("")

        return "\n".join(lines)


def load_task(task_input: str) -> Dict:
    """加载任务数据

    Args:
        task_input: 任务 JSON 字符串或包含 JSON 的文件路径

    Returns:
        任务字典
    """
    task_path = Path(task_input)
    if task_path.exists():
        with open(task_path, "r", encoding="utf-8") as f:
            return json.load(f)

    try:
        return json.loads(task_input)
    except json.JSONDecodeError:
        print(f"❌ 错误：无法解析任务数据: {task_input}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="代码分析工具 - 使用 AST 分析 Python 源代码"
    )
    parser.add_argument("--file", help="要分析的文件路径")
    parser.add_argument("--files", nargs="+", help="要分析的多个文件路径")
    parser.add_argument("--task", help="任务 JSON（字符串或文件路径），从中提取文件列表")
    parser.add_argument("--output", choices=["json", "markdown"], default="markdown",
                       help="输出格式（默认 markdown）")
    parser.add_argument("--project-root", default=".", help="项目根目录")

    args = parser.parse_args()

    # 确定要分析的文件列表
    file_paths = []

    if args.task:
        task = load_task(args.task)
        # 从任务中提取文件路径
        if "created_files" in task:
            file_paths = task["created_files"]
        elif "file" in task:
            # 单个任务文件
            file_paths = [task["file"]]
            # 添加对应的测试文件
            test_file = f"tests/unit/test_{Path(task['file']).name}"
            if Path(test_file).exists():
                file_paths.append(test_file)
    elif args.files:
        file_paths = args.files
    elif args.file:
        file_paths = [args.file]
    else:
        parser.print_help()
        print("\n错误：必须指定 --file, --files 或 --task")
        return 1

    # 分析文件
    analyzer = CodeAnalyzer(args.project_root)

    if args.output == "json":
        results = analyzer.analyze_files(file_paths)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        # Markdown 输出
        for file_path in file_paths:
            result = analyzer.analyze_file(file_path)
            print(analyzer.format_markdown(result))
            print("---")
            print()

    return 0


if __name__ == "__main__":
    exit(main())