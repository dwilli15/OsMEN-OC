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

system_monitor
- ``get_hardware_metrics`` — CPU/GPU/fan metrics via lm-sensors, nvidia-smi, rocm-smi.
- ``set_power_profile`` — CPU/GPU TDP limits via ryzenadj / nvidia-smi.
- ``set_fan_curve`` — laptop fan speed via nbfc-linux.
- ``get_compute_routing`` — read compute-routing rules from config.
- ``set_compute_routing`` — add/update a single compute-routing rule.
- ``intake_compute_routing`` — 20-question interactive routing configuration interview.
- ``get_npu_status`` — XDNA 2 NPU status/utilization via xrt-smi (experimental).
"""

from __future__ import annotations

import hashlib as _hashlib
import ipaddress as _ipaddress
import json as _json
import os as _os
import re as _re
import secrets as _secrets
import shutil as _shutil
import socket as _socket
from datetime import UTC as _UTC
from datetime import datetime as _datetime
from pathlib import Path as _Path
from typing import Any
from urllib.parse import urljoin as _urljoin
from urllib.parse import urlparse as _urlparse

import anyio as _anyio
import httpx as _httpx
import yaml as _yaml
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

# Minimum free disk space (bytes) required for Plex readiness.
_PLEX_MIN_FREE_BYTES = 10 * 1024 * 1024 * 1024  # 10 GiB


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


@register_handler("assess_plex_readiness")
async def handle_assess_plex_readiness(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Assess whether the system is ready to accept Plex media transfers.

    Runs a set of read-only checks and returns a structured readiness report:

    - ``plex_library_root_configured`` — ``PLEX_LIBRARY_ROOT`` env var is set.
    - ``plex_library_root_exists`` — the configured path is an accessible directory.
    - ``disk_space`` — at least 10 GiB free at the library root.
      This check includes a ``free_gib`` field with the measured free space in GiB.
    - ``library_dir_<media_type>`` — per-media-type subdirectory exists.

    Returns:
        A dict with ``status``, ``ready`` (overall bool), and ``checks`` list.
        Each check entry has ``name``, ``passed``, and ``detail``.
        The ``disk_space`` check also includes ``free_gib`` (float, rounded to 2 dp).
    """
    checks: list[dict[str, Any]] = []

    # --- Check 1: PLEX_LIBRARY_ROOT is configured ---
    library_root_str = _os.environ.get("PLEX_LIBRARY_ROOT")
    if not library_root_str:
        checks.append(
            {
                "name": "plex_library_root_configured",
                "passed": False,
                "detail": "PLEX_LIBRARY_ROOT environment variable is not set",
            }
        )
        return {"status": "ok", "ready": False, "checks": checks}

    checks.append(
        {
            "name": "plex_library_root_configured",
            "passed": True,
            "detail": library_root_str,
        }
    )
    library_root = _Path(library_root_str)

    # --- Check 2: Library root directory exists ---
    root_exists = await _anyio.to_thread.run_sync(library_root.is_dir)
    checks.append(
        {
            "name": "plex_library_root_exists",
            "passed": root_exists,
            "detail": (
                str(library_root)
                if root_exists
                else f"Directory not found: {library_root}"
            ),
        }
    )

    if root_exists:
        # --- Check 3: Disk space ---
        try:
            usage = await _anyio.to_thread.run_sync(
                lambda: _shutil.disk_usage(str(library_root))
            )
            free_gib = usage.free / (1024**3)
            min_free_gib = _PLEX_MIN_FREE_BYTES / (1024**3)
            space_ok = usage.free >= _PLEX_MIN_FREE_BYTES
            checks.append(
                {
                    "name": "disk_space",
                    "passed": space_ok,
                    "free_gib": round(free_gib, 2),
                    "detail": (
                        f"{free_gib:.1f} GiB free"
                        if space_ok
                        else (
                            f"Low disk space: {free_gib:.1f} GiB free"
                            f" (need ≥ {min_free_gib:.0f} GiB)"
                        )
                    ),
                }
            )
        except OSError as exc:
            checks.append(
                {
                    "name": "disk_space",
                    "passed": False,
                    "detail": f"Could not check disk space: {exc}",
                }
            )

        # --- Check 4: Per-media-type subdirectories ---
        for media_type in sorted(_PLEX_MEDIA_TYPES):
            subdir = library_root / media_type
            subdir_exists = await _anyio.to_thread.run_sync(subdir.is_dir)
            checks.append(
                {
                    "name": f"library_dir_{media_type}",
                    "passed": subdir_exists,
                    "detail": (
                        str(subdir) if subdir_exists else f"Missing subdirectory: {subdir}"
                    ),
                }
            )

    ready = all(c["passed"] for c in checks)
    logger.info(
        "assess_plex_readiness: ready={}, passed={}/{}",
        ready,
        sum(1 for c in checks if c["passed"]),
        len(checks),
    )
    return {"status": "ok", "ready": ready, "checks": checks}


# ---------------------------------------------------------------------------
# system_monitor — constants
# ---------------------------------------------------------------------------

# Path to compute-routing config, relative to this file's package root.
# Override via COMPUTE_ROUTING_CONFIG env var for testing.
_COMPUTE_ROUTING_DEFAULT = _Path(__file__).parent.parent.parent / "config" / "compute-routing.yaml"

