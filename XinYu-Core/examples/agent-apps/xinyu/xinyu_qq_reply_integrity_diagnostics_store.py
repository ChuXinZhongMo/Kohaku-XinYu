from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import write_text_atomic


ACK_SPOOL_REL = Path("runtime/gateway_ack_spool.jsonl")
ROUTE_TRACE_REL = Path("runtime/turn_route_trace.jsonl")
WORKING_MEMORY_DIR_REL = Path("runtime/dialogue_working_memory")
STATE_REL = Path("memory/context/qq_reply_integrity_diagnostics_state.md")
REPORT_REL = Path("worklog/xinyu-qq-reply-integrity-diagnostics-latest.md")
TRACE_REL = Path("runtime/qq_reply_integrity_diagnostics_trace.jsonl")


def qq_reply_integrity_ack_spool_path(root: Path | str) -> Path:
    return Path(root).resolve() / ACK_SPOOL_REL


def qq_reply_integrity_route_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / ROUTE_TRACE_REL


def qq_reply_integrity_working_memory_dir(root: Path | str) -> Path:
    return Path(root).resolve() / WORKING_MEMORY_DIR_REL


def qq_reply_integrity_report_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def qq_reply_integrity_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def qq_reply_integrity_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / TRACE_REL


def read_qq_reply_integrity_jsonl_tail(path: Path, *, max_lines: int) -> list[dict[str, Any]]:
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


def read_qq_reply_integrity_working_memory_rows(root: Path | str) -> tuple[list[dict[str, Any]], int]:
    working_dir = qq_reply_integrity_working_memory_dir(root)
    files = list(working_dir.glob("*.jsonl")) if working_dir.exists() else []
    rows: list[dict[str, Any]] = []
    for path in files:
        rows.extend(read_qq_reply_integrity_jsonl_tail(path, max_lines=10_000_000))
    return rows, len(files)


def write_qq_reply_integrity_report_text(
    root: Path | str,
    text: str,
    *,
    output: Path | None = None,
) -> Path:
    path = qq_reply_integrity_report_path(root, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_qq_reply_integrity_state_text(root: Path | str, text: str) -> Path:
    path = qq_reply_integrity_state_path(root)
    write_text_atomic(path, text)
    return path


def append_qq_reply_integrity_trace_event(root: Path | str, row: dict[str, Any]) -> Path:
    path = qq_reply_integrity_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
