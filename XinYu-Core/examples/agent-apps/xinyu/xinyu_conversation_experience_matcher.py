from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from xinyu_bridge_values import as_bool, safe_str
from xinyu_conversation_experience_cases import (
    ConversationExperienceCase,
    candidate_cases,
    record_match_trace,
)
from xinyu_retrieval_envelope import RetrievalCandidateEnvelope, case_envelope, envelope_trace_notes
from xinyu_retrieval_need_reranker import build_retrieval_need_profile, retrieval_need_flags


CANONICAL_RECALL_OWNER = "xinyu_living_memory_recall.run_living_memory_recall_algorithm"
CONVERSATION_EXPERIENCE_ROLE = "advisory_case_provider"
CONVERSATION_EXPERIENCE_BOUNDARY = "provider_hint_not_memory_recall_owner"


@dataclass(frozen=True)
class ConversationExperienceQuery:
    query_text: str
    scenario_tags: tuple[str, ...]
    privacy_scope: str
    channel_scope: str
    technical_work: bool
    owner_pressure: bool
    context_reference: bool
    status_reference: bool


@dataclass(frozen=True)
class ConversationExperienceDecision:
    case: ConversationExperienceCase
    score: float
    admitted: bool
    reason: str


@dataclass(frozen=True)
class ConversationExperienceMatchResult:
    query: ConversationExperienceQuery
    decisions: tuple[ConversationExperienceDecision, ...]
    notes: tuple[str, ...]
    envelopes: tuple[RetrievalCandidateEnvelope, ...] = ()

    @property
    def selected(self) -> tuple[ConversationExperienceDecision, ...]:
        return tuple(decision for decision in self.decisions if decision.admitted)

    @property
    def suppressed(self) -> tuple[ConversationExperienceDecision, ...]:
        return tuple(decision for decision in self.decisions if not decision.admitted)


def build_query_features(
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None = None,
    visible_turn: Any | None = None,
) -> ConversationExperienceQuery:
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    message_type = safe_str(payload.get("message_type")).lower()
    group_id = safe_str(payload.get("group_id")).strip()
    is_owner = as_bool(metadata.get("is_owner_user"), default=False)
    is_group = bool(group_id) or message_type.startswith("group")
    is_desktop = message_type.startswith("desktop")

    if is_group:
        privacy_scope = "qq_group"
        channel_scope = "qq_group"
    elif is_owner:
        privacy_scope = "owner_private"
        channel_scope = "desktop_private" if is_desktop else "owner_private"
    else:
        privacy_scope = "qq_private_non_owner"
        channel_scope = "qq_private_non_owner"

    tail_text = " ".join(
        safe_str(item.get("content")).strip()
        for item in list(dialogue_tail or [])[-3:]
        if isinstance(item, dict)
    )
    query_text = re.sub(r"\s+", " ", f"{tail_text} {safe_str(user_text)}").strip()
    lower = query_text.lower()

    technical_work = as_bool(getattr(visible_turn, "technical_work", False), default=False) or _contains_any(
        lower,
        ("code", "test", "fix", "bug", "implement", "migration", "\u4fee\u590d", "\u4ee3\u7801", "\u62a5\u9519"),
    )
    owner_pressure = any(
        as_bool(getattr(visible_turn, attr, False), default=False)
        for attr in ("owner_style_pressure", "owner_no_change_pressure", "relationship_pressure", "rest_silence")
    ) or _contains_any(
        lower,
        (
            "why did you stop",
            "stopped",
            "again",
            "\u4e3a\u4ec0\u4e48\u505c",
            "\u600e\u4e48\u53c8",
            "\u4e0d\u662f\u8bf4",
        ),
    )
    context_reference = _contains_any(
        lower,
        (
            "continue",
            "just now",
            "last turn",
            "what happened",
            "where did we stop",
            "\u7ee7\u7eed",
            "\u521a\u624d",
            "\u8fdb\u5ea6",
            "\u505c\u4e0b",
            "\u4e0a\u4e00\u8f6e",
        ),
    )
    status_reference = _contains_any(
        lower,
        (
            "status",
            "progress",
            "done",
            "left",
            "what remains",
            "\u72b6\u6001",
            "\u8fdb\u5ea6",
            "\u8fd8\u5dee",
            "\u505a\u5b8c",
            "\u8fd8\u6709\u4ec0\u4e48",
        ),
    )

    tags: list[str] = []
    if technical_work:
        tags.extend(["technical_work", "implementation_followup"])
    if owner_pressure:
        tags.extend(["owner_pressure", "owner_frustrated"])
    if context_reference:
        tags.append("context_reference")
    if status_reference:
        tags.append("status_question")
    if _contains_any(lower, ("mechanics", "internal", "orchestration", "\u673a\u5236", "\u6d41\u7a0b")):
        tags.append("mechanics_explanation_bad")
    if _contains_any(lower, ("promise", "later", "\u7b54\u5e94", "\u627f\u8bfa", "\u518d\u770b\u770b", "\u67e5\u4e00\u4e0b")):
        tags.append("empty_promise")
    if _contains_any(lower, ("sorry", "apolog", "\u62b1\u6b49", "\u4e0d\u597d\u610f\u601d", "\u7b97\u9519")):
        tags.append("template_apology")
    if _contains_any(lower, ("screenshot", "attachment", "file", "image", "\u622a\u56fe", "\u6587\u4ef6", "\u9644\u4ef6", "\u56fe")):
        tags.append("attachment_followup")
    if not tags:
        tags.append("ordinary_chat")

    return ConversationExperienceQuery(
        query_text=query_text,
        scenario_tags=_dedupe(tags),
        privacy_scope=privacy_scope,
        channel_scope=channel_scope,
        technical_work=technical_work,
        owner_pressure=owner_pressure,
        context_reference=context_reference,
        status_reference=status_reference,
    )


