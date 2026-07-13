"""Kernel-aware proactive scoring adjustments (read-only signals, review-gated outward)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_kernel_goal_bridge import read_kernel_pressure_signals


def read_proactive_kernel_gate(root: Path) -> dict[str, Any]:
    signals = read_kernel_pressure_signals(root)
    pending = int(signals.get("pending_review_count") or 0)
    slow = int(signals.get("slow_signal_count") or 0)
    structural = bool(signals.get("structural_impact_recent"))
    pressure = bool(signals.get("kernel_pressure"))

    emergence_level = "quiet"
    if structural:
        emergence_level = "kernel_structural_pressure"
    elif pending >= 3:
        emergence_level = "kernel_review_pressure"
    elif pressure or slow >= 3:
        emergence_level = "kernel_slow_signal_pressure"

    score_penalty = 0
    interruption_bonus = 0
    inbox_threshold_boost = 0
    send_threshold_boost = 0
    hold_non_urgent = False

    if structural:
        score_penalty += 18
        interruption_bonus += 12
        inbox_threshold_boost += 8
        send_threshold_boost += 18
        hold_non_urgent = True
    if pending >= 3:
        score_penalty += 14
        interruption_bonus += 8
        inbox_threshold_boost += 6
        send_threshold_boost += 12
        hold_non_urgent = True
    elif pending >= 1:
        score_penalty += 6
        inbox_threshold_boost += 3
        send_threshold_boost += 6
    if slow >= 3:
        score_penalty += 8
        interruption_bonus += 4
        inbox_threshold_boost += 4
        send_threshold_boost += 8
    elif pressure:
        score_penalty += 4
        inbox_threshold_boost += 2
        send_threshold_boost += 4

    return {
        "available": bool(signals.get("available")),
        "kernel_pressure": pressure,
        "pending_review_count": pending,
        "structural_impact_recent": structural,
        "slow_signal_count": slow,
        "emergence_level": emergence_level,
        "score_penalty": score_penalty,
        "interruption_bonus": interruption_bonus,
        "inbox_threshold_boost": inbox_threshold_boost,
        "send_threshold_boost": send_threshold_boost,
        "hold_non_urgent": hold_non_urgent,
    }


def merge_kernel_gate_into_context(context: dict[str, Any], kernel_gate: dict[str, Any]) -> dict[str, Any]:
    merged = dict(context)
    merged["kernel_gate"] = kernel_gate
    merged["kernel_emergence_level"] = kernel_gate.get("emergence_level", "quiet")
    merged["kernel_pending_review_count"] = kernel_gate.get("pending_review_count", 0)
    merged["kernel_structural_impact_recent"] = kernel_gate.get("structural_impact_recent", False)
    return merged