"""Emotion vector models."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..types import JSONValue


EMOTION_DIMENSIONS: tuple[str, ...] = (
    "warmth",
    "trust",
    "hurt",
    "guardedness",
    "curiosity",
    "fatigue",
    "attachment",
    "conflict",
    "irritation",
    "stability",
    "volatility",
    "openness",
)


@dataclass(frozen=True, slots=True)
class EmotionVector:
    values: dict[str, float] = field(default_factory=dict)

    @classmethod
    def neutral(cls) -> "EmotionVector":
        return cls({dimension: 0.0 for dimension in EMOTION_DIMENSIONS})

    def get(self, dimension: str) -> float:
        return float(self.values.get(dimension, 0.0))

    def normalized(self) -> "EmotionVector":
        return EmotionVector(
            {
                dimension: max(-1.0, min(1.0, float(self.values.get(dimension, 0.0))))
                for dimension in EMOTION_DIMENSIONS
            }
        )

    def to_json(self) -> dict[str, JSONValue]:
        return {dimension: self.get(dimension) for dimension in EMOTION_DIMENSIONS}


@dataclass(frozen=True, slots=True)
class EmotionDelta:
    values: dict[str, float]
    salience: float = 0.0
    reason: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def normalized(self) -> "EmotionDelta":
        return EmotionDelta(
            values={dimension: max(-1.0, min(1.0, float(value))) for dimension, value in self.values.items()},
            salience=max(0.0, min(1.0, self.salience)),
            reason=self.reason,
            tags=self.tags,
        )


@dataclass(frozen=True, slots=True)
class EmotionState:
    vector: EmotionVector
    updated_at: str
    inertia: float = 0.72
    residue_notes: tuple[str, ...] = field(default_factory=tuple)
    version: int = 1

    @classmethod
    def neutral(cls, timestamp: str) -> "EmotionState":
        return cls(vector=EmotionVector.neutral(), updated_at=timestamp)

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "inertia": self.inertia,
            "vector": self.vector.to_json(),
            "residue_notes": list(self.residue_notes),
        }


@dataclass(frozen=True, slots=True)
class EmotionTransition:
    previous: EmotionState
    current: EmotionState
    delta: EmotionDelta
    applied_delta: EmotionVector
    notes: tuple[str, ...] = field(default_factory=tuple)

