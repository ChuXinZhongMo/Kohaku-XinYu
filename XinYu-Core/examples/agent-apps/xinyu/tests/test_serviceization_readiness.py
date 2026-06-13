from __future__ import annotations

from xinyu_serviceization_contracts import service_boundary_contracts, service_contract_by_id, process_split_candidates
from xinyu_serviceization_readiness import (
    PROCESS_SPLIT_ENTRY_GATES,
    PROCESS_SPLIT_PILOT_PREFLIGHT_GATES,
    PREFERRED_PROCESS_SPLIT_PILOT,
    SERVICE_PILOT_PREFLIGHT_REQUIRED_GATES,
    SERVICE_PILOT_PREFLIGHT_SATISFIED_GATES,
    SERVICE_SPLIT_SATISFIED_GATES,
    SERVICE_TRANSPORT_PREFLIGHT_REQUIRED_GATES,
    SERVICE_TRANSPORT_PREFLIGHT_SATISFIED_GATES,
    assess_service_pilot_preflight,
    assess_service_split_readiness,
    assess_service_transport_preflight,
    service_pilot_preflight_report,
    service_split_readiness_report,
    service_transport_preflight_report,
)


def test_service_split_readiness_marks_first_ready_candidates() -> None:
    report = {item.service_id: item for item in service_split_readiness_report()}
    candidate_ids = {contract.service_id for contract in process_split_candidates()}

    assert candidate_ids == {
        "proactive_delivery",
        "desktop_surface",
        "desktop_event_stream",
        "codex_execution",
        "external_action",
        "health_diagnostics",
    }
    for service_id in candidate_ids:
        readiness = report[service_id]
        assert readiness.candidate is True
        assert readiness.ready is (
            service_id
            in {
                "health_diagnostics",
                "codex_execution",
                "external_action",
                "desktop_event_stream",
                "proactive_delivery",
                "desktop_surface",
            }
        )
        if service_id in {
            "health_diagnostics",
            "codex_execution",
            "external_action",
            "desktop_event_stream",
            "proactive_delivery",
            "desktop_surface",
        }:
            assert readiness.satisfied_gates == PROCESS_SPLIT_ENTRY_GATES
            assert not any(gate in readiness.blockers for gate in PROCESS_SPLIT_ENTRY_GATES)
        else:
            assert readiness.satisfied_gates == ()
            for gate in PROCESS_SPLIT_ENTRY_GATES:
                assert gate in readiness.blockers


def test_service_split_readiness_marks_chat_turn_as_local_only() -> None:
    readiness = assess_service_split_readiness(service_contract_by_id("chat_turn"))

    assert readiness.candidate is False
    assert readiness.ready is False
    assert readiness.satisfied_gates == ()
    assert readiness.blockers[0] == "not_process_split_candidate"


def test_service_split_readiness_keeps_fixed_local_not_ready_set() -> None:
    local_not_ready = {
        contract.service_id
        for contract in service_boundary_contracts()
        if not contract.process_split_ready
    }

    assert local_not_ready == {
        "chat_turn",
        "learning_ingest",
        "life_metabolism",
        "diagnostic_reports",
        "memory_governance_reports",
        "state_persistence",
    }
    for service_id in local_not_ready:
        readiness = assess_service_split_readiness(service_contract_by_id(service_id))
        assert readiness.candidate is False
        assert readiness.ready is False
        assert readiness.satisfied_gates == ()
        assert readiness.blockers[0] == "not_process_split_candidate"


def test_service_split_entry_gates_cover_s2_plan_requirements() -> None:
    assert PROCESS_SPLIT_ENTRY_GATES == (
        "request_response_contract",
        "health_readiness_contract",
        "lifecycle_start_stop_contract",
        "state_owner_contract",
        "in_process_fallback_adapter",
        "single_slice_rollback_plan",
    )


