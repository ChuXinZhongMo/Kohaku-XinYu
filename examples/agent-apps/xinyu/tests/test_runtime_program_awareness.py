from __future__ import annotations

import json
from pathlib import Path

from xinyu_runtime_presence import (
    build_runtime_presence_prompt_block,
    read_runtime_presence_summary,
    record_bridge_heartbeat,
    record_codex_presence,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_runtime_program_awareness_collects_known_subsystems(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/autonomous_mind_loop_state.md",
        """
        ---
        updated_at: 2026-05-02T00:10:00+08:00
        ---
        - status: sleeping
        - enabled: true
        - in_progress: false
        - run_count: 3
        - failure_count: 0
        - next_run_at: 2026-05-02T00:40:00+08:00
        - last_error: none
        """,
    )
    _write(
        tmp_path / "memory/context/self_thought_state.md",
        """
        - status: candidate
        - outcome: request_candidate
        - focus_kind: dream_residue
        - candidate_enabled: true
        - research_needed: false
        """,
    )
    _write(
        tmp_path / "memory/context/proactive_request_state.md",
        """
        - status: ready
        - kind: dream_share
        - delivery_level: queue_owner_private
        - request_answer_state: pending
        """,
    )
    _write(
        tmp_path / "memory/context/qq_outbox_dispatch_state.md",
        """
        - last_event: enqueue
        - queued_count: 1
        - claimed_count: 0
        - sent_count: 2
        - failed_count: 0
        - dead_count: 0
        """,
    )
    _write(
        tmp_path / "memory/context/research_handoff_state.md",
        """
        - status: none
        - research_needed: false
        - route: none
        - allow_codex: false
        - provider_results: 0
        """,
    )
    _write(
        tmp_path / "memory/context/watched_source_state.md",
        """
        - status: fetched
        - source_id: linux-do-latest
        - source_url: https://linux.do/latest
        - filter_topic: ai_related
        - scanned_items: 8
        - matched_items: 3
        - ignored_items: 5
        - fetched_items: 3
        - new_items: 2
        - latest_title: Agent topic
        - read_only: true
        - no_posting: true
        """,
    )
    _write(
        tmp_path / "memory/context/memory_self_review_state.md",
        """
        - status: reviewed
        - pending_seen: 4
        - reviewed_candidates: 4
        - self_approved: 2
        - observe_more: 1
        - owner_review_required: 1
        - blocked: 0
        - latest_decision: self_approved_recent_context
        - latest_action: keep_as_recent_project_continuity
        - stable_memory_write: blocked
        - owner_bulk_review_required: false
        """,
    )
    _write(
        tmp_path / "memory/context/inner_cycle_state.md",
        """
        - checked_at: 2026-05-02T00:09:00+08:00
        - initiative_decision: defer
        - source_ready_requests: 6
        - search_accepted_results: 3
        - learning_quality_grade: review_needed
        - archive_next_action: keep_holding
        """,
    )
    _write(
        tmp_path / "memory/context/interaction_journal_state.md",
        """
        - last_interaction_at: 2026-05-02T00:12:00+08:00
        - last_source: owner_private
        - last_topic: runtime_self_awareness
        - last_turn_kind: ordinary_owner_chat
        - last_reply_elapsed_ms: 1200
        - last_user_summary: 你怎么看自己的运行状态
        - last_reply_summary: 我需要交互日志和心跳。
        - minutes_since_last_owner_private: 0
        - recent_interaction_count: 3
        """,
    )
    _write(
        tmp_path / "memory/self/personality_self_review_state.md",
        """
        - decision: continue_trial
        - action: keep_runtime_trial_only
        - autonomy_level: self_can_continue_trial
        - profile_changed: false
        - candidate_theme: style repair after repeated owner pressure
        - active_trial_habit: replace_explanations_with_one_concrete_owner-facing_line_under_style_pressure
        """,
    )
    _write(
        tmp_path / "memory/self/private_thought_feedback_state.md",
        """
        - status: evaluated
        - outcome: no_strong_mismatch
        - persona_trial_feedback: weak_acceptance_continue
        - promotion_signal: false
        - repair_signal: false
        - feedback_confidence: 42
        """,
    )
    _write(
        tmp_path / "memory/self/expression_self_learning_state.md",
        """
        ---
        updated_at: 2026-05-02T00:13:00+08:00
        status: active
        ---
        - failure_kind: visible_mechanism_or_template_leak
        - source_request_id: request-2026-05-02-expr-001
        - search_status: pending_url_or_provider_collection
        - learning_goal: avoid fake tool posture and fixed fallback templates
        - visible_reply_policy: do not send pseudo tools, file names, or fixed apology templates to owner-private chat.
        - repair_policy: retry the reply as live speech; if retry still leaks mechanism, send no visible reply rather than a canned fallback.
        """,
    )
    _write(
        tmp_path / "memory/self/learning_closed_loop_state.md",
        """
        ---
        updated_at: 2026-05-02T00:14:00+08:00
        status: active
        ---
        - status: trial_active
        - latest_failure_kind: owner_reported_template_voice_failure
        - active_trial_habit: direct next concrete line under style pressure
        - expected_next_behavior: avoid postmortem and fixed apology
        - next_action: apply_trial_habit_on_similar_turn
        - repair_count: 2
        - success_count: 1
        - success_streak: 1
        - promotion_signal: false
        - self_thought_memory_route: self_thought_to_proactive_request_memory
        """,
    )
    _write(
        tmp_path / "memory/context/runtime_bridge_state.md",
        """
        - evaluated_at: 2026-05-02T00:08:00+08:00
        - ready_source_requests: 9
        - pending_source_requests: 0
        - autonomous_search_permission: provider_allowed
        - learning_quality_grade: review_needed
        """,
    )
    queue_path = tmp_path / "memory/context/qq_outbox_queue.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            {
                "version": 1,
                "updated_at": "2026-05-02T00:11:00+08:00",
                "items": [
                    {"status": "queued"},
                    {"status": "sent"},
                ],
            }
        ),
        encoding="utf-8",
    )

    record_bridge_heartbeat(
        tmp_path,
        reason="test",
        bridge_snapshot={
            "active_sessions": 2,
            "autonomous_maintenance": "idle",
            "qq_outbox": "pending",
        },
    )
    record_codex_presence(
        tmp_path,
        job_id="job-1",
        status="running",
        request_path="D:/secret/request.md",
        report_path="D:/secret/report.md",
        visible_window_title="Xinyu codex",
    )

    block = build_runtime_presence_prompt_block(tmp_path, limit=6000)
    summary = read_runtime_presence_summary(tmp_path)

    assert "program_awareness:" in block
    assert "ordinary_chat_rule:" in block
    assert "visibility_rule:" in block
    assert "autonomous_loop:" in block
    assert "self_thought:" in block
    assert "candidate_enabled=true" in block
    assert "proactive_request:" in block
    assert "qq_outbox:" in block
    assert "queue_items=2" in block
    assert "codex_delegate:" in block
    assert "status=running" in block
    assert "research_handoff:" in block
    assert "watched_source:" in block
    assert "source_id=linux-do-latest" in block
    assert "filter_topic=ai_related" in block
    assert "ignored_items=5" in block
    assert "memory_self_review:" in block
    assert "stable_memory_write=blocked" in block
    assert "owner_bulk_review_required=false" in block
    assert "inner_cycle:" in block
    assert "interaction_journal:" in block
    assert "last_topic=runtime_self_awareness" in block
    assert "personality_self_review:" in block
    assert "decision=continue_trial" in block
    assert "persona_feedback:" in block
    assert "persona_trial_feedback=weak_acceptance_continue" in block
    assert "expression_self_learning:" in block
    assert "failure_kind=visible_mechanism_or_template_leak" in block
    assert "learning_closed_loop:" in block
    assert "latest_failure_kind=owner_reported_template_voice_failure" in block
    assert "runtime_bridge:" in block
    assert "[local-path]" not in block

    awareness = summary["program_awareness"]
    assert awareness["observed_subsystem_count"] >= 8
    assert awareness["subsystems"]["self_thought"]["status"] == "candidate"
    assert awareness["subsystems"]["interaction_journal"]["last_source"] == "owner_private"
    assert awareness["subsystems"]["personality_self_review"]["autonomy_level"] == "self_can_continue_trial"
    assert awareness["subsystems"]["persona_feedback"]["promotion_signal"] == "false"
    assert awareness["subsystems"]["expression_self_learning"]["source_request_id"] == "request-2026-05-02-expr-001"
    assert awareness["subsystems"]["learning_closed_loop"]["repair_count"] == "2"
    assert awareness["subsystems"]["qq_outbox"]["queued_count"] == "1"
    assert awareness["subsystems"]["codex_delegate"]["status"] == "running"
    assert awareness["subsystems"]["watched_source"]["source_id"] == "linux-do-latest"
    assert awareness["subsystems"]["watched_source"]["filter_topic"] == "ai_related"
    assert awareness["subsystems"]["memory_self_review"]["owner_review_required"] == "1"
    assert awareness["subsystems"]["memory_self_review"]["stable_memory_write"] == "blocked"
    assert (tmp_path / "memory/context/runtime_program_awareness.md").exists()
