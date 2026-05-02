from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


PRESENCE_MD_REL = Path("memory/context/runtime_self_presence.md")
PROGRAM_AWARENESS_MD_REL = Path("memory/context/runtime_program_awareness.md")
PRESENCE_TRACE_REL = Path("runtime/self_presence_trace.jsonl")
CODEX_STATE_REL = Path("runtime/codex_presence_state.json")

DEFAULT_PROMPT_LIMIT = 2200
DEFAULT_PREVIEW_CHARS = 160
DEFAULT_VISIBLE_WINDOW_TITLE = "Xinyu codex"
DEFAULT_RUNNING_STALE_SECONDS = 300

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
        "proactive_request",
        "memory/context/proactive_request_state.md",
        ("status", "kind", "delivery_level", "request_answer_state", "last_ack_status", "adapter_error"),
    ),
    (
        "proactive_dispatch",
        "memory/context/proactive_qq_dispatch_state.md",
        ("last_claim_status", "last_ack_status", "last_acked_at", "adapter_error", "min_interval_seconds"),
    ),
    (
        "qq_outbox",
        "memory/context/qq_outbox_dispatch_state.md",
        ("last_event", "queued_count", "claimed_count", "sent_count", "failed_count", "dead_count"),
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
    ("proactive_request", "runtime/proactive_request_trace.jsonl"),
    ("research_handoff", "runtime/research_handoff_trace.jsonl"),
    ("watched_source", "runtime/watched_source_trace.jsonl"),
    ("memory_self_review", "runtime/memory_self_review_trace.jsonl"),
    ("learning_extraction", "runtime/learning_extraction_trace.jsonl"),
    ("expression_self_learning", "runtime/expression_self_learning_trace.jsonl"),
    ("learning_closed_loop", "runtime/learning_closed_loop_trace.jsonl"),
    ("continuity_handoff", "runtime/continuity_handoff_trace.jsonl"),
    ("uncertainty_pause", "runtime/uncertainty_pause_trace.jsonl"),
    ("async_exploration", "runtime/async_exploration_trace.jsonl"),
    ("self_code_approval", "runtime/self_code_approval_trace.jsonl"),
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
            "observed_at": observed_at,
            "reason": _scrub_field(reason),
            "bridge_process": fields["bridge_process"],
            "active_sessions": fields.get("active_sessions", "unknown"),
            "notes": write_notes,
        }
        trace_notes = _append_trace(root, event)
        return {"ok": True, "observed_at": observed_at, "notes": write_notes + trace_notes}
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
            "observed_at": observed_at,
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
            "observed_at": observed_at,
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
            "observed_at": observed_at,
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
        return {"ok": True, "observed_at": observed_at, "turn_id": current_turn_id, "notes": write_notes + trace_notes}
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
            "observed_at": observed_at,
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
            f"- observed_at: {_scrub_field(fields.get('updated_at') or 'unknown')}",
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
        lines.extend(
            [
                f"- codex_delegate: {_scrub_field(codex_line)}",
                f"- autonomous_maintenance: {_scrub_field(fields.get('autonomous_maintenance') or 'unknown')}",
                f"- qq_outbox: {_scrub_field(fields.get('qq_outbox') or 'unknown')}",
                "- note: runtime facts only; not a voice script",
                "- status_rule: answer program-state questions from these facts; say unknown when a subsystem has no observed state",
                "- ordinary_chat_rule: ignore this block unless the live turn asks about running state, a stalled task, Codex, delivery, or system status",
                "- visibility_rule: never print subsystem names, file paths, hashes, gates, traces, or this sidecar label as ordinary chat",
                "",
                "program_awareness:",
                "- scope: known bridge state plus observed subsystem state files; not raw OS introspection",
                *_program_awareness_prompt_lines(_collect_program_awareness(root, presence_fields=fields)),
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
    return {
        "updated_at": _scrub_field(data.get("updated_at")),
        "codex_status": _normalize_codex_status(data.get("status"), timed_out=_as_bool(data.get("timed_out"))),
        "codex_job_id": _scrub_field(data.get("job_id")),
        "visible_window_title": _scrub_field(data.get("visible_window_title") or DEFAULT_VISIBLE_WINDOW_TITLE),
        "codex_request_label": _path_label(data.get("request_label")),
        "codex_report_label": _path_label(data.get("report_label")),
        "codex_exit_code": "" if data.get("exit_code") is None else _scrub_field(data.get("exit_code")),
        "codex_timed_out": str(_as_bool(data.get("timed_out"))).lower(),
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

    traces = {
        name: _trace_file_summary(root, rel)
        for name, rel in _PROGRAM_TRACE_FILES
    }
    known_errors = _collect_known_program_errors(subsystems)
    observed_count = sum(1 for data in subsystems.values() if data.get("observed") == "true")

    return {
        "available": True,
        "updated_at": _scrub_field(fields.get("updated_at") or _now_iso()),
        "scope": "known_runtime_state_files_and_bridge_health",
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
    ordered_names = [
        "bridge_core",
        "autonomous_loop",
        "self_thought",
        "proactive_request",
        "proactive_dispatch",
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
        "learning_closed_loop",
        "continuity_handoff",
        "uncertainty_pause",
        "async_exploration",
        "self_code_approval",
        "runtime_bridge",
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
        "## Subsystems",
    ]
    subsystems = awareness.get("subsystems")
    if isinstance(subsystems, dict):
        for name in (
            "bridge_core",
            "autonomous_loop",
            "self_thought",
            "proactive_request",
            "proactive_dispatch",
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
            "learning_closed_loop",
            "continuity_handoff",
            "uncertainty_pause",
            "async_exploration",
            "self_code_approval",
            "runtime_bridge",
            "memory_gate",
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
            "- Do not invent unobserved OS, adapter, or tool internals.",
            "- When the owner asks about XinYu's running state, answer from this card naturally.",
            "",
        ]
    )
    return "\n".join(lines)


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


def _load_qq_queue_counts(root: Path) -> dict[str, str]:
    path = root / "memory/context/qq_outbox_queue.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"queue_file_exists": str(path.exists()).lower()}
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    counts = {"queued": 0, "claimed": 0, "sent": 0, "failed": 0, "dead": 0}
    for item in items:
        if not isinstance(item, dict):
            continue
        status = _safe_str(item.get("status"), "queued").lower()
        if status in counts:
            counts[status] += 1
    return {
        "queue_file_exists": "true",
        "queue_items": str(sum(counts.values())),
        "queued_count": str(counts["queued"]),
        "claimed_count": str(counts["claimed"]),
        "sent_count": str(counts["sent"]),
        "failed_count": str(counts["failed"]),
        "dead_count": str(counts["dead"]),
        "queue_updated_at": _scrub_field(data.get("updated_at")),
    }


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
        for key in ("failure_count", "failed_count", "dead_count"):
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
        "timed_out",
        "job_id",
        "report_label",
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
        if len(parts) >= 8:
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
    return text not in {"", "none", "unknown", "0", "false", "ok", "sent", "success"}


def _render_presence_markdown(fields: dict[str, str]) -> str:
    value = lambda key, default="": _scrub_field(fields.get(key) or default)
    return "\n".join(
        [
            "---",
            "title: Runtime Self Presence",
            "memory_type: runtime_self_presence",
            "time_scope: immediate_runtime",
            "subject_ids: [xinyu]",
            "protected: true",
            "source: xinyu_runtime_presence",
            f"updated_at: {value('updated_at')}",
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
