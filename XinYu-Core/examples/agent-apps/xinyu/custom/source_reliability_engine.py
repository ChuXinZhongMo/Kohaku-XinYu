from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from xinyu_storage_paths import knowledge_file_path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def extract_candidates(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    pattern = re.compile(r"^- (q-\d+):\s*(.+)$", re.M)
    for match in pattern.finditer(text):
        pairs.append((match.group(1), match.group(2).strip()))
    return pairs


def classify_target(target: str) -> str:
    if target == "ai-self-understanding":
        return "high_ready"
    if target in {"human-relationship", "memory-emotion"}:
        return "medium_ready"
    return "unknown"


def render_state(
    checked_at: str, mode: str, pairs: list[tuple[str, str, str]]
) -> str:
    snapshot = (
        "\n".join(f"- {qid}: {level}" for qid, _, level in pairs)
        if pairs
        else "- none"
    )
    rationale = (
        "\n".join(f"- {qid}: {target} -> {level}" for qid, target, level in pairs)
        if pairs
        else "- no source candidates"
    )
    return f"""---
title: Source Reliability State
memory_type: source_reliability_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 81
impact_score: 80
confidence_score: 100
status: active
tags: [knowledge, source, reliability]
---

# Source Reliability State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}

## Reliability Snapshot
{snapshot}

## Notes
{rationale}

## Rules
- Reliability classification is preparatory, not evidence ingestion.
- Relationship, memory-emotion, and AI self-understanding topics may proceed to future sourcing, but may not rewrite self or relationship layers directly.
"""


def run_source_reliability(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_source_reliability",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()
    source_gate = read_text(_knowledge(root, "source_gate_state.md"))
    candidates = extract_candidates(source_gate)
    pairs = [(qid, target, classify_target(target)) for qid, target in candidates]

    write_text(
        _knowledge(root, "source_reliability_state.md"),
        render_state(checked_at, mode, pairs),
    )
    return {
        "checked_at": checked_at,
        "candidate_count": len(pairs),
        "pairs": pairs,
    }
