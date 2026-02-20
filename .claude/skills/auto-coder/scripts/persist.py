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
