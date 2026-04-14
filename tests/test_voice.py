"""Tests for core.voice — STT and TTS engines."""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.voice.stt import Segment, TranscriptionResult, WhisperSTT
from core.voice.tts import PiperTTS, PocketTTS, TTSDispatcher, TTSEngine, TTSResult


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


class TestWhisperSTT:
    def test_default_config(self):
        stt = WhisperSTT()
        assert stt.model_size == "small"
        assert stt.device == "cpu"
        assert stt.compute_type == "int8"
        assert stt.language is None

    def test_custom_config(self):
        stt = WhisperSTT(model_size="large-v3", device="cuda", language="fr")
        assert stt.model_size == "large-v3"
        assert stt.device == "cuda"
        assert stt.language == "fr"

    def test_transcribe_sync_file_not_found(self):
        stt = WhisperSTT()
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            stt.transcribe_sync("/nonexistent/audio.wav")

    @patch("faster_whisper.WhisperModel", autospec=False)
    def test_transcribe_sync_with_mock(self, mock_model_cls, tmp_path):
        # Create a minimal WAV file
        wav_path = tmp_path / "test.wav"
        with wave.open(str(wav_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00" * 32000)

        # Mock the model
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 1.0
        mock_segment.text = "Hello world"
        mock_segment.avg_logprob = -0.3
        mock_segment.no_speech_prob = 0.01

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.98
        mock_info.duration = 1.0

        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = ([mock_segment], mock_info)
        mock_model_cls.return_value = mock_instance

        stt = WhisperSTT()
        result = stt.transcribe_sync(wav_path)

        assert result.language == "en"
        assert result.text == "Hello world"
        assert len(result.segments) == 1
        assert result.duration == 1.0

    @pytest.mark.anyio
    @patch("faster_whisper.WhisperModel", autospec=False)
    async def test_transcribe_async(self, mock_model_cls, tmp_path):
        wav_path = tmp_path / "test.wav"
        with wave.open(str(wav_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00" * 32000)

        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 0.5
        mock_segment.text = "async test"
        mock_segment.avg_logprob = -0.2
        mock_segment.no_speech_prob = 0.0

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95
        mock_info.duration = 0.5

        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = ([mock_segment], mock_info)
        mock_model_cls.return_value = mock_instance

        stt = WhisperSTT()
        result = await stt.transcribe(wav_path)

        assert result.text == "async test"

    def test_close(self):
        stt = WhisperSTT()
        stt._model = MagicMock()
        stt.close()
        assert stt._model is None


# ── TTS unit tests ──────────────────────────────────────────────────


class TestTTSResult:
    def test_tts_result_creation(self):
        r = TTSResult(
            audio_path=Path("/tmp/out.wav"),
            engine=TTSEngine.PIPER,
            sample_rate=22050,
            size_bytes=1000,
        )
        assert r.engine == TTSEngine.PIPER
        assert r.sample_rate == 22050


class TestPiperTTS:
    def test_default_config(self):
        tts = PiperTTS()
        assert "lessac" in str(tts.model_path)
        assert tts.use_cuda is False

    def test_synthesize_model_not_found(self):
        tts = PiperTTS(model_path="/nonexistent/model.onnx")
        with pytest.raises(FileNotFoundError, match="Piper model not found"):
            tts.synthesize_sync("Hello", "/tmp/out.wav")

    @patch("piper.PiperVoice", autospec=False)
    def test_synthesize_sync_with_mock(self, mock_voice_cls, tmp_path):
        # Create a fake model file
        model_file = tmp_path / "model.onnx"
        model_file.write_bytes(b"fake")

        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        mock_voice_cls.load.return_value = mock_voice

        # Mock synthesize_wav to write actual WAV data
        def fake_synth(text, wav_file, **kwargs):
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x00" * 4410)

        mock_voice.synthesize_wav.side_effect = fake_synth

        tts = PiperTTS(model_path=model_file)
        out_path = tmp_path / "out.wav"
        result = tts.synthesize_sync("Test", out_path)

        assert result.engine == TTSEngine.PIPER
        assert result.sample_rate == 22050
        assert result.audio_path == out_path
        assert result.size_bytes > 0
        mock_voice.synthesize_wav.assert_called_once()

    def test_close(self):
        tts = PiperTTS()
        tts._voice = MagicMock()
        tts.close()
        assert tts._voice is None


class TestPocketTTS:
    def test_default_config(self):
        tts = PocketTTS()
        assert tts.device == "cpu"

    def test_close(self):
        tts = PocketTTS()
        tts._model = MagicMock()
        tts.close()
        assert tts._model is None


class TestTTSDispatcher:
    def test_default_engine(self):
        d = TTSDispatcher()
        assert d.default_engine == TTSEngine.PIPER

    @patch("piper.PiperVoice", autospec=False)
    def test_dispatch_to_piper(self, mock_voice_cls, tmp_path):
        model_file = tmp_path / "model.onnx"
        model_file.write_bytes(b"fake")

        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        mock_voice_cls.load.return_value = mock_voice

        def fake_synth(text, wav_file, **kwargs):
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x00" * 4410)

        mock_voice.synthesize_wav.side_effect = fake_synth

        dispatcher = TTSDispatcher(piper=PiperTTS(model_path=model_file))
        out_path = tmp_path / "dispatch_out.wav"
        result = dispatcher.synthesize_sync("Test dispatch", out_path)

        assert result.engine == TTSEngine.PIPER

    def test_dispatch_unknown_engine(self, tmp_path):
        dispatcher = TTSDispatcher()
        with pytest.raises(ValueError, match="Unknown TTS engine"):
            dispatcher.synthesize_sync(
                "Test", tmp_path / "out.wav", engine="nonexistent"
            )

    def test_close_all(self):
        piper = PiperTTS()
        piper._voice = MagicMock()
        pocket = PocketTTS()
        pocket._model = MagicMock()
        d = TTSDispatcher(piper=piper, pocket=pocket)
        d.close()
        assert piper._voice is None
        assert pocket._model is None