# Named power profiles matching config/hardware.yaml.
_POWER_PROFILES: dict[str, dict[str, int]] = {
    "quiet": {
        "amd_stapm_watts": 15,
        "amd_fast_watts": 20,
        "amd_slow_watts": 15,
        "nvidia_power_limit_watts": 35,
    },
    "balanced": {
        "amd_stapm_watts": 28,
        "amd_fast_watts": 35,
        "amd_slow_watts": 28,
        "nvidia_power_limit_watts": 60,
    },
    "performance": {
        "amd_stapm_watts": 45,
        "amd_fast_watts": 54,
        "amd_slow_watts": 45,
        "nvidia_power_limit_watts": 80,
    },
}

# Valid target_compute values for routing rules.
_VALID_COMPUTE_TARGETS = frozenset({"nvidia", "amd_rocm", "amd_vulkan", "npu", "cpu"})

# Valid task_type values for routing rule triggers.
_VALID_TASK_TYPES = frozenset({"inference", "rendering", "gaming", "transcription", "embedding"})

# Directory for intake interview session files.
# Stored under the user's home cache directory with restricted permissions (0o700)
# so other users on the same system cannot read configuration answers.
_INTAKE_SESSION_DIR = _Path.home() / ".cache" / "osmen" / "intake_sessions"

# 20-question intake interview definition.
# Each entry: id, text, type ("yn" or "text"), help text.
_INTAKE_QUESTIONS: list[dict[str, str]] = [
    {
        "id": "q01_gaming_primary",
        "text": (
            "Is gaming (e.g. FFXIV, Proton/Wine games) a primary workload"
            " that needs dedicated NVIDIA GPU time?"
        ),
        "type": "yn",
        "help": "Answering yes creates a rule that pins named game processes to the NVIDIA dGPU.",
    },
    {
        "id": "q02_gaming_offload_inference",
        "text": (
            "When a game is running on NVIDIA, should inference workloads"
            " automatically move off NVIDIA to avoid stuttering?"
        ),
        "type": "yn",
        "help": (
            "Answering yes creates a high-priority rule routing inference"
            " away from NVIDIA during gaming sessions."
        ),
    },
    {
        "id": "q03_npu_first_inference",
        "text": (
            "Should the NPU be the first choice for LLM inference"
            " when it is available and the model fits?"
        ),
        "type": "yn",
        "help": "Requires amdxdna driver and AMD XRT. Falls back to amd_vulkan if NPU is busy.",
    },
    {
        "id": "q04_nvidia_large_models",
        "text": (
            "Should NVIDIA CUDA be used for large model inference"
            " (models requiring ≥ 8 GiB VRAM)?"
        ),
        "type": "yn",
        "help": "Large models typically exceed NPU and iGPU capacity.",
    },
    {
        "id": "q05_amd_vulkan_fallback",
        "text": (
            "Should the AMD iGPU (Radeon / Vulkan) serve as a fallback"
            " when the NPU is busy or unavailable?"
        ),
        "type": "yn",
        "help": "Answering yes enables amd_vulkan as the secondary compute target for inference.",
    },
    {
        "id": "q06_transcription_nvidia",
        "text": "Should audio transcription (Whisper) run on NVIDIA CUDA for maximum speed?",
        "type": "yn",
        "help": "Answering no will route transcription to the NPU or amd_vulkan instead.",
    },
    {
        "id": "q07_embedding_npu",
        "text": (
            "Should embedding generation (ChromaDB ingest, sentence-transformers)"
            " run on the NPU for power efficiency?"
        ),
        "type": "yn",
        "help": "Embeddings are small and continuous — ideal for NPU's low-power profile.",
    },
    {
        "id": "q08_cpu_fallback",
        "text": (
            "Should a CPU-only fallback be available for inference"
            " when all GPUs/NPU are saturated?"
        ),
        "type": "yn",
        "help": "Adds a lowest-priority fallback rule so inference never fails entirely.",
    },
    {
        "id": "q09_igpu_display_only",
        "text": (
            "Should the AMD iGPU handle display rendering and compositing"
            " exclusively (NVIDIA never used for display)?"
        ),
        "type": "yn",
        "help": "Standard for hybrid GPU laptops where the iGPU drives all display outputs.",
    },
    {
        "id": "q10_extra_game_processes",
        "text": (
            "Are there additional games or applications (other than FFXIV)"
            " you want to pin to the NVIDIA GPU?"
        ),
        "type": "yn",
        "help": "Answering yes will prompt you to list the process names in the next question.",
    },
    {
        "id": "q11_extra_process_names",
        "text": (
            "Enter additional process names to pin to NVIDIA"
            " (comma-separated, e.g. eldenring.exe,GenshinImpact.exe), or 'none'."
        ),
        "type": "text",
        "help": (
            "Exact executable names as they appear in 'ps aux'"
            " or Task Manager (for Proton games)."
        ),
    },
    {
        "id": "q12_quiet_npu_preference",
        "text": (
            "Should the quiet/power-saving power profile automatically"
            " shift inference to NPU instead of NVIDIA?"
        ),
        "type": "yn",
        "help": "Improves battery life by avoiding the discrete GPU when in quiet mode.",
    },
    {
        "id": "q13_image_gen_workload",
        "text": "Do you run Stable Diffusion or other image generation workloads?",
        "type": "yn",
        "help": "Image generation workloads benefit from large VRAM and fast memory bandwidth.",
    },
    {
        "id": "q14_image_gen_nvidia",
        "text": "Should image generation (Stable Diffusion) use NVIDIA CUDA as the primary target?",
        "type": "yn",
        "help": (
            "NVIDIA CUDA offers the widest compatibility for diffusion libraries"
            " (torch, diffusers)."
        ),
    },
    {
        "id": "q15_vulkan_over_rocm",
        "text": (
            "For AMD GPU inference, prefer the Vulkan backend (llama.cpp)"
            " over ROCm (torch/HIP)?"
        ),
        "type": "yn",
        "help": (
            "Vulkan backend has broader GPU support; ROCm offers better BLAS throughput"
            " when properly installed."
        ),
    },
    {
        "id": "q16_power_efficiency_first",
        "text": (
            "Should power efficiency be the top priority, meaning NPU is preferred"
            " over NVIDIA even for medium workloads?"
        ),
        "type": "yn",
        "help": (
            "Answering yes lowers NVIDIA's effective priority vs. NPU for most"
            " non-gaming workloads."
        ),
    },
    {
        "id": "q17_route_away_when_gaming",
        "text": (
            "Should inference automatically route to CPU when NVIDIA 3D utilisation"
            " is above 50% (active gaming)?"
        ),
        "type": "yn",
        "help": "Prevents inference from stealing VRAM/memory bandwidth mid-game.",
    },
    {
        "id": "q18_rag_npu",
        "text": (
            "For research and RAG query inference, prefer NPU (energy efficient)"
            " over NVIDIA (maximum throughput)?"
        ),
        "type": "yn",
        "help": "RAG queries are frequent and short — NPU provides lower latency at lower power.",
    },
    {
        "id": "q19_medium_model_nvidia_fallback",
        "text": (
            "For medium models (2–8 GiB) that exceed NPU capacity,"
            " fall back to NVIDIA CUDA (instead of amd_vulkan)?"
        ),
        "type": "yn",
        "help": (
            "Answering yes prioritises throughput; no prioritises"
            " keeping NVIDIA free for gaming."
        ),
    },
    {
        "id": "q20_commit",
        "text": (
            "Commit these rules to config/compute-routing.yaml now?"
            " (Existing rules will be replaced.)"
        ),
        "type": "yn",
        "help": "Answering no saves the session so you can review, but does not write the file.",
    },
]


