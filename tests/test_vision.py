"""Tests for core.vision — VisionClient and ImageGenClient."""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from core.utils.exceptions import ImageGenError, VisionError
from core.vision.client import (
    VisionBackend,
    VisionClient,
    VisionResult,
    _build_messages,
    _encode_image,
)
from core.vision.image_gen import ImageGenClient, ImageGenResult


# ── Helper fixtures ─────────────────────────────────────────────────


@pytest.fixture
def tmp_image(tmp_path: Path) -> Path:
    """Create a minimal valid PNG file for testing."""
    # Minimal 1x1 white PNG
    png_data = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
        b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    img = tmp_path / "test.png"
    img.write_bytes(png_data)
    return img


@pytest.fixture
def vision_client() -> VisionClient:
    """VisionClient with known endpoints for testing."""
    return VisionClient(
        local_base_url="http://127.0.0.1:8001/v1",
        local_model="qwen3.5-4b-FLM",
        cloud_base_url="https://api.z.ai/api/coding/paas/v4",
        cloud_model="glm-4.5v",
        cloud_api_key="test-key-not-real",
    )


@pytest.fixture
def image_gen_client(tmp_path: Path) -> ImageGenClient:
    """ImageGenClient with test output directory."""
    return ImageGenClient(
        model="SD-Turbo",
        port=13395,
        output_dir=tmp_path / "images",
    )


# ── _encode_image tests ────────────────────────────────────────────


class TestEncodeImage:
    def test_encode_valid_png(self, tmp_image: Path) -> None:
        b64, mime = _encode_image(tmp_image)
        assert isinstance(b64, str)
        assert len(b64) > 0
        # Round-trip: decode should not raise
        base64.b64decode(b64)
        assert mime == "image/png"

    def test_encode_jpeg(self, tmp_path: Path) -> None:
        jpg = tmp_path / "photo.jpg"
        jpg.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-data")
        b64, mime = _encode_image(jpg)
        assert mime == "image/jpeg"
        assert len(b64) > 0

    def test_encode_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(VisionError, match="not found"):
            _encode_image(tmp_path / "nonexistent.png")

    def test_encode_unknown_extension_defaults_png(self, tmp_path: Path) -> None:
        f = tmp_path / "data.qzx9"
        f.write_bytes(b"some data")
        _, mime = _encode_image(f)
        assert mime == "image/png"


# ── _build_messages tests ──────────────────────────────────────────


