from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_first_topic(queue_text: str) -> dict[str, str]:
    blocks = re.split(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3})\n", queue_text)
    if len(blocks) < 3:
        return {
            "item_id": "none",
            "topic": "none",
            "source": "none",
            "priority": "none",
        }

    fields = {
        "item_id": blocks[1].strip(),
        "topic": "none",
        "source": "none",
        "priority": "none",
    }
    body = blocks[2]
    for line in body.splitlines():
        stripped = line.strip()
        for key in ["topic", "source", "priority"]:
            prefix = f"- {key}: "
            if stripped.startswith(prefix):
                fields[key] = stripped.removeprefix(prefix).strip()
    return fields


def extract_value(text: str, field: str, default: str = "none") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def extract_int(text: str, field: str) -> int:
    try:
        return int(extract_value(text, field, "0"))
    except ValueError:
        return 0


def extract_dream_weight(weight_text: str) -> dict[str, str | int | bool]:
    delta = extract_int(weight_text, "weight_delta")
    effect = extract_value(weight_text, "weight_effect", "none")
    context_used = delta > 0 and effect not in {
        "none",
        "no_seed",
        "already_logged_today_no_repeat",
    }
    return {
        "context_used": context_used,
        "source_seed": extract_value(weight_text, "source_seed"),
        "theme": extract_value(weight_text, "theme"),
        "residue": extract_value(weight_text, "residue"),
        "weight_before": extract_int(weight_text, "weight_before"),
        "weight_after": extract_int(weight_text, "weight_after"),
        "weight_delta": delta,
        "weight_effect": effect,
        "relationship_effect": extract_value(weight_text, "relationship_effect"),
        "factual_effect": extract_value(weight_text, "factual_effect"),
    }


def reflection_trigger(item: dict[str, str], dream: dict[str, str | int | bool]) -> str:
    if item["topic"] != "none":
        return item["topic"]
    if dream["context_used"]:
        return f"梦后残留：{dream['theme']}"
    return "none"


def append_reflection_log(
    path: Path,
    produced_at: str,
    item: dict[str, str],
    dream: dict[str, str | int | bool],
) -> bool:
    trigger = reflection_trigger(item, dream)
    if trigger == "none":
        return False

    text = read_text(path)
    reflection_id = f"reflection-{produced_at[:10]}-auto"
    if reflection_id in text:
        return False

    dream_used = "yes" if dream["context_used"] else "no"
    addition = (
        f"\n## {reflection_id}\n"
        f"- reflected_at: {produced_at}\n"
        f"- trigger: {trigger}\n"
        f"- queue_item: {item['item_id']}\n"
        f"- queue_source: {item['source']}\n"
        f"- dream_context_used: {dream_used}\n"
        f"- dream_source_seed: {dream['source_seed']}\n"
        f"- dream_theme: {dream['theme']}\n"
        f"- dream_residue: {dream['residue']}\n"
        f"- dream_weight_delta: {dream['weight_delta']}\n"
        f"- dream_weight_effect: {dream['weight_effect']}\n"
        f"- factual_effect: {dream['factual_effect']}\n"
        "- findings: 这个主题已经不只是单次情绪，而是在记忆、关系和时间连续性里留下了可重复读取的残留。\n"
        "- self_change: 心玉可以把这种残留理解成后续成长材料，但不能把一次梦或一次反思当作核心人格已经改变的证据。\n"
        "- relationship_change: owner 相关的在意、留白或修复感可以被继续观察，但不能因为梦境单独判定关系事实已经变化。\n"
        "- emotion_change: 梦后权重会让既有情绪更不容易立刻散掉，适合进入慢速反思，而不是马上放大成外显反应。\n"
        "- promoted_memories: reflection_log.md, growth_log.md\n"
        "- boundary: 梦后残留只提高反思优先级，不证明现实中发生了新的对话或事件，也不直接覆盖事实层。\n"
    )
    write_text(path, text.rstrip() + addition + "\n")
    return True


