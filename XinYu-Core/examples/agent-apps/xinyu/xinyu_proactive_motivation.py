"""Model-free proactive motivation gate (Inner-Thoughts shape, XinYu-native).

Scores 1–5 heuristics; speak only if max score high enough AND concrete payload.
owner_long_idle never interrupts / never speaks without concrete finding.

H1 (2026-07-17): optional allostatic signals (predicted deviation, PE stress,
stick/carrot satiety) raise the speak bar or force silence without empty pings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from xinyu_silence_reasons import EMPTY_CONCRETE, NO_FINDING, OWNER_LONG_IDLE_SILENT


@dataclass(frozen=True)
class MotivationDecision:
    speak: bool
    score: float
    reason: str
    heuristics: dict[str, int]
    allostatic: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "speak": self.speak,
            "score": self.score,
            "reason": self.reason,
            "heuristics": dict(self.heuristics),
        }
        if self.allostatic is not None:
            payload["allostatic"] = dict(self.allostatic)
        return payload


def _clamp_score(value: int) -> int:
    return max(1, min(5, int(value)))


def evaluate_proactive_motivation(
    *,
    source: str = "",
    concrete_question: str = "",
    has_finding: bool = False,
    relevance: int = 3,
    info_gap: int = 3,
    expected_impact: int = 3,
    urgency: int = 2,
    coherence: int = 3,
    speak_threshold: int = 4,
    # Optional H1 allostatic inputs (all default-off compatible).
    hours_since_owner: float | None = None,
    open_threads: int = 0,
    last_success_at: str | datetime | None = None,
    last_outcome_ok: bool | None = None,
    repeated_failure_count: int = 0,
    satiety_minutes: float = 45.0,
    use_allostatic: bool = True,
) -> MotivationDecision:
    heuristics = {
        "relevance": _clamp_score(relevance),
        "info_gap": _clamp_score(info_gap),
        "expected_impact": _clamp_score(expected_impact),
        "urgency": _clamp_score(urgency),
        "coherence": _clamp_score(coherence),
    }
    top = float(max(heuristics.values()))
    concrete = str(concrete_question or "").strip()
    src = str(source or "").strip().lower()
    allo_dict: dict[str, Any] | None = None
    effective_threshold = int(speak_threshold)

    if use_allostatic and (
        hours_since_owner is not None
        or last_success_at is not None
        or last_outcome_ok is not None
        or repeated_failure_count
        or open_threads
    ):
        from xinyu_allostatic_initiative import evaluate_allostatic_signals

        signals = evaluate_allostatic_signals(
            source=src,
            has_finding=has_finding,
            concrete_question=concrete,
            hours_since_owner=float(hours_since_owner or 0.0),
            open_threads=int(open_threads or 0),
            last_success_at=last_success_at,
            last_outcome_ok=last_outcome_ok,
            repeated_failure_count=int(repeated_failure_count or 0),
            satiety_minutes=float(satiety_minutes),
        )
        allo_dict = signals.as_dict()
        effective_threshold = int(speak_threshold) + int(signals.speak_threshold_boost)
        # Stick can lift urgency heuristic when deficit high and finding present.
        if signals.stick_deficit >= 0.7 and has_finding and concrete:
            heuristics["urgency"] = _clamp_score(max(heuristics["urgency"], 4))
            top = float(max(heuristics.values()))
        if src in {"owner_long_idle", "owner_long_idle_v0"} and not signals.allow_idle_speak:
            return MotivationDecision(
                speak=False,
                score=top,
                reason=OWNER_LONG_IDLE_SILENT
                if not concrete
                else signals.reason or OWNER_LONG_IDLE_SILENT,
                heuristics=heuristics,
                allostatic=allo_dict,
            )

    if src in {"owner_long_idle", "owner_long_idle_v0"}:
        # Policy: empty idle never speaks.
        if not concrete:
            return MotivationDecision(
                speak=False,
                score=top,
                reason=OWNER_LONG_IDLE_SILENT,
                heuristics=heuristics,
                allostatic=allo_dict,
            )
        # Even with text, idle pings need finding-level substance.
        if not has_finding and len(concrete) < 8:
            return MotivationDecision(
                speak=False,
                score=top,
                reason=EMPTY_CONCRETE,
                heuristics=heuristics,
                allostatic=allo_dict,
            )

    if not concrete:
        return MotivationDecision(
            speak=False,
            score=top,
            reason=EMPTY_CONCRETE,
            heuristics=heuristics,
            allostatic=allo_dict,
        )

    if not has_finding and src in {"private_ecosystem", "browse", "reflection"}:
        return MotivationDecision(
            speak=False,
            score=top,
            reason=NO_FINDING,
            heuristics=heuristics,
            allostatic=allo_dict,
        )

    if top < effective_threshold:
        return MotivationDecision(
            speak=False,
            score=top,
            reason="below_speak_threshold",
            heuristics=heuristics,
            allostatic=allo_dict,
        )

    return MotivationDecision(
        speak=True,
        score=top,
        reason="speak",
        heuristics=heuristics,
        allostatic=allo_dict,
    )
