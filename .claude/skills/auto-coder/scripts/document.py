#!/usr/bin/env python3
"""
Document - 任务完成记录工具

在任务完成时自动向 devspec.md 追加详细的实现记录。

功能：
1. 分析创建的文件，提取类/函数信息（AST）
2. 读取测试报告
3. 生成结构化的完成记录
4. 插入到 devspec.md 对应阶段
5. 更新 task_index.json 添加 documented 标记

用法：
    python3 document.py --task <task_json> --spec devspec.md
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# 导入 CodeAnalyzer
try:
    from code_analyzer import CodeAnalyzer
except ImportError:
    # 如果直接运行此脚本，尝试从同一目录导入
    sys.path.insert(0, str(Path(__file__).parent))
    from code_analyzer import CodeAnalyzer


class TaskDocumenter:
    """任务文档记录器"""

    def __init__(self, project_root: str, spec_path: str):
        """初始化文档记录器

        Args:
            project_root: 项目根目录
            spec_path: 规格文档路径
        """
        self.project_root = Path(project_root).resolve()
        self.spec_path = self.project_root / spec_path
        self.index_path = self.project_root / "specs" / "task_index.json"
        self.code_analyzer = CodeAnalyzer(project_root)

    def document_task(self, task: Dict, dry_run: bool = False) -> bool:
        """记录任务完成

        Args:
            task: 任务字典
            dry_run: 是否只预览不实际写入

        Returns:
            是否成功
        """
        print(f"\n📝 记录任务完成: {task['title']}")
        print(f"   任务 ID: {task['id']}")

        # 1. 收集实现信息
        impl_info = self._collect_implementation_info(task)

        # 2. 生成完成记录
        completion_record = self._generate_completion_record(task, impl_info)

        if dry_run:
            print("\n📄 预览完成记录:")
            print("=" * 60)
            print(completion_record)
            print("=" * 60)
            return True

        # 3. 检查是否已记录
        if self._is_already_documented(task):
            print(f"⚠️  任务已被记录，跳过")
            return True

        # 4. 插入到 devspec.md
        if not self._insert_completion_record(task, completion_record):
            return False

        # 5. 更新 task_index.json
        if not self._update_task_index(task):
            return False

        print(f"✅ 任务完成记录已添加到 {self.spec_path}")
        return True

    def _collect_implementation_info(self, task: Dict) -> Dict[str, Any]:
        """收集实现信息

        Args:
            task: 任务字典

        Returns:
            包含实现信息的字典
        """
        impl_info = {
            "created_files": [],
            "classes_and_functions": [],
            "test_results": None,
            "completion_time": datetime.now().isoformat()
        }

        # 1. 获取创建的文件列表
        if "created_files" in task:
            file_paths = task["created_files"]
        else:
            # 从任务文件推断
            file_paths = [task["file"]]
            # 添加测试文件
            test_file = self._infer_test_file(task["file"])
            if test_file and (self.project_root / test_file).exists():
                file_paths.append(test_file)

        # 筛选实际存在的 Python 文件
        for file_path in file_paths:
            full_path = self.project_root / file_path
            if full_path.exists() and file_path.endswith('.py'):
                impl_info["created_files"].append(file_path)

        # 2. 分析代码结构
        print(f"   分析 {len(impl_info['created_files'])} 个文件...")
        for file_path in impl_info["created_files"]:
            full_path = self.project_root / file_path
            if full_path.exists():
                analysis = self.code_analyzer.analyze_file(str(full_path))
                if "error" not in analysis:
                    impl_info["classes_and_functions"].append(analysis)

        # 3. 读取测试报告
        test_report_path = self.project_root / "specs" / f"test_report_{task['id']}.json"
        if test_report_path.exists():
            with open(test_report_path, "r", encoding="utf-8") as f:
                impl_info["test_results"] = json.load(f)

        return impl_info

    def _generate_completion_record(self, task: Dict, impl_info: Dict[str, Any]) -> str:
        """生成完成记录 Markdown

        Args:
            task: 任务字典
            impl_info: 实现信息字典

        Returns:
            Markdown 格式的完成记录
        """
        lines = []

        # 开始详情块
        lines.append('<details>')
        lines.append(f'<summary>✅ {task["title"]} - 完成详情</summary>')
        lines.append('')

        # 任务目标
        lines.append('### 任务目标')
        acceptance_criteria = task.get('acceptance_criteria', '无')
        lines.append(acceptance_criteria)
        lines.append('')

        # 实现内容
        lines.append('### 实现内容')
        lines.append('')

        # 创建的文件
        if impl_info["created_files"]:
            lines.append('#### 创建的文件')
            for file_path in impl_info["created_files"]:
                lines.append(f'* `{file_path}`')
            lines.append('')

        # 实现的类/函数
        if impl_info["classes_and_functions"]:
            lines.append('#### 实现的类/函数')
            for analysis in impl_info["classes_and_functions"]:
                file_path = analysis["file"]
                lines.append(f'* **文件**: `{file_path}`')

                # 类
                for cls in analysis.get("classes", []):
                    bases = f"({', '.join(cls['bases'])})" if cls['bases'] else ""
                    lines.append(f'  * **类**: `{cls["name"]}`{bases}')

                    if cls["methods"]:
                        lines.append('    * 方法:')
                        for method in cls["methods"]:
                            args = ", ".join(method["args"])
                            returns = f" -> {method['returns']}" if method['returns'] else ""
                            lines.append(f'      * `{method["name"]}({args}){returns}`')

                # 顶层函数
                for func in analysis.get("functions", []):
                    args = ", ".join(func["args"])
                    returns = f" -> {func['returns']}" if func['returns'] else ""
                    lines.append(f'  * **函数**: `{func["name"]}({args}){returns}`')

                lines.append('')

        # 验收标准验证
        lines.append('### 验收标准验证')
        if impl_info["test_results"]:
            test_result = impl_info["test_results"]
            success = test_result.get("success", False)
            total_rounds = test_result.get("total_rounds", 0)
            passed = test_result.get("rounds", [{}])[-1].get("passed", 0)
            failed = test_result.get("rounds", [{}])[-1].get("failed", 0)

            if success:
                lines.append(f'* ✅ 测试通过: {passed} 个测试用例')
            else:
                lines.append(f'* ⚠️  测试未完全通过: {passed} 通过, {failed} 失败')

            if total_rounds > 1:
                lines.append(f'* 经过 {total_rounds} 轮测试修复')
        else:
            lines.append(f'* ✅ {acceptance_criteria}')
        lines.append('')

        # 测试方法
        test_file = self._infer_test_file(task["file"])
        if test_file:
            lines.append('### 测试方法')
            lines.append(f'```bash')
            lines.append(f'pytest {test_file} -v')
            lines.append(f'```')
            lines.append('')

            # 测试统计
            if impl_info["test_results"]:
                test_result = impl_info["test_results"]
                lines.append(f'**测试轮次**: {test_result.get("total_rounds", 1)} 轮')
                lines.append(f'**测试结果**: {"✅ 通过" if test_result.get("success") else "❌ 失败"}')

                # 计算覆盖率（如果有）
                last_round = test_result.get("rounds", [{}])[-1]
                total = last_round.get("total", 0)
                if total > 0:
                    passed = last_round.get("passed", 0)
                    coverage = int((passed / total) * 100)
                    lines.append(f'**通过率**: {coverage}%')
                lines.append('')

        # 实现备注
        lines.append('### 实现备注')
        lines.append(f'完成时间: {impl_info["completion_time"]}')
        lines.append('')

        # 结束详情块
        lines.append('</details>')
        lines.append('')

        return "\n".join(lines)

    def _is_already_documented(self, task: Dict) -> bool:
        """检查任务是否已被记录

        Args:
            task: 任务字典

        Returns:
            是否已记录
        """
        # 检查 task_index.json
        if self.index_path.exists():
            with open(self.index_path, "r", encoding="utf-8") as f:
                index = json.load(f)

            for t in index.get("tasks", []):
                if t.get("id") == task["id"] and t.get("documented"):
                    return True

        # 检查 devspec.md 中是否已有记录
        if self.spec_path.exists():
            content = self.spec_path.read_text(encoding="utf-8")
            pattern = f'<summary>✅ {re.escape(task["title"])} - 完成详情</summary>'
            if re.search(pattern, content):
                return True

        return False

    def _insert_completion_record(self, task: Dict, record: str) -> bool:
        """插入完成记录到 devspec.md

        Args:
            task: 任务字典
            record: 完成记录 Markdown

        Returns:
            是否成功
        """
        if not self.spec_path.exists():
            print(f"❌ 规格文档不存在: {self.spec_path}")
            return False

        content = self.spec_path.read_text(encoding="utf-8")

        # 查找插入位置
        insertion_point = self._find_insertion_point(content, task)

        if insertion_point is None:
            print(f"⚠️  无法找到插入位置，将在文件末尾添加")
            new_content = content + "\n" + record
        else:
            # 在插入位置前添加记录
            new_content = (
                content[:insertion_point] +
                "\n#### 完成记录\n\n" +
                record +
                content[insertion_point:]
            )

        # 写回文件
        self.spec_path.write_text(new_content, encoding="utf-8")
        return True

    def _find_insertion_point(self, content: str, task: Dict) -> Optional[int]:
        """查找插入位置

        在任务所属阶段的任务表格后、里程碑行之前插入

        Args:
            content: devspec.md 内容
            task: 任务字典

        Returns:
            插入位置的字符索引，None 表示文件末尾
        """
        # 获取任务的阶段
        phase = task.get("phase", "")

        # 查找阶段标题
        phase_pattern = rf'^##+ {re.escape(phase)}.*?$'
        phase_match = re.search(phase_pattern, content, re.MULTILINE)

        if not phase_match:
            return None

        phase_start = phase_match.end()

        # 从阶段开始位置查找里程碑行
        # 里程碑行格式：**里程碑 M1**: ...
        milestone_pattern = r'\*\*里程碑 [MN]\d+\*\*:'

        # 在阶段内容中查找里程碑
        milestone_match = re.search(milestone_pattern, content[phase_start:], re.MULTILINE)

        if milestone_match:
            return phase_start + milestone_match.start()

        # 如果没有里程碑，查找下一个阶段标题
        next_phase_pattern = r'^##+ '
        next_phase_match = re.search(next_phase_pattern, content[phase_start:], re.MULTILINE)

        if next_phase_match:
            return phase_start + next_phase_match.start()

        # 如果都没有，返回文件末尾
        return None

    def _update_task_index(self, task: Dict) -> bool:
        """更新任务索引，添加 documented 标记

        Args:
            task: 任务字典

        Returns:
            是否成功
        """
        if not self.index_path.exists():
            print(f"⚠️  任务索引不存在: {self.index_path}")
            return False

        with open(self.index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

        # 更新任务
        updated = False
        for t in index.get("tasks", []):
            if t.get("id") == task["id"]:
                t["documented"] = True
                t["documented_at"] = datetime.now().isoformat()
                updated = True
                break

        if not updated:
            print(f"⚠️  未在索引中找到任务: {task['id']}")
            return False

        # 写回文件
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        return True

    def _infer_test_file(self, source_file: str) -> Optional[str]:
        """从源文件推断测试文件路径

        Args:
            source_file: 源文件路径

        Returns:
            测试文件路径，如果无法推断则返回 None
        """
        # 例如：src/core/settings.py -> tests/unit/test_settings.py
        # 例如：src/libs/llm/azure_llm.py -> tests/unit/test_azure_llm.py
        parts = Path(source_file).parts
        if "src" in parts:
            idx = parts.index("src")
            test_path = Path("tests") / "/".join(parts[idx+1:])
        else:
            test_path = Path("tests") / "/".join(parts[1:])

        return f"tests/unit/test_{test_path.name}"


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
        description="任务完成记录工具 - 向 devspec.md 添加完成详情"
    )
    parser.add_argument("--task", required=True,
                       help="任务 JSON（字符串或文件路径）")
    parser.add_argument("--spec", default="devspec.md",
                       help="规格文档路径（默认 devspec.md）")
    parser.add_argument("--project-root", default=".",
                       help="项目根目录（默认当前目录）")
    parser.add_argument("--dry-run", action="store_true",
                       help="预览模式，不实际写入")

    args = parser.parse_args()

    # 加载任务
    task = load_task(args.task)

    # 记录任务
    documenter = TaskDocumenter(args.project_root, args.spec)
    success = documenter.document_task(task, dry_run=args.dry_run)

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())