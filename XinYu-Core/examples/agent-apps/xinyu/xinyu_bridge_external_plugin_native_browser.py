from __future__ import annotations

from typing import Any

from xinyu_external_plugins import TRANSPORT_NATIVE_BRIDGE, ExternalCallContext


def _close_quietly(resource: Any) -> None:
    if resource is None:
        return
    try:
        resource.close()
    except Exception:
        pass


def execute_private_browser(
    root: Any,
    capability: str,
    args: dict[str, Any],
    context: ExternalCallContext,
    grants: dict[str, Any],
    deps: Any,
) -> dict[str, Any]:
    from xinyu_browser_control import run_browser_action
    from xinyu_private_ecosystem_grants import browser_grant

    safe_str = deps.safe_str
    action_kind = {"navigate": "navigate_readonly"}.get(capability, capability)
    engine = None
    try:
        from xinyu_browser_engine_playwright import create_browser_engine

        engine = create_browser_engine(root, headless=True)
    except Exception:
        engine = None
    try:
        result = run_browser_action(
            root,
            action_kind=action_kind,
            url=safe_str(args.get("url")),
            element_id=safe_str(args.get("element_id") or args.get("elementId")),
            value=safe_str(args.get("value")),
            grant=browser_grant(grants),
            approved=bool(context.approved),
            execute=True,
            engine=engine,
        )
    finally:
        _close_quietly(engine)

    decision_data = result.get("decision") if isinstance(result.get("decision"), dict) else {}
    record = result.get("record") if isinstance(result.get("record"), dict) else {}
    error_code = safe_str(record.get("error_code") or decision_data.get("reason")) if not result.get("ok") else ""
    return {
        "ok": bool(result.get("ok")),
        "executed": True,
        "transport": TRANSPORT_NATIVE_BRIDGE,
        "result": safe_str(result.get("result")),
        "engine": safe_str(result.get("engine")),
        "decision": decision_data,
        "record": record,
        "error_code": error_code,
    }