def test_health_diagnostics_s2_gates_are_satisfied_and_split_ready() -> None:
    readiness = assess_service_split_readiness(service_contract_by_id("health_diagnostics"))

    assert SERVICE_SPLIT_SATISFIED_GATES["health_diagnostics"] == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.satisfied_gates == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.ready is True
    assert readiness.blockers == ()


def test_codex_execution_s2_gates_are_satisfied_and_split_ready() -> None:
    readiness = assess_service_split_readiness(service_contract_by_id("codex_execution"))

    assert SERVICE_SPLIT_SATISFIED_GATES["codex_execution"] == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.satisfied_gates == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.ready is True
    assert readiness.blockers == ()


def test_external_action_s2_gates_are_satisfied_and_split_ready() -> None:
    readiness = assess_service_split_readiness(service_contract_by_id("external_action"))

    assert SERVICE_SPLIT_SATISFIED_GATES["external_action"] == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.satisfied_gates == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.ready is True
    assert readiness.blockers == ()


def test_desktop_event_stream_s2_gates_are_satisfied_and_split_ready() -> None:
    readiness = assess_service_split_readiness(service_contract_by_id("desktop_event_stream"))

    assert SERVICE_SPLIT_SATISFIED_GATES["desktop_event_stream"] == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.satisfied_gates == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.ready is True
    assert readiness.blockers == ()


def test_proactive_delivery_s2_gates_are_satisfied_and_split_ready() -> None:
    readiness = assess_service_split_readiness(service_contract_by_id("proactive_delivery"))

    assert SERVICE_SPLIT_SATISFIED_GATES["proactive_delivery"] == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.satisfied_gates == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.ready is True
    assert readiness.blockers == ()


def test_desktop_surface_s2_gates_are_satisfied_and_split_ready() -> None:
    readiness = assess_service_split_readiness(service_contract_by_id("desktop_surface"))

    assert SERVICE_SPLIT_SATISFIED_GATES["desktop_surface"] == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.satisfied_gates == PROCESS_SPLIT_ENTRY_GATES
    assert readiness.ready is True
    assert readiness.blockers == ()


def test_codex_execution_s3_pilot_preflight_and_process_split_ready() -> None:
    preflight = assess_service_pilot_preflight(service_contract_by_id("codex_execution"))

    assert PREFERRED_PROCESS_SPLIT_PILOT == "codex_execution"
    assert SERVICE_PILOT_PREFLIGHT_SATISFIED_GATES["codex_execution"] == PROCESS_SPLIT_PILOT_PREFLIGHT_GATES
    assert preflight.service_id == "codex_execution"
    assert preflight.candidate is True
    assert preflight.preferred is True
    assert preflight.preflight_ready is True
    assert preflight.process_split_ready is True
    assert preflight.satisfied_gates == PROCESS_SPLIT_PILOT_PREFLIGHT_GATES
    assert preflight.missing_gates == ()
    assert preflight.split_blockers == ()


def test_desktop_surface_s3_preflight_and_process_split_ready() -> None:
    preflight = assess_service_pilot_preflight(service_contract_by_id("desktop_surface"))

    assert preflight.service_id == "desktop_surface"
    assert preflight.candidate is True
    assert preflight.preferred is False
    assert preflight.preflight_ready is True
    assert preflight.process_split_ready is True
    assert preflight.satisfied_gates == SERVICE_PILOT_PREFLIGHT_REQUIRED_GATES["desktop_surface"]
    assert preflight.missing_gates == ()
    assert preflight.split_blockers == ()


def test_desktop_event_stream_s3_preflight_and_process_split_ready() -> None:
    preflight = assess_service_pilot_preflight(service_contract_by_id("desktop_event_stream"))

    assert preflight.service_id == "desktop_event_stream"
    assert preflight.candidate is True
    assert preflight.preferred is False
    assert preflight.preflight_ready is True
    assert preflight.process_split_ready is True
    assert preflight.satisfied_gates == SERVICE_PILOT_PREFLIGHT_REQUIRED_GATES["desktop_event_stream"]
    assert preflight.missing_gates == ()
    assert preflight.split_blockers == ()


