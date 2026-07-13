from __future__ import annotations

import json
from pathlib import Path

import xinyu_qq_voice_reply as voice


def test_voice_tts_payload_includes_emotion_when_enabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XINYU_TTS_EMOTION", "1")
    # Point voice module root reads via chdir-less monkeypatch of helper
    monkeypatch.setattr(voice, "_tts_emotion_enabled", lambda: True)
    monkeypatch.setattr(voice, "_read_delivery_category_for_voice", lambda: "warm")
    monkeypatch.setattr(voice, "_tts_character", lambda: "xinyu")
    monkeypatch.setattr(voice, "_tts_split_sentence", lambda: False)
    monkeypatch.setattr(voice, "_tts_base_url", lambda: "http://127.0.0.1:9")
    monkeypatch.setattr(voice, "_retry_count", lambda: 0)
    monkeypatch.setattr(voice, "_timeout", lambda: 0.1)

    captured: dict = {}

    class _Resp:
        status = 200

        def read(self) -> bytes:
            # minimal RIFF header so path accepts audio
            return b"RIFF" + b"\x00" * 40

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=0):  # noqa: ANN001
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _Resp()

    monkeypatch.setattr(voice.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(voice, "trim_wav_trailing_silence", lambda audio: audio)

    result = voice.synth_voice_b64_result("你好")
    assert result.ok is True
    assert captured["body"]["emotion"] == "warm"
    assert captured["body"]["text"] == "你好"


def test_voice_tts_payload_omits_emotion_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(voice, "_tts_emotion_enabled", lambda: False)
    monkeypatch.setattr(voice, "_read_delivery_category_for_voice", lambda: "warm")
    monkeypatch.setattr(voice, "_tts_character", lambda: "xinyu")
    monkeypatch.setattr(voice, "_tts_split_sentence", lambda: False)
    monkeypatch.setattr(voice, "_tts_base_url", lambda: "http://127.0.0.1:9")
    monkeypatch.setattr(voice, "_retry_count", lambda: 0)
    monkeypatch.setattr(voice, "_timeout", lambda: 0.1)

    captured: dict = {}

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return b"RIFF" + b"\x00" * 40

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=0):  # noqa: ANN001
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _Resp()

    monkeypatch.setattr(voice.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(voice, "trim_wav_trailing_silence", lambda audio: audio)

    result = voice.synth_voice_b64_result("你好")
    assert result.ok is True
    assert "emotion" not in captured["body"]
