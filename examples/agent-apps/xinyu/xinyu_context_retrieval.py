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
from xinyu_text_variants import readable_markers


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

GROUP_REQUEST_MARKERS = readable_markers("群", "群里", "群聊", "群消息", "那个群")

CORRECTION_MARKERS = readable_markers(
    "不是",
    "没变化",
    "不像你",
    "别这样",
    "太客服",
    "AI味",
    "GPT味",
)

STABLE_MEMORY_TARGETS: tuple[str, ...] = (
    "memory/context/recent_context.md",
    "memory/context/codex_delegation_policy.md",
    "memory/context/life_month_slots.md",
    "memory/context/current_life_month_context.md",
    "memory/self/personality_profile.md",
    "memory/self/voice_profile_zh.md",
    "memory/self/personality_change_state.md",
    "memory/relationships/index.md",
    "memory/people/owner.md",
    "memory/emotions/current_state.md",
    "memory/knowledge/general.md",
    "memory/knowledge/source_materials.md",
    "memory/knowledge/source_notes.md",
    "memory/knowledge/learning_quality_state.md",
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


def _tokens(text: str) -> list[str]:
    raw_tokens = re.findall(r"[A-Za-z0-9_+#./-]{2,}|[\u4e00-\u9fff]{2,}", text)
    tokens: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        candidates = [token]
        if re.fullmatch(r"[\u4e00-\u9fff]{5,}", token):
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
    if _contains_any(user_text, RECALL_MARKERS):
        return True
    if _contains_any(query_text, PROJECT_MARKERS):
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
    try:
        text = (root / rel_path).read_text(encoding="utf-8-sig", errors="replace").strip()
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


def _stable_memory_items(root: Path, *, query_terms: list[str]) -> list[RecalledContextItem]:
    items: list[RecalledContextItem] = []
    for rel_path in STABLE_MEMORY_TARGETS:
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
            f"  summary: {item.summary}",
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
    scopes = _scopes_for_payload(payload, user_text)
    current_scope = scope.scope

    items: list[RecalledContextItem] = []
    items.extend(
        _tail_items(
            tail,
            query_terms=query_terms,
            recall_requested=recall_requested,
            scope=current_scope,
        )
    )
    archive_records = search_dialogue_archive(
        root,
        query_text,
        scopes=scopes,
        session_key=scope.session_key if current_scope != GROUP_SCOPE else None,
        limit=24,
    )
    items.extend(
        _archive_item(record, query_terms=query_terms, current_scope=current_scope, session_hash=scope.session_key_hash)
        for record in archive_records
    )
    if recall_requested or _contains_any(query_text, PROJECT_MARKERS + CORRECTION_MARKERS):
        items.extend(
            _trace_item(row, query_terms=query_terms)
            for row in search_temporal_traces(root, query_text, limit=8)
        )
    if bool(getattr(visible_turn, "technical_work", False)) or _contains_any(query_text, PROJECT_MARKERS):
        items.extend(_stable_memory_items(root, query_terms=query_terms))

    selected = _dedupe_items([item for item in items if item.score > 0])[: retrieval_max_items()]
    prompt_block = render_recalled_context(selected)
    notes = ["recalled_context_active"] if selected else ["recalled_context_no_matches"]
    return RecalledContextResult(
        turn_id=turn_id,
        query_text=query_text,
        prompt_block=prompt_block,
        items=tuple(selected),
        notes=tuple(notes),
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
        notes={"item_count": len(result.items), "sources": [item.source for item in result.items]},
    )
