"""Built-in tool handlers for OsMEN-OC agents.

Each handler is registered on the global :data:`~core.gateway.handlers.handler_registry`
at import time.  Import this module during startup to activate them.

Implemented handlers:

knowledge_librarian
- ``ingest_url`` — fetch + chunk + store in ChromaDB.
- ``search_knowledge`` — semantic query against ChromaDB.
- ``transcribe_audio`` — whisper CLI transcription + ChromaDB ingest.

daily_brief
- ``generate_brief`` — morning/evening briefing via GLM API (ZAI_API_KEY).
- ``fetch_task_summary`` — Taskwarrior task export grouped by project.

media_organization
- ``transfer_to_plex`` — move downloads to PLEX_LIBRARY_ROOT.
- ``audit_vpn`` — verify gluetun VPN container is connected.
- ``list_downloads`` — aggregate qBittorrent + SABnzbd download lists.
- ``purge_completed`` — delete old staged downloads from DOWNLOAD_STAGING_DIR.
"""

from __future__ import annotations

import hashlib as _hashlib
import ipaddress as _ipaddress
import json as _json
import os as _os
import re as _re
import shutil as _shutil
import socket as _socket
from datetime import UTC as _UTC
from datetime import datetime as _datetime
from pathlib import Path as _Path
from typing import Any
from urllib.parse import urlparse as _urlparse

import anyio as _anyio
import httpx as _httpx
from loguru import logger

from core.gateway.handlers import HandlerContext, register_handler
from core.memory.chunking import chunk_text

_MAX_FETCH_BYTES = 10 * 1024 * 1024  # 10 MiB
_ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "application/xhtml+xml",
    "text/xml",
}

# Audio/video file extensions supported by whisper transcription.
_AUDIO_VIDEO_EXTENSIONS = frozenset(
    {
        ".mp3", ".mp4", ".wav", ".flac", ".m4a", ".ogg", ".webm",
        ".mkv", ".avi", ".mov", ".opus", ".aac",
    }
)

# Valid media types for Plex library routing.
_PLEX_MEDIA_TYPES = frozenset({"movies", "tv", "music", "audiobooks"})

# qBittorrent torrent state → normalised status string.
_QBT_STATE_MAP: dict[str, str] = {
    "downloading": "active",
    "stalledDL": "active",
    "metaDL": "active",
    "forcedDL": "active",
    "checkingDL": "active",
    "uploading": "completed",
    "stalledUP": "completed",
    "forcedUP": "completed",
    "checkingUP": "completed",
    "queuedDL": "paused",
    "queuedUP": "paused",
    "pausedDL": "paused",
    "pausedUP": "paused",
    "error": "paused",
    "missingFiles": "paused",
    "moving": "active",
    "unknown": "paused",
}

# GLM API endpoint (Coding API, OpenAI-compatible).
_GLM_API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
_GLM_DEFAULT_MODEL = "glm-4"
_GLM_RATE_LIMIT_CODE = 1302

# Bytes per megabyte — used for SABnzbd size conversion.
_MB_TO_BYTES = 1024 * 1024


def _qbt_state_to_status(state: str) -> str:
    return _QBT_STATE_MAP.get(state, "paused")


def _sabnzbd_status_to_status(state: str) -> str:
    state_lower = state.lower()
    if state_lower in ("downloading", "fetching", "verifying", "repairing", "extracting"):
        return "active"
    if state_lower in ("completed", "moved"):
        return "completed"
    return "paused"


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

    # Fetch content with streaming + hard cap to prevent oversized responses.
    try:
        async with _httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
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


# ---------------------------------------------------------------------------
# daily_brief handlers
# ---------------------------------------------------------------------------


