from __future__ import annotations

from typing import Any


def build_pre_model_phase_deps(hooks: Any) -> dict[str, Any]:
    return {
        "publish_started_func": hooks.publish_chat_started_with_trace,
        "memory_snapshot_func": hooks.capture_memory_snapshot_with_trace,
        "observations_func": hooks.run_pre_model_observation_sidecars_with_trace,
        "routes_with_timeout_func": hooks.run_pre_model_routes_with_timeout,
        "route_runner_func": hooks.run_pre_model_routes,
        "safe_str_func": hooks._safe_str,
    }


def build_observation_deps(hooks: Any) -> dict[str, Any]:
    return {
        "curiosity_func": hooks.evaluate_previous_reaction,
        "private_thought_func": hooks.record_private_thought_outcome,
        "uncertainty_pause_func": hooks.mark_uncertainty_pause_replied,
        "observed_at_func": lambda: hooks.datetime.now().astimezone().isoformat(),
    }


def build_routes_timeout_deps(hooks: Any, *, runner: Any = None) -> dict[str, Any]:
    return {
        "runner": runner or hooks.run_pre_model_routes,
        "wait_for_func": hooks.asyncio.wait_for,
    }


def build_routes_dispatch_deps(hooks: Any) -> dict[str, Any]:
    return {
        "runtime_repair_status_func": hooks._maybe_handle_runtime_repair_status_turn,
        "tinykernel_shadow_func": hooks._run_tinykernel_shadow,
        "event_recorder_func": hooks.record_chat_event,
        "to_thread_func": hooks.asyncio.to_thread,
    }


def build_tinykernel_deps(hooks: Any) -> dict[str, Any]:
    return {
        "shadow_enabled_func": hooks.shadow_enabled,
        "record_shadow_func": hooks.record_tinykernel_shadow,
        "to_thread_func": hooks.asyncio.to_thread,
        "timestamp_func": hooks._timestamp_or_now_iso,
        "safe_str_func": hooks._safe_str,
    }


def build_runtime_repair_status_deps(hooks: Any) -> dict[str, Any]:
    return {
        "status_question_func": hooks._looks_like_runtime_repair_status_question,
        "source_digest_func": hooks.source_file_digest,
        "tcp_connect_func": hooks._tcp_connect,
        "memory_snapshot_func": hooks._memory_snapshot,
        "finish_coherence_func": hooks.finish_turn_coherence,
        "clock_func": hooks.time.perf_counter,
        "record_finished_func": hooks.record_turn_finished,
        "visible_hash_func": hooks.visible_text_hash,
        "timestamp_func": hooks._timestamp_or_now_iso,
        "safe_str_func": hooks._safe_str,
    }


__all__ = [
    "build_observation_deps",
    "build_pre_model_phase_deps",
    "build_routes_dispatch_deps",
    "build_routes_timeout_deps",
    "build_runtime_repair_status_deps",
    "build_tinykernel_deps",
]
