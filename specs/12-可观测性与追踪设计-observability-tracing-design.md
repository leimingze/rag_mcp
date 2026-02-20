## 可观测性与追踪设计 (Observability & Tracing Design)
针对 RAG 系统常见的"黑盒"问题，设计全链路可观测的追踪体系，使每一次检索与生成过程都透明可见且可量化，为调试优化与质量评估提供数据基础。
### 设计理念
- 请求级全链路追踪 (Request-Level Tracing)：以 trace_id 为核心，完整记录单次请求从 Query 输入到 Response 输出的全过程，包括各阶段的输入输出、耗时与评估分数。
- 透明可回溯 (Transparent & Traceable)：每个阶段的中间状态都被记录，开发者可以清晰看到"系统为什么召回了这些文档"、"Rerank 前后排名如何变化"，从而精准定位问题。
- 低侵入性 (Low Intrusiveness)：追踪逻辑与业务逻辑解耦，通过装饰器或回调机制注入，避免污染核心代码。
- 轻量本地化 (Lightweight & Local)：采用结构化日志 + 本地 Dashboard 的方案，零外部依赖，开箱即用。
### 追踪数据结构
trace_id：请求唯一标识
timestamp：请求时间戳
user_query：用户原始查询
collection：检索的知识库集合
| 阶段 | 记录内容 |
|------|----------|
| Query Processing | 原始 Query；改写后 Query（若有）；提取的关键词；耗时 |
| Dense Retrieval | 返回的 Top-N 候选及相似度分数；耗时 |
| Sparse Retrieval | 返回的 Top-N 候选及 BM25 分数；耗时 |
| Fusion | 融合后的统一排名；耗时 |
| Rerank | 重排后的最终排名及分数；是否触发 Fallback；耗时 |

- 汇总指标：
  - titak_latency:端到端总耗时
  - top_k_results:最终返回的top-k文档id
  - error：异常信息
- 评估指标：
每次请求可选计算轻量评估分数，记录在trace中。
  - context_relevance:召回文档与qyery的相关性分数。
  - answer_faithfulness:生成答案与召回文档的一致性分数。 
### 技术方案：结构化日志 + 本地 Web Dashboard
本项目采用 "结构化日志 + 本地 Web Dashboard" 作为可观测性的实现方案。

选型理由：

- 零外部依赖：不依赖 LangSmith、LangFuse 等第三方平台，无需网络连接与账号注册，完全本地化运行。
- 轻量易部署：仅需 Python 标准库 + 一个轻量 Web 框架（如 Streamlit），pip install 即可使用，无需 Docker 或数据库服务。
- 学习成本低：结构化日志是通用技能，调试时可直接用 jq、grep 等命令行工具查询；Dashboard 代码简单直观，便于理解与二次开发。
- 契合项目定位：本项目面向本地 MCP Server 场景，单用户、单机运行，无需分布式追踪或多租户隔离等企业级能力。
- 实现架构：
```bash
RAG Pipeline
    │
    ▼
Trace Collector (装饰器/回调)
    │
    ▼
JSON Lines 日志文件 (logs/traces.jsonl)
    │
    ▼
本地 Web Dashboard (Streamlit)
    │
    ▼
按 trace_id 查看各阶段详情与性能指标
```
核心组件：
- 结构化日志层：基于 Python logging + JSON Formatter，将每次请求的 Trace 数据以 JSON Lines 格式追加写入本地文件。每行一条完整的请求记录，包含 trace_id、各阶段详情与耗时。
- 本地 Web Dashboard：基于 Streamlit 构建的轻量级 Web UI，读取日志文件并提供交互式可视化。核心功能是按 trace_id 检索并展示单次请求的完整追踪链路。
### 追踪机制实现
为确保各 RAG 阶段（可替换、可自定义）都能输出统一格式的追踪日志，系统采用 TraceContext（追踪上下文） 作为核心机制。
- 工作原理：
  - 请求开始：Pipeline 入口创建一个 TraceContext 实例，生成唯一 trace_id，记录请求基础信息（Query、Collection 等）。
  - 阶段记录：TraceContext 提供 record_stage() 方法，各阶段执行完毕后调用该方法，传入阶段名称、耗时、输入输出等数据。
  - 请求结束：调用 trace.finish()，TraceContext 将收集的完整数据序列化为 JSON，追加写入日志文件。
- 与可插拔组件配合
  - 各阶段组件（Retriever、Reranker 等）的接口约定中包含 TraceContext 参数。
  - 组件实现者在执行核心逻辑后，调用 trace.record_stage() 记录本阶段的关键信息。
  - 这是显式调用模式：不强制、不会因未调用而报错，但依赖开发者主动记录。好处是代码透明，开发者清楚知道哪些数据被记录；代价是需要开发者自觉遵守约定。

- 阶段划分原则：
  - Stage 是固定的通用大类：retrieval（检索）、rerank（重排）、generation（生成）等，不随具体实现方案变化。
  - 具体实现是阶段内部的细节：在 record_stage() 中通过 method 字段记录采用的具体方法（如 bm25、hybrid），通过 details 字段记录方法相关的细节数据。
  - 这样无论底层方案怎么替换，阶段结构保持稳定，Dashboard 展示逻辑无需调整。

### dashboard功能
dashboard 以trace_id为核心，提供一下视图。
- 请求列表：按时间倒序展示历史请求，支持按 Query 关键词筛选。
- 单请求详情页：
  - 耗时瀑布图：展示各阶段的时间分布，快速定位性能瓶颈。
  - 阶段详情展开：点击任意阶段，查看该阶段的输入、输出与关键参数。
  - 召回结果表：展示 Top-K 候选文档在各阶段的排名与分数变化。
### 配置示例
```yaml
observability:
  enabled: true
  
  # 日志配置
  logging:
    log_file: logs/traces.jsonl  # JSON Lines 格式日志文件
    log_level: INFO  # DEBUG | INFO | WARNING
  
  # 追踪粒度控制
  detail_level: standard  # minimal | standard | verbose
  
  # Dashboard 配置
  dashboard:
    enabled: true
    port: 8501  # Streamlit 默认端口
```