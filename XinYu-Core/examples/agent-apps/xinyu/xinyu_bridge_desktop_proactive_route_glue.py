from __future__ import annotations

from typing import Any, Mapping

import xinyu_bridge_desktop_proactive_inbox as _proactive_inbox
import xinyu_bridge_desktop_proactive_payloads as _proactive_payloads
import xinyu_bridge_desktop_proactive_route_ack as _proactive_route_ack
from xinyu_bridge_desktop_proactive_deps_support import DesktopProactiveDeps
from xinyu_bridge_proactive_delivery_route_backend import maybe_execute_proactive_delivery_backend


DESKTOP_PROACTIVE_INBOX_MAX = _proactive_inbox.DESKTOP_PROACTIVE_INBOX_MAX
DESKTOP_PROACTIVE_HISTORY_MAX = _proactive_inbox.DESKTOP_PROACTIVE_HISTORY_MAX
DESKTOP_PROACTIVE_HISTORY_REL = _proactive_inbox.DESKTOP_PROACTIVE_HISTORY_REL
DESKTOP_PROACTIVE_INBOX_STATUSES = _proactive_inbox.DESKTOP_PROACTIVE_INBOX_STATUSES
DESKTOP_PROACTIVE_ACK_ACTIONS = _proactive_payloads.DESKTOP_PROACTIVE_ACK_ACTIONS
DESKTOP_PROACTIVE_FINAL_STATUSES = _proactive_inbox.DESKTOP_PROACTIVE_FINAL_STATUSES

ensure_payload = _proactive_payloads.ensure_payload


def facade_deps(facade: Mapping[str, Any]) -> DesktopProactiveDeps:
    return DesktopProactiveDeps(
        safe_str=facade["_safe_str"],
        dedupe=facade["_dedupe"],
        as_bool=facade["_as_bool"],
        read_text_safe=facade["_read_text_safe"],
        state_field=facade["_state_field"],
        desktop_hash=facade["desktop_hash"],
        desktop_text_preview=facade["desktop_text_preview"],
        compose_visible_message=facade["compose_proactive_visible_message"],
        record_initiative_feedback=facade["record_initiative_feedback"],
        runtime_owner_private_turns=facade["runtime_owner_private_turns"],
        enqueue_qq_outbox_message=facade["enqueue_qq_outbox_message"],
        write_proactive_qq_dispatch_state=facade["write_proactive_qq_dispatch_state"],
        append_jsonl=facade["append_jsonl"],
        atomic_write_text=facade["atomic_write_text"],
        inbox_max=facade["DESKTOP_PROACTIVE_INBOX_MAX"],
        history_max=facade["DESKTOP_PROACTIVE_HISTORY_MAX"],
        history_rel=facade["DESKTOP_PROACTIVE_HISTORY_REL"],
        inbox_statuses=facade["DESKTOP_PROACTIVE_INBOX_STATUSES"],
        final_statuses=facade["DESKTOP_PROACTIVE_FINAL_STATUSES"],
    )


async def desktop_proactive_ack(
    runtime: Any,
    payload: dict[str, Any] | None,
    *,
    facade: Mapping[str, Any],
) -> dict[str, Any]:
    backend_result = await maybe_execute_proactive_delivery_backend(
        runtime,
        payload,
        route="/desktop/proactive/ack",
        http_method="POST",
        runtime_method="desktop_proactive_ack",
    )
    if backend_result is not None:
        return backend_result
    return await _proactive_route_ack.desktop_proactive_ack(
        runtime,
        payload,
        safe_str=facade["_safe_str"],
        ensure_payload_func=facade["_ensure_payload"],
        ack_actions=facade["DESKTOP_PROACTIVE_ACK_ACTIONS"],
    )
