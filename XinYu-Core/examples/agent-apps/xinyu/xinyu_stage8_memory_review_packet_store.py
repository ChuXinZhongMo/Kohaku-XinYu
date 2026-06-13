from __future__ import annotations

from pathlib import Path

from xinyu_state_io import write_text_atomic


PACKET_REL = Path("worklog") / "xinyu-stage8-memory-review-packet-latest.md"
STATE_REL = Path("memory/context/stage8_memory_review_packet_state.md")


def stage8_memory_review_packet_path(root: Path, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / PACKET_REL
    if not path.is_absolute():
        path = root / path
    return path


def stage8_memory_review_packet_state_path(root: Path) -> Path:
    return Path(root).resolve() / STATE_REL


def write_stage8_memory_review_packet_text(root: Path, text: str, *, output: Path | None = None) -> Path:
    path = stage8_memory_review_packet_path(root, output)
    write_text_atomic(path, text)
    return path


def write_stage8_memory_review_packet_state_text(root: Path, text: str) -> Path:
    path = stage8_memory_review_packet_state_path(root)
    write_text_atomic(path, text)
    return path
