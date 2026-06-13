from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xinyu_serviceization_contracts import service_contract_by_id


DESKTOP_SURFACE_STATE_OWNER = "desktop_surface_state_store_projection_snapshot_and_approval_backends"
DESKTOP_SURFACE_FALLBACK_ADAPTER = "in_process_runtime_desktop_surface_methods"
DESKTOP_SURFACE_ROLLBACK = "route_desktop_surface_back_to_current_runtime_facades"
DESKTOP_EVENT_STREAM_STATE_OWNER = "desktop_event_bus_and_ws_server_state"
DESKTOP_EVENT_STREAM_ROLLBACK = "disable_desktop_ws_stream_keep_rest_surface_in_process"
DESKTOP_EVENT_STREAM_RUNTIME_ATTR = "_desktop_event_stream_service"
DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY = "app_owned_websocket_lifecycle_not_runtime_service_starter"
DESKTOP_EVENT_STREAM_EXTERNALIZATION_SCOPE = "event_bus_replay_only_ws_lifecycle_app_owned"
DESKTOP_EVENT_STREAM_SERVICE_ID = "desktop_event_stream"
DESKTOP_EVENT_STREAM_SERVICE_CONTRACT = service_contract_by_id(DESKTOP_EVENT_STREAM_SERVICE_ID)
DESKTOP_EVENT_STREAM_S3_PREFLIGHT_GATES = (
    "websocket_lifecycle_contract",
    "event_replay_contract",
    "backpressure_contract",
    "degraded_event_stream_fallback_contract",
    "in_process_event_stream_rollback_contract",
)
DESKTOP_EVENT_STREAM_S3_SATISFIED_GATES = DESKTOP_EVENT_STREAM_S3_PREFLIGHT_GATES
DESKTOP_SURFACE_S3_PREFLIGHT_GATES = (
    "route_backend_selection_contract",
    "projection_backend_contract",
    "self_action_approval_backend_contract",
    "snapshot_state_backend_contract",
    "websocket_lifecycle_contract",
    "event_replay_contract",
    "backpressure_contract",
    "snapshot_dto_stability_contract",
    "degraded_event_stream_fallback_contract",
    "in_process_surface_rollback_contract",
)
DESKTOP_SURFACE_S3_SATISFIED_GATES = (
    "route_backend_selection_contract",
    "projection_backend_contract",
    "self_action_approval_backend_contract",
    "snapshot_state_backend_contract",
    "websocket_lifecycle_contract",
    "event_replay_contract",
    "backpressure_contract",
    "snapshot_dto_stability_contract",
    "degraded_event_stream_fallback_contract",
    "in_process_surface_rollback_contract",
)
DESKTOP_SURFACE_SNAPSHOT_DTO_TOP_LEVEL_KEYS = (
    "version",
    "snapshotAt",
    "lastEventId",
    "eventBus",
    "services",
    "selfAction",
)
DESKTOP_EVENT_STREAM_REPLAY_EVENTS = (
    "desktop.event_replay.unavailable",
    "desktop.event_stream.ready",
)


@dataclass(frozen=True, slots=True)
class DesktopSurfaceCapability:
    route: str
    http_method: str
    runtime_method: str
    contract: str


@dataclass(frozen=True, slots=True)
class DesktopEventStreamReadiness:
    available: bool
    status: str
    listener_url: str
    service_id: str = DESKTOP_EVENT_STREAM_SERVICE_ID
    mode: str = "in_process"
    started: bool = False
    ready: bool = False
    api_routes: tuple[str, ...] = DESKTOP_EVENT_STREAM_SERVICE_CONTRACT.api_routes
    runtime_facade_methods: tuple[str, ...] = DESKTOP_EVENT_STREAM_SERVICE_CONTRACT.runtime_facade_methods
    process_split_candidate: bool = DESKTOP_EVENT_STREAM_SERVICE_CONTRACT.process_split_candidate
    process_split_ready: bool = DESKTOP_EVENT_STREAM_SERVICE_CONTRACT.process_split_ready
    process_split_gate: str = DESKTOP_EVENT_STREAM_SERVICE_CONTRACT.process_split_gate
    state_owner: str = DESKTOP_EVENT_STREAM_STATE_OWNER
    fallback_adapter: str = DESKTOP_SURFACE_FALLBACK_ADAPTER
    rollback: str = DESKTOP_EVENT_STREAM_ROLLBACK
    runtime_attr: str = DESKTOP_EVENT_STREAM_RUNTIME_ATTR
    lifecycle_boundary: str = DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY
    externalization_scope: str = DESKTOP_EVENT_STREAM_EXTERNALIZATION_SCOPE
    app_owned_lifecycle: bool = True
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DesktopSurfaceReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    event_stream: DesktopEventStreamReadiness
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DesktopSurfaceS3PreflightContract:
    service_id: str
    ready: bool
    required_gates: tuple[str, ...]
    satisfied_gates: tuple[str, ...]
    missing_gates: tuple[str, ...]
    snapshot_top_level_keys: tuple[str, ...]
    event_stream_replay_events: tuple[str, ...]
    rollback: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DesktopEventStreamS3PreflightContract:
    service_id: str
    ready: bool
    required_gates: tuple[str, ...]
    satisfied_gates: tuple[str, ...]
    missing_gates: tuple[str, ...]
    event_stream_replay_events: tuple[str, ...]
    rollback: str
    notes: tuple[str, ...] = ()


