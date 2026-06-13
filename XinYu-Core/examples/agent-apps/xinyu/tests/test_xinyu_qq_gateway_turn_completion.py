from __future__ import annotations

import asyncio
from pathlib import Path

import xinyu_qq_gateway
from xinyu_qq_core_client import BridgeError
import xinyu_qq_voice_transcript
from xinyu_qq_gateway import GatewayConfig, NativeQQGateway, PreparedMessage, ReplyTarget
from xinyu_qq_models import RecentStickerImportState


class _ReplyClient:
    def __init__(self) -> None:
        self.drops = []

    async def chat(self, payload):
        return {
            "accepted": True,
            "reply": "old reply",
            "route": "chat",
            "session_id": payload.get("session_id", ""),
            "turn_id": "turn-1",
            "reply_hash": "sha256:old",
            "archive_message_ids": [1, 2],
            "archive_assistant_message_id": "2",
        }

    async def message_drop(self, payload):
        self.drops.append(dict(payload))
        return {"accepted": True, "tail_removed": True, "archive_deleted": True}


class _StickerImportClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    async def sticker_import(self, payload):
        self.calls += 1
        if self.fail:
            raise BridgeError("core bridge HTTP 500: clip failed")
        return {"accepted": True, "imported": True, "mood": "playful"}


class _StaleGateway(NativeQQGateway):
    def __init__(self) -> None:
        super().__init__(
            GatewayConfig(
                bridge_token="smoke-token",
                whitelist_user_ids=frozenset({"42"}),
                owner_user_ids=frozenset({"42"}),
                owner_private_coalesce_seconds=0.0,
            )
        )
        self.client = _ReplyClient()
        self.replies: list[str] = []
        self.traces: list[dict[str, str]] = []

    async def send_reply(self, websocket, target, text):
        self.replies.append(text)
        return {"status": "ok"}

    def _trace_qq_inbound(
        self,
        event,
        *,
        stage,
        arrival_seq=0,
        prepared=None,
        session_queue_key="",
        queue_depth=None,
        drop_reason="",
        error="",
        delivery_kind="",
        adapter_message_id="",
        adapter_error="",
        voice_fallback_reason="",
    ):
        self.traces.append({"stage": stage, "drop_reason": drop_reason})

    def _trace_qq_rich_context(self, event, prepared, *, stage):
        return None


class _StickerBackgroundGateway(_StaleGateway):
    def __init__(self, *, fail: bool = False) -> None:
        super().__init__()
        self.client = _StickerImportClient(fail=fail)
        self.scheduled_stickers: list[dict] = []
        self.sticker_traces: list[dict] = []
        self.sticker_states: list[dict] = []

    def _schedule_sticker_import_background(self, websocket, event, *, target, sticker_payload):
        self.scheduled_stickers.append(dict(sticker_payload))

    def _trace_sticker_import(
        self,
        event,
        *,
        target,
        payload,
        stage,
        response=None,
        elapsed_ms=None,
        error="",
    ):
        self.sticker_traces.append({"stage": stage, "error": error})

    def _remember_recent_sticker_import(
        self,
        *,
        target,
        event,
        payload,
        status,
        response=None,
        error="",
    ):
        self.sticker_states.append({"status": status, "error": error})
        return RecentStickerImportState(
            target=target,
            event=dict(event),
            payload=dict(payload),
            response=dict(response or {}),
            status=status,
            error=error,
        )


class _VoiceTranscriptionGateway(_StaleGateway):
    def __init__(self, root: Path, audio_path: Path | None = None) -> None:
        super().__init__()
        self.xinyu_dir = root
        self.audio_path = audio_path
        self.actions: list[tuple[str, dict]] = []

    async def send_action(self, websocket, action, params):
        self.actions.append((action, dict(params)))
        if action != "get_record" or self.audio_path is None:
            return {"status": "failed", "retcode": 404, "data": None}
        return {
            "status": "ok",
            "retcode": 0,
            "data": {
                "file": str(self.audio_path),
                "url": str(self.audio_path),
                "file_name": self.audio_path.name,
            },
        }


