from __future__ import annotations

import asyncio
from types import SimpleNamespace

import xinyu_qq_outbox_dispatcher as outbox_dispatcher
from xinyu_qq_models import ReplyTarget
from xinyu_qq_outbox import ack_qq_outbox_message, claim_next_qq_outbox_message, enqueue_qq_outbox_message
from xinyu_qq_outbox_client import outbox_message_ack_payload, sent_outbox_delivery_route
from xinyu_qq_outbox_dispatcher import poll_qq_outbox, qq_outbox_visible_dispatch_enabled
from xinyu_qq_outbox_state import summarize_outbox_items
from xinyu_runtime_presence import read_runtime_presence_summary


def _gateway_config(
    *,
    qq_outbox_enabled: bool = True,
    bridge_token: str = "bridge-token",
    send_replies: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            qq_outbox_enabled=qq_outbox_enabled,
            bridge_token=bridge_token,
            send_replies=send_replies,
        )
    )


def test_send_replies_is_global_visible_outbox_kill_switch() -> None:
    gateway = _gateway_config(send_replies=False)

    assert qq_outbox_visible_dispatch_enabled(gateway) is False

    gateway.config.send_replies = True
    assert qq_outbox_visible_dispatch_enabled(gateway) is True


def test_qq_outbox_visible_dispatch_requires_outbox_token_and_replies() -> None:
    assert qq_outbox_visible_dispatch_enabled(_gateway_config()) is True
    assert qq_outbox_visible_dispatch_enabled(_gateway_config(qq_outbox_enabled=False)) is False
    assert qq_outbox_visible_dispatch_enabled(_gateway_config(bridge_token="")) is False
    assert qq_outbox_visible_dispatch_enabled(_gateway_config(send_replies=False)) is False
    assert qq_outbox_visible_dispatch_enabled(SimpleNamespace()) is False


def test_poll_qq_outbox_acks_claim_failed_when_dispatch_is_disabled_after_claim(monkeypatch) -> None:
    async def fast_sleep(_seconds: float) -> None:
        return None

    class ClaimingClient:
        def __init__(self, gateway: SimpleNamespace) -> None:
            self.gateway = gateway
            self.claim_payloads: list[dict[str, object]] = []

        async def qq_outbox_claim(self, payload: dict[str, object]) -> dict[str, object]:
            self.claim_payloads.append(dict(payload))
            self.gateway.config.send_replies = False
            return {
                "message_claimed": True,
                "message_id": "proactive:s4-transport-1",
                "claim_id": "claim-s4",
                "target": {"message_kind": "private", "user_id": "42", "group_id": ""},
                "message_type": "text",
                "message": "should not be sent",
                "source": "xinyu_proactive_direct_sender",
                "metadata": {"proactive_request_id": "proreq-s4"},
            }

    class Gateway(SimpleNamespace):
        def _outbox_target(self, _claim: dict[str, object]) -> None:
            raise AssertionError("dispatch disabled should stop before target resolution")

        async def _ack_qq_outbox(
            self,
            claim: dict[str, object],
            *,
            status: str,
            error: str = "",
            adapter_message_id: str = "",
        ) -> None:
            self.acks.append(
                {
                    "message_id": claim.get("message_id"),
                    "claim_id": claim.get("claim_id"),
                    "status": status,
                    "error": error,
                    "adapter_message_id": adapter_message_id,
                }
            )
            raise asyncio.CancelledError

    gateway = Gateway(
        config=SimpleNamespace(
            qq_outbox_enabled=True,
            bridge_token="bridge-token",
            send_replies=True,
            qq_outbox_poll_seconds=5,
        ),
        acks=[],
    )
    gateway.client = ClaimingClient(gateway)
    monkeypatch.setattr(
        outbox_dispatcher,
        "asyncio",
        SimpleNamespace(sleep=fast_sleep, CancelledError=asyncio.CancelledError),
    )

    try:
        asyncio.run(poll_qq_outbox(gateway, None, "conn", gateway_name="xinyu_native_qq_gateway"))
    except asyncio.CancelledError:
        pass

    assert len(gateway.client.claim_payloads) == 1
    assert gateway.client.claim_payloads[0]["adapter"] == "xinyu_native_qq_gateway"
    assert str(gateway.client.claim_payloads[0]["claim_id"]).startswith("conn-")
    assert gateway.acks == [
        {
            "message_id": "proactive:s4-transport-1",
            "claim_id": "claim-s4",
            "status": "failed",
            "error": "visible outbound dispatch disabled",
            "adapter_message_id": "",
        }
    ]


