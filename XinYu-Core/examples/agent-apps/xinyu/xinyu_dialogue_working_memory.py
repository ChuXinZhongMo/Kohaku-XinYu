from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_visible_text_sanitizer import sanitize_visible_text


DEFAULT_PROMPT_TAIL_ENTRIES = 32
DEFAULT_SESSION_TAIL_ENTRIES = 64
DEFAULT_PERSISTED_TAIL_ENTRIES = 192
DEFAULT_PROMPT_ENTRY_CHARS = 360
DEFAULT_PROMPT_TOTAL_CHARS = 2600


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _env_int(name: str, default: int) -> int:
    try:
        return int(_safe_str(os.environ.get(name)).strip() or default)
    except (TypeError, ValueError):
        return default


def prompt_tail_entries() -> int:
    return max(0, _env_int("XINYU_DIALOGUE_PROMPT_TAIL_ENTRIES", DEFAULT_PROMPT_TAIL_ENTRIES))


def session_tail_entries() -> int:
    return max(0, _env_int("XINYU_DIALOGUE_SESSION_TAIL_ENTRIES", DEFAULT_SESSION_TAIL_ENTRIES))


def persisted_tail_entries() -> int:
    return max(0, _env_int("XINYU_DIALOGUE_PERSISTED_TAIL_ENTRIES", DEFAULT_PERSISTED_TAIL_ENTRIES))


def prompt_entry_chars() -> int:
    return max(40, _env_int("XINYU_DIALOGUE_PROMPT_ENTRY_CHARS", DEFAULT_PROMPT_ENTRY_CHARS))


def prompt_total_chars() -> int:
    return max(400, _env_int("XINYU_DIALOGUE_PROMPT_TOTAL_CHARS", DEFAULT_PROMPT_TOTAL_CHARS))


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _session_hash(session_key: str) -> str:
    normalized = _safe_str(session_key, "default").strip() or "default"
    return hashlib.sha256(normalized.encode("utf-8", errors="replace")).hexdigest()[:24]


def _session_path(root: Path, session_key: str) -> Path:
    return root / "runtime/dialogue_working_memory" / f"{_session_hash(session_key)}.jsonl"


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def inspect_dialogue_tail_storage(root: Path, session_key: str) -> dict[str, Any]:
    safe_session_key = _safe_str(session_key).strip()
    if not safe_session_key:
        return {
            "status": "session_unscoped",
            "reason": "missing_session_key",
            "usable_row_count": 0,
            "filtered_row_count": 0,
            "invalid_line_count": 0,
        }

    path = _session_path(root, safe_session_key)
    if not path.exists():
        return {
            "status": "missing_file",
            "reason": "working_memory_file_missing",
            "usable_row_count": 0,
            "filtered_row_count": 0,
            "invalid_line_count": 0,
        }

    try:
        raw = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        return {
            "status": "read_error",
            "reason": f"working_memory_read_error:{type(exc).__name__}",
            "usable_row_count": 0,
            "filtered_row_count": 0,
            "invalid_line_count": 0,
        }

    nonempty_line_count = 0
    usable_row_count = 0
    filtered_row_count = 0
    invalid_line_count = 0
    json_row_count = 0

    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        nonempty_line_count += 1
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            invalid_line_count += 1
            continue
        if not isinstance(data, dict):
            filtered_row_count += 1
            continue
        json_row_count += 1
        role = _safe_str(data.get("role")).strip()
        content = _safe_str(data.get("content")).strip()
        if role == "assistant":
            content = sanitize_visible_text(content).strip()
        if role in {"user", "assistant"} and content:
            usable_row_count += 1
        else:
            filtered_row_count += 1

    if nonempty_line_count == 0:
        status = "empty_file"
        reason = "working_memory_file_empty"
    elif usable_row_count > 0 and (filtered_row_count > 0 or invalid_line_count > 0):
        status = "available_with_filtered_rows"
        reason = "working_memory_rows_available_with_filtered_lines"
    elif usable_row_count > 0:
        status = "available"
        reason = "working_memory_rows_available"
    elif json_row_count > 0 or filtered_row_count > 0:
        status = "filtered_only"
        reason = "working_memory_rows_filtered"
    elif invalid_line_count > 0:
        status = "decode_failed"
        reason = "working_memory_decode_failed"
    else:
        status = "empty_file"
        reason = "working_memory_file_empty"

    return {
        "status": status,
        "reason": reason,
        "usable_row_count": usable_row_count,
        "filtered_row_count": filtered_row_count,
        "invalid_line_count": invalid_line_count,
    }


