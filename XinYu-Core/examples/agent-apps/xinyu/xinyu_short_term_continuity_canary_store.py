from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import write_text_atomic


SHORT_TRACE_REL = Path("runtime/short_term_continuity_trace.jsonl")
ACK_SPOOL_REL = Path("runtime/gateway_ack_spool.jsonl")
STATE_REL = Path("memory/context/short_term_continuity_canary_state.md")
REPORT_REL = Path("worklog/xinyu-short-term-continuity-canary-latest.md")
TRACE_REL = Path("runtime/short_term_continuity_canary_trace.jsonl")


def short_term_continuity_trace_path(root: Path) -> Path:
    return Path(root).resolve() / SHORT_TRACE_REL


def gateway_ack_spool_path(root: Path) -> Path:
    return Path(root).resolve() / ACK_SPOOL_REL


def short_term_continuity_canary_state_path(root: Path) -> Path:
    return Path(root).resolve() / STATE_REL


def short_term_continuity_canary_report_path(root: Path, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def short_term_continuity_canary_trace_path(root: Path) -> Path:
    return Path(root).resolve() / TRACE_REL


def read_short_term_continuity_jsonl_tail(root: Path, *, max_lines: int) -> list[dict[str, Any]]:
    return read_jsonl_tail(short_term_continuity_trace_path(root), max_lines=max_lines)


def read_gateway_ack_spool_jsonl_tail(root: Path, *, max_lines: int) -> list[dict[str, Any]]:
    return read_jsonl_tail(gateway_ack_spool_path(root), max_lines=max_lines)


def read_jsonl_tail(path: Path, *, max_lines: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max(1, int(max_lines)) :]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def write_short_term_continuity_canary_report_text(root: Path, text: str, *, output: Path | None = None) -> Path:
    path = short_term_continuity_canary_report_path(root, output)
    write_text_atomic(path, text)
    return path


def write_short_term_continuity_canary_state_text(root: Path, text: str) -> Path:
    path = short_term_continuity_canary_state_path(root)
    write_text_atomic(path, text)
    return path


def append_short_term_continuity_canary_trace_event(root: Path, row: dict[str, Any]) -> Path:
    path = short_term_continuity_canary_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