def test_dispatch_disabled_ack_is_visible_in_program_health(tmp_path) -> None:
    dispatch_state = tmp_path / "memory/context/proactive_qq_dispatch_state.md"
    dispatch_state.parent.mkdir(parents=True, exist_ok=True)
    dispatch_state.write_text(
        """
        - last_claim_id: claim-disabled
        - proactive_request_id: proreq-s4
        - last_claim_status: claimed
        - last_ack_status: claimed
        - adapter_error: none
        - min_interval_seconds: 0
        """.strip()
        + "\n",
        encoding="utf-8",
    )
    queued = enqueue_qq_outbox_message(
        tmp_path,
        user_id="42",
        message="owner-visible proactive reply",
        source="xinyu_proactive_direct_sender",
        dedupe_key="proactive-s4-disabled",
        metadata={
            "proactive_request_id": "proreq-s4",
            "claim_id": "claim-disabled",
            "direct_proactive": True,
        },
    )
    claim = claim_next_qq_outbox_message(
        tmp_path,
        {"claim_id": "claim-disabled", "adapter": "xinyu_native_qq_gateway"},
    )

    ack = ack_qq_outbox_message(
        tmp_path,
        {
            "message_id": claim["message_id"],
            "claim_id": claim["claim_id"],
            "ack_status": "failed",
            "adapter_error": "visible outbound dispatch disabled",
        },
    )
    summary = read_runtime_presence_summary(tmp_path)
    qq_outbox = summary["program_awareness"]["subsystems"]["qq_outbox"]
    proactive_dispatch = summary["program_awareness"]["subsystems"]["proactive_dispatch"]

    assert queued["queued"] is True
    assert claim["message_claimed"] is True
    assert ack["ack_status"] == "failed"
    assert "proactive_dispatch_state_updated" in ack["notes"]
    assert qq_outbox["queue_items"] == "1"
    assert qq_outbox["failed_count"] == "1"
    assert qq_outbox["recent_failed_count"] == "1"
    assert qq_outbox["last_failed_at"] != "none"
    assert proactive_dispatch["last_ack_status"] == "failed"
    assert proactive_dispatch["adapter_error"] == "visible outbound dispatch disabled"
    assert "qq_outbox.recent_failed_count=1" in summary["program_awareness"]["known_errors"]
    assert (
        "proactive_dispatch.adapter_error=visible outbound dispatch disabled"
        in summary["program_awareness"]["known_errors"]
    )


def test_outbox_sent_delivery_route_and_payload_contract_stay_stable() -> None:
    gateway = SimpleNamespace(
        gateway_version="0.1.test",
        _session_id=lambda target: f"qq:{target.message_kind}:{target.user_id}",
    )
    target = ReplyTarget(message_kind="private", user_id="42", group_id="")
    claim = {
        "message_id": "proactive:s4-transport-1",
        "source": "xinyu_proactive_direct_sender",
        "message_type": "text",
        "metadata": {
            "session_id": "qq:private:42",
            "turn_id": "turn-s4",
            "archive_message_ids": ["archive-user-1"],
            "archive_assistant_message_id": "archive-assistant-1",
            "source_message_id": "source-message-1",
            "reply_hash": "sha256:reply",
        },
    }

    payload = outbox_message_ack_payload(
        gateway,
        claim,
        target=target,
        visible_text="caption sent",
        adapter_message_id="adapter-message-1",
        delivery_kind="caption",
    )

    assert sent_outbox_delivery_route("ordinary-outbox-1", "text") == "qq_outbox"
    assert sent_outbox_delivery_route("ordinary-outbox-1", "caption") == "qq_outbox_caption"
    assert sent_outbox_delivery_route("proactive:s4-transport-1", "image") == "proactive_image"
    assert sent_outbox_delivery_route("proactive:s4-transport-1", "caption") == "proactive_caption"
    assert payload["route"] == "proactive_caption"
    assert payload["source_route"] == "proactive_caption"
    assert payload["session_id"] == "qq:private:42"
    assert payload["turn_id"] == "turn-s4"
    assert payload["archive_message_ids"] == ["archive-user-1"]
    assert payload["archive_assistant_message_id"] == "archive-assistant-1"
    assert payload["source_message_id"] == "source-message-1"
    assert payload["outbox_message_id"] == "proactive:s4-transport-1"
    assert payload["target"] == {"message_kind": "private", "user_id": "42", "group_id": ""}
    assert payload["visible_text"] == "caption sent"
    assert payload["visible_text_hash"] == "sha256:reply"
    assert payload["metadata"]["source_route"] == "proactive_caption"
    assert payload["metadata"]["outbox_source"] == "xinyu_proactive_direct_sender"
    assert payload["metadata"]["outbox_message_type"] == "text"
    assert payload["metadata"]["delivery_kind"] == "caption"


def test_outbox_summary_counts_suppressed_and_unknown_statuses() -> None:
    summary = summarize_outbox_items(
        [
            {"status": "queued"},
            {"status": "suppressed"},
            {"status": "legacy_status"},
        ]
    )

    assert summary["queue_items"] == 3
    assert summary["queued_count"] == 1
    assert summary["suppressed_count"] == 1
    assert summary["unknown_status_count"] == 1
