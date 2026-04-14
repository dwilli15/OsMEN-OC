"""Speech-to-text using faster-whisper (CTranslate2 backend).

Supports CPU and CUDA, configurable model size, and optional streaming.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Iterator

    from faster_whisper import WhisperModel


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


@dataclass
class WhisperSTT:
    """Speech-to-text engine wrapping faster-whisper.

    Args:
        model_size: Whisper model size (tiny, base, small, medium, large-v3).
        device: Compute device (cpu, cuda, auto).
        compute_type: Quantization type (int8, float16, float32).
        language: Force language code or None for auto-detect.
    """

    model_size: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str | None = None
    _model: WhisperModel | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def _ensure_model(self) -> WhisperModel:
        """Lazy-load the Whisper model on first use (thread-safe)."""
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                logger.info(
                    "Loading Whisper {} on {} ({})",
                    self.model_size,
                    self.device,
                    self.compute_type,
                )
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                logger.info("Whisper model loaded")
        return self._model

    def transcribe_sync(
        self,
        audio_path: str | Path,
        *,
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> TranscriptionResult:
        """Transcribe an audio file synchronously.

        Args:
            audio_path: Path to audio file (WAV, MP3, FLAC, etc.).
            beam_size: Beam search width.
            vad_filter: Filter out non-speech segments.

        Returns:
            TranscriptionResult with segments and metadata.
        """
        model = self._ensure_model()
        audio_path = Path(audio_path)
        if not audio_path.exists():
            msg = f"Audio file not found: {audio_path}"
            raise FileNotFoundError(msg)

        segments_iter, info = model.transcribe(
            str(audio_path),
            beam_size=beam_size,
            language=self.language,
            vad_filter=vad_filter,
        )

        segments = [
            Segment(
                start=s.start,
                end=s.end,
                text=s.text,
                avg_logprob=s.avg_logprob,
                no_speech_prob=s.no_speech_prob,
            )
            for s in segments_iter
        ]

        result = TranscriptionResult(
            segments=segments,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
        )
        logger.info(
            "Transcribed {} ({:.1f}s, lang={}, {} segments)",
            audio_path.name,
            result.duration,
            result.language,
            len(segments),
        )
        return result

    async def transcribe(
        self,
        audio_path: str | Path,
        *,
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> TranscriptionResult:
        """Transcribe an audio file asynchronously (runs in thread pool).

        Args:
            audio_path: Path to audio file.
            beam_size: Beam search width.
            vad_filter: Filter out non-speech segments.

        Returns:
            TranscriptionResult with segments and metadata.
        """
        return await anyio.to_thread.run_sync(
            lambda: self.transcribe_sync(
                audio_path, beam_size=beam_size, vad_filter=vad_filter
            ),
        )

    def segments_iter(
        self,
        audio_path: str | Path,
        *,
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> Iterator[Segment]:
        """Yield transcription segments one at a time (streaming).

        Args:
            audio_path: Path to audio file.
            beam_size: Beam search width.
            vad_filter: Filter out non-speech segments.

        Yields:
            Segment objects as they are decoded.
        """
        model = self._ensure_model()
        audio_path = Path(audio_path)
        if not audio_path.exists():
            msg = f"Audio file not found: {audio_path}"
            raise FileNotFoundError(msg)

        segments_iter, _info = model.transcribe(
            str(audio_path),
            beam_size=beam_size,
            language=self.language,
            vad_filter=vad_filter,
        )
        for s in segments_iter:
            yield Segment(
                start=s.start,
                end=s.end,
                text=s.text,
                avg_logprob=s.avg_logprob,
                no_speech_prob=s.no_speech_prob,
            )

    def close(self) -> None:
        """Release the model from memory."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Whisper model released")
