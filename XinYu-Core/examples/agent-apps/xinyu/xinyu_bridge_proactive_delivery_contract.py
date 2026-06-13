from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


PROACTIVE_OUTBOX_MESSAGE_PREFIX = "proactive:"
PROACTIVE_DELIVERY_STATE_OWNER = "proactive_request_and_qq_outbox_state"
PROACTIVE_DELIVERY_FALLBACK_ADAPTER = "in_process_proactive_delivery_runtime_methods"
PROACTIVE_DELIVERY_ROLLBACK = "route_proactive_delivery_back_to_current_runtime_facades"
PROACTIVE_CLAIM_SOURCE = "proactive_request"
PROACTIVE_CLAIM_REQUIRED_FIELDS = (
    "accepted",
    "message_claimed",
    "message_id",
    "claim_id",
    "target",
    "message",
    "attempts",
    "source",
    "notes",
)
PROACTIVE_CLAIM_TARGET_CONTRACT = {
    "message_kind": "private",
    "group_id": "",
}
PROACTIVE_CLAIM_STATE_TRANSITIONS = (
    "ordinary_qq_outbox_claim_has_priority",
    "proactive_fallback_only_when_ordinary_outbox_empty",
    "candidate_must_be_ready",
    "owner_private_share_must_not_be_paused",
    "owner_user_id_required",
    "claim_sets_request_status_claimed",
    "claim_sets_last_ack_status_pending",
)
PROACTIVE_ACK_PAYLOAD_FIELDS = (
    "message_id",
    "claim_id",
    "ack_status_or_status",
    "adapter_message_id",
    "adapter_error_or_error",
)
PROACTIVE_ACK_STATUS_VALUES = ("sent", "failed", "queued", "dry_run")
PROACTIVE_ACK_RESULT_SUCCESS_FIELDS = (
    "accepted",
    "ack_recorded",
    "claim_id",
    "ack_status",
    "adapter_message_id",
    "notes",
)
PROACTIVE_ACK_ERROR_NOTES = (
    "invalid_ack_status",
    "no_claim_to_ack",
    "claim_id_mismatch",
)
PROACTIVE_ACK_STATUS_REQUEST_STATES = {
    "sent": "sent",
    "failed": "failed",
    "queued": "queued_qq",
    "dry_run": "ready",
}
PROACTIVE_ACK_STATUS_ANSWER_STATES = {
    "sent": "sent_waiting_owner_reply",
    "failed": "not_requested_failed",
}
PROACTIVE_ACK_BRANCH_SEMANTICS = (
    "proactive_message_id_routes_to_proactive_presence_ack",
    "ordinary_message_id_routes_to_qq_outbox_ack",
    "status_alias_maps_to_ack_status",
    "error_alias_maps_to_adapter_error",
    "missing_adapter_message_id_falls_back_to_message_id",
    "record_outbound_only_when_ack_recorded_and_sent",
    "proactive_failed_does_not_use_ordinary_outbox_dead_attempt_counter",
    "terminal_sent_ack_is_idempotent",
    "late_failed_ack_does_not_downgrade_sent",
)
PROACTIVE_GATEWAY_ADAPTER_NAME = "xinyu_native_qq_gateway"
PROACTIVE_GATEWAY_VERSION_FALLBACK = "0.1.24"
PROACTIVE_GATEWAY_CLAIM_PAYLOAD_FIELDS = ("claim_id", "adapter")
PROACTIVE_GATEWAY_ACK_PAYLOAD_FIELDS = (
    "message_id",
    "claim_id",
    "ack_status",
    "adapter_message_id",
    "adapter_error",
)
PROACTIVE_GATEWAY_SENT_ACK_REQUIRED_FIELDS = (
    "adapter",
    "gateway",
    "adapter_message_id",
    "route",
    "source_route",
    "session_id",
    "turn_id",
    "archive_message_ids",
    "archive_assistant_message_id",
    "source_message_id",
    "outbox_message_id",
    "message_type",
    "target",
    "visible_text",
    "visible_text_hash",
    "sent_at",
    "adapter_error",
    "metadata",
)
PROACTIVE_GATEWAY_SENT_DELIVERY_ROUTES = {
    "proactive_text": "proactive",
    "proactive_image": "proactive_image",
    "proactive_caption": "proactive_caption",
    "ordinary_text": "qq_outbox",
    "ordinary_image": "qq_outbox_image",
    "ordinary_caption": "qq_outbox_caption",
}
PROACTIVE_GATEWAY_ACTION_SUCCESS_STATUSES = ("ok", "async")
PROACTIVE_GATEWAY_ACTION_SUCCESS_RETCODES = ("0",)
PROACTIVE_GATEWAY_ACTION_TIMEOUT_ERROR = "onebot_action_timeout"
PROACTIVE_TRANSPORT_VISIBLE_DISPATCH_REQUIRED_CONFIG = (
    "qq_outbox_enabled",
    "bridge_token",
    "send_replies",
)
PROACTIVE_TRANSPORT_SENT_ACK_REQUIRED_CONFIG = (
    "bridge_token",
    "message_ack_url",
)
PROACTIVE_TRANSPORT_HEALTH_DISABLED_ERRORS = (
    "visible outbound dispatch disabled",
    "invalid target",
    "empty text message",
    "qq outbox image dispatch disabled",
    "qq outbox file dispatch disabled",
    PROACTIVE_GATEWAY_ACTION_TIMEOUT_ERROR,
)
PROACTIVE_TRANSPORT_PREFLIGHT_GATES = (
    "claim_dto_contract",
    "ack_dto_contract",
    "virtual_message_id_branch_contract",
    "ordinary_outbox_priority_contract",
    "retry_dead_semantics_contract",
    "gateway_adapter_contract",
    "transport_health_contract",
    "route_backend_selection_contract",
    "state_store_ownership_contract",
    "in_process_fallback_rollback_contract",
)
PROACTIVE_TRANSPORT_SATISFIED_GATES = (
    "claim_dto_contract",
    "ack_dto_contract",
    "virtual_message_id_branch_contract",
    "ordinary_outbox_priority_contract",
    "retry_dead_semantics_contract",
    "gateway_adapter_contract",
    "transport_health_contract",
    "route_backend_selection_contract",
    "state_store_ownership_contract",
    "in_process_fallback_rollback_contract",
)


