from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_sent_reply_index_store import read_sent_reply_index_data
from xinyu_sent_reply_index_store import write_sent_reply_index_data
from xinyu_visible_text_sanitizer import sanitize_visible_text


INDEX_REL = Path("runtime/sent_reply_index.json")
DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_MAX_ENTRIES = 1000
_CQ_RE = re.compile(r"\[CQ:[^\]]+\]", re.I)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = _safe_str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return _now_iso()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return _now_iso()
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def normalize_visible_text(text: str) -> str:
    cleaned = _CQ_RE.sub("", _safe_str(text))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return sanitize_visible_text(cleaned)


def visible_text_hash(text: str) -> str:
    normalized = normalize_visible_text(text)
    if not normalized:
        return ""
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _parse_time(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(_safe_str(value))
    except Exception:
        return None


def _age_seconds(value: Any) -> float:
    parsed = _parse_time(value)
    if parsed is None:
        return 999999999.0
    return max(0.0, (datetime.now().astimezone() - parsed).total_seconds())


def _read_index(path: Path) -> dict[str, Any]:
    return read_sent_reply_index_data(path)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    write_sent_reply_index_data(path, data)


def _entry_key(adapter: str, adapter_message_id: str, route: str) -> str:
    return "|".join((adapter.strip(), adapter_message_id.strip(), route.strip()))


def _normalize_adapter_message_id(value: Any) -> str:
    text = _safe_str(value).strip()
    if text.lower().startswith("qq:"):
        text = text[3:].strip()
    return text


def _adapter_message_id_parts(value: Any) -> list[str]:
    parts = [_normalize_adapter_message_id(part) for part in re.split(r"\s*,\s*", _safe_str(value))]
    return [part for part in parts if part]


def _compact_entries(
    entries: list[dict[str, Any]],
    *,
    ttl_seconds: int,
    max_entries: int,
) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        key = _safe_str(raw.get("key")).strip()
        if not key:
            key = _entry_key(
                _safe_str(raw.get("adapter")),
                _safe_str(raw.get("adapter_message_id")),
                _safe_str(raw.get("route")),
            )
        if not key or "||" in key:
            continue
        updated_at = _safe_str(raw.get("last_seen_at") or raw.get("sent_at") or raw.get("created_at"))
        if updated_at and _age_seconds(updated_at) > ttl_seconds:
            continue
        item = dict(raw)
        item["key"] = key
        old = by_key.get(key)
        if old is None or _safe_str(item.get("last_seen_at") or item.get("sent_at")) >= _safe_str(
            old.get("last_seen_at") or old.get("sent_at")
        ):
            by_key[key] = item
    compacted = sorted(
        by_key.values(),
        key=lambda item: _safe_str(item.get("last_seen_at") or item.get("sent_at") or item.get("created_at")),
        reverse=True,
    )
    return compacted[:max_entries]


def register_sent_reply_ack(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    max_entries: int = DEFAULT_MAX_ENTRIES,
) -> dict[str, Any]:
    payload = payload or {}
    adapter = _safe_str(payload.get("adapter") or payload.get("gateway") or "xinyu_native_qq_gateway").strip()
    adapter_message_id = _safe_str(payload.get("adapter_message_id")).strip()
    route = _safe_str(payload.get("route") or payload.get("source_route") or "chat").strip()
    if not adapter or not adapter_message_id or not route:
        return {"accepted": False, "indexed": False, "notes": ["missing_adapter_message_id_or_route"]}

    sent_at = _timestamp_or_now_iso(payload.get("sent_at"))
    visible_text = normalize_visible_text(_safe_str(payload.get("visible_text") or payload.get("message")))
    text_hash = _safe_str(payload.get("visible_text_hash") or payload.get("reply_hash")).strip()
    if not text_hash and visible_text:
        text_hash = visible_text_hash(visible_text)
    key = _entry_key(adapter, adapter_message_id, route)

    path = root / INDEX_REL
    data = _read_index(path)
    entries = _compact_entries(
        [item for item in data.get("entries", []) if isinstance(item, dict)],
        ttl_seconds=ttl_seconds,
        max_entries=max_entries,
    )

    existing: dict[str, Any] | None = None
    for item in entries:
        if _safe_str(item.get("key")) == key:
            existing = item
            break

    now = _timestamp_or_now_iso()
    entry = {
        "key": key,
        "adapter": adapter,
        "adapter_message_id": adapter_message_id,
        "route": route,
        "session_id": _safe_str(payload.get("session_id")).strip(),
        "turn_id": _safe_str(payload.get("turn_id")).strip(),
        "archive_message_ids": payload.get("archive_message_ids") if isinstance(payload.get("archive_message_ids"), list) else [],
        "archive_assistant_message_id": _safe_str(payload.get("archive_assistant_message_id")).strip(),
        "source_message_id": _safe_str(payload.get("source_message_id") or payload.get("message_id")).strip(),
        "outbox_message_id": _safe_str(payload.get("outbox_message_id")).strip(),
        "message_type": _safe_str(payload.get("message_type")).strip(),
        "target": payload.get("target") if isinstance(payload.get("target"), dict) else {},
        "visible_text_hash": text_hash,
        "visible_text_preview": visible_text[:240],
        "sent_at": sent_at,
        "first_seen_at": _timestamp_or_now_iso(existing.get("first_seen_at")) if existing else now,
        "last_seen_at": _timestamp_or_now_iso(now),
        "retry_count": int(existing.get("retry_count") or 0) + 1 if existing else 0,
        "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    }
    entries = [item for item in entries if _safe_str(item.get("key")) != key]
    entries.insert(0, entry)
    entries = _compact_entries(entries, ttl_seconds=ttl_seconds, max_entries=max_entries)
    data = {
        "version": 1,
        "updated_at": _timestamp_or_now_iso(now),
        "ttl_seconds": ttl_seconds,
        "max_entries": max_entries,
        "entries": entries,
    }
    _atomic_write_json(path, data)
    return {
        "accepted": True,
        "indexed": True,
        "key": key,
        "entry_count": len(entries),
        "notes": ["sent_reply_index_updated"],
    }


def read_sent_reply_index(root: Path) -> dict[str, Any]:
    return _read_index(root / INDEX_REL)


def lookup_sent_reply_by_adapter_msg_id(
    root: Path,
    adapter_message_id: str,
    *,
    adapter: str = "xinyu_native_qq_gateway",
    route: str = "",
) -> dict[str, Any]:
    needle = _normalize_adapter_message_id(adapter_message_id)
    if not needle:
        return {"found": False, "entry": {}, "notes": ["missing_adapter_message_id"]}

    data = read_sent_reply_index(root)
    entries = [item for item in data.get("entries", []) if isinstance(item, dict)]
    route = _safe_str(route).strip()
    adapter = _safe_str(adapter).strip()
    for item in entries:
        if adapter and _safe_str(item.get("adapter")).strip() != adapter:
            continue
        if route and _safe_str(item.get("route")).strip() != route:
            continue
        if needle in _adapter_message_id_parts(item.get("adapter_message_id")):
            return {
                "found": True,
                "entry": dict(item),
                "notes": ["sent_reply_index_hit"],
            }

    return {
        "found": False,
        "entry": {},
        "notes": ["sent_reply_index_miss"],
    }
