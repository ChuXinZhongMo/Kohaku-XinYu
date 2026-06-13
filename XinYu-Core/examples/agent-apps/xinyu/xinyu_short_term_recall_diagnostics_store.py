from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import dialogue_archive_path
from xinyu_prompt_pressure import PROMPT_PRESSURE_REPORT_REL
from xinyu_state_io import write_text_atomic


SHORT_TRACE_REL = Path("runtime/short_term_continuity_trace.jsonl")
WORKING_MEMORY_DIR_REL = Path("runtime/dialogue_working_memory")
STATE_REL = Path("memory/context/short_term_recall_diagnostics_state.md")
REPORT_REL = Path("worklog/xinyu-short-term-recall-diagnostics-latest.md")
TRACE_REL = Path("runtime/short_term_recall_diagnostics_trace.jsonl")


def short_term_recall_short_trace_path(root: Path) -> Path:
    return Path(root).resolve() / SHORT_TRACE_REL


def short_term_recall_prompt_report_path(root: Path) -> Path:
    return Path(root).resolve() / PROMPT_PRESSURE_REPORT_REL


def short_term_recall_working_memory_dir(root: Path) -> Path:
    return Path(root).resolve() / WORKING_MEMORY_DIR_REL


def short_term_recall_report_path(root: Path, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def short_term_recall_state_path(root: Path) -> Path:
    return Path(root).resolve() / STATE_REL


def short_term_recall_trace_path(root: Path) -> Path:
    return Path(root).resolve() / TRACE_REL


def read_short_term_recall_trace_tail(root: Path, *, max_lines: int) -> list[dict[str, Any]]:
    return read_jsonl_tail(short_term_recall_short_trace_path(root), max_lines=max_lines)


def read_short_term_recall_prompt_report(root: Path) -> dict[str, Any]:
    return read_json(short_term_recall_prompt_report_path(root))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


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


def short_term_recall_storage_stats(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    working_dir = short_term_recall_working_memory_dir(root)
    working_files = list(working_dir.glob("*.jsonl")) if working_dir.exists() else []
    working_rows = 0
    for path in working_files:
        try:
            working_rows += sum(
                1
                for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
                if line.strip()
            )
        except OSError:
            continue

    archive_path = dialogue_archive_path(root)
    archive_exists = archive_path.exists()
    archive_messages = 0
    if archive_exists:
        try:
            with sqlite3.connect(archive_path) as conn:
                row = conn.execute("SELECT COUNT(*) FROM dialogue_messages").fetchone()
                archive_messages = int(row[0] if row else 0)
        except sqlite3.Error:
            archive_messages = 0
    return {
        "working_memory_file_count": len(working_files),
        "working_memory_row_count": working_rows,
        "archive_db_exists": archive_exists,
        "archive_message_count": archive_messages,
    }


def write_short_term_recall_report_text(root: Path, text: str, *, output: Path | None = None) -> Path:
    path = short_term_recall_report_path(root, output)
    write_text_atomic(path, text)
    return path


def write_short_term_recall_state_text(root: Path, text: str) -> Path:
    path = short_term_recall_state_path(root)
    write_text_atomic(path, text)
    return path


def append_short_term_recall_trace_event(root: Path, row: dict[str, Any]) -> Path:
    path = short_term_recall_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
