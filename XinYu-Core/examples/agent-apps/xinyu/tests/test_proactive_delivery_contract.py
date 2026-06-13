from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_http_dispatch_table import GET_ROUTE_DISPATCH, POST_ROUTE_DISPATCH
from xinyu_bridge_http_routes import is_known_get_route, is_known_post_route
from xinyu_bridge_proactive_delivery_claim import qq_outbox_claim, qq_outbox_claim_fast
from xinyu_bridge_proactive_delivery_ack import qq_outbox_ack, qq_outbox_ack_fast
from xinyu_bridge_proactive_delivery_contract import (
    PROACTIVE_DELIVERY_FALLBACK_ADAPTER,
    PROACTIVE_DELIVERY_ROLLBACK,
    PROACTIVE_DELIVERY_STATE_OWNER,
    PROACTIVE_GATEWAY_ACTION_TIMEOUT_ERROR,
    PROACTIVE_GATEWAY_ADAPTER_NAME,
    PROACTIVE_OUTBOX_MESSAGE_PREFIX,
    PROACTIVE_ACK_ERROR_NOTES,
    PROACTIVE_ACK_STATUS_VALUES,
    PROACTIVE_CLAIM_REQUIRED_FIELDS,
    PROACTIVE_CLAIM_SOURCE,
    ProactiveDeliveryHarness,
    is_proactive_outbox_message_id,
    proactive_ack_dto_contract,
    proactive_claim_dto_contract,
    proactive_delivery_capabilities,
    proactive_delivery_routes,
    proactive_gateway_adapter_contract,
    proactive_outbox_message_id,
    proactive_transport_health_contract,
    proactive_transport_preflight_contract,
)
from xinyu_bridge_proactive_delivery_routes_claim_result import build_proactive_claim_result
from xinyu_serviceization_contracts import service_contract_by_id
from xinyu_qq_outbox_client import (
    GATEWAY_NAME,
    GATEWAY_VERSION_FALLBACK,
    onebot_action_result,
    outbox_message_ack_payload,
    outbox_target,
    record_sent_message_ack_payload,
    sent_outbox_delivery_route,
)
from xinyu_qq_outbox_dispatcher import qq_outbox_visible_dispatch_enabled
from xinyu_qq_outbox import (
    MAX_ATTEMPTS,
    ack_qq_outbox_message,
    claim_next_qq_outbox_message,
    enqueue_qq_outbox_message,
)


def _safe_str(value: object = "", default: str = "") -> str:
    text = "" if value is None else str(value)
    return text or default


def test_proactive_delivery_contract_matches_service_boundary_manifest() -> None:
    contract = service_contract_by_id("proactive_delivery")
    capabilities = proactive_delivery_capabilities()

    assert proactive_delivery_routes() == contract.api_routes
    assert {capability.runtime_method for capability in capabilities}.issubset(contract.runtime_facade_methods)
    assert {
        capability.fast_method
        for capability in capabilities
        if capability.fast_method
    }.issubset(contract.runtime_facade_methods)


def test_proactive_delivery_contract_matches_http_dispatch_table() -> None:
    for capability in proactive_delivery_capabilities():
        if capability.http_method == "GET":
            assert is_known_get_route(capability.route)
            spec = GET_ROUTE_DISPATCH[capability.route]
        else:
            assert capability.http_method == "POST"
            assert is_known_post_route(capability.route)
            spec = POST_ROUTE_DISPATCH[capability.route]

        assert spec.method == capability.runtime_method
        assert (spec.fast_method or "") == capability.fast_method


def test_proactive_delivery_message_id_contract() -> None:
    assert proactive_outbox_message_id("request-1") == "proactive:request-1"
    assert is_proactive_outbox_message_id("proactive:request-1") is True
    assert is_proactive_outbox_message_id("qq-outbox-1") is False


def test_proactive_claim_result_uses_message_id_contract() -> None:
    result = build_proactive_claim_result(
        {"request_id": "request-1", "notes": ["source-note"]},
        claim_id="claim-1",
        owner_user_id="owner-1",
        message="hello",
        note="claimed-from-test",
        safe_str_func=_safe_str,
    )

    assert result["message_id"] == proactive_outbox_message_id("request-1")
    assert result["notes"] == ["claimed", "claimed-from-test", "source-note"]


