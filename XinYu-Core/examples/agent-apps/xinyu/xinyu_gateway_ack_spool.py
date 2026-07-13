from __future__ import annotations

import contextlib
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_gateway_ack_spool_store import append_gateway_ack_spool_event
from xinyu_gateway_ack_spool_store import gateway_ack_spool_file_size
from xinyu_gateway_ack_spool_store import read_gateway_ack_spool_events
from xinyu_gateway_ack_spool_store import write_gateway_ack_spool_events
from xinyu_visible_text_sanitizer import sanitize_visible_text


DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_MAX_ENTRIES = 1000
DEFAULT_MAX_BYTES = 1_000_000


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_time(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(_safe_str(value))
    except Exception:
        return None


def _age_seconds(value: Any) -> float:
    parsed = _parse_time(value)
    if parsed is None:
        return 999999999.0
    now = datetime.now().astimezone()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=now.tzinfo)
    return max(0.0, (now - parsed).total_seconds())


def ack_unique_key(payload: dict[str, Any]) -> str:
    adapter = _safe_str(payload.get("adapter") or payload.get("gateway") or "xinyu_native_qq_gateway").strip()
    adapter_message_id = _safe_str(payload.get("adapter_message_id")).strip()
    route = _safe_str(payload.get("route") or payload.get("source_route") or "chat").strip()
    if not adapter or not adapter_message_id or not route:
        return ""
    return "|".join((adapter, adapter_message_id, route))


def _sanitize_visible_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    changed = False
    for key in ("visible_text", "message"):
        value = _safe_str(sanitized.get(key)).strip()
        if not value:
            continue
        clean = sanitize_visible_text(value)
        if clean != value:
            sanitized[key] = clean
            changed = True
    if changed:
        sanitized["visible_text_hash"] = ""
    return sanitized


class SentAckSpool:
    def __init__(
        self,
        path: Path,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.max_bytes = max_bytes

    def append_pending(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = _sanitize_visible_payload(payload)
        key = ack_unique_key(payload)
        if not key:
            return {"accepted": False, "queued": False, "notes": ["missing_ack_unique_key"]}
        event = {
            "event": "pending",
            "key": key,
            "created_at": _now_iso(),
            "attempts": _safe_int(payload.get("ack_attempts")),
            "payload": payload,
        }
        self._append_event(event)
        self._compact_if_needed()
        return {"accepted": True, "queued": True, "key": key, "notes": ["pending_spooled"]}

    def append_acked(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = ack_unique_key(payload)
        if not key:
            return {"accepted": False, "acked": False, "notes": ["missing_ack_unique_key"]}
        self._append_event(
            {
                "event": "acked",
                "key": key,
                "acked_at": _now_iso(),
                "adapter_message_id": _safe_str(payload.get("adapter_message_id")),
                "route": _safe_str(payload.get("route")),
            }
        )
        self._compact_if_needed()
        return {"accepted": True, "acked": True, "key": key, "notes": ["acked_spooled"]}

    def pending_payloads(self) -> list[dict[str, Any]]:
        pending, _acked = self._fold_events()
        return list(pending.values())

    def compact(self) -> dict[str, Any]:
        pending, _acked = self._fold_events()
        events = [
            {
                "event": "pending",
                "key": ack_unique_key(payload),
                "created_at": _safe_str(payload.get("spooled_at") or payload.get("sent_at") or _now_iso()),
                "attempts": _safe_int(payload.get("ack_attempts")),
                "payload": payload,
            }
            for payload in pending.values()
        ]
        write_gateway_ack_spool_events(self.path, events)
        return {"compacted": True, "pending_count": len(pending)}

    def _append_event(self, event: dict[str, Any]) -> None:
        append_gateway_ack_spool_event(self.path, event)

    def _iter_events(self) -> tuple[list[dict[str, Any]], int]:
        return read_gateway_ack_spool_events(self.path)

    def _fold_events(self) -> tuple[dict[str, dict[str, Any]], set[str]]:
        events, _line_count = self._iter_events()
        pending: dict[str, dict[str, Any]] = {}
        acked: set[str] = set()
        for event in events:
            kind = _safe_str(event.get("event")).strip().lower()
            key = _safe_str(event.get("key")).strip()
            if not key:
                continue
            if kind == "acked":
                acked.add(key)
                pending.pop(key, None)
                continue
            if kind != "pending" or key in acked:
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            created_at = _safe_str(event.get("created_at") or payload.get("spooled_at") or payload.get("sent_at"))
            if created_at and _age_seconds(created_at) > self.ttl_seconds:
                continue
            item = dict(payload)
            item["spooled_at"] = created_at or _now_iso()
            item["ack_attempts"] = _safe_int(event.get("attempts") or payload.get("ack_attempts"))
            pending[key] = item
        if len(pending) > self.max_entries:
            ordered = sorted(
                pending.items(),
                key=lambda pair: _safe_str(pair[1].get("spooled_at") or pair[1].get("sent_at")),
                reverse=True,
            )
            pending = dict(ordered[: self.max_entries])
        return pending, acked

    def _compact_if_needed(self) -> None:
        size = gateway_ack_spool_file_size(self.path)
        if size is None:
            return
        _events, line_count = self._iter_events()
        if line_count > self.max_entries * 3 or size > self.max_bytes:
            with contextlib.suppress(OSError, ValueError):
                self.compact()
