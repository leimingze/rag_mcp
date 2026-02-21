"""Core data types for the RAG MCP framework.

This module defines the fundamental data structures used throughout the system:
- Document: Represents a loaded document from various sources
- Chunk: Represents a semantic unit of text from a document
- ChunkMetadata: Metadata associated with chunks

These types are used by ingestion, retrieval, and MCP layers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum


class DocumentType(Enum):
    """Supported document types."""
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    DOCX = "docx"
    HTML = "html"


@dataclass
class DocumentMetadata:
    """Metadata associated with a document.

    Attributes:
        title: Document title
        author: Document author (optional)
        created_at: Document creation timestamp (optional)
        modified_at: Document last modified timestamp (optional)
        file_path: Original file path
        file_size: File size in bytes
        document_type: Type of document
        tags: User-defined tags
        custom_fields: Additional custom metadata
    """
    title: str
    file_path: str
    file_size: int
    document_type: DocumentType
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of metadata.
        """
        return {
            "title": self.title,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "document_type": self.document_type.value,
            "tags": self.tags,
            **self.custom_fields
        }


@dataclass
class Document:
    """Represents a loaded document.

    A Document is the output of the Loader stage and input to the Chunking stage.
    It contains the raw content and associated metadata.

    Attributes:
        content: The raw text content of the document
        metadata: Document metadata
        doc_id: Unique document identifier (SHA256 hash-based)
        sections: Optional list of section headers for navigation
    """
    content: str
    metadata: DocumentMetadata
    doc_id: Optional[str] = None
    sections: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Generate doc_id if not provided."""
        if self.doc_id is None:
            import hashlib
            content_hash = hashlib.sha256(
                f"{self.metadata.file_path}:{self.content}".encode()
            ).hexdigest()
            self.doc_id = f"doc_{content_hash[:16]}"

    @property
    def char_count(self) -> int:
        """Get character count of content."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of document.
        """
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "sections": self.sections,
            "char_count": self.char_count,
            "word_count": self.word_count
        }


@dataclass
class ChunkMetadata:
    """Metadata associated with a chunk.

    Attributes:
        chunk_id: Unique chunk identifier
        doc_id: Source document ID
        source: Source file path
        chunk_index: Index of this chunk in the document
        start_offset: Character offset of chunk start in document
        end_offset: Character offset of chunk end in document
        title: Extracted or inferred title (optional)
        summary: Content summary (optional)
        tags: Content tags (optional)
        page_num: Page number for PDFs (optional)
        section_path: Hierarchical section path (e.g., ["Chapter 1", "Section 2"])
        created_at: Timestamp when chunk was created
    """
    chunk_id: str
    doc_id: str
    source: str
    chunk_index: int
    start_offset: int
    end_offset: int
    created_at: datetime
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    page_num: Optional[int] = None
    section_path: List[str] = field(default_factory=list)
    image_refs: List[str] = field(default_factory=list)  # References to images
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        """Get chunk length in characters."""
        return self.end_offset - self.start_offset

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of metadata.
        """
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "source": self.source,
            "chunk_index": self.chunk_index,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "title": self.title,
            "summary": self.summary,
            "tags": self.tags,
            "page_num": self.page_num,
            "section_path": self.section_path,
            "image_refs": self.image_refs,
            "created_at": self.created_at.isoformat(),
            **self.custom_fields
        }


@dataclass
class Chunk:
    """Represents a semantic unit of text from a document.

    A Chunk is the output of the Chunking stage and flows through
    Transform, Embedding, and Storage stages.

    Attributes:
        content: The text content of this chunk
        metadata: Chunk metadata
        content_hash: Hash of content for idempotency checks
    """
    content: str
    metadata: ChunkMetadata
    content_hash: Optional[str] = None

    def __post_init__(self):
        """Generate content_hash if not provided."""
        if self.content_hash is None:
            import hashlib
            self.content_hash = hashlib.sha256(
                self.content.encode("utf-8")
            ).hexdigest()

    @property
    def char_count(self) -> int:
        """Get character count of content."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of chunk.
        """
        return {
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "content_hash": self.content_hash,
            "char_count": self.char_count,
            "word_count": self.word_count
        }

    def get_display_text(self) -> str:
        """Get a display-friendly version of the chunk.

        Returns:
            Formatted text with title prefix if available.
        """
        if self.metadata.title:
            return f"# {self.metadata.title}\n\n{self.content}"
        return self.content


@dataclass
class ChunkRecord:
    """Record of a chunk in vector store with embeddings.

    This is the complete record stored in the vector database,
    including both dense and sparse embeddings.

    Attributes:
        chunk: The original chunk
        dense_embedding: Dense vector embedding (optional)
        sparse_embedding: Sparse BM25 vector (optional)
        upserted_at: Timestamp when upserted to vector store
    """
    chunk: Chunk
    dense_embedding: Optional[List[float]] = None
    sparse_embedding: Optional[Dict[str, float]] = None
    upserted_at: Optional[datetime] = None

    def __post_init__(self):
        """Set upserted_at if not provided."""
        if self.upserted_at is None:
            self.upserted_at = datetime.now()

    @property
    def vector_id(self) -> str:
        """Get the vector ID for this record.

        Returns:
            Unique ID combining chunk_id and content_hash.
        """
        return f"{self.chunk.metadata.chunk_id}_{self.chunk.content_hash[:8]}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of chunk record.
        """
        return {
            "vector_id": self.vector_id,
            "chunk": self.chunk.to_dict(),
            "dense_embedding": self.dense_embedding,
            "sparse_embedding": self.sparse_embedding,
            "upserted_at": self.upserted_at.isoformat()
        }


def create_chunk(
    content: str,
    doc_id: str,
    source: str,
    chunk_index: int,
    start_offset: int,
    end_offset: int,
    **kwargs
) -> Chunk:
    """Factory function to create a Chunk with proper metadata.

    Args:
        content: The text content
        doc_id: Source document ID
        source: Source file path
        chunk_index: Index in document
        start_offset: Start character offset
        end_offset: End character offset
        **kwargs: Additional metadata fields

    Returns:
        A new Chunk instance.
    """
    import hashlib
    import uuid

    # Generate unique chunk_id
    unique_part = hashlib.sha256(
        f"{doc_id}:{chunk_index}:{start_offset}:{end_offset}".encode()
    ).hexdigest()[:12]
    chunk_id = f"chunk_{unique_part}"

    # Create metadata
    metadata = ChunkMetadata(
        chunk_id=chunk_id,
        doc_id=doc_id,
        source=source,
        chunk_index=chunk_index,
        start_offset=start_offset,
        end_offset=end_offset,
        created_at=datetime.now(),
        **kwargs
    )

    return Chunk(content=content, metadata=metadata)
