from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xinyu_bridge_http_routes import post_route_requires_bridge_token


CHAT_TURN_PROCESS_SPLIT_ALLOWED = False
CHAT_TURN_STATE_OWNER = "chat_service_prepared_in_process_slow_live_runtime_state"
CHAT_TURN_FALLBACK_ADAPTER = "in_process_runtime_chat_and_control_methods"
CHAT_TURN_ROLLBACK = "route_chat_turn_back_to_current_runtime_facade"

CHAT_TURN_PROTECTED_MODULES = (
    "xinyu_bridge_chat_turn.py",
    "xinyu_bridge_turn_pipeline.py",
    "xinyu_bridge_slow_live_turn.py",
    "xinyu_bridge_session.py",
    "xinyu_bridge_intervention_routes.py",
    "xinyu_bridge_utility_message.py",
)


@dataclass(frozen=True, slots=True)
class ChatTurnCapability:
    route: str
    http_method: str
    runtime_method: str
    contract: str
    kind: str = "execution"
    requires_bridge_token: bool = False


@dataclass(frozen=True, slots=True)
class ChatTurnReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    api_routes: tuple[str, ...]
    runtime_facade_methods: tuple[str, ...]
    execution_routes: tuple[str, ...]
    control_plane_routes: tuple[str, ...]
    token_required_routes: tuple[str, ...]
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


CHAT_TURN_CAPABILITIES = (
    ChatTurnCapability(
        route="/chat",
        http_method="POST",
        runtime_method="chat",
        contract="local chat turn execution; request prepared by ChatService; slow-live runtime remains in-process",
    ),
    ChatTurnCapability(
        route="/internal/message/ack",
        http_method="POST",
        runtime_method="message_ack",
        contract="local post-reply feedback acknowledgement; session/action feedback remains in-process",
        kind="message_feedback",
        requires_bridge_token=True,
    ),
    ChatTurnCapability(
        route="/internal/message/drop",
        http_method="POST",
        runtime_method="message_drop",
        contract="local post-reply retraction feedback; dialogue tail/archive mutation remains in-process",
        kind="message_feedback",
        requires_bridge_token=True,
    ),
    ChatTurnCapability(
        route="/turn/cancel",
        http_method="POST",
        runtime_method="turn_cancel",
        contract="local operator turn intervention; running turn state remains in-process",
        kind="turn_control",
    ),
    ChatTurnCapability(
        route="/turn/retry-lightweight",
        http_method="POST",
        runtime_method="turn_retry_lightweight",
        contract="local operator turn retry intervention; slow-live runtime remains in-process",
        kind="turn_control",
    ),
    ChatTurnCapability(
        route="/turn/skip-sidecar",
        http_method="POST",
        runtime_method="turn_skip_sidecar",
        contract="local operator sidecar skip intervention; turn route trace remains in-process",
        kind="turn_control",
    ),
    ChatTurnCapability(
        route="/turn/continue",
        http_method="POST",
        runtime_method="turn_continue",
        contract="local operator continue intervention; turn route trace remains in-process",
        kind="turn_control",
    ),
    ChatTurnCapability(
        route="/turn/status-message",
        http_method="POST",
        runtime_method="turn_status_message",
        contract="local read-only turn status message rendering; operator state remains in-process",
        kind="turn_control",
    ),
)


class ChatTurnHarness:
    def __init__(self) -> None:
        self._started = False

    def start(self) -> ChatTurnReadiness:
        self._started = True
        return self.readiness()

    def stop(self) -> ChatTurnReadiness:
        self._started = False
        return self.readiness()

    def readiness(self) -> ChatTurnReadiness:
        return ChatTurnReadiness(
            service_id="chat_turn",
            mode="in_process",
            started=self._started,
            ready=self._started,
            api_routes=chat_turn_routes(),
            runtime_facade_methods=chat_turn_runtime_methods(),
            execution_routes=chat_turn_execution_routes(),
            control_plane_routes=chat_turn_control_plane_routes(),
            token_required_routes=chat_turn_token_required_routes(),
            state_owner=CHAT_TURN_STATE_OWNER,
            fallback_adapter=CHAT_TURN_FALLBACK_ADAPTER,
            rollback=CHAT_TURN_ROLLBACK,
            notes=(
                "chat_service_remains_request_preparer",
                "runtime_chat_method_remains_monkeypatchable",
                "control_plane_routes_remain_in_process",
            ),
        )

    @staticmethod
    def fallback_adapter(runtime: Any) -> dict[str, Callable[..., Any]]:
        return {
            capability.runtime_method: getattr(runtime, capability.runtime_method)
            for capability in CHAT_TURN_CAPABILITIES
        }


def chat_turn_capabilities() -> tuple[ChatTurnCapability, ...]:
    return CHAT_TURN_CAPABILITIES


def chat_turn_routes() -> tuple[str, ...]:
    return tuple(capability.route for capability in CHAT_TURN_CAPABILITIES)


def chat_turn_runtime_methods() -> tuple[str, ...]:
    return tuple(capability.runtime_method for capability in CHAT_TURN_CAPABILITIES)


def chat_turn_execution_routes() -> tuple[str, ...]:
    return tuple(capability.route for capability in CHAT_TURN_CAPABILITIES if capability.kind == "execution")


def chat_turn_control_plane_routes() -> tuple[str, ...]:
    return tuple(capability.route for capability in CHAT_TURN_CAPABILITIES if capability.kind != "execution")


def chat_turn_token_required_routes() -> tuple[str, ...]:
    return tuple(route for route in chat_turn_routes() if post_route_requires_bridge_token(route))
