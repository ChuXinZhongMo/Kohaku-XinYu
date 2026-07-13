from __future__ import annotations

import json
from pathlib import Path

from xinyu_self_action_gateway import (
    APPROVAL_QUEUE_REL,
    STATE_JSON_REL,
    list_self_action_approvals,
    run_self_action_gateway,
)
from xinyu_self_action_trusted_autoapproval import (
    NEVER_AUTO_APPROVE_ACTION_KINDS,
    POLICY_REL,
    load_policy,
    prune_ledger,
    scope_is_auto_approvable,
    write_example_policy,
)
from xinyu_self_chosen_goal_ecology import run_self_chosen_goal_ecology


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _seed_bounded_work(root: Path) -> None:
    # Drives goal selection to "continue_bounded_work" -> self_code_patch_request /
    # focused_xinyu_app_patch, which is a default trusted scope.
    _write(root / "xinyu_self_chosen_goal_ecology.py", "def ok():\n    return 'goal'\n")
    _write(root / "xinyu_goal_outcome_observer.py", "def ok():\n    return 'observer'\n")
    _write(root / "xinyu_self_action_gateway.py", "def ok():\n    return 'action'\n")
    _write(root / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")


def _write_policy(root: Path, **overrides: object) -> None:
    policy = {
        "enabled": True,
        "trusted_scopes": ["focused_xinyu_app_patch", "replay_fixture_or_test_patch"],
        "trusted_action_kinds": ["self_code_patch_request"],
        "max_auto_approvals_per_window": 3,
        "window_hours": 24,
        "auto_execute_handoff": True,
    }
    policy.update(overrides)
    _write(root / POLICY_REL, json.dumps(policy, ensure_ascii=False))


# --- policy unit behavior ---------------------------------------------------


def test_missing_policy_is_disabled_by_default(tmp_path: Path) -> None:
    policy = load_policy(tmp_path)
    assert policy.enabled is False
    assert scope_is_auto_approvable("self_code_patch_request", "focused_xinyu_app_patch", policy) is False


def test_outward_and_stable_memory_scopes_can_never_be_auto_approved(tmp_path: Path) -> None:
    # Even if the owner explicitly lists forbidden scopes/kinds, they are stripped.
    _write_policy(
        tmp_path,
        trusted_scopes=["owner_private_message_draft", "stable_memory_or_voice_repair", "focused_xinyu_app_patch"],
        trusted_action_kinds=["owner_message_draft_request", "stable_memory_change_request", "self_code_patch_request"],
    )
    policy = load_policy(tmp_path)
    assert "owner_private_message_draft" not in policy.trusted_scopes
    assert "stable_memory_or_voice_repair" not in policy.trusted_scopes
    assert NEVER_AUTO_APPROVE_ACTION_KINDS.isdisjoint(policy.trusted_action_kinds)
    assert scope_is_auto_approvable("owner_message_draft_request", "owner_private_message_draft", policy) is False
    assert scope_is_auto_approvable("stable_memory_change_request", "stable_memory_or_voice_repair", policy) is False
    # The legitimate code-patch scope still survives.
    assert scope_is_auto_approvable("self_code_patch_request", "focused_xinyu_app_patch", policy) is True


def test_prune_ledger_drops_entries_outside_window() -> None:
    ledger = [
        {"signature": "old", "decided_at": "2026-05-15T11:00:00+08:00"},  # 25h before now
        {"signature": "fresh", "decided_at": "2026-05-16T11:30:00+08:00"},
    ]
    kept = prune_ledger(ledger, now_iso="2026-05-16T12:00:00+08:00", window_hours=24)
    signatures = {entry["signature"] for entry in kept}
    assert signatures == {"fresh"}


# --- end-to-end gateway wiring ----------------------------------------------


def test_default_gateway_run_does_not_auto_approve(tmp_path: Path) -> None:
    _seed_bounded_work(tmp_path)
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    assert result["auto_approved_count"] == 0
    assert result["trusted_auto_approval"]["enabled"] is False
    queue = _read_jsonl(tmp_path / APPROVAL_QUEUE_REL)
    assert queue[-1]["status"] == "pending_owner_approval"
    assert list_self_action_approvals(tmp_path)["approval_queue"]["pending_count"] == 1


def test_enabled_policy_auto_approves_trusted_code_patch(tmp_path: Path) -> None:
    _seed_bounded_work(tmp_path)
    _write_policy(tmp_path)
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    assert result["auto_approved_count"] == 1
    approved = result["trusted_auto_approval"]["auto_approved"][0]
    assert approved["scope"] == "focused_xinyu_app_patch"
    overview = list_self_action_approvals(tmp_path)["approval_queue"]
    assert overview["pending_count"] == 0
    assert overview["executed_count"] == 1  # auto_execute_handoff defaults on

    queue = _read_jsonl(tmp_path / APPROVAL_QUEUE_REL)
    decided = [row for row in queue if row.get("event_kind") == "self_action_approval_decided"]
    assert decided and decided[-1]["decided_by"] == "trusted_auto_approval"

    state = json.loads((tmp_path / STATE_JSON_REL).read_text(encoding="utf-8"))
    assert len(state["trusted_auto_approvals"]) == 1


def test_rate_limit_blocks_further_auto_approvals_in_window(tmp_path: Path) -> None:
    _seed_bounded_work(tmp_path)
    _write_policy(tmp_path, max_auto_approvals_per_window=1)
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")
    run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    # Force a brand-new pending candidate so dedup does not mask the rate limit:
    # clear the queued-signature memory, then re-run within the same window.
    state_path = tmp_path / STATE_JSON_REL
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["queued_signatures"] = []
    state_path.write_text(json.dumps(state), encoding="utf-8")

    second = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:05:00+08:00", trigger="test")

    assert second["auto_approved_count"] == 0
    assert second["trusted_auto_approval"]["skipped_budget"] == 1


def test_write_example_policy_is_disabled(tmp_path: Path) -> None:
    path = write_example_policy(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["enabled"] is False
    assert load_policy(tmp_path).enabled is False
