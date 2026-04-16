"""Text-to-speech via Lemonade Server kokoro-v1 (ONNX/CPU).

Migrated from piper-tts and pocket-tts (local pip packages) to Lemonade's
OpenAI-compatible ``/v1/audio/speech`` endpoint using the kokoro-v1 model.

Kokoro produces high-quality multi-voice, multi-language speech at 24 kHz
with a small 82M parameter ONNX model running on CPU.

Provider: Lemonade Server (http://127.0.0.1:13305)
Model: kokoro-v1
"""

from __future__ import annotations

import wave
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import anyio
import httpx
from loguru import logger

if TYPE_CHECKING:
    pass


class TTSEngine(str, Enum):
    """Available TTS engine identifiers."""

    KOKORO = "kokoro"
    PIPER = "piper"
    POCKET = "pocket"


@dataclass(frozen=True)
class TTSResult:
    """Result from a TTS synthesis operation."""

    audio_path: Path
    engine: TTSEngine
    sample_rate: int
    size_bytes: int


# ---------------------------------------------------------------------------
# Kokoro TTS via Lemonade
# ---------------------------------------------------------------------------


@dataclass
class KokoroTTS:
    """Text-to-speech via Lemonade Server using the kokoro-v1 model.

    Sends text to ``/v1/audio/speech`` and writes the returned PCM audio
    to a WAV file.

    Args:
        base_url: Lemonade Server base URL.
        model: Kokoro model identifier.
        voice: Voice name (kokoro supports multiple voices).
        speed: Speech speed multiplier (1.0 = normal).
        timeout: HTTP request timeout in seconds.
    """

    base_url: str = "http://127.0.0.1:13305"
    model: str = "kokoro-v1"
    voice: str = "af_bella"
    speed: float = 1.0
    timeout: float = 60.0
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    def _get_client(self) -> httpx.AsyncClient:
        """Return (or create) the shared async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Shut down the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def synthesize_sync(
        self,
        text: str,
        output_path: str | Path,
        *,
        voice: str | None = None,
        speed: float | None = None,
    ) -> TTSResult:
        """Synthesize text to a WAV file synchronously."""
        return anyio.run(
            lambda: self.synthesize(
                text,
                output_path,
                voice=voice,
                speed=speed,
            )
        )

    async def synthesize(
        self,
        text: str,
        output_path: str | Path,
        *,
        voice: str | None = None,
        speed: float | None = None,
    ) -> TTSResult:
        """Synthesize text to a WAV file asynchronously.

        Args:
            text: Text to synthesize.
            output_path: Path for the output WAV file.
            voice: Override voice name (default: self.voice).
            speed: Override speed multiplier (default: self.speed).

        Returns:
            :class:`TTSResult` with output file metadata.

        Raises:
            httpx.HTTPStatusError: If Lemonade returns an error status.
        """
        client = self._get_client()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        payload: dict[str, Any] = {
            "input": text,
            "model": self.model,
            "voice": voice or self.voice,
        }
        if speed is not None:
            payload["speed"] = speed
        elif self.speed != 1.0:
            payload["speed"] = self.speed

        resp = await client.post(
            "/v1/audio/speech",
            json=payload,
        )
        resp.raise_for_status()

        # Lemonade returns raw PCM audio (24 kHz, 16-bit, mono)
        pcm_data = resp.content

        # Write WAV header + PCM data
        sample_rate = 24000
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)

        size = output_path.stat().st_size
        logger.debug(
            "Kokoro synthesized {} chars → {} ({:,} bytes)",
            len(text),
            output_path.name,
            size,
        )
        return TTSResult(
            audio_path=output_path,
            engine=TTSEngine.KOKORO,
            sample_rate=sample_rate,
            size_bytes=size,
        )


# ---------------------------------------------------------------------------
# TTS Dispatcher
# ---------------------------------------------------------------------------


@dataclass
class TTSDispatcher:
    """Multi-engine TTS dispatcher.

    Routes synthesis requests to the appropriate engine:
    - Kokoro: primary, multi-voice, multi-language, via Lemonade Server.
    - Piper/Pocket: legacy, retained for backward compatibility.

    Args:
        kokoro: KokoroTTS instance (primary engine).
        default_engine: Default engine for unspecified requests.
    """

    kokoro: KokoroTTS = field(default_factory=KokoroTTS)
    default_engine: TTSEngine = TTSEngine.KOKORO

    def synthesize_sync(
        self,
        text: str,
        output_path: str | Path,
        *,
        engine: TTSEngine | None = None,
        **kwargs: Any,
    ) -> TTSResult:
        """Synthesize text using the specified or default engine."""
        engine = engine or self.default_engine

        if engine in (TTSEngine.KOKORO, TTSEngine.PIPER, TTSEngine.POCKET):
            # All routes go through kokoro now; legacy enums are accepted
            # but mapped to kokoro.
            return self.kokoro.synthesize_sync(text, output_path, **kwargs)

        msg = f"Unknown TTS engine: {engine}"
        raise ValueError(msg)

    async def synthesize(
        self,
        text: str,
        output_path: str | Path,
        *,
        engine: TTSEngine | None = None,
        **kwargs: Any,
    ) -> TTSResult:
        """Synthesize text asynchronously."""
        engine = engine or self.default_engine

        if engine in (TTSEngine.KOKORO, TTSEngine.PIPER, TTSEngine.POCKET):
            return await self.kokoro.synthesize(text, output_path, **kwargs)

        msg = f"Unknown TTS engine: {engine}"
        raise ValueError(msg)

    async def close(self) -> None:
        """Release all engine resources."""
        await self.kokoro.close()


# Backward-compatible aliases for older imports.
PiperTTS = KokoroTTS
PocketTTS = KokoroTTS