def _compute_routing_path() -> _Path:
    """Return the active compute-routing config path.

    Respects ``COMPUTE_ROUTING_CONFIG`` env var for testing.
    """
    override = _os.environ.get("COMPUTE_ROUTING_CONFIG")
    return _Path(override) if override else _COMPUTE_ROUTING_DEFAULT


def _build_routing_rules(answers: dict[str, str]) -> list[dict[str, Any]]:
    """Convert intake interview answers into compute-routing rule dicts.

    Args:
        answers: Mapping of question_id → answer string ("yes"/"no"/text).

    Returns:
        Ordered list of routing rule dicts ready for YAML serialisation.
    """

    def yes(qid: str) -> bool:
        return answers.get(qid, "no").strip().lower() in ("yes", "y", "true", "1")

    rules: list[dict[str, Any]] = []
    priority_counter = [100]  # mutable so nested helpers can decrement

    def next_priority() -> int:
        p = priority_counter[0]
        priority_counter[0] -= 5
        return p

    # Rule: pin extra game processes + FFXIV to NVIDIA.
    game_processes: list[str] = []
    if yes("q01_gaming_primary"):
        game_processes.extend(["ffxiv_dx11.exe", "ffxiv_dx9.exe"])
    extra_raw = answers.get("q11_extra_process_names", "none").strip()
    if extra_raw.lower() != "none" and extra_raw:
        game_processes.extend([p.strip() for p in extra_raw.split(",") if p.strip()])
    if game_processes:
        rules.append(
            {
                "id": "gaming_process_nvidia",
                "description": "Pin known game processes to the NVIDIA dGPU.",
                "trigger": {"process_names": game_processes},
                "action": {"target_compute": "nvidia"},
                "priority": next_priority(),
            }
        )

    # Rule: when gaming, route inference away from NVIDIA.
    if yes("q01_gaming_primary") and yes("q02_gaming_offload_inference"):
        if yes("q03_npu_first_inference"):
            fallback = "npu"
        elif yes("q05_amd_vulkan_fallback"):
            fallback = "amd_vulkan"
        else:
            fallback = "cpu"
        rules.append(
            {
                "id": "inference_offload_when_gaming",
                "description": "Route inference away from NVIDIA while a game process is running.",
                "trigger": {"task_type": "inference", "condition": "gaming_process_active"},
                "action": {"target_compute": fallback},
                "priority": next_priority(),
            }
        )

    # Rule: rendering → amd_vulkan (iGPU).
    if yes("q09_igpu_display_only"):
        rules.append(
            {
                "id": "rendering_amd_vulkan",
                "description": "Desktop rendering and compositing use AMD iGPU via Vulkan.",
                "trigger": {"task_type": "rendering"},
                "action": {"target_compute": "amd_vulkan"},
                "priority": next_priority(),
            }
        )

    # Rule: image generation → NVIDIA.
    if yes("q13_image_gen_workload") and yes("q14_image_gen_nvidia"):
        rules.append(
            {
                "id": "image_generation_nvidia",
                "description": "Stable Diffusion and image generation use NVIDIA CUDA.",
                "trigger": {
                    "task_type": "rendering",
                    "process_names": ["sd_webui", "comfyui", "invokeai"],
                },
                "action": {"target_compute": "nvidia"},
                "priority": next_priority(),
            }
        )

    # Rule: transcription → NVIDIA or NPU/Vulkan.
    if yes("q06_transcription_nvidia"):
        transcription_target = "nvidia"
        transcription_fallback = "npu" if yes("q03_npu_first_inference") else "amd_vulkan"
    else:
        transcription_target = "npu" if yes("q03_npu_first_inference") else "amd_vulkan"
        transcription_fallback = "amd_vulkan" if transcription_target == "npu" else "cpu"
    rules.append(
        {
            "id": "transcription_routing",
            "description": "Audio transcription (Whisper) routing.",
            "trigger": {"task_type": "transcription"},
            "action": {"target_compute": transcription_target, "fallback": transcription_fallback},
            "priority": next_priority(),
        }
    )

    # Rule: large model inference (≥ 8 GiB) → NVIDIA.
    if yes("q04_nvidia_large_models"):
        rules.append(
            {
                "id": "inference_large_model_nvidia",
                "description": "Large LLM inference (≥ 8 GiB VRAM) uses NVIDIA CUDA.",
                "trigger": {"task_type": "inference", "model_size_gb_min": 8},
                "action": {"target_compute": "nvidia"},
                "priority": next_priority(),
            }
        )

    # Rule: medium model inference (2–8 GiB) → NPU or NVIDIA fallback.
    if yes("q03_npu_first_inference"):
        med_fallback = "nvidia" if yes("q19_medium_model_nvidia_fallback") else "amd_vulkan"
        rules.append(
            {
                "id": "inference_medium_model",
                "description": "Medium LLM inference (2–8 GiB) uses NPU; falls back when busy.",
                "trigger": {
                    "task_type": "inference",
                    "model_size_gb_min": 2,
                    "model_size_gb_max": 8,
                },
                "action": {"target_compute": "npu", "fallback": med_fallback},
                "priority": next_priority(),
            }
        )
    elif yes("q04_nvidia_large_models"):
        # NPU not preferred but medium models don't hit the large-model threshold
        rules.append(
            {
                "id": "inference_medium_model",
                "description": "Medium LLM inference (2–8 GiB) uses NVIDIA CUDA.",
                "trigger": {
                    "task_type": "inference",
                    "model_size_gb_min": 2,
                    "model_size_gb_max": 8,
                },
                "action": {"target_compute": "nvidia"},
                "priority": next_priority(),
            }
        )

    # Rule: small model inference (< 2 GiB) → NPU or amd_vulkan.
    if yes("q03_npu_first_inference") or yes("q16_power_efficiency_first"):
        small_target = "npu"
        small_fallback = "amd_vulkan" if yes("q05_amd_vulkan_fallback") else "cpu"
        rules.append(
            {
                "id": "inference_small_model",
                "description": "Small LLM inference (< 2 GiB) uses NPU for power efficiency.",
                "trigger": {"task_type": "inference", "model_size_gb_max": 2},
                "action": {"target_compute": small_target, "fallback": small_fallback},
                "priority": next_priority(),
            }
        )

    # Rule: RAG / research queries.
    if yes("q18_rag_npu"):
        rag_target = "npu"
        rag_fallback = "amd_vulkan" if yes("q05_amd_vulkan_fallback") else "cpu"
    else:
        rag_target = "nvidia" if yes("q04_nvidia_large_models") else "amd_vulkan"
        rag_fallback = "cpu"
    rules.append(
        {
            "id": "rag_inference",
            "description": "Research and RAG query inference routing.",
            "trigger": {"task_type": "inference", "context": "rag"},
            "action": {"target_compute": rag_target, "fallback": rag_fallback},
            "priority": next_priority(),
        }
    )

    # Rule: embedding generation.
    if yes("q07_embedding_npu"):
        embed_target = "npu"
        embed_fallback = "amd_vulkan" if yes("q05_amd_vulkan_fallback") else "cpu"
        rules.append(
            {
                "id": "embedding_npu",
                "description": "Embedding generation uses NPU for continuous low-power operation.",
                "trigger": {"task_type": "embedding"},
                "action": {"target_compute": embed_target, "fallback": embed_fallback},
                "priority": next_priority(),
            }
        )

    # Rule: route inference to CPU when gaming (NVIDIA utilisation > 50%).
    if yes("q17_route_away_when_gaming"):
        rules.append(
            {
                "id": "inference_cpu_during_gaming",
                "description": "Route inference to CPU when NVIDIA GPU 3D utilisation > 50%.",
                "trigger": {"task_type": "inference", "condition": "nvidia_3d_utilization_gt_50"},
                "action": {"target_compute": "cpu"},
                "priority": next_priority(),
            }
        )

    # Rule: CPU fallback.
    if yes("q08_cpu_fallback"):
        rules.append(
            {
                "id": "cpu_fallback",
                "description": "CPU-only fallback when all GPUs/NPU are saturated.",
                "trigger": {"task_type": "inference", "condition": "all_gpu_busy"},
                "action": {"target_compute": "cpu"},
                "priority": 1,
            }
        )

    return rules


