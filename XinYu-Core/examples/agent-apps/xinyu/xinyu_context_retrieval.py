"""Implementation layer for living memory recall.

The canonical public owner is ``xinyu_living_memory_recall``. Keep this module
focused on candidate collection, routing, reranking, rendering, and compatibility
for older tests/tools while the live path migrates to the owner surface.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import (
    GROUP_SCOPE,
    OWNER_PRIVATE_SCOPE,
    DialogueArchiveRecord,
    record_recalled_context_log,
    resolve_dialogue_scope,
    search_dialogue_archive,
    search_temporal_traces,
)
from xinyu_retrieval_envelope import RetrievalCandidateEnvelope, safe_envelope_trace
from xinyu_retrieval_need_reranker import build_retrieval_need_profile, rerank_recalled_items_with_report
from xinyu_self_state_capsule import classify_self_state_query
from xinyu_sparse_memory_router import SparseMemoryRoutePlan, apply_sparse_memory_route, build_sparse_memory_route
from xinyu_storage_paths import knowledge_file_path, knowledge_ref
from xinyu_text_variants import readable_markers


CANONICAL_RECALL_OWNER = "xinyu_living_memory_recall.run_living_memory_recall_algorithm"
CONTEXT_RETRIEVAL_ROLE = "provider/compatibility"
CONTEXT_RETRIEVAL_PUBLIC_ENTRYPOINT = "xinyu_context_retrieval.retrieve_recalled_context"

RECALL_MARKERS = readable_markers(
    "刚才",
    "上次",
    "之前",
    "昨天",
    "前面",
    "那个",
    "你刚说",
    "你刚才说",
    "我刚说",
    "我刚才说",
    "我说过",
    "我们之前",
    "继续",
    "接着",
    "回到",
    "不是这个",
    "你忘了",
    "原话怎么说",
    "我原话",
)

PROJECT_MARKERS = readable_markers(
    "Codex",
    "OCR",
    "乱码",
    "上下文",
    "长期记忆",
    "runtime",
    "readiness",
    "NapCat",
    "QQ gateway",
    "学习质量",
    "semantic mismatch",
    "bridge",
    "smoke",
    "SQLite",
    "FTS",
)

SELF_CORE_ARCHITECTURE_MARKERS = readable_markers(
    "API",
    "api",
    "基底",
    "本地模型",
    "小模型",
    "0.1B",
    "7B",
    "MIMO",
    "Codex",
    "慢慢学",
    "从头训",
    "训练",
    "工具调用",
    "记忆连贯性",
    "本地小型自我核心",
    "小型自我核心",
    "本地核心",
    "自我核心",
)

GROUP_REQUEST_MARKERS = readable_markers("群", "群里", "群聊", "群消息", "那个群")

CORRECTION_MARKERS = readable_markers(
    "不是",
    "没变化",
    "不像你",
    "别这样",
    "太接待腔",
    "AI味",
    "GPT味",
)

REPAIR_META_RECALL_REDACT_MARKERS = readable_markers(
    "懂，问题在话本身，我继续修。",
    "问题在话本身",
    "我继续修",
    "继续修",
    "没降干净",
    "还不稳",
    "缩回",
    "滑回",
    "安全的壳",
    "安全壳",
    "答题腔",
    "一被你问到",
)

STABLE_MEMORY_TARGETS: tuple[str, ...] = (
    "memory/context/recent_context.md",
    "memory/context/codex_delegation_policy.md",
    "memory/context/life_month_slots.md",
    "memory/context/current_life_month_context.md",
    "memory/creative/planning/novel_profile.md",
    "memory/creative/planning/novel_state.md",
    "memory/creative/planning/novel_outline.md",
    "memory/creative/planning/publication_state.md",
    "memory/creative/planning/publication_log.md",
    "memory/self/personality_profile.md",
    "memory/self/voice_profile_zh.md",
    "memory/self/personality_change_state.md",
    "memory/context/persona_surface_state.md",
    "memory/context/self_state_capsule_state.md",
    "memory/self/learning_closed_loop_state.md",
    "memory/self/expression_self_learning_state.md",
    "memory/relationships/index.md",
    "memory/people/owner.md",
    "memory/emotions/current_state.md",
    knowledge_ref("general.md"),
    knowledge_ref("source_materials.md"),
    knowledge_ref("source_notes.md"),
    knowledge_ref("learning_quality_state.md"),
)

SELF_STATE_STABLE_MEMORY_TARGETS: tuple[str, ...] = (
    "memory/context/persona_surface_state.md",
    "memory/context/self_state_capsule_state.md",
    "memory/self/learning_closed_loop_state.md",
    "memory/self/expression_self_learning_state.md",
    "memory/emotions/current_state.md",
    "memory/relationships/index.md",
    "memory/people/owner.md",
)

_KNOWLEDGE_MEMORY_REF_FILENAMES: dict[str, str] = {
    knowledge_ref("general.md"): "general.md",
    knowledge_ref("source_materials.md"): "source_materials.md",
    knowledge_ref("source_notes.md"): "source_notes.md",
    knowledge_ref("learning_quality_state.md"): "learning_quality_state.md",
}

SELF_CORE_CONTEXT_TARGETS: tuple[str, ...] = (
    "project-plans/XINYU-LOCAL-TINY-SELF-CORE-BACKUP.md",
    "project-plans/XINYU-ALIFE-OPEN-ENDED-DIRECTION-PLAN.md",
    "OPEN-ENDED-BOUNDED-LOOP.md",
    "memory/self/learning_closed_loop_state.md",
    "memory/self/voice_calibration_log.md",
    "memory/self/voice_profile_review_state.md",
)


@dataclass(frozen=True)
class RecalledContextItem:
    recall_id: str
    source: str
    scope: str
    time: str
    speaker: str
    summary: str
    relevance: str
    confidence: str
    score: float
    message_id: int | None = None
    memory_ref: str = ""


@dataclass(frozen=True)
class RecalledContextResult:
    turn_id: str
    query_text: str
    prompt_block: str
    items: tuple[RecalledContextItem, ...]
    notes: tuple[str, ...] = ()
    envelopes: tuple[RetrievalCandidateEnvelope, ...] = ()
    route_plan: SparseMemoryRoutePlan | None = None


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _env_bool(name: str, default: bool) -> bool:
    return _as_bool(os.environ.get(name), default=default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(_safe_str(os.environ.get(name)).strip() or default)
    except (TypeError, ValueError):
        return default


def retrieval_enabled() -> bool:
    return _env_bool("XINYU_DIALOGUE_RETRIEVAL_ENABLED", True)


def retrieval_max_items() -> int:
    return max(1, _env_int("XINYU_DIALOGUE_RETRIEVAL_MAX_ITEMS", 8))


def retrieval_max_chars() -> int:
    return max(600, _env_int("XINYU_DIALOGUE_RETRIEVAL_MAX_CHARS", 1800))


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker and marker in text for marker in markers)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _trim(text: str, limit: int = 220) -> str:
    clean = _normalize_text(text)
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _redact_repair_meta_for_recall(text: str) -> str:
    clean = text
    for marker in REPAIR_META_RECALL_REDACT_MARKERS:
        if marker:
            clean = clean.replace(marker, "[repair-meta-redacted]")
    return clean


def _tokens(text: str) -> list[str]:
    raw_tokens = re.findall(r"[A-Za-z0-9_+#./-]{2,}|[\u4e00-\u9fff]{2,}", text)
    tokens: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        candidates = [token]
        if re.fullmatch(r"[\u4e00-\u9fff]{5,}", token):
            candidates.extend(token[idx : idx + 2] for idx in range(0, len(token) - 1))
            candidates.extend(token[idx : idx + 3] for idx in range(0, len(token) - 2))
        for candidate in candidates:
            normalized = candidate.lower() if re.search(r"[A-Za-z]", candidate) else candidate
            if normalized and normalized not in seen:
                seen.add(normalized)
                tokens.append(normalized)
    return tokens[:16]


def _lexical_score(query_terms: list[str], text: str) -> float:
    if not query_terms or not text:
        return 0.0
    lowered = text.lower()
    score = 0.0
    for term in query_terms:
        haystack = lowered if re.search(r"[a-z]", term) else text
        if term in haystack:
            score += 1.0 if len(term) <= 3 else 1.5
    return score


def _turn_id(scope_hash: str, text: str) -> str:
    seed = f"{datetime.now().astimezone().isoformat()}|{scope_hash}|{text[:240]}"
    return "turn-" + hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()[:16]


def _build_query_text(user_text: str, dialogue_tail: list[dict[str, str]], visible_turn: Any | None) -> str:
    parts = [_safe_str(user_text).strip()]
    for item in dialogue_tail[-4:]:
        content = _safe_str(item.get("content")).strip()
        if content:
            parts.append(content[:220])
    if visible_turn is not None:
        turn_kind = _safe_str(getattr(visible_turn, "turn_kind", "")).strip()
        if turn_kind:
            parts.append(turn_kind)
        if bool(getattr(visible_turn, "technical_work", False)):
            parts.append("technical_work")
    return "\n".join(part for part in parts if part)


def _should_retrieve(user_text: str, query_text: str, visible_turn: Any | None) -> bool:
    if classify_self_state_query(user_text) != "none":
        return True
    if _contains_any(user_text, RECALL_MARKERS):
        return True
    if _contains_any(query_text, PROJECT_MARKERS):
        return True
    if _contains_any(query_text, SELF_CORE_ARCHITECTURE_MARKERS):
        return True
    if visible_turn is not None and bool(getattr(visible_turn, "technical_work", False)):
        return True
    return False


def _scopes_for_payload(payload: dict[str, Any] | None, user_text: str) -> tuple[str, ...]:
    scope = resolve_dialogue_scope(payload)
    if scope.scope == OWNER_PRIVATE_SCOPE:
        if _contains_any(user_text, GROUP_REQUEST_MARKERS):
            return (OWNER_PRIVATE_SCOPE, GROUP_SCOPE)
        return (OWNER_PRIVATE_SCOPE,)
    return (scope.scope,)


def _confidence(score: float) -> str:
    if score >= 8:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def _speaker_for_role(role: str) -> str:
    return "owner" if role == "user" else "XinYu" if role == "assistant" else role or "unknown"


def _tail_items(
    dialogue_tail: list[dict[str, str]],
    *,
    query_terms: list[str],
    recall_requested: bool,
    scope: str,
) -> list[RecalledContextItem]:
    items: list[RecalledContextItem] = []
    for offset, raw in enumerate(dialogue_tail[-8:], start=1):
        role = _safe_str(raw.get("role")).strip()
        text = _safe_str(raw.get("content")).strip()
        if role not in {"user", "assistant"} or not text:
            continue
        score = _lexical_score(query_terms, text) + (3.0 if recall_requested else 0.0)
        score += offset / 10.0
        if score <= 0:
            continue
        items.append(
            RecalledContextItem(
                recall_id=f"tail-{offset:03d}",
                source="dialogue_tail",
                scope=scope,
                time=_safe_str(raw.get("recorded_at"), "current session"),
                speaker=_speaker_for_role(role),
                summary=_trim(text, 180),
                relevance="nearby session tail; preferred for direct callbacks and just-now references",
                confidence=_confidence(score + 2),
                score=score + 5.0,
            )
        )
    return items


def _archive_item(record: DialogueArchiveRecord, *, query_terms: list[str], current_scope: str, session_hash: str) -> RecalledContextItem:
    score = _lexical_score(query_terms, record.text)
    if record.retrieval_source == "semantic":
        score += max(1.0, record.rank_score * 4.0)
    if record.scope == OWNER_PRIVATE_SCOPE:
        score += 1.5
    if record.session_key_hash == session_hash:
        score += 1.5
    if _contains_any(record.text, PROJECT_MARKERS):
        score += 1.0
    if _contains_any(record.text, SELF_CORE_ARCHITECTURE_MARKERS):
        score += 1.2
    if _contains_any(record.text, CORRECTION_MARKERS):
        score += 0.8
    if record.scope == GROUP_SCOPE and current_scope == OWNER_PRIVATE_SCOPE:
        score -= 2.0
    flags = record.quality_flags.get("flags", [])
    flag_text = " ".join(_safe_str(item) for item in flags) if isinstance(flags, list) else _safe_str(flags)
    if "quality_hold_garbled_text" in flag_text:
        score -= 3.0
    if len(record.text) < 8:
        score -= 0.5
    return RecalledContextItem(
        recall_id=f"msg-{record.message_id}",
        source="dialogue_archive",
        scope=record.scope,
        time=record.created_at,
        speaker=_speaker_for_role(record.role),
        summary=_trim(record.text, 220),
        relevance="local dialogue archive match for the current continuity query",
        confidence=_confidence(score),
        score=score,
        message_id=record.message_id,
    )


def _trace_item(row: dict[str, Any], *, query_terms: list[str]) -> RecalledContextItem:
    summary = _safe_str(row.get("summary") or row.get("evidence_text"))
    score = _lexical_score(query_terms, summary)
    score += max(0.0, float(row.get("confidence_score") or 0)) / 40.0
    return RecalledContextItem(
        recall_id=_safe_str(row.get("trace_id"), "trace"),
        source="temporal_trace",
        scope=_safe_str(row.get("scope"), "candidate_trace"),
        time=_safe_str(row.get("created_at"), "trace time unknown"),
        speaker="memory_candidate_trace",
        summary=_trim(summary, 220),
        relevance=(
            "lightweight temporal trace from a memory candidate; "
            "gate review still required before stable memory"
        ),
        confidence=_confidence(score),
        score=score,
        memory_ref=_safe_str(row.get("source_candidate_id")),
    )


def _read_stable_memory(root: Path, rel_path: str, *, limit: int = 12000) -> str:
    normalized_ref = rel_path.replace("\\", "/").strip()
    filename = _KNOWLEDGE_MEMORY_REF_FILENAMES.get(normalized_ref)
    path = knowledge_file_path(root, filename) if filename else root / normalized_ref
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    except OSError:
        return ""
    if text.startswith("content:---"):
        text = text.removeprefix("content:")
    elif text.startswith("content:\n"):
        text = text.removeprefix("content:\n")
    if len(text) <= limit:
        return text
    return text[-limit:]


def _snippet(text: str, terms: list[str], *, limit: int = 220) -> str:
    normalized = _normalize_text(text)
    lowered = normalized.lower()
    hit_index = -1
    for term in terms:
        index = lowered.find(term.lower())
        if index >= 0:
            hit_index = index
            break
    if hit_index < 0:
        return _trim(normalized, limit)
    start = max(0, hit_index - 80)
    end = min(len(normalized), hit_index + limit)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(normalized) else ""
    return prefix + normalized[start:end].strip() + suffix


def _stable_memory_items(
    root: Path,
    *,
    query_terms: list[str],
    rel_paths: tuple[str, ...] | None = None,
) -> list[RecalledContextItem]:
    items: list[RecalledContextItem] = []
    targets = STABLE_MEMORY_TARGETS if rel_paths is None else tuple(
        rel_path for rel_path in rel_paths if rel_path in STABLE_MEMORY_TARGETS
    )
    for rel_path in targets:
        text = _read_stable_memory(root, rel_path)
        if not text:
            continue
        score = _lexical_score(query_terms, text)
        if score <= 0:
            continue
        items.append(
            RecalledContextItem(
                recall_id="mem-" + hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:8],
                source="stable_memory",
                scope="stable",
                time="stable memory file",
                speaker="memory",
                summary=_snippet(text, query_terms, limit=220),
                relevance=f"selected stable memory reference: {rel_path}",
                confidence=_confidence(score + 2),
                score=score + 2.0,
                memory_ref=rel_path,
            )
        )
    return items


def _self_state_stable_items(
    root: Path,
    *,
    query_terms: list[str],
    rel_paths: tuple[str, ...],
) -> list[RecalledContextItem]:
    items: list[RecalledContextItem] = []
    for index, rel_path in enumerate(rel_paths):
        text = _read_stable_memory(root, rel_path, limit=6000)
        if not text:
            continue
        score = 4.8 - min(index, 4) * 0.25
        items.append(
            RecalledContextItem(
                recall_id="selfstate-" + hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:8],
                source="stable_memory",
                scope="stable",
                time="stable self-state support file",
                speaker="memory",
                summary=_snippet(text, query_terms, limit=220),
                relevance=f"self-state support memory reference: {rel_path}",
                confidence=_confidence(score + 2),
                score=score,
                memory_ref=rel_path,
            )
        )
    return items


def _self_core_architecture_items(root: Path, *, query_terms: list[str]) -> list[RecalledContextItem]:
    items: list[RecalledContextItem] = []
    for rel_path in SELF_CORE_CONTEXT_TARGETS:
        text = _read_stable_memory(root, rel_path, limit=18000)
        if not text:
            continue
        score = _lexical_score(query_terms, text)
        if score <= 0 and rel_path.endswith("XINYU-LOCAL-TINY-SELF-CORE-BACKUP.md"):
            score = 1.0
        if score <= 0:
            continue
        items.append(
            RecalledContextItem(
                recall_id="selfcore-" + hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:8],
                source="self_core_architecture_context",
                scope="project_plan",
                time="local project plan / short-term state",
                speaker="project_context",
                summary=_snippet(text, query_terms, limit=260),
                relevance=(
                    "self-learning architecture context; advisory only and not stable personality memory: "
                    f"{rel_path}"
                ),
                confidence=_confidence(score + 2),
                score=score + 2.6,
                memory_ref=rel_path,
            )
        )
    return items


def _dedupe_items(items: list[RecalledContextItem]) -> list[RecalledContextItem]:
    seen: set[str] = set()
    result: list[RecalledContextItem] = []
    for item in sorted(items, key=lambda entry: entry.score, reverse=True):
        key = hashlib.sha256(
            f"{item.speaker}|{_normalize_text(item.summary)[:160]}".encode("utf-8", errors="replace")
        ).hexdigest()[:16]
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def render_recalled_context(items: list[RecalledContextItem], *, max_chars: int | None = None) -> str:
    if not items:
        return ""
    char_budget = retrieval_max_chars() if max_chars is None else max(600, int(max_chars))
    lines: list[str] = [
        "## Recalled Context",
        "purpose: help XinYu remember relevant prior dialogue; advisory only",
        "priority: below current owner message, live voice card, current life posture, privacy boundaries, and stable memory",
        "instruction: Use recalled context only if it helps the current turn. Current owner message and current emotional posture outrank retrieved fragments.",
        "instruction: When uncertain, say uncertainty naturally instead of pretending.",
        "",
    ]
    for index, item in enumerate(items, start=1):
        block = [
            f"- id: rc-{index:03d}",
            f"  source: {item.source}",
            f"  scope: {item.scope}",
            f"  time: {item.time}",
            f"  speaker: {item.speaker}",
            f"  summary: {_redact_repair_meta_for_recall(item.summary)}",
            f"  relevance: {item.relevance}",
            f"  confidence: {item.confidence}",
            "  boundary: recalled dialogue context only; not stable memory unless already marked stable",
        ]
        candidate_lines = lines + block + [""]
        if len("\n".join(candidate_lines)) > char_budget and index > 1:
            break
        lines.extend(block)
        lines.append("")
    return "\n".join(lines).strip()


def retrieve_recalled_context(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None = None,
    visible_turn: Any | None = None,
) -> RecalledContextResult:
    scope = resolve_dialogue_scope(payload)
    turn_id = _turn_id(scope.session_key_hash, user_text)
    if not retrieval_enabled():
        return RecalledContextResult(turn_id=turn_id, query_text="", prompt_block="", items=(), notes=("retrieval_disabled",))

    tail = list(dialogue_tail or [])
    query_text = _build_query_text(user_text, tail, visible_turn)
    if not _should_retrieve(user_text, query_text, visible_turn):
        return RecalledContextResult(turn_id=turn_id, query_text=query_text, prompt_block="", items=(), notes=("retrieval_not_needed",))

    query_terms = _tokens(query_text)
    recall_requested = _contains_any(user_text, RECALL_MARKERS)
    self_core_topic = _contains_any(query_text, SELF_CORE_ARCHITECTURE_MARKERS)
    self_state_topic = classify_self_state_query(user_text) != "none"
    scopes = _scopes_for_payload(payload, user_text)
    current_scope = scope.scope
    route_plan = build_sparse_memory_route(
        query_text=query_text,
        query_terms=query_terms,
        user_text=user_text,
        visible_turn=visible_turn,
        direct_recall=recall_requested,
        self_core_topic=self_core_topic,
        payload=payload,
    )

    items: list[RecalledContextItem] = []
    items.extend(
        _tail_items(
            tail,
            query_terms=query_terms,
            recall_requested=recall_requested or self_state_topic,
            scope=current_scope,
        )
    )
    archive_session_key = None if current_scope == OWNER_PRIVATE_SCOPE else scope.session_key
    if current_scope == GROUP_SCOPE:
        archive_session_key = None
    archive_records = search_dialogue_archive(
        root,
        query_text,
        scopes=scopes,
        session_key=archive_session_key,
        limit=24,
    )
    items.extend(
        _archive_item(record, query_terms=query_terms, current_scope=current_scope, session_hash=scope.session_key_hash)
        for record in archive_records
    )
    if recall_requested or _contains_any(query_text, PROJECT_MARKERS + CORRECTION_MARKERS) or self_core_topic:
        items.extend(
            _trace_item(row, query_terms=query_terms)
            for row in search_temporal_traces(root, query_text, limit=8)
        )
    if (
        bool(getattr(visible_turn, "technical_work", False))
        or _contains_any(query_text, PROJECT_MARKERS)
        or self_core_topic
    ):
        stable_targets = tuple(rel_path for rel_path in STABLE_MEMORY_TARGETS if route_plan.allows_memory_ref(rel_path))
        if route_plan.allows_source("stable_memory") and stable_targets:
            items.extend(_stable_memory_items(root, query_terms=query_terms, rel_paths=stable_targets))
    if self_state_topic and route_plan.allows_source("stable_memory"):
        self_state_targets = tuple(
            rel_path for rel_path in SELF_STATE_STABLE_MEMORY_TARGETS if route_plan.allows_memory_ref(rel_path)
        )
        if self_state_targets:
            items.extend(
                _self_state_stable_items(
                    root,
                    query_terms=query_terms,
                    rel_paths=self_state_targets,
                )
            )
    if self_core_topic and route_plan.allows_source("self_core_architecture_context"):
        items.extend(_self_core_architecture_items(root, query_terms=query_terms))

    need_profile = build_retrieval_need_profile(
        query_text=query_text,
        query_terms=query_terms,
        user_text=user_text,
        visible_turn=visible_turn,
        direct_recall=recall_requested,
        self_core_topic=self_core_topic,
    )
    routed_items = apply_sparse_memory_route(
        _dedupe_items([item for item in items if item.score > 0]),
        route_plan,
    )
    rerank_result = rerank_recalled_items_with_report(
        list(routed_items.items),
        need_profile,
        limit=retrieval_max_items(),
    )
    selected = list(rerank_result.items)
    prompt_block = render_recalled_context(selected, max_chars=4200 if self_state_topic else None)
    notes = ["recalled_context_active"] if selected else ["recalled_context_no_matches"]
    notes.extend(route_plan.notes)
    notes.extend(routed_items.notes)
    notes.extend(rerank_result.note_lines())
    return RecalledContextResult(
        turn_id=turn_id,
        query_text=query_text,
        prompt_block=prompt_block,
        items=tuple(selected),
        notes=tuple(notes),
        envelopes=rerank_result.envelopes,
        route_plan=route_plan,
    )


def log_recalled_context(root: Path, result: RecalledContextResult) -> bool:
    if not result.items:
        return False
    message_ids = [item.message_id for item in result.items if item.message_id is not None]
    memory_refs = [item.memory_ref for item in result.items if item.memory_ref]
    return record_recalled_context_log(
        root,
        turn_id=result.turn_id,
        query_text=result.query_text,
        selected_message_ids=message_ids,
        selected_memory_refs=memory_refs,
        notes={
            "item_count": len(result.items),
            "sources": [item.source for item in result.items],
            "candidate_envelopes": safe_envelope_trace(tuple(getattr(result, "envelopes", ()) or ())[:12]),
            "memory_route": _memory_route_log_notes(getattr(result, "route_plan", None)),
        },
    )


def _memory_route_log_notes(route_plan: Any | None) -> dict[str, Any]:
    if route_plan is None:
        return {}
    return {
        "selected_experts": list(getattr(route_plan, "selected_experts", ()) or ())[:8],
        "current_turn_facts": list(getattr(route_plan, "current_turn_facts", ()) or ())[:8],
        "allowed_sources": list(getattr(route_plan, "allowed_sources", ()) or ())[:8],
    }
