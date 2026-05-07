from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def count_items(text: str, prefix: str) -> int:
    return len(re.findall(rf"(?m)^## {re.escape(prefix)}", text))


def count_active_archive_items(text: str) -> int:
    terminal_statuses = {"compressed", "committed", "archived", "dormant"}
    parts = re.split(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    if len(parts) < 3:
        return 0
    active = 0
    for i in range(1, len(parts), 2):
        body = parts[i + 1]
        status = "hold"
        for line in body.splitlines():
            if line.startswith("- status: "):
                status = line.removeprefix("- status: ").strip()
                break
        if status not in terminal_statuses:
            active += 1
    return active


def first_match(text: str, prefixes: list[str]) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        for prefix in prefixes:
            marker = f"- {prefix}: "
            if stripped.startswith(marker):
                return stripped.removeprefix(marker).strip()
    return "none"


def extract_value(text: str, field: str, default: str = "none") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def extract_int(text: str, field: str) -> int:
    try:
        return int(extract_value(text, field, "0"))
    except ValueError:
        return 0


def dream_weight_is_active(weight_text: str) -> bool:
    effect = extract_value(weight_text, "weight_effect", "none")
    if effect in {"none", "no_seed", "already_logged_today_no_repeat"}:
        return False
    return extract_int(weight_text, "weight_delta") > 0


def render_state(
    checked_at: str,
    mode: str,
    reflection_count: int,
    dream_count: int,
    dream_weight_delta: int,
    dream_weight_effect: str,
    dream_weight_active: bool,
    archive_count: int,
    coordination: str,
    archive_action: str,
    top_topic: str,
) -> str:
    return f"""---
title: Consolidation State
memory_type: consolidation_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 83
impact_score: 84
confidence_score: 100
status: active
tags: [consolidation, dream, reflection, archive]
---

# Consolidation State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}

## Current Counts
- reflection_queue_items: {reflection_count}
- dream_seed_items: {dream_count}
- dream_weight_active: {str(dream_weight_active).lower()}
- dream_weight_delta: {dream_weight_delta}
- dream_weight_effect: {dream_weight_effect}
- archive_queue_items: {archive_count}

## Coordination Decision
- top_topic: {top_topic}
- consolidation_priority: {coordination}
- archive_action: {archive_action}

## Rules
- Reflection should interpret meaning before archive compresses it.
- Dream seeds may increase weight, but may not overwrite facts.
- Active dream weight should delay archive flattening even after the seed has been promoted.
- Archive remains conservative while a pattern is still emotionally active.
- When reflection and dream are both active, archive should prefer holding over flattening.
"""


def run_consolidation(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_consolidation",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    reflection_text = read_text(root / "memory/reflection/reflection_queue.md")
    dream_text = read_text(root / "memory/dreams/dream_seeds.md")
    dream_weight_text = read_text(root / "memory/dreams/dream_weight_state.md")
    archive_text = read_text(root / "memory/archive/archive_queue.md")
    archive_output_text = read_text(root / "memory/archive/archive_output_state.md")

    reflection_count = count_items(reflection_text, "item-")
    dream_count = count_items(dream_text, "seed-")
    dream_weight_delta = extract_int(dream_weight_text, "weight_delta")
    dream_weight_effect = extract_value(dream_weight_text, "weight_effect", "none")
    dream_weight_active = dream_weight_is_active(dream_weight_text)
    archive_count = count_active_archive_items(archive_text)

    top_topic = first_match(reflection_text, ["topic", "theme", "target"])
    if top_topic == "none":
        top_topic = first_match(dream_text, ["theme", "residue"])

    archive_action = first_match(archive_output_text, ["next_action"])

    dream_active = dream_count > 0 or dream_weight_active

    if reflection_count > 0 and dream_active:
        coordination = "reflection_then_dream_then_archive_hold"
    elif reflection_count > 0:
        coordination = "reflection_before_archive"
    elif dream_active:
        coordination = "dream_weight_before_archive"
    elif archive_count > 0:
        coordination = "archive_ready_without_active_residue"
    else:
        coordination = "idle"

    write_text(
        root / "memory/reflection/consolidation_state.md",
        render_state(
            checked_at,
            mode,
            reflection_count,
            dream_count,
            dream_weight_delta,
            dream_weight_effect,
            dream_weight_active,
            archive_count,
            coordination,
            archive_action,
            top_topic,
        ),
    )

    return {
        "checked_at": checked_at,
        "reflection_count": reflection_count,
        "dream_count": dream_count,
        "dream_weight_delta": dream_weight_delta,
        "dream_weight_effect": dream_weight_effect,
        "dream_weight_active": dream_weight_active,
        "archive_count": archive_count,
        "coordination": coordination,
        "archive_action": archive_action,
        "top_topic": top_topic,
    }
