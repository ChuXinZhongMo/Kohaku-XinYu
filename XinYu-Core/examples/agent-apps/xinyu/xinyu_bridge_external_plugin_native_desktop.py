from __future__ import annotations

from typing import Any

from xinyu_external_plugins import TRANSPORT_NATIVE_BRIDGE, ExternalCallContext


def execute_private_desktop(
    root: Any,
    capability: str,
    args: dict[str, Any],
    context: ExternalCallContext,
    grants: dict[str, Any],
    deps: Any,
) -> dict[str, Any]:
    from xinyu_private_desktop_control import run_desktop_action
    from xinyu_private_desktop_service import active_backend
    from xinyu_private_ecosystem_grants import desktop_grant

    safe_str = deps.safe_str
    backend = None
    try:
        backend = active_backend(root)
    except Exception:
        backend = None
    result = run_desktop_action(
        root,
        action_kind=capability,
        x=args.get("x"),
        y=args.get("y"),
        button=safe_str(args.get("button")) or "left",
        delta=deps.as_int(args.get("delta"), 0),
        text=safe_str(args.get("text")),
        keys=safe_str(args.get("keys")),
        window_title=safe_str(args.get("window_title") or args.get("windowTitle")),
        grant=desktop_grant(grants),
        approved=bool(context.approved),
        execute=True,
        backend=backend,
    )
    return {
        "ok": bool(result.get("ok")),
        "executed": True,
        "transport": TRANSPORT_NATIVE_BRIDGE,
        "result": safe_str(result.get("result")),
        "backend": safe_str(result.get("backend")),
        "frame_ref": safe_str(result.get("frame_ref")),
        "decision": result.get("decision", {}),
        "record": result.get("record", {}),
        "error_code": safe_str(result.get("error_code")),
    }
