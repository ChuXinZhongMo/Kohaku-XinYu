from __future__ import annotations

from typing import Any

from xinyu_bridge_health_diagnostics_service import HealthDiagnosticsService


async def probe(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    bridge_version: str,
    deps: Any,
) -> dict[str, Any]:
    return await HealthDiagnosticsService.probe(runtime, payload, bridge_version=bridge_version, deps=deps)


async def runtime_probe(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    deps: Any,
) -> dict[str, Any]:
    return await HealthDiagnosticsService.runtime_probe(runtime, payload, deps=deps)
