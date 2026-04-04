"""Typed wrapper for a Chroma-style vector store client."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MemoryDocument(BaseModel):
    """Document payload stored in vector memory."""

    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChromaStore:
    """Thin wrapper around a Chroma-like collection API.

    The provided client is expected to expose:
    - get_or_create_collection(name=...)

    And the resulting collection should expose:
    - add(documents=[...], ids=[...], metadatas=[...])
    - query(query_texts=[...], n_results=..., where=...)
    - delete(ids=[...])
    """

    def __init__(self, client: Any, collection_name: str = "osmen-memory") -> None:
        self._client = client
        self._collection = client.get_or_create_collection(name=collection_name)

    def add_documents(self, documents: list[MemoryDocument]) -> None:
        if not documents:
            return
        self._collection.add(
            documents=[d.text for d in documents],
            ids=[d.id for d in documents],
            metadatas=[d.metadata for d in documents],
        )

    def query(
        self,
        query_text: str,
        *,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
        )

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        self._collection.delete(ids=ids)
