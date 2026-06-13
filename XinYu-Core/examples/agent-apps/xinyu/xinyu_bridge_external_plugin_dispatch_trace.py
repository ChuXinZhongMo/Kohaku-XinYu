from __future__ import annotations

from typing import Any

from xinyu_external_plugins import TRANSPORT_NATIVE_BRIDGE


def empty_execution_trace() -> dict[str, Any]:
    return {}


def codex_delegate_execution_trace(result: dict[str, Any]) -> dict[str, Any]:
    ok = bool(result.get("accepted"))
    return {
        "ok": ok,
        "executed": True,
        "transport": TRANSPORT_NATIVE_BRIDGE,
        "bridge_method": "codex_execute",
        "result": result,
    }


__all__ = ["codex_delegate_execution_trace", "empty_execution_trace"]
