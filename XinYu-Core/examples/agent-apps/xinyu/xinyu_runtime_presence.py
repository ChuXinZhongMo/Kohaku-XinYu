from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from xinyu_qq_outbox_state import summarize_outbox_items


PRESENCE_MD_REL = Path("memory/context/runtime_self_presence.md")
PROGRAM_AWARENESS_MD_REL = Path("memory/context/runtime_program_awareness.md")
CAPABILITY_MANIFEST_MD_REL = Path("memory/context/capability_manifest_state.md")
PRESENCE_TRACE_REL = Path("runtime/self_presence_trace.jsonl")
CODEX_STATE_REL = Path("runtime/codex_presence_state.json")
INITIATIVE_METRICS_REL = Path("runtime/initiative_metrics.json")

DEFAULT_PROMPT_LIMIT = 2200
DEFAULT_PREVIEW_CHARS = 160
DEFAULT_VISIBLE_WINDOW_TITLE = "Xinyu codex"
DEFAULT_RUNNING_STALE_SECONDS = 300
CODEX_RUNNING_STALE_SECONDS = 4500

_FIELD_RE = re.compile(r"^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_FRONTMATTER_FIELD_RE = re.compile(r"^\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
_LONG_NUMERIC_ID_RE = re.compile(r"\b\d{8,}\b")
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bxinyu[_-]?(?:api[_-]?key|bridge[_-]?token)\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)

_PROGRAM_STATE_FILES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "autonomous_loop",
        "memory/context/autonomous_mind_loop_state.md",
        ("status", "enabled", "in_progress", "run_count", "failure_count", "next_run_at", "last_error"),
    ),
    (
        "self_thought",
        "memory/context/self_thought_state.md",
        (
            "status",
            "outcome",
            "focus_kind",
            "candidate_enabled",
            "research_needed",
            "route",
            "no_visible_reply",
        ),
    ),
    (
        "self_chosen_goal_ecology",
        "memory/context/self_chosen_goal_ecology_state.md",
        (
            "selected_goal_id",
            "selected_label",
            "selected_score",
            "action_policy",
            "next_safe_action",
            "boundary",
            "last_observed_goal_id",
            "last_outcome",
            "last_reason_code",
            "observations_24h",
            "goal_switch_count_24h",
            "cooled_goal_ids",
        ),
    ),
    (
        "self_action_gateway",
        "memory/context/self_action_gateway_state.md",
        (
            "checked_at",
            "selected_goal_id",
            "candidate_count",
            "executed_action_count",
            "queued_approval_count",
            "pending_approval_count",
        ),
    ),
    (
        "self_action_patch_executor",
        "memory/context/self_action_patch_executor_state.md",
        (
            "checked_at",
            "status",
            "execution_level",
            "queue_id",
            "approval_id",
            "task_id",
            "codex_status",
            "report_path",
        ),
    ),
    (
        "private_ecosystem",
        "memory/context/private_ecosystem_state.md",
        (
            "rollout_state",
            "selected_goal_id",
            "selected_action_kind",
            "last_action_status",
            "tick_count",
            "low_risk_executed_count",
            "approval_queued_count",
            "owner_private_shares_prepared",
            "owner_private_shares_sent",
            "owner_private_shares_held",
            "owner_private_share_status",
            "owner_private_share_paused",
            "stable_memory_write",
            "qq_message_enqueued_directly",
        ),
    ),
    (
        "private_desktop",
        "memory/context/private_ecosystem_desktop_state.md",
        (
            "session_id",
            "backend",
            "last_action_kind",
            "last_result",
            "last_risk",
            "actions_total",
            "actions_executed",
            "actions_blocked",
            "frame_count",
        ),
    ),
    (
        "private_owner_share",
        "memory/context/private_ecosystem_owner_share_state.md",
        (
            "enabled",
            "paused",
            "last_delivery_level",
            "last_allowed",
            "last_queued",
            "last_block_reasons",
            "daily_remaining",
            "cooldown_minutes",
            "channel",
        ),
    ),
    (
        "proactive_request",
        "memory/context/proactive_request_state.md",
        ("status", "kind", "delivery_level", "request_answer_state", "last_ack_status", "adapter_error"),
    ),
    (
        "proactive_decision_shadow",
        "memory/context/proactive_decision_state.md",
        (
            "checked_at",
            "source_type",
            "intent_type",
            "total_score",
            "recommendation",
            "preferred_channel",
            "shadow_only",
            "hard_blocks",
            "next_review_after",
        ),
    ),
    (
        "contextual_self_loop",
        "memory/context/contextual_self_loop_state.md",
        (
            "evaluated_at",
            "last_trigger",
            "current_scene",
            "working_context_budget",
            "forgetting_posture",
            "retrieval_intents",
            "admitted_context_count",
            "suppressed_context_count",
            "working_self",
            "initiative_posture",
            "next_action_bias",
            "short_context_first",
            "retrieval_before_expansion",
            "hidden_orchestration_only",
        ),
    ),
    (
        "contextual_recall",
        "memory/context/contextual_recall_state.md",
        (
            "evaluated_at",
            "current_scene",
            "retrieval_intents",
            "admitted_recall_count",
            "suppressed_recall_count",
            "source_count",
            "short_previews_only",
            "raw_history_dump",
            "visible_source_labels",
        ),
    ),
    (
        "contextual_self_observatory",
        "memory/context/contextual_self_observatory_state.md",
        (
            "updated_at",
            "window_hours",
            "self_loop_event_count_24h",
            "recall_event_count_24h",
            "initiative_decision_count_24h",
            "initiative_feedback_count_24h",
            "latest_scene",
            "latest_working_self",
            "latest_initiative_posture",
            "recall_admitted_count_24h",
            "recall_suppressed_count_24h",
            "latest_recall_admitted_count",
            "initiative_held_by_context_count_24h",
            "initiative_allowed_by_context_count_24h",
            "quiet_default_hold_count_24h",
            "feedback_after_context_allowed_count_24h",
            "posture",
            "observatory_only",
            "behavior_change",
            "raw_history_dump",
        ),
    ),
    (
        "initiative_lifecycle",
        "memory/context/initiative_lifecycle_state.md",
        (
            "checked_at",
            "last_trigger",
            "candidate_count",
            "decision_count",
            "selected_candidate_id",
            "selected_source",
            "selected_intent",
            "selected_decision",
            "selected_score",
            "blocked_count",
            "held_count",
            "delivery_level",
            "pending_feedback_count",
            "context_gate_observed",
            "context_scene",
            "context_initiative_posture",
            "context_recall_support",
            "context_gate_age_seconds",
            "context_gate_stale",
            "interruption_posture",
            "next_step",
        ),
    ),
    (
        "initiative_feedback",
        "memory/context/initiative_feedback_state.md",
        (
            "last_feedback_at",
            "candidate_id",
            "candidate_signature",
            "action",
            "source_type",
            "intent_type",
            "future_effect",
            "stable_memory_write",
            "personality_promotion",
            "scoring_bias_only",
        ),
    ),
    (
        "impulse_soup",
        "memory/context/impulse_soup_state.md",
        (
            "checked_at",
            "schema_version",
            "thoughtlet_count",
            "active_count",
            "dormant_count",
            "quarantined_count",
            "extinct_count",
            "lineage_count",
            "top_desire_shape",
            "top_energy",
            "top_action",
            "soft_active_count",
            "outward_action_allowed",
        ),
    ),
    (
        "early_visible_segment_shadow",
        "memory/context/early_visible_segment_shadow_state.md",
        (
            "status",
            "checked_at",
            "latest_status",
            "window_rows",
            "eligible_count",
            "accepted_shadow_count",
            "rejected_shadow_count",
            "no_candidate_count",
            "not_eligible_count",
            "acceptance_rate_pct",
            "avg_elapsed_ms",
            "p95_elapsed_ms",
            "avg_segment_chars",
            "top_reasons",
            "privacy_violation_count",
            "raw_user_text_saved",
            "raw_segment_saved",
            "behavior_change",
            "canary_readiness",
            "next_action",
        ),
    ),
    (
        "proactive_dispatch",
        "memory/context/proactive_qq_dispatch_state.md",
        ("last_claim_status", "last_ack_status", "last_acked_at", "adapter_error", "min_interval_seconds"),
    ),
    (
        "qq_outbox",
        "memory/context/qq_outbox_dispatch_state.md",
        (
            "last_event",
            "queued_count",
            "claimed_count",
            "sent_count",
            "failed_count",
            "dead_count",
            "recent_failed_count",
            "recent_dead_count",
            "last_failed_at",
            "last_dead_at",
        ),
    ),
    (
        "v1_canary_readiness",
        "memory/context/v1_canary_readiness_state.md",
        (
            "readiness_decision",
            "switch_permission",
            "auto_full_switch",
            "proposal_status",
            "next_action",
            "sample_window_turns",
            "error_rate",
            "route_diversity",
            "latest_error",
        ),
    ),
    (
        "research_handoff",
        "memory/context/research_handoff_state.md",
        ("status", "research_needed", "route", "allow_codex", "codex_status", "provider_results", "pending_requests"),
    ),
    (
        "watched_source",
        "memory/context/watched_source_state.md",
        (
            "status",
            "source_id",
            "filter_topic",
            "scanned_items",
            "matched_items",
            "ignored_items",
            "fetched_items",
            "new_items",
            "latest_title",
            "read_only",
            "no_posting",
        ),
    ),
    (
        "github_learning",
        "memory/context/github_learning_state.md",
        (
            "status",
            "permission_reason",
            "queries_checked",
            "candidates_found",
            "candidates_recorded",
            "staged_repos",
            "skipped_reason",
            "latest_repo",
            "public_github_only",
            "no_code_execution",
        ),
    ),
    (
        "memory_self_review",
        "memory/context/memory_self_review_state.md",
        (
            "status",
            "stable_memory_write",
            "owner_bulk_review_required",
            "pending_seen",
            "reviewed_candidates",
            "self_approved",
            "observe_more",
            "owner_review_required",
            "blocked",
            "latest_decision",
            "latest_action",
            "stable_memory_write",
            "owner_bulk_review_required",
        ),
    ),
    (
        "inner_cycle",
        "memory/context/inner_cycle_state.md",
        (
            "checked_at",
            "initiative_decision",
            "source_ready_requests",
            "search_accepted_results",
            "learning_quality_grade",
            "archive_next_action",
            "personality_gate_decision",
        ),
    ),
    (
        "interaction_journal",
        "memory/context/interaction_journal_state.md",
        (
            "status",
            "last_interaction_at",
            "last_source",
            "last_topic",
            "last_turn_kind",
            "last_reply_elapsed_ms",
            "last_user_summary",
            "last_reply_summary",
            "minutes_since_last_owner_private",
            "recent_interaction_count",
        ),
    ),
    (
        "personality_self_review",
        "memory/self/personality_self_review_state.md",
        (
            "decision",
            "action",
            "autonomy_level",
            "profile_changed",
            "candidate_theme",
            "active_trial_habit",
        ),
    ),
    (
        "persona_feedback",
        "memory/self/private_thought_feedback_state.md",
        (
            "status",
            "outcome",
            "persona_trial_feedback",
            "promotion_signal",
            "repair_signal",
            "feedback_confidence",
        ),
    ),
    (
        "expression_self_learning",
        "memory/self/expression_self_learning_state.md",
        (
            "status",
            "failure_kind",
            "source_request_id",
            "search_status",
            "learning_goal",
            "visible_reply_policy",
            "repair_policy",
        ),
    ),
    (
        "post_reply_self_observation",
        "memory/self/expression_self_learning_state.md",
        (
            "observation_kind",
            "self_state_kind",
            "alive_voice",
            "mechanical_risk",
            "template_risk",
            "over_explained_risk",
            "emotional_grounding",
            "self_state_grounding",
            "raw_text_saved",
            "stable_personality_write",
        ),
    ),
    (
        "learning_closed_loop",
        "memory/self/learning_closed_loop_state.md",
        (
            "status",
            "latest_failure_at",
            "latest_failure_kind",
            "active_trial_habit",
            "expected_next_behavior",
            "next_action",
            "repair_count",
            "success_count",
            "success_streak",
            "promotion_signal",
            "self_thought_memory_route",
            "last_learning_loop_reflected_at",
        ),
    ),
    (
        "self_state_capsule",
        "memory/context/self_state_capsule_state.md",
        (
            "active",
            "query_kind",
            "posture",
            "recent_pressure",
            "runtime_feel",
            "memory_basis",
            "reply_contract",
            "raw_user_text_saved",
            "raw_memory_body_saved",
        ),
    ),
    (
        "continuity_handoff",
        "memory/context/continuity_handoff_state.md",
        (
            "continuity_mode",
            "open_loop_count",
            "self_thought_thread",
            "proactive_thread",
            "uncertainty_pause_thread",
            "learning_thread",
        ),
    ),
    (
        "uncertainty_pause",
        "memory/context/uncertainty_pause_state.md",
        (
            "status",
            "reason",
            "owner_private",
            "followup_allowed",
            "requested_action",
            "evidence_hash",
        ),
    ),
    (
        "async_exploration",
        "memory/context/async_exploration_state.md",
        (
            "status",
            "resume_id",
            "result_quality",
            "failure_kind",
            "owner_intervention",
            "report_label",
        ),
    ),
    (
        "self_code_approval",
        "memory/context/self_code_approval_state.md",
        (
            "status",
            "approval_id",
            "owner_decision",
            "approval_scope",
            "execution_job_id",
        ),
    ),
    (
        "self_code_watchdog",
        "memory/context/self_code_watchdog_state.md",
        (
            "status",
            "snapshot_id",
            "approval_id",
            "file_count",
            "reason",
        ),
    ),
    (
        "code_awareness",
        "memory/context/code_change_awareness_state.md",
        (
            "status",
            "source_changed",
            "changed_count",
            "bridge_restart_required",
            "runtime_restart_required",
            "gateway_restart_may_be_needed",
            "last_changed_files",
        ),
    ),
    (
        "runtime_bridge",
        "memory/context/runtime_bridge_state.md",
        (
            "evaluated_at",
            "ready_source_requests",
            "pending_source_requests",
            "autonomous_search_permission",
            "learning_quality_grade",
            "archive_next_action",
        ),
    ),
    (
        "memory_gate",
        "memory/archive/long_term_memory_gate_state.md",
        ("long_term_memory_action", "long_term_forget_permission", "archive_permission", "archive_next_action"),
    ),
)

