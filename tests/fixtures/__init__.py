"""Test fixtures for RAG MCP tests."""

from pathlib import Path

# Data fixtures directory
FIXTURES_DIR = Path(__file__).parent


def load_fixture(name: str) -> str:
    """Load a fixture file by name."""
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def get_fixture_path(name: str) -> Path:
    """Get the path to a fixture file."""
    return FIXTURES_DIR / name
