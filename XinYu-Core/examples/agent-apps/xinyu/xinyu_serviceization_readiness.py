from __future__ import annotations

from dataclasses import dataclass

from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_EVENT_STREAM_S3_PREFLIGHT_GATES,
    DESKTOP_EVENT_STREAM_S3_SATISFIED_GATES,
    DESKTOP_SURFACE_S3_PREFLIGHT_GATES,
    DESKTOP_SURFACE_S3_SATISFIED_GATES,
)
from xinyu_bridge_external_action_backend import (
    EXTERNAL_ACTION_S3_PREFLIGHT_GATES,
    EXTERNAL_ACTION_S3_SATISFIED_GATES,
)
from xinyu_bridge_health_diagnostics_service import (
    HEALTH_DIAGNOSTICS_S3_PREFLIGHT_GATES,
    HEALTH_DIAGNOSTICS_S3_SATISFIED_GATES,
)
from xinyu_bridge_proactive_delivery_contract import (
    PROACTIVE_TRANSPORT_PREFLIGHT_GATES,
    PROACTIVE_TRANSPORT_SATISFIED_GATES,
)
from xinyu_serviceization_contracts import ServiceBoundaryContract, service_boundary_contracts


PROCESS_SPLIT_ENTRY_GATES = (
    "request_response_contract",
    "health_readiness_contract",
    "lifecycle_start_stop_contract",
    "state_owner_contract",
    "in_process_fallback_adapter",
    "single_slice_rollback_plan",
)

PROCESS_SPLIT_PILOT_PREFLIGHT_GATES = (
    "backend_selection_contract",
    "worker_client_dry_run_contract",
    "job_contract",
    "cancellation_contract",
    "completion_outbox_contract",
    "health_semantics_contract",
    "in_process_fallback_rollback_contract",
)

SERVICE_SPLIT_SATISFIED_GATES = {
    "health_diagnostics": PROCESS_SPLIT_ENTRY_GATES,
    "codex_execution": PROCESS_SPLIT_ENTRY_GATES,
    "external_action": PROCESS_SPLIT_ENTRY_GATES,
    "proactive_delivery": PROCESS_SPLIT_ENTRY_GATES,
    "desktop_event_stream": PROCESS_SPLIT_ENTRY_GATES,
    "desktop_surface": PROCESS_SPLIT_ENTRY_GATES,
}

PREFERRED_PROCESS_SPLIT_PILOT = "codex_execution"

SERVICE_PILOT_PREFLIGHT_REQUIRED_GATES = {
    "codex_execution": PROCESS_SPLIT_PILOT_PREFLIGHT_GATES,
    "desktop_surface": DESKTOP_SURFACE_S3_PREFLIGHT_GATES,
    "desktop_event_stream": DESKTOP_EVENT_STREAM_S3_PREFLIGHT_GATES,
    "external_action": EXTERNAL_ACTION_S3_PREFLIGHT_GATES,
    "health_diagnostics": HEALTH_DIAGNOSTICS_S3_PREFLIGHT_GATES,
}

SERVICE_PILOT_PREFLIGHT_SATISFIED_GATES = {
    "codex_execution": PROCESS_SPLIT_PILOT_PREFLIGHT_GATES,
    "desktop_surface": DESKTOP_SURFACE_S3_SATISFIED_GATES,
    "desktop_event_stream": DESKTOP_EVENT_STREAM_S3_SATISFIED_GATES,
    "external_action": EXTERNAL_ACTION_S3_SATISFIED_GATES,
    "health_diagnostics": HEALTH_DIAGNOSTICS_S3_SATISFIED_GATES,
}

SERVICE_TRANSPORT_PREFLIGHT_REQUIRED_GATES = {
    "proactive_delivery": PROACTIVE_TRANSPORT_PREFLIGHT_GATES,
}

SERVICE_TRANSPORT_PREFLIGHT_SATISFIED_GATES = {
    "proactive_delivery": PROACTIVE_TRANSPORT_SATISFIED_GATES,
}


