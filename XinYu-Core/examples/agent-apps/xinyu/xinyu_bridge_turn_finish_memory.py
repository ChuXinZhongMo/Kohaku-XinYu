from __future__ import annotations

from typing import Any, Callable


def archive_dialogue_turn_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    visible_turn: Any,
    final_guard_flags: list[str],
    archive_dialogue_turn_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    try:
        return archive_dialogue_turn_func(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            assistant_reply=reply,
            message_type=safe_str_func(getattr(visible_turn, "turn_kind", "")),
            quality_flags=final_guard_flags,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] dialogue archive failed: {exc}", flush=True)
        return {"notes": [f"dialogue_archive_error:{type(exc).__name__}"], "message_ids": []}


def extract_memory_candidates_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    archive_result: dict[str, Any],
    session: Any,
    visible_turn: Any,
    final_guard_flags: list[str],
    post_reply_observation: dict[str, Any] | None,
    extract_memory_candidates_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        return extract_memory_candidates_func(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            assistant_reply=reply,
            source_message_ids=list(archive_result.get("message_ids", [])),
            dialogue_tail=session.dialogue_tail,
            visible_turn=visible_turn,
            quality_flags=final_guard_flags,
            post_reply_observation=post_reply_observation,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] memory candidate extraction failed: {exc}", flush=True)
        return {"notes": [f"memory_candidate_error:{type(exc).__name__}"]}


def run_memory_self_review_sidecar(
    runtime: Any,
    *,
    run_memory_self_review_func: Callable[..., dict[str, Any]],
    run_memory_candidate_maintenance_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    try:
        result = run_memory_self_review_func(runtime.xinyu_dir)
        try:
            maintenance = run_memory_candidate_maintenance_func(runtime.xinyu_dir)
            result["candidate_maintenance"] = maintenance
            if int(maintenance.get("backfill", {}).get("backfilled") or 0) or int(
                maintenance.get("cleanup", {}).get("archived") or 0
            ):
                result.setdefault("notes", []).append(
                    "memory_candidate_maintenance:"
                    f"{safe_str_func(maintenance.get('backfill', {}).get('backfilled'), '0')}/"
                    f"{safe_str_func(maintenance.get('cleanup', {}).get('archived'), '0')}"
                )
        except Exception as exc:
            print(f"[xinyu_core_bridge] memory candidate maintenance failed: {exc}", flush=True)
            result.setdefault("notes", []).append(f"memory_candidate_maintenance_error:{type(exc).__name__}")
        if int(result.get("reviewed_candidates") or 0) > 0:
            result.setdefault("notes", []).append(
                "memory_self_review:"
                f"{safe_str_func(result.get('reviewed_candidates'), '0')}/"
                f"{safe_str_func(result.get('self_approved'), '0')}/"
                f"{safe_str_func(result.get('observe_more'), '0')}/"
                f"{safe_str_func(result.get('owner_review_required'), '0')}/"
                f"{safe_str_func(result.get('blocked'), '0')}"
            )
        return result
    except Exception as exc:
        print(f"[xinyu_core_bridge] memory self-review failed: {exc}", flush=True)
        return {"notes": [f"memory_self_review_error:{type(exc).__name__}"]}


def record_interaction_journal_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
    visible_turn: Any,
    turn_id: str,
    turn_started_at: float,
    record_interaction_turn_func: Callable[..., dict[str, Any]],
    ensure_recent_context_health_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
    perf_counter_func: Callable[[], float],
) -> dict[str, Any]:
    try:
        result = record_interaction_turn_func(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            session_key=session_key,
            source="qq_gateway",
            turn_kind=safe_str_func(getattr(visible_turn, "turn_kind", "")),
            turn_id=turn_id,
            elapsed_ms=int((perf_counter_func() - turn_started_at) * 1000),
        )
        recent_context_guard = ensure_recent_context_health_func(runtime.xinyu_dir)
        result.setdefault("notes", []).append(
            "recent_context_guard:"
            f"{safe_str_func(recent_context_guard.get('status'))}/"
            f"{safe_str_func(recent_context_guard.get('action'))}"
        )
        return result
    except Exception as exc:
        print(f"[xinyu_core_bridge] interaction journal failed: {exc}", flush=True)
        return {"notes": [f"interaction_journal_error:{type(exc).__name__}"]}
