from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_promise_markers import PROMISE_FOLLOWUP_STATE_REL


def write_state(
    runtime: Any,
    followup: dict[str, str],
    *,
    status: str,
    message_id: str,
    notes: list[str],
    atomic_write_text_func: Callable[[Path, str], None],
    normalize_bridge_reply_func: Callable[[Any], str],
    dedupe_func: Callable[[list[str]], list[str]],
    safe_str_func: Callable[..., str],
    state_rel: Path = PROMISE_FOLLOWUP_STATE_REL,
) -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    note_lines = "\n".join(f"- {note}" for note in dedupe_func(notes)) or "- none"
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
- status: {safe_str_func(status, "unknown")}
- checked_at: {now}
- session_key: {safe_str_func(followup.get("session_key"), "unknown")}
- user_id: {safe_str_func(followup.get("user_id"), "unknown")}
- dedupe_key: {safe_str_func(followup.get("dedupe_key"), "unknown")}
- queued_message_id: {safe_str_func(message_id, "none") or "none"}
- owner_request: {normalize_bridge_reply_func(followup.get("user_text", ""))[:240] or "none"}
- promised_reply: {normalize_bridge_reply_func(followup.get("reply", ""))[:160] or "none"}

## Notes
{note_lines}
"""
    atomic_write_text_func(runtime.xinyu_dir / state_rel, text)