def test_proactive_claim_dto_contract_freezes_minimum_shape() -> None:
    contract = proactive_claim_dto_contract()
    result = build_proactive_claim_result(
        {"request_id": "request-1", "notes": ["source-note"]},
        claim_id="claim-1",
        owner_user_id="owner-1",
        message="hello",
        note="claimed-from-test",
        safe_str_func=_safe_str,
    )

    assert contract.required_fields == PROACTIVE_CLAIM_REQUIRED_FIELDS
    assert contract.source == PROACTIVE_CLAIM_SOURCE
    assert contract.message_id_prefix == PROACTIVE_OUTBOX_MESSAGE_PREFIX
    assert set(contract.required_fields).issubset(result)
    assert result["accepted"] is True
    assert result["message_claimed"] is True
    assert result["message_id"] == "proactive:request-1"
    assert result["claim_id"] == "claim-1"
    assert result["target"] == {"message_kind": "private", "user_id": "owner-1", "group_id": ""}
    assert result["message"] == "hello"
    assert result["attempts"] == contract.attempts
    assert result["source"] == contract.source
    assert "claimed" in result["notes"]
    assert "ordinary_qq_outbox_claim_has_priority" in contract.state_transitions
    assert "claim_sets_last_ack_status_pending" in contract.state_transitions


def test_proactive_ack_dto_contract_freezes_status_and_branch_semantics() -> None:
    contract = proactive_ack_dto_contract()

    assert contract.payload_fields == (
        "message_id",
        "claim_id",
        "ack_status_or_status",
        "adapter_message_id",
        "adapter_error_or_error",
    )
    assert contract.status_values == PROACTIVE_ACK_STATUS_VALUES
    assert set(contract.status_values) == {"sent", "failed", "queued", "dry_run"}
    assert contract.error_notes == PROACTIVE_ACK_ERROR_NOTES
    assert contract.request_status_by_ack_status == {
        "sent": "sent",
        "failed": "failed",
        "queued": "queued_qq",
        "dry_run": "ready",
    }
    assert contract.answer_state_by_ack_status == {
        "sent": "sent_waiting_owner_reply",
        "failed": "not_requested_failed",
    }
    assert "proactive_message_id_routes_to_proactive_presence_ack" in contract.branch_semantics
    assert "ordinary_message_id_routes_to_qq_outbox_ack" in contract.branch_semantics
    assert "missing_adapter_message_id_falls_back_to_message_id" in contract.branch_semantics
    assert "record_outbound_only_when_ack_recorded_and_sent" in contract.branch_semantics
    assert "terminal_sent_ack_is_idempotent" in contract.branch_semantics
    assert "late_failed_ack_does_not_downgrade_sent" in contract.branch_semantics


