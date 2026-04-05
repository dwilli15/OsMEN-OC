"""Tests for core/gateway/handlers.py and core/gateway/builtin_handlers.py.

Covers:
- Handler registration and lookup.
- Handler execution.
- ingest_url handler (with mocked httpx).
- search_knowledge handler.
- All 7 additional builtin handlers.
"""

from __future__ import annotations

from pathlib import Path as _Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx as _httpx
import pytest

from core.gateway.handlers import HandlerContext, HandlerRegistry


class TestHandlerRegistry:
    """Tests for the HandlerRegistry class."""

    def test_register_and_lookup(self) -> None:
        reg = HandlerRegistry()

        async def my_handler(params, ctx):
            return {"ok": True}

        reg.register("test_tool", my_handler)
        assert reg.has("test_tool")
        assert reg.get("test_tool") is my_handler

    def test_get_missing_returns_none(self) -> None:
        reg = HandlerRegistry()
        assert reg.get("nonexistent") is None
        assert not reg.has("nonexistent")

    @pytest.mark.anyio
    async def test_execute_calls_handler(self) -> None:
        reg = HandlerRegistry()
        called_with: dict = {}

        async def my_handler(params, ctx):
            called_with.update(params)
            return {"status": "ok"}

        reg.register("test_tool", my_handler)
        ctx = HandlerContext(agent_id="test", correlation_id="cid")
        result = await reg.execute("test_tool", {"key": "val"}, ctx)

        assert result == {"status": "ok"}
        assert called_with == {"key": "val"}

    @pytest.mark.anyio
    async def test_execute_missing_raises_key_error(self) -> None:
        reg = HandlerRegistry()
        ctx = HandlerContext(agent_id="test")
        with pytest.raises(KeyError, match="nonexistent"):
            await reg.execute("nonexistent", {}, ctx)

    def test_registered_tools_listing(self) -> None:
        reg = HandlerRegistry()

        async def h1(p, c):
            return {}

        async def h2(p, c):
            return {}

        reg.register("tool_a", h1)
        reg.register("tool_b", h2)
        assert sorted(reg.registered_tools) == ["tool_a", "tool_b"]


