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

