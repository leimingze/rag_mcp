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
    - 为每个chunk生成全局唯一的chunk_id，生成算法采用确定的哈希组合：hash（source_path+section_path+content_hash）。
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
  - rerank backend（可插拔精排后端）
    - 目标：模块必须可关闭，并提供稳定的回退策略。
    - 后端选项：
      - none：直接返回融合后的top-k
      - cross-encoder rerank:输入为[query,chunk]，输出相关性分数并排序。提供超时回退。
      - llm rerank：使用llm对候选集排序。
