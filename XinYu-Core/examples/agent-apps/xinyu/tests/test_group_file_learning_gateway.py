from __future__ import annotations

import asyncio

from xinyu_qq_attachment_resolver import resolve_learning_ingest_payload
from xinyu_qq_config import GatewayConfig
from xinyu_qq_gateway import NativeQQGateway


def test_config_loads_group_file_learning_allowlist(tmp_path) -> None:
    config_path = tmp_path / "gateway.json"
    config_path.write_text(
        '{"qq_file_learning_allowed_group_ids":["g1","g2"],"owner_user_ids":["owner"]}',
        encoding="utf-8",
    )

    config = GatewayConfig.from_file(config_path)
    overridden = config.with_overrides(port=6200)

    assert config.qq_file_learning_allowed_group_ids == frozenset({"g1", "g2"})
    assert overridden.qq_file_learning_allowed_group_ids == frozenset({"g1", "g2"})


def _gateway() -> NativeQQGateway:
    return NativeQQGateway(
        GatewayConfig(
            require_whitelist=False,
            owner_user_ids=frozenset({"owner"}),
            trusted_user_ids=frozenset({"trusted"}),
            allowed_group_ids=frozenset({"g1"}),
            qq_file_learning_allowed_group_ids=frozenset({"g1"}),
        )
    )


def _group_file_event(*, user_id: str = "owner", group_id: str = "g1") -> dict:
    return {
        "post_type": "message",
        "message_type": "group",
        "platform": "qq",
        "group_id": group_id,
        "user_id": user_id,
        "self_id": "bot",
        "message_id": "m-file",
        "message": [
            {
                "type": "file",
                "data": {
                    "name": "notes.txt",
                    "file_id": "qq-file-token",
                },
            }
        ],
        "raw_message": "[CQ:file,file_id=qq-file-token,name=notes.txt]",
        "time": 1_700_000_000,
    }


def _group_image_event(*, user_id: str = "external", group_id: str = "g1", mention_bot: bool = True) -> dict:
    message = []
    raw = ""
    if mention_bot:
        message.append({"type": "at", "data": {"qq": "bot"}})
        raw += "[CQ:at,qq=bot]"
    message.append(
        {
            "type": "image",
            "data": {
                "file": "scan.png",
                "url": "https://example.com/scan.png",
            },
        }
    )
    raw += "[CQ:image,file=scan.png,url=https://example.com/scan.png]"
    return {
        "post_type": "message",
        "message_type": "group",
        "platform": "qq",
        "group_id": group_id,
        "user_id": user_id,
        "self_id": "bot",
        "message_id": "m-image",
        "message": message,
        "raw_message": raw,
        "time": 1_700_000_000,
    }


def test_file_segment_accepts_napcat_download_url_alias() -> None:
    event = _group_file_event()
    event["message"][0]["data"] = {
        "name": "notes.txt",
        "download_url": "https://example.com/notes.txt",
    }

    prepared = _gateway().prepare_message(event)

    assert prepared is not None
    assert prepared.route == "learning_ingest"
    assert prepared.payload["file_url"] == "https://example.com/notes.txt"


def test_file_segment_accepts_napcat_file_id_and_busid_aliases() -> None:
    event = _group_file_event()
    event["message"][0]["data"] = {
        "name": "notes.txt",
        "fileId": "camel-file-token",
        "busid": "102",
    }

    prepared = _gateway().prepare_message(event)

    assert prepared is not None
    assert prepared.route == "learning_ingest"
    assert prepared.payload["file_id"] == "camel-file-token"
    assert prepared.payload["busid"] == "102"
    assert prepared.payload["metadata"]["busid"] == "102"


def test_resolver_passes_group_file_busid_to_onebot() -> None:
    class Gateway:
        def __init__(self) -> None:
            self.calls = []

        async def _onebot_file_url_action(self, websocket, action, params):
            self.calls.append((action, params))
            return "https://example.com/resolved.txt"

    gateway = Gateway()
    payload = {
        "file_id": "group-file-token",
        "metadata": {
            "segment_type": "file",
            "group_id": "674690634",
            "busid": "102",
        },
    }

    resolved = asyncio.run(resolve_learning_ingest_payload(gateway, None, payload))

    assert resolved["file_url"] == "https://example.com/resolved.txt"
    assert gateway.calls == [
        (
            "get_group_file_url",
            {"group_id": 674690634, "file_id": "group-file-token", "busid": 102},
        )
    ]


def test_owner_group_file_learning_uses_learning_ingest() -> None:
    prepared = _gateway().prepare_message(_group_file_event())

    assert prepared is not None
    assert prepared.route == "learning_ingest"
    assert prepared.target.message_kind == "group"
    assert prepared.payload["file_id"] == "qq-file-token"
    assert prepared.payload["file_name"] == "notes.txt"
    assert prepared.payload["metadata"]["group_id"] == "g1"


def test_trusted_group_file_learning_is_allowed() -> None:
    prepared = _gateway().prepare_message(_group_file_event(user_id="trusted"))

    assert prepared is not None
    assert prepared.route == "learning_ingest"


def test_external_group_file_learning_is_rejected() -> None:
    gateway = _gateway()
    event = _group_file_event(user_id="external")

    assert gateway.prepare_message(event) is None
    assert gateway._prepare_none_reason(event) == "file_learning_sender_not_trusted"


def test_owner_group_file_learning_rejects_empty_group_file_allowlist() -> None:
    gateway = NativeQQGateway(
        GatewayConfig(
            require_whitelist=False,
            owner_user_ids=frozenset({"owner"}),
            allowed_group_ids=frozenset({"g1"}),
            qq_file_learning_allowed_group_ids=frozenset(),
        )
    )
    event = _group_file_event(user_id="owner", group_id="g1")

    assert gateway.prepare_message(event) is None
    assert gateway._prepare_none_reason(event) == "file_learning_group_not_allowed"


def test_external_group_image_mention_falls_through_to_chat_context() -> None:
    prepared = _gateway().prepare_message(_group_image_event())

    assert prepared is not None
    assert prepared.route == "chat"
    assert prepared.payload["metadata"]["qq_image_count"] == 1
    assert prepared.payload["metadata"]["qq_rich_message"] is True
    assert prepared.payload["metadata"]["qq_group_trigger_reason"] == "group_mention_or_prefix"


def test_external_group_image_without_trigger_is_not_file_learning_rejected() -> None:
    gateway = _gateway()
    event = _group_image_event(mention_bot=False)

    assert gateway.prepare_message(event) is None
    assert gateway._prepare_none_reason(event) == "group_trigger_required"


def test_group_file_learning_requires_group_allowlist() -> None:
    gateway = _gateway()
    event = _group_file_event(group_id="g2")

    assert gateway.prepare_message(event) is None
    assert gateway._prepare_none_reason(event) == "file_learning_group_not_allowed"
