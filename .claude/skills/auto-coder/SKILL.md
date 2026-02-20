---
name: auto-coder
description: Autonomous code generation agent for spec-driven development. Use when user says "auto code", "auto dev", "自动开发", "自动写代码", "autopilot", "一键开发" or wants to automatically implement tasks from a specification document like devspec.md. Reads spec, selects next task, generates code + tests, runs tests with auto-fix (max 3 rounds), updates spec status, documents completion, and optionally commits to git.
---

# Auto-Coder

自主代码生成 Agent，基于规格文档自动实现功能、生成测试、执行验证。

## 触发关键词

当用户使用以下关键词时触发此技能：
- `auto code`, `auto dev`, `autopilot`, `一键开发`
- `自动开发`, `自动写代码`, `自主开发`
- `next task`, `implement task`, `continue development`

## 参数说明

用户可附加参数：
- `--task-id <id>`: 指定任务 ID（不指定则自动选择下一个）
- `--no-commit`: 跳过 git commit
- `--spec <path>`: 指定规格文档路径（默认 devspec.md）

## Pipeline 工作流程

### 1. Sync Spec（同步规格）

使用 `scripts/sync_spec.py` 解析规格文档：

```bash
python3 scripts/sync_spec.py --spec devspec.md --output specs/
```

**功能**：
- 按章节拆分规格文档（如 01-overview.md, 02-tech-stack.md）
- 提取所有 checkbox 任务（`[ ]` 未开始, `[~]` 进行中, `[x]` 已完成）
- 生成任务索引 JSON（`specs/task_index.json`）

**输出结构**：
```json
{
  "tasks": [
    {
      "id": "phase1-1-1",
      "title": "配置加载器",
      "file": "src/core/settings.py",
      "status": "pending",
      "phase": "1.1 核心数据类型",
      "dependencies": []
    }
  ]
}
```

### 2. Find Task（查找任务）

使用 `scripts/find_task.py` 选择下一个任务：

```bash
python3 scripts/find_task.py --task-id <id> --index specs/task_index.json
```

**选择策略**：
1. 若指定 `--task-id`，直接返回该任务
2. 否则按优先级选择：
   - 优先选择 `[~]`（进行中）的任务
   - 其次选择 `[ ]`（未开始）且依赖已满足的任务
3. 检查依赖：所有 `dependencies` 中的任务状态为 `[x]` 才可开始

**输出**：任务详情 JSON

### 3. Implement（实现任务）

使用 `scripts/implement.py` 生成代码和测试：

```bash
python3 scripts/implement.py --task <task_json> --spec-dir specs/
```

**实现步骤**：
1. 读取相关技术规范（architecture、tech stack、testing）
2. 生成文件列表计划
3. 创建目录结构
4. 生成代码文件（遵循代码标准）
5. 生成对应测试文件

**代码标准**（强制执行）：
- 类型注解：所有函数必须包含参数和返回值类型注解
- Docstring：Google 风格 docstring
- 配置驱动：从 `config/settings.yaml` 读取配置
- 单一职责：每个类/函数只做一件事
- 错误处理：使用 try-except，记录详细错误信息

### 4. Test & Auto-Fix（测试与修复）

使用 `scripts/test_fix.py` 执行测试并自动修复：

```bash
python3 scripts/test_fix.py --task <task_json> --max-rounds 3
```

**流程**：
1. 激活 venv 环境：`source .venv/bin/activate`
2. 运行测试：`pytest tests/unit/test_<module>.py -v`
3. 若失败，分析错误原因并修复代码
4. 最多 3 轮修复尝试
5. 记录每轮的测试结果和修复内容

**输出**：测试报告 JSON

### 5. Persist（持久化）

使用 `scripts/persist.py` 更新规格文档：

```bash
python3 scripts/persist.py --task <task_json> --spec devspec.md [--commit]
```

