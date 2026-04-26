from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

TERMINAL_STATUSES = {"compressed", "committed", "archived", "dormant"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_archive_items(text: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    parts = re.split(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    if len(parts) < 3:
        return results
    for i in range(1, len(parts), 2):
        item_id = parts[i]
        body = parts[i + 1]
        item = {
            "item_id": item_id,
            "target": "none",
            "status": "hold",
            "reason": "none",
        }
        for line in body.splitlines():
            if line.startswith("- target: "):
                item["target"] = line.removeprefix("- target: ").strip()
            elif line.startswith("- status: "):
                item["status"] = line.removeprefix("- status: ").strip()
            elif line.startswith("- reason: "):
                item["reason"] = line.removeprefix("- reason: ").strip()
        results.append(item)
    return results


def count_items(text: str, prefix: str) -> int:
    return len(re.findall(rf"(?m)^## {re.escape(prefix)}", text))


def _render_state(
    checked_at: str,
    mode: str,
    queue_count: int,
    active_queue_count: int,
    committed_queue_count: int,
    compressed_count: int,
    dormant_count: int,
    next_action: str,
    conservative_reason: str,
) -> str:
    return f"""---
title: Archive Output State
memory_type: archive_output_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 81
impact_score: 82
confidence_score: 100
status: active
tags: [archive, output, state]
---

# Archive Output State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}

## Current Counts
- archive_queue_items: {queue_count}
- active_archive_queue_items: {active_queue_count}
- committed_archive_queue_items: {committed_queue_count}
- compressed_items: {compressed_count}
- dormant_items: {dormant_count}

## Current Decision
- next_action: {next_action}
- conservative_reason: {conservative_reason}

## Rules
- Archive output is low-frequency and conservative.
- Do not compress relationship-shaping material too early.
- Do not move anything into dormant state while the pattern is still actively forming.
- Prefer summarizing readiness before altering memory layers.
"""


def _read_gate(retention_gate_text: str) -> tuple[str, str]:
    archive_permission = "idle"
    gate_reason = "unknown_gate_reason"
    for line in retention_gate_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- archive_permission:"):
            archive_permission = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- gate_reason:"):
            gate_reason = stripped.split(":", 1)[1].strip()
    return archive_permission, gate_reason


def run_archive_output(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_archive_output",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    queue_text = read_text(root / "memory/archive/archive_queue.md")
    compressed_text = read_text(root / "memory/archive/compressed.md")
    dormant_text = read_text(root / "memory/archive/dormant.md")
    retention_gate_text = read_text(root / "memory/archive/retention_gate_state.md")

    queue_items = extract_archive_items(queue_text)
    active_items = [item for item in queue_items if item["status"] not in TERMINAL_STATUSES]
    committed_items = [item for item in queue_items if item["status"] in TERMINAL_STATUSES]
    queue_count = len(queue_items)
    active_queue_count = len(active_items)
    committed_queue_count = len(committed_items)
    compressed_count = count_items(compressed_text, "compressed-")
    dormant_count = count_items(dormant_text, "dormant-")
    archive_permission, gate_reason = _read_gate(retention_gate_text)

    if not active_items:
        next_action = "idle"
        conservative_reason = "no_active_archive_candidates"
    elif archive_permission != "compress_ready":
        next_action = "keep_holding"
        conservative_reason = gate_reason
    elif any(item["status"] == "hold" for item in active_items):
        next_action = "keep_holding"
        conservative_reason = "queue_item_still_marked_hold"
    else:
        next_action = "summarize_then_compress"
        conservative_reason = gate_reason

    write_text(
        root / "memory/archive/archive_output_state.md",
        _render_state(
            checked_at,
            mode,
            queue_count,
            active_queue_count,
            committed_queue_count,
            compressed_count,
            dormant_count,
            next_action,
            conservative_reason,
        ),
    )

    return {
        "checked_at": checked_at,
        "queue_count": queue_count,
        "active_queue_count": active_queue_count,
        "committed_queue_count": committed_queue_count,
        "compressed_count": compressed_count,
        "dormant_count": dormant_count,
        "next_action": next_action,
        "conservative_reason": conservative_reason,
    }