DESKTOP_SURFACE_CAPABILITIES = (
    DesktopSurfaceCapability(
        route="/desktop/snapshot",
        http_method="GET",
        runtime_method="desktop_snapshot",
        contract="owner-visible desktop snapshot DTO",
    ),
    DesktopSurfaceCapability(
        route="/desktop/events/recent",
        http_method="GET",
        runtime_method="desktop_events_recent",
        contract="recent desktop event buffer read",
    ),
    DesktopSurfaceCapability(
        route="/desktop/proactive/inbox",
        http_method="GET",
        runtime_method="desktop_proactive_inbox",
        contract="desktop proactive inbox projection",
    ),
    DesktopSurfaceCapability(
        route="/desktop/chat/recent",
        http_method="GET",
        runtime_method="desktop_chat_recent",
        contract="recent chat projection buffer read",
    ),
    DesktopSurfaceCapability(
        route="/desktop/memory/recent",
        http_method="GET",
        runtime_method="desktop_memory_recent",
        contract="recent memory event projection buffer read",
    ),
    DesktopSurfaceCapability(
        route="/desktop/memory/growth-candidates",
        http_method="GET",
        runtime_method="desktop_memory_growth_candidates",
        contract="memory growth candidate projection read",
    ),
    DesktopSurfaceCapability(
        route="/desktop/self-action/approval",
        http_method="POST",
        runtime_method="desktop_self_action_approval",
        contract="owner desktop self-action approval control",
    ),
)

DESKTOP_SURFACE_S3_PREFLIGHT_CONTRACT = DesktopSurfaceS3PreflightContract(
    service_id="desktop_surface",
    ready=True,
    required_gates=DESKTOP_SURFACE_S3_PREFLIGHT_GATES,
    satisfied_gates=DESKTOP_SURFACE_S3_SATISFIED_GATES,
    missing_gates=(),
    snapshot_top_level_keys=DESKTOP_SURFACE_SNAPSHOT_DTO_TOP_LEVEL_KEYS,
    event_stream_replay_events=DESKTOP_EVENT_STREAM_REPLAY_EVENTS,
    rollback=DESKTOP_SURFACE_ROLLBACK,
    notes=(
        "s3_preflight_contract_only",
        "route_backend_selection_ready",
        "snapshot_projection_backend_ready",
        "self_action_approval_backend_ready",
        "snapshot_state_backend_ready",
        "event_stream_already_split_ready_as_separate_boundary",
    ),
)

DESKTOP_EVENT_STREAM_S3_PREFLIGHT_CONTRACT = DesktopEventStreamS3PreflightContract(
    service_id="desktop_event_stream",
    ready=True,
    required_gates=DESKTOP_EVENT_STREAM_S3_PREFLIGHT_GATES,
    satisfied_gates=DESKTOP_EVENT_STREAM_S3_SATISFIED_GATES,
    missing_gates=(),
    event_stream_replay_events=DESKTOP_EVENT_STREAM_REPLAY_EVENTS,
    rollback=DESKTOP_EVENT_STREAM_ROLLBACK,
    notes=(
        "event_stream_boundary_only",
        "snapshot_projection_and_self_action_remain_in_desktop_surface",
        "ws_lifecycle_replay_backpressure_and_fallback_contracts_ready",
    ),
)


