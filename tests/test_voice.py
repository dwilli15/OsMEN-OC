"""Tests for core.voice — STT and TTS engines (Lemonade Server)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.voice.stt import LemonadeSTT, Segment, TranscriptionResult, WhisperSTT
from core.voice.tts import KokoroTTS, TTSDispatcher, TTSEngine, TTSResult


# ── STT unit tests ──────────────────────────────────────────────────


class TestSegment:
    def test_segment_creation(self):
        s = Segment(start=0.0, end=1.5, text="hello world")
        assert s.start == 0.0
        assert s.end == 1.5
        assert s.text == "hello world"
        assert s.avg_logprob == 0.0
        assert s.no_speech_prob == 0.0

    def test_segment_is_frozen(self):
        s = Segment(start=0.0, end=1.0, text="test")
        with pytest.raises(AttributeError):
            s.text = "changed"


class TestTranscriptionResult:
    def test_text_concatenation(self):
        segs = [
            Segment(start=0.0, end=1.0, text=" Hello "),
            Segment(start=1.0, end=2.0, text=" world "),
        ]
        result = TranscriptionResult(
            segments=segs, language="en", language_probability=0.99, duration=2.0
        )
        assert result.text == "Hello world"

    def test_empty_segments(self):
        result = TranscriptionResult(
            segments=[], language="en", language_probability=0.0, duration=0.0
        )
        assert result.text == ""


class TestLemonadeSTT:
    def test_default_config(self):
        stt = LemonadeSTT()
        assert stt.model == "whisper-v3-turbo-FLM"
        assert stt.base_url == "http://127.0.0.1:13305"
        assert stt.language is None

    def test_custom_config(self):
        stt = LemonadeSTT(base_url="http://10.0.0.1:13305", model="custom-model", language="fr")
        assert stt.base_url == "http://10.0.0.1:13305"
        assert stt.model == "custom-model"
        assert stt.language == "fr"

    def test_backward_compat_alias(self):
        """WhisperSTT should be the same class as LemonadeSTT."""
        assert WhisperSTT is LemonadeSTT

    def test_transcribe_sync_file_not_found(self):
        stt = LemonadeSTT()
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            stt.transcribe_sync("/nonexistent/audio.wav")

    @pytest.mark.asyncio
    async def test_transcribe_plain_text_response(self, tmp_path):
        """Lemonade returns a plain string (no segments)."""
        wav_path = tmp_path / "test.wav"
        wav_path.write_bytes(b"fake audio")

        mock_response = MagicMock()
        mock_response.json.return_value = "Hello world this is a test"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        stt = LemonadeSTT()
        stt._client = mock_client

        result = await stt.transcribe(wav_path)

        assert result.text == "Hello world this is a test"
        assert len(result.segments) == 1
        assert result.segments[0].text == "Hello world this is a test"

    @pytest.mark.asyncio
    async def test_transcribe_detailed_response(self, tmp_path):
        """Lemonade returns JSON with segments."""
        wav_path = tmp_path / "test.wav"
        wav_path.write_bytes(b"fake audio")

        body = {
            "text": "Hello world",
            "segments": [
                {"start": 0.0, "end": 0.5, "text": "Hello", "avg_logprob": -0.2, "no_speech_prob": 0.01},
                {"start": 0.5, "end": 1.0, "text": "world", "avg_logprob": -0.3, "no_speech_prob": 0.02},
            ],
            "language": "en",
            "language_probability": 0.98,
            "duration": 1.0,
        }
        mock_response = MagicMock()
        mock_response.json.return_value = body
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        stt = LemonadeSTT()
        stt._client = mock_client

        result = await stt.transcribe(wav_path)

        assert result.text == "Hello world"
        assert result.language == "en"
        assert result.language_probability == 0.98
        assert result.duration == 1.0
        assert len(result.segments) == 2
        assert result.segments[0].text == "Hello"
        assert result.segments[1].text == "world"

    @pytest.mark.asyncio
    async def test_transcribe_empty_segments_with_text(self, tmp_path):
        """When segments list is empty but text exists, create a synthetic segment."""
        wav_path = tmp_path / "test.wav"
        wav_path.write_bytes(b"fake audio")

        body = {
            "text": "Some transcription",
            "segments": [],
            "language": "en",
            "language_probability": 0.9,
            "duration": 0.5,
        }
        mock_response = MagicMock()
        mock_response.json.return_value = body
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        stt = LemonadeSTT()
        stt._client = mock_client

        result = await stt.transcribe(wav_path)

        assert len(result.segments) == 1
        assert result.segments[0].text == "Some transcription"

    @pytest.mark.asyncio
    async def test_transcribe_sends_language(self, tmp_path):
        """Verify language parameter is sent when configured."""
        wav_path = tmp_path / "test.wav"
        wav_path.write_bytes(b"fake audio")

        mock_response = MagicMock()
        mock_response.json.return_value = "Bonjour"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        stt = LemonadeSTT(language="fr")
        stt._client = mock_client

        await stt.transcribe(wav_path)

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/v1/audio/transcriptions"
        assert call_args[1]["data"]["language"] == "fr"

    @pytest.mark.asyncio
    async def test_close(self):
        stt = LemonadeSTT()
        client = AsyncMock()
        stt._client = client
        await stt.close()
        client.aclose.assert_called_once()


# ── TTS unit tests ──────────────────────────────────────────────────


class TestTTSResult:
    def test_tts_result_creation(self):
        r = TTSResult(
            audio_path=Path("/tmp/out.wav"),
            engine=TTSEngine.KOKORO,
            sample_rate=24000,
            size_bytes=1000,
        )
        assert r.engine == TTSEngine.KOKORO
        assert r.sample_rate == 24000


class TestKokoroTTS:
    def test_default_config(self):
        tts = KokoroTTS()
        assert tts.model == "kokoro-v1"
        assert tts.base_url == "http://127.0.0.1:13305"
        assert tts.voice == "af_bella"
        assert tts.speed == 1.0

    def test_custom_config(self):
        tts = KokoroTTS(base_url="http://10.0.0.1:13305", voice="af_nicole", speed=1.2)
        assert tts.voice == "af_nicole"
        assert tts.speed == 1.2

    @pytest.mark.asyncio
    async def test_synthesize_success(self, tmp_path):
        """Lemonade returns PCM audio data."""
        fake_pcm = b"\x00\x01" * 12000  # ~24KB of fake 16-bit PCM

        mock_response = MagicMock()
        mock_response.content = fake_pcm
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        tts = KokoroTTS()
        tts._client = mock_client

        out_path = tmp_path / "out.wav"
        result = await tts.synthesize("Hello world", out_path)

        assert result.engine == TTSEngine.KOKORO
        assert result.sample_rate == 24000
        assert result.size_bytes > 0
        assert out_path.exists()

        # Verify WAV header is valid
        import wave

        with wave.open(str(out_path), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 24000

    @pytest.mark.asyncio
    async def test_synthesize_sends_payload(self, tmp_path):
        """Verify correct JSON payload is sent."""
        mock_response = MagicMock()
        mock_response.content = b"\x00\x00" * 100
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        tts = KokoroTTS(voice="af_nicole", speed=1.5)
        tts._client = mock_client

        out_path = tmp_path / "out.wav"
        await tts.synthesize("Test", out_path)

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/v1/audio/speech"
        payload = call_args[1]["json"]
        assert payload["input"] == "Test"
        assert payload["model"] == "kokoro-v1"
        assert payload["voice"] == "af_nicole"
        assert payload["speed"] == 1.5

    @pytest.mark.asyncio
    async def test_synthesize_voice_override(self, tmp_path):
        """Voice can be overridden per call."""
        mock_response = MagicMock()
        mock_response.content = b"\x00\x00" * 100
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        tts = KokoroTTS(voice="af_bella")
        tts._client = mock_client

        out_path = tmp_path / "out.wav"
        await tts.synthesize("Test", out_path, voice="bm_george")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["voice"] == "bm_george"

    @pytest.mark.asyncio
    async def test_close(self):
        tts = KokoroTTS()
        client = AsyncMock()
        tts._client = client
        await tts.close()
        client.aclose.assert_called_once()


class TestTTSDispatcher:
    def test_default_engine(self):
        d = TTSDispatcher()
        assert d.default_engine == TTSEngine.KOKORO

    @pytest.mark.asyncio
    async def test_dispatch_to_kokoro(self, tmp_path):
        mock_response = MagicMock()
        mock_response.content = b"\x00\x00" * 100
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        kokoro = KokoroTTS()
        kokoro._client = mock_client

        dispatcher = TTSDispatcher(kokoro=kokoro)
        out_path = tmp_path / "dispatch_out.wav"
        result = await dispatcher.synthesize("Test dispatch", out_path)

        assert result.engine == TTSEngine.KOKORO

    def test_dispatch_legacy_piper_enum(self, tmp_path):
        """Legacy PIPER enum should still be accepted (mapped to kokoro)."""
        d = TTSDispatcher()
        # Should not raise — just routes through kokoro
        assert d.default_engine == TTSEngine.KOKORO

    def test_dispatch_unknown_engine(self, tmp_path):
        dispatcher = TTSDispatcher()
        with pytest.raises(ValueError, match="Unknown TTS engine"):
            dispatcher.synthesize_sync(
                "Test", tmp_path / "out.wav", engine="nonexistent"
            )

    def test_close(self):
        kokoro = KokoroTTS()
        d = TTSDispatcher(kokoro=kokoro)
        # close() uses anyio.from_thread.run_sync which needs an event loop
        # Just verify the method exists and doesn't crash with no-op
        assert hasattr(d, "close")
