from __future__ import annotations

from typing import Any, Callable, Mapping

import xinyu_bridge_desktop_proactive_bindings as _proactive_bindings
import xinyu_bridge_desktop_proactive_route_glue as _proactive_route_glue


DepsProvider = Callable[[], Any]
FacadeProvider = Callable[[], Mapping[str, Any]]


def build_desktop_proactive_ack_facade(
    *,
    deps_provider: DepsProvider,
    facade_provider: FacadeProvider,
) -> dict[str, Callable[..., Any]]:
    async def desktop_proactive_ack(
        runtime: Any,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await _proactive_route_glue.desktop_proactive_ack(runtime, payload, facade=facade_provider())

    async def desktop_finish_proactive_ack(
        runtime: Any,
        item: dict[str, Any],
        *,
        action: str,
        status: str,
        answer_state: str,
        ack_status: str,
        notes: list[str],
        adapter_message_id: str = "",
        adapter_error: str = "",
        extra: dict[str, Any] | None = None,
        claim_id: str = "",
    ) -> dict[str, Any]:
        return await _proactive_bindings.desktop_finish_proactive_ack(
            runtime,
            item,
            action=action,
            status=status,
            answer_state=answer_state,
            ack_status=ack_status,
            notes=notes,
            adapter_message_id=adapter_message_id,
            adapter_error=adapter_error,
            extra=extra,
            claim_id=claim_id,
            deps=deps_provider(),
        )

    async def desktop_approve_proactive_qq(runtime: Any, item: dict[str, Any]) -> dict[str, Any]:
        return await _proactive_bindings.desktop_approve_proactive_qq(
            runtime,
            item,
            current_question_func=facade_provider()["desktop_current_proactive_question"],
            deps=deps_provider(),
        )

    def desktop_update_proactive_request_state(
        runtime: Any,
        *,
        candidate_id: str,
        status: str,
        answer_state: str = "",
        ack_status: str = "",
        adapter_message_id: str = "",
        adapter_error: str = "",
        claim_id: str = "",
    ) -> dict[str, Any]:
        return _proactive_bindings.desktop_update_proactive_request_state(
            runtime,
            candidate_id=candidate_id,
            status=status,
            answer_state=answer_state,
            ack_status=ack_status,
            adapter_message_id=adapter_message_id,
            adapter_error=adapter_error,
            claim_id=claim_id,
            deps=deps_provider(),
        )

    return {
        "desktop_proactive_ack": desktop_proactive_ack,
        "desktop_finish_proactive_ack": desktop_finish_proactive_ack,
        "desktop_approve_proactive_qq": desktop_approve_proactive_qq,
        "desktop_update_proactive_request_state": desktop_update_proactive_request_state,
    }
