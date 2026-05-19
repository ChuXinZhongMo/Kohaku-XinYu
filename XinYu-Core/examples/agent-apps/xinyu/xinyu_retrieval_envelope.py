from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RetrievalCandidateEnvelope:
    candidate_id: str
    source_type: str
    source_scope: str
    privacy_scope: str
    base_score: float
    need_score: float
    authority: str
    freshness: str
    budget_cost: int
    evidence_kind: str
    boundary: str
    original_rank: int
    final_rank: int
    selected: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return asdict(self)


def recall_item_envelope(
    item: Any,
    *,
    original_rank: int,
    final_rank: int,
    base_score: float,
    need_score: float,
    selected: bool,
) -> RetrievalCandidateEnvelope:
    source = _safe_str(getattr(item, "source", "unknown")) or "unknown"
    scope = _safe_str(getattr(item, "scope", "unknown")) or "unknown"
    memory_ref = _safe_str(getattr(item, "memory_ref", ""))
    message_id = _safe_str(getattr(item, "message_id", ""))
    summary = _safe_str(getattr(item, "summary", ""))
    return RetrievalCandidateEnvelope(
        candidate_id=_stable_candidate_id("recall", source, scope, memory_ref, message_id, summary),
        source_type=source,
        source_scope=scope,
        privacy_scope=_privacy_scope_for_recall(source, scope),
        base_score=round(float(base_score), 4),
        need_score=round(float(need_score), 4),
        authority=_authority_for_recall(source),
        freshness=_freshness_for_recall(source, _safe_str(getattr(item, "time", ""))),
        budget_cost=len(summary),
        evidence_kind=_evidence_kind_for_recall(source),
        boundary=_boundary_for_recall(source),
        original_rank=max(1, int(original_rank)),
        final_rank=max(1, int(final_rank)),
        selected=bool(selected),
    )


def case_envelope(
    decision: Any,
    *,
    original_rank: int,
    final_rank: int,
) -> RetrievalCandidateEnvelope:
    case = getattr(decision, "case", None)
    source_tier = _safe_str(getattr(case, "source_tier", "unknown")) or "unknown"
    privacy_scope = _safe_str(getattr(case, "privacy_scope", "unknown")) or "unknown"
    channel_scope = _safe_str(getattr(case, "channel_scope", privacy_scope)) or privacy_scope
    case_id = _safe_str(getattr(case, "case_id", "case"))
    score = _as_float(getattr(decision, "score", 0.0))
    useful_adjustment = _safe_str(getattr(case, "useful_adjustment", ""))
    bad_pattern = _safe_str(getattr(case, "bad_pattern", ""))
    return RetrievalCandidateEnvelope(
        candidate_id=_stable_candidate_id("case", case_id),
        source_type="conversation_experience",
        source_scope=source_tier,
        privacy_scope=privacy_scope,
        base_score=round(score, 4),
        need_score=round(score, 4),
        authority=_authority_for_case(source_tier),
        freshness="reviewed_case",
        budget_cost=len(useful_adjustment) + len(bad_pattern),
        evidence_kind="behavior_adjustment_case",
        boundary="advisory_case_current_turn_wins",
        original_rank=max(1, int(original_rank)),
        final_rank=max(1, int(final_rank)),
        selected=bool(getattr(decision, "admitted", False)),
    )


def envelope_trace_notes(envelopes: tuple[RetrievalCandidateEnvelope, ...] | list[RetrievalCandidateEnvelope]) -> tuple[str, ...]:
    selected = [envelope for envelope in envelopes if envelope.selected]
    if not selected:
        return ()
    sources = _dedupe(envelope.source_type for envelope in selected[:6])
    authority = _dedupe(envelope.authority for envelope in selected[:6])
    return (
        "candidate_envelope_v1",
        "envelope_sources:" + ",".join(sources),
        "envelope_authority:" + ",".join(authority),
    )


def safe_envelope_trace(envelopes: tuple[RetrievalCandidateEnvelope, ...] | list[RetrievalCandidateEnvelope]) -> list[dict[str, Any]]:
    return [envelope.to_safe_dict() for envelope in envelopes]


def _stable_candidate_id(*parts: str) -> str:
    seed = "|".join(_safe_str(part)[:200] for part in parts if _safe_str(part))
    digest = hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()[:16]
    prefix = _safe_str(parts[0], "candidate") if parts else "candidate"
    return f"{prefix}-{digest}"


def _privacy_scope_for_recall(source: str, scope: str) -> str:
    if scope in {"owner_private", "qq_group", "qq_private_non_owner", "desktop_private", "general"}:
        return scope
    if source == "stable_memory":
        return "stable"
    if source == "self_core_architecture_context":
        return "project_plan"
    return scope or "unknown"


def _authority_for_recall(source: str) -> str:
    return {
        "dialogue_tail": "current_session",
        "dialogue_archive": "local_archive",
        "temporal_trace": "candidate_trace",
        "stable_memory": "stable_memory_reference",
        "self_core_architecture_context": "project_plan_reference",
    }.get(source, "supporting_context")


def _freshness_for_recall(source: str, item_time: str) -> str:
    if source == "dialogue_tail":
        return "current_turn_tail"
    if source == "stable_memory":
        return "stable_file"
    if source == "self_core_architecture_context":
        return "local_plan"
    return "timestamped" if item_time else "unknown"


def _evidence_kind_for_recall(source: str) -> str:
    return {
        "dialogue_tail": "near_context",
        "dialogue_archive": "past_dialogue",
        "temporal_trace": "memory_candidate_trace",
        "stable_memory": "stable_memory_snippet",
        "self_core_architecture_context": "project_plan_snippet",
    }.get(source, "context_snippet")


def _boundary_for_recall(source: str) -> str:
    if source == "stable_memory":
        return "stable_reference_current_turn_wins"
    if source == "self_core_architecture_context":
        return "project_plan_advisory_not_personality_memory"
    return "recalled_context_only_not_stable_memory"


def _authority_for_case(source_tier: str) -> str:
    return {
        "owner_xinyu": "owner_reviewed_case",
        "negative_case": "owner_reviewed_negative_case",
        "reviewed_group": "reviewed_group_pattern",
        "group_contributed": "consented_group_pattern",
        "synthetic_reviewed": "synthetic_reviewed_pattern",
        "public_pattern": "public_low_trust_pattern",
    }.get(source_tier, "case_pattern")


def _dedupe(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _safe_str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)

