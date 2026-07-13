from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_short_term_continuity_store import append_short_term_continuity_trace
from xinyu_short_term_continuity_store import write_short_term_continuity_state
from xinyu_visible_text_sanitizer import sanitize_visible_text


ARCHIVE_FALLBACK_LIMIT = 8

DIRECT_REFERENCE_MARKERS = (
    "刚才",
    "刚刚",
    "刚聊",
    "刚聊过",
    "刚说",
    "刚说过",
    "才刚",
    "前面",
    "上面",
    "上一句",
    "前一句",
    "那句",
    "这一句",
    "这句",
    "这几句",
    "这两句",
    "这些话",
    "这段话",
    "刚刚聊过的对话",
    "刚聊过的对话",
    "哪一句",
    "哪几句",
    "哪两句",
    "还要问我哪一句",
)

REFERENCE_QUESTION_RE = re.compile(r"(哪[一两几]?句|哪[一两几]?段|什么话|刚才.*什么|刚刚.*什么)")


@dataclass(frozen=True)
class ShortTermContinuityState:
    checked_at: str
    turn_id: str
    status: str
    direct_reference: bool
    recall_status: str
    recall_source: str
    tail_count: int
    archive_recovered_count: int
    recent_user_count: int
    recent_assistant_count: int
    latest_user_ref: str
    latest_assistant_ref: str
    tail_storage_status: str
    tail_storage_reason: str
    tail_storage_usable_row_count: int
    tail_storage_filtered_row_count: int
    tail_storage_invalid_line_count: int
    notes: tuple[str, ...]
    prompt_rows: tuple[dict[str, str], ...]

    def to_trace_dict(self) -> dict[str, Any]:
        return {
            "checked_at": self.checked_at,
            "turn_id": self.turn_id,
            "status": self.status,
            "direct_reference": self.direct_reference,
            "recall_status": self.recall_status,
            "recall_source": self.recall_source,
            "tail_count": self.tail_count,
            "archive_recovered_count": self.archive_recovered_count,
            "recent_user_count": self.recent_user_count,
            "recent_assistant_count": self.recent_assistant_count,
            "latest_user_ref": self.latest_user_ref,
            "latest_assistant_ref": self.latest_assistant_ref,
            "tail_storage_status": self.tail_storage_status,
            "tail_storage_reason": self.tail_storage_reason,
            "tail_storage_usable_row_count": self.tail_storage_usable_row_count,
            "tail_storage_filtered_row_count": self.tail_storage_filtered_row_count,
            "tail_storage_invalid_line_count": self.tail_storage_invalid_line_count,
            "notes": list(self.notes),
            "raw_private_body_retained": False,
            "visible_reply_text_retained": False,
        }


def evaluate_short_term_continuity(
    root: Path,
    *,
    payload: dict[str, Any] | None = None,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None,
    session_key: str = "",
    turn_id: str = "",
    checked_at: str | None = None,
    write_state: bool = False,
) -> ShortTermContinuityState:
    root = Path(root)
    checked_at = checked_at or _now_iso()
    direct_reference = _has_direct_reference(user_text)
    source_tail = list(dialogue_tail or [])
    archive_recovered_count = 0
    prompt_rows = tuple(_recent_prompt_rows(source_tail, max_rows=8))
    recent_users = [row for row in prompt_rows if row.get("role") == "user"]
    recent_assistants = [row for row in prompt_rows if row.get("role") == "assistant"]
    recall_status = "not_requested"
    recall_source = "not_requested"
    notes: list[str] = []
    tail_storage = _tail_storage_diagnostics(
        root,
        payload=payload,
        session_key=session_key,
        enabled=direct_reference,
    )
    if direct_reference:
        notes.append("direct_reference_requested")
        if prompt_rows:
            recall_status = "tail_available"
            recall_source = "dialogue_tail"
            notes.append("recent_tail_available")
        else:
            working_rows = _recent_working_memory_prompt_rows(
                root,
                payload=payload,
                session_key=session_key,
                max_rows=ARCHIVE_FALLBACK_LIMIT,
            )
            if working_rows:
                prompt_rows = tuple(working_rows)
                recent_users = [row for row in prompt_rows if row.get("role") == "user"]
                recent_assistants = [row for row in prompt_rows if row.get("role") == "assistant"]
                recall_status = "tail_available"
                recall_source = "dialogue_working_memory"
                notes.append("working_memory_tail_recovered")
            else:
                archive_rows, archive_note = _recent_archive_prompt_rows(
                    root,
                    payload=payload,
                    max_rows=ARCHIVE_FALLBACK_LIMIT,
                )
                if archive_note:
                    notes.append(archive_note)
                if archive_rows:
                    prompt_rows = tuple(archive_rows)
                    archive_recovered_count = len(archive_rows)
                    recent_users = [row for row in prompt_rows if row.get("role") == "user"]
                    recent_assistants = [row for row in prompt_rows if row.get("role") == "assistant"]
                    recall_status = "tail_available"
                    recall_source = "dialogue_archive"
                else:
                    recall_status = "tail_missing"
                    recall_source = "none"
                    notes.append("recent_tail_missing")
    else:
        recall_source = "not_requested"
        notes.append("no_direct_reference")

    state = ShortTermContinuityState(
        checked_at=checked_at,
        turn_id=_safe_str(turn_id).strip() or "none",
        status="active" if direct_reference else "inactive",
        direct_reference=direct_reference,
        recall_status=recall_status,
        recall_source=recall_source,
        tail_count=len(source_tail),
        archive_recovered_count=archive_recovered_count,
        recent_user_count=len(recent_users),
        recent_assistant_count=len(recent_assistants),
        latest_user_ref=_content_ref(recent_users[-1].get("content")) if recent_users else "none",
        latest_assistant_ref=_content_ref(recent_assistants[-1].get("content")) if recent_assistants else "none",
        tail_storage_status=_safe_str(tail_storage.get("status")).strip() or "not_checked",
        tail_storage_reason=_safe_str(tail_storage.get("reason")).strip() or "not_checked",
        tail_storage_usable_row_count=_as_int(tail_storage.get("usable_row_count")),
        tail_storage_filtered_row_count=_as_int(tail_storage.get("filtered_row_count")),
        tail_storage_invalid_line_count=_as_int(tail_storage.get("invalid_line_count")),
        notes=tuple(notes),
        prompt_rows=prompt_rows,
    )
    if write_state:
        _write_state(root, state)
        _append_trace(root, state)
    return state


