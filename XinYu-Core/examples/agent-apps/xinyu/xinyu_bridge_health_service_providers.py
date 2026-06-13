from __future__ import annotations

from dataclasses import asdict, is_dataclass
from types import SimpleNamespace
from typing import Any, Mapping

from xinyu_bridge_chat_turn_contract import ChatTurnHarness
from xinyu_bridge_chat_turn_service import chat_turn_service_readiness
from xinyu_bridge_codex_execution_backend import codex_execution_backend_readiness
from xinyu_bridge_codex_execution_contract import CodexExecutionHarness
from xinyu_bridge_codex_execution_service import codex_execution_service_readiness
from xinyu_bridge_desktop_surface_contract import DESKTOP_EVENT_STREAM_RUNTIME_ATTR, DesktopEventStreamReadiness
from xinyu_bridge_desktop_surface_service import (
    build_desktop_surface_service_handle,
    desktop_surface_service_readiness,
)
from xinyu_desktop_service import desktop_event_stream_service_readiness
from xinyu_bridge_external_action_backend import external_action_backend_readiness
from xinyu_bridge_external_action_contract import ExternalActionHarness
from xinyu_bridge_external_action_service import external_action_service_readiness
from xinyu_bridge_health_diagnostics_service import (
    HEALTH_DIAGNOSTICS_FALLBACK_ADAPTER,
    HEALTH_DIAGNOSTICS_ROLLBACK,
    HEALTH_DIAGNOSTICS_SERVICE_CONTRACT,
    HEALTH_DIAGNOSTICS_SERVICE_HEALTH_PROVIDER_IDS,
    HEALTH_DIAGNOSTICS_SERVICE_ID,
    HEALTH_DIAGNOSTICS_STATE_OWNER,
    HealthDiagnosticsReadiness,
    HealthDiagnosticsServiceHealthProvider,
)
from xinyu_bridge_learning_ingest_service import (
    build_learning_ingest_service_handle,
    learning_ingest_service_readiness,
)
from xinyu_bridge_life_metabolism_contract import LifeMetabolismHarness
from xinyu_bridge_life_metabolism_service import life_metabolism_service_readiness
from xinyu_bridge_local_report_services import (
    build_diagnostic_reports_service_handle,
    build_memory_governance_reports_service_handle,
    diagnostic_reports_service_readiness,
    memory_governance_reports_service_readiness,
)
from xinyu_bridge_proactive_delivery_contract import proactive_transport_preflight_contract
from xinyu_bridge_proactive_delivery_service import (
    build_proactive_delivery_service_handle,
    proactive_delivery_service_readiness,
)
from xinyu_bridge_state_persistence_service import (
    build_state_persistence_service_handle,
    state_persistence_service_readiness,
)


def health_diagnostics_default_service_health_providers(
    runtime: Any,
) -> tuple[HealthDiagnosticsServiceHealthProvider, ...]:
    del runtime
    return (
        HealthDiagnosticsServiceHealthProvider("chat_turn", chat_turn_service_health),
        HealthDiagnosticsServiceHealthProvider("codex_execution", codex_execution_service_health),
        HealthDiagnosticsServiceHealthProvider("desktop_event_stream", desktop_event_stream_service_health),
        HealthDiagnosticsServiceHealthProvider("desktop_surface", desktop_surface_service_health),
        HealthDiagnosticsServiceHealthProvider("diagnostic_reports", diagnostic_reports_service_health),
        HealthDiagnosticsServiceHealthProvider("external_action", external_action_service_health),
        HealthDiagnosticsServiceHealthProvider("health_diagnostics", health_diagnostics_service_health),
        HealthDiagnosticsServiceHealthProvider("learning_ingest", learning_ingest_service_health),
        HealthDiagnosticsServiceHealthProvider("life_metabolism", life_metabolism_service_health),
        HealthDiagnosticsServiceHealthProvider("memory_governance_reports", memory_governance_reports_service_health),
        HealthDiagnosticsServiceHealthProvider("proactive_delivery", proactive_delivery_service_health),
        HealthDiagnosticsServiceHealthProvider("state_persistence", state_persistence_service_health),
    )