def test_proactive_gateway_adapter_contract_matches_qq_outbox_helpers() -> None:
    contract = proactive_gateway_adapter_contract()

    assert contract.gateway_name == PROACTIVE_GATEWAY_ADAPTER_NAME == GATEWAY_NAME
    assert contract.gateway_version_fallback == GATEWAY_VERSION_FALLBACK
    assert contract.claim_payload_fields == ("claim_id", "adapter")
    assert contract.ack_payload_fields == (
        "message_id",
        "claim_id",
        "ack_status",
        "adapter_message_id",
        "adapter_error",
    )

    target = outbox_target(
        None,
        {"target": {"message_kind": "private", "user_id": "owner-1", "group_id": ""}},
        SimpleNamespace,
    )
    assert target == SimpleNamespace(message_kind="private", user_id="owner-1", group_id="")
    assert outbox_target(
        None,
        {"target": {"message_kind": "group", "user_id": "owner-1", "group_id": "group-1"}},
        SimpleNamespace,
    ) is None

    ok, adapter_message_id, adapter_error = onebot_action_result(
        None,
        {"status": "ok", "retcode": 1, "data": {"message_id": "onebot-1"}},
    )
    assert (ok, adapter_message_id, adapter_error) == (True, "onebot-1", "")
    assert onebot_action_result(None, {"status": "failed", "message": "denied"}) == (False, "", "denied")
    assert onebot_action_result(None, None) == (False, "", PROACTIVE_GATEWAY_ACTION_TIMEOUT_ERROR)

    assert sent_outbox_delivery_route("proactive:request-1", "text") == contract.sent_delivery_routes["proactive_text"]
    assert sent_outbox_delivery_route("proactive:request-1", "image") == contract.sent_delivery_routes["proactive_image"]
    assert sent_outbox_delivery_route("proactive:request-1", "caption") == contract.sent_delivery_routes[
        "proactive_caption"
    ]
    assert sent_outbox_delivery_route("ordinary-1", "text") == contract.sent_delivery_routes["ordinary_text"]
    assert sent_outbox_delivery_route("ordinary-1", "image") == contract.sent_delivery_routes["ordinary_image"]
    assert sent_outbox_delivery_route("ordinary-1", "caption") == contract.sent_delivery_routes["ordinary_caption"]

    gateway = SimpleNamespace(gateway_version="0.1.29", _session_id=lambda target: "session-owner")
    payload = outbox_message_ack_payload(
        gateway,
        {
            "message_id": "proactive:request-1",
            "source": "proactive_request",
            "message_type": "text",
            "metadata": {
                "turn_id": "turn-1",
                "source_message_id": "source-1",
                "reply_hash": "hash-1",
            },
        },
        target=SimpleNamespace(message_kind="private", user_id="owner-1", group_id=""),
        visible_text="hello",
        adapter_message_id="onebot-2",
        delivery_kind="text",
    )

    assert set(contract.sent_ack_required_fields).issubset(payload)
    assert payload["adapter"] == contract.gateway_name
    assert payload["gateway"] == contract.gateway_name
    assert payload["adapter_message_id"] == "onebot-2"
    assert payload["route"] == "proactive"
    assert payload["source_route"] == "proactive"
    assert payload["session_id"] == "session-owner"
    assert payload["target"] == {"message_kind": "private", "user_id": "owner-1", "group_id": ""}
    assert payload["metadata"]["outbox_source"] == "proactive_request"
    assert payload["metadata"]["delivery_kind"] == "text"
    assert outbox_message_ack_payload(
        gateway,
        {"message_id": "proactive:request-1"},
        target=SimpleNamespace(message_kind="private", user_id="owner-1", group_id=""),
        visible_text="hello",
        adapter_message_id="",
        delivery_kind="text",
    ) == {}


def test_proactive_transport_health_contract_matches_dispatch_controls() -> None:
    contract = proactive_transport_health_contract()

    assert contract.visible_dispatch_required_config == (
        "qq_outbox_enabled",
        "bridge_token",
        "send_replies",
    )
    assert contract.sent_ack_required_config == (
        "bridge_token",
        "message_ack_url",
    )
    assert PROACTIVE_GATEWAY_ACTION_TIMEOUT_ERROR in contract.disabled_errors
    assert "transport_health_ready_does_not_enable_process_split" in contract.semantics

    gateway = SimpleNamespace(
        config=SimpleNamespace(
            qq_outbox_enabled=True,
            bridge_token="bridge-token",
            send_replies=True,
            message_ack_url="",
        ),
        client=SimpleNamespace(message_ack_url=""),
    )
    assert qq_outbox_visible_dispatch_enabled(gateway) is True

    for field in contract.visible_dispatch_required_config:
        original = getattr(gateway.config, field)
        setattr(gateway.config, field, "" if isinstance(original, str) else False)
        assert qq_outbox_visible_dispatch_enabled(gateway) is False
        setattr(gateway.config, field, original)

    assert asyncio.run(record_sent_message_ack_payload(gateway, {"adapter_message_id": "onebot-1"})) is False
    gateway.config.message_ack_url = "http://core/message/ack"
    assert asyncio.run(record_sent_message_ack_payload(gateway, {"adapter_message_id": "onebot-1"})) is False


def test_proactive_transport_preflight_is_s4_ready_without_process_split() -> None:
    contract = proactive_transport_preflight_contract()

    assert contract.service_id == "proactive_delivery"
    assert contract.ready is True
    assert contract.satisfied_gates == (
        "claim_dto_contract",
        "ack_dto_contract",
        "virtual_message_id_branch_contract",
        "ordinary_outbox_priority_contract",
        "retry_dead_semantics_contract",
        "gateway_adapter_contract",
        "transport_health_contract",
        "route_backend_selection_contract",
        "state_store_ownership_contract",
        "in_process_fallback_rollback_contract",
    )
    assert contract.missing_gates == ()
    assert "transport_contracts_ready_for_controlled_process_split" in contract.notes


