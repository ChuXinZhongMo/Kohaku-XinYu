from __future__ import annotations

from pathlib import Path
from typing import Any

from stores.state_service import append_jsonl
from stores.state_service import atomic_write_json
from stores.state_service import atomic_write_text
from stores.state_service import read_json
from stores.state_service import read_text_safe


BOUNDARY_ID = "stores/daily_digest_state"
COMPATIBILITY_NOTE = "legacy memory/context/daily_digest.json physical path kept until callers finish migration"

DIGEST_REL = Path("memory/context/daily_digest.json")
SOURCE_STATE_REL = Path("memory/context/watched_source_state.md")
STATE_REL = Path("memory/context/daily_digest_state.md")
TRACE_REL = Path("runtime/daily_digest_trace.jsonl")


def daily_digest_path(root: Path) -> Path:
    return Path(root) / DIGEST_REL


def daily_digest_source_state_path(root: Path) -> Path:
    return Path(root) / SOURCE_STATE_REL


def daily_digest_rendered_state_path(root: Path) -> Path:
    return Path(root) / STATE_REL


def daily_digest_trace_path(root: Path) -> Path:
    return Path(root) / TRACE_REL


def read_daily_digest(root: Path, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    data = read_json(daily_digest_path(root), default=default or {})
    return data if isinstance(data, dict) else dict(default or {})


def write_daily_digest(root: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(daily_digest_path(root), payload)


def read_daily_digest_source_state(root: Path) -> str:
    return read_text_safe(daily_digest_source_state_path(root), default="")


def write_daily_digest_state_text(root: Path, text: str) -> None:
    atomic_write_text(daily_digest_rendered_state_path(root), text, final_newline=False)


def append_daily_digest_trace(root: Path, payload: dict[str, Any]) -> None:
    append_jsonl(daily_digest_trace_path(root), payload, sort_keys=True)
