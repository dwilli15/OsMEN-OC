"""Tests for core/gateway/handlers.py and core/gateway/builtin_handlers.py.

Covers:
- Handler registration and lookup.
- Handler execution.
- ingest_url handler (with mocked httpx).
- search_knowledge handler.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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
