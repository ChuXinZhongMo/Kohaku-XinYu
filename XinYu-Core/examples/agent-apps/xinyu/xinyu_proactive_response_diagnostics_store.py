from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import read_text
from xinyu_state_io import write_text_atomic


STATE_REL = Path("memory/context/proactive_response_diagnostics_state.md")
TRACE_REL = Path("runtime/proactive_response_diagnostics_trace.jsonl")
REPORT_REL = Path("worklog/xinyu-proactive-response-diagnostics-latest.md")

PROACTIVE_REQUEST_STATE_REL = Path("memory/context/proactive_request_state.md")
PROACTIVE_DISPATCH_STATE_REL = Path("memory/context/proactive_qq_dispatch_state.md")


def proactive_response_diagnostics_state_path(root: Path) -> Path:
    return Path(root).resolve() / STATE_REL


def proactive_response_diagnostics_trace_path(root: Path) -> Path:
    return Path(root).resolve() / TRACE_REL


def proactive_response_diagnostics_report_path(root: Path, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def proactive_request_state_path(root: Path) -> Path:
    return Path(root).resolve() / PROACTIVE_REQUEST_STATE_REL


def proactive_dispatch_state_path(root: Path) -> Path:
    return Path(root).resolve() / PROACTIVE_DISPATCH_STATE_REL


def read_proactive_request_state_text(root: Path) -> str:
    return read_text(proactive_request_state_path(root))


def read_proactive_dispatch_state_text(root: Path) -> str:
    return read_text(proactive_dispatch_state_path(root))


def write_proactive_response_diagnostics_report_text(
    root: Path,
    text: str,
    *,
    output: Path | None = None,
) -> Path:
    path = proactive_response_diagnostics_report_path(root, output)
    write_text_atomic(path, text)
    return path


def write_proactive_response_diagnostics_state_text(root: Path, text: str) -> Path:
    path = proactive_response_diagnostics_state_path(root)
    write_text_atomic(path, text)
    return path


def append_proactive_response_diagnostics_trace_event(root: Path, row: dict[str, Any]) -> Path:
    path = proactive_response_diagnostics_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
