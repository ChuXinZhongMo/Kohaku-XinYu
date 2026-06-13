from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_action_layer import XinyuActionLayer
from xinyu_bridge_bootstrap import load_local_env
from xinyu_bridge_chat_turn_service import build_chat_turn_service_handle
from xinyu_bridge_codex_execution_service import (
    build_codex_execution_service_handle,
    codex_execution_service_config_from_env,
)
from xinyu_bridge_external_action_service import (
    build_external_action_service_handle,
    external_action_service_config_from_env,
)
from xinyu_bridge_desktop_surface_service import (
    build_desktop_surface_service_handle,
    desktop_surface_service_config_from_env,
)
from xinyu_bridge_health_snapshot import build_runtime_health_diagnostics_service
from xinyu_bridge_proactive_delivery_service import (
    build_proactive_delivery_service_handle,
    proactive_delivery_service_config_from_env,
)
from xinyu_bridge_life_metabolism_service import (
    build_life_metabolism_service_handle,
    life_metabolism_service_config_from_env,
)
from xinyu_bridge_learning_ingest_service import (
    build_learning_ingest_service_handle,
    learning_ingest_service_config_from_env,
)
from xinyu_bridge_local_report_services import (
    build_diagnostic_reports_service_handle,
    build_memory_governance_reports_service_handle,
    diagnostic_reports_service_config_from_env,
    memory_governance_reports_service_config_from_env,
)
from xinyu_bridge_renderer import BridgeRenderer
from xinyu_bridge_session import AgentSession
from xinyu_bridge_runtime_state_payloads import (
    build_runtime_environment_state,
    build_runtime_interval_state,
    build_startup_bridge_snapshot,
    build_startup_route_payload,
)
from xinyu_bridge_runtime_state_service_bindings import RuntimeServiceBindings, bind_runtime_services
from xinyu_bridge_runtime_state_mutable import reset_runtime_mutable_state
from xinyu_bridge_runtime_state_startup import record_runtime_startup_traces
from xinyu_bridge_state_persistence_service import build_state_persistence_service_handle
from xinyu_bridge_values import as_bool, as_int, as_str_set
from xinyu_chat_service import build_chat_service
from xinyu_dialogue_working_memory import persisted_tail_entries, prompt_tail_entries, session_tail_entries
from xinyu_learning_service import build_learning_service
from xinyu_runtime_presence import record_bridge_heartbeat
from xinyu_self_choice_store import SelfChoiceStore
from xinyu_speech_controller import XinyuSpeechController
from xinyu_tts_output import XinYuTTSOutput
from xinyu_turn_route_trace import record_turn_route_stage
from xinyu_bridge_v1_routes import V1_OWNER_SIMPLE_CANARY_ENV


@dataclass(frozen=True)
class RuntimeInitConfig:
    xinyu_dir: Path
    turn_timeout_seconds: int
    max_text_chars: int
    settle_seconds: float
    outward_renderer: bool
    renderer_mode: str = "off"
    render_timeout_seconds: int = 60
    session_idle_ttl_seconds: int = 86400
    max_sessions: int = 8
    proactive_min_interval_seconds: int = 21600
    autonomous_maintenance_enabled: bool = True
    autonomous_maintenance_initial_delay_seconds: int = 60
    autonomous_maintenance_interval_seconds: int = 1800
    autonomous_maintenance_session_key: str = "xinyu:autonomous:maintenance"
    metabolism_runner_interval_seconds: int = 30


