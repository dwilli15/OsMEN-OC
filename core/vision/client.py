"""Vision / multimodal inference client.

Provides image analysis, OCR, and visual Q&A via:
  1. Local: qwen3.5-4b-FLM on NPU (lemonade OpenAI-compat API)
  2. Fallback: GLM-4.5V on ZAI cloud API

The client spins up the local model on demand via lemonade CLI,
calls the OpenAI-compatible ``/v1/chat/completions`` endpoint with
base64 image content, and optionally falls back to cloud.
"""

from __future__ import annotations

import asyncio
import base64
import mimetypes
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from core.utils.config import load_config
from core.utils.exceptions import VisionError

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Defaults — overridable via config/compute-routing.yaml
_LOCAL_MODEL = "qwen3.5-4b-FLM"
_LOCAL_RECIPE = "flm"
_LOCAL_HOST = "127.0.0.1"
_LOCAL_PORT = 8001  # lemonade FLM default serve port
_CLOUD_MODEL = "glm-4.5v"
_CLOUD_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
_CONNECT_TIMEOUT = 5.0
_REQUEST_TIMEOUT = 120.0


class VisionBackend(str, Enum):
    """Available vision inference backends."""

    LOCAL_NPU = "local_npu"
    CLOUD_GLM = "cloud_glm"


@dataclass
class VisionResult:
    """Result from a vision inference call."""

    text: str
    backend_used: VisionBackend
    model: str
    usage: dict[str, int] = field(default_factory=dict)


def _encode_image(image_path: Path) -> tuple[str, str]:
    """Read and base64-encode a local image file.

    Returns:
        Tuple of (base64_data, mime_type).

    Raises:
        VisionError: If the file cannot be read.
    """
    if not image_path.is_file():
        raise VisionError(f"Image file not found: {image_path}")

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/png"

    data = image_path.read_bytes()
    return base64.b64encode(data).decode("ascii"), mime_type


def _build_messages(
    prompt: str,
    image_b64: str | None = None,
    image_mime: str = "image/png",
    image_url: str | None = None,
) -> list[dict[str, Any]]:
    """Build OpenAI-format messages with optional image content."""
    content: list[dict[str, Any]] = []

    if image_b64:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_mime};base64,{image_b64}"},
            }
        )
    elif image_url:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            }
        )

    content.append({"type": "text", "text": prompt})
    return [{"role": "user", "content": content}]


