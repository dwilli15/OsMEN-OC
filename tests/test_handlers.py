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
            status_code: int = 200,
            headers: dict[str, str] | None = None,
        ) -> None:
            self._chunks = chunks
            self.status_code = status_code
            self.headers = {"content-type": content_type}
            if headers:
                self.headers.update(headers)
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
        responses: TestBuiltinIngestUrl._MockStreamResponse
        | list[TestBuiltinIngestUrl._MockStreamResponse],
    ) -> AsyncMock:
        mock_client = AsyncMock()
        if isinstance(responses, list):
            mock_client.stream = MagicMock(
                side_effect=[TestBuiltinIngestUrl._MockStreamContext(resp) for resp in responses],
            )
        else:
            ctx = TestBuiltinIngestUrl._MockStreamContext(responses)
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
    async def test_ingest_url_rejects_redirect_to_localhost(self) -> None:
        from core.gateway.builtin_handlers import handle_ingest_url

        redirect_resp = self._MockStreamResponse(
            chunks=[],
            status_code=302,
            headers={"location": "http://localhost/internal"},
        )
        final_resp = self._MockStreamResponse(chunks=[b"ok"], content_type="text/plain")
        mock_client = self._make_streaming_client([redirect_resp, final_resp])

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                side_effect=[
                    [(2, 1, 6, "", ("93.184.216.34", 443))],
                    [(2, 1, 6, "", ("127.0.0.1", 80))],
                ],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/redirect"}, ctx)

        assert result["status"] == "error"
        assert "redirect target blocked" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_redirect_to_loopback_ip(self) -> None:
        """Redirect to a bare loopback IP (127.0.0.1) must be blocked."""
        from core.gateway.builtin_handlers import handle_ingest_url

        redirect_resp = self._MockStreamResponse(
            chunks=[],
            status_code=301,
            headers={"location": "http://127.0.0.1/secret"},
        )
        final_resp = self._MockStreamResponse(chunks=[b"secret"], content_type="text/plain")
        mock_client = self._make_streaming_client([redirect_resp, final_resp])

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                side_effect=[
                    [(2, 1, 6, "", ("93.184.216.34", 443))],
                    [(2, 1, 6, "", ("127.0.0.1", 80))],
                ],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/page"}, ctx)

        assert result["status"] == "error"
        assert "redirect target blocked" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_redirect_to_link_local_metadata(self) -> None:
        """Redirect to 169.254.169.254 (cloud metadata endpoint) must be blocked."""
        from core.gateway.builtin_handlers import handle_ingest_url

        redirect_resp = self._MockStreamResponse(
            chunks=[],
            status_code=302,
            headers={"location": "http://169.254.169.254/latest/meta-data/"},
        )
        final_resp = self._MockStreamResponse(chunks=[b"metadata"], content_type="text/plain")
        mock_client = self._make_streaming_client([redirect_resp, final_resp])

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                side_effect=[
                    [(2, 1, 6, "", ("93.184.216.34", 443))],
                    [(2, 1, 6, "", ("169.254.169.254", 80))],
                ],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/page"}, ctx)

        assert result["status"] == "error"
        assert "redirect target blocked" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_redirect_to_rfc1918_class_a(self) -> None:
        """Redirect to an RFC1918 10.x.x.x address must be blocked."""
        from core.gateway.builtin_handlers import handle_ingest_url

        redirect_resp = self._MockStreamResponse(
            chunks=[],
            status_code=302,
            headers={"location": "http://10.0.0.1/admin"},
        )
        final_resp = self._MockStreamResponse(chunks=[b"admin"], content_type="text/plain")
        mock_client = self._make_streaming_client([redirect_resp, final_resp])

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                side_effect=[
                    [(2, 1, 6, "", ("93.184.216.34", 443))],
                    [(2, 1, 6, "", ("10.0.0.1", 80))],
                ],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/page"}, ctx)

        assert result["status"] == "error"
        assert "redirect target blocked" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_redirect_to_rfc1918_class_b(self) -> None:
        """Redirect to an RFC1918 172.16.x.x address must be blocked."""
        from core.gateway.builtin_handlers import handle_ingest_url

        redirect_resp = self._MockStreamResponse(
            chunks=[],
            status_code=302,
            headers={"location": "http://172.16.0.1/internal"},
        )
        final_resp = self._MockStreamResponse(chunks=[b"internal"], content_type="text/plain")
        mock_client = self._make_streaming_client([redirect_resp, final_resp])

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                side_effect=[
                    [(2, 1, 6, "", ("93.184.216.34", 443))],
                    [(2, 1, 6, "", ("172.16.0.1", 80))],
                ],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/page"}, ctx)

        assert result["status"] == "error"
        assert "redirect target blocked" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_multihop_chain_ending_at_private(self) -> None:
        """A multi-hop redirect chain that terminates at a private IP must be blocked."""
        from core.gateway.builtin_handlers import handle_ingest_url

        hop1 = self._MockStreamResponse(
            chunks=[],
            status_code=302,
            headers={"location": "https://cdn.example.com/resource"},
        )
        hop2 = self._MockStreamResponse(
            chunks=[],
            status_code=301,
            headers={"location": "http://192.168.0.10/internal"},
        )
        final_resp = self._MockStreamResponse(chunks=[b"internal"], content_type="text/plain")
        mock_client = self._make_streaming_client([hop1, hop2, final_resp])

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                side_effect=[
                    [(2, 1, 6, "", ("93.184.216.34", 443))],   # example.com/start
                    [(2, 1, 6, "", ("198.51.100.5", 443))],    # cdn.example.com (public)
                    [(2, 1, 6, "", ("192.168.0.10", 80))],     # 192.168.0.10 (private) → blocked
                ],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/start"}, ctx)

        assert result["status"] == "error"
        assert "redirect target blocked" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_too_many_redirect_hops(self) -> None:
        """A redirect chain exceeding _MAX_REDIRECT_HOPS must be rejected."""
        from core.gateway.builtin_handlers import _MAX_REDIRECT_HOPS, handle_ingest_url

        # Build _MAX_REDIRECT_HOPS + 1 redirect responses, all pointing to the next hop.
        redirects = [
            self._MockStreamResponse(
                chunks=[],
                status_code=302,
                headers={"location": f"https://hop{i + 1}.example.com/"},
            )
            for i in range(_MAX_REDIRECT_HOPS + 1)
        ]
        final_resp = self._MockStreamResponse(chunks=[b"never reached"], content_type="text/plain")
        mock_client = self._make_streaming_client([*redirects, final_resp])

        public_addr = [(2, 1, 6, "", ("93.184.216.34", 443))]
        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                return_value=public_addr,
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/start"}, ctx)

        assert result["status"] == "error"
        assert "too many redirect" in result["detail"].lower()

    @pytest.mark.anyio
    async def test_ingest_url_rejects_redirect_without_location(self) -> None:
        from core.gateway.builtin_handlers import handle_ingest_url

        redirect_resp = self._MockStreamResponse(chunks=[], status_code=301)
        mock_client = self._make_streaming_client(redirect_resp)

        ctx = HandlerContext(agent_id="knowledge_librarian")
        with (
            patch(
                "core.gateway.builtin_handlers._socket.getaddrinfo",
                return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
            ),
            patch("core.gateway.builtin_handlers._httpx.AsyncClient", return_value=mock_client),
        ):
            result = await handle_ingest_url({"url": "https://example.com/redirect"}, ctx)

        assert result["status"] == "error"
        assert "missing location" in result["detail"].lower()

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
        mock_chroma.add_documents_async.assert_awaited_once()


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
        mock_chroma.query_async = AsyncMock(return_value={"documents": [["hello"]], "ids": [["1"]]})

        app_state = MagicMock()
        app_state.chroma_store = mock_chroma

        ctx = HandlerContext(agent_id="knowledge_librarian", app_state=app_state)
        result = await handle_search_knowledge({"query": "hello", "top_k": "3"}, ctx)

        assert result["status"] == "ok"
        mock_chroma.query_async.assert_awaited_once()


