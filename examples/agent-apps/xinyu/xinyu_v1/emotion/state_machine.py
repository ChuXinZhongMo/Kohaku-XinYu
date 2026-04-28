"""Continuous emotion state machine."""

from __future__ import annotations

from dataclasses import dataclass

from .dampening import DampeningConfig, apply_recovery_slowdown, damp_delta
from .models import EmotionDelta, EmotionState, EmotionTransition
from .vector_math import add, decay_toward_neutral, distance


@dataclass(slots=True)
class EmotionStateMachine:
    config: DampeningConfig = DampeningConfig()

    def apply(self, state: EmotionState, delta: EmotionDelta, *, timestamp: str) -> EmotionTransition:
        try:
            decayed = decay_toward_neutral(state.vector, self.config.decay_factor)
            damped = damp_delta(delta, self.config)
            slowed = apply_recovery_slowdown(state.vector, damped, self.config)
            updated_vector = add(decayed, slowed).normalized()
            movement = distance(state.vector, updated_vector)
            notes = [f"movement:{movement:.3f}", f"reason:{delta.reason or 'unspecified'}"]
            if delta.salience >= 0.75:
                notes.append("high_salience")
            current = EmotionState(
                vector=updated_vector,
                updated_at=timestamp,
                inertia=state.inertia,
                residue_notes=tuple((*state.residue_notes[-8:], *notes[-2:])),
                version=state.version,
            )
            return EmotionTransition(previous=state, current=current, delta=delta, applied_delta=slowed, notes=tuple(notes))
        except Exception as exc:
            fallback = EmotionState(vector=state.vector.normalized(), updated_at=timestamp, inertia=state.inertia)
            return EmotionTransition(
                previous=state,
                current=fallback,
                delta=delta,
                applied_delta=damp_delta(EmotionDelta({}, reason="fallback"), self.config),
                notes=("emotion_update_failed", str(exc)),
            )

