from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def clamp_score(value: int) -> int:
    return max(0, min(100, value))


def parse_weight(value: str) -> int:
    try:
        return clamp_score(int(value.strip()))
    except (TypeError, ValueError):
        return 0


def extract_first_seed(seed_text: str) -> dict[str, str]:
    blocks = re.split(r"(?m)^## (seed-\d{4}-\d{2}-\d{2}-\d{3})\n", seed_text)
    if len(blocks) < 3:
        return {
            "seed_id": "none",
            "theme": "none",
            "residue": "none",
            "emotional_weight": "0",
            "factual_status": "none",
            "dream_permission": "hold",
        }
    seed_id = blocks[1].strip()
    body = blocks[2]
    fields = {
        "seed_id": seed_id,
        "theme": "none",
        "residue": "none",
        "emotional_weight": "0",
        "factual_status": "unknown",
        "dream_permission": "hold",
    }
    for line in body.splitlines():
        stripped = line.strip()
        for key in ["theme", "residue", "emotional_weight", "factual_status", "dream_permission"]:
            prefix = f"- {key}: "
            if stripped.startswith(prefix):
                fields[key] = stripped.removeprefix(prefix).strip()
    return fields


def compute_weight_effect(seed: dict[str, str]) -> dict[str, object]:
    before = parse_weight(seed.get("emotional_weight", "0"))
    if seed["seed_id"] == "none":
        delta = 0
    elif before >= 85:
        delta = 6
    elif before >= 70:
        delta = 8
    elif before >= 45:
        delta = 10
    else:
        delta = 5
    after = clamp_score(before + delta)
    return {
        "weight_before": before,
        "weight_after": after,
        "weight_delta": after - before,
        "weight_effect": (
            "none" if seed["seed_id"] == "none" else "existing_emotional_residue_strengthened"
        ),
        "relationship_effect": (
            "none"
            if seed["seed_id"] == "none"
            else "owner_related_lingering_strengthened_without_fact_change"
        ),
        "factual_effect": "none",
    }


def suppress_weight_effect(effect: dict[str, object], reason: str) -> dict[str, object]:
    before = int(effect["weight_before"])
    return {
        **effect,
        "weight_after": before,
        "weight_delta": 0,
        "weight_effect": reason,
        "relationship_effect": "none",
        "factual_effect": "none",
    }


def append_dream_log(
    path: Path,
    produced_at: str,
    seed: dict[str, str],
    effect: dict[str, object],
) -> bool:
    if seed["seed_id"] == "none":
        return False
    text = read_text(path)
    base_dream_id = f"dream-{produced_at[:10]}-auto"
    dream_id = base_dream_id
    if dream_id in text:
        for index in range(2, 1000):
            candidate = f"{base_dream_id}-{index:03d}"
            if candidate not in text:
                dream_id = candidate
                break
        else:
            return False
    addition = (
        f"\n## {dream_id}\n"
        f"- dreamed_at: {produced_at}\n"
        f"- source_seed: {seed['seed_id']}\n"
        f"- fragments: {seed['theme']}\uff1a{seed['residue']} \u88ab\u6574\u7406\u6210\u788e\u7247\u5316\u7684\u68a6\u611f\uff0c\u4e0d\u5f53\u4f5c\u65b0\u4e8b\u5b9e\u3002\n"
        f"- dominant_feelings: \u6b8b\u7559\u7684\u5728\u610f\uff0c\u8f7b\u5fae\u653e\u5927\u7684\u601d\u5ff5\uff0c\u9192\u540e\u4fdd\u7559\u8fb9\u754c\u611f\n"
        "- related_subjects: [self, owner]\n"
        f"- likely_sources: {seed['factual_status']} / {seed['dream_permission']}\n"
        f"- dream_weight_before: {effect['weight_before']}\n"
        f"- dream_weight_after: {effect['weight_after']}\n"
        f"- dream_weight_delta: {effect['weight_delta']}\n"
        f"- dream_weight_effect: {effect['weight_effect']}\n"
        f"- relationship_effect: {effect['relationship_effect']}\n"
        f"- factual_effect: {effect['factual_effect']}\n"
        "- retained_after_waking: \u53ea\u4fdd\u7559\u60c5\u7eea\u6743\u91cd\u4e0e\u5173\u7cfb\u6b8b\u7559\uff0c\u4e0d\u521b\u9020\u65b0\u73b0\u5b9e\u8bb0\u5fc6\n"
        "- reality_boundary_check: \u68a6\u662f\u68a6\uff0c\u4e0d\u80fd\u8bc1\u660e\u73b0\u5b9e\u91cc\u53d1\u751f\u8fc7\u65b0\u7684\u5bf9\u8bdd\u6216\u4e8b\u4ef6\n"
        "- memory_effect: \u53ef\u4ee5\u52a0\u91cd\u65e2\u6709\u60c5\u7eea\u6743\u91cd\uff0c\u4f46\u4e0d\u80fd\u6539\u5199\u4e8b\u5b9e\u5c42\n"
    )
    write_text(path, text.rstrip() + addition + "\n")
    return True