def test_external_action_s3_preflight_and_process_split_ready() -> None:
    preflight = assess_service_pilot_preflight(service_contract_by_id("external_action"))

    assert preflight.service_id == "external_action"
    assert preflight.candidate is True
    assert preflight.preferred is False
    assert preflight.preflight_ready is True
    assert preflight.process_split_ready is True
    assert preflight.satisfied_gates == SERVICE_PILOT_PREFLIGHT_REQUIRED_GATES["external_action"]
    assert preflight.missing_gates == ()
    assert preflight.split_blockers == ()


def test_health_diagnostics_s3_preflight_and_process_split_ready() -> None:
    preflight = assess_service_pilot_preflight(service_contract_by_id("health_diagnostics"))

    assert preflight.service_id == "health_diagnostics"
    assert preflight.candidate is True
    assert preflight.preferred is False
    assert preflight.preflight_ready is True
    assert preflight.process_split_ready is True
    assert preflight.satisfied_gates == SERVICE_PILOT_PREFLIGHT_SATISFIED_GATES["health_diagnostics"]
    assert preflight.missing_gates == ()
    assert preflight.split_blockers == ()


def test_s3_pilot_preflight_report_keeps_other_candidates_not_preflight_ready() -> None:
    report = {item.service_id: item for item in service_pilot_preflight_report()}

    assert report["codex_execution"].preflight_ready is True
    assert report["desktop_surface"].preflight_ready is True
    assert report["desktop_surface"].process_split_ready is True
    assert report["desktop_surface"].split_blockers == ()
    assert report["desktop_event_stream"].preflight_ready is True
    assert report["desktop_event_stream"].process_split_ready is True
    assert report["desktop_event_stream"].split_blockers == ()
    assert report["external_action"].preflight_ready is True
    assert report["external_action"].process_split_ready is True
    assert report["external_action"].split_blockers == ()
    proactive = report["proactive_delivery"]
    assert proactive.candidate is True
    assert proactive.preflight_ready is False
    assert proactive.process_split_ready is True
    assert proactive.satisfied_gates == ()
    assert proactive.missing_gates == PROCESS_SPLIT_PILOT_PREFLIGHT_GATES
    assert proactive.split_blockers == ()

    health = report["health_diagnostics"]
    assert health.candidate is True
    assert health.preflight_ready is True
    assert health.process_split_ready is True
    assert health.satisfied_gates == SERVICE_PILOT_PREFLIGHT_SATISFIED_GATES["health_diagnostics"]
    assert health.missing_gates == ()
    assert health.split_blockers == ()


def test_proactive_delivery_transport_preflight_and_process_split_ready() -> None:
    preflight = assess_service_transport_preflight(service_contract_by_id("proactive_delivery"))

    assert preflight.service_id == "proactive_delivery"
    assert preflight.candidate is True
    assert preflight.transport_preflight_ready is True
    assert preflight.process_split_ready is True
    assert preflight.satisfied_gates == SERVICE_TRANSPORT_PREFLIGHT_SATISFIED_GATES["proactive_delivery"]
    assert preflight.missing_gates == ()
    assert preflight.split_blockers == ()


def test_transport_preflight_report_is_only_for_proactive_delivery() -> None:
    report = {item.service_id: item for item in service_transport_preflight_report()}

    assert report["proactive_delivery"].candidate is True
    assert report["proactive_delivery"].transport_preflight_ready is True
    assert report["proactive_delivery"].process_split_ready is True
    assert report["proactive_delivery"].split_blockers == ()
    assert report["proactive_delivery"].satisfied_gates == SERVICE_TRANSPORT_PREFLIGHT_SATISFIED_GATES[
        "proactive_delivery"
    ]
    for service_id, preflight in report.items():
        if service_id == "proactive_delivery":
            continue
        assert preflight.candidate is False
        assert preflight.transport_preflight_ready is False
        assert preflight.satisfied_gates == ()
        assert preflight.missing_gates == ()