@register_handler("fetch_task_summary")
async def handle_fetch_task_summary(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Retrieve open Taskwarrior tasks grouped by project.

    Optional parameters:
        limit: Maximum total tasks to return (default 20).
    """
    limit = int(parameters.get("limit", 20))
    if limit <= 0:
        return {"status": "error", "detail": "limit must be a positive integer"}

    try:
        with _anyio.fail_after(15):
            result = await _anyio.run_process(
                ["task", "export", "status:pending"],
                check=False,
            )
    except FileNotFoundError:
        return {"status": "error", "detail": "taskwarrior not installed"}
    except TimeoutError:
        return {"status": "error", "detail": "task export timed out"}

    # task returns exit code 1 when the filter matches nothing — that is OK.
    if result.returncode not in (0, 1):
        return {
            "status": "error",
            "detail": f"task export failed: {result.stderr.decode(errors='replace')[:200]}",
        }

    raw = result.stdout.decode(errors="replace").strip()
    if not raw:
        return {"status": "ok", "total": 0, "projects": {}}

    try:
        tasks: list[dict[str, Any]] = _json.loads(raw)
    except _json.JSONDecodeError as exc:
        return {"status": "error", "detail": f"Failed to parse task export JSON: {exc}"}

    projects: dict[str, list[dict[str, Any]]] = {}
    capped = tasks[:limit]
    for task in capped:
        project = task.get("project") or "(none)"
        projects.setdefault(project, []).append(
            {
                "id": task.get("id"),
                "description": task.get("description"),
                "urgency": task.get("urgency"),
                "due": task.get("due"),
                "priority": task.get("priority"),
                "tags": task.get("tags", []),
            }
        )

    returned = sum(len(v) for v in projects.values())
    logger.info(
        "fetch_task_summary: returning {} of {} tasks across {} projects",
        returned,
        len(tasks),
        len(projects),
    )
    return {"status": "ok", "total": len(tasks), "projects": projects}


@register_handler("generate_brief")
async def handle_generate_brief(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Produce a morning or evening briefing via the GLM API.

    Required parameters:
        period: ``"morning"`` or ``"evening"``.

    Optional parameters:
        date: ISO-8601 date string (defaults to today in UTC).
    """
    period = parameters.get("period")
    if period not in ("morning", "evening"):
        return {"status": "error", "detail": "period must be 'morning' or 'evening'"}

    date_str = parameters.get("date") or _datetime.now(_UTC).strftime("%Y-%m-%d")

    api_key = _os.environ.get("ZAI_API_KEY")
    if not api_key:
        return {"status": "error", "detail": "ZAI_API_KEY not configured"}

    greeting = "Good morning" if period == "morning" else "Good evening"
    prompt = (
        f"{greeting}. Today is {date_str}. "
        f"Please generate a concise, helpful {period} briefing for the operator of OsMEN-OC. "
        "Include a brief overview of the day ahead (morning) or a summary of the day (evening), "
        "any reminders, and a motivating closing note. Keep it under 200 words."
    )

    try:
        async with _httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _GLM_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _GLM_DEFAULT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except _httpx.HTTPStatusError as exc:
        logger.warning("generate_brief GLM API HTTP error: {}", exc)
        return {"status": "error", "detail": f"GLM API HTTP error: {exc.response.status_code}"}
    except _httpx.HTTPError as exc:
        logger.warning("generate_brief GLM API request failed: {}", exc)
        return {"status": "error", "detail": f"GLM API request failed: {exc}"}

    # GLM rate-limit error is returned as a 200 with an error body.
    error_info = data.get("error") or {}
    if isinstance(error_info, dict) and error_info.get("code") == _GLM_RATE_LIMIT_CODE:
        logger.warning("generate_brief: GLM rate limit hit (1302), backoff required")
        return {"status": "error", "detail": "rate_limited", "retry_after": 120}

    try:
        text: str = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        return {"status": "error", "detail": f"Unexpected GLM API response shape: {exc}"}

    logger.info("generate_brief: {} briefing generated for {}", period, date_str)
    return {"status": "ok", "period": period, "date": date_str, "brief": text}


# ---------------------------------------------------------------------------
# knowledge_librarian handlers (continued)
# ---------------------------------------------------------------------------


@register_handler("transcribe_audio")
async def handle_transcribe_audio(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Transcribe a local audio/video file via the whisper CLI and ingest the transcript.

    Required parameters:
        file_path: Absolute path to the audio or video file.

    Optional parameters:
        language: BCP-47 language code (default ``"en"``).
    """
    file_path_str = parameters.get("file_path")
    if not file_path_str:
        return {"status": "error", "detail": "Missing required parameter: file_path"}

    file_path = _Path(file_path_str)
    if not file_path.is_absolute():
        return {"status": "error", "detail": "file_path must be an absolute path"}

    if not file_path.exists():
        return {"status": "error", "detail": f"File not found: {file_path}"}

    if file_path.suffix.lower() not in _AUDIO_VIDEO_EXTENSIONS:
        return {
            "status": "error",
            "detail": (
                f"Unsupported file type: {file_path.suffix!r}. "
                f"Supported: {', '.join(sorted(_AUDIO_VIDEO_EXTENSIONS))}"
            ),
        }

    language = parameters.get("language", "en")

    # Run whisper CLI; output a plain-text .txt file next to the source.
    try:
        with _anyio.fail_after(300):
            result = await _anyio.run_process(
                [
                    "whisper",
                    str(file_path),
                    "--language",
                    language,
                    "--output_format",
                    "txt",
                    "--output_dir",
                    str(file_path.parent),
                ],
                check=False,
            )
    except FileNotFoundError:
        return {
            "status": "error",
            "detail": "whisper CLI not installed (pip install openai-whisper)",
        }
    except TimeoutError:
        return {"status": "error", "detail": "transcription timed out after 5 minutes"}

    if result.returncode != 0:
        return {
            "status": "error",
            "detail": f"whisper failed: {result.stderr.decode(errors='replace')[:200]}",
        }

    transcript_path = file_path.with_suffix(".txt")
    if not transcript_path.exists():
        return {"status": "error", "detail": "whisper ran but no transcript file was produced"}

    transcript = transcript_path.read_text(encoding="utf-8", errors="replace")

    chunks = chunk_text(transcript, max_chunk_tokens=512, overlap_tokens=64)

    chroma_store = getattr(context.app_state, "chroma_store", None) if context.app_state else None
    if chroma_store is not None:
        from core.memory.store import MemoryDocument

        docs = [
            MemoryDocument(
                id=_hashlib.sha256(f"{file_path}:{i}".encode()).hexdigest()[:16],
                text=chunk,
                metadata={
                    "source": str(file_path),
                    "chunk_index": i,
                    "language": language,
                    "collection": "transcripts",
                },
            )
            for i, chunk in enumerate(chunks)
        ]
        await chroma_store.add_documents_async(docs)
        logger.info(
            "transcribe_audio: {} chunks from {} stored in ChromaDB", len(docs), file_path.name
        )
    else:
        logger.warning(
            "transcribe_audio: ChromaDB not configured; {} chunks not stored", len(chunks)
        )

    return {
        "status": "ok",
        "file_path": str(file_path),
        "language": language,
        "transcript_length": len(transcript),
        "chunks": len(chunks),
        "stored": chroma_store is not None,
    }


# ---------------------------------------------------------------------------
# media_organization handlers
# ---------------------------------------------------------------------------


@register_handler("transfer_to_plex")
async def handle_transfer_to_plex(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Move a completed download into the Plex library directory.

    Required parameters:
        source_path: Absolute path of the completed download.
        media_type: Library category — one of ``movies``, ``tv``, ``music``, ``audiobooks``.
    """
    source_path_str = parameters.get("source_path")
    if not source_path_str:
        return {"status": "error", "detail": "Missing required parameter: source_path"}

    media_type = parameters.get("media_type")
    if media_type not in _PLEX_MEDIA_TYPES:
        return {
            "status": "error",
            "detail": f"media_type must be one of: {', '.join(sorted(_PLEX_MEDIA_TYPES))}",
        }

    source = _Path(source_path_str)
    if not source.is_absolute():
        return {"status": "error", "detail": "source_path must be an absolute path"}

    if not source.exists():
        return {"status": "error", "detail": f"Source not found: {source}"}

    library_root = _os.environ.get("PLEX_LIBRARY_ROOT")
    if not library_root:
        return {"status": "error", "detail": "PLEX_LIBRARY_ROOT not configured"}

    dest_dir = _Path(library_root) / media_type
    dest_path = dest_dir / source.name

    try:
        await _anyio.to_thread.run_sync(lambda: dest_dir.mkdir(parents=True, exist_ok=True))
        await _anyio.to_thread.run_sync(lambda: _shutil.move(str(source), str(dest_path)))
    except (OSError, _shutil.Error) as exc:
        logger.error("transfer_to_plex move failed: {}", exc)
        return {"status": "error", "detail": f"File move failed: {exc}"}

    logger.info("transfer_to_plex: {} → {}", source, dest_path)
    return {
        "status": "ok",
        "source": str(source),
        "destination": str(dest_path),
        "media_type": media_type,
    }


@register_handler("audit_vpn")
async def handle_audit_vpn(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Verify that the gluetun VPN container is connected.

    Checks that the ``osmen-media-gluetun`` Podman container is running, then
    queries an external IP service from inside the container.  The result
    distinguishes between *not running*, *running but unable to reach internet*,
    and *fully connected*.
    """
    # Step 1: check container is running.
    try:
        with _anyio.fail_after(10):
            inspect_result = await _anyio.run_process(
                ["podman", "inspect", "--format", "{{.State.Running}}", "osmen-media-gluetun"],
                check=False,
            )
        container_running = inspect_result.stdout.decode().strip().lower() == "true"
    except FileNotFoundError:
        return {"status": "error", "detail": "podman not installed"}
    except TimeoutError:
        return {"status": "error", "detail": "podman inspect timed out"}

    if not container_running:
        logger.warning("audit_vpn: gluetun container is not running")
        return {"status": "ok", "vpn_connected": False, "detail": "gluetun container not running"}

    # Step 2: obtain the public IP through the container network namespace.
    try:
        with _anyio.fail_after(20):
            exec_result = await _anyio.run_process(
                [
                    "podman",
                    "exec",
                    "osmen-media-gluetun",
                    "sh",
                    "-c",
                    (
                        "curl -sf --max-time 10 https://api.ipify.org"
                        " || wget -qO- --timeout=10 https://api.ipify.org"
                        " || true"
                    ),
                ],
                check=False,
            )
        vpn_ip = exec_result.stdout.decode().strip()
    except TimeoutError:
        return {"status": "error", "detail": "VPN IP check timed out"}

    if not vpn_ip:
        return {
            "status": "ok",
            "vpn_connected": False,
            "detail": "gluetun running but cannot reach external IP service",
        }

    logger.info("audit_vpn: VPN connected, public IP={}", vpn_ip)
    return {"status": "ok", "vpn_connected": True, "vpn_ip": vpn_ip}


@register_handler("list_downloads")
async def handle_list_downloads(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """List active and completed downloads from qBittorrent and SABnzbd.

    Optional parameters:
        status: Filter — one of ``active``, ``completed``, ``paused``, ``all`` (default).
    """
    status_filter = parameters.get("status", "all")
    if status_filter not in ("active", "completed", "paused", "all"):
        return {
            "status": "error",
            "detail": "status must be one of: active, completed, paused, all",
        }

    downloads: list[dict[str, Any]] = []
    errors: list[str] = []

    # --- qBittorrent ---
    qbt_url = _os.environ.get("QBITTORRENT_URL", "http://localhost:8080")
    try:
        async with _httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{qbt_url}/api/v2/torrents/info")
            resp.raise_for_status()
            torrents: list[dict[str, Any]] = resp.json()
        for torrent in torrents:
            dl_status = _qbt_state_to_status(torrent.get("state", ""))
            if status_filter in ("all", dl_status):
                downloads.append(
                    {
                        "source": "qbittorrent",
                        "name": torrent.get("name"),
                        "status": dl_status,
                        "progress": round(float(torrent.get("progress", 0)), 4),
                        "size_bytes": torrent.get("size", 0),
                    }
                )
    except _httpx.HTTPError as exc:
        errors.append(f"qBittorrent unavailable: {exc}")
        logger.debug("list_downloads qBittorrent error: {}", exc)

    # --- SABnzbd ---
    sabnzbd_url = _os.environ.get("SABNZBD_URL", "http://localhost:8085")
    sabnzbd_key = _os.environ.get("SABNZBD_API_KEY", "")
    if sabnzbd_key:
        try:
            async with _httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{sabnzbd_url}/api",
                    params={"apikey": sabnzbd_key, "output": "json", "mode": "queue"},
                )
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
            for slot in data.get("queue", {}).get("slots", []):
                dl_status = _sabnzbd_status_to_status(slot.get("status", ""))
                if status_filter in ("all", dl_status):
                    downloads.append(
                        {
                            "source": "sabnzbd",
                            "name": slot.get("filename"),
                            "status": dl_status,
                            "progress": round(float(slot.get("percentage", 0)) / 100, 4),
                            "size_bytes": int(float(slot.get("mb", 0)) * _MB_TO_BYTES),
                        }
                    )
        except _httpx.HTTPError as exc:
            errors.append(f"SABnzbd unavailable: {exc}")
            logger.debug("list_downloads SABnzbd error: {}", exc)
    else:
        logger.debug("list_downloads: SABNZBD_API_KEY not set, skipping SABnzbd")

    return {
        "status": "ok",
        "filter": status_filter,
        "total": len(downloads),
        "downloads": downloads,
        "errors": errors,
    }


@register_handler("purge_completed")
async def handle_purge_completed(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Delete completed download files from the staging area.

    Optional parameters:
        older_than_days: Only purge files/directories older than this many days (default 7).
    """
    older_than_days = int(parameters.get("older_than_days", 7))
    if older_than_days < 0:
        return {"status": "error", "detail": "older_than_days must be a non-negative integer"}

    staging_dir = _os.environ.get("DOWNLOAD_STAGING_DIR")
    if not staging_dir:
        return {"status": "error", "detail": "DOWNLOAD_STAGING_DIR not configured"}

    staging_path = _Path(staging_dir)
    if not staging_path.is_dir():
        return {"status": "error", "detail": f"Staging directory not found: {staging_dir}"}

    cutoff_ts = _datetime.now(_UTC).timestamp() - (older_than_days * 86400)

    purged: list[str] = []
    errors: list[str] = []

    def _do_purge() -> None:
        for item in staging_path.iterdir():
            try:
                if item.stat().st_mtime < cutoff_ts:
                    if item.is_dir() and not item.is_symlink():
                        _shutil.rmtree(item)
                    else:
                        item.unlink(missing_ok=True)
                    purged.append(str(item))
            except OSError as exc:
                errors.append(f"{item.name}: {exc}")
                logger.warning("purge_completed: could not remove {}: {}", item, exc)

    await _anyio.to_thread.run_sync(_do_purge)

    logger.info(
        "purge_completed: removed {} items from {} (cutoff={}d)",
        len(purged),
        staging_dir,
        older_than_days,
    )
    return {
        "status": "ok",
        "purged": len(purged),
        "files": purged,
        "errors": errors,
    }
