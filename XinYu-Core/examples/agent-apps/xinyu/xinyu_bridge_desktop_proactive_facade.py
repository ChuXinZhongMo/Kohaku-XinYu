from __future__ import annotations

from typing import Any, Callable, Mapping

from xinyu_bridge_desktop_proactive_deps_support import DesktopProactiveDeps
from xinyu_bridge_desktop_proactive_facade_ack import build_desktop_proactive_ack_facade
from xinyu_bridge_desktop_proactive_facade_delivery import build_desktop_proactive_delivery_facade
from xinyu_bridge_desktop_proactive_facade_inbox import build_desktop_proactive_inbox_facade


DepsProvider = Callable[[], DesktopProactiveDeps]
FacadeProvider = Callable[[], Mapping[str, Any]]


def bind_desktop_proactive_facade(
    *,
    deps_provider: DepsProvider,
    facade_provider: FacadeProvider,
    module_name: str,
) -> dict[str, Callable[..., Any]]:
    facade: dict[str, Callable[..., Any]] = {}
    facade.update(
        build_desktop_proactive_inbox_facade(
            deps_provider=deps_provider,
            facade_provider=facade_provider,
        )
    )
    facade.update(build_desktop_proactive_delivery_facade(deps_provider))
    facade.update(
        build_desktop_proactive_ack_facade(
            deps_provider=deps_provider,
            facade_provider=facade_provider,
        )
    )
    for name, func in facade.items():
        func.__module__ = module_name
        func.__qualname__ = name
    return facade