def build_short_term_continuity_prompt_block(
    root: Path,
    *,
    payload: dict[str, Any] | None = None,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None,
    session_key: str = "",
    turn_id: str = "",
    write_state: bool = True,
    max_chars: int = 1600,
) -> str:
    state = evaluate_short_term_continuity(
        root,
        payload=payload,
        user_text=user_text,
        dialogue_tail=dialogue_tail,
        session_key=session_key,
        turn_id=turn_id,
        write_state=write_state,
    )
    if not state.direct_reference:
        return ""

    lines = [
        "short-term continuity sidecar:",
        "visibility_rule: hidden; do not mention continuity state, hashes, traces, files, or sidecar names.",
        f"tail_status: {state.recall_status}",
        f"tail_source: {state.recall_source}",
        "reference_rule: resolve 刚才/刚刚/这句/这几句/哪一句 from the recent tail below before asking the owner to repeat.",
        "anti_repeat_rule: if a recent assistant or owner line is listed, do not ask 哪一句/哪几句; answer from that line directly.",
        "missing_rule: if tail_status is tail_missing, say you cannot reliably recover the exact previous line; do not fabricate or invent it.",
        "recent_tail_anchor:",
    ]
    if state.prompt_rows:
        for row in state.prompt_rows:
            role = row.get("role", "unknown")
            recorded_at = row.get("recorded_at", "")
            suffix = f" ({recorded_at})" if recorded_at else ""
            lines.append(f"- {role}{suffix}: {row.get('content', '')}")
    else:
        lines.append("- none")
    block = "\n".join(lines)
    return block[: max(0, int(max_chars))].rstrip()


def _has_direct_reference(text: str) -> bool:
    clean = _safe_str(text)
    compact = re.sub(r"\s+", "", clean)
    return any(marker in compact for marker in DIRECT_REFERENCE_MARKERS) or bool(REFERENCE_QUESTION_RE.search(clean))


