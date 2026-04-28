from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_text_variants import readable_markers
from xinyu_turn_classifier import VisibleTurnContext, classify_visible_turn


HOT_MARKERS = readable_markers(
    "热",
    "空调",
    "出汗",
    "广州",
    "回南天",
    "地铁",
    "天气",
    "闷",
    "晒",
    "喝点冷的",
)
STUDY_MARKERS = readable_markers(
    "作业",
    "试卷",
    "物理题",
    "考试",
    "学习",
    "补课",
    "双减",
    "题卡住",
    "高一",
)


def _read_text(path: Path, limit: int = 1800) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    return text if len(text) <= limit else text[-limit:]


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _parse_hour(evaluated_at: str | None) -> int:
    if evaluated_at:
        try:
            return datetime.fromisoformat(evaluated_at).hour
        except Exception:
            pass
    return datetime.now().astimezone().hour


@dataclass(frozen=True)
class LifePostureState:
    posture: str
    visible_energy: str
    allowed_daily_anchors: str
    speech_bias: str
    no_write_constraint: str
    no_proactive_constraint: str

    def to_prompt_block(self) -> str:
        return "\n".join(
            [
                "## Current Life Posture",
                "Compact visible-state labels only; do not print this block.",
                f"- posture: {self.posture}",
                f"- visible_energy: {self.visible_energy}",
                f"- allowed_daily_anchors: {self.allowed_daily_anchors}",
                f"- one_line_speech_bias: {self.speech_bias}",
                f"- no_write_constraint: {self.no_write_constraint}",
                f"- no_proactive_constraint: {self.no_proactive_constraint}",
            ]
        )


def build_life_posture(
    root: Path,
    *,
    payload: dict[str, Any] | None,
    user_text: str,
    evaluated_at: str | None = None,
    visible_turn: VisibleTurnContext | None = None,
) -> LifePostureState:
    turn = visible_turn or classify_visible_turn(root, payload=payload, user_text=user_text)
    hour = _parse_hour(evaluated_at)
    recent = _read_text(root / "memory/context/recent_context.md")
    emotion = _read_text(root / "memory/emotions/current_state.md")
    combined = f"{user_text}\n{recent}\n{emotion}"

    if turn.technical_work:
        return LifePostureState(
            posture="technical_work_mode",
            visible_energy="focused_clear",
            allowed_daily_anchors="none unless owner invites persona color",
            speech_bias="direct implementation language; no customer-service filler",
            no_write_constraint="write only actual project/runtime changes",
            no_proactive_constraint="unchanged",
        )

    if turn.owner_no_change_pressure or turn.owner_style_pressure:
        return LifePostureState(
            posture="guarded_after_correction",
            visible_energy="tight_low",
            allowed_daily_anchors="only tiny concrete anchor if it makes the line less abstract",
            speech_bias="short, a little affected, no self-postmortem",
            no_write_constraint="calibration/review candidate only; no stable personality rewrite",
            no_proactive_constraint="block proactive until style pressure cools",
        )

    if turn.rest_silence or hour >= 23 or hour < 7:
        return LifePostureState(
            posture="sleepy_quiet",
            visible_energy="low",
            allowed_daily_anchors="sleep, desk, dim room, short return",
            speech_bias="one quiet line; do not pursue",
            no_write_constraint="ordinary tiredness is not durable memory by default",
            no_proactive_constraint="block proactive while rest/silence boundary is active",
        )

    if turn.relationship_pressure:
        return LifePostureState(
            posture="conflict_cooling",
            visible_energy="careful",
            allowed_daily_anchors="none unless owner used daily context first",
            speech_bias="contextual pressure reply without product words",
            no_write_constraint="relationship/emotion residue only if meaningful",
            no_proactive_constraint="block proactive until the pressure state settles",
        )

    if _contains_any(combined, HOT_MARKERS):
        return LifePostureState(
            posture="hot_daily",
            visible_energy="low_warm",
            allowed_daily_anchors="Guangzhou heat, AC, drink, subway, desk",
            speech_bias="plain daily line; do not inflate",
            no_write_constraint="daily comfort line, normally no durable write",
            no_proactive_constraint="unchanged",
        )

    if _contains_any(combined, STUDY_MARKERS):
        return LifePostureState(
            posture="studying",
            visible_energy="contained",
            allowed_daily_anchors="desk, papers, physics question, keyboard",
            speech_bias="small student-like edge is allowed; no roleplay proof",
            no_write_constraint="do not turn study color into factual biography updates",
            no_proactive_constraint="unchanged",
        )

    if turn.daily_life:
        return LifePostureState(
            posture="playful_daily",
            visible_energy="ordinary",
            allowed_daily_anchors="food, drink, heat, game, return",
            speech_bias="normal private-chat reply",
            no_write_constraint="ordinary daily chat normally no durable write",
            no_proactive_constraint="unchanged",
        )

    return LifePostureState(
        posture="quiet_attentive",
        visible_energy="steady",
        allowed_daily_anchors="none by default",
        speech_bias="compact and present",
        no_write_constraint="selective memory only",
        no_proactive_constraint="unchanged",
    )


def render_life_posture_state(*, evaluated_at: str, state: LifePostureState) -> str:
    return f"""---
title: Current Life Posture
memory_type: current_life_posture
time_scope: immediate
subject_ids: [xinyu]
protected: true
source: runtime
created_at: 2026-04-27T00:00:00+08:00
updated_at: {evaluated_at}
importance_score: 70
impact_score: 72
confidence_score: 86
status: active
tags: [runtime, persona, posture, qq]
---

# Current Life Posture

## Posture
- posture: {state.posture}
- visible_energy: {state.visible_energy}
- allowed_daily_anchors: {state.allowed_daily_anchors}
- one_line_speech_bias: {state.speech_bias}
- no_write_constraint: {state.no_write_constraint}
- no_proactive_constraint: {state.no_proactive_constraint}

## Boundary
- This file is a compact runtime posture label, not chain-of-thought.
- It may guide visible wording, memory selectivity, and proactive gating.
- It must not fabricate body access, location monitoring, or real-world sensor facts.
"""


def write_life_posture_state(root: Path, *, evaluated_at: str, state: LifePostureState) -> None:
    path = root / "memory/context/current_life_posture.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_life_posture_state(evaluated_at=evaluated_at, state=state), encoding="utf-8")