class TestBuiltinIngestUrl:
    """Tests for the ingest_url builtin handler."""

    class _MockStreamResponse:
        def __init__(
            self,
            *,
            chunks: list[bytes],
            content_type: str = "text/html; charset=utf-8",
            encoding: str = "utf-8",
        ) -> None:
            self._chunks = chunks
            self.headers = {"content-type": content_type}
            self.encoding = encoding
            self.raise_for_status = MagicMock()

        async def aiter_bytes(self):
            for chunk in self._chunks:
                yield chunk

    class _MockStreamContext:
        def __init__(self, response: TestBuiltinIngestUrl._MockStreamResponse) -> None:
            self._response = response

        async def __aenter__(self):
            return self._response

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    @staticmethod
    def _make_streaming_client(
        response: TestBuiltinIngestUrl._MockStreamResponse,
    ) -> AsyncMock:
        mock_client = AsyncMock()
        ctx = TestBuiltinIngestUrl._MockStreamContext(response)
        mock_client.stream = MagicMock(return_value=ctx)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        return mock_client

    @pytest.mark.anyio
    async def test_ingest_url_missing_url_param(self) -> None:
        from core.gateway.builtin_handlers import handle_ingest_url

        ctx = HandlerContext(agent_id="knowledge_librarian")
        result = await handle_ingest_url({}, ctx)
        assert result["status"] == "error"
        assert "url" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_localhost_hostname(self) -> None:
        from core.gateway.builtin_handlers import handle_ingest_url

        ctx = HandlerContext(agent_id="knowledge_librarian")

        with patch("core.gateway.builtin_handlers._httpx.AsyncClient") as mock_async_client:
            result = await handle_ingest_url({"url": "https://localhost/internal"}, ctx)

        assert result["status"] == "error"
        assert "localhost" in result["detail"].lower()
        mock_async_client.assert_not_called()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_private_ip(self) -> None:
        from core.gateway.builtin_handlers import handle_ingest_url

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                return_value=[(2, 1, 6, "", ("192.168.1.10", 443))],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient") as mock_async_client,
        ):
            result = await handle_ingest_url({"url": "https://internal.example/private"}, ctx)

        assert result["status"] == "error"
        assert "non-public" in result["detail"].lower()
        mock_async_client.assert_not_called()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_unsupported_content_type(self) -> None:
        from core.gateway.builtin_handlers import handle_ingest_url

        response = self._MockStreamResponse(chunks=[b"%PDF-1.7"], content_type="application/pdf")
        mock_client = self._make_streaming_client(response)

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/file.pdf"}, ctx)

        assert result["status"] == "error"
        assert "unsupported content type" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_oversized_response(self) -> None:
        from core.gateway.builtin_handlers import handle_ingest_url

        response = self._MockStreamResponse(
            chunks=[b"a" * (10 * 1024 * 1024), b"b"],
            content_type="text/plain",
        )
        mock_client = self._make_streaming_client(response)

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/huge.txt"}, ctx)

        assert result["status"] == "error"
        assert "10 mib" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_url_fetches_and_chunks(self) -> None:
        from core.gateway.builtin_handlers import handle_ingest_url

        response = self._MockStreamResponse(
            chunks=[
                b"<html><body>First sentence. ",
                b"Second sentence. Third sentence.</body></html>",
            ]
        )
        mock_client = self._make_streaming_client(response)

        ctx = HandlerContext(agent_id="knowledge_librarian")

        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/doc"}, ctx)

        assert result["status"] == "ok"
        assert result["chunks"] >= 1
        assert result["url"] == "https://example.com/doc"
        assert result["stored"] is False  # no chroma configured

    @pytest.mark.anyio
    async def test_ingest_url_stores_in_chroma_when_available(self) -> None:
        from core.gateway.builtin_handlers import handle_ingest_url

        response = self._MockStreamResponse(chunks=[b"Hello world. This is a test document."])
        mock_client = self._make_streaming_client(response)

        mock_chroma = MagicMock()
        mock_chroma.add_documents_async = AsyncMock()

        app_state = MagicMock()
        app_state.chroma_store = mock_chroma

        ctx = HandlerContext(
            agent_id="knowledge_librarian",
            app_state=app_state,
        )

        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url(
                {"url": "https://example.com/test", "collection": "test_coll"},
                ctx,
            )

        assert result["status"] == "ok"
        assert result["stored"] is True
        mock_chroma.add_documents_async.assert_called_once()


class TestBuiltinSearchKnowledge:
    """Tests for the search_knowledge builtin handler."""

    @pytest.mark.anyio
    async def test_search_missing_query(self) -> None:
        from core.gateway.builtin_handlers import handle_search_knowledge

        ctx = HandlerContext(agent_id="knowledge_librarian")
        result = await handle_search_knowledge({}, ctx)
        assert result["status"] == "error"

    @pytest.mark.anyio
    async def test_search_no_chroma(self) -> None:
        from core.gateway.builtin_handlers import handle_search_knowledge

        ctx = HandlerContext(agent_id="knowledge_librarian")
        result = await handle_search_knowledge({"query": "test"}, ctx)
        assert result["status"] == "error"
        assert "ChromaDB" in result["detail"]

    @pytest.mark.anyio
    async def test_search_returns_results(self) -> None:
        from core.gateway.builtin_handlers import handle_search_knowledge

        mock_chroma = MagicMock()
        mock_chroma.query_async = AsyncMock(
            return_value={"documents": [["hello"]], "ids": [["1"]]},
        )

        app_state = MagicMock()
        app_state.chroma_store = mock_chroma

        ctx = HandlerContext(agent_id="knowledge_librarian", app_state=app_state)
        result = await handle_search_knowledge({"query": "hello", "top_k": "3"}, ctx)

        assert result["status"] == "ok"
        mock_chroma.query_async.assert_called_once()


# ---------------------------------------------------------------------------
# Entry-point plugin loader
# ---------------------------------------------------------------------------


