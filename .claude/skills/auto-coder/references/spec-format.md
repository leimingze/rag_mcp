# 规格文档格式规范

## 概述

本文档定义了规格文档（如 `devspec.md`）的格式规范，确保自动代码生成工具能够正确解析任务信息。

## 任务表格格式

规格文档中的任务应使用 Markdown 表格格式，每一行代表一个任务：

```markdown
| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | 配置加载器 | src/core/settings.py | 2h | 可加载YAML |
| [x] | 核心类型定义 | src/core/types.py | 2h | Document/Chunk类可用 |
```

## Checkbox 状态定义

| Checkbox | 状态 | 说明 |
|----------|------|------|
| `[ ]` | pending | 未开始 |
| `[~]` | in_progress | 进行中 |
| `[x]` | completed | 已完成 |

## 章节结构

规格文档应按层级章节组织：

```markdown
# 一级标题
## 二级标题（阶段）
### 三级标题（子模块）
```

## 任务提取规则

1. **表格识别**：以 `|` 开头和结尾的行被视为表格行
2. **跳过标题行**：包含 "任务" 和 "文件" 的行被视为标题行
3. **状态解析**：从第一列提取 checkbox 状态
4. **文件路径**：文件路径列指定源代码文件位置

## 章节拆分输出

运行 `sync_spec.py` 后，规格文档将按章节拆分为：

```
specs/
├── 01-overview.md
├── 02-tech-stack.md
├── 03-architecture.md
└── ...
```

## 任务索引格式

`specs/task_index.json` 格式：

```json
{
  "spec_file": "devspec.md",
  "total_tasks": 100,
  "completed": 10,
  "in_progress": 2,
  "pending": 88,
  "tasks": [
    {
      "id": "task-001",
      "title": "配置加载器",
      "file": "src/core/settings.py",
      "status": "pending",
      "phase": "1.1 核心数据类型",
      "dependencies": [],
      "description": "",
      "acceptance_criteria": "可加载YAML",
      "estimated_hours": 2
    }
  ]
}
```

## 依赖关系推断

依赖关系根据文件路径层次自动推断：

- `src/core/query_engine/xxx.py` → 依赖 `src/core/types.py`
- `src/ingestion/xxx.py` → 依赖 `src/libs/llm/*`, `src/libs/embedding/*`
- `src/mcp_server/xxx.py` → 依赖 `src/core/*`

## 示例

完整的任务表格示例：

```markdown
### 1.1 核心数据类型

| 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|----------|
| [ ] 配置加载器 | src/core/settings.py | 2h | 可加载YAML |
| [ ] 核心类型定义 | src/core/types.py | 2h | Document/Chunk类可用 |
| [ ] 单元测试 | tests/unit/test_settings.py, test_types.py | 2h | 测试通过 |
```

## 注意事项

1. **表格格式**：确保表格列对齐，使用正确的 Markdown 语法
2. **文件路径**：使用相对于项目根目录的路径
3. **工时格式**：使用数字 + `h` 后缀（如 `2h`）
4. **状态一致**：状态应在 devspec.md 和 task_index.json 中保持一致
