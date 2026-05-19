from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from xinyu_retrieval_envelope import RetrievalCandidateEnvelope, envelope_trace_notes, recall_item_envelope


class RecallItemLike(Protocol):
    source: str
    summary: str
    relevance: str
    confidence: str
    score: float


@dataclass(frozen=True, slots=True)
class RetrievalNeedProfile:
    query_text: str
    query_terms: tuple[str, ...]
    direct_recall: bool = False
    technical_work: bool = False
    self_core_topic: bool = False
    status_or_progress: bool = False
    owner_pressure: bool = False
    context_reference: bool = False


@dataclass(frozen=True, slots=True)
class RerankDecision:
    source: str
    original_rank: int
    final_rank: int
    base_score: float
    need_score: float
    selected: bool


@dataclass(frozen=True, slots=True)
class RerankResult:
    items: tuple[RecallItemLike, ...]
    decisions: tuple[RerankDecision, ...]
    profile_flags: tuple[str, ...]
    envelopes: tuple[RetrievalCandidateEnvelope, ...] = ()

    def note_lines(self) -> tuple[str, ...]:
        notes = ["need_aware_rerank_v1"]
        if self.profile_flags:
            notes.append("need_profile:" + "+".join(self.profile_flags))
        if self.items:
            top_sources = _dedupe_terms([_safe_str(getattr(item, "source", "")) for item in self.items[:4]])
            if top_sources:
                notes.append("rerank_top_sources:" + ",".join(top_sources))
        notes.extend(envelope_trace_notes(self.envelopes))
        return tuple(notes)


_STATUS_MARKERS = (
    "status",
    "progress",
    "done",
    "left",
    "remaining",
    "finish",
    "\u72b6\u6001",
    "\u8fdb\u5ea6",
    "\u505a\u5b8c",
    "\u8fd8\u5dee",
    "\u5269\u4e0b",
)
_CONTEXT_MARKERS = (
    "previous",
    "earlier",
    "last turn",
    "continue",
    "context",
    "remember",
    "\u4e4b\u524d",
    "\u4e0a\u6b21",
    "\u521a\u624d",
    "\u521a\u521a",
    "\u7ee7\u7eed",
    "\u8bb0\u5f97",
)
_OWNER_PRESSURE_MARKERS = (
    "again",
    "stopped",
    "why did you stop",
    "not what i asked",
    "\u600e\u4e48\u53c8",
    "\u4e3a\u4ec0\u4e48\u505c",
    "\u4e0d\u662f\u8fd9\u4e2a",
    "\u8fd8\u6ca1\u505a",
)
_PROJECT_MARKERS = (
    "codex",
    "runtime",
    "test",
    "smoke",
    "bridge",
    "gateway",
    "api",
    "llm",
    "memory",
    "retrieval",
    "\u9879\u76ee",
    "\u4ee3\u7801",
    "\u6d4b\u8bd5",
    "\u4fee",
    "\u6539",
    "\u8bb0\u5fc6",
    "\u68c0\u7d22",
)


def build_retrieval_need_profile(
    *,
    query_text: str,
    query_terms: tuple[str, ...] | list[str],
    user_text: str = "",
    visible_turn: Any | None = None,
    direct_recall: bool = False,
    self_core_topic: bool = False,
) -> RetrievalNeedProfile:
    text = _norm_space(f"{query_text} {user_text}")
    lowered = text.lower()
    technical_work = bool(getattr(visible_turn, "technical_work", False)) or _contains_any(lowered, _PROJECT_MARKERS)
    owner_pressure = any(
        bool(getattr(visible_turn, attr, False))
        for attr in (
            "owner_style_pressure",
            "owner_no_change_pressure",
            "relationship_pressure",
            "rest_silence",
        )
    ) or _contains_any(lowered, _OWNER_PRESSURE_MARKERS)
    return RetrievalNeedProfile(
        query_text=text,
        query_terms=tuple(_dedupe_terms(query_terms)),
        direct_recall=direct_recall or _contains_any(lowered, _CONTEXT_MARKERS),
        technical_work=technical_work,
        self_core_topic=self_core_topic,
        status_or_progress=_contains_any(lowered, _STATUS_MARKERS),
        owner_pressure=owner_pressure,
        context_reference=_contains_any(lowered, _CONTEXT_MARKERS),
    )


def rerank_recalled_items(
    items: list[RecallItemLike],
    profile: RetrievalNeedProfile,
    *,
    limit: int | None = None,
) -> list[RecallItemLike]:
    return list(rerank_recalled_items_with_report(items, profile, limit=limit).items)


