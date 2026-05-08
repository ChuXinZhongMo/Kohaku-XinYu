from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path

from xinyu_image_context import _image_data_uri, build_image_context
import xinyu_qq_reply_bubbles
import xinyu_qq_server
from xinyu_qq_gateway import GatewayConfig, NativeQQGateway, PreparedMessage, ReplyTarget


MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@contextmanager
def _smoke_dir(name: str):
    root = Path(__file__).resolve().parent / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    config = GatewayConfig(
        bridge_token="smoke-token",
        whitelist_user_ids=frozenset({"42"}),
        owner_user_ids=frozenset({"42"}),
        group_trigger_prefixes=("心玉", "@心玉", "小心玉"),
    )
    gateway = NativeQQGateway(config)
    assert gateway.config.qq_outbox_enabled is True
    assert gateway.client.qq_outbox_claim_url.endswith("/qq/outbox/claim")
    assert gateway.client.qq_outbox_ack_url.endswith("/qq/outbox/ack")
    assert gateway.client.learning_ingest_url.endswith("/learning/ingest")
    assert gateway.client.sticker_import_url.endswith("/sticker/import")
    assert gateway.client.review_inbox_command_url.endswith("/review/inbox/command")
    assert NativeQQGateway._install_signal_handlers is xinyu_qq_server.install_signal_handlers

    with _smoke_dir(".qq_gateway_trusted_config_smoke_runtime") as tmp:
        config_path = tmp / "gateway.config.json"
        config_path.write_text(
            json.dumps(
                {
                    "bridge_token": "smoke-token",
                    "owner_user_ids": ["42"],
                    "whitelist_user_ids": [],
                    "trusted_user_ids": ["44"],
                    "blocked_user_ids": ["46"],
                    "blocked_group_ids": ["9"],
                    "group_shadow_enabled": True,
                    "group_shadow_allowed_group_ids": ["7"],
                    "group_trigger_prefixes": ["xinyu"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        old_trusted_env = os.environ.get("XINYU_TRUSTED_USER_IDS")
        os.environ["XINYU_TRUSTED_USER_IDS"] = "45"
        try:
            trusted_config = GatewayConfig.from_file(config_path)
        finally:
            if old_trusted_env is None:
                os.environ.pop("XINYU_TRUSTED_USER_IDS", None)
            else:
                os.environ["XINYU_TRUSTED_USER_IDS"] = old_trusted_env
        trusted_gateway = NativeQQGateway(trusted_config, config_path=config_path)
        assert trusted_config.trusted_user_ids == frozenset({"44", "45"})
        assert trusted_gateway._effective_whitelist_user_ids() == {"42", "44", "45"}
        overridden_config = trusted_config.with_overrides(host="127.0.0.1", port=6199)
        assert overridden_config.group_shadow_enabled is True
        assert overridden_config.group_shadow_allowed_group_ids == frozenset({"7"})
        assert overridden_config.blocked_user_ids == frozenset({"46"})
        assert overridden_config.blocked_group_ids == frozenset({"9"})

    class ImageActionGateway(NativeQQGateway):
        def __init__(self):
            super().__init__(config)
            self.actions = []

        async def send_action(self, websocket, action, params):
            self.actions.append((action, params))
            return {"status": "ok", "retcode": 0, "data": {"message_id": 2001}}

    with _smoke_dir(".qq_gateway_image_smoke_runtime") as tmp:
        image_path = tmp / "owner-preview.png"
        image_path.write_bytes(MINIMAL_PNG)
        report_path = tmp / "owner-report.txt"
        report_path.write_text("report ready\n", encoding="utf-8")
        image_gateway = ImageActionGateway()
        onebot_file, image_error = image_gateway._onebot_local_image_file(str(image_path))
        assert image_error == ""
        assert onebot_file.startswith("file:///")
        send_image_response = asyncio.run(
            image_gateway.send_image(
                None,
                ReplyTarget(message_kind="private", user_id="42", group_id=""),
                onebot_file,
                caption="preview ready",
            )
        )
        assert send_image_response["status"] == "ok"
        assert image_gateway.actions == [
            (
                "send_private_msg",
                {
                    "message": [{"type": "image", "data": {"file": onebot_file}}],
                    "auto_escape": False,
                    "user_id": 42,
                },
            )
        ]
        local_file, local_name, file_error = image_gateway._onebot_local_file(str(report_path), file_name="owner/report.txt")
        assert file_error == ""
        assert local_file == str(report_path.resolve())
        assert local_name == "owner_report.txt"
        send_file_response = asyncio.run(
            image_gateway.send_file(
                None,
                ReplyTarget(message_kind="private", user_id="42", group_id=""),
                local_file,
                name=local_name,
            )
        )
        assert send_file_response["status"] == "ok"
        assert image_gateway.actions[-1] == (
            "upload_private_file",
            {
                "file": str(report_path.resolve()),
                "name": "owner_report.txt",
                "user_id": 42,
            },
        )

    class MediaResolveGateway(NativeQQGateway):
        def __init__(self, image_path: Path):
            super().__init__(config)
            self.image_path = image_path
            self.actions = []

        async def _onebot_action_data(self, websocket, action, params):
            self.actions.append((action, params))
            if action == "get_image":
                return {"file": str(self.image_path)}
            return {}

    with _smoke_dir(".qq_gateway_media_resolve_smoke_runtime") as tmp:
        resolved_image = tmp / "resolved-sticker.webp"
        resolved_image.write_bytes(MINIMAL_PNG)
        media_gateway = MediaResolveGateway(resolved_image)
        resolved_payload = asyncio.run(
            media_gateway._resolve_sticker_import_payload(
                None,
                {
                    "file_id": "image-token",
                    "metadata": {"segment_type": "image", "file_id": "image-token"},
                },
            )
        )
        assert resolved_payload["file_path"] == str(resolved_image)
        assert resolved_payload["metadata"]["file_resolution_status"] == "resolved"
        assert resolved_payload["metadata"]["file_resolved_by"] == "get_image"
        assert resolved_payload["metadata"]["file_resolution_attempts"] == ["get_image"]
        assert media_gateway.actions[0] == ("get_image", {"file": "image-token"})

    with _smoke_dir(".qq_gateway_gif_context_smoke_runtime") as tmp:
        import warnings

        from PIL import Image, features

        gif_path = tmp / "animated.gif"
        frame_one = Image.new("RGB", (12, 12), (255, 0, 0))
        frame_two = Image.new("RGB", (12, 12), (0, 0, 255))
        frame_one.save(gif_path, save_all=True, append_images=[frame_two], duration=80, loop=0)
        data_uri, gif_error, gif_notes = _image_data_uri(gif_path, {"file_name": "animated.gif"})
        assert gif_error == ""
        assert data_uri.startswith("data:image/png;base64,")
        assert "gif_frames_sampled:2" in gif_notes
        assert "gif_total_frames:2" in gif_notes
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            webp_anim_supported = features.check("webp_anim")
        if webp_anim_supported:
            webp_path = tmp / "animated.webp"
            frame_one.save(webp_path, save_all=True, append_images=[frame_two], duration=80, loop=0)
            webp_uri, webp_error, webp_notes = _image_data_uri(webp_path, {"file_name": "animated.webp"})
            assert webp_error == ""
            assert webp_uri.startswith("data:image/png;base64,")
            assert "animated_frames_sampled:2" in webp_notes
            assert "animated_total_frames:2" in webp_notes

    private_event = {
        "post_type": "message",
        "message_type": "private",
        "user_id": 42,
        "self_id": 99,
        "message_id": 1001,
        "message": [{"type": "text", "data": {"text": "你好"}}],
        "raw_message": "你好",
        "sender": {"nickname": "owner"},
        "time": 1770000000,
    }
    private_prepared = gateway.prepare_message(private_event)
    assert private_prepared is not None
    assert private_prepared.route == "chat"
    assert private_prepared.target.message_kind == "private"
    assert private_prepared.payload["platform"] == "qq"
    assert private_prepared.payload["adapter"] == "xinyu_native_qq_gateway"
    assert private_prepared.payload["text"] == "你好"
    assert private_prepared.payload["metadata"]["is_owner_user"] is True

    blocked_gateway = NativeQQGateway(
        GatewayConfig(
            bridge_token="smoke-token",
            require_whitelist=False,
            owner_user_ids=frozenset({"42"}),
            blocked_user_ids=frozenset({"42", "43"}),
            blocked_group_ids=frozenset({"7"}),
            group_trigger_prefixes=("心玉", "@心玉", "小心玉"),
            group_shadow_enabled=True,
            group_shadow_allowed_group_ids=frozenset({"7", "8"}),
        )
    )
    blocked_private = dict(private_event)
    blocked_private["user_id"] = 43
    assert blocked_gateway.prepare_message(blocked_private) is None
    assert blocked_gateway._prepare_none_reason(blocked_private) == "sender_blocked"
    assert blocked_gateway.prepare_message(private_event) is not None
    blocked_group_event = {
        "post_type": "message",
        "message_type": "group",
        "group_id": 7,
        "user_id": 44,
        "self_id": 99,
        "message": [{"type": "text", "data": {"text": "心玉 在吗"}}],
        "raw_message": "心玉 在吗",
    }
    assert blocked_gateway.prepare_message(blocked_group_event) is None
    assert blocked_gateway._prepare_none_reason(blocked_group_event) == "group_blocked"
    assert blocked_gateway._maybe_record_group_shadow_event(blocked_group_event)["notes"] == ["group_blocked"]

    sticker_event = dict(private_event)
    sticker_event["message_id"] = 1006
    sticker_event["message"] = [
        {"type": "mface", "data": {"summary": "[摸鱼]", "emoji_id": "sticker-1"}},
    ]
    sticker_event["raw_message"] = "[CQ:mface,summary=[摸鱼],emoji_id=sticker-1]"
    sticker_prepared = gateway.prepare_message(sticker_event)
    assert sticker_prepared is not None
    assert sticker_prepared.route == "chat"
    assert "表情包" in sticker_prepared.payload["text"]
    assert sticker_prepared.payload["metadata"]["qq_rich_message"] is True
    assert sticker_prepared.payload["metadata"]["qq_sticker_count"] == 1
    assert sticker_prepared.payload["metadata"]["qq_message_segments"][0]["kind"] == "sticker"
    assert sticker_prepared.payload["metadata"]["qq_message_segments"][0]["meaning"]

    laugh_sticker_event = dict(private_event)
    laugh_sticker_event["message_id"] = 10061
    laugh_sticker_event["message"] = [
        {"type": "mface", "data": {"summary": "[笑死]", "emoji_id": "sticker-laugh"}}
    ]
    laugh_sticker_prepared = gateway.prepare_message(laugh_sticker_event)
    assert laugh_sticker_prepared is not None
    assert laugh_sticker_prepared.payload["metadata"]["qq_message_segments"][0]["mood"] == "laugh"

    image_sticker_event = dict(private_event)
    image_sticker_event["message_id"] = 1007
    image_sticker_event["message"] = [
        {"type": "image", "data": {"file": "sticker.webp", "summary": "[动画表情]", "subType": "sticker"}},
    ]
    image_sticker_event["raw_message"] = "[CQ:image,file=sticker.webp,summary=[动画表情],subType=sticker]"
    image_sticker_prepared = gateway.prepare_message(image_sticker_event)
    assert image_sticker_prepared is not None
    assert image_sticker_prepared.route == "sticker_import"
    assert image_sticker_prepared.payload["file_id"] == "sticker.webp"
    assert image_sticker_prepared.payload["file_name"] == "sticker.webp"
    assert image_sticker_prepared.payload["metadata"]["source"] == "qq_sticker_message"
    assert image_sticker_prepared.payload["metadata"]["control_plane"] is True
    image_sticker_followup = gateway._build_sticker_followup_chat_payload(
        image_sticker_event,
        target=image_sticker_prepared.target,
        sticker_payload=image_sticker_prepared.payload,
        sticker_response={"material_id": "sticker-material"},
    )
    assert image_sticker_followup is not None
    assert image_sticker_followup["metadata"]["source"] == "qq_sticker_context_reaction"
    assert image_sticker_followup["metadata"]["sticker_followup_before_import"] is True
    assert image_sticker_followup["metadata"]["sticker_import_queued"] is True
    assert image_sticker_followup["metadata"]["qq_rich_message"] is True
    assert image_sticker_followup["metadata"]["qq_sticker_count"] == 1
    assert image_sticker_followup["metadata"]["qq_message_segments"][0]["kind"] == "sticker"

    image_sticker_url_event = dict(private_event)
    image_sticker_url_event["message_id"] = 1008
    image_sticker_url_event["message"] = [
        {
            "type": "image",
            "data": {
                "file": "sticker.webp",
                "url": "https://example.com/sticker.webp",
                "summary": "[animated sticker]",
                "subType": "sticker",
            },
        },
    ]
    image_sticker_url_prepared = gateway.prepare_message(image_sticker_url_event)
    assert image_sticker_url_prepared is not None
    assert image_sticker_url_prepared.route == "sticker_import"
    assert image_sticker_url_prepared.payload["file_url"] == "https://example.com/sticker.webp"

    raw_image_sticker_event = dict(private_event)
    raw_image_sticker_event["message_id"] = 10081
    raw_image_sticker_event["message"] = "[CQ:image,file=sticker.webp,summary=[动画表情],subType=sticker]"
    raw_image_sticker_event["raw_message"] = raw_image_sticker_event["message"]
    raw_image_sticker_prepared = gateway.prepare_message(raw_image_sticker_event)
    assert raw_image_sticker_prepared is not None
    assert raw_image_sticker_prepared.route == "sticker_import"
    assert raw_image_sticker_prepared.payload["file_id"] == "sticker.webp"
    assert raw_image_sticker_prepared.payload["summary"] == "[动画表情]"

    raw_image_event = dict(private_event)
    raw_image_event["message_id"] = 10082
    raw_image_event["message"] = "看这个[CQ:image,file=scan.png,url=https%3A%2F%2Fexample.com%2Fscan.png]"
    raw_image_event["raw_message"] = raw_image_event["message"]
    raw_image_prepared = gateway.prepare_message(raw_image_event)
    assert raw_image_prepared is not None
    assert raw_image_prepared.route == "learning_ingest"
    assert raw_image_prepared.payload["file_url"] == "https://example.com/scan.png"
    assert raw_image_prepared.payload["reason"] == "看这个"

    punctuated_owner_text = dict(private_event)
    punctuated_owner_text["message_id"] = 10083
    punctuated_owner_text["message"] = [{"type": "text", "data": {"text": "!这句别吞"}}]
    punctuated_owner_text["raw_message"] = "!这句别吞"
    punctuated_prepared = gateway.prepare_message(punctuated_owner_text)
    assert punctuated_prepared is not None
    assert punctuated_prepared.route == "chat"
    assert punctuated_prepared.payload["text"] == "!这句别吞"

    class OrderedStickerClient:
        def __init__(self):
            self.calls = []

        async def chat(self, payload):
            self.calls.append(("chat", payload))
            return {"accepted": True, "reply": "chat reply"}

        async def sticker_import(self, payload):
            self.calls.append(("sticker_import", payload))
            return {
                "accepted": True,
                "imported": True,
                "mood": "happy",
                "mood_label": "开心",
                "confidence": "medium",
                "destination": "开心/sticker.webp",
                "items": [
                    {
                        "mood": "happy",
                        "confidence": "medium",
                        "meaning": "开心、轻松",
                        "clip_mood": "happy",
                        "clip_confidence": 0.72,
                    }
                ],
                "notes": ["sticker_import"],
            }

        async def message_ack(self, payload):
            self.calls.append(("message_ack", payload))
            return {"accepted": True}

    class OrderedStickerGateway(NativeQQGateway):
        def __init__(self):
            super().__init__(config)
            self.client = OrderedStickerClient()
            self.replies = []

        async def send_reply(self, websocket, target, text):
            self.replies.append(text)
            return {"status": "ok", "retcode": 0, "data": {"message_id": 3001}}

        def _trace_qq_rich_context(self, event, prepared, *, stage):
            return None

        def _trace_qq_inbound(self, event, *, stage, arrival_seq=0, prepared=None, session_queue_key="", queue_depth=None, drop_reason="", error=""):
            return None

        def _trace_sticker_import(self, event, *, target, payload, stage, response=None, elapsed_ms=None, error=""):
            return None

        def _write_recent_sticker_state(self, key, state):
            return None

        async def _ack_sent_visible_reply(self, prepared, *, reply, core_response, action_response):
            return None

    async def _dispatch_order_smoke():
        ordered_gateway = OrderedStickerGateway()
        prepared = ordered_gateway.prepare_message(image_sticker_url_event)
        assert prepared is not None
        await ordered_gateway._dispatch_prepared_message(None, prepared, event=image_sticker_url_event)
        await asyncio.sleep(0.05)
        call_names = [name for name, _payload in ordered_gateway.client.calls]
        assert call_names[:2] == ["sticker_import", "chat"]
        assert ordered_gateway.replies == ["chat reply"]
        chat_payload = ordered_gateway.client.calls[1][1]
        assert chat_payload["metadata"]["sticker_import_completed"] is True
        assert chat_payload["metadata"]["sticker_import_queued"] is False
        assert chat_payload["metadata"]["sticker_mood"] == "happy"
        assert chat_payload["metadata"]["qq_image_context_available"] is True
        assert chat_payload["metadata"]["qq_message_segments"][0]["mood"] == "happy"
        assert "开心" in chat_payload["text"]
        assert "轻松" in chat_payload["text"]

    asyncio.run(_dispatch_order_smoke())

    async def _recent_sticker_question_smoke():
        recent_gateway = OrderedStickerGateway()
        sticker_prepared = recent_gateway.prepare_message(image_sticker_url_event)
        assert sticker_prepared is not None
        recent_gateway._remember_recent_sticker_import(
            target=sticker_prepared.target,
            event=image_sticker_url_event,
            payload=sticker_prepared.payload,
            status="error",
            error="core bridge HTTP 502",
        )
        question_event = dict(private_event)
        question_event["message_id"] = 10084
        question_event["message"] = [{"type": "text", "data": {"text": "我刚发的是什么"}}]
        question_event["raw_message"] = "我刚发的是什么"
        question_prepared = recent_gateway.prepare_message(question_event)
        assert question_prepared is not None
        enriched = await recent_gateway._maybe_enrich_recent_sticker_question(
            None,
            question_event,
            question_prepared,
        )
        assert recent_gateway.client.calls[0][0] == "sticker_import"
        enriched_metadata = enriched.payload["metadata"]
        assert enriched_metadata["recent_sticker_question"] is True
        assert enriched_metadata["sticker_import_completed"] is True
        assert enriched_metadata["sticker_mood"] == "happy"
        assert enriched_metadata["sticker_mood_label"] == "开心"
        assert enriched_metadata["qq_image_context_available"] is True

    asyncio.run(_recent_sticker_question_smoke())

    class ReplyBubbleClient:
        def __init__(self, reply, extra=None):
            self.reply = reply
            self.extra = extra if isinstance(extra, dict) else {}
            self.calls = []

        async def chat(self, payload):
            self.calls.append(payload)
            response = {"accepted": True, "reply": self.reply, "route": "chat", "session_id": payload.get("session_id", "")}
            response.update(self.extra)
            return response

    class ReplyBubbleGateway(NativeQQGateway):
        def __init__(self, reply, *, target=None, source="onebot_message_event", response_extra=None):
            super().__init__(
                GatewayConfig(
                    bridge_token="",
                    whitelist_user_ids=frozenset({"42"}),
                    owner_user_ids=frozenset({"42"}),
                    reply_bubble_min_chars=60,
                    reply_bubble_soft_max_chars=60,
                    reply_bubble_delay_seconds=0.0,
                    owner_private_coalesce_seconds=0.0,
                )
            )
            self.client = ReplyBubbleClient(reply, extra=response_extra)
            self.target = target or ReplyTarget(message_kind="private", user_id="42", group_id="")
            self.source = source
            self.replies = []

        def prepared(self):
            return PreparedMessage(
                target=self.target,
                payload={
                    "text": "owner sent several fragments",
                    "message_id": "reply-bubble-smoke",
                    "session_id": "qq:private:42",
                    "metadata": {
                        "source": self.source,
                        "message_type": self.target.message_kind,
                    },
                },
                route="chat",
            )

        async def send_reply(self, websocket, target, text):
            self.replies.append(text)
            return {"status": "ok", "retcode": 0, "data": {"message_id": 4000 + len(self.replies)}}

        def _trace_qq_inbound(self, event, *, stage, arrival_seq=0, prepared=None, session_queue_key="", queue_depth=None, drop_reason="", error=""):
            return None

    async def _reply_bubble_smoke():
        long_reply = (
            "I read the whole run before answering. "
            "The issue is rhythm, not just one bad sentence. "
            "I will answer the batch once and split only when a reply is long."
        )
        bubble_gateway = ReplyBubbleGateway(long_reply)
        await bubble_gateway._dispatch_prepared_message(None, bubble_gateway.prepared())
        assert bubble_gateway.replies == [
            "I read the whole run before answering.",
            "The issue is rhythm, not just one bad sentence.",
            "I will answer the batch once and split only when a reply is long.",
        ]

        short_gateway = ReplyBubbleGateway("Short enough.")
        await short_gateway._dispatch_prepared_message(None, short_gateway.prepared())
        assert short_gateway.replies == ["Short enough."]

        technical_reply = "Result:\n- xinyu_qq_gateway.py changed\n- tests passed\n- exit code 0"
        technical_gateway = ReplyBubbleGateway(technical_reply)
        await technical_gateway._dispatch_prepared_message(None, technical_gateway.prepared())
        assert technical_gateway.replies == [technical_reply]

        group_gateway = ReplyBubbleGateway(
            long_reply,
            target=ReplyTarget(message_kind="group", user_id="42", group_id="7"),
        )
        await group_gateway._dispatch_prepared_message(None, group_gateway.prepared())
        assert group_gateway.replies == [
            "I read the whole run before answering.",
            "The issue is rhythm, not just one bad sentence.",
            "I will answer the batch once and split only when a reply is long.",
        ]

        chinese_reply = "这次问题不是模型内容本身，而是出口把所有东西挤成一段了。所以我把长回复拆成更像聊天的几口气。代码和日志还是保持原样，不会为了节奏乱切。"
        codex_chat_gateway = ReplyBubbleGateway(chinese_reply, source="codex_completion")
        await codex_chat_gateway._dispatch_prepared_message(None, codex_chat_gateway.prepared())
        assert len(codex_chat_gateway.replies) > 1
        assert "".join(codex_chat_gateway.replies) == chinese_reply

        outbox_gateway = ReplyBubbleGateway(chinese_reply)
        outbox_bubbles = outbox_gateway._outbox_visible_reply_bubbles(
            ReplyTarget(message_kind="private", user_id="42", group_id=""),
            chinese_reply,
            {"source": "codex_completion", "metadata": {}},
        )
        assert len(outbox_bubbles) > 1
        assert "".join(outbox_bubbles) == chinese_reply

        technical_outbox = "Result: xinyu_qq_gateway.py changed. tests passed. exit code 0"
        assert outbox_gateway._outbox_visible_reply_bubbles(
            ReplyTarget(message_kind="private", user_id="42", group_id=""),
            technical_outbox,
            {"source": "codex_completion", "metadata": {}},
        ) == [technical_outbox]

        forced_units = [str(value) for value in range(1, 11)]
        forced_gateway = ReplyBubbleGateway(
            " ".join(forced_units),
            response_extra={"reply_bubble_force_units": forced_units},
        )
        await forced_gateway._dispatch_prepared_message(None, forced_gateway.prepared())
        assert forced_gateway.replies == forced_units

    asyncio.run(_reply_bubble_smoke())
    assert NativeQQGateway._looks_like_structured_visible_reply is xinyu_qq_reply_bubbles.looks_like_structured_visible_reply

    class OrderedInboundGateway(NativeQQGateway):
        def __init__(self):
            super().__init__(
                GatewayConfig(
                    bridge_token="smoke-token",
                    whitelist_user_ids=frozenset({"42"}),
                    owner_user_ids=frozenset({"42"}),
                    owner_private_coalesce_seconds=0.0,
                )
            )
            self.dispatched = []

        def _trace_qq_inbound(self, event, *, stage, arrival_seq=0, prepared=None, session_queue_key="", queue_depth=None, drop_reason="", error=""):
            return None

        def _trace_qq_rich_context(self, event, prepared, *, stage):
            return None

        async def _dispatch_prepared_message(self, websocket, prepared, *, event=None):
            if prepared.payload["text"] == "first":
                await asyncio.sleep(0.05)
            self._annotate_dispatch_reception(prepared)
            metadata = prepared.payload["metadata"]
            self.dispatched.append(
                (
                    prepared.payload["text"],
                    metadata.get("qq_arrival_seq"),
                    metadata.get("qq_prepared_seq"),
                    metadata.get("qq_dispatch_seq"),
                )
            )

    async def _inbound_queue_order_smoke():
        inbound_gateway = OrderedInboundGateway()
        first_event = dict(private_event)
        first_event["message_id"] = 10091
        first_event["message"] = [{"type": "text", "data": {"text": "first"}}]
        second_event = dict(private_event)
        second_event["message_id"] = 10092
        second_event["message"] = [{"type": "text", "data": {"text": "second"}}]
        await inbound_gateway._enqueue_onebot_event(None, first_event)
        await inbound_gateway._enqueue_onebot_event(None, second_event)
        deadline = asyncio.get_running_loop().time() + 1.0
        while len(inbound_gateway.dispatched) < 2 and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.01)
        for task in list(inbound_gateway._event_tasks):
            task.cancel()
        if inbound_gateway._event_tasks:
            await asyncio.gather(*inbound_gateway._event_tasks, return_exceptions=True)
        assert [item[0] for item in inbound_gateway.dispatched] == ["first", "second"]
        assert [item[1] for item in inbound_gateway.dispatched] == [1, 2]
        assert [item[2] for item in inbound_gateway.dispatched] == [1, 2]
        assert [item[3] for item in inbound_gateway.dispatched] == [1, 2]

    asyncio.run(_inbound_queue_order_smoke())

    self_event = dict(private_event)
    self_event["user_id"] = 99
    self_event["sender"] = {"user_id": 99, "nickname": "xinyu"}
    assert gateway.prepare_message(self_event) is None

    self_sender_event = dict(private_event)
    self_sender_event["sender"] = {"user_id": 99, "nickname": "xinyu"}
    self_sender_event["message"] = [{"type": "image", "data": {"file": "self-sent.png", "url": "https://example.com/self-sent.png"}}]
    assert gateway.prepare_message(self_sender_event) is None

    review_event = dict(private_event)
    review_event["message"] = [{"type": "text", "data": {"text": "!ok all"}}]
    review_event["raw_message"] = "!ok all"
    review_prepared = gateway.prepare_message(review_event)
    assert review_prepared is not None
    assert review_prepared.route == "review_admin"
    assert review_prepared.payload["command"] == "ok"
    assert review_prepared.payload["indices"] == "all"
    assert review_prepared.payload["metadata"]["control_plane"] is True

    fullwidth_review_event = dict(private_event)
    fullwidth_review_event["message"] = [{"type": "text", "data": {"text": "！ok all"}}]
    fullwidth_review_event["raw_message"] = "！ok all"
    fullwidth_review_prepared = gateway.prepare_message(fullwidth_review_event)
    assert fullwidth_review_prepared is not None
    assert fullwidth_review_prepared.route == "review_admin"
    assert fullwidth_review_prepared.payload["command"] == "ok"
    assert fullwidth_review_prepared.payload["indices"] == "all"

    review_mod_event = dict(private_event)
    review_mod_event["message"] = [{"type": "text", "data": {"text": "!mod 2 better pressure"}}]
    review_mod_prepared = gateway.prepare_message(review_mod_event)
    assert review_mod_prepared is not None
    assert review_mod_prepared.route == "review_admin"
    assert review_mod_prepared.payload["command"] == "mod"
    assert review_mod_prepared.payload["indices"] == ["2"]
    assert review_mod_prepared.payload["mod_text"] == "better pressure"

    typo_event = dict(private_event)
    typo_event["message"] = [{"type": "text", "data": {"text": "!okk"}}]
    typo_event["raw_message"] = "!okk"
    assert gateway.prepare_message(typo_event) is None

    fullwidth_typo_event = dict(private_event)
    fullwidth_typo_event["message"] = [{"type": "text", "data": {"text": "！okk"}}]
    fullwidth_typo_event["raw_message"] = "！okk"
    assert gateway.prepare_message(fullwidth_typo_event) is None

    fragment_event = dict(private_event)
    fragment_event["message_id"] = 1002
    fragment_event["message"] = [{"type": "text", "data": {"text": "比如"}}]
    fragment_prepared = gateway.prepare_message(fragment_event)
    follow_fragment_event = dict(private_event)
    follow_fragment_event["message_id"] = 1003
    follow_fragment_event["message"] = [{"type": "text", "data": {"text": "这样"}}]
    follow_fragment_prepared = gateway.prepare_message(follow_fragment_event)
    assert fragment_prepared is not None and follow_fragment_prepared is not None
    coalesced = gateway._build_coalesced_prepared_message([fragment_prepared, follow_fragment_prepared])
    assert coalesced is not None
    assert coalesced.payload["text"] == "比如\n这样"
    assert coalesced.payload["metadata"]["qq_coalesced_owner_messages"] is True
    assert coalesced.payload["metadata"]["qq_coalesced_message_count"] == 2
    many_fragments = []
    for index in range(gateway.config.owner_private_coalesce_max_fragments + 2):
        event = dict(private_event)
        event["message_id"] = 1100 + index
        event["message"] = [{"type": "text", "data": {"text": f"frag-{index}"}}]
        prepared = gateway.prepare_message(event)
        assert prepared is not None
        many_fragments.append(prepared)
    many_coalesced = gateway._build_coalesced_prepared_message(many_fragments)
    assert many_coalesced is not None
    assert many_coalesced.payload["text"].splitlines()[0] == "frag-0"
    assert many_coalesced.payload["metadata"]["qq_coalesced_message_count"] == gateway.config.owner_private_coalesce_max_fragments + 2

    file_event = dict(private_event)
    file_event["message"] = [
        {"type": "text", "data": {"text": "read this"}},
        {"type": "file", "data": {"name": "paper.pdf", "url": "https://example.com/paper.pdf"}},
    ]
    file_event["raw_message"] = "[CQ:file,name=paper.pdf]"
    file_prepared = gateway.prepare_message(file_event)
    assert file_prepared is not None
    assert file_prepared.route == "learning_ingest"
    assert file_prepared.payload["file_url"] == "https://example.com/paper.pdf"
    assert file_prepared.payload["file_name"] == "paper.pdf"
    assert file_prepared.payload["stage"] is True
    assert file_prepared.payload["curated"] is True
    assert file_prepared.payload["metadata"]["source"] == "qq_file_message"
    followup_payload = gateway._build_attachment_followup_chat_payload(
        file_event,
        target=file_prepared.target,
        learning_payload=file_prepared.payload,
        learning_response={
            "extracted_text": True,
            "learning_item_id": "learn-paper",
            "material_id": "material-paper",
            "extracted_text_path": "learning/owner_supplied/paper/extracted_text.md",
        },
    )
    assert followup_payload is not None
    assert followup_payload["text"] == "read this"
    assert followup_payload["metadata"]["source"] == "qq_attachment_followup_after_learning_ingest"
    assert followup_payload["metadata"]["attachment_followup_after_ingest"] is True

    image_event = dict(private_event)
    image_event["message"] = [
        {"type": "image", "data": {"file": "C:\\XinYu-Local-Scope\\Inbox\\scan.png"}},
    ]
    image_event["raw_message"] = "[CQ:image,file=scan.png]"
    image_prepared = gateway.prepare_message(image_event)
    assert image_prepared is not None
    assert image_prepared.route == "learning_ingest"
    assert image_prepared.payload["file_path"].endswith("scan.png")
    image_followup_payload = gateway._build_attachment_followup_chat_payload(
        image_event,
        target=image_prepared.target,
        learning_payload=image_prepared.payload,
        learning_response={
            "extracted_text": True,
            "learning_item_id": "learn-scan",
            "material_id": "material-scan",
            "extracted_text_path": "learning/owner_supplied/scan/extracted_text.md",
        },
    )
    assert image_followup_payload is not None
    assert image_followup_payload["text"].startswith("\u6211\u53d1\u4e86\u56fe\u7247:")
    assert image_followup_payload["metadata"]["qq_rich_message"] is True
    assert image_followup_payload["metadata"]["qq_image_count"] == 1

    with _smoke_dir(".qq_gateway_image_context_smoke_runtime") as tmp:
        old_vision = os.environ.get("XINYU_IMAGE_VISION_ENABLED")
        os.environ["XINYU_IMAGE_VISION_ENABLED"] = "0"
        try:
            (tmp / "learning/owner_supplied/item").mkdir(parents=True, exist_ok=True)
            image_file = tmp / "learning/owner_supplied/item/scan.png"
            image_file.write_bytes(MINIMAL_PNG)
            extracted = tmp / "learning/owner_supplied/item/extracted_text.md"
            extracted.write_text("截图里写着：权限配置失败。", encoding="utf-8")
            context = build_image_context(
                tmp,
                learning_payload=image_prepared.payload,
                learning_response={
                    "extracted_text": True,
                    "extracted_text_path": "learning/owner_supplied/item/extracted_text.md",
                    "stored_paths": ["learning/owner_supplied/item/scan.png"],
                },
                owner_text="看这张截图",
            )
        finally:
            if old_vision is None:
                os.environ.pop("XINYU_IMAGE_VISION_ENABLED", None)
            else:
                os.environ["XINYU_IMAGE_VISION_ENABLED"] = old_vision
        assert context["available"] is True
        assert "权限配置失败" in context["ocr_text"]
        image_context_followup = gateway._build_attachment_followup_chat_payload(
            image_event,
            target=image_prepared.target,
            learning_payload=image_prepared.payload,
            learning_response={
                "extracted_text": False,
                "learning_item_id": "learn-scan",
                "material_id": "material-scan",
            },
            image_context=context,
        )
        assert image_context_followup is not None
        assert image_context_followup["metadata"]["qq_image_context_available"] is True
        empty_image_context_followup = gateway._build_attachment_followup_chat_payload(
            image_event,
            target=image_prepared.target,
            learning_payload=image_prepared.payload,
            learning_response={
                "extracted_text": False,
                "learning_item_id": "learn-empty-scan",
                "material_id": "material-empty-scan",
            },
            image_context={"available": False, "kind": "image", "notes": ["vision_disabled", "ocr_text_empty"]},
        )
        assert empty_image_context_followup is not None
        assert empty_image_context_followup["metadata"]["qq_rich_message"] is True
        assert empty_image_context_followup["metadata"]["qq_image_count"] == 1
        assert empty_image_context_followup["metadata"]["qq_image_context_available"] is False
        assert "vision_disabled" in empty_image_context_followup["metadata"]["qq_image_context_notes"]

    file_id_event = dict(private_event)
    file_id_event["message"] = [
        {"type": "file", "data": {"name": "nips.pdf", "file_id": "private-file-token"}}
    ]
    file_id_prepared = gateway.prepare_message(file_id_event)
    assert file_id_prepared is not None
    assert file_id_prepared.route == "learning_ingest"
    assert file_id_prepared.payload["file_id"] == "private-file-token"

    raw_cq_file_event = dict(private_event)
    raw_cq_file_event["message"] = "[CQ:file,file_id=abc123,name=NIPS-2017.pdf]"
    raw_cq_file_event["raw_message"] = "[CQ:file,file_id=abc123,name=NIPS-2017.pdf]"
    raw_cq_prepared = gateway.prepare_message(raw_cq_file_event)
    assert raw_cq_prepared is not None
    assert raw_cq_prepared.route == "learning_ingest"
    assert raw_cq_prepared.payload["file_id"] == "abc123"
    assert raw_cq_prepared.payload["file_name"] == "NIPS-2017.pdf"

    class ReplyFileGateway(NativeQQGateway):
        def __init__(self, reply_data):
            super().__init__(config)
            self.reply_data = reply_data
            self.actions = []

        async def _onebot_action_data(self, websocket, action, params):
            self.actions.append((action, params))
            return self.reply_data

    reply_file_gateway = ReplyFileGateway(
        {
            "message_id": 1002,
            "message": "[CQ:file,file=NIPS-2017-attention-is-all-you-need-Paper.pdf,file_id=reply-file-token,file_size=569417]",
            "raw_message": "[CQ:file,file=NIPS-2017-attention-is-all-you-need-Paper.pdf,file_id=reply-file-token,file_size=569417]",
        }
    )
    reply_file_event = dict(private_event)
    reply_file_event["message_id"] = 1003
    reply_file_event["message"] = [
        {"type": "reply", "data": {"id": "1002"}},
        {"type": "text", "data": {"text": "读一下这个吧"}},
    ]
    reply_file_event["raw_message"] = "[CQ:reply,id=1002]读一下这个吧"
    reply_file_prepared = reply_file_gateway.prepare_message(reply_file_event)
    assert reply_file_prepared is not None
    assert reply_file_prepared.route == "chat"
    reply_file_upgraded = asyncio.run(
        reply_file_gateway._upgrade_reply_file_learning(None, reply_file_event, reply_file_prepared)
    )
    assert reply_file_upgraded is not None
    assert reply_file_upgraded.route == "learning_ingest"
    assert reply_file_upgraded.payload["file_id"] == "reply-file-token"
    assert reply_file_upgraded.payload["file_name"] == "NIPS-2017-attention-is-all-you-need-Paper.pdf"
    assert reply_file_upgraded.payload["metadata"]["source"] == "qq_reply_file_message"
    assert reply_file_gateway.actions == [("get_msg", {"message_id": 1002})]

    reply_image_gateway = ReplyFileGateway(
        {
            "message_id": 1004,
            "message": [
                {
                    "type": "image",
                    "data": {
                        "file": "shot.jpg",
                        "url": "https://example.com/shot.jpg",
                    },
                }
            ],
            "raw_message": "[CQ:image,file=shot.jpg,url=https://example.com/shot.jpg]",
        }
    )
    reply_image_event = dict(private_event)
    reply_image_event["message_id"] = 1005
    reply_image_event["message"] = [
        {"type": "reply", "data": {"id": "1004"}},
        {"type": "text", "data": {"text": "我已经发截图了"}},
    ]
    reply_image_prepared = reply_image_gateway.prepare_message(reply_image_event)
    assert reply_image_prepared is not None
    assert reply_image_prepared.route == "chat"
    reply_image_upgraded = asyncio.run(
        reply_image_gateway._upgrade_reply_file_learning(None, reply_image_event, reply_image_prepared)
    )
    assert reply_image_upgraded is not None
    assert reply_image_upgraded.route == "learning_ingest"
    assert reply_image_upgraded.payload["file_url"] == "https://example.com/shot.jpg"
    assert reply_image_upgraded.payload["file_name"] == "shot.jpg"

    quote_gateway = ReplyFileGateway(
        {
            "message_id": 1008,
            "user_id": 42,
            "sender": {"nickname": "owner"},
            "message": [{"type": "text", "data": {"text": "这句是被引用的内容"}}],
            "raw_message": "这句是被引用的内容",
        }
    )
    quote_event = dict(private_event)
    quote_event["message_id"] = 1009
    quote_event["message"] = [
        {"type": "reply", "data": {"id": "1008"}},
        {"type": "text", "data": {"text": "我说的是这条"}},
    ]
    quote_event["raw_message"] = "[CQ:reply,id=1008]我说的是这条"
    quote_prepared = quote_gateway.prepare_message(quote_event)
    assert quote_prepared is not None
    assert quote_prepared.route == "chat"
    quote_enriched = asyncio.run(quote_gateway._enrich_reply_context(None, quote_event, quote_prepared))
    assert quote_enriched is not None
    assert quote_enriched.payload["metadata"]["qq_reply_message_id"] == "1008"
    assert quote_enriched.payload["metadata"]["qq_reply_context_available"] is True
    assert quote_enriched.payload["metadata"]["qq_reply_context"]["text"] == "这句是被引用的内容"
    assert quote_enriched.payload["quoted_message"]["message_id"] == "1008"

    with _smoke_dir(".qq_gateway_owner_trust_command_smoke_runtime") as tmp:
        trust_config_path = tmp / "gateway.config.json"
        trust_config_path.write_text(
            json.dumps(
                {
                    "bridge_token": "smoke-token",
                    "owner_user_ids": ["42"],
                    "whitelist_user_ids": [],
                    "trusted_user_ids": [],
                    "group_trigger_prefixes": ["xinyu"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        class TrustCommandGateway(NativeQQGateway):
            def __init__(self):
                super().__init__(GatewayConfig.from_file(trust_config_path), config_path=trust_config_path)
                self.actions = []

            async def _onebot_action_data(self, websocket, action, params):
                self.actions.append((action, params))
                return {
                    "message_id": 2008,
                    "user_id": 43,
                    "sender": {"nickname": "sis"},
                    "message": [{"type": "text", "data": {"text": "search public info"}}],
                    "raw_message": "search public info",
                }

        trust_gateway = TrustCommandGateway()
        trust_event = dict(private_event)
        trust_event["message_id"] = 2009
        trust_event["message"] = [
            {"type": "reply", "data": {"id": "2008"}},
            {"type": "text", "data": {"text": "\u7ed9\u4e2a\u6743\u9650"}},
        ]
        trust_event["raw_message"] = "[CQ:reply,id=2008]\u7ed9\u4e2a\u6743\u9650"
        trust_prepared = trust_gateway.prepare_message(trust_event)
        assert trust_prepared is not None
        trust_prepared = asyncio.run(trust_gateway._enrich_reply_context(None, trust_event, trust_prepared))
        trust_reply = trust_gateway._handle_owner_trust_command(trust_prepared)
        assert trust_reply
        assert "43" in trust_gateway.config.trusted_user_ids
        persisted_trust = json.loads(trust_config_path.read_text(encoding="utf-8"))
        assert persisted_trust["trusted_user_ids"] == ["43"]

    with _smoke_dir(".qq_gateway_group_trust_command_smoke_runtime") as tmp:
        group_trust_config_path = tmp / "gateway.config.json"
        group_trust_config_path.write_text(
            json.dumps(
                {
                    "bridge_token": "smoke-token",
                    "owner_user_ids": ["42"],
                    "whitelist_user_ids": [],
                    "trusted_user_ids": [],
                    "group_trigger_prefixes": ["xinyu"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        class GroupTrustCommandGateway(NativeQQGateway):
            def __init__(self):
                super().__init__(GatewayConfig.from_file(group_trust_config_path), config_path=group_trust_config_path)
                self.actions = []

            async def _onebot_action_data(self, websocket, action, params):
                self.actions.append((action, params))
                return {
                    "message_id": 2010,
                    "user_id": 45,
                    "sender": {"nickname": "sister", "user_id": 45},
                    "message": [{"type": "text", "data": {"text": "search public info"}}],
                    "raw_message": "search public info",
                }

        group_trust_gateway = GroupTrustCommandGateway()
        group_trust_event = {
            "post_type": "message",
            "message_type": "group",
            "group_id": 7,
            "user_id": 42,
            "self_id": 99,
            "message_id": 2011,
            "message": [
                {"type": "reply", "data": {"id": "2010"}},
                {"type": "text", "data": {"text": "\u7ed9\u4e2a\u6743\u9650"}},
            ],
            "raw_message": "[CQ:reply,id=2010]\u7ed9\u4e2a\u6743\u9650",
        }
        group_trust_prepared = group_trust_gateway.prepare_message(group_trust_event)
        assert group_trust_prepared is not None
        assert group_trust_prepared.route == "chat"
        assert group_trust_prepared.payload["metadata"]["source"] == "qq_gateway_trust_admin_command"
        group_trust_prepared = asyncio.run(
            group_trust_gateway._enrich_reply_context(None, group_trust_event, group_trust_prepared)
        )
        group_trust_reply = group_trust_gateway._handle_owner_trust_command(group_trust_prepared)
        assert group_trust_reply
        assert "45" in group_trust_gateway.config.trusted_user_ids
        persisted_group_trust = json.loads(group_trust_config_path.read_text(encoding="utf-8"))
        assert persisted_group_trust["trusted_user_ids"] == ["45"]

    class ForwardGateway(NativeQQGateway):
        def __init__(self):
            super().__init__(config)
            self.actions = []

        async def send_action(self, websocket, action, params):
            self.actions.append((action, params))
            if action == "get_msg":
                return {
                    "status": "ok",
                    "retcode": 0,
                    "data": {
                        "message_id": 1011,
                        "user_id": 42,
                        "sender": {"nickname": "owner"},
                        "message": [{"type": "forward", "data": {"id": "fw-quoted"}}],
                        "raw_message": "[CQ:forward,id=fw-quoted]",
                    },
                }
            if action == "get_forward_msg":
                forward_id = str(params.get("message_id") or params.get("id"))
                return {
                    "status": "ok",
                    "retcode": 0,
                    "data": {
                        "messages": [
                            {
                                "message_id": f"{forward_id}-1",
                                "sender": {"nickname": "Alice", "user_id": "10001"},
                                "message": [{"type": "text", "data": {"text": "第一句转发内容"}}],
                            },
                            {
                                "message_id": f"{forward_id}-2",
                                "sender": {"nickname": "Bob", "user_id": "10002"},
                                "message": [{"type": "text", "data": {"text": "第二句转发内容"}}],
                            },
                        ]
                    },
                }
            return {"status": "failed", "retcode": 1, "data": {}}

    forward_gateway = ForwardGateway()
    forward_event = dict(private_event)
    forward_event["message_id"] = 1010
    forward_event["message"] = [{"type": "forward", "data": {"id": "fw-direct"}}]
    forward_event["raw_message"] = "[CQ:forward,id=fw-direct]"
    forward_prepared = forward_gateway.prepare_message(forward_event)
    assert forward_prepared is not None
    assert forward_prepared.route == "chat"
    assert forward_prepared.payload["text"] == "我转发了一段聊天记录。"
    assert forward_prepared.payload["metadata"]["qq_forward_message_ids"] == ["fw-direct"]
    forward_enriched = asyncio.run(forward_gateway._enrich_forward_context(None, forward_event, forward_prepared))
    assert forward_enriched is not None
    assert forward_enriched.payload["metadata"]["qq_forward_context_available"] is True
    assert forward_enriched.payload["metadata"]["qq_forward_context"]["messages"][0]["text"] == "第一句转发内容"
    assert forward_gateway.actions == [("get_forward_msg", {"message_id": "fw-direct"})]

    quoted_forward_gateway = ForwardGateway()
    quoted_forward_event = dict(private_event)
    quoted_forward_event["message_id"] = 1012
    quoted_forward_event["message"] = [
        {"type": "reply", "data": {"id": "1011"}},
        {"type": "text", "data": {"text": "看这段转发"}},
    ]
    quoted_forward_event["raw_message"] = "[CQ:reply,id=1011]看这段转发"
    quoted_forward_prepared = quoted_forward_gateway.prepare_message(quoted_forward_event)
    assert quoted_forward_prepared is not None
    quoted_forward_prepared = asyncio.run(
        quoted_forward_gateway._enrich_reply_context(None, quoted_forward_event, quoted_forward_prepared)
    )
    quoted_forward_enriched = asyncio.run(
        quoted_forward_gateway._enrich_forward_context(None, quoted_forward_event, quoted_forward_prepared)
    )
    assert quoted_forward_enriched is not None
    assert quoted_forward_enriched.payload["metadata"]["qq_reply_context"]["forward_message_ids"] == ["fw-quoted"]
    assert quoted_forward_enriched.payload["metadata"]["qq_forward_message_ids"] == ["fw-quoted"]
    assert quoted_forward_enriched.payload["forwarded_messages"]["messages"][1]["text"] == "第二句转发内容"

    pkg_event = dict(private_event)
    pkg_event["message"] = [{"type": "text", "data": {"text": "\u5e2e\u5979\u88c5 pymupdf"}}]
    pkg_event["raw_message"] = "\u5e2e\u5979\u88c5 pymupdf"
    pkg_prepared = gateway.prepare_message(pkg_event)
    assert pkg_prepared is not None
    assert pkg_prepared.route == "package_install"
    assert pkg_prepared.payload["packages"] == "pymupdf"
    assert pkg_prepared.payload["session_id"] == "qq:private:42"

    contextual_pkg_event = dict(private_event)
    contextual_pkg_event["message"] = [{"type": "text", "data": {"text": "\u5e2e\u5979\u88c5"}}]
    contextual_pkg_prepared = gateway.prepare_message(contextual_pkg_event)
    assert contextual_pkg_prepared is not None
    assert contextual_pkg_prepared.route == "package_install"
    assert contextual_pkg_prepared.payload["packages"] == ""

    codex_event = dict(private_event)
    codex_event["message"] = [{"type": "text", "data": {"text": "/codex 核查当前架构"}}]
    codex_event["raw_message"] = "/codex 核查当前架构"
    codex_prepared = gateway.prepare_message(codex_event)
    assert codex_prepared is not None
    assert codex_prepared.route == "codex_execute"
    assert codex_prepared.target.message_kind == "private"
    assert codex_prepared.payload["source"] == "qq_gateway_codex_execute_message"
    assert codex_prepared.payload["background"] is True
    assert codex_prepared.payload["auto_study"] is True
    assert codex_prepared.payload["timeout_seconds"] == 3600
    assert codex_prepared.payload["visible_window"] is True
    assert codex_prepared.payload["window_title"] == "Xinyu codex"
    assert codex_prepared.payload["network_access"] is True
    assert codex_prepared.payload["raw_owner_task"] == "核查当前架构"
    assert "Codex 辅助慢脑" in codex_prepared.payload["text"]
    assert codex_prepared.payload["metadata"]["direct_cli_execution"] is False

    natural_codex_event = dict(private_event)
    natural_codex_text = "\u4f60\u8bd5\u8bd5\u7528codex\u641c\u7d22 consciousness is useful philosophy"
    natural_codex_event["message"] = [{"type": "text", "data": {"text": natural_codex_text}}]
    natural_codex_event["raw_message"] = natural_codex_text
    natural_codex_prepared = gateway.prepare_message(natural_codex_event)
    assert natural_codex_prepared is not None
    assert natural_codex_prepared.route == "chat"
    assert natural_codex_prepared.payload["text"] == natural_codex_text

    meta_codex_event = dict(private_event)
    meta_codex_text = "\u5fc3\u7389\u4e3a\u4ec0\u4e48\u4e0d\u80fd\u8c03\u7528codex\u8fdb\u884c\u641c\u7d22"
    meta_codex_event["message"] = [{"type": "text", "data": {"text": meta_codex_text}}]
    meta_codex_event["raw_message"] = meta_codex_text
    meta_codex_prepared = gateway.prepare_message(meta_codex_event)
    assert meta_codex_prepared is not None
    assert meta_codex_prepared.route == "chat"

    empty_codex_event = dict(private_event)
    empty_codex_event["message"] = [{"type": "text", "data": {"text": "/codex"}}]
    empty_codex_event["raw_message"] = "/codex"
    empty_codex_prepared = gateway.prepare_message(empty_codex_event)
    assert empty_codex_prepared is not None
    assert empty_codex_prepared.route == "local_reply"
    assert "/codex 后面" in empty_codex_prepared.local_reply

    non_owner_gateway = NativeQQGateway(
        GatewayConfig(
            bridge_token="smoke-token",
            whitelist_user_ids=frozenset({"43"}),
            owner_user_ids=frozenset({"42"}),
            group_trigger_prefixes=("心玉", "@心玉", "小心玉"),
        )
    )
    non_owner_event = dict(private_event)
    non_owner_event["user_id"] = 43
    non_owner_event["message"] = [{"type": "text", "data": {"text": "/codex 不该执行"}}]
    non_owner_event["raw_message"] = "/codex 不该执行"
    assert non_owner_gateway.prepare_message(non_owner_event) is None

    trusted_gateway = NativeQQGateway(
        GatewayConfig(
            bridge_token="smoke-token",
            whitelist_user_ids=frozenset(),
            owner_user_ids=frozenset({"42"}),
            trusted_user_ids=frozenset({"43"}),
            group_trigger_prefixes=("xinyu",),
        )
    )
    trusted_chat = dict(private_event)
    trusted_chat["user_id"] = 43
    trusted_chat["message"] = [{"type": "text", "data": {"text": "search public sources"}}]
    trusted_chat["raw_message"] = "search public sources"
    trusted_prepared = trusted_gateway.prepare_message(trusted_chat)
    assert trusted_prepared is not None
    assert trusted_prepared.route == "chat"
    assert trusted_prepared.payload["metadata"]["is_trusted_user"] is True
    assert trusted_prepared.payload["metadata"]["user_trust_level"] == "trusted"

    trusted_codex = dict(trusted_chat)
    trusted_codex["message"] = [{"type": "text", "data": {"text": "/codex search public sources"}}]
    trusted_codex["raw_message"] = "/codex search public sources"
    assert trusted_gateway.prepare_message(trusted_codex) is None

    non_owner_file = dict(private_event)
    non_owner_file["user_id"] = 43
    non_owner_file["message"] = [{"type": "file", "data": {"name": "nope.pdf", "url": "https://example.com/nope.pdf"}}]
    assert non_owner_gateway.prepare_message(non_owner_file) is None

    non_owner_sticker = dict(private_event)
    non_owner_sticker["user_id"] = 43
    non_owner_sticker["message"] = [
        {"type": "image", "data": {"file": "nope.webp", "url": "https://example.com/nope.webp", "subType": "sticker"}}
    ]
    assert non_owner_gateway.prepare_message(non_owner_sticker) is None

    ignored_group = {
        "post_type": "message",
        "message_type": "group",
        "group_id": 7,
        "user_id": 42,
        "self_id": 99,
        "message": [{"type": "text", "data": {"text": "普通群聊"}}],
        "raw_message": "普通群聊",
    }
    assert gateway.prepare_message(ignored_group) is None
    assert gateway._prepare_none_reason(ignored_group) == "group_trigger_required"

    with _smoke_dir(".qq_gateway_group_shadow_smoke_runtime") as tmp:
        shadow_gateway = NativeQQGateway(
            GatewayConfig(
                bridge_token="smoke-token",
                whitelist_user_ids=frozenset(),
                owner_user_ids=frozenset({"42"}),
                group_trigger_prefixes=("心玉", "@心玉", "小心玉"),
                group_shadow_enabled=True,
                group_shadow_allowed_group_ids=frozenset({"7"}),
            )
        )
        shadow_gateway.xinyu_dir = tmp
        shadow_event = dict(ignored_group)
        shadow_event["user_id"] = 43
        shadow_event["message_id"] = 12001
        shadow_event["message"] = [{"type": "text", "data": {"text": "普通群聊里的一句真实闲聊"}}]
        shadow_event["raw_message"] = "普通群聊里的一句真实闲聊"
        shadow_result = shadow_gateway._maybe_record_group_shadow_event(shadow_event)
        assert shadow_result["recorded"] is True
        assert shadow_gateway.prepare_message(shadow_event) is None
        shadow_trace = tmp / "runtime/group_shadow/group_shadow_observations.jsonl"
        assert shadow_trace.exists()
        shadow_row = json.loads(shadow_trace.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert shadow_row["reply_policy"] == "no_reply_shadow_only"
        assert shadow_row["stable_memory_write"] == "blocked"
        assert shadow_row["owner_relationship_write"] == "blocked"
        assert shadow_row["triggered"] is False
        assert shadow_row["prepare_reason"] == "sender_not_whitelisted"
        assert shadow_row["text_excerpt"] == "普通群聊里的一句真实闲聊"
        shadow_state = tmp / "memory/context/group_shadow_state.md"
        assert shadow_state.exists()
        assert "reply_policy: no_reply_shadow_only" in shadow_state.read_text(encoding="utf-8")

        blocked_shadow = dict(shadow_event)
        blocked_shadow["group_id"] = 8
        blocked_result = shadow_gateway._maybe_record_group_shadow_event(blocked_shadow)
        assert blocked_result["recorded"] is False
        assert "group_shadow_group_not_allowed" in blocked_result["notes"]

    group_sticker = dict(ignored_group)
    group_sticker["message"] = [
        {"type": "image", "data": {"file": "group.webp", "url": "https://example.com/group.webp", "subType": "sticker"}}
    ]
    assert gateway.prepare_message(group_sticker) is None
    assert gateway._prepare_none_reason(group_sticker) == "sticker_import_private_owner_only"

    prefixed_group = dict(ignored_group)
    prefixed_group["message"] = [{"type": "text", "data": {"text": "心玉 看一下"}}]
    prefixed_group["raw_message"] = "心玉 看一下"
    group_prepared = gateway.prepare_message(prefixed_group)
    assert group_prepared is not None
    assert group_prepared.route == "chat"
    assert group_prepared.target.message_kind == "group"
    assert group_prepared.payload["text"] == "看一下"
    assert group_prepared.payload["session_id"] == "qq:group:7:42"

    group_codex = dict(ignored_group)
    group_codex["message"] = [{"type": "text", "data": {"text": "心玉 /codex 不该执行"}}]
    group_codex["raw_message"] = "心玉 /codex 不该执行"
    assert gateway.prepare_message(group_codex) is None

    at_group = dict(ignored_group)
    at_group["message"] = [
        {"type": "at", "data": {"qq": "99"}},
        {"type": "text", "data": {"text": "在吗"}},
    ]
    at_group["raw_message"] = "[CQ:at,qq=99] 在吗"
    at_prepared = gateway.prepare_message(at_group)
    assert at_prepared is not None
    assert at_prepared.payload["text"] == "在吗"

    print("xinyu_qq_gateway_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