@dataclass(frozen=True, slots=True)
class ServiceSplitReadiness:
    service_id: str
    candidate: bool
    ready: bool
    satisfied_gates: tuple[str, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ServiceSplitPilotPreflight:
    service_id: str
    candidate: bool
    preferred: bool
    preflight_ready: bool
    process_split_ready: bool
    satisfied_gates: tuple[str, ...]
    missing_gates: tuple[str, ...]
    split_blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ServiceTransportPreflight:
    service_id: str
    candidate: bool
    transport_preflight_ready: bool
    process_split_ready: bool
    satisfied_gates: tuple[str, ...]
    missing_gates: tuple[str, ...]
    split_blockers: tuple[str, ...]


def assess_service_split_readiness(contract: ServiceBoundaryContract) -> ServiceSplitReadiness:
    satisfied_gates = SERVICE_SPLIT_SATISFIED_GATES.get(contract.service_id, ())
    if not contract.process_split_candidate:
        return ServiceSplitReadiness(
            service_id=contract.service_id,
            candidate=False,
            ready=False,
            satisfied_gates=satisfied_gates,
            blockers=("not_process_split_candidate", contract.process_split_gate),
        )
    if contract.process_split_ready:
        return ServiceSplitReadiness(
            service_id=contract.service_id,
            candidate=True,
            ready=True,
            satisfied_gates=PROCESS_SPLIT_ENTRY_GATES,
            blockers=(),
        )
    missing_gates = tuple(gate for gate in PROCESS_SPLIT_ENTRY_GATES if gate not in satisfied_gates)
    return ServiceSplitReadiness(
        service_id=contract.service_id,
        candidate=True,
        ready=False,
        satisfied_gates=satisfied_gates,
        blockers=(*missing_gates, contract.process_split_gate),
    )


def assess_service_pilot_preflight(contract: ServiceBoundaryContract) -> ServiceSplitPilotPreflight:
    preferred = contract.service_id == PREFERRED_PROCESS_SPLIT_PILOT
    required_gates = SERVICE_PILOT_PREFLIGHT_REQUIRED_GATES.get(
        contract.service_id,
        PROCESS_SPLIT_PILOT_PREFLIGHT_GATES,
    )
    satisfied_gates = SERVICE_PILOT_PREFLIGHT_SATISFIED_GATES.get(contract.service_id, ())
    if not contract.process_split_candidate:
        return ServiceSplitPilotPreflight(
            service_id=contract.service_id,
            candidate=False,
            preferred=preferred,
            preflight_ready=False,
            process_split_ready=False,
            satisfied_gates=satisfied_gates,
            missing_gates=(),
            split_blockers=("not_process_split_candidate", contract.process_split_gate),
        )

    missing_gates = tuple(gate for gate in required_gates if gate not in satisfied_gates)
    return ServiceSplitPilotPreflight(
        service_id=contract.service_id,
        candidate=True,
        preferred=preferred,
        preflight_ready=not missing_gates,
        process_split_ready=contract.process_split_ready,
        satisfied_gates=satisfied_gates,
        missing_gates=missing_gates,
        split_blockers=() if contract.process_split_ready else (contract.process_split_gate,),
    )


def service_split_readiness_report(
    contracts: tuple[ServiceBoundaryContract, ...] | None = None,
) -> tuple[ServiceSplitReadiness, ...]:
    source = service_boundary_contracts() if contracts is None else contracts
    return tuple(assess_service_split_readiness(contract) for contract in source)


def service_pilot_preflight_report(
    contracts: tuple[ServiceBoundaryContract, ...] | None = None,
) -> tuple[ServiceSplitPilotPreflight, ...]:
    source = service_boundary_contracts() if contracts is None else contracts
    return tuple(assess_service_pilot_preflight(contract) for contract in source)


def assess_service_transport_preflight(contract: ServiceBoundaryContract) -> ServiceTransportPreflight:
    required_gates = SERVICE_TRANSPORT_PREFLIGHT_REQUIRED_GATES.get(contract.service_id, ())
    satisfied_gates = SERVICE_TRANSPORT_PREFLIGHT_SATISFIED_GATES.get(contract.service_id, ())
    missing_gates = tuple(gate for gate in required_gates if gate not in satisfied_gates)
    candidate = contract.service_id in SERVICE_TRANSPORT_PREFLIGHT_REQUIRED_GATES
    return ServiceTransportPreflight(
        service_id=contract.service_id,
        candidate=candidate,
        transport_preflight_ready=candidate and not missing_gates,
        process_split_ready=contract.process_split_ready,
        satisfied_gates=satisfied_gates,
        missing_gates=missing_gates,
        split_blockers=() if contract.process_split_ready else (contract.process_split_gate,),
    )


def service_transport_preflight_report(
    contracts: tuple[ServiceBoundaryContract, ...] | None = None,
) -> tuple[ServiceTransportPreflight, ...]:
    source = service_boundary_contracts() if contracts is None else contracts
    return tuple(assess_service_transport_preflight(contract) for contract in source)
