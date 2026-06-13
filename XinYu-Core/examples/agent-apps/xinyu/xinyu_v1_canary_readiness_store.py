from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from state_service import atomic_write_text
from state_service import read_text_safe


STATE_REL = Path("memory/context/v1_canary_readiness_state.md")
TRACE_REL = Path("runtime/v1_shadow_trace.jsonl")
OWNER_CONFIG_REL = Path("xinyu_qq_gateway.config.json")


def v1_canary_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def v1_canary_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / TRACE_REL


def v1_owner_config_path(root: Path | str) -> Path:
    return Path(root).resolve() / OWNER_CONFIG_REL


def read_v1_canary_text(path: Path) -> str:
    return read_text_safe(path)


def write_v1_canary_text(path: Path, text: str) -> None:
    atomic_write_text(path, text.rstrip())


def append_v1_canary_trace_event(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_v1_shadow_observation_tail(path: Path, limit: int) -> tuple[list[dict[str, Any]], int]:
    rows: deque[dict[str, Any]] = deque(maxlen=max(1, limit))
    total = 0
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict) or data.get("event_kind") != "v1_shadow_observation":
                    continue
                total += 1
                rows.append(data)
    except OSError:
        return [], 0
    return list(rows), total


def read_v1_owner_config(path: Path) -> tuple[str, Any]:
    try:
        return "ok", json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return "not_found", None
    except Exception:
        return "unreadable", None
