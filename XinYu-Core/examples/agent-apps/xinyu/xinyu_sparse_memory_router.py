from __future__ import annotations

import re
from dataclasses import dataclass, is_dataclass, replace
from typing import Any

from xinyu_storage_paths import knowledge_ref


@dataclass(frozen=True, slots=True)
class SparseMemoryExpertSpec:
    name: str
    source_types: tuple[str, ...]
    memory_refs: tuple[str, ...]
    markers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SparseMemoryExpertDecision:
    expert: str
    score: float
    selected: bool
    reasons: tuple[str, ...]
    source_types: tuple[str, ...]
    memory_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SparseMemoryRoutePlan:
    selected_experts: tuple[str, ...]
    allowed_sources: tuple[str, ...]
    allowed_memory_refs: tuple[str, ...]
    current_turn_facts: tuple[str, ...]
    decisions: tuple[SparseMemoryExpertDecision, ...]
    notes: tuple[str, ...]

    def allows_source(self, source: str) -> bool:
        return _normalize_source(source) in set(self.allowed_sources)

    def allows_memory_ref(self, memory_ref: str) -> bool:
        return _normalize_ref(memory_ref) in set(self.allowed_memory_refs)


@dataclass(frozen=True, slots=True)
class SparseMemoryRoutingResult:
    items: tuple[Any, ...]
    notes: tuple[str, ...]


_RECENT_MARKERS = (
    "previous",
    "earlier",
    "last turn",
    "continue",
    "remember",
    "just now",
    "\u521a\u624d",
    "\u521a\u521a",
    "\u4e0a\u6b21",
    "\u4e4b\u524d",
    "\u524d\u9762",
    "\u7ee7\u7eed",
    "\u8bb0\u5f97",
)

_PROJECT_MARKERS = (
    "codex",
    "runtime",
    "bridge",
    "gateway",
    "frontend",
    "desktop",
    "test",
    "smoke",
    "status",
    "progress",
    "\u9879\u76ee",
    "\u4ee3\u7801",
    "\u524d\u7aef",
    "\u6d4b\u8bd5",
    "\u8fdb\u5ea6",
    "\u72b6\u6001",
    "\u4fee\u590d",
)

_TOOL_PLUGIN_MARKERS = (
    "api",
    "mcp",
    "plugin",
    "kohaku",
    "terrarium",
    "qq",
    "napcat",
    "local model",
    "llm",
    "\u63d2\u4ef6",
    "\u5916\u6302",
    "\u63a5\u53e3",
    "\u989d\u5ea6",
    "\u672c\u5730\u6a21\u578b",
    "\u5c0f\u6a21\u578b",
)

_OWNER_RELATION_MARKERS = (
    "owner",
    "why did you",
    "not reply",
    "empty reply",
    "\u4e3a\u4ec0\u4e48",
    "\u4e0d\u56de\u590d",
    "\u7a7a\u56de\u590d",
    "\u4e0d\u56de\u8bdd",
    "\u4f60\u600e\u4e48",
    "\u4e3b\u4eba",
)

_EMOTION_MARKERS = (
    "emotion",
    "mood",
    "tone",
    "\u60c5\u7eea",
    "\u8bed\u6c14",
    "\u8868\u60c5",
    "\u751f\u6c14",
    "\u70e6",
    "\u4f24\u5fc3",
)

_IDENTITY_MARKERS = (
    "persona",
    "voice",
    "identity",
    "\u6027\u683c",
    "\u58f0\u97f3",
    "\u4eba\u683c",
    "\u8eab\u4efd",
    "\u600e\u4e48\u53eb\u6211",
)

_CREATIVE_WRITING_MARKERS = (
    "novel",
    "chapter",
    "story",
    "writing",
    "creative writing",
    "\u5c0f\u8bf4",
    "\u5199\u5c0f\u8bf4",
    "\u5199\u4f5c",
    "\u7ae0\u8282",
    "\u4e09\u7ae0",
    "\u7231\u597d",
    "\u661f\u6865",
)

