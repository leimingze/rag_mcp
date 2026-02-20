"""Pytest configuration and shared fixtures for RAG MCP tests."""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any
import pytest
import yaml

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_config_path(project_root: Path) -> Path:
    """Get the test configuration file path."""
    config_path = project_root / "config" / "settings.yaml"
    if not config_path.exists():
        # Create minimal test config
        config_path.parent.mkdir(parents=True, exist_ok=True)
        test_config = {
            "llm": {"provider": "openai", "model": "gpt-4o"},
            "embedding": {"provider": "openai", "model": "text-embedding-3-small"},
            "vector_store": {"backend": "chroma"},
            "retrieval": {"top_k": 5, "final_top_k": 3},
            "observability": {"logging": {"level": "WARNING"}},
        }
        with open(config_path, "w") as f:
            yaml.dump(test_config, f)
    return config_path


@pytest.fixture
def test_config(test_config_path: Path) -> Dict[str, Any]:
    """Load test configuration."""
    with open(test_config_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def temp_dir(project_root: Path) -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    temp_path = project_root / "temp_test"
    temp_path.mkdir(parents=True, exist_ok=True)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def temp_db_dir(temp_dir: Path) -> Path:
    """Create a temporary directory for test databases."""
    db_dir = temp_dir / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir


@pytest.fixture
def sample_documents() -> list[Dict[str, Any]]:
    """Sample documents for testing."""
    return [
        {
            "id": "doc1",
            "text": "Python is a high-level programming language.",
            "metadata": {"source": "test.txt", "page": 1},
        },
        {
            "id": "doc2",
            "text": "Machine learning is a subset of AI.",
            "metadata": {"source": "test.txt", "page": 2},
        },
        {
            "id": "doc3",
            "text": "RAG combines retrieval and generation.",
            "metadata": {"source": "test.txt", "page": 3},
        },
    ]


@pytest.fixture
def sample_chunks() -> list[Dict[str, Any]]:
    """Sample chunks for testing."""
    return [
        {
            "id": "chunk1",
            "text": "Python is a high-level programming language.",
            "metadata": {
                "source": "test.txt",
                "page": 1,
                "chunk_index": 0,
                "doc_id": "doc1",
            },
        },
        {
            "id": "chunk2",
            "text": "Machine learning is a subset of AI.",
            "metadata": {
                "source": "test.txt",
                "page": 2,
                "chunk_index": 0,
                "doc_id": "doc2",
            },
        },
    ]


@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """Mock LLM response for testing."""
    return {
        "content": "This is a mock response from the LLM.",
        "model": "gpt-4o",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


@pytest.fixture
def mock_embedding() -> list[float]:
    """Mock embedding vector for testing."""
    return [0.1, -0.2, 0.3, -0.4, 0.5] * 30  # 1536 dimensions


@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set mock environment variables for testing."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "test-qdrant-key")


@pytest.fixture
def sample_pdf_path(temp_dir: Path) -> Path:
    """Create a sample PDF file for testing."""
    pdf_path = temp_dir / "test.pdf"
    # Write minimal PDF content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def sample_markdown_path(temp_dir: Path) -> Path:
    """Create a sample Markdown file for testing."""
    md_path = temp_dir / "test.md"
    md_content = """# Test Document

This is a test document for RAG processing.

## Section 1

Some content here.

## Section 2

More content here.
"""
    md_path.write_text(md_content)
    return md_path


@pytest.fixture
def sample_trace_data() -> Dict[str, Any]:
    """Sample trace data for testing observability."""
    return {
        "trace_id": "test-trace-001",
        "timestamp": "2024-01-01T00:00:00Z",
        "user_query": "What is Python?",
        "collection": "test_collection",
        "stages": {
            "query_processing": {
                "input": "What is Python?",
                "output": {"query": "What is Python?", "keywords": ["Python"]},
                "latency_ms": 10,
            },
            "dense_retrieval": {
                "results": [
                    {"id": "chunk1", "score": 0.95},
                    {"id": "chunk2", "score": 0.85},
                ],
                "latency_ms": 50,
            },
            "sparse_retrieval": {
                "results": [{"id": "chunk1", "score": 2.5}],
                "latency_ms": 20,
            },
            "fusion": {
                "results": [{"id": "chunk1", "score": 0.9}],
                "latency_ms": 5,
            },
        },
        "total_latency_ms": 85,
        "error": None,
    }


# Markers for test categories
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "llm: Tests that call LLM APIs")
    config.addinivalue_line("markers", "requires_api: Tests that require API keys")