class TestEntryPointLoader:
    """Tests for load_entry_point_handlers."""

    def test_loads_entry_points_into_registry(self) -> None:
        from core.gateway.handlers import HandlerRegistry, load_entry_point_handlers

        async def fake_handler(params, ctx):
            return {"plugin": True}

        fake_ep = MagicMock()
        fake_ep.name = "plugin_tool"
        fake_ep.value = "mypkg.handlers:handle_plugin"
        fake_ep.load.return_value = fake_handler

        with patch("core.gateway.handlers.importlib.metadata.entry_points", return_value=[fake_ep]):
            reg = HandlerRegistry()
            loaded = load_entry_point_handlers(registry=reg)

        assert loaded == ["plugin_tool"]
        assert reg.has("plugin_tool")
        assert reg.get("plugin_tool") is fake_handler

    def test_skips_broken_entry_point(self) -> None:
        from core.gateway.handlers import HandlerRegistry, load_entry_point_handlers

        bad_ep = MagicMock()
        bad_ep.name = "broken_tool"
        bad_ep.value = "bad.module:fn"
        bad_ep.load.side_effect = ImportError("no such module")

        with patch("core.gateway.handlers.importlib.metadata.entry_points", return_value=[bad_ep]):
            reg = HandlerRegistry()
            loaded = load_entry_point_handlers(registry=reg)

        assert loaded == []
        assert not reg.has("broken_tool")

    def test_no_entry_points_returns_empty(self) -> None:
        from core.gateway.handlers import HandlerRegistry, load_entry_point_handlers

        with patch("core.gateway.handlers.importlib.metadata.entry_points", return_value=[]):
            reg = HandlerRegistry()
            loaded = load_entry_point_handlers(registry=reg)

        assert loaded == []


# ---------------------------------------------------------------------------
# fetch_task_summary
# ---------------------------------------------------------------------------


def _make_completed(returncode: int, stdout: bytes, stderr: bytes = b""):
    """Build a subprocess.CompletedProcess for mocking anyio.run_process."""
    import subprocess

    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestFetchTaskSummary:
    """Tests for the fetch_task_summary builtin handler."""

    @pytest.mark.anyio
    async def test_taskwarrior_not_installed(self) -> None:
        from core.gateway.builtin_handlers import handle_fetch_task_summary

        ctx = HandlerContext(agent_id="daily_brief")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=FileNotFoundError,
        ):
            result = await handle_fetch_task_summary({}, ctx)

        assert result["status"] == "error"
        assert "taskwarrior" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_invalid_limit(self) -> None:
        from core.gateway.builtin_handlers import handle_fetch_task_summary

        ctx = HandlerContext(agent_id="daily_brief")
        result = await handle_fetch_task_summary({"limit": 0}, ctx)
        assert result["status"] == "error"

    @pytest.mark.anyio
    async def test_empty_task_list(self) -> None:
        from core.gateway.builtin_handlers import handle_fetch_task_summary

        ctx = HandlerContext(agent_id="daily_brief")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, b"")),
        ):
            result = await handle_fetch_task_summary({}, ctx)

        assert result["status"] == "ok"
        assert result["total"] == 0
        assert result["projects"] == {}

    @pytest.mark.anyio
    async def test_tasks_grouped_by_project(self) -> None:
        import json

        from core.gateway.builtin_handlers import handle_fetch_task_summary

        tasks = [
            {"id": 1, "description": "Task A", "project": "work", "urgency": 5.0},
            {"id": 2, "description": "Task B", "project": "home", "urgency": 2.0},
            {"id": 3, "description": "Task C", "project": "work", "urgency": 3.0},
        ]
        stdout = json.dumps(tasks).encode()

        ctx = HandlerContext(agent_id="daily_brief")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, stdout)),
        ):
            result = await handle_fetch_task_summary({}, ctx)

        assert result["status"] == "ok"
        assert result["total"] == 3
        assert "work" in result["projects"]
        assert "home" in result["projects"]
        assert len(result["projects"]["work"]) == 2

    @pytest.mark.anyio
    async def test_task_export_failure(self) -> None:
        from core.gateway.builtin_handlers import handle_fetch_task_summary

        ctx = HandlerContext(agent_id="daily_brief")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(2, b"", b"error")),
        ):
            result = await handle_fetch_task_summary({}, ctx)

        assert result["status"] == "error"

    @pytest.mark.anyio
    async def test_limit_respected(self) -> None:
        import json

        from core.gateway.builtin_handlers import handle_fetch_task_summary

        tasks = [{"id": i, "description": f"T{i}", "project": "work"} for i in range(50)]

        ctx = HandlerContext(agent_id="daily_brief")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, json.dumps(tasks).encode())),
        ):
            result = await handle_fetch_task_summary({"limit": 5}, ctx)

        assert result["status"] == "ok"
        total_returned = sum(len(v) for v in result["projects"].values())
        assert total_returned == 5


