from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_bridge_values import safe_str


ALLOWED_BROWSER_ACTIONS = {
    "list_tabs",
    "new_tab",
    "navigate_readonly",
    "snapshot_dom",
    "screenshot",
    "extract_text",
    "wait_for_text",
    "navigate",
    "click_element",
    "fill",
    "press",
    "scroll",
}


def browser_action_args(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": safe_str(payload.get("url")).strip(),
        "element_id": safe_str(payload.get("element_id") or payload.get("elementId")).strip(),
        "value": safe_str(payload.get("value")),
    }


def run_browser_action_via_plugin(
    root: Path,
    *,
    action_kind: str,
    args: dict[str, Any],
    approved: bool,
) -> dict[str, Any]:
    from xinyu_bridge_external_plugin_routes import run_private_ecosystem_native_call
    from xinyu_external_plugins import ExternalCallContext

    context = ExternalCallContext(
        source="cockpit_owner",
        owner_private=True,
        proactive=False,
        approved=approved,
        reason="owner cockpit browser action",
    )
    return run_private_ecosystem_native_call(root, "xinyu_private_browser", action_kind, args, context, execute=True)


def browser_action_response(outcome: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    execution = outcome.get("execution", {}) if isinstance(outcome.get("execution"), dict) else {}
    return {
        "ok": bool(outcome.get("ok")),
        "accepted": bool(outcome.get("ok")),
        "result": safe_str(outcome.get("result")),
        "reason": safe_str(outcome.get("reason")),
        "engine": safe_str(execution.get("engine")),
        "decision": outcome.get("decision", {}),
        "record": execution.get("record", {}),
        "browser": snapshot,
        "notes": ["private_browser_action_via_plugin"],
    }
