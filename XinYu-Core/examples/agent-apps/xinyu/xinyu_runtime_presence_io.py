"""Atomic file IO helpers for runtime presence state.

Keeps scrub-on-write behavior without bloating the presence API module.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from xinyu_runtime_presence_text import scrub_field


def clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): clean_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [clean_json_value(item) for item in value]
    if isinstance(value, str):
        return scrub_field(value)
    return value


def atomic_write_text(path: Path, text: str) -> list[str]:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(scrub_field(text), encoding="utf-8")
        os.replace(tmp, path)
        return []
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return [f"presence_write_failed:{type(exc).__name__}"]


def atomic_write_json(path: Path, data: dict[str, Any]) -> list[str]:
    return atomic_write_text(path, json.dumps(clean_json_value(data), ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, event: dict[str, Any]) -> list[str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        clean_event = clean_json_value(event)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(clean_event, ensure_ascii=False, sort_keys=True) + "\n")
        return []
    except OSError as exc:
        return [f"presence_trace_write_failed:{type(exc).__name__}"]
