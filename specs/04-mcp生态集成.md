## mcp生态集成
项目的设计核心完全遵循mcp标准，使得项目不仅是一个独立的问答服务，更是一个即插即用的知识上下文提供者。
- 工作原理
  - 我们的server作为mcpserver运行，提供一组标准的tools和resources接口。
  - mcp clients（如github copilot、research agent、claude desktop等）可以直接连接到这个server。
  - 无缝接入：当即在github copilot中提问时，copilot作为一个mcp host，能够自动发现并调用我们的server提供的工具。
- 优势
  - 另前端开发，可直接服用chatui和ai助手
  - 上下文互通：copilot可以同时看到代码文件和知识库内容。
