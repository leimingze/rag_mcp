# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **RAG (Retrieval-Augmented Generation) + MCP (Model Context Protocol)** framework designed to build an extensible, highly observable, and easy-to-iterate intelligent Q&A and knowledge retrieval system.

**Important:** This project is currently in the **design/specification phase**. The comprehensive technical specification is in `devspec.md` (in Chinese). No implementation code exists yet.

## Technology Stack (Planned)

- **Language:** Python
- **Core Frameworks:** LangChain, LangGraph
- **MCP Protocol:** JSON-RPC 2.0 with stdio transport
- **Vector Stores:** Chroma (primary), Qdrant, Pinecone, Milvus
- **LLM Providers:** Azure OpenAI, OpenAI API, Ollama (local), DeepSeek, Anthropic Claude, Zhipu
- **Embedding Models:** OpenAI, BGE, Ollama (local)
- **Reranking:** Cross-Encoder, LLM-based
- **Evaluation:** Ragas, DeepEval
- **Observability:** Streamlit dashboard, structured JSON logging
- **PDF Processing:** MarkItDown
- **Testing:** pytest, pytest-mock, pytest-asyncio

## High-Level Architecture

The system follows a **layered architecture** with pluggable components:

```
MCP Clients (Copilot, Claude, etc.)
    ↓ JSON-RPC 2.0 (Stdio)
MCP Server Layer (Protocol Handler + Tools)
    ↓
Core Layer (Query Engine + Response + Trace)
    ↓
Storage Layer (Vector Store + BM25 + Images + Logs)
```

### Key Architectural Patterns

1. **Factory Pattern:** All components (LLM, Embedding, VectorStore, Reranker, etc.) use factory pattern for dynamic instantiation based on `config/settings.yaml`

2. **Hybrid Retrieval Strategy:**
   - Dense retrieval (semantic vectors)
   - Sparse retrieval (BM25 keywords)
   - RRF (Reciprocal Rank Fusion) for result merging
   - Optional reranking (Cross-Encoder or LLM-based)

3. **Multi-modal Image Processing:** Uses multi-embedding strategy (CLIP-style) supporting image→image, text→image, image→text retrieval

4. **Observability-First Design:**
   - Request-level tracing with trace_id
   - JSON Lines structured logging (`logs/traces.jsonl`)
   - Streamlit dashboard for visualization

5. **Data Ingestion Pipeline:** Loader → Splitter → Transform → Embedding → Upsert

## Planned Directory Structure

```
smart-knowledge-hub/
├── config/                    # Configuration files
│   ├── settings.yaml         # Main config (LLM/Embedding/VectorStore)
│   └── prompts/              # Prompt templates
├── src/                      # Source code
│   ├── mcp_server/          # MCP Server layer (interface)
│   ├── core/                # Core business logic
│   │   ├── query_engine/   # Query processing & hybrid search
│   │   ├── response/       # Response building & citations
│   │   └── trace/          # Request tracing
│   ├── ingestion/          # Data ingestion pipeline
│   │   ├── chunking/      # Document splitting
│   │   ├── transform/     # Enhancement (LLM rewrite, image captioning)
│   │   ├── embedding/     # Vectorization
│   │   └── storage/       # Vector store upsert
│   ├── libs/              # Pluggable abstraction layer
│   │   ├── loader/        # Document loaders
│   │   ├── llm/           # LLM clients (factory pattern)
│   │   ├── embedding/     # Embedding clients
│   │   ├── splitter/      # Text splitters
│   │   ├── vector_store/  # Vector store abstraction
│   │   ├── reranker/      # Reranking implementations
│   │   └── evaluator/     # Evaluation frameworks
│   └── observability/     # Observability layer
│       ├── dashboard/     # Streamlit web dashboard
│       └── evaluation/    # Evaluation modules
├── data/                   # Data directory
│   ├── documents/         # Original documents
│   ├── images/            # Extracted images
│   └── db/               # Databases (SQLite, Chroma, BM25)
├── cache/                 # Caches (embeddings, captions)
├── logs/                  # Logs (traces.jsonl, app.log)
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/             # End-to-end tests
├── scripts/              # Utility scripts
├── main.py              # MCP Server entry point
└── pyproject.toml       # Python project config
```

## Key Design Principles

1. **Interface Segregation:** Minimal abstractions for each component type
2. **Configuration-Driven:** All component selection via `config/settings.yaml`
3. **Factory Pattern:** Dynamic instantiation based on config
4. **Graceful Fallback:** Automatic fallback to alternatives on failure
5. **Idempotency:** All operations designed to be repeatable safely
6. **Traceability:** Every request fully traceable through the pipeline
7. **Test-Driven Development:** Write tests first, use mocks for external dependencies

## Common Development Commands (Planned)

Once implementation begins:

```bash
# Data ingestion (offline)
python scripts/ingest.py

# Query testing
python scripts/query.py

# Run evaluation
python scripts/evaluate.py

# Start observability dashboard
python scripts/start_dashboard.py

# Start MCP server
python main.py

# Run tests
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/e2e/           # End-to-end tests
```

## Configuration

All components are configured through `config/settings.yaml`:

```yaml
llm:
  provider: azure  # azure | openai | ollama | deepseek
  model: gpt-4o

embedding:
  provider: openai
  model: text-embedding-3-small

vector_store:
  backend: chroma  # chroma | qdrant | pinecone

retrieval:
  sparse_backend: bm25
  fusion_algorithm: rrf
  rerank_backend: cross_encoder  # none | cross_encoder | llm

evaluation:
  backends: [ragas, custom_metrics]
```

## Important Implementation Notes

1. **MCP Protocol Compliance:** Server uses stdio transport. stdout only for valid MCP messages (JSON-RPC 2.0). All logs go to stderr.

2. **Content Hashing:** Compute SHA256 hashes for files and chunks to enable idempotent upserts and avoid duplicate processing.

3. **Multi-modal Images:** Images use multi-embedding strategy (not image-to-text). Store image vectors in vector store, original images in filesystem with Base64 encoding for MCP responses.

4. **Metadata Filtering:** Apply filters pre-retrieval when index supports, post-retrieval as fallback. Soft preferences (e.g., recency) should boost scores, not filter.

5. **Observability:** Each request gets a trace_id. Use `TraceContext.record_stage()` in each component for transparent debugging.

## Testing Strategy

- **Unit Tests:** Mock external dependencies (LLM APIs), test individual components
- **Integration Tests:** Use temporary databases, verify data flow through pipelines
- **E2E Tests:** Validate complete workflows (ingestion, query, MCP protocol)
- **Evaluation Metrics:** Target Hit Rate@K ≥ 90%, MRR ≥ 0.8, Faithfulness ≥ 0.9

## Documentation

- `devspec.md`: Comprehensive technical specification (in Chinese) - **primary reference for implementation**
- Architecture details, data structures, and component contracts are defined in devspec.md sections 2-7
