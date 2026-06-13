from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_SURFACE_FALLBACK_ADAPTER,
    DESKTOP_SURFACE_ROLLBACK,
    DESKTOP_SURFACE_STATE_OWNER,
)


DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_RUNTIME_ATTR = "_desktop_surface_snapshot_state_backend"
DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_MODE = "desktop_surface_snapshot_state_backend_in_process"
DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_ROLLBACK = (
    "remove_runtime_snapshot_state_backend_attr_to_use_current_runtime_snapshot_methods"
)


class DesktopSurfaceSnapshotStateBackend(Protocol):
    mode: str

    def root(self, runtime: Any) -> Path:
        ...

    async def prepare_self_choice(self, runtime: Any) -> None:
        ...

    async def self_choice_private(self, runtime: Any) -> dict[str, Any]:
        ...

    async def self_choice_public(self, runtime: Any) -> dict[str, Any]:
        ...

    async def event_state(self, runtime: Any) -> dict[str, Any]:
        ...

    async def active_desires(
        self,
        runtime: Any,
        *,
        environment: dict[str, Any],
        entropy_state: Any,
        proactive_items: list[Any],
        recent_turns: list[Any],
        recent_memory_events: list[Any],
        self_choice_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        ...

    def health_snapshot(self, runtime: Any) -> dict[str, Any]:
        ...

    def services(self, runtime: Any) -> list[dict[str, Any]]:
        ...

    def xinyu_state(
        self,
        runtime: Any,
        *,
        environment: dict[str, Any],
        entropy_state: dict[str, Any],
        active_desires: list[dict[str, Any]],
        proactive_items: list[Any],
        recent_turns: list[Any],
        recent_memory_events: list[Any],
        action_digest: dict[str, Any],
        initiative_metrics: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    def self_action_snapshot(self, runtime: Any, snapshot_func: Any) -> dict[str, Any]:
        ...

    def private_ecosystem_snapshot(self, runtime: Any, snapshot_func: Any) -> dict[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class DesktopSurfaceSnapshotStateBackendReadiness:
    service_id: str
    mode: str
    ready: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


class InProcessDesktopSurfaceSnapshotStateBackend:
    mode = DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_MODE

    def root(self, runtime: Any) -> Path:
        return runtime.xinyu_dir

    async def prepare_self_choice(self, runtime: Any) -> None:
        await runtime._ensure_self_choice_ready()
        await runtime.self_choice_store.apply_time_decay()

    async def self_choice_private(self, runtime: Any) -> dict[str, Any]:
        return await runtime.self_choice_store.snapshot_private()

    async def self_choice_public(self, runtime: Any) -> dict[str, Any]:
        return await runtime.self_choice_store.snapshot_public()

    async def event_state(self, runtime: Any) -> dict[str, Any]:
        return await runtime._desktop_event_state()

    async def active_desires(
        self,
        runtime: Any,
        *,
        environment: dict[str, Any],
        entropy_state: Any,
        proactive_items: list[Any],
        recent_turns: list[Any],
        recent_memory_events: list[Any],
        self_choice_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return await runtime._desktop_active_desires(
            environment=environment,
            entropy_state=entropy_state,
            proactive_items=proactive_items,
            recent_turns=recent_turns,
            recent_memory_events=recent_memory_events,
            self_choice_state=self_choice_state,
        )

    def health_snapshot(self, runtime: Any) -> dict[str, Any]:
        return runtime.health_snapshot()

    def services(self, runtime: Any) -> list[dict[str, Any]]:
        return runtime._desktop_services()

    def xinyu_state(
        self,
        runtime: Any,
        *,
        environment: dict[str, Any],
        entropy_state: dict[str, Any],
        active_desires: list[dict[str, Any]],
        proactive_items: list[Any],
        recent_turns: list[Any],
        recent_memory_events: list[Any],
        action_digest: dict[str, Any],
        initiative_metrics: dict[str, Any],
    ) -> dict[str, Any]:
        return runtime._desktop_xinyu_state(
            environment=environment,
            entropy_state=entropy_state,
            active_desires=active_desires,
            proactive_items=proactive_items,
            recent_turns=recent_turns,
            recent_memory_events=recent_memory_events,
            action_digest=action_digest,
            initiative_metrics=initiative_metrics,
        )

    def self_action_snapshot(self, runtime: Any, snapshot_func: Any) -> dict[str, Any]:
        return snapshot_func(self.root(runtime))

    def private_ecosystem_snapshot(self, runtime: Any, snapshot_func: Any) -> dict[str, Any]:
        return snapshot_func(self.root(runtime))


DEFAULT_DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND = InProcessDesktopSurfaceSnapshotStateBackend()


def desktop_surface_snapshot_state_backend_for_runtime(
    runtime: Any,
    *,
    explicit_backend: DesktopSurfaceSnapshotStateBackend | None = None,
) -> DesktopSurfaceSnapshotStateBackend:
    if explicit_backend is not None:
        return explicit_backend
    runtime_backend = getattr(runtime, DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_RUNTIME_ATTR, None)
    if runtime_backend is not None:
        return runtime_backend
    return DEFAULT_DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND


def desktop_surface_snapshot_state_backend_readiness(
    runtime: Any,
    *,
    explicit_backend: DesktopSurfaceSnapshotStateBackend | None = None,
) -> DesktopSurfaceSnapshotStateBackendReadiness:
    backend = desktop_surface_snapshot_state_backend_for_runtime(runtime, explicit_backend=explicit_backend)
    return DesktopSurfaceSnapshotStateBackendReadiness(
        service_id="desktop_surface",
        mode=getattr(backend, "mode", type(backend).__name__),
        ready=True,
        state_owner=DESKTOP_SURFACE_STATE_OWNER,
        fallback_adapter=DESKTOP_SURFACE_FALLBACK_ADAPTER,
        rollback=DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_ROLLBACK,
        notes=(
            "snapshot_state_backend_contract_ready",
            "snapshot_context_and_assembly_use_backend_methods",
            "default_backend_uses_current_in_process_runtime_facades",
            f"surface_rollback={DESKTOP_SURFACE_ROLLBACK}",
        ),
    )
