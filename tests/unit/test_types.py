"""Tests for core.types module."""

import pytest
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.types import (
    Document,
    DocumentMetadata,
    DocumentType,
    Chunk,
    ChunkMetadata,
    ChunkRecord,
    create_chunk
)


class TestDocumentType:
    """Test DocumentType enum."""

    def test_values(self):
        """Test enum values."""
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.MARKDOWN.value == "markdown"
        assert DocumentType.TEXT.value == "text"
        assert DocumentType.DOCX.value == "docx"
        assert DocumentType.HTML.value == "html"


class TestDocumentMetadata:
    """Test DocumentMetadata class."""

    @pytest.fixture
    def metadata(self):
        """Create sample metadata."""
        return DocumentMetadata(
            title="Test Document",
            file_path="/path/to/doc.pdf",
            file_size=1024,
            document_type=DocumentType.PDF,
            author="Test Author",
            tags=["test", "sample"]
        )

    def test_creation(self, metadata):
        """Test metadata creation."""
        assert metadata.title == "Test Document"
        assert metadata.file_path == "/path/to/doc.pdf"
        assert metadata.file_size == 1024
        assert metadata.document_type == DocumentType.PDF
        assert metadata.author == "Test Author"
        assert metadata.tags == ["test", "sample"]

    def test_to_dict(self, metadata):
        """Test metadata to dictionary conversion."""
        result = metadata.to_dict()
        assert result["title"] == "Test Document"
        assert result["file_path"] == "/path/to/doc.pdf"
        assert result["document_type"] == "pdf"
        assert result["tags"] == ["test", "sample"]


class TestDocument:
    """Test Document class."""

    @pytest.fixture
    def metadata(self):
        """Create sample metadata."""
        return DocumentMetadata(
            title="Test Document",
            file_path="/path/to/doc.pdf",
            file_size=1024,
            document_type=DocumentType.PDF
        )

    @pytest.fixture
    def document(self, metadata):
        """Create sample document."""
        return Document(
            content="This is a test document content.",
            metadata=metadata
        )

    def test_creation(self, document):
        """Test document creation."""
        assert document.content == "This is a test document content."
        assert document.metadata.title == "Test Document"
        assert document.doc_id is not None  # Auto-generated

    def test_doc_id_generation(self, document):
        """Test doc_id is auto-generated."""
        assert document.doc_id.startswith("doc_")
        assert len(document.doc_id) == 20  # "doc_" + 16 char hash

    def test_char_count(self, document):
        """Test character count."""
        assert document.char_count == len("This is a test document content.")

    def test_word_count(self, document):
        """Test word count."""
        assert document.word_count == 6  # "This is a test document content."

    def test_to_dict(self, document):
        """Test document to dictionary conversion."""
        result = document.to_dict()
        assert "doc_id" in result
        assert result["content"] == document.content
        assert "metadata" in result
        assert result["char_count"] == document.char_count


class TestChunkMetadata:
    """Test ChunkMetadata class."""

    @pytest.fixture
    def chunk_metadata(self):
        """Create sample chunk metadata."""
        return ChunkMetadata(
            chunk_id="chunk_123",
            doc_id="doc_456",
            source="/path/to/doc.pdf",
            chunk_index=0,
            start_offset=0,
            end_offset=100,
            created_at=datetime.now(),
            title="Introduction",
            tags=["intro", "overview"]
        )

    def test_creation(self, chunk_metadata):
        """Test chunk metadata creation."""
        assert chunk_metadata.chunk_id == "chunk_123"
        assert chunk_metadata.doc_id == "doc_456"
        assert chunk_metadata.title == "Introduction"
        assert chunk_metadata.tags == ["intro", "overview"]

    def test_length_property(self, chunk_metadata):
        """Test length property."""
        assert chunk_metadata.length == 100  # end_offset - start_offset

    def test_to_dict(self, chunk_metadata):
        """Test chunk metadata to dictionary conversion."""
        result = chunk_metadata.to_dict()
        assert result["chunk_id"] == "chunk_123"
        assert result["title"] == "Introduction"
        assert result["tags"] == ["intro", "overview"]


