"""Built-in tool handlers for OsMEN-OC agents.

Each handler is registered on the global :data:`~core.gateway.handlers.handler_registry`
at import time.  Import this module during startup to activate them.

Currently implemented:
- ``ingest_url`` — fetch + chunk + store in ChromaDB (knowledge_librarian).
- ``search_knowledge`` — semantic query against ChromaDB (knowledge_librarian).
"""

from __future__ import annotations

import hashlib as _hashlib
import re as _re
from typing import Any

import httpx as _httpx
from loguru import logger

from core.gateway.handlers import HandlerContext, register_handler
from core.memory.chunking import chunk_text


@register_handler("ingest_url")
async def handle_ingest_url(parameters: dict[str, Any], context: HandlerContext) -> dict[str, Any]:
    """Fetch a URL, chunk the text, and store in ChromaDB.

    Required parameters:
        url: The URL to fetch.

    Optional parameters:
        collection: ChromaDB collection name (default ``"general"``).
    """
    url = parameters.get("url")
    if not url:
        return {"status": "error", "detail": "Missing required parameter: url"}

    collection_name = parameters.get("collection", "general")

    # Fetch content via httpx (available in core deps)
    try:
        async with _httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            text = resp.text
    except _httpx.HTTPError as exc:
        logger.warning("ingest_url fetch failed for {}: {}", url, exc)
        return {"status": "error", "detail": f"Fetch failed: {exc}"}

    # Strip HTML tags (basic extraction — full readability is a future enhancement)
    clean = _re.sub(r"<[^>]+>", " ", text)
    clean = _re.sub(r"\s+", " ", clean).strip()

    if not clean:
        return {"status": "error", "detail": "No text content extracted from URL"}

    # Chunk at sentence boundaries
    chunks = chunk_text(clean, max_chunk_tokens=512, overlap_tokens=64)

    # Store in ChromaDB if available
    chroma_store = getattr(context.app_state, "chroma_store", None) if context.app_state else None
    if chroma_store is not None:
        from core.memory.store import MemoryDocument

        docs = [
            MemoryDocument(
                id=_hashlib.sha256(f"{url}:{i}".encode()).hexdigest()[:16],
                text=chunk,
                metadata={
                    "source": url,
                    "chunk_index": i,
                    "collection": collection_name,
                },
            )
            for i, chunk in enumerate(chunks)
        ]
        chroma_store.add_documents(docs)
        logger.info("Ingested {} chunks from {} into '{}'", len(docs), url, collection_name)
    else:
        logger.warning("ChromaDB not configured; chunked {} but not stored", len(chunks))

    return {
        "status": "ok",
        "url": url,
        "chunks": len(chunks),
        "collection": collection_name,
        "stored": chroma_store is not None,
    }


@register_handler("search_knowledge")
async def handle_search_knowledge(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Semantic search against ChromaDB.

    Required parameters:
        query: Natural-language query string.

    Optional parameters:
        collection: ChromaDB collection to search (default ``"general"``).
        top_k: Number of results (default 5).
    """
    query = parameters.get("query")
    if not query:
        return {"status": "error", "detail": "Missing required parameter: query"}

    top_k = int(parameters.get("top_k", 5))
    collection = parameters.get("collection")

    chroma_store = getattr(context.app_state, "chroma_store", None) if context.app_state else None
    if chroma_store is None:
        return {"status": "error", "detail": "ChromaDB not configured"}

    where_filter = {"collection": collection} if collection else None
    results = chroma_store.query(query, n_results=top_k, where=where_filter)

    return {
        "status": "ok",
        "query": query,
        "results": results,
    }
