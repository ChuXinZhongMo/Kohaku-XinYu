from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from stores.persona_runtime_overlay import (
    read_goldmark_overlay as store_read_goldmark_overlay,
    write_goldmark_overlay,
)
from xinyu_dialogue_archive import dialogue_archive_path
from xinyu_sent_reply_index import lookup_sent_reply_by_adapter_msg_id, normalize_visible_text


MAX_OWNER_NOTE_CHARS = 500
MAX_OVERLAY_ENTRIES = 1000

_HARD_REJECT_FLAGS = {
    "empty_reply",
    "final_guard_blocked_unsendable_reply",
    "false_codex_unavailable_claim_blocked",
}
_ERROR_TEXT_MARKERS = (
    "traceback",
    "attributeerror",
    "exception:",
    "core bridge error",
    "xinYu core bridge error".lower(),
    "http 500",
    "unauthorized",
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _mark_id_from_turn(turn_id: str, adapter_message_id: str) -> str:
    match = re.search(r"turn-(\d{8})T(\d{6})", turn_id)
    if match:
        return f"gm-{match.group(1)}-T{match.group(2)}"
    digest = hashlib.sha256(f"{turn_id}|{adapter_message_id}".encode("utf-8", errors="replace")).hexdigest()[:8]
    return f"gm-{datetime.now().astimezone().strftime('%Y%m%d-T%H%M%S')}-{digest}"


def _entry_identity(entry: dict[str, Any]) -> str:
    return "|".join(
        (
            _safe_str(entry.get("adapter")).strip(),
            _safe_str(entry.get("adapter_msg_id") or entry.get("adapter_message_id")).strip(),
            _safe_str(entry.get("route")).strip(),
            _safe_str(entry.get("turn_id")).strip(),
        )
    )


def _json_loads(value: Any) -> Any:
    try:
        return json.loads(_safe_str(value))
    except (TypeError, json.JSONDecodeError):
        return {}


def _archive_message_by_id(root: Path, message_id: str) -> dict[str, Any]:
    if not _safe_str(message_id).strip().isdigit():
        return {}
    path = dialogue_archive_path(root)
    if not path.exists():
        return {}
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, role, text, quality_flags_json, metadata_json
            FROM dialogue_messages
            WHERE id = ?
            """,
            (int(message_id),),
        ).fetchone()
    except sqlite3.Error:
        return {}
    finally:
        if conn is not None:
            conn.close()
    return dict(row) if row is not None else {}


def _flags_from_archive(row: dict[str, Any]) -> set[str]:
    raw = _json_loads(row.get("quality_flags_json"))
    if isinstance(raw, list):
        return {_safe_str(item).strip() for item in raw if _safe_str(item).strip()}
    if isinstance(raw, dict):
        flags = raw.get("flags")
        if isinstance(flags, list):
            values = {_safe_str(item).strip() for item in flags if _safe_str(item).strip()}
        else:
            values = set()
        values.update(_safe_str(key).strip() for key, value in raw.items() if value is True and _safe_str(key).strip())
        return values
    return set()


def validate_goldmark_target(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    turn_id = _safe_str(entry.get("turn_id")).strip()
    if not turn_id:
        return {"ok": False, "reason": "missing_turn_id", "notes": ["goldmark_target_missing_turn_id"]}

    preview = normalize_visible_text(_safe_str(entry.get("visible_text_preview")))
    text_hash = _safe_str(entry.get("visible_text_hash")).strip()
    if not preview and not text_hash:
        return {"ok": False, "reason": "empty_visible_text", "notes": ["goldmark_target_empty_visible_text"]}

    lowered_preview = preview.lower()
    if any(marker in lowered_preview for marker in _ERROR_TEXT_MARKERS):
        return {"ok": False, "reason": "error_like_visible_text", "notes": ["goldmark_target_error_like_text"]}

    archive_id = _safe_str(entry.get("archive_assistant_message_id")).strip()
    archive_row = _archive_message_by_id(root, archive_id)
    if archive_row:
        role = _safe_str(archive_row.get("role")).strip()
        text = _safe_str(archive_row.get("text")).strip()
        if role != "assistant":
            return {"ok": False, "reason": "archive_role_not_assistant", "notes": ["goldmark_target_not_assistant"]}
        if not text:
            return {"ok": False, "reason": "empty_archive_reply", "notes": ["goldmark_target_empty_archive_reply"]}
        flags = _flags_from_archive(archive_row)
        blocked = sorted(flag for flag in flags if flag in _HARD_REJECT_FLAGS)
        if blocked:
            return {
                "ok": False,
                "reason": "hard_guard_flag",
                "notes": ["goldmark_target_hard_guard_flag:" + ",".join(blocked)],
            }

    return {"ok": True, "reason": "ok", "notes": ["goldmark_target_validated"]}


def read_goldmark_overlay(root: Path) -> list[dict[str, Any]]:
    return store_read_goldmark_overlay(root)


def mark_goldmark_request(root: Path, payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    adapter_message_id = _safe_str(payload.get("adapter_message_id") or payload.get("adapter_msg_id")).strip()
    adapter = _safe_str(payload.get("adapter") or "xinyu_native_qq_gateway").strip()
    route = _safe_str(payload.get("route") or "chat").strip()
    owner_note = _safe_str(payload.get("owner_note")).strip()[:MAX_OWNER_NOTE_CHARS]
    if not adapter_message_id:
        return {
            "accepted": False,
            "marked": False,
            "error": "missing_adapter_message_id",
            "http_status": 400,
            "notes": ["goldmark_missing_adapter_message_id"],
        }

    lookup = lookup_sent_reply_by_adapter_msg_id(root, adapter_message_id, adapter=adapter, route=route)
    if not lookup.get("found") and route:
        lookup = lookup_sent_reply_by_adapter_msg_id(root, adapter_message_id, adapter=adapter, route="")
    if not lookup.get("found"):
        return {
            "accepted": False,
            "marked": False,
            "error": "target_not_found",
            "http_status": 404,
            "adapter_message_id": adapter_message_id,
            "route": route,
            "notes": ["goldmark_target_not_found"],
        }

    sent_entry = dict(lookup.get("entry") if isinstance(lookup.get("entry"), dict) else {})
    validation = validate_goldmark_target(root, sent_entry)
    if not validation.get("ok"):
        return {
            "accepted": False,
            "marked": False,
            "error": "invalid_target",
            "http_status": 409,
            "adapter_message_id": adapter_message_id,
            "route": _safe_str(sent_entry.get("route") or route),
            "turn_id": _safe_str(sent_entry.get("turn_id")),
            "notes": list(validation.get("notes", [])),
        }

    now_iso = _now_iso()
    now_epoch = int(time.time())
    entry = {
        "mark_id": _mark_id_from_turn(_safe_str(sent_entry.get("turn_id")), adapter_message_id),
        "turn_id": _safe_str(sent_entry.get("turn_id")).strip(),
        "adapter": _safe_str(sent_entry.get("adapter") or adapter).strip(),
        "adapter_msg_id": _safe_str(sent_entry.get("adapter_message_id") or adapter_message_id).strip(),
        "route": _safe_str(sent_entry.get("route") or route).strip(),
        "session_id": _safe_str(sent_entry.get("session_id")).strip(),
        "archive_assistant_message_id": _safe_str(sent_entry.get("archive_assistant_message_id")).strip(),
        "visible_text_hash": _safe_str(sent_entry.get("visible_text_hash")).strip(),
        "visible_text_preview": _safe_str(sent_entry.get("visible_text_preview")).strip()[:240],
        "owner_note": owner_note,
        "marked_at": now_epoch,
        "marked_at_iso": now_iso,
        "source_command_message_id": _safe_str(payload.get("source_message_id") or payload.get("message_id")).strip(),
        "status": "marked",
        "stage": "p4b_mvp_mark_only",
        "dehydration_status": "pending",
        "dehydration_provider": "",
        "processing_started_at": "",
        "vibe_features": None,
        "error_log": None,
    }

    entries = read_goldmark_overlay(root)
    identity = _entry_identity(entry)
    existing = next((item for item in entries if _entry_identity(item) == identity), None)
    if existing:
        entry["mark_id"] = _safe_str(existing.get("mark_id") or entry["mark_id"])
        entry["first_marked_at"] = existing.get("first_marked_at") or existing.get("marked_at") or now_epoch
        entry["first_marked_at_iso"] = existing.get("first_marked_at_iso") or existing.get("marked_at_iso") or now_iso
        entry["remark_count"] = int(existing.get("remark_count") or 1) + 1
        entry["dehydration_status"] = _safe_str(existing.get("dehydration_status") or "pending").strip() or "pending"
        entry["dehydration_provider"] = _safe_str(existing.get("dehydration_provider")).strip()
        entry["processing_started_at"] = _safe_str(existing.get("processing_started_at")).strip()
        entry["vibe_features"] = existing.get("vibe_features")
        entry["error_log"] = existing.get("error_log")
    else:
        entry["first_marked_at"] = now_epoch
        entry["first_marked_at_iso"] = now_iso
        entry["remark_count"] = 1

    entries = [item for item in entries if _entry_identity(item) != identity]
    entries.insert(0, entry)
    entries = entries[:MAX_OVERLAY_ENTRIES]
    write_goldmark_overlay(root, entries)
    return {
        "accepted": True,
        "marked": True,
        "http_status": 200,
        "mark_id": entry["mark_id"],
        "turn_id": entry["turn_id"],
        "adapter_message_id": entry["adapter_msg_id"],
        "route": entry["route"],
        "entry_count": len(entries),
        "notes": ["goldmark_marked"],
    }
