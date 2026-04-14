"""Text-to-speech engines and multi-engine dispatcher.

Engines:
- PiperTTS: Fast, lightweight, local ONNX models (primary).
- PocketTTS: PyTorch-based, supports voice cloning (secondary).
- TTSDispatcher: Routes requests to the appropriate engine.
"""

from __future__ import annotations

import threading
import wave
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
from loguru import logger

if TYPE_CHECKING:
    from piper import PiperVoice


class TTSEngine(str, Enum):
    """Available TTS engine identifiers."""

    PIPER = "piper"
    POCKET = "pocket"


@dataclass(frozen=True)
class TTSResult:
    """Result from a TTS synthesis operation."""

    audio_path: Path
    engine: TTSEngine
    sample_rate: int
    size_bytes: int


@dataclass
class PiperTTS:
    """Piper TTS engine using ONNX models via piper-tts.

    Args:
        model_path: Path to the .onnx voice model file.
        use_cuda: Use GPU acceleration if available.
    """

    model_path: str | Path = Path.home() / ".local/share/osmen/models/piper/en_US-lessac-medium.onnx"
    use_cuda: bool = False
    _voice: PiperVoice | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def _ensure_voice(self) -> PiperVoice:
        """Lazy-load the voice model (thread-safe)."""
        if self._voice is not None:
            return self._voice
        with self._lock:
            if self._voice is None:
                from piper import PiperVoice

                model_path = Path(self.model_path)
                if not model_path.exists():
                    msg = f"Piper model not found: {model_path}"
                    raise FileNotFoundError(msg)

                logger.info("Loading Piper voice model: {}", model_path.name)
                self._voice = PiperVoice.load(str(model_path), use_cuda=self.use_cuda)
                logger.info(
                    "Piper voice loaded (sample_rate={})", self._voice.config.sample_rate
                )
        return self._voice

    def synthesize_sync(
        self,
        text: str,
        output_path: str | Path,
        *,
        speaker_id: int | None = None,
        length_scale: float | None = None,
        noise_scale: float | None = None,
        noise_w: float | None = None,
    ) -> TTSResult:
        """Synthesize text to a WAV file synchronously.

        Args:
            text: Text to synthesize.
            output_path: Path for the output WAV file.
            speaker_id: Speaker ID for multi-speaker models.
            length_scale: Speed adjustment (lower = faster).
            noise_scale: Phoneme-level noise.
            noise_w: Word-level noise.

        Returns:
            TTSResult with output file metadata.
        """
        voice = self._ensure_voice()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        synth_kwargs: dict = {}
        if speaker_id is not None:
            synth_kwargs["speaker_id"] = speaker_id
        if length_scale is not None:
            synth_kwargs["length_scale"] = length_scale
        if noise_scale is not None:
            synth_kwargs["noise_scale"] = noise_scale
        if noise_w is not None:
            synth_kwargs["noise_w"] = noise_w

        wav_file = wave.open(str(output_path), "wb")
        try:
            voice.synthesize_wav(text, wav_file, **synth_kwargs)
        except Exception:
            wav_file.close()
            output_path.unlink(missing_ok=True)
            raise
        else:
            wav_file.close()

        size = output_path.stat().st_size
        logger.debug(
            "Piper synthesized {} chars → {} ({:,} bytes)",
            len(text),
            output_path.name,
            size,
        )
        return TTSResult(
            audio_path=output_path,
            engine=TTSEngine.PIPER,
            sample_rate=voice.config.sample_rate,
            size_bytes=size,
        )

    async def synthesize(
        self,
        text: str,
        output_path: str | Path,
        **kwargs: object,
    ) -> TTSResult:
        """Synthesize text to WAV asynchronously (runs in thread pool)."""
        return await anyio.to_thread.run_sync(
            lambda: self.synthesize_sync(text, output_path, **kwargs)
        )

    def close(self) -> None:
        """Release the voice model."""
        if self._voice is not None:
            del self._voice
            self._voice = None
            logger.info("Piper voice released")


