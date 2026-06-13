from __future__ import annotations

import asyncio
import time
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_proactive import acknowledge as proactive_ack_bridge
from xinyu_bridge_proactive import claim_or_preview as proactive_bridge
from xinyu_bridge_proactive_delivery_routes_ack import acknowledge_proactive as _acknowledge_proactive
from xinyu_bridge_proactive_delivery_routes_ack import qq_outbox_ack as _qq_outbox_ack
from xinyu_bridge_proactive_delivery_routes_ack import qq_outbox_ack_fast as _qq_outbox_ack_fast
from xinyu_bridge_proactive_delivery_routes_claim import (
    claim_proactive_for_qq_outbox as _claim_proactive_for_qq_outbox,
)
from xinyu_bridge_proactive_delivery_routes_claim import (
    claim_proactive_for_qq_outbox_sync as _claim_proactive_for_qq_outbox_sync,
)
from xinyu_bridge_proactive_delivery_routes_claim import qq_outbox_claim as _qq_outbox_claim
from xinyu_bridge_proactive_delivery_routes_claim import qq_outbox_claim_fast as _qq_outbox_claim_fast
from xinyu_bridge_proactive_delivery_routes_outbound import (
    proactive_candidate_already_handled as _proactive_candidate_already_handled,
)
from xinyu_bridge_proactive_delivery_routes_outbound import (
    ready_proactive_outbox_candidate as _ready_proactive_outbox_candidate,
)
from xinyu_bridge_proactive_delivery_routes_outbound import (
    record_proactive_outbound_dialogue as _record_proactive_outbound_dialogue,
)
from xinyu_bridge_proactive_delivery_routes_payload import ensure_open as _ensure_open
from xinyu_bridge_proactive_delivery_routes_payload import ensure_payload as _ensure_payload
from xinyu_bridge_proactive_delivery_routes_payload import result_notes as _result_notes
from xinyu_bridge_proactive_delivery_routes_payload import timestamp_or_now_iso as _timestamp_or_now_iso_helper
from xinyu_bridge_proactive_delivery_routes_response import proactive as _proactive
from xinyu_bridge_proactive_delivery_route_backend import (
    maybe_execute_proactive_delivery_backend,
    maybe_execute_proactive_delivery_backend_sync,
)
from xinyu_bridge_state_text import read_text_safe as _read_text_safe
from xinyu_bridge_state_text import state_field as _state_field
from xinyu_bridge_values import as_int as _as_int
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_dialogue_archive import archive_message
from xinyu_private_ecosystem_grants import load_share_block_reasons
from xinyu_proactive_context_adapter import runtime_owner_private_turns
from xinyu_proactive_presence import acknowledge_proactive_qq_message
from xinyu_proactive_presence import claim_proactive_qq_message
from xinyu_qq_outbox import ack_qq_outbox_message
from xinyu_qq_outbox import claim_next_qq_outbox_message
from xinyu_visible_persona_voice import compose_proactive_visible_message


def _timestamp_or_now_iso(value: Any = None) -> str:
    return _timestamp_or_now_iso_helper(value, safe_str_func=_safe_str)


