"""Text scrubbing / normalization helpers for runtime presence.

Extracted from ``xinyu_runtime_presence`` so the presence module can stay focused
on record/read APIs while pure string policy lives here (testable, no IO).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

DEFAULT_PREVIEW_CHARS = 160

_LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
_LONG_NUMERIC_ID_RE = re.compile(r"\b\d{8,}\b")
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bxinyu[_-]?(?:api[_-]?key|bridge[_-]?token)\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def stable_hash(value: str, *, length: int = 12) -> str:
    clean = safe_str(value).strip()
    if not clean:
        return ""
    return "sha256:" + hashlib.sha256(clean.encode("utf-8", errors="ignore")).hexdigest()[:length]


def scrub_field(value: Any) -> str:
    text = safe_str(value)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[redacted-secret]", text)
    text = _LOCAL_PATH_RE.sub("[local-path]", text)
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def clip_preview(value: Any, *, limit: int = DEFAULT_PREVIEW_CHARS) -> str:
    text = scrub_field(value)
    text = _LONG_NUMERIC_ID_RE.sub("[id]", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def clip_note(value: Any, *, limit: int = 120) -> str:
    return clip_preview(value, limit=limit)


def path_label(value: Any) -> str:
    text = safe_str(value).strip()
    if not text:
        return ""
    parts = re.split(r"[\\/]+", text)
    return clip_preview(parts[-1] if parts else text, limit=120)


def normalize_turn_status(value: Any) -> str:
    text = safe_str(value).strip().lower()
    if text in {"ok", "done", "success", "finished"}:
        return "ok"
    if text in {"timeout", "timed_out", "time_out"}:
        return "timeout"
    if text in {"cancelled", "canceled"}:
        return "cancelled"
    if text in {"error", "failed", "fail"}:
        return "error"
    return clip_preview(text or "unknown", limit=40)


def normalize_codex_status(value: Any, *, timed_out: bool = False) -> str:
    if timed_out:
        return "timed_out"
    text = safe_str(value).strip().lower()
    aliases = {
        "done": "finished",
        "ok": "finished",
        "success": "finished",
        "completed": "finished",
        "complete": "finished",
        "timeout": "timed_out",
        "timedout": "timed_out",
        "time_out": "timed_out",
        "error": "failed",
        "failure": "failed",
        "fail": "failed",
        "scheduled": "running",
        "started": "running",
    }
    clean = aliases.get(text, text)
    if clean in {"idle", "running", "finished", "timed_out", "failed", "unknown"}:
        return clean
    return clip_preview(clean or "unknown", limit=40)


def codex_event_kind(status: str) -> str:
    if status == "running":
        return "codex_started"
    if status == "finished":
        return "codex_finished"
    if status == "timed_out":
        return "codex_timed_out"
    if status == "failed":
        return "codex_failed"
    return "codex_presence"


def normalize_background_state(value: Any) -> str:
    if isinstance(value, bool):
        return "running" if value else "idle"
    text = safe_str(value).strip().lower()
    if text in {"idle", "running", "disabled", "unknown", "pending"}:
        return text
    if text in {"true", "yes", "on", "active"}:
        return "running"
    if text in {"false", "no", "off", "inactive"}:
        return "idle"
    return clip_preview(text or "unknown", limit=40)
