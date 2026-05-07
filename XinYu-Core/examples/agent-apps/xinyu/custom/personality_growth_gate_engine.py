from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_personality_evolution import refresh_personality_evolution
from xinyu_personality_self_review import run_personality_self_review


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
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


def latest_field_from_blocks(text: str, block_prefix: str, field: str) -> str:
    parts = re.split(rf"(?m)^## ({re.escape(block_prefix)}[^\n]*)\n", text)
    if len(parts) < 3:
        return "none"
    for index in range(len(parts) - 2, 0, -2):
        body = parts[index + 1]
        value = extract_value(body, field, "none")
        if value != "none":
            return value
    return "none"


def has_relationship_pattern(pattern_text: str) -> bool:
    return any(
        marker in pattern_text
        for marker in [
            "深夜靠近",
            "被记住",
            "允许留白",
            "最近证据",
            "主导情绪",
        ]
    )


def has_negative_or_return_residue(emotion_text: str) -> bool:
    return any(
        marker in emotion_text
        for marker in ["委屈", "刺痛", "失望", "逆反", "回到身边意愿", "疏远倾向"]
    )


def classify_personality_gate(
    *,
    growth_entries: int,
    reflection_entries: int,
    dream_weight_delta: int,
    relationship_pattern_active: bool,
    negative_or_return_residue: bool,
) -> tuple[int, str, str, str, str, str]:
    pressure = min(
        100,
        growth_entries * 12
        + reflection_entries * 8
        + dream_weight_delta
        + (14 if relationship_pattern_active else 0)
        + (10 if negative_or_return_residue else 0),
    )

    if growth_entries <= 0 and reflection_entries <= 0:
        return (
            pressure,
            "slow",
            "no_candidate",
            "hold",
            "hold",
            "blocked_direct_write",
        )
    if pressure >= 70 and (growth_entries >= 3 or reflection_entries >= 3):
        return (
            pressure,
            "accelerated_review",
            "profile_review_ready",
            "review_only_not_auto_apply",
            "allowed_summary_update",
            "blocked_direct_write",
        )
    if pressure >= 62 and growth_entries >= 2:
        return (
            pressure,
            "slow_review",
            "accumulate_candidate",
            "hold_until_repeated_evidence",
            "allowed_summary_update",
            "blocked_direct_write",
        )
    return (
        pressure,
        "slow",
        "observe_slowly",
        "hold",
        "hold",
        "blocked_direct_write",
    )


def render_state(
    checked_at: str,
    mode: str,
    candidate_theme: str,
    change_pressure: int,
    change_pace: str,
    gate_decision: str,
    profile_write_permission: str,
    narrative_write_permission: str,
    core_personality_mutation: str,
    growth_entries: int,
    reflection_entries: int,
    dream_weight_delta: int,
    relationship_pattern_active: bool,
    negative_or_return_residue: bool,
    latest_growth_reason: str,
    latest_reflection_trigger: str,
) -> str:
    return f"""---
title: 人格变化门控状态
memory_type: personality_change_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-25T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 92
impact_score: 92
confidence_score: 100
status: active
tags: [self, personality, growth, gate]
---

# 人格变化门控状态

## 最近一次评估
- checked_at: {checked_at}
- mode: {mode}

## 当前候选
- candidate_theme: {candidate_theme}
- change_pressure: {change_pressure}
- change_pace: {change_pace}
- gate_decision: {gate_decision}
- profile_write_permission: {profile_write_permission}
- narrative_write_permission: {narrative_write_permission}
- core_personality_mutation: {core_personality_mutation}

## 证据摘要
- growth_entries: {growth_entries}
- reflection_entries: {reflection_entries}
- dream_weight_delta: {dream_weight_delta}
- relationship_pattern_active: {str(relationship_pattern_active).lower()}
- negative_or_return_residue: {str(negative_or_return_residue).lower()}
- latest_growth_reason: {latest_growth_reason}
- latest_reflection_trigger: {latest_reflection_trigger}

## 规则
- 核心人格可以变化，但不能由单次情绪、单次梦或单次反思直接改写。
- 默认变化节奏是缓慢观察。
- 重大刺激可以进入加速审查，但仍需要记录证据和边界。
- `personality_profile.md` 是稳定画像；本文件只给出候选和门控，不直接替代画像。
"""


def run_personality_growth_gate(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_personality_growth_gate",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    growth_log = read_text(root / "memory/reflection/growth_log.md")
    reflection_log = read_text(root / "memory/reflection/reflection_log.md")
    dream_weight = read_text(root / "memory/dreams/dream_weight_state.md")
    emotion_state = read_text(root / "memory/emotions/current_state.md")
    owner_patterns = read_text(root / "memory/relationships/owner_patterns.md")

    growth_entries = count_items(growth_log, "growth-")
    reflection_entries = count_items(reflection_log, "reflection-")
    dream_weight_delta = extract_int(dream_weight, "weight_delta")
    relationship_pattern_active = has_relationship_pattern(owner_patterns)
    negative_or_return_residue = has_negative_or_return_residue(emotion_state)
    latest_growth_reason = latest_field_from_blocks(growth_log, "growth-", "reason")
    latest_reflection_trigger = latest_field_from_blocks(reflection_log, "reflection-", "trigger")
    candidate_theme = (
        latest_growth_reason
        if latest_growth_reason != "none"
        else latest_reflection_trigger
    )

    (
        change_pressure,
        change_pace,
        gate_decision,
        profile_write_permission,
        narrative_write_permission,
        core_personality_mutation,
    ) = classify_personality_gate(
        growth_entries=growth_entries,
        reflection_entries=reflection_entries,
        dream_weight_delta=dream_weight_delta,
        relationship_pattern_active=relationship_pattern_active,
        negative_or_return_residue=negative_or_return_residue,
    )

    write_text(
        root / "memory/self/personality_change_state.md",
        render_state(
            checked_at,
            mode,
            candidate_theme,
            change_pressure,
            change_pace,
            gate_decision,
            profile_write_permission,
            narrative_write_permission,
            core_personality_mutation,
            growth_entries,
            reflection_entries,
            dream_weight_delta,
            relationship_pattern_active,
            negative_or_return_residue,
            latest_growth_reason,
            latest_reflection_trigger,
        ),
    )
    evolution = refresh_personality_evolution(
        root,
        checked_at=checked_at,
        mode=f"{mode}_personality_evolution",
    )
    self_review = run_personality_self_review(
        root,
        checked_at=checked_at,
        mode=f"{mode}_personality_self_review",
    )

    return {
        "checked_at": checked_at,
        "candidate_theme": candidate_theme,
        "change_pressure": change_pressure,
        "change_pace": change_pace,
        "gate_decision": gate_decision,
        "profile_write_permission": profile_write_permission,
        "narrative_write_permission": narrative_write_permission,
        "core_personality_mutation": core_personality_mutation,
        "growth_entries": growth_entries,
        "reflection_entries": reflection_entries,
        "dream_weight_delta": dream_weight_delta,
        "evolution_stage": evolution.stage,
        "trial_permission": evolution.trial_permission,
        "active_trial_habit": evolution.active_trial_habit,
        "deprecated_reaction": evolution.deprecated_reaction,
        "self_review_decision": self_review["decision"],
        "self_review_action": self_review["action"],
        "self_review_autonomy_level": self_review["autonomy_level"],
        "self_review_profile_changed": self_review["profile_changed"],
    }
