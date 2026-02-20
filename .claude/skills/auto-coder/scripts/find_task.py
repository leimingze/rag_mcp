#!/usr/bin/env python3
"""
Find Task - 查找下一个待执行的任务

功能：
1. 根据 task_index.json 查找任务
2. 支持指定 task-id
3. 自动选择下一个任务（优先进行中，其次未开始且依赖满足）
4. 检查依赖关系

用法：
    python3 find_task.py --index specs/task_index.json [--task-id <id>]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Dict, List


class TaskFinder:
    """任务查找器"""

    def __init__(self, index_path: str):
        self.index_path = Path(index_path)
        self.index: Dict = {}

    def load_index(self) -> bool:
        """加载任务索引"""
        if not self.index_path.exists():
            print(f"❌ 错误：任务索引不存在: {self.index_path}")
            print(f"   请先运行: python3 sync_spec.py --spec devspec.md --output specs/")
            return False

        with open(self.index_path, "r", encoding="utf-8") as f:
            self.index = json.load(f)

        return True

    def find_by_id(self, task_id: str) -> Optional[Dict]:
        """根据 ID 查找任务"""
        for task in self.index["tasks"]:
            if task["id"] == task_id:
                return task
        return None

    def find_next(self) -> Optional[Dict]:
        """查找下一个待执行任务

        优先级：
        1. [~] 进行中的任务
        2. [ ] 未开始且所有依赖已完成
        """
        tasks = self.index["tasks"]

        # 1. 优先查找进行中的任务
        for task in tasks:
            if task["status"] == "in_progress":
                if self._check_dependencies(task):
                    return task

        # 2. 查找未开始且依赖满足的任务
        for task in tasks:
            if task["status"] == "pending":
                if self._check_dependencies(task):
                    return task

        return None

    def _check_dependencies(self, task: Dict) -> bool:
        """检查任务依赖是否满足"""
        deps = task.get("dependencies", [])
        if not deps:
            return True

        for dep_id in deps:
            dep_task = self.find_by_id(dep_id)
            if not dep_task:
                print(f"⚠️  警告：依赖任务 {dep_id} 不存在")
                return False
            if dep_task["status"] != "completed":
                return False

        return True

    def get_blocking_tasks(self, task: Dict) -> List[Dict]:
        """获取阻塞当前任务的任务列表"""
        blockers = []
        for dep_id in task.get("dependencies", []):
            dep_task = self.find_by_id(dep_id)
            if dep_task and dep_task["status"] != "completed":
                blockers.append(dep_task)
        return blockers

    def print_task(self, task: Dict):
        """打印任务详情"""
        print(f"\n{'='*60}")
        print(f"📋 任务: {task['title']}")
        print(f"{'='*60}")
        print(f"ID:          {task['id']}")
        print(f"文件:        {task['file']}")
        print(f"阶段:        {task['phase']}")
        print(f"状态:        {self._status_emoji(task['status'])} {task['status']}")
        print(f"预计工时:    {task['estimated_hours']}h")
        print(f"\n验收标准:")
        print(f"  {task['acceptance_criteria']}")

        if task.get("dependencies"):
            print(f"\n依赖任务:")
            for dep_id in task["dependencies"]:
                dep_task = self.find_by_id(dep_id)
                status = self._status_emoji(dep_task["status"]) if dep_task else "❓"
                print(f"  - {dep_id}: {status}")

    @staticmethod
    def _status_emoji(status: str) -> str:
        """状态 emoji 映射"""
        emoji_map = {
            "pending": "⬜",
            "in_progress": "🟡",
            "completed": "✅"
        }
        return emoji_map.get(status, "❓")

    def print_summary(self):
        """打印任务摘要"""
        total = self.index["total_tasks"]
        completed = self.index["completed"]
        in_progress = self.index["in_progress"]
        pending = self.index["pending"]

        print(f"\n📊 任务概览:")
        print(f"  总计:     {total}")
        print(f"  ✅ 已完成: {completed} ({completed/total*100:.1f}%)")
        print(f"  🟡 进行中: {in_progress}")
        print(f"  ⬜ 待开始: {pending}")


def main():
    parser = argparse.ArgumentParser(description="查找下一个待执行任务")
    parser.add_argument("--index", default="specs/task_index.json", help="任务索引路径")
    parser.add_argument("--task-id", help="指定任务 ID")
    parser.add_argument("--list", action="store_true", help="列出所有未完成任务")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    args = parser.parse_args()

    finder = TaskFinder(args.index)
    if not finder.load_index():
        return 1

    # 列出所有未完成任务
    if args.list:
        print("\n📋 未完成任务列表:")
        print("-" * 60)
        for task in finder.index["tasks"]:
            if task["status"] != "completed":
                status = finder._status_emoji(task["status"])
                print(f"{status} [{task['id']}] {task['title']}")
                print(f"   文件: {task['file']}")
                print(f"   阶段: {task['phase']}")
        return 0

    # 查找任务
    task = None
    if args.task_id:
        task = finder.find_by_id(args.task_id)
        if not task:
            print(f"❌ 错误：任务 {args.task_id} 不存在")
            return 1
    else:
        task = finder.find_next()
        if not task:
            finder.print_summary()
            print("\n✅ 所有任务已完成！")
            return 0

        # 检查阻塞
        blockers = finder.get_blocking_tasks(task)
        if blockers:
            print(f"\n⚠️  任务 [{task['id']}] 被以下任务阻塞:")
            for blocker in blockers:
                print(f"   - [{blocker['id']}] {blocker['title']} ({blocker['status']})")
            print("\n建议：先完成阻塞任务后再继续")
            return 1

    # JSON 输出
    if args.json:
        print(json.dumps(task, ensure_ascii=False, indent=2))
    else:
        finder.print_summary()
        finder.print_task(task)

    return 0


if __name__ == "__main__":
    exit(main())