# ---------------------------------------------------------------------------
# Entry-point plugin loader
# ---------------------------------------------------------------------------


class TestLoadEntryPointHandlers:
    """Tests for load_entry_point_handlers()."""

    def test_returns_empty_when_no_entry_points(self) -> None:
        """With no osmen_oc.handlers entry-points, returns an empty list."""
        from unittest.mock import patch

        from core.gateway.handlers import HandlerRegistry, load_entry_point_handlers

        registry = HandlerRegistry()
        with patch("importlib.metadata.entry_points", return_value=[]) as mock_eps:
            result = load_entry_point_handlers(registry=registry)
        assert result == []
        mock_eps.assert_called_once_with(group="osmen_oc.handlers")

    def test_loads_and_registers_entry_point(self) -> None:
        """A valid entry-point is loaded and registered in the registry."""
        from unittest.mock import MagicMock, patch

        from core.gateway.handlers import HandlerRegistry, load_entry_point_handlers

        async def dummy_handler(params: dict, ctx: object) -> dict:
            return {"status": "ok"}

        ep = MagicMock()
        ep.name = "dummy_tool"
        ep.value = "my_package.handlers:dummy_handler"
        ep.load.return_value = dummy_handler

        registry = HandlerRegistry()
        with patch("importlib.metadata.entry_points", return_value=[ep]):
            loaded = load_entry_point_handlers(registry=registry)

        assert loaded == ["dummy_tool"]
        assert registry.has("dummy_tool")

    def test_skips_entry_point_that_fails_to_load(self) -> None:
        """A broken entry-point is skipped; other tools still load."""
        from unittest.mock import MagicMock, patch

        from core.gateway.handlers import HandlerRegistry, load_entry_point_handlers

        async def good_handler(params: dict, ctx: object) -> dict:
            return {"status": "ok"}

        bad_ep = MagicMock()
        bad_ep.name = "broken_tool"
        bad_ep.load.side_effect = ImportError("module not found")

        good_ep = MagicMock()
        good_ep.name = "good_tool"
        good_ep.value = "my_package:good_handler"
        good_ep.load.return_value = good_handler

        registry = HandlerRegistry()
        with patch("importlib.metadata.entry_points", return_value=[bad_ep, good_ep]):
            loaded = load_entry_point_handlers(registry=registry)

        assert "good_tool" in loaded
        assert "broken_tool" not in loaded
        assert not registry.has("broken_tool")
        assert registry.has("good_tool")


