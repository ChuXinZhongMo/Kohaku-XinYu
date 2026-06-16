from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_context_retrieval import RecalledContextItem, RecalledContextResult, log_recalled_context
from xinyu_context_retrieval import render_recalled_context
from xinyu_context_retrieval import retrieve_recalled_context as _retrieve_recalled_context
from xinyu_memory_candidate_analysis import build_memory_candidate_recall_boundary
from xinyu_skill_library import build_skill_recall_block
from xinyu_neuro_memory_rules import rule_ids_for_flow
from xinyu_temporal_memory_context import build_temporal_memory_context, render_temporal_memory_context


CANONICAL_RECALL_OWNER = "xinyu_living_memory_recall.run_living_memory_recall_algorithm"
CANONICAL_RECALL_RESULT_SHAPE = "xinyu_context_retrieval.RecalledContextResult"
LEGACY_RECALL_PROVIDER = "xinyu_context_retrieval.retrieve_recalled_context"
RECALL_PROVIDER_MODULES: tuple[str, ...] = (
    "xinyu_context_retrieval",
    "xinyu_sparse_memory_router",
    "xinyu_retrieval_need_reranker",
    "xinyu_retrieval_envelope",
)

MUST_REMEMBER_SOURCES: tuple[str, ...] = ("dialogue_tail", "stable_memory")
EXPERIENCE_HINT_SOURCES: tuple[str, ...] = (
    "dialogue_archive",
    "temporal_trace",
    "self_core_architecture_context",
    "conversation_experience",
)

LONG_LIVED_MEMORY_WRITE_SIGNALS: tuple[str, ...] = (
    "promise_or_obligation",
    "relationship_change",
    "strong_affective_event",
    "durable_preference",
    "identity_or_persona_correction",
    "factual_correction",
    "repeated_pattern",
    "prediction_error",
    "owner_approved_summary",
)


@dataclass(frozen=True, slots=True)
class LivingMemoryRecallBuckets:
    must_remember: tuple[RecalledContextItem, ...]
    experience_hints: tuple[RecalledContextItem, ...]
    uncertainties: tuple[str, ...]
    trace: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LivingMemoryRecallAlgorithmRun:
    result: RecalledContextResult
    buckets: LivingMemoryRecallBuckets
    notes: tuple[str, ...]

    @property
    def prompt_block(self) -> str:
        return self.result.prompt_block


@dataclass(frozen=True, slots=True)
class LivingMemoryRecall:
    root: Path

    def run(
        self,
        payload: dict[str, Any] | None,
        *,
        user_text: str,
        dialogue_tail: list[dict[str, str]] | None = None,
        visible_turn: Any | None = None,
        evaluated_at: datetime | str | None = None,
        log: bool = False,
    ) -> LivingMemoryRecallAlgorithmRun:
        return run_living_memory_recall_algorithm(
            self.root,
            payload,
            user_text=user_text,
            dialogue_tail=dialogue_tail,
            visible_turn=visible_turn,
            evaluated_at=evaluated_at,
            log=log,
        )

    def retrieve(
        self,
        payload: dict[str, Any] | None,
        *,
        user_text: str,
        dialogue_tail: list[dict[str, str]] | None = None,
        visible_turn: Any | None = None,
        evaluated_at: datetime | str | None = None,
    ) -> RecalledContextResult:
        return retrieve_living_memory(
            self.root,
            payload,
            user_text=user_text,
            dialogue_tail=dialogue_tail,
            visible_turn=visible_turn,
            evaluated_at=evaluated_at,
        )

    def log(self, result: RecalledContextResult) -> bool:
        return log_living_memory_recall(self.root, result)

    def bucket(self, result: RecalledContextResult) -> LivingMemoryRecallBuckets:
        return bucket_living_memory_recall(result)


def run_living_memory_recall_algorithm(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None = None,
    visible_turn: Any | None = None,
    evaluated_at: datetime | str | None = None,
    log: bool = False,
) -> LivingMemoryRecallAlgorithmRun:
    """Single living-memory recall algorithm entry.

    The algorithm is intentionally one path:
    current turn -> sparse route -> candidate recall -> need rerank ->
    temporal context -> compact prompt block -> buckets -> optional safe trace log.
    """

    result = _retrieve_living_memory_core(
        root,
        payload,
        user_text=user_text,
        dialogue_tail=dialogue_tail,
        visible_turn=visible_turn,
    )
    result = apply_temporal_memory_context(result, user_text=user_text, evaluated_at=evaluated_at)
    result = apply_memory_candidate_boundaries(root, result, user_text=user_text)
    result = apply_skill_recall(root, result, user_text=user_text)
    buckets = bucket_living_memory_recall(result)
    recall_rule_ids = rule_ids_for_flow("recall")
    notes = [
        "living_memory_recall_algorithm_v1",
        "neuro_rules:" + ",".join(recall_rule_ids),
        *result.notes[:6],
    ]
    if log and result.items:
        logged = log_living_memory_recall(root, result)
        notes.append("living_memory_recall_logged" if logged else "living_memory_recall_log_skipped")
    return LivingMemoryRecallAlgorithmRun(result=result, buckets=buckets, notes=tuple(notes))


