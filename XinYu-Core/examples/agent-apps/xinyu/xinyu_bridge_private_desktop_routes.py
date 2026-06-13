"""Bridge routes for XinYu's private ISOLATED desktop cockpit.

Owner control plane for XinYu's own isolated Linux desktop (container), NOT the
owner's host Windows desktop. Read-only snapshot/live-state/frame plus tightly
gated owner-only start/stop. Every GET requires the bridge token; every mutating
route additionally requires the owner-private context. Frame serving is limited
to the workspace and cannot path-traverse. No raw host paths, VNC password,
Docker secret, or host-desktop capture is ever returned.
"""
from __future__ import annotations

import asyncio
from typing import Any

from xinyu_bridge_external_action_route_backend import maybe_execute_external_action_backend
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_bridge_private_desktop_backend import _backend_status, _live_backend, _start_backend, _stop_backend
from xinyu_bridge_private_desktop_frame import _FRAME_ID_RE, _frame_ref, _read_frame_data_url, _resolve_frame
from xinyu_bridge_private_desktop_payload import (
    _ensure_payload,
    _observe_action,
    _require_owner_private,
    _require_private_desktop_enabled,
    _root,
)
from xinyu_bridge_private_desktop_status import _lifecycle_payload, _live_state_payload, _observe_payload
from xinyu_private_desktop_control import (
    FRAMES_REL,
    LATEST_FRAME_REL,
    build_desktop_snapshot,
    boundaries_dict,
    run_desktop_action,
)


async def desktop_private_desktop_snapshot(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _ensure_payload(payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-desktop/snapshot",
        http_method="GET",
        runtime_method="desktop_private_desktop_snapshot",
    )
    if backend_response is not None:
        return backend_response
    root = _root(runtime)
    status = await asyncio.to_thread(_backend_status, root)
    snapshot = await asyncio.to_thread(build_desktop_snapshot, root, backend_status=status)
    return {"ok": True, "accepted": True, "privateDesktop": snapshot, "notes": ["private_desktop_snapshot"]}


async def desktop_private_desktop_live_state(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _ensure_payload(payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-desktop/live-state",
        http_method="GET",
        runtime_method="desktop_private_desktop_live_state",
    )
    if backend_response is not None:
        return backend_response
    root = _root(runtime)
    status = await asyncio.to_thread(_backend_status, root)
    return _live_state_payload(root, status, boundaries_func=boundaries_dict)


async def desktop_private_desktop_frame(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _ensure_payload(payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-desktop/frame",
        http_method="GET",
        runtime_method="desktop_private_desktop_frame",
    )
    if backend_response is not None:
        return backend_response
    root = _root(runtime)
    frame_id = _safe_str(payload.get("frame_id") or payload.get("frameId")).strip()
    path = _resolve_frame(root, frame_id)
    data_url = await asyncio.to_thread(_read_frame_data_url, path)
    return {
        "ok": bool(data_url),
        "accepted": True,
        "frame_ref": _frame_ref(frame_id),
        "frame_data_url": data_url,
        "has_frame": bool(data_url),
        "notes": ["private_desktop_frame"] if data_url else ["private_desktop_frame_missing"],
    }


async def desktop_private_desktop_observe(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _ensure_payload(payload)
    _require_owner_private(runtime, payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-desktop/observe",
        http_method="POST",
        runtime_method="desktop_private_desktop_observe",
        owner_private_context=True,
    )
    if backend_response is not None:
        return backend_response
    root = _root(runtime)
    action = _observe_action(payload)
    backend = await asyncio.to_thread(_live_backend, root)
    outcome = await asyncio.to_thread(
        run_desktop_action,
        root,
        action_kind=action,
        execute=True,
        backend=backend,
    )
    status = await asyncio.to_thread(_backend_status, root)
    snapshot = await asyncio.to_thread(build_desktop_snapshot, root, backend_status=status)
    return _observe_payload(action, outcome, snapshot)


async def desktop_private_desktop_start(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _ensure_payload(payload)
    _require_owner_private(runtime, payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-desktop/start",
        http_method="POST",
        runtime_method="desktop_private_desktop_start",
        owner_private_context=True,
    )
    if backend_response is not None:
        return backend_response
    root = _root(runtime)
    _require_private_desktop_enabled(root)
    outcome = await asyncio.to_thread(_start_backend, root)
    status = await asyncio.to_thread(_backend_status, root)
    snapshot = await asyncio.to_thread(build_desktop_snapshot, root, backend_status=status)
    return _lifecycle_payload(outcome, snapshot, note="private_desktop_start", include_error_code=True)


async def desktop_private_desktop_stop(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _ensure_payload(payload)
    _require_owner_private(runtime, payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-desktop/stop",
        http_method="POST",
        runtime_method="desktop_private_desktop_stop",
        owner_private_context=True,
    )
    if backend_response is not None:
        return backend_response
    root = _root(runtime)
    outcome = await asyncio.to_thread(_stop_backend, root)
    status = await asyncio.to_thread(_backend_status, root)
    snapshot = await asyncio.to_thread(build_desktop_snapshot, root, backend_status=status)
    return _lifecycle_payload(outcome, snapshot, note="private_desktop_stop")