def test_qq_outbox_claim_prefers_ordinary_outbox_before_proactive_fallback() -> None:
    calls: list[str] = []
    ordinary_claim = {
        "accepted": True,
        "message_claimed": True,
        "message_id": "ordinary-1",
        "claim_id": "claim-1",
        "notes": ["claimed"],
    }

    def claim_next_message(root: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append("ordinary")
        return ordinary_claim

    async def to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def proactive_fallback(payload: dict[str, object]) -> dict[str, object]:
        raise AssertionError("proactive fallback must not run when ordinary outbox claimed a message")

    runtime = SimpleNamespace(xinyu_dir="xinyu", _claim_proactive_for_qq_outbox=proactive_fallback)

    result = asyncio.run(
        qq_outbox_claim(
            runtime,
            {"claim_id": "claim-1"},
            claim_next_message_func=claim_next_message,
            to_thread_func=to_thread,
        )
    )

    assert result is ordinary_claim
    assert calls == ["ordinary"]


def test_qq_outbox_claim_fast_prefers_ordinary_outbox_before_proactive_fallback() -> None:
    ordinary_claim = {
        "accepted": True,
        "message_claimed": True,
        "message_id": "ordinary-1",
        "claim_id": "claim-1",
        "notes": ["claimed"],
    }

    def proactive_fallback(payload: dict[str, object]) -> dict[str, object]:
        raise AssertionError("proactive fallback must not run when ordinary outbox claimed a message")

    runtime = SimpleNamespace(xinyu_dir="xinyu", _claim_proactive_for_qq_outbox_sync=proactive_fallback)

    result = qq_outbox_claim_fast(
        runtime,
        {"claim_id": "claim-1"},
        claim_next_message_func=lambda root, payload: ordinary_claim,
    )

    assert result is ordinary_claim


def test_ordinary_qq_outbox_failed_retry_reaches_dead_after_max_attempts(tmp_path: Path) -> None:
    queued = enqueue_qq_outbox_message(
        tmp_path,
        user_id="owner-1",
        message="hello",
        source="test",
        dedupe_key="retry-dead",
    )
    message_id = queued["message_id"]

    def age_failed_item() -> None:
        queue_path = tmp_path / "memory/context/qq_outbox_queue.json"
        data = json.loads(queue_path.read_text(encoding="utf-8"))
        data["items"][0]["acked_at"] = "2000-01-01T00:00:00+00:00"
        queue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        claim = claim_next_qq_outbox_message(
            tmp_path,
            {"claim_id": f"claim-{attempt}", "retry_after_seconds": 5},
        )
        assert claim["message_claimed"] is True
        assert claim["message_id"] == message_id
        assert claim["attempts"] == attempt

        ack = ack_qq_outbox_message(
            tmp_path,
            {
                "message_id": message_id,
                "claim_id": f"claim-{attempt}",
                "ack_status": "failed",
                "adapter_error": f"boom-{attempt}",
            },
        )

        expected_status = "dead" if attempt == MAX_ATTEMPTS else "failed"
        assert ack["ack_recorded"] is True
        assert ack["ack_status"] == expected_status
        assert ack["attempts"] == attempt
        if attempt < MAX_ATTEMPTS:
            age_failed_item()

    empty = claim_next_qq_outbox_message(tmp_path, {"claim_id": "after-dead"})
    assert empty["message_claimed"] is False
    assert empty["notes"] == ["empty"]


def test_proactive_transport_preflight_requires_all_gates() -> None:
    all_gates = proactive_transport_preflight_contract().required_gates
    contract = proactive_transport_preflight_contract(all_gates)

    assert contract.ready is True
    assert contract.satisfied_gates == all_gates
    assert contract.missing_gates == ()


def test_proactive_delivery_harness_lifecycle_readiness_and_fallback() -> None:
    harness = ProactiveDeliveryHarness()

    initial = harness.readiness()
    assert initial.service_id == "proactive_delivery"
    assert initial.mode == "in_process"
    assert initial.started is False
    assert initial.ready is False
    assert initial.state_owner == PROACTIVE_DELIVERY_STATE_OWNER
    assert initial.fallback_adapter == PROACTIVE_DELIVERY_FALLBACK_ADAPTER
    assert initial.rollback == PROACTIVE_DELIVERY_ROLLBACK

    started = harness.start()
    assert started.started is True
    assert started.ready is True

    def _method(name: str):
        def call(*args, **kwargs):
            return {"method": name, "args": args, "kwargs": kwargs}

        return call

    method_names = {
        capability.runtime_method for capability in proactive_delivery_capabilities()
    } | {
        capability.fast_method for capability in proactive_delivery_capabilities() if capability.fast_method
    }
    runtime = SimpleNamespace(**{method: _method(method) for method in method_names})
    fallback = harness.fallback_adapter(runtime)

    assert set(fallback) == method_names
    assert fallback["qq_outbox_claim_fast"]({"claim": True})["method"] == "qq_outbox_claim_fast"

    stopped = harness.stop()
    assert stopped.started is False
    assert stopped.ready is False


def test_qq_outbox_ack_routes_proactive_message_id_to_proactive_ack() -> None:
    calls: list[tuple[str, object]] = []

    async def proactive_ack_bridge(**kwargs: object) -> dict[str, object]:
        calls.append(("proactive", kwargs["payload"]))
        return {
            "accepted": True,
            "ack_recorded": True,
            "claim_id": "claim-1",
            "ack_status": "sent",
            "adapter_message_id": "onebot-1",
            "notes": ["sent"],
        }

    def ack_outbox_message(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("ordinary outbox ack must not run for proactive ids")

    async def publish(**kwargs: object) -> None:
        calls.append(("publish", kwargs))

    def record_outbound(runtime: object, payload: dict[str, object]) -> None:
        calls.append(("outbound", dict(payload)))

    runtime = SimpleNamespace(
        xinyu_dir="xinyu",
        memory_root="memory",
        _cleanup_idle_sessions=lambda: None,
        _sessions={},
        _global_turn_lock=object(),
        _desktop_publish_proactive_delivery_from_state=publish,
    )
    payload = {
        "message_id": "proactive:request-1",
        "claim_id": "claim-1",
        "ack_status": "sent",
        "adapter_message_id": "onebot-1",
    }

    result = asyncio.run(
        qq_outbox_ack(
            runtime,
            payload,
            proactive_ack_bridge_func=proactive_ack_bridge,
            ack_outbox_message_func=ack_outbox_message,
            to_thread_func=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ordinary branch")),
            safe_str_func=_safe_str,
            record_outbound_func=record_outbound,
        )
    )

    assert result["ack_recorded"] is True
    assert calls[0] == ("proactive", payload)
    assert calls[1][0] == "publish"
    assert calls[2] == ("outbound", payload)


def test_qq_outbox_ack_fast_maps_aliases_and_keeps_outbound_sent_only() -> None:
    calls: list[tuple[str, object]] = []

    def acknowledge_proactive_qq_message(*args: object, **kwargs: object) -> dict[str, object]:
        calls.append(("proactive", kwargs))
        return {
            "accepted": True,
            "ack_recorded": True,
            "claim_id": kwargs["claim_id"],
            "ack_status": kwargs["ack_status"],
            "adapter_message_id": kwargs["adapter_message_id"],
            "notes": [kwargs["adapter_error"]],
        }

    def ack_outbox_message(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("ordinary outbox ack must not run for proactive ids")

    def record_outbound(runtime: object, payload: dict[str, object]) -> None:
        calls.append(("outbound", dict(payload)))

    runtime = SimpleNamespace(
        xinyu_dir="xinyu",
        _sessions={},
        _desktop_publish_proactive_delivery_from_state_threadsafe=lambda **kwargs: calls.append(("publish", kwargs)),
    )
    payload = {
        "message_id": "proactive:request-1",
        "claim_id": "claim-1",
        "status": "queued",
        "error": "adapter-timeout",
    }

    result = qq_outbox_ack_fast(
        runtime,
        payload,
        acknowledge_proactive_qq_message_func=acknowledge_proactive_qq_message,
        ack_outbox_message_func=ack_outbox_message,
        safe_str_func=_safe_str,
        record_outbound_func=record_outbound,
    )

    assert result["ack_status"] == "queued"
    assert result["adapter_message_id"] == "proactive:request-1"
    assert calls[0] == (
        "proactive",
        {
            "claim_id": "claim-1",
            "ack_status": "queued",
            "adapter_message_id": "proactive:request-1",
            "adapter_error": "adapter-timeout",
        },
    )
    assert calls[1][0] == "publish"
    assert all(call[0] != "outbound" for call in calls)