class DesktopSurfaceHarness:
    def __init__(self, *, event_bus: Any | None = None, ws_server: Any | None = None) -> None:
        self._event_bus = event_bus
        self._ws_server = ws_server
        self._started = False

    @property
    def capabilities(self) -> tuple[DesktopSurfaceCapability, ...]:
        return DESKTOP_SURFACE_CAPABILITIES

    def start(self) -> DesktopSurfaceReadiness:
        self._started = True
        return self.readiness()

    def stop(self) -> DesktopSurfaceReadiness:
        self._started = False
        return self.readiness()

    def readiness(self) -> DesktopSurfaceReadiness:
        event_stream = desktop_event_stream_readiness(
            event_bus=self._event_bus,
            ws_server=self._ws_server,
        )
        return DesktopSurfaceReadiness(
            service_id="desktop_surface",
            mode="in_process",
            started=self._started,
            ready=self._started,
            state_owner=DESKTOP_SURFACE_STATE_OWNER,
            fallback_adapter=DESKTOP_SURFACE_FALLBACK_ADAPTER,
            rollback=DESKTOP_SURFACE_ROLLBACK,
            event_stream=event_stream,
            notes=(
                "s2_in_process_harness",
                "fallback_maps_runtime_desktop_methods_only",
                f"event_stream_{event_stream.status}",
            ),
        )

    @staticmethod
    def fallback_adapter(runtime: Any) -> dict[str, Callable[..., Any]]:
        return {
            capability.runtime_method: getattr(runtime, capability.runtime_method)
            for capability in DESKTOP_SURFACE_CAPABILITIES
        }


def desktop_surface_capabilities() -> tuple[DesktopSurfaceCapability, ...]:
    return DESKTOP_SURFACE_CAPABILITIES


def desktop_surface_routes() -> tuple[str, ...]:
    return tuple(capability.route for capability in DESKTOP_SURFACE_CAPABILITIES)


def desktop_surface_s3_preflight_contract(
    satisfied_gates: tuple[str, ...] | None = None,
) -> DesktopSurfaceS3PreflightContract:
    provided_gates = set(DESKTOP_SURFACE_S3_SATISFIED_GATES if satisfied_gates is None else satisfied_gates)
    normalized_satisfied = tuple(
        gate for gate in DESKTOP_SURFACE_S3_PREFLIGHT_GATES if gate in provided_gates
    )
    missing = tuple(
        gate for gate in DESKTOP_SURFACE_S3_PREFLIGHT_GATES if gate not in normalized_satisfied
    )
    return DesktopSurfaceS3PreflightContract(
        service_id="desktop_surface",
        ready=not missing,
        required_gates=DESKTOP_SURFACE_S3_PREFLIGHT_GATES,
        satisfied_gates=normalized_satisfied,
        missing_gates=missing,
        snapshot_top_level_keys=DESKTOP_SURFACE_SNAPSHOT_DTO_TOP_LEVEL_KEYS,
        event_stream_replay_events=DESKTOP_EVENT_STREAM_REPLAY_EVENTS,
        rollback=DESKTOP_SURFACE_ROLLBACK,
        notes=DESKTOP_SURFACE_S3_PREFLIGHT_CONTRACT.notes,
    )


def desktop_event_stream_s3_preflight_contract(
    satisfied_gates: tuple[str, ...] | None = None,
) -> DesktopEventStreamS3PreflightContract:
    provided_gates = set(DESKTOP_EVENT_STREAM_S3_SATISFIED_GATES if satisfied_gates is None else satisfied_gates)
    normalized_satisfied = tuple(
        gate for gate in DESKTOP_EVENT_STREAM_S3_PREFLIGHT_GATES if gate in provided_gates
    )
    missing = tuple(
        gate for gate in DESKTOP_EVENT_STREAM_S3_PREFLIGHT_GATES if gate not in normalized_satisfied
    )
    return DesktopEventStreamS3PreflightContract(
        service_id="desktop_event_stream",
        ready=not missing,
        required_gates=DESKTOP_EVENT_STREAM_S3_PREFLIGHT_GATES,
        satisfied_gates=normalized_satisfied,
        missing_gates=missing,
        event_stream_replay_events=DESKTOP_EVENT_STREAM_REPLAY_EVENTS,
        rollback=DESKTOP_EVENT_STREAM_ROLLBACK,
        notes=DESKTOP_EVENT_STREAM_S3_PREFLIGHT_CONTRACT.notes,
    )


def desktop_event_stream_readiness(
    *,
    event_bus: Any | None,
    ws_server: Any | None,
) -> DesktopEventStreamReadiness:
    if event_bus is None or ws_server is None:
        return DesktopEventStreamReadiness(
            available=False,
            status="disabled",
            listener_url="",
            notes=("event_bus_or_ws_server_missing",),
        )
    listener_url = f"ws://{ws_server.host}:{ws_server.bound_port}{ws_server.path}"
    started = getattr(ws_server, "server", None) is not None
    status = "ready" if started else "configured"
    return DesktopEventStreamReadiness(
        available=True,
        status=status,
        listener_url=listener_url,
        started=started,
        ready=started,
        notes=(f"ws_server_{status}",),
    )
