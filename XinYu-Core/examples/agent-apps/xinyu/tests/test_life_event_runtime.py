from __future__ import annotations

import json
from pathlib import Path

from xinyu_private_ecosystem_grants import save_grants_patch
from xinyu_life_event_runtime import process_life_event


def _seed_owner_private_send_grant(root: Path) -> None:
    (root / "memory/context").mkdir(parents=True, exist_ok=True)
    save_grants_patch(root, {"owner_private_autonomous_share": {"enabled": True, "paused": False}})
    (root / "xinyu_qq_gateway.config.json").write_text('{"owner_user_ids": ["owner-1"]}', encoding="utf-8")
    (root / "memory/context/current_life_posture.md").write_text("- no_proactive_constraint: unchanged\n", encoding="utf-8")
    (root / "memory/context/owner_permission_grants.md").write_text("", encoding="utf-8")
    (root / "memory/context/capability_zones_state.md").write_text(
        "- proactive_qq_send: enabled_gated_one_short_message\n",
        encoding="utf-8",
    )


def _event(question: str, *, route: str = "owner_private_question") -> dict[str, str]:
    return {
        "event_type": "desktop_residue",
        "source": "desktop",
        "observed_at": "2026-05-24T00:20:00+08:00",
        "summary": question,
        "privacy_scope": "owner_private",
        "risk_level": "low",
        "suggested_route": route,
    }


def test_life_event_runtime_does_not_send_unless_enabled(tmp_path: Path) -> None:
    _seed_owner_private_send_grant(tmp_path)

    result = process_life_event(
        tmp_path,
        _event("要不要我把刚才的生活事件链路接到主动直发？"),
        evaluated_at="2026-05-24T00:20:00+08:00",
        allow_direct_send=False,
        min_interval_seconds=0,
    )

    assert result["self_thought_written"] is True
    assert result["direct_send"]["attempted"] is False
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_life_event_runtime_can_process_attention_to_direct_outbox_once(tmp_path: Path) -> None:
    _seed_owner_private_send_grant(tmp_path)

    result = process_life_event(
        tmp_path,
        _event("要不要我把刚才的生活事件链路接到主动直发？"),
        evaluated_at="2026-05-24T00:20:00+08:00",
        allow_direct_send=True,
        min_interval_seconds=0,
        claim_id="runtime-life-event-1",
    )

    queue = json.loads((tmp_path / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    assert result["route"] == "owner_private_question"
    assert result["direct_send"]["attempted"] is True
    assert result["direct_send"]["status"] == "queued_qq"
    assert len(queue["items"]) == 1
    # owner policy 2026-06-15 (模板静音): no mechanical "X还看吗/还要吗" check-in tic;
    # the concrete question is sent in its own words instead.
    message = queue["items"][0]["message"]
    assert message
    assert "还看吗" not in message and "还要吗" not in message


def test_life_event_runtime_refuses_generic_attention_even_when_direct_enabled(tmp_path: Path) -> None:
    _seed_owner_private_send_grant(tmp_path)

    result = process_life_event(
        tmp_path,
        _event("你在吗？"),
        evaluated_at="2026-05-24T00:20:00+08:00",
        allow_direct_send=True,
        min_interval_seconds=0,
        claim_id="runtime-life-event-generic",
    )

    assert result["route"] == "short_trace"
    assert result["self_thought_written"] is False
    assert result["direct_send"]["attempted"] is False
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_life_event_runtime_dry_run_does_not_enqueue(tmp_path: Path) -> None:
    _seed_owner_private_send_grant(tmp_path)

    result = process_life_event(
        tmp_path,
        _event("要不要我用 dry-run 检查主动事件闭环？"),
        evaluated_at="2026-05-24T00:20:00+08:00",
        allow_direct_send=True,
        min_interval_seconds=0,
        claim_id="runtime-life-event-dry",
        dry_run=True,
    )

    assert result["direct_send"]["attempted"] is True
    assert result["direct_send"]["status"] == "dry_run_claimed_not_enqueued"
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()
    dispatch = (tmp_path / "memory/context/proactive_qq_dispatch_state.md").read_text(encoding="utf-8")
    request_state = (tmp_path / "memory/context/proactive_request_state.md").read_text(encoding="utf-8")
    assert "- last_ack_status: dry_run" in dispatch
    assert "- adapter_error: none" in dispatch
    assert "- status: ready" in request_state
    assert "- request_answer_state: not_requested" in request_state
    assert "- qq_outbox_message_id: none" in request_state