class TestBuildMessages:
    def test_text_only(self) -> None:
        msgs = _build_messages("describe this")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        content = msgs[0]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "describe this"

    def test_with_base64_image(self) -> None:
        msgs = _build_messages("what is this?", image_b64="abc123", image_mime="image/jpeg")
        content = msgs[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "image_url"
        assert "data:image/jpeg;base64,abc123" in content[0]["image_url"]["url"]
        assert content[1]["type"] == "text"

    def test_with_url_image(self) -> None:
        msgs = _build_messages("analyze", image_url="https://example.com/img.png")
        content = msgs[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "image_url"
        assert content[0]["image_url"]["url"] == "https://example.com/img.png"

    def test_b64_takes_precedence_over_url(self) -> None:
        msgs = _build_messages(
            "test", image_b64="b64data", image_url="https://example.com/img.png"
        )
        content = msgs[0]["content"]
        # b64 is first, URL is ignored when b64 is provided
        assert "base64" in content[0]["image_url"]["url"]


# ── VisionResult tests ─────────────────────────────────────────────


class TestVisionResult:
    def test_creation(self) -> None:
        r = VisionResult(
            text="A cat",
            backend_used=VisionBackend.LOCAL_NPU,
            model="qwen3.5-4b-FLM",
        )
        assert r.text == "A cat"
        assert r.backend_used == VisionBackend.LOCAL_NPU
        assert r.usage == {}

    def test_with_usage(self) -> None:
        r = VisionResult(
            text="test",
            backend_used=VisionBackend.CLOUD_GLM,
            model="glm-4.5v",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
        )
        assert r.usage["prompt_tokens"] == 100


# ── VisionBackend enum tests ──────────────────────────────────────


class TestVisionBackend:
    def test_values(self) -> None:
        assert VisionBackend.LOCAL_NPU == "local_npu"
        assert VisionBackend.CLOUD_GLM == "cloud_glm"

    def test_from_string(self) -> None:
        assert VisionBackend("local_npu") == VisionBackend.LOCAL_NPU


# ── VisionClient tests ─────────────────────────────────────────────


class TestVisionClient:
    def test_init_defaults(self) -> None:
        c = VisionClient()
        assert "127.0.0.1" in c._local_url
        assert c._cloud_model == "glm-4.5v"
        assert c._prefer_local is True

    def test_init_custom(self) -> None:
        c = VisionClient(
            local_base_url="http://custom:1234/v1",
            cloud_model="glm-4.5v",
            prefer_local=False,
        )
        assert c._local_url == "http://custom:1234/v1"
        assert c._prefer_local is False

    @pytest.mark.anyio
    async def test_analyze_image_no_input_raises(self, vision_client: VisionClient) -> None:
        with pytest.raises(VisionError, match="Must provide"):
            await vision_client.analyze_image("describe this")

    @pytest.mark.anyio
    async def test_analyze_image_local_success(
        self, vision_client: VisionClient, tmp_image: Path
    ) -> None:
        mock_response = httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "A white pixel"}}],
                "model": "qwen3.5-4b-FLM",
                "usage": {"prompt_tokens": 50, "completion_tokens": 10},
            },
            request=httpx.Request("POST", "http://test"),
        )

        with patch("core.vision.client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await vision_client.analyze_image(
                "what is this?", image_path=tmp_image
            )

        assert result.text == "A white pixel"
        assert result.backend_used == VisionBackend.LOCAL_NPU
        assert result.usage["prompt_tokens"] == 50

    @pytest.mark.anyio
    async def test_analyze_image_local_fails_cloud_fallback(
        self, vision_client: VisionClient, tmp_image: Path
    ) -> None:
        cloud_response = httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Cloud sees a pixel"}}],
                "model": "glm-4.5v",
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
            request=httpx.Request("POST", "http://test"),
        )

        call_count = 0

        async def mock_post(url: str, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Local call fails
                raise httpx.ConnectError("Connection refused")
            return cloud_response

        with patch("core.vision.client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await vision_client.analyze_image(
                "what is this?", image_path=tmp_image
            )

        assert result.text == "Cloud sees a pixel"
        assert result.backend_used == VisionBackend.CLOUD_GLM

    @pytest.mark.anyio
    async def test_analyze_image_force_cloud(
        self, vision_client: VisionClient, tmp_image: Path
    ) -> None:
        cloud_response = httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Forced cloud"}}],
                "model": "glm-4.5v",
            },
            request=httpx.Request("POST", "http://test"),
        )

        with patch("core.vision.client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=cloud_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await vision_client.analyze_image(
                "describe",
                image_path=tmp_image,
                force_backend=VisionBackend.CLOUD_GLM,
            )

        assert result.backend_used == VisionBackend.CLOUD_GLM

    @pytest.mark.anyio
    async def test_analyze_image_force_local_fails_no_fallback(
        self, vision_client: VisionClient, tmp_image: Path
    ) -> None:
        with patch("core.vision.client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(VisionError, match="Local vision failed"):
                await vision_client.analyze_image(
                    "describe",
                    image_path=tmp_image,
                    force_backend=VisionBackend.LOCAL_NPU,
                )

    @pytest.mark.anyio
    async def test_analyze_all_backends_fail_raises(
        self, vision_client: VisionClient, tmp_image: Path
    ) -> None:
        with patch("core.vision.client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(VisionError, match="All vision backends failed"):
                await vision_client.analyze_image(
                    "describe", image_path=tmp_image
                )

    @pytest.mark.anyio
    async def test_cloud_no_api_key_raises(self, tmp_image: Path) -> None:
        client = VisionClient(cloud_api_key=None, prefer_local=False)

        with patch("core.vision.client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(VisionError, match="No cloud API key"):
                await client.analyze_image(
                    "describe", image_path=tmp_image
                )


# ── OCR tests ──────────────────────────────────────────────────────


class TestOCR:
    @pytest.mark.anyio
    async def test_ocr_calls_analyze_with_extraction_prompt(
        self, vision_client: VisionClient, tmp_image: Path
    ) -> None:
        mock_response = httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Hello World"}}],
                "model": "qwen3.5-4b-FLM",
            },
            request=httpx.Request("POST", "http://test"),
        )

        with patch("core.vision.client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await vision_client.ocr(image_path=tmp_image)

        assert result.text == "Hello World"
        # Verify the prompt included OCR-specific instructions
        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        prompt_text = payload["messages"][0]["content"][-1]["text"]
        assert "Extract ALL text" in prompt_text

    @pytest.mark.anyio
    async def test_ocr_with_language_hint(
        self, vision_client: VisionClient, tmp_image: Path
    ) -> None:
        mock_response = httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Bonjour"}}],
                "model": "qwen3.5-4b-FLM",
            },
            request=httpx.Request("POST", "http://test"),
        )

        with patch("core.vision.client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await vision_client.ocr(
                image_path=tmp_image, language_hint="French"
            )

        assert result.text == "Bonjour"
        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        prompt_text = payload["messages"][0]["content"][-1]["text"]
        assert "French" in prompt_text


# ── ImageGenResult tests ───────────────────────────────────────────


class TestImageGenResult:
    def test_creation(self) -> None:
        r = ImageGenResult(
            image_b64="abc123",
            model="SD-Turbo",
        )
        assert r.image_b64 == "abc123"
        assert r.model == "SD-Turbo"
        assert r.revised_prompt == ""
        assert r.output_path is None

    def test_with_path(self, tmp_path: Path) -> None:
        r = ImageGenResult(
            image_b64="abc123",
            model="SD-Turbo",
            output_path=tmp_path / "out.png",
        )
        assert r.output_path == tmp_path / "out.png"