class _ImageContextGateway(_StaleGateway):
    def __init__(self, root: Path, image_path: Path) -> None:
        super().__init__()
        self.xinyu_dir = root
        self.image_path = image_path
        self.actions: list[tuple[str, dict]] = []

    async def _onebot_action_data(self, websocket, action, params):
        self.actions.append((action, dict(params)))
        if action == "get_image":
            return {"file": str(self.image_path)}
        return {}


def _private_text_event(text: str, *, message_id: str = "m-text") -> dict:
    return {
        "post_type": "message",
        "message_type": "private",
        "user_id": "42",
        "message_id": message_id,
        "message": [{"type": "text", "data": {"text": text}}],
    }


def _private_sticker_event(*, message_id: str = "m-sticker") -> dict:
    return {
        "post_type": "message",
        "message_type": "private",
        "user_id": "42",
        "message_id": message_id,
        "message": [
            {
                "type": "mface",
                "data": {"file": "sticker.webp", "summary": "sticker"},
            }
        ],
    }


def _private_voice_event(*, message_id: str = "m-voice") -> dict:
    return {
        "post_type": "message",
        "message_type": "private",
        "user_id": "42",
        "message_id": message_id,
        "message": [
            {
                "type": "record",
                "data": {"file": "private-voice.silk", "duration": "3"},
            }
        ],
    }


def _private_image_event(*, message_id: str = "m-image") -> dict:
    return {
        "post_type": "message",
        "message_type": "private",
        "user_id": "42",
        "message_id": message_id,
        "message": [
            {
                "type": "image",
                "data": {"file": "scan.png"},
            }
        ],
        "raw_message": "[CQ:image,file=scan.png]",
    }


def test_owner_private_image_routes_to_chat_not_learning_ingest() -> None:
    prepared = _StaleGateway().prepare_message(_private_image_event())

    assert prepared is not None
    assert prepared.route == "chat"
    assert prepared.payload["metadata"]["qq_image_count"] == 1
    assert prepared.payload["metadata"]["qq_rich_message"] is True


def test_chat_image_context_enrichment_resolves_current_turn_image(tmp_path: Path, monkeypatch) -> None:
    async def _run() -> None:
        image_path = tmp_path / "scan.png"
        image_path.write_bytes(b"fake png bytes")
        gateway = _ImageContextGateway(tmp_path, image_path)
        event = _private_image_event()
        prepared = PreparedMessage(
            target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
            payload={
                "text": "图片:scan.png",
                "message_id": "m-image",
                "session_id": "qq:private:42",
                "metadata": {
                    "source": "onebot_message_event",
                    "is_owner_user": True,
                    "qq_image_count": 1,
                    "qq_rich_message": True,
                },
            },
            route="chat",
        )

        def _fake_context(root, *, image_path, image_payload, owner_text, image_only=False):
            assert root == tmp_path
            assert image_path == gateway.image_path
            assert image_payload["file_path"] == str(gateway.image_path)
            assert owner_text == "图片:scan.png"
            return {
                "available": True,
                "kind": "image",
                "ocr_text": "截图里写着：通道已经通了。",
                "vision_summary": "",
                "notes": ["image_context_requested", "ocr_text_available"],
            }

        monkeypatch.setattr(xinyu_qq_gateway, "build_image_context_from_path", _fake_context)

        enriched = await gateway._maybe_enrich_current_image_context(None, event, prepared)

        assert enriched is not None
        metadata = enriched.payload["metadata"]
        assert metadata["qq_image_context_available"] is True
        assert metadata["qq_image_context"]["ocr_text"] == "截图里写着：通道已经通了。"
        assert metadata["qq_image_context_route"] == "direct_current_turn"
        assert metadata["file_resolution_status"] == "resolved"
        assert metadata["file_resolved_by"] == "get_image"
        assert gateway.actions[0] == ("get_image", {"file": "scan.png"})

    asyncio.run(_run())


