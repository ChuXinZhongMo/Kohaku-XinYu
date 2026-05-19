"""Adapters between legacy emotion files and v1 vectors."""

from __future__ import annotations

import re
from pathlib import Path

from .models import EmotionState, EmotionVector


LEGACY_HINTS: tuple[tuple[str, str, float], ...] = (
    ("hurt", "hurt", 0.35),
    ("guarded", "guardedness", 0.28),
    ("fatigue", "fatigue", 0.25),
    ("warm", "warmth", 0.22),
    ("trust", "trust", 0.22),
    ("curious", "curiosity", 0.2),
    ("irritat", "irritation", 0.25),
    ("anger", "anger", 0.28),
    ("angry", "anger", 0.28),
    ("annoy", "annoyance", 0.26),
    ("aversion", "aversion", 0.28),
    ("disgust", "disgust", 0.28),
    ("dislike", "dislike", 0.22),
    ("resent", "resentment", 0.24),
    ("distance", "distance_impulse", 0.22),
    ("conflict", "conflict", 0.25),
    ("受伤", "hurt", 0.35),
    ("防备", "guardedness", 0.3),
    ("疲惫", "fatigue", 0.25),
    ("亲近", "warmth", 0.25),
    ("信任", "trust", 0.24),
    ("生气", "anger", 0.3),
    ("烦", "annoyance", 0.26),
    ("反感", "aversion", 0.28),
    ("厌恶", "disgust", 0.3),
    ("嫌弃", "dislike", 0.26),
    ("想保持距离", "distance_impulse", 0.25),
    ("想沉默", "silence_impulse", 0.22),
    ("想反驳", "pushback_impulse", 0.22),
)


def read_legacy_emotion(path: Path, *, timestamp: str) -> EmotionState:
    try:
        text = path.read_text(encoding="utf-8-sig").lower()
    except OSError:
        return EmotionState.neutral(timestamp)
    values: dict[str, float] = {}
    for marker, dimension, score in LEGACY_HINTS:
        if marker.lower() in text:
            values[dimension] = max(values.get(dimension, 0.0), score)
    for match in re.finditer(r"(?m)^-\s*([a-z_]+):\s*(-?\d+(?:\.\d+)?)", text):
        dimension = match.group(1)
        try:
            values[dimension] = max(-1.0, min(1.0, float(match.group(2))))
        except ValueError:
            continue
    return EmotionState(vector=EmotionVector(values).normalized(), updated_at=timestamp)
