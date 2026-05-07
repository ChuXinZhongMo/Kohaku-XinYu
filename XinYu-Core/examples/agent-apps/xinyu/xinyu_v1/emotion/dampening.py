"""Emotion inertia and per-turn damping."""

from __future__ import annotations

from dataclasses import dataclass

from .models import EMOTION_DIMENSIONS, EmotionDelta, EmotionVector
from .vector_math import clamp


@dataclass(frozen=True, slots=True)
class DampeningConfig:
    max_step: float = 0.22
    high_salience_max_step: float = 0.38
    decay_factor: float = 0.985
    recovery_slowdown: float = 0.55


def damp_delta(delta: EmotionDelta, config: DampeningConfig) -> EmotionVector:
    normalized = delta.normalized()
    max_step = config.high_salience_max_step if normalized.salience >= 0.75 else config.max_step
    values: dict[str, float] = {}
    for dimension in EMOTION_DIMENSIONS:
        raw = float(normalized.values.get(dimension, 0.0))
        values[dimension] = clamp(raw * max_step, -max_step, max_step)
    return EmotionVector(values)


def apply_recovery_slowdown(previous: EmotionVector, applied: EmotionVector, config: DampeningConfig) -> EmotionVector:
    values: dict[str, float] = {}
    for dimension in EMOTION_DIMENSIONS:
        step = applied.get(dimension)
        old = previous.get(dimension)
        if old > 0 and step < 0 or old < 0 and step > 0:
            step *= config.recovery_slowdown
        values[dimension] = step
    return EmotionVector(values)

