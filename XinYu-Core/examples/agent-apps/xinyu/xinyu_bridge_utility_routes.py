from __future__ import annotations

import asyncio
from http import HTTPStatus
from typing import Any

from xinyu_action_feedback_surface import record_action_feedback_from_message_ack
from xinyu_action_feedback_surface import record_action_feedback_from_message_drop
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_learning import LearningBridgeError
from xinyu_bridge_learning_ingest_route_backend import maybe_execute_learning_ingest_backend
import xinyu_bridge_utility_route_helpers as _helpers
from xinyu_dialogue_archive import retract_archived_assistant_message
from xinyu_dialogue_working_memory import remove_matching_assistant_reply
from xinyu_dialogue_working_memory import remove_matching_assistant_reply_from_tail
from xinyu_dialogue_working_memory import save_dialogue_tail
from xinyu_goldmark import mark_goldmark_request as mark_goldmark_request_bridge
from xinyu_package_installer import install_python_packages
from xinyu_review_inbox import handle_review_inbox_command
from xinyu_sent_reply_index import register_sent_reply_ack
from xinyu_sticker_ingest import import_sticker_from_payload


def _deps() -> _helpers.UtilityRouteDeps:
    return _helpers.UtilityRouteDeps(
        bridge_request_error_type=BridgeRequestError,
        learning_bridge_error_type=LearningBridgeError,
        bad_request_status=HTTPStatus.BAD_REQUEST,
        service_unavailable_status=HTTPStatus.SERVICE_UNAVAILABLE,
        to_thread=asyncio.to_thread,
        handle_review_inbox_command=handle_review_inbox_command,
        install_python_packages=install_python_packages,
        import_sticker_from_payload=import_sticker_from_payload,
        register_sent_reply_ack=register_sent_reply_ack,
        record_action_feedback_from_message_ack=record_action_feedback_from_message_ack,
        record_action_feedback_from_message_drop=record_action_feedback_from_message_drop,
        remove_matching_assistant_reply_from_tail=remove_matching_assistant_reply_from_tail,
        save_dialogue_tail=save_dialogue_tail,
        remove_matching_assistant_reply=remove_matching_assistant_reply,
        retract_archived_assistant_message=retract_archived_assistant_message,
        mark_goldmark_request=mark_goldmark_request_bridge,
    )


def _sessions(runtime: Any) -> int:
    return _helpers.sessions(runtime)


def _ensure_open(runtime: Any) -> None:
    _helpers.ensure_open(runtime, _deps())


def _ensure_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    return _helpers.ensure_payload(payload, _deps())


def _payload_or_empty(payload: dict[str, Any] | None) -> dict[str, Any]:
    return _helpers.payload_or_empty(payload, _deps())


async def probe(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    bridge_version: str,
) -> dict[str, Any]:
    """No-memory diagnostic endpoint.

    This intentionally does not start an Agent, create a session, render a
    reply, or inject a turn. It is for startup/status checks that should not
    become lived context.
    """
    return await _helpers.probe(runtime, payload, bridge_version=bridge_version, deps=_deps())


async def runtime_probe(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _helpers.runtime_probe(runtime, payload, deps=_deps())


async def review_inbox_command(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _helpers.review_inbox_command(runtime, payload, deps=_deps())


async def package_install(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _helpers.package_install(runtime, payload, deps=_deps())


async def learning_ingest(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_learning_ingest_backend(
        runtime,
        payload,
        route="/learning/ingest",
        http_method="POST",
        runtime_method="learning_ingest",
        service_method="ingest",
    )
    if backend_result is not None:
        return backend_result
    return await _helpers.learning_ingest(runtime, payload, deps=_deps())


async def learning_study(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_learning_ingest_backend(
        runtime,
        payload,
        route="/learning/study",
        http_method="POST",
        runtime_method="learning_study",
        service_method="study",
    )
    if backend_result is not None:
        return backend_result
    return await _helpers.learning_study(runtime, payload, deps=_deps())


async def learning_observe(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_learning_ingest_backend(
        runtime,
        payload,
        route="/learning/observe",
        http_method="POST",
        runtime_method="learning_observe",
        service_method="observe",
    )
    if backend_result is not None:
        return backend_result
    return await _helpers.learning_observe(runtime, payload, deps=_deps())


async def sticker_import(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _helpers.sticker_import(runtime, payload, deps=_deps())


async def message_ack(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _helpers.message_ack(runtime, payload, deps=_deps())


async def message_drop(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _helpers.message_drop(runtime, payload, deps=_deps())


async def goldmark_mark_request(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _helpers.goldmark_mark_request(runtime, payload, deps=_deps())
