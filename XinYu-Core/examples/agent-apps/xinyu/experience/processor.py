"""Lightweight Experience Processor.

This module implements the first stage of turning raw events into
structured signals that can influence memory (importance) and future
belief/world-model updates.

Design constraints (from task):
- Simple rules + optional lightweight LLM judgment.
- No preset personality or emotion logic.
- Output must be easy to feed into the existing event sourcing pipeline.
- No heavy models.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

from .models import BeliefProposal, EventInput, ExperienceEnrichment, ExperienceResult


class LightweightJudge(Protocol):
    """Protocol for an optional lightweight judge.

    The callable receives the raw text (and optionally metadata) and
    should return a small dict with keys:
        - "importance_delta": int (-20 to +20)
        - "proposals": list[dict] with proposal_type, content, confidence
    It must be cheap and side-effect free.
    """
    def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]: ...


# Simple keyword sets for rule-based importance (kept minimal and explicit)
IMPORTANT_MARKERS = (
    "记住", "不要忘", "重要", "永远", "always", "remember", "never forget",
    "you must", "必须", "关键", "核心", "boundary", "底线",
)

PREFERENCE_MARKERS = (
    "喜欢", "讨厌", "prefer", "hate", "love", "不要", "别", "不要这样",
    "希望你", "希望我", "我希望",
)

FACT_LIKE_MARKERS = ("事实", "实际上", "其实", "true", "actually")


def _group_full_memory_pipeline_enabled() -> bool:
    raw = os.environ.get("XINYU_GROUP_FULL_MEMORY_PIPELINE", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return True


class ExperienceProcessor:
    """Main class for processing an event into experience signals."""

    def __init__(
        self,
        *,
        llm_judge: LightweightJudge | None = None,
        max_text_length: int = 2000,
    ) -> None:
        self.llm_judge = llm_judge
        self.max_text_length = max_text_length

    def process(self, event: dict[str, Any]) -> ExperienceResult:
        """Main entry point.

        Accepts a raw-ish event dict (from record_chat_event or similar)
        and returns structured experience output.
        """
        try:
            ev = EventInput.model_validate(event)
        except Exception as exc:  # pydantic validation failure should not crash caller
            return ExperienceResult(
                importance_score=10,
                notes=[f"input_validation_failed:{type(exc).__name__}"]
            )

        text = ev.raw_text[: self.max_text_length]
        if not text:
            return ExperienceResult(importance_score=0, notes=["empty_text"])

        score = self._rule_based_importance(ev, text)
        proposals: list[BeliefProposal] = self._rule_based_proposals(ev, text)
        notes: list[str] = []

        # Optional lightweight LLM pass
        if self.llm_judge is not None:
            try:
                judge_out = self.llm_judge(text, actor_scope=ev.actor_scope, source=ev.source_channel)
                delta = int(judge_out.get("importance_delta", 0))
                score = max(0, min(100, score + delta))
                notes.append("llm_judge_applied")

                for p in judge_out.get("proposals", [])[:3]:  # limit
                    try:
                        bp = BeliefProposal(
                            proposal_type=p.get("proposal_type", "other"),
                            content=str(p.get("content", ""))[:400],
                            confidence=float(p.get("confidence", 0.4)),
                            evidence_span=p.get("evidence_span"),
                        )
                        proposals.append(bp)
                    except Exception:
                        continue
            except Exception as exc:
                notes.append(f"llm_judge_error:{type(exc).__name__}")

        # Dedup proposals roughly
        seen = set()
        deduped: list[BeliefProposal] = []
        for p in proposals:
            key = (p.proposal_type, p.content[:60])
            if key not in seen:
                seen.add(key)
                deduped.append(p)
        proposals = deduped[:5]  # hard cap for lightness

        if score >= 70:
            notes.append("high_importance")
        elif score <= 15:
            notes.append("low_importance")

        return ExperienceResult(
            importance_score=score,
            belief_update_proposals=proposals,
            notes=notes,
        )

    def _rule_based_importance(self, ev: EventInput, text: str) -> int:
        """Pure rule-based importance scoring. No personality assumptions."""
        score = 25  # neutral base

        length = len(text)
        if length > 80:
            score += min(20, (length - 80) // 15)
        if length < 20:
            score -= 10

        # Actor importance
        if ev.actor_scope == "owner":
            score += 25
        elif ev.actor_scope in ("group_member", "non_owner"):
            score += 5

        # Marker boosts (explicit and limited)
        text_lower = text.lower()
        for marker in IMPORTANT_MARKERS:
            if marker.lower() in text_lower:
                score += 18
                break

        for marker in PREFERENCE_MARKERS:
            if marker.lower() in text_lower:
                score += 12
                break

        # Source channel adjustments (simple, not emotional)
        if ev.source_channel in ("qq_group", "group"):
            if _group_full_memory_pipeline_enabled():
                if ev.actor_scope == "owner":
                    score += 8
            else:
                score = int(score * 0.75)  # group chatter usually lower signal
        if "priority" in ev.source_channel:
            score += 10

        # Turn mode hint
        if "live" in ev.turn_mode.lower() or ev.turn_mode == "live_user_turn":
            score += 5

        return max(0, min(100, score))

    def _rule_based_proposals(self, ev: EventInput, text: str) -> list[BeliefProposal]:
        """Extract very conservative proposals from text using surface patterns."""
        proposals: list[BeliefProposal] = []
        text_lower = text.lower()

        # Very simple preference / boundary detection
        if ev.actor_scope == "owner":
            for marker in PREFERENCE_MARKERS:
                if marker.lower() in text_lower:
                    # Take a small window around the marker
                    idx = text_lower.find(marker.lower())
                    span = text[max(0, idx - 10): idx + 60].strip()
                    proposals.append(
                        BeliefProposal(
                            proposal_type="preference",
                            content=f"owner expressed: {span[:120]}",
                            confidence=0.55,
                            evidence_span=span[:80],
                        )
                    )
                    break  # one per call for lightness

            # Crude boundary signals
            if any(m in text_lower for m in ("不要", "别", "不要这样", "stop", "never")):
                span = text[:120]
                proposals.append(
                    BeliefProposal(
                        proposal_type="boundary",
                        content=f"owner signalled restriction: {span[:100]}",
                        confidence=0.48,
                        evidence_span=span[:60],
                    )
                )

        # Fact-like statements (very weak signal)
        if any(m in text_lower for m in FACT_LIKE_MARKERS):
            proposals.append(
                BeliefProposal(
                    proposal_type="fact",
                    content=text[:160],
                    confidence=0.35,
                    evidence_span=text[:80],
                )
            )

        # Self-observation style (owner talking about "you")
        if ev.actor_scope == "owner" and ("你" in text or "you " in text_lower):
            if len(text) > 30:
                proposals.append(
                    BeliefProposal(
                        proposal_type="self_observation",
                        content=f"owner addressed xinyu: {text[:100]}",
                        confidence=0.40,
                    )
                )

        return proposals

    def to_enrichment(self, result: ExperienceResult, base_salience: int | None = None) -> ExperienceEnrichment:
        """Helper to produce data suitable for merging into existing event structures."""
        return ExperienceEnrichment(
            salience=base_salience,
            experience_importance=result.importance_score,
            belief_proposals=[p.model_dump() for p in result.belief_update_proposals],
            processor_notes=result.notes,
        )