def test_owner_private_voice_payload_is_a_bounded_rich_context_event() -> None:
    gateway = _StaleGateway()
    event = _private_voice_event(message_id="m-voice")

    rich = gateway._extract_rich_message_context(event)
    prepared = gateway.prepare_message(event)

    assert rich["voice_count"] == 1
    assert rich["record_count"] == 1
    assert rich["audio_count"] == 0
    assert rich["fallback_text"]
    assert prepared is not None
    assert prepared.route == "local_reply"
    assert "转写" in prepared.local_reply
    assert prepared.payload == {}
    assert "private-voice.silk" not in str(rich)
    assert "private-voice.silk" not in prepared.local_reply
    return
    assert rich["fallback_text"] == "我发了一条语音。"
    assert prepared is not None
    assert prepared.route == "chat"
    assert prepared.payload["text"] == "我发了一条语音。"
    metadata = prepared.payload["metadata"]
    assert metadata["qq_voice_count"] == 1
    assert metadata["qq_record_count"] == 1
    assert metadata["qq_audio_count"] == 0
    assert "private-voice.silk" not in str(rich)
    assert "private-voice.silk" not in str(metadata)


def test_owner_private_voice_transcript_upgrades_local_reply_to_chat(tmp_path: Path, monkeypatch) -> None:
    async def _run() -> None:
        audio_path = tmp_path / "voice.mp3"
        audio_path.write_bytes(b"fake mp3 bytes")
        gateway = _VoiceTranscriptionGateway(tmp_path, audio_path)
        event = _private_voice_event(message_id="m-voice-transcribed")
        prepared = gateway.prepare_message(event)

        def _fake_transcribe(root, path):
            assert root == tmp_path
            assert path == audio_path
            return {
                "status": "transcribed",
                "engine": "fake_stt",
                "model": "fake-model",
                "language": "zh",
                "transcript": "我们继续测试语音转文字。",
                "confidence": 0.91,
            }

        monkeypatch.setattr(xinyu_qq_voice_transcript, "transcribe_audio_file", _fake_transcribe)

        upgraded = await gateway._maybe_transcribe_owner_private_voice(None, event, prepared)

        assert prepared is not None
        assert prepared.route == "local_reply"
        assert upgraded is not None
        assert upgraded.route == "chat"
        assert upgraded.local_reply == ""
        assert upgraded.payload["text"] == "我们继续测试语音转文字。"
        metadata = upgraded.payload["metadata"]
        assert metadata["source"] == "qq_voice_transcript_message"
        assert metadata["qq_voice_transcript_available"] is True
        assert metadata["qq_voice_transcript_text_len"] == len("我们继续测试语音转文字。")
        assert metadata["qq_voice_transcript_engine"] == "fake_stt"
        assert metadata["qq_voice_count"] == 1
        assert "private-voice.silk" not in str(metadata)
        assert str(audio_path) not in str(metadata)
        assert gateway.actions
        assert gateway.actions[0][0] == "get_record"
        assert gateway.actions[0][1]["out_format"] == "mp3"

        trace = (tmp_path / "runtime/voice_input_trace.jsonl").read_text(encoding="utf-8")
        assert "我们继续测试语音转文字。" in trace
        assert str(audio_path) not in trace

    asyncio.run(_run())


def test_owner_private_voice_transcript_failure_keeps_local_reply_boundary(tmp_path: Path, monkeypatch) -> None:
    async def _run() -> None:
        audio_path = tmp_path / "voice.mp3"
        audio_path.write_bytes(b"fake mp3 bytes")
        gateway = _VoiceTranscriptionGateway(tmp_path, audio_path)
        event = _private_voice_event(message_id="m-voice-failed")
        prepared = gateway.prepare_message(event)

        def _fake_transcribe(root, path):
            return {
                "status": "transcription_unavailable",
                "engine": "fake_stt",
                "error": "missing_api_key",
            }

        monkeypatch.setattr(xinyu_qq_voice_transcript, "transcribe_audio_file", _fake_transcribe)

        upgraded = await gateway._maybe_transcribe_owner_private_voice(None, event, prepared)

        assert upgraded is prepared
        assert upgraded is not None
        assert upgraded.route == "local_reply"
        assert "转写" in upgraded.local_reply
        trace = (tmp_path / "runtime/voice_input_trace.jsonl").read_text(encoding="utf-8")
        assert "transcription_unavailable" in trace
        assert "missing_api_key" in trace
        assert str(audio_path) not in trace

    asyncio.run(_run())


