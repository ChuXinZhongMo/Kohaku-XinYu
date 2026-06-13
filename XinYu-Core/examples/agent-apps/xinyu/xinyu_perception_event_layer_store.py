from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import read_text
from xinyu_state_io import write_text_atomic


STATE_REL = Path("memory/context/perception_event_layer_state.md")
TRACE_REL = Path("runtime/perception_event_layer_trace.jsonl")
REPORT_REL = Path("worklog/xinyu-perception-event-layer-latest.md")

QQ_TRACE_REL = Path("runtime/qq_inbound_trace.jsonl")
QQ_ACK_REL = Path("runtime/gateway_ack_spool.jsonl")
PROACTIVE_REQUEST_STATE_REL = Path("memory/context/proactive_request_state.md")
OCR_TRACE_REL = Path("runtime/learning_ocr_trace.jsonl")
VOICE_TRACE_RELS = (
    Path("runtime/voice_input_trace.jsonl"),
    Path("runtime/speech_transcript_trace.jsonl"),
    Path("runtime/audio_transcript_trace.jsonl"),
)


def perception_event_layer_report_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def perception_event_layer_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def perception_event_layer_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / TRACE_REL


def perception_event_layer_qq_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / QQ_TRACE_REL


def perception_event_layer_ack_spool_path(root: Path | str) -> Path:
    return Path(root).resolve() / QQ_ACK_REL


def perception_event_layer_proactive_request_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / PROACTIVE_REQUEST_STATE_REL


def perception_event_layer_ocr_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / OCR_TRACE_REL


def perception_event_layer_voice_trace_path(root: Path | str, rel: Path) -> Path:
    return Path(root).resolve() / rel


def read_perception_event_layer_state_text(root: Path | str) -> str:
    return read_text(perception_event_layer_state_path(root))


def read_perception_event_layer_proactive_request_state_text(root: Path | str) -> str:
    return read_text(perception_event_layer_proactive_request_state_path(root))


def read_perception_event_layer_jsonl_tail(path: Path, max_lines: int = 500) -> list[dict[str, Any]]:
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


def write_perception_event_layer_report_text(
    root: Path | str,
    text: str,
    *,
    output: Path | None = None,
) -> Path:
    path = perception_event_layer_report_path(root, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_perception_event_layer_state_text(root: Path | str, text: str) -> Path:
    path = perception_event_layer_state_path(root)
    write_text_atomic(path, text)
    return path


def append_perception_event_layer_trace_event(root: Path | str, row: dict[str, Any]) -> Path:
    path = perception_event_layer_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
