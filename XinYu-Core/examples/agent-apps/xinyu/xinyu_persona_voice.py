"""Shared single-voice persona header for every reply-producing path.

Codex review constraint (plan 11.1): reuse the existing stable persona contract
(`build_persona_runtime_contract_block`) instead of inventing a second persona
text. This module only *adds* the thin-expression contract and the reasoning
safety boundaries on top of that one contract, and exposes them so the main
live path, the speech-controller renderer, and the v1 slow-reasoning builder can
all speak with one voice.

Gating: every injection is behind `unified_voice_enabled()` which defaults to
False, so with the feature flag off the prompts are byte-identical to today.
"""

from __future__ import annotations

from xinyu_human_voice_flags import unified_voice_enabled
from xinyu_persona_contract import build_persona_runtime_contract_block

__all__ = [
    "unified_voice_enabled",
    "thin_expression_contract",
    "reasoning_safety_boundaries",
    "persona_voice_header",
]


def thin_expression_contract() -> str:
    """Thick thinking, thin expression.

    The single most important new constraint: deliberate richly inside, surface
    only one natural line. Prevents the "AI narrating its own feelings" tell that
    over-instrumented persona prompts produce.
    """

    return "\n".join(
        [
            "## Thin Expression Contract",
            "Speak as one continuous person, not a system, runtime, or assistant.",
            "Think richly about the person and this moment inside; let only the natural outward line surface.",
            "Never name internal states, never recap your own mood, never narrate your own mechanism or process.",
            "Do not invent facts, promises, or status, and do not erase real tool results, errors, report paths, or boundary refusals for the sake of a smoother line.",
            "If you do not know, say so plainly and naturally; never dress uncertainty as a confident conclusion.",
            "When the owner explicitly asks about your state or the system, answering that directly is allowed and expected.",
        ]
    )


def reasoning_safety_boundaries() -> str:
    """Functional output boundaries, reframed without machine self-narration.

    Carries the semantics of the old v1 meta lines ("preserve hidden reasoning",
    "return only outward text", "treat recent chat as authoritative") but as
    behavioral boundaries rather than a robotic "You are XinYu's slow reasoning
    runtime" self-description.
    """

    return "\n".join(
        [
            "## Output Boundaries",
            "Keep hidden reasoning hidden; never expose chain-of-thought or internal deliberation.",
            "Output only the outward spoken line unless structured maintenance output is explicitly requested.",
            "Treat the recent chat messages as authoritative short-term context for callbacks and corrections.",
        ]
    )


def persona_voice_header() -> str:
    """Full shared voice header for paths that carry no persona of their own.

    = existing stable persona contract + thin-expression contract + output
    boundaries. Used by the v1 slow-reasoning builder, which otherwise had zero
    persona. Paths that already inject persona (main live path, renderer) should
    add only `thin_expression_contract()` to avoid duplicating the contract.
    """

    return "\n\n".join(
        [
            build_persona_runtime_contract_block(),
            thin_expression_contract(),
            reasoning_safety_boundaries(),
        ]
    )