def test_owner_private_reply_is_dropped_when_newer_input_arrived() -> None:
    async def _run() -> None:
        gateway = _StaleGateway()
        event = {"post_type": "message", "message_type": "private", "user_id": "42", "message_id": "m1"}
        prepared = PreparedMessage(
            target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
            payload={
                "text": "first",
                "message_id": "m1",
                "session_id": "qq:private:42",
                "metadata": {"source": "onebot_message_event", "is_owner_user": True},
            },
            route="chat",
        )
        prepared = gateway._annotate_prepared_reception(
            prepared,
            event,
            arrival_seq=1,
            session_queue_key="private:42",
        )
        gateway._mark_latest_session_arrival("private:42", 2)

        await gateway._dispatch_prepared_message(None, prepared, event=event)

        assert gateway.replies == []
        assert any(item["stage"] == "stale_reply_dropped" for item in gateway.traces)
        stale = [item for item in gateway.traces if item["stage"] == "stale_reply_dropped"][-1]
        assert stale["drop_reason"].startswith("newer_input_before_visible_send:1->2")
        assert gateway.client.drops
        assert gateway.client.drops[0]["archive_assistant_message_id"] == "2"
        assert gateway.client.drops[0]["reply"] == "old reply"

    asyncio.run(_run())


def test_sticker_only_arrival_does_not_make_pending_text_reply_stale() -> None:
    async def _run() -> None:
        gateway = _StaleGateway()
        event = _private_text_event("first", message_id="m1")
        prepared = PreparedMessage(
            target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
            payload={
                "text": "first",
                "message_id": "m1",
                "session_id": "qq:private:42",
                "metadata": {"source": "onebot_message_event", "is_owner_user": True},
            },
            route="chat",
        )
        prepared = gateway._annotate_prepared_reception(
            prepared,
            event,
            arrival_seq=1,
            session_queue_key="private:42",
        )

        sticker_event = _private_sticker_event(message_id="m2")
        assert gateway._event_supersedes_pending_visible_reply(_private_text_event("newer")) is True
        assert gateway._event_supersedes_pending_visible_reply(sticker_event) is False
        if gateway._event_supersedes_pending_visible_reply(sticker_event):
            gateway._mark_latest_session_arrival("private:42", 2)

        await gateway._dispatch_prepared_message(None, prepared, event=event)

        assert gateway.replies == ["old reply"]
        assert not gateway.client.drops
        assert not any(item["stage"] == "stale_reply_dropped" for item in gateway.traces)

    asyncio.run(_run())


def test_sticker_import_route_queues_background_without_blocking_visible_reply_path() -> None:
    async def _run() -> None:
        gateway = _StickerBackgroundGateway()
        event = _private_sticker_event(message_id="m-sticker")
        prepared = PreparedMessage(
            target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
            payload={
                "message_id": "m-sticker",
                "file_path": "D:/XinYu/runtime/tmp/sticker.webp",
                "metadata": {
                    "source": "qq_sticker_message",
                    "message_id": "m-sticker",
                    "qq_arrival_seq": 2,
                    "qq_session_queue_hash": "queue-1",
                },
            },
            route="sticker_import",
        )

        await gateway._dispatch_prepared_message(None, prepared, event=event)

        assert gateway.client.calls == 0
        assert gateway.scheduled_stickers
        assert gateway.sticker_states[0]["status"] == "pending"
        assert any(item["stage"] == "background_queued" for item in gateway.sticker_traces)
        assert gateway.replies == []
        assert any(item["stage"] == "dispatch_done" for item in gateway.traces)

    asyncio.run(_run())


