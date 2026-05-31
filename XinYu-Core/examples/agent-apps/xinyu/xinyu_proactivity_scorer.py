from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from xinyu_runtime_failure_freshness import (
    codex_delegate_failure_active as _codex_delegate_failure_active,
    parse_inline_fields as _parse_inline_fields,
    runtime_failure_counts_active as _runtime_failure_counts_active,
)
from xinyu_proactive_contract import (
    PROACTIVE_SOURCE_TYPES,
    PROACTIVE_URGENT_SOURCE_TYPES,
    should_surface_runtime_error,
)


TRACE_REL = Path("memory/context/proactive_decision_trace.jsonl")
STATE_REL = Path("memory/context/proactive_decision_state.md")
CONTEXT_REL = Path("memory/context/proactive_decision_context.md")

DEFAULT_EXPIRES_SECONDS = 86400
RECENT_TRACE_SCAN_LINES = 200
STYLE_REPAIR_REALTIME_CAP_THRESHOLD = 8

SOURCE_TYPES = set(PROACTIVE_SOURCE_TYPES)

THRESHOLDS: dict[str, tuple[int, int | None]] = {
    "task_failed": (45, 70),
    "runtime_error": (45, 70),
    "task_done": (50, 75),
    "reflection_question": (55, 90),
    "style_repair": (55, 90),
    "dream_residue": (60, 95),
    "owner_long_idle": (70, None),
}

COOLDOWN_SECONDS: dict[str, int] = {
    "task_done": 1800,
    "task_failed": 1800,
    "runtime_error": 1800,
    "reflection_question": 21600,
    "style_repair": 21600,
    "dream_residue": 86400,
    "owner_long_idle": 43200,
}

POSITIVE_BASES: dict[str, dict[str, int]] = {
    "task_failed": {
        "utility_score": 48,
        "urgency_score": 38,
        "owner_relevance": 38,
        "novelty_score": 18,
        "inner_pressure": 12,
    },
    "runtime_error": {
        "utility_score": 50,
        "urgency_score": 36,
        "owner_relevance": 34,
        "novelty_score": 16,
        "inner_pressure": 12,
    },
    "task_done": {
        "utility_score": 42,
        "urgency_score": 24,
        "owner_relevance": 42,
        "novelty_score": 20,
        "inner_pressure": 8,
    },
    "reflection_question": {
        "utility_score": 28,
        "urgency_score": 12,
        "owner_relevance": 34,
        "novelty_score": 26,
        "inner_pressure": 25,
    },
    "style_repair": {
        "utility_score": 32,
        "urgency_score": 14,
        "owner_relevance": 44,
        "novelty_score": 22,
        "inner_pressure": 24,
    },
    "dream_residue": {
        "utility_score": 12,
        "urgency_score": 6,
        "owner_relevance": 22,
        "novelty_score": 38,
        "inner_pressure": 36,
    },
    "owner_long_idle": {
        "utility_score": 8,
        "urgency_score": 5,
        "owner_relevance": 22,
        "novelty_score": 14,
        "inner_pressure": 25,
    },
}

FLAVOR_PENALTY = {
    "dream_residue": 16,
    "owner_long_idle": 20,
    "style_repair": 8,
    "reflection_question": 6,
}

URGENT_TYPES = set(PROACTIVE_URGENT_SOURCE_TYPES)
EMOTION_OR_DREAM_TYPES = {"dream_residue", "style_repair", "owner_long_idle"}
FINAL_PROACTIVE_REQUEST_STATUSES = {
    "answered",
    "sent",
    "expired",
    "dismissed",
    "read_locally",
    "replied",
    "failed",
    "blocked",
    "none",
}
MEANINGFUL_PROACTIVE_REQUEST_STATUSES = {"ready", "candidate_only", "active", "claimed"}

INTERNAL_VISIBLE_RE = re.compile(
    r"(?i)(\bcodex\b|source_seed|source_seeds|dream_weight|stdout|stderr|traceback|"
    r"\btool[_ -]?call\b|\btool[_ -]?output\b|[a-z]:\\|\\\\|/users/|/home/)"
)
LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bxinyu[_-]?(?:api[_-]?key|bridge[_-]?token)\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)

