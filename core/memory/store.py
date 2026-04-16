"""Typed wrapper for ChromaDB vector store via REST API (v1).

Uses httpx against the ChromaDB v1 REST API directly, avoiding
client library version mismatches.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel, Field


class MemoryDocument(BaseModel):
    """Document payload stored in vector memory."""

    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChromaStore:
    """HTTP-based ChromaDB store using the v1 REST API.

    Args:
        base_url: ChromaDB server URL (default: http://127.0.0.1:8000).
        collection_name: Name of the collection to operate on.
        auth_token: Optional Bearer token for authenticated access.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8000",
        collection_name: str = "osmen-memory",
        auth_token: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._collection_name = collection_name
        self._auth_token = auth_token
        self._collection_id: str | None = None
        self._client = httpx.Client(timeout=30.0)
        self._async_client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return self._collection_name

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers

    def _ensure_collection(self) -> str:
        """Get or create the collection, returning its ID."""
        if self._collection_id is not None:
            return self._collection_id
        resp = self._client.post(
            f"{self._base_url}/api/v1/collections",
            headers=self._headers(),
            json={
                "name": self._collection_name,
                "metadata": {"hnsw:space": "cosine"},
                "get_or_create": True,
            },
        )
        resp.raise_for_status()
        self._collection_id = resp.json()["id"]
        return self._collection_id

    async def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(timeout=30.0)
        return self._async_client

    async def _ensure_collection_async(self) -> str:
        if self._collection_id is not None:
            return self._collection_id
        client = await self._get_async_client()
        resp = await client.post(
            f"{self._base_url}/api/v1/collections",
            headers=self._headers(),
            json={
                "name": self._collection_name,
                "metadata": {"hnsw:space": "cosine"},
                "get_or_create": True,
            },
        )
        resp.raise_for_status()
        self._collection_id = resp.json()["id"]
        return self._collection_id

    def add_documents(
        self,
        documents: list[MemoryDocument],
        *,
        embeddings: list[list[float]] | None = None,
    ) -> None:
        if not documents:
            return
        coll_id = self._ensure_collection()
        payload: dict[str, Any] = {
            "ids": [d.id for d in documents],
            "documents": [d.text for d in documents],
            "metadatas": [d.metadata for d in documents],
        }
        if embeddings:
            payload["embeddings"] = embeddings
        resp = self._client.post(
            f"{self._base_url}/api/v1/collections/{coll_id}/add",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()

    async def add_documents_async(
        self,
        documents: list[MemoryDocument],
        *,
        embeddings: list[list[float]] | None = None,
    ) -> None:
        if not documents:
            return
        coll_id = await self._ensure_collection_async()
        payload: dict[str, Any] = {
            "ids": [d.id for d in documents],
            "documents": [d.text for d in documents],
            "metadatas": [d.metadata for d in documents],
        }
        if embeddings:
            payload["embeddings"] = embeddings
        client = await self._get_async_client()
        resp = await client.post(
            f"{self._base_url}/api/v1/collections/{coll_id}/add",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()

    def query(
        self,
        query_text: str,
        *,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        query_embeddings: list[list[float]] | None = None,
    ) -> dict[str, Any]:
        coll_id = self._ensure_collection()
        payload: dict[str, Any] = {"n_results": n_results}
        if query_embeddings:
            payload["query_embeddings"] = query_embeddings
        else:
            payload["query_texts"] = [query_text]
        if where:
            payload["where"] = where
        resp = self._client.post(
            f"{self._base_url}/api/v1/collections/{coll_id}/query",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    async def query_async(
        self,
        query_text: str,
        *,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        query_embeddings: list[list[float]] | None = None,
    ) -> dict[str, Any]:
        coll_id = await self._ensure_collection_async()
        payload: dict[str, Any] = {"n_results": n_results}
        if query_embeddings:
            payload["query_embeddings"] = query_embeddings
        else:
            payload["query_texts"] = [query_text]
        if where:
            payload["where"] = where
        client = await self._get_async_client()
        resp = await client.post(
            f"{self._base_url}/api/v1/collections/{coll_id}/query",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def get(
        self,
        ids: list[str],
        *,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        coll_id = self._ensure_collection()
        payload: dict[str, Any] = {"ids": ids}
        if include:
            payload["include"] = include
        resp = self._client.post(
            f"{self._base_url}/api/v1/collections/{coll_id}/get",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def count(self) -> int:
        coll_id = self._ensure_collection()
        resp = self._client.get(
            f"{self._base_url}/api/v1/collections/{coll_id}/count",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        coll_id = self._ensure_collection()
        resp = self._client.post(
            f"{self._base_url}/api/v1/collections/{coll_id}/delete",
            headers=self._headers(),
            json={"ids": ids},
        )
        resp.raise_for_status()

    async def delete_async(self, ids: list[str]) -> None:
        if not ids:
            return
        coll_id = await self._ensure_collection_async()
        client = await self._get_async_client()
        resp = await client.post(
            f"{self._base_url}/api/v1/collections/{coll_id}/delete",
            headers=self._headers(),
            json={"ids": ids},
        )
        resp.raise_for_status()

    async def close(self) -> None:
        if self._async_client is not None and not self._async_client.is_closed:
            await self._async_client.aclose()
        self._client.close()

# ---------------------------------------------------------------------------
# DEPRECATION NOTICE (P14.28)
# ---------------------------------------------------------------------------
# This module wraps ChromaDB REST API and is considered LEGACY.
# New consumers should use MemoryHub (core/memory/hub.py) which uses
# PostgreSQL + pgvector for vector storage.
# ChromaDB remains available for backward compatibility during migration.
# ---------------------------------------------------------------------------