_WORLD_KNOWLEDGE_MARKERS = (
    "paper",
    "research",
    "\u8bba\u6587",
    "\u7814\u7a76",
    "\u6709\u6ca1\u6709\u4eba\u505a\u8fc7",
    "\u65b9\u5411",
)

_FAILURE_MARKERS = (
    "bug",
    "failed",
    "broken",
    "not working",
    "why",
    "\u7206\u4e86",
    "\u4e0d\u751f\u6548",
    "\u6ca1\u751f\u6548",
    "\u95ee\u9898",
    "\u5931\u6548",
    "\u4e3a\u4ec0\u4e48",
)

_SELF_CORE_MARKERS = (
    "self core",
    "tinykernel",
    "tiny kernel",
    "local tiny",
    "\u5fc3\u7389\u6838",
    "\u672c\u5730\u6838\u5fc3",
    "\u5c0f\u578b\u81ea\u6211\u6838\u5fc3",
    "\u672c\u5730\u5c0f\u6a21\u578b",
)

_EXPERTS: tuple[SparseMemoryExpertSpec, ...] = (
    SparseMemoryExpertSpec(
        name="recent_dialogue",
        source_types=("dialogue_tail", "dialogue_archive"),
        memory_refs=(
            "memory/context/recent_context.md",
            "memory/context/continuity_handoff_state.md",
        ),
        markers=_RECENT_MARKERS,
    ),
    SparseMemoryExpertSpec(
        name="project_task",
        source_types=("dialogue_archive", "temporal_trace", "stable_memory"),
        memory_refs=(
            "memory/context/recent_context.md",
            "memory/context/codex_delegation_policy.md",
            knowledge_ref("learning_quality_state.md"),
            knowledge_ref("source_notes.md"),
        ),
        markers=_PROJECT_MARKERS,
    ),
    SparseMemoryExpertSpec(
        name="tool_plugin",
        source_types=("dialogue_archive", "temporal_trace", "stable_memory", "self_core_architecture_context"),
        memory_refs=(
            "memory/context/codex_delegation_policy.md",
            knowledge_ref("source_materials.md"),
            knowledge_ref("source_notes.md"),
            knowledge_ref("general.md"),
        ),
        markers=_TOOL_PLUGIN_MARKERS,
    ),
    SparseMemoryExpertSpec(
        name="owner_relation",
        source_types=("dialogue_tail", "dialogue_archive", "stable_memory"),
        memory_refs=(
            "memory/relationships/index.md",
            "memory/people/owner.md",
            "memory/context/recent_context.md",
        ),
        markers=_OWNER_RELATION_MARKERS,
    ),
    SparseMemoryExpertSpec(
        name="emotion_residue",
        source_types=("dialogue_archive", "stable_memory"),
        memory_refs=(
            "memory/emotions/current_state.md",
            "memory/context/current_life_month_context.md",
        ),
        markers=_EMOTION_MARKERS,
    ),
    SparseMemoryExpertSpec(
        name="identity_voice",
        source_types=("stable_memory", "dialogue_archive"),
        memory_refs=(
            "memory/self/personality_profile.md",
            "memory/self/voice_profile_zh.md",
            "memory/self/personality_change_state.md",
        ),
        markers=_IDENTITY_MARKERS,
    ),
    SparseMemoryExpertSpec(
        name="creative_writing",
        source_types=("stable_memory", "dialogue_archive"),
        memory_refs=(
            "memory/creative/planning/novel_profile.md",
            "memory/creative/planning/novel_state.md",
            "memory/creative/planning/novel_outline.md",
            "memory/creative/planning/publication_state.md",
            "memory/creative/planning/publication_log.md",
        ),
        markers=_CREATIVE_WRITING_MARKERS,
    ),
    SparseMemoryExpertSpec(
        name="world_knowledge",
        source_types=("stable_memory", "dialogue_archive"),
        memory_refs=(
            knowledge_ref("general.md"),
            knowledge_ref("source_materials.md"),
            knowledge_ref("source_notes.md"),
        ),
        markers=_WORLD_KNOWLEDGE_MARKERS,
    ),
    SparseMemoryExpertSpec(
        name="failure_memory",
        source_types=("dialogue_tail", "dialogue_archive", "temporal_trace", "stable_memory"),
        memory_refs=(
            "memory/context/recent_context.md",
            knowledge_ref("learning_quality_state.md"),
        ),
        markers=_FAILURE_MARKERS,
    ),
    SparseMemoryExpertSpec(
        name="self_core",
        source_types=("self_core_architecture_context", "stable_memory", "dialogue_archive"),
        memory_refs=(
            "memory/self/learning_closed_loop_state.md",
            "project-plans/XINYU-LOCAL-TINY-SELF-CORE-BACKUP.md",
            "project-plans/XINYU-ALIFE-OPEN-ENDED-DIRECTION-PLAN.md",
            "OPEN-ENDED-BOUNDED-LOOP.md",
        ),
        markers=_SELF_CORE_MARKERS,
    ),
)

