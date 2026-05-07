"""Continuous emotion state for XinYu v1."""

from __future__ import annotations

from .models import EmotionDelta, EmotionState, EmotionVector
from .state_machine import EmotionStateMachine

__all__ = ["EmotionDelta", "EmotionState", "EmotionStateMachine", "EmotionVector"]

