from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from xinyu_state_io import write_text


REPORT_REL = Path("worklog") / "xinyu-stage11-voice-ingress-diagnostics-latest.md"
STATE_REL = Path("memory/context/stage11_voice_ingress_diagnostics_state.md")
TRACE_REL = Path("runtime/stage11_voice_ingress_diagnostics_trace.jsonl")

QQ_TRACE_REL = Path("runtime/qq_inbound_trace.jsonl")
QQ_RICH_TRACE_REL = Path("runtime/qq_rich_context_trace.jsonl")
VOICE_TRACE_RELS = (
    Path("runtime/voice_input_trace.jsonl"),
    Path("runtime/speech_transcript_trace.jsonl"),
    Path("runtime/audio_transcript_trace.jsonl"),
)


def stage11_voice_qq_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / QQ_TRACE_REL


def stage11_voice_qq_rich_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / QQ_RICH_TRACE_REL


def stage11_voice_trace_path_for(root: Path | str, rel: Path) -> Path:
    return Path(root).resolve() / rel


def stage11_voice_report_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def stage11_voice_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def stage11_voice_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / TRACE_REL


def read_stage11_voice_jsonl_tail(path: Path, *, max_lines: int) -> tuple[list[dict[str, Any]], int]:
    if not path.exists():
        return [], 0
    tail: deque[str] = deque(maxlen=max(1, int(max_lines)))
    total = 0
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for total, line in enumerate(handle, start=1):
                tail.append(line)
    except OSError:
        return [], 0
    rows: list[dict[str, Any]] = []
    for line in tail:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows, total


def count_stage11_voice_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for total, _line in enumerate(handle, start=1):
                pass
    except OSError:
        return 0
    return total


def read_stage11_voice_transcript_rows(root: Path | str, *, max_lines: int = 200) -> tuple[list[dict[str, Any]], int, int]:
    root = Path(root).resolve()
    rows: list[dict[str, Any]] = []
    file_count = 0
    line_count = 0
    for rel in VOICE_TRACE_RELS:
        path = root / rel
        if not path.exists():
            continue
        file_count += 1
        line_count += count_stage11_voice_jsonl_lines(path)
        tail_rows, _total = read_stage11_voice_jsonl_tail(path, max_lines=max_lines)
        for row in tail_rows:
            copied = dict(row)
            copied["_trace_rel"] = rel.as_posix()
            rows.append(copied)
    return rows, file_count, line_count


def write_stage11_voice_report_text(root: Path | str, text: str, *, output: Path | None = None) -> Path:
    path = stage11_voice_report_path(root, output)
    write_text(path, text)
    return path


def write_stage11_voice_state_text(root: Path | str, text: str) -> Path:
    path = stage11_voice_state_path(root)
    write_text(path, text)
    return path


def append_stage11_voice_trace_event(root: Path | str, row: dict[str, Any]) -> Path:
    path = stage11_voice_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
