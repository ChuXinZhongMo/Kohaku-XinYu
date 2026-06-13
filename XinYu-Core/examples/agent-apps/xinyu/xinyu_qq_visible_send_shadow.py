from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_answer_discipline_visible_guard import evaluate_visible_reply_for_answer_discipline
from xinyu_qq_visible_send_shadow_store import append_visible_send_shadow_trace
from xinyu_qq_visible_send_shadow_store import read_visible_send_shadow_context_text
from xinyu_qq_visible_send_shadow_store import write_visible_send_shadow_state
from xinyu_sent_reply_index import visible_text_hash


TRACE_REL = Path("runtime/answer_discipline_visible_send_shadow.jsonl")
STATE_REL = Path("memory/context/answer_discipline_visible_send_shadow_state.md")
CONTEXTUAL_RECALL_STATE_REL = Path("memory/context/contextual_recall_state.md")

DEFAULT_CONTEXT = {
    "retrieval_pressure": "none",
    "evidence_sufficiency": "usable",
    "answer_discipline": "answer_normally_current_message_first",
}


def record_visible_send_shadow(
    root: Path | str,
    *,
    reply: str,
    source: str,
    route: str = "",
    target_kind: str = "",
    session_id: str = "",
    turn_id: str = "",
    message_id: str = "",
    delivery_kind: str = "",
    reply_hash: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a non-blocking pre-send visible reply guard shadow event.

    The report intentionally stores only hashes and guard flags. It must never
    store raw prompt text, raw reply text, QQ ids, or target ids.
    """

    root_path = Path(root)
    observed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    context = _read_contextual_recall_context(root_path)
    guard = evaluate_visible_reply_for_answer_discipline(reply, context)
    safe_reply_hash = _reply_hash(reply_hash, reply)
    row: dict[str, Any] = {
        "observed_at": observed_at,
        "source": _safe_str(source),
        "shadow_only": True,
        "send_blocked": False,
        "passed": guard.passed,
        "constraint_id": guard.constraint_id,
        "flags": dict(guard.flags),
        "active_flags": [name for name, active in guard.flags.items() if active],
        "notes": list(guard.notes),
        "reply_hash": safe_reply_hash,
        "raw_reply_saved": False,
        "raw_prompt_saved": False,
        "route": _safe_str(route),
        "target_kind": _safe_str(target_kind),
        "delivery_kind": _safe_str(delivery_kind),
        "session_id_hash": _short_hash(session_id),
        "turn_id_hash": _short_hash(turn_id),
        "message_id_hash": _short_hash(message_id),
        "context": context,
        "metadata": _safe_metadata(metadata or {}),
    }
    try:
        append_visible_send_shadow_trace(root_path / TRACE_REL, row)
        write_visible_send_shadow_state(root_path / STATE_REL, _render_state(row))
    except Exception as exc:  # pragma: no cover - defensive; sending must continue
        return {
            **row,
            "recorded": False,
            "record_error": type(exc).__name__,
            "metadata": row["metadata"],
        }
    return {**row, "recorded": True}


def _read_contextual_recall_context(root: Path) -> dict[str, str]:
    path = root / CONTEXTUAL_RECALL_STATE_REL
    text = read_visible_send_shadow_context_text(path)
    if not text:
        return dict(DEFAULT_CONTEXT)
    fields = dict(DEFAULT_CONTEXT)
    for key in ("retrieval_pressure", "evidence_sufficiency", "answer_discipline"):
        value = _state_value(text, key)
        if value:
            fields[key] = value
    return fields


def _state_value(text: str, key: str) -> str:
    prefix = f"- {key}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key in (
        "outbox_source",
        "outbox_message_type",
        "source_route",
        "delivery_kind",
        "message_type",
    ):
        value = _safe_str(metadata.get(key)).strip()
        if value:
            safe[key] = value[:80]
    return safe


def _render_state(row: dict[str, Any]) -> str:
    flags = ", ".join(row.get("active_flags") or []) or "none"
    context = row.get("context") if isinstance(row.get("context"), dict) else {}
    return "\n".join(
        [
            "---",
            "title: Answer Discipline Visible Send Shadow State",
            "memory_type: answer_discipline_visible_send_shadow_state",
            "time_scope: immediate_runtime",
            "subject_ids: [xinyu, owner]",
            "protected: true",
            "source: xinyu_qq_visible_send_shadow",
            f"updated_at: {_safe_str(row.get('observed_at'))}",
            "status: active",
            "tags: [qq, visible-reply, answer-discipline, shadow]",
            "---",
            "",
            "# Answer Discipline Visible Send Shadow State",
            "",
            f"- observed_at: {_safe_str(row.get('observed_at'))}",
            f"- source: {_safe_str(row.get('source'))}",
            "- shadow_only: true",
            "- send_blocked: false",
            "- raw_reply_saved: false",
            "- raw_prompt_saved: false",
            f"- passed: {_bool_text(row.get('passed'))}",
            f"- constraint_id: {_safe_str(row.get('constraint_id'))}",
            f"- active_flags: {flags}",
            f"- reply_hash: {_safe_str(row.get('reply_hash'))}",
            f"- route: {_safe_str(row.get('route'))}",
            f"- target_kind: {_safe_str(row.get('target_kind'))}",
            f"- delivery_kind: {_safe_str(row.get('delivery_kind'))}",
            f"- retrieval_pressure: {_safe_str(context.get('retrieval_pressure'))}",
            f"- evidence_sufficiency: {_safe_str(context.get('evidence_sufficiency'))}",
            f"- answer_discipline: {_safe_str(context.get('answer_discipline'))}",
        ]
    )


def _short_hash(value: Any) -> str:
    text = _safe_str(value).strip()
    if not text:
        return ""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _reply_hash(candidate: str, reply: str) -> str:
    clean = _safe_str(candidate).strip()
    if re.fullmatch(r"sha256:[0-9a-f]{64}", clean):
        return clean
    return visible_text_hash(reply) or clean[:80]


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)
