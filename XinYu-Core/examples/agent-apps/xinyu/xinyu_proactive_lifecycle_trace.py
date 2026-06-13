from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_proactive_lifecycle_trace_store import append_proactive_lifecycle_trace_event


TRACE_REL = Path("runtime/proactive_request_trace.jsonl")

_FIELD_RE = re.compile(r"(?m)^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")


def append_proactive_lifecycle_event(
    root: Path,
    *,
    event_kind: str,
    event_time: str | None = None,
    request_state: str = "",
    dispatch_state: str = "",
    request_id: str = "",
    claim_id: str = "",
    ack_status: str = "",
    adapter_status: str = "",
    notes: list[Any] | tuple[Any, ...] = (),
) -> None:
    """Append a privacy-preserving lifecycle event for proactive candidates."""
    root = root.resolve()
    event_time = _timestamp_or_now_iso(event_time)
    request_id = _first_non_empty(
        request_id,
        _extract_value(request_state, "request_id", ""),
        _extract_value(dispatch_state, "proactive_request_id", ""),
    )
    candidate_text = _first_non_empty(
        _extract_value(request_state, "concrete_question", ""),
        _extract_value(dispatch_state, "last_claimed_message", ""),
    )
    payload = {
        "event_kind": _clean_token(event_kind),
        "event_time": event_time,
        "request_id": _safe_value(request_id, default="none"),
        "status": _safe_value(_extract_value(request_state, "status", ""), default="unknown"),
        "kind": _safe_value(_extract_value(request_state, "kind", ""), default="unknown"),
        "source": _safe_value(_extract_value(request_state, "source", ""), default="unknown"),
        "focus_kind": _safe_value(_extract_value(request_state, "focus_kind", ""), default="unknown"),
        "reason": _safe_value(_extract_value(request_state, "reason", ""), default="unknown"),
        "urgency": _safe_value(_extract_value(request_state, "urgency", ""), default="unknown"),
        "risk": _safe_value(_extract_value(request_state, "risk", ""), default="unknown"),
        "owner_relevance": _safe_value(_extract_value(request_state, "owner_relevance", ""), default="unknown"),
        "channel": _safe_value(_extract_value(request_state, "channel", ""), default="unknown"),
        "expiration": _safe_value(
            _first_non_empty(
                _extract_value(request_state, "expiration", ""),
                _extract_value(request_state, "expires_at", ""),
            ),
            default="unknown",
        ),
        "delivery_level": _safe_value(_extract_value(request_state, "delivery_level", ""), default="unknown"),
        "claim_id": _safe_value(
            _first_non_empty(claim_id, _extract_value(dispatch_state, "last_claim_id", "")),
            default="none",
        ),
        "claim_status": _safe_value(_extract_value(dispatch_state, "last_claim_status", ""), default="unknown"),
        "ack_status": _safe_value(
            _first_non_empty(ack_status, _extract_value(dispatch_state, "last_ack_status", "")),
            default="unknown",
        ),
        "adapter_status": _safe_value(adapter_status, default="none"),
        "candidate_hash": _text_hash(candidate_text),
        "notes": [_safe_value(note, default="note") for note in notes if _safe_value(note, default="")],
    }
    append_proactive_lifecycle_trace_event(root / TRACE_REL, payload)


def _extract_value(text: str, field: str, default: str = "none") -> str:
    for match in _FIELD_RE.finditer(text or ""):
        if match.group(1) == field:
            value = " ".join(str(match.group(2) or "").replace("\r\n", "\n").replace("\r", "\n").split())
            return value or default
    return default


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = "" if value is None else str(value).strip()
        if text and text not in {"none", "unknown"}:
            return text
    return ""


def _safe_value(value: Any, *, default: str) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split())
    text = text[:240].strip()
    return text or default


def _clean_token(value: Any) -> str:
    text = _safe_value(value, default="unknown").lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_.:-]+", "_", text).strip("_")
    return text or "unknown"


def _text_hash(value: str) -> str:
    text = _safe_value(value, default="")
    if not text:
        return "none"
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = "" if value is None else str(value).strip()
    if text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            return parsed.astimezone().isoformat()
        except Exception:
            pass
    return datetime.now().astimezone().isoformat()