_EXPERT_BY_NAME = {spec.name: spec for spec in _EXPERTS}

_STATUS_PROGRESS_MARKERS = (
    "status",
    "progress",
    "done",
    "remaining",
    "\u72b6\u6001",
    "\u8fdb\u5ea6",
    "\u505a\u5b8c",
    "\u5269\u4e0b",
)

_QQ_SUBJECT_MARKERS = (
    "qq",
    "napcat",
    "gateway",
    "\u7f51\u5173",
)

_STALE_STATUS_MARKERS = (
    "offline",
    "not live",
    "not running",
    "not connected",
    "disconnected",
    "stale",
    "old status",
    "stopped",
    "\u79bb\u7ebf",
    "\u672a\u8fde\u63a5",
    "\u6ca1\u8fde\u63a5",
    "\u6ca1\u6709\u542f\u52a8",
    "\u672a\u542f\u52a8",
    "\u65ad\u5f00",
    "\u505c\u6b62",
    "\u65e7\u72b6\u6001",
)


def build_sparse_memory_route(
    *,
    query_text: str,
    query_terms: tuple[str, ...] | list[str] = (),
    user_text: str = "",
    visible_turn: Any | None = None,
    direct_recall: bool = False,
    self_core_topic: bool = False,
    payload: dict[str, Any] | None = None,
    max_experts: int = 4,
) -> SparseMemoryRoutePlan:
    text = _norm_space(f"{query_text} {user_text} {' '.join(query_terms)}")
    lowered = text.lower()
    current_turn_facts = _current_turn_facts(payload, visible_turn)
    scored: list[tuple[SparseMemoryExpertSpec, float, tuple[str, ...]]] = []
    for spec in _EXPERTS:
        score, reasons = _score_expert(
            spec,
            lowered=lowered,
            visible_turn=visible_turn,
            direct_recall=direct_recall,
            self_core_topic=self_core_topic,
            current_turn_facts=current_turn_facts,
        )
        scored.append((spec, score, tuple(reasons)))

    selected_names = _select_experts(
        scored,
        visible_turn=visible_turn,
        direct_recall=direct_recall,
        self_core_topic=self_core_topic,
        max_experts=max_experts,
    )
    decisions = tuple(
        SparseMemoryExpertDecision(
            expert=spec.name,
            score=round(score, 4),
            selected=spec.name in selected_names,
            reasons=reasons,
            source_types=spec.source_types,
            memory_refs=spec.memory_refs,
        )
        for spec, score, reasons in sorted(scored, key=lambda item: (-item[1], item[0].name))
    )
    allowed_sources = _dedupe(
        source for name in selected_names for source in _EXPERT_BY_NAME[name].source_types
    )
    allowed_memory_refs = _dedupe(
        _normalize_ref(ref) for name in selected_names for ref in _EXPERT_BY_NAME[name].memory_refs
    )
    notes = [
        "sparse_memory_router_v1",
        "memory_experts:" + ",".join(selected_names),
        f"memory_route_sparse:{len(selected_names)}/{len(_EXPERTS)}",
    ]
    if current_turn_facts:
        notes.append("memory_route_current_turn_priority:" + ",".join(current_turn_facts))
    return SparseMemoryRoutePlan(
        selected_experts=tuple(selected_names),
        allowed_sources=tuple(allowed_sources),
        allowed_memory_refs=tuple(allowed_memory_refs),
        current_turn_facts=current_turn_facts,
        decisions=decisions,
        notes=tuple(notes),
    )


