"""Stable silence / suppress reason codes for proactive and life-reply paths."""

from __future__ import annotations

from typing import Iterable

# Stable string constants — scorecard and autonomy reports should reuse these.
EMPTY_CONCRETE = "empty_concrete"
COOLDOWN = "cooldown"
OWNER_LONG_IDLE_SILENT = "owner_long_idle_silent"
NO_FINDING = "no_finding"
GATE_BLOCKED = "gate_blocked"
RISK_HIGH = "risk_high"
DUPLICATE = "duplicate"
EXPIRED = "expired"
NATURAL_VOICE_SUPPRESS = "natural_voice_suppress"

ALL_REASONS = frozenset(
    {
        EMPTY_CONCRETE,
        COOLDOWN,
        OWNER_LONG_IDLE_SILENT,
        NO_FINDING,
        GATE_BLOCKED,
        RISK_HIGH,
        DUPLICATE,
        EXPIRED,
        NATURAL_VOICE_SUPPRESS,
    }
)


def normalize_silence_reason(reason: str) -> str:
    text = str(reason or "").strip().lower().replace(" ", "_")
    if text in ALL_REASONS:
        return text
    # Soft aliases
    if "empty" in text and "concrete" in text:
        return EMPTY_CONCRETE
    if "idle" in text:
        return OWNER_LONG_IDLE_SILENT
    if "finding" in text or "no_finding" in text:
        return NO_FINDING
    if "cooldown" in text:
        return COOLDOWN
    if "duplicate" in text or "dedupe" in text:
        return DUPLICATE
    if "expir" in text:
        return EXPIRED
    if "risk" in text:
        return RISK_HIGH
    if "gate" in text or "block" in text:
        return GATE_BLOCKED
    return text or GATE_BLOCKED


def silence_explain_rate(reasons: Iterable[str]) -> float:
    items = [normalize_silence_reason(r) for r in reasons if str(r or "").strip()]
    if not items:
        return 0.0
    known = sum(1 for r in items if r in ALL_REASONS)
    return known / len(items)
