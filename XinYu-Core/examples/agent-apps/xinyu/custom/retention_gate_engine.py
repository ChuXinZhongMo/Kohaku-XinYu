from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def extract_int(text: str, field: str) -> int:
    value = extract_value(text, field, "0")
    try:
        return int(value)
    except ValueError:
        return 0


def render_state(
    checked_at: str,
    mode: str,
    retention_tier: str,
    archive_permission: str,
    gate_reason: str,
    consolidation_priority: str,
    memory_action: str,
    compression_permission: str,
    forget_permission: str,
    reflection_count: int,
    dream_count: int,
    archive_count: int,
) -> str:
    return f"""---
title: Retention Gate State
memory_type: retention_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 84
impact_score: 85
confidence_score: 100
status: active
tags: [retention, gate, archive]
---

# Retention Gate State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}

## Gate Decision
- retention_tier: {retention_tier}
- archive_permission: {archive_permission}
- gate_reason: {gate_reason}

## Inputs
- consolidation_priority: {consolidation_priority}
- long_term_memory_action: {memory_action}
- compression_permission: {compression_permission}
- forget_permission: {forget_permission}
- reflection_queue_items: {reflection_count}
- dream_seed_items: {dream_count}
- archive_queue_items: {archive_count}

## Rules
- High-preserve material may not be compressed while emotional residue is still active.
- Consolidation must settle before archive is allowed to compress.
- Archive permission is a gate, not an instruction to flatten memory immediately.
"""


def run_retention_gate(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_retention_gate",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    consolidation = read_text(root / "memory/reflection/consolidation_state.md")
    long_term_gate_path = root / "memory/archive/long_term_memory_gate_state.md"
    long_term_gate = read_text(long_term_gate_path) if long_term_gate_path.exists() else ""

    consolidation_priority = extract_value(
        consolidation, "consolidation_priority", "idle"
    )
    memory_action = extract_value(long_term_gate, "memory_action", "unknown")
    compression_permission = extract_value(long_term_gate, "compression_permission", "unknown")
    forget_permission = extract_value(long_term_gate, "forget_permission", "unknown")
    reflection_count = extract_int(consolidation, "reflection_queue_items")
    dream_count = extract_int(consolidation, "dream_seed_items")
    archive_count = extract_int(consolidation, "archive_queue_items")

    if archive_count <= 0:
        retention_tier = "none"
        archive_permission = "idle"
        gate_reason = "no_archive_candidates"
    elif memory_action == "preserve_active" or compression_permission == "blocked":
        retention_tier = "high_preserve"
        archive_permission = "hold"
        gate_reason = "long_term_memory_gate_holding"
    elif compression_permission == "allowed" and consolidation_priority == "archive_ready_without_active_residue":
        retention_tier = "medium_preserve"
        archive_permission = "compress_ready"
        gate_reason = "long_term_memory_gate_allows_summary"
    elif consolidation_priority in {
        "reflection_then_dream_then_archive_hold",
        "reflection_before_archive",
        "dream_weight_before_archive",
    }:
        retention_tier = "high_preserve"
        archive_permission = "hold"
        gate_reason = "active_residue_not_settled"
    elif reflection_count == 0 and dream_count == 0:
        retention_tier = "medium_preserve"
        archive_permission = "compress_ready"
        gate_reason = "residue_cleared_for_summary"
    else:
        retention_tier = "medium_preserve"
        archive_permission = "hold"
        gate_reason = "await_clearer_pattern"

    write_text(
        root / "memory/archive/retention_gate_state.md",
        render_state(
            checked_at,
            mode,
            retention_tier,
            archive_permission,
            gate_reason,
            consolidation_priority,
            memory_action,
            compression_permission,
            forget_permission,
            reflection_count,
            dream_count,
            archive_count,
        ),
    )

    return {
        "checked_at": checked_at,
        "retention_tier": retention_tier,
        "archive_permission": archive_permission,
        "gate_reason": gate_reason,
        "consolidation_priority": consolidation_priority,
        "memory_action": memory_action,
        "compression_permission": compression_permission,
        "forget_permission": forget_permission,
        "reflection_count": reflection_count,
        "dream_count": dream_count,
        "archive_count": archive_count,
    }