_PROGRAM_TRACE_FILES: tuple[tuple[str, str], ...] = (
    ("self_presence", "runtime/self_presence_trace.jsonl"),
    ("self_thought", "runtime/self_thought_trace.jsonl"),
    ("self_chosen_goal_ecology", "runtime/self_chosen_goal_ecology/trace.jsonl"),
    ("self_action_gateway", "runtime/self_action_gateway/trace.jsonl"),
    ("self_action_patch_executor", "runtime/self_action_patch_executor/trace.jsonl"),
    ("proactive_request", "runtime/proactive_request_trace.jsonl"),
    ("proactive_decision", "memory/context/proactive_decision_trace.jsonl"),
    ("contextual_self_loop", "runtime/contextual_self_loop_trace.jsonl"),
    ("contextual_recall", "runtime/contextual_recall_trace.jsonl"),
    ("initiative_lifecycle", "runtime/initiative_lifecycle_events.jsonl"),
    ("impulse_soup", "memory/context/impulse_soup_trace.jsonl"),
    ("early_visible_segment_shadow", "runtime/early_visible_segment_shadow.jsonl"),
    ("v1_shadow", "runtime/v1_shadow_trace.jsonl"),
    ("research_handoff", "runtime/research_handoff_trace.jsonl"),
    ("watched_source", "runtime/watched_source_trace.jsonl"),
    ("github_learning", "runtime/github_learning_trace.jsonl"),
    ("memory_self_review", "runtime/memory_self_review_trace.jsonl"),
    ("learning_extraction", "runtime/learning_extraction_trace.jsonl"),
    ("expression_self_learning", "runtime/expression_self_learning_trace.jsonl"),
    ("post_reply_self_observation", "runtime/post_reply_self_observation_trace.jsonl"),
    ("learning_closed_loop", "runtime/learning_closed_loop_trace.jsonl"),
    ("continuity_handoff", "runtime/continuity_handoff_trace.jsonl"),
    ("uncertainty_pause", "runtime/uncertainty_pause_trace.jsonl"),
    ("async_exploration", "runtime/async_exploration_trace.jsonl"),
    ("self_code_approval", "runtime/self_code_approval_trace.jsonl"),
    ("self_code_watchdog", "runtime/self_code_watchdog_trace.jsonl"),
)

_CODE_SURFACE_ENTRYPOINTS: tuple[str, ...] = (
    "xinyu_core_bridge.py",
    "xinyu_qq_gateway.py",
    "xinyu_bridge_renderer.py",
    "xinyu_runtime_presence.py",
    "xinyu_contextual_self_loop.py",
    "xinyu_contextual_recall.py",
    "xinyu_contextual_self_observatory.py",
    "xinyu_learning_closed_loop.py",
    "xinyu_post_reply_self_observation.py",
    "xinyu_self_chosen_goal_ecology.py",
    "xinyu_goal_outcome_observer.py",
    "xinyu_self_action_gateway.py",
    "xinyu_self_action_patch_executor.py",
    "xinyu_self_code_approval.py",
    "xinyu_self_code_watchdog.py",
)


