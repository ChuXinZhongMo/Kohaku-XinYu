"""Compatibility re-export for desktop surface state store.

Implementation lives in ``stores.desktop_surface_state``; this module keeps the
legacy import path used by bridge routes, runtime wiring, and service contracts.
"""

from __future__ import annotations

from stores.desktop_surface_state import (
    DESKTOP_SURFACE_STATE_STORE_LEGACY_MODE,
    DESKTOP_SURFACE_STATE_STORE_LOCAL_MODE,
    DESKTOP_SURFACE_STATE_STORE_ROLLBACK,
    DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR,
    DesktopSurfaceStateStore,
    DesktopSurfaceStateStoreReadiness,
    LegacyRuntimeDesktopSurfaceStateStore,
    LocalDesktopSurfaceStateStore,
    desktop_surface_state_store_for_runtime,
    desktop_surface_state_store_readiness,
)

__all__ = [
    "DESKTOP_SURFACE_STATE_STORE_LEGACY_MODE",
    "DESKTOP_SURFACE_STATE_STORE_LOCAL_MODE",
    "DESKTOP_SURFACE_STATE_STORE_ROLLBACK",
    "DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR",
    "DesktopSurfaceStateStore",
    "DesktopSurfaceStateStoreReadiness",
    "LegacyRuntimeDesktopSurfaceStateStore",
    "LocalDesktopSurfaceStateStore",
    "desktop_surface_state_store_for_runtime",
    "desktop_surface_state_store_readiness",
]
