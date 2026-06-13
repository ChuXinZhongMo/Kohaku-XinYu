"""Payload and owner-gate helpers for private ecosystem bridge routes."""
from __future__ import annotations

from collections.abc import Container
from http import HTTPStatus
from pathlib import Path
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import safe_str as _safe_str


def _root(runtime: Any) -> Path:
    return Path(runtime.xinyu_dir)


def _require_owner_private(runtime: Any, payload: dict[str, Any]) -> None:
    matcher = getattr(runtime, "_owner_private_payload_matches", None)
    if callable(matcher) and not matcher(payload):
        raise BridgeRequestError(HTTPStatus.FORBIDDEN, "owner_private_context_required")


def _ensure_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return dict(payload or {})


def _pause_state(payload: dict[str, Any]) -> bool:
    action = _safe_str(payload.get("action") or payload.get("state")).lower()
    if action in {"pause", "paused", "stop", "off"}:
        return True
    if action in {"resume", "unpause", "start", "on"}:
        return False
    return _as_bool(payload.get("paused"), default=True)


def _grant_patch_input(payload: dict[str, Any]) -> dict[str, Any]:
    patch_in = payload.get("grant") if isinstance(payload.get("grant"), dict) else payload.get("patch")
    if not isinstance(patch_in, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "grant patch object required")
    return patch_in


def _tick_trigger(payload: dict[str, Any]) -> str:
    return _safe_str(payload.get("trigger")).strip() or "owner_desktop"


def _browser_action_kind(payload: dict[str, Any], allowed_actions: Container[str]) -> str:
    action_kind = _safe_str(payload.get("action") or payload.get("action_kind")).strip()
    if action_kind not in allowed_actions:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, f"unsupported browser action: {action_kind}")
    return action_kind


def _browser_approved(payload: dict[str, Any]) -> bool:
    return _as_bool(payload.get("approved"), default=False)
