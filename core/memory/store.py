"""Legacy ChromaStore — deprecated. Use MemoryHub (core/memory/hub.py) instead.

This module is kept for backward compatibility only.
All new code should use MemoryHub for vector storage and retrieval.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

import warnings

warnings.warn(
    "ChromaStore is deprecated — use MemoryHub (core/memory/hub.py) instead.",
    DeprecationWarning,
    stacklevel=2,
)


class MemoryDocument(BaseModel):
    """Document payload stored in vector memory."""

    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChromaStore:
    """Legacy vector store — deprecated. Use MemoryHub instead."""

    def query(
        self,
        query_text: str,
        *,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[MemoryDocument]:
        """Query the store. Deprecated — use MemoryHub.recall()."""
        return []

    async def query_async(
        self,
        query_text: str,
        *,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[MemoryDocument]:
        """Async query. Deprecated — use MemoryHub."""
        return []

    def delete(self, ids: list[str]) -> None:
        """Delete documents by ID."""
        if not ids:
            return
