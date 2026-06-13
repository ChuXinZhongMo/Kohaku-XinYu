from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_proactive_delivery_ack import qq_outbox_ack, qq_outbox_ack_fast
from xinyu_proactive_presence import acknowledge_proactive_qq_message
from xinyu_qq_outbox import ack_qq_outbox_message, claim_next_qq_outbox_message, enqueue_qq_outbox_message


def _safe_str(value: object = "", default: str = "") -> str:
    text = "" if value is None else str(value)
    return text or default


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _queue_data(root: Path) -> dict[str, object]:
    return json.loads((root / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))


def _seed_proactive_outbox_states(root: Path, *, request_id: str, message_id: str, claim_id: str) -> None:
    _write(
        root / "memory/context/proactive_request_state.md",
        f"""
        ---
        title: Proactive Request State
        updated_at: 2026-06-09T10:00:00+08:00
        ---

        # Proactive Request State

        - request_id: {request_id}
        - concrete_question: Should I continue the current plan?
        - status: queued_qq
        - delivery_level: queue_owner_private
        - request_answer_state: approved_qq
        - qq_outbox_message_id: {message_id}
        - adapter_message_id: {message_id}
        - last_ack_status: queued
        - adapter_error: none
        """,
    )
    _write(
        root / "memory/context/proactive_qq_dispatch_state.md",
        f"""
        ---
        title: Proactive QQ Dispatch State
        updated_at: 2026-06-09T10:00:00+08:00
        ---

        # Proactive QQ Dispatch State

        ## Last Claim
        - last_claimed_at: 2026-06-09T10:00:00+08:00
        - last_claim_id: {claim_id}
        - last_claim_status: queued
        - proactive_request_id: {request_id}
        - min_interval_seconds: 0
        - last_claimed_message: Should I continue the current plan?

        ## Last Ack
        - last_acked_at: 2026-06-09T10:00:00+08:00
        - last_ack_status: queued
        - adapter_message_id: {message_id}
        - adapter_error: none
        """,
    )


def _seed_proactive_virtual_claim(root: Path, *, claim_id: str = "claim-virtual-1") -> None:
    _write(
        root / "memory/context/proactive_request_state.md",
        f"""
        ---
        title: Proactive Request State
        updated_at: 2026-06-09T11:00:00+08:00
        ---

        # Proactive Request State

        - request_id: proreq-virtual
        - concrete_question: Can I send the summary?
        - status: claimed
        - delivery_level: queue_owner_private
        - request_answer_state: sent_waiting_owner_reply
        - qq_outbox_message_id: none
        - adapter_message_id: none
        - last_claim_id: {claim_id}
        - last_ack_status: pending
        - adapter_error: none
        """,
    )
    _write(
        root / "memory/context/proactive_qq_dispatch_state.md",
        f"""
        ---
        title: Proactive QQ Dispatch State
        updated_at: 2026-06-09T11:00:00+08:00
        ---

        # Proactive QQ Dispatch State

        ## Last Claim
        - last_claimed_at: 2026-06-09T11:00:00+08:00
        - last_claim_id: {claim_id}
        - last_claim_status: claimed
        - proactive_request_id: proreq-virtual
        - min_interval_seconds: 0
        - last_claimed_message: Can I send the summary?

        ## Last Ack
        - last_acked_at: none
        - last_ack_status: pending
        - adapter_message_id: none
        - adapter_error: none
        """,
    )