@dataclass(frozen=True, slots=True)
class ProactiveDeliveryCapability:
    route: str
    http_method: str
    runtime_method: str
    fast_method: str
    contract: str


@dataclass(frozen=True, slots=True)
class ProactiveDeliveryReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProactiveClaimDtoContract:
    required_fields: tuple[str, ...]
    source: str
    message_id_prefix: str
    target_contract: dict[str, str]
    attempts: int
    required_notes: tuple[str, ...]
    state_transitions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProactiveAckDtoContract:
    payload_fields: tuple[str, ...]
    status_values: tuple[str, ...]
    success_fields: tuple[str, ...]
    error_notes: tuple[str, ...]
    request_status_by_ack_status: dict[str, str]
    answer_state_by_ack_status: dict[str, str]
    branch_semantics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProactiveGatewayAdapterContract:
    gateway_name: str
    gateway_version_fallback: str
    claim_payload_fields: tuple[str, ...]
    ack_payload_fields: tuple[str, ...]
    sent_ack_required_fields: tuple[str, ...]
    sent_delivery_routes: dict[str, str]
    action_success_statuses: tuple[str, ...]
    action_success_retcodes: tuple[str, ...]
    action_timeout_error: str
    semantics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProactiveTransportHealthContract:
    visible_dispatch_required_config: tuple[str, ...]
    sent_ack_required_config: tuple[str, ...]
    disabled_errors: tuple[str, ...]
    semantics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProactiveTransportPreflightContract:
    service_id: str
    ready: bool
    required_gates: tuple[str, ...]
    satisfied_gates: tuple[str, ...]
    missing_gates: tuple[str, ...]
    rollback: str
    notes: tuple[str, ...] = ()


PROACTIVE_DELIVERY_CAPABILITIES = (
    ProactiveDeliveryCapability(
        route="/proactive",
        http_method="GET",
        runtime_method="proactive",
        fast_method="",
        contract="preview or claim proactive request through bridge API",
    ),
    ProactiveDeliveryCapability(
        route="/proactive",
        http_method="POST",
        runtime_method="proactive",
        fast_method="",
        contract="preview or claim proactive request through bridge API",
    ),
    ProactiveDeliveryCapability(
        route="/proactive/ack",
        http_method="POST",
        runtime_method="proactive_ack",
        fast_method="",
        contract="acknowledge a proactive request lifecycle event",
    ),
    ProactiveDeliveryCapability(
        route="/desktop/proactive/ack",
        http_method="POST",
        runtime_method="desktop_proactive_ack",
        fast_method="",
        contract="owner desktop ack path for proactive request items",
    ),
    ProactiveDeliveryCapability(
        route="/qq/outbox/claim",
        http_method="POST",
        runtime_method="qq_outbox_claim",
        fast_method="qq_outbox_claim_fast",
        contract="claim queued QQ outbox item or fallback proactive request candidate",
    ),
    ProactiveDeliveryCapability(
        route="/qq/outbox/ack",
        http_method="POST",
        runtime_method="qq_outbox_ack",
        fast_method="qq_outbox_ack_fast",
        contract="ack queued QQ outbox item or proactive delivery message id",
    ),
)

