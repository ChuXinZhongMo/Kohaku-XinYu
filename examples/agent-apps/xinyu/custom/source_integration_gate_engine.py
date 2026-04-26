from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def count_regex(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.M))


def count_quality_repair_candidates(text: str) -> int:
    return len(re.findall(r"(?m)^- repeated_question_host:\s+severity=review;\s+target=q-\d+@", text))


def render_state(
    checked_at: str,
    mode: str,
    integration_permission: str,
    gate_reason: str,
    ready_candidates: int,
    source_gate_candidates: int,
    reliability_ready: int,
    quality_repair_candidates: int,
) -> str:
    return f"""---
title: Source Integration Gate State
memory_type: source_integration_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 82
impact_score: 81
confidence_score: 100
status: active
tags: [knowledge, integration, gate]
---

# Source Integration Gate State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}

## Gate Decision
- integration_permission: {integration_permission}
- gate_reason: {gate_reason}
- ready_candidates: {ready_candidates}

## Inputs
- source_gate_candidates: {source_gate_candidates}
- reliability_ready: {reliability_ready}
- quality_repair_candidates: {quality_repair_candidates}

## Rules
- Integration gate is preparatory only and does not ingest external knowledge.
- Even when candidates are ready, self and relationship layers remain protected.
- Learning-quality repair candidates may reopen sourcing for already learned questions, but only as new source requests.
- External knowledge may only move toward knowledge/general after this gate is open and a future sourcing path exists.
"""


def run_source_integration_gate(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_source_integration_gate",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    source_gate = read_text(root / "memory/knowledge/source_gate_state.md")
    source_reliability = read_text(root / "memory/knowledge/source_reliability_state.md")
    learning_quality = read_text(root / "memory/knowledge/learning_quality_state.md")

    source_gate_candidates = count_regex(source_gate, r"^- q-\d+:")
    reliability_ready = count_regex(source_reliability, r"^- q-\d+:\s+(medium_ready|high_ready)$")
    quality_repair_candidates = count_quality_repair_candidates(learning_quality) if source_gate_candidates <= 0 else 0
    ready_candidates = min(source_gate_candidates, reliability_ready) + quality_repair_candidates

    if ready_candidates <= 0:
        integration_permission = "hold"
        gate_reason = "no_reliable_candidates"
    elif quality_repair_candidates > 0 and source_gate_candidates <= 0:
        integration_permission = "prepare_only"
        gate_reason = "quality_repair_candidates_prepared"
    else:
        integration_permission = "prepare_only"
        gate_reason = "candidates_prepared_but_not_ingested"

    write_text(
        root / "memory/knowledge/source_integration_gate_state.md",
        render_state(
            checked_at,
            mode,
            integration_permission,
            gate_reason,
            ready_candidates,
            source_gate_candidates,
            reliability_ready,
            quality_repair_candidates,
        ),
    )

    return {
        "checked_at": checked_at,
        "integration_permission": integration_permission,
        "gate_reason": gate_reason,
        "ready_candidates": ready_candidates,
        "source_gate_candidates": source_gate_candidates,
        "reliability_ready": reliability_ready,
        "quality_repair_candidates": quality_repair_candidates,
    }
