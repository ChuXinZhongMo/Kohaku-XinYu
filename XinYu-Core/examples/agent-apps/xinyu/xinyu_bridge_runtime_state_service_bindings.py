from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_session import AgentSession


@dataclass(frozen=True)
class RuntimeServiceBindings:
    self_choice_store_cls: Callable[[Path], Any]
    action_layer_cls: Callable[[Path], Any]
    speech_controller_cls: Callable[[Path], Any]
    tts_output_cls: Callable[[Path], Any]
    renderer_cls: Callable[..., Any]
    build_state_persistence_service: Callable[[], Any]
    build_chat_service: Callable[[], Any]
    build_chat_turn_service: Callable[[], Any]
    build_learning_service: Callable[..., Any]
    build_codex_execution_service: Callable[[], Any]
    build_external_action_service: Callable[[], Any]
    build_desktop_surface_service: Callable[[], Any]
    build_proactive_delivery_service: Callable[[], Any]
    build_life_metabolism_service: Callable[[], Any]
    build_learning_ingest_service: Callable[[], Any]
    build_diagnostic_reports_service: Callable[[], Any]
    build_memory_governance_reports_service: Callable[[], Any]
    build_health_diagnostics_service: Callable[[], Any]
    load_local_env: Callable[..., Any]


def bind_runtime_services(runtime: Any, bindings: RuntimeServiceBindings) -> None:
    xinyu_dir = runtime.xinyu_dir
    runtime.self_choice_store = bindings.self_choice_store_cls(xinyu_dir)
    runtime.action_layer = bindings.action_layer_cls(xinyu_dir)
    runtime._self_choice_boot_logged = False
    runtime.speech_controller = bindings.speech_controller_cls(xinyu_dir)
    runtime.tts_output = bindings.tts_output_cls(xinyu_dir)
    runtime.renderer = bindings.renderer_cls(
        xinyu_dir=xinyu_dir,
        speech_controller=runtime.speech_controller,
        renderer_mode=runtime.renderer_mode,
        render_timeout_seconds=runtime.render_timeout_seconds,
    )
    runtime._state_persistence_service = bindings.build_state_persistence_service()
    runtime.chat_service = bindings.build_chat_service()
    runtime._chat_turn_service = bindings.build_chat_turn_service()
    runtime._codex_execution_service = bindings.build_codex_execution_service()
    runtime._external_action_service = bindings.build_external_action_service()
    runtime._desktop_surface_service = bindings.build_desktop_surface_service()
    runtime._proactive_delivery_service = bindings.build_proactive_delivery_service()
    runtime._life_metabolism_service = bindings.build_life_metabolism_service()
    runtime._learning_ingest_service = bindings.build_learning_ingest_service()
    runtime._diagnostic_reports_service = bindings.build_diagnostic_reports_service()
    runtime._memory_governance_reports_service = bindings.build_memory_governance_reports_service()
    runtime._health_diagnostics_service = bindings.build_health_diagnostics_service()
    runtime._sessions: dict[str, AgentSession] = {}
    runtime._sessions_lock = asyncio.Lock()
    runtime._global_turn_lock = asyncio.Lock()
    runtime.learning_service = bindings.build_learning_service(
        xinyu_dir=runtime.xinyu_dir,
        memory_root=runtime.memory_root,
        cleanup_idle_sessions=runtime._cleanup_idle_sessions,
        session_count=lambda: len(runtime._sessions),
        lock=runtime._global_turn_lock,
        load_local_env=bindings.load_local_env,
    )