class TestChunk:
    """Test Chunk class."""

    @pytest.fixture
    def chunk_metadata(self):
        """Create sample chunk metadata."""
        return ChunkMetadata(
            chunk_id="chunk_123",
            doc_id="doc_456",
            source="/path/to/doc.pdf",
            chunk_index=0,
            start_offset=0,
            end_offset=100,
            created_at=datetime.now()
        )

    @pytest.fixture
    def chunk(self, chunk_metadata):
        """Create sample chunk."""
        return Chunk(
            content="This is a test chunk content.",
            metadata=chunk_metadata
        )

    def test_creation(self, chunk):
        """Test chunk creation."""
        assert chunk.content == "This is a test chunk content."
        assert chunk.metadata.chunk_id == "chunk_123"
        assert chunk.content_hash is not None  # Auto-generated

    def test_content_hash_generation(self, chunk):
        """Test content_hash is auto-generated."""
        assert chunk.content_hash is not None
        assert len(chunk.content_hash) == 64  # SHA256 hex length

    def test_char_count(self, chunk):
        """Test character count."""
        assert chunk.char_count == len("This is a test chunk content.")

    def test_word_count(self, chunk):
        """Test word count."""
        assert chunk.word_count == 6

    def test_get_display_text_with_title(self, chunk):
        """Test display text with title."""
        chunk.metadata.title = "Test Title"
        display = chunk.get_display_text()
        assert display.startswith("# Test Title")
        assert chunk.content in display

    def test_get_display_text_without_title(self, chunk):
        """Test display text without title."""
        display = chunk.get_display_text()
        assert display == chunk.content

    def test_to_dict(self, chunk):
        """Test chunk to dictionary conversion."""
        result = chunk.to_dict()
        assert "content" in result
        assert "metadata" in result
        assert "content_hash" in result


class TestChunkRecord:
    """Test ChunkRecord class."""

    @pytest.fixture
    def chunk(self):
        """Create sample chunk."""
        metadata = ChunkMetadata(
            chunk_id="chunk_123",
            doc_id="doc_456",
            source="/path/to/doc.pdf",
            chunk_index=0,
            start_offset=0,
            end_offset=100,
            created_at=datetime.now()
        )
        return Chunk(
            content="Test content",
            metadata=metadata
        )

    @pytest.fixture
    def chunk_record(self, chunk):
        """Create sample chunk record."""
        return ChunkRecord(
            chunk=chunk,
            dense_embedding=[0.1, 0.2, 0.3],
            sparse_embedding={"test": 1.0, "content": 0.5}
        )

    def test_creation(self, chunk_record):
        """Test chunk record creation."""
        assert chunk_record.chunk is not None
        assert chunk_record.dense_embedding == [0.1, 0.2, 0.3]
        assert chunk_record.sparse_embedding == {"test": 1.0, "content": 0.5}
        assert chunk_record.upserted_at is not None  # Auto-generated

    def test_vector_id(self, chunk_record):
        """Test vector_id generation."""
        vector_id = chunk_record.vector_id
        assert vector_id.startswith("chunk_123_")
        assert len(vector_id.split("_")[-1]) == 8  # Short content hash

    def test_to_dict(self, chunk_record):
        """Test chunk record to dictionary conversion."""
        result = chunk_record.to_dict()
        assert "vector_id" in result
        assert "chunk" in result
        assert "dense_embedding" in result
        assert "sparse_embedding" in result


class TestCreateChunk:
    """Test create_chunk factory function."""

    def test_create_basic_chunk(self):
        """Test creating a basic chunk."""
        chunk = create_chunk(
            content="Test content",
            doc_id="doc_123",
            source="/path/to/doc.pdf",
            chunk_index=0,
            start_offset=0,
            end_offset=100
        )

        assert chunk.content == "Test content"
        assert chunk.metadata.doc_id == "doc_123"
        assert chunk.metadata.chunk_index == 0
        assert chunk.metadata.chunk_id.startswith("chunk_")

    def test_create_chunk_with_extra_metadata(self):
        """Test creating chunk with extra metadata."""
        chunk = create_chunk(
            content="Test content",
            doc_id="doc_123",
            source="/path/to/doc.pdf",
            chunk_index=0,
            start_offset=0,
            end_offset=100,
            title="Test Title",
            tags=["test"],
            page_num=1
        )

        assert chunk.metadata.title == "Test Title"
        assert chunk.metadata.tags == ["test"]
        assert chunk.metadata.page_num == 1
