from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from state_service import atomic_write_text
from xinyu_bridge_payload_policy import owner_private_payload_matches
from xinyu_bridge_promises import compact_promise_text
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_values import as_str_set, dedupe, safe_str
from xinyu_qq_outbox import enqueue_qq_outbox_message


PROMISE_FOLLOWUP_STATE_REL = Path("memory/context/promise_followup_state.md")


def owner_private_user_id(runtime: Any) -> str:
    if runtime.v1_owner_user_ids:
        return sorted(runtime.v1_owner_user_ids)[0]

    env_owner_ids = as_str_set(os.environ.get("XINYU_OWNER_USER_IDS"))
    if env_owner_ids:
        return sorted(env_owner_ids)[0]

    config_path = runtime.xinyu_dir / "xinyu_qq_gateway.config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return ""
    owner_ids = as_str_set(data.get("owner_user_ids") if isinstance(data, dict) else None)
    return sorted(owner_ids)[0] if owner_ids else ""


def candidate(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    user_markers: tuple[str, ...],
    reply_markers: tuple[str, ...],
    done_markers: tuple[str, ...],
    model_codex_task: str = "",
) -> dict[str, str]:
    if model_codex_task:
        return {}
    if not owner_private_payload_matches(payload):
        return {}
    user_id = safe_str(payload.get("user_id")).strip() or owner_private_user_id(runtime)
    if not user_id:
        return {}
    compact_user = compact_promise_text(user_text)
    compact_reply = compact_promise_text(reply)
    if not any(marker in compact_user for marker in user_markers):
        return {}
    if not any(marker in compact_reply for marker in reply_markers):
        return {}
    if any(marker in compact_reply for marker in done_markers):
        return {}
    digest = hashlib.sha1(f"{session_key}\n{user_text}\n{reply}".encode("utf-8", errors="replace")).hexdigest()[:16]
    return {
        "user_id": user_id,
        "session_key": session_key,
        "user_text": safe_str(user_text).strip(),
        "reply": safe_str(reply).strip(),
        "dedupe_key": f"promise_followup:{digest}",
    }


def schedule_if_needed(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    user_markers: tuple[str, ...],
    reply_markers: tuple[str, ...],
    done_markers: tuple[str, ...],
    message_func: Callable[[dict[str, str]], str],
    model_codex_task: str = "",
) -> dict[str, Any]:
    followup = candidate(
        runtime,
        payload,
        user_text=user_text,
        reply=reply,
        session_key=session_key,
        user_markers=user_markers,
        reply_markers=reply_markers,
        done_markers=done_markers,
        model_codex_task=model_codex_task,
    )
    if not followup:
        return {"scheduled": False, "notes": []}
    write_state(runtime, followup, status="scheduled", message_id="none", notes=["scheduled"])
    asyncio.create_task(
        asyncio.to_thread(run_review, runtime, followup, message_func=message_func),
        name=f"xinyu-promised-followup-{followup['dedupe_key'].split(':')[-1]}",
    )
    return {"scheduled": True, "notes": ["promised_followup_scheduled"]}


def run_review(
    runtime: Any,
    followup: dict[str, str],
    *,
    message_func: Callable[[dict[str, str]], str],
) -> dict[str, Any]:
    notes = ["reviewed_runtime_followup_contract"]
    message = message_func(followup)
    queued = enqueue_qq_outbox_message(
        runtime.xinyu_dir,
        user_id=followup["user_id"],
        message=message,
        source="promise_followup",
        dedupe_key=followup["dedupe_key"],
        metadata={
            "session_key": followup.get("session_key", ""),
            "origin_user_text": followup.get("user_text", "")[:240],
            "origin_reply": followup.get("reply", "")[:120],
            "followup_kind": "promised_review_completion",
        },
    )
    notes.extend(safe_str(note) for note in queued.get("notes", []))
    status = "queued" if queued.get("queued") or queued.get("accepted") else "failed"
    write_state(
        runtime,
        followup,
        status=status,
        message_id=safe_str(queued.get("message_id")),
        notes=notes,
    )
    return {
        "scheduled": True,
        "queued": bool(queued.get("queued")),
        "message_id": queued.get("message_id", ""),
        "notes": notes,
    }


def write_state(
    runtime: Any,
    followup: dict[str, str],
    *,
    status: str,
    message_id: str,
    notes: list[str],
    state_rel: Path = PROMISE_FOLLOWUP_STATE_REL,
) -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    note_lines = "\n".join(f"- {note}" for note in dedupe(notes)) or "- none"
    text = f"""---
title: Promise Followup State
memory_type: promise_followup_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_core_bridge
updated_at: {now}
status: active
tags: [promise, followup, qq-outbox, continuity]
---

# Promise Followup State

## Latest Promise
- status: {safe_str(status, "unknown")}
- checked_at: {now}
- session_key: {safe_str(followup.get("session_key"), "unknown")}
- user_id: {safe_str(followup.get("user_id"), "unknown")}
- dedupe_key: {safe_str(followup.get("dedupe_key"), "unknown")}
- queued_message_id: {safe_str(message_id, "none") or "none"}
- owner_request: {normalize_bridge_reply(followup.get("user_text", ""))[:240] or "none"}
- promised_reply: {normalize_bridge_reply(followup.get("reply", ""))[:160] or "none"}

## Notes
{note_lines}
"""
    atomic_write_text(runtime.xinyu_dir / state_rel, text)
