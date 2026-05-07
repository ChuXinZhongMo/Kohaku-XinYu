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


def _normalize_content(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


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
