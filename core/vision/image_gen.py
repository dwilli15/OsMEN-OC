"""On-demand image generation via lemonade sd-cpp backend.

Uses lemonade's OpenAI-compatible ``/v1/images/generations`` endpoint.
The sd-cpp server is started on demand and stopped after an idle timeout.
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from core.utils.exceptions import ImageGenError

_DEFAULT_MODEL = "SD-Turbo"
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 13395  # lemonade sd-cpp default port
_CONNECT_TIMEOUT = 5.0
_GENERATE_TIMEOUT = 300.0  # CPU image gen can be slow
_STARTUP_POLL_INTERVAL = 2.0
_STARTUP_MAX_WAIT = 120.0


@dataclass
class ImageGenResult:
    """Result from an image generation call."""

    image_b64: str
    model: str
    revised_prompt: str = ""
    output_path: Path | None = None


class ImageGenClient:
    """On-demand image generation via lemonade sd-cpp.

    The sd-cpp server is not always running. This client:
    1. Checks if the server is already up
    2. Starts it via ``lemonade run <model> --sdcpp cpu`` if not
    3. Waits for the health endpoint
    4. Calls ``/v1/images/generations``

    Args:
        model: sd-cpp model name (e.g. "SD-Turbo", "Flux-2-Klein-4B").
        host: Bind host for the sd-cpp server.
        port: Bind port for the sd-cpp server.
        output_dir: Directory to save generated images.
    """

    def __init__(
        self,
        *,
        model: str = _DEFAULT_MODEL,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
        output_dir: Path | None = None,
    ) -> None:
        self._model = model
        self._host = host
        self._port = port
        self._base_url = f"http://{host}:{port}"
        self._output_dir = output_dir or Path.home() / ".local/share/osmen/images"
        self._server_process: subprocess.Popen[bytes] | None = None

    async def _is_server_up(self) -> bool:
        """Check if the sd-cpp server is responding."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/v1/models",
                    timeout=_CONNECT_TIMEOUT,
                )
                return resp.status_code == 200
        except (httpx.HTTPError, httpx.TimeoutException):
            return False

    async def _start_server(self) -> None:
        """Start the sd-cpp server via lemonade CLI.

        Runs ``lemonade run <model> --sdcpp cpu --port <port>`` as a
        background process and waits for it to respond.

        Raises:
            ImageGenError: If the server fails to start within the timeout.
        """
        if await self._is_server_up():
            logger.info("sd-cpp server already running on {}:{}", self._host, self._port)
            return

        logger.info("Starting sd-cpp server: model={}, port={}", self._model, self._port)

        cmd = [
            "lemonade",
            "run",
            self._model,
            "--sdcpp",
            "cpu",
            "--port",
            str(self._port),
            "--host",
            self._host,
        ]

        self._server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        start = time.monotonic()
        while time.monotonic() - start < _STARTUP_MAX_WAIT:
            if self._server_process.poll() is not None:
                stderr = self._server_process.stderr
                err_msg = stderr.read().decode() if stderr else "unknown error"
                raise ImageGenError(
                    f"sd-cpp server exited during startup: {err_msg}"
                )
            if await self._is_server_up():
                logger.info("sd-cpp server ready after {:.1f}s", time.monotonic() - start)
                return
            await asyncio.sleep(_STARTUP_POLL_INTERVAL)

        # Timed out
        self.stop_server()
        raise ImageGenError(
            f"sd-cpp server failed to start within {_STARTUP_MAX_WAIT}s"
        )

    def stop_server(self) -> None:
        """Stop the sd-cpp server if we started it."""
        if self._server_process and self._server_process.poll() is None:
            logger.info("Stopping sd-cpp server (pid={})", self._server_process.pid)
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
            self._server_process = None

    async def generate(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        size: str = "512x512",
        steps: int | None = None,
        save: bool = True,
    ) -> ImageGenResult:
        """Generate an image from a text prompt.

        Starts the sd-cpp server on demand if not already running.

        Args:
            prompt: Text description of the image to generate.
            negative_prompt: Things to avoid in the image.
            size: Output size as "WxH" (e.g. "512x512").
            steps: Number of diffusion steps (None = model default).
            save: Whether to save the image to disk.

        Returns:
            ImageGenResult with base64 image data and metadata.

        Raises:
            ImageGenError: If generation fails.
        """
        await self._start_server()

        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "size": size,
            "response_format": "b64_json",
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if steps is not None:
            payload["steps"] = steps

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/v1/images/generations",
                    json=payload,
                    timeout=_GENERATE_TIMEOUT,
                )
                resp.raise_for_status()
                body = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            raise ImageGenError(f"Image generation failed: {exc}") from exc

        image_data = body["data"][0]
        image_b64 = image_data.get("b64_json", "")
        revised = image_data.get("revised_prompt", prompt)

        result = ImageGenResult(
            image_b64=image_b64,
            model=self._model,
            revised_prompt=revised,
        )

        if save and image_b64:
            result.output_path = self._save_image(image_b64, prompt)

        return result

    def _save_image(self, b64_data: str, prompt: str) -> Path:
        """Save a base64-encoded image to disk.

        Args:
            b64_data: Base64-encoded image data.
            prompt: Used to generate a filename slug.

        Returns:
            Path to the saved file.
        """
        import base64

        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Generate a safe filename from the prompt
        slug = "".join(c if c.isalnum() or c in "-_ " else "" for c in prompt[:50]).strip()
        slug = slug.replace(" ", "_").lower() or "image"
        timestamp = int(time.time())
        filename = f"{timestamp}_{slug}.png"
        path = self._output_dir / filename

        path.write_bytes(base64.b64decode(b64_data))
        logger.info("Saved generated image: {}", path)
        return path
