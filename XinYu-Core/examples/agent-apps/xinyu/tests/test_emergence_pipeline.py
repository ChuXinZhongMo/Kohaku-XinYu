from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_action_followup_proposals import (  # noqa: E402
    build_followup_proposals_from_audit,
    build_followup_proposals_from_replicator_pressure,
    load_followup_inbox,
    queue_followup_proposals,
    run_audit_and_queue_followups,
    update_followup_review_status,
)
from xinyu_action_openended_audit import run_audit  # noqa: E402
from xinyu_autonomy_expansion_grant import (  # noqa: E402
    GRANT_MARKER,
    autonomy_expansion_granted,
    effective_autonomy_policy,
)
from xinyu_initiative_spine import build_initiative_spine_snapshot  # noqa: E402
from xinyu_kernel_goal_bridge import kernel_goal_candidate_specs, sync_kernel_goal_signals  # noqa: E402
from xinyu_replicator_pressure_audit import assess_replicator_pressure  # noqa: E402

def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_followup_proposals_from_unhealthy_audit() -> None:
    audit = {
        "health_status": "unhealthy",
        "warnings": ["low_salience_leak:count=2:threshold=0.6", "repeated_action_theme:tool/status:count=4"],
        "top_repeated_action_themes": [{"theme": "tool/status", "count": 4}],
        "top_repeated_visible_phrases": [],
    }
    proposals = build_followup_proposals_from_audit(audit)
    assert proposals
    assert all(p.get("requires_owner") is True for p in proposals)
    assert all(p.get("domain") == "followup" for p in proposals)


def test_queue_followup_and_kernel_inbox(tmp_path: Path) -> None:
    audit = {"health_status": "watch", "warnings": ["repeated_visible_phrase:hello:count=3"], "top_repeated_action_themes": [], "top_repeated_visible_phrases": []}
    proposals = build_followup_proposals_from_audit(audit)
    queue = queue_followup_proposals(tmp_path, proposals)
    assert queue["queued_count"] >= 1
    from kernel.bridge_governance import get_kernel_review_inbox
    from kernel.self import Self

    inbox = get_kernel_review_inbox(Self(self_id="test"), tmp_path)
    assert inbox["followup_count"] >= 1
    item_id = proposals[0]["item_id"]
    updated = update_followup_review_status(tmp_path, item_id, action="approve")
    assert updated["updated"] is True
    inbox_after = get_kernel_review_inbox(Self(self_id="test"), tmp_path)
    assert inbox_after["followup_count"] == max(0, inbox["followup_count"] - 1)


def test_run_audit_and_queue_followups_writes_inbox_only(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/recent_action_experience.jsonl",
        [{"experience_id": "exp-1", "tool": "status_probe", "target_alias": "x", "result": "ok", "salience": 0.2, "summary": "low"}],
    )
    result = run_audit_and_queue_followups(tmp_path)
    assert "followup_proposals" in result
    assert (tmp_path / "runtime/kernel_followup_review_inbox.jsonl").exists()
    assert "replicator_pressure" in result


def test_replicator_alert_builds_followup_proposals() -> None:
    pressure = {
        "level": "alert",
        "score": 7,
        "signals": [
            "visible_phrase_repeat:12",
            "life_narrative_markers:3",
            "tool_call_motif:status_probe:5",
        ],
        "memory_write": False,
    }
    proposals = build_followup_proposals_from_replicator_pressure(pressure)
    assert proposals
    assert all(p.get("source") == "replicator_pressure_audit" for p in proposals)
    assert all(p.get("requires_owner") is True for p in proposals)
    assert any("replicator pressure cluster" in p.get("candidate", "") for p in proposals)
    assert any("life-narrative" in p.get("candidate", "") for p in proposals)


def test_replicator_watch_does_not_build_followup_proposals() -> None:
    pressure = {"level": "watch", "score": 4, "signals": ["top_phrase_cluster"], "memory_write": False}
    assert build_followup_proposals_from_replicator_pressure(pressure) == []


