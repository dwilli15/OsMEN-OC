"""Speech-to-text via Lemonade Server whisper-v3:turbo (FLM/NPU).

Migrated from faster-whisper (local CTranslate2) to Lemonade's
OpenAI-compatible ``/v1/audio/transcriptions`` endpoint.

The transcription runs on the AMD XDNA 2 NPU via FLM for power-efficient
always-on transcription, falling back to NVIDIA CUDA when the NPU is
unavailable (see compute-routing.yaml rule ``transcription_npu``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import anyio
import httpx
from loguru import logger

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class Segment:
    """A single transcription segment."""

    start: float
    end: float
    text: str
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0


@dataclass(frozen=True)
class TranscriptionResult:
    """Full transcription result with metadata."""

    segments: list[Segment]
    language: str
    language_probability: float
    duration: float

    @property
    def text(self) -> str:
        """Concatenated text from all segments."""
        return " ".join(s.text.strip() for s in self.segments)


# ---------------------------------------------------------------------------
# Lemonade STT client
# ---------------------------------------------------------------------------


@dataclass
class LemonadeSTT:
    """Speech-to-text via Lemonade Server OpenAI-compatible API.

    Sends audio files to ``/v1/audio/transcriptions`` and parses the
    response into :class:`TranscriptionResult`.

    Args:
        base_url: Lemonade Server base URL (default: localhost:13305).
        model: Whisper model identifier (default: whisper-v3-turbo-FLM).
        language: Force language code or ``None`` for auto-detect.
        timeout: HTTP request timeout in seconds.
    """

    base_url: str = "http://127.0.0.1:13305"
    model: str = "whisper-v3-turbo-FLM"
    language: str | None = None
    timeout: float = 120.0
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

    def transcribe_sync(
        self,
        audio_path: str | Path,
        *,
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> TranscriptionResult:
        """Transcribe an audio file synchronously via Lemonade API."""
        return anyio.run(
            lambda: self.transcribe(
                audio_path,
                beam_size=beam_size,
                vad_filter=vad_filter,
            )
        )

    async def transcribe(
        self,
        audio_path: str | Path,
        *,
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> TranscriptionResult:
        """Transcribe an audio file asynchronously via Lemonade API.

        Args:
            audio_path: Path to audio file (WAV, MP3, FLAC, MP4, etc.).
            beam_size: Beam search width (passed to Lemonade).
            vad_filter: Request voice-activity-detection filtering.

        Returns:
            :class:`TranscriptionResult` with segments and metadata.

        Raises:
            FileNotFoundError: If ``audio_path`` does not exist.
            httpx.HTTPStatusError: If Lemonade returns an error status.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            msg = f"Audio file not found: {audio_path}"
            raise FileNotFoundError(msg)

        client = self._get_client()

        # Build multipart form data
        form_fields: dict[str, Any] = {
            "model": self.model,
        }
        if self.language:
            form_fields["language"] = self.language
        if beam_size != 5:
            form_fields["beam_size"] = str(beam_size)

        with audio_path.open("rb") as f:
            resp = await client.post(
                "/v1/audio/transcriptions",
                data=form_fields,
                files={"file": (audio_path.name, f, "audio/wav")},
            )
        resp.raise_for_status()

        body = resp.json()

        # Lemonade returns either a plain text string or a JSON object
        if isinstance(body, str):
            text = body
            segments = [Segment(start=0.0, end=0.0, text=text.strip())]
            return TranscriptionResult(
                segments=segments,
                language=self.language or "unknown",
                language_probability=1.0,
                duration=0.0,
            )

        # Detailed response format
        text = body.get("text", "")
        segments = [
            Segment(
                start=s.get("start", 0.0),
                end=s.get("end", 0.0),
                text=s.get("text", ""),
                avg_logprob=s.get("avg_logprob", 0.0),
                no_speech_prob=s.get("no_speech_prob", 0.0),
            )
            for s in body.get("segments", [])
        ]

        if not segments and text:
            segments = [Segment(start=0.0, end=0.0, text=text.strip())]

        duration = body.get("duration", 0.0)
        language = body.get("language", self.language or "unknown")
        language_probability = body.get("language_probability", 1.0)

        result = TranscriptionResult(
            segments=segments,
            language=language,
            language_probability=language_probability,
            duration=duration,
        )
        logger.info(
            "Transcribed {} ({:.1f}s, lang={}, {} segments) via Lemonade",
            audio_path.name,
            duration,
            language,
            len(segments),
        )
        return result

    async def segments_iter(
        self,
        audio_path: str | Path,
        *,
        beam_size: int = 5,
        vad_filter: bool = True,
    ):
        """Yield transcription segments one at a time.

        Since Lemonade returns all segments at once, this simply
        iterates the result of :meth:`transcribe`.
        """
        result = await self.transcribe(
            audio_path, beam_size=beam_size, vad_filter=vad_filter
        )
        for seg in result.segments:
            yield seg


# ---------------------------------------------------------------------------
# Backward-compatible alias
# ---------------------------------------------------------------------------

#: Alias so that existing code referencing ``WhisperSTT`` continues to work.
#: The old class has been replaced by :class:`LemonadeSTT` which talks to
#: the Lemonade Server instead of loading a local faster-whisper model.
WhisperSTT = LemonadeSTT
