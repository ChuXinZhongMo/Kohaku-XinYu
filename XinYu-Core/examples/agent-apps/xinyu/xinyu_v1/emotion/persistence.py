"""Persist structured emotion state and compatibility snapshots."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from .models import EMOTION_DIMENSIONS, EmotionState, EmotionVector


def _timestamp_or_now_iso(value: object = None) -> str:
    text = "" if value is None else str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def read_emotion_state(path: Path, *, default_timestamp: str) -> EmotionState:
    if not path.exists():
        return EmotionState.neutral(default_timestamp)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return EmotionState.neutral(default_timestamp)
    vector_raw = data.get("vector") if isinstance(data, dict) else {}
    vector_values = {
        dimension: float(vector_raw.get(dimension, 0.0))
        for dimension in EMOTION_DIMENSIONS
        if isinstance(vector_raw, dict)
    }
    notes_raw = data.get("residue_notes", []) if isinstance(data, dict) else []
    notes = tuple(str(item) for item in notes_raw if str(item).strip()) if isinstance(notes_raw, list) else ()
    return EmotionState(
        vector=EmotionVector(vector_values).normalized(),
        updated_at=str(data.get("updated_at") or default_timestamp),
        inertia=float(data.get("inertia") or 0.72),
        residue_notes=notes,
        version=int(data.get("version") or 1),
    )


def write_emotion_state(path: Path, state: EmotionState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(state.to_json(), ensure_ascii=False, indent=2, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.write("\n")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def write_compat_markdown(path: Path, state: EmotionState) -> None:
    lines = ["# XinYu Emotion State", "", f"- updated_at: {_timestamp_or_now_iso(state.updated_at)}", "- vector:"]
    for dimension in EMOTION_DIMENSIONS:
        lines.append(f"  - {dimension}: {state.vector.get(dimension):.3f}")
    if state.residue_notes:
        lines.extend(["", "## Residue Notes"])
        lines.extend(f"- {note}" for note in state.residue_notes[-12:])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
