from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import write_text_atomic


STATE_REL = Path("memory/context/decision_chain_latest_state.md")
TRACE_REL = Path("runtime/decision_chain_latest_trace.jsonl")
REPORT_REL = Path("worklog/xinyu-decision-chain-latest.md")


def decision_chain_latest_report_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def decision_chain_latest_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def decision_chain_latest_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / TRACE_REL


def write_decision_chain_latest_report_text(
    root: Path | str,
    text: str,
    *,
    output: Path | None = None,
) -> Path:
    path = decision_chain_latest_report_path(root, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_decision_chain_latest_state_text(root: Path | str, text: str) -> Path:
    path = decision_chain_latest_state_path(root)
    write_text_atomic(path, text)
    return path


def append_decision_chain_latest_trace_event(root: Path | str, row: dict[str, Any]) -> Path:
    path = decision_chain_latest_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