**操作**：
1. 更新 devspec.md 中的任务状态：
   - `[ ]` → `[x]`（测试通过）
   - `[ ]` → `[~]`（测试失败但已尝试修复）
2. 更新 `specs/task_index.json`
3. 若 `--commit` 且测试通过：
   - 添加文件到 git
   - 创建原子 commit：`git commit -m "feat(<module>): <task_title>"`
4. 提示用户：`Task completed. Commit created. Next task?`

### 6. Document Completion（文档记录）

使用 `scripts/document.py` 记录任务完成详情：

```bash
python3 scripts/document.py --task <task_json> --spec devspec.md [--dry-run]
```

**功能**：
1. **代码分析**：使用 AST 模块分析创建的文件，提取类/函数信息
2. **测试报告**：读取 `specs/test_report_*.json` 获取测试结果
3. **生成记录**：生成结构化的 Markdown 完成记录
4. **插入文档**：将记录插入到 devspec.md 对应阶段的里程碑前
5. **更新索引**：在 `task_index.json` 中添加 `documented: true` 标记

**记录格式**：
```markdown
<details>
<summary>✅ 任务标题 - 完成详情</summary>

### 任务目标
验收标准描述

### 实现内容
#### 创建的文件
* `src/core/settings.py`

#### 实现的类/函数
* **类**: `Settings`
  * 方法: `load_settings()` -> Dict
  * 方法: `validate_settings()` -> None

### 验收标准验证
* ✅ 测试通过: 3 个测试用例

### 测试方法
```bash
pytest tests/unit/test_settings.py -v
```

**测试轮次**: 1 轮
**测试结果**: ✅ 通过
**通过率**: 100%

### 实现备注
完成时间: 2026-02-20T22:30:00

</details>
```

**幂等性**：重复执行不会产生重复记录，通过检查 `documented` 标记和 devspec.md 中的摘要行判断。

## Guardrails（安全约束）

1. **原子提交**：每个任务一个 commit，消息格式 `feat(<module>): <description>`
2. **Spec 为 SSOT**：devspec.md 是唯一事实源，所有状态从文档读取
3. **venv 环境**：所有 Python/pytest 命令在项目 venv 中执行
4. **依赖检查**：执行前检查前置依赖文件是否存在
5. **自包含**：无外部 skill 依赖，所有脚本独立运行
6. **幂等性**：重复执行同一任务不会产生副作用

## 工作流程图

```
用户触发 (auto code)
    │
    ▼
Sync Spec → 解析 devspec.md → 生成 specs/task_index.json
    │
    ▼
Find Task → 选择下一个未完成任务
    │
    ▼
Implement → 生成代码 + 测试
    │
    ▼
Test & Fix → pytest → 失败? → 修复 (max 3轮)
    │                      │
    │                      ▼
    │                   成功
    ▼
Persist → 更新 devspec.md → [可选] git commit
    │
    ▼
Document → 生成完成记录 → 插入 devspec.md → 更新 task_index.json
    │
    ▼
提示用户 → "Next task?" (继续/停止)
```

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 规格文档不存在 | 提示用户指定正确路径 |
| 无可执行任务（全部完成） | 提示 "All tasks completed!" |
| 无可执行任务（依赖未满足） | 列出阻塞任务 |
| 测试失败（3轮后） | 标记为 `[~]`，记录错误日志 |
| 代码生成失败 | 回滚已创建文件，报告错误 |

## References

- **scripts/sync_spec.py**: 规格文档解析脚本
- **scripts/find_task.py**: 任务选择脚本
- **scripts/implement.py**: 代码生成脚本
- **scripts/test_fix.py**: 测试与修复脚本
- **scripts/persist.py**: 持久化脚本
- **scripts/document.py**: 文档记录脚本（新增）
- **scripts/code_analyzer.py**: 代码分析工具，使用 AST 提取类/函数信息（新增）
- **references/spec-format.md**: 规格文档格式规范
- **references/code-standards.md**: 代码编写标准
