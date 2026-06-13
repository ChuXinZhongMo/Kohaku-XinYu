from __future__ import annotations

from collections.abc import Container
from typing import Any

from xinyu_bridge_values import as_int, safe_str


GRANT_PATCH_SECTIONS = {
    "owner_private_autonomous_share",
    "private_browser",
    "computer_control",
    "private_ecosystem",
    "private_desktop",
}


def sanitize_grant_patch(
    patch_in: dict[str, Any],
    *,
    rollout_states: Container[str],
) -> tuple[dict[str, Any], list[str]]:
    """Clamp and whitelist owner-private grant edits."""
    clean: dict[str, Any] = {}
    rejected: list[str] = []

    share = patch_in.get("owner_private_autonomous_share")
    if isinstance(share, dict):
        out: dict[str, Any] = {}
        for key, value in share.items():
            if key in {"enabled", "paused", "quiet_hours_override"}:
                out[key] = bool(value)
            elif key == "daily_limit":
                out[key] = max(0, min(8, as_int(value, 8)))
            elif key == "cooldown_minutes":
                out[key] = max(30, as_int(value, 30))
            elif key == "max_message_chars":
                out[key] = max(1, min(800, as_int(value, 800)))
            elif key == "quiet_hours":
                text = safe_str(value).strip()
                if text:
                    out[key] = text
                else:
                    rejected.append("owner_private_autonomous_share.quiet_hours")
            else:
                rejected.append(f"owner_private_autonomous_share.{key}")
        if out:
            clean["owner_private_autonomous_share"] = out

    browser = patch_in.get("private_browser")
    if isinstance(browser, dict):
        out: dict[str, Any] = {}
        for key, value in browser.items():
            if key in {"enabled", "read_only"}:
                out[key] = bool(value)
            elif key == "allowed_urls":
                if isinstance(value, list):
                    out[key] = [safe_str(url).strip() for url in value if safe_str(url).strip()]
                else:
                    rejected.append("private_browser.allowed_urls")
            elif key == "single_step_actions":
                rejected.append("private_browser.single_step_actions")
            else:
                rejected.append(f"private_browser.{key}")
        if out:
            clean["private_browser"] = out

    computer = patch_in.get("computer_control")
    if isinstance(computer, dict):
        for key in computer:
            rejected.append(f"computer_control.{key}")

    desktop = patch_in.get("private_desktop")
    if isinstance(desktop, dict):
        out: dict[str, Any] = {}
        for key, value in desktop.items():
            if key in {"enabled", "observe_only"}:
                out[key] = bool(value)
            elif key == "max_frame_rate":
                out[key] = max(1, min(30, as_int(value, 10)))
            elif key == "idle_shutdown_minutes":
                out[key] = max(1, min(240, as_int(value, 30)))
            elif key in {"single_step_actions", "shell_enabled", "network_enabled"}:
                rejected.append(f"private_desktop.{key}")
            else:
                rejected.append(f"private_desktop.{key}")
        if out:
            clean["private_desktop"] = out

    ecosystem = patch_in.get("private_ecosystem")
    if isinstance(ecosystem, dict):
        out: dict[str, Any] = {}
        for key, value in ecosystem.items():
            if key == "enabled":
                out[key] = bool(value)
            elif key == "rollout_state":
                rollout_state = safe_str(value).strip() or "disabled"
                if rollout_state in rollout_states:
                    out[key] = rollout_state
                else:
                    rejected.append("private_ecosystem.rollout_state")
            else:
                rejected.append(f"private_ecosystem.{key}")
        if out.get("enabled") is False:
            out["rollout_state"] = "disabled"
        elif out.get("enabled") is True and out.get("rollout_state", "disabled") == "disabled":
            out["rollout_state"] = "observe_only"
        if out:
            clean["private_ecosystem"] = out

    for key in patch_in:
        if key not in GRANT_PATCH_SECTIONS:
            rejected.append(key)

    return clean, rejected