def chat_turn_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, "_chat_turn_service", None)
    readiness = chat_turn_service_readiness(runtime) if service is not None else ChatTurnHarness().start()
    return _service_health_from_readiness(
        readiness,
        payload=_payload(readiness),
        notes=("runtime_chat_turn_service" if service is not None else "service_owned_in_process_harness", *tuple(readiness.notes)),
    )


def codex_execution_service_health(runtime: Any) -> dict[str, Any]:
    readiness = CodexExecutionHarness().start()
    backend = codex_execution_backend_readiness(runtime)
    service = codex_execution_service_readiness(runtime)
    return _service_health_from_readiness(
        readiness,
        payload={"backend": _payload(backend), "service": _payload(service)},
        notes=("service_owned_in_process_harness", *tuple(readiness.notes), *tuple(backend.notes), *tuple(service.notes)),
    )


def desktop_surface_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, "_desktop_surface_service", None)
    if service is not None:
        readiness = desktop_surface_service_readiness(runtime)
    else:
        readiness = build_desktop_surface_service_handle().start(runtime)
    return _service_health_from_readiness(
        readiness,
        payload=_payload(readiness),
        notes=("runtime_desktop_surface_service" if service is not None else "service_owned_in_process_harness", *tuple(readiness.notes)),
    )


def desktop_event_stream_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, DESKTOP_EVENT_STREAM_RUNTIME_ATTR, None)
    has_runtime_attrs = hasattr(runtime, "desktop_event_bus") or hasattr(runtime, "desktop_ws_server")
    if service is not None or has_runtime_attrs:
        readiness = desktop_event_stream_service_readiness(runtime)
        note = "runtime_desktop_event_stream_service" if service is not None else "runtime_desktop_event_attrs"
    else:
        readiness = DesktopEventStreamReadiness(
            available=True,
            status="contract_only",
            listener_url="",
            started=True,
            ready=True,
            notes=("service_owned_in_process_harness", "app_level_ws_lifecycle_not_started_by_runtime"),
        )
        note = "service_owned_in_process_harness"
    return _service_health_from_readiness(
        readiness,
        payload=_payload(readiness),
        notes=(note, *tuple(readiness.notes)),
    )


def diagnostic_reports_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, "_diagnostic_reports_service", None)
    readiness = (
        diagnostic_reports_service_readiness(runtime)
        if service is not None
        else build_diagnostic_reports_service_handle().start(runtime)
    )
    return _service_health_from_readiness(
        readiness,
        payload=_payload(readiness),
        notes=("runtime_diagnostic_reports_service" if service is not None else "service_owned_in_process_harness", *tuple(readiness.notes)),
    )


def external_action_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, "_external_action_service", None)
    backend = external_action_backend_readiness(runtime)
    service_readiness = external_action_service_readiness(runtime)
    if service is not None:
        return _service_health_from_readiness(
            service_readiness,
            payload={"backend": _payload(backend), "service": _payload(service_readiness)},
            notes=("runtime_external_action_service", *tuple(service_readiness.notes), *tuple(backend.notes)),
        )
    readiness = ExternalActionHarness().start()
    return _service_health_from_readiness(
        readiness,
        payload={"backend": _payload(backend), "service": _payload(service_readiness)},
        notes=("service_owned_in_process_harness", *tuple(readiness.notes), *tuple(service_readiness.notes), *tuple(backend.notes)),
    )


def learning_ingest_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, "_learning_ingest_service", None)
    if service is not None:
        readiness = learning_ingest_service_readiness(runtime)
    else:
        readiness = build_learning_ingest_service_handle().start(
            SimpleNamespace(learning_service=_LearningIngestProbeService())
        )
    return _service_health_from_readiness(
        readiness,
        payload=_payload(readiness),
        notes=("runtime_learning_ingest_service" if service is not None else "service_owned_in_process_harness", *tuple(readiness.notes)),
    )


def life_metabolism_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, "_life_metabolism_service", None)
    readiness = life_metabolism_service_readiness(runtime) if service is not None else LifeMetabolismHarness().start()
    return _service_health_from_readiness(
        readiness,
        payload=_payload(readiness),
        notes=("runtime_life_metabolism_service" if service is not None else "service_owned_in_process_harness", *tuple(readiness.notes)),
    )