# ---------------------------------------------------------------------------
# generate_brief
# ---------------------------------------------------------------------------


class TestGenerateBrief:
    """Tests for the generate_brief builtin handler."""

    @pytest.mark.anyio
    async def test_missing_period(self) -> None:
        from core.gateway.builtin_handlers import handle_generate_brief

        ctx = HandlerContext(agent_id="daily_brief")
        result = await handle_generate_brief({}, ctx)
        assert result["status"] == "error"
        assert "period" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_invalid_period(self) -> None:
        from core.gateway.builtin_handlers import handle_generate_brief

        ctx = HandlerContext(agent_id="daily_brief")
        result = await handle_generate_brief({"period": "noon"}, ctx)
        assert result["status"] == "error"
        assert "period" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_missing_api_key(self) -> None:
        from core.gateway.builtin_handlers import handle_generate_brief

        ctx = HandlerContext(agent_id="daily_brief")
        with patch.dict("os.environ", {}, clear=True):
            import os

            os.environ.pop("ZAI_API_KEY", None)
            result = await handle_generate_brief({"period": "morning"}, ctx)

        assert result["status"] == "error"
        assert "ZAI_API_KEY" in result["detail"]

    @pytest.mark.anyio
    async def test_successful_morning_brief(self) -> None:
        from core.gateway.builtin_handlers import handle_generate_brief

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Good morning! Have a great day."}}]
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        ctx = HandlerContext(agent_id="daily_brief")
        with (
            patch.dict("os.environ", {"ZAI_API_KEY": "test-key"}),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_generate_brief({"period": "morning", "date": "2026-04-05"}, ctx)

        assert result["status"] == "ok"
        assert result["period"] == "morning"
        assert result["date"] == "2026-04-05"
        assert "brief" in result
        assert len(result["brief"]) > 0

    @pytest.mark.anyio
    async def test_rate_limit_returns_retry_after(self) -> None:
        from core.gateway.builtin_handlers import handle_generate_brief

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "error": {"code": 1302, "message": "rate limit exceeded"}
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        ctx = HandlerContext(agent_id="daily_brief")
        with (
            patch.dict("os.environ", {"ZAI_API_KEY": "test-key"}),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_generate_brief({"period": "evening"}, ctx)

        assert result["status"] == "error"
        assert result["detail"] == "rate_limited"
        assert result["retry_after"] == 120

    @pytest.mark.anyio
    async def test_api_http_error(self) -> None:
        from core.gateway.builtin_handlers import handle_generate_brief

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=_httpx.ConnectError("connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        ctx = HandlerContext(agent_id="daily_brief")
        with (
            patch.dict("os.environ", {"ZAI_API_KEY": "test-key"}),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_generate_brief({"period": "morning"}, ctx)

        assert result["status"] == "error"
        assert "GLM" in result["detail"]


# ---------------------------------------------------------------------------
# transcribe_audio
# ---------------------------------------------------------------------------


class TestTranscribeAudio:
    """Tests for the transcribe_audio builtin handler."""

    @pytest.mark.anyio
    async def test_missing_file_path(self) -> None:
        from core.gateway.builtin_handlers import handle_transcribe_audio

        ctx = HandlerContext(agent_id="knowledge_librarian")
        result = await handle_transcribe_audio({}, ctx)
        assert result["status"] == "error"
        assert "file_path" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_relative_path_rejected(self) -> None:
        from core.gateway.builtin_handlers import handle_transcribe_audio

        ctx = HandlerContext(agent_id="knowledge_librarian")
        result = await handle_transcribe_audio({"file_path": "relative/path.mp3"}, ctx)
        assert result["status"] == "error"
        assert "absolute" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_file_not_found(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_transcribe_audio

        ctx = HandlerContext(agent_id="knowledge_librarian")
        result = await handle_transcribe_audio(
            {"file_path": str(tmp_path / "nonexistent.mp3")}, ctx
        )
        assert result["status"] == "error"
        assert "not found" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_unsupported_extension(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_transcribe_audio

        doc = tmp_path / "file.docx"
        doc.write_text("content")
        ctx = HandlerContext(agent_id="knowledge_librarian")
        result = await handle_transcribe_audio({"file_path": str(doc)}, ctx)
        assert result["status"] == "error"
        assert "unsupported" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_whisper_not_installed(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_transcribe_audio

        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"\x00" * 100)
        ctx = HandlerContext(agent_id="knowledge_librarian")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=FileNotFoundError,
        ):
            result = await handle_transcribe_audio({"file_path": str(audio)}, ctx)

        assert result["status"] == "error"
        assert "whisper" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_successful_transcription_no_chroma(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_transcribe_audio

        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"\x00" * 100)
        transcript = tmp_path / "audio.txt"
        transcript.write_text("Hello world. This is a test transcript.")

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, b"")),
        ):
            result = await handle_transcribe_audio({"file_path": str(audio)}, ctx)

        assert result["status"] == "ok"
        assert result["chunks"] >= 1
        assert result["stored"] is False
        assert result["transcript_length"] > 0

    @pytest.mark.anyio
    async def test_transcription_stores_in_chroma(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_transcribe_audio

        audio = tmp_path / "talk.wav"
        audio.write_bytes(b"\x00" * 100)
        transcript = tmp_path / "talk.txt"
        transcript.write_text("Sentence one. Sentence two. Sentence three.")

        mock_chroma = MagicMock()
        mock_chroma.add_documents_async = AsyncMock()
        app_state = MagicMock()
        app_state.chroma_store = mock_chroma

        ctx = HandlerContext(agent_id="knowledge_librarian", app_state=app_state)
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, b"")),
        ):
            result = await handle_transcribe_audio({"file_path": str(audio)}, ctx)

        assert result["status"] == "ok"
        assert result["stored"] is True
        mock_chroma.add_documents_async.assert_called_once()