def apply_sparse_memory_route(items: list[Any] | tuple[Any, ...], plan: SparseMemoryRoutePlan) -> SparseMemoryRoutingResult:
    routed: list[Any] = []
    dropped = 0
    current_turn_penalties = 0
    for item in items:
        source = _normalize_source(getattr(item, "source", ""))
        memory_ref = _normalize_ref(getattr(item, "memory_ref", ""))
        if not _item_allowed_by_plan(source, memory_ref, plan):
            dropped += 1
            continue
        delta, reasons = _item_route_delta(item, plan)
        if "current_turn_contradiction_penalty" in reasons:
            current_turn_penalties += 1
        routed.append(_replace_item(item, score_delta=delta, route_reasons=reasons))

    notes: list[str] = []
    if dropped:
        notes.append(f"sparse_route_filtered:{dropped}")
    if current_turn_penalties:
        notes.append(f"sparse_route_current_turn_penalties:{current_turn_penalties}")
    if not routed and items:
        fallback = max(items, key=lambda item: _as_float(getattr(item, "score", 0.0)))
        routed.append(_replace_item(fallback, score_delta=-1.0, route_reasons=("sparse_route_fallback_one",)))
        notes.append("sparse_route_fallback_one")
    return SparseMemoryRoutingResult(items=tuple(routed), notes=tuple(notes))