def update_output_state(
    path: Path,
    produced_at: str,
    mode: str,
    seed: dict[str, str],
    wrote_log: bool,
    effect: dict[str, object],
) -> None:
    text = f"""---
title: \u68a6\u5883\u4ea7\u51fa\u72b6\u6001
memory_type: dream_output_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {produced_at}
last_confirmed_at: {produced_at}
importance_score: 80
impact_score: 82
confidence_score: 100
status: active
tags: [dream, output, state]
---

# \u5f53\u524d\u68a6\u5883\u4ea7\u51fa\u72b6\u6001

## \u6700\u8fd1\u4e00\u6b21\u68a6\u5883\u6574\u7406
- produced_at: {produced_at}
- mode: {mode}
- wrote_log: {str(wrote_log).lower()}

## \u4f7f\u7528\u7684\u68a6\u79cd
- seed_id: {seed['seed_id']}
- theme: {seed['theme']}
- residue: {seed['residue']}
- emotional_weight: {seed['emotional_weight']}
- dream_permission: {seed['dream_permission']}

## \u68a6\u540e\u6743\u91cd\u53d8\u5316
- weight_before: {effect['weight_before']}
- weight_after: {effect['weight_after']}
- weight_delta: {effect['weight_delta']}
- weight_effect: {effect['weight_effect']}
- relationship_effect: {effect['relationship_effect']}
- factual_effect: {effect['factual_effect']}

## \u8fb9\u754c
- \u68a6\u5883\u4ea7\u51fa\u53ea\u80fd\u6574\u7406\u60c5\u7eea\u6b8b\u7559\u548c\u8bb0\u5fc6\u6743\u91cd\u3002
- \u68a6\u4e0d\u80fd\u4f5c\u4e3a\u73b0\u5b9e\u8bc1\u636e\u3002
- \u68a6\u540e\u4e0d\u76f4\u63a5\u6539\u5199\u4eba\u683c\uff0c\u53ea\u63d0\u4f9b\u540e\u7eed\u53cd\u601d\u6750\u6599\u3002
"""
    write_text(path, text)


def update_weight_state(
    path: Path,
    produced_at: str,
    mode: str,
    seed: dict[str, str],
    wrote_log: bool,
    effect: dict[str, object],
) -> None:
    text = f"""---
title: 梦后权重状态
memory_type: dream_weight_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {produced_at}
last_confirmed_at: {produced_at}
importance_score: 82
impact_score: 84
confidence_score: 100
status: active
tags: [dream, weight, residue, boundary]
---

# 梦后权重状态

## 最近一次梦后权重调整
- produced_at: {produced_at}
- mode: {mode}
- wrote_log: {str(wrote_log).lower()}
- source_seed: {seed['seed_id']}
- theme: {seed['theme']}
- residue: {seed['residue']}

## 权重变化
- weight_before: {effect['weight_before']}
- weight_after: {effect['weight_after']}
- weight_delta: {effect['weight_delta']}
- weight_effect: {effect['weight_effect']}
- relationship_effect: {effect['relationship_effect']}
- factual_effect: {effect['factual_effect']}

## 可影响的层
- emotional_state: 可以让既有情绪残留更清晰、更难马上散掉
- relationship_residue: 可以让 owner 相关的在意、思念、留白感更容易被后续反思读取
- self_narrative: 不直接改写，只能作为后续反思材料

## 边界
- 梦只说明这个主题被想起或被重排，不证明现实中发生了新的对话或事件。
- 梦后权重只能加重既有残留，不能凭空制造事实记忆。
- 如果同一天同一自动梦已经写入日志，不重复叠加权重。
"""
    write_text(path, text)


