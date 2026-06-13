from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_codex_execution_service import CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT
from xinyu_bridge_desktop_surface_service import DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
from xinyu_bridge_external_action_service import EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN
from xinyu_bridge_proactive_delivery_service import PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
from xinyu_bridge_life_metabolism_service import LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
from xinyu_bridge_learning_ingest_service import LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
import xinyu_bridge_runtime_state


def test_initialize_runtime_sets_config_services_and_startup_traces(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _OneArgService:
        def __init__(self, root: Path) -> None:
            calls.append((type(self).__name__, root))
            self.root = root

    class _Renderer:
        def __init__(self, **kwargs: object) -> None:
            calls.append(("renderer", kwargs))
            self.kwargs = kwargs

    def fake_build_chat_service() -> str:
        calls.append(("chat_service", "built"))
        return "chat-service"

    learning_kwargs: dict[str, object] = {}

    def fake_build_learning_service(**kwargs: object) -> str:
        learning_kwargs.update(kwargs)
        calls.append(("learning_service", kwargs))
        return "learning-service"

    heartbeat_rows: list[dict[str, object]] = []
    route_rows: list[dict[str, object]] = []

    monkeypatch.setattr(xinyu_bridge_runtime_state, "SelfChoiceStore", _OneArgService)
    monkeypatch.setattr(xinyu_bridge_runtime_state, "XinyuActionLayer", _OneArgService)
    monkeypatch.setattr(xinyu_bridge_runtime_state, "XinyuSpeechController", _OneArgService)
    monkeypatch.setattr(xinyu_bridge_runtime_state, "XinYuTTSOutput", _OneArgService)
    monkeypatch.setattr(xinyu_bridge_runtime_state, "BridgeRenderer", _Renderer)
    monkeypatch.setattr(xinyu_bridge_runtime_state, "build_chat_service", fake_build_chat_service)
    monkeypatch.setattr(xinyu_bridge_runtime_state, "build_learning_service", fake_build_learning_service)
    monkeypatch.setattr(xinyu_bridge_runtime_state, "prompt_tail_entries", lambda: 11)
    monkeypatch.setattr(xinyu_bridge_runtime_state, "session_tail_entries", lambda: 12)
    monkeypatch.setattr(xinyu_bridge_runtime_state, "persisted_tail_entries", lambda: 13)
    monkeypatch.setattr(xinyu_bridge_runtime_state, "record_bridge_heartbeat", lambda *args, **kwargs: heartbeat_rows.append({"args": args, **kwargs}))
    monkeypatch.setattr(xinyu_bridge_runtime_state, "record_turn_route_stage", lambda *args, **kwargs: route_rows.append({"args": args, **kwargs}))
    monkeypatch.setattr(xinyu_bridge_runtime_state.time, "time", lambda: 123456.7)
    monkeypatch.setenv("XINYU_V1_ENABLED", "true")
    monkeypatch.setenv("XINYU_V1_SHADOW_MODE", "true")
    monkeypatch.setenv("XINYU_V1_SHADOW_TIMEOUT_SECONDS", "0")
    monkeypatch.setenv("XINYU_PRE_MODEL_ROUTES_TIMEOUT_SECONDS", "0")
    monkeypatch.setenv("XINYU_EMOTION_COUNCIL_PROMPT_ENABLED", "true")
    monkeypatch.setenv(xinyu_bridge_runtime_state.V1_OWNER_SIMPLE_CANARY_ENV, "true")
    monkeypatch.setenv("XINYU_OWNER_PRIVATE_SEMANTIC_FAST_ROUTE", "false")
    monkeypatch.setenv("XINYU_V1_CANARY_TIMEOUT_SECONDS", "0")
    monkeypatch.setenv("XINYU_OWNER_USER_IDS", "owner-b, owner-a")
    monkeypatch.setenv("XINYU_CODEX_EXECUTION_BACKEND", "worker_client")
    monkeypatch.setenv("XINYU_CODEX_EXECUTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("XINYU_EXTERNAL_ACTION_BACKEND", "dry_run")
    monkeypatch.setenv("XINYU_DESKTOP_SURFACE_BACKEND", "dry_run")
    monkeypatch.setenv("XINYU_PROACTIVE_DELIVERY_BACKEND", "dry_run")
    monkeypatch.setenv("XINYU_LIFE_METABOLISM_BACKEND", "dry_run")
    monkeypatch.setenv("XINYU_LEARNING_INGEST_BACKEND", "dry_run")

    runtime = SimpleNamespace(
        _normalize_renderer_mode=lambda mode: f"normalized:{mode}",
        _cleanup_idle_sessions=lambda: {"cleaned_sessions": 0},
    )

    xinyu_bridge_runtime_state.initialize_runtime(
        runtime,
        xinyu_bridge_runtime_state.RuntimeInitConfig(
            xinyu_dir=tmp_path,
            turn_timeout_seconds=30,
            max_text_chars=2048,
            settle_seconds=0.25,
            outward_renderer=True,
            renderer_mode="safe",
            render_timeout_seconds=9,
            session_idle_ttl_seconds=99,
            max_sessions=3,
            proactive_min_interval_seconds=44,
            autonomous_maintenance_enabled=False,
            autonomous_maintenance_initial_delay_seconds=-5,
            autonomous_maintenance_interval_seconds=10,
            autonomous_maintenance_session_key="  ",
            metabolism_runner_interval_seconds=1,
        ),
        bridge_version="version-test",
        bridge_source_digest="bridge-digest",
        bridge_runtime_source_digest="runtime-digest",
    )

    assert runtime.xinyu_dir == tmp_path
    assert runtime.bridge_version == "version-test"
    assert runtime.bridge_source_digest == "bridge-digest"
    assert runtime.bridge_runtime_source_digest == "runtime-digest"
    assert runtime.memory_root == tmp_path / "memory"
    assert runtime.renderer_mode == "normalized:safe"
    assert runtime.dialogue_prompt_tail_entries == 11
    assert runtime.dialogue_session_tail_entries == 12
    assert runtime.dialogue_persisted_tail_entries == 13
    assert runtime.autonomous_maintenance_initial_delay_seconds == 0
    assert runtime.autonomous_maintenance_interval_seconds == 60
    assert runtime.autonomous_maintenance_session_key == "xinyu:autonomous:maintenance"
    assert runtime.metabolism_runner_interval_seconds == 5
    assert runtime.v1_enabled is True
    assert runtime.v1_shadow_mode is True
    assert runtime.v1_shadow_timeout_seconds == 1
    assert runtime.pre_model_routes_timeout_seconds == 1
    assert runtime.emotion_council_prompt_enabled is True
    assert runtime.v1_owner_simple_canary is True
    assert runtime.owner_private_semantic_fast_route is False
    assert runtime.v1_canary_timeout_seconds == 1
    assert runtime.v1_owner_user_ids == {"owner-a", "owner-b"}
    assert runtime.chat_service == "chat-service"
    state_persistence_readiness = runtime._state_persistence_service.readiness(runtime)
    assert state_persistence_readiness.service_id == "state_persistence"
    assert state_persistence_readiness.started is False
    assert state_persistence_readiness.local_only is True
    assert state_persistence_readiness.process_split_candidate is False
    chat_turn_readiness = runtime._chat_turn_service.readiness(runtime)
    assert chat_turn_readiness.service_id == "chat_turn"
    assert chat_turn_readiness.started is False
    assert chat_turn_readiness.local_only is True
    assert chat_turn_readiness.process_split_candidate is False
    assert runtime.learning_service == "learning-service"
    assert runtime._desktop_event_stream_service is None
    assert runtime.desktop_event_bus is None
    assert runtime.desktop_ws_server is None
    assert learning_kwargs["xinyu_dir"] == tmp_path
    assert learning_kwargs["memory_root"] == tmp_path / "memory"
    assert learning_kwargs["cleanup_idle_sessions"] is runtime._cleanup_idle_sessions
    assert learning_kwargs["session_count"]() == 0
    runtime._sessions["session-1"] = object()
    assert learning_kwargs["session_count"]() == 1
    assert runtime._desktop_recent_turns == []
    assert runtime._desktop_proactive_inbox == {}
    assert runtime._metabolism_last_result == {}
    assert runtime._autonomous_last_memory_changed == "unknown"
    assert runtime._v1_app is None
    codex_service_readiness = runtime._codex_execution_service.readiness()
    assert codex_service_readiness.mode == CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT
    assert codex_service_readiness.backend_mode == "in_process_runtime_delegate_backend"
    external_action_readiness = runtime._external_action_service.readiness()
    assert external_action_readiness.mode == EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN
    assert external_action_readiness.backend_mode == "disabled_contract_only_dry_run_backend"
    desktop_surface_readiness = runtime._desktop_surface_service.readiness(runtime)
    assert desktop_surface_readiness.mode == DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    assert desktop_surface_readiness.route_backend_mode == "disabled_contract_only_route_backend"
    proactive_delivery_readiness = runtime._proactive_delivery_service.readiness()
    assert proactive_delivery_readiness.mode == PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    assert proactive_delivery_readiness.route_backend_mode == "disabled_contract_only_route_backend"
    life_metabolism_readiness = runtime._life_metabolism_service.readiness(runtime)
    assert life_metabolism_readiness.mode == LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    assert life_metabolism_readiness.route_backend_mode == "disabled_contract_only_life_metabolism_route_backend"
    assert life_metabolism_readiness.local_only is True
    learning_ingest_readiness = runtime._learning_ingest_service.readiness(runtime)
    assert learning_ingest_readiness.mode == LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    assert learning_ingest_readiness.route_backend_mode == "disabled_contract_only_learning_route_backend"
    assert learning_ingest_readiness.local_only is True
    assert learning_ingest_readiness.process_split_candidate is False
    diagnostic_reports_readiness = runtime._diagnostic_reports_service.readiness(runtime)
    assert diagnostic_reports_readiness.service_id == "diagnostic_reports"
    assert diagnostic_reports_readiness.local_only is True
    assert diagnostic_reports_readiness.process_split_candidate is False
    memory_governance_readiness = runtime._memory_governance_reports_service.readiness(runtime)
    assert memory_governance_readiness.service_id == "memory_governance_reports"
    assert memory_governance_readiness.local_only is True
    assert memory_governance_readiness.process_split_candidate is False
    health_diagnostics_readiness = runtime._health_diagnostics_service.readiness()
    assert health_diagnostics_readiness.service_id == "health_diagnostics"
    assert health_diagnostics_readiness.started is False
    assert health_diagnostics_readiness.ready is False
    assert runtime._closed is False
    assert heartbeat_rows == [
        {
            "args": (tmp_path,),
            "reason": "bridge_init",
            "bridge_snapshot": {
                "active_sessions": 0,
                "autonomous_maintenance": "disabled",
                "qq_outbox": "unknown",
            },
        }
    ]
    assert route_rows == [
        {
            "args": (tmp_path,),
            "turn_id": "bridge-startup-123456",
            "stage": "bridge_started",
            "route": "idle",
            "status": "ok",
            "elapsed_ms": 0,
            "notes": ["bridge_init"],
        }
    ]
    assert ("chat_service", "built") in calls
    assert any(name == "learning_service" for name, _ in calls)