def record_bridge_heartbeat(
    root: Path,
    *,
    reason: str,
    bridge_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        observed_at = _now_iso()
        snapshot = bridge_snapshot if isinstance(bridge_snapshot, dict) else {}
        fields = _load_presence_fields(root)
        fields["updated_at"] = observed_at
        fields["bridge_process"] = _scrub_field(snapshot.get("bridge_process") or "running")
        fields["heartbeat_reason"] = _scrub_field(reason or "heartbeat")
        if reason in {"bridge_init", "startup"}:
            fields["current_turn_state"] = "idle"
            fields["current_turn_started_at"] = ""
            fields["current_turn_id"] = ""
            fields["current_turn_kind"] = ""
            fields["current_turn_source"] = ""
            fields["current_turn_relation"] = ""
            fields["current_session_hash"] = ""
            fields["current_user_preview"] = ""
        if "active_sessions" in snapshot:
            fields["active_sessions"] = _safe_count(snapshot.get("active_sessions"))
        if "autonomous_maintenance" in snapshot:
            fields["autonomous_maintenance"] = _normalize_background_state(snapshot.get("autonomous_maintenance"))
        if "qq_outbox" in snapshot:
            fields["qq_outbox"] = _normalize_background_state(snapshot.get("qq_outbox"))

        write_notes = _write_presence_markdown(root, fields)
        event = {
            "event_id": _event_id("presence"),
            "event_kind": "bridge_heartbeat",
            "observed_at": _timestamp_or_now_iso(observed_at),
            "reason": _scrub_field(reason),
            "bridge_process": fields["bridge_process"],
            "active_sessions": fields.get("active_sessions", "unknown"),
            "notes": write_notes,
        }
        trace_notes = _append_trace(root, event)
        return {"ok": True, "observed_at": _timestamp_or_now_iso(observed_at), "notes": write_notes + trace_notes}
    except Exception as exc:
        return _soft_failure("bridge_heartbeat", exc)


def record_turn_started(
    root: Path,
    *,
    payload: dict[str, Any],
    text: str,
    session_key: str,
    active_sessions: int | None = None,
) -> dict[str, Any]:
    try:
        observed_at = _now_iso()
        source_channel, relation, current_turn = _classify_payload(payload)
        session_hash = _stable_hash(session_key)
        user_hash = _stable_hash(_safe_str(payload.get("user_id")))
        group_hash = _stable_hash(_safe_str(payload.get("group_id")))
        turn_id = _make_turn_id(payload, session_key)

        fields = _load_presence_fields(root)
        fields["updated_at"] = observed_at
        fields["bridge_process"] = "running"
        fields["current_turn_state"] = "running"
        fields["current_turn_started_at"] = observed_at
        fields["current_turn_id"] = turn_id
        fields["current_turn_kind"] = current_turn
        fields["current_turn_source"] = source_channel
        fields["current_turn_relation"] = relation
        fields["current_session_hash"] = session_hash
        fields["current_user_preview"] = _clip_preview(text)
        if active_sessions is not None:
            fields["active_sessions"] = _safe_count(active_sessions)

        write_notes = _write_presence_markdown(root, fields)
        event = {
            "event_id": _event_id("presence"),
            "event_kind": "turn_started",
            "observed_at": _timestamp_or_now_iso(observed_at),
            "turn_id": turn_id,
            "session_hash": session_hash,
            "user_hash": user_hash,
            "group_hash": group_hash,
            "source_channel": source_channel,
            "relation": relation,
            "text_preview": _clip_preview(text),
            "active_sessions": fields.get("active_sessions", "unknown"),
            "notes": write_notes,
        }
        trace_notes = _append_trace(root, event)
        return {
            "ok": True,
            "turn_id": turn_id,
            "observed_at": _timestamp_or_now_iso(observed_at),
            "session_hash": session_hash,
            "source_channel": source_channel,
            "relation": relation,
            "notes": write_notes + trace_notes,
        }
    except Exception as exc:
        return _soft_failure("turn_started", exc)


def record_turn_finished(
    root: Path,
    *,
    turn_id: str,
    reply: str,
    elapsed_ms: int,
    status: str,
    notes: list[str] | None = None,
    memory_changed: bool | None = None,
) -> dict[str, Any]:
    try:
        observed_at = _now_iso()
        fields = _load_presence_fields(root)
        clean_status = _normalize_turn_status(status)
        current_turn_id = _scrub_field(turn_id) or fields.get("current_turn_id", "")
        event_kind = "turn_finished" if clean_status in {"ok", "finished"} else "turn_failed"

        fields["updated_at"] = observed_at
        fields["bridge_process"] = "running"
        fields["current_turn_state"] = "finished" if clean_status in {"ok", "finished"} else clean_status
        fields["last_turn_id"] = current_turn_id
        fields["last_turn_at"] = observed_at
        fields["last_turn_status"] = clean_status
        fields["last_turn_elapsed_ms"] = _safe_count(elapsed_ms)
        fields["last_source"] = _scrub_field(fields.get("current_turn_source") or "unknown")
        fields["last_relation"] = _scrub_field(fields.get("current_turn_relation") or "unknown")
        fields["last_session_hash"] = _scrub_field(fields.get("current_session_hash") or "")
        fields["last_user_preview"] = _clip_preview(fields.get("current_user_preview") or "")
        fields["last_reply_preview"] = _clip_preview(reply)
        fields["current_turn_started_at"] = ""
        fields["current_turn_id"] = ""
        fields["current_turn_kind"] = ""
        fields["current_turn_source"] = ""
        fields["current_turn_relation"] = ""
        fields["current_session_hash"] = ""
        fields["current_user_preview"] = ""

        clean_notes = [_clip_note(note) for note in (notes or []) if _safe_str(note).strip()]
        if memory_changed is not None:
            clean_notes.append(f"memory_changed:{str(bool(memory_changed)).lower()}")
        write_notes = _write_presence_markdown(root, fields)
        event = {
            "event_id": _event_id("presence"),
            "event_kind": event_kind,
            "observed_at": _timestamp_or_now_iso(observed_at),
            "turn_id": current_turn_id,
            "session_hash": fields.get("last_session_hash", ""),
            "source_channel": fields.get("last_source", "unknown"),
            "relation": fields.get("last_relation", "unknown"),
            "status": clean_status,
            "elapsed_ms": max(0, int(elapsed_ms or 0)),
            "reply_preview": _clip_preview(reply),
            "notes": clean_notes + write_notes,
        }
        trace_notes = _append_trace(root, event)
        return {
            "ok": True,
            "observed_at": _timestamp_or_now_iso(observed_at),
            "turn_id": current_turn_id,
            "notes": write_notes + trace_notes,
        }
    except Exception as exc:
        return _soft_failure("turn_finished", exc)


def record_codex_presence(
    root: Path,
    *,
    job_id: str,
    status: str,
    report_path: str = "",
    request_path: str = "",
    exit_code: int | None = None,
    timed_out: bool = False,
    visible_window_title: str = DEFAULT_VISIBLE_WINDOW_TITLE,
) -> dict[str, Any]:
    try:
        observed_at = _now_iso()
        clean_status = _normalize_codex_status(status, timed_out=timed_out)
        request_label = _path_label(request_path)
        report_label = _path_label(report_path)
        clean_job_id = _scrub_field(job_id)
        clean_title = _scrub_field(visible_window_title or DEFAULT_VISIBLE_WINDOW_TITLE)
        state = {
            "updated_at": observed_at,
            "status": clean_status,
            "job_id": clean_job_id,
            "visible_window_title": clean_title,
            "request_label": request_label,
            "report_label": report_label,
            "exit_code": exit_code,
            "timed_out": bool(timed_out),
        }

        fields = _load_presence_fields(root)
        fields["updated_at"] = observed_at
        fields["bridge_process"] = fields.get("bridge_process") or "running"
        fields["codex_status"] = clean_status
        fields["codex_job_id"] = clean_job_id
        fields["codex_updated_at"] = observed_at
        fields["visible_window_title"] = clean_title
        fields["codex_request_label"] = request_label
        fields["codex_report_label"] = report_label
        fields["codex_exit_code"] = "" if exit_code is None else str(exit_code)
        fields["codex_timed_out"] = str(bool(timed_out)).lower()

        write_notes = _atomic_write_json(root / CODEX_STATE_REL, state)
        write_notes.extend(_write_presence_markdown(root, fields))
        event = {
            "event_id": _event_id("presence"),
            "event_kind": _codex_event_kind(clean_status),
            "observed_at": _timestamp_or_now_iso(observed_at),
            "job_id": clean_job_id,
            "status": clean_status,
            "request_label": request_label,
            "report_label": report_label,
            "exit_code": exit_code,
            "timed_out": bool(timed_out),
            "notes": write_notes,
        }
        trace_notes = _append_trace(root, event)
        return {"ok": True, "observed_at": observed_at, "status": clean_status, "notes": write_notes + trace_notes}
    except Exception as exc:
        return _soft_failure("codex_presence", exc)


def build_runtime_presence_prompt_block(root: Path, *, limit: int = DEFAULT_PROMPT_LIMIT) -> str:
    try:
        if limit <= 0:
            return ""
        fields = _load_presence_fields(root)
        if not (root / PRESENCE_MD_REL).exists() and not (root / CODEX_STATE_REL).exists():
            return ""
        codex_fields = _load_codex_fields(root)
        for key, value in codex_fields.items():
            if value and (not fields.get(key) or key.startswith("codex_") or key in {"visible_window_title"}):
                fields[key] = value

        running_age_seconds = _age_seconds(fields.get("current_turn_started_at"))
        current_turn_state = fields.get("current_turn_state") or "unknown"
        if current_turn_state == "running" and _is_stale_age(running_age_seconds):
            current_turn_state = "stale_running"
        codex_line = fields.get("codex_status", "unknown") or "unknown"
        if fields.get("codex_job_id"):
            codex_line += f" job={fields['codex_job_id']}"
        if fields.get("codex_report_label"):
            codex_line += f" report={fields['codex_report_label']}"
        if fields.get("codex_exit_code"):
            codex_line += f" exit={fields['codex_exit_code']}"
        if fields.get("codex_timed_out") == "true":
            codex_line += " timed_out=true"

        current_turn = fields.get("current_turn_kind") or current_turn_state or "unknown"
        if current_turn_state == "stale_running":
            current_turn = "stale_running"
        continuity = "active" if fields.get("last_turn_at") or fields.get("current_turn_state") == "running" else "unknown"
        if current_turn_state == "stale_running":
            continuity = "stale"
        lines = [
            f"- observed_at: {_timestamp_or_now_iso(fields.get('updated_at'))}",
            f"- bridge_process: {_scrub_field(fields.get('bridge_process') or 'unknown')}",
            f"- current_turn: {_scrub_field(current_turn)}",
            f"- current_turn_state: {_scrub_field(current_turn_state)}",
            f"- session_continuity: {continuity}",
        ]
        if current_turn_state == "stale_running" and running_age_seconds is not None:
            lines.append(f"- current_turn_age_seconds: {int(running_age_seconds)}")
        if fields.get("last_turn_at"):
            lines.append(f"- last_turn_at: {_scrub_field(fields.get('last_turn_at'))}")
        if fields.get("last_turn_elapsed_ms"):
            lines.append(f"- last_turn_elapsed_ms: {_scrub_field(fields.get('last_turn_elapsed_ms'))}")
        if fields.get("last_turn_status"):
            lines.append(f"- last_turn_status: {_scrub_field(fields.get('last_turn_status'))}")
        if fields.get("last_source"):
            lines.append(f"- last_source: {_scrub_field(fields.get('last_source'))}")
        if fields.get("last_relation"):
            lines.append(f"- last_relation: {_scrub_field(fields.get('last_relation'))}")
        if fields.get("last_session_hash"):
            lines.append(f"- last_session_hash: {_scrub_field(fields.get('last_session_hash'))}")
        code_fields = _load_markdown_state_fields(root, "memory/context/code_change_awareness_state.md")
        if code_fields.get("_exists") == "true":
            code_status = _format_subsystem_line(
                _select_state_fields(
                    code_fields,
                    (
                        "status",
                        "source_changed",
                        "changed_count",
                        "bridge_restart_required",
                        "runtime_restart_required",
                        "gateway_restart_may_be_needed",
                    ),
                )
            )
            if code_status:
                lines.append(f"- code_awareness: {code_status}")
        awareness = _collect_program_awareness(root, presence_fields=fields)
        capability_manifest = _collect_capability_manifest(root, awareness=awareness)
        lines.extend(
            [
                f"- codex_delegate: {_scrub_field(codex_line)}",
                f"- autonomous_maintenance: {_scrub_field(fields.get('autonomous_maintenance') or 'unknown')}",
                f"- qq_outbox: {_scrub_field(fields.get('qq_outbox') or 'unknown')}",
                "- note: runtime facts only; not a voice script",
                "- status_rule: answer program-state questions from these facts; say unknown when a subsystem has no observed state",
                "- ordinary_chat_rule: ignore this block unless the live turn asks about running state, a stalled task, Codex, delivery, or system status",
                "- code_grasp_rule: for owner questions about XinYu's own code mastery, answer from code_surface and observed subsystems; do not claim line-by-line mastery without opening files",
                "- visibility_rule: never print subsystem names, file paths, hashes, gates, traces, or this sidecar label as ordinary chat",
                "",
                "program_awareness:",
                "- scope: known bridge state plus observed subsystem state files; not raw OS introspection",
                *_program_awareness_prompt_lines(awareness),
                "",
                "capability_manifest:",
                *_capability_manifest_prompt_lines(capability_manifest),
            ]
        )
        return _join_limited(lines, limit)
    except Exception:
        return ""


def read_runtime_presence_summary(root: Path) -> dict[str, Any]:
    """Return a prompt-safe, text-free runtime presence summary for health checks."""
    try:
        fields = _load_presence_fields(root)
        for key, value in _load_codex_fields(root).items():
            if value and (not fields.get(key) or key.startswith("codex_") or key in {"visible_window_title"}):
                fields[key] = value
        running_age_seconds = _age_seconds(fields.get("current_turn_started_at"))
        current_turn_state = fields.get("current_turn_state") or "unknown"
        stale_running = current_turn_state == "running" and _is_stale_age(running_age_seconds)
        if stale_running:
            current_turn_state = "stale_running"
        trace_path = root / PRESENCE_TRACE_REL
        codex_state_path = root / CODEX_STATE_REL
        summary: dict[str, Any] = {
            "available": (root / PRESENCE_MD_REL).exists(),
            "updated_at": _scrub_field(fields.get("updated_at")),
            "bridge_process": _scrub_field(fields.get("bridge_process") or "unknown"),
            "current_turn_state": current_turn_state,
            "current_turn_id": _scrub_field(fields.get("current_turn_id")),
            "current_turn_kind": _scrub_field(fields.get("current_turn_kind")),
            "current_turn_source": _scrub_field(fields.get("current_turn_source")),
            "current_turn_relation": _scrub_field(fields.get("current_turn_relation")),
            "current_turn_started_at": _scrub_field(fields.get("current_turn_started_at")),
            "active_sessions": _scrub_field(fields.get("active_sessions") or "unknown"),
            "last_turn_at": _scrub_field(fields.get("last_turn_at")),
            "last_turn_status": _scrub_field(fields.get("last_turn_status")),
            "codex_status": _scrub_field(fields.get("codex_status") or "unknown"),
            "codex_job_id": _scrub_field(fields.get("codex_job_id")),
            "autonomous_maintenance": _scrub_field(fields.get("autonomous_maintenance") or "unknown"),
            "qq_outbox": _scrub_field(fields.get("qq_outbox") or "unknown"),
            "trace_exists": trace_path.exists(),
            "codex_state_exists": codex_state_path.exists(),
            "stale_running": stale_running,
        }
        summary["program_awareness"] = _collect_program_awareness(root, presence_fields=fields)
        summary["capability_manifest"] = _collect_capability_manifest(root, awareness=summary["program_awareness"])
        summary["initiative_lifecycle"] = summary["program_awareness"].get("subsystems", {}).get(
            "initiative_lifecycle",
            {},
        )
        summary["contextual_self_loop"] = summary["program_awareness"].get("subsystems", {}).get(
            "contextual_self_loop",
            {},
        )
        summary["contextual_recall"] = summary["program_awareness"].get("subsystems", {}).get(
            "contextual_recall",
            {},
        )
        summary["contextual_self_observatory"] = summary["program_awareness"].get("subsystems", {}).get(
            "contextual_self_observatory",
            {},
        )
        summary["initiative_metrics"] = summary["program_awareness"].get("subsystems", {}).get(
            "initiative_metrics",
            {},
        )
        if running_age_seconds is not None:
            summary["current_turn_age_seconds"] = int(running_age_seconds)
        try:
            summary["trace_size_bytes"] = trace_path.stat().st_size if trace_path.exists() else 0
        except OSError:
            summary["trace_size_bytes"] = "unknown"
        return summary
    except Exception as exc:
        return {
            "available": False,
            "error": type(exc).__name__,
        }


def _default_fields() -> dict[str, str]:
    return {
        "updated_at": "",
        "bridge_process": "unknown",
        "heartbeat_reason": "",
        "current_turn_state": "idle",
        "current_turn_started_at": "",
        "current_turn_id": "",
        "current_turn_kind": "",
        "current_turn_source": "",
        "current_turn_relation": "",
        "current_session_hash": "",
        "current_user_preview": "",
        "active_sessions": "unknown",
        "last_turn_id": "",
        "last_turn_at": "",
        "last_turn_status": "",
        "last_turn_elapsed_ms": "",
        "last_source": "unknown",
        "last_relation": "unknown",
        "last_session_hash": "",
        "last_user_preview": "",
        "last_reply_preview": "",
        "codex_status": "unknown",
        "codex_job_id": "",
        "visible_window_title": DEFAULT_VISIBLE_WINDOW_TITLE,
        "codex_request_label": "",
        "codex_report_label": "",
        "codex_exit_code": "",
        "codex_timed_out": "false",
        "autonomous_maintenance": "unknown",
        "qq_outbox": "unknown",
    }


def _load_presence_fields(root: Path) -> dict[str, str]:
    fields = _default_fields()
    path = root / PRESENCE_MD_REL
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return fields
    for line in text.splitlines():
        match = _FIELD_RE.match(line)
        if not match:
            match = _FRONTMATTER_FIELD_RE.match(line)
        if not match:
            continue
        key = match.group(1)
        if key in fields:
            fields[key] = _scrub_field(match.group(2))
    return fields


def _load_codex_fields(root: Path) -> dict[str, str]:
    path = root / CODEX_STATE_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    updated_at = _scrub_field(data.get("updated_at"))
    timed_out = _as_bool(data.get("timed_out"))
    codex_status = _normalize_codex_status(data.get("status"), timed_out=timed_out)
    if codex_status == "running" and _is_stale_age(
        _age_seconds(updated_at),
        threshold=CODEX_RUNNING_STALE_SECONDS,
    ):
        codex_status = "timed_out"
        timed_out = True
    return {
        "updated_at": updated_at,
        "codex_updated_at": updated_at,
        "codex_status": codex_status,
        "codex_job_id": _scrub_field(data.get("job_id")),
        "visible_window_title": _scrub_field(data.get("visible_window_title") or DEFAULT_VISIBLE_WINDOW_TITLE),
        "codex_request_label": _path_label(data.get("request_label")),
        "codex_report_label": _path_label(data.get("report_label")),
        "codex_exit_code": "" if data.get("exit_code") is None else _scrub_field(data.get("exit_code")),
        "codex_timed_out": str(timed_out).lower(),
    }


def _collect_program_awareness(root: Path, *, presence_fields: dict[str, str] | None = None) -> dict[str, Any]:
    fields = dict(presence_fields or _load_presence_fields(root))
    for key, value in _load_codex_fields(root).items():
        if value and (not fields.get(key) or key.startswith("codex_") or key in {"visible_window_title"}):
            fields[key] = value

    running_age_seconds = _age_seconds(fields.get("current_turn_started_at"))
    current_turn_state = fields.get("current_turn_state") or "unknown"
    if current_turn_state == "running" and _is_stale_age(running_age_seconds):
        current_turn_state = "stale_running"

    subsystems: dict[str, dict[str, str]] = {
        "bridge_core": {
            "observed": "true" if fields.get("bridge_process") else "false",
            "bridge_process": _scrub_field(fields.get("bridge_process") or "unknown"),
            "current_turn_state": _scrub_field(current_turn_state),
            "active_sessions": _scrub_field(fields.get("active_sessions") or "unknown"),
            "last_turn_status": _scrub_field(fields.get("last_turn_status") or "unknown"),
            "last_turn_at": _scrub_field(fields.get("last_turn_at")),
        },
        "codex_delegate": {
            "observed": "true" if (root / CODEX_STATE_REL).exists() or fields.get("codex_status") else "false",
            "status": _scrub_field(fields.get("codex_status") or "unknown"),
            "updated_at": _scrub_field(fields.get("codex_updated_at")),
            "job_id": _scrub_field(fields.get("codex_job_id")),
            "report_label": _scrub_field(fields.get("codex_report_label")),
            "exit_code": _scrub_field(fields.get("codex_exit_code")),
            "timed_out": _scrub_field(fields.get("codex_timed_out") or "false"),
            "visible_window_title": _scrub_field(fields.get("visible_window_title") or DEFAULT_VISIBLE_WINDOW_TITLE),
        },
    }
    if running_age_seconds is not None:
        subsystems["bridge_core"]["current_turn_age_seconds"] = str(int(running_age_seconds))

    for name, rel, wanted_keys in _PROGRAM_STATE_FILES:
        state_fields = _load_markdown_state_fields(root, rel)
        selected = _select_state_fields(state_fields, wanted_keys)
        selected["observed"] = state_fields.get("_exists", "false")
        if state_fields.get("_updated_at"):
            selected["updated_at"] = state_fields["_updated_at"]
        if state_fields.get("_age_seconds"):
            selected["age_seconds"] = state_fields["_age_seconds"]
        subsystems[name] = selected

    qq_counts = _load_qq_queue_counts(root)
    if qq_counts:
        subsystems.setdefault("qq_outbox", {}).update(qq_counts)
    initiative_metrics = _load_initiative_metrics(root)
    if initiative_metrics:
        subsystems["initiative_metrics"] = initiative_metrics

    traces = {
        name: _trace_file_summary(root, rel)
        for name, rel in _PROGRAM_TRACE_FILES
    }
    known_errors = _collect_known_program_errors(subsystems)
    observed_count = sum(1 for data in subsystems.values() if data.get("observed") == "true")

    return {
        "available": True,
        "updated_at": _timestamp_or_now_iso(fields.get("updated_at")),
        "scope": "known_runtime_state_files_and_bridge_health",
        "code_surface": _collect_code_surface(root),
        "observed_subsystem_count": observed_count,
        "subsystems": subsystems,
        "traces": traces,
        "known_error_count": len(known_errors),
        "known_errors": known_errors[:8],
        "unknown_boundary": "OS process internals, raw logs, adapter display success, and hidden tool output need explicit state writers",
    }


def _program_awareness_prompt_lines(awareness: dict[str, Any]) -> list[str]:
    subsystems = awareness.get("subsystems")
    if not isinstance(subsystems, dict):
        return ["- program_status: unavailable"]
    lines = [
        f"- observed_subsystems: {_scrub_field(awareness.get('observed_subsystem_count'))}",
    ]
    code_surface = awareness.get("code_surface")
    if isinstance(code_surface, dict):
        code_line = _format_subsystem_line(code_surface)
        if code_line:
            lines.append(f"- code_surface: {code_line}")
    ordered_names = [
        "bridge_core",
        "autonomous_loop",
        "self_thought",
        "self_chosen_goal_ecology",
        "self_action_gateway",
        "self_action_patch_executor",
        "proactive_request",
        "contextual_self_loop",
        "contextual_recall",
        "contextual_self_observatory",
        "initiative_lifecycle",
        "initiative_metrics",
        "initiative_feedback",
        "early_visible_segment_shadow",
        "qq_outbox",
        "codex_delegate",
        "research_handoff",
        "watched_source",
        "memory_self_review",
        "inner_cycle",
        "interaction_journal",
        "personality_self_review",
        "persona_feedback",
        "expression_self_learning",
        "post_reply_self_observation",
        "learning_closed_loop",
        "self_state_capsule",
        "self_code_watchdog",
        "runtime_bridge",
        "code_awareness",
        "proactive_dispatch",
        "private_ecosystem",
        "private_desktop",
        "private_owner_share",
        "github_learning",
        "v1_canary_readiness",
        "continuity_handoff",
        "uncertainty_pause",
        "async_exploration",
        "self_code_approval",
        "memory_gate",
    ]
    for name in ordered_names:
        data = subsystems.get(name)
        if not isinstance(data, dict):
            continue
        line = _format_subsystem_line(data)
        if line:
            lines.append(f"- {name}: {line}")
    known_error_count = _safe_int(awareness.get("known_error_count"), 0)
    if known_error_count > 0:
        first_error = ""
        errors = awareness.get("known_errors")
        if isinstance(errors, list) and errors:
            first_error = _clip_preview(errors[0], limit=120)
        suffix = f" latest={first_error}" if first_error else ""
        lines.append(f"- known_errors: count={known_error_count}{suffix}")
    else:
        lines.append("- known_errors: none_observed")
    trace_line = _format_trace_line(awareness.get("traces"))
    if trace_line:
        lines.append(f"- traces: {trace_line}")
    lines.append(f"- unknown_boundary: {_scrub_field(awareness.get('unknown_boundary'))}")
    return lines


def _collect_capability_manifest(root: Path, *, awareness: dict[str, Any] | None = None) -> dict[str, Any]:
    awareness = awareness if isinstance(awareness, dict) else _collect_program_awareness(root)
    subsystems = awareness.get("subsystems")
    if not isinstance(subsystems, dict):
        subsystems = {}
    zones = _load_markdown_state_fields(root, "memory/context/capability_zones_state.md")
    grants = _load_json_object(root / "memory/context/private_ecosystem_grants.json")

    def sub(name: str) -> dict[str, str]:
        data = subsystems.get(name)
        return data if isinstance(data, dict) else {}

    def zone(key: str, default: str = "unknown") -> str:
        value = zones.get(key)
        if value is None or value == "":
            return default
        return _scrub_field(value)

    def grant(path: tuple[str, str], default: str = "unknown") -> str:
        node: Any = grants
        for key in path:
            if not isinstance(node, dict):
                return default
            node = node.get(key)
        if node is None:
            return default
        return _scrub_field(str(node).lower() if isinstance(node, bool) else node)

    def observed(name: str) -> bool:
        return sub(name).get("observed") == "true"

    def add(
        capability_id: str,
        *,
        status: str,
        trigger: str,
        authorization: str,
        output: str,
        boundary: str,
        current: str,
        source_subsystems: tuple[str, ...],
    ) -> None:
        capabilities[capability_id] = {
            "status": _scrub_field(status),
            "trigger": _scrub_field(trigger),
            "authorization": _scrub_field(authorization),
            "output": _scrub_field(output),
            "boundary": _scrub_field(boundary),
            "current": _clip_preview(current, limit=180),
            "source_subsystems": ",".join(source_subsystems),
        }

    bridge = sub("bridge_core")
    autonomous = sub("autonomous_loop")
    initiative = sub("initiative_lifecycle")
    metrics = sub("initiative_metrics")
    dispatch = sub("proactive_dispatch")
    qq_outbox = sub("qq_outbox")
    codex = sub("codex_delegate")
    self_action = sub("self_action_gateway")
    patch = sub("self_action_patch_executor")
    watched = sub("watched_source")
    github = sub("github_learning")
    memory_review = sub("memory_self_review")
    expression = sub("expression_self_learning")
    learning = sub("learning_closed_loop")
    personality = sub("personality_self_review")
    private_ecosystem = sub("private_ecosystem")
    private_desktop = sub("private_desktop")
    private_share = sub("private_owner_share")
    code_surface = awareness.get("code_surface") if isinstance(awareness.get("code_surface"), dict) else {}

    capabilities: dict[str, dict[str, str]] = {}
    bridge_status = "available" if bridge.get("bridge_process") == "running" else "unavailable"
    add(
        "live_chat",
        status=bridge_status,
        trigger="owner_or_authorized_message",
        authorization="configured_chat_routes",
        output="visible_reply",
        boundary="hide_runtime_labels_in_ordinary_chat",
        current=f"turn={bridge.get('current_turn_state', 'unknown')} sessions={bridge.get('active_sessions', 'unknown')} last={bridge.get('last_turn_status', 'unknown')}",
        source_subsystems=("bridge_core", "interaction_journal"),
    )
    add(
        "runtime_self_awareness",
        status="available" if _safe_int(awareness.get("observed_subsystem_count"), 0) > 0 else "unavailable",
        trigger="owner_asks_system_state_or_capability",
        authorization="read_state_mirrors",
        output="natural_runtime_summary",
        boundary="not_code_omniscience_needs_file_open_for_details",
        current=f"observed_subsystems={awareness.get('observed_subsystem_count', '0')} python_files={code_surface.get('python_files', 'unknown')}",
        source_subsystems=("runtime_program_awareness", "code_awareness"),
    )
    auto_enabled = autonomous.get("enabled", "false") == "true"
    add(
        "autonomous_maintenance",
        status="active" if auto_enabled else "disabled",
        trigger="timer",
        authorization=zone("regular_mind_loop", "low_frequency_runtime_maintenance"),
        output="state_updates_and_local_candidates",
        boundary="no_visible_chat_unless_outward_gate_passes",
        current=f"status={autonomous.get('status', 'unknown')} run_count={autonomous.get('run_count', '0')} next={autonomous.get('next_run_at', 'unknown')}",
        source_subsystems=("autonomous_loop", "self_chosen_goal_ecology"),
    )
    desktop_visible = initiative.get("delivery_level") == "desktop_inbox" or _safe_int(
        metrics.get("desktop_shown_count_24h"), 0
    ) > 0
    add(
        "proactive_desktop_inbox",
        status="active" if desktop_visible else "observing",
        trigger="high_score_owner_relevant_event",
        authorization="local_desktop_state_only",
        output="desktop_inbox_candidate",
        boundary="requires_owner_ack_no_qq_claim",
        current=f"delivery={initiative.get('delivery_level', 'unknown')} pending={initiative.get('pending_feedback_count', metrics.get('pending_feedback_count', '0'))} shown_24h={metrics.get('desktop_shown_count_24h', '0')}",
        source_subsystems=("initiative_lifecycle", "initiative_metrics"),
    )
    proactive_qq_zone = zone("proactive_qq_send", "not_granted")
    proactive_qq_enabled = proactive_qq_zone.startswith("enabled")
    add(
        "proactive_owner_private_qq",
        status="enabled_gated" if proactive_qq_enabled else "blocked",
        trigger="owner_only_outward_candidate_after_gates",
        authorization=proactive_qq_zone,
        output="owner_private_qq_message",
        boundary="one_short_message_min_interval_nonowner_and_group_blocked",
        current=f"claim={dispatch.get('last_claim_status', 'unknown')} ack={dispatch.get('last_ack_status', 'unknown')} queued={qq_outbox.get('queued_count', 'unknown')} failed={qq_outbox.get('recent_failed_count', 'unknown')}",
        source_subsystems=("proactive_dispatch", "qq_outbox", "capability_zones"),
    )
    codex_zone = zone("codex_as_eye_and_hand", "ask_owner_first")
    codex_available = codex_zone.startswith("approved") or codex_zone.startswith("enabled")
    add(
        "codex_delegate",
        status="available" if codex_available else "ask_first",
        trigger="owner_approved_or_bounded_research_task",
        authorization=codex_zone,
        output="codex_report_or_material",
        boundary="bounded_delegate_no_privacy_or_source_gate_bypass",
        current=f"status={codex.get('status', 'unknown')} job={codex.get('job_id', '')} report={codex.get('report_label', '')}",
        source_subsystems=("codex_delegate", "research_handoff"),
    )
    add(
        "self_code_iteration",
        status="approval_required" if observed("self_action_patch_executor") or observed("self_code_approval") else "available_when_requested",
        trigger="owner_private_self_code_request_or_prepared_self_action",
        authorization=zone("self_code_iteration_via_codex", "explicit_owner_approval_required"),
        output="approval_queue_codex_patch_watchdog_snapshot",
        boundary="one_time_scope_stable_memory_blocked_watchdog_required",
        current=f"gateway_candidates={self_action.get('candidate_count', '0')} patch_status={patch.get('status', 'unknown')} codex={patch.get('codex_status', 'unknown')}",
        source_subsystems=("self_action_gateway", "self_action_patch_executor", "self_code_watchdog"),
    )
    public_learning_ready = observed("watched_source") or observed("github_learning")
    add(
        "public_learning",
        status="available" if public_learning_ready else "unobserved",
        trigger="scheduled_public_source_scan_or_research_gap",
        authorization=zone("autonomous_search_provider", "bounded_public_read_only"),
        output="staged_learning_candidates",
        boundary="read_only_no_posting_no_code_execution_learning_gates_required",
        current=f"watched={watched.get('status', 'unknown')} github={github.get('status', 'unknown')} accepted={sub('runtime_bridge').get('ready_source_requests', '')}",
        source_subsystems=("watched_source", "github_learning", "runtime_bridge"),
    )
    add(
        "memory_review",
        status=memory_review.get("status", "unknown") if observed("memory_self_review") else "unobserved",
        trigger="memory_pressure_or_pending_candidates",
        authorization="review_gate_then_owner_bulk_review_when_required",
        output="review_decisions_or_owner_review_items",
        boundary="stable_memory_write_blocked_until_gate_passes",
        current=f"pending={memory_review.get('pending_seen', '0')} owner_review={memory_review.get('owner_review_required', '0')} stable={memory_review.get('stable_memory_write', 'blocked')}",
        source_subsystems=("memory_self_review", "inner_cycle"),
    )
    add(
        "expression_learning",
        status=learning.get("status", expression.get("status", "unknown")),
        trigger="owner_feedback_or_reply_self_observation",
        authorization="runtime_trial_only",
        output="voice_behavior_bias",
        boundary=f"stable_personality_auto_apply={zone('stable_personality_auto_apply', 'disabled')}",
        current=f"failure={learning.get('latest_failure_kind', expression.get('failure_kind', 'none'))} repair_count={learning.get('repair_count', '0')} profile_changed={personality.get('profile_changed', 'false')}",
        source_subsystems=("expression_self_learning", "learning_closed_loop", "personality_self_review"),
    )
    private_enabled = grant(("private_ecosystem", "enabled"), "false") == "true"
    add(
        "private_ecosystem",
        status="enabled" if private_enabled else private_ecosystem.get("rollout_state", "disabled"),
        trigger="private_self_space_tick",
        authorization=f"grant_enabled={grant(('private_ecosystem', 'enabled'), 'false')}",
        output="self_private_observations_and_gated_owner_share",
        boundary="low_risk_local_only_no_stable_memory_no_direct_send",
        current=f"rollout={private_ecosystem.get('rollout_state', grant(('private_ecosystem', 'rollout_state'), 'unknown'))} action={private_ecosystem.get('last_action_status', 'unknown')} shares_sent={private_ecosystem.get('owner_private_shares_sent', '0')}",
        source_subsystems=("private_ecosystem", "private_owner_share"),
    )
    desktop_enabled = grant(("private_desktop", "enabled"), "false") == "true"
    desktop_observe_only = grant(("private_desktop", "observe_only"), "true") == "true"
    add(
        "private_desktop",
        status="enabled_observe_only" if desktop_enabled and desktop_observe_only else ("enabled" if desktop_enabled else "disabled"),
        trigger="desktop_panel_or_authorized_single_step",
        authorization=f"enabled={grant(('private_desktop', 'enabled'), 'false')} observe_only={grant(('private_desktop', 'observe_only'), 'true')} single_step={grant(('private_desktop', 'single_step_actions'), 'false')}",
        output="sanitized_isolated_desktop_frames",
        boundary="isolated_linux_desktop_not_owner_host_click_type_need_grant",
        current=f"backend={private_desktop.get('backend', 'unknown')} last={private_desktop.get('last_action_kind', 'none')}/{private_desktop.get('last_result', 'unknown')} risk={private_desktop.get('last_risk', 'unknown')}",
        source_subsystems=("private_desktop", "private_ecosystem_grants"),
    )
    browser_enabled = grant(("private_browser", "enabled"), "false") == "true"
    add(
        "private_browser",
        status="enabled_read_only" if browser_enabled else "disabled",
        trigger="desktop_panel_or_authorized_browser_observation",
        authorization=f"enabled={grant(('private_browser', 'enabled'), 'false')} read_only={grant(('private_browser', 'read_only'), 'true')} single_step={grant(('private_browser', 'single_step_actions'), 'false')}",
        output="private_browser_snapshot",
        boundary="read_only_by_default_single_step_actions_need_grant",
        current=f"max_tabs={grant(('private_browser', 'max_tabs'), 'unknown')} screenshot_ttl_hours={grant(('private_browser', 'screenshot_ttl_hours'), 'unknown')}",
        source_subsystems=("private_browser_grants",),
    )
    share_enabled = private_share.get("enabled", grant(("owner_private_autonomous_share", "enabled"), "false"))
    share_paused = private_share.get("paused", grant(("owner_private_autonomous_share", "paused"), "true"))
    add(
        "owner_private_share",
        status="paused" if share_paused == "true" else ("enabled_gated" if share_enabled == "true" else "disabled"),
        trigger="private_ecosystem_share_candidate",
        authorization=f"enabled={share_enabled} paused={share_paused} channel=owner_private_only",
        output="owner_private_share_candidate_or_hold",
        boundary="owner_only_never_group_public_or_third_party",
        current=f"last_allowed={private_share.get('last_allowed', 'unknown')} last_queued={private_share.get('last_queued', 'unknown')} daily_remaining={private_share.get('daily_remaining', grant(('owner_private_autonomous_share', 'daily_limit'), 'unknown'))}",
        source_subsystems=("private_owner_share", "private_ecosystem_grants"),
    )
    active_count = sum(1 for data in capabilities.values() if data.get("status") not in {"disabled", "blocked", "unavailable", "unobserved"})
    return {
        "available": True,
        "updated_at": _scrub_field(awareness.get("updated_at") or _now_iso()),
        "scope": "runtime_capability_map_from_state_mirrors_and_owner_grants",
        "direct_capability_omniscience": "false",
        "capability_count": str(len(capabilities)),
        "active_capability_count": str(active_count),
        "capabilities": capabilities,
        "runtime_use": "answer capability questions from this map; distinguish current status from authorization and boundary",
    }


def _capability_manifest_prompt_lines(manifest: dict[str, Any]) -> list[str]:
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict):
        return ["- capability_status: unavailable"]
    lines = [
        f"- capability_count: {_scrub_field(manifest.get('capability_count'))}",
        f"- active_capability_count: {_scrub_field(manifest.get('active_capability_count'))}",
        "- use_rule: answer what XinYu can do from status+authorization+boundary; do not treat configured ability as permission to act",
    ]
    for name in (
        "live_chat",
        "runtime_self_awareness",
        "autonomous_maintenance",
        "proactive_desktop_inbox",
        "proactive_owner_private_qq",
        "codex_delegate",
        "self_code_iteration",
        "public_learning",
        "memory_review",
        "expression_learning",
        "private_ecosystem",
        "private_desktop",
        "private_browser",
        "owner_private_share",
    ):
        data = capabilities.get(name)
        if not isinstance(data, dict):
            continue
        compact = _format_subsystem_line(
            _select_state_fields(
                data,
                ("status", "authorization", "output", "boundary", "current"),
            )
        )
        if compact:
            lines.append(f"- {name}: {compact}")
    return lines


