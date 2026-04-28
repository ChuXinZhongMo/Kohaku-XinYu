"""Bounded vector operations for emotion state."""

from __future__ import annotations

import math

from .models import EMOTION_DIMENSIONS, EmotionVector


def clamp(value: float, minimum: float = -1.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def add(left: EmotionVector, right: EmotionVector) -> EmotionVector:
    return EmotionVector({dimension: clamp(left.get(dimension) + right.get(dimension)) for dimension in EMOTION_DIMENSIONS})


def scale(vector: EmotionVector, factor: float) -> EmotionVector:
    return EmotionVector({dimension: clamp(vector.get(dimension) * factor) for dimension in EMOTION_DIMENSIONS})


def blend(previous: EmotionVector, target: EmotionVector, alpha: float) -> EmotionVector:
    safe_alpha = max(0.0, min(1.0, alpha))
    return EmotionVector(
        {
            dimension: clamp(previous.get(dimension) * (1.0 - safe_alpha) + target.get(dimension) * safe_alpha)
            for dimension in EMOTION_DIMENSIONS
        }
    )


def distance(left: EmotionVector, right: EmotionVector) -> float:
    total = 0.0
    for dimension in EMOTION_DIMENSIONS:
        diff = left.get(dimension) - right.get(dimension)
        total += diff * diff
    return math.sqrt(total)


def decay_toward_neutral(vector: EmotionVector, factor: float) -> EmotionVector:
    safe_factor = max(0.0, min(1.0, factor))
    return EmotionVector({dimension: vector.get(dimension) * safe_factor for dimension in EMOTION_DIMENSIONS})

