from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_proactive_delivery_contract import (
    PROACTIVE_GATEWAY_ACTION_TIMEOUT_ERROR,
    PROACTIVE_TRANSPORT_HEALTH_DISABLED_ERRORS,
    proactive_ack_dto_contract,
    proactive_gateway_adapter_contract,
    proactive_transport_health_contract,
    proactive_transport_preflight_contract,
)
from xinyu_qq_outbox_client import GATEWAY_NAME, onebot_action_result
from xinyu_qq_outbox_dispatcher import qq_outbox_visible_dispatch_enabled
from xinyu_serviceization_contracts import service_contract_by_id
from xinyu_serviceization_readiness import (
    assess_service_transport_preflight,
    service_transport_preflight_report,
)


def test_gateway_disabled_transport_health_contract_shape_is_contractual() -> None:
    contract = proactive_transport_health_contract()
    gateway = SimpleNamespace(
        config=SimpleNamespace(
            qq_outbox_enabled=True,
            bridge_token="bridge-token",
            send_replies=False,
        )
    )

    assert contract.visible_dispatch_required_config == (
        "qq_outbox_enabled",
        "bridge_token",
        "send_replies",
    )
    assert contract.sent_ack_required_config == (
        "bridge_token",
        "message_ack_url",
    )
    assert contract.disabled_errors == PROACTIVE_TRANSPORT_HEALTH_DISABLED_ERRORS
    assert "visible outbound dispatch disabled" in contract.disabled_errors
    assert "disabled_after_claim_acks_failed_without_sending" in contract.semantics
    assert qq_outbox_visible_dispatch_enabled(gateway) is False


def test_timeout_and_error_expression_stays_adapter_error_based() -> None:
    ok, adapter_message_id, adapter_error = onebot_action_result(SimpleNamespace(), None)
    ack_contract = proactive_ack_dto_contract()
    gateway_contract = proactive_gateway_adapter_contract()
    health_contract = proactive_transport_health_contract()

    assert ok is False
    assert adapter_message_id == ""
    assert adapter_error == PROACTIVE_GATEWAY_ACTION_TIMEOUT_ERROR
    assert gateway_contract.gateway_name == GATEWAY_NAME
    assert gateway_contract.action_timeout_error == PROACTIVE_GATEWAY_ACTION_TIMEOUT_ERROR
    assert PROACTIVE_GATEWAY_ACTION_TIMEOUT_ERROR in health_contract.disabled_errors
    assert "adapter_error_or_error" in ack_contract.payload_fields
    assert "error_alias_maps_to_adapter_error" in ack_contract.branch_semantics
    assert "onebot_timeout_maps_to_adapter_error" in gateway_contract.semantics


def test_transport_health_ready_still_keeps_proactive_delivery_process_split_blocked() -> None:
    preflight_contract = proactive_transport_preflight_contract()
    health_contract = proactive_transport_health_contract()
    readiness = assess_service_transport_preflight(service_contract_by_id("proactive_delivery"))
    report = {item.service_id: item for item in service_transport_preflight_report()}

    assert "transport_health_contract" in preflight_contract.required_gates
    assert "transport_health_contract" in preflight_contract.satisfied_gates
    assert preflight_contract.missing_gates == ()
    assert preflight_contract.ready is True
    assert "transport_contracts_ready_for_controlled_process_split" in preflight_contract.notes
    assert "transport_health_ready_does_not_enable_process_split" in health_contract.semantics
    assert readiness.transport_preflight_ready is True
    assert readiness.process_split_ready is True
    assert readiness.missing_gates == ()
    assert readiness.split_blockers == ()
    assert report["proactive_delivery"].transport_preflight_ready is True
    assert report["proactive_delivery"].process_split_ready is True
