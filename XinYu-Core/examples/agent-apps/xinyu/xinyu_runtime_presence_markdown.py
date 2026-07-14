"""Presence markdown rendering (runtime self-presence card).

Extracted from xinyu_runtime_presence so the API module stays thinner.
Program-awareness / capability-manifest renderers still live in the main module
because they depend on collectors there.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from xinyu_runtime_presence_text import scrub_field


def _timestamp_or_now_iso(value: Any, *, now_iso: Callable[[], str] | None = None) -> str:
    text = "" if value is None else str(value).strip()
    now = now_iso or (lambda: datetime.now().astimezone().isoformat(timespec="seconds"))
    if not text or text == "unknown":
        return now()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return now()
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def render_presence_markdown(
    fields: dict[str, str],
    *,
    default_visible_window_title: str = "Xinyu codex",
) -> str:
    def value(key: str, default: str = "") -> str:
        return scrub_field(fields.get(key) or default)

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
            f"- visible_window_title: {value('visible_window_title', default_visible_window_title)}",
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