FIELD_RE = re.compile(r"(?m)^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
FRONTMATTER_RE = re.compile(r"(?m)^\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")


@dataclass(frozen=True)
class ProactiveCandidate:
    candidate_id: str
    source_type: str
    source_ref: str
    intent_type: str
    owner_visible_text: str
    content_preview: str
    utility_hint: str
    emotional_weight: int
    novelty_hint: str
    confidence: int
    risk_flags: tuple[str, ...]
    created_at: str
    expires_at: str


@dataclass(frozen=True)
class ProactivityScore:
    utility_score: int
    urgency_score: int
    owner_relevance: int
    novelty_score: int
    inner_pressure: int
    interruption_cost: int
    repetition_penalty: int
    uncertainty_penalty: int
    flavor_penalty: int
    stale_penalty: int
    total_score: int
    confidence: int
    hard_blocks: tuple[str, ...]
    reasons_positive: tuple[str, ...]
    reasons_negative: tuple[str, ...]


@dataclass(frozen=True)
class ProactiveDecision:
    decision_id: str
    checked_at: str
    candidate_id: str
    candidate_signature: str
    source_type: str
    intent_type: str
    content_preview: str
    total_score: int
    recommendation: str
    preferred_channel: str
    shadow_only: bool
    hard_blocks: tuple[str, ...]
    reasons_positive: tuple[str, ...]
    reasons_negative: tuple[str, ...]
    next_review_after: str
    score: ProactivityScore
    candidate: ProactiveCandidate


def run_proactivity_scorer_shadow(
    root: Path,
    *,
    checked_at: str | None = None,
    gate_context: dict[str, Any] | None = None,
    max_candidates: int = 8,
) -> dict[str, Any]:
    root = root.resolve()
    checked_at = _timestamp_or_now_iso(checked_at)
    candidates = collect_proactive_candidates(root, checked_at=checked_at)
    if not candidates:
        _write_state(root, checked_at=checked_at, decisions=[], notes=["no_candidates"])
        return {
            "accepted": True,
            "status": "no_candidates",
            "checked_at": checked_at,
            "candidate_count": 0,
            "decision_count": 0,
            "notes": ["no_candidates"],
        }

    context = _build_gate_context(root, checked_at=checked_at, overrides=gate_context or {})
    previous_signatures = _load_recent_candidate_signatures(root / TRACE_REL)
    decisions: list[ProactiveDecision] = []
    for candidate in candidates[: max(1, int(max_candidates))]:
        score = score_proactive_candidate(
            candidate,
            checked_at=checked_at,
            gate_context=context,
            previous_signatures=previous_signatures,
        )
        decision = decide_proactive_candidate(candidate, score, checked_at=checked_at, gate_context=context)
        decisions.append(decision)

    decisions.sort(key=_decision_sort_key, reverse=True)
    _write_state(root, checked_at=checked_at, decisions=decisions, notes=[])
    for decision in reversed(decisions):
        _append_trace(root, decision)
    latest = decisions[0]
    return {
        "accepted": True,
        "status": latest.recommendation,
        "checked_at": checked_at,
        "candidate_count": len(candidates),
        "decision_count": len(decisions),
        "decision_id": latest.decision_id,
        "candidate_id": latest.candidate_id,
        "source_type": latest.source_type,
        "intent_type": latest.intent_type,
        "total_score": latest.total_score,
        "recommendation": latest.recommendation,
        "preferred_channel": latest.preferred_channel,
        "shadow_only": latest.shadow_only,
        "hard_blocks": list(latest.hard_blocks),
        "reasons_positive": list(latest.reasons_positive),
        "reasons_negative": list(latest.reasons_negative),
        "notes": ["shadow_only"],
    }


def collect_proactive_candidates(root: Path, *, checked_at: str | None = None) -> list[ProactiveCandidate]:
    root = root.resolve()
    checked_at = _timestamp_or_now_iso(checked_at)
    candidates: list[ProactiveCandidate] = []

    _extend(candidates, _candidate_from_proactive_request(root, checked_at=checked_at))
    _extend(candidates, _candidate_from_self_thought(root, checked_at=checked_at))
    _extend(candidates, _candidates_from_runtime_program_awareness(root, checked_at=checked_at))
    _extend(candidates, _candidate_from_dream_output(root, checked_at=checked_at))
    _extend(candidates, _candidate_from_dream_log(root, checked_at=checked_at))
    _extend(candidates, _candidate_from_reflection_queue(root, checked_at=checked_at))
    _extend(candidates, _candidate_from_qq_outbox_dispatch(root, checked_at=checked_at))
    _extend(candidates, _candidate_from_owner_long_idle(root, checked_at=checked_at))

    deduped: list[ProactiveCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        signature = candidate_signature(candidate)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(candidate)
    deduped.sort(key=_candidate_sort_key, reverse=True)
    return deduped


def score_proactive_candidate(
    candidate: ProactiveCandidate,
    *,
    checked_at: str,
    gate_context: dict[str, Any] | None = None,
    previous_signatures: set[str] | None = None,
) -> ProactivityScore:
    gate_context = gate_context or {}
    previous_signatures = previous_signatures or set()
    source_type = _known_source_type(candidate.source_type)
    base = POSITIVE_BASES.get(source_type, POSITIVE_BASES["reflection_question"])

    utility_score = _clamp(base["utility_score"] + _hint_bonus(candidate.utility_hint, ("owner", "task", "failed")))
    urgency_score = _clamp(base["urgency_score"] + _hint_bonus(candidate.utility_hint, ("urgent", "error", "failed")))
    owner_relevance = _clamp(base["owner_relevance"] + _hint_bonus(candidate.utility_hint, ("owner", "private")))
    novelty_score = _clamp(base["novelty_score"] + _hint_bonus(candidate.novelty_hint, ("new", "latest", "fresh")))
    inner_pressure = _clamp(base["inner_pressure"] + int(candidate.emotional_weight / 10))

    interruption_cost = _interruption_cost(gate_context, source_type)
    repetition_penalty = 35 if candidate_signature(candidate) in previous_signatures else 0
    uncertainty_penalty = max(0, int((100 - _clamp(candidate.confidence)) / 2))
    if "uncertain_source" in candidate.risk_flags:
        uncertainty_penalty += 12
    flavor_penalty = FLAVOR_PENALTY.get(source_type, 0)
    stale_penalty = _stale_penalty(candidate, checked_at=checked_at)

    hard_blocks = _hard_blocks(candidate, gate_context=gate_context, checked_at=checked_at)

    total = _clamp(
        utility_score
        + urgency_score
        + owner_relevance
        + novelty_score
        + inner_pressure
        - interruption_cost
        - repetition_penalty
        - uncertainty_penalty
        - flavor_penalty
        - stale_penalty
    )
    positive_reasons = _score_reasons(
        {
            "utility_score": utility_score,
            "urgency_score": urgency_score,
            "owner_relevance": owner_relevance,
            "novelty_score": novelty_score,
            "inner_pressure": inner_pressure,
        }
    )
    negative_reasons = _score_reasons(
        {
            "interruption_cost": interruption_cost,
            "repetition_penalty": repetition_penalty,
            "uncertainty_penalty": uncertainty_penalty,
            "flavor_penalty": flavor_penalty,
            "stale_penalty": stale_penalty,
        }
    )
    if hard_blocks:
        negative_reasons = tuple(dict.fromkeys((*negative_reasons, *hard_blocks)))
    return ProactivityScore(
        utility_score=utility_score,
        urgency_score=urgency_score,
        owner_relevance=owner_relevance,
        novelty_score=novelty_score,
        inner_pressure=inner_pressure,
        interruption_cost=_clamp(interruption_cost),
        repetition_penalty=_clamp(repetition_penalty),
        uncertainty_penalty=_clamp(uncertainty_penalty),
        flavor_penalty=_clamp(flavor_penalty),
        stale_penalty=_clamp(stale_penalty),
        total_score=total,
        confidence=_clamp(candidate.confidence),
        hard_blocks=tuple(hard_blocks),
        reasons_positive=positive_reasons,
        reasons_negative=negative_reasons,
    )


def decide_proactive_candidate(
    candidate: ProactiveCandidate,
    score: ProactivityScore,
    *,
    checked_at: str,
    gate_context: dict[str, Any] | None = None,
) -> ProactiveDecision:
    source_type = _known_source_type(candidate.source_type)
    recommendation = _threshold_recommendation(source_type, score.total_score)
    hard_blocks = list(score.hard_blocks)

    if "owner_visible_text_internal_marker" in hard_blocks:
        recommendation = "drop"
    elif _has_hold_block(hard_blocks):
        recommendation = "hold"
    elif source_type == "dream_residue" and recommendation == "send_now":
        recommendation = "inbox"
    elif source_type == "owner_long_idle" and recommendation == "send_now":
        recommendation = "inbox"

    preferred_channel = _preferred_channel(source_type, recommendation, hard_blocks)
    decision = ProactiveDecision(
        decision_id="prodecision-" + _timestamp_id(checked_at) + "-" + _short_hash(candidate.candidate_id)[:8],
        checked_at=checked_at,
        candidate_id=candidate.candidate_id,
        candidate_signature=candidate_signature(candidate),
        source_type=source_type,
        intent_type=_clean_token(candidate.intent_type or source_type),
        content_preview=_clip(candidate.content_preview, 180),
        total_score=score.total_score,
        recommendation=recommendation,
        preferred_channel=preferred_channel,
        shadow_only=True,
        hard_blocks=tuple(dict.fromkeys(hard_blocks)),
        reasons_positive=score.reasons_positive,
        reasons_negative=score.reasons_negative,
        next_review_after=_next_review_after(source_type, recommendation, checked_at=checked_at, gate_context=gate_context or {}),
        score=score,
        candidate=candidate,
    )
    return decision


def candidate_signature(candidate: ProactiveCandidate) -> str:
    raw = "|".join(
        (
            _known_source_type(candidate.source_type),
            _clean_token(candidate.source_ref),
            _short_hash(f"{candidate.owner_visible_text}|{candidate.content_preview}", length=16),
        )
    )
    return "prosig:" + _short_hash(raw, length=24)


def _candidate_from_proactive_request(root: Path, *, checked_at: str) -> ProactiveCandidate | None:
    text = _read_text(root / "memory/context/proactive_request_state.md")
    if not text:
        return None
    fields = _parse_fields(text)
    status = _clean_token(fields.get("status", "none")).lower()
    if status in FINAL_PROACTIVE_REQUEST_STATUSES and status not in MEANINGFUL_PROACTIVE_REQUEST_STATUSES:
        return None
    kind = _clean_token(fields.get("kind", "none")).lower()
    focus_kind = _clean_token(fields.get("focus_kind", "none")).lower()
    source_type = _source_type_from_kind(kind, focus_kind, fields.get("evidence_label", ""))
    question = _extract_value_raw(text, "concrete_question", fields.get("concrete_question", ""))
    if not _meaningful(question):
        question = _extract_value_raw(text, "evidence_label", fields.get("evidence_label", ""))
    if not _meaningful(question):
        return None
    source_ref = fields.get("request_id") or fields.get("evidence_hash") or "proactive_request"
    confidence = 78 if status in {"ready", "candidate_only"} else 62
    risk_flags = _risk_flags(source_type, question)
    return _make_candidate(
        source_type=source_type,
        source_ref=f"proactive_request:{source_ref}",
        intent_type=kind or source_type,
        owner_visible_text=question,
        content_preview=question,
        utility_hint=fields.get("evidence_label", ""),
        emotional_weight=_emotional_weight_for(source_type, fields),
        novelty_hint=fields.get("focus_label", ""),
        confidence=confidence,
        risk_flags=risk_flags,
        created_at=fields.get("created_at") or checked_at,
        checked_at=checked_at,
    )


def _candidate_from_self_thought(root: Path, *, checked_at: str) -> ProactiveCandidate | None:
    text = _read_text(root / "memory/context/self_thought_state.md")
    if not text:
        return None
    fields = _parse_fields(text)
    focus_kind = _clean_token(fields.get("focus_kind", "none")).lower()
    intention = _clean_token(fields.get("intention", "none")).lower()
    status = _clean_token(fields.get("status", "none")).lower()
    evidence = _extract_value_raw(text, "evidence_label", fields.get("evidence_label", ""))
    concrete = _extract_value_raw(text, "concrete_question", fields.get("concrete_question", ""))
    private_summary = _extract_value_raw(text, "private_summary", fields.get("private_summary", ""))
    source_type = _source_type_from_kind(intention, focus_kind, f"{evidence} {private_summary} {status}")

    owner_text = concrete if _meaningful(concrete) else ""
    if not owner_text:
        owner_text = _owner_safe_text_for_source(source_type, fields, private_summary or evidence)
    preview = _first_meaningful(concrete, private_summary, evidence, fields.get("focus_label", ""))
    if not _meaningful(preview):
        return None
    confidence = 74 if fields.get("candidate_enabled", "").lower() == "true" else 58
    if status in {"blocked", "none"}:
        confidence -= 8
    return _make_candidate(
        source_type=source_type,
        source_ref=f"self_thought:{fields.get('pass_id') or fields.get('evidence_hash') or focus_kind}",
        intent_type=intention or source_type,
        owner_visible_text=owner_text or preview,
        content_preview=preview,
        utility_hint=evidence or private_summary,
        emotional_weight=_emotional_weight_for(source_type, fields),
        novelty_hint=fields.get("focus_label", ""),
        confidence=confidence,
        risk_flags=_risk_flags(source_type, owner_text or preview),
        created_at=fields.get("checked_at") or fields.get("updated_at") or checked_at,
        checked_at=checked_at,
    )


def _candidates_from_runtime_program_awareness(root: Path, *, checked_at: str) -> list[ProactiveCandidate]:
    text = _read_text(root / "memory/context/runtime_program_awareness.md")
    if not text:
        return []
    candidates: list[ProactiveCandidate] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        label, detail = stripped[2:].split(":", 1)
        label = _clean_token(label)
        detail = _one_line(detail)
        lowered = detail.lower()
        if label == "codex_delegate":
            if "status=finished" in lowered:
                candidates.append(
                    _make_candidate(
                        source_type="task_done",
                        source_ref="runtime_program_awareness:codex_delegate",
                        intent_type="report_completion",
                        owner_visible_text="A delegated task finished.",
                        content_preview=detail,
                        utility_hint="owner delegated task finished",
                        emotional_weight=10,
                        novelty_hint=detail,
                        confidence=82,
                        risk_flags=(),
                        created_at=_timestamp_or_now_iso(checked_at),
                        checked_at=checked_at,
                    )
                )
            elif "status=failed" in lowered or "timed_out=true" in lowered or "timed_out" in lowered:
                inline_fields = _parse_inline_fields(detail)
                if not _codex_delegate_failure_active(inline_fields, checked_at=checked_at):
                    continue
                candidates.append(
                    _make_candidate(
                        source_type="task_failed",
                        source_ref="runtime_program_awareness:codex_delegate",
                        intent_type="report_failure",
                        owner_visible_text="A delegated task failed or timed out.",
                        content_preview=detail,
                        utility_hint="owner delegated task failed",
                        emotional_weight=20,
                        novelty_hint=detail,
                        confidence=84,
                        risk_flags=(),
                        created_at=_timestamp_or_now_iso(checked_at),
                        checked_at=checked_at,
                    )
                )
        elif label in {"expression_self_learning", "learning_closed_loop", "persona_feedback"}:
            if any(marker in lowered for marker in ("failure_kind=", "repair_signal=true", "trial_active")):
                candidates.append(
                    _make_candidate(
                        source_type="style_repair",
                        source_ref=f"runtime_program_awareness:{label}",
                        intent_type="style_repair",
                        owner_visible_text="A reply-style repair signal is waiting.",
                        content_preview=detail,
                        utility_hint="owner-facing style repair",
                        emotional_weight=35,
                        novelty_hint=detail,
                        confidence=72,
                        risk_flags=("emotional_or_style",),
                        created_at=_timestamp_or_now_iso(checked_at),
                        checked_at=checked_at,
                    )
                )
        elif "status=error" in lowered or "last_error=" in lowered or "adapter_error=" in lowered:
            if "last_error=none" in lowered or "adapter_error=none" in lowered:
                continue
            if not should_surface_runtime_error(label=label, detail=detail):
                continue
            candidates.append(
                _make_candidate(
                    source_type="runtime_error",
                    source_ref=f"runtime_program_awareness:{label}",
                    intent_type="runtime_error",
                    owner_visible_text="A runtime subsystem reported an error.",
                    content_preview=detail,
                    utility_hint="runtime error visible in state mirror",
                    emotional_weight=8,
                    novelty_hint=detail,
                    confidence=76,
                    risk_flags=(),
                    created_at=_timestamp_or_now_iso(checked_at),
                    checked_at=checked_at,
                )
            )
        elif re.search(r"\b(?:failure_count|failed_count|dead_count|recent_failed_count|recent_dead_count)=[1-9]", lowered):
            inline_fields = _parse_inline_fields(detail)
            if not _runtime_failure_counts_active(inline_fields, checked_at=checked_at):
                continue
            candidates.append(
                _make_candidate(
                    source_type="runtime_error",
                    source_ref=f"runtime_program_awareness:{label}",
                    intent_type="runtime_error",
                    owner_visible_text="A runtime queue has failures.",
                    content_preview=detail,
                    utility_hint="runtime failure count",
                    emotional_weight=8,
                    novelty_hint=detail,
                    confidence=75,
                    risk_flags=(),
                    created_at=_timestamp_or_now_iso(checked_at),
                    checked_at=checked_at,
                )
            )
    return candidates


def _candidate_from_dream_output(root: Path, *, checked_at: str) -> ProactiveCandidate | None:
    text = _read_text(root / "memory/dreams/dream_output_state.md")
    if not text:
        return None
    fields = _parse_fields(text)
    dream_id = fields.get("dream_id") or fields.get("seed_id") or "latest_dream_output"
    if not _meaningful(dream_id) and fields.get("reflection_candidate", "").lower() != "yes":
        return None
    preview = _first_meaningful(
        fields.get("dream_surface", ""),
        fields.get("residue", ""),
        fields.get("theme", ""),
        fields.get("waking_residue", ""),
        dream_id,
    )
    if not _meaningful(preview):
        return None
    return _make_candidate(
        source_type="dream_residue",
        source_ref=f"dream_output:{dream_id}",
        intent_type="dream_residue_review",
        owner_visible_text="A dream residue is available for review.",
        content_preview=preview,
        utility_hint=fields.get("theme", "dream residue"),
        emotional_weight=_safe_int(fields.get("emotional_weight"), 60),
        novelty_hint=dream_id,
        confidence=_safe_int(fields.get("confidence_score"), 72),
        risk_flags=("dream_or_emotion", "qq_send_disabled_for_dream_v0"),
        created_at=fields.get("produced_at") or fields.get("updated_at") or checked_at,
        checked_at=checked_at,
    )


def _candidate_from_dream_log(root: Path, *, checked_at: str) -> ProactiveCandidate | None:
    text = _read_text(root / "memory/dreams/dream_log.md")
    if not text:
        return None
    section_id, section = _latest_heading_section(text, "dream-")
    if not section:
        return None
    fields = _parse_fields(section)
    preview = _first_meaningful(
        fields.get("dream_surface", ""),
        fields.get("waking_residue", ""),
        fields.get("retained_after_waking", ""),
        section_id,
    )
    if not _meaningful(preview):
        return None
    return _make_candidate(
        source_type="dream_residue",
        source_ref=f"dream_log:{section_id or fields.get('source_seed', 'latest')}",
        intent_type="dream_residue_review",
        owner_visible_text="A dream residue is available for review.",
        content_preview=preview,
        utility_hint=fields.get("reflection_priority", "dream residue"),
        emotional_weight=_safe_int(fields.get("dream_weight_after"), 66),
        novelty_hint=section_id,
        confidence=70,
        risk_flags=("dream_or_emotion", "qq_send_disabled_for_dream_v0"),
        created_at=fields.get("dreamed_at") or checked_at,
        checked_at=checked_at,
    )


def _candidate_from_reflection_queue(root: Path, *, checked_at: str) -> ProactiveCandidate | None:
    text = _read_text(root / "memory/reflection/reflection_queue.md")
    if not text:
        return None
    section_id, section = _latest_heading_section(text, "item-")
    if not section:
        return None
    fields = _parse_fields(section)
    topic = fields.get("topic", "")
    if not _meaningful(topic):
        return None
    source_type = "dream_residue" if "dream" in fields.get("source", "").lower() else "reflection_question"
    return _make_candidate(
        source_type=source_type,
        source_ref=f"reflection_queue:{section_id}",
        intent_type="reflection_review",
        owner_visible_text="A reflection topic is waiting.",
        content_preview=topic,
        utility_hint=fields.get("priority", ""),
        emotional_weight=55 if fields.get("priority", "").lower() == "high" else 35,
        novelty_hint=section_id,
        confidence=68,
        risk_flags=_risk_flags(source_type, "A reflection topic is waiting."),
        created_at=fields.get("updated_at") or checked_at,
        checked_at=checked_at,
    )


def _candidate_from_qq_outbox_dispatch(root: Path, *, checked_at: str) -> ProactiveCandidate | None:
    text = _read_text(root / "memory/context/qq_outbox_dispatch_state.md")
    if not text:
        return None
    fields = _parse_fields(text)
    failed = _safe_int(fields.get("failed_count"), 0)
    dead = _safe_int(fields.get("dead_count"), 0)
    if failed + dead <= 0:
        return None
    if not _runtime_failure_counts_active(fields, checked_at=checked_at):
        return None
    return _make_candidate(
        source_type="task_failed",
        source_ref="qq_outbox_dispatch_state",
        intent_type="dispatch_failure",
        owner_visible_text="A queued outbound message failed to dispatch.",
        content_preview=f"failed_count={failed} dead_count={dead} last_event={fields.get('last_event', 'unknown')}",
        utility_hint="outbound dispatch failure",
        emotional_weight=5,
        novelty_hint=fields.get("last_message_id", ""),
        confidence=86,
        risk_flags=(),
        created_at=fields.get("updated_at") or checked_at,
        checked_at=checked_at,
    )


def _candidate_from_owner_long_idle(root: Path, *, checked_at: str) -> ProactiveCandidate | None:
    text = _read_text(root / "memory/context/interaction_journal_state.md")
    if not text:
        return None
    fields = _parse_fields(text)
    minutes = _safe_int(fields.get("minutes_since_last_owner_private"), -1)
    if minutes < 720:
        return None
    return _make_candidate(
        source_type="owner_long_idle",
        source_ref=f"interaction_journal:{fields.get('last_owner_private_at', 'unknown')}",
        intent_type="owner_long_idle",
        owner_visible_text="Owner has been away for a long time.",
        content_preview=f"minutes_since_last_owner_private={minutes}",
        utility_hint="owner long idle",
        emotional_weight=30,
        novelty_hint=fields.get("last_owner_private_at", ""),
        confidence=65,
        risk_flags=("owner_long_idle_send_blocked_v0", "emotional_or_style"),
        created_at=_timestamp_or_now_iso(checked_at),
        checked_at=checked_at,
    )


def _make_candidate(
    *,
    source_type: str,
    source_ref: str,
    intent_type: str,
    owner_visible_text: str,
    content_preview: str,
    utility_hint: str,
    emotional_weight: int,
    novelty_hint: str,
    confidence: int,
    risk_flags: tuple[str, ...],
    created_at: str,
    checked_at: str,
) -> ProactiveCandidate:
    source_type = _known_source_type(source_type)
    safe_preview = _clip(content_preview, 240)
    owner_visible = _clip(_scrub_text(owner_visible_text), 180)
    created = _normalize_iso(created_at) or checked_at
    source_ref = _clean_ref(source_ref)
    candidate_id = (
        "proshadow-"
        + _timestamp_id(checked_at)
        + "-"
        + _short_hash(f"{source_type}|{source_ref}|{owner_visible}|{safe_preview}", length=10)
    )
    return ProactiveCandidate(
        candidate_id=candidate_id,
        source_type=source_type,
        source_ref=source_ref,
        intent_type=_clean_token(intent_type or source_type),
        owner_visible_text=owner_visible,
        content_preview=safe_preview,
        utility_hint=_clip(utility_hint, 120),
        emotional_weight=_clamp(emotional_weight),
        novelty_hint=_clip(novelty_hint, 120),
        confidence=_clamp(confidence),
        risk_flags=tuple(dict.fromkeys(_clean_token(flag) for flag in risk_flags if _clean_token(flag))),
        created_at=_timestamp_or_now_iso(created),
        expires_at=_plus_seconds(created, DEFAULT_EXPIRES_SECONDS),
    )


def _build_gate_context(root: Path, *, checked_at: str, overrides: dict[str, Any]) -> dict[str, Any]:
    context_text = _read_text(root / CONTEXT_REL)
    context = _parse_fields(context_text)
    interaction = _parse_fields(_read_text(root / "memory/context/interaction_journal_state.md"))
    proactive_request = _parse_fields(_read_text(root / "memory/context/proactive_request_state.md"))
    proactive_dispatch = _parse_fields(_read_text(root / "memory/context/proactive_qq_dispatch_state.md"))
    runtime_presence = _parse_fields(_read_text(root / "memory/context/runtime_self_presence.md"))
    style_repair_realtime_pressure = _style_repair_realtime_pressure_status(root)

    owner_recent_minutes = _safe_int(
        context.get("owner_recent_private_minutes"),
        _safe_int(interaction.get("minutes_since_last_owner_private"), 999),
    )
    if owner_recent_minutes == 999 and interaction.get("last_owner_private_at"):
        owner_recent_minutes = _minutes_since(interaction.get("last_owner_private_at", ""), checked_at, default=999)
    last_sent = (
        context.get("last_proactive_sent_at")
        or proactive_dispatch.get("last_acked_at")
        or proactive_dispatch.get("updated_at")
        or ""
    )
    if proactive_request.get("last_ack_status", "").lower() == "sent":
        last_sent = last_sent or proactive_request.get("updated_at", "")
    last_owner_reply = context.get("last_owner_reply_to_proactive_at") or proactive_request.get("owner_replied_at") or ""
    unanswered_default = 0
    if proactive_request.get("status", "").lower() in {"ready", "sent", "claimed"} and not last_owner_reply:
        unanswered_default = 1

    merged: dict[str, Any] = {
        "owner_recent_private_minutes": owner_recent_minutes,
        "desktop_active": _as_bool(context.get("desktop_active"), default=False),
        "system_idle_state": context.get("system_idle_state") or runtime_presence.get("current_turn_state") or "unknown",
        "screen_locked": _as_bool(context.get("screen_locked"), default=False),
        "fullscreen": _as_bool(context.get("fullscreen"), default=False),
        "quiet_hours": _as_bool(context.get("quiet_hours"), default=False),
        "last_proactive_sent_at": last_sent,
        "last_owner_reply_to_proactive_at": last_owner_reply,
        "unanswered_proactive_count": _safe_int(
            context.get("unanswered_proactive_count"), unanswered_default
        ),
        "same_type_last_sent_at": context.get("same_type_last_sent_at", ""),
        "same_type_cooldown_active": _as_bool(context.get("same_type_cooldown_active"), default=False),
        "owner_recently_rejected": _as_bool(context.get("owner_recently_rejected"), default=False)
        or _owner_recently_rejected(proactive_request),
        "style_repair_realtime_pressure": style_repair_realtime_pressure,
    }
    merged.update(overrides)
    return merged


def _style_repair_realtime_pressure_status(root: Path) -> str:
    learning_text = _read_text(root / "memory/self/learning_closed_loop_state.md")
    if learning_text:
        learning = _parse_fields(learning_text)
        latest_failure = _one_line(learning.get("latest_failure_kind")).lower()
        if latest_failure != "owner_reported_template_voice_failure":
            return "normal"
        repair_count = _safe_int(learning.get("repair_count"), 0)
        success_streak = _safe_int(learning.get("success_streak"), 0)
        trial_success_streak = _safe_int(learning.get("trial_success_streak"), success_streak)
        success_evidence = _one_line(learning.get("success_evidence_status"))
        if (
            repair_count >= STYLE_REPAIR_REALTIME_CAP_THRESHOLD
            and trial_success_streak < 2
            and success_evidence != "same_trial_explicit_owner_success"
        ):
            return "capped_direct_failure_only"
        return "normal"

    owner_feedback = _parse_fields(_read_text(root / "memory/context/owner_feedback_effect_state.md"))
    effect_status = _one_line(owner_feedback.get("realtime_pressure_status")).lower()
    if effect_status not in {"", "none", "unknown", "missing"}:
        return effect_status
    return "normal"


def _hard_blocks(candidate: ProactiveCandidate, *, gate_context: dict[str, Any], checked_at: str) -> list[str]:
    blocks: list[str] = []
    if INTERNAL_VISIBLE_RE.search(candidate.owner_visible_text or ""):
        blocks.append("owner_visible_text_internal_marker")
    if _as_bool(gate_context.get("screen_locked"), default=False) and (
        candidate.source_type in EMOTION_OR_DREAM_TYPES or "dream_or_emotion" in candidate.risk_flags
    ):
        blocks.append("screen_locked_emotion_or_dream_hold")
    if _as_bool(gate_context.get("quiet_hours"), default=False) and candidate.source_type not in URGENT_TYPES:
        blocks.append("quiet_hours_non_urgent_hold")
    if _safe_int(gate_context.get("unanswered_proactive_count"), 0) >= 2:
        blocks.append("unanswered_proactive_limit_hold")
    if _as_bool(gate_context.get("same_type_cooldown_active"), default=False):
        blocks.append("same_type_cooldown_active_hold")
    elif _same_type_cooldown_active(candidate, gate_context, checked_at=checked_at):
        blocks.append("same_type_cooldown_active_hold")
    if _as_bool(gate_context.get("owner_recently_rejected"), default=False):
        blocks.append("owner_recently_rejected_hold")
    if (
        candidate.source_type == "style_repair"
        and _one_line(gate_context.get("style_repair_realtime_pressure")).lower() == "capped_direct_failure_only"
    ):
        blocks.append("style_repair_realtime_pressure_capped_hold")
    if candidate.source_type == "dream_residue":
        blocks.append("qq_send_disabled_for_dream_v0")
    if candidate.source_type == "owner_long_idle":
        blocks.append("qq_send_disabled_for_owner_long_idle_v0")
    if _stale_penalty(candidate, checked_at=checked_at) >= 80:
        blocks.append("candidate_expired_drop")
    return blocks


def _interruption_cost(gate_context: dict[str, Any], source_type: str) -> int:
    cost = 0
    recent_minutes = _safe_int(gate_context.get("owner_recent_private_minutes"), 999)
    if recent_minutes < 10:
        cost += 30
    elif recent_minutes < 30:
        cost += 18
    elif recent_minutes < 60:
        cost += 8
    if _as_bool(gate_context.get("desktop_active"), default=False):
        cost += 4
    if _as_bool(gate_context.get("fullscreen"), default=False):
        cost += 18
    if _as_bool(gate_context.get("screen_locked"), default=False):
        cost += 10
    if _as_bool(gate_context.get("quiet_hours"), default=False) and source_type not in URGENT_TYPES:
        cost += 22
    if source_type in URGENT_TYPES:
        cost = max(0, cost - 18)
    return _clamp(cost)


def _threshold_recommendation(source_type: str, total_score: int) -> str:
    inbox_threshold, send_threshold = THRESHOLDS.get(source_type, (60, 85))
    if send_threshold is not None and total_score >= send_threshold:
        return "send_now"
    if total_score >= inbox_threshold:
        return "inbox"
    if total_score >= 35:
        return "hold"
    return "drop"


def _preferred_channel(source_type: str, recommendation: str, hard_blocks: list[str]) -> str:
    if recommendation == "send_now":
        if source_type in {"dream_residue", "owner_long_idle"}:
            return "inbox"
        return "qq"
    if recommendation == "inbox":
        return "inbox"
    if recommendation == "hold":
        return "silent"
    return "silent"


def _has_hold_block(hard_blocks: list[str]) -> bool:
    if "owner_visible_text_internal_marker" in hard_blocks or "candidate_expired_drop" in hard_blocks:
        return False
    return any(block.endswith("_hold") for block in hard_blocks)


def _same_type_cooldown_active(candidate: ProactiveCandidate, gate_context: dict[str, Any], *, checked_at: str) -> bool:
    last = str(gate_context.get("same_type_last_sent_at") or "").strip()
    if not last:
        return False
    elapsed = _seconds_between(last, checked_at)
    if elapsed is None:
        return False
    return elapsed < COOLDOWN_SECONDS.get(candidate.source_type, 3600)


def _stale_penalty(candidate: ProactiveCandidate, *, checked_at: str) -> int:
    if _seconds_between(candidate.expires_at, checked_at) is not None and _seconds_between(candidate.expires_at, checked_at) > 0:
        return 85
    age = _seconds_between(candidate.created_at, checked_at)
    if age is None:
        return 8
    if age > 172800:
        return 35
    if age > 86400:
        return 18
    return 0


def _source_type_from_kind(kind: str, focus_kind: str, context: str) -> str:
    combined = f"{kind} {focus_kind} {context}".lower()
    if "dream" in combined:
        return "dream_residue"
    if "failed" in combined or "failure" in combined or "timeout" in combined or "timed_out" in combined:
        return "task_failed"
    if "runtime_error" in combined or "adapter_error" in combined or "error" in combined:
        return "runtime_error"
    if "report_completion" in combined or "completion" in combined or "finished" in combined or "done" in combined:
        return "task_done"
    if "style" in combined or "repair" in combined or "template" in combined or "expression" in combined:
        return "style_repair"
    if "reflection" in combined or "clarify" in combined or "ask_owner" in combined:
        return "reflection_question"
    if "owner_long_idle" in combined:
        return "owner_long_idle"
    return "reflection_question"


def _owner_safe_text_for_source(source_type: str, fields: dict[str, str], fallback: str) -> str:
    if source_type == "task_done":
        return "A delegated task finished."
    if source_type == "task_failed":
        return "A delegated task failed or timed out."
    if source_type == "runtime_error":
        return "A runtime subsystem reported an error."
    if source_type == "dream_residue":
        return "A dream residue is available for review."
    if source_type == "style_repair":
        return "A reply-style repair signal is waiting."
    if source_type == "owner_long_idle":
        return "Owner has been away for a long time."
    return fallback or "A reflection topic is waiting."


def _risk_flags(source_type: str, text: str) -> tuple[str, ...]:
    flags: list[str] = []
    if source_type == "dream_residue":
        flags.extend(["dream_or_emotion", "qq_send_disabled_for_dream_v0"])
    if source_type == "owner_long_idle":
        flags.extend(["owner_long_idle_send_blocked_v0", "emotional_or_style"])
    if source_type == "style_repair":
        flags.append("emotional_or_style")
    if INTERNAL_VISIBLE_RE.search(text or ""):
        flags.append("owner_visible_text_internal_marker")
    return tuple(dict.fromkeys(flags))


def _emotional_weight_for(source_type: str, fields: dict[str, str]) -> int:
    for key in ("emotional_weight", "dream_weight_after", "importance_score", "impact_score"):
        if key in fields:
            return _safe_int(fields.get(key), 50)
    if source_type == "dream_residue":
        return 70
    if source_type in {"style_repair", "reflection_question"}:
        return 45
    return 10


def _write_state(root: Path, *, checked_at: str, decisions: list[ProactiveDecision], notes: list[str]) -> None:
    latest = decisions[0] if decisions else None
    lines: list[str] = [
        "---",
        "title: Proactive Decision State",
        "memory_type: proactive_decision_state",
        "time_scope: short_term",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: xinyu_proactivity_scorer",
        f"updated_at: {_timestamp_or_now_iso(checked_at)}",
        "status: active",
        "tags: [proactive, shadow, scorer, decision]",
        "---",
        "",
        "# Proactive Decision State",
        "",
        "## Latest Shadow Decision",
    ]
    if latest is None:
        lines.extend(
            [
                f"- checked_at: {_timestamp_or_now_iso(checked_at)}",
                "- candidate_id: none",
                "- source_type: none",
                "- preview: none",
                "- total_score: 0",
                "- recommendation: hold",
                "- preferred_channel: silent",
                "- shadow_only: true",
                "- hard_blocks: none",
                "- positive: none",
                "- negative: none",
                "- next_review_after: none",
                "",
                "## Notes",
                *[f"- {note}" for note in notes],
            ]
        )
    else:
        lines.extend(
            [
                f"- checked_at: {_timestamp_or_now_iso(latest.checked_at)}",
                f"- decision_id: {latest.decision_id}",
                f"- candidate_id: {latest.candidate_id}",
                f"- source_type: {latest.source_type}",
                f"- intent_type: {latest.intent_type}",
                f"- preview: {_clip(latest.candidate.owner_visible_text, 180)}",
                f"- total_score: {latest.total_score}",
                f"- recommendation: {latest.recommendation}",
                f"- preferred_channel: {latest.preferred_channel}",
                "- shadow_only: true",
                f"- hard_blocks: {_join_or_none(latest.hard_blocks)}",
                f"- positive: {_join_or_none(latest.reasons_positive)}",
                f"- negative: {_join_or_none(latest.reasons_negative)}",
                f"- next_review_after: {latest.next_review_after}",
                "",
                "## Score",
                f"- utility_score: {latest.score.utility_score}",
                f"- urgency_score: {latest.score.urgency_score}",
                f"- owner_relevance: {latest.score.owner_relevance}",
                f"- novelty_score: {latest.score.novelty_score}",
                f"- inner_pressure: {latest.score.inner_pressure}",
                f"- interruption_cost: {latest.score.interruption_cost}",
                f"- repetition_penalty: {latest.score.repetition_penalty}",
                f"- uncertainty_penalty: {latest.score.uncertainty_penalty}",
                f"- flavor_penalty: {latest.score.flavor_penalty}",
                f"- stale_penalty: {latest.score.stale_penalty}",
                "",
                "## Recent Shadow Decisions",
            ]
        )
        for decision in decisions[:5]:
            lines.append(
                "- "
                + " ".join(
                    [
                        f"checked_at={_timestamp_or_now_iso(decision.checked_at)}",
                        f"source_type={decision.source_type}",
                        f"total_score={decision.total_score}",
                        f"recommendation={decision.recommendation}",
                        f"preferred_channel={decision.preferred_channel}",
                    ]
                )
            )
    lines.extend(
        [
            "",
            "## Boundaries",
            "- shadow_only: true",
            "- no_qq_enqueue: true",
            "- no_gateway_bypass: true",
            "- no_dispatch_claim_or_ack_change: true",
            "- dream_residue_qq_send_blocked_v0: true",
            "- owner_long_idle_qq_send_blocked_v0: true",
            "",
        ]
    )
    _write_text_atomic(root / STATE_REL, "\n".join(lines))


def _append_trace(root: Path, decision: ProactiveDecision) -> None:
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    event = _decision_to_json(decision)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _decision_to_json(decision: ProactiveDecision) -> dict[str, Any]:
    data = {
        "event_kind": "proactive_decision",
        "observed_at": _timestamp_or_now_iso(decision.checked_at),
        "status": decision.recommendation,
        "reason": ",".join(decision.reasons_positive[:3]),
        "notes": list(decision.hard_blocks),
        **asdict(decision),
    }
    data["score"] = asdict(decision.score)
    data["candidate"] = asdict(decision.candidate)
    return _clean_json_value(data)


def _load_recent_candidate_signatures(path: Path) -> set[str]:
    signatures: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return signatures
    for line in lines[-RECENT_TRACE_SCAN_LINES:]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        signature = str(data.get("candidate_signature") or "").strip()
        if signature:
            signatures.add(signature)
    return signatures


def _decision_sort_key(decision: ProactiveDecision) -> tuple[int, int]:
    recommendation_rank = {"send_now": 4, "inbox": 3, "hold": 2, "drop": 1}.get(decision.recommendation, 0)
    return recommendation_rank, decision.total_score


def _candidate_sort_key(candidate: ProactiveCandidate) -> tuple[int, int, int]:
    source_rank = {
        "task_failed": 7,
        "runtime_error": 6,
        "task_done": 5,
        "style_repair": 4,
        "reflection_question": 3,
        "dream_residue": 2,
        "owner_long_idle": 1,
    }.get(candidate.source_type, 0)
    return source_rank, candidate.confidence, candidate.emotional_weight


def _next_review_after(
    source_type: str,
    recommendation: str,
    *,
    checked_at: str,
    gate_context: dict[str, Any],
) -> str:
    if recommendation == "drop":
        return "none"
    seconds = COOLDOWN_SECONDS.get(source_type, 3600)
    if recommendation == "send_now":
        seconds = min(seconds, 1800)
    elif recommendation == "inbox":
        seconds = min(seconds, 21600)
    return _plus_seconds(checked_at, seconds)


def _latest_heading_section(text: str, prefix: str) -> tuple[str, str]:
    matches = list(re.finditer(rf"(?m)^##\s+({re.escape(prefix)}[^\r\n]+)\s*$", text))
    if not matches:
        return "", ""
    match = matches[-1]
    next_match = None
    for candidate in matches:
        if candidate.start() > match.start():
            next_match = candidate
            break
    end = next_match.start() if next_match else len(text)
    return match.group(1).strip(), text[match.end() : end]


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in FRONTMATTER_RE.finditer(text or ""):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key and value:
            fields[key] = _scrub_text(value)
    for match in FIELD_RE.finditer(text or ""):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key and value:
            fields[key] = _scrub_text(value)
    return fields


def _extract_value_raw(text: str, field: str, default: str = "") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(field)}:\s*(.*?)\s*$", text or "")
    return _scrub_text(match.group(1)) if match else _scrub_text(default)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, str):
        return _scrub_text(value)
    return value