def rerank_recalled_items_with_report(
    items: list[RecallItemLike],
    profile: RetrievalNeedProfile,
    *,
    limit: int | None = None,
) -> RerankResult:
    scored = [
        (index, item, score_recalled_item(item, profile))
        for index, item in enumerate(items)
    ]
    ranked = sorted(
        scored,
        key=lambda pair: (
            -pair[2],
            -_base_score(pair[1]),
            pair[0],
        ),
    )
    selected_limit = len(ranked) if limit is None else max(0, int(limit))
    result = [item for _, item, _ in ranked[:selected_limit]]
    decisions = [
        RerankDecision(
            source=_safe_str(getattr(item, "source", "")),
            original_rank=original_index + 1,
            final_rank=final_index + 1,
            base_score=round(_base_score(item), 4),
            need_score=round(need_score, 4),
            selected=final_index < selected_limit,
        )
        for final_index, (original_index, item, need_score) in enumerate(ranked)
    ]
    envelopes = tuple(
        recall_item_envelope(
            item,
            original_rank=original_index + 1,
            final_rank=final_index + 1,
            base_score=_base_score(item),
            need_score=need_score,
            selected=final_index < selected_limit,
        )
        for final_index, (original_index, item, need_score) in enumerate(ranked)
    )
    report = RerankResult(
        items=tuple(result),
        decisions=tuple(decisions),
        profile_flags=_profile_flags(profile),
        envelopes=envelopes,
    )
    if limit is not None:
        return report
    return report


def score_recalled_item(item: RecallItemLike, profile: RetrievalNeedProfile) -> float:
    source = _safe_str(getattr(item, "source", "")).strip().lower()
    item_text = _item_text(item)
    lowered = item_text.lower()
    overlap = _term_overlap(profile.query_terms, lowered)
    score = _base_score(item)
    score += _confidence_bonus(_safe_str(getattr(item, "confidence", "")))
    score += overlap * 0.75

    if profile.direct_recall:
        score += _source_bonus(
            source,
            {
                "dialogue_tail": 4.0,
                "dialogue_archive": 2.4,
                "temporal_trace": 1.2,
                "stable_memory": 0.5,
            },
        )

    if profile.technical_work:
        score += _source_bonus(
            source,
            {
                "stable_memory": 2.2,
                "self_core_architecture_context": 2.0,
                "temporal_trace": 1.4,
                "dialogue_archive": 1.0,
                "conversation_experience": 0.9,
            },
        )
        if _contains_any(lowered, _PROJECT_MARKERS):
            score += 0.8

    if profile.self_core_topic:
        score += _source_bonus(
            source,
            {
                "self_core_architecture_context": 5.0,
                "stable_memory": 1.1,
                "dialogue_archive": 0.4,
            },
        )

    if profile.status_or_progress:
        score += _source_bonus(
            source,
            {
                "dialogue_tail": 1.5,
                "stable_memory": 1.2,
                "temporal_trace": 1.0,
                "dialogue_archive": 0.8,
            },
        )

    if profile.owner_pressure:
        score += _source_bonus(
            source,
            {
                "dialogue_tail": 1.8,
                "dialogue_archive": 1.1,
                "conversation_experience": 1.0,
            },
        )

    if overlap <= 0:
        if profile.self_core_topic and source == "self_core_architecture_context":
            score += 0.8
        elif profile.direct_recall and source == "dialogue_tail":
            score += 0.5
        else:
            score -= 0.8

    return score


def _source_bonus(source: str, weights: dict[str, float]) -> float:
    return weights.get(source, 0.0)


def _profile_flags(profile: RetrievalNeedProfile) -> tuple[str, ...]:
    flags: list[str] = []
    if profile.direct_recall:
        flags.append("direct_recall")
    if profile.technical_work:
        flags.append("technical_work")
    if profile.self_core_topic:
        flags.append("self_core")
    if profile.status_or_progress:
        flags.append("status")
    if profile.owner_pressure:
        flags.append("owner_pressure")
    if profile.context_reference and "direct_recall" not in flags:
        flags.append("context_reference")
    return tuple(flags)


def retrieval_need_flags(profile: RetrievalNeedProfile) -> tuple[str, ...]:
    return _profile_flags(profile)


def _confidence_bonus(confidence: str) -> float:
    match confidence.strip().lower():
        case "high":
            return 0.8
        case "medium":
            return 0.35
        case "low":
            return 0.0
        case _:
            return 0.0


def _base_score(item: RecallItemLike) -> float:
    try:
        return float(getattr(item, "score", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _item_text(item: RecallItemLike) -> str:
    return _norm_space(
        " ".join(
            part
            for part in (
                _safe_str(getattr(item, "source", "")),
                _safe_str(getattr(item, "summary", "")),
                _safe_str(getattr(item, "relevance", "")),
                _safe_str(getattr(item, "confidence", "")),
            )
            if part
        )
    )


def _term_overlap(query_terms: tuple[str, ...], lowered_text: str) -> float:
    if not query_terms or not lowered_text:
        return 0.0
    hits = 0
    for term in query_terms:
        normalized = term.lower() if re.search(r"[A-Za-z]", term) else term
        if normalized and normalized in lowered_text:
            hits += 1
    return hits / max(1, len(query_terms))


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker and marker in text for marker in markers)


def _dedupe_terms(terms: tuple[str, ...] | list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for term in terms:
        clean = _safe_str(term).strip()
        key = clean.lower() if re.search(r"[A-Za-z]", clean) else clean
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def _norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", _safe_str(text)).strip()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)
