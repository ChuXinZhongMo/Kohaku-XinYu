from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from xinyu_state_io import write_text


REPORT_REL = Path("worklog") / "xinyu-stage11-visual-ingress-diagnostics-latest.md"
STATE_REL = Path("memory/context/stage11_visual_ingress_diagnostics_state.md")
TRACE_REL = Path("runtime/stage11_visual_ingress_diagnostics_trace.jsonl")

QQ_TRACE_REL = Path("runtime/qq_inbound_trace.jsonl")
QQ_RICH_TRACE_REL = Path("runtime/qq_rich_context_trace.jsonl")
OCR_TRACE_REL = Path("runtime/learning_ocr_trace.jsonl")


def stage11_visual_qq_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / QQ_TRACE_REL


def stage11_visual_qq_rich_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / QQ_RICH_TRACE_REL


def stage11_visual_ocr_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / OCR_TRACE_REL


def stage11_visual_report_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def stage11_visual_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def stage11_visual_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / TRACE_REL


def read_stage11_visual_jsonl_tail(path: Path, *, max_lines: int) -> tuple[list[dict[str, Any]], int]:
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


def count_stage11_visual_jsonl_lines(path: Path) -> int:
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


def write_stage11_visual_report_text(root: Path | str, text: str, *, output: Path | None = None) -> Path:
    path = stage11_visual_report_path(root, output)
    write_text(path, text)
    return path


def write_stage11_visual_state_text(root: Path | str, text: str) -> Path:
    path = stage11_visual_state_path(root)
    write_text(path, text)
    return path


def append_stage11_visual_trace_event(root: Path | str, row: dict[str, Any]) -> Path:
    path = stage11_visual_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
