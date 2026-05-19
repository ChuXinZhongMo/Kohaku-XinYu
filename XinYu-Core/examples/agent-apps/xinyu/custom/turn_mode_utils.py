"""Shared helpers for reading Xinyu runtime turn mode from disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

TURN_MODE_EXTERNAL_STATE_KEY = "xinyu:turn_mode:external_mode"


def _session_store_state(ctx: Any | None) -> dict[str, Any] | None:
    if ctx is None:
        return None
    try:
        store = ctx.session_store
    except Exception:
        return None
    state = getattr(store, "state", None)
    return state if isinstance(state, dict) else None


def _session_extra(ctx: Any | None) -> dict[str, Any] | None:
    if ctx is None:
        return None
    try:
        agent = ctx.host_agent
    except Exception:
        agent = getattr(ctx, "_host_agent", None)
    session = getattr(agent, "session", None)
    extra = getattr(session, "extra", None)
    return extra if isinstance(extra, dict) else None


def write_external_turn_mode(ctx: Any | None, mode: str) -> None:
    value = str(mode or "").strip()
    if not value:
        return
    state = _session_store_state(ctx)
    if state is not None:
        state[TURN_MODE_EXTERNAL_STATE_KEY] = value
    extra = _session_extra(ctx)
    if extra is not None:
        extra[TURN_MODE_EXTERNAL_STATE_KEY] = value


def read_external_turn_mode(ctx: Any | None, root: Path) -> str:
    state = _session_store_state(ctx)
    if state is not None:
        value = str(state.get(TURN_MODE_EXTERNAL_STATE_KEY) or "").strip()
        if value:
            return value
    extra = _session_extra(ctx)
    if extra is not None:
        value = str(extra.get(TURN_MODE_EXTERNAL_STATE_KEY) or "").strip()
        if value:
            return value
    return read_turn_mode(root)


def read_turn_mode(root: Path) -> str:
    path = root / "memory/context/turn_mode_state.md"
    if not path.exists():
        return ""
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if line.startswith("- mode:"):
            return line.split(":", 1)[1].strip()
    return ""
