"""Payload and owner gate helpers for private isolated-desktop routes."""
from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import safe_str as _safe_str

_READ_ONLY_OBSERVE_ACTIONS = frozenset({"screenshot", "status", "live_view", "list_windows", "observe_text"})


def _root(runtime: Any) -> Path:
    return Path(runtime.xinyu_dir)


def _require_owner_private(runtime: Any, payload: dict[str, Any]) -> None:
    matcher = getattr(runtime, "_owner_private_payload_matches", None)
    if callable(matcher) and not matcher(payload):
        raise BridgeRequestError(HTTPStatus.FORBIDDEN, "owner_private_context_required")


def _require_private_desktop_enabled(root: Path) -> None:
    from xinyu_private_ecosystem_grants import desktop_grant, load_grants

    grant = desktop_grant(load_grants(root))
    if not _as_bool(grant.get("enabled"), default=False):
        raise BridgeRequestError(HTTPStatus.FORBIDDEN, "private_desktop_grant_disabled")


def _ensure_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return dict(payload or {})


def _observe_action(payload: dict[str, Any]) -> str:
    action = _safe_str(payload.get("action") or payload.get("actionKind") or "screenshot").strip() or "screenshot"
    if action not in _READ_ONLY_OBSERVE_ACTIONS:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "private_desktop_observe_read_only_only")
    return action
