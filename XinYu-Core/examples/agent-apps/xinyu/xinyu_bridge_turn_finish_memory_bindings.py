from __future__ import annotations

from typing import Any, Callable


FacadeGlobals = Callable[[], dict[str, Any]]


def bind_archive_dialogue_turn(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _archive_dialogue_turn(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        visible_turn: Any,
        final_guard_flags: list[str],
    ) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_archive_dialogue_turn"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            visible_turn=visible_turn,
            final_guard_flags=final_guard_flags,
            archive_dialogue_turn_func=facade["archive_dialogue_turn"],
            safe_str_func=facade["_safe_str"],
        )

    return _archive_dialogue_turn


def bind_extract_memory_candidates(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _extract_memory_candidates(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        archive_result: dict[str, Any],
        session: Any,
        visible_turn: Any,
        final_guard_flags: list[str],
        post_reply_observation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_extract_memory_candidates"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            archive_result=archive_result,
            session=session,
            visible_turn=visible_turn,
            final_guard_flags=final_guard_flags,
            post_reply_observation=post_reply_observation,
            extract_memory_candidates_func=facade["extract_memory_candidates"],
        )

    return _extract_memory_candidates


def bind_run_memory_self_review(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _run_memory_self_review(runtime: Any) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_run_memory_self_review"](
            runtime,
            run_memory_self_review_func=facade["run_memory_self_review"],
            run_memory_candidate_maintenance_func=facade["run_memory_candidate_maintenance"],
            safe_str_func=facade["_safe_str"],
        )

    return _run_memory_self_review


def bind_run_kernel_post_turn(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _run_kernel_post_turn(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        turn_id: str,
        event_sidecar: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_run_kernel_post_turn"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            turn_id=turn_id,
            event_sidecar=event_sidecar,
            run_kernel_post_turn_cycle_func=facade["run_kernel_post_turn_cycle"],
        )

    return _run_kernel_post_turn


def bind_record_interaction_journal(facade_globals: FacadeGlobals) -> Callable[..., dict[str, Any]]:
    def _record_interaction_journal(
        runtime: Any,
        *,
        payload: dict[str, Any],
        text: str,
        reply: str,
        session_key: str,
        visible_turn: Any,
        turn_id: str,
        turn_started_at: float,
    ) -> dict[str, Any]:
        facade = facade_globals()
        return facade["_runtime_record_interaction_journal"](
            runtime,
            payload=payload,
            text=text,
            reply=reply,
            session_key=session_key,
            visible_turn=visible_turn,
            turn_id=turn_id,
            turn_started_at=turn_started_at,
            record_interaction_turn_func=facade["record_interaction_turn"],
            ensure_recent_context_health_func=facade["ensure_recent_context_health"],
            safe_str_func=facade["_safe_str"],
            perf_counter_func=facade["time"].perf_counter,
        )

    return _record_interaction_journal
