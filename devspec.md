# 技术规格文档 (devspec.md)

> **RAG + MCP 智能问答与知识检索框架**

---

## 目录

- [项目概述](#项目概述)
- [核心特点](#核心特点)
  - [RAG 策略与设计亮点](#rag-策略与设计亮点)
  - [全链路可插拔架构](#全链路可插拔架构)
  - [MCP 生态集成](#mcp-生态集成)
  - [多模态图像处理](#多模态图像处理)
  - [可观测性与可评估体系](#可观测性与可评估体系)
  - [业务可扩展性](#业务可扩展性)
- [技术选型](#技术选型)
  - [1. 数据摄取流水线](#1-数据摄取流水线)
  - [2. 检索流水线](#2-检索流水线)
  - [3. MCP 服务设计](#3-mcp-服务设计)
  - [4. 可插拔架构设计](#4-可插拔架构设计)
  - [5. 可观测性与追踪设计](#5-可观测性与追踪设计)
  - [6. 多模态图片处理设计](#6-多模态图片处理设计)
  - [7. 测试方案](#7-测试方案)
- [系统架构与模块设计](#系统架构与模块设计)
- [项目开发排期](#项目开发排期)

---

# 项目概述

项目基于 RAG 与 MCP，目标是搭建一个可扩展、高可观测、易迭代的智能问答与知识检索框架。

## 核心特点

### RAG 策略与设计亮点

**分块策略：智能分块与上下文增强**
- **智能分块**：摒弃机械的定长切分，采用语义感知的切分策略以保证完整语义。
- **上下文增强**：为 chunk 注入文档元数据（标题、页码）和图片描述，确保检索时不仅匹配文本，还能感知上下文。

**粗排召回：混合检索**
- 结合**稀疏检索**（BM25）利用关键词精确匹配，解决专有名词查找问题。
- 结合**稠密检索**（语义向量）利用语义向量，解决同义词与模糊表达问题。
- 两者互补，通过 RRF 算法融合，确保查全率与查准率的平衡。

**精排重排**
- 采用 Cross-Encoder（专用重排模型）或 LLM Rerank 对候选集进行逐一打分，识别细微的语义差异。

### 全链路可插拔架构

**LLM 调用层可插拔**
- 核心推理 LLM 通过统一的抽象接口封装，支持多协议无缝切换：
  - Azure OpenAI：企业级 Azure 云端服务，符合合规与安全要求。
  - OpenAI API：直接对接 OpenAI 官方接口。
  - 本地部署：支持 Ollama、vLLM 等本地私有化部署方案。
  - 其他云服务：DeepSeek、Anthropic Claude、Zhipu 等第三方 API。
- 通过配置文件一键切换后端，零代码修改完成 LLM 迁移。

**Embedding & Rerank 可插拔**
- Embedding 模型与 Rerank 模型同样采用统一接口封装。
- 支持云端服务和本地服务自由切换。

**RAG Pipeline 组件可插拔**
- Loader（解析器）：支持 PDF、Markdown、Code 等多文档解析器独立替换。
- Smart Splitter（切分策略）：语义切分、定长切分、递归策略可配置。
- Transformation（元数据/图文增强逻辑）：OCR、Image Caption 等增强模块可独立配置。

**检索策略可插拔**
- 支持动态配置纯向量、纯关键词或混合检索模式。
- 支持灵活更换向量数据库后端（如从 Chroma 迁移至 Qdrant、Milvus）。

**评估体系可插拔**
- 评估模块不锁定单一指标，支持挂载不同的 Evaluator（如 Ragas、DeepEval）。

### MCP 生态集成

项目的设计核心完全遵循 MCP 标准，使得项目不仅是一个独立的问答服务，更是一个即插即用的知识上下文提供者。

**工作原理**
- Server 作为 MCP Server 运行，提供一组标准的 tools 和 resources 接口。
- MCP Clients（如 GitHub Copilot、Research Agent、Claude Desktop 等）可以直接连接到这个 Server。
- 无缝接入：当在 GitHub Copilot 中提问时，Copilot 作为一个 MCP Host，能够自动发现并调用 Server 提供的工具。

**优势**
- 无需前端开发，可直接复用 ChatUI 和 AI 助手。
- 上下文互通：Copilot 可以同时看到代码文件和知识库内容。

### 多模态图像处理

图像采用 Multi-Embedding 多模态向量策略，支持图→图、文→图、图→文的跨模态检索。

### 可观测性与可评估体系

避免黑盒问题，本项目致力于让每一次生成过程都透明可见且可量化。

**全链路白盒化**
- 记录并可视化 RAG 流水线的每一个中间状态：从 Query 改写，到 Hybrid Search 的初步召回列表，再到 Reranker 重新排序，最后到 LLM 的 Prompt 构建。
- 开发者可以清晰看到系统为什么选了这个文档以及 Rerank 起了什么作用，从而精确定位 Bad Case。

**自动化评估闭环**
- 集成 Ragas 等评估框架，为每一次检索和生成计算"体检报告"（召回率、准确率等指标）。
- 拒绝凭感觉调优，建立基于数据的迭代反馈回路，确保每一次策略调整都有量化分数支撑。

### 业务可扩展性

本项目采用通用化架构设计，不仅是一个开箱即用的知识问答系统，更是一个可以快速适配各类业务场景的扩展基座。

---

# 技术选型
## RAG 核心流水线设计

### 1. 数据摄取流水线
#### 目标
构建统一、可配置、可观测的数据导入与分块能力，覆盖文档加载，格式解析、语义切分、多模态增强、嵌入计算、去重与批量上载到向量存储。该能力应是多重用的库模块。

- langchain&langgraph

#### 设计要点
- 明确分层职责：
  - loader：负责吧原始文件解析为统一的document对象(text+metadata)。当前阶段，仅实现pdf格式的loader/
    - 统一输出格式采用规范化markdown作为document.txt。可以更好的配合split。

    - loader同时抽取/补充metadata（如source_path、doc_type=pdf、page、title、/heading_outline、images饮用列表等），为定位、回溯或后续transform提供依据。

  - spiltter:基于markdown结构，将doc切分为若干chunk，保留原始位置与上下文引用。

  - transform：对原始文档（如图片、代码、网页等）进行内容提取和标准化处理。通过可插入的模块（如 ImageCaptioning为图片生成描述、OCR识别文字、清理 HTML 标签等），将非结构化数据转为纯文本。处理后的信息可以追加到文本内容（chunk.text），或存入元数据（chunk.metadata）。

  - embed & upset:按批计算embedding，并上载到向量存储；支持向量+metadata上载，并提供幂等upsert策略（基于id/hash）.

  - dedup & normalize:在上载前运行向量/文本去重与哈希过滤，避免重复索引。

#### 关键实现
- loader
  - 前置去重（early exit/file integrity check）:
    - 机制：解析文件前，计算原始文件的sha256哈希指纹。
    - 动作：检索“ingestion_history”表，若发现相同hash且状态为'success'的记录，则认定该文件未发生改变，直接跳过后续所有处理（解析、切分、llm重写）。

  - 解析与标准化
    - 当前范围：仅实现pdf->canonical markdown子集的转换。

  - 技术选型（python pdf->markdown）
    - 首选：markltdown(作为默认pdf解析/转换引擎)。有点事直接产出markdown形态文本，便于后续操作。
    - 标准输出document：
    id|source|text(markdown)|metadata。metadata至少包含source_path,doc_type,title/heading_outline,page/slide（如适用）images(图片引用列表)。
    - loader不负责切分：只做格式统一+结构抽取+引用收集。

- splitter
  - 实现方案：用kangchain的RecursiveCharacterTextSplitter进行切分。
    - 优势：该方法对markdown文档的结构（标题，段落，列表，代码块）有天然的适配行，能通过配置语义断点实现高质量、语义完整的切块。
    - splitter 输入：loader产出的markdown document。
    - splitter 输出：若干chunk，每个chunk必须携带稳定的定位信息与来源信息：source，chunk_index,start_offset/end_offset。

- transform & enrichment
负责接splitter产出的非线形结构转换成结构化、富语义的智能切片。
  - 结构转换：string->record/object。
  - 核心增强策略：
    - 智能重组
      - 策略：利用llm语义的理解能力，对上一阶段“粗切分”的片段二次加工。
      - 动作：合并在逻辑上紧密相关但是被物理切断的段落，提出无意义的页眉页脚或乱码（去燥），取保每个chunk是自包含的语义单元。
    - 语义元数据注入：
      - 策略：在基础元数据（路径、页码）之上，利用llm提取高维语义特征。
      - 产出：为每个chunk自动生成title（精确小标题），summary（内容摘要）和tags（主题标签），并将其注入到metadata字段中，支持后续的混合检索和精确过滤。
    - 多模态增强：
      - 策略：扫描文档片段中的图像引用，调用vllm进行试掘理解。
      - 动作：生成高保真的文本描述（caption），描述图表逻辑或提取截图文字。
      - 存储：将caption文本“缝合”进chunk的征文或metadata中，打通模态隔阂，实现文搜图。
  - 工程特性：transform步骤设计为原子化与幂等操作，支持针对特定chunk的独立重试与增量更新，避免因llm调用而导致整个文档处理中断。

- embedding 双路向量化
  - 差量计算：
    - 策略：在调用embedding api之前，计算chunk的内容哈希（content hash）。仅针对数据库中不存在的新内容哈希执行向量化计算，对文件名更变但是内容未变的片段，直接服用已有向量。
    - 核心策略：为了支持高精度的混合检索，系统对每个chunk并行执行双路编码计算。
      - dense embedding：调用embedding模型生成向量捕捉语义关联。
      - sparse embedidng：利用bm25编码器或者splade模型生成系数向量，捕捉精确的关键词匹配信息，解决专有名词查找问题。
    - 批处理优化。

- upsert & storage
  - 存储后端：milvus。
  - all-in-one策略：包含index data(用于计算相似度的稠密向量稀疏向量)、payload data（完整的chunk原始文本及metadata）。
  - 幂等性设计：
    - 为每个chunk生成全局唯一的chunk_id，生成算法采用确定的哈希组合：hash（source_path+section_path+content_hash）。
    - 写入时词啊用upsert语义，确保同一文档即使被多次处理，数据库中也永远只有一份最新的副本。
  - 原子性：以batch为单位进行事务性写入。


### 2. 检索流水线
采用多阶段过滤架构。
- 查询预处理
  - 核心假设：输入query已由上游(client/mcp host)完成会话上下文补全（de-referencing）,不仅如此，还进行了指代消歧。
  - 查询转换与扩张策略：
    - keyword extraction：利用nlp工具提取query中的关键实体与动词（去停用词），生成用于稀疏检索的token列表。
    - query expansion：
      - 系统可做同名次、别名、缩写扩展，默认策略采用扩展融入稀疏检索、稠密检索保持单次以控制成本与复杂度。
      - sparse route（BM25）:将关键词+同义词/别名合并为一个查询表达式（逻辑上按'or'扩展），只执行一次稀疏检索。原始关键词可赋予更高权重以抑制语义漂移。
      - dense route:使用原始query（或轻度改写后的语义query），只进行一次稠密检索。默认不为每个同义词单独触发额外的向量检索请求。

- 混合检索扩展
  - 并行召回：采用rrf（reciprocal rank fusion）算法，不依赖各路分数的绝对值，而是基于排名的倒数进行加权融合。公式策略：Score=1/(k+Rank_Dense)+1/(k+Rank Sparse),平滑因单一模态缺陷导致的漏召回。

- filter & reranking
  - metadata filter strategy:
    - 原则：先解析、能前置就前置。无法前置则后置兜底。
    - 若底层索引支持且属于硬约束，则在dense/sparse检索阶段做pre-filter以缩小候选集、降低成本。
    - 无法前置的过滤（索引不支持或字段缺失/质量不稳）在rerank之前做，对缺失字段默认宽松包含，以避免误杀召回。
    - 软偏好（例如：更近期更好）不应硬过滤，而应作为排序信号在融合/重排序阶段加权。
  - rerank backend（可插拔精排后端）
    - 目标：模块必须可关闭，并提供稳定的回退策略。
    - 后端选项：
      - none：直接返回融合后的top-k
      - cross-encoder rerank:输入为[query,chunk]，输出相关性分数并排序。提供超时回退。
      - llm rerank：使用llm对候选集排序。


### 3. MCP 服务设计
目标：设计一个符合mcp规范的server，使其能够作为知识上下文提供者，无缝对接主流mcp clients，用户可通过现有的ai助手即可查询私有知识库。

### 核心设计理念
- 协议优先：遵循mcp官方规范 json-rpc 2.0
- 开箱即用
- 引用透明
- 多模态友好

### 传输协议：stdio本地通信
采用stdio transport作为唯一通信模式。
- 工作方式：client（vscode copilot 、 claude desktop）以子进程方式启动server，通过json-rpc交换消息。
- 选型理由：
  - 零配置：无需网络端口、无需鉴权，用户只需在client配置文件中制定命令即可使用。
  - 隐私安全：数据不经过网络。
- 实现约束：
  - stdout仅输出合法mcp消息，禁止混入任何日志和调试信息。
  - 日志统一输出至stderr，避免污染通信环境。

### sdk与实现库选型
- 首选python官方mcp sdk
- 备选：fastapi+自定义协议层

### 对外暴露工具函数设计
- 核心工具

| 工具名称 | 功能描述 | 典型输入参数 | 输出特点 |
|---------|----------|--------------|----------|
| query_knowledge_hub | 主检索入口，执行混合检索 + Rerank，返回最相关片段 | `query: string`<br>`top_k?: int`<br>`collection?: string` | 返回带引用的结构化结果 |
| list_collections | 列举知识库中可用的文档集合 | 无 | 集合名称、描述、文档数量 |
| get_document_summary | 获取指定文档的摘要与元信息 | `doc_id: string` | 标题、摘要、创建时间、标签 |

- 扩展工具（agentic演进方向）
  - search_by_keyword/search_by_semantic:拆分独立的检索策略，供 Agent 自主选择。
  - verify_answer:事实核查工具，检测生成内容是否有依据支撑。
  - list document sections :浏览文档目录结构，支持多步.

### 返回内容与引用透明设计
mcp协议的tool返回格式支持多种内容类型（content数组），本项目将充分利用这一特性实现可溯源的回答。
- 结构化引用设计：
  - 每个检索结果片段应包含完整的定位信息：source_file（文件名/路径）、page（页码，如适用）、chunk_id（片段标识）、score（相关性分数）。
  - 推荐在返回的 structuredContent 中采用统一的 Citation 格式：
```python
 {
   "answer": "...",
   "citations": [
     { "id": 1, "source": "xxx.pdf", "page": 5, "text": "原文片段...", "score": 0.92 },
     ...
   ]
 }
```
  - 同时在 content 数组中以 Markdown 格式呈现人类可读的带引用回答（[1] 标注），保证 Client 无论是否解析结构化内容都能展示引用。

- 多模态内容返回：

  - 文本内容 (TextContent)：默认返回类型，Markdown 格式，支持代码块、列表等富文本。
  - 图像内容 (ImageContent)：当检索结果关联图像时，Server 读取本地图片文件并编码为 Base64 返回。
    - 格式：{ "type": "image", "data": "<base64>", "mimeType": "image/png" }
    - 工作流程：数据摄取阶段存储图片本地路径 → 检索命中后 Server 动态读取 → 编码为 Base64 → 嵌入返回消息。
    - Client 兼容性：图像展示能力取决于 Client 实现，GitHub Copilot 可能降级处理，Claude Desktop 支持完整渲染。Server 端统一返回 Base64 格式，由 Client 决定如何渲染。



### 4. 可插拔架构设计
目标： 定义清晰的抽象层与接口契约，使 RAG 链路的每个核心组件都能够独立替换与升级，避免技术锁定，支持低成本的 A/B 测试与环境迁移。
```bash
术语说明：本节中的"提供者 (Provider)"、"实现 (Implementation)"指的是完成某项功能的具体技术方案，而非传统 Web 架构中的"后端服务器"。例如，LLM 提供者可以是远程的 Azure OpenAI API，也可以是本地运行的 Ollama；向量存储可以是本地嵌入式的 Chroma，也可以是云端托管的 Pinecone。本项目作为本地 MCP Server，通过统一接口对接这些不同的提供者，实现灵活切换。
```
### 设计原则
- 接口隔离 (Interface Segregation)：为每类组件定义最小化的抽象接口，上层业务逻辑仅依赖接口而非具体实现。
- 配置驱动 (Configuration-Driven)：通过统一配置文件（如 settings.yaml）指定各组件的具体后端，代码无需修改即可切换实现。
- 工厂模式 (Factory Pattern)：使用工厂函数根据配置动态实例化对应的实现类，实现"一处配置，处处生效"。
- 优雅降级 (Graceful Fallback)：当首选后端不可用时，系统应自动回退到备选方案或安全默认值，保障可用性。
通用结构示意：
```bash
业务代码
  │
  ▼
<Component>Factory.get_xxx()  ← 读取配置，决定用哪个实现
  │
  ├─→ ImplementationA()
  ├─→ ImplementationB()  
  └─→ ImplementationC()
      │
      ▼
    都实现了统一的抽象接口
```

### LLM 与 Embedding 提供者抽象
这是可插拔设计的核心环节，因为模型提供者的选择直接影响成本、性能与隐私合规。
- 统一接口层 (Unified API Abstraction)：
  - 设计思路：无论底层使用 Azure OpenAI、OpenAI 原生 API、DeepSeek 还是本地 Ollama，上层调用代码应保持一致。
  - 关键抽象：
    - LLMClient：暴露 chat(messages) -> response 方法，屏蔽不同 Provider 的认证方式与请求格式差异。
    - EmbeddingClient：暴露 embed(texts) -> vectors 方法，统一处理批量请求与维度归一化。
- 技术选型建议：对于企业级需求，可在其基础上增加统一的 重试、限流、日志 中间层，提升生产可靠性。
- Vision LLM 扩展：针对图像描述生成（Image Captioning）需求，系统扩展了 BaseVisionLLM 接口，支持文本+图片的多模态输入。当前实现：
  - Azure OpenAI Vision（GPT-4o/GPT-4-Vision）：企业级合规部署，支持复杂图表解析，与 Azure 生态深度集成。

### 检索策略抽象
检索层的可插拔性决定了系统在不同数据规模与查询模式下的适应能力。
设计模式：抽象工厂模式

### 评估框架抽象
- 设计思路
  - 定义统一的 Evaluator 接口，暴露 evaluate(query, retrieved_chunks, generated_answer, ground_truth) -> metrics 方法。
  - 各评估框架实现该接口，输出标准化的指标字典。
  - RAG 评估框架对比

| 框架 | 特点 | 适用场景 |
|------|------|----------|
| Ragas | RAG 专用，指标丰富（Faithfulness、Answer Relevancy、Context Precision 等） | 全面评估 RAG 质量、学术对比 |
| DeepEval | LLM-as-Judge 模式，支持自定义评估标准 | 需要主观质量判断、复杂业务规则 |
| 自定义指标 | Hit Rate、MRR、Latency P99 等基础工程指标 | 快速回归测试、上线前 Sanity Check |

  - 组合与扩展：
    - 评估模块设计为组合模式，可同时挂载多个 Evaluator，生成综合报告。
    - 配置示例：evaluation.backends: [ragas, custom_metrics]，系统并行执行并汇总结果。
### 配置管理与切换流程
- 配置文件结构示例 (config/settings.yaml)：
```yaml
 llm:
   provider: azure  # azure | openai | ollama | deepseek
   model: gpt-4o
   # provider-specific configs...
 
 embedding:
   provider: openai
   model: text-embedding-3-small
 
 vector_store:
   backend: chroma  # chroma | qdrant | pinecone
 
 retrieval:
   sparse_backend: bm25  # bm25 | elasticsearch
   fusion_algorithm: rrf  # rrf | weighted_sum
   rerank_backend: cross_encoder  # none | cross_encoder | llm
 
 evaluation:
   backends: [ragas, custom_metrics]
```


### 5. 可观测性与追踪设计
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

### 6. 多模态图片处理设计
- 目标： 设计一套完整的图片处理方案，使 RAG 系统能够理解、索引并检索文档中的图片内容，实现"用自然语言搜索图片"的能力，同时保持架构的简洁性与可扩展性。
###  设计理念与策略选型
- 多模态 RAG 的核心挑战在于：如何让纯文本的检索系统"看懂"图片。业界主要有两种技术路线：

| 策略 | 核心思路 | 优势 | 劣势 |
|------|----------|------|------|
| Image-to-Text（图转文） | 利用 Vision LLM 将图片转化为文本描述，复用纯文本 RAG 链路 | 架构统一、实现简单、成本可控 | 描述质量依赖 LLM 能力，可能丢失视觉细节 |
| Multi-Embedding（多模态向量） | 使用 CLIP 等模型将图文统一映射到同一向量空间 | 保留原始视觉特征，支持图搜图 | 需引入额外向量库，架构复杂度高 |
- 本项目采用multi-embedding策略
  - 天然支持：
    - 图 → 图
    - 文 → 图
    - 图 → 文
    - ✅ 对专利 / 工业图 / 外观设计极友好
### 图片处理流程
- 图片处理贯穿 Ingestion Pipeline 的多个阶段，整体流程如下：
```
原始文档 (PDF/PPT/Markdown)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Loader阶段：图片提取与引用收集                           │
│  - 解析文档并提取嵌入图片                                │
│  - 为图片生成唯一 image_id                               │
│  - 插入图片占位符/引用标记                               │
│  - 输出：Document (text + metadata.images[])            │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Splitter阶段：保持图文关联                               │
│  - 切分时保留图片引用标记                                │
│  - 确保图片与上下文段落关联                               │
│  - 输出：Chunks (含 image_refs)                         │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Transform阶段：多模态理解与向量化                        │
│  - 多模态模型联合编码图像与上下文                         │
│  - 生成图像语义向量（可选保留轻量描述/标签）               │
│  - 输出：Enriched Chunks (含图像向量与引用)               │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Storage阶段：双轨存储                                    │
│  - 向量库存储文本向量+图像向量用于检索                    │
│  - 文件系统/Blob存储原始图片                             │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Retrieval阶段：图文联合检索与返回                        │
│  - 用户Query进入混合检索                                  │
│  - 命中含图片的Chunk与引用                                │
│  - 读取原图并Base64编码                                   │
│  - 返回Text+ImageContent+引用                             │
└─────────────────────────────────────────────────────────┘
```
---



### 7. 测试方案
### 设计理念：测试驱动开发 (TDD)
本项目采用**测试驱动开发（Test-Driven Development）**作为核心开发范式，确保每个组件在实现前就已明确其预期行为，通过自动化测试持续验证系统质量。
- 核心原则：
  - 早测试、常测试：每个功能模块实现的同时就编写对应的单元测试，而非事后补测。
  - 测试即文档：测试用例本身就是最准确的行为规范，新加入的开发者可通过阅读测试快速理解各模块功能。
  - 快速反馈循环：单元测试应在秒级完成，支持开发者高频执行，立即发现引入的问题。
  - 分层测试金字塔：大量快速的单元测试作为基座，少量关键路径的集成测试作为保障，极少数端到端测试验证完整流程。
        /\
       /E2E\         <- 少量，验证关键业务流程
      /------\
     /Integration\   <- 中量，验证模块协作
    /------------\
   /  Unit Tests  \  <- 大量，验证单个函数/类
  /________________\

### 测试分层策略

##### 单元测试 (Unit Tests)
目标：验证每个独立组件的内部逻辑正确性，隔离外部依赖。
- 覆盖范围：
| 模块 | 测试重点 | 典型测试用例 |
|------|---------|-------------|
| Loader (文档解析器) | 格式解析、元数据提取、图片引用收集 | - 测试解析单页/多页 PDF<br>- 验证 Markdown 标题层级提取<br>- 检查图片占位符插入位置 |
| Splitter (切分器) | 切分边界、上下文保留、元数据传递 | - 验证按标题切分不破坏段落<br>- 测试超长文本的递归切分<br>- 检查 Chunk 的 source 字段正确性 |
| Transform (增强器) | 图片描述生成、元数据注入 | - Mock Vision LLM，验证描述注入逻辑<br>- 测试无图片时的降级行为<br>- 验证幂等性（重复处理相同输入） |
| Embedding (向量化) | 批处理、差量计算、向量维度 | - 验证相同文本生成相同向量<br>- 测试批量请求的拆分与合并<br>- 检查缓存命中逻辑 |
| BM25 (稀疏编码) | 关键词提取、权重计算 | - 验证停用词过滤<br>- 测试 IDF 计算准确性<br>- 检查稀疏向量格式 |
| Retrieval (检索器) | 召回精度、融合算法 | - 测试纯 Dense/Sparse/Hybrid 三种模式<br>- 验证 RRF 融合分数计算<br>- 检查 Top-K 结果排序 |
| Reranker (重排器) | 分数归一化、降级回退 | - Mock Cross-Encoder，验证分数重排<br>- 测试超时后的 Fallback 逻辑<br>- 验证空候选集处理 |

- 技术选型：
  - 测试框架：pytest（Python 标准选择，支持参数化测试、Fixture 机制）
  - Mock 工具：unittest.mock / pytest-mock（隔离外部依赖，如 LLM API）
  - 断言增强：pytest-check（支持多断言不中断执行）

##### 集成测试 (Integration Tests)
目标：验证多个组件协作时的数据流转与接口兼容性。
| 测试场景 | 验证要点 | 测试策略 |
|---------|---------|---------|
| Ingestion Pipeline | Loader → Splitter → Transform → Storage 的完整流程 | - 使用真实的测试 PDF 文件<br>- 验证最终存入向量库的数据完整性<br>- 检查中间产物（如临时图片文件）是否正确清理 |
| Hybrid Search | Dense + Sparse 召回的融合结果 | - 准备已知答案的查询-文档对<br>- 验证融合后的 Top-1 是否命中正确文档<br>- 测试极端情况（某一路无结果） |
| Rerank Pipeline | 召回 → 过滤 → 重排的组合 | - 验证 Metadata 过滤后的候选集正确性<br>- 检查 Reranker 是否改变了 Top-1 结果<br>- 测试 Reranker 失败时的回退 |
| MCP Server | 工具调用的端到端流程 | - 模拟 MCP Client 发送 JSON-RPC 请求<br>- 验证返回的 content 格式符合协议<br>- 测试错误处理（如查询语法错误） |

- 技术选型：
  - 数据隔离：每个测试使用独立的临时数据库/向量库（pytest-tempdir）
  - 异步测试：pytest-asyncio（若 MCP Server 采用异步实现）
  - 契约测试：定义各模块间的 Schema，确保接口不漂移


##### 端到端测试 (End-to-End Tests)
目标：模拟真实用户操作，验证完整业务流程的可用性。
核心场景：

- 场景 1：数据准备（离线摄取）

  测试目标：验证文档摄取流程的完整性与正确性
  测试步骤：
  准备测试文档（PDF 文件，包含文本、图片、表格等多种元素）
  执行离线摄取脚本，将文档导入知识库
  验证摄取结果：检查生成的 Chunk 数量、元数据完整性、图片描述生成
  验证存储状态：确认向量库和 BM25 索引正确创建
  验证幂等性：重复摄取同一文档，确保不产生重复数据
  验证要点：
  Chunk 的切分质量（语义完整性、上下文保留）
  元数据字段完整性（source、page、title、tags 等）
  图片处理结果（Caption 生成、Base64 编码存储）
  向量与稀疏索引的正确性
  
- 场景 2：召回测试
  测试目标：验证检索系统的召回精度与排序质量
  测试步骤：
  基于已摄取的知识库，准备一组测试查询（包含不同难度与类型）
  执行混合检索（Dense + Sparse + Rerank）
  验证召回结果：检查 Top-K 文档是否包含预期来源
  对比不同检索策略的效果（纯 Dense、纯 Sparse、Hybrid）
  验证 Rerank 的影响：对比重排前后的结果变化
  验证要点：
  Hit Rate@K：Top-K 结果命中率是否达标
  排序质量：正确答案是否排在前列（MRR、NDCG）
  边界情况处理：空查询、无结果查询、超长查询
  多模态召回：包含图片的文档是否能通过文本查询召回

- 场景 3：MCP Client 功能测试

  测试目标：验证 MCP Server 与 Client（如 GitHub Copilot）的协议兼容性与功能完整性
  测试步骤：
  启动 MCP Server（Stdio Transport 模式）
  模拟 MCP Client 发送各类 JSON-RPC 请求
  测试工具调用：query_knowledge_hub、list_collections 等
  验证返回格式：符合 MCP 协议规范（content 数组、structuredContent）
  测试引用透明性：返回结果包含完整的 Citation 信息
  测试多模态返回：包含图片的响应正确编码为 Base64
  验证要点：
  协议合规性：JSON-RPC 2.0 格式、错误码映射
  工具注册：tools/list 返回所有可用工具及其 Schema
  响应格式：TextContent 与 ImageContent 的正确组合
  错误处理：无效参数、超时、服务不可用等异常场景
  性能指标：单次请求的端到端延迟（含检索、重排、格式化）

- 测试工具：
  BDD 框架：behave 或 pytest-bdd（以 Gherkin 语法描述场景）
  环境准备：
  临时测试向量库（独立于生产数据）
  预置的标准测试文档集
  本地 MCP Server 进程（Stdio Transport）


##### RAG 质量评估测试
目标：验证已设计的评估体系是否正确实现，并能有效评估 RAG 系统的召回与生成质量。
- 测试要点：

  - 黄金测试集准备
    构建标准的"问题-答案-来源文档"测试集（JSON 格式）
    初期人工标注核心场景，后期持续积累坏 Case

  - 评估框架实现验证
    验证 Ragas/DeepEval 等评估框架的正确集成
    确认评估接口能输出标准化的指标字典
    测试多评估器并行执行与结果汇总

  - 关键指标达标验证
    检索指标：Hit Rate@K ≥ 90%、MRR ≥ 0.8、NDCG@K ≥ 0.85
    生成指标：Faithfulness ≥ 0.9、Answer Relevancy ≥ 0.85
    定期运行评估，监控指标是否回归
说明：本节重点是验证评估体系的工程实现，而非重新设计评估方法（评估方法的设计见第 3 章技术选型）。


---

# 系统架构与模块设计

## 整体架构图
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     MCP Clients (外部调用层)                                  │
│                                                                                             │
│    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │
│    │  GitHub Copilot │    │  Claude Desktop │    │  其他 MCP Agent │                        │
│    └────────┬────────┘    └────────┬────────┘    └────────┬────────┘                        │
│             │                      │                      │                                 │
│             └──────────────────────┼──────────────────────┘                                 │
│                                    │  JSON-RPC 2.0 (Stdio Transport)                       │
└────────────────────────────────────┼────────────────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MCP Server 层 (接口层)                                     │
│                                                                                             │
│    ┌─────────────────────────────────────────────────────────────────────────────────┐      │
│    │                              MCP Protocol Handler                               │      │
│    │                    (tools/list, tools/call, resources/*)                        │      │
│    └─────────────────────────────────────────────────────────────────────────────────┘      │
│                                           │                                                 │
│    ┌──────────────────────┬───────────────┼───────────────┬──────────────────────┐          │
│    ▼                      ▼               ▼               ▼                      ▼          │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│ │query_knowledge│ │list_collections│ │get_document_ │  │search_by_    │  │  其他扩展    │    │
│ │    _hub      │  │              │  │   summary    │  │  keyword     │  │   工具...    │    │
│ └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Core 层 (核心业务逻辑)                                     │
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                            Query Engine (查询引擎)                                   │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐    │    │
│  │  │                         Query Processor (查询预处理)                         │    │    │
│  │  │            关键词提取 | 查询扩展 (同义词/别名) | Metadata 解析               │    │    │
│  │  └─────────────────────────────────────────────────────────────────────────────┘    │    │
│  │                                       │                                             │    │
│  │  ┌────────────────────────────────────┼────────────────────────────────────┐        │    │
│  │  │                     Hybrid Search Engine (混合检索引擎)                  │        │    │
│  │  │                                    │                                    │        │    │
│  │  │    ┌───────────────────┐    ┌──────┴──────┐    ┌───────────────────┐    │        │    │
│  │  │    │   Dense Route     │    │   Fusion    │    │   Sparse Route    │    │        │    │
│  │  │    │ (Embedding 语义)  │◄───┤    (RRF)    ├───►│   (BM25 关键词)   │    │        │    │
│  │  │    └───────────────────┘    └─────────────┘    └───────────────────┘    │        │    │
│  │  └─────────────────────────────────────────────────────────────────────────┘        │    │
│  │                                       │                                             │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐    │    │
│  │  │                        Reranker (重排序模块) [可选]                          │    │    │
│  │  │          None (关闭) | Cross-Encoder (本地模型) | LLM Rerank               │    │    │
│  │  └─────────────────────────────────────────────────────────────────────────────┘    │    │
│  │                                       │                                             │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐    │    │
│  │  │                      Response Builder (响应构建器)                           │    │    │
│  │  │            引用生成 (Citation) | 多模态内容组装 (Text + Image)               │    │    │
│  │  └─────────────────────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                          Trace Collector (追踪收集器)                                │    │
│  │                   trace_id 生成 | 各阶段耗时记录 | JSON Lines 输出                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Storage 层 (存储层)                                        │
│                                                                                             │
│    ┌─────────────────────────────────────────────────────────────────────────────────┐      │
│    │                             Vector Store (向量存储)                              │      │
│    │                                                                                 │      │
│    │     ┌─────────────────────────────────────────────────────────────────────┐     │      │
│    │     │                         Chroma DB                                   │     │      │
│    │     │    Dense Vector | Sparse Vector | Chunk Content | Metadata          │     │      │
│    │     └─────────────────────────────────────────────────────────────────────┘     │      │
│    └─────────────────────────────────────────────────────────────────────────────────┘      │
│                                                                                             │
│    ┌──────────────────────────────────┐    ┌──────────────────────────────────┐             │
│    │       BM25 Index (稀疏索引)       │    │       Image Store (图片存储)     │             │
│    │        倒排索引 | IDF 统计        │    │    本地文件系统 | Base64 编码     │             │
│    └──────────────────────────────────┘    └──────────────────────────────────┘             │
│                                                                                             │
│    ┌──────────────────────────────────┐    ┌──────────────────────────────────┐             │
│    │     Trace Logs (追踪日志)         │    │   Processing Cache (处理缓存)    │             │
│    │     JSON Lines 格式文件           │    │   文件哈希 | Chunk 哈希 | 状态   │             │
│    └──────────────────────────────────┘    └──────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              Ingestion Pipeline (离线数据摄取)                               │
│                                                                                             │
│    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐   │
│    │   Loader   │───►│  Splitter  │───►│ Transform  │───►│  Embedding │───►│   Upsert   │   │
│    │ (文档解析) │    │  (切分器)  │    │ (增强处理) │    │  (向量化)  │    │  (存储)    │   │
│    └────────────┘    └────────────┘    └────────────┘    └────────────┘    └────────────┘   │
│         │                  │                  │                  │                │         │
│         ▼                  ▼                  ▼                  ▼                ▼         │
│    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐   │
│    │MarkItDown │    │Recursive   │    │LLM重写     │    │Dense:      │    │Chroma      │   │
│    │PDF→MD     │    │Character   │    │Image       │    │OpenAI/BGE  │    │Upsert      │   │
│    │元数据提取 │    │TextSplitter│    │Captioning  │    │Sparse:BM25 │    │幂等写入    │   │
│    └────────────┘    └────────────┘    └────────────┘    └────────────┘    └────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                Libs 层 (可插拔抽象层)                                        │
│                                                                                             │
│    ┌────────────────────────────────────────────────────────────────────────────────┐       │
│    │                            Factory Pattern (工厂模式)                           │       │
│    └────────────────────────────────────────────────────────────────────────────────┘       │
│                                           │                                                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │
│  │ LLM Client │ │ Embedding  │ │  Splitter  │ │VectorStore │ │  Reranker  │ │ Evaluator  │  │
│  │  Factory   │ │  Factory   │ │  Factory   │ │  Factory   │ │  Factory   │ │  Factory   │  │
│  ├────────────┤ ├────────────┤ ├────────────┤ ├────────────┤ ├────────────┤ ├────────────┤  │
│  │ · Azure    │ │ · OpenAI   │ │ · Recursive│ │ · Chroma   │ │ · None     │ │ · Ragas    │  │
│  │ · OpenAI   │ │ · BGE      │ │ · Semantic │ │ · Qdrant   │ │ · CrossEnc │ │ · DeepEval │  │
│  │ · Ollama   │ │ · Ollama   │ │ · FixedLen │ │ · Pinecone │ │ · LLM      │ │ · Custom   │  │
│  │ · DeepSeek │ │ · ...      │ │ · ...      │ │ · ...      │ │            │ │            │  │
│  │ · Vision✨ │ │            │ │            │ │            │ │            │ │            │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                             Observability 层 (可观测性)                                      │
│                                                                                             │
│    ┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐     │
│    │          Trace Context               │    │         Web Dashboard                │     │
│    │   trace_id | stages[] | metrics      │    │        (Streamlit)                   │     │
│    │   record_stage() | finish()          │    │    请求列表 | 耗时瀑布图 | 详情展开   │     │
│    └──────────────────────────────────────┘    └──────────────────────────────────────┘     │
│                                                                                             │
│    ┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐     │
│    │          Evaluation Module           │    │         Structured Logger            │     │
│    │   Hit Rate | MRR | Faithfulness      │    │    JSON Formatter | File Handler     │     │
│    └──────────────────────────────────────┘    └──────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

## 目录结构
smart-knowledge-hub/
│
├── config/                              # 配置文件目录
│   ├── settings.yaml                    # 主配置文件 (LLM/Embedding/VectorStore 配置)
│   └── prompts/                         # Prompt 模板目录
│       ├── image_captioning.txt         # 图片描述生成 Prompt
│       ├── chunk_refinement.txt         # Chunk 重写 Prompt
│       └── rerank.txt                   # LLM Rerank Prompt
│
├── src/                                 # 源代码主目录
│   │
│   ├── mcp_server/                      # MCP Server 层 (接口层)
│   │   ├── __init__.py
│   │   ├── server.py                    # MCP Server 入口 (Stdio Transport)
│   │   ├── protocol_handler.py          # JSON-RPC 协议处理
│   │   └── tools/                       # MCP Tools 定义
│   │       ├── __init__.py
│   │       ├── query_knowledge_hub.py   # 主检索工具
│   │       ├── list_collections.py      # 列出集合工具
│   │       └── get_document_summary.py  # 文档摘要工具
│   │
│   ├── core/                            # Core 层 (核心业务逻辑)
│   │   ├── __init__.py
│   │   ├── settings.py                   # 配置加载与校验 (Settings：load_settings/validate_settings)
│   │   ├── types.py                      # 核心数据类型/契约（Document/Chunk/ChunkRecord），供 ingestion/retrieval/mcp 复用
│   │   │
│   │   ├── query_engine/                # 查询引擎模块
│   │   │   ├── __init__.py
│   │   │   ├── query_processor.py       # 查询预处理 (关键词提取/查询扩展)
│   │   │   ├── hybrid_search.py         # 混合检索引擎 (Dense + Sparse + RRF)
│   │   │   ├── dense_retriever.py       # 稠密向量检索
│   │   │   ├── sparse_retriever.py      # 稀疏检索 (BM25)
│   │   │   ├── fusion.py                # 结果融合 (RRF 算法)
│   │   │   └── reranker.py              # 重排序模块 (None/CrossEncoder/LLM)
│   │   │
│   │   ├── response/                    # 响应构建模块
│   │   │   ├── __init__.py
│   │   │   ├── response_builder.py      # 响应构建器
│   │   │   ├── citation_generator.py    # 引用生成器
│   │   │   └── multimodal_assembler.py  # 多模态内容组装 (Text + Image)
│   │   │
│   │   └── trace/                       # 追踪模块
│   │       ├── __init__.py
│   │       ├── trace_context.py         # 追踪上下文 (trace_id/stages)
│   │       └── trace_collector.py       # 追踪收集器
│   │
│   ├── ingestion/                       # Ingestion Pipeline (离线数据摄取)
│   │   ├── __init__.py
│   │   ├── pipeline.py                  # Pipeline 主流程编排 (支持 on_progress 回调)
│   │   ├── document_manager.py          # 文档生命周期管理 (list/delete/stats)
│   │   │
│   │   ├── chunking/                    # Chunking 模块 (文档切分)
│   │   │   ├── __init__.py
│   │   │   └── document_chunker.py      # Document → Chunks 转换（调用 libs.splitter）
│   │   │
│   │   ├── transform/                   # Transform 模块 (增强处理)
│   │   │   ├── __init__.py
│   │   │   ├── base_transform.py        # Transform 抽象基类
│   │   │   ├── chunk_refiner.py         # Chunk 智能重组/去噪
│   │   │   ├── metadata_enricher.py     # 语义元数据注入 (Title/Summary/Tags)
│   │   │   └── image_captioner.py       # 图片描述生成 (Vision LLM)
│   │   │
│   │   ├── embedding/                   # Embedding 模块 (向量化)
│   │   │   ├── __init__.py
│   │   │   ├── dense_encoder.py         # 稠密向量编码
│   │   │   ├── sparse_encoder.py        # 稀疏向量编码 (BM25)
│   │   │   └── batch_processor.py       # 批处理优化
│   │   │
│   │   └── storage/                     # Storage 模块 (存储)
│   │       ├── __init__.py
│   │       ├── vector_upserter.py       # 向量库 Upsert
│   │       ├── bm25_indexer.py          # BM25 索引构建
│   │       └── image_storage.py         # 图片文件存储
│   │
│   ├── libs/                            # Libs 层 (可插拔抽象层)
│   │   ├── __init__.py
│   │   │
│   │   ├── loader/                      # Loader 抽象 (文档加载)
│   │   │   ├── __init__.py
│   │   │   ├── base_loader.py           # Loader 抽象基类
│   │   │   ├── pdf_loader.py            # PDF Loader (MarkItDown)
│   │   │   └── file_integrity.py        # 文件完整性检查 (SHA256 哈希)
│   │   │
│   │   ├── llm/                         # LLM 抽象
│   │   │   ├── __init__.py
│   │   │   ├── base_llm.py              # LLM 抽象基类
│   │   │   ├── llm_factory.py           # LLM 工厂
│   │   │   ├── azure_llm.py             # Azure OpenAI 实现
│   │   │   ├── openai_llm.py            # OpenAI 实现
│   │   │   ├── ollama_llm.py            # Ollama 本地模型实现
│   │   │   ├── deepseek_llm.py          # DeepSeek 实现
│   │   │   ├── base_vision_llm.py       # Vision LLM 抽象基类（支持图像输入）
│   │   │   └── azure_vision_llm.py      # Azure Vision 实现 (GPT-4o/GPT-4-Vision)
│   │   │
│   │   ├── embedding/                   # Embedding 抽象
│   │   │   ├── __init__.py
│   │   │   ├── base_embedding.py        # Embedding 抽象基类
│   │   │   ├── embedding_factory.py     # Embedding 工厂
│   │   │   ├── openai_embedding.py      # OpenAI Embedding 实现
│   │   │   ├── azure_embedding.py       # Azure Embedding 实现
│   │   │   └── ollama_embedding.py      # Ollama 本地模型实现
│   │   │
│   │   ├── splitter/                    # Splitter 抽象 (切分策略)
│   │   │   ├── __init__.py
│   │   │   ├── base_splitter.py         # Splitter 抽象基类
│   │   │   ├── splitter_factory.py      # Splitter 工厂
│   │   │   ├── recursive_splitter.py    # RecursiveCharacterTextSplitter 实现
│   │   │   ├── semantic_splitter.py     # 语义切分实现
│   │   │   └── fixed_length_splitter.py # 定长切分实现
│   │   │
│   │   ├── vector_store/                # VectorStore 抽象
│   │   │   ├── __init__.py
│   │   │   ├── base_vector_store.py     # VectorStore 抽象基类
│   │   │   ├── vector_store_factory.py  # VectorStore 工厂
│   │   │   └── chroma_store.py          # Chroma 实现
│   │   │
│   │   ├── reranker/                    # Reranker 抽象
│   │   │   ├── __init__.py
│   │   │   ├── base_reranker.py         # Reranker 抽象基类
│   │   │   ├── reranker_factory.py      # Reranker 工厂
│   │   │   ├── cross_encoder_reranker.py# CrossEncoder 实现
│   │   │   └── llm_reranker.py          # LLM Rerank 实现
│   │   │
│   │   └── evaluator/                   # Evaluator 抽象
│   │       ├── __init__.py
│   │       ├── base_evaluator.py        # Evaluator 抽象基类
│   │       ├── evaluator_factory.py     # Evaluator 工厂
│   │       ├── ragas_evaluator.py       # Ragas 实现
│   │       └── custom_evaluator.py      # 自定义指标实现
│   │
│   └── observability/                   # Observability 层 (可观测性)
│       ├── __init__.py
│       ├── logger.py                    # 结构化日志 (JSON Formatter)
│       ├── dashboard/                   # Web Dashboard (可视化管理平台)
│       │   ├── __init__.py
│       │   ├── app.py                   # Streamlit 入口 (页面导航注册)
│       │   ├── pages/                   # 六大功能页面
│       │   │   ├── overview.py          # 系统总览 (组件配置 + 数据统计)
│       │   │   ├── data_browser.py      # 数据浏览器 (文档/Chunk/图片查看)
│       │   │   ├── ingestion_manager.py # Ingestion 管理 (触发摄取/删除文档)
│       │   │   ├── ingestion_traces.py  # Ingestion 追踪 (摄取历史与详情)
│       │   │   ├── query_traces.py      # Query 追踪 (查询历史与详情)
│       │   │   └── evaluation_panel.py  # 评估面板 (运行评估/查看指标)
│       │   └── services/                # Dashboard 数据服务层
│       │       ├── trace_service.py     # Trace 读取服务 (解析 traces.jsonl)
│       │       ├── data_service.py      # 数据浏览服务 (ChromaStore/ImageStorage)
│       │       └── config_service.py    # 配置读取服务 (Settings 展示)
│       └── evaluation/                  # 评估模块
│           ├── __init__.py
│           ├── eval_runner.py           # 评估执行器
│           ├── ragas_evaluator.py       # Ragas 评估实现
│           └── composite_evaluator.py   # 组合评估器 (多后端并行)

│
├── data/                                # 数据目录
│   ├── documents/                       # 原始文档存放
│   │   └── {collection}/                # 按集合分类
│   ├── images/                          # 提取的图片存放
│   │   └── {collection}/                # 按集合分类（实际存储在 {doc_hash}/ 子目录下）
│   └── db/                              # 数据库与索引文件目录
│       ├── ingestion_history.db         # 文件完整性历史记录 (SQLite)
│       │                                # 表结构：file_hash, file_path, status, processed_at, error_msg
│       │                                # 用途：增量摄取，避免重复处理未变更文件
│       ├── image_index.db               # 图片索引映射 (SQLite)
│       │                                # 表结构：image_id, file_path, collection, doc_hash, page_num
│       │                                # 用途：快速查询 image_id → 本地文件路径，支持图片检索与引用
│       ├── chroma/                      # Chroma 向量库目录
│       │                                # 存储 Dense Vector、Sparse Vector 与 Chunk Metadata
│       └── bm25/                        # BM25 索引目录
│                                        # 存储倒排索引与 IDF 统计信息（当前使用 pickle）
│
├── cache/                               # 缓存目录
│   ├── embeddings/                      # Embedding 缓存 (按内容哈希)
│   ├── captions/                        # 图片描述缓存
│   └── processing/                      # 处理状态缓存 (文件哈希/Chunk 哈希)
│
├── logs/                                # 日志目录
│   ├── traces.jsonl                     # 追踪日志 (JSON Lines)
│   └── app.log                          # 应用日志
│
├── tests/                               # 测试目录
│   ├── unit/                            # 单元测试
│   │   ├── test_dense_retriever.py      # D2: 稠密检索器测试
│   │   ├── test_sparse_retriever.py     # D3: 稀疏检索器测试
│   │   ├── test_fusion_rrf.py           # D4: RRF 融合测试
│   │   ├── test_reranker_fallback.py    # D6: Reranker 回退测试
│   │   ├── test_protocol_handler.py     # E2: 协议处理器测试
│   │   ├── test_response_builder.py     # E3: 响应构建器测试
│   │   ├── test_list_collections.py     # E4: 集合列表工具测试
│   │   ├── test_get_document_summary.py # E5: 文档摘要工具测试
│   │   ├── test_trace_context.py        # F1: 追踪上下文测试
│   │   ├── test_jsonl_logger.py         # F2: JSON Lines 日志测试
│   │   └── ...                          # 其他已有单元测试
│   ├── integration/                     # 集成测试
│   │   ├── test_ingestion_pipeline.py
│   │   ├── test_hybrid_search.py        # D5: 混合检索集成测试
│   │   └── test_mcp_server.py           # E1-E6: MCP 服务器集成测试
│   ├── e2e/                             # 端到端测试
│   │   ├── test_data_ingestion.py
│   │   ├── test_recall.py               # G2: 召回回归测试
│   │   └── test_mcp_client.py           # G1: MCP Client 模拟测试
│   └── fixtures/                        # 测试数据
│       ├── sample_documents/
│       └── golden_test_set.json         # F5/G2: 黄金测试集
│
├── scripts/                             # 脚本目录
│   ├── ingest.py                        # 数据摄取脚本（离线摄取入口）
│   ├── query.py                         # 查询测试脚本（在线查询入口）
│   ├── evaluate.py                      # 评估运行脚本
│   └── start_dashboard.py               # Dashboard 启动脚本
│
├── main.py                              # MCP Server 启动入口
├── pyproject.toml                       # Python 项目配置
├── requirements.txt                     # 依赖列表
└── README.md                            # 项目说明


# 项目开发排期

> **规格驱动开发 (SDD) 计划**
> 基于本详细技术规格文档制定
> 最后更新: 2026-02-20

---

## 项目概要

| 项目 | 说明 |
| :--- | :--- |
| **目标** | 构建一个可扩展、高可观测、易迭代的 RAG + MCP 智能问答与知识检索框架 |
| **技术栈** | Python + LangChain/LangGraph + MCP Protocol + Chroma + 多种 LLM/Embedding |
| **预计总工时** | 约 80-120 小时（个人开发） |

---

## 开发原则

1. **规格驱动**: 严格按照本文档执行，不偏离设计
2. **测试驱动 (TDD)**: 每个模块先写测试，再写实现
3. **接口优先**: 先定义抽象接口，再实现具体类
4. **渐进增强**: 每个阶段产生可运行的增量版本
5. **可观测优先**: 从第一天开始就记录 trace

---

## 阶段划分


### 阶段 0: 项目基础设施 (Day 1)

**目标**: 搭建项目骨架，配置开发环境

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
| :--- | :--- | :--- | :--- | :--- |
| [x] | 创建目录结构 | 按规格创建完整目录 | 1h | 所有目录存在 |
| [x] | 配置项目管理 | pyproject.toml, requirements.txt | 1h | 可 pip install |
| [x] | 配置文件 | config/settings.yaml (模板) | 1h | 结构符合 spec |
| [x] | 测试框架 | pytest 配置, tests/fixtures/ | 1h | pytest 可运行 |

**里程碑 M0**: `python -m pytest` 可正常运行

---


### 阶段 1: Libs 层 - 可插拔抽象 (Day 2-5)

**目标**: 实现所有核心抽象层和工厂模式

#### 1.1 核心数据类型 (优先级: 最高)

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | 配置加载器 | src/core/settings.py | 2h | 可加载YAML |
| [ ] | 核心类型定义 | src/core/types.py | 2h | Document/Chunk类可用 |
| [ ] | 单元测试 | tests/unit/test_settings.py, test_types.py | 2h | 测试通过 |

#### 1.2 LLM 抽象 (优先级: 高)

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | LLM抽象基类 | src/libs/llm/base_llm.py | 2h | chat()方法定义 |
| [ ] | Vision LLM抽象 | src/libs/llm/base_vision_llm.py | 1h | 支持图片输入 |
| [ ] | LLM工厂 | src/libs/llm/llm_factory.py | 1h | 根据config实例化 |
| [ ] | Azure OpenAI实现 | src/libs/llm/azure_llm.py | 3h | 可调用GPT-4 |
| [ ] | OpenAI实现 | src/libs/llm/openai_llm.py | 2h | 可调用OpenAI |
| [ ] | Azure Vision实现 | src/libs/llm/azure_vision_llm.py | 3h | 可识别图片 |
| [ ] | 单元测试 | tests/unit/test_*llm.py | 3h | Mock测试通过 |

#### 1.3 Embedding 抽象 (优先级: 高)

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Embedding抽象 | src/libs/embedding/base_embedding.py | 1h | embed()方法定义 |
| [ ] | Embedding工厂 | src/libs/embedding/embedding_factory.py | 1h | 根据config实例化 |
| [ ] | OpenAI实现 | src/libs/embedding/openai_embedding.py | 2h | 可生成向量 |
| [ ] | 单元测试 | tests/unit/test_*embedding.py | 2h | 测试通过 |

#### 1.4 VectorStore 抽象 (优先级: 高)

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | VectorStore抽象 | src/libs/vector_store/base_vector_store.py | 2h | upsert/query方法 |
| [ ] | VectorStore工厂 | src/libs/vector_store/vector_store_factory.py | 1h | 根据config实例化 |
| [ ] | Chroma实现 | src/libs/vector_store/chroma_store.py | 4h | 可存储/检索向量 |
| [ ] | 单元测试 | tests/unit/test_chroma_store.py | 2h | 测试通过 |

#### 1.5 Splitter 抽象 (优先级: 中)

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Splitter抽象 | src/libs/splitter/base_splitter.py | 1h | split()方法定义 |
| [ ] | Splitter工厂 | src/libs/splitter/splitter_factory.py | 1h | 根据config实例化 |
| [ ] | Recursive实现 | src/libs/splitter/recursive_splitter.py | 3h | 可切分Markdown |
| [ ] | 单元测试 | tests/unit/test_recursive_splitter.py | 2h | 测试通过 |

#### 1.6 Reranker 抽象 (优先级: 中)

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Reranker抽象 | src/libs/reranker/base_reranker.py | 1h | rerank()方法定义 |
| [ ] | Reranker工厂 | src/libs/reranker/reranker_factory.py | 1h | 根据config实例化 |
| [ ] | None实现 | src/libs/reranker/none_reranker.py | 1h | 返回原排序 |
| [ ] | 单元测试 | tests/unit/test_*reranker.py | 2h | 测试通过 |

#### 1.7 Loader 抽象 (优先级: 中)

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Loader抽象 | src/libs/loader/base_loader.py | 1h | load()方法定义 |
| [ ] | 文件完整性检查 | src/libs/loader/file_integrity.py | 2h | SHA256哈希 |
| [ ] | PDF Loader | src/libs/loader/pdf_loader.py | 4h | MarkItDown集成 |
| [ ] | 单元测试 | tests/unit/test_pdf_loader.py | 2h | 测试通过 |

**里程碑 M1**: 所有 Libs 层模块通过单元测试，工厂模式可正确实例化

---


### 阶段 2: Ingestion Pipeline (Day 6-9)

**目标**: 实现离线数据摄取流程

#### 2.1 Chunking 模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Document Chunker | src/ingestion/chunking/document_chunker.py | 3h | Document→Chunks |
| [ ] | 单元测试 | tests/unit/test_document_chunker.py | 2h | 测试通过 |

#### 2.2 Transform 模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Transform抽象 | src/ingestion/transform/base_transform.py | 1h | transform()方法 |
| [ ] | Chunk Refiner | src/ingestion/transform/chunk_refiner.py | 3h | LLM重写chunk |
| [ ] | Metadata Enricher | src/ingestion/transform/metadata_enricher.py | 3h | 提取title/summary |
| [ ] | Image Captioner | src/ingestion/transform/image_captioner.py | 4h | Vision LLM描述图片 |
| [ ] | 单元测试 | tests/unit/test_transform*.py | 3h | Mock测试通过 |

#### 2.3 Embedding 模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Dense Encoder | src/ingestion/embedding/dense_encoder.py | 2h | 调用Embedding API |
| [ ] | Sparse Encoder | src/ingestion/embedding/sparse_encoder.py | 3h | BM25编码 |
| [ ] | Batch Processor | src/ingestion/embedding/batch_processor.py | 2h | 批处理优化 |
| [ ] | 单元测试 | tests/unit/test_*encoder.py | 2h | 测试通过 |

#### 2.4 Storage 模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Vector Upserter | src/ingestion/storage/vector_upserter.py | 3h | 批量upsert |
| [ ] | BM25 Indexer | src/ingestion/storage/bm25_indexer.py | 3h | 构建倒排索引 |
| [ ] | Image Storage | src/ingestion/storage/image_storage.py | 2h | 图片文件存储 |
| [ ] | 单元测试 | tests/unit/test_*storage.py | 2h | 测试通过 |

#### 2.5 Pipeline 主流程

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Pipeline | src/ingestion/pipeline.py | 4h | 编排全流程 |
| [ ] | Document Manager | src/ingestion/document_manager.py | 2h | list/delete |
| [ ] | 摄取脚本 | scripts/ingest.py | 1h | CLI入口 |
| [ ] | 集成测试 | tests/integration/test_ingestion_pipeline.py | 3h | 端到端测试 |

**里程碑 M2**: 可执行 `python scripts/ingest.py` 导入PDF文档

---


### 阶段 3: Query Engine (Day 10-13)

**目标**: 实现混合检索引擎

#### 3.1 Query Processor

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Query Processor | src/core/query_engine/query_processor.py | 3h | 关键词提取/查询扩展 |
| [ ] | 单元测试 | tests/unit/test_query_processor.py | 2h | 测试通过 |

#### 3.2 Retrieval 模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Dense Retriever | src/core/query_engine/dense_retriever.py | 3h | 向量检索 |
| [ ] | Sparse Retriever | src/core/query_engine/sparse_retriever.py | 3h | BM25检索 |
| [ ] | Fusion (RRF) | src/core/query_engine/fusion.py | 3h | RRF融合 |
| [ ] | Hybrid Search | src/core/query_engine/hybrid_search.py | 4h | 编排检索流程 |
| [ ] | 单元测试 | tests/unit/test_*retriever.py, test_fusion.py | 3h | 测试通过 |
| [ ] | 集成测试 | tests/integration/test_hybrid_search.py | 2h | 端到端测试 |

#### 3.3 Reranker 模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Reranker实现 | src/core/query_engine/reranker.py | 2h | 调用Reranker抽象 |
| [ ] | 单元测试 | tests/unit/test_reranker_fallback.py | 2h | 回退测试通过 |

**里程碑 M3**: 可执行 `python scripts/query.py` 进行检索

---


### 阶段 4: Response & Trace (Day 14-15)

**目标**: 实现响应构建和追踪

#### 4.1 Response 模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Citation Generator | src/core/response/citation_generator.py | 2h | 生成引用 |
| [ ] | Multimodal Assembler | src/core/response/multimodal_assembler.py | 3h | 组装图文 |
| [ ] | Response Builder | src/core/response/response_builder.py | 3h | 构建最终响应 |
| [ ] | 单元测试 | tests/unit/test_response_builder.py | 2h | 测试通过 |

#### 4.2 Trace 模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Trace Context | src/core/trace/trace_context.py | 3h | 记录阶段 |
| [ ] | Trace Collector | src/core/trace/trace_collector.py | 2h | JSON Lines输出 |
| [ ] | 单元测试 | tests/unit/test_trace_context.py, test_jsonl_logger.py | 2h | 测试通过 |

**里程碑 M4**: 查询结果包含完整引用和trace

---


### 阶段 5: Observability 基础 (Day 16-17)

**目标**: 实现日志和评估基础

#### 5.1 Logger 模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | 结构化Logger | src/observability/logger.py | 2h | JSON Formatter |

#### 5.2 Evaluation 模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Evaluator抽象 | src/libs/evaluator/base_evaluator.py | 1h | evaluate()方法 |
| [ ] | Evaluator工厂 | src/libs/evaluator/evaluator_factory.py | 1h | 根据config实例化 |
| [ ] | Ragas实现 | src/libs/evaluator/ragas_evaluator.py | 3h | Ragas集成 |
| [ ] | Custom实现 | src/libs/evaluator/custom_evaluator.py | 2h | 自定义指标 |
| [ ] | Composite Evaluator | src/observability/evaluation/composite_evaluator.py | 2h | 多评估器组合 |
| [ ] | Eval Runner | src/observability/evaluation/eval_runner.py | 2h | 执行评估 |
| [ ] | 评估脚本 | scripts/evaluate.py | 1h | CLI入口 |

**里程碑 M5**: 可执行 `python scripts/evaluate.py` 运行评估

---


### 阶段 6: MCP Server (Day 18-20)

**目标**: 实现 MCP 协议层

#### 6.1 MCP 核心模块

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Protocol Handler | src/mcp_server/protocol_handler.py | 4h | JSON-RPC 2.0处理 |
| [ ] | Server入口 | src/mcp_server/server.py | 2h | Stdio Transport |
| [ ] | main.py | main.py | 1h | 启动入口 |

#### 6.2 MCP Tools

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | query_knowledge_hub | src/mcp_server/tools/query_knowledge_hub.py | 3h | 主检索工具 |
| [ ] | list_collections | src/mcp_server/tools/list_collections.py | 2h | 列集合工具 |
| [ ] | get_document_summary | src/mcp_server/tools/get_document_summary.py | 2h | 文档摘要工具 |
| [ ] | 单元测试 | tests/unit/test_*tools.py | 2h | 测试通过 |
| [ ] | 集成测试 | tests/integration/test_mcp_server.py | 3h | MCP协议测试 |

**里程碑 M6**: 可作为 MCP Server 启动，响应 tools/list 和 tools/call

---


### 阶段 7: Dashboard (Day 21-24)

**目标**: 实现 Streamlit 可视化面板

#### 7.1 Dashboard Services

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Trace Service | src/observability/dashboard/services/trace_service.py | 2h | 读取traces.jsonl |
| [ ] | Data Service | src/observability/dashboard/services/data_service.py | 2h | 读取向量库 |
| [ ] | Config Service | src/observability/dashboard/services/config_service.py | 1h | 读取配置 |

#### 7.2 Dashboard Pages (并行开发)

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | Overview | src/observability/dashboard/pages/overview.py | 2h | 系统总览 |
| [ ] | Data Browser | src/observability/dashboard/pages/data_browser.py | 3h | 数据浏览 |
| [ ] | Ingestion Manager | src/observability/dashboard/pages/ingestion_manager.py | 3h | 摄取管理 |
| [ ] | Ingestion Traces | src/observability/dashboard/pages/ingestion_traces.py | 2h | 摄取追踪 |
| [ ] | Query Traces | src/observability/dashboard/pages/query_traces.py | 2h | 查询追踪 |
| [ ] | Evaluation Panel | src/observability/dashboard/pages/evaluation_panel.py | 3h | 评估面板 |

#### 7.3 Dashboard App

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | App入口 | src/observability/dashboard/app.py | 2h | 页面导航 |
| [ ] | 启动脚本 | scripts/start_dashboard.py | 1h | CLI入口 |

**里程碑 M7**: 可执行 `python scripts/start_dashboard.py` 打开面板

---


### 阶段 8: 测试与优化 (Day 25-27)

**目标**: 完善测试覆盖，性能优化

#### 8.1 E2E 测试

| 状态 | 任务 | 文件 | 工时 | 验收标准 |
|------|------|------|------|----------|
| [ ] | 数据摄取E2E | tests/e2e/test_data_ingestion.py | 3h | 完整流程 |
| [ ] | 召回E2E | tests/e2e/test_recall.py | 2h | 召回测试 |
| [ ] | MCP Client | tests/e2e/test_mcp_client.py | 3h | 模拟客户端 |

#### 8.2 优化与文档

| 状态 | 任务 | 工时 | 验收标准 |
|------|------|------|----------|
| [ ] | 性能优化 | 4h | 满足性能指标 |
| [ ] | README完善 | 2h | 文档完整 |
| [ ] | 配置示例 | 1h | 提供示例配置 |

**里程碑 M8**: 所有测试通过，文档完整

---

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

## 依赖关系总览

```
阶段0 (基础设施)
    │
    ▼
阶段1 (Libs层) ←─ 可并行开发7个子模块
    │
    ├─┬─► 阶段2 (Ingestion)  依赖: LLM, Embedding, VectorStore, Splitter, Loader
    │ │
    │ └─┬─► 阶段3 (Query Engine)  依赖: Embedding, VectorStore, Reranker
    │   │
    │   └─┬─► 阶段4 (Response & Trace)
    │     │
    │     ├─┬─► 阶段5 (Observability)  依赖: Trace
    │     │ │
    │     │ └─┬─► 阶段6 (MCP Server)  依赖: Query Engine, Response, Trace
    │     │   │
    │     │   └─┬─► 阶段7 (Dashboard)  依赖: Observability
    │     │     │
    │     │     └─┬─► 阶段8 (测试与优化)
    │     │       │
    └─────┴───────┴──────► Skills创建 (与各阶段并行)
```

---

## 进度跟踪

| 阶段 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| 阶段0 | 🟡 进行中 | - | 基础设施 |
| 阶段1 | ⬜ 待开始 | - | Libs层 |
| 阶段2 | ⬜ 待开始 | - | Ingestion |
| 阶段3 | ⬜ 待开始 | - | Query Engine |
| 阶段4 | ⬜ 待开始 | - | Response & Trace |
| 阶段5 | ⬜ 待开始 | - | Observability |
| 阶段6 | ⬜ 待开始 | - | MCP Server |
| 阶段7 | ⬜ 待开始 | - | Dashboard |
| 阶段8 | ⬜ 待开始 | - | 测试与优化 |

**图例**: ⬜ 待开始 | 🟡 进行中 | ✅ 已完成

---

## 验收标准总结

### 功能验收
| 状态 | 验收项 |
|------|--------|
| [ ] | 可导入PDF文档并正确分块 |
| [ ] | 可执行混合检索(Dense+Sparse+RRF) |
| [ ] | 可通过MCP协议调用 |
| [ ] | 可在Dashboard中查看数据和trace |
| [ ] | 可运行评估并查看指标 |

### 质量验收
| 状态 | 验收项 |
|------|--------|
| [ ] | 单元测试覆盖率 ≥ 80% |
| [ ] | 所有集成测试通过 |
| [ ] | E2E测试通过 |
| [ ] | 代码符合本文档设计 |

### 性能验收
| 状态 | 验收项 |
|------|--------|
| [ ] | Hit Rate@K ≥ 90% |
| [ ] | MRR ≥ 0.8 |
| [ ] | 单次查询延迟 ≤ 3s (不含LLM生成) |

---

## 备注

1. **工时估算**: 基于个人开发，实际可能因经验水平有所调整
2. **Skills创建**: 建议在对应阶段完成后立即创建，边开发边优化
3. **测试策略**: 严格遵循TDD，先写测试再写实现
4. **可观测性**: 从阶段1开始就应记录trace，不要等到最后
5. **配置管理**: 所有可配置项都应在 settings.yaml 中

---

*此排期文档将随着开发进展持续更新*

