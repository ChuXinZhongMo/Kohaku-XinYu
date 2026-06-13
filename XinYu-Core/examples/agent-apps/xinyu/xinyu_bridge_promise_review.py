from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_promise_markers import (
    PROMISE_FOLLOWUP_DONE_MARKERS,
    PROMISE_FOLLOWUP_REPLY_MARKERS,
    PROMISE_FOLLOWUP_USER_MARKERS,
)


def schedule_if_needed(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    message_func: Callable[[dict[str, str]], str],
    candidate_func: Callable[..., dict[str, str]],
    write_state_func: Callable[..., None],
    run_review_func: Callable[..., dict[str, Any]],
    create_task_func: Callable[..., Any],
    to_thread_func: Callable[..., Any],
    user_markers: tuple[str, ...] = PROMISE_FOLLOWUP_USER_MARKERS,
    reply_markers: tuple[str, ...] = PROMISE_FOLLOWUP_REPLY_MARKERS,
    done_markers: tuple[str, ...] = PROMISE_FOLLOWUP_DONE_MARKERS,
    model_codex_task: str = "",
) -> dict[str, Any]:
    followup = candidate_func(
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

    write_state_func(runtime, followup, status="scheduled", message_id="none", notes=["scheduled"])
    create_task_func(
        to_thread_func(run_review_func, runtime, followup, message_func=message_func),
        name=f"xinyu-promised-followup-{followup['dedupe_key'].split(':')[-1]}",
    )
    return {"scheduled": True, "notes": ["promised_followup_scheduled"]}


def run_review(
    runtime: Any,
    followup: dict[str, str],
    *,
    message_func: Callable[[dict[str, str]], str],
    enqueue_message_func: Callable[..., dict[str, Any]],
    write_state_func: Callable[..., None],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    notes = ["reviewed_runtime_followup_contract"]
    message = message_func(followup)
    queued = enqueue_message_func(
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
    notes.extend(safe_str_func(note) for note in queued.get("notes", []))
    status = "queued" if queued.get("queued") or queued.get("accepted") else "failed"
    write_state_func(
        runtime,
        followup,
        status=status,
        message_id=safe_str_func(queued.get("message_id")),
        notes=notes,
    )
    return {
        "scheduled": True,
        "queued": bool(queued.get("queued")),
        "message_id": queued.get("message_id", ""),
        "notes": notes,
    }