def initialize_runtime(
    runtime: Any,
    config: RuntimeInitConfig,
    *,
    bridge_version: str,
    bridge_source_digest: str,
    bridge_runtime_source_digest: str,
) -> None:
    xinyu_dir = config.xinyu_dir
    runtime.xinyu_dir = xinyu_dir
    runtime.bridge_version = bridge_version
    runtime.bridge_source_digest = bridge_source_digest
    runtime.bridge_runtime_source_digest = bridge_runtime_source_digest
    runtime.memory_root = xinyu_dir / "memory"
    runtime.turn_timeout_seconds = config.turn_timeout_seconds
    runtime.max_text_chars = config.max_text_chars
    runtime.settle_seconds = config.settle_seconds
    runtime.outward_renderer = config.outward_renderer
    runtime.renderer_mode = runtime._normalize_renderer_mode(config.renderer_mode)
    runtime.render_timeout_seconds = config.render_timeout_seconds
    runtime.session_idle_ttl_seconds = config.session_idle_ttl_seconds
    runtime.dialogue_prompt_tail_entries = prompt_tail_entries()
    runtime.dialogue_session_tail_entries = session_tail_entries()
    runtime.dialogue_persisted_tail_entries = persisted_tail_entries()
    runtime.max_sessions = config.max_sessions
    runtime.proactive_min_interval_seconds = config.proactive_min_interval_seconds
    runtime.autonomous_maintenance_enabled = config.autonomous_maintenance_enabled
    interval_state = build_runtime_interval_state(
        autonomous_maintenance_initial_delay_seconds=config.autonomous_maintenance_initial_delay_seconds,
        autonomous_maintenance_interval_seconds=config.autonomous_maintenance_interval_seconds,
        autonomous_maintenance_session_key=config.autonomous_maintenance_session_key,
        metabolism_runner_interval_seconds=config.metabolism_runner_interval_seconds,
    )
    runtime.autonomous_maintenance_initial_delay_seconds = (
        interval_state.autonomous_maintenance_initial_delay_seconds
    )
    runtime.autonomous_maintenance_interval_seconds = interval_state.autonomous_maintenance_interval_seconds
    runtime.autonomous_maintenance_session_key = interval_state.autonomous_maintenance_session_key
    runtime.metabolism_runner_interval_seconds = interval_state.metabolism_runner_interval_seconds
    environment_state = build_runtime_environment_state(
        os.environ,
        v1_owner_simple_canary_env=V1_OWNER_SIMPLE_CANARY_ENV,
        as_bool_fn=as_bool,
        as_int_fn=as_int,
        as_str_set_fn=as_str_set,
    )
    runtime.v1_enabled = environment_state.v1_enabled
    runtime.v1_shadow_mode = environment_state.v1_shadow_mode
    runtime.v1_shadow_timeout_seconds = environment_state.v1_shadow_timeout_seconds
    runtime.pre_model_routes_timeout_seconds = environment_state.pre_model_routes_timeout_seconds
    runtime.emotion_council_prompt_enabled = environment_state.emotion_council_prompt_enabled
    runtime.v1_owner_simple_canary = environment_state.v1_owner_simple_canary
    runtime.owner_private_semantic_fast_route = environment_state.owner_private_semantic_fast_route
    runtime.v1_canary_timeout_seconds = environment_state.v1_canary_timeout_seconds
    runtime.v1_owner_user_ids = environment_state.v1_owner_user_ids
    bind_runtime_services(
        runtime,
        RuntimeServiceBindings(
            self_choice_store_cls=SelfChoiceStore,
            action_layer_cls=XinyuActionLayer,
            speech_controller_cls=XinyuSpeechController,
            tts_output_cls=XinYuTTSOutput,
            renderer_cls=BridgeRenderer,
            build_state_persistence_service=build_state_persistence_service_handle,
            build_chat_service=build_chat_service,
            build_chat_turn_service=build_chat_turn_service_handle,
            build_learning_service=build_learning_service,
            build_codex_execution_service=lambda: build_codex_execution_service_handle(
                codex_execution_service_config_from_env(os.environ)
            ),
            build_external_action_service=lambda: build_external_action_service_handle(
                external_action_service_config_from_env(os.environ)
            ),
            build_desktop_surface_service=lambda: build_desktop_surface_service_handle(
                desktop_surface_service_config_from_env(os.environ)
            ),
            build_proactive_delivery_service=lambda: build_proactive_delivery_service_handle(
                proactive_delivery_service_config_from_env(os.environ)
            ),
            build_life_metabolism_service=lambda: build_life_metabolism_service_handle(
                life_metabolism_service_config_from_env(os.environ)
            ),
            build_learning_ingest_service=lambda: build_learning_ingest_service_handle(
                learning_ingest_service_config_from_env(os.environ)
            ),
            build_diagnostic_reports_service=lambda: build_diagnostic_reports_service_handle(
                diagnostic_reports_service_config_from_env(os.environ)
            ),
            build_memory_governance_reports_service=lambda: build_memory_governance_reports_service_handle(
                memory_governance_reports_service_config_from_env(os.environ)
            ),
            build_health_diagnostics_service=build_runtime_health_diagnostics_service,
            load_local_env=load_local_env,
        ),
    )
    reset_runtime_mutable_state(runtime)
    record_runtime_startup_traces(
        runtime,
        started_at_seconds=time.time(),
        build_startup_bridge_snapshot_func=build_startup_bridge_snapshot,
        build_startup_route_payload_func=build_startup_route_payload,
        record_bridge_heartbeat_func=record_bridge_heartbeat,
        record_turn_route_stage_func=record_turn_route_stage,
    )
