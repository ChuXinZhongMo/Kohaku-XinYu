"""Service-level implementations for private ecosystem bridge routes."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Container
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_private_ecosystem_payload import _browser_action_kind, _browser_approved, _tick_trigger
from xinyu_bridge_private_ecosystem_response import (
    private_browser_snapshot_response,
    private_ecosystem_grant_response,
    private_ecosystem_pause_response,
    private_ecosystem_snapshot_response,
    private_ecosystem_tick_disabled_response,
    private_ecosystem_tick_note,
    private_ecosystem_tick_response,
)


@dataclass(frozen=True)
class PrivateEcosystemRouteDeps:
    root: Callable[[Any], Path]
    to_thread: Callable[..., Awaitable[Any]]
    as_bool: Callable[..., bool]
    load_grants: Callable[..., dict[str, Any]]
    save_grants_patch: Callable[..., dict[str, Any]]
    build_private_ecosystem_snapshot: Callable[..., dict[str, Any]]
    build_browser_snapshot: Callable[..., dict[str, Any]]
    run_private_ecosystem_tick: Callable[..., dict[str, Any]]
    sanitize_grant_patch: Callable[[dict[str, Any]], tuple[dict[str, Any], list[str]]]
    browser_action_args: Callable[[dict[str, Any]], dict[str, Any]]
    browser_action_via_plugin: Callable[..., dict[str, Any]]
    browser_action_response: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
    allowed_browser_actions: Container[str]


def _private_ecosystem_enabled(grants: dict[str, Any], *, deps: PrivateEcosystemRouteDeps) -> bool:
    ecosystem_value = grants.get("private_ecosystem")
    ecosystem = ecosystem_value if isinstance(ecosystem_value, dict) else {}
    return deps.as_bool(ecosystem.get("enabled"), default=False)


def append_private_ecosystem_note_impl(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    deps: PrivateEcosystemRouteDeps,
) -> None:
    try:
        root = deps.root(runtime)
        grants = deps.load_grants(root)
        if not _private_ecosystem_enabled(grants, deps=deps):
            notes.append("private_ecosystem:disabled")
            return
        result = deps.run_private_ecosystem_tick(
            root,
            checked_at=checked_at,
            trigger="autonomous_maintenance",
            allow_send=True,
        )
        notes.append(private_ecosystem_tick_note(result))
    except Exception as exc:
        notes.append(f"private_ecosystem_error:{type(exc).__name__}")
        runtime._trace_autonomous(f"private_ecosystem_error={exc!r}")


async def private_ecosystem_snapshot_route(
    root: Path,
    *,
    deps: PrivateEcosystemRouteDeps,
) -> dict[str, Any]:
    snapshot = await deps.to_thread(deps.build_private_ecosystem_snapshot, root)
    return private_ecosystem_snapshot_response(snapshot)


async def private_ecosystem_pause_route(
    root: Path,
    *,
    paused: bool,
    deps: PrivateEcosystemRouteDeps,
) -> dict[str, Any]:
    merged = await deps.to_thread(
        deps.save_grants_patch,
        root,
        {"owner_private_autonomous_share": {"paused": paused}},
    )
    snapshot = await deps.to_thread(deps.build_private_ecosystem_snapshot, root)
    return private_ecosystem_pause_response(merged, snapshot, paused=paused)


async def private_ecosystem_grant_route(
    root: Path,
    *,
    patch_in: dict[str, Any],
    deps: PrivateEcosystemRouteDeps,
) -> dict[str, Any]:
    patch, rejected = deps.sanitize_grant_patch(patch_in)
    if not patch:
        raise BridgeRequestError(
            HTTPStatus.BAD_REQUEST,
            f"no applicable grant fields; rejected={','.join(rejected) or 'none'}",
        )
    merged = await deps.to_thread(deps.save_grants_patch, root, patch)
    snapshot = await deps.to_thread(deps.build_private_ecosystem_snapshot, root)
    return private_ecosystem_grant_response(patch=patch, rejected=rejected, merged=merged, snapshot=snapshot)


async def private_ecosystem_tick_route(
    root: Path,
    payload: dict[str, Any],
    *,
    deps: PrivateEcosystemRouteDeps,
) -> dict[str, Any]:
    grants = await deps.to_thread(deps.load_grants, root)
    if not _private_ecosystem_enabled(grants, deps=deps):
        snapshot = await deps.to_thread(deps.build_private_ecosystem_snapshot, root)
        return private_ecosystem_tick_disabled_response(snapshot)
    result = await deps.to_thread(
        deps.run_private_ecosystem_tick,
        root,
        trigger=_tick_trigger(payload),
        allow_send=True,
    )
    snapshot = await deps.to_thread(deps.build_private_ecosystem_snapshot, root)
    return private_ecosystem_tick_response(result, snapshot)


async def private_browser_snapshot_route(
    root: Path,
    *,
    deps: PrivateEcosystemRouteDeps,
) -> dict[str, Any]:
    snapshot = await deps.to_thread(deps.build_browser_snapshot, root)
    return private_browser_snapshot_response(snapshot)


async def private_browser_action_route(
    root: Path,
    payload: dict[str, Any],
    *,
    deps: PrivateEcosystemRouteDeps,
) -> dict[str, Any]:
    action_kind = _browser_action_kind(payload, deps.allowed_browser_actions)
    outcome = await deps.to_thread(
        deps.browser_action_via_plugin,
        root,
        action_kind=action_kind,
        args=deps.browser_action_args(payload),
        approved=_browser_approved(payload),
    )
    snapshot = await deps.to_thread(deps.build_browser_snapshot, root)
    return deps.browser_action_response(outcome, snapshot)
