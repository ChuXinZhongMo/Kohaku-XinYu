from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from behavior_gate import behavior_gate, normalize_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = ROOT / "state" / "behavior_gate_shadow.jsonl"


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_text(source: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = source.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return path.name


def shadow_gate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    context = _safe_dict(payload.get("input_context"))
    user_text = _first_text(payload, ("u", "user_text", "text", "message", "content"))
    if not user_text:
        user_text = _first_text(context, ("u", "user_text", "text", "message", "content"))

    gate_payload: dict[str, Any] = {
        "u": normalize_text(user_text),
        "act": _first_text(payload, ("act", "dialog_act")) or _first_text(context, ("act", "dialog_act")),
        "category": _first_text(payload, ("category",)) or _first_text(context, ("category",)),
        "signal": _first_text(payload, ("signal",)) or _first_text(context, ("signal",)),
        "surface": _first_text(payload, ("surface",)) or _first_text(context, ("surface",)),
        "source": _first_text(payload, ("source",)) or _first_text(context, ("source",)),
    }
    return {key: value for key, value in gate_payload.items() if value != ""}


def behavior_shadow_event(
    payload: dict[str, Any],
    *,
    source_endpoint: str = "",
    include_text: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    gate_payload = shadow_gate_payload(payload)
    text = normalize_text(gate_payload.get("u"))
    mode, reason = behavior_gate(gate_payload)
    event = {
        "schema": "xinyu_behavior_shadow_log_v001",
        "event_id": "behavior-shadow-" + uuid.uuid4().hex[:12],
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "event_kind": "xinyu_maia_behavior_gate_shadow",
        "source_endpoint": source_endpoint,
        "turn_id": _first_text(payload, ("turn_id", "request_id", "message_id")),
        "request_hash": text_hash(text),
        "request_chars": len(text),
        "behavior": {
            "mode": mode,
            "reason": reason,
        },
        "kernel_decision_mode": _first_text(payload, ("kernel_decision_mode",)),
        "gate_payload_meta": {
            key: gate_payload.get(key)
            for key in ("act", "category", "signal", "surface", "source")
            if gate_payload.get(key)
        },
        "shadow_only": True,
        "visible_reply_sent": False,
        "stable_memory_written": False,
        "tool_executed": False,
        "adapter_activated": False,
        "training_target": False,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "notes": ["behavior_gate_shadow_log", "offline_only"],
    }
    if include_text:
        event["u"] = text
    return event


def append_behavior_shadow_event(
    payload: dict[str, Any],
    *,
    path: Path = DEFAULT_LOG_PATH,
    source_endpoint: str = "",
    include_text: bool = False,
) -> dict[str, Any]:
    event = behavior_shadow_event(payload, source_endpoint=source_endpoint, include_text=include_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "ok": True,
        "stored": True,
        "path": _relative(path),
        "event": event,
    }
