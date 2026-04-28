from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _split_dormant_items(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^## (dormant-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    items: list[dict[str, str]] = []
    for index in range(1, len(parts), 2):
        item_id = parts[index].strip()
        body = parts[index + 1]
        item = {
            "item_id": item_id,
            "summary": "none",
            "wake_conditions": "none",
            "subjects": "[]",
            "last_accessed_at": "unknown",
        }
        for line in body.splitlines():
            stripped = line.strip()
            for key in ["summary", "wake_conditions", "subjects", "last_accessed_at"]:
                prefix = f"- {key}: "
                if stripped.startswith(prefix):
                    item[key] = stripped.removeprefix(prefix).strip()
        items.append(item)
    return items


def _tokens(text: str) -> set[str]:
    clean = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text.lower())
    tokens = {part for part in clean.split() if len(part) >= 2}
    for phrase in [
        "整理",
        "文件",
        "桌面",
        "普通",
        "低权重",
        "工具",
        "刺痛",
        "owner",
        "回到身边",
        "残留",
        "靠近",
    ]:
        if phrase in text:
            tokens.add(phrase)
    return tokens


def _score(query: str, item: dict[str, str]) -> int:
    query_tokens = _tokens(query)
    item_tokens = _tokens(f"{item['summary']} {item['wake_conditions']} {item['subjects']}")
    overlap = len(query_tokens & item_tokens)
    if item["summary"] != "none" and item["summary"] in query:
        overlap += 3
    return overlap


def render_state(
    checked_at: str,
    mode: str,
    query: str,
    matched: list[dict[str, str]],
    decision: str,
) -> str:
    if matched:
        matched_block = "\n".join(
            (
                f"- item_id: {item['item_id']}\n"
                f"  summary: {item['summary']}\n"
                f"  subjects: {item['subjects']}\n"
                "  boundary: dormant summary only; not new factual memory"
            )
            for item in matched[:5]
        )
    else:
        matched_block = "- none"
    return f"""---
title: Dormant Reactivation State
memory_type: dormant_reactivation_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-26T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 78
impact_score: 76
confidence_score: 94
status: active
tags: [archive, dormant, reactivation]
---

# Dormant Reactivation State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}
- query: {query}
- decision: {decision}

## Matched Dormant Items
{matched_block}

## Rules
- Dormant reactivation surfaces compressed summaries only.
- Reactivation is not proof of new facts.
- Reactivation must not rewrite self, owner, relationship, emotion, or knowledge memory directly.
- High-preserve owner relationship residue should not be displaced by ordinary dormant material.
"""


def run_dormant_reactivation(
    root: Path,
    query: str,
    checked_at: str | None = None,
    mode: str = "runtime_dormant_reactivation",
    min_score: int = 1,
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()
    dormant_text = read_text(root / "memory/archive/dormant.md")
    items = _split_dormant_items(dormant_text)
    scored = [(item, _score(query, item)) for item in items]
    matched = [item for item, score in scored if score >= min_score]
    matched.sort(key=lambda item: _score(query, item), reverse=True)
    decision = "reactivate_summary" if matched else "no_match"

    write_text(
        root / "memory/archive/dormant_reactivation_state.md",
        render_state(checked_at, mode, query, matched, decision),
    )
    return {
        "checked_at": checked_at,
        "decision": decision,
        "matched_items": len(matched),
        "matched_item_ids": [item["item_id"] for item in matched[:5]],
        "query": query,
    }
