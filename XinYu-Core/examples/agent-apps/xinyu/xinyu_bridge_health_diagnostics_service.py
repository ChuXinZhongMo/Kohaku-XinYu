from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from xinyu_bridge_utility_common import ensure_payload
from xinyu_bridge_utility_common import sessions
from xinyu_bridge_health_snapshot_service import build_health_snapshot
from xinyu_bridge_health_snapshot_service import build_operator_health
from xinyu_serviceization_contracts import service_contract_by_id


def _no_service_health_providers(runtime: Any) -> tuple[Any, ...]:
    del runtime
    return ()


HEALTH_DIAGNOSTICS_SERVICE_ID = "health_diagnostics"


@dataclass(frozen=True, slots=True)
class HealthDiagnosticsCapability:
    route: str
    runtime_method: str
    contract: str


@dataclass(frozen=True, slots=True)
class HealthDiagnosticsDeps:
    read_code_awareness_summary_func: Callable[..., dict[str, Any]]
    read_runtime_presence_summary_func: Callable[..., dict[str, Any]]
    read_turn_route_summary_func: Callable[..., dict[str, Any]]
    read_recent_action_digest_snapshot_func: Callable[..., dict[str, Any]]
    autonomous_maintenance_health_func: Callable[[Any], dict[str, Any]]
    metabolism_health_func: Callable[[Any], dict[str, Any]]
    operator_health_func: Callable[..., dict[str, Any]]
    service_health_providers_func: Callable[[Any], tuple[Any, ...]] = _no_service_health_providers


@dataclass(frozen=True, slots=True)
class HealthDiagnosticsReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    api_routes: tuple[str, ...]
    runtime_facade_methods: tuple[str, ...]
    process_split_candidate: bool
    process_split_ready: bool
    process_split_gate: str
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


HEALTH_DIAGNOSTICS_CAPABILITIES = (
    HealthDiagnosticsCapability(
        route="/health",
        runtime_method="health",
        contract="synchronous snapshot; no memory writes; public liveness response",
    ),
    HealthDiagnosticsCapability(
        route="/probe",
        runtime_method="probe",
        contract="diagnostic no-memory turn; no session creation",
    ),
    HealthDiagnosticsCapability(
        route="/turn/current",
        runtime_method="turn_current",
        contract="owner-authenticated turn inspection snapshot",
    ),
)


HEALTH_DIAGNOSTICS_STATE_OWNER = "runtime_read_only_diagnostics"
HEALTH_DIAGNOSTICS_FALLBACK_ADAPTER = "in_process_health_snapshot"
HEALTH_DIAGNOSTICS_ROLLBACK = "route_health_back_to_xinyu_bridge_health_snapshot_facade"
HEALTH_DIAGNOSTICS_SERVICE_CONTRACT = service_contract_by_id(HEALTH_DIAGNOSTICS_SERVICE_ID)
HEALTH_DIAGNOSTICS_RUNTIME_INTERNAL_FIELDS = (
    "bridge_version",
    "bridge_source_digest",
    "bridge_runtime_source_digest",
    "xinyu_dir",
    "memory_root",
    "_sessions",
    "turn_timeout_seconds",
    "pre_model_routes_timeout_seconds",
    "outward_renderer",
    "renderer_mode",
    "render_timeout_seconds",
    "session_idle_ttl_seconds",
    "max_sessions",
    "dialogue_prompt_tail_entries",
    "dialogue_session_tail_entries",
    "dialogue_persisted_tail_entries",
    "proactive_min_interval_seconds",
    "_autonomous_task",
    "_autonomous_in_progress",
    "autonomous_maintenance_enabled",
    "autonomous_maintenance_session_key",
    "autonomous_maintenance_initial_delay_seconds",
    "autonomous_maintenance_interval_seconds",
    "_autonomous_run_count",
    "_autonomous_failure_count",
    "_autonomous_last_started_at",
    "_autonomous_last_success_at",
    "_autonomous_last_error",
    "_autonomous_last_memory_changed",
    "_autonomous_next_run_at",
    "_metabolism_task",
    "_metabolism_in_progress",
    "metabolism_runner_interval_seconds",
    "_metabolism_run_count",
    "_metabolism_last_started_at",
    "_metabolism_last_success_at",
    "_metabolism_last_error",
    "_v1_health",
    "self_choice_store.health_snapshot",
    "_payload_text",
    "_cleanup_idle_sessions",
    "_closed",
)
HEALTH_DIAGNOSTICS_INJECTED_DEPENDENCIES = (
    "read_code_awareness_summary_func",
    "read_runtime_presence_summary_func",
    "read_turn_route_summary_func",
    "read_recent_action_digest_snapshot_func",
    "autonomous_maintenance_health_func",
    "metabolism_health_func",
    "operator_health_func",
    "service_health_providers_func",
)
HEALTH_DIAGNOSTICS_S3_PREFLIGHT_GATES = (
    "snapshot_dto_contract",
    "dependency_injection_contract",
    "lifecycle_fallback_contract",
    "digest_safe_no_write_contract",
    "runtime_internal_field_inventory_contract",
    "service_health_aggregation_contract",
    "runtime_internal_replacement_contract",
)
HEALTH_DIAGNOSTICS_S3_SATISFIED_GATES = (
    "snapshot_dto_contract",
    "dependency_injection_contract",
    "lifecycle_fallback_contract",
    "digest_safe_no_write_contract",
    "runtime_internal_field_inventory_contract",
    "service_health_aggregation_contract",
    "runtime_internal_replacement_contract",
)


