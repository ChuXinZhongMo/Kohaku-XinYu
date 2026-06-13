from __future__ import annotations

import asyncio
import base64
import json
import wave
from pathlib import Path

import xinyu_qq_voice_reply
from xinyu_qq_gateway import GatewayConfig, NativeQQGateway, ReplyTarget


class _VoiceGateway(NativeQQGateway):
    def __init__(self) -> None:
        super().__init__(GatewayConfig())
        self.actions: list[tuple[str, dict[str, object]]] = []
        self.fail_record = False

    async def send_action(self, websocket, action, params):
        self.actions.append((action, params))
        segment_type = params["message"][0]["type"]
        if segment_type == "record" and self.fail_record:
            return {"status": "failed", "retcode": 1, "message": "record denied"}
        return {"status": "ok", "retcode": 0, "data": {"message_id": f"{segment_type}-1"}}


def _private_target() -> ReplyTarget:
    return ReplyTarget(message_kind="private", user_id="42", group_id="")


class _FakeTTSResponse:
    status = 200

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeTTSResponse":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_synth_voice_uses_genie_voice_settings_and_wraps_pcm(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / "xinyu.local.env"
    env_path.write_text(
        "\n".join(
            [
                "XINYU_GENIE_TTS_BASE_URL=http://127.0.0.1:8000",
                "XINYU_GENIE_TTS_CHARACTER=myvoice",
                "XINYU_GENIE_TTS_SPLIT_SENTENCE=1",
                "XINYU_GENIE_TTS_SAMPLE_RATE=32000",
                "XINYU_GENIE_TTS_CHANNELS=1",
                "XINYU_GENIE_TTS_SAMPLE_WIDTH=2",
                "XINYU_TTS_RETRY_COUNT=0",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(xinyu_qq_voice_reply, "_ENV_PATH", env_path)
    monkeypatch.setattr(xinyu_qq_voice_reply, "_env_cache", {})
    monkeypatch.setattr(xinyu_qq_voice_reply, "_env_mtime", -1.0)
    requests: list[tuple[str, dict[str, object]]] = []

    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        requests.append((request.full_url, json.loads(request.data.decode("utf-8"))))
        return _FakeTTSResponse(b"\x00\x01" * 1200)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = xinyu_qq_voice_reply.synth_voice_b64_result("你好。等一下。")

    assert result.ok is True
    assert requests == [
        (
            "http://127.0.0.1:8000/tts",
            {"character_name": "myvoice", "text": "你好。等一下。", "split_sentence": True},
        )
    ]
    assert result.record_file.startswith("base64://")
    audio = base64.b64decode(result.record_file.removeprefix("base64://"))
    wav_path = tmp_path / "qq-voice.wav"
    wav_path.write_bytes(audio)
    with wave.open(str(wav_path), "rb") as handle:
        assert handle.getframerate() == 32000
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2


def test_play_voice_result_locally_uses_existing_wav(monkeypatch, tmp_path: Path) -> None:
    played: list[tuple[str, int]] = []

    class _FakeWinSound:
        SND_FILENAME = 1
        SND_NODEFAULT = 2
        SND_ASYNC = 4

        @staticmethod
        def PlaySound(path: str, flags: int) -> None:
            played.append((path, flags))

    wav_path = tmp_path / "source.wav"
    with wave.open(str(wav_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(32000)
        handle.writeframes(b"\x00\x01" * 320)

    monkeypatch.setattr(xinyu_qq_voice_reply, "winsound", _FakeWinSound)
    monkeypatch.setattr(xinyu_qq_voice_reply.sys, "platform", "win32")
    monkeypatch.setattr(xinyu_qq_voice_reply, "local_playback_enabled", lambda: True)
    monkeypatch.setattr(xinyu_qq_voice_reply, "_playback_dir", lambda: tmp_path / "playback")

    result = xinyu_qq_voice_reply.play_voice_result_locally(
        xinyu_qq_voice_reply.VoiceSynthesisResult(ok=True, wav_bytes=wav_path.read_bytes())
    )

    assert result["played"] is True
    assert played
    retained_path = Path(played[0][0])
    assert retained_path.exists()
    assert retained_path.read_bytes() == wav_path.read_bytes()


def test_send_reply_falls_back_to_text_when_voice_synthesis_fails(monkeypatch) -> None:
    gateway = _VoiceGateway()
    monkeypatch.setattr(xinyu_qq_voice_reply, "voice_reply_enabled", lambda _kind: True)
    monkeypatch.setattr(xinyu_qq_voice_reply, "strict_voice_reply_enabled", lambda _kind: False)
    monkeypatch.setattr(
        xinyu_qq_voice_reply,
        "synth_voice_b64_result",
        lambda _text: xinyu_qq_voice_reply.VoiceSynthesisResult(ok=False, reason="tts_down"),
    )

    result = asyncio.run(gateway.send_reply(None, _private_target(), "hello"))

    assert result is not None
    assert result["status"] == "ok"
    assert result["data"]["message_id"] == "text-1"
    assert result["data"]["delivery_kind"] == "text"
    assert result["xinyu_delivery_kind"] == "text"
    assert result["xinyu_voice_fallback_reason"] == "tts_down"
    assert [params["message"][0]["type"] for _action, params in gateway.actions] == ["text"]


def test_send_reply_suppresses_text_when_private_voice_synthesis_fails_in_strict_mode(monkeypatch) -> None:
    gateway = _VoiceGateway()
    monkeypatch.setattr(xinyu_qq_voice_reply, "voice_reply_enabled", lambda _kind: True)
    monkeypatch.setattr(xinyu_qq_voice_reply, "strict_voice_reply_enabled", lambda _kind: True)
    monkeypatch.setattr(
        xinyu_qq_voice_reply,
        "synth_voice_b64_result",
        lambda _text: xinyu_qq_voice_reply.VoiceSynthesisResult(ok=False, reason="tts_down"),
    )

    result = asyncio.run(gateway.send_reply(None, _private_target(), "hello"))

    assert result is not None
    assert result["status"] == "failed"
    assert result["xinyu_delivery_kind"] == "voice_failed"
    assert result["xinyu_voice_fallback_reason"] == "tts_down"
    assert result["xinyu_voice_strict_drop"] is True
    assert gateway.actions == []


def test_send_reply_falls_back_to_text_when_record_send_fails(monkeypatch) -> None:
    gateway = _VoiceGateway()
    gateway.fail_record = True
    monkeypatch.setattr(xinyu_qq_voice_reply, "voice_reply_enabled", lambda _kind: True)
    monkeypatch.setattr(xinyu_qq_voice_reply, "strict_voice_reply_enabled", lambda _kind: False)
    monkeypatch.setattr(xinyu_qq_voice_reply, "play_voice_result_locally", lambda _result: {"played": False})
    monkeypatch.setattr(
        xinyu_qq_voice_reply,
        "synth_voice_b64_result",
        lambda _text: xinyu_qq_voice_reply.VoiceSynthesisResult(
            ok=True,
            record_file="base64://UklGRg==",
            audio_bytes=4,
        ),
    )

    result = asyncio.run(gateway.send_reply(None, _private_target(), "hello"))

    assert result is not None
    assert result["status"] == "ok"
    assert result["data"]["message_id"] == "text-1"
    assert result["data"]["delivery_kind"] == "text"
    assert result["xinyu_delivery_kind"] == "text"
    assert result["xinyu_voice_fallback_reason"] == "record denied"
    assert [params["message"][0]["type"] for _action, params in gateway.actions] == ["record", "text"]


def test_send_reply_marks_successful_voice_delivery(monkeypatch) -> None:
    gateway = _VoiceGateway()
    monkeypatch.setattr(xinyu_qq_voice_reply, "voice_reply_enabled", lambda _kind: True)
    monkeypatch.setattr(xinyu_qq_voice_reply, "strict_voice_reply_enabled", lambda _kind: True)
    monkeypatch.setattr(xinyu_qq_voice_reply, "play_voice_result_locally", lambda _result: {"played": False})
    monkeypatch.setattr(
        xinyu_qq_voice_reply,
        "synth_voice_b64_result",
        lambda _text: xinyu_qq_voice_reply.VoiceSynthesisResult(
            ok=True,
            record_file="base64://UklGRg==",
            audio_bytes=4,
        ),
    )

    result = asyncio.run(gateway.send_reply(None, _private_target(), "hello"))

    assert result is not None
    assert result["status"] == "ok"
    assert result["data"]["message_id"] == "record-1"
    assert result["data"]["delivery_kind"] == "voice"
    assert result["xinyu_delivery_kind"] == "voice"
    assert [params["message"][0]["type"] for _action, params in gateway.actions] == ["record"]
