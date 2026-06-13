from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_turn_route_trace_store import append_turn_route_trace
from xinyu_turn_route_trace_store import read_turn_route_state
from xinyu_turn_route_trace_store import read_turn_route_trace_text
from xinyu_turn_route_trace_store import write_turn_route_state


TRACE_REL = Path("runtime/turn_route_trace.jsonl")
STATE_REL = Path("runtime/turn_route_state.json")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _hash_text(value: Any) -> str:
    text = _safe_str(value).strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _payload_scope(payload: dict[str, Any] | None) -> dict[str, str]:
    data = payload if isinstance(payload, dict) else {}
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    return {
        "source": _safe_str(data.get("source") or metadata.get("source") or data.get("platform") or "unknown"),
        "message_type": _safe_str(data.get("message_type") or metadata.get("message_type") or "unknown"),
        "session_hash": _hash_text(data.get("session_id") or metadata.get("session_id")),
        "user_hash": _hash_text(data.get("user_id") or metadata.get("user_id")),
        "group_hash": _hash_text(data.get("group_id") or metadata.get("group_id")),
    }


def record_turn_route_stage(
    root: Path,
    *,
    turn_id: str,
    stage: str,
    route: str,
    status: str = "",
    elapsed_ms: int | None = None,
    payload: dict[str, Any] | None = None,
    notes: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    try:
        clean_notes = [_safe_str(note)[:160] for note in (notes or []) if _safe_str(note).strip()]
        row: dict[str, Any] = {
            "observed_at": _now_iso(),
            "turn_id": _safe_str(turn_id),
            "stage": _safe_str(stage, "unknown"),
            "route": _safe_str(route, "unknown"),
            "status": _safe_str(status),
            "notes": clean_notes[:12],
            **_payload_scope(payload),
        }
        if elapsed_ms is not None:
            row["elapsed_ms"] = max(0, _safe_int(elapsed_ms))
        append_turn_route_trace(root / TRACE_REL, row)
        write_turn_route_state(root / STATE_REL, row)
        return {"ok": True, "notes": ["turn_route_trace_recorded"]}
    except Exception as exc:
        return {"ok": False, "notes": [f"turn_route_trace_error:{type(exc).__name__}"]}


def read_turn_route_summary(root: Path) -> dict[str, Any]:
    state = read_turn_route_state(root / STATE_REL)
    if not isinstance(state, dict):
        state = {}
    last_timeout = _read_last_timeout(root / TRACE_REL)
    return {
        "available": bool(state),
        "trace_path": str(TRACE_REL),
        "state_path": str(STATE_REL),
        "last_observed_at": _safe_str(state.get("observed_at")),
        "last_turn_id": _safe_str(state.get("turn_id")),
        "last_stage": _safe_str(state.get("stage")),
        "last_route": _safe_str(state.get("route")),
        "last_status": _safe_str(state.get("status")),
        "last_elapsed_ms": _safe_int(state.get("elapsed_ms"), 0) if "elapsed_ms" in state else 0,
        "last_notes": state.get("notes", []) if isinstance(state.get("notes"), list) else [],
        "last_timeout_stage": _safe_str(last_timeout.get("stage")),
        "last_timeout_reason": _safe_str(last_timeout.get("reason")),
        "last_timeout_elapsed_ms": _safe_int(last_timeout.get("elapsed_ms"), 0)
        if "elapsed_ms" in last_timeout
        else 0,
    }


def _read_last_timeout(path: Path) -> dict[str, Any]:
    text = read_turn_route_trace_text(path)
    if not text:
        return {}
    lines = text.splitlines()
    for line in reversed(lines[-500:]):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        notes = row.get("notes", [])
        clean_notes = [_safe_str(note) for note in notes] if isinstance(notes, list) else []
        status = _safe_str(row.get("status"))
        if status != "timeout" and not any("timeout" in note.lower() for note in clean_notes):
            continue
        reason = next((note for note in clean_notes if "timeout" in note.lower()), "")
        return {
            "stage": _safe_str(row.get("stage")),
            "reason": reason or status,
            "elapsed_ms": row.get("elapsed_ms"),
        }
    return {}