def _render_capability_manifest_markdown(root: Path, fields: dict[str, str]) -> str:
    awareness = _collect_program_awareness(root, presence_fields=fields)
    manifest = _collect_capability_manifest(root, awareness=awareness)
    value = lambda item, default="": _scrub_field(item or default)
    lines = [
        "---",
        "title: Runtime Capability Manifest State",
        "memory_type: capability_manifest_state",
        "time_scope: immediate_runtime",
        "subject_ids: [xinyu]",
        "protected: true",
        "source: xinyu_runtime_presence",
        f"updated_at: {value(manifest.get('updated_at'))}",
        "status: active",
        "tags: [runtime, capability, autonomy, boundary]",
        "---",
        "",
        "# Runtime Capability Manifest State",
        "",
        "## Boundary",
        f"- scope: {value(manifest.get('scope'))}",
        f"- direct_capability_omniscience: {value(manifest.get('direct_capability_omniscience'), 'false')}",
        "- not_identity_contract: true",
        "- stable_memory_write_permission: blocked",
        "- permission_rule: current ability does not imply permission to act",
        "- source_rule: derived from runtime state mirrors and owner grant files",
        f"- capability_count: {value(manifest.get('capability_count'), '0')}",
        f"- active_capability_count: {value(manifest.get('active_capability_count'), '0')}",
        "",
        "## Capabilities",
    ]
    capabilities = manifest.get("capabilities")
    if isinstance(capabilities, dict):
        for name, data in capabilities.items():
            if isinstance(data, dict):
                lines.append(f"- {name}: {_format_subsystem_line(data) or 'status=unknown'}")
    lines.extend(
        [
            "",
            "## Runtime Use",
            f"- {value(manifest.get('runtime_use'))}",
            "- For autonomous iteration, check status, authorization, output, and boundary before proposing or acting.",
            "- For owner-facing answers, summarize naturally; do not dump this manifest as raw machinery.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_program_awareness_markdown(root: Path, fields: dict[str, str]) -> str:
    awareness = _collect_program_awareness(root, presence_fields=fields)
    value = lambda item, default="": _scrub_field(item or default)
    lines = [
        "---",
        "title: Runtime Program Awareness",
        "memory_type: runtime_program_awareness",
        "time_scope: immediate_runtime",
        "subject_ids: [xinyu]",
        "protected: true",
        "source: xinyu_runtime_presence",
        f"updated_at: {value(awareness.get('updated_at'))}",
        "status: active",
        "tags: [runtime, presence, program, sidecar]",
        "---",
        "",
        "# Runtime Program Awareness",
        "",
        "## Scope",
        f"- scope: {value(awareness.get('scope'))}",
        "- direct_program_omniscience: false",
        "- known_by_state_mirrors: true",
        f"- observed_subsystem_count: {value(awareness.get('observed_subsystem_count'), '0')}",
        f"- unknown_boundary: {value(awareness.get('unknown_boundary'))}",
        "",
        "## Code Surface",
    ]
    code_surface = awareness.get("code_surface")
    if isinstance(code_surface, dict):
        lines.append(f"- {_format_subsystem_line(code_surface) or 'observed=false'}")
    else:
        lines.append("- observed=false")
    lines.extend(
        [
            "",
            "## Subsystems",
        ]
    )
    subsystems = awareness.get("subsystems")
    if isinstance(subsystems, dict):
        for name in (
            "bridge_core",
            "autonomous_loop",
            "self_thought",
            "self_chosen_goal_ecology",
            "self_action_gateway",
            "self_action_patch_executor",
            "private_ecosystem",
            "private_desktop",
            "private_owner_share",
            "proactive_request",
            "proactive_decision_shadow",
            "contextual_self_loop",
            "contextual_recall",
            "contextual_self_observatory",
            "initiative_lifecycle",
            "initiative_metrics",
            "initiative_feedback",
            "impulse_soup",
            "early_visible_segment_shadow",
            "proactive_dispatch",
            "qq_outbox",
            "v1_canary_readiness",
            "codex_delegate",
            "research_handoff",
            "watched_source",
            "github_learning",
            "memory_self_review",
            "inner_cycle",
            "interaction_journal",
            "personality_self_review",
            "persona_feedback",
            "expression_self_learning",
            "post_reply_self_observation",
            "learning_closed_loop",
            "self_state_capsule",
            "continuity_handoff",
            "uncertainty_pause",
            "async_exploration",
            "self_code_approval",
            "self_code_watchdog",
            "runtime_bridge",
            "memory_gate",
            "code_awareness",
        ):
            data = subsystems.get(name)
            if not isinstance(data, dict):
                continue
            lines.append(f"- {name}: {_format_subsystem_line(data) or 'observed=false'}")
    lines.extend(["", "## Traces"])
    traces = awareness.get("traces")
    if isinstance(traces, dict):
        for name, data in traces.items():
            if isinstance(data, dict):
                lines.append(f"- {name}: {_format_subsystem_line(data) or 'observed=false'}")
    known_errors = awareness.get("known_errors")
    lines.extend(["", "## Known Errors"])
    if isinstance(known_errors, list) and known_errors:
        for item in known_errors[:8]:
            lines.append(f"- {value(item)}")
    else:
        lines.append("- none_observed")
    lines.extend(
        [
            "",
            "## Runtime Use",
            "- Use this as factual program-state awareness.",
            "- For owner questions about code mastery, answer from Code Surface plus observed subsystem states and say details require opening files.",
            "- Do not invent unobserved OS, adapter, or tool internals.",
            "- When the owner asks about XinYu's running state, answer from this card naturally.",
            "",
        ]
    )
    return "\n".join(lines)


def _collect_code_surface(root: Path) -> dict[str, str]:
    root_files = _count_files(root, "*.py")
    custom_files = _count_files(root, "custom/**/*.py")
    v1_files = _count_files(root, "xinyu_v1/**/*.py")
    test_files = _count_files(root, "tests/**/*.py")
    smoke_files = _count_files(root, "*_smoke.py") + _count_files(root, "tests/**/*_smoke.py")
    entrypoints = [name for name in _CODE_SURFACE_ENTRYPOINTS if _safe_file_exists(root / name)]
    python_files = _unique_code_file_count(
        root,
        ("*.py", "custom/**/*.py", "xinyu_v1/**/*.py", "tests/**/*.py"),
    )
    return {
        "observed": "true",
        "python_files": str(python_files),
        "root_modules": str(root_files),
        "custom_modules": str(custom_files),
        "v1_modules": str(v1_files),
        "test_files": str(test_files),
        "smoke_tests": str(smoke_files),
        "major_entrypoints": ",".join(entrypoints) or "none_observed",
        "knowledge_boundary": "file_inventory_and_state_mirrors_only",
        "needs_file_open_for_details": "true",
    }


def _count_files(root: Path, pattern: str) -> int:
    return sum(1 for _ in _iter_code_files(root, pattern))


def _unique_code_file_count(root: Path, patterns: tuple[str, ...]) -> int:
    seen: set[str] = set()
    for pattern in patterns:
        for path in _iter_code_files(root, pattern):
            try:
                seen.add(path.resolve().as_posix())
            except OSError:
                continue
    return len(seen)


def _iter_code_files(root: Path, pattern: str) -> Iterator[Path]:
    try:
        candidates = root.glob(pattern)
        for path in candidates:
            try:
                if path.is_file():
                    yield path
            except OSError:
                continue
    except OSError:
        return


def _safe_file_exists(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _load_markdown_state_fields(root: Path, rel: str) -> dict[str, str]:
    path = root / rel
    fields: dict[str, str] = {"_exists": "false"}
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        stat = path.stat()
    except OSError:
        return fields
    fields["_exists"] = "true"
    fields["_size_bytes"] = str(stat.st_size)
    fields["_age_seconds"] = str(max(0, int(time.time() - stat.st_mtime)))
    fields["_mtime_at"] = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")
    for line in text.splitlines():
        match = _FIELD_RE.match(line)
        if not match:
            match = _FRONTMATTER_FIELD_RE.match(line)
        if not match:
            continue
        fields[match.group(1)] = _clip_preview(match.group(2), limit=180)
    fields["_updated_at"] = (
        fields.get("updated_at")
        or fields.get("checked_at")
        or fields.get("evaluated_at")
        or fields.get("last_confirmed_at")
        or fields.get("_mtime_at")
        or ""
    )
    return fields


def _select_state_fields(fields: dict[str, str], wanted_keys: tuple[str, ...]) -> dict[str, str]:
    selected: dict[str, str] = {}
    for key in wanted_keys:
        value = fields.get(key)
        if value is None or value == "":
            continue
        selected[key] = _scrub_field(value)
    return selected


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_qq_queue_counts(root: Path) -> dict[str, str]:
    path = root / "memory/context/qq_outbox_queue.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"queue_file_exists": str(path.exists()).lower()}
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    items = [item for item in items if isinstance(item, dict)]
    summary = summarize_outbox_items(items)
    return {
        "queue_file_exists": "true",
        "queue_items": str(summary["queue_items"]),
        "queued_count": str(summary["queued_count"]),
        "claimed_count": str(summary["claimed_count"]),
        "sent_count": str(summary["sent_count"]),
        "failed_count": str(summary["failed_count"]),
        "dead_count": str(summary["dead_count"]),
        "recent_failed_count": str(summary["recent_failed_count"]),
        "recent_dead_count": str(summary["recent_dead_count"]),
        "last_failed_at": summary["last_failed_at"],
        "last_dead_at": summary["last_dead_at"],
        "queue_updated_at": _scrub_field(data.get("updated_at")),
    }


def _load_initiative_metrics(root: Path) -> dict[str, str]:
    path = root / INITIATIVE_METRICS_REL
    try:
        stat = path.stat()
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"observed": "false"} if path.exists() else {}
    if not isinstance(data, dict):
        return {"observed": "false"}
    wanted = (
        "updated_at",
        "window_hours",
        "event_count_24h",
        "decision_event_count_24h",
        "candidate_seen_count_24h",
        "selected_count_24h",
        "desktop_shown_count_24h",
        "held_private_count_24h",
        "blocked_count_24h",
        "feedback_count_24h",
        "dismiss_count_24h",
        "reply_count_24h",
        "approved_qq_count_24h",
        "failed_count_24h",
        "pending_feedback_count",
    )
    result = {
        "observed": "true",
        "age_seconds": str(max(0, int(time.time() - stat.st_mtime))),
    }
    for key in wanted:
        value = data.get(key)
        if value is None:
            continue
        result[key] = _clip_preview(value, limit=80)
    return result


def _trace_file_summary(root: Path, rel: str) -> dict[str, str]:
    path = root / rel
    try:
        stat = path.stat()
    except OSError:
        return {"observed": "false"}
    result = {
        "observed": "true",
        "size_bytes": str(stat.st_size),
        "age_seconds": str(max(0, int(time.time() - stat.st_mtime))),
    }
    last_event = _read_last_jsonl_object(path)
    if isinstance(last_event, dict):
        for key in ("event_kind", "observed_at", "status", "reason", "notes"):
            value = last_event.get(key)
            if value is None or value == "":
                continue
            if isinstance(value, list):
                value = ",".join(_safe_str(item) for item in value[:3])
            result[f"last_{key}"] = _clip_preview(value, limit=140)
    return result


def _read_last_jsonl_object(path: Path) -> dict[str, Any] | None:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines[-50:]):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _collect_known_program_errors(subsystems: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for name, data in subsystems.items():
        for key in ("last_error", "adapter_error"):
            value = data.get(key)
            if _is_meaningful_error_value(value):
                errors.append(f"{name}.{key}={_clip_preview(value, limit=120)}")
        count_keys = ["failure_count"]
        if "recent_failed_count" in data or "recent_dead_count" in data:
            count_keys.extend(("recent_failed_count", "recent_dead_count"))
        else:
            count_keys.extend(("failed_count", "dead_count"))
        for key in count_keys:
            value = data.get(key)
            if _safe_int(value, 0) > 0:
                errors.append(f"{name}.{key}={_safe_int(value, 0)}")
    return errors


def _format_subsystem_line(data: dict[str, Any]) -> str:
    if data.get("observed") == "false":
        return "observed=false"
    parts: list[str] = []
    priority_keys = (
        "bridge_process",
        "current_turn_state",
        "active_sessions",
        "python_files",
        "root_modules",
        "custom_modules",
        "v1_modules",
        "test_files",
        "smoke_tests",
        "major_entrypoints",
        "knowledge_boundary",
        "needs_file_open_for_details",
        "status",
        "enabled",
        "in_progress",
        "run_count",
        "failure_count",
        "last_error",
        "outcome",
        "focus_kind",
        "candidate_enabled",
        "research_needed",
        "kind",
        "delivery_level",
        "request_answer_state",
        "current_scene",
        "working_context_budget",
        "forgetting_posture",
        "retrieval_intents",
        "admitted_recall_count",
        "suppressed_recall_count",
        "source_count",
        "short_previews_only",
        "raw_history_dump",
        "visible_source_labels",
        "self_loop_event_count_24h",
        "recall_event_count_24h",
        "initiative_decision_count_24h",
        "initiative_feedback_count_24h",
        "latest_scene",
        "latest_working_self",
        "latest_initiative_posture",
        "recall_admitted_count_24h",
        "recall_suppressed_count_24h",
        "latest_recall_admitted_count",
        "initiative_held_by_context_count_24h",
        "initiative_allowed_by_context_count_24h",
        "quiet_default_hold_count_24h",
        "feedback_after_context_allowed_count_24h",
        "posture",
        "observatory_only",
        "behavior_change",
        "admitted_context_count",
        "suppressed_context_count",
        "working_self",
        "initiative_posture",
        "next_action_bias",
        "short_context_first",
        "retrieval_before_expansion",
        "hidden_orchestration_only",
        "context_gate_observed",
        "context_scene",
        "context_initiative_posture",
        "context_recall_support",
        "context_gate_age_seconds",
        "context_gate_stale",
        "source_type",
        "intent_type",
        "total_score",
        "recommendation",
        "preferred_channel",
        "shadow_only",
        "hard_blocks",
        "next_review_after",
        "window_hours",
        "event_count_24h",
        "decision_event_count_24h",
        "candidate_seen_count_24h",
        "selected_count_24h",
        "desktop_shown_count_24h",
        "held_private_count_24h",
        "blocked_count_24h",
        "feedback_count_24h",
        "dismiss_count_24h",
        "reply_count_24h",
        "approved_qq_count_24h",
        "failed_count_24h",
        "pending_feedback_count",
        "schema_version",
        "thoughtlet_count",
        "active_count",
        "dormant_count",
        "quarantined_count",
        "extinct_count",
        "lineage_count",
        "top_desire_shape",
        "top_energy",
        "top_action",
        "soft_active_count",
        "outward_action_allowed",
        "latest_status",
        "window_rows",
        "eligible_count",
        "accepted_shadow_count",
        "rejected_shadow_count",
        "no_candidate_count",
        "not_eligible_count",
        "acceptance_rate_pct",
        "avg_elapsed_ms",
        "p95_elapsed_ms",
        "avg_segment_chars",
        "top_reasons",
        "privacy_violation_count",
        "raw_user_text_saved",
        "raw_segment_saved",
        "canary_readiness",
        "last_claim_status",
        "last_ack_status",
        "adapter_error",
        "last_event",
        "queue_items",
        "queued_count",
        "claimed_count",
        "sent_count",
        "failed_count",
        "dead_count",
        "recent_failed_count",
        "recent_dead_count",
        "last_failed_at",
        "last_dead_at",
        "readiness_decision",
        "switch_permission",
        "auto_full_switch",
        "proposal_status",
        "next_action",
        "sample_window_turns",
        "error_rate",
        "route_diversity",
        "latest_error",
        "timed_out",
        "job_id",
        "report_label",
        "snapshot_id",
        "approval_id",
        "file_count",
        "reason",
        "route",
        "allow_codex",
        "provider_results",
        "last_interaction_at",
        "last_source",
        "last_topic",
        "last_turn_kind",
        "last_reply_elapsed_ms",
        "minutes_since_last_owner_private",
        "last_user_summary",
        "last_reply_summary",
        "decision",
        "action",
        "autonomy_level",
        "profile_changed",
        "candidate_theme",
        "active_trial_habit",
        "persona_trial_feedback",
        "promotion_signal",
        "repair_signal",
        "feedback_confidence",
        "checked_at",
        "initiative_decision",
        "learning_quality_grade",
        "archive_next_action",
        "updated_at",
        "age_seconds",
    )
    ordered_keys = list(priority_keys) + [key for key in data if key not in priority_keys]
    for key in ordered_keys:
        value = data.get(key)
        if key.startswith("_"):
            continue
        text = _scrub_field(value)
        if text == "":
            continue
        if key == "observed" and text == "true":
            continue
        parts.append(f"{key}={text}")
        if len(parts) >= 12:
            break
    return " ".join(parts)


def _format_trace_line(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    parts: list[str] = []
    for name, data in value.items():
        if not isinstance(data, dict) or data.get("observed") != "true":
            continue
        event = data.get("last_event_kind") or data.get("last_status") or "observed"
        parts.append(f"{name}:{_scrub_field(event)}")
        if len(parts) >= 5:
            break
    return ", ".join(parts)


def _is_meaningful_error_value(value: Any) -> bool:
    text = _safe_str(value).strip().lower()
    return text not in {"", "none", "unknown", "0", "false", "ok", "sent", "success", "dry_run_not_enqueued"}


def _render_presence_markdown(fields: dict[str, str]) -> str:
    value = lambda key, default="": _scrub_field(fields.get(key) or default)
    updated_at = _timestamp_or_now_iso(fields.get("updated_at"))
    return "\n".join(
        [
            "---",
            "title: Runtime Self Presence",
            "memory_type: runtime_self_presence",
            "time_scope: immediate_runtime",
            "subject_ids: [xinyu]",
            "protected: true",
            "source: xinyu_runtime_presence",
            f"updated_at: {_timestamp_or_now_iso(updated_at)}",
            "status: active",
            "tags: [runtime, presence, continuity, sidecar]",
            "---",
            "",
            "# Runtime Self Presence",
            "",
            "## Boundary",
            "- scope: observed runtime facts only",
            "- not_identity_contract: true",
            "- not_voice_script: true",
            "- stable_self_write_permission: blocked",
            "",
            "## Current Runtime",
            f"- bridge_process: {value('bridge_process', 'unknown')}",
            f"- heartbeat_reason: {value('heartbeat_reason')}",
            f"- current_turn_state: {value('current_turn_state', 'idle')}",
            f"- current_turn_started_at: {value('current_turn_started_at')}",
            f"- current_turn_id: {value('current_turn_id')}",
            f"- current_turn_kind: {value('current_turn_kind')}",
            f"- current_turn_source: {value('current_turn_source')}",
            f"- current_turn_relation: {value('current_turn_relation')}",
            f"- current_session_hash: {value('current_session_hash')}",
            f"- current_user_preview: {value('current_user_preview')}",
            f"- active_sessions: {value('active_sessions', 'unknown')}",
            "",
            "## Last Live Turn",
            f"- last_turn_id: {value('last_turn_id')}",
            f"- last_turn_at: {value('last_turn_at')}",
            f"- last_turn_status: {value('last_turn_status')}",
            f"- last_turn_elapsed_ms: {value('last_turn_elapsed_ms')}",
            f"- last_source: {value('last_source', 'unknown')}",
            f"- last_relation: {value('last_relation', 'unknown')}",
            f"- last_session_hash: {value('last_session_hash')}",
            f"- last_user_preview: {value('last_user_preview')}",
            f"- last_reply_preview: {value('last_reply_preview')}",
            "",
            "## Codex Delegate",
            f"- codex_status: {value('codex_status', 'unknown')}",
            f"- codex_job_id: {value('codex_job_id')}",
            f"- visible_window_title: {value('visible_window_title', DEFAULT_VISIBLE_WINDOW_TITLE)}",
            f"- codex_request_label: {value('codex_request_label')}",
            f"- codex_report_label: {value('codex_report_label')}",
            f"- codex_exit_code: {value('codex_exit_code')}",
            f"- codex_timed_out: {value('codex_timed_out', 'false')}",
            "",
            "## Background",
            f"- autonomous_maintenance: {value('autonomous_maintenance', 'unknown')}",
            f"- qq_outbox: {value('qq_outbox', 'unknown')}",
            "",
            "## Runtime Use",
            "- This is factual continuity, not a sentence template.",
            "- Use it only when it helps answer the live turn naturally.",
            "",
        ]
    )


def _write_presence_markdown(root: Path, fields: dict[str, str]) -> list[str]:
    notes = _atomic_write_text(root / PRESENCE_MD_REL, _render_presence_markdown(fields))
    notes.extend(_atomic_write_text(root / PROGRAM_AWARENESS_MD_REL, _render_program_awareness_markdown(root, fields)))
    notes.extend(_atomic_write_text(root / CAPABILITY_MANIFEST_MD_REL, _render_capability_manifest_markdown(root, fields)))
    return notes


def _append_trace(root: Path, event: dict[str, Any]) -> list[str]:
    path = root / PRESENCE_TRACE_REL
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        clean_event = _clean_json_value(event)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(clean_event, ensure_ascii=False, sort_keys=True) + "\n")
        return []
    except OSError as exc:
        return [f"presence_trace_write_failed:{type(exc).__name__}"]


def _atomic_write_json(path: Path, data: dict[str, Any]) -> list[str]:
    return _atomic_write_text(path, json.dumps(_clean_json_value(data), ensure_ascii=False, indent=2) + "\n")


def _atomic_write_text(path: Path, text: str) -> list[str]:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(_scrub_field(text), encoding="utf-8")
        os.replace(tmp, path)
        return []
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return [f"presence_write_failed:{type(exc).__name__}"]


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {_safe_str(key): _clean_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, str):
        return _scrub_field(value)
    return value


def _classify_payload(payload: dict[str, Any]) -> tuple[str, str, str]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    message_type = _safe_str(payload.get("message_type")).lower()
    platform = _safe_str(payload.get("platform"), "qq").lower()
    is_group = message_type.startswith("group") or bool(_safe_str(payload.get("group_id")).strip())
    is_owner = _as_bool(metadata.get("is_owner_user"), default=False)
    if is_group:
        source = "qq_group" if platform == "qq" else "group"
        relation = "owner" if is_owner else "group_member"
        turn = "qq_group_live_turn"
    elif is_owner:
        source = "owner_private"
        relation = "owner"
        turn = "owner_private_live_turn"
    elif platform == "qq":
        source = "qq_private"
        relation = "external_contact"
        turn = "qq_private_live_turn"
    else:
        source = "unknown"
        relation = "external_contact"
        turn = "live_turn"
    return source, relation, turn


def _make_turn_id(payload: dict[str, Any], session_key: str) -> str:
    raw = "|".join(
        [
            _safe_str(payload.get("message_id")),
            _safe_str(payload.get("message_seq")),
            _safe_str(payload.get("time")),
            _safe_str(session_key),
            str(time.time_ns()),
        ]
    )
    return f"turn-{datetime.now().astimezone().strftime('%Y%m%dT%H%M%S')}-{_stable_hash(raw, length=10)}"


def _stable_hash(value: str, *, length: int = 12) -> str:
    clean = _safe_str(value).strip()
    if not clean:
        return ""
    return "sha256:" + hashlib.sha256(clean.encode("utf-8", errors="ignore")).hexdigest()[:length]


def _scrub_field(value: Any) -> str:
    text = _safe_str(value)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[redacted-secret]", text)
    text = _LOCAL_PATH_RE.sub("[local-path]", text)
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _clip_preview(value: Any, *, limit: int = DEFAULT_PREVIEW_CHARS) -> str:
    text = _scrub_field(value)
    text = _LONG_NUMERIC_ID_RE.sub("[id]", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _clip_note(value: Any, *, limit: int = 120) -> str:
    return _clip_preview(value, limit=limit)


def _path_label(value: Any) -> str:
    text = _safe_str(value).strip()
    if not text:
        return ""
    parts = re.split(r"[\\/]+", text)
    return _clip_preview(parts[-1] if parts else text, limit=120)


def _normalize_turn_status(value: Any) -> str:
    text = _safe_str(value).strip().lower()
    if text in {"ok", "done", "success", "finished"}:
        return "ok"
    if text in {"timeout", "timed_out", "time_out"}:
        return "timeout"
    if text in {"cancelled", "canceled"}:
        return "cancelled"
    if text in {"error", "failed", "fail"}:
        return "error"
    return _clip_preview(text or "unknown", limit=40)


def _normalize_codex_status(value: Any, *, timed_out: bool = False) -> str:
    if timed_out:
        return "timed_out"
    text = _safe_str(value).strip().lower()
    aliases = {
        "done": "finished",
        "ok": "finished",
        "success": "finished",
        "completed": "finished",
        "complete": "finished",
        "timeout": "timed_out",
        "timedout": "timed_out",
        "time_out": "timed_out",
        "error": "failed",
        "failure": "failed",
        "fail": "failed",
        "scheduled": "running",
        "started": "running",
    }
    clean = aliases.get(text, text)
    if clean in {"idle", "running", "finished", "timed_out", "failed", "unknown"}:
        return clean
    return _clip_preview(clean or "unknown", limit=40)


def _codex_event_kind(status: str) -> str:
    if status == "running":
        return "codex_started"
    if status == "finished":
        return "codex_finished"
    if status == "timed_out":
        return "codex_timed_out"
    if status == "failed":
        return "codex_failed"
    return "codex_presence"


def _normalize_background_state(value: Any) -> str:
    if isinstance(value, bool):
        return "running" if value else "idle"
    text = _safe_str(value).strip().lower()
    if text in {"idle", "running", "disabled", "unknown", "pending"}:
        return text
    if text in {"true", "yes", "on", "active"}:
        return "running"
    if text in {"false", "no", "off", "inactive"}:
        return "idle"
    return _clip_preview(text or "unknown", limit=40)


def _safe_count(value: Any) -> str:
    try:
        return str(max(0, int(value)))
    except (TypeError, ValueError):
        return "unknown"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(_safe_str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat(timespec="seconds")


def _parse_iso(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text or text == "unknown":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _age_seconds(value: Any) -> float | None:
    parsed = _parse_iso(value)
    if parsed is None:
        return None
    return max(0.0, (datetime.now().astimezone() - parsed).total_seconds())


def _is_stale_age(age_seconds: float | None, *, threshold: int = DEFAULT_RUNNING_STALE_SECONDS) -> bool:
    return age_seconds is not None and age_seconds > threshold


def _event_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().astimezone().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"


def _join_limited(lines: list[str], limit: int) -> str:
    out: list[str] = []
    for line in lines:
        candidate = "\n".join(out + [line])
        if len(candidate) <= limit:
            out.append(line)
            continue
        remaining = limit - len("\n".join(out)) - (1 if out else 0)
        if remaining > 24:
            out.append(line[: max(0, remaining - 3)].rstrip() + "...")
        break
    return "\n".join(out)[:limit]


def _soft_failure(action: str, exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "action": action,
        "notes": [f"runtime_presence_error:{type(exc).__name__}"],
    }
