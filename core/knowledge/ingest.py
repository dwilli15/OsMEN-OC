"""File ingestion pipeline: detect type → extract text → chunk → embed → store.

Supported formats: Markdown, plain text, HTML, PDF (via pymupdf), EPUB.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
from enum import Enum
from pathlib import Path
from typing import Any

import anyio
from loguru import logger
from pydantic import BaseModel, Field

from core.memory.chunking import chunk_text
from core.memory.embeddings import OllamaEmbedder
from core.memory.store import ChromaStore, MemoryDocument


class FileType(str, Enum):
    """Recognized ingestible file types."""

    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    HTML = "html"
    PDF = "pdf"
    EPUB = "epub"
    UNKNOWN = "unknown"


class IngestResult(BaseModel):
    """Result of ingesting a single file."""

    source_path: str
    file_type: FileType
    chunk_count: int
    doc_ids: list[str] = Field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


# ---------------------------------------------------------------------------
# File-type detection
# ---------------------------------------------------------------------------

_EXTENSION_MAP: dict[str, FileType] = {
    ".md": FileType.MARKDOWN,
    ".markdown": FileType.MARKDOWN,
    ".txt": FileType.PLAIN_TEXT,
    ".text": FileType.PLAIN_TEXT,
    ".log": FileType.PLAIN_TEXT,
    ".html": FileType.HTML,
    ".htm": FileType.HTML,
    ".pdf": FileType.PDF,
    ".epub": FileType.EPUB,
}


def detect_file_type(path: Path) -> FileType:
    """Determine file type from extension."""
    suffix = path.suffix.lower()
    return _EXTENSION_MAP.get(suffix, FileType.UNKNOWN)


# ---------------------------------------------------------------------------
# Text extractors (one per file type)
# ---------------------------------------------------------------------------

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _extract_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_plain_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = _HTML_TAG_RE.sub(" ", raw)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _extract_pdf(path: Path) -> str:
    try:
        import pymupdf  # noqa: WPS433
    except ImportError:
        try:
            import fitz as pymupdf  # noqa: WPS433
        except ImportError:
            raise ImportError(
                "PDF extraction requires pymupdf. Install: pip install pymupdf"
            )

    text_parts: list[str] = []
    with pymupdf.open(str(path)) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def _extract_epub(path: Path) -> str:
    try:
        from ebooklib import epub  # noqa: WPS433
        from ebooklib import ITEM_DOCUMENT  # noqa: WPS433
    except ImportError:
        raise ImportError(
            "EPUB extraction requires ebooklib. Install: pip install ebooklib"
        )

    book = epub.read_epub(str(path), options={"ignore_ncx": True})
    text_parts: list[str] = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        content = item.get_content().decode("utf-8", errors="replace")
        clean = _HTML_TAG_RE.sub(" ", content)
        clean = _WHITESPACE_RE.sub(" ", clean).strip()
        if clean:
            text_parts.append(clean)
    return "\n\n".join(text_parts)


_EXTRACTORS: dict[FileType, Any] = {
    FileType.MARKDOWN: _extract_markdown,
    FileType.PLAIN_TEXT: _extract_plain_text,
    FileType.HTML: _extract_html,
    FileType.PDF: _extract_pdf,
    FileType.EPUB: _extract_epub,
}


def extract_text(path: Path, file_type: FileType | None = None) -> str:
    """Extract raw text from a file. Raises ValueError for unknown types."""
    if file_type is None:
        file_type = detect_file_type(path)
    extractor = _EXTRACTORS.get(file_type)
    if extractor is None:
        raise ValueError(f"No extractor for file type: {file_type}")
    return extractor(path)


# ---------------------------------------------------------------------------
# Document ID generation
# ---------------------------------------------------------------------------


def _make_doc_id(source: str, chunk_index: int) -> str:
    """Deterministic document ID from source path and chunk index."""
    digest = hashlib.sha256(source.encode()).hexdigest()[:12]
    return f"{digest}-{chunk_index:04d}"


# ---------------------------------------------------------------------------
# Main ingestion pipeline
# ---------------------------------------------------------------------------


class IngestPipeline:
    """Orchestrates file → chunk → embed → store.

    Args:
        embedder: OllamaEmbedder instance for generating vectors.
        store: ChromaStore instance for persisting documents.
        max_chunk_tokens: Maximum tokens per chunk.
        overlap_tokens: Overlap between consecutive chunks.
        collection_name: ChromaDB collection to store into.
    """

    def __init__(
        self,
        *,
        embedder: OllamaEmbedder,
        store: ChromaStore,
        max_chunk_tokens: int = 512,
        overlap_tokens: int = 64,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._max_chunk_tokens = max_chunk_tokens
        self._overlap_tokens = overlap_tokens

    async def ingest_file(
        self,
        path: Path,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> IngestResult:
        """Ingest a single file through the full pipeline."""
        resolved = path.resolve()
        file_type = detect_file_type(resolved)

        if file_type == FileType.UNKNOWN:
            return IngestResult(
                source_path=str(resolved),
                file_type=file_type,
                chunk_count=0,
                error=f"Unsupported file type: {resolved.suffix}",
            )

        try:
            raw_text = await anyio.to_thread.run_sync(extract_text, resolved, file_type)
        except Exception as exc:
            logger.error("Text extraction failed for {}: {}", resolved, exc)
            return IngestResult(
                source_path=str(resolved),
                file_type=file_type,
                chunk_count=0,
                error=f"Extraction failed: {exc}",
            )

        if not raw_text.strip():
            return IngestResult(
                source_path=str(resolved),
                file_type=file_type,
                chunk_count=0,
                error="File produced no text",
            )

        chunks = chunk_text(
            raw_text,
            max_chunk_tokens=self._max_chunk_tokens,
            overlap_tokens=self._overlap_tokens,
        )

        if not chunks:
            return IngestResult(
                source_path=str(resolved),
                file_type=file_type,
                chunk_count=0,
                error="Chunking produced no results",
            )

        # Generate embeddings
        batch = await self._embedder.embed_batch(chunks)

        # Build stored documents
        base_metadata = {
            "source": str(resolved),
            "file_type": file_type.value,
        }
        if metadata:
            base_metadata.update(metadata)

        documents: list[MemoryDocument] = []
        for idx, (chunk, emb_result) in enumerate(
            zip(chunks, batch.results, strict=True)
        ):
            doc_id = _make_doc_id(str(resolved), idx)
            doc_meta = {
                **base_metadata,
                "chunk_index": idx,
                "chunk_count": len(chunks),
            }
            documents.append(
                MemoryDocument(id=doc_id, text=chunk, metadata=doc_meta)
            )

        await self._store.add_documents_async(
            documents, embeddings=batch.embeddings
        )
        doc_ids = [d.id for d in documents]

        logger.info(
            "Ingested {} ({} chunks) → {}",
            resolved.name,
            len(chunks),
            self._store.name,
        )
        return IngestResult(
            source_path=str(resolved),
            file_type=file_type,
            chunk_count=len(chunks),
            doc_ids=doc_ids,
        )

    async def ingest_directory(
        self,
        directory: Path,
        *,
        recursive: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> list[IngestResult]:
        """Ingest all supported files in a directory."""
        resolved = directory.resolve()
        if not resolved.is_dir():
            raise ValueError(f"Not a directory: {resolved}")

        pattern = "**/*" if recursive else "*"
        results: list[IngestResult] = []

        for file_path in sorted(resolved.glob(pattern)):
            if not file_path.is_file():
                continue
            file_type = detect_file_type(file_path)
            if file_type == FileType.UNKNOWN:
                continue
            result = await self.ingest_file(file_path, metadata=metadata)
            results.append(result)

        logger.info(
            "Directory ingest complete: {} files, {} successful",
            len(results),
            sum(1 for r in results if r.success),
        )
        return results