def _score_expert(
    spec: SparseMemoryExpertSpec,
    *,
    lowered: str,
    visible_turn: Any | None,
    direct_recall: bool,
    self_core_topic: bool,
    current_turn_facts: tuple[str, ...],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    marker_hits = _marker_hits(lowered, spec.markers)
    if marker_hits:
        score += min(2.4, 0.8 + 0.35 * len(marker_hits))
        reasons.append("marker")

    if direct_recall and spec.name == "recent_dialogue":
        score += 3.0
        reasons.append("direct_recall")
    if direct_recall and spec.name in {"owner_relation", "failure_memory"}:
        score += 0.8
        reasons.append("direct_recall_support")

    if _visible_bool(visible_turn, "technical_work") and spec.name in {"project_task", "tool_plugin", "failure_memory"}:
        score += 2.0
        reasons.append("technical_work")
    if self_core_topic and spec.name == "self_core":
        score += 4.0
        reasons.append("self_core_topic")
    if self_core_topic and spec.name in {"project_task", "tool_plugin"}:
        score += 0.8
        reasons.append("self_core_support")

    if _visible_bool(visible_turn, "owner_style_pressure") or _visible_bool(visible_turn, "owner_no_change_pressure"):
        if spec.name in {"failure_memory", "recent_dialogue", "owner_relation"}:
            score += 1.6
            reasons.append("owner_pressure")
    if _visible_bool(visible_turn, "relationship_pressure") and spec.name == "owner_relation":
        score += 2.0
        reasons.append("relationship_pressure")

    if _contains_any(lowered, _STATUS_PROGRESS_MARKERS) and spec.name in {"project_task", "recent_dialogue"}:
        score += 1.0
        reasons.append("status_progress")
    if "qq_live_current_turn" in current_turn_facts and spec.name in {"recent_dialogue", "tool_plugin", "project_task"}:
        score += 1.2
        reasons.append("live_current_turn")
    return score, reasons


def _select_experts(
    scored: list[tuple[SparseMemoryExpertSpec, float, tuple[str, ...]]],
    *,
    visible_turn: Any | None,
    direct_recall: bool,
    self_core_topic: bool,
    max_experts: int,
) -> tuple[str, ...]:
    ranked = sorted(scored, key=lambda item: (-item[1], item[0].name))
    selected = [spec.name for spec, score, _ in ranked if score >= 1.0][: max(1, max_experts)]
    if direct_recall:
        _append_missing(selected, "recent_dialogue")
    if self_core_topic:
        _append_missing(selected, "self_core")
    if _visible_bool(visible_turn, "technical_work"):
        _append_missing(selected, "project_task")
    if not selected:
        selected.append("recent_dialogue")
    return tuple(selected)


def _item_allowed_by_plan(source: str, memory_ref: str, plan: SparseMemoryRoutePlan) -> bool:
    if source == "stable_memory":
        return plan.allows_source(source) and (not memory_ref or plan.allows_memory_ref(memory_ref))
    if source == "self_core_architecture_context":
        return plan.allows_source(source)
    return plan.allows_source(source)


def _item_route_delta(item: Any, plan: SparseMemoryRoutePlan) -> tuple[float, tuple[str, ...]]:
    source = _normalize_source(getattr(item, "source", ""))
    memory_ref = _normalize_ref(getattr(item, "memory_ref", ""))
    matched_experts = [
        name
        for name in plan.selected_experts
        if source in _EXPERT_BY_NAME[name].source_types
        and (source != "stable_memory" or not memory_ref or memory_ref in plan.allowed_memory_refs)
    ]
    delta = 0.0
    reasons: list[str] = []
    if matched_experts:
        delta += min(1.2, 0.45 * len(matched_experts))
        reasons.append("sparse_expert_match")
    if _contradicts_current_turn(item, plan):
        delta -= 8.0
        reasons.append("current_turn_contradiction_penalty")
    return delta, tuple(reasons)


def _contradicts_current_turn(item: Any, plan: SparseMemoryRoutePlan) -> bool:
    if "qq_live_current_turn" not in plan.current_turn_facts:
        return False
    text = _norm_space(
        " ".join(
            _safe_str(part)
            for part in (
                getattr(item, "source", ""),
                getattr(item, "memory_ref", ""),
                getattr(item, "summary", ""),
                getattr(item, "relevance", ""),
            )
        )
    ).lower()
    return _contains_any(text, _QQ_SUBJECT_MARKERS) and _contains_any(text, _STALE_STATUS_MARKERS)


def _replace_item(item: Any, *, score_delta: float, route_reasons: tuple[str, ...]) -> Any:
    if not route_reasons and score_delta == 0:
        return item
    score = _as_float(getattr(item, "score", 0.0)) + score_delta
    relevance = _safe_str(getattr(item, "relevance", ""))
    reason_text = ",".join(route_reasons)
    if reason_text and reason_text not in relevance:
        relevance = (relevance + "; " if relevance else "") + "sparse_route:" + reason_text
    if is_dataclass(item):
        try:
            return replace(item, score=score, relevance=relevance)
        except TypeError:
            return item
    return item


def _current_turn_facts(payload: dict[str, Any] | None, visible_turn: Any | None) -> tuple[str, ...]:
    metadata = payload.get("metadata") if isinstance(payload, dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}
    facts: list[str] = []
    if _as_bool(metadata.get("qq_gateway_live_current_turn")):
        facts.append("qq_live_current_turn")
    if _safe_str(metadata.get("qq_current_turn_transport")).strip():
        facts.append("qq_transport_current")
    if _safe_str(metadata.get("qq_current_turn_message_kind")).strip():
        facts.append("qq_message_kind_current")
    if _safe_str(metadata.get("source_channel")).strip():
        facts.append("source_channel_current")
    if visible_turn is not None and _visible_bool(visible_turn, "technical_work"):
        facts.append("visible_turn_current")
    return tuple(_dedupe(facts))


def _marker_hits(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker and marker.lower() in text]


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker and marker.lower() in text for marker in markers)


def _append_missing(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _dedupe(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _safe_str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _visible_bool(visible_turn: Any | None, attr: str) -> bool:
    return bool(getattr(visible_turn, attr, False)) if visible_turn is not None else False


def _normalize_source(source: str) -> str:
    return _safe_str(source).strip().lower()


def _normalize_ref(memory_ref: str) -> str:
    return _safe_str(memory_ref).replace("\\", "/").strip()


def _norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", _safe_str(text)).strip()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)
