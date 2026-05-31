from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import xinyu_bridge_desktop_proactive_routes as desktop_routes
from xinyu_proactive_response_diagnostics import (
    build_proactive_response_diagnostics,
    write_proactive_response_diagnostics,
)
from xinyu_qq_outbox import ack_qq_outbox_message, claim_next_qq_outbox_message, enqueue_qq_outbox_message


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _replace_line(text: str, field: str, value: str) -> str:
    lines = text.splitlines()
    replacement = f"- {field}: {value}"
    for index, line in enumerate(lines):
        if line.strip().startswith(f"- {field}:"):
            lines[index] = replacement
            return "\n".join(lines) + "\n"
    return text.rstrip() + "\n" + replacement + "\n"


def test_qq_outbox_ack_updates_proactive_request_without_copying_message_body(tmp_path: Path) -> None:
    raw_outbox_message = "RAW_OUTBOX_BODY_SHOULD_NOT_COPY_6219"
    queued = enqueue_qq_outbox_message(
        tmp_path,
        user_id="owner-1",
        message=raw_outbox_message,
        source="desktop_proactive_ack",
        dedupe_key="desktop-proactive:proreq-outbox-ack",
        metadata={
            "source": "xinyu_desktop_shell",
            "desktop_candidate_id": "proreq-outbox-ack",
            "proactive_request_id": "proreq-outbox-ack",
            "desktop_action": "approve_qq",
        },
    )
    message_id = str(queued["message_id"])
    _write(
        tmp_path / "memory/context/proactive_request_state.md",
        f"""
        ---
        title: Proactive Request State
        updated_at: 2026-05-27T17:10:00+08:00
        ---

        # Proactive Request State

        - request_id: proreq-outbox-ack
        - created_at: 2026-05-27T17:10:00+08:00
        - status: queued_qq
        - delivery_level: queue_owner_private
        - request_answer_state: approved_qq
        - qq_outbox_message_id: {message_id}
        - adapter_message_id: {message_id}
        - last_ack_status: queued
        - adapter_error: none
        """,
    )

    claim = claim_next_qq_outbox_message(tmp_path, {"claim_id": "claim-outbox-1"})
    ack = ack_qq_outbox_message(
        tmp_path,
        {
            "message_id": message_id,
            "claim_id": claim["claim_id"],
            "ack_status": "sent",
            "adapter_message_id": "adapter-msg-1",
        },
    )

    state = (tmp_path / "memory/context/proactive_request_state.md").read_text(encoding="utf-8")
    assert ack["ack_recorded"] is True
    assert "proactive_request_state_updated" in ack["notes"]
    assert "- status: sent" in state
    assert "- request_answer_state: sent_waiting_owner_reply" in state
    assert "- last_ack_status: sent" in state
    assert "- last_acked_at:" in state
    assert "- adapter_message_id: adapter-msg-1" in state
    assert raw_outbox_message not in state