PROACTIVE_CLAIM_DTO_CONTRACT = ProactiveClaimDtoContract(
    required_fields=PROACTIVE_CLAIM_REQUIRED_FIELDS,
    source=PROACTIVE_CLAIM_SOURCE,
    message_id_prefix=PROACTIVE_OUTBOX_MESSAGE_PREFIX,
    target_contract=PROACTIVE_CLAIM_TARGET_CONTRACT,
    attempts=1,
    required_notes=("claimed",),
    state_transitions=PROACTIVE_CLAIM_STATE_TRANSITIONS,
)

PROACTIVE_ACK_DTO_CONTRACT = ProactiveAckDtoContract(
    payload_fields=PROACTIVE_ACK_PAYLOAD_FIELDS,
    status_values=PROACTIVE_ACK_STATUS_VALUES,
    success_fields=PROACTIVE_ACK_RESULT_SUCCESS_FIELDS,
    error_notes=PROACTIVE_ACK_ERROR_NOTES,
    request_status_by_ack_status=PROACTIVE_ACK_STATUS_REQUEST_STATES,
    answer_state_by_ack_status=PROACTIVE_ACK_STATUS_ANSWER_STATES,
    branch_semantics=PROACTIVE_ACK_BRANCH_SEMANTICS,
)

PROACTIVE_GATEWAY_ADAPTER_CONTRACT = ProactiveGatewayAdapterContract(
    gateway_name=PROACTIVE_GATEWAY_ADAPTER_NAME,
    gateway_version_fallback=PROACTIVE_GATEWAY_VERSION_FALLBACK,
    claim_payload_fields=PROACTIVE_GATEWAY_CLAIM_PAYLOAD_FIELDS,
    ack_payload_fields=PROACTIVE_GATEWAY_ACK_PAYLOAD_FIELDS,
    sent_ack_required_fields=PROACTIVE_GATEWAY_SENT_ACK_REQUIRED_FIELDS,
    sent_delivery_routes=PROACTIVE_GATEWAY_SENT_DELIVERY_ROUTES,
    action_success_statuses=PROACTIVE_GATEWAY_ACTION_SUCCESS_STATUSES,
    action_success_retcodes=PROACTIVE_GATEWAY_ACTION_SUCCESS_RETCODES,
    action_timeout_error=PROACTIVE_GATEWAY_ACTION_TIMEOUT_ERROR,
    semantics=(
        "claim_uses_gateway_adapter_name",
        "ack_uses_claim_message_id_and_claim_id",
        "private_outbox_target_requires_user_id",
        "non_private_outbox_target_is_rejected",
        "onebot_timeout_maps_to_adapter_error",
        "sent_delivery_ack_requires_adapter_message_id",
        "proactive_message_id_selects_proactive_delivery_route",
        "ordinary_message_id_selects_qq_outbox_delivery_route",
    ),
)

PROACTIVE_TRANSPORT_HEALTH_CONTRACT = ProactiveTransportHealthContract(
    visible_dispatch_required_config=PROACTIVE_TRANSPORT_VISIBLE_DISPATCH_REQUIRED_CONFIG,
    sent_ack_required_config=PROACTIVE_TRANSPORT_SENT_ACK_REQUIRED_CONFIG,
    disabled_errors=PROACTIVE_TRANSPORT_HEALTH_DISABLED_ERRORS,
    semantics=(
        "visible_outbox_dispatch_requires_enabled_bridge_token_and_send_replies",
        "outbox_poll_rechecks_dispatch_enabled_after_claim_before_send",
        "disabled_after_claim_acks_failed_without_sending",
        "sent_message_ack_spools_before_bridge_delivery",
        "failed_sent_message_ack_remains_pending_for_retry",
        "ack_spool_requires_bridge_token_and_message_ack_url",
        "transport_health_ready_does_not_enable_process_split",
    ),
)

