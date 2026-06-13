"""Lean live-prompt mode (owner-private coherence rescue).

Measured baseline (real owner turn, 2026-06-14): a 4-char owner message produced
a 31,231-char system prompt. A mid-tier model drowns under that much always-on
meta-state and replies incoherently / out of character.

Lean mode keeps only what the model actually needs to answer the current message
in character and with continuity:
  - the persona identity block (kept once, from persona_runtime)
  - the recent conversation tail (continuity)
  - sidecars that carry *current-turn information* (who is speaking, recalled
    memory, an attachment, a correction, rich QQ context, a current uncertainty)
and drops the always-on internal meta-state (intention ecology, relation/turn
modulators, memory-coherence braids, initiative spine, self-state capsule,
duplicated persona, runtime presence, etc.).

It is gated behind XINYU_LEAN_PROMPT and defaults OFF, so the live path is
byte-identical to the legacy prompt until the owner flips it on to A/B the
difference in real chat.
"""

from __future__ import annotations

import os

LEAN_PROMPT_ENV = "XINYU_LEAN_PROMPT"
_TRUE_VALUES = {"1", "true", "yes", "on"}

# Sidecar names (see xinyu_bridge_turn_sidecar_state.py /
# xinyu_bridge_turn_sidecar_context.py) that carry genuine current-turn
# information the model needs. Everything not listed is internal meta-state and
# is dropped in lean mode regardless of its normal admission/required flag.
LEAN_SIDECAR_WHITELIST = frozenset(
    {
        "owner_address",
        "recalled_context",
        "owner_continuity_hint",
        "owner_active_corrections",
        "recent_attachment",
        "qq_rich_message",
        "qq_segmented_intent",
        "qq_current_turn_transport",
        "uncertainty_pause",
        "factual_time_correction",
    }
)


def lean_prompt_enabled() -> bool:
    return os.environ.get(LEAN_PROMPT_ENV, "").strip().lower() in _TRUE_VALUES


def lean_sidecar_admitted(name: str) -> bool:
    return name in LEAN_SIDECAR_WHITELIST
