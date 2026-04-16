"""Cross-collection lateral similarity search.

Finds related content across multiple ChromaDB collections, enabling
discovery of connections between documents, transcripts, notes, and web pages.
"""

from __future__ import annotations

from typing import Any

import anyio
from loguru import logger
from pydantic import BaseModel, Field

from core.memory.embeddings import OllamaEmbedder
from core.memory.store import ChromaStore


class LateralMatch(BaseModel):
    """A single match from lateral search across collections."""

    collection: str
    document_id: str
    text: str
    distance: float
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def similarity(self) -> float:
        """Convert distance to 0-1 similarity (assumes cosine distance)."""
        return max(0.0, 1.0 - self.distance)


class LateralResult(BaseModel):
    """Aggregated results from searching across multiple collections."""

    query: str
    matches: list[LateralMatch] = Field(default_factory=list)
    collections_searched: list[str] = Field(default_factory=list)

    @property
    def top_match(self) -> LateralMatch | None:
        return self.matches[0] if self.matches else None

    def by_collection(self) -> dict[str, list[LateralMatch]]:
        """Group matches by source collection."""
        grouped: dict[str, list[LateralMatch]] = {}
        for match in self.matches:
            grouped.setdefault(match.collection, []).append(match)
        return grouped


class LateralBridge:
    """Search across multiple ChromaDB collections for related content.

    Args:
        base_url: ChromaDB server URL.
        embedder: OllamaEmbedder for generating query vectors.
        collection_names: List of collection names to search across.
        auth_token: Optional Bearer token for ChromaDB.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8000",
        embedder: OllamaEmbedder,
        collection_names: list[str] | None = None,
        auth_token: str | None = None,
    ) -> None:
        self._base_url = base_url
        self._embedder = embedder
        self._auth_token = auth_token
        self._collection_names = collection_names or [
            "documents",
            "transcripts",
            "notes",
            "web_pages",
        ]

    async def search(
        self,
        query: str,
        *,
        n_results: int = 5,
        collections: list[str] | None = None,
        min_similarity: float = 0.0,
        where: dict[str, Any] | None = None,
    ) -> LateralResult:
        """Search across collections for content similar to the query.

        Args:
            query: Natural language query text.
            n_results: Max results per collection.
            collections: Specific collections to search (default: all).
            min_similarity: Minimum similarity threshold (0-1).
            where: ChromaDB metadata filter applied to all collections.
        """
        target_collections = collections or self._collection_names
        all_matches: list[LateralMatch] = []
        searched: list[str] = []

        # Generate query embedding once
        emb_result = await self._embedder.embed_one(query)
        query_embedding = emb_result.embedding

        for coll_name in target_collections:
            store = ChromaStore(
                base_url=self._base_url,
                collection_name=coll_name,
                auth_token=self._auth_token,
            )

            searched.append(coll_name)

            try:
                results = await store.query_async(
                    "",
                    n_results=n_results,
                    where=where,
                    query_embeddings=[query_embedding],
                )
            except Exception as exc:
                logger.warning(
                    "Query failed on collection '{}': {}", coll_name, exc
                )
                continue

            ids = results.get("ids", [[]])[0]
            documents = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]

            if not ids:
                continue

            for doc_id, text, dist, meta in zip(
                ids, documents, distances, metadatas, strict=True
            ):
                match = LateralMatch(
                    collection=coll_name,
                    document_id=doc_id,
                    text=text or "",
                    distance=dist,
                    metadata=meta or {},
                )
                if match.similarity >= min_similarity:
                    all_matches.append(match)

        # Sort by distance (ascending = most similar first)
        all_matches.sort(key=lambda m: m.distance)

        logger.debug(
            "Lateral search '{}': {} matches across {} collections",
            query[:50],
            len(all_matches),
            len(searched),
        )

        return LateralResult(
            query=query,
            matches=all_matches,
            collections_searched=searched,
        )

    async def find_related(
        self,
        document_id: str,
        source_collection: str,
        *,
        n_results: int = 5,
        exclude_same_source: bool = True,
    ) -> LateralResult:
        """Find content related to an existing document.

        Retrieves the document's text, then searches other collections.
        """
        try:
            store = ChromaStore(
                base_url=self._base_url,
                collection_name=source_collection,
                auth_token=self._auth_token,
            )
            result = store.get(ids=[document_id], include=["documents"])
            docs = result.get("documents", [])
            if not docs:
                return LateralResult(
                    query=f"[doc:{document_id}]",
                    collections_searched=[],
                )
            source_text = docs[0]
        except Exception as exc:
            logger.error(
                "Could not retrieve document '{}' from '{}': {}",
                document_id,
                source_collection,
                exc,
            )
            return LateralResult(
                query=f"[doc:{document_id}]",
                collections_searched=[],
            )

        # Search across other collections (or all, then filter)
        search_collections = (
            [c for c in self._collection_names if c != source_collection]
            if exclude_same_source
            else None
        )

        return await self.search(
            source_text,
            n_results=n_results,
            collections=search_collections,
        )
# DEPRECATED: See core/memory/hub.py (MemoryHub) for new vector storage.
