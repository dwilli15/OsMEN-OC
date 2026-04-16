"""Tests for the knowledge ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.knowledge.ingest import (
    FileType,
    IngestResult,
    detect_file_type,
    extract_text,
    _make_doc_id,
)


def test_detect_file_type_markdown() -> None:
    assert detect_file_type(Path("readme.md")) == FileType.MARKDOWN
    assert detect_file_type(Path("notes.markdown")) == FileType.MARKDOWN


def test_detect_file_type_plain_text() -> None:
    assert detect_file_type(Path("notes.txt")) == FileType.PLAIN_TEXT
    assert detect_file_type(Path("app.log")) == FileType.PLAIN_TEXT


def test_detect_file_type_html() -> None:
    assert detect_file_type(Path("page.html")) == FileType.HTML
    assert detect_file_type(Path("page.htm")) == FileType.HTML


def test_detect_file_type_pdf() -> None:
    assert detect_file_type(Path("paper.pdf")) == FileType.PDF


def test_detect_file_type_epub() -> None:
    assert detect_file_type(Path("book.epub")) == FileType.EPUB


def test_detect_file_type_unknown() -> None:
    assert detect_file_type(Path("image.png")) == FileType.UNKNOWN
    assert detect_file_type(Path("archive.zip")) == FileType.UNKNOWN


def test_extract_markdown(tmp_path: Path) -> None:
    md_file = tmp_path / "test.md"
    md_file.write_text("# Hello\n\nSome content here.", encoding="utf-8")
    text = extract_text(md_file)
    assert "# Hello" in text
    assert "Some content here." in text


def test_extract_plain_text(tmp_path: Path) -> None:
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Plain text content.", encoding="utf-8")
    text = extract_text(txt_file)
    assert text == "Plain text content."


def test_extract_html(tmp_path: Path) -> None:
    html_file = tmp_path / "test.html"
    html_file.write_text(
        "<html><body><p>Hello</p><p>World</p></body></html>",
        encoding="utf-8",
    )
    text = extract_text(html_file)
    assert "Hello" in text
    assert "World" in text
    assert "<" not in text


def test_extract_unknown_raises() -> None:
    with pytest.raises(ValueError, match="No extractor"):
        extract_text(Path("image.png"), FileType.UNKNOWN)


def test_make_doc_id_deterministic() -> None:
    id1 = _make_doc_id("/path/to/file.md", 0)
    id2 = _make_doc_id("/path/to/file.md", 0)
    id3 = _make_doc_id("/path/to/file.md", 1)
    assert id1 == id2
    assert id1 != id3
    assert id1.endswith("-0000")
    assert id3.endswith("-0001")


def test_ingest_result_success() -> None:
    result = IngestResult(
        source_path="/test.md",
        file_type=FileType.MARKDOWN,
        chunk_count=5,
        doc_ids=["a", "b", "c", "d", "e"],
    )
    assert result.success is True


def test_ingest_result_failure() -> None:
    result = IngestResult(
        source_path="/test.bin",
        file_type=FileType.UNKNOWN,
        chunk_count=0,
        error="Unsupported file type",
    )
    assert result.success is False
