from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


TERMINAL_STATUSES = {"compressed", "committed", "archived", "dormant"}
HIGH_PRESERVE_MARKERS = [
    "owner",
    "最高特殊",
    "能力",
    "刺痛",
    "委屈",
    "失望",
    "疏远",
    "负面",
    "回到身边",
    "残留",
    "关系波动",
    "被记住",
    "认得",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def count_items(text: str, prefix: str) -> int:
    return len(re.findall(rf"(?m)^## {re.escape(prefix)}", text))


def extract_value(text: str, field: str, default: str = "none") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def extract_int(text: str, field: str) -> int:
    try:
        return int(extract_value(text, field, "0"))
    except ValueError:
        return 0


def extract_archive_items(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    items: list[dict[str, str]] = []
    for index in range(1, len(parts), 2):
        item_id = parts[index].strip()
        body = parts[index + 1]
        item = {
            "item_id": item_id,
            "target": "none",
            "status": "hold",
            "reason": "none",
        }
        for line in body.splitlines():
            stripped = line.strip()
            for key in ["target", "status", "reason"]:
                prefix = f"- {key}: "
                if stripped.startswith(prefix):
                    item[key] = stripped.removeprefix(prefix).strip()
        items.append(item)
    return items


def item_is_high_preserve(item: dict[str, str]) -> bool:
    combined = f"{item.get('target', '')} {item.get('reason', '')}"
    return any(marker in combined for marker in HIGH_PRESERVE_MARKERS)


def dream_weight_is_active(weight_text: str) -> bool:
    effect = extract_value(weight_text, "weight_effect", "none")
    if effect in {"none", "no_seed", "already_logged_today_no_repeat"}:
        return False
    return extract_int(weight_text, "weight_delta") > 0


def classify_gate(
    *,
    active_archive_items: int,
    ready_archive_items: int,
    high_preserve_items: int,
    reflection_queue_items: int,
    dream_weight_active: bool,
    growth_entries: int,
) -> tuple[str, str, str, str, str, str]:
    if active_archive_items <= 0:
        return (
            "idle",
            "none",
            "allow_fade_for_unpromoted_low_impact_only",
            "none",
            "none",
            "no_active_archive_candidates",
        )

    if reflection_queue_items > 0 or dream_weight_active:
        return (
            "preserve_active",
            "high_preserve",
            "blocked_active_residue",
            "blocked",
            "blocked",
            "active_reflection_or_dream_residue",
        )

    if high_preserve_items > 0:
        return (
            "hold_high_preserve_relationship",
            "high_preserve",
            "blocked_relationship_residue",
            "blocked",
            "blocked",
            "high_preserve_relationship_target",
        )

    if ready_archive_items > 0 and growth_entries > 0:
        return (
            "compress_to_long_term_summary",
            "medium_preserve",
            "blocked_compress_instead",
            "allowed",
            "allowed_after_compression",
            "ready_items_can_be_summarized_not_deleted",
        )

    if ready_archive_items > 0:
        return (
            "compress_to_long_term_summary",
            "medium_preserve",
            "blocked_compress_instead",
            "allowed",
            "allowed_after_compression",
            "ready_items_without_active_residue",
        )

    return (
        "hold_for_more_evidence",
        "medium_preserve",
        "blocked_pending_pattern",
        "blocked",
        "blocked",
        "queue_items_not_ready",
    )


def render_state(
    checked_at: str,
    mode: str,
    memory_action: str,
    retention_tier: str,
    forget_permission: str,
    compression_permission: str,
    dormant_permission: str,
    gate_reason: str,
    active_archive_items: int,
    ready_archive_items: int,
    high_preserve_items: int,
    reflection_queue_items: int,
    dream_weight_active: bool,
    dream_weight_delta: int,
    growth_entries: int,
    compressed_items: int,
    dormant_items: int,
    active_targets: list[str],
) -> str:
    targets = "\n".join(f"- {target}" for target in active_targets[:8]) or "- none"
    return f"""---
title: 长期记忆门控状态
memory_type: long_term_memory_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-25T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 86
impact_score: 86
confidence_score: 100
status: active
tags: [memory, retention, forgetting, gate]
---

# 长期记忆门控状态

## 最近一次评估
- checked_at: {checked_at}
- mode: {mode}

## 当前决策
- memory_action: {memory_action}
- retention_tier: {retention_tier}
- forget_permission: {forget_permission}
- compression_permission: {compression_permission}
- dormant_permission: {dormant_permission}
- gate_reason: {gate_reason}

## 输入摘要
- active_archive_items: {active_archive_items}
- ready_archive_items: {ready_archive_items}
- high_preserve_items: {high_preserve_items}
- reflection_queue_items: {reflection_queue_items}
- dream_weight_active: {str(dream_weight_active).lower()}
- dream_weight_delta: {dream_weight_delta}
- growth_entries: {growth_entries}
- compressed_items: {compressed_items}
- dormant_items: {dormant_items}

## 当前活跃目标
{targets}

## 规则
- 高情绪、高关系、高自我叙事材料不得直接遗忘。
- 活跃残留只能保留或等待，不能压平。
- 可遗忘首先表现为不写入长期记忆，其次是沉睡；不做破坏性删除。
- 梦境只能影响残留权重，不能把梦内片段归档成现实事实。
"""


def run_long_term_memory_gate(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_long_term_memory_gate",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    archive_queue = read_text(root / "memory/archive/archive_queue.md")
    reflection_queue = read_text(root / "memory/reflection/reflection_queue.md")
    dream_weight = read_text(root / "memory/dreams/dream_weight_state.md")
    growth_log = read_text(root / "memory/reflection/growth_log.md")
    compressed = read_text(root / "memory/archive/compressed.md")
    dormant = read_text(root / "memory/archive/dormant.md")

    archive_items = extract_archive_items(archive_queue)
    active_items = [item for item in archive_items if item["status"] not in TERMINAL_STATUSES]
    ready_items = [item for item in active_items if item["status"] != "hold"]
    high_preserve_items = [item for item in active_items if item_is_high_preserve(item)]
    active_archive_items = len(active_items)
    ready_archive_items = len(ready_items)
    high_preserve_item_count = len(high_preserve_items)
    reflection_queue_items = count_items(reflection_queue, "item-")
    dream_weight_delta = extract_int(dream_weight, "weight_delta")
    dream_weight_active = dream_weight_is_active(dream_weight)
    growth_entries = count_items(growth_log, "growth-")
    compressed_items = count_items(compressed, "compressed-")
    dormant_items = count_items(dormant, "dormant-")

    (
        memory_action,
        retention_tier,
        forget_permission,
        compression_permission,
        dormant_permission,
        gate_reason,
    ) = classify_gate(
        active_archive_items=active_archive_items,
        ready_archive_items=ready_archive_items,
        high_preserve_items=high_preserve_item_count,
        reflection_queue_items=reflection_queue_items,
        dream_weight_active=dream_weight_active,
        growth_entries=growth_entries,
    )

    active_targets = [item["target"] for item in active_items]
    write_text(
        root / "memory/archive/long_term_memory_gate_state.md",
        render_state(
            checked_at,
            mode,
            memory_action,
            retention_tier,
            forget_permission,
            compression_permission,
            dormant_permission,
            gate_reason,
            active_archive_items,
            ready_archive_items,
            high_preserve_item_count,
            reflection_queue_items,
            dream_weight_active,
            dream_weight_delta,
            growth_entries,
            compressed_items,
            dormant_items,
            active_targets,
        ),
    )

    return {
        "checked_at": checked_at,
        "memory_action": memory_action,
        "retention_tier": retention_tier,
        "forget_permission": forget_permission,
        "compression_permission": compression_permission,
        "dormant_permission": dormant_permission,
        "gate_reason": gate_reason,
        "active_archive_items": active_archive_items,
        "ready_archive_items": ready_archive_items,
        "high_preserve_items": high_preserve_item_count,
        "reflection_queue_items": reflection_queue_items,
        "dream_weight_active": dream_weight_active,
        "dream_weight_delta": dream_weight_delta,
        "growth_entries": growth_entries,
    }
