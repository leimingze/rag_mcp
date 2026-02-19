# 项目概述
项目基于rag与mcp，目标是搭建一个可扩展。高观测、易迭代的智能问答与知识检索框架。

# 核心特点
## rag策略与设计亮点
- 分块策略：采用**智能分块**与上下文增强，为高质量检索打下基础。
  - 智能分块：摒弃机械的鼎昌气氛，采用语义感知的切分策略以保证完整语义。
  - 上下文增强：为chunk注入文档元数据（标题、页码）和图片描述，确保检索时不仅匹配文本、还能感知上下文。#TODO:为什么需要感知上下文？
  
  
- 粗排召回：混合检索作为第一阶段快速召回
  - 结合**稀疏检索**利用关键词精确匹配，解决专有名词查找问题。
  - 结合**稠密检索**利用语义向量，解决同义词与模糊表达问题。
  - 两者互补，通过rrf算法融合，确保查全率与查准率的平衡。#TODO:为什么rff能保证查全率和查准率？

- 精排重排：在醋召回的基础上进行语义排序
  - 采用cross-encoder（专用重排模型）或llm rerank对候选集进行逐一打分，识别细微的语义差异。
## 全链路可插拔架构
- LLM调用层可插拔：
  - 核心推理llm通过统一的抽象接口封装，支持多协议无缝切换。
    - azure openai:企业级azure云端服务，符合合规与安全要求。#TODO:azure openai是什么？
    - openai api:直接对接openai官方接口。
    - 本地部署：支持ollama、vllm等本地私有化部署方案。
    - 其他云服务：deepseek、anthropic claude、zhipu 等第三方api。
  - 通过配置文件一键切换后端，零代码修改完成llm迁移。

- embedding & rerank可插拔
  - embedding模型与rerank模型同样采用统一接口封装。
  - 支持云端服务和本地服务自由切换。

- rag pipeline组件可插拔：
  - loader（解析器）：支持pdf、markdown、code等多文档解析器独立替换。
  - smart splitter（切分策略）：语义切分、定长切分、递归策略可配置。
  - transformation（元数据/图文争抢逻辑）：ocr、imagecatpion等增强模块可独立配置。

- 检索策略插拔：
  - 支持动态配置纯向量、纯关键词或混合检索模式。
  - 支持灵活更换向量数据库后端（如从chroma迁移至Qdrant、milvus）。

- 评估体系插拔：
  - 评估模块不锁定单一指标，支持挂载不同的evaluator（如regas,deepeval）。
## mcp生态集成
项目的设计核心完全遵循mcp标准，使得项目不仅是一个独立的问答服务，更是一个即插即用的知识上下文提供者。
- 工作原理
  - 我们的server作为mcpserver运行，提供一组标准的tools和resources接口。
  - mcp clients（如github copilot、research agent、claude desktop等）可以直接连接到这个server。
  - 无缝接入：当即在github copilot中提问时，copilot作为一个mcp host，能够自动发现并调用我们的server提供的工具。
- 优势
  - 另前端开发，可直接服用chatui和ai助手
  - 上下文互通：copilot可以同时看到代码文件和知识库内容。

## 多模态图像处理
图像采用了多模态向量方式。
## 可观测性与可评估体系
避免黑盒问题，本项目致力于让每一次生成过程都透明可见且可量化。
- 全链路白盒化：
  - 记录并可视化rag刘姝贤的每一个中间状态：从query改写，到hybrid search的初步召回列表，再到reranker大粉排序，最后到llm的prompt构建。
  - 开发者可以清晰看到，系统为什么选了这个文档以及rerank起了什么作用，从而精确定位badcase。
- 自动化评估闭环：
  - 集成ragas等评估框架，为每一次检索和生成计算“体检报告”（召回率，准确率等指标）。
  - 拒绝凭感觉调优，建立基于数据的迭代反馈回路，确保每一次策略调整都有量化分数支撑。

## 业务课扩展性
本项目采用通用化架构设计，不仅是一个开箱即用的知识问答系统，更是一个可以快速适配各类业务场景的扩展基座。

# 技术选型
## rag核心流水线设计
### 数据摄取流水线
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
    - 为每个chunk生成全局唯一的chunk_id，生成算法采用确定的哈希组合：hash（source_path+section_path+content_hash）。#TODO:为什么要这么组合？
    - 写入时词啊用upsert语义，确保同一文档即使被多次处理，数据库中也永远只有一份最新的副本。
  - 原子性：以batch为单位进行事务性写入。

### 检索流水线
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
    #TODO:软偏好，硬偏好？
  - rerank backend（可插拔精排后端）
    - 目标：模块必须可关闭，并提供稳定的回退策略。
    - 后端选项：
      - none：直接返回融合后的top-k
      - cross-encoder rerank:输入为[query,chunk]，输出相关性分数并排序。提供超时回退。
      - llm rerank：使用llm对候选集排序。

## mcp服务设计
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


## 可插拔架构设计
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

## 可观测性与追踪设计 (Observability & Tracing Design)
针对 RAG 系统常见的"黑盒"问题，设计全链路可观测的追踪体系，使每一次检索与生成过程都透明可见且可量化，为调试优化与质量评估提供数据基础。
### 设计理念
- 请求级全链路追踪 (Request-Level Tracing)：以 trace_id 为核心，完整记录单次请求从 Query 输入到 Response 输出的全过程，包括各阶段的输入输出、耗时与评估分数。
- 透明可回溯 (Transparent & Traceable)：每个阶段的中间状态都被记录，开发者可以清晰看到"系统为什么召回了这些文档"、"Rerank 前后排名如何变化"，从而精准定位问题。
- 低侵入性 (Low Intrusiveness)：追踪逻辑与业务逻辑解耦，通过装饰器或回调机制注入，避免污染核心代码。
- 轻量本地化 (Lightweight & Local)：采用结构化日志 + 本地 Dashboard 的方案，零外部依赖，开箱即用。
### 追踪数据结构
#TODO:数据追踪
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
## 多模态图片处理设计
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
