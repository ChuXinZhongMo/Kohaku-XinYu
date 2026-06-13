from __future__ import annotations

import json
import wave
from pathlib import Path
from types import SimpleNamespace

import xinyu_tts_output
from xinyu_tts_output import XinYuTTSOutput


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def _enable_windows_playback(monkeypatch) -> None:
    fake_winsound = SimpleNamespace(
        SND_FILENAME=1,
        SND_NODEFAULT=2,
        SND_ASYNC=4,
        SND_PURGE=8,
        PlaySound=lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(xinyu_tts_output, "winsound", fake_winsound)
    monkeypatch.setattr(xinyu_tts_output.sys, "platform", "win32")


def test_tts_engine_genie_posts_to_genie_server_without_current_api_key(monkeypatch, tmp_path: Path) -> None:
    _enable_windows_playback(monkeypatch)
    monkeypatch.setenv("XINYU_TTS_ENABLED", "1")
    monkeypatch.setenv("XINYU_TTS_ENGINE", "genie")
    monkeypatch.setenv("XINYU_TTS_FORMAT", "wav")
    monkeypatch.setenv("XINYU_GENIE_TTS_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("XINYU_GENIE_TTS_CHARACTER", "xinyu")
    monkeypatch.setenv("XINYU_GENIE_TTS_SPLIT_SENTENCE", "0")
    monkeypatch.delenv("XINYU_TTS_API_KEY", raising=False)
    monkeypatch.delenv("XINYU_TTS_BASE_URL", raising=False)

    requests: list[tuple[str, dict[str, object], dict[str, str]]] = []

    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        requests.append((request.full_url, json.loads(request.data.decode("utf-8")), dict(request.header_items())))
        return _FakeResponse((b"\x00\x01" * 1200))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    speaker = XinYuTTSOutput(tmp_path)
    try:
        assert speaker._startup_disabled_reason() == ""
        audio, engine = speaker._synthesize_audio("你好")
    finally:
        speaker.close()

    assert audio.startswith(b"RIFF")
    assert engine == "genie"
    wav_path = tmp_path / "genie.wav"
    wav_path.write_bytes(audio)
    with wave.open(str(wav_path), "rb") as handle:
        assert handle.getframerate() == 32000
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
    assert requests == [
        (
            "http://127.0.0.1:8000/tts",
            {"character_name": "xinyu", "text": "你好", "split_sentence": False},
            {"Accept": "audio/wav, application/octet-stream", "Content-type": "application/json"},
        )
    ]


def test_tts_engine_current_keeps_existing_audio_speech_path(monkeypatch, tmp_path: Path) -> None:
    _enable_windows_playback(monkeypatch)
    monkeypatch.setenv("XINYU_TTS_ENABLED", "1")
    monkeypatch.setenv("XINYU_TTS_ENGINE", "current")
    monkeypatch.setenv("XINYU_TTS_BASE_URL", "https://tts.example.test/v1")
    monkeypatch.setenv("XINYU_TTS_API_KEY", "tts-key")
    monkeypatch.setenv("XINYU_TTS_MODEL", "tts-1")
    monkeypatch.setenv("XINYU_TTS_VOICE", "alloy")
    monkeypatch.setenv("XINYU_TTS_FORMAT", "wav")
    monkeypatch.setenv("XINYU_TTS_REQUEST_MODE", "audio_speech")

    requests: list[tuple[str, dict[str, object], dict[str, str]]] = []

    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        requests.append((request.full_url, json.loads(request.data.decode("utf-8")), dict(request.header_items())))
        return _FakeResponse(b"RIFFcurrent-wav")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    speaker = XinYuTTSOutput(tmp_path)
    try:
        audio, engine = speaker._synthesize_audio("你好")
    finally:
        speaker.close()

    assert audio == b"RIFFcurrent-wav"
    assert engine == "audio_speech"
    assert requests == [
        (
            "https://tts.example.test/v1/audio/speech",
            {"model": "tts-1", "voice": "alloy", "input": "你好", "response_format": "wav"},
            {"Authorization": "Bearer tts-key", "Content-type": "application/json"},
        )
    ]
