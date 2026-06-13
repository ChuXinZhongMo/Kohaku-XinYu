from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

TimeoutResolver = int | Callable[[int], int]


@dataclass(frozen=True)
class RuntimeRouteSpec:
    method: str
    timeout: TimeoutResolver
    fast_method: str | None = None
    status_from_http_status: bool = False

    def resolve_timeout(self, request_timeout_seconds: int) -> int:
        if callable(self.timeout):
            return self.timeout(request_timeout_seconds)
        return self.timeout


def request_timeout(request_timeout_seconds: int) -> int:
    return request_timeout_seconds


def timeout_at_least(minimum_seconds: int) -> Callable[[int], int]:
    return lambda request_timeout_seconds: max(minimum_seconds, request_timeout_seconds)


GET_ROUTE_DISPATCH: dict[str, RuntimeRouteSpec] = {
    "/probe": RuntimeRouteSpec("probe", 10),
    "/proactive": RuntimeRouteSpec("proactive", 10),
    "/desktop/snapshot": RuntimeRouteSpec("desktop_snapshot", 5),
    "/desktop/events/recent": RuntimeRouteSpec("desktop_events_recent", 5),
    "/desktop/proactive/inbox": RuntimeRouteSpec("desktop_proactive_inbox", 5),
    "/desktop/chat/recent": RuntimeRouteSpec("desktop_chat_recent", 5),
    "/desktop/memory/recent": RuntimeRouteSpec("desktop_memory_recent", 5),
    "/desktop/memory/growth-candidates": RuntimeRouteSpec(
        "desktop_memory_growth_candidates",
        5,
    ),
    "/desktop/private-ecosystem/snapshot": RuntimeRouteSpec(
        "desktop_private_ecosystem_snapshot",
        5,
    ),
    "/desktop/private-browser/snapshot": RuntimeRouteSpec(
        "desktop_private_browser_snapshot",
        5,
    ),
    "/desktop/private-desktop/snapshot": RuntimeRouteSpec(
        "desktop_private_desktop_snapshot",
        15,
    ),
    "/desktop/private-desktop/live-state": RuntimeRouteSpec(
        "desktop_private_desktop_live_state",
        15,
    ),
    "/desktop/private-desktop/frame": RuntimeRouteSpec(
        "desktop_private_desktop_frame",
        10,
    ),
    "/external/plugins": RuntimeRouteSpec("external_plugin_manifest", 5),
    "/turn/current": RuntimeRouteSpec("turn_current", 5),
}


LIFE_TICKET_ACTION_METHODS: dict[str, str] = {
    "approve": "life_metabolism_ticket_approve",
    "reject": "life_metabolism_ticket_reject",
    "cancel": "life_metabolism_ticket_cancel",
}


POST_ROUTE_DISPATCH: dict[str, RuntimeRouteSpec] = {
    "/probe": RuntimeRouteSpec("probe", 10),
    "/proactive": RuntimeRouteSpec("proactive", 10),
    "/proactive/ack": RuntimeRouteSpec("proactive_ack", 10),
    "/desktop/proactive/ack": RuntimeRouteSpec("desktop_proactive_ack", 10),
    "/desktop/self-action/approval": RuntimeRouteSpec(
        "desktop_self_action_approval",
        10,
    ),
    "/desktop/private-ecosystem/pause": RuntimeRouteSpec(
        "desktop_private_ecosystem_pause",
        10,
    ),
    "/desktop/private-ecosystem/grant": RuntimeRouteSpec(
        "desktop_private_ecosystem_grant",
        10,
    ),
    "/desktop/private-ecosystem/tick": RuntimeRouteSpec(
        "desktop_private_ecosystem_tick",
        15,
    ),
    "/desktop/private-browser/action": RuntimeRouteSpec(
        "desktop_private_browser_action",
        timeout_at_least(45),
    ),
    "/desktop/private-desktop/observe": RuntimeRouteSpec(
        "desktop_private_desktop_observe",
        timeout_at_least(30),
    ),
    "/desktop/private-desktop/start": RuntimeRouteSpec(
        "desktop_private_desktop_start",
        timeout_at_least(45),
    ),
    "/desktop/private-desktop/stop": RuntimeRouteSpec(
        "desktop_private_desktop_stop",
        timeout_at_least(30),
    ),
    "/qq/outbox/claim": RuntimeRouteSpec(
        "qq_outbox_claim",
        10,
        fast_method="qq_outbox_claim_fast",
    ),
    "/qq/outbox/ack": RuntimeRouteSpec(
        "qq_outbox_ack",
        10,
        fast_method="qq_outbox_ack_fast",
    ),
    "/internal/message/ack": RuntimeRouteSpec("message_ack", 10),
    "/internal/message/drop": RuntimeRouteSpec("message_drop", 10),
    "/review/inbox/command": RuntimeRouteSpec("review_inbox_command", 10),
    "/review/goldmark/mark_request": RuntimeRouteSpec(
        "goldmark_mark_request",
        10,
        status_from_http_status=True,
    ),
    "/learning/ingest": RuntimeRouteSpec("learning_ingest", request_timeout),
    "/learning/study": RuntimeRouteSpec("learning_study", request_timeout),
    "/learning/observe": RuntimeRouteSpec("learning_observe", request_timeout),
    "/sticker/import": RuntimeRouteSpec("sticker_import", request_timeout),
    "/package/install": RuntimeRouteSpec("package_install", request_timeout),
    "/codex/execute": RuntimeRouteSpec("codex_execute", request_timeout),
    "/external/call": RuntimeRouteSpec("external_plugin_call", request_timeout),
    "/external/plugins/config": RuntimeRouteSpec("external_plugin_config", 10),
    "/external/plugins/install": RuntimeRouteSpec(
        "external_plugin_install",
        request_timeout,
    ),
    "/turn/cancel": RuntimeRouteSpec("turn_cancel", 10),
    "/turn/retry-lightweight": RuntimeRouteSpec("turn_retry_lightweight", 10),
    "/turn/skip-sidecar": RuntimeRouteSpec("turn_skip_sidecar", 10),
    "/turn/continue": RuntimeRouteSpec("turn_continue", 10),
    "/turn/status-message": RuntimeRouteSpec("turn_status_message", 10),
    "/chat": RuntimeRouteSpec("chat", request_timeout),
}