def test_proactive_response_diagnostics_reports_waiting_and_timeout_without_raw_text(tmp_path: Path) -> None:
    raw_question = "RAW_PROACTIVE_QUESTION_SHOULD_NOT_SURFACE_8125"
    _write(
        tmp_path / "memory/context/proactive_request_state.md",
        f"""
        ---
        title: Proactive Request State
        updated_at: 2026-05-27T10:00:00+08:00
        ---

        # Proactive Request State

        - request_id: proreq-timeout
        - thread_id: prothread-timeout
        - created_at: 2026-05-27T09:55:00+08:00
        - status: sent
        - delivery_level: queue_owner_private
        - concrete_question: {raw_question}
        - request_answer_state: sent_waiting_owner_reply
        - last_ack_status: sent
        - last_acked_at: 2026-05-27T10:00:00+08:00
        - adapter_error: none
        """,
    )

    waiting = build_proactive_response_diagnostics(tmp_path, generated_at="2026-05-27T11:00:00+08:00")
    timeout = build_proactive_response_diagnostics(tmp_path, generated_at="2026-05-27T13:01:00+08:00")
    write_proactive_response_diagnostics(tmp_path, timeout)

    state = (tmp_path / "memory/context/proactive_response_diagnostics_state.md").read_text(encoding="utf-8")
    trace = (tmp_path / "runtime/proactive_response_diagnostics_trace.jsonl").read_text(encoding="utf-8")
    report = (tmp_path / "worklog/xinyu-proactive-response-diagnostics-latest.md").read_text(encoding="utf-8")

    assert waiting["status"] == "waiting"
    assert waiting["response_signal_candidate"] == "waiting_owner_response"
    assert waiting["minutes_until_no_response_timeout"] == "120"
    assert timeout["status"] == "timeout_active"
    assert timeout["response_signal_candidate"] == "owner_no_response_timeout"
    assert timeout["timeout_active"] is True
    assert raw_question not in state
    assert raw_question not in trace
    assert raw_question not in report


@pytest.mark.asyncio
async def test_desktop_approve_qq_enqueue_failure_is_written_to_request_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_id = "proreq-desktop-fail"
    _write(
        tmp_path / "memory/context/proactive_request_state.md",
        f"""
        ---
        title: Proactive Request State
        updated_at: 2026-05-27T17:20:00+08:00
        ---

        # Proactive Request State

        - request_id: {candidate_id}
        - created_at: 2026-05-27T17:20:00+08:00
        - status: ready
        - delivery_level: queue_owner_private
        - request_answer_state: not_requested
        - last_ack_status: none
        - adapter_error: none
        """,
    )

    def fake_update(**kwargs: Any) -> dict[str, Any]:
        path = tmp_path / "memory/context/proactive_request_state.md"
        state = path.read_text(encoding="utf-8")
        for field in ("status", "request_answer_state", "last_ack_status", "adapter_error"):
            value = kwargs.get(
                {
                    "request_answer_state": "answer_state",
                    "last_ack_status": "ack_status",
                }.get(field, field),
                "",
            )
            if value:
                state = _replace_line(state, field, str(value))
        state = _replace_line(state, "last_acked_at", "2026-05-27T17:20:05+08:00")
        path.write_text(state, encoding="utf-8")
        return {"candidateId": candidate_id, "status": kwargs.get("status", "")}

    async def fake_publish(item: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return {"id": "desktop-event-failed", "item": item, **kwargs}

    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        proactive_min_interval_seconds=0,
        _owner_private_user_id=lambda: "owner-1",
        _desktop_update_proactive_request_state=fake_update,
        _desktop_publish_proactive_delivery_item=fake_publish,
    )

    async def fake_finish(item: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return await desktop_routes.desktop_finish_proactive_ack(runtime, item, **kwargs)

    runtime._desktop_finish_proactive_ack = fake_finish
    monkeypatch.setattr(
        desktop_routes,
        "enqueue_qq_outbox_message",
        lambda *args, **kwargs: {"accepted": False, "queued": False, "notes": ["queue_lock_timeout"]},
    )

    result = await desktop_routes.desktop_approve_proactive_qq(
        runtime,
        {
            "candidateId": candidate_id,
            "requestId": candidate_id,
            "claimable": True,
            "candidatePreview": "safe candidate preview",
            "focusLabel": "safe focus",
            "whyNowPreview": "safe reason",
        },
    )

    state = (tmp_path / "memory/context/proactive_request_state.md").read_text(encoding="utf-8")
    assert result["accepted"] is False
    assert result["ack_recorded"] is True
    assert result["status"] == "failed"
    assert "- status: failed" in state
    assert "- request_answer_state: qq_enqueue_failed" in state
    assert "- last_ack_status: failed" in state
    assert "- adapter_error: desktop_qq_enqueue_failed;queue_lock_timeout" in state
