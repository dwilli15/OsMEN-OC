"""Tests for memory chunking and vector store wrappers."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.memory.chunking import chunk_text, split_sentences
from core.memory.store import ChromaStore, MemoryDocument


def test_split_sentences_preserves_abbreviations_and_urls() -> None:
    text = (
        "Dr. Smith read docs at https://example.com/docs/index.html. "
        "He said e.g. this pattern is stable. "
        "Then he shipped it!"
    )
    sentences = split_sentences(text)

    assert len(sentences) == 3
    assert "https://example.com/docs/index.html" in sentences[0]
    assert sentences[1].startswith("He said e.g.")


def test_chunk_text_never_splits_mid_sentence() -> None:
    text = "A short sentence. Another short sentence. Final sentence!"
    chunks = chunk_text(text, max_chunk_tokens=4, overlap_tokens=0)

    assert len(chunks) >= 2
    # Every chunk should end at sentence punctuation.
    for chunk in chunks:
        assert chunk[-1] in ".!?"


def test_chunk_text_adds_overlap_context() -> None:
    text = "One sentence. Two sentence. Three sentence. Four sentence."
    chunks = chunk_text(text, max_chunk_tokens=6, overlap_tokens=2)

    assert len(chunks) >= 2
    # Overlap means a sentence from chunk[0] should appear in chunk[1].
    assert any(sentence in chunks[1] for sentence in split_sentences(chunks[0]))


def test_chroma_store_add_query_delete_roundtrip() -> None:
    collection = MagicMock()
    collection.query.return_value = {"ids": [["doc-1"]], "documents": [["hello"]]}

    client = MagicMock()
    client.get_or_create_collection.return_value = collection

    store = ChromaStore(client, collection_name="test-memory")
    docs = [MemoryDocument(id="doc-1", text="hello", metadata={"source": "unit"})]

    store.add_documents(docs)
    client.get_or_create_collection.assert_called_once_with(name="test-memory")
    collection.add.assert_called_once_with(
        documents=["hello"],
        ids=["doc-1"],
        metadatas=[{"source": "unit"}],
    )

    result = store.query("hello", n_results=3, where={"source": "unit"})
    collection.query.assert_called_once_with(
        query_texts=["hello"],
        n_results=3,
        where={"source": "unit"},
    )
    assert result["ids"][0][0] == "doc-1"

    store.delete(["doc-1"])
    collection.delete.assert_called_once_with(ids=["doc-1"])