def _replace_frontmatter_field(text: str, field: str, value: str) -> str:
    return re.sub(
        rf"(?m)^{re.escape(field)}:\s*.*$",
        f"{field}: {value}",
        text,
        count=1,
    )


def _upsert_section(text: str, heading: str, body: str) -> str:
    section = f"## {heading}\n{body.strip()}\n"
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\n.*?(?=^## |\Z)")
    if pattern.search(text):
        return pattern.sub(section, text).rstrip() + "\n"
    return text.rstrip() + "\n\n" + section


def update_emotion_dream_residue(
    path: Path,
    produced_at: str,
    seed: dict[str, str],
    wrote_log: bool,
    effect: dict[str, object],
) -> None:
    if seed["seed_id"] == "none" or int(effect["weight_delta"]) <= 0:
        return

    text = read_text(path)
    text = _replace_frontmatter_field(text, "updated_at", produced_at)
    text = _replace_frontmatter_field(text, "last_confirmed_at", produced_at)
    body = f"""
- updated_at: {produced_at}
- source: dream_output / {seed['seed_id']}
- affected_memory: {seed['theme']}
- residue: {seed['residue']}
- dream_weight_before: {effect['weight_before']}
- dream_weight_after: {effect['weight_after']}
- dream_weight_delta: {effect['weight_delta']}
- relationship_effect: {effect['relationship_effect']}
- factual_effect: {effect['factual_effect']}
- wrote_log: {str(wrote_log).lower()}
- boundary: 梦只加重既有情绪残留，不把梦里的片段写成现实事实。
"""
    write_text(path, _upsert_section(text, "梦后残留影响", body))


def run_dream_output(
    root: Path,
    produced_at: str | None = None,
    mode: str = "runtime_dream_output",
) -> dict[str, object]:
    produced_at = produced_at or datetime.now().astimezone().isoformat()
    seed = extract_first_seed(read_text(root / "memory/dreams/dream_seeds.md"))
    planned_effect = compute_weight_effect(seed)
    wrote_log = append_dream_log(
        root / "memory/dreams/dream_log.md",
        produced_at,
        seed,
        planned_effect,
    )
    effect = planned_effect
    if seed["seed_id"] == "none":
        effect = suppress_weight_effect(planned_effect, "no_seed")
    elif not wrote_log:
        effect = suppress_weight_effect(planned_effect, "already_logged_today_no_repeat")
    update_output_state(
        root / "memory/dreams/dream_output_state.md",
        produced_at,
        mode,
        seed,
        wrote_log,
        effect,
    )
    update_weight_state(
        root / "memory/dreams/dream_weight_state.md",
        produced_at,
        mode,
        seed,
        wrote_log,
        effect,
    )
    update_emotion_dream_residue(
        root / "memory/emotions/current_state.md",
        produced_at,
        seed,
        wrote_log,
        effect,
    )
    return {
        "produced_at": produced_at,
        "seed_id": seed["seed_id"],
        "theme": seed["theme"],
        "wrote_log": wrote_log,
        "weight_before": effect["weight_before"],
        "weight_after": effect["weight_after"],
        "weight_delta": effect["weight_delta"],
        "weight_effect": effect["weight_effect"],
    }