def _recent_prompt_rows(dialogue_tail: list[dict[str, str]], *, max_rows: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in dialogue_tail[-max(1, int(max_rows)) :]:
        if not isinstance(item, dict):
            continue
        role = _safe_str(item.get("role")).strip()
        if role not in {"user", "assistant"}:
            continue
        content = _safe_str(item.get("content")).strip()
        if role == "assistant":
            content = sanitize_visible_text(content).strip()
        if not content:
            continue
        row = {"role": role, "content": _compact(content, limit=260)}
        recorded_at = _safe_str(item.get("recorded_at")).strip()
        if recorded_at:
            row["recorded_at"] = recorded_at
        rows.append(row)
    return rows


def _recent_archive_prompt_rows(
    root: Path,
    *,
    payload: dict[str, Any] | None,
    max_rows: int,
) -> tuple[list[dict[str, str]], str]:
    if not isinstance(payload, dict):
        return [], "archive_fallback_no_payload"
    try:
        from xinyu_dialogue_archive import dialogue_archive_path
        from xinyu_dialogue_archive import resolve_dialogue_scope
        from xinyu_dialogue_archive import search_dialogue_archive

        if not dialogue_archive_path(root).exists():
            return [], "archive_fallback_unavailable"
        scope = resolve_dialogue_scope(payload)
        records = search_dialogue_archive(
            root,
            "",
            scopes=[scope.scope],
            session_key=scope.session_key,
            limit=max(1, int(max_rows)),
        )
    except Exception as exc:
        return [], f"archive_fallback_error:{type(exc).__name__}"
    rows: list[dict[str, str]] = []
    sorted_records = sorted(records, key=lambda item: (item.created_at, item.message_id))
    for record in sorted_records[-max(1, int(max_rows)) :]:
        role = _safe_str(record.role).strip()
        if role not in {"user", "assistant"}:
            continue
        content = _safe_str(record.text).strip()
        if role == "assistant":
            content = sanitize_visible_text(content).strip()
        if not content:
            continue
        row = {"role": role, "content": _compact(content, limit=260)}
        recorded_at = _safe_str(record.created_at).strip()
        if recorded_at:
            row["recorded_at"] = recorded_at
        rows.append(row)
    return rows, "archive_tail_recovered" if rows else "archive_fallback_empty"


def _recent_working_memory_prompt_rows(
    root: Path,
    *,
    payload: dict[str, Any] | None,
    session_key: str,
    max_rows: int,
) -> list[dict[str, str]]:
    resolved_session_key = _resolve_session_key(payload=payload, session_key=session_key)
    if not resolved_session_key:
        return []
    try:
        from xinyu_dialogue_working_memory import load_dialogue_tail

        rows = load_dialogue_tail(
            root,
            resolved_session_key,
            max_entries=max(1, int(max_rows)),
            include_timestamps=True,
            truncate_chars=260,
        )
    except Exception:
        return []
    return _recent_prompt_rows(rows, max_rows=max_rows)


def _tail_storage_diagnostics(
    root: Path,
    *,
    payload: dict[str, Any] | None,
    session_key: str,
    enabled: bool,
) -> dict[str, Any]:
    if not enabled:
        return {
            "status": "not_checked",
            "reason": "no_direct_reference",
            "usable_row_count": 0,
            "filtered_row_count": 0,
            "invalid_line_count": 0,
        }
    resolved_session_key = _resolve_session_key(payload=payload, session_key=session_key)
    try:
        from xinyu_dialogue_working_memory import inspect_dialogue_tail_storage

        return inspect_dialogue_tail_storage(root, resolved_session_key)
    except Exception as exc:
        return {
            "status": "read_error",
            "reason": f"working_memory_storage_diag_error:{type(exc).__name__}",
            "usable_row_count": 0,
            "filtered_row_count": 0,
            "invalid_line_count": 0,
        }


def _resolve_session_key(*, payload: dict[str, Any] | None, session_key: str) -> str:
    clean = _safe_str(session_key).strip()
    if clean:
        return clean
    if not isinstance(payload, dict):
        return ""
    try:
        from xinyu_bridge_session import session_key_from_payload

        return _safe_str(session_key_from_payload(payload)).strip()
    except Exception:
        return ""


def _write_state(root: Path, state: ShortTermContinuityState) -> None:
    notes = ", ".join(state.notes) if state.notes else "none"
    text = f"""---
title: Short Term Continuity State
memory_type: short_term_continuity_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_short_term_continuity
updated_at: {state.checked_at}
status: active
tags: [continuity, dialogue-tail, recall, autonomy]
---

# Short Term Continuity State

## Current Turn
- status: {state.status}
- checked_at: {state.checked_at}
- turn_id: {state.turn_id}
- direct_reference: {str(state.direct_reference).lower()}
- recall_status: {state.recall_status}
- recall_source: {state.recall_source}
- tail_count: {state.tail_count}
- archive_recovered_count: {state.archive_recovered_count}
- recent_user_count: {state.recent_user_count}
- recent_assistant_count: {state.recent_assistant_count}
- latest_user_ref: {state.latest_user_ref}
- latest_assistant_ref: {state.latest_assistant_ref}
- tail_storage_status: {state.tail_storage_status}
- tail_storage_reason: {state.tail_storage_reason}
- tail_storage_usable_row_count: {state.tail_storage_usable_row_count}
- tail_storage_filtered_row_count: {state.tail_storage_filtered_row_count}
- tail_storage_invalid_line_count: {state.tail_storage_invalid_line_count}
- notes: {notes}

## Boundaries
- prompt_tail_text_available: hidden_prompt_only
- raw_private_body_retained: false
- visible_reply_text_retained: false
- stable_memory_write: blocked
"""
    write_short_term_continuity_state(root, text)


def _append_trace(root: Path, state: ShortTermContinuityState) -> None:
    append_short_term_continuity_trace(root, state.to_trace_dict())


def _content_ref(value: Any) -> str:
    clean = _safe_str(value).strip()
    if not clean:
        return "none"
    return "sha256:" + hashlib.sha256(clean.encode("utf-8", errors="replace")).hexdigest()[:16]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _compact(text: str, *, limit: int) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()
