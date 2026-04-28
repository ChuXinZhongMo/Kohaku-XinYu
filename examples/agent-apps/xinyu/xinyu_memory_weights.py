from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


STATE_REL = "memory/context/memory_weight_state.md"


@dataclass(frozen=True)
class MemoryWeightSpec:
    rel: str
    layer: str
    half_life_hours: float
    floor: int
    stable: bool = False


MEMORY_WEIGHT_SPECS = (
    MemoryWeightSpec("memory/self/system_prompt_memory.md", "stable_prompt_memory", 1000000.0, 92, True),
    MemoryWeightSpec("memory/self/core.md", "stable_identity", 1000000.0, 96, True),
    MemoryWeightSpec("memory/self/personality_profile.md", "stable_identity", 1000000.0, 96, True),
    MemoryWeightSpec("memory/context/persona_life_anchors.md", "stable_identity", 1000000.0, 84, True),
    MemoryWeightSpec("memory/context/real_world_anchor_policy.md", "stable_reality_boundary", 1000000.0, 90, True),
    MemoryWeightSpec("memory/context/life_month_slots.md", "life_memory_slots", 1000000.0, 52, True),
    MemoryWeightSpec("memory/context/current_life_month_context.md", "floating_life_month_context", 12.0, 18, False),
    MemoryWeightSpec("memory/people/owner.md", "stable_relationship", 1000000.0, 92, True),
    MemoryWeightSpec("memory/relationships/index.md", "stable_relationship", 720.0, 82, False),
    MemoryWeightSpec("memory/self/voice_profile_zh.md", "stable_voice", 1000000.0, 88, True),
    MemoryWeightSpec("memory/self/voice_calibration_log.md", "floating_voice", 168.0, 35, False),
    MemoryWeightSpec("memory/emotions/current_state.md", "floating_emotion", 36.0, 30, False),
    MemoryWeightSpec("memory/context/persona_surface_state.md", "floating_surface", 6.0, 0, False),
    MemoryWeightSpec("memory/context/current_life_posture.md", "floating_surface", 12.0, 15, False),
    MemoryWeightSpec("memory/context/recent_context.md", "recent_context", 72.0, 18, False),
    MemoryWeightSpec("memory/context/unfinished_experiences.md", "recent_context", 120.0, 25, False),
    MemoryWeightSpec("memory/context/active_questions.md", "active_questions", 168.0, 25, False),
    MemoryWeightSpec("memory/dreams/dream_weight_state.md", "floating_dream_residue", 48.0, 10, False),
    MemoryWeightSpec("memory/archive/long_term_memory_gate_state.md", "retention_gate", 168.0, 40, False),
)


def _now() -> datetime:
    return datetime.now().astimezone()


def _parse_dt(value: str) -> datetime | None:
    text = value.strip()
    if not text or text == "unknown":
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fields: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _as_int(value: str | None, default: int = 0) -> int:
    if value is None:
        return default
    match = re.search(r"-?\d+", value)
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def _score(fields: dict[str, str]) -> int:
    importance = _as_int(fields.get("importance_score"), 50)
    impact = _as_int(fields.get("impact_score"), 50)
    confidence = _as_int(fields.get("confidence_score"), 80)
    return max(0, min(100, round(importance * 0.45 + impact * 0.45 + confidence * 0.10)))


def _age_hours(fields: dict[str, str], *, at: datetime) -> float:
    dt = _parse_dt(fields.get("last_confirmed_at", "")) or _parse_dt(fields.get("updated_at", ""))
    if dt is None:
        return 0.0
    return max(0.0, (at - dt).total_seconds() / 3600.0)


def _decayed_weight(base: int, age_hours: float, half_life_hours: float, floor: int, stable: bool) -> int:
    if stable:
        return max(floor, base)
    if half_life_hours <= 0:
        decayed = base
    else:
        decayed = base * math.pow(0.5, age_hours / half_life_hours)
    return max(floor, min(100, int(round(decayed))))


def calculate_memory_weights(root: Path, *, at: datetime | None = None) -> list[dict[str, object]]:
    evaluated = at or _now()
    rows: list[dict[str, object]] = []
    for spec in MEMORY_WEIGHT_SPECS:
        path = root / spec.rel
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            rows.append(
                {
                    "path": spec.rel,
                    "layer": spec.layer,
                    "status": "missing",
                    "base_weight": 0,
                    "active_weight": 0,
                    "age_hours": 0.0,
                    "floor": spec.floor,
                    "stable": spec.stable,
                }
            )
            continue
        fields = _frontmatter(text)
        base = _score(fields)
        age = _age_hours(fields, at=evaluated)
        rows.append(
            {
                "path": spec.rel,
                "layer": spec.layer,
                "status": fields.get("status", "active"),
                "base_weight": base,
                "active_weight": _decayed_weight(base, age, spec.half_life_hours, spec.floor, spec.stable),
                "age_hours": age,
                "floor": spec.floor,
                "stable": spec.stable,
            }
        )
    return rows


def render_memory_weight_state(evaluated_at: datetime, rows: list[dict[str, object]]) -> str:
    active_rows = [row for row in rows if row["status"] != "missing"]
    active_rows.sort(key=lambda row: int(row["active_weight"]), reverse=True)
    row_lines = "\n".join(
        "- path: {path} | layer: {layer} | active_weight: {active} | base_weight: {base} | age_hours: {age:.2f} | floor: {floor} | stable: {stable}".format(
            path=row["path"],
            layer=row["layer"],
            active=int(row["active_weight"]),
            base=int(row["base_weight"]),
            age=float(row["age_hours"]),
            floor=int(row["floor"]),
            stable=str(bool(row["stable"])).lower(),
        )
        for row in active_rows
    ) or "- none"
    return f"""---
title: Memory Weight State
memory_type: memory_weight_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_memory_weights
created_at: 2026-04-27T00:00:00+08:00
updated_at: {evaluated_at.isoformat()}
last_confirmed_at: {evaluated_at.isoformat()}
importance_score: 86
impact_score: 86
confidence_score: 100
status: active
tags: [memory, weights, retention, decay]
---

# Memory Weight State

## Policy
- decay_model: gradual_half_life
- stable_layer_rule: self core, personality profile, owner relation, and voice profile have high floors and must not decay into default assistant persona.
- floating_layer_rule: emotion, tone, recent context, dream residue, and life posture decay by elapsed time instead of disappearing after one turn.
- retention_rule: low active_weight means less vivid surface influence, not destructive deletion.
- use_rule: when choosing visible wording, prefer higher active_weight rows; do not let fresh but low-weight trivia overwrite stable identity or relationship memory.

## Active Weights
{row_lines}
"""


def refresh_memory_weight_state(root: Path, *, at: datetime | None = None) -> str:
    evaluated = at or _now()
    rows = calculate_memory_weights(root, at=evaluated)
    text = render_memory_weight_state(evaluated, rows)
    path = root / STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    old = ""
    try:
        old = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        pass
    if old != text:
        path.write_text(text, encoding="utf-8")
    return text
