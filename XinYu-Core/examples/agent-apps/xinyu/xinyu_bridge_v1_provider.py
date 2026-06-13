from __future__ import annotations

from typing import Any


def health(runtime: Any) -> dict[str, Any]:
    return {
        "enabled": runtime.v1_enabled,
        "shadow_mode": runtime.v1_shadow_mode,
        "shadow_timeout_seconds": runtime.v1_shadow_timeout_seconds,
        "owner_simple_canary": runtime.v1_owner_simple_canary,
        "canary_timeout_seconds": runtime.v1_canary_timeout_seconds,
        "owner_user_ids_configured": len(runtime.v1_owner_user_ids),
        "loaded": runtime._v1_app is not None,
        "last_trace_id": runtime._v1_last_trace_id,
        "last_route": runtime._v1_last_route,
        "last_error": runtime._v1_last_error,
    }


def ensure_app(runtime: Any) -> Any:
    if runtime._v1_app is not None:
        return runtime._v1_app
    from xinyu_v1.app import XinYuV1App
    from xinyu_v1.config import XinYuV1Config

    runtime._v1_app = XinYuV1App(XinYuV1Config.load(runtime.xinyu_dir))
    return runtime._v1_app