def test_ordinary_outbox_terminal_sent_ack_is_idempotent_and_not_downgraded(tmp_path: Path) -> None:
    queued = enqueue_qq_outbox_message(
        tmp_path,
        user_id="owner-1",
        message="visible proactive reply",
        source="xinyu_proactive_direct_sender",
        dedupe_key="idempotent-ordinary",
        metadata={
            "proactive_request_id": "proreq-ordinary",
            "claim_id": "claim-ordinary-1",
            "direct_proactive": True,
        },
    )
    message_id = str(queued["message_id"])
    _seed_proactive_outbox_states(
        tmp_path,
        request_id="proreq-ordinary",
        message_id=message_id,
        claim_id="claim-ordinary-1",
    )
    claim = claim_next_qq_outbox_message(tmp_path, {"claim_id": "claim-ordinary-1"})

    first = ack_qq_outbox_message(
        tmp_path,
        {
            "message_id": message_id,
            "claim_id": claim["claim_id"],
            "ack_status": "sent",
            "adapter_message_id": "adapter-ordinary-1",
        },
    )
    queue_after_sent = _queue_data(tmp_path)
    request_after_sent = _read(tmp_path / "memory/context/proactive_request_state.md")
    dispatch_after_sent = _read(tmp_path / "memory/context/proactive_qq_dispatch_state.md")

    duplicate = ack_qq_outbox_message(
        tmp_path,
        {
            "message_id": message_id,
            "claim_id": claim["claim_id"],
            "ack_status": "sent",
            "adapter_message_id": "adapter-ordinary-duplicate",
        },
    )
    late_failed = ack_qq_outbox_message(
        tmp_path,
        {
            "message_id": message_id,
            "claim_id": claim["claim_id"],
            "ack_status": "failed",
            "adapter_error": "late timeout after sent",
        },
    )

    assert first["ack_recorded"] is True
    assert first["ack_status"] == "sent"
    assert duplicate["accepted"] is True
    assert duplicate["ack_recorded"] is False
    assert duplicate["ack_status"] == "sent"
    assert "terminal_ack_already_recorded" in duplicate["notes"]
    assert late_failed["accepted"] is True
    assert late_failed["ack_recorded"] is False
    assert late_failed["ack_status"] == "sent"
    assert "late_ack_ignored_terminal_sent" in late_failed["notes"]
    assert _queue_data(tmp_path) == queue_after_sent
    assert _read(tmp_path / "memory/context/proactive_request_state.md") == request_after_sent
    assert _read(tmp_path / "memory/context/proactive_qq_dispatch_state.md") == dispatch_after_sent


def test_ordinary_outbox_ack_rejections_do_not_mutate_queue_or_dispatch_state(tmp_path: Path) -> None:
    queued = enqueue_qq_outbox_message(
        tmp_path,
        user_id="owner-1",
        message="hello",
        source="test",
        dedupe_key="reject-no-mutate",
    )
    message_id = str(queued["message_id"])
    claim_next_qq_outbox_message(tmp_path, {"claim_id": "claim-current"})
    queue_before_mismatch = _queue_data(tmp_path)

    mismatch = ack_qq_outbox_message(
        tmp_path,
        {"message_id": message_id, "claim_id": "claim-wrong", "ack_status": "sent"},
    )
    queue_before_missing = _queue_data(tmp_path)
    dispatch_before_missing = _read(tmp_path / "memory/context/qq_outbox_dispatch_state.md")
    missing = ack_qq_outbox_message(
        tmp_path,
        {"message_id": "missing-message", "claim_id": "claim-current", "ack_status": "failed"},
    )

    assert mismatch["ack_recorded"] is False
    assert mismatch["notes"] == ["claim_id_mismatch"]
    assert _queue_data(tmp_path) == queue_before_mismatch
    assert missing["ack_recorded"] is False
    assert missing["notes"] == ["message_not_found"]
    assert _queue_data(tmp_path) == queue_before_missing
    assert _read(tmp_path / "memory/context/qq_outbox_dispatch_state.md") == dispatch_before_missing


def test_proactive_virtual_terminal_sent_ack_is_idempotent_and_not_downgraded(tmp_path: Path) -> None:
    _seed_proactive_virtual_claim(tmp_path)

    first = acknowledge_proactive_qq_message(
        tmp_path,
        acked_at="2026-06-09T11:01:00+08:00",
        claim_id="claim-virtual-1",
        ack_status="sent",
        adapter_message_id="adapter-virtual-1",
    )
    request_after_sent = _read(tmp_path / "memory/context/proactive_request_state.md")
    dispatch_after_sent = _read(tmp_path / "memory/context/proactive_qq_dispatch_state.md")

    duplicate = acknowledge_proactive_qq_message(
        tmp_path,
        acked_at="2026-06-09T11:02:00+08:00",
        claim_id="claim-virtual-1",
        ack_status="sent",
        adapter_message_id="adapter-virtual-duplicate",
    )
    late_failed = acknowledge_proactive_qq_message(
        tmp_path,
        acked_at="2026-06-09T11:03:00+08:00",
        claim_id="claim-virtual-1",
        ack_status="failed",
        adapter_error="late timeout after sent",
    )

    assert first["ack_recorded"] is True
    assert first["ack_status"] == "sent"
    assert duplicate["accepted"] is True
    assert duplicate["ack_recorded"] is False
    assert duplicate["ack_status"] == "sent"
    assert "duplicate_sent_ack_ignored" in duplicate["notes"]
    assert late_failed["accepted"] is True
    assert late_failed["ack_recorded"] is False
    assert late_failed["ack_status"] == "sent"
    assert "late_ack_ignored_terminal_sent" in late_failed["notes"]
    assert _read(tmp_path / "memory/context/proactive_request_state.md") == request_after_sent
    assert _read(tmp_path / "memory/context/proactive_qq_dispatch_state.md") == dispatch_after_sent