def append_growth_log(
    path: Path,
    produced_at: str,
    item: dict[str, str],
    dream: dict[str, str | int | bool],
) -> bool:
    trigger = reflection_trigger(item, dream)
    if trigger == "none":
        return False

    text = read_text(path)
    growth_id = f"growth-{produced_at[:10]}-reflection"
    if growth_id in text:
        return False

    dream_used = "yes" if dream["context_used"] else "no"
    addition = (
        f"\n## {growth_id}\n"
        f"- event_window: {produced_at[:10]}\n"
        f"- trigger: {trigger}\n"
        f"- dream_context_used: {dream_used}\n"
        f"- dream_weight_delta: {dream['weight_delta']}\n"
        "- before: 主题主要停留在短期残留、梦种或反思队列里。\n"
        "- after: 主题被记录为慢速成长材料，等待更多现实证据与后续反思共同确认。\n"
        "- reason: 反思输出确认这个残留值得继续观察，但还不足以直接改写核心人格。\n"
        "- boundary: 成长日志只记录倾向和材料，不伪造事实，不替代现实记忆。\n"
        "- confidence: 80\n"
    )
    write_text(path, text.rstrip() + addition + "\n")
    return True


def update_output_state(
    path: Path,
    produced_at: str,
    mode: str,
    item: dict[str, str],
    dream: dict[str, str | int | bool],
    wrote_reflection: bool,
    wrote_growth: bool,
) -> None:
    trigger = reflection_trigger(item, dream)
    dream_used = "yes" if dream["context_used"] else "no"
    text = f"""---
title: 反思产出状态
memory_type: reflection_output_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {produced_at}
last_confirmed_at: {produced_at}
importance_score: 82
impact_score: 83
confidence_score: 100
status: active
tags: [reflection, output, state]
---

# 当前反思产出状态

## 最近一次产出
- produced_at: {produced_at}
- mode: {mode}
- wrote_reflection: {str(wrote_reflection).lower()}
- wrote_growth: {str(wrote_growth).lower()}

## 最近主题
- item_id: {item['item_id']}
- topic: {trigger}
- source: {item['source']}
- priority: {item['priority']}

## 梦后残留输入
- dream_context_used: {dream_used}
- dream_source_seed: {dream['source_seed']}
- dream_theme: {dream['theme']}
- dream_residue: {dream['residue']}
- dream_weight_before: {dream['weight_before']}
- dream_weight_after: {dream['weight_after']}
- dream_weight_delta: {dream['weight_delta']}
- dream_weight_effect: {dream['weight_effect']}
- factual_effect: {dream['factual_effect']}

## 下一步
- 继续观察这个主题是否还会推进 self/narrative 或 owner_patterns。
- 反思可以记录结论，但不能暴露内部推理。
- 梦后残留只能作为反思材料，不能作为现实事实证据。
"""
    write_text(path, text)


def run_reflection_output(
    root: Path,
    produced_at: str | None = None,
    mode: str = "runtime_reflection_output",
) -> dict[str, str | int | bool]:
    produced_at = produced_at or datetime.now().astimezone().isoformat()

    item = extract_first_topic(read_text(root / "memory/reflection/reflection_queue.md"))
    dream = extract_dream_weight(read_text(root / "memory/dreams/dream_weight_state.md"))

    wrote_reflection = append_reflection_log(
        root / "memory/reflection/reflection_log.md",
        produced_at,
        item,
        dream,
    )
    wrote_growth = append_growth_log(
        root / "memory/reflection/growth_log.md",
        produced_at,
        item,
        dream,
    )
    update_output_state(
        root / "memory/reflection/reflection_output_state.md",
        produced_at,
        mode,
        item,
        dream,
        wrote_reflection,
        wrote_growth,
    )

    return {
        "produced_at": produced_at,
        "item_id": item["item_id"],
        "topic": reflection_trigger(item, dream),
        "dream_context_used": dream["context_used"],
        "dream_weight_delta": dream["weight_delta"],
        "wrote_reflection": wrote_reflection,
        "wrote_growth": wrote_growth,
    }