def _make_completed(returncode: int, stdout: bytes, stderr: bytes = b""):
    """Build a subprocess.CompletedProcess for mocking anyio.run_process."""
    import subprocess

    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _make_disk_usage(free: int, total: int = 100 * 1024**3):
    """Build a shutil.disk_usage namedtuple for mocking."""
    from collections import namedtuple

    DiskUsage = namedtuple("DiskUsage", ["total", "used", "free"])
    return DiskUsage(total=total, used=total - free, free=free)


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


# ---------------------------------------------------------------------------
# assess_plex_readiness
# ---------------------------------------------------------------------------


class TestAssessPlexReadiness:
    """Tests for the assess_plex_readiness builtin handler."""

    @pytest.mark.anyio
    async def test_library_root_not_configured(self) -> None:
        from core.gateway.builtin_handlers import handle_assess_plex_readiness

        ctx = HandlerContext(agent_id="media_organization")
        with patch.dict("os.environ", {}, clear=True):
            result = await handle_assess_plex_readiness({}, ctx)

        assert result["status"] == "ok"
        assert result["ready"] is False
        root_check = next(
            c for c in result["checks"] if c["name"] == "plex_library_root_configured"
        )
        assert root_check["passed"] is False
        assert "PLEX_LIBRARY_ROOT" in root_check["detail"]

    @pytest.mark.anyio
    async def test_library_root_not_found(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_assess_plex_readiness

        missing = tmp_path / "no_such_dir"
        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, b"false\n")),
        ):
            with patch.dict("os.environ", {"PLEX_LIBRARY_ROOT": str(missing)}):
                result = await handle_assess_plex_readiness({}, ctx)

        assert result["status"] == "ok"
        assert result["ready"] is False
        exists_check = next(c for c in result["checks"] if c["name"] == "plex_library_root_exists")
        assert exists_check["passed"] is False
        assert "not found" in exists_check["detail"].lower()

    @pytest.mark.anyio
    async def test_all_checks_pass(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import _PLEX_MEDIA_TYPES, handle_assess_plex_readiness

        library_root = tmp_path / "plex"
        library_root.mkdir()
        for media_type in _PLEX_MEDIA_TYPES:
            (library_root / media_type).mkdir()

        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, b"true\n")),
        ):
            with patch(
                "core.gateway.builtin_handlers._shutil.disk_usage",
                return_value=_make_disk_usage(free=20 * 1024**3),
            ):
                with patch.dict("os.environ", {"PLEX_LIBRARY_ROOT": str(library_root)}):
                    result = await handle_assess_plex_readiness({}, ctx)

        assert result["status"] == "ok"
        assert result["ready"] is True
        assert all(c["passed"] for c in result["checks"])

    @pytest.mark.anyio
    async def test_low_disk_space_fails(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import _PLEX_MEDIA_TYPES, handle_assess_plex_readiness

        library_root = tmp_path / "plex"
        library_root.mkdir()
        for media_type in _PLEX_MEDIA_TYPES:
            (library_root / media_type).mkdir()

        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, b"true\n")),
        ):
            with patch(
                "core.gateway.builtin_handlers._shutil.disk_usage",
                return_value=_make_disk_usage(free=1 * 1024**3),
            ):
                with patch.dict("os.environ", {"PLEX_LIBRARY_ROOT": str(library_root)}):
                    result = await handle_assess_plex_readiness({}, ctx)

        assert result["status"] == "ok"
        assert result["ready"] is False
        disk_check = next(c for c in result["checks"] if c["name"] == "disk_space")
        assert disk_check["passed"] is False
        assert "low disk space" in disk_check["detail"].lower()

    @pytest.mark.anyio
    async def test_missing_media_subdirectory(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import handle_assess_plex_readiness

        library_root = tmp_path / "plex"
        library_root.mkdir()
        # Intentionally omit all media subdirectories.

        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, b"true\n")),
        ):
            with patch(
                "core.gateway.builtin_handlers._shutil.disk_usage",
                return_value=_make_disk_usage(free=20 * 1024**3),
            ):
                with patch.dict("os.environ", {"PLEX_LIBRARY_ROOT": str(library_root)}):
                    result = await handle_assess_plex_readiness({}, ctx)

        assert result["status"] == "ok"
        assert result["ready"] is False
        subdir_checks = [c for c in result["checks"] if c["name"].startswith("library_dir_")]
        assert len(subdir_checks) == 4
        assert all(not c["passed"] for c in subdir_checks)
        assert all("missing" in c["detail"].lower() for c in subdir_checks)

    @pytest.mark.anyio
    async def test_plex_container_not_running(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import _PLEX_MEDIA_TYPES, handle_assess_plex_readiness

        library_root = tmp_path / "plex"
        library_root.mkdir()
        for media_type in _PLEX_MEDIA_TYPES:
            (library_root / media_type).mkdir()

        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, b"false\n")),
        ):
            with patch(
                "core.gateway.builtin_handlers._shutil.disk_usage",
                return_value=_make_disk_usage(free=20 * 1024**3),
            ):
                with patch.dict("os.environ", {"PLEX_LIBRARY_ROOT": str(library_root)}):
                    result = await handle_assess_plex_readiness({}, ctx)

        assert result["status"] == "ok"
        assert result["ready"] is False
        container_check = next(c for c in result["checks"] if c["name"] == "plex_container_running")
        assert container_check["passed"] is False
        assert "not running" in container_check["detail"]

    @pytest.mark.anyio
    async def test_podman_not_installed(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import _PLEX_MEDIA_TYPES, handle_assess_plex_readiness

        library_root = tmp_path / "plex"
        library_root.mkdir()
        for media_type in _PLEX_MEDIA_TYPES:
            (library_root / media_type).mkdir()

        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            side_effect=FileNotFoundError,
        ):
            with patch(
                "core.gateway.builtin_handlers._shutil.disk_usage",
                return_value=_make_disk_usage(free=20 * 1024**3),
            ):
                with patch.dict("os.environ", {"PLEX_LIBRARY_ROOT": str(library_root)}):
                    result = await handle_assess_plex_readiness({}, ctx)

        assert result["status"] == "ok"
        assert result["ready"] is False
        container_check = next(c for c in result["checks"] if c["name"] == "plex_container_running")
        assert container_check["passed"] is False
        assert "podman not installed" in container_check["detail"]

    @pytest.mark.anyio
    async def test_checks_include_all_expected_names(self, tmp_path) -> None:
        from core.gateway.builtin_handlers import _PLEX_MEDIA_TYPES, handle_assess_plex_readiness

        library_root = tmp_path / "plex"
        library_root.mkdir()
        for media_type in _PLEX_MEDIA_TYPES:
            (library_root / media_type).mkdir()

        ctx = HandlerContext(agent_id="media_organization")
        with patch(
            "core.gateway.builtin_handlers._anyio.run_process",
            new=AsyncMock(return_value=_make_completed(0, b"true\n")),
        ):
            with patch(
                "core.gateway.builtin_handlers._shutil.disk_usage",
                return_value=_make_disk_usage(free=20 * 1024**3),
            ):
                with patch.dict("os.environ", {"PLEX_LIBRARY_ROOT": str(library_root)}):
                    result = await handle_assess_plex_readiness({}, ctx)

        check_names = {c["name"] for c in result["checks"]}
        assert "plex_library_root_configured" in check_names
        assert "plex_library_root_exists" in check_names
        assert "disk_space" in check_names
        assert "plex_container_running" in check_names
        for media_type in _PLEX_MEDIA_TYPES:
            assert f"library_dir_{media_type}" in check_names

