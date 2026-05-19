from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


TRACE_REL = Path("runtime/tinykernel_compose_shadow_trace.jsonl")
DEFAULT_ENDPOINT = "http://127.0.0.1:8877/compose_shadow"
ENABLED_ENV = "XINYU_TINYKERNEL_SHADOW_ENABLED"
ENDPOINT_ENV = "XINYU_TINYKERNEL_SHADOW_ENDPOINT"
TIMEOUT_ENV = "XINYU_TINYKERNEL_SHADOW_TIMEOUT_SECONDS"
PostFn = Callable[[str, dict[str, Any], float], dict[str, Any]]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat(timespec="seconds")


def _parse_iso(value: Any) -> datetime | None:
    text = "" if value is None else str(value).strip()
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def shadow_enabled() -> bool:
    return str(os.environ.get(ENABLED_ENV, "")).strip().lower() in {"1", "true", "yes", "on"}


def build_tinykernel_payload(
    *,
    turn_id: str,
    source: str,
    user_text: str,
    context: dict[str, Any] | None = None,
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "turn_id": str(turn_id or ""),
        "source": str(source or "unknown"),
        "user_text": str(user_text or "")[:1200],
        "context": context if isinstance(context, dict) else {},
        "capabilities": capabilities if isinstance(capabilities, dict) else {},
        "constraints": {
            "max_reply_chars": 240,
            "allow_tool_request": False,
            "allow_memory_candidate": False,
        },
    }


def call_tinykernel(endpoint: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="replace")
    value = json.loads(body)
    return value if isinstance(value, dict) else {}


def record_tinykernel_shadow(
    root: Path,
    *,
    turn_id: str,
    source: str,
    user_text: str,
    context: dict[str, Any] | None = None,
    capabilities: dict[str, Any] | None = None,
    enabled: bool | None = None,
    endpoint: str | None = None,
    post_fn: PostFn | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    enabled_value = shadow_enabled() if enabled is None else bool(enabled)
    observed_at = _timestamp_or_now_iso(observed_at or _now_iso())
    if not enabled_value:
        return {"recorded": False, "ok": False, "notes": ["tinykernel_shadow_disabled"]}

    endpoint = endpoint or os.environ.get(ENDPOINT_ENV, DEFAULT_ENDPOINT)
    try:
        timeout_seconds = max(0.1, min(10.0, float(os.environ.get(TIMEOUT_ENV, "2.0"))))
    except ValueError:
        timeout_seconds = 2.0
    payload = build_tinykernel_payload(
        turn_id=turn_id,
        source=source,
        user_text=user_text,
        context=context,
        capabilities=capabilities,
    )
    started = time.perf_counter()
    error = ""
    response: dict[str, Any] = {}
    try:
        response = (post_fn or call_tinykernel)(endpoint, payload, timeout_seconds)
        if response.get("shadow_only") is not True:
            error = "shadow_only_false"
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        error = f"{type(exc).__name__}:{exc}"
    except Exception as exc:
        error = f"{type(exc).__name__}:{exc}"
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    emotion_biases = response.get("emotion_biases") if isinstance(response.get("emotion_biases"), list) else []
    selected_bias = response.get("selected_bias") if isinstance(response.get("selected_bias"), dict) else {}
    row = {
        "event_kind": "tinykernel_compose_shadow_observation",
        "observed_at": _timestamp_or_now_iso(observed_at),
        "turn_id": str(turn_id or ""),
        "ok": bool(response.get("ok")) and not error,
        "shadow_only": response.get("shadow_only") is True,
        "mode": str(response.get("mode") or ""),
        "request_hash": str(response.get("request_hash") or ""),
        "request_chars": int(response.get("request_chars") or len(str(user_text or ""))),
        "reply_candidate_chars": len(str(response.get("reply_candidate") or "")),
        "emotion_lenses": [str(item.get("lens")) for item in emotion_biases if isinstance(item, dict) and item.get("lens")],
        "selected_lens": str(selected_bias.get("lens") or ""),
        "confidence": float(response.get("confidence") or 0.0),
        "elapsed_ms": elapsed_ms,
        "error": error,
        "notes": [str(item) for item in response.get("notes", [])] if isinstance(response.get("notes"), list) else [],
    }
    trace_path = root / TRACE_REL
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return {"recorded": True, "ok": row["ok"], "row": row, "notes": ["tinykernel_shadow_recorded"]}