def test_proactive_virtual_claim_id_mismatch_does_not_mutate_state(tmp_path: Path) -> None:
    _seed_proactive_virtual_claim(tmp_path, claim_id="claim-current")
    request_before = _read(tmp_path / "memory/context/proactive_request_state.md")
    dispatch_before = _read(tmp_path / "memory/context/proactive_qq_dispatch_state.md")

    result = acknowledge_proactive_qq_message(
        tmp_path,
        acked_at="2026-06-09T11:04:00+08:00",
        claim_id="claim-wrong",
        ack_status="sent",
        adapter_message_id="adapter-wrong",
    )

    assert result["accepted"] is True
    assert result["ack_recorded"] is False
    assert result["expected_claim_id"] == "claim-current"
    assert result["notes"][-1] == "claim_id_mismatch"
    assert _read(tmp_path / "memory/context/proactive_request_state.md") == request_before
    assert _read(tmp_path / "memory/context/proactive_qq_dispatch_state.md") == dispatch_before


def test_ack_route_wrappers_do_not_publish_or_record_outbound_for_idempotent_terminal_ack() -> None:
    async_calls: list[tuple[str, object]] = []

    async def proactive_ack_bridge(**kwargs: object) -> dict[str, object]:
        async_calls.append(("proactive", kwargs["payload"]))
        return {
            "accepted": True,
            "ack_recorded": False,
            "claim_id": "claim-1",
            "ack_status": "sent",
            "notes": ["terminal_ack_already_recorded"],
        }

    async def publish(**kwargs: object) -> None:
        async_calls.append(("publish", kwargs))

    runtime = SimpleNamespace(
        xinyu_dir="xinyu",
        memory_root="memory",
        _cleanup_idle_sessions=lambda: None,
        _sessions={},
        _global_turn_lock=object(),
        _desktop_publish_proactive_delivery_from_state=publish,
    )
    payload = {"message_id": "proactive:request-1", "claim_id": "claim-1", "ack_status": "sent"}

    async_result = asyncio.run(
        qq_outbox_ack(
            runtime,
            payload,
            proactive_ack_bridge_func=proactive_ack_bridge,
            ack_outbox_message_func=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ordinary branch")),
            to_thread_func=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ordinary thread branch")),
            safe_str_func=_safe_str,
            record_outbound_func=lambda runtime, payload: async_calls.append(("outbound", dict(payload))),
        )
    )

    fast_calls: list[tuple[str, object]] = []
    fast_runtime = SimpleNamespace(
        xinyu_dir="xinyu",
        _sessions={},
        _desktop_publish_proactive_delivery_from_state_threadsafe=lambda **kwargs: fast_calls.append(
            ("publish", kwargs)
        ),
    )

    def acknowledge_proactive_qq_message_func(*args: object, **kwargs: object) -> dict[str, object]:
        fast_calls.append(("proactive", kwargs))
        return {
            "accepted": True,
            "ack_recorded": False,
            "claim_id": kwargs["claim_id"],
            "ack_status": "sent",
            "notes": ["terminal_ack_already_recorded"],
        }

    fast_result = qq_outbox_ack_fast(
        fast_runtime,
        payload,
        acknowledge_proactive_qq_message_func=acknowledge_proactive_qq_message_func,
        ack_outbox_message_func=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ordinary branch")),
        safe_str_func=_safe_str,
        record_outbound_func=lambda runtime, payload: fast_calls.append(("outbound", dict(payload))),
    )

    assert async_result["ack_recorded"] is False
    assert async_calls == [("proactive", payload)]
    assert fast_result["ack_recorded"] is False
    assert fast_calls == [
        (
            "proactive",
            {
                "claim_id": "claim-1",
                "ack_status": "sent",
                "adapter_message_id": "proactive:request-1",
                "adapter_error": "",
            },
        )
    ]
