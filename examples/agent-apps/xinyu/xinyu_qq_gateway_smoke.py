from __future__ import annotations

import asyncio

from xinyu_qq_gateway import GatewayConfig, NativeQQGateway


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
    assert image_followup_payload["text"] == "\u6211\u521a\u53d1\u4e86\u4e00\u4e2a\u9644\u4ef6\u3002"

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

    non_owner_file = dict(private_event)
    non_owner_file["user_id"] = 43
    non_owner_file["message"] = [{"type": "file", "data": {"name": "nope.pdf", "url": "https://example.com/nope.pdf"}}]
    assert non_owner_gateway.prepare_message(non_owner_file) is None

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
