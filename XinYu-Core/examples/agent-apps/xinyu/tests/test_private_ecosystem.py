from __future__ import annotations

import json
from pathlib import Path

import xinyu_private_ecosystem_grants as grants_mod
from xinyu_private_ecosystem import (
    MEMORY_CANDIDATES_REL,
    STATE_JSON_REL,
    STATE_MD_REL,
    GoalCandidate,
    _maybe_create_memory_candidate,
    build_private_ecosystem_snapshot,
    run_private_ecosystem_tick,
)
from xinyu_private_ecosystem_journal import JOURNAL_REL, read_journal_events

QQ_OUTBOX_QUEUE = Path("memory/context/qq_outbox_queue.json")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_tick_writes_journal_and_no_stable_memory_or_send(tmp_path: Path) -> None:
    result = run_private_ecosystem_tick(
        tmp_path, checked_at="2026-06-02T10:00:00+08:00", trigger="test"
    )

    assert result["ok"] is True
    assert result["selected_goal_id"] != "none"

    events = read_journal_events(tmp_path)
    kinds = {event["event_kind"] for event in events}
    assert "tick_started" in kinds
    assert "goal_selected" in kinds
    assert "action_executed" in kinds
    # No journal event may ever be a stable memory write.
    assert all(event["stable_memory_write"] is False for event in events)

    assert (tmp_path / JOURNAL_REL).exists()
    assert (tmp_path / STATE_JSON_REL).exists()
    assert (tmp_path / STATE_MD_REL).exists()

    # No stable memory layers touched, and nothing enqueued to QQ.
    assert not (tmp_path / "memory/self").exists()
    assert not (tmp_path / "memory/reflection").exists()
    assert not (tmp_path / QQ_OUTBOX_QUEUE).exists()

    snapshot = build_private_ecosystem_snapshot(tmp_path)
    assert snapshot["counters"]["low_risk_executed"] >= 1
    assert snapshot["boundaries"]["stable_memory_write"] == "blocked"


def test_tick_prepares_memory_candidate_without_stable_write(tmp_path: Path) -> None:
    # Owner config present (so a share could resolve a target), but share grant
    # is disabled by default -> any share must hold, never send.
    _write_json(tmp_path / "xinyu_qq_gateway.config.json", {"owner_user_ids": ["1001"]})
    _write(
        tmp_path / "memory/context/owner_feedback_effect_state.md",
        "- feedback_influence_count: 3\n",
    )
    # Bias goal selection toward reflect_recent_feedback.
    _write_json(
        tmp_path / STATE_JSON_REL,
        {"goals": {"reflect_recent_feedback": {"habit_weight": 0.1, "success_count": 2}}},
    )

    result = run_private_ecosystem_tick(
        tmp_path, checked_at="2026-06-02T10:00:00+08:00", trigger="test"
    )

    assert result["selected_goal_id"] == "reflect_recent_feedback"
    assert result["memory_candidate_created"] is True

    rows = [
        json.loads(line)
        for line in (tmp_path / MEMORY_CANDIDATES_REL).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    assert rows[0]["stable_memory_write_allowed"] is False
    assert rows[0]["status"] == "candidate"
    assert rows[0]["target_gate"] == "stage8_review"

    # Share held: grant disabled -> nothing queued.
    assert result["owner_private_share"]["delivery_level"] in {"hold", "none"}
    assert not (tmp_path / QQ_OUTBOX_QUEUE).exists()


def test_memory_candidate_helper_is_redacted_and_never_stable(tmp_path: Path) -> None:
    goal = GoalCandidate(
        goal_id="reflect_recent_feedback",
        label="x",
        motive="x",
        base_score=0.5,
        habit_weight=0.0,
        final_score=0.5,
        status="active",
        next_safe_action="read_state",
    )
    candidate = _maybe_create_memory_candidate(
        tmp_path,
        goal,
        {"owner_feedback_influence_count": 5, "observed_at": "2026-06-02T10:00:00+08:00"},
        checked_at="2026-06-02T10:00:00+08:00",
    )
    assert candidate is not None
    assert candidate["stable_memory_write_allowed"] is False
    assert candidate["candidate_id"].startswith("memcand-")


def test_status_exposes_private_ecosystem_check(tmp_path: Path) -> None:
    from xinyu_status import check_state, status_fields

    run_private_ecosystem_tick(tmp_path, checked_at="2026-06-02T10:00:00+08:00", trigger="test")
    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert "private_ecosystem" in checks
    assert checks["private_ecosystem"].ok is True
    assert fields["private_ecosystem_stable_memory_write"] == "blocked"
    assert fields["private_ecosystem_journal_stable_memory_write_count"] == "0"
    assert fields["private_ecosystem_qq_message_enqueued_directly"] == "false"
    assert fields["private_ecosystem_active_goal"] != "none"


def test_grants_default_safe_off(tmp_path: Path) -> None:
    grants = grants_mod.load_grants(tmp_path, env={})
    assert grants["private_ecosystem"]["enabled"] is False
    assert grants["owner_private_autonomous_share"]["enabled"] is False
    assert grants["private_browser"]["enabled"] is False
    assert grants["computer_control"]["enabled"] is False
    assert grants_mod.share_active(grants) is False
