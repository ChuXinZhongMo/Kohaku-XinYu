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


def find_first_topic(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("- topic: "):
            return line.removeprefix("- topic: ").strip()
        if line.startswith("- theme: "):
            return line.removeprefix("- theme: ").strip()
        if line.startswith("- target: "):
            return line.removeprefix("- target: ").strip()
    return "none"


def update_reprocessing_state(
    path: Path,
    checked_at: str,
    mode: str,
    reflection_count: int,
    dream_count: int,
    archive_count: int,
    top_topic: str,
) -> None:
    text = f"""---
title: 慢处理状态
memory_type: reprocessing_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 82
impact_score: 83
confidence_score: 100
status: active
tags: [reflection, dream, archive, state]
---

# 当前慢处理状态

## 最近一次检查
- checked_at: {checked_at}
- mode: {mode}

## 当前来源概况
- reflection_queue_items: {reflection_count}
- dream_seed_items: {dream_count}
- archive_queue_items: {archive_count}

## 当前优先顺序
- reflection_queue
- dream_seeds
- archive_queue

## 当前最高优先主题
- {top_topic}

## 下一步
- 先判断这个主题是否应该沉入 reflection_log 或 growth_log。
- 如果仍未说透，就继续保留 dream_seeds 的权重。
- 在形成更清晰模式之前，不急着压进 compressed 或 dormant。
"""
    write_text(path, text)


def append_growth_checkpoint(
    path: Path,
    checked_at: str,
    top_topic: str,
    reflection_count: int,
    mode: str,
) -> None:
    text = read_text(path)
    marker = f"## growth-{checked_at[:10]}-reprocess"
    if marker in text:
        return
    addition = (
        f"\n## growth-{checked_at[:10]}-reprocess\n"
        f"- event_window: {checked_at[:10]}\n"
        f"- mode: {mode}\n"
        "- before: 慢处理层已经形成队列，但还需要更稳定的低频维护入口。\n"
        "- after: 可以独立检查 reflection / dream / archive 的优先顺序。\n"
        f"- reason: 当前最高优先主题为“{top_topic}”，反思队列项目数为 {reflection_count}。\n"
        "- confidence: 78\n"
    )
    write_text(path, text + addition)


def run_slow_reprocess(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_slow_reprocess",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    reflection_text = read_text(root / "memory/reflection/reflection_queue.md")
    dream_text = read_text(root / "memory/dreams/dream_seeds.md")
    archive_text = read_text(root / "memory/archive/archive_queue.md")

    reflection_count = count_items(reflection_text, "item-")
    dream_count = count_items(dream_text, "seed-")
    archive_count = count_active_archive_items(archive_text)

    top_topic = find_first_topic(reflection_text)
    if top_topic == "none":
        top_topic = find_first_topic(dream_text)
    if top_topic == "none":
        top_topic = find_first_topic(archive_text)

    update_reprocessing_state(
        root / "memory/reflection/reprocessing_state.md",
        checked_at,
        mode,
        reflection_count,
        dream_count,
        archive_count,
        top_topic,
    )
    append_growth_checkpoint(
        root / "memory/reflection/growth_log.md",
        checked_at,
        top_topic,
        reflection_count,
        mode,
    )

    return {
        "checked_at": checked_at,
        "reflection_count": reflection_count,
        "dream_count": dream_count,
        "archive_count": archive_count,
        "top_topic": top_topic,
    }