def _owner_recently_rejected(fields: dict[str, str]) -> bool:
    text = " ".join(
        [
            fields.get("owner_reply_preview", ""),
            fields.get("last_owner_reply_preview", ""),
            fields.get("feedback", ""),
        ]
    ).lower()
    return any(marker in text for marker in ("annoy", "stop sending", "do not send", "template", "meaningless"))


def _score_reasons(scores: dict[str, int]) -> tuple[str, ...]:
    return tuple(name for name, value in scores.items() if value > 0)


def _hint_bonus(text: str, markers: tuple[str, ...]) -> int:
    lowered = (text or "").lower()
    return 6 if any(marker in lowered for marker in markers) else 0


def _known_source_type(value: str) -> str:
    clean = _clean_token(value)
    return clean if clean in SOURCE_TYPES else "reflection_question"


def _first_meaningful(*values: str) -> str:
    for value in values:
        if _meaningful(value):
            return _scrub_text(value)
    return ""


def _meaningful(value: Any) -> bool:
    text = _one_line(value).lower()
    return text not in {"", "none", "unknown", "false", "null"}


def _clean_ref(value: Any) -> str:
    text = _scrub_text(value)
    text = re.sub(r"[^A-Za-z0-9_.:/#-]+", "_", text).strip("_")
    return _clip(text or "unknown", 120)