def match_conversation_experience_cases(
    root: Any,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None = None,
    visible_turn: Any | None = None,
    turn_id: str = "",
    limit: int = 2,
    min_score: float = 0.72,
) -> ConversationExperienceMatchResult:
    query = build_query_features(payload, user_text=user_text, dialogue_tail=dialogue_tail, visible_turn=visible_turn)
    need_profile = build_retrieval_need_profile(
        query_text=query.query_text,
        query_terms=_tokens(query.query_text),
        user_text=user_text,
        visible_turn=visible_turn,
        direct_recall=query.context_reference,
    )
    need_flags = retrieval_need_flags(need_profile)
    candidates = candidate_cases(
        root,
        query_text=query.query_text,
        scenario_tags=query.scenario_tags,
        privacy_scope=query.privacy_scope,
        channel_scope=query.channel_scope,
        min_confidence=0.3,
        limit=80,
    )
    original_rank_by_id = {case.case_id: index + 1 for index, case in enumerate(candidates)}
    scored_candidates: list[tuple[ConversationExperienceCase, float, str]] = []
    for case in candidates:
        score, reason = _score_case(case, query)
        scored_candidates.append((case, score, reason))
    scored_candidates.sort(key=lambda item: (item[2] == "matched", item[1]), reverse=True)

    decisions: list[ConversationExperienceDecision] = []
    selected_count = 0
    for case, score, reason in scored_candidates:
        admitted = score >= min_score and selected_count < max(1, int(limit)) and reason == "matched"
        if admitted:
            selected_count += 1
            final_reason = "matched"
        elif reason != "matched":
            final_reason = reason
        elif score < min_score:
            final_reason = "score_below_threshold"
        else:
            final_reason = "case_limit_reached"
        decisions.append(ConversationExperienceDecision(case=case, score=score, admitted=admitted, reason=final_reason))
    envelopes = tuple(
        case_envelope(
            decision,
            original_rank=original_rank_by_id.get(decision.case.case_id, index + 1),
            final_rank=index + 1,
        )
        for index, decision in enumerate(decisions)
    )

    notes = ["conversation_experience_match_done"]
    if need_flags:
        notes.append("need_profile:" + "+".join(need_flags))
    notes.extend(envelope_trace_notes(envelopes))
    if not decisions:
        notes.append("conversation_experience_no_candidates")
    elif selected_count == 0:
        notes.append("conversation_experience_no_selected_case")
    else:
        notes.append(f"conversation_experience_selected:{selected_count}")

    try:
        record_match_trace(
            root,
            turn_id=turn_id or "unknown",
            query_text=query.query_text,
            selected_case_ids=[decision.case.case_id for decision in decisions if decision.admitted],
            suppressed_case_ids=[decision.case.case_id for decision in decisions if not decision.admitted],
            notes=notes,
        )
    except OSError:
        notes.append("conversation_experience_trace_failed")

    return ConversationExperienceMatchResult(query=query, decisions=tuple(decisions), notes=tuple(notes), envelopes=envelopes)