# ---------------------------------------------------------------------------
# transfer_to_plex
# ---------------------------------------------------------------------------


class TestTransferToPlex:
    """Tests for the transfer_to_plex builtin handler."""

    @pytest.mark.anyio
    async def test_missing_source_path(self) -> None:
        from core.gateway.builtin_handlers import handle_transfer_to_plex

        ctx = HandlerContext(agent_id="media_organization")
        result = await handle_transfer_to_plex({"media_type": "movies"}, ctx)
        assert result["status"] == "error"
        assert "source_path" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_invalid_media_type(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_transfer_to_plex

        src = tmp_path / "movie.mkv"
        src.write_bytes(b"\x00")
        ctx = HandlerContext(agent_id="media_organization")
        result = await handle_transfer_to_plex(
            {"source_path": str(src), "media_type": "games"}, ctx
        )
        assert result["status"] == "error"
        assert "media_type" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_relative_source_path_rejected(self) -> None:
        from core.gateway.builtin_handlers import handle_transfer_to_plex

        ctx = HandlerContext(agent_id="media_organization")
        result = await handle_transfer_to_plex(
            {"source_path": "relative/movie.mkv", "media_type": "movies"}, ctx
        )
        assert result["status"] == "error"
        assert "absolute" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_source_not_found(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_transfer_to_plex

        ctx = HandlerContext(agent_id="media_organization")
        result = await handle_transfer_to_plex(
            {"source_path": str(tmp_path / "missing.mkv"), "media_type": "movies"}, ctx
        )
        assert result["status"] == "error"
        assert "not found" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_missing_plex_library_root(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_transfer_to_plex

        src = tmp_path / "movie.mkv"
        src.write_bytes(b"\x00")
        ctx = HandlerContext(agent_id="media_organization")
        with patch.dict("os.environ", {}, clear=True):
            import os

            os.environ.pop("PLEX_LIBRARY_ROOT", None)
            result = await handle_transfer_to_plex(
                {"source_path": str(src), "media_type": "movies"}, ctx
            )

        assert result["status"] == "error"
        assert "PLEX_LIBRARY_ROOT" in result["detail"]

    @pytest.mark.anyio
    async def test_successful_transfer(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_transfer_to_plex

        src = tmp_path / "source" / "my_movie.mkv"
        src.parent.mkdir()
        src.write_bytes(b"\x00" * 64)
        library_root = tmp_path / "plex"

        ctx = HandlerContext(agent_id="media_organization")
        with patch.dict("os.environ", {"PLEX_LIBRARY_ROOT": str(library_root)}):
            result = await handle_transfer_to_plex(
                {"source_path": str(src), "media_type": "movies"}, ctx
            )

        assert result["status"] == "ok"
        assert result["media_type"] == "movies"
        dest = _Path(result["destination"])
        assert dest.exists()
        assert dest.name == "my_movie.mkv"
        assert not src.exists()


# ---------------------------------------------------------------------------
# audit_vpn
# ---------------------------------------------------------------------------


class TestAuditVpn:
    """Tests for the audit_vpn builtin handler."""

    @pytest.mark.anyio
    async def test_podman_not_installed(self) -> None:
        from core.gateway.builtin_handlers import handle_audit_vpn

        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=FileNotFoundError,
        ):
            result = await handle_audit_vpn({}, ctx)

        assert result["status"] == "error"
        assert "podman" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_container_not_running(self) -> None:
        from core.gateway.builtin_handlers import handle_audit_vpn

        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, b"false\n")),
        ):
            result = await handle_audit_vpn({}, ctx)

        assert result["status"] == "ok"
        assert result["vpn_connected"] is False

    @pytest.mark.anyio
    async def test_container_running_vpn_connected(self) -> None:
        from core.gateway.builtin_handlers import handle_audit_vpn

        # First call: podman inspect → running=true
        # Second call: podman exec → returns public IP
        call_count = 0

        async def _fake_run_process(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_completed(0, b"true\n")
            return _make_completed(0, b"203.0.113.42\n")

        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=_fake_run_process,
        ):
            result = await handle_audit_vpn({}, ctx)

        assert result["status"] == "ok"
        assert result["vpn_connected"] is True
        assert result["vpn_ip"] == "203.0.113.42"

    @pytest.mark.anyio
    async def test_vpn_ip_empty_means_not_connected(self) -> None:
        from core.gateway.builtin_handlers import handle_audit_vpn

        call_count = 0

        async def _fake_run_process(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_completed(0, b"true\n")
            return _make_completed(0, b"")

        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=_fake_run_process,
        ):
            result = await handle_audit_vpn({}, ctx)

        assert result["status"] == "ok"
        assert result["vpn_connected"] is False