def retrieve_living_memory(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None = None,
    visible_turn: Any | None = None,
    evaluated_at: datetime | str | None = None,
) -> RecalledContextResult:
    return run_living_memory_recall_algorithm(
        root,
        payload,
        user_text=user_text,
        dialogue_tail=dialogue_tail,
        visible_turn=visible_turn,
        evaluated_at=evaluated_at,
        log=False,
    ).result


def _retrieve_living_memory_core(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None = None,
    visible_turn: Any | None = None,
) -> RecalledContextResult:
    """Delegate candidate retrieval to the legacy provider under the owner path."""

    return _retrieve_recalled_context(
        root,
        payload,
        user_text=user_text,
        dialogue_tail=dialogue_tail,
        visible_turn=visible_turn,
    )


def log_living_memory_recall(root: Path, result: RecalledContextResult) -> bool:
    return log_recalled_context(root, result)


def apply_temporal_memory_context(
    result: RecalledContextResult,
    *,
    user_text: str,
    evaluated_at: datetime | str | None = None,
) -> RecalledContextResult:
    if not result.items:
        return result
    temporal = build_temporal_memory_context(
        result.items,
        user_text=user_text,
        evaluated_at=evaluated_at,
    )
    enhanced_items = tuple(_with_temporal_hint(item, temporal.hint_for(item.recall_id)) for item in result.items)
    prompt_block = render_recalled_context(
        list(enhanced_items),
        max_chars=4200 if _is_self_state_recall(result) else None,
    )
    temporal_block = render_temporal_memory_context(temporal)
    if temporal_block:
        prompt_block = (prompt_block + "\n\n" + temporal_block).strip() if prompt_block else temporal_block
    return replace(
        result,
        prompt_block=prompt_block,
        items=enhanced_items,
        notes=tuple([*result.notes, *temporal.notes]),
    )


def apply_memory_candidate_boundaries(
    root: Path,
    result: RecalledContextResult,
    *,
    user_text: str,
) -> RecalledContextResult:
    boundary = build_memory_candidate_recall_boundary(root, query_text=user_text)
    if not boundary:
        return result
    prompt_block = (result.prompt_block + "\n\n" + boundary).strip() if result.prompt_block else boundary
    return replace(
        result,
        prompt_block=prompt_block,
        notes=tuple([*result.notes, "memory_candidate_boundaries_attached"]),
    )


def apply_skill_recall(
    root: Path,
    result: RecalledContextResult,
    *,
    user_text: str,
) -> RecalledContextResult:
    block = build_skill_recall_block(root, query_text=user_text)
    if not block:
        return result
    prompt_block = (result.prompt_block + "\n\n" + block).strip() if result.prompt_block else block
    return replace(
        result,
        prompt_block=prompt_block,
        notes=tuple([*result.notes, "skill_recall_attached"]),
    )


def bucket_living_memory_recall(result: RecalledContextResult) -> LivingMemoryRecallBuckets:
    must_remember: list[RecalledContextItem] = []
    experience_hints: list[RecalledContextItem] = []
    uncertainties: list[str] = []
    trace: list[str] = []

    for item in result.items:
        source = str(getattr(item, "source", "") or "")
        confidence = str(getattr(item, "confidence", "") or "").lower()
        if source in MUST_REMEMBER_SOURCES or confidence in {"high", "stable"}:
            must_remember.append(item)
        elif source in EXPERIENCE_HINT_SOURCES:
            experience_hints.append(item)
        else:
            experience_hints.append(item)
        trace.append(f"{source}:{round(float(getattr(item, 'score', 0.0) or 0.0), 3)}")

    for note in result.notes:
        text = str(note)
        if any(marker in text for marker in ("no_matches", "not_needed", "uncertain", "correction")):
            uncertainties.append(text)

    if not result.items and not uncertainties:
        uncertainties.append("no_recalled_items")

    return LivingMemoryRecallBuckets(
        must_remember=tuple(must_remember),
        experience_hints=tuple(experience_hints),
        uncertainties=tuple(uncertainties),
        trace=tuple(trace),
    )


def _is_self_state_recall(result: RecalledContextResult) -> bool:
    route_plan = getattr(result, "route_plan", None)
    selected = getattr(route_plan, "selected_experts", ()) if route_plan is not None else ()
    return "self_state" in set(str(item) for item in selected)


# Compatibility names for older callers while the live path migrates.
retrieve_recalled_context = retrieve_living_memory


def _with_temporal_hint(item: RecalledContextItem, hint: str) -> RecalledContextItem:
    if not hint:
        return item
    relevance = str(getattr(item, "relevance", "") or "")
    if "time_context:" in relevance:
        return item
    return replace(item, relevance=f"{relevance}; time_context: {hint}".strip("; "))