# ── ImageGenClient tests ──────────────────────────────────────────


class TestImageGenClient:
    def test_init_defaults(self) -> None:
        c = ImageGenClient()
        assert c._model == "SD-Turbo"
        assert c._port == 13395
        assert c._server_process is None

    def test_init_custom(self, tmp_path: Path) -> None:
        c = ImageGenClient(
            model="Flux-2-Klein-4B",
            port=9999,
            output_dir=tmp_path / "gen",
        )
        assert c._model == "Flux-2-Klein-4B"
        assert c._port == 9999
        assert c._output_dir == tmp_path / "gen"

    @pytest.mark.anyio
    async def test_is_server_up_when_down(self, image_gen_client: ImageGenClient) -> None:
        with patch("core.vision.image_gen.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await image_gen_client._is_server_up()

        assert result is False

    @pytest.mark.anyio
    async def test_is_server_up_when_running(self, image_gen_client: ImageGenClient) -> None:
        with patch("core.vision.image_gen.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=httpx.Response(200, request=httpx.Request("GET", "http://test"))
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await image_gen_client._is_server_up()

        assert result is True

    @pytest.mark.anyio
    async def test_generate_success(self, image_gen_client: ImageGenClient) -> None:
        # Minimal valid base64 PNG for save test
        fake_b64 = base64.b64encode(b"fake-image-data").decode()

        gen_response = httpx.Response(
            200,
            json={
                "data": [
                    {
                        "b64_json": fake_b64,
                        "revised_prompt": "a beautiful sunset",
                    }
                ]
            },
            request=httpx.Request("POST", "http://test"),
        )

        with (
            patch.object(image_gen_client, "_start_server", new_callable=AsyncMock),
            patch("core.vision.image_gen.httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=gen_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await image_gen_client.generate("a sunset over mountains")

        assert result.image_b64 == fake_b64
        assert result.model == "SD-Turbo"
        assert result.revised_prompt == "a beautiful sunset"
        assert result.output_path is not None
        assert result.output_path.exists()

    @pytest.mark.anyio
    async def test_generate_no_save(self, image_gen_client: ImageGenClient) -> None:
        fake_b64 = base64.b64encode(b"image").decode()

        gen_response = httpx.Response(
            200,
            json={"data": [{"b64_json": fake_b64}]},
            request=httpx.Request("POST", "http://test"),
        )

        with (
            patch.object(image_gen_client, "_start_server", new_callable=AsyncMock),
            patch("core.vision.image_gen.httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=gen_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await image_gen_client.generate("test", save=False)

        assert result.output_path is None

    @pytest.mark.anyio
    async def test_generate_http_error_raises(self, image_gen_client: ImageGenClient) -> None:
        with (
            patch.object(image_gen_client, "_start_server", new_callable=AsyncMock),
            patch("core.vision.image_gen.httpx.AsyncClient") as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("failed"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with pytest.raises(ImageGenError, match="Image generation failed"):
                await image_gen_client.generate("test")

    def test_stop_server_no_process(self, image_gen_client: ImageGenClient) -> None:
        # Should not raise when no server is running
        image_gen_client.stop_server()

    def test_stop_server_with_process(self, image_gen_client: ImageGenClient) -> None:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.wait.return_value = 0
        image_gen_client._server_process = mock_proc

        image_gen_client.stop_server()

        mock_proc.terminate.assert_called_once()
        assert image_gen_client._server_process is None

    def test_save_image(self, image_gen_client: ImageGenClient) -> None:
        data = base64.b64encode(b"png-data-here").decode()
        path = image_gen_client._save_image(data, "test prompt with spaces")

        assert path.exists()
        assert path.read_bytes() == b"png-data-here"
        assert "test_prompt_with_spaces" in path.name
        assert path.suffix == ".png"

    def test_save_image_creates_directory(self, image_gen_client: ImageGenClient) -> None:
        # output_dir doesn't exist yet
        assert not image_gen_client._output_dir.exists()

        data = base64.b64encode(b"data").decode()
        path = image_gen_client._save_image(data, "new dir test")

        assert path.exists()
        assert image_gen_client._output_dir.exists()


# ── Agent manifest integration ─────────────────────────────────────


class TestVisionToolsManifest:
    """Verify the vision_tools agent manifest is valid and scannable."""

    def test_manifest_loads(self) -> None:
        from core.gateway.mcp import scan_manifests

        tools = scan_manifests("agents")
        vision_tools = [t for t in tools if t.agent_id == "vision_tools"]
        assert len(vision_tools) == 3

    def test_manifest_tool_names(self) -> None:
        from core.gateway.mcp import scan_manifests

        tools = scan_manifests("agents")
        vision_names = {t.name for t in tools if t.agent_id == "vision_tools"}
        assert vision_names == {"analyze_image", "ocr_extract", "generate_image"}

    def test_manifest_risk_levels(self) -> None:
        from core.gateway.mcp import scan_manifests

        tools = scan_manifests("agents")
        for t in tools:
            if t.agent_id == "vision_tools":
                assert t.risk_level == "low"