PROACTIVE_TRANSPORT_PREFLIGHT_CONTRACT = ProactiveTransportPreflightContract(
    service_id="proactive_delivery",
    ready=True,
    required_gates=PROACTIVE_TRANSPORT_PREFLIGHT_GATES,
    satisfied_gates=PROACTIVE_TRANSPORT_SATISFIED_GATES,
    missing_gates=tuple(
        gate for gate in PROACTIVE_TRANSPORT_PREFLIGHT_GATES if gate not in PROACTIVE_TRANSPORT_SATISFIED_GATES
    ),
    rollback=PROACTIVE_DELIVERY_ROLLBACK,
    notes=(
        "s4_transport_preflight_contract_only",
        "transport_contracts_ready_for_controlled_process_split",
        "proactive_core_policy_remains_available_as_in_process_fallback",
    ),
)


class ProactiveDeliveryHarness:
    def __init__(self) -> None:
        self._started = False

    def start(self) -> ProactiveDeliveryReadiness:
        self._started = True
        return self.readiness()

    def stop(self) -> ProactiveDeliveryReadiness:
        self._started = False
        return self.readiness()

    def readiness(self) -> ProactiveDeliveryReadiness:
        return ProactiveDeliveryReadiness(
            service_id="proactive_delivery",
            mode="in_process",
            started=self._started,
            ready=self._started,
            state_owner=PROACTIVE_DELIVERY_STATE_OWNER,
            fallback_adapter=PROACTIVE_DELIVERY_FALLBACK_ADAPTER,
            rollback=PROACTIVE_DELIVERY_ROLLBACK,
            notes=("state_store_owned_by_local_proactive_delivery_adapter",),
        )

    @staticmethod
    def fallback_adapter(runtime: Any) -> dict[str, Callable[..., Any]]:
        methods = {
            capability.runtime_method
            for capability in PROACTIVE_DELIVERY_CAPABILITIES
        } | {
            capability.fast_method
            for capability in PROACTIVE_DELIVERY_CAPABILITIES
            if capability.fast_method
        }
        return {method: getattr(runtime, method) for method in methods}


def proactive_delivery_capabilities() -> tuple[ProactiveDeliveryCapability, ...]:
    return PROACTIVE_DELIVERY_CAPABILITIES


def proactive_delivery_routes() -> tuple[str, ...]:
    seen: set[str] = set()
    routes: list[str] = []
    for capability in PROACTIVE_DELIVERY_CAPABILITIES:
        if capability.route in seen:
            continue
        seen.add(capability.route)
        routes.append(capability.route)
    return tuple(routes)


def proactive_claim_dto_contract() -> ProactiveClaimDtoContract:
    return PROACTIVE_CLAIM_DTO_CONTRACT


def proactive_ack_dto_contract() -> ProactiveAckDtoContract:
    return PROACTIVE_ACK_DTO_CONTRACT


def proactive_gateway_adapter_contract() -> ProactiveGatewayAdapterContract:
    return PROACTIVE_GATEWAY_ADAPTER_CONTRACT


def proactive_transport_health_contract() -> ProactiveTransportHealthContract:
    return PROACTIVE_TRANSPORT_HEALTH_CONTRACT


def proactive_transport_preflight_contract(
    satisfied_gates: tuple[str, ...] | None = None,
) -> ProactiveTransportPreflightContract:
    provided_gates = set(PROACTIVE_TRANSPORT_SATISFIED_GATES if satisfied_gates is None else satisfied_gates)
    normalized_satisfied = tuple(
        gate for gate in PROACTIVE_TRANSPORT_PREFLIGHT_GATES if gate in provided_gates
    )
    missing = tuple(
        gate for gate in PROACTIVE_TRANSPORT_PREFLIGHT_GATES if gate not in normalized_satisfied
    )
    return ProactiveTransportPreflightContract(
        service_id="proactive_delivery",
        ready=not missing,
        required_gates=PROACTIVE_TRANSPORT_PREFLIGHT_GATES,
        satisfied_gates=normalized_satisfied,
        missing_gates=missing,
        rollback=PROACTIVE_DELIVERY_ROLLBACK,
        notes=PROACTIVE_TRANSPORT_PREFLIGHT_CONTRACT.notes,
    )


def proactive_outbox_message_id(request_id: Any) -> str:
    return f"{PROACTIVE_OUTBOX_MESSAGE_PREFIX}{str(request_id).strip()}"


def is_proactive_outbox_message_id(message_id: Any) -> bool:
    return str(message_id or "").strip().startswith(PROACTIVE_OUTBOX_MESSAGE_PREFIX)