# ---------------------------------------------------------------------------
# list_downloads
# ---------------------------------------------------------------------------


class TestListDownloads:
    """Tests for the list_downloads builtin handler."""

    @pytest.mark.anyio
    async def test_invalid_status_filter(self) -> None:
        from core.gateway.builtin_handlers import handle_list_downloads

        ctx = HandlerContext(agent_id="media_organization")
        result = await handle_list_downloads({"status": "unknown_value"}, ctx)
        assert result["status"] == "error"
        assert "status" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_qbt_unavailable_returns_ok_with_errors(self) -> None:
        from core.gateway.builtin_handlers import handle_list_downloads

        ctx = HandlerContext(agent_id="media_organization")
        with (
            patch.dict("os.environ", {"SABNZBD_API_KEY": ""}),
            patch(
                "core.gateway.builtin_handlers._httpx.AsyncClient",
                side_effect=_httpx.ConnectError("refused"),
            ),
        ):
            result = await handle_list_downloads({}, ctx)

        assert result["status"] == "ok"
        assert result["downloads"] == []
        assert len(result["errors"]) > 0

    @pytest.mark.anyio
    async def test_qbt_returns_downloads(self) -> None:
        from core.gateway.builtin_handlers import handle_list_downloads

        torrents = [
            {"name": "Movie A", "state": "downloading", "progress": 0.5, "size": 2_000_000_000},
            {"name": "Movie B", "state": "pausedDL", "progress": 0.0, "size": 1_000_000_000},
        ]

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = torrents

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        ctx = HandlerContext(agent_id="media_organization")
        with (
            patch.dict("os.environ", {"SABNZBD_API_KEY": ""}),
            patch(
                "core.gateway.builtin_handlers._httpx.AsyncClient",
                return_value=mock_client,
            ),
        ):
            result = await handle_list_downloads({}, ctx)

        assert result["status"] == "ok"
        assert result["total"] == 2
        names = [d["name"] for d in result["downloads"]]
        assert "Movie A" in names
        assert "Movie B" in names

    @pytest.mark.anyio
    async def test_status_filter_active_only(self) -> None:
        from core.gateway.builtin_handlers import handle_list_downloads

        torrents = [
            {"name": "Active", "state": "downloading", "progress": 0.3, "size": 100},
            {"name": "Paused", "state": "pausedDL", "progress": 0.0, "size": 100},
        ]

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = torrents

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        ctx = HandlerContext(agent_id="media_organization")
        with (
            patch.dict("os.environ", {"SABNZBD_API_KEY": ""}),
            patch(
                "core.gateway.builtin_handlers._httpx.AsyncClient",
                return_value=mock_client,
            ),
        ):
            result = await handle_list_downloads({"status": "active"}, ctx)

        assert result["status"] == "ok"
        assert result["total"] == 1
        assert result["downloads"][0]["name"] == "Active"


