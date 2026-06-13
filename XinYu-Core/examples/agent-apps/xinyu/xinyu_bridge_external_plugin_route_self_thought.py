from __future__ import annotations

from typing import Any

from xinyu_bridge_external_plugin_self_thought import (
    SelfThoughtExternalPluginDeps,
    maybe_run_self_thought_external_plugin_impl,
)


def maybe_run_self_thought_external_plugin_route(
    runtime: Any,
    *,
    thought: dict[str, Any],
    checked_at: str,
    deps: SelfThoughtExternalPluginDeps,
) -> list[str]:
    return maybe_run_self_thought_external_plugin_impl(
        runtime,
        thought=thought,
        checked_at=checked_at,
        deps=deps,
    )


__all__ = ["maybe_run_self_thought_external_plugin_route"]
