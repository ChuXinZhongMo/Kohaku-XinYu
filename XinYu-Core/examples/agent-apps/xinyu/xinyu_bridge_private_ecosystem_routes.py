"""Bridge routes for the XinYu Private Ecosystem cockpit.

Owner control plane: sanitized snapshot, kill switch (pause/resume share),
owner grant edits, and policy-gated private-browser actions. Every mutating or
acting route requires the owner-private context (and the HTTP layer requires the
bridge token). Browser execution runs the sync Playwright engine off the event
loop via asyncio.to_thread, exactly as other sync bridge work is offloaded.
"""
from __future__ import annotations

import asyncio
from http import HTTPStatus
from pathlib import Path
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_external_action_route_backend import maybe_execute_external_action_backend
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import as_int as _as_int
from xinyu_bridge_values import safe_str as _safe_str

import xinyu_private_ecosystem_grants as grants_mod
from xinyu_bridge_private_ecosystem_browser import (
    ALLOWED_BROWSER_ACTIONS as _ALLOWED_BROWSER_ACTIONS,
)
from xinyu_bridge_private_ecosystem_browser import browser_action_args as _browser_action_args
from xinyu_bridge_private_ecosystem_browser import browser_action_response as _browser_action_response
from xinyu_bridge_private_ecosystem_browser import run_browser_action_via_plugin as _browser_action_via_plugin
from xinyu_bridge_private_ecosystem_grant_sanitizer import sanitize_grant_patch
from xinyu_bridge_private_ecosystem_payload import (
    _ensure_payload,
    _grant_patch_input,
    _pause_state,
    _require_owner_private,
    _root,
)
from xinyu_bridge_private_ecosystem_service import (
    PrivateEcosystemRouteDeps,
    append_private_ecosystem_note_impl,
    private_browser_action_route,
    private_browser_snapshot_route,
    private_ecosystem_grant_route,
    private_ecosystem_pause_route,
    private_ecosystem_snapshot_route,
    private_ecosystem_tick_route,
)
from xinyu_bridge_desktop_snapshot import (
    desktop_private_ecosystem_snapshot as _build_pe_snapshot,
)
from xinyu_browser_control import build_browser_snapshot
from xinyu_private_ecosystem import run_private_ecosystem_tick


def _sanitize_grant_patch(patch_in: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Clamp and whitelist a grant patch so the cockpit cannot escalate beyond
    policy. Returns (clean_patch, rejected_keys). Privilege-escalating keys
    (browser single-step, computer enable/single-step) are NOT settable here;
    they require a dedicated owner-approved mode, not the normal grant route."""
    return sanitize_grant_patch(patch_in, rollout_states=grants_mod.ROLLOUT_STATES)


def _deps() -> PrivateEcosystemRouteDeps:
    return PrivateEcosystemRouteDeps(
        root=_root,
        to_thread=asyncio.to_thread,
        as_bool=_as_bool,
        load_grants=grants_mod.load_grants,
        save_grants_patch=grants_mod.save_grants_patch,
        build_private_ecosystem_snapshot=_build_pe_snapshot,
        build_browser_snapshot=build_browser_snapshot,
        run_private_ecosystem_tick=run_private_ecosystem_tick,
        sanitize_grant_patch=_sanitize_grant_patch,
        browser_action_args=_browser_action_args,
        browser_action_via_plugin=_browser_action_via_plugin,
        browser_action_response=_browser_action_response,
        allowed_browser_actions=_ALLOWED_BROWSER_ACTIONS,
    )


def append_private_ecosystem_note(runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_private_ecosystem_note_impl(runtime, notes, checked_at=checked_at, deps=_deps())


async def desktop_private_ecosystem_snapshot(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _ensure_payload(payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-ecosystem/snapshot",
        http_method="GET",
        runtime_method="desktop_private_ecosystem_snapshot",
    )
    if backend_response is not None:
        return backend_response
    return await private_ecosystem_snapshot_route(_root(runtime), deps=_deps())


async def desktop_private_ecosystem_pause(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Kill switch: pause or resume owner-private autonomous sharing."""
    payload = _ensure_payload(payload)
    _require_owner_private(runtime, payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-ecosystem/pause",
        http_method="POST",
        runtime_method="desktop_private_ecosystem_pause",
        owner_private_context=True,
    )
    if backend_response is not None:
        return backend_response
    return await private_ecosystem_pause_route(_root(runtime), paused=_pause_state(payload), deps=_deps())


async def desktop_private_ecosystem_grant(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Owner grant edit. Sections/keys are whitelisted and clamped; privilege
    escalation (browser single-step, computer control) is rejected here."""
    payload = _ensure_payload(payload)
    _require_owner_private(runtime, payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-ecosystem/grant",
        http_method="POST",
        runtime_method="desktop_private_ecosystem_grant",
        owner_private_context=True,
    )
    if backend_response is not None:
        return backend_response
    return await private_ecosystem_grant_route(_root(runtime), patch_in=_grant_patch_input(payload), deps=_deps())


async def desktop_private_ecosystem_tick(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run one owner-requested low-risk private ecosystem tick.

    This is not a high-risk desktop-control route. It advances the existing
    private ecosystem kernel: local probes auto-run, outward sharing remains
    gated by the owner-private share grant, and stable memory writes stay
    blocked by the kernel boundaries.
    """
    payload = _ensure_payload(payload)
    _require_owner_private(runtime, payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-ecosystem/tick",
        http_method="POST",
        runtime_method="desktop_private_ecosystem_tick",
        owner_private_context=True,
    )
    if backend_response is not None:
        return backend_response
    return await private_ecosystem_tick_route(_root(runtime), payload, deps=_deps())


async def desktop_private_browser_snapshot(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _ensure_payload(payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-browser/snapshot",
        http_method="GET",
        runtime_method="desktop_private_browser_snapshot",
    )
    if backend_response is not None:
        return backend_response
    return await private_browser_snapshot_route(_root(runtime), deps=_deps())


async def desktop_private_browser_action(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Owner cockpit browser action — token + owner-private gated, routed through
    the external_plugin_call gate chain (runtime_allowed -> evaluate_external_call
    -> native executor). Blocked with `plugin_disabled` when the
    xinyu_private_browser plugin is not enabled."""
    payload = _ensure_payload(payload)
    _require_owner_private(runtime, payload)
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/desktop/private-browser/action",
        http_method="POST",
        runtime_method="desktop_private_browser_action",
        owner_private_context=True,
    )
    if backend_response is not None:
        return backend_response
    return await private_browser_action_route(_root(runtime), payload, deps=_deps())