def _normalize_content(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _content_hash(text: str) -> str:
    clean = _normalize_content(sanitize_visible_text(text))
    if not clean:
        return ""
    return "sha256:" + hashlib.sha256(clean.encode("utf-8", errors="replace")).hexdigest()


def _assistant_reply_matches(row: dict[str, Any], *, reply: str, reply_hash: str) -> bool:
    if _safe_str(row.get("role")).strip() != "assistant":
        return False
    content = sanitize_visible_text(_safe_str(row.get("content")).strip())
    if not content:
        return False
    clean_reply = sanitize_visible_text(reply)
    if clean_reply and _normalize_content(content) == _normalize_content(clean_reply):
        return True
    return bool(reply_hash and _content_hash(content) == reply_hash)


def _truncate(text: str, limit: int) -> str:
    clean = _normalize_content(text)
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def load_dialogue_tail(
    root: Path,
    session_key: str,
    *,
    max_entries: int | None = None,
    include_timestamps: bool = False,
    truncate_chars: int | None = None,
) -> list[dict[str, str]]:
    safe_max = session_tail_entries() if max_entries is None else max(0, int(max_entries))
    if safe_max == 0:
        return []
    tail: list[dict[str, str]] = []
    for row in _load_rows(_session_path(root, session_key))[-safe_max:]:
        role = _safe_str(row.get("role")).strip()
        content = _safe_str(row.get("content")).strip()
        if role in {"user", "assistant"} and content:
            if role == "assistant":
                content = sanitize_visible_text(content)
            item = {"role": role, "content": _truncate(content, truncate_chars) if truncate_chars else content}
            if include_timestamps:
                recorded_at = _safe_str(row.get("recorded_at")).strip()
                if recorded_at:
                    item["recorded_at"] = recorded_at
            tail.append(item)
    return tail[-safe_max:]


def save_dialogue_tail(
    root: Path,
    session_key: str,
    tail: list[dict[str, str]],
    *,
    max_entries: int | None = None,
) -> bool:
    safe_max = persisted_tail_entries() if max_entries is None else max(0, int(max_entries))
    path = _session_path(root, session_key)
    if safe_max == 0:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
        except OSError:
            return False
        return True
    rows: list[dict[str, str]] = []
    for item in tail[-safe_max:]:
        role = _safe_str(item.get("role")).strip()
        content = _safe_str(item.get("content")).strip()
        if role in {"user", "assistant"} and content:
            if role == "assistant":
                content = sanitize_visible_text(content)
            recorded_at = _safe_str(item.get("recorded_at")).strip() or _now_iso()
            rows.append({"role": role, "content": content, "recorded_at": recorded_at})
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
    except OSError:
        return False
    return True


def remove_matching_assistant_reply_from_tail(
    tail: list[dict[str, str]],
    *,
    reply: str = "",
    reply_hash: str = "",
    max_scan_entries: int = 16,
) -> dict[str, Any]:
    clean_hash = _safe_str(reply_hash).strip()
    clean_reply = sanitize_visible_text(reply).strip()
    if not clean_reply and not clean_hash:
        return {"removed": False, "removed_count": 0, "notes": ["missing_reply_identity"]}
    scan = max(1, int(max_scan_entries))
    start = max(0, len(tail) - scan)
    for index in range(len(tail) - 1, start - 1, -1):
        item = tail[index]
        if not isinstance(item, dict):
            continue
        if _assistant_reply_matches(item, reply=clean_reply, reply_hash=clean_hash):
            del tail[index]
            return {"removed": True, "removed_count": 1, "notes": ["dialogue_tail_assistant_reply_removed"]}
    return {"removed": False, "removed_count": 0, "notes": ["matching_assistant_reply_not_found"]}


def remove_matching_assistant_reply(
    root: Path,
    session_key: str,
    *,
    reply: str = "",
    reply_hash: str = "",
    max_scan_entries: int = 16,
) -> dict[str, Any]:
    path = _session_path(root, session_key)
    rows = _load_rows(path)
    if not rows:
        return {"removed": False, "removed_count": 0, "notes": ["dialogue_tail_empty_or_missing"]}
    result = remove_matching_assistant_reply_from_tail(
        rows,
        reply=reply,
        reply_hash=reply_hash,
        max_scan_entries=max_scan_entries,
    )
    if not result.get("removed"):
        return result
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
    except OSError:
        return {"removed": False, "removed_count": 0, "notes": ["dialogue_tail_write_failed"]}
    return result


def compact_tail_for_prompt(
    dialogue_tail: list[dict[str, str]],
    *,
    max_entries: int | None = None,
    entry_chars: int | None = None,
    total_chars: int | None = None,
    include_timestamps: bool = False,
) -> list[dict[str, str]]:
    safe_entries = prompt_tail_entries() if max_entries is None else max(0, int(max_entries))
    safe_entry_chars = prompt_entry_chars() if entry_chars is None else max(40, int(entry_chars))
    safe_total_chars = prompt_total_chars() if total_chars is None else max(400, int(total_chars))
    if safe_entries == 0:
        return []

    compacted: list[dict[str, str]] = []
    used_chars = 0
    for raw in dialogue_tail[-safe_entries:]:
        role = _safe_str(raw.get("role")).strip()
        content = _safe_str(raw.get("content")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        remaining = safe_total_chars - used_chars
        if remaining <= 0:
            break
        limit = min(safe_entry_chars, remaining)
        item = {"role": role, "content": _truncate(content, limit)}
        if include_timestamps:
            recorded_at = _safe_str(raw.get("recorded_at")).strip()
            if recorded_at:
                item["recorded_at"] = recorded_at
        compacted.append(item)
        used_chars += len(item["content"]) + len(role) + 8
    return compacted
