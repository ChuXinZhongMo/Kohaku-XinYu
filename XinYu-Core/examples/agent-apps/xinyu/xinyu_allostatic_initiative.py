"""Allostatic initiative helpers (H1 / Cards 2–5).

Model-free signals for proactive motivation:
- predicted deviation (social/continuity deficit forecast)
- prediction-error (PE) stress mediator
- stick (non-adapting deficit) / carrot (brief satiety after success)

Does not implement biological cortisol. Pure engineering control signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class AllostaticSignals:
    predicted_deviation: float  # 0..1 higher = more need to act
    pe_stress: float  # 0..1 surprisal / prediction error
    stick_deficit: float  # 0..1 non-adapting need-fill drive
    satiety: float  # 0..1 post-success suppression
    speak_threshold_boost: int  # added to proactive speak_threshold
    allow_idle_speak: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "predicted_deviation": self.predicted_deviation,
            "pe_stress": self.pe_stress,
            "stick_deficit": self.stick_deficit,
            "satiety": self.satiety,
            "speak_threshold_boost": self.speak_threshold_boost,
            "allow_idle_speak": self.allow_idle_speak,
            "reason": self.reason,
        }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _parse_iso(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        ts = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        return ts.astimezone()
    return ts


def compute_satiety(
    *,
    last_success_at: str | datetime | None = None,
    satiety_minutes: float = 45.0,
    now: datetime | None = None,
) -> float:
    """Brief post-success satiety (carrot adapts fast). 1.0 = fully sated / suppress."""
    if last_success_at is None or last_success_at == "":
        return 0.0
    if isinstance(last_success_at, datetime):
        ts = last_success_at
        if ts.tzinfo is None:
            ts = ts.astimezone()
    else:
        ts = _parse_iso(str(last_success_at))
    if ts is None:
        return 0.0
    current = now or datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.astimezone()
    elapsed = (current - ts).total_seconds() / 60.0
    window = max(1.0, float(satiety_minutes))
    if elapsed >= window:
        return 0.0
    return _clamp01(1.0 - (elapsed / window))


def compute_predicted_deviation(
    *,
    hours_since_owner: float = 0.0,
    open_threads: int = 0,
    concrete_pending: bool = False,
    has_finding: bool = False,
) -> float:
    """Forecast social/continuity deficit without requiring an LLM."""
    idle = _clamp01(float(hours_since_owner) / 24.0)  # 24h idle → 1.0
    threads = _clamp01(float(open_threads) / 5.0)
    base = 0.55 * idle + 0.25 * threads
    if concrete_pending and has_finding:
        base += 0.35
    elif has_finding:
        base += 0.2
    elif concrete_pending:
        base += 0.1
    return _clamp01(base)


def compute_pe_stress(
    *,
    predicted_deviation: float,
    last_outcome_ok: bool | None = None,
    repeated_failure_count: int = 0,
) -> float:
    """Surprisal-like stress: high when prediction and outcome diverge or fails stack."""
    pe = float(predicted_deviation)
    if last_outcome_ok is False:
        pe = max(pe, 0.55)
    if last_outcome_ok is True and predicted_deviation < 0.3:
        pe *= 0.5  # better-than-expected calms
    pe += min(0.3, 0.08 * max(0, int(repeated_failure_count)))
    return _clamp01(pe)


def evaluate_allostatic_signals(
    *,
    source: str = "",
    has_finding: bool = False,
    concrete_question: str = "",
    hours_since_owner: float = 0.0,
    open_threads: int = 0,
    last_success_at: str | datetime | None = None,
    last_outcome_ok: bool | None = None,
    repeated_failure_count: int = 0,
    satiety_minutes: float = 45.0,
    now: datetime | None = None,
) -> AllostaticSignals:
    concrete = bool(str(concrete_question or "").strip())
    predicted = compute_predicted_deviation(
        hours_since_owner=hours_since_owner,
        open_threads=open_threads,
        concrete_pending=concrete,
        has_finding=has_finding,
    )
    satiety = compute_satiety(
        last_success_at=last_success_at,
        satiety_minutes=satiety_minutes,
        now=now,
    )
    pe = compute_pe_stress(
        predicted_deviation=predicted,
        last_outcome_ok=last_outcome_ok,
        repeated_failure_count=repeated_failure_count,
    )
    # Stick: non-adapting deficit — does not decay with satiety alone when finding+concrete.
    stick = predicted
    if has_finding and concrete:
        stick = max(stick, 0.6)
    stick = _clamp01(stick * (1.0 - 0.7 * satiety))

    src = str(source or "").strip().lower()
    boost = 0
    allow_idle = True
    reason = "allostatic_ok"

    # High satiety raises speak bar (carrot brief).
    if satiety >= 0.5:
        boost += 1
        reason = "satiety_suppress"

    # Low predicted deviation + no finding → hard silence for idle sources.
    if src in {"owner_long_idle", "owner_long_idle_v0"}:
        if not has_finding or not concrete:
            allow_idle = False
            reason = "idle_no_finding"
        elif predicted < 0.35 and pe < 0.4:
            allow_idle = False
            boost += 1
            reason = "low_predicted_deviation"
        elif satiety >= 0.6:
            allow_idle = False
            reason = "satiety_idle"

    # Very high PE with finding: slightly lower bar (urgency), but never empty concrete.
    if pe >= 0.75 and has_finding and concrete and satiety < 0.4:
        boost = max(0, boost - 1)
        if reason == "allostatic_ok":
            reason = "pe_urgency"

    return AllostaticSignals(
        predicted_deviation=predicted,
        pe_stress=pe,
        stick_deficit=stick,
        satiety=satiety,
        speak_threshold_boost=int(boost),
        allow_idle_speak=allow_idle,
        reason=reason,
    )