def test_replicator_alert_queues_into_kernel_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_pressure(root: Path, *, audit_result: dict | None = None) -> dict:
        return {
            "level": "alert",
            "score": 8,
            "signals": ["visible_phrase_repeat:12", "top_theme_cluster"],
            "memory_write": False,
            "action": "alert_only",
            "notes": ["replicator_pressure_read_only"],
        }

    monkeypatch.setattr("xinyu_replicator_pressure_audit.assess_replicator_pressure", fake_pressure)
    result = run_audit_and_queue_followups(tmp_path)
    assert result["replicator_followup_count"] >= 1
    assert "replicator_alert_followups:" in " ".join(result.get("notes") or [])
    repl_rows = [row for row in load_followup_inbox(tmp_path) if row.get("source") == "replicator_pressure_audit"]
    assert repl_rows
    from kernel.bridge_governance import get_kernel_review_inbox
    from kernel.self import Self

    inbox = get_kernel_review_inbox(Self(self_id="test"), tmp_path)
    repl_ids = {row["item_id"] for row in repl_rows}
    inbox_ids = {item["item_id"] for item in inbox.get("items", []) if item.get("domain") == "followup"}
    assert repl_ids & inbox_ids


def test_replicator_pressure_is_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    audit = run_audit(tmp_path)
    before = {p.name for p in tmp_path.rglob("*") if p.is_file()}
    pressure = assess_replicator_pressure(tmp_path, audit_result=audit)
    after = {p.name for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    assert pressure["memory_write"] is False
    assert pressure["level"] in {"quiet", "watch", "alert"}


def test_autonomy_expansion_grant_enables_levers(tmp_path: Path) -> None:
    grants = tmp_path / "memory/context/owner_permission_grants.md"
    grants.parent.mkdir(parents=True, exist_ok=True)
    grants.write_text(f"- {GRANT_MARKER}\n", encoding="utf-8")
    assert autonomy_expansion_granted(tmp_path) is True
    policy = effective_autonomy_policy(tmp_path)
    assert policy.productive_low_risk_enabled is True
    assert policy.reliability_budget_enabled is True
    assert policy.max_low_risk_actions_per_cycle >= 2


def test_kernel_signals_create_goal_candidates(tmp_path: Path) -> None:
    cycles = tmp_path / "memory/events/cognitive_cycle_events.jsonl"
    cycles.parent.mkdir(parents=True, exist_ok=True)
    cycles.write_text(
        json.dumps({"structural_impact": True, "reorg_mode": "fast"}) + "\n",
        encoding="utf-8",
    )
    sync_kernel_goal_signals(tmp_path, cycle_result={"structural_impact": True, "reorg_mode": "fast"})
    signals = json.loads((tmp_path / "runtime/self_chosen_goal_ecology/kernel_signals.json").read_text(encoding="utf-8"))
    specs = kernel_goal_candidate_specs({**signals, "kernel_pressure": True, "structural_impact_recent": True})
    assert any(spec["goal_id"] == "kernel_reorg_review" for spec in specs)


def test_initiative_spine_kernel_emergence_with_pressure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for rel in (
        "memory/context/self_thought_state.md",
        "memory/context/emotion_council_state.md",
        "memory/context/impulse_soup_state.md",
        "memory/context/proactive_request_state.md",
        "memory/context/proactive_decision_state.md",
        "memory/self/learning_closed_loop_state.md",
    ):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("- status: quiet\n", encoding="utf-8")

    def fake_signals(root: Path) -> dict:
        return {
            "available": True,
            "pending_review_count": 4,
            "structural_impact_recent": False,
            "slow_signal_count": 1,
            "kernel_pressure": True,
        }

    monkeypatch.setattr("xinyu_kernel_goal_bridge.read_kernel_pressure_signals", fake_signals)
    snapshot = build_initiative_spine_snapshot(tmp_path, trigger="test")
    assert snapshot.emergence_level == "kernel_review_pressure"
    assert "kernel_lane" in snapshot.prompt_block