# ---------------------------------------------------------------------------
# purge_completed
# ---------------------------------------------------------------------------


class TestPurgeCompleted:
    """Tests for the purge_completed builtin handler."""

    @pytest.mark.anyio
    async def test_staging_dir_not_configured(self) -> None:
        from core.gateway.builtin_handlers import handle_purge_completed

        ctx = HandlerContext(agent_id="media_organization")
        with patch.dict("os.environ", {}, clear=True):
            import os

            os.environ.pop("DOWNLOAD_STAGING_DIR", None)
            result = await handle_purge_completed({}, ctx)

        assert result["status"] == "error"
        assert "DOWNLOAD_STAGING_DIR" in result["detail"]

    @pytest.mark.anyio
    async def test_staging_dir_not_found(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_purge_completed

        ctx = HandlerContext(agent_id="media_organization")
        with patch.dict("os.environ", {"DOWNLOAD_STAGING_DIR": str(tmp_path / "missing")}):
            result = await handle_purge_completed({}, ctx)

        assert result["status"] == "error"
        assert "not found" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_negative_days_rejected(self) -> None:
        from core.gateway.builtin_handlers import handle_purge_completed

        ctx = HandlerContext(agent_id="media_organization")
        result = await handle_purge_completed({"older_than_days": -1}, ctx)
        assert result["status"] == "error"

    @pytest.mark.anyio
    async def test_purges_old_files(self, tmp_path) -> None:
        import time

        from core.gateway.builtin_handlers import handle_purge_completed

        staging = tmp_path / "staging"
        staging.mkdir()

        old_file = staging / "old_download.mkv"
        old_file.write_bytes(b"\x00" * 10)
        old_ts = time.time() - (10 * 86400)  # 10 days ago
        import os

        os.utime(old_file, (old_ts, old_ts))

        new_file = staging / "new_download.mkv"
        new_file.write_bytes(b"\x00" * 10)

        ctx = HandlerContext(agent_id="media_organization")
        with patch.dict("os.environ", {"DOWNLOAD_STAGING_DIR": str(staging)}):
            result = await handle_purge_completed({"older_than_days": 7}, ctx)

        assert result["status"] == "ok"
        assert result["purged"] == 1
        assert not old_file.exists()
        assert new_file.exists()

    @pytest.mark.anyio
    async def test_empty_staging_dir(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_purge_completed

        staging = tmp_path / "staging"
        staging.mkdir()

        ctx = HandlerContext(agent_id="media_organization")
        with patch.dict("os.environ", {"DOWNLOAD_STAGING_DIR": str(staging)}):
            result = await handle_purge_completed({}, ctx)

        assert result["status"] == "ok"
        assert result["purged"] == 0
