from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_REL = "memory/context/persona_surface_state.md"
RESIDUE_HALF_LIFE_HOURS = 6.0


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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


def _extract_field(text: str, field: str, default: str = "") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.*)$", text)
    return match.group(1).strip() if match else default


def _extract_int(text: str, field: str, default: int = 0) -> int:
    try:
        return int(_extract_field(text, field, str(default)))
    except ValueError:
        return default


def _decay_strength(strength: int, updated_at: str, *, at: datetime | None = None) -> int:
    if strength <= 0:
        return 0
    updated = _parse_dt(updated_at)
    if updated is None:
        return max(0, min(100, strength))
    current = at or _now()
    elapsed_hours = max(0.0, (current - updated).total_seconds() / 3600.0)
    decayed = strength * math.pow(0.5, elapsed_hours / RESIDUE_HALF_LIFE_HOURS)
    return max(0, min(100, int(round(decayed))))


@dataclass(frozen=True)
class TurnResidue:
    scene: str = "none"
    pressure: str = "none"
    speech_act: str = "none"
    tone: str = "neutral"
    felt_residue: str = "none"
    reply_shape: str = "none"
    updated_at: str = "unknown"
    raw_strength: int = 0
    decayed_strength: int = 0

    @property
    def active(self) -> bool:
        return self.decayed_strength >= 12

    def to_prompt_block(self) -> str:
        if not self.active:
            return "\n".join(
                [
                    "## Previous Turn Residue",
                    "No active previous-turn surface residue. Do not reset stable persona; just avoid inventing residue.",
                ]
            )
        return "\n".join(
            [
                "## Previous Turn Residue",
                "This is floating surface state from the last visible turn. It decays gradually and must not rewrite stable identity.",
                f"- previous_scene: {self.scene}",
                f"- previous_pressure: {self.pressure}",
                f"- previous_speech_act: {self.speech_act}",
                f"- previous_tone: {self.tone}",
                f"- previous_felt_residue: {self.felt_residue}",
                f"- previous_reply_shape: {self.reply_shape}",
                f"- residue_strength_now: {self.decayed_strength}",
                f"- residue_updated_at: {self.updated_at}",
                "- use: let the next reply inherit a little tone/emotional inertia instead of snapping back to default assistant mode",
            ]
        )


def read_turn_residue(root: Path, *, at: datetime | None = None) -> TurnResidue:
    path = root / STATE_REL
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return TurnResidue()

    updated_at = _extract_field(text, "updated_at", "")
    raw_strength = _extract_int(text, "residue_strength", 0)
    return TurnResidue(
        scene=_extract_field(text, "last_scene", "unknown"),
        pressure=_extract_field(text, "last_pressure", "unknown"),
        speech_act=_extract_field(text, "last_speech_act", "unknown"),
        tone=_extract_field(text, "last_tone", "unknown"),
        felt_residue=_extract_field(text, "last_felt_residue", "unknown"),
        reply_shape=_extract_field(text, "last_reply_shape", "unknown"),
        updated_at=_extract_field(text, "updated_at", ""),
        raw_strength=raw_strength,
        decayed_strength=_decay_strength(raw_strength, updated_at, at=at),
    )


def _tone_from_scene(scene: Any) -> tuple[str, str, str, int]:
    style_pressure = bool(getattr(scene, "style_pressure", False))
    relationship_pressure = bool(getattr(scene, "relationship_pressure", False))
    technical_request = bool(getattr(scene, "technical_request", False))
    is_owner = bool(getattr(scene, "is_owner", False))

    if style_pressure:
        return (
            "short_affected_guarded",
            "owner heard style failure; keep a small guarded edge",
            "style_pressure_reply",
            88,
        )
    if relationship_pressure and is_owner and not technical_request:
        return (
            "hurt_pressure_residue",
            "relationship pressure should linger into the next turn",
            "relationship_pressure_reply",
            82,
        )
    if technical_request:
        return (
            "focused_engineering",
            "task focus can remain, but should not erase XinYu identity",
            "technical_reply",
            36,
        )
    if is_owner:
        return (
            "ordinary_owner_continuity",
            "carry a little private-chat continuity",
            "owner_chat_reply",
            46,
        )
    return (
        "external_boundary",
        "keep external-contact boundary without owner intimacy",
        "external_chat_reply",
        32,
    )


def _reply_shape(reply: str) -> str:
    text = reply.strip()
    if not text:
        return "empty"
    if "\n" in text or "\r" in text:
        return "multi_line"
    if len(text) <= 80:
        return "compact"
    if len(text) <= 180:
        return "medium_bubble"
    return "long_bubble"


def write_turn_residue(
    root: Path,
    *,
    scene: Any,
    user_text: str,
    reply: str,
    source: str = "xinyu_core_bridge",
    evaluated_at: datetime | None = None,
) -> bool:
    evaluated = evaluated_at or _now()
    tone, felt, speech_act, strength = _tone_from_scene(scene)
    if not reply.strip():
        strength = min(strength, 25)
        felt = "visible reply was empty; preserve caution"

    path = root / STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""---
title: Persona Surface State
memory_type: persona_surface_state
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: {source}
created_at: 2026-04-27T00:00:00+08:00
updated_at: {evaluated.isoformat()}
last_confirmed_at: {evaluated.isoformat()}
importance_score: 78
impact_score: 84
confidence_score: 100
status: active
tags: [persona, floating, tone, residue]
---

# Persona Surface State

## Layer Boundary
- stable_layer: self/personality_profile + owner relation + reality boundaries
- floating_layer: current scene, pressure, visible energy, last tone, last reply shape
- rule: floating_layer may color the next turn but cannot rename XinYu, erase owner relation, or turn her into a default assistant

## Previous Visible Turn
- updated_at: {evaluated.isoformat()}
- last_scene: {_safe_str(getattr(scene, "scene", "")) or _safe_str(getattr(scene, "turn_kind", "")) or "runtime_classified"}
- last_pressure: {"style" if bool(getattr(scene, "style_pressure", False)) else "relationship" if bool(getattr(scene, "relationship_pressure", False)) else "task" if bool(getattr(scene, "technical_request", False)) else "normal"}
- last_speech_act: {speech_act}
- last_tone: {tone}
- last_felt_residue: {felt}
- last_reply_shape: {_reply_shape(reply)}
- residue_strength: {strength}
- decay_half_life_hours: {RESIDUE_HALF_LIFE_HOURS:g}
- last_user_text_chars: {len(user_text)}
- last_reply_chars: {len(reply.strip())}

## Runtime Use
- The next turn should inherit residue_strength as tone inertia, then decay it by real elapsed time.
- Do not snap from hurt/guarded/style-pressure turns back to polished helper voice.
- Do not let residue override a clear technical task, explicit rest boundary, or stable identity/reality boundaries.
"""
    old = ""
    try:
        old = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        pass
    if old == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True
