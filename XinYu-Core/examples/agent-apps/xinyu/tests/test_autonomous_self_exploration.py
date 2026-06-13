from __future__ import annotations

import json
from pathlib import Path

from xinyu_autonomous_self_exploration import STATE_REL, TRACE_REL, run_autonomous_self_exploration_tick
from xinyu_self_chosen_goal_ecology import run_self_chosen_goal_ecology


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _seed_compile_targets(root: Path) -> None:
    _write(root / "xinyu_self_chosen_goal_ecology.py", "def ok():\n    return 'goal'\n")
    _write(root / "xinyu_goal_outcome_observer.py", "def ok():\n    return 'observer'\n")
    _write(root / "xinyu_self_action_gateway.py", "def ok():\n    return 'action'\n")
    _write(root / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    run_self_chosen_goal_ecology(root, checked_at="2026-06-01T09:58:00+08:00", trigger="test")


def _seed_source_handoff(root: Path, *, grant: bool = True, source_collect: bool = True) -> None:
    grants = []
    if grant:
        grants.append(
            "- grant_autonomous_self_exploration_tick: approved_low_frequency_local_readonly_and_source_handoff"
        )
    if source_collect:
        grants.append("- grant_autonomous_source_collect: approved_bounded_candidate_material_only")
    _write(root / "memory/context/owner_permission_grants.md", "\n".join(grants) + "\n")
    _write(
        root / "memory/context/capability_zones_state.md",
        "- autonomous_search_provider: enabled_duckduckgo_html_bounded_ai_domain\n",
    )
    _write(
        root / "memory/context/self_thought_state.md",
        """# Self Thought State

## Research Handoff
- research_needed: true
- route: source_search_provider
- handoff_target: source_search_provider_bridge
- source_request_id: request-2026-06-01-001
- question_id: q-001
- target: ai-self-understanding
- query: language agent memory context reliable source
- execution_ceiling: candidate_urls_only_existing_source_gates
- codex_launch_permission: not_needed_source_pipeline_first
- memory_boundary: candidate_results_only_no_stable_memory_without_gates
""",
    )
    _write(
        root / "memory/knowledge/source_integration_gate_state.md",
        """# Source Integration Gate State

## Gate Decision
- integration_permission: prepare_only
- gate_reason: test_source_handoff
""",
    )
    _write(
        root / "memory/knowledge/source_requests.md",
        """# Source Requests

## request-2026-06-01-001
- question_id: q-001
- target: ai-self-understanding
- query: language agent memory context reliable source
- url: none
- status: pending_url
- source_policy: controlled_fetch_only
- planned_at: 2026-06-01T09:55:00+08:00
- reason: test source handoff
""",
    )
    _write(
        root / "memory/knowledge/source_search_results.md",
        """# Source Search Results

## result-none
- request_id: none
- question_id: none
- url: none
- status: hold
""",
    )
    _write(
        root / "memory/knowledge/learning_quality_state.md",
        """# Learning Quality State

## Last Evaluation
- quality_grade: stable
- learned_entries: 0
- warning_count: 0
""",
    )


def _seed_codex_handoff(root: Path, *, codex_grant: bool) -> None:
    grants = [
        "- grant_autonomous_self_exploration_tick: approved_low_frequency_local_readonly_and_source_handoff",
    ]
    if codex_grant:
        grants.append("- grant_autonomous_codex_research_collect: approved_visible_bounded_report_only")
    _write(root / "memory/context/owner_permission_grants.md", "\n".join(grants) + "\n")
    _write(
        root / "memory/context/self_thought_state.md",
        """# Self Thought State

## Research Handoff
- research_needed: true
- route: codex_delegate_candidate
- handoff_target: codex_delegate_candidate
- source_request_id: request-2026-06-01-codex
- question_id: q-codex
- target: local-project-runtime
- query: inspect local runtime gap without rewriting memory
- execution_ceiling: bounded_codex_report_only_no_memory_write
- codex_launch_permission: requires_owner_private_or_explicit_grant
- memory_boundary: candidate_results_only_no_stable_memory_without_gates
""",
    )


def test_autonomous_self_exploration_requires_grant(tmp_path: Path) -> None:
    _seed_compile_targets(tmp_path)
    _seed_source_handoff(tmp_path, grant=False, source_collect=True)

    result = run_autonomous_self_exploration_tick(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        allow_live_search=False,
    )

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    assert result["status"] == "blocked"
    assert "self_exploration_grant_missing" in result["policy"]["blocks"]
    assert "allowed: false" in state
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_autonomous_self_exploration_runs_local_probe_and_source_activation(tmp_path: Path) -> None:
    _seed_compile_targets(tmp_path)
    _seed_source_handoff(tmp_path, grant=True, source_collect=True)
    _write(tmp_path / "memory/self/core.md", "stable self")

    result = run_autonomous_self_exploration_tick(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        allow_live_search=False,
    )

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    trace = json.loads((tmp_path / TRACE_REL).read_text(encoding="utf-8").splitlines()[-1])

    assert result["status"] == "activation_ready"
    assert result["local_probe_executed_action_count"] == 1
    assert result["local_probe_queued_approval_count"] == 1
    assert result["research_route"] == "source_search_provider"
    assert result["research_execution_level"] == "activate"
    assert result["activation_permission"] == "provider_allowed"
    assert "no_qq_message_from_self_exploration: true" in state
    assert "no_stable_memory_write: true" in state
    assert trace["research_status"] == "activation_ready"
    assert (tmp_path / "memory/self/core.md").read_text(encoding="utf-8") == "stable self\n"
    assert not (tmp_path / "memory/context/qq_outbox_queue.json").exists()


def test_autonomous_self_exploration_keeps_source_search_gated_without_source_grant(tmp_path: Path) -> None:
    _seed_compile_targets(tmp_path)
    _seed_source_handoff(tmp_path, grant=True, source_collect=False)

    result = run_autonomous_self_exploration_tick(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        allow_live_search=None,
    )

    assert result["status"] == "waiting_activation"
    assert result["research_execution_level"] == "activate"
    assert result["activation_permission"] == "disabled"
    assert result["provider_results"] == 0


def test_autonomous_self_exploration_codex_route_needs_explicit_grant(tmp_path: Path) -> None:
    _seed_compile_targets(tmp_path)
    _seed_codex_handoff(tmp_path, codex_grant=False)

    result = run_autonomous_self_exploration_tick(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        allow_codex=False,
    )

    assert result["status"] == "codex_blocked"
    assert result["research_execution_level"] == "state_only"
    assert result["codex_allowed"] is False


def test_autonomous_self_exploration_codex_route_accepts_explicit_grant_without_launch_when_disabled(
    tmp_path: Path,
) -> None:
    _seed_compile_targets(tmp_path)
    _seed_codex_handoff(tmp_path, codex_grant=True)

    result = run_autonomous_self_exploration_tick(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        allow_codex=False,
    )

    research_state = (tmp_path / "memory/context/research_handoff_state.md").read_text(encoding="utf-8")
    assert result["status"] == "codex_candidate"
    assert result["research_execution_level"] == "state_only"
    assert result["codex_allowed"] is False
    assert "codex_explicit_grant: true" in research_state


def test_autonomous_self_exploration_codex_auto_launch_uses_cooldown(tmp_path: Path) -> None:
    _seed_compile_targets(tmp_path)
    _seed_codex_handoff(tmp_path, codex_grant=True)
    _write(
        tmp_path / TRACE_REL,
        json.dumps(
            {
                "event_kind": "autonomous_self_exploration",
                "evaluated_at": "2026-06-01T09:30:00+08:00",
                "research_execution_level": "execute_codex",
            }
        ),
    )

    result = run_autonomous_self_exploration_tick(
        tmp_path,
        evaluated_at="2026-06-01T10:00:00+08:00",
        codex_min_interval_seconds=21600,
    )

    assert result["status"] == "codex_candidate"
    assert result["research_execution_level"] == "state_only"
    assert result["codex_allowed"] is False
    assert result["codex_cooldown_active"] is True
