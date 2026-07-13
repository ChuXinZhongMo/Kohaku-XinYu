from __future__ import annotations

from typing import Any, Callable, NamedTuple


class MemoryFinishResult(NamedTuple):
    archive_result: dict[str, Any]
    candidate_result: dict[str, Any]
    memory_self_review: dict[str, Any]
    interaction_journal: dict[str, Any]
    kernel_post_turn: dict[str, Any]


def _record_recalled_context_log(
    runtime: Any,
    *,
    recalled_context: Any,
    recalled_context_notes: list[str],
    log_living_memory_recall_func: Callable[..., bool],
) -> None:
    if recalled_context is None or not getattr(recalled_context, "items", ()):
        return
    try:
        if log_living_memory_recall_func(runtime.xinyu_dir, recalled_context):
            recalled_context_notes.append("recalled_context_logged")
    except Exception as exc:
        print(f"[xinyu_core_bridge] recalled context log failed: {exc}", flush=True)
        recalled_context_notes.append(f"recalled_context_log_error:{type(exc).__name__}")


def run_memory_archive_finish_sidecars(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session: Any,
    session_key: str,
    turn_id: str,
    turn_started_at: float,
    visible_turn: Any,
    final_guard_flags: list[str],
    recalled_context: Any,
    recalled_context_notes: list[str],
    post_reply_observation: dict[str, Any],
    archive_dialogue_turn_func: Callable[..., dict[str, Any]],
    log_living_memory_recall_func: Callable[..., bool],
    extract_memory_candidates_func: Callable[..., dict[str, Any]],
    run_memory_self_review_func: Callable[..., dict[str, Any]],
    record_interaction_journal_func: Callable[..., dict[str, Any]],
    run_kernel_post_turn_func: Callable[..., dict[str, Any]],
    event_sidecar: dict[str, Any] | None = None,
) -> MemoryFinishResult:
    archive_result = archive_dialogue_turn_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
    )
    _record_recalled_context_log(
        runtime,
        recalled_context=recalled_context,
        recalled_context_notes=recalled_context_notes,
        log_living_memory_recall_func=log_living_memory_recall_func,
    )
    candidate_result = extract_memory_candidates_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        archive_result=archive_result,
        session=session,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
        post_reply_observation=post_reply_observation,
    )
    memory_self_review = run_memory_self_review_func(runtime)
    interaction_journal = record_interaction_journal_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
        visible_turn=visible_turn,
        turn_id=turn_id,
        turn_started_at=turn_started_at,
    )
    kernel_post_turn = run_kernel_post_turn_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        turn_id=turn_id,
        event_sidecar=event_sidecar,
    )
    return MemoryFinishResult(
        archive_result=archive_result,
        candidate_result=candidate_result,
        memory_self_review=memory_self_review,
        interaction_journal=interaction_journal,
        kernel_post_turn=kernel_post_turn,
    )