class VisionClient:
    """On-demand multimodal vision client.

    Tries local NPU model first, falls back to GLM-4.5V cloud.

    Args:
        local_base_url: Lemonade OpenAI-compat endpoint.
        local_model: Model ID for local inference.
        cloud_base_url: ZAI API base URL.
        cloud_model: Cloud vision model ID.
        cloud_api_key: ZAI API key (read from env if not provided).
        prefer_local: Whether to try local before cloud.
    """

    def __init__(
        self,
        *,
        local_base_url: str | None = None,
        local_model: str = _LOCAL_MODEL,
        cloud_base_url: str = _CLOUD_BASE_URL,
        cloud_model: str = _CLOUD_MODEL,
        cloud_api_key: str | None = None,
        prefer_local: bool = True,
    ) -> None:
        self._local_url = local_base_url or f"http://{_LOCAL_HOST}:{_LOCAL_PORT}/v1"
        self._local_model = local_model
        self._cloud_url = cloud_base_url.rstrip("/")
        self._cloud_model = cloud_model
        self._cloud_api_key = cloud_api_key
        self._prefer_local = prefer_local

    async def _check_local_available(self, client: httpx.AsyncClient) -> bool:
        """Probe lemonade to see if the local model is loaded."""
        try:
            resp = await client.get(
                f"{self._local_url}/models",
                timeout=_CONNECT_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                model_ids = [m["id"] for m in data.get("data", [])]
                return any(self._local_model.lower() in mid.lower() for mid in model_ids)
        except (httpx.HTTPError, httpx.TimeoutException):
            pass
        return False

    async def _call_local(
        self,
        messages: list[dict[str, Any]],
        client: httpx.AsyncClient,
        max_tokens: int = 2048,
    ) -> VisionResult:
        """Call the local lemonade OpenAI-compat endpoint."""
        payload = {
            "model": self._local_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        resp = await client.post(
            f"{self._local_url}/chat/completions",
            json=payload,
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        return VisionResult(
            text=body["choices"][0]["message"]["content"],
            backend_used=VisionBackend.LOCAL_NPU,
            model=body.get("model", self._local_model),
            usage=body.get("usage", {}),
        )

    async def _call_cloud(
        self,
        messages: list[dict[str, Any]],
        client: httpx.AsyncClient,
        max_tokens: int = 2048,
    ) -> VisionResult:
        """Call GLM-4.5V via ZAI cloud API."""
        if not self._cloud_api_key:
            raise VisionError("No cloud API key configured for GLM-4.5V fallback")

        payload = {
            "model": self._cloud_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        headers = {"Authorization": f"Bearer {self._cloud_api_key}"}
        resp = await client.post(
            f"{self._cloud_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        return VisionResult(
            text=body["choices"][0]["message"]["content"],
            backend_used=VisionBackend.CLOUD_GLM,
            model=body.get("model", self._cloud_model),
            usage=body.get("usage", {}),
        )

    async def analyze_image(
        self,
        prompt: str,
        *,
        image_path: Path | None = None,
        image_url: str | None = None,
        image_b64: str | None = None,
        image_mime: str = "image/png",
        max_tokens: int = 2048,
        force_backend: VisionBackend | None = None,
    ) -> VisionResult:
        """Analyze an image with a text prompt.

        Accepts one of: local file path, URL, or pre-encoded base64 data.
        Tries local NPU model first, falls back to GLM-4.5V cloud.

        Args:
            prompt: Question or instruction about the image.
            image_path: Path to a local image file.
            image_url: URL of a remote image.
            image_b64: Pre-encoded base64 image data.
            image_mime: MIME type when using image_b64.
            max_tokens: Maximum response tokens.
            force_backend: Skip fallback logic and use a specific backend.

        Returns:
            VisionResult with analysis text and metadata.

        Raises:
            VisionError: If all backends fail.
        """
        b64 = image_b64
        mime = image_mime

        if image_path and not image_b64:
            b64, mime = _encode_image(Path(image_path))

        if not b64 and not image_url:
            raise VisionError("Must provide image_path, image_url, or image_b64")

        messages = _build_messages(prompt, image_b64=b64, image_mime=mime, image_url=image_url)

        async with httpx.AsyncClient() as client:
            if force_backend == VisionBackend.CLOUD_GLM:
                return await self._call_cloud(messages, client, max_tokens)

            if force_backend == VisionBackend.LOCAL_NPU or self._prefer_local:
                try:
                    return await self._call_local(messages, client, max_tokens)
                except (httpx.HTTPError, httpx.TimeoutException, KeyError) as exc:
                    if force_backend == VisionBackend.LOCAL_NPU:
                        raise VisionError(f"Local vision failed: {exc}") from exc
                    logger.warning(
                        "Local vision failed ({}), falling back to cloud GLM-4.5V",
                        exc,
                    )

            # Cloud fallback
            try:
                return await self._call_cloud(messages, client, max_tokens)
            except (httpx.HTTPError, httpx.TimeoutException, KeyError) as exc:
                raise VisionError(f"All vision backends failed. Last error: {exc}") from exc

    async def ocr(
        self,
        *,
        image_path: Path | None = None,
        image_url: str | None = None,
        image_b64: str | None = None,
        image_mime: str = "image/png",
        language_hint: str = "English",
        force_backend: VisionBackend | None = None,
    ) -> VisionResult:
        """Extract text from an image using the vision model as OCR.

        Args:
            image_path: Path to a local image file.
            image_url: URL of a remote image.
            image_b64: Pre-encoded base64 image data.
            image_mime: MIME type when using image_b64.
            language_hint: Expected language of text in the image.
            force_backend: Skip fallback logic and use a specific backend.

        Returns:
            VisionResult with extracted text.
        """
        prompt = (
            f"Extract ALL text from this image exactly as it appears. "
            f"Preserve layout and formatting. Language hint: {language_hint}. "
            f"Return only the extracted text, no commentary."
        )
        return await self.analyze_image(
            prompt,
            image_path=image_path,
            image_url=image_url,
            image_b64=image_b64,
            image_mime=image_mime,
            max_tokens=4096,
            force_backend=force_backend,
        )
