#!/usr/bin/env python3
"""
Test & Fix - 执行测试并自动修复

功能：
1. 在 venv 环境中运行 pytest
2. 分析测试失败原因
3. 自动修复代码
4. 最多 3 轮修复尝试
5. 生成测试报告

用法：
    python3 test_fix.py --task <task_json> [--max-rounds 3]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TestResult:
    """测试结果"""
    round: int
    success: bool
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    fix_attempts: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "round": self.round,
            "success": self.success,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "fix_attempts": self.fix_attempts,
            "timestamp": self.timestamp
        }


class TestRunner:
    """测试运行器"""

    def __init__(self, project_root: str, venv_path: str = ".venv"):
        self.project_root = Path(project_root).resolve()
        self.venv_path = Path(venv_path).resolve()
        self.results: List[TestResult] = []

    def run_tests(self, task: Dict, max_rounds: int = 3) -> bool:
        """运行测试并尝试修复

        Args:
            task: 任务字典
            max_rounds: 最大修复轮数

        Returns:
            测试是否通过
        """
        test_file = self._get_test_file(task["file"])
        if not test_file.exists():
            print(f"⚠️  测试文件不存在: {test_file}")
            return False

        print(f"\n🧪 运行测试: {test_file.name}")
        print(f"   最多尝试 {max_rounds} 轮修复")

        for round_num in range(1, max_rounds + 1):
            print(f"\n{'='*50}")
            print(f"Round {round_num}/{max_rounds}")
            print(f"{'='*50}")

            result = self._run_single_round(test_file, round_num)
            self.results.append(result)

            if result.success:
                print(f"\n✅ 测试通过！")
                self._save_report(task)
                return True

            if round_num < max_rounds:
                print(f"\n🔧 尝试修复...")
                fix_applied = self._attempt_fix(test_file, result, task)
                if not fix_applied:
                    print(f"⚠️  无法自动修复，停止尝试")
                    break
            else:
                print(f"\n❌ 达到最大尝试次数，测试仍未通过")

        self._save_report(task)
        return False

    def _run_single_round(self, test_file: Path, round_num: int) -> TestResult:
        """运行单轮测试"""
        # 激活 venv 并运行 pytest
        pytest_cmd = self._get_pytest_command(test_file)

        try:
            result = subprocess.run(
                pytest_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
        except subprocess.TimeoutExpired:
            print(f"⏱️  测试超时")
            return TestResult(
                round=round_num,
                success=False,
                errors=["Test execution timeout"]
            )
        except FileNotFoundError:
            print(f"❌ pytest 未找到，请确保 venv 已正确配置")
            return TestResult(
                round=round_num,
                success=False,
                errors=["pytest not found"]
            )

        # 解析测试结果
        return self._parse_test_output(result, round_num)

    def _get_pytest_command(self, test_file: Path) -> List[str]:
        """获取 pytest 命令"""
        # 在 venv 中运行 pytest
        if os.name == "nt":  # Windows
            pytest_bin = self.venv_path / "Scripts" / "pytest.exe"
        else:  # Unix-like
            pytest_bin = self.venv_path / "bin" / "pytest"

        return [
            str(pytest_bin),
            str(test_file.relative_to(self.project_root)),
            "-v",
            "--tb=short",
            "--color=yes"
        ]

    def _parse_test_output(self, result: subprocess.CompletedProcess, round_num: int) -> TestResult:
        """解析 pytest 输出"""
        output = result.stdout + result.stderr

        # 解析测试数量
        total_match = re.search(r'(\d+) passed', output)
        failed_match = re.search(r'(\d+) failed', output)
        error_match = re.search(r'(\d+) error', output)

        total = 0
        passed = int(total_match.group(1)) if total_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        errors_count = int(error_match.group(1)) if error_match else 0

        total = passed + failed + errors_count

        # 提取错误信息
        errors = self._extract_errors(output)

        success = result.returncode == 0

        test_result = TestResult(
            round=round_num,
            success=success,
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
            timestamp=datetime.now().isoformat()
        )

        # 打印摘要
        print(f"   总计: {total}, 通过: {passed}, 失败: {failed}")

        if errors:
            print(f"\n   错误:")
            for error in errors[:3]:  # 只显示前 3 个
                print(f"   - {error[:80]}...")

        return test_result

    def _extract_errors(self, output: str) -> List[str]:
        """提取错误信息"""
        errors = []

        # 提取 FAILED 行
        for line in output.split("\n"):
            if line.strip().startswith("FAILED"):
                errors.append(line.strip())
            elif "AssertionError" in line:
                errors.append(line.strip())
            elif "Error:" in line:
                errors.append(line.strip())

        return errors

    def _attempt_fix(self, test_file: Path, result: TestResult, task: Dict) -> bool:
        """尝试修复代码

        注意：这是一个简化版本。实际使用时，应该由 Claude AI 分析错误
        并生成修复后的代码。
        """
        # 这里只做演示，实际应该调用 Claude AI 生成修复代码
        fix_description = f"Attempt to fix {len(result.errors)} errors"
        result.fix_attempts.append(fix_description)

        print(f"   {fix_description}")
        print(f"   ⚠️  自动修复功能需要 Claude AI 集成")

        # 实际实现应该：
        # 1. 读取源文件和测试文件
        # 2. 分析错误原因
        # 3. 调用 Claude AI 生成修复代码
        # 4. 应用修复并保存
        # 5. 返回 True

        return False

    def _get_test_file(self, source_file: str) -> Path:
        """从源文件路径获取测试文件路径"""
        # 例如：src/core/settings.py -> tests/unit/test_settings.py
        parts = Path(source_file).parts
        if "src" in parts:
            idx = parts.index("src")
            test_path = Path("tests") / "/".join(parts[idx+1:])
        else:
            test_path = Path("tests") / "/".join(parts[1:])

        return self.project_root / f"tests/unit/test_{test_path.name}"

    def _save_report(self, task: Dict):
        """保存测试报告"""
        report = {
            "task_id": task["id"],
            "task_title": task["title"],
            "file": task["file"],
            "total_rounds": len(self.results),
            "success": self.results[-1].success if self.results else False,
            "rounds": [r.to_dict() for r in self.results]
        }

        report_file = self.project_root / "specs" / f"test_report_{task['id']}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📄 测试报告已保存: {report_file}")


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


def main():
    parser = argparse.ArgumentParser(description="运行测试并自动修复")
    parser.add_argument("--task", required=True, help="任务 JSON（字符串或文件路径）")
    parser.add_argument("--max-rounds", type=int, default=3, help="最大修复轮数（默认 3）")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--venv", default=".venv", help="虚拟环境路径")

    args = parser.parse_args()

    # 加载任务
    task = load_task(args.task)

    # 运行测试
    runner = TestRunner(args.project_root, args.venv)
    success = runner.run_tests(task, args.max_rounds)

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
