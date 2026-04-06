"""Built-in tool handlers for OsMEN-OC agents.

Each handler is registered on the global :data:`~core.gateway.handlers.handler_registry`
at import time.  Import this module during startup to activate them.

Currently implemented:
- ``ingest_url`` — fetch + chunk + store in ChromaDB (knowledge_librarian).
- ``search_knowledge`` — semantic query against ChromaDB (knowledge_librarian).
"""

from __future__ import annotations

import hashlib as _hashlib
import ipaddress as _ipaddress
import re as _re
import socket as _socket
from typing import Any
from urllib.parse import urljoin as _urljoin
from urllib.parse import urlparse as _urlparse

import httpx as _httpx
from loguru import logger

from core.gateway.handlers import HandlerContext, register_handler
from core.memory.chunking import chunk_text

_MAX_FETCH_BYTES = 10 * 1024 * 1024  # 10 MiB
_MAX_REDIRECT_HOPS = 5
_ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "application/xhtml+xml",
    "text/xml",
}


def _is_public_ip(ip_text: str) -> bool:
    ip = _ipaddress.ip_address(ip_text)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_ingest_url(url: str) -> str | None:
    try:
        parsed = _urlparse(url)
    except ValueError:
        return "Invalid URL format"

    if parsed.scheme not in {"http", "https"}:
        return "URL scheme must be http or https"

    hostname = parsed.hostname
    if not hostname:
        return "URL must include a hostname"

    host_lower = hostname.lower()
    if host_lower == "localhost" or host_lower.endswith(".localhost"):
        return "localhost URLs are not allowed"

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return "URL contains an invalid port"

    try:
        resolved = _socket.getaddrinfo(hostname, port, type=_socket.SOCK_STREAM)
    except OSError:
        return "URL hostname could not be resolved"

    if not resolved:
        return "URL hostname could not be resolved"

    for info in resolved:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_text = str(sockaddr[0])
        try:
            if not _is_public_ip(ip_text):
                return "URL hostname resolves to a non-public IP"
        except ValueError:
            return "URL hostname resolved to an invalid IP"

    return None


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
    validation_error = _validate_ingest_url(url)
    if validation_error:
        return {"status": "error", "detail": validation_error}

    # Fetch content with streaming + hard cap. Redirects are handled manually
    # so each hop can be re-validated against SSRF policy.
    try:
        current_url = url
        async with _httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            for hop in range(_MAX_REDIRECT_HOPS + 1):
                validation_error = _validate_ingest_url(current_url)
                if validation_error:
                    return {
                        "status": "error",
                        "detail": f"Redirect target blocked: {validation_error}",
                    }

                async with client.stream("GET", current_url) as resp:
                    if 300 <= resp.status_code < 400:
                        location = resp.headers.get("location")
                        if not location:
                            return {
                                "status": "error",
                                "detail": "Redirect response missing Location header",
                            }
                        if hop >= _MAX_REDIRECT_HOPS:
                            return {
                                "status": "error",
                                "detail": "Too many redirect hops",
                            }
                        current_url = _urljoin(current_url, location)
                        continue

                    resp.raise_for_status()

                    content_type = resp.headers.get("content-type", "")
                    media_type = content_type.split(";", 1)[0].strip().lower()
                    if not (
                        media_type.startswith("text/")
                        or media_type in _ALLOWED_CONTENT_TYPES
                    ):
                        return {
                            "status": "error",
                            "detail": f"Unsupported content type: {media_type or 'unknown'}",
                        }

                    content = bytearray()
                    async for chunk in resp.aiter_bytes():
                        if not chunk:
                            continue
                        content.extend(chunk)
                        if len(content) > _MAX_FETCH_BYTES:
                            return {
                                "status": "error",
                                "detail": "Response body exceeds 10 MiB limit",
                            }

                    text = content.decode(resp.encoding or "utf-8", errors="replace")
                    break
            else:
                return {"status": "error", "detail": "Too many redirect hops"}
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
        await chroma_store.add_documents_async(docs)
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
    results = await chroma_store.query_async(query, n_results=top_k, where=where_filter)

    return {
        "status": "ok",
        "query": query,
        "results": results,
    }