@dataclass
class PocketTTS:
    """Pocket TTS engine for high-quality and voice cloning synthesis.

    Uses PyTorch + pocket-tts. Heavier than Piper but supports voice cloning
    and produces higher quality output for longform content.

    Args:
        device: Torch device string (cpu, cuda).
    """

    device: str = "cpu"
    _model: object | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def _ensure_model(self) -> object:
        """Lazy-load the Pocket TTS model (thread-safe)."""
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from pocket_tts import TTSModel

                logger.info("Loading Pocket TTS model on {}", self.device)
                self._model = TTSModel.from_pretrained(device=self.device)
                logger.info("Pocket TTS model loaded")
        return self._model

    def synthesize_sync(
        self,
        text: str,
        output_path: str | Path,
        *,
        speaker_wav: str | Path | None = None,
    ) -> TTSResult:
        """Synthesize text to a WAV file.

        Args:
            text: Text to synthesize.
            output_path: Path for the output WAV file.
            speaker_wav: Optional reference audio for voice cloning.

        Returns:
            TTSResult with output file metadata.
        """
        model = self._ensure_model()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        gen_kwargs: dict = {"text": text}
        if speaker_wav is not None:
            gen_kwargs["speaker_wav"] = str(speaker_wav)

        audio = model.generate(**gen_kwargs)

        # Write to WAV
        import numpy as np

        wav_file = wave.open(str(output_path), "wb")
        try:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
            wav_file.writeframes(audio_int16.tobytes())
        except Exception:
            wav_file.close()
            output_path.unlink(missing_ok=True)
            raise
        else:
            wav_file.close()

        size = output_path.stat().st_size
        logger.debug(
            "Pocket TTS synthesized {} chars → {} ({:,} bytes)",
            len(text),
            output_path.name,
            size,
        )
        return TTSResult(
            audio_path=output_path,
            engine=TTSEngine.POCKET,
            sample_rate=24000,
            size_bytes=size,
        )

    async def synthesize(
        self,
        text: str,
        output_path: str | Path,
        **kwargs: object,
    ) -> TTSResult:
        """Synthesize text to WAV asynchronously."""
        return await anyio.to_thread.run_sync(
            lambda: self.synthesize_sync(text, output_path, **kwargs)
        )

    def close(self) -> None:
        """Release the model and free GPU memory if applicable."""
        if self._model is not None:
            device = self.device
            del self._model
            self._model = None
            if device != "cpu":
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass
            logger.info("Pocket TTS model released")


@dataclass
class TTSDispatcher:
    """Multi-engine TTS dispatcher.

    Routes synthesis requests to the appropriate engine based on use case:
    - Piper: default, fast responses, alerts, agent voice.
    - Pocket: voice cloning, audiobooks, longform content.

    Args:
        piper: PiperTTS instance (primary engine).
        pocket: PocketTTS instance (secondary engine, lazy-loaded).
        default_engine: Default engine for unspecified requests.
    """

    piper: PiperTTS = field(default_factory=PiperTTS)
    pocket: PocketTTS = field(default_factory=PocketTTS)
    default_engine: TTSEngine = TTSEngine.PIPER

    def synthesize_sync(
        self,
        text: str,
        output_path: str | Path,
        *,
        engine: TTSEngine | None = None,
        **kwargs: object,
    ) -> TTSResult:
        """Synthesize text using the specified or default engine.

        Args:
            text: Text to synthesize.
            output_path: Output WAV file path.
            engine: Engine to use (defaults to self.default_engine).
            **kwargs: Engine-specific arguments.

        Returns:
            TTSResult with output file metadata.
        """
        engine = engine or self.default_engine

        if engine == TTSEngine.PIPER:
            return self.piper.synthesize_sync(text, output_path, **kwargs)
        if engine == TTSEngine.POCKET:
            return self.pocket.synthesize_sync(text, output_path, **kwargs)

        msg = f"Unknown TTS engine: {engine}"
        raise ValueError(msg)

    async def synthesize(
        self,
        text: str,
        output_path: str | Path,
        *,
        engine: TTSEngine | None = None,
        **kwargs: object,
    ) -> TTSResult:
        """Synthesize text asynchronously."""
        engine = engine or self.default_engine

        if engine == TTSEngine.PIPER:
            return await self.piper.synthesize(text, output_path, **kwargs)
        if engine == TTSEngine.POCKET:
            return await self.pocket.synthesize(text, output_path, **kwargs)

        msg = f"Unknown TTS engine: {engine}"
        raise ValueError(msg)

    def close(self) -> None:
        """Release all engine resources."""
        self.piper.close()
        self.pocket.close()
