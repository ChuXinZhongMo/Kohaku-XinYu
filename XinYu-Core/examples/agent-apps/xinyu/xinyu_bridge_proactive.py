from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_proactive_presence import acknowledge_proactive_qq_message, claim_proactive_qq_message


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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


def _as_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


async def claim_or_preview(
    *,
    xinyu_dir: Path,
    memory_root: Path,
    payload: dict[str, Any],
    proactive_min_interval_seconds: int,
    cleanup_idle_sessions: Callable[..., Any],
    session_count: Callable[[], int],
    lock: Any,
) -> dict[str, Any]:
    claim = _as_bool(payload.get("claim"), default=True)
    min_interval_seconds = _as_int(payload.get("min_interval_seconds"), proactive_min_interval_seconds)
    if min_interval_seconds < 0:
        raise ValueError("min_interval_seconds must be >= 0")
    claim_id = _safe_str(payload.get("claim_id")).strip() or f"bridge-{int(time.time())}"

    # Proactive QQ claim/ack is a file-backed adapter handshake, not an agent
    # turn. Keeping it outside the global turn lock prevents QQ outbox polling
    # from timing out while autonomous maintenance or a live reply is running.
    _ = lock
    cleanup = await cleanup_idle_sessions()
    before_memory = _memory_snapshot(memory_root)
    result = claim_proactive_qq_message(
        xinyu_dir,
        mode="bridge_proactive_qq_claim" if claim else "bridge_proactive_qq_preview",
        claim=claim,
        claim_id=claim_id,
        min_interval_seconds=min_interval_seconds,
    )
    after_memory = _memory_snapshot(memory_root)

    notes = list(result.get("notes", []))
    if cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    return {
        **result,
        "memory_changed": before_memory != after_memory,
        "session_created": False,
        "sessions": session_count(),
        "notes": notes,
    }


async def acknowledge(
    *,
    xinyu_dir: Path,
    memory_root: Path,
    payload: dict[str, Any],
    cleanup_idle_sessions: Callable[..., Any],
    session_count: Callable[[], int],
    lock: Any,
) -> dict[str, Any]:
    claim_id = _safe_str(payload.get("claim_id")).strip()
    ack_status = _safe_str(payload.get("ack_status") or payload.get("status"), "sent").strip()
    adapter_message_id = _safe_str(payload.get("adapter_message_id") or payload.get("message_id")).strip()
    adapter_error = _safe_str(payload.get("adapter_error") or payload.get("error")).strip()

    # See claim_or_preview: ack should not wait for the agent-turn lock either.
    _ = lock
    cleanup = await cleanup_idle_sessions()
    before_memory = _memory_snapshot(memory_root)
    result = acknowledge_proactive_qq_message(
        xinyu_dir,
        claim_id=claim_id,
        ack_status=ack_status,
        adapter_message_id=adapter_message_id,
        adapter_error=adapter_error,
    )
    after_memory = _memory_snapshot(memory_root)

    notes = list(result.get("notes", []))
    if cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    return {
        **result,
        "memory_changed": before_memory != after_memory,
        "session_created": False,
        "sessions": session_count(),
        "notes": notes,
    }
