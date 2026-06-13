"""Owner-approved grants and rollout flags for the XinYu Private Ecosystem.

Single source of truth for "what is XinYu allowed to do inside her own space".
Grants live in ``memory/context/private_ecosystem_grants.json`` (owner-owned,
durable). Environment variables may *enable code paths* but never *grant
permission*: actual action permission is decided by grants + runtime state, per
dossier section 15.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from stores.state_service import atomic_write_json, read_json

GRANTS_REL = Path("memory/context/private_ecosystem_grants.json")

ROLLOUT_STATES = (
    "disabled",
    "dry_run",
    "observe_only",
    "owner_private_share_enabled",
    "browser_read_only",
    "single_step_approved_actions",
)


def _env(env: Mapping[str, str] | None, name: str, default: str = "") -> str:
    source = env if env is not None else os.environ
    value = source.get(name)
    return str(value).strip() if value is not None else default


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "enabled", "approved"}:
        return True
    if text in {"0", "false", "no", "off", "disabled", "blocked", ""}:
        return False
    return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def default_grants(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Safe/off defaults. Mirrors the rollout flags in dossier section 15."""
    return {
        "version": 1,
        "private_ecosystem": {
            "enabled": _as_bool(_env(env, "XINYU_PRIVATE_ECOSYSTEM"), default=False),
            "rollout_state": _env(env, "XINYU_PRIVATE_ECOSYSTEM", "disabled") or "disabled",
        },
        "owner_private_autonomous_share": {
            "enabled": _as_bool(_env(env, "XINYU_OWNER_PRIVATE_AUTONOMOUS_SHARE"), default=False),
            "paused": True,
            "daily_limit": _as_int(_env(env, "XINYU_OWNER_PRIVATE_SHARE_DAILY_LIMIT"), 8),
            "cooldown_minutes": _as_int(_env(env, "XINYU_OWNER_PRIVATE_SHARE_COOLDOWN_MINUTES"), 30),
            "max_message_chars": _as_int(_env(env, "XINYU_OWNER_PRIVATE_SHARE_MAX_CHARS"), 800),
            "quiet_hours": _env(env, "XINYU_OWNER_PRIVATE_SHARE_QUIET_HOURS", "00:00-06:00")
            or "00:00-06:00",
        },
        "private_browser": {
            "enabled": _as_bool(_env(env, "XINYU_PRIVATE_BROWSER"), default=False),
            "read_only": True,
            "single_step_actions": False,
            "max_tabs": _as_int(_env(env, "XINYU_PRIVATE_BROWSER_MAX_TABS"), 4),
            "screenshot_ttl_hours": _as_int(_env(env, "XINYU_PRIVATE_BROWSER_SCREENSHOT_TTL_HOURS"), 24),
        },
        "computer_control": {
            "enabled": _as_bool(_env(env, "XINYU_COMPUTER_CONTROL"), default=False),
            "observe_only": True,
            "single_step_actions": False,
        },
        "private_desktop": {
            # XinYu's own ISOLATED desktop (container/VM), never the owner's host
            # Windows desktop. Env may enable the code path but never escalate
            # high-risk fields (single-step / shell / network).
            "enabled": _as_bool(_env(env, "XINYU_PRIVATE_DESKTOP"), default=False),
            "observe_only": True,
            "single_step_actions": False,
            "shell_enabled": False,
            "network_enabled": False,
            "max_frame_rate": _as_int(_env(env, "XINYU_PRIVATE_DESKTOP_MAX_FRAME_RATE"), 10),
            "idle_shutdown_minutes": _as_int(_env(env, "XINYU_PRIVATE_DESKTOP_IDLE_SHUTDOWN_MINUTES"), 30),
            "workspace": "isolated_desktop",
        },
    }


def _deep_merge(base: dict[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def grants_path(root: Path) -> Path:
    return Path(root) / GRANTS_REL


def load_grants(root: Path, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Load owner grants overlaid on safe defaults.

    The on-disk file is authoritative where present; missing sections fall back
    to env-derived safe defaults. Env never *raises* a stored grant above what
    the owner wrote — disk values win on conflict.
    """
    defaults = default_grants(env)
    stored = read_json(grants_path(root), default=None)
    if not isinstance(stored, dict):
        return defaults
    return _deep_merge(defaults, stored)


def save_grants_patch(root: Path, patch: Mapping[str, Any], env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Owner-side write. Persists a merged grants file and returns it."""
    current = load_grants(root, env)
    merged = _deep_merge(current, patch)
    atomic_write_json(grants_path(root), merged)
    return merged


def share_grant(grants: Mapping[str, Any]) -> dict[str, Any]:
    section = grants.get("owner_private_autonomous_share")
    return dict(section) if isinstance(section, dict) else {}


def share_block_reasons(grants: Mapping[str, Any]) -> list[str]:
    section = share_grant(grants)
    blocks: list[str] = []
    if not _as_bool(section.get("enabled")):
        blocks.append("owner_private_autonomous_share_disabled")
    if _as_bool(section.get("paused"), default=True):
        blocks.append("owner_private_autonomous_share_paused")
    return blocks


def load_share_block_reasons(root: Path, env: Mapping[str, str] | None = None) -> list[str]:
    return share_block_reasons(load_grants(root, env))


def browser_grant(grants: Mapping[str, Any]) -> dict[str, Any]:
    section = grants.get("private_browser")
    return dict(section) if isinstance(section, dict) else {}


def computer_grant(grants: Mapping[str, Any]) -> dict[str, Any]:
    section = grants.get("computer_control")
    return dict(section) if isinstance(section, dict) else {}


def desktop_grant(grants: Mapping[str, Any]) -> dict[str, Any]:
    section = grants.get("private_desktop")
    return dict(section) if isinstance(section, dict) else {}


def share_active(grants: Mapping[str, Any]) -> bool:
    return not share_block_reasons(grants)