async def proactive(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    backend_result = await maybe_execute_proactive_delivery_backend(
        runtime,
        payload,
        route="/proactive",
        http_method="GET_OR_POST",
        runtime_method="proactive",
    )
    if backend_result is not None:
        return backend_result
    return await _proactive(
        runtime,
        payload,
        proactive_bridge_func=proactive_bridge,
        safe_str_func=_safe_str,
        result_notes_func=_result_notes,
        bridge_request_error_type=BridgeRequestError,
    )


async def proactive_ack(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    backend_result = await maybe_execute_proactive_delivery_backend(
        runtime,
        payload,
        route="/proactive/ack",
        http_method="POST",
        runtime_method="proactive_ack",
    )
    if backend_result is not None:
        return backend_result
    return await _acknowledge_proactive(
        runtime,
        payload,
        proactive_ack_bridge_func=proactive_ack_bridge,
        safe_str_func=_safe_str,
    )


async def qq_outbox_claim(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    backend_result = await maybe_execute_proactive_delivery_backend(
        runtime,
        payload,
        route="/qq/outbox/claim",
        http_method="POST",
        runtime_method="qq_outbox_claim",
    )
    if backend_result is not None:
        return backend_result
    return await _qq_outbox_claim(
        runtime,
        payload,
        claim_next_message_func=claim_next_qq_outbox_message,
        to_thread_func=asyncio.to_thread,
    )


def qq_outbox_claim_fast(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    backend_result = maybe_execute_proactive_delivery_backend_sync(
        runtime,
        payload,
        route="/qq/outbox/claim",
        http_method="POST",
        runtime_method="qq_outbox_claim_fast",
    )
    if backend_result is not None:
        return backend_result
    return _qq_outbox_claim_fast(
        runtime,
        payload,
        claim_next_message_func=claim_next_qq_outbox_message,
    )


async def qq_outbox_ack(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    backend_result = await maybe_execute_proactive_delivery_backend(
        runtime,
        payload,
        route="/qq/outbox/ack",
        http_method="POST",
        runtime_method="qq_outbox_ack",
    )
    if backend_result is not None:
        return backend_result
    return await _qq_outbox_ack(
        runtime,
        payload,
        proactive_ack_bridge_func=proactive_ack_bridge,
        ack_outbox_message_func=ack_qq_outbox_message,
        to_thread_func=asyncio.to_thread,
        safe_str_func=_safe_str,
        record_outbound_func=record_proactive_outbound_dialogue,
    )


def qq_outbox_ack_fast(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    backend_result = maybe_execute_proactive_delivery_backend_sync(
        runtime,
        payload,
        route="/qq/outbox/ack",
        http_method="POST",
        runtime_method="qq_outbox_ack_fast",
    )
    if backend_result is not None:
        return backend_result
    return _qq_outbox_ack_fast(
        runtime,
        payload,
        acknowledge_proactive_qq_message_func=acknowledge_proactive_qq_message,
        ack_outbox_message_func=ack_qq_outbox_message,
        safe_str_func=_safe_str,
        record_outbound_func=record_proactive_outbound_dialogue,
    )


async def claim_proactive_for_qq_outbox(runtime: Any, payload: dict[str, Any]) -> dict[str, Any] | None:
    return await _claim_proactive_for_qq_outbox(
        runtime,
        payload,
        proactive_bridge_func=proactive_bridge,
        owner_private_turns_func=runtime_owner_private_turns,
        load_share_block_reasons_func=load_share_block_reasons,
        compose_visible_message_func=compose_proactive_visible_message,
        safe_str_func=_safe_str,
        time_func=time.time,
    )


def claim_proactive_for_qq_outbox_sync(runtime: Any, payload: dict[str, Any]) -> dict[str, Any] | None:
    return _claim_proactive_for_qq_outbox_sync(
        runtime,
        payload,
        claim_proactive_qq_message_func=claim_proactive_qq_message,
        owner_private_turns_func=runtime_owner_private_turns,
        load_share_block_reasons_func=load_share_block_reasons,
        compose_visible_message_func=compose_proactive_visible_message,
        safe_str_func=_safe_str,
        as_int_func=_as_int,
        time_func=time.time,
    )


def ready_proactive_outbox_candidate(runtime: Any) -> str:
    return _ready_proactive_outbox_candidate(
        runtime,
        read_text_safe_func=_read_text_safe,
        state_field_func=_state_field,
    )


def proactive_candidate_already_handled(runtime: Any, candidate: str) -> bool:
    return _proactive_candidate_already_handled(
        runtime,
        candidate,
        read_text_safe_func=_read_text_safe,
        state_field_func=_state_field,
    )


def record_proactive_outbound_dialogue(runtime: Any, ack_payload: dict[str, Any]) -> None:
    _record_proactive_outbound_dialogue(
        runtime,
        ack_payload,
        read_text_safe_func=_read_text_safe,
        state_field_func=_state_field,
        timestamp_or_now_iso_func=_timestamp_or_now_iso,
        safe_str_func=_safe_str,
        archive_message_func=archive_message,
    )
