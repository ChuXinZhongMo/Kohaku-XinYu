from __future__ import annotations

from typing import Any

from xinyu_external_plugins import TRANSPORT_NATIVE_BRIDGE, ExternalCallContext


def execute_computer_control(
    root: Any,
    capability: str,
    args: dict[str, Any],
    context: ExternalCallContext,
    grants: dict[str, Any],
    deps: Any,
) -> dict[str, Any]:
    safe_str = deps.safe_str
    if capability not in {"screenshot", "region_screenshot"}:
        return {
            "ok": False,
            "executed": False,
            "transport": TRANSPORT_NATIVE_BRIDGE,
            "result": "blocked",
            "decision": {},
            "record": {},
            "error_code": "computer_control_capability_unavailable",
        }

    from xinyu_computer_control import run_computer_action
    from xinyu_private_ecosystem_grants import computer_grant

    backend = None
    try:
        from xinyu_computer_capture_mss import MssCaptureBackend

        backend = MssCaptureBackend()
    except Exception:
        backend = None
    result = run_computer_action(
        root,
        action_kind=capability,
        window_title=safe_str(args.get("window_title") or args.get("windowTitle")),
        region=args.get("region") if isinstance(args.get("region"), dict) else None,
        x=args.get("x"),
        y=args.get("y"),
        text=safe_str(args.get("text")),
        keys=safe_str(args.get("keys")),
        grant=computer_grant(grants),
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
        "screenshot_ref": safe_str(result.get("screenshot_ref")),
        "decision": result.get("decision", {}),
        "record": result.get("record", {}),
        "error_code": safe_str((result.get("decision") or {}).get("reason")) if not result.get("ok") else "",
    }
