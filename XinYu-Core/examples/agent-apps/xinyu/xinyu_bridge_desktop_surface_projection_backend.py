from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_SURFACE_FALLBACK_ADAPTER,
    DESKTOP_SURFACE_ROLLBACK,
    DESKTOP_SURFACE_STATE_OWNER,
)


DESKTOP_SURFACE_PROJECTION_BACKEND_RUNTIME_ATTR = "_desktop_surface_projection_backend"
DESKTOP_SURFACE_PROJECTION_BACKEND_MODE = "desktop_surface_projection_backend_in_process"
DESKTOP_SURFACE_PROJECTION_BACKEND_ROLLBACK = "remove_runtime_projection_backend_attr_to_use_current_facades"


@dataclass(frozen=True, slots=True)
class DesktopSurfaceProjectionSnapshot:
    proactive_items: list[Any]
    proactive_history: list[Any]
    recent_turns: list[Any]
    recent_memory_events: list[Any]


class DesktopSurfaceProjectionBackend(Protocol):
    mode: str

    async def collect(self, runtime: Any, payload: dict[str, Any]) -> DesktopSurfaceProjectionSnapshot:
        ...


@dataclass(frozen=True, slots=True)
class DesktopSurfaceProjectionBackendReadiness:
    service_id: str
    mode: str
    ready: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


class InProcessDesktopSurfaceProjectionBackend:
    mode = DESKTOP_SURFACE_PROJECTION_BACKEND_MODE

    async def collect(self, runtime: Any, payload: dict[str, Any]) -> DesktopSurfaceProjectionSnapshot:
        proactive_inbox = await runtime.desktop_proactive_inbox(payload)
        return DesktopSurfaceProjectionSnapshot(
            proactive_items=list(proactive_inbox.get("items", [])),
            proactive_history=list(proactive_inbox.get("history", [])),
            recent_turns=list((await runtime.desktop_chat_recent(payload)).get("items", [])),
            recent_memory_events=list((await runtime.desktop_memory_recent(payload)).get("items", [])),
        )


DEFAULT_DESKTOP_SURFACE_PROJECTION_BACKEND = InProcessDesktopSurfaceProjectionBackend()


def desktop_surface_projection_backend_for_runtime(
    runtime: Any,
    *,
    explicit_backend: DesktopSurfaceProjectionBackend | None = None,
) -> DesktopSurfaceProjectionBackend:
    if explicit_backend is not None:
        return explicit_backend
    runtime_backend = getattr(runtime, DESKTOP_SURFACE_PROJECTION_BACKEND_RUNTIME_ATTR, None)
    if runtime_backend is not None:
        return runtime_backend
    return DEFAULT_DESKTOP_SURFACE_PROJECTION_BACKEND


async def collect_desktop_surface_projection(
    runtime: Any,
    payload: dict[str, Any],
    *,
    explicit_backend: DesktopSurfaceProjectionBackend | None = None,
) -> DesktopSurfaceProjectionSnapshot:
    backend = desktop_surface_projection_backend_for_runtime(runtime, explicit_backend=explicit_backend)
    return await backend.collect(runtime, payload)


def desktop_surface_projection_backend_readiness(
    runtime: Any,
    *,
    explicit_backend: DesktopSurfaceProjectionBackend | None = None,
) -> DesktopSurfaceProjectionBackendReadiness:
    backend = desktop_surface_projection_backend_for_runtime(runtime, explicit_backend=explicit_backend)
    return DesktopSurfaceProjectionBackendReadiness(
        service_id="desktop_surface",
        mode=getattr(backend, "mode", type(backend).__name__),
        ready=True,
        state_owner=DESKTOP_SURFACE_STATE_OWNER,
        fallback_adapter=DESKTOP_SURFACE_FALLBACK_ADAPTER,
        rollback=DESKTOP_SURFACE_PROJECTION_BACKEND_ROLLBACK,
        notes=(
            "projection_backend_contract_ready",
            "default_backend_uses_current_in_process_facades",
            "snapshot_context_can_use_runtime_backend_attr",
            f"surface_rollback={DESKTOP_SURFACE_ROLLBACK}",
        ),
    )
