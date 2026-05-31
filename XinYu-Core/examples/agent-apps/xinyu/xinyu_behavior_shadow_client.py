from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable


DEFAULT_ENDPOINT = "http://127.0.0.1:8877/behavior_shadow_log"
NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PostFn = Callable[[str, dict[str, Any], float], dict[str, Any]]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_text(source: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _safe_str(source.get(key)).strip()
        if text:
            return text
    return ""


def _route_signal(route: str, payload: dict[str, Any], metadata: dict[str, Any]) -> str:
    route = _safe_str(route).strip()
    source = _safe_str(payload.get("source") or metadata.get("source")).strip()
    if route == "codex_execute" or source == "qq_gateway_codex_execute_message":
        return "code_or_file_review_request"
    if route == "learning_ingest":
        return "learning_ingest_request"
    if route == "sticker_import":
        return "sticker_import_request"
    if route in {"package_install", "review_admin", "goldmark_mark", "self_action_approval"}:
        return "control_plane_request"
    return ""


def build_behavior_shadow_payload(
    payload: dict[str, Any],
    *,
    route: str,
    target: dict[str, Any] | None = None,
    include_text: bool = False,
) -> dict[str, Any]:
    metadata = _safe_dict(payload.get("metadata"))
    text = _first_text(
        payload,
        (
            "raw_owner_task",
            "text",
            "reason",
            "raw_command",
            "owner_note",
            "message",
            "content",
        ),
    )
    signal = _route_signal(route, payload, metadata)
    message_id = _safe_str(payload.get("message_id") or metadata.get("message_id")).strip()
    turn_id = _safe_str(payload.get("turn_id") or payload.get("request_id") or message_id).strip()
    return {
        "turn_id": turn_id,
        "request_id": turn_id,
        "message_id": message_id,
        "session_id": _safe_str(payload.get("session_id")).strip(),
        "user_text": text[:1200],
        "source": "qq_gateway_live_entry",
        "surface": "qq",
        "signal": signal,
        "shadow_behavior_include_text": bool(include_text),
        "input_context": {
            "route": _safe_str(route).strip(),
            "platform": _safe_str(payload.get("platform")).strip(),
            "adapter": _safe_str(payload.get("adapter")).strip(),
            "message_type": _safe_str(payload.get("message_type")).strip(),
            "source": _safe_str(payload.get("source") or metadata.get("source")).strip(),
            "source_channel": _safe_str(metadata.get("source_channel")).strip(),
            "onebot_message_type": _safe_str(metadata.get("onebot_message_type")).strip(),
            "qq_current_turn_message_kind": _safe_str(metadata.get("qq_current_turn_message_kind")).strip(),
            "target": target if isinstance(target, dict) else {},
        },
    }


def post_behavior_shadow_log(endpoint: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"},
        method="POST",
    )
    with NO_PROXY_OPENER.open(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="replace")
    value = json.loads(body)
    return value if isinstance(value, dict) else {}


def record_behavior_shadow_log(
    payload: dict[str, Any],
    *,
    route: str,
    target: dict[str, Any] | None = None,
    enabled: bool,
    endpoint: str | None = None,
    include_text: bool = False,
    timeout_seconds: float = 1.0,
    post_fn: PostFn | None = None,
) -> dict[str, Any]:
    if not enabled:
        return {"recorded": False, "ok": False, "notes": ["behavior_shadow_log_disabled"]}
    endpoint = (endpoint or DEFAULT_ENDPOINT).strip()
    if not endpoint:
        return {"recorded": False, "ok": False, "notes": ["behavior_shadow_log_endpoint_empty"]}
    try:
        timeout_seconds = max(0.1, min(10.0, float(timeout_seconds)))
    except (TypeError, ValueError):
        timeout_seconds = 1.0
    shadow_payload = build_behavior_shadow_payload(
        payload,
        route=route,
        target=target,
        include_text=include_text,
    )
    if not shadow_payload["user_text"]:
        return {"recorded": False, "ok": False, "notes": ["behavior_shadow_log_empty_text"]}

    started = time.perf_counter()
    try:
        response = (post_fn or post_behavior_shadow_log)(endpoint, shadow_payload, timeout_seconds)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {
            "recorded": False,
            "ok": False,
            "error": f"{type(exc).__name__}:{exc}",
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "notes": ["behavior_shadow_log_post_failed"],
        }
    except Exception as exc:
        return {
            "recorded": False,
            "ok": False,
            "error": f"{type(exc).__name__}:{exc}",
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "notes": ["behavior_shadow_log_unexpected_error"],
        }

    return {
        "recorded": True,
        "ok": bool(response.get("ok")) and response.get("shadow_only") is True,
        "behavior": response.get("behavior") if isinstance(response.get("behavior"), dict) else {},
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "notes": ["behavior_shadow_log_recorded"],
    }
