#!/usr/bin/env python3
"""
Sync Spec - 解析规格文档并生成任务索引

功能：
1. 按章节拆分规格文档
2. 提取所有 checkbox 任务（[ ] 未开始, [~] 进行中, [x] 已完成）
3. 生成任务索引 JSON

用法：
    python3 sync_spec.py --spec devspec.md --output specs/
"""

import argparse
import json
import re
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class Task:
    """任务数据结构"""
    id: str
    title: str
    file: str
    status: str  # pending, in_progress, completed
    phase: str
    dependencies: List[str] = field(default_factory=list)
    description: str = ""
    acceptance_criteria: str = ""
    estimated_hours: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "file": self.file,
            "status": self.status,
            "phase": self.phase,
            "dependencies": self.dependencies,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "estimated_hours": self.estimated_hours
        }


class SpecParser:
    """规格文档解析器"""

    # Checkbox 状态映射
    STATUS_MAP = {
        "[ ]": "pending",
        "[~]": "in_progress",
        "[x]": "completed"
    }

    # 任务模式（匹配表格中的任务行）
    TASK_PATTERN = re.compile(
        r'\|\s*([\[~x ])\]\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
    )

    # 章节标题模式
    SECTION_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$')

    def __init__(self, spec_path: str):
        self.spec_path = Path(spec_path)
        self.content = ""
        self.tasks: List[Task] = []
        self.current_phase = ""
        self.current_section = ""
        self.task_counter = 0

    def load(self) -> bool:
        """加载规格文档"""
        if not self.spec_path.exists():
            print(f"错误：规格文档不存在: {self.spec_path}")
            return False
        self.content = self.spec_path.read_text(encoding="utf-8")
        return True

    def parse(self) -> List[Task]:
        """解析规格文档，提取所有任务"""
        lines = self.content.split("\n")

        in_table = False
        table_headers = []

        for line in lines:
            # 检测章节标题
            section_match = self.SECTION_PATTERN.match(line)
            if section_match:
                self.current_section = section_match.group(2)
                # 更新 phase（用于阶段 0-8）
                if "阶段" in self.current_section or "阶段" in line:
                    self.current_phase = self.current_section
                continue

            # 检测表格开始/结束
            if line.strip().startswith("|") and line.strip().endswith("|"):
                if not in_table:
                    in_table = True
                    # 下一行是分隔符，跳过
                    continue
                # 解析任务行
                task = self._parse_task_line(line)
                if task:
                    self.tasks.append(task)
            else:
                in_table = False

        return self.tasks

    def _parse_task_line(self, line: str) -> Optional[Task]:
        """解析单行任务"""
        match = self.TASK_PATTERN.match(line)
        if not match:
            return None

        checkbox, title, file_path, hours, acceptance = match.groups()

        # 跳过标题行
        if "任务" in title and "文件" in file_path:
            return None

        # 解析状态
        status = self.STATUS_MAP.get(checkbox.strip(), "pending")

        # 生成任务 ID
        self.task_counter += 1
        task_id = f"task-{self.task_counter:03d}"

        # 解析依赖（从描述或当前阶段推断）
        dependencies = self._infer_dependencies(title, file_path)

        return Task(
            id=task_id,
            title=title.strip(),
            file=file_path.strip(),
            status=status,
            phase=self.current_phase or "未分类",
            dependencies=dependencies,
            acceptance_criteria=acceptance.strip(),
            estimated_hours=int(hours.strip()) if hours.strip().isdigit() else 0
        )

    def _infer_dependencies(self, title: str, file_path: str) -> List[str]:
        """根据文件路径推断依赖关系"""
        # 简单的依赖推断：根据文件路径的层次结构
        deps = []

        # 例如：src/core/query_engine/xxx.py 依赖 src/core/types.py
        if "query_engine" in file_path:
            deps = ["task-001"]  # 假设 types.py 是 task-001
        elif "ingestion" in file_path:
            deps = ["task-001", "task-002"]  # 依赖 libs 层

        return deps

    def save_index(self, output_path: str) -> bool:
        """保存任务索引"""
        output_file = Path(output_path) / "task_index.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        index = {
            "spec_file": str(self.spec_path),
            "total_tasks": len(self.tasks),
            "completed": sum(1 for t in self.tasks if t.status == "completed"),
            "in_progress": sum(1 for t in self.tasks if t.status == "in_progress"),
            "pending": sum(1 for t in self.tasks if t.status == "pending"),
            "tasks": [t.to_dict() for t in self.tasks]
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        print(f"✅ 任务索引已生成: {output_file}")
        print(f"   总任务数: {index['total_tasks']}")
        print(f"   已完成: {index['completed']}")
        print(f"   进行中: {index['in_progress']}")
        print(f"   待开始: {index['pending']}")

        return True

    def split_sections(self, output_dir: str) -> bool:
        """按章节拆分规格文档"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        lines = self.content.split("\n")
        current_section_lines = []
        section_number = 0
        current_file = None

        for line in lines:
            section_match = self.SECTION_PATTERN.match(line)
            if section_match:
                level = len(section_match.group(1))
                title = section_match.group(2)

                # 一级或二级章节
                if level <= 2 and current_section_lines:
                    # 保存上一章节
                    if current_file:
                        self._save_section(current_file, current_section_lines)

                    section_number += 1
                    current_file = output_path / f"{section_number:02d}-{self._slugify(title)}.md"
                    current_section_lines = [line]
                else:
                    current_section_lines.append(line)
            else:
                current_section_lines.append(line)

        # 保存最后一章
        if current_file and current_section_lines:
            self._save_section(current_file, current_section_lines)

        print(f"✅ 已拆分 {section_number} 个章节到: {output_dir}")
        return True

    def _save_section(self, file_path: Path, lines: List[str]):
        """保存章节内容"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @staticmethod
    def _slugify(text: str) -> str:
        """将文本转换为文件名友好的格式"""
        # 转小写，替换空格和特殊字符为连字符
        slug = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text.lower())
        return slug.strip('-')


def main():
    parser = argparse.ArgumentParser(description="同步规格文档并生成任务索引")
    parser.add_argument("--spec", default="devspec.md", help="规格文档路径（默认 devspec.md）")
    parser.add_argument("--output", default="specs", help="输出目录（默认 specs/）")
    parser.add_argument("--no-split", action="store_true", help="不拆分章节")

    args = parser.parse_args()

    print(f"📖 解析规格文档: {args.spec}")

    spec_parser = SpecParser(args.spec)
    if not spec_parser.load():
        return 1

    # 解析任务
    tasks = spec_parser.parse()
    print(f"📋 提取到 {len(tasks)} 个任务")

    # 生成任务索引
    spec_parser.save_index(args.output)

    # 拆分章节
    if not args.no_split:
        spec_parser.split_sections(args.output)

    return 0


if __name__ == "__main__":
    exit(main())
