from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_queue_items(text: str) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    parts = re.split(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    if len(parts) < 3:
        return results
    seen: set[str] = set()
    for i in range(1, len(parts), 2):
        body = parts[i + 1]
        qid = "none"
        target = "none"
        status = "pending"
        for line in body.splitlines():
            if line.startswith("- question_id: "):
                qid = line.removeprefix("- question_id: ").strip()
            elif line.startswith("- target: "):
                target = line.removeprefix("- target: ").strip()
            elif line.startswith("- status: "):
                status = line.removeprefix("- status: ").strip()
        if qid == "none" or qid in seen or status in {"answered", "partially_answered", "closed", "dormant"}:
            continue
        seen.add(qid)
        results.append((qid, target or "general"))
    return results


def source_type_for_target(target: str) -> str:
    if target == "human-relationship":
        return "relationship psychology, attachment, boundary, and trust sources"
    if target == "memory-emotion":
        return "cognitive psychology, affective memory, dream, and consolidation sources"
    if target == "ai-self-understanding":
        return "AI architecture, long-term agent memory, tool use, alignment, and safety sources"
    if target == "relationship-meaning":
        return "relationship meaning, attachment, memory, and emotional salience sources"
    return "reliable public reference or institutional sources"


def update_source_gate_state(
    path: Path, checked_at: str, mode: str, items: list[tuple[str, str]]
) -> None:
    candidate_lines = "\n".join(f"- {qid}: {target}" for qid, target in items) or "- none"
    text = f"""---
title: Source Gate State
memory_type: source_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 79
impact_score: 79
confidence_score: 100
status: active
tags: [knowledge, source_gate, state]
---

# Source Gate State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}

## Current Candidates
{candidate_lines}

## Next Step
- Choose source types before any external content is treated as usable material.
- Do not write external conclusions into knowledge/general before real source material exists.
"""
    write_text(path, text)


def update_source_notes(path: Path, checked_at: str, items: list[tuple[str, str]]) -> None:
    lines = [
        f"- {qid}: target={target}; source_type={source_type_for_target(target)}; reliability must be judged before integration."
        for qid, target in items
    ]
    note_lines = "\n".join(lines) if lines else "- no current source-gate candidates"
    if path.exists():
        text = read_text(path).rstrip()
        text = re.sub(r"(?m)^updated_at:\s*.+$", f"updated_at: {checked_at}", text)
        text = re.sub(r"(?m)^last_confirmed_at:\s*.+$", f"last_confirmed_at: {checked_at}", text)
        section = f"## Current Source-Gate Candidates\n{note_lines}"
        if "## Current Source-Gate Candidates" in text:
            text = re.sub(
                r"(?ms)^## Current Source-Gate Candidates\n.*?(?=^## |\Z)",
                section + "\n\n",
                text,
            ).rstrip()
        else:
            text += "\n\n" + section
        write_text(path, text.rstrip() + "\n")
        return

    text = f"""---
title: Source Notes
memory_type: source_notes
time_scope: mid_term
subject_ids: [xinyu]
protected: false
source: system
created_at: 2026-04-22T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 72
impact_score: 58
confidence_score: 76
status: active
tags: [knowledge, sources]
---

# Source Notes

## Purpose
- Track source direction, reliability, and integration boundaries.
- External content must not directly rewrite self or relationship layers.

## Current Source-Gate Candidates
{note_lines}
"""
    write_text(path, text)


def run_source_gate(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_source_gate",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()
    items = extract_queue_items(read_text(root / "memory/context/exploration_queue.md"))

    update_source_gate_state(
        root / "memory/knowledge/source_gate_state.md",
        checked_at,
        mode,
        items,
    )
    update_source_notes(root / "memory/knowledge/source_notes.md", checked_at, items)
    return {
        "checked_at": checked_at,
        "candidate_count": len(items),
        "items": items,
    }
