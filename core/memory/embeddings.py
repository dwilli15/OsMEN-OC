"""Embedding generation via Ollama (nomic-embed-text).

Connects to a local Ollama instance to produce 768-dimension embeddings
suitable for ChromaDB and pgvector storage.
"""

from __future__ import annotations

from typing import Any

import anyio
import httpx
from loguru import logger
from pydantic import BaseModel, Field

_DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
_DEFAULT_MODEL = "nomic-embed-text"
_EMBEDDING_DIM = 768
_MAX_BATCH_SIZE = 64


class EmbeddingResult(BaseModel):
    """Single embedding result with source text reference."""

    text: str
    embedding: list[float]
    model: str
    dimensions: int


class EmbeddingBatch(BaseModel):
    """Collection of embedding results from a batch call."""

    results: list[EmbeddingResult] = Field(default_factory=list)
    model: str = _DEFAULT_MODEL
    total_tokens: int = 0

    @property
    def embeddings(self) -> list[list[float]]:
        return [r.embedding for r in self.results]

    @property
    def texts(self) -> list[str]:
        return [r.text for r in self.results]


class OllamaEmbedder:
    """Generate embeddings using a local Ollama instance.

    Args:
        base_url: Ollama API base URL (default: http://127.0.0.1:11434).
        model: Embedding model name (default: nomic-embed-text).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        *,
        base_url: str = _DEFAULT_OLLAMA_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def embed_one(self, text: str) -> EmbeddingResult:
        """Generate an embedding for a single text string."""
        client = await self._get_client()
        response = await client.post(
            "/api/embed",
            json={"model": self._model, "input": text},
        )
        response.raise_for_status()
        data = response.json()
        embedding = data["embeddings"][0]
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self._model,
            dimensions=len(embedding),
        )

    async def embed_batch(self, texts: list[str]) -> EmbeddingBatch:
        """Generate embeddings for a batch of texts.

        Automatically splits into sub-batches of _MAX_BATCH_SIZE to avoid
        overloading the Ollama API.
        """
        if not texts:
            return EmbeddingBatch(model=self._model)

        all_results: list[EmbeddingResult] = []
        for start in range(0, len(texts), _MAX_BATCH_SIZE):
            chunk = texts[start : start + _MAX_BATCH_SIZE]
            client = await self._get_client()
            response = await client.post(
                "/api/embed",
                json={"model": self._model, "input": chunk},
            )
            response.raise_for_status()
            data = response.json()
            embeddings_list: list[list[float]] = data["embeddings"]
            for text, emb in zip(chunk, embeddings_list, strict=True):
                all_results.append(
                    EmbeddingResult(
                        text=text,
                        embedding=emb,
                        model=self._model,
                        dimensions=len(emb),
                    )
                )
            logger.debug(
                "Embedded batch of {} texts (offset {})",
                len(chunk),
                start,
            )

        return EmbeddingBatch(results=all_results, model=self._model)

    async def health_check(self) -> bool:
        """Verify Ollama is reachable and the model is available."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            available = [m.get("name", "").split(":")[0] for m in models]
            if self._model not in available:
                logger.warning(
                    "Model '{}' not found in Ollama. Available: {}",
                    self._model,
                    available,
                )
                return False
            return True
        except httpx.HTTPError as exc:
            logger.error("Ollama health check failed: {}", exc)
            return False

    def embed_one_sync(self, text: str) -> EmbeddingResult:
        """Synchronous wrapper for embed_one."""
        return anyio.from_thread.run(self.embed_one, text)

    def embed_batch_sync(self, texts: list[str]) -> EmbeddingBatch:
        """Synchronous wrapper for embed_batch."""
        return anyio.from_thread.run(self.embed_batch, texts)


async def get_embedder(
    *,
    base_url: str = _DEFAULT_OLLAMA_URL,
    model: str = _DEFAULT_MODEL,
) -> OllamaEmbedder:
    """Create and health-check an embedder instance."""
    embedder = OllamaEmbedder(base_url=base_url, model=model)
    healthy = await embedder.health_check()
    if not healthy:
        logger.warning("Ollama embedder created but health check failed")
    return embedder
