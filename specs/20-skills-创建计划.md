## Skills 创建计划

### Skill 1: `/rag-test` (在阶段1完成后创建)

**用途**: 封装测试相关工作流

**功能**:
- 运行单元测试: `pytest tests/unit/`
- 运行集成测试: `pytest tests/integration/`
- 运行E2E测试: `pytest tests/e2e/`
- 运行所有测试: `pytest`
- 生成覆盖率报告: `pytest --cov`

### Skill 2: `/rag-ingest` (在阶段2完成后创建)

**用途**: 封装数据摄取工作流

**功能**:
- 导入单个文档: `python scripts/ingest.py --file xxx.pdf`
- 导入目录: `python scripts/ingest.py --dir ./data/documents/`
- 列出已导入文档: 调用 document_manager
- 删除文档: 调用 document_manager
- 查看摄取历史: 读取 traces.jsonl

### Skill 3: `/rag-query` (在阶段3完成后创建)

**用途**: 封装查询测试工作流

**功能**:
- 执行查询: `python scripts/query.py --query "xxx"`
- 指定top-k: `python scripts/query.py --query "xxx" --top-k 10`
- 查看trace详情: 读取 traces.jsonl
- 对比不同检索策略

### Skill 4: `/rag-eval` (在阶段5完成后创建)

**用途**: 封装评估工作流

**功能**:
- 运行完整评估: `python scripts/evaluate.py`
- 指定评估集: `python scripts/evaluate.py --dataset xxx.json`
- 生成评估报告: HTML/PDF报告
- 对比历史评估结果

---
