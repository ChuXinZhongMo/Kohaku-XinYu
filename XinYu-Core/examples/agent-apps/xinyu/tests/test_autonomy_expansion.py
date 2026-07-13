from __future__ import annotations

import json
from pathlib import Path

import pytest

import xinyu_self_action_patch_executor
from xinyu_autonomy_policy import (
    POLICY_REL as AUTONOMY_POLICY_REL,
    reliability_budget_bonus,
)
from xinyu_self_action_gateway import run_self_action_gateway
from xinyu_self_action_trusted_autoapproval import (
    POLICY_REL as TRUSTED_POLICY_REL,
    TrustedAutoApprovalPolicy,
    scope_is_auto_approvable,
    scope_is_codex_auto_runnable,
)
from xinyu_self_chosen_goal_ecology import (
    build_self_chosen_goal_decision,
    record_self_chosen_goal_outcome,
    run_self_chosen_goal_ecology,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, obj: object) -> None:
    _write(path, json.dumps(obj, ensure_ascii=False))


def _seed_bounded_work(root: Path) -> None:
    _write(root / "xinyu_self_chosen_goal_ecology.py", "def ok():\n    return 'g'\n")
    _write(root / "xinyu_goal_outcome_observer.py", "def ok():\n    return 'o'\n")
    _write(root / "xinyu_self_action_gateway.py", "def ok():\n    return 'a'\n")
    _write(root / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")


def _autonomy_policy(root: Path, **fields: object) -> None:
    _write_json(root / AUTONOMY_POLICY_REL, fields)


def _trusted_policy(root: Path, **fields: object) -> None:
    base = {"enabled": True}
    base.update(fields)
    _write_json(root / TRUSTED_POLICY_REL, base)


# --- #2 productive goals ----------------------------------------------------


def test_productive_goals_absent_by_default(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    decision = build_self_chosen_goal_decision(tmp_path, checked_at="2026-05-16T10:00:00+08:00")
    goal_ids = {c.goal_id for c in decision.candidates}
    assert "synthesize_knowledge" not in goal_ids
    assert "draft_self_improvement" not in goal_ids
    assert decision.selected_goal_id == "continue_bounded_work"


def test_productive_goals_appear_when_enabled_without_disturbing_selection(tmp_path: Path) -> None:
    _autonomy_policy(tmp_path, productive_goals_enabled=True)
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    decision = build_self_chosen_goal_decision(tmp_path, checked_at="2026-05-16T10:00:00+08:00")
    goal_ids = {c.goal_id for c in decision.candidates}
    assert {"synthesize_knowledge", "draft_self_improvement"} <= goal_ids
    # New goals stay below the pressured incumbent; selection is unchanged.
    assert decision.selected_goal_id == "continue_bounded_work"


# --- #1 productive low-risk + #5 multi-action -------------------------------


def test_productive_low_risk_writes_reversible_scratch_note(tmp_path: Path) -> None:
    _seed_bounded_work(tmp_path)
    _autonomy_policy(tmp_path, productive_low_risk_enabled=True, max_low_risk_actions_per_cycle=2)
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    assert result["executed_action_count"] == 2  # #5: probe + scratch reflection
    kinds = {r["action_kind"] for r in result["low_risk_results"]}
    assert "self_scratch_reflection" in kinds
    scratch = list((tmp_path / "runtime/self_scratch/continue_bounded_work").glob("*.md"))
    assert len(scratch) == 1
    body = scratch[0].read_text(encoding="utf-8")
    assert "reversible scratch artifact only" in body


def test_single_action_cap_is_unchanged_by_default(tmp_path: Path) -> None:
    _seed_bounded_work(tmp_path)
    _autonomy_policy(tmp_path, productive_low_risk_enabled=True)  # but cap stays 1
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    assert result["executed_action_count"] == 1
    assert not (tmp_path / "runtime/self_scratch").exists()


# --- #4 reliability-scaled budget -------------------------------------------


def test_reliability_bonus_grows_with_success() -> None:
    from xinyu_autonomy_policy import AutonomyPolicy

    off = AutonomyPolicy(reliability_budget_enabled=False)
    on = AutonomyPolicy(reliability_budget_enabled=True, reliability_bonus_per_success=1.0, reliability_bonus_cap=3)
    assert reliability_budget_bonus(5, off) == 0
    assert reliability_budget_bonus(2, on) == 2
    assert reliability_budget_bonus(99, on) == 3  # capped


def test_reliability_budget_unblocks_auto_approval_when_base_is_zero(tmp_path: Path) -> None:
    _seed_bounded_work(tmp_path)
    # Base window budget is 0, so without reliability nothing auto-approves.
    _trusted_policy(tmp_path, max_auto_approvals_per_window=0)
    _autonomy_policy(tmp_path, reliability_budget_enabled=True, reliability_bonus_per_success=1.0, reliability_bonus_cap=3)
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")
    record_self_chosen_goal_outcome(tmp_path, "continue_bounded_work", "success", observed_at="2026-05-16T10:00:10+08:00")
    record_self_chosen_goal_outcome(tmp_path, "continue_bounded_work", "success", observed_at="2026-05-16T10:00:20+08:00")

    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    assert result["trusted_auto_approval"]["reliability_bonus"] == 2
    assert result["auto_approved_count"] == 1


# --- #3 codex closure -------------------------------------------------------


def test_codex_auto_runnable_is_strictly_narrower_than_approval() -> None:
    policy = TrustedAutoApprovalPolicy(
        enabled=True,
        auto_run_codex=True,
        codex_eligible_scopes=frozenset({"replay_fixture_or_test_patch"}),
    )
    # focused app patch is approvable but NOT codex-auto-runnable by default.
    assert scope_is_auto_approvable("self_code_patch_request", "focused_xinyu_app_patch", policy) is True
    assert scope_is_codex_auto_runnable("self_code_patch_request", "focused_xinyu_app_patch", policy) is False
    # fixture/test patch is both.
    assert scope_is_codex_auto_runnable("self_code_patch_request", "replay_fixture_or_test_patch", policy) is True
    # outward/stable-memory can never be codex-runnable.
    assert scope_is_codex_auto_runnable("owner_message_draft_request", "owner_private_message_draft", policy) is False


def test_auto_run_codex_invokes_executor_for_eligible_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Drive goal -> curate_failure_replay -> replay_fixture_or_test_patch scope.
    _write_json(tmp_path / "runtime/replay_candidates/chat_replay_export_summary.json", {"selected_count": 3})
    _trusted_policy(
        tmp_path,
        trusted_scopes=["replay_fixture_or_test_patch"],
        auto_execute_handoff=True,
        auto_run_codex=True,
        codex_eligible_scopes=["replay_fixture_or_test_patch"],
    )
    calls: list[dict[str, object]] = []

    def _stub(root, **kwargs):  # noqa: ANN001
        calls.append(kwargs)
        return {"codex": {"status": "scheduled"}}

    monkeypatch.setattr(xinyu_self_action_patch_executor, "run_self_action_patch_executor", _stub)

    selected = run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")
    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    assert selected["selected_goal_id"] == "curate_failure_replay"
    assert result["auto_approved_count"] == 1
    assert result["trusted_auto_approval"]["auto_approved"][0]["codex_status"] == "scheduled"
    assert len(calls) == 1
    assert calls[0]["execution_level"] == "schedule_codex"
    assert calls[0]["allow_codex"] is True


def test_auto_run_codex_skipped_for_non_eligible_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_bounded_work(tmp_path)  # -> continue_bounded_work -> focused_xinyu_app_patch
    _trusted_policy(tmp_path, auto_execute_handoff=True, auto_run_codex=True)  # default codex scopes exclude focused
    calls: list[object] = []
    monkeypatch.setattr(
        xinyu_self_action_patch_executor,
        "run_self_action_patch_executor",
        lambda root, **kw: calls.append(kw) or {"codex": {"status": "scheduled"}},
    )

    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")
    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    assert result["auto_approved_count"] == 1
    assert result["trusted_auto_approval"]["auto_approved"][0]["codex_status"] is None
    assert calls == []