def _score_case(case: ConversationExperienceCase, query: ConversationExperienceQuery) -> tuple[float, str]:
    case_tags = {tag.lower() for tag in case.scenario_tags}
    query_tags = {tag.lower() for tag in query.scenario_tags}
    if query.privacy_scope == "owner_private" and case.source_tier not in {"owner_xinyu", "negative_case"}:
        if "owner_relationship" in case_tags or "relationship_pressure" in case_tags:
            return 0.0, "external_owner_relationship_case_rejected"

    tag_overlap = len(case_tags & query_tags) / max(1, len(query_tags))
    text_overlap = _text_overlap(query.query_text, case.searchable_text)
    scope_score = 1.0 if case.privacy_scope == query.privacy_scope else 0.7 if case.privacy_scope == "general" else 0.0
    channel_score = 1.0 if case.channel_scope == query.channel_scope else 0.7 if case.channel_scope == "general" else 0.0
    tier_bonus = {
        "owner_xinyu": 0.08,
        "negative_case": 0.06,
        "reviewed_group": 0.03,
        "group_contributed": 0.02,
        "synthetic_reviewed": 0.02,
        "public_pattern": 0.0,
    }.get(case.source_tier, 0.0)
    relevance = (
        0.38 * case.confidence
        + 0.32 * tag_overlap
        + 0.14 * text_overlap
        + 0.08 * scope_score
        + 0.04 * channel_score
        + tier_bonus
        + _need_alignment_bonus(case_tags, query)
    )
    if tag_overlap <= 0 and text_overlap < 0.12:
        return relevance, "weak_relevance"
    if query.privacy_scope != "owner_private" and case.privacy_scope == "owner_private":
        return 0.0, "owner_private_case_rejected_for_non_owner"
    return min(1.0, relevance), "matched"


def _need_alignment_bonus(case_tags: set[str], query: ConversationExperienceQuery) -> float:
    bonus = 0.0
    if query.technical_work and case_tags & {"technical_work", "implementation_followup", "task_stopped"}:
        bonus += 0.045
    if query.status_reference and case_tags & {"status_question", "blocked_boundary", "final_report"}:
        bonus += 0.04
    if query.owner_pressure and case_tags & {"owner_pressure", "owner_frustrated", "mechanics_explanation_bad"}:
        bonus += 0.04
    if query.context_reference and case_tags & {"context_reference", "stale_memory", "implementation_followup"}:
        bonus += 0.035
    return min(0.12, bonus)


def _text_overlap(left: str, right: str) -> float:
    left_terms = set(_tokens(left))
    right_terms = set(_tokens(right))
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / max(1, len(left_terms))


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9_\-]+", safe_str(text)) if len(token) >= 2]


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker and marker.lower() in text for marker in markers)


def _dedupe(values: list[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = safe_str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)
