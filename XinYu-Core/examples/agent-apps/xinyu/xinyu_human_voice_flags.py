"""Env-resolved gates for the human-voice unification (plan §4.4).

These mirror `FeatureFlags.human_voice_*` and are read directly from the
environment so the many prompt/route/pipeline helpers that do not carry the
config object stay consistent without threading config through every layer.
All default False => behavior is byte-identical to the pre-change runtime.
"""

from __future__ import annotations

import os

_UNIFIED_VOICE_ENV = "XINYU_HUMAN_VOICE_UNIFIED_PROMPT"
_BYPASS_MODEL_ENV = "XINYU_HUMAN_VOICE_BYPASS_MODEL"
_REGEN_PIPELINE_ENV = "XINYU_HUMAN_VOICE_REGEN_PIPELINE"


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def unified_voice_enabled() -> bool:
    """Inject the shared single-voice header into every prompt path."""

    return _env_bool(_UNIFIED_VOICE_ENV, False)


def bypass_model_enabled() -> bool:
    """Let semantic-fast / pre-model bypass routes render through the model
    instead of emitting a pre-baked canned constant."""

    return _env_bool(_BYPASS_MODEL_ENV, False)


def regen_pipeline_enabled() -> bool:
    """Let the slow-live post-processing regenerate (via the existing async
    empty-recovery) instead of substituting a fixed string."""

    return _env_bool(_REGEN_PIPELINE_ENV, False)
