from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from xinyu_runtime_presence import (
    _render_presence_markdown,
    _render_program_awareness_markdown,
    build_runtime_presence_prompt_block,
    read_runtime_presence_summary,
    record_bridge_heartbeat,
    record_codex_presence,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _frontmatter_value(text: str, field: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{field}: "):
            return line.split(": ", 1)[1].strip()
    raise AssertionError(f"missing frontmatter field: {field}")


def test_runtime_presence_writers_default_invalid_frontmatter_time_to_iso(tmp_path: Path) -> None:
    presence = _render_presence_markdown({"updated_at": "unknown"})
    program = _render_program_awareness_markdown(tmp_path, {"updated_at": "not-a-time"})

    datetime.fromisoformat(_frontmatter_value(presence, "updated_at"))
    datetime.fromisoformat(_frontmatter_value(program, "updated_at"))
    assert "updated_at: unknown" not in presence
    assert "updated_at: not-a-time" not in program


def test_runtime_program_awareness_collects_known_subsystems(tmp_path: Path) -> None:
    _write(tmp_path / "xinyu_core_bridge.py", 'BRIDGE_VERSION = "test"')
    _write(tmp_path / "xinyu_qq_gateway.py", "GATEWAY = True")
    _write(tmp_path / "xinyu_runtime_presence.py", "PRESENCE = True")
    _write(tmp_path / "xinyu_self_chosen_goal_ecology.py", "GOAL_ECOLOGY = True")
    _write(tmp_path / "xinyu_goal_outcome_observer.py", "GOAL_OUTCOME = True")
    _write(tmp_path / "xinyu_self_action_gateway.py", "SELF_ACTION = True")
    _write(tmp_path / "xinyu_self_action_patch_executor.py", "PATCH_EXECUTOR = True")
    _write(tmp_path / "custom/learning_quality_engine.py", "QUALITY = True")
    _write(tmp_path / "xinyu_v1/app.py", "APP = True")
    _write(tmp_path / "tests/test_runtime_program_awareness.py", "def test_marker(): pass")
    _write(tmp_path / "runtime/ignored_runtime_module.py", "IGNORED = True")
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
        tmp_path / "memory/context/self_chosen_goal_ecology_state.md",
        """
        - selected_goal_id: continue_bounded_work
        - selected_label: continue bounded technical work
        - selected_score: 0.58
        - action_policy: state_only_no_outward_action
        - next_safe_action: continue the next safe local verification step
        - boundary: state_only; no outward action
        - last_observed_goal_id: continue_bounded_work
        - last_outcome: useful
        - last_reason_code: local_maintenance_completed
        - observations_24h: 1
        - goal_switch_count_24h: 0
        - cooled_goal_ids: continue_bounded_work
        """,
    )
    _write(
        tmp_path / "memory/context/self_action_gateway_state.md",
        """
        - checked_at: 2026-05-16T10:01:00+08:00
        - selected_goal_id: continue_bounded_work
        - candidate_count: 2
        - executed_action_count: 1
        - queued_approval_count: 1
        - pending_approval_count: 1
        """,
    )
    _write(
        tmp_path / "memory/context/self_action_patch_executor_state.md",
        """
        - checked_at: 2026-05-16T10:03:00+08:00
        - status: prepared
        - execution_level: prepare
        - queue_id: selfaction-approval-test
        - approval_id: selfaction-decision-test
        - task_id: selfaction-patch-test
        - codex_status: not_requested
        - report_path: none
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

        ## Latest Post Reply Observation
        - observation_kind: owner_private_reply_self_observation
        - self_state_kind: feeling_inquiry
        - alive_voice: medium
        - mechanical_risk: low
        - template_risk: medium
        - over_explained_risk: low
        - emotional_grounding: present
        - self_state_grounding: present
        - raw_text_saved: false
        - stable_personality_write: no
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
        tmp_path / "memory/context/self_code_watchdog_state.md",
        """
        - status: snapshot_created
        - snapshot_id: watchdog-test
        - approval_id: selfcode-direct-test
        - file_count: 12
        - reason: owner_self_code_iteration
        """,
    )
    _write(
        tmp_path / "memory/context/code_change_awareness_state.md",
        """
        - status: changed
        - source_changed: true
        - changed_count: 1
        - bridge_restart_required: false
        - runtime_restart_required: true
        - gateway_restart_may_be_needed: false
        - current_project_digest: code-digest-test
        - current_bridge_digest: bridge-digest-current
        - running_bridge_digest: bridge-digest-current
        - last_changed_files: modified:xinyu_speech_controller.py
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
    _write(
        tmp_path / "memory/context/contextual_self_loop_state.md",
        """
        - evaluated_at: 2026-05-13T03:00:00+08:00
        - last_trigger: renderer_memory_context
        - current_scene: memory_review
        - working_context_budget: short_memory_window
        - forgetting_posture: keep_indices_suppress_raw_history
        - retrieval_intents: memory_policy,context_horizon,recent_owner_correction,relevant_feedback_bias
        - admitted_context_count: 3
        - suppressed_context_count: 3
        - working_self: careful_context_architect
        - initiative_posture: hold_unless_owner_asks
        - next_action_bias: explain_then_ground
        - short_context_first: true
        - retrieval_before_expansion: true
        - hidden_orchestration_only: true
        """,
    )
    _write(
        tmp_path / "runtime/contextual_self_loop_trace.jsonl",
        json.dumps(
            {
                "ts": "2026-05-13T03:00:00+08:00",
                "stage": "contextual_self_loop",
                "status": "evaluated",
                "current_scene": "memory_review",
            }
        ),
    )
    _write(
        tmp_path / "memory/context/contextual_recall_state.md",
        """
        - evaluated_at: 2026-05-13T03:00:00+08:00
        - current_scene: memory_review
        - retrieval_intents: memory_policy,context_horizon,recent_owner_correction,relevant_feedback_bias
        - admitted_recall_count: 2
        - suppressed_recall_count: 1
        - source_count: 3
        - short_previews_only: true
        - raw_history_dump: blocked
        - visible_source_labels: blocked
        """,
    )
    _write(
        tmp_path / "runtime/contextual_recall_trace.jsonl",
        json.dumps(
            {
                "ts": "2026-05-13T03:00:00+08:00",
                "stage": "contextual_recall",
                "status": "evaluated",
                "current_scene": "memory_review",
                "admitted_recall_count": 2,
            }
        ),
    )
    _write(
        tmp_path / "memory/context/contextual_self_observatory_state.md",
        """
        - updated_at: 2026-05-13T03:10:00+08:00
        - window_hours: 24
        - self_loop_event_count_24h: 3
        - recall_event_count_24h: 2
        - initiative_decision_count_24h: 2
        - initiative_feedback_count_24h: 1
        - latest_scene: initiative_feedback
        - latest_working_self: restrained_initiative_operator
        - latest_initiative_posture: feedback_shaped
        - recall_admitted_count_24h: 4
        - recall_suppressed_count_24h: 1
        - latest_recall_admitted_count: 2
        - initiative_held_by_context_count_24h: 1
        - initiative_allowed_by_context_count_24h: 1
        - quiet_default_hold_count_24h: 1
        - feedback_after_context_allowed_count_24h: 1
        - posture: balanced_or_insufficient_data
        - observatory_only: true
        - behavior_change: blocked
        - raw_history_dump: blocked
        """,
    )
    _write(
        tmp_path / "memory/context/initiative_lifecycle_state.md",
        """
        - checked_at: 2026-05-13T02:00:00+08:00
        - last_trigger: autonomous_maintenance
        - candidate_count: 2
        - decision_count: 2
        - selected_candidate_id: procand-test
        - selected_source: reflection_question
        - selected_intent: ask_owner
        - selected_decision: desktop_inbox
        - selected_score: 120
        - blocked_count: 0
        - held_count: 1
        - delivery_level: desktop_inbox
        - pending_feedback_count: 1
        - interruption_posture: owner_visible_local
        - next_step: wait for owner ack before changing future initiative bias
        """,
    )
    _write(
        tmp_path / "memory/context/initiative_feedback_state.md",
        """
        - last_feedback_at: 2026-05-13T02:02:00+08:00
        - candidate_id: procand-test
        - candidate_signature: prosig-test
        - action: dismissed
        - source_type: reflection_question
        - intent_type: ask_owner
        - future_effect: lower similar future initiative priority
        - stable_memory_write: blocked
        - personality_promotion: blocked
        - scoring_bias_only: true
        """,
    )
    _write(
        tmp_path / "memory/context/early_visible_segment_shadow_state.md",
        """
        - status: shadow_observing
        - checked_at: 2026-05-23T00:03:00+08:00
        - latest_status: accepted_shadow
        - window_rows: 5
        - eligible_count: 4
        - accepted_shadow_count: 3
        - rejected_shadow_count: 1
        - no_candidate_count: 0
        - not_eligible_count: 1
        - acceptance_rate_pct: 75
        - avg_elapsed_ms: 900
        - p95_elapsed_ms: 1400
        - avg_segment_chars: 18
        - top_reasons: generic_presence_or_meta_prefix:1
        - privacy_violation_count: 0
        - raw_user_text_saved: false
        - raw_segment_saved: false
        - behavior_change: none_shadow_only
        - canary_readiness: collect_more_shadow
        - next_action: collect_shadow_observations
        """,
    )
    _write(
        tmp_path / "memory/context/self_state_capsule_state.md",
        """
        ---
        updated_at: 2026-05-23T00:05:00+08:00
        status: active
        ---
        - active: true
        - query_kind: feeling_inquiry
        - posture: felt_state_from_current_context
        - recent_pressure: recent_template_voice_repair_pressure
        - runtime_feel: steady_with_recent_context
        - memory_basis: recalled_context,learning_closed_loop
        - reply_contract: one_or_two_present_tense_owner_private_sentences
        - raw_user_text_saved: false
        - raw_memory_body_saved: false
        """,
    )
    _write(
        tmp_path / "runtime/early_visible_segment_shadow.jsonl",
        json.dumps(
            {
                "event_kind": "early_visible_segment_shadow",
                "checked_at": "2026-05-23T00:03:00+08:00",
                "status": "accepted_shadow",
            }
        ),
    )
    _write(
        tmp_path / "runtime/initiative_metrics.json",
        json.dumps(
            {
                "updated_at": "2026-05-13T02:02:00+08:00",
                "window_hours": 24,
                "event_count_24h": 3,
                "decision_event_count_24h": 2,
                "candidate_seen_count_24h": 4,
                "selected_count_24h": 2,
                "desktop_shown_count_24h": 1,
                "held_private_count_24h": 1,
                "blocked_count_24h": 0,
                "feedback_count_24h": 1,
                "dismiss_count_24h": 1,
                "reply_count_24h": 0,
                "approved_qq_count_24h": 0,
                "failed_count_24h": 0,
                "pending_feedback_count": 0,
            }
        ),
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

    block = build_runtime_presence_prompt_block(tmp_path, limit=11000)
    summary = read_runtime_presence_summary(tmp_path)

    assert "program_awareness:" in block
    assert "code_grasp_rule:" in block
    assert "code_surface:" in block
    assert "major_entrypoints=xinyu_core_bridge.py,xinyu_qq_gateway.py,xinyu_runtime_presence.py" in block
    assert "ordinary_chat_rule:" in block
    assert "visibility_rule:" in block
    assert "autonomous_loop:" in block
    assert "self_thought:" in block
    assert "candidate_enabled=true" in block
    assert "self_chosen_goal_ecology:" in block
    assert "selected_goal_id=continue_bounded_work" in block
    assert "last_outcome=useful" in block
    assert "self_action_gateway:" in block
    assert "executed_action_count=1" in block
    assert "queued_approval_count=1" in block
    assert "self_action_patch_executor:" in block
    assert "task_id=selfaction-patch-test" in block
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
    assert "post_reply_self_observation:" in block
    assert "observation_kind=owner_private_reply_self_observation" in block
    assert "raw_text_saved=false" in block
    assert "stable_personality_write=no" in block
    assert "learning_closed_loop:" in block
    assert "latest_failure_kind=owner_reported_template_voice_failure" in block
    assert "self_code_watchdog:" in block
    assert "snapshot_id=watchdog-test" in block
    assert "code_awareness:" in block
    assert "runtime_restart_required=true" in block
    assert "runtime_bridge:" in block
    assert "contextual_self_loop:" in block
    assert "current_scene=memory_review" in block
    assert "contextual_recall:" in block
    assert "admitted_recall_count=2" in block
    assert "contextual_self_observatory:" in block
    assert "initiative_held_by_context_count_24h=1" in block
    assert "initiative_lifecycle:" in block
    assert "selected_decision=desktop_inbox" in block
    assert "initiative_metrics:" in block
    assert "desktop_shown_count_24h=1" in block
    assert "feedback_count_24h=1" in block
    assert "initiative_feedback:" in block
    assert "future_effect=lower similar future initiative priority" in block
    assert "early_visible_segment_shadow:" in block
    assert "accepted_shadow_count=3" in block
    assert "behavior_change=none_shadow_only" in block
    assert "self_state_capsule:" in block
    assert "query_kind=feeling_inquiry" in block
    assert "raw_user_text_saved=false" in block
    assert "[local-path]" not in block

    awareness = summary["program_awareness"]
    code_surface = awareness["code_surface"]
    assert code_surface["python_files"] == "10"
    assert code_surface["root_modules"] == "7"
    assert code_surface["custom_modules"] == "1"
    assert code_surface["v1_modules"] == "1"
    assert code_surface["test_files"] == "1"
    assert code_surface["needs_file_open_for_details"] == "true"
    assert "xinyu_core_bridge.py" in code_surface["major_entrypoints"]
    assert awareness["observed_subsystem_count"] >= 8
    assert awareness["subsystems"]["self_thought"]["status"] == "candidate"
    assert awareness["subsystems"]["self_chosen_goal_ecology"]["selected_goal_id"] == "continue_bounded_work"
    assert awareness["subsystems"]["self_chosen_goal_ecology"]["last_outcome"] == "useful"
    assert awareness["subsystems"]["self_action_gateway"]["executed_action_count"] == "1"
    assert awareness["subsystems"]["self_action_gateway"]["queued_approval_count"] == "1"
    assert awareness["subsystems"]["self_action_patch_executor"]["task_id"] == "selfaction-patch-test"
    assert awareness["subsystems"]["self_action_patch_executor"]["codex_status"] == "not_requested"
    assert awareness["subsystems"]["interaction_journal"]["last_source"] == "owner_private"
    assert awareness["subsystems"]["personality_self_review"]["autonomy_level"] == "self_can_continue_trial"
    assert awareness["subsystems"]["persona_feedback"]["promotion_signal"] == "false"
    assert awareness["subsystems"]["expression_self_learning"]["source_request_id"] == "request-2026-05-02-expr-001"
    assert awareness["subsystems"]["post_reply_self_observation"]["alive_voice"] == "medium"
    assert awareness["subsystems"]["post_reply_self_observation"]["stable_personality_write"] == "no"
    assert awareness["subsystems"]["learning_closed_loop"]["repair_count"] == "2"
    assert awareness["subsystems"]["qq_outbox"]["queued_count"] == "1"
    assert awareness["subsystems"]["codex_delegate"]["status"] == "running"
    assert awareness["subsystems"]["self_code_watchdog"]["snapshot_id"] == "watchdog-test"
    assert awareness["subsystems"]["code_awareness"]["runtime_restart_required"] == "true"
    assert awareness["subsystems"]["watched_source"]["source_id"] == "linux-do-latest"
    assert awareness["subsystems"]["watched_source"]["filter_topic"] == "ai_related"
    assert awareness["subsystems"]["memory_self_review"]["owner_review_required"] == "1"
    assert awareness["subsystems"]["memory_self_review"]["stable_memory_write"] == "blocked"
    assert awareness["subsystems"]["contextual_self_loop"]["current_scene"] == "memory_review"
    assert awareness["subsystems"]["contextual_self_loop"]["working_self"] == "careful_context_architect"
    assert awareness["subsystems"]["contextual_recall"]["admitted_recall_count"] == "2"
    assert awareness["subsystems"]["contextual_recall"]["raw_history_dump"] == "blocked"
    assert awareness["subsystems"]["contextual_self_observatory"]["latest_scene"] == "initiative_feedback"
    assert awareness["subsystems"]["contextual_self_observatory"]["observatory_only"] == "true"
    assert awareness["subsystems"]["initiative_lifecycle"]["selected_decision"] == "desktop_inbox"
    assert awareness["subsystems"]["initiative_metrics"]["desktop_shown_count_24h"] == "1"
    assert awareness["subsystems"]["initiative_metrics"]["feedback_count_24h"] == "1"
    assert awareness["subsystems"]["initiative_feedback"]["scoring_bias_only"] == "true"
    assert awareness["subsystems"]["early_visible_segment_shadow"]["accepted_shadow_count"] == "3"
    assert awareness["subsystems"]["early_visible_segment_shadow"]["behavior_change"] == "none_shadow_only"
    assert awareness["subsystems"]["self_state_capsule"]["query_kind"] == "feeling_inquiry"
    assert awareness["subsystems"]["self_state_capsule"]["raw_user_text_saved"] == "false"
    assert awareness["traces"]["early_visible_segment_shadow"]["last_event_kind"] == "early_visible_segment_shadow"
    assert summary["initiative_lifecycle"]["pending_feedback_count"] == "1"
    assert summary["contextual_self_loop"]["initiative_posture"] == "hold_unless_owner_asks"
    assert summary["contextual_recall"]["admitted_recall_count"] == "2"
    assert summary["contextual_self_observatory"]["initiative_allowed_by_context_count_24h"] == "1"
    assert summary["initiative_metrics"]["pending_feedback_count"] == "0"
    assert (tmp_path / "memory/context/runtime_program_awareness.md").exists()


def test_stale_codex_running_presence_reports_timed_out(tmp_path: Path) -> None:
    (tmp_path / "runtime").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/codex_presence_state.json").write_text(
        json.dumps(
            {
                "updated_at": "2026-01-01T00:00:00+08:00",
                "status": "running",
                "job_id": "codex-stale",
                "visible_window_title": "Xinyu codex",
                "request_label": "codex-stale.md",
                "report_label": "codex-stale-report.md",
                "timed_out": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = read_runtime_presence_summary(tmp_path)

    assert summary["codex_status"] == "timed_out"
    assert summary["program_awareness"]["subsystems"]["codex_delegate"]["status"] == "timed_out"
    assert summary["program_awareness"]["subsystems"]["codex_delegate"]["timed_out"] == "true"
    assert summary["program_awareness"]["subsystems"]["codex_delegate"]["updated_at"] == "2026-01-01T00:00:00+08:00"


def test_qq_outbox_stale_dead_count_is_not_known_error(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/qq_outbox_dispatch_state.md",
        """
        - last_event: claim_empty
        - queued_count: 0
        - claimed_count: 0
        - sent_count: 1
        - failed_count: 0
        - dead_count: 1
        - last_failed_at: none
        - last_dead_at: 2000-01-01T00:00:00+08:00
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
                    {"status": "sent", "updated_at": "2026-05-02T00:10:00+08:00"},
                    {"status": "dead", "updated_at": "2000-01-01T00:00:00+08:00"},
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = read_runtime_presence_summary(tmp_path)
    qq_outbox = summary["program_awareness"]["subsystems"]["qq_outbox"]

    assert qq_outbox["dead_count"] == "1"
    assert qq_outbox["recent_dead_count"] == "0"
    assert qq_outbox["last_dead_at"] == "2000-01-01T00:00:00+08:00"
    assert "qq_outbox.dead_count=1" not in summary["program_awareness"]["known_errors"]
    assert "qq_outbox.recent_dead_count=1" not in summary["program_awareness"]["known_errors"]


def test_dry_run_not_enqueued_is_not_known_adapter_error(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/proactive_qq_dispatch_state.md",
        """
        - last_claim_status: failed
        - last_ack_status: failed
        - last_acked_at: 2026-05-24T01:15:00+08:00
        - adapter_error: dry_run_not_enqueued
        - min_interval_seconds: 0
        """,
    )

    summary = read_runtime_presence_summary(tmp_path)

    assert "proactive_dispatch.adapter_error=dry_run_not_enqueued" not in summary["program_awareness"]["known_errors"]
