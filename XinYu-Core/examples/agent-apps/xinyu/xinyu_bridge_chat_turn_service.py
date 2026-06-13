from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xinyu_bridge_chat_turn_contract import (
    CHAT_TURN_FALLBACK_ADAPTER,
    CHAT_TURN_PROCESS_SPLIT_ALLOWED,
    CHAT_TURN_ROLLBACK,
    CHAT_TURN_STATE_OWNER,
    chat_turn_control_plane_routes,
    chat_turn_execution_routes,
    chat_turn_routes,
    chat_turn_runtime_methods,
    chat_turn_token_required_routes,
)


CHAT_TURN_SERVICE_ID = "chat_turn"
CHAT_TURN_SERVICE_MODE_LOCAL = "local_only_in_process"


@dataclass(frozen=True, slots=True)
class ChatTurnServiceConfig:
    mode: str = CHAT_TURN_SERVICE_MODE_LOCAL


@dataclass(frozen=True, slots=True)
class ChatTurnServiceReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    local_only: bool
    process_split_candidate: bool
    process_split_ready: bool
    runtime_method_available: bool
    chat_service_available: bool
    api_routes: tuple[str, ...]
    runtime_facade_methods: tuple[str, ...]
    execution_routes: tuple[str, ...]
    control_plane_routes: tuple[str, ...]
    token_required_routes: tuple[str, ...]
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


class ChatTurnServiceHandle:
    def __init__(self, config: ChatTurnServiceConfig) -> None:
        self.config = config
        self._started = False

    def start(self, runtime: Any) -> ChatTurnServiceReadiness:
        self._started = True
        return self.readiness(runtime)

    def close(self, runtime: Any) -> ChatTurnServiceReadiness:
        self._started = False
        return self.readiness(runtime)

    def readiness(self, runtime: Any | None = None) -> ChatTurnServiceReadiness:
        runtime_method_available = callable(getattr(runtime, "chat", None))
        service = getattr(runtime, "chat_service", None)
        chat_service_available = (
            callable(getattr(service, "prepare_request", None))
            and callable(getattr(service, "start_turn_clock", None))
        )
        return ChatTurnServiceReadiness(
            service_id=CHAT_TURN_SERVICE_ID,
            mode=self.config.mode,
            started=self._started,
            ready=self._started and runtime_method_available and chat_service_available,
            local_only=not CHAT_TURN_PROCESS_SPLIT_ALLOWED,
            process_split_candidate=CHAT_TURN_PROCESS_SPLIT_ALLOWED,
            process_split_ready=False,
            runtime_method_available=runtime_method_available,
            chat_service_available=chat_service_available,
            api_routes=chat_turn_routes(),
            runtime_facade_methods=chat_turn_runtime_methods(),
            execution_routes=chat_turn_execution_routes(),
            control_plane_routes=chat_turn_control_plane_routes(),
            token_required_routes=chat_turn_token_required_routes(),
            state_owner=CHAT_TURN_STATE_OWNER,
            fallback_adapter=CHAT_TURN_FALLBACK_ADAPTER,
            rollback=CHAT_TURN_ROLLBACK,
            notes=(
                "local_only_runtime_service",
                "not_process_split_candidate",
                "chat_execution_path_unchanged",
                "runtime_chat_method_remains_monkeypatchable",
                "control_plane_routes_remain_in_process",
            ),
        )


def build_chat_turn_service_handle(config: ChatTurnServiceConfig | None = None) -> ChatTurnServiceHandle:
    return ChatTurnServiceHandle(ChatTurnServiceConfig() if config is None else config)


def chat_turn_service_readiness(runtime: Any) -> ChatTurnServiceReadiness:
    handle = getattr(runtime, "_chat_turn_service", None)
    if handle is None:
        return build_chat_turn_service_handle().readiness(runtime)
    return handle.readiness(runtime)
