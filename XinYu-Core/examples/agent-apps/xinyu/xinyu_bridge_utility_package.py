from __future__ import annotations

from typing import Any

from xinyu_bridge_external_action_route_backend import maybe_execute_external_action_backend
from xinyu_bridge_utility_common import ensure_open
from xinyu_bridge_utility_common import payload_or_empty


async def package_install(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    deps: Any,
) -> dict[str, Any]:
    ensure_open(runtime, deps)
    payload = payload_or_empty(payload, deps)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/package/install",
        http_method="POST",
        runtime_method="package_install",
    )
    if backend_response is not None:
        return backend_response
    async with runtime._global_turn_lock:
        return await deps.to_thread(deps.install_python_packages, runtime.xinyu_dir, payload)