@dataclass(frozen=True, slots=True)
class HealthDiagnosticsPreflightContract:
    service_id: str
    ready: bool
    required_gates: tuple[str, ...]
    satisfied_gates: tuple[str, ...]
    missing_gates: tuple[str, ...]
    runtime_internal_fields: tuple[str, ...]
    injected_dependencies: tuple[str, ...]
    rollback: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HealthDiagnosticsServiceHealthProvider:
    service_id: str
    health_func: Callable[[Any], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class HealthDiagnosticsServiceHealthContract:
    service_id: str
    gate: str
    aggregate_field: str
    aggregate_status_field: str
    provider_method: str
    provider_fields: tuple[str, ...]
    required_provider_service_ids: tuple[str, ...]
    status_precedence: tuple[str, ...]
    provider_failure_status: str
    health_result_fields: tuple[str, ...]
    summary_fields: tuple[str, ...]
    failure_notes: tuple[str, ...]
    semantics: tuple[str, ...]


HEALTH_DIAGNOSTICS_SERVICE_HEALTH_PROVIDER_FIELDS = (
    "service_id",
    "mode",
    "started",
    "ready",
    "state_owner",
    "fallback_adapter",
    "rollback",
    "notes",
)
HEALTH_DIAGNOSTICS_SERVICE_HEALTH_PROVIDER_IDS = (
    "chat_turn",
    "codex_execution",
    "desktop_event_stream",
    "desktop_surface",
    "diagnostic_reports",
    "external_action",
    "health_diagnostics",
    "learning_ingest",
    "life_metabolism",
    "memory_governance_reports",
    "proactive_delivery",
    "state_persistence",
)
HEALTH_DIAGNOSTICS_SERVICE_HEALTH_STATUS_PRECEDENCE = (
    "failed",
    "degraded",
    "unknown",
    "ok",
)
HEALTH_DIAGNOSTICS_SERVICE_HEALTH_RESULT_FIELDS = (
    "service_id",
    "available",
    "ok",
    "status",
    "payload",
    "error_type",
    "error_message",
    "notes",
)
HEALTH_DIAGNOSTICS_SERVICE_HEALTH_SUMMARY_FIELDS = (
    "ok",
    "service_health_status",
    "service_count",
    "degraded_count",
    "services",
)
HEALTH_DIAGNOSTICS_SERVICE_HEALTH_FAILURE_NOTES = (
    "provider_returned_non_mapping",
    "provider_exception",
)
HEALTH_DIAGNOSTICS_SERVICE_HEALTH_CONTRACT = HealthDiagnosticsServiceHealthContract(
    service_id="health_diagnostics",
    gate="service_health_aggregation_contract",
    aggregate_field="services",
    aggregate_status_field="service_health_status",
    provider_method="readiness",
    provider_fields=HEALTH_DIAGNOSTICS_SERVICE_HEALTH_PROVIDER_FIELDS,
    required_provider_service_ids=HEALTH_DIAGNOSTICS_SERVICE_HEALTH_PROVIDER_IDS,
    status_precedence=HEALTH_DIAGNOSTICS_SERVICE_HEALTH_STATUS_PRECEDENCE,
    provider_failure_status="unknown",
    health_result_fields=HEALTH_DIAGNOSTICS_SERVICE_HEALTH_RESULT_FIELDS,
    summary_fields=HEALTH_DIAGNOSTICS_SERVICE_HEALTH_SUMMARY_FIELDS,
    failure_notes=HEALTH_DIAGNOSTICS_SERVICE_HEALTH_FAILURE_NOTES,
    semantics=(
        "providers_are_in_process_callables",
        "provider_result_is_normalized_by_service_id",
        "provider_exception_becomes_unknown_service_entry",
        "missing_or_invalid_provider_result_is_degraded",
        "does_not_call_runtime_health_snapshot",
        "does_not_read_runtime_internal_fields",
        "aggregation_does_not_set_process_split_ready",
    ),
)


class HealthDiagnosticsService:
    def __init__(self, deps: HealthDiagnosticsDeps) -> None:
        self._deps = deps
        self._started = False

    @property
    def capabilities(self) -> tuple[HealthDiagnosticsCapability, ...]:
        return HEALTH_DIAGNOSTICS_CAPABILITIES

    def start(self) -> HealthDiagnosticsReadiness:
        self._started = True
        return self.readiness()

    def stop(self) -> HealthDiagnosticsReadiness:
        self._started = False
        return self.readiness()

    def readiness(self) -> HealthDiagnosticsReadiness:
        return HealthDiagnosticsReadiness(
            service_id=HEALTH_DIAGNOSTICS_SERVICE_ID,
            mode="in_process",
            started=self._started,
            ready=self._started,
            api_routes=HEALTH_DIAGNOSTICS_SERVICE_CONTRACT.api_routes,
            runtime_facade_methods=HEALTH_DIAGNOSTICS_SERVICE_CONTRACT.runtime_facade_methods,
            process_split_candidate=HEALTH_DIAGNOSTICS_SERVICE_CONTRACT.process_split_candidate,
            process_split_ready=HEALTH_DIAGNOSTICS_SERVICE_CONTRACT.process_split_ready,
            process_split_gate=HEALTH_DIAGNOSTICS_SERVICE_CONTRACT.process_split_gate,
            state_owner=HEALTH_DIAGNOSTICS_STATE_OWNER,
            fallback_adapter=HEALTH_DIAGNOSTICS_FALLBACK_ADAPTER,
            rollback=HEALTH_DIAGNOSTICS_ROLLBACK,
            notes=("no_background_resources",),
        )

    def fallback_adapter(self) -> Callable[..., dict[str, Any]]:
        return self.health_snapshot

    @staticmethod
    async def probe(
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        bridge_version: str,
        deps: Any,
    ) -> dict[str, Any]:
        payload = ensure_payload(payload, deps)
        text = runtime._payload_text(payload)
        cleanup = await runtime._cleanup_idle_sessions()
        return {
            "ok": True,
            "bridge": "xinyu_core_bridge",
            "version": bridge_version,
            "probe": "diagnostic_no_memory",
            "accepted": True,
            "reply": "probe_ok",
            "received_text_chars": len(text),
            "memory_changed": False,
            "session_created": False,
            "sessions": sessions(runtime),
            "cleaned_sessions": cleanup["cleaned_sessions"],
            "notes": ["no_agent_turn", "no_memory_write", "no_session_created"],
        }

    @staticmethod
    async def runtime_probe(runtime: Any, payload: dict[str, Any] | None = None, *, deps: Any) -> dict[str, Any]:
        bridge_version = str(getattr(runtime, "bridge_version", "") or "unknown")
        return await HealthDiagnosticsService.probe(runtime, payload, bridge_version=bridge_version, deps=deps)

    @staticmethod
    async def turn_current(
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        current_turn_snapshot_func: Callable[[Any], dict[str, Any]],
    ) -> dict[str, Any]:
        del payload
        snapshot = current_turn_snapshot_func(runtime)
        return {
            "ok": True,
            "current_turn": snapshot["current_turn"],
            "route": snapshot["route"],
            "operator": build_operator_health(
                runtime_presence=snapshot.get("presence", {}),
                turn_route=snapshot["route"],
            ),
        }

    def health_snapshot(
        self,
        runtime: Any,
        *,
        bridge_version: str,
        source_digest: str,
        runtime_source_digest: str,
    ) -> dict[str, Any]:
        deps = self._deps
        service_health_providers = tuple(deps.service_health_providers_func(runtime) or ())
        return build_health_snapshot(
            runtime,
            bridge_version=bridge_version,
            source_digest=source_digest,
            runtime_source_digest=runtime_source_digest,
            read_code_awareness_summary_func=deps.read_code_awareness_summary_func,
            read_runtime_presence_summary_func=deps.read_runtime_presence_summary_func,
            read_turn_route_summary_func=deps.read_turn_route_summary_func,
            read_recent_action_digest_snapshot_func=deps.read_recent_action_digest_snapshot_func,
            autonomous_maintenance_health_func=deps.autonomous_maintenance_health_func,
            metabolism_health_func=deps.metabolism_health_func,
            operator_health_func=deps.operator_health_func,
            service_health=aggregate_service_health(service_health_providers, runtime)
            if service_health_providers
            else None,
        )


def build_health_diagnostics_service(deps: HealthDiagnosticsDeps) -> HealthDiagnosticsService:
    return HealthDiagnosticsService(deps)


def health_diagnostics_service_health_contract() -> HealthDiagnosticsServiceHealthContract:
    return HEALTH_DIAGNOSTICS_SERVICE_HEALTH_CONTRACT


def health_diagnostics_service_health_aggregation_contract() -> HealthDiagnosticsServiceHealthContract:
    return HEALTH_DIAGNOSTICS_SERVICE_HEALTH_CONTRACT


def aggregate_service_health(
    providers: tuple[HealthDiagnosticsServiceHealthProvider, ...],
    runtime: Any,
    *,
    required_service_ids: tuple[str, ...] = HEALTH_DIAGNOSTICS_SERVICE_HEALTH_PROVIDER_IDS,
) -> dict[str, Any]:
    provider_by_id = {_safe_str(provider.service_id, "unknown_service"): provider for provider in providers}
    services: dict[str, dict[str, Any]] = {}
    degraded_count = 0
    service_ids = tuple(dict.fromkeys((*required_service_ids, *provider_by_id)))
    for service_id in service_ids:
        provider = provider_by_id.get(service_id)
        if provider is None:
            item = _missing_service_health(service_id)
            degraded_count += 1
            services[service_id] = item
            continue
        try:
            raw = provider.health_func(runtime)
        except Exception as exc:
            item = _unknown_service_health(
                service_id,
                error_type=type(exc).__name__,
                notes=("provider_exception",),
            )
        else:
            item = _normalize_service_health(service_id, raw)
        if not item["ok"]:
            degraded_count += 1
        services[service_id] = item
    service_health_status = _aggregate_service_health_status(tuple(item["status"] for item in services.values()))
    return {
        "ok": service_health_status == "ok",
        "service_health_status": service_health_status,
        "service_count": len(services),
        "degraded_count": degraded_count,
        "services": services,
    }


def _normalize_service_health(service_id: str, raw: Mapping[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return _degraded_service_health(
            service_id,
            status="invalid_provider_payload",
            notes=("provider_returned_non_mapping",),
        )
    ok = _safe_bool(raw.get("ok"), default=_safe_bool(raw.get("ready"), default=True))
    notes = raw.get("notes")
    if isinstance(notes, (list, tuple)):
        normalized_notes = tuple(_safe_str(note) for note in notes if _safe_str(note))
    elif _safe_str(notes):
        normalized_notes = (_safe_str(notes),)
    else:
        normalized_notes = ()
    payload = raw.get("payload")
    if not isinstance(payload, Mapping):
        payload = {
            key: value
            for key, value in raw.items()
            if key
            not in {
                "service_id",
                "available",
                "ok",
                "status",
                "error_type",
                "error_message",
                "notes",
            }
        }
    return {
        "service_id": service_id,
        "available": _safe_bool(raw.get("available"), default=True),
        "ok": ok,
        "status": _service_status(raw.get("status"), ok=ok),
        "payload": dict(payload),
        "error_type": _safe_str(raw.get("error_type")),
        "error_message": _safe_str(raw.get("error_message")),
        "notes": normalized_notes,
    }


def _missing_service_health(service_id: str) -> dict[str, Any]:
    return {
        "service_id": service_id,
        "available": False,
        "ok": False,
        "status": "missing_provider",
        "payload": {},
        "error_type": "",
        "error_message": "",
        "notes": ("provider_missing",),
    }


def _unknown_service_health(service_id: str, *, error_type: str, notes: tuple[str, ...]) -> dict[str, Any]:
    return {
        "service_id": service_id,
        "available": True,
        "ok": False,
        "status": "unknown",
        "payload": {},
        "error_type": error_type,
        "error_message": "",
        "notes": notes,
    }


def _degraded_service_health(
    service_id: str,
    *,
    status: str = "degraded",
    notes: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "service_id": service_id,
        "available": True,
        "ok": False,
        "status": status,
        "payload": {},
        "error_type": "",
        "error_message": "",
        "notes": notes,
    }


def _service_status(value: Any, *, ok: bool) -> str:
    status = _safe_str(value)
    if status in {
        "ok",
        "degraded",
        "failed",
        "unknown",
        "missing_provider",
        "provider_error",
        "invalid_provider_payload",
    }:
        return status
    return "ok" if ok else "degraded"


def _aggregate_service_health_status(statuses: tuple[str, ...]) -> str:
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status in {"degraded", "missing_provider", "provider_error", "invalid_provider_payload"} for status in statuses):
        return "degraded"
    if any(status == "unknown" for status in statuses):
        return "unknown"
    return "ok"


def health_diagnostics_preflight_contract(
    satisfied_gates: tuple[str, ...] | None = None,
) -> HealthDiagnosticsPreflightContract:
    provided_gates = set(HEALTH_DIAGNOSTICS_S3_SATISFIED_GATES if satisfied_gates is None else satisfied_gates)
    normalized_satisfied = tuple(
        gate for gate in HEALTH_DIAGNOSTICS_S3_PREFLIGHT_GATES if gate in provided_gates
    )
    missing = tuple(
        gate for gate in HEALTH_DIAGNOSTICS_S3_PREFLIGHT_GATES if gate not in normalized_satisfied
    )
    return HealthDiagnosticsPreflightContract(
        service_id="health_diagnostics",
        ready=not missing,
        required_gates=HEALTH_DIAGNOSTICS_S3_PREFLIGHT_GATES,
        satisfied_gates=normalized_satisfied,
        missing_gates=missing,
        runtime_internal_fields=HEALTH_DIAGNOSTICS_RUNTIME_INTERNAL_FIELDS,
        injected_dependencies=HEALTH_DIAGNOSTICS_INJECTED_DEPENDENCIES,
        rollback=HEALTH_DIAGNOSTICS_ROLLBACK,
        notes=(
            "s3_health_aggregation_preflight_contract_only",
            "process_split_ready_uses_provider_registry_rollback",
            "health_snapshot_route_payload_unchanged",
        ),
    )


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "ready", "ok"}:
        return True
    if text in {"0", "false", "no", "off", "degraded", "failed", "error"}:
        return False
    return default