def memory_governance_reports_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, "_memory_governance_reports_service", None)
    readiness = (
        memory_governance_reports_service_readiness(runtime)
        if service is not None
        else build_memory_governance_reports_service_handle().start(runtime)
    )
    return _service_health_from_readiness(
        readiness,
        payload=_payload(readiness),
        notes=("runtime_memory_governance_reports_service" if service is not None else "service_owned_in_process_harness", *tuple(readiness.notes)),
    )


def health_diagnostics_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, "_health_diagnostics_service", None)
    readiness = getattr(service, "readiness", None)
    if callable(readiness):
        service_readiness = readiness()
        return _service_health_from_readiness(
            service_readiness,
            payload=_payload(service_readiness),
            notes=("runtime_health_diagnostics_service", *tuple(service_readiness.notes)),
        )
    service_readiness = HealthDiagnosticsReadiness(
        service_id=HEALTH_DIAGNOSTICS_SERVICE_ID,
        mode="in_process",
        started=True,
        ready=True,
        api_routes=HEALTH_DIAGNOSTICS_SERVICE_CONTRACT.api_routes,
        runtime_facade_methods=HEALTH_DIAGNOSTICS_SERVICE_CONTRACT.runtime_facade_methods,
        process_split_candidate=HEALTH_DIAGNOSTICS_SERVICE_CONTRACT.process_split_candidate,
        process_split_ready=HEALTH_DIAGNOSTICS_SERVICE_CONTRACT.process_split_ready,
        process_split_gate=HEALTH_DIAGNOSTICS_SERVICE_CONTRACT.process_split_gate,
        state_owner=HEALTH_DIAGNOSTICS_STATE_OWNER,
        fallback_adapter=HEALTH_DIAGNOSTICS_FALLBACK_ADAPTER,
        rollback=HEALTH_DIAGNOSTICS_ROLLBACK,
        notes=("service_owned_health_route_provider",),
    )
    return _service_health_from_readiness(
        service_readiness,
        payload=_payload(service_readiness),
        notes=service_readiness.notes,
    )


def proactive_delivery_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, "_proactive_delivery_service", None)
    if service is not None:
        readiness = proactive_delivery_service_readiness(runtime)
    else:
        readiness = build_proactive_delivery_service_handle().start(runtime)
    transport = proactive_transport_preflight_contract()
    return _service_health_from_readiness(
        readiness,
        payload={"service": _payload(readiness), "transport_preflight": _payload(transport)},
        notes=("runtime_proactive_delivery_service" if service is not None else "service_owned_in_process_harness", *tuple(readiness.notes), *tuple(transport.notes)),
    )


def state_persistence_service_health(runtime: Any) -> dict[str, Any]:
    service = getattr(runtime, "_state_persistence_service", None)
    readiness = (
        state_persistence_service_readiness(runtime)
        if service is not None
        else build_state_persistence_service_handle().start(runtime)
    )
    return _service_health_from_readiness(
        readiness,
        payload=_payload(readiness),
        notes=("runtime_state_persistence_service" if service is not None else "service_owned_in_process_harness", *tuple(readiness.notes)),
    )


def service_health_provider_ids() -> tuple[str, ...]:
    return HEALTH_DIAGNOSTICS_SERVICE_HEALTH_PROVIDER_IDS


def _service_health_from_readiness(
    readiness: Any,
    *,
    payload: Mapping[str, Any] | None = None,
    notes: tuple[str, ...] = (),
) -> dict[str, Any]:
    raw = _payload(readiness)
    ready = bool(raw.get("ready"))
    normalized_payload = dict(payload or raw)
    return {
        "service_id": str(raw.get("service_id") or "unknown_service"),
        "available": True,
        "ok": ready,
        "ready": ready,
        "status": "ok" if ready else "degraded",
        "mode": str(raw.get("mode") or "in_process"),
        "payload": normalized_payload,
        "notes": notes or tuple(raw.get("notes") or ()),
    }


def _payload(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {
        key: getattr(value, key)
        for key in dir(value)
        if not key.startswith("_") and not callable(getattr(value, key))
    }


class _LearningIngestProbeService:
    async def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    async def study(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    async def observe(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload
