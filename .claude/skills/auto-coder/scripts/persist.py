#!/usr/bin/env python3
"""
Persist - 更新规格文档状态并可选提交到 git

功能：
1. 更新 devspec.md 中的任务状态
2. 更新 specs/task_index.json
3. 可选：创建 git commit
4. 提示用户下一步操作

用法：
    python3 persist.py --task <task_json> --spec devspec.md [--commit]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class SpecUpdater:
    """规格文档更新器"""

    STATUS_MAP = {
        "pending": "[ ]",
        "in_progress": "[~]",
        "completed": "[x]"
    }

    def __init__(self, project_root: str, spec_path: str):
        self.project_root = Path(project_root).resolve()
        self.spec_path = self.project_root / spec_path
        self.index_path = self.project_root / "specs" / "task_index.json"

    def update_task_status(self, task: Dict, new_status: str) -> bool:
        """更新任务状态

        Args:
            task: 任务字典
            new_status: 新状态 (pending, in_progress, completed)

        Returns:
            是否更新成功
        """
        print(f"\n📝 更新任务状态: {task['title']} -> {new_status}")

        # 1. 更新 devspec.md
        if not self._update_spec_file(task, new_status):
            return False

        # 2. 更新 task_index.json
        if not self._update_index_file(task, new_status):
            return False

        # 3. 更新进度跟踪表格
        if not self._update_progress_table():
            return False

        print(f"✅ 任务状态已更新")
        return True

    def _update_spec_file(self, task: Dict, new_status: str) -> bool:
        """更新规格文档中的任务状态"""
        if not self.spec_path.exists():
            print(f"❌ 规格文档不存在: {self.spec_path}")
            return False

        content = self.spec_path.read_text(encoding="utf-8")
        new_checkbox = self.STATUS_MAP.get(new_status, "[ ]")

        # 查找并替换任务行
        # 匹配格式：| [checkbox] | title | file | ...
        pattern = re.compile(
            rf'(\|\s*)\[[\]~x]\](\s*\|\s*{re.escape(task["title"])}\s*\|\s*{re.escape(task["file"])}\s*\|)',
            re.MULTILINE
        )

        match = pattern.search(content)
        if not match:
            print(f"⚠️  警告：在规格文档中未找到任务: {task['title']}")
            return False

        # 替换状态
        new_line = match.group(1) + new_checkbox + match.group(2)
        content = pattern.sub(new_line, content, count=1)

        # 写回文件
        self.spec_path.write_text(content, encoding="utf-8")
        print(f"   ✅ 更新: {self.spec_path}")

        return True

    def _update_index_file(self, task: Dict, new_status: str) -> bool:
        """更新任务索引文件"""
        if not self.index_path.exists():
            print(f"⚠️  警告：任务索引不存在: {self.index_path}")
            return False

        with open(self.index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

        # 更新任务状态
        for t in index["tasks"]:
            if t["id"] == task["id"]:
                t["status"] = new_status
                break

        # 更新统计
        index["completed"] = sum(1 for t in index["tasks"] if t["status"] == "completed")
        index["in_progress"] = sum(1 for t in index["tasks"] if t["status"] == "in_progress")
        index["pending"] = sum(1 for t in index["tasks"] if t["status"] == "pending")

        # 写回文件
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        print(f"   ✅ 更新: {self.index_path}")
        return True

    def _update_progress_table(self) -> bool:
        """更新进度跟踪表格

        根据各阶段任务完成情况，更新进度跟踪表格中的状态。

        Returns:
            是否更新成功
        """
        if not self.index_path.exists():
            return True  # 如果索引不存在，跳过

        # 读取任务索引
        with open(self.index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

        # 按阶段统计任务
        phase_stats: Dict[str, Dict[str, int]] = {}
        for task in index["tasks"]:
            phase = task.get("phase", "未知")
            if phase not in phase_stats:
                phase_stats[phase] = {"total": 0, "completed": 0, "in_progress": 0}
            phase_stats[phase]["total"] += 1
            if task["status"] == "completed":
                phase_stats[phase]["completed"] += 1
            elif task["status"] == "in_progress":
                phase_stats[phase]["in_progress"] += 1

        # 读取 spec 文件
        content = self.spec_path.read_text(encoding="utf-8")

        # 更新进度跟踪表格
        today = datetime.now().strftime("%Y-%m-%d")

        # 阶段映射：从 phase 名称到表格中的行名
        phase_mapping = {
            "阶段 0: 项目基础设施 (Day 1)": "阶段0",
            "阶段 1: Libs 层 - 可插拔抽象 (Day 2-5)": "阶段1",
            "阶段 2: Ingestion Pipeline (Day 6-9)": "阶段2",
            "阶段 3: Query Engine (Day 10-13)": "阶段3",
            "阶段 4: Response & Trace (Day 14-15)": "阶段4",
            "阶段 5: Observability 基础 (Day 16-17)": "阶段5",
            "阶段 6: MCP Server (Day 18-20)": "阶段6",
            "阶段 7: Dashboard (Day 21-24)": "阶段7",
            "阶段 8: 测试与优化 (Day 25-27)": "阶段8",
        }

        # 原始备注映射（保留原有描述）
        original_notes = {
            "阶段0": "基础设施",
            "阶段1": "Libs层",
            "阶段2": "Ingestion",
            "阶段3": "Query Engine",
            "阶段4": "Response & Trace",
            "阶段5": "Observability",
            "阶段6": "MCP Server",
            "阶段7": "Dashboard",
            "阶段8": "测试与优化",
        }

        for phase_full, phase_short in phase_mapping.items():
            if phase_full not in phase_stats:
                continue

            stats = phase_stats[phase_full]
            original_note = original_notes.get(phase_short, "")

            # 确定状态
            if stats["completed"] == stats["total"]:
                status = "✅ 已完成"
                date = today
            elif stats["completed"] > 0 or stats["in_progress"] > 0:
                status = "🟡 进行中"
                date = today
            else:
                status = "⬜ 待开始"
                date = "-"

            # 生成备注（保留原描述，添加进度）
            if stats["completed"] == stats["total"] and stats["total"] > 0:
                note = original_note
            elif stats["completed"] > 0 or stats["in_progress"] > 0:
                note = f"{original_note} ({stats['completed']}/{stats['total']})"
            else:
                note = original_note

            # 匹配并替换表格行
            # 格式：| 阶段1 | ⬜ 待开始 | - | Libs层 |
            pattern = re.compile(
                rf'(\|\s*{re.escape(phase_short)}\s*\|\s*)[^\|]+(\s*\|\s*)[^\|]+(\s*\|\s*)[^\|]+(\s*\|)'
            )

            def replacement(match):
                return f"{match.group(1)}{status}{match.group(2)}{date}{match.group(3)}{note}{match.group(4)}"

            new_content = pattern.sub(replacement, content)
            if new_content != content:
                content = new_content
                print(f"   ✅ 更新进度: {phase_short} -> {status}")

        # 写回文件
        self.spec_path.write_text(content, encoding="utf-8")
        return True


class GitCommitter:
    """Git 提交器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()

    def commit_task(self, task: Dict, files: Optional[list] = None) -> bool:
        """创建 git commit

        Args:
            task: 任务字典
            files: 要提交的文件列表（None 表示所有更改）

        Returns:
            是否提交成功
        """
        # 检查是否在 git 仓库中
        if not self._is_git_repo():
            print(f"⚠️  不是 git 仓库，跳过 commit")
            return False

        print(f"\n📦 创建 git commit")

        # 生成 commit message
        commit_msg = self._generate_commit_message(task)
        print(f"   消息: {commit_msg}")

        # 添加文件
        if files:
            for file in files:
                self._git_add(file)
        else:
            self._git_add_all()

        # 创建 commit
        result = self._git_commit(commit_msg)
        if result:
            print(f"✅ Commit 创建成功")
        else:
            print(f"❌ Commit 创建失败")

        return result

    def _is_git_repo(self) -> bool:
        """检查是否在 git 仓库中"""
        git_dir = self.project_root / ".git"
        return git_dir.exists()

    def _git_add(self, file_path: str):
        """添加单个文件到 git"""
        result = subprocess.run(
            ["git", "add", file_path],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"   ➕ 添加: {file_path}")
        else:
            print(f"   ⚠️  添加失败: {file_path}")

    def _git_add_all(self):
        """添加所有更改到 git"""
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"   ➕ 添加所有更改")

    def _git_commit(self, message: str) -> bool:
        """创建 git commit"""
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def _generate_commit_message(self, task: Dict) -> str:
        """生成 commit message

        格式：feat(<module>): <description>
        例如：feat(core): 配置加载器实现
        """
        # 从文件路径推断模块名
        file_path = Path(task["file"])
        if "src" in file_path.parts:
            idx = file_path.parts.index("src")
            if idx + 1 < len(file_path.parts):
                module = file_path.parts[idx + 1]
            else:
                module = "core"
        else:
            module = "misc"

        # 生成描述
        description = task["title"]

        return f"feat({module}): {description}"


def load_task(task_input: str) -> Dict:
    """加载任务数据"""
    task_path = Path(task_input)
    if task_path.exists():
        with open(task_path, "r", encoding="utf-8") as f:
            return json.load(f)
    try:
        return json.loads(task_input)
    except json.JSONDecodeError:
        print(f"❌ 错误：无法解析任务数据: {task_input}")
        sys.exit(1)


def prompt_next_action() -> str:
    """提示用户下一步操作"""
    print("\n" + "="*50)
    print("✅ 任务完成！")
    print("="*50)
    print("\n下一步操作:")
    print("  1. 继续下一个任务")
    print("  2. 查看当前进度")
    print("  3. 退出")
    print("\n请选择 [1/2/3]: ", end="")

    return input().strip()


def main():
    parser = argparse.ArgumentParser(description="更新规格文档并可选提交")
    parser.add_argument("--task", required=True, help="任务 JSON（字符串或文件路径）")
    parser.add_argument("--spec", default="devspec.md", help="规格文档路径")
    parser.add_argument("--status", required=True, choices=["pending", "in_progress", "completed"],
                       help="新状态")
    parser.add_argument("--commit", action="store_true", help="创建 git commit")
    parser.add_argument("--project-root", default=".", help="项目根目录")

    args = parser.parse_args()

    # 加载任务
    task = load_task(args.task)

    # 更新规格文档
    updater = SpecUpdater(args.project_root, args.spec)
    if not updater.update_task_status(task, args.status):
        return 1

    # Git commit
    if args.commit and args.status == "completed":
        committer = GitCommitter(args.project_root)
        committer.commit_task(task)

    return 0


if __name__ == "__main__":
    exit(main())