# ---------------------------------------------------------------------------
# system_monitor handlers
# ---------------------------------------------------------------------------


@register_handler("get_hardware_metrics")
async def handle_get_hardware_metrics(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Read CPU, GPU, fan, and thermal metrics.

    Uses lm-sensors (``sensors -j``), ``nvidia-smi``, and ``rocm-smi``.
    Each source degrades gracefully when the CLI tool is not installed.

    Returns:
        Dict with ``status``, and optional ``cpu``, ``nvidia``, ``amd``
        sections, plus ``errors`` list for any unavailable tools.
    """
    result: dict[str, Any] = {"status": "ok", "errors": []}

    # --- lm-sensors: CPU temps, fan RPMs, voltage rails ---
    try:
        with _anyio.fail_after(10):
            sensors_proc = await _anyio.run_process(["sensors", "-j"], check=False)
        if sensors_proc.returncode == 0:
            try:
                result["cpu"] = _json.loads(sensors_proc.stdout.decode())
            except _json.JSONDecodeError as exc:
                result["errors"].append(f"sensors JSON parse error: {exc}")
        else:
            result["errors"].append(
                f"sensors exited {sensors_proc.returncode}: "
                f"{sensors_proc.stderr.decode(errors='replace').strip()}"
            )
    except FileNotFoundError:
        result["errors"].append("lm-sensors not installed (apt install lm-sensors)")
    except TimeoutError:
        result["errors"].append("sensors command timed out")

    # --- nvidia-smi: GPU utilisation, power, temp, clocks ---
    _nvidia_fields = (
        "name,temperature.gpu,utilization.gpu,utilization.memory,"
        "power.draw,power.limit,clocks.current.graphics,clocks.current.memory,"
        "memory.used,memory.total"
    )
    try:
        with _anyio.fail_after(10):
            nv_proc = await _anyio.run_process(
                ["nvidia-smi", f"--query-gpu={_nvidia_fields}", "--format=csv,noheader,nounits"],
                check=False,
            )
        if nv_proc.returncode == 0:
            lines = nv_proc.stdout.decode().strip().splitlines()
            fields = [f.strip() for f in _nvidia_fields.split(",")]
            gpus = []
            for line in lines:
                vals = [v.strip() for v in line.split(",")]
                gpus.append(dict(zip(fields, vals)))
            result["nvidia"] = gpus
        else:
            result["errors"].append(
                f"nvidia-smi exited {nv_proc.returncode}: "
                f"{nv_proc.stderr.decode(errors='replace').strip()}"
            )
    except FileNotFoundError:
        result["errors"].append("nvidia-smi not available (NVIDIA driver not installed)")
    except TimeoutError:
        result["errors"].append("nvidia-smi timed out")

    # --- rocm-smi: AMD GPU utilisation, power, temp ---
    try:
        with _anyio.fail_after(10):
            amd_proc = await _anyio.run_process(
                ["rocm-smi", "--showuse", "--showpower", "--showtemp", "--json"],
                check=False,
            )
        if amd_proc.returncode == 0:
            try:
                result["amd"] = _json.loads(amd_proc.stdout.decode())
            except _json.JSONDecodeError:
                result["errors"].append("rocm-smi JSON parse error")
        else:
            result["errors"].append(
                f"rocm-smi exited {amd_proc.returncode}: "
                f"{amd_proc.stderr.decode(errors='replace').strip()}"
            )
    except FileNotFoundError:
        result["errors"].append("rocm-smi not available (ROCm not installed)")
    except TimeoutError:
        result["errors"].append("rocm-smi timed out")

    logger.debug("get_hardware_metrics: errors={}", result["errors"])
    return result


@register_handler("set_power_profile")
async def handle_set_power_profile(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Set CPU and/or GPU power limits.

    For AMD CPUs: uses ``ryzenadj`` (Zen2/3/4/5 mobile APUs).
    For NVIDIA GPUs: uses ``nvidia-smi -pl``.

    Accepts either a named profile (balanced/performance/quiet) or explicit
    watt values.  Explicit values override the profile.

    Returns:
        Dict with ``status`` and ``applied`` list of changes made.
    """
    profile_name = parameters.get("profile")
    profile_defaults: dict[str, int] = {}
    if profile_name:
        if profile_name not in _POWER_PROFILES:
            return {
                "status": "error",
                "detail": f"Unknown profile '{profile_name}'. Valid: {sorted(_POWER_PROFILES)}",
            }
        profile_defaults = dict(_POWER_PROFILES[profile_name])

    amd_stapm = parameters.get("amd_stapm_watts", profile_defaults.get("amd_stapm_watts"))
    amd_fast = parameters.get("amd_fast_watts", profile_defaults.get("amd_fast_watts"))
    amd_slow = parameters.get("amd_slow_watts", profile_defaults.get("amd_slow_watts"))
    nvidia_pl = parameters.get(
        "nvidia_power_limit_watts", profile_defaults.get("nvidia_power_limit_watts")
    )

    if all(v is None for v in (amd_stapm, amd_fast, amd_slow, nvidia_pl)):
        return {
            "status": "error",
            "detail": "No power limits specified. Provide a profile or explicit watt values.",
        }

    applied: list[str] = []
    errors: list[str] = []

    # --- ryzenadj: AMD CPU power ---
    if any(v is not None for v in (amd_stapm, amd_fast, amd_slow)):
        ryzenadj_args = ["ryzenadj"]
        if amd_stapm is not None:
            ryzenadj_args += [f"--stapm-limit={int(amd_stapm) * 1000}"]  # ryzenadj uses milliwatts
        if amd_fast is not None:
            ryzenadj_args += [f"--fast-limit={int(amd_fast) * 1000}"]
        if amd_slow is not None:
            ryzenadj_args += [f"--slow-limit={int(amd_slow) * 1000}"]
        try:
            with _anyio.fail_after(10):
                rj_proc = await _anyio.run_process(ryzenadj_args, check=False)
            if rj_proc.returncode == 0:
                applied.append(
                    f"ryzenadj: stapm={amd_stapm}W fast={amd_fast}W slow={amd_slow}W"
                )
                logger.info("set_power_profile ryzenadj: {}", applied[-1])
            else:
                err = rj_proc.stderr.decode(errors="replace").strip()
                errors.append(f"ryzenadj failed (rc={rj_proc.returncode}): {err}")
                logger.warning("set_power_profile ryzenadj error: {}", err)
        except FileNotFoundError:
            errors.append(
                "ryzenadj not installed. Compatible with Zen2/3/4/5 mobile CPUs. "
                "Install from https://github.com/FlyGoat/RyzenAdj"
            )
        except TimeoutError:
            errors.append("ryzenadj timed out")

    # --- nvidia-smi: NVIDIA GPU power limit ---
    if nvidia_pl is not None:
        try:
            with _anyio.fail_after(10):
                nv_proc = await _anyio.run_process(
                    ["nvidia-smi", "-pl", str(int(nvidia_pl))], check=False
                )
            if nv_proc.returncode == 0:
                applied.append(f"nvidia-smi: power_limit={nvidia_pl}W")
                logger.info("set_power_profile nvidia: {}", applied[-1])
            else:
                err = nv_proc.stderr.decode(errors="replace").strip()
                errors.append(f"nvidia-smi -pl failed (rc={nv_proc.returncode}): {err}")
                logger.warning("set_power_profile nvidia error: {}", err)
        except FileNotFoundError:
            errors.append("nvidia-smi not available (NVIDIA driver not installed)")
        except TimeoutError:
            errors.append("nvidia-smi timed out")

    status = "ok" if applied else "error"
    return {"status": status, "applied": applied, "errors": errors}


@register_handler("set_fan_curve")
async def handle_set_fan_curve(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Control laptop fan speed via nbfc-linux.

    Args:
        speed_percent: Fan speed 0–100 as a string, or ``"auto"`` for
            automatic firmware control.
        fan_index: Fan index for multi-fan systems (default: all fans).

    Returns:
        Dict with ``status``, ``detail``, and any ``error``.
    """
    speed_raw = parameters.get("speed_percent", "")
    if not speed_raw:
        return {"status": "error", "detail": "speed_percent is required"}

    fan_index = parameters.get("fan_index")

    if str(speed_raw).lower() == "auto":
        # Auto mode: restore firmware control.
        nbfc_args = ["nbfc", "set", "--auto"]
        if fan_index is not None:
            nbfc_args += ["--fan", str(int(fan_index))]
        speed_label = "auto"
    else:
        try:
            speed_val = int(speed_raw)
        except (ValueError, TypeError):
            return {
                "status": "error",
                "detail": (
                    f"speed_percent must be an integer 0–100 or 'auto',"
                    f" got: {speed_raw!r}"
                ),
            }
        if not (0 <= speed_val <= 100):
            return {"status": "error", "detail": "speed_percent must be between 0 and 100"}
        nbfc_args = ["nbfc", "set", "--speed", str(speed_val)]
        if fan_index is not None:
            nbfc_args += ["--fan", str(int(fan_index))]
        speed_label = f"{speed_val}%"

    try:
        with _anyio.fail_after(10):
            proc = await _anyio.run_process(nbfc_args, check=False)
        if proc.returncode == 0:
            detail = (
                f"Fan {'#' + str(fan_index) if fan_index is not None else 'all'} "
                f"set to {speed_label}"
            )
            logger.info("set_fan_curve: {}", detail)
            return {"status": "ok", "detail": detail}
        err = (
            proc.stderr.decode(errors="replace").strip()
            or proc.stdout.decode(errors="replace").strip()
        )
        return {"status": "error", "detail": f"nbfc failed (rc={proc.returncode}): {err}"}
    except FileNotFoundError:
        return {
            "status": "error",
            "detail": (
                "nbfc-linux not installed or not in PATH. "
                "Install from https://github.com/nbfc-linux/nbfc-linux and "
                "enable the service: systemctl --user enable --now nbfc"
            ),
        }
    except TimeoutError:
        return {"status": "error", "detail": "nbfc command timed out"}


@register_handler("get_compute_routing")
async def handle_get_compute_routing(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Read compute-routing rules from config/compute-routing.yaml.

    Returns:
        Dict with ``status``, ``default_compute``, ``rule_count``, and
        ``rules`` list.
    """
    config_path = _compute_routing_path()

    def _read() -> dict[str, Any]:
        if not config_path.exists():
            return {}
        with config_path.open(encoding="utf-8") as fh:
            return _yaml.safe_load(fh) or {}

    try:
        data = await _anyio.to_thread.run_sync(_read)
    except OSError as exc:
        return {"status": "error", "detail": f"Cannot read compute-routing config: {exc}"}

    if not data:
        return {
            "status": "ok",
            "default_compute": "cpu",
            "rule_count": 0,
            "rules": [],
            "detail": "compute-routing.yaml not found; using built-in defaults",
        }

    rules = data.get("rules", [])
    return {
        "status": "ok",
        "default_compute": data.get("default_compute", "cpu"),
        "rule_count": len(rules),
        "rules": rules,
    }


@register_handler("set_compute_routing")
async def handle_set_compute_routing(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Add or update a single compute-routing rule.

    The rule is upserted by ``rule_id`` — if a rule with the same id exists
    it is replaced; otherwise it is appended.

    Returns:
        Dict with ``status``, ``action`` (``"created"`` or ``"updated"``),
        and the ``rule`` that was written.
    """
    rule_id = parameters.get("rule_id", "").strip()
    if not rule_id:
        return {"status": "error", "detail": "rule_id is required"}

    target_compute = parameters.get("target_compute", "").strip()
    if target_compute not in _VALID_COMPUTE_TARGETS:
        return {
            "status": "error",
            "detail": f"target_compute must be one of {sorted(_VALID_COMPUTE_TARGETS)}",
        }

    description = parameters.get("description", "").strip()
    if not description:
        return {"status": "error", "detail": "description is required"}

    # Build trigger dict from optional parameters.
    trigger: dict[str, Any] = {}
    task_type = parameters.get("trigger_task_type", "").strip()
    if task_type:
        if task_type not in _VALID_TASK_TYPES:
            return {
                "status": "error",
                "detail": f"trigger_task_type must be one of {sorted(_VALID_TASK_TYPES)}",
            }
        trigger["task_type"] = task_type
    proc = parameters.get("trigger_process", "").strip()
    if proc:
        trigger["process_names"] = [p.strip() for p in proc.split(",") if p.strip()]
    min_gb = parameters.get("trigger_model_size_gb_min")
    if min_gb is not None:
        trigger["model_size_gb_min"] = int(min_gb)

    priority = int(parameters.get("priority", 5))

    new_rule: dict[str, Any] = {
        "id": rule_id,
        "description": description,
        "trigger": trigger,
        "action": {"target_compute": target_compute},
        "priority": priority,
    }

    config_path = _compute_routing_path()

    def _upsert() -> str:
        if config_path.exists():
            with config_path.open(encoding="utf-8") as fh:
                data = _yaml.safe_load(fh) or {}
        else:
            data = {"version": 1, "default_compute": "cpu", "rules": []}

        rules: list[dict[str, Any]] = data.setdefault("rules", [])
        existing_idx = next((i for i, r in enumerate(rules) if r.get("id") == rule_id), None)
        if existing_idx is not None:
            rules[existing_idx] = new_rule
            action = "updated"
        else:
            rules.append(new_rule)
            action = "created"
        rules.sort(key=lambda r: r.get("priority", 0), reverse=True)

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as fh:
            _yaml.dump(data, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return action

    try:
        action = await _anyio.to_thread.run_sync(_upsert)
    except OSError as exc:
        return {"status": "error", "detail": f"Cannot write compute-routing config: {exc}"}

    logger.info("set_compute_routing: {} rule '{}'", action, rule_id)
    return {"status": "ok", "action": action, "rule": new_rule}


@register_handler("intake_compute_routing")
async def handle_intake_compute_routing(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Run a 20-question intake interview to configure compute-routing rules.

    First call: ``{"start": true}`` — creates a new session, returns Q1.
    Subsequent calls: ``{"session_id": "<id>", "answer": "<text>"}`` — stores
    the answer for the current question and returns the next question.
    After Q20 (if the operator answered "yes" to commit), the generated
    rules are written to ``config/compute-routing.yaml``.

    Returns:
        Dict with ``status``, ``session_id``, ``question_index``,
        ``question``, and optionally ``complete`` and ``rules_written``.
    """
    start = parameters.get("start", False)
    session_id = parameters.get("session_id", "").strip()
    answer = str(parameters.get("answer", "")).strip()

    _INTAKE_SESSION_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    total = len(_INTAKE_QUESTIONS)

    if start:
        # Generate a fresh session.
        session_id = _secrets.token_hex(16)
        session_data: dict[str, Any] = {"answers": {}, "current_index": 0}
        session_path = _INTAKE_SESSION_DIR / f"{session_id}.json"

        def _create_session() -> None:
            with session_path.open("w", encoding="utf-8") as fh:
                _json.dump(session_data, fh)

        await _anyio.to_thread.run_sync(_create_session)
        q = _INTAKE_QUESTIONS[0]
        return {
            "status": "ok",
            "session_id": session_id,
            "question_index": 1,
            "total_questions": total,
            "question_id": q["id"],
            "question": q["text"],
            "help": q["help"],
            "type": q["type"],
        }

    # --- Continuing an existing session ---
    if not session_id:
        return {
            "status": "error",
            "detail": "Provide session_id to continue, or start=true to begin.",
        }
    if not answer:
        return {"status": "error", "detail": "answer is required when continuing a session"}

    session_path = _INTAKE_SESSION_DIR / f"{session_id}.json"
    if not session_path.exists():
        return {
            "status": "error",
            "detail": f"Session '{session_id}' not found. Use start=true to begin.",
        }

    def _load_session() -> dict[str, Any]:
        with session_path.open(encoding="utf-8") as fh:
            return _json.load(fh)

    session_data = await _anyio.to_thread.run_sync(_load_session)
    current_index: int = session_data["current_index"]
    answers: dict[str, str] = session_data["answers"]

    if current_index >= total:
        return {"status": "error", "detail": "Session already complete. Use start=true to restart."}

    # Validate yes/no answers.
    current_q = _INTAKE_QUESTIONS[current_index]
    if current_q["type"] == "yn":
        if answer.lower() not in ("yes", "y", "no", "n"):
            return {
                "status": "error",
                "detail": f"Question {current_index + 1} requires a yes/no answer. Got: {answer!r}",
                "question_id": current_q["id"],
                "question": current_q["text"],
            }
        answer = "yes" if answer.lower() in ("yes", "y") else "no"

    answers[current_q["id"]] = answer
    current_index += 1
    session_data["current_index"] = current_index
    session_data["answers"] = answers

    # If all questions are answered, generate and optionally commit rules.
    if current_index >= total:
        rules = _build_routing_rules(answers)
        commit = answers.get("q20_commit", "no") == "yes"
        committed = False

        if commit:
            config_path = _compute_routing_path()

            def _write_rules() -> None:
                prefer_power_efficiency = (
                    answers.get("q16_power_efficiency_first") == "yes"
                )
                data = {
                    "version": 1,
                    "default_compute": "npu" if prefer_power_efficiency else "cpu",
                    "rules": rules,
                }
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with config_path.open("w", encoding="utf-8") as fh:
                    _yaml.dump(
                        data, fh, default_flow_style=False,
                        allow_unicode=True, sort_keys=False,
                    )

            try:
                await _anyio.to_thread.run_sync(_write_rules)
                committed = True
                logger.info("intake_compute_routing: committed {} rules", len(rules))
            except OSError as exc:
                # Clean up session and surface error.
                session_path.unlink(missing_ok=True)
                return {
                    "status": "error",
                    "detail": f"Failed to write config: {exc}",
                    "rules": rules,
                }

        # Clean up session file.
        session_path.unlink(missing_ok=True)

        if committed:
            _detail = (
                f"Interview complete. {len(rules)} rules written to compute-routing.yaml."
            )
        else:
            _detail = (
                f"Interview complete. {len(rules)} rules generated"
                " but NOT written (answered 'no' to commit)."
            )
        return {
            "status": "ok",
            "complete": True,
            "rules_written": committed,
            "rule_count": len(rules),
            "rules": rules,
            "detail": _detail,
        }

    def _save_session() -> None:
        with session_path.open("w", encoding="utf-8") as fh:
            _json.dump(session_data, fh)

    await _anyio.to_thread.run_sync(_save_session)

    next_q = _INTAKE_QUESTIONS[current_index]
    return {
        "status": "ok",
        "session_id": session_id,
        "question_index": current_index + 1,
        "total_questions": total,
        "question_id": next_q["id"],
        "question": next_q["text"],
        "help": next_q["help"],
        "type": next_q["type"],
    }


@register_handler("get_npu_status")
async def handle_get_npu_status(
    parameters: dict[str, Any], context: HandlerContext
) -> dict[str, Any]:
    """Report XDNA 2 NPU status and utilisation via xrt-smi.

    This handler is **experimental**.  The amdxdna driver and AMD XRT runtime
    must be installed for successful output.  Degrades gracefully with a
    clear error message when the tool or driver is absent.

    Compatible hardware: AMD Ryzen AI 9 300+ series (XDNA 2 architecture),
    kernel ≥ 6.8 with amdxdna module, AMD XRT package installed.

    Returns:
        Dict with ``status``, ``experimental`` flag, and either ``npu``
        data from xrt-smi or an ``error`` / ``dependency`` message.
    """
    base: dict[str, Any] = {"status": "ok", "experimental": True}

    # Attempt 1: xrt-smi examine (AMD XRT runtime).
    try:
        with _anyio.fail_after(10):
            proc = await _anyio.run_process(
                ["xrt-smi", "examine", "--format", "JSON", "--report", "aie"],
                check=False,
            )
        if proc.returncode == 0:
            try:
                npu_data = _json.loads(proc.stdout.decode())
                base["npu"] = npu_data
                base["source"] = "xrt-smi"
                logger.debug("get_npu_status: xrt-smi OK")
                return base
            except _json.JSONDecodeError:
                base["npu_raw"] = proc.stdout.decode(errors="replace").strip()
                base["source"] = "xrt-smi"
                return base
        stderr = proc.stderr.decode(errors="replace").strip()
        if "not found" in stderr.lower() or "no device" in stderr.lower():
            base["error"] = (
                "NPU device not found. Ensure the amdxdna kernel module is loaded: "
                "modprobe amdxdna"
            )
            base["dependency"] = "amdxdna kernel module (kernel >= 6.8)"
        else:
            base["error"] = f"xrt-smi exited {proc.returncode}: {stderr}"
        return base
    except FileNotFoundError:
        pass  # Fall through to sysfs check.
    except TimeoutError:
        base["error"] = "xrt-smi timed out"
        return base

    # Attempt 2: sysfs fallback — check if amdxdna driver is loaded.
    amdxdna_sysfs = _Path("/sys/bus/platform/drivers/amdxdna")

    def _check_sysfs() -> bool:
        return amdxdna_sysfs.is_dir()

    driver_loaded = await _anyio.to_thread.run_sync(_check_sysfs)
    if driver_loaded:
        base["error"] = (
            "amdxdna driver is loaded but xrt-smi is not installed. "
            "Install AMD XRT to read NPU metrics: "
            "https://github.com/Xilinx/XRT"
        )
        base["dependency"] = "xrt package (provides xrt-smi)"
        base["driver_loaded"] = True
    else:
        base["error"] = (
            "NPU not available. Missing dependencies:\n"
            "  1. amdxdna kernel module (kernel >= 6.8): modprobe amdxdna\n"
            "  2. AMD XRT runtime: https://github.com/Xilinx/XRT\n"
            "Compatible hardware: AMD Ryzen AI 9 300+ series (XDNA 2)"
        )
        base["dependency"] = "amdxdna kernel module + xrt package"
        base["driver_loaded"] = False

    return base
