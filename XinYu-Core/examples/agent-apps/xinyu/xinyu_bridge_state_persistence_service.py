from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from xinyu_bridge_state_persistence_contract import (
    StatePersistenceLocalHarness,
    StatePersistenceReadiness,
    state_persistence_default_local_adapters,
)


STATE_PERSISTENCE_SERVICE_MODE_LOCAL = "local_consolidation_only"


@dataclass(frozen=True, slots=True)
class StatePersistenceServiceConfig:
    mode: str = STATE_PERSISTENCE_SERVICE_MODE_LOCAL


class StatePersistenceServiceHandle:
    def __init__(
        self,
        config: StatePersistenceServiceConfig,
        *,
        local_adapters: Mapping[str, Callable[..., Any]] | None = None,
    ) -> None:
        self.config = config
        self._harness = StatePersistenceLocalHarness(
            state_persistence_default_local_adapters() if local_adapters is None else dict(local_adapters)
        )

    def start(self, runtime: Any | None = None) -> StatePersistenceReadiness:
        return self._harness.start()

    def close(self, runtime: Any | None = None) -> StatePersistenceReadiness:
        return self._harness.stop()

    def readiness(self, runtime: Any | None = None) -> StatePersistenceReadiness:
        return self._harness.readiness()

    def fallback_adapter(self) -> dict[str, Callable[..., Any]]:
        return self._harness.fallback_adapter()


def build_state_persistence_service_handle(
    config: StatePersistenceServiceConfig | None = None,
    *,
    local_adapters: Mapping[str, Callable[..., Any]] | None = None,
) -> StatePersistenceServiceHandle:
    return StatePersistenceServiceHandle(
        StatePersistenceServiceConfig() if config is None else config,
        local_adapters=local_adapters,
    )


def state_persistence_service_readiness(runtime: Any) -> StatePersistenceReadiness:
    handle = getattr(runtime, "_state_persistence_service", None)
    if handle is None:
        return build_state_persistence_service_handle().readiness(runtime)
    return handle.readiness(runtime)