def _clean_token(value: Any) -> str:
    text = _one_line(value).lower()
    text = re.sub(r"[^a-z0-9_.:-]+", "_", text).strip("_")
    return text or "none"


def _one_line(value: Any) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def _scrub_text(value: Any) -> str:
    text = _one_line(value)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[redacted-secret]", text)
    text = LOCAL_PATH_RE.sub("[local-path]", text)
    return text


def _clip(value: Any, limit: int = 160) -> str:
    text = _scrub_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _clamp(value: Any, lo: int = 0, hi: int = 100) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0
    return max(lo, min(hi, number))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "enabled"}:
        return True
    if text in {"0", "false", "no", "off", "disabled", ""}:
        return False
    return default


def _normalize_iso(value: Any) -> str:
    text = _one_line(value)
    if not text:
        return ""
    parsed = _parse_iso(text)
    if parsed is None:
        return ""
    return parsed.astimezone().isoformat()


def _parse_iso(value: Any) -> datetime | None:
    text = _one_line(value)
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _seconds_between(start: str, end: str) -> float | None:
    start_dt = _parse_iso(start)
    end_dt = _parse_iso(end)
    if start_dt is None or end_dt is None:
        return None
    return (end_dt - start_dt).total_seconds()


def _minutes_since(start: str, end: str, *, default: int) -> int:
    seconds = _seconds_between(start, end)
    if seconds is None:
        return default
    return max(0, int(seconds / 60))


def _plus_seconds(value: str, seconds: int) -> str:
    parsed = _parse_iso(value) or datetime.now().astimezone()
    return (parsed + timedelta(seconds=max(0, int(seconds)))).astimezone().isoformat()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _timestamp_or_now_iso(value: Any) -> str:
    return _normalize_iso(value) or _now_iso()


def _timestamp_id(value: str) -> str:
    parsed = _parse_iso(value) or datetime.now().astimezone()
    return parsed.strftime("%Y%m%dT%H%M%S%f")[:21]


def _short_hash(value: Any, *, length: int = 12) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="ignore")).hexdigest()[:length]


def _join_or_none(values: tuple[str, ...] | list[str]) -> str:
    clean = [str(value) for value in values if str(value).strip()]
    return ",".join(clean) if clean else "none"


def _extend(items: list[ProactiveCandidate], item: ProactiveCandidate | list[ProactiveCandidate] | None) -> None:
    if item is None:
        return
    if isinstance(item, list):
        items.extend(candidate for candidate in item if candidate is not None)
    else:
        items.append(item)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run XinYu proactivity scorer in shadow mode.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args(argv)
    result = run_proactivity_scorer_shadow(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
