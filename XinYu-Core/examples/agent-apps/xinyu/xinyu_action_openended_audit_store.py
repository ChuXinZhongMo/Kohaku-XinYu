from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RECENT_ACTION_REL = Path("runtime/life_kernel/recent_action_experience.jsonl")
ACTION_RESIDUE_REL = Path("runtime/life_kernel/action_experience_residue.jsonl")
DREAM_SEEDS_REL = Path("memory/dreams/dream_seeds.md")
REFLECTION_QUEUE_REL = Path("memory/reflection/reflection_queue.md")


def read_action_openended_audit_text(path: Path) -> tuple[str, list[str]]:
    if not path.exists():
        return "", [f"missing_input:{path.as_posix()}"]
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace"), []
    except OSError as exc:
        return "", [f"read_error:{path.as_posix()}:{type(exc).__name__}"]


def read_action_openended_audit_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    text, warnings = read_action_openended_audit_text(path)
    rows: list[dict[str, Any]] = []
    invalid = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if isinstance(value, dict):
            rows.append(value)
        else:
            invalid += 1
    if invalid:
        warnings.append(f"invalid_jsonl_lines:{path.as_posix()}:{invalid}")
    return rows, warnings