def test_turn_completion_ready_prevents_terminal_wait_more_drop() -> None:
    gateway = _StaleGateway()
    prepared = PreparedMessage(
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        payload={
            "text": "我想了一下然后",
            "message_id": "m-fragment",
            "session_id": "qq:private:42",
            "metadata": {
                "source": "onebot_message_event",
                "qq_turn_completion_reason": "continuation_marker",
                "qq_turn_completion_should_generate": True,
            },
        },
        route="chat",
    )

    decision = gateway._owner_private_segmented_intent_decision(prepared)

    assert decision["action"] == "reply_now"
    assert decision["should_reply"] is True
    assert "turn_completion_ready_overrides_fragment_wait" in decision["notes"]


def test_fragment_continuation_without_turn_completion_ready_still_waits() -> None:
    gateway = _StaleGateway()
    prepared = PreparedMessage(
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        payload={
            "text": "我想了一下然后",
            "message_id": "m-fragment",
            "session_id": "qq:private:42",
            "metadata": {"source": "onebot_message_event"},
        },
        route="chat",
    )

    decision = gateway._owner_private_segmented_intent_decision(prepared)

    assert decision["action"] == "wait_more"
    assert decision["should_reply"] is False
    assert "fragment_continuation_marker" in decision["notes"]


def test_turn_completion_ready_prevents_terminal_silent_drop() -> None:
    gateway = _StaleGateway()
    prepared = PreparedMessage(
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        payload={
            "text": "下班了",
            "message_id": "m-status",
            "session_id": "qq:private:42",
            "metadata": {
                "source": "onebot_message_event",
                "qq_turn_completion_reason": "short_fragment",
                "qq_turn_completion_should_generate": True,
            },
        },
        route="chat",
    )

    decision = gateway._owner_private_segmented_intent_decision(prepared)

    assert decision["action"] == "reply_now"
    assert decision["should_reply"] is True
    assert "turn_completion_ready_overrides_silent" in decision["notes"]


def test_turn_completion_ready_prevents_conversational_closure_silent_drop() -> None:
    gateway = _StaleGateway()
    prepared = PreparedMessage(
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        payload={
            "text": "\u55ef\uff0c\u90a3\u5c31\u540c\u6b65\u8d70\u3002",
            "message_id": "m-closure",
            "session_id": "qq:private:42",
            "metadata": {
                "source": "onebot_message_event",
                "qq_turn_completion_reason": "short_fragment",
                "qq_turn_completion_should_generate": True,
            },
        },
        route="chat",
    )

    decision = gateway._owner_private_segmented_intent_decision(prepared)

    assert decision["action"] == "reply_now"
    assert decision["should_reply"] is True
    assert "turn_completion_ready_overrides_silent" in decision["notes"]


def test_low_info_without_turn_completion_ready_still_silences() -> None:
    gateway = _StaleGateway()
    prepared = PreparedMessage(
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        payload={
            "text": "好的",
            "message_id": "m-low-info",
            "session_id": "qq:private:42",
            "metadata": {"source": "onebot_message_event"},
        },
        route="chat",
    )

    decision = gateway._owner_private_segmented_intent_decision(prepared)

    assert decision["action"] == "silent"
    assert decision["should_reply"] is False
    assert "low_info_owner_turn" in decision["notes"]


def test_background_sticker_import_failure_records_perceptual_error_without_raise() -> None:
    async def _run() -> None:
        gateway = _StickerBackgroundGateway(fail=True)
        event = _private_sticker_event(message_id="m-sticker")
        target = ReplyTarget(message_kind="private", user_id="42", group_id="")
        payload = {
            "message_id": "m-sticker",
            "file_path": "D:/XinYu/runtime/tmp/sticker.webp",
            "metadata": {"source": "qq_sticker_message", "message_id": "m-sticker"},
        }

        await gateway._run_sticker_import_background(None, event, target=target, sticker_payload=payload)

        assert gateway.client.calls == 1
        assert [item["status"] for item in gateway.sticker_states] == ["pending", "error"]
        assert any(item["stage"] == "error" for item in gateway.sticker_traces)

    asyncio.run(_run())
