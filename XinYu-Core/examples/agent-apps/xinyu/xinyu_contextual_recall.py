from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_contextual_self_loop import ContextualSelfLoopSnapshot


"""Renderer/offline contextual recall.

This is not the canonical live living-memory recall algorithm. Live chat should
use `xinyu_living_memory_recall.run_living_memory_recall_algorithm` and pass its
compact prompt block into the renderer.
"""


STATE_REL = Path("memory/context/contextual_recall_state.md")
TRACE_REL = Path("runtime/contextual_recall_trace.jsonl")
DEFAULT_MAX_ITEMS = 4
DEFAULT_PROMPT_LIMIT = 1400
CANONICAL_RECALL_OWNER = "xinyu_living_memory_recall.run_living_memory_recall_algorithm"
CONTEXTUAL_RECALL_ROLE = "renderer/offline_context_pack"
CONTEXTUAL_RECALL_BOUNDARY = "not_canonical_living_memory_recall"

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)
_LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
_FIELD_RE = re.compile(r"^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_FRONTMATTER_RE = re.compile(r"^\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat(timespec="seconds")


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


@dataclass(frozen=True, slots=True)
class RecallItem:
    source: str
    intent: str
    why_admitted: str
    risk: str
    preview: str


@dataclass(frozen=True, slots=True)
class ContextualRecallSnapshot:
    evaluated_at: str
    current_scene: str
    retrieval_pressure: str
    evidence_sufficiency: str
    answer_discipline: str
    retrieval_intents: tuple[str, ...]
    admitted: tuple[RecallItem, ...]
    suppressed_count: int
    source_count: int
    notes: tuple[str, ...]


def build_contextual_recall_prompt_block(
    root: Path,
    *,
    contextual_self: ContextualSelfLoopSnapshot,
    user_text: str = "",
    evaluated_at: str | None = None,
    write_state: bool = True,
    append_trace: bool = True,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_chars: int = DEFAULT_PROMPT_LIMIT,
) -> str:
    snapshot = build_contextual_recall_snapshot(
        root,
        contextual_self=contextual_self,
        user_text=user_text,
        evaluated_at=evaluated_at,
        max_items=max_items,
    )
    if write_state:
        write_contextual_recall_state(root, snapshot)
    if append_trace:
        append_contextual_recall_trace(root, snapshot, user_text=user_text)
    return snapshot_to_prompt_block(snapshot, max_chars=max_chars)


def build_contextual_recall_snapshot(
    root: Path,
    *,
    contextual_self: ContextualSelfLoopSnapshot,
    user_text: str = "",
    evaluated_at: str | None = None,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> ContextualRecallSnapshot:
    evaluated_at = _timestamp_or_now_iso(evaluated_at)
    candidates = _collect_candidates(
        root,
        scene=contextual_self.current_scene,
        retrieval_pressure=contextual_self.retrieval_pressure,
        retrieval_intents=contextual_self.retrieval_intents,
        user_text=user_text,
    )
    admitted = tuple(candidates[: _effective_max_items(max_items, contextual_self.retrieval_pressure)])
    evidence_sufficiency = _evidence_sufficiency(
        admitted,
        retrieval_pressure=contextual_self.retrieval_pressure,
    )
    return ContextualRecallSnapshot(
        evaluated_at=evaluated_at,
        current_scene=contextual_self.current_scene,
        retrieval_pressure=contextual_self.retrieval_pressure,
        evidence_sufficiency=evidence_sufficiency,
        answer_discipline=_answer_discipline(
            retrieval_pressure=contextual_self.retrieval_pressure,
            evidence_sufficiency=evidence_sufficiency,
        ),
        retrieval_intents=tuple(contextual_self.retrieval_intents),
        admitted=admitted,
        suppressed_count=max(0, len(candidates) - len(admitted)),
        source_count=len({item.source for item in candidates}),
        notes=("rule_recall_v0", "short_previews_only", "no_raw_history_dump"),
    )


def snapshot_to_prompt_block(snapshot: ContextualRecallSnapshot, *, max_chars: int = DEFAULT_PROMPT_LIMIT) -> str:
    if not snapshot.admitted:
        return ""
    lines = [
        "## Contextual Recall Pack",
        "scope: hidden scene-relevant recall, short previews only.",
        "visibility_rule: use recalled meaning when helpful; do not mention recall machinery, source paths, scores, or gates.",
        f"current_scene: {snapshot.current_scene}",
        f"retrieval_pressure: {snapshot.retrieval_pressure}",
        f"evidence_sufficiency: {snapshot.evidence_sufficiency}",
        f"answer_discipline: {snapshot.answer_discipline}",
        f"suppressed_count: {snapshot.suppressed_count}",
        "",
        "### Admitted Recall",
    ]
    for item in snapshot.admitted:
        lines.extend(
            [
                f"- intent: {item.intent}",
                f"  source: {item.source}",
                f"  why_admitted: {item.why_admitted}",
                f"  risk: {item.risk}",
                f"  preview: {item.preview}",
            ]
        )
    lines.extend(
        [
            "",
            "### Use",
            "- Treat this as optional current-scene memory.",
            "- Current owner message still outranks every recalled preview.",
            "- If retrieval pressure is high and evidence is none or weak, do not invent missing history.",
            "- When evidence is weak, answer with uncertainty and only use what the previews support.",
        ]
    )
    return "\n".join(lines)[:max_chars].rstrip()


def write_contextual_recall_state(root: Path, snapshot: ContextualRecallSnapshot) -> None:
    lines = [
        "---",
        "title: Contextual Recall State",
        "memory_type: contextual_recall_state",
        "time_scope: immediate_runtime",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: xinyu_contextual_recall",
        f"updated_at: {_timestamp_or_now_iso(snapshot.evaluated_at)}",
        "status: active",
        "tags: [context, recall, retrieval, short_context]",
        "---",
        "",
        "# Contextual Recall State",
        "",
        f"- evaluated_at: {snapshot.evaluated_at}",
        f"- current_scene: {snapshot.current_scene}",
        f"- retrieval_pressure: {snapshot.retrieval_pressure}",
        f"- evidence_sufficiency: {snapshot.evidence_sufficiency}",
        f"- answer_discipline: {snapshot.answer_discipline}",
        f"- retrieval_intents: {','.join(snapshot.retrieval_intents)}",
        f"- admitted_recall_count: {len(snapshot.admitted)}",
        f"- suppressed_recall_count: {snapshot.suppressed_count}",
        f"- source_count: {snapshot.source_count}",
        "",
        "## Boundaries",
        "- short_previews_only: true",
        "- raw_history_dump: blocked",
        "- visible_source_labels: blocked",
        "",
        "## Admitted Recall",
    ]
    if snapshot.admitted:
        for item in snapshot.admitted:
            lines.append(f"- {item.intent}: {item.preview}")
    else:
        lines.append("- none")
    _write_text_atomic(root / STATE_REL, "\n".join(lines).rstrip() + "\n")


def append_contextual_recall_trace(root: Path, snapshot: ContextualRecallSnapshot, *, user_text: str = "") -> None:
    event = {
        "event_id": "ctxrecall-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S") + "-" + _short_hash(time.time_ns()),
        "ts": snapshot.evaluated_at,
        "stage": "contextual_recall",
        "status": "evaluated",
        "current_scene": snapshot.current_scene,
        "retrieval_pressure": snapshot.retrieval_pressure,
        "evidence_sufficiency": snapshot.evidence_sufficiency,
        "answer_discipline": snapshot.answer_discipline,
        "retrieval_intent_count": len(snapshot.retrieval_intents),
        "admitted_recall_count": len(snapshot.admitted),
        "suppressed_recall_count": snapshot.suppressed_count,
        "source_count": snapshot.source_count,
        "admitted_sources": [item.source for item in snapshot.admitted],
        "user_text_hash": _short_hash(user_text, length=16) if user_text else "",
        "notes": list(snapshot.notes),
    }
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_clean_json_value(event), ensure_ascii=False, sort_keys=True) + "\n")


def snapshot_to_json(snapshot: ContextualRecallSnapshot) -> dict[str, Any]:
    data = asdict(snapshot)
    data["admitted"] = [asdict(item) for item in snapshot.admitted]
    return _clean_json_value(data)


def _collect_candidates(
    root: Path,
    *,
    scene: str,
    retrieval_pressure: str,
    retrieval_intents: tuple[str, ...],
    user_text: str,
) -> list[RecallItem]:
    candidates: list[RecallItem] = []
    seen_labels: set[str] = set()
    for spec in _scene_sources(scene) + _retrieval_pressure_sources(retrieval_pressure):
        label = str(spec.get("label") or "")
        if label in seen_labels:
            continue
        seen_labels.add(label)
        preview = _preview_for_source(root, spec["rel"], spec["keys"])
        if not preview:
            continue
        candidates.append(
            RecallItem(
                source=spec["label"],
                intent=_best_intent(spec["intents"], retrieval_intents),
                why_admitted=spec["why"],
                risk=spec["risk"],
                preview=preview,
            )
        )
    query_terms = _query_terms(user_text)
    if query_terms:
        candidates.sort(key=lambda item: _candidate_rank(item, query_terms), reverse=True)
    return candidates


def _effective_max_items(max_items: int, retrieval_pressure: str) -> int:
    base = max(1, int(max_items))
    if retrieval_pressure == "high":
        return min(8, base + 2)
    if retrieval_pressure == "medium":
        return min(6, base + 1)
    return base


def _evidence_sufficiency(admitted: tuple[RecallItem, ...], *, retrieval_pressure: str) -> str:
    if not admitted:
        return "none"
    if retrieval_pressure in {"none", "low"}:
        return "usable"
    evidence_intents = {
        "long_history_evidence",
        "recent_thread_resolution",
        "sparse_evidence_check",
        "short_reference_resolution",
        "context_horizon",
        "memory_policy",
    }
    evidence_like_count = sum(1 for item in admitted if item.intent in evidence_intents)
    low_risk_count = sum(1 for item in admitted if item.risk == "low")
    if retrieval_pressure == "high":
        if evidence_like_count <= 0:
            return "none"
        if evidence_like_count >= 2 or (evidence_like_count >= 1 and low_risk_count >= 1):
            return "usable"
        return "weak"
    if evidence_like_count >= 1 or len(admitted) >= 2:
        return "usable"
    return "weak"


def _answer_discipline(*, retrieval_pressure: str, evidence_sufficiency: str) -> str:
    if retrieval_pressure == "high" and evidence_sufficiency == "none":
        return "answer_current_only_acknowledge_missing_evidence"
    if retrieval_pressure == "high" and evidence_sufficiency == "weak":
        return "answer_with_uncertainty_use_only_supported_recall"
    if retrieval_pressure == "high":
        return "answer_from_recalled_evidence_without_overclaim"
    if retrieval_pressure == "medium" and evidence_sufficiency in {"none", "weak"}:
        return "resolve_reference_carefully_avoid_overclaim"
    return "answer_normally_current_message_first"


def _scene_sources(scene: str) -> list[dict[str, Any]]:
    sources: dict[str, list[dict[str, Any]]] = {
        "memory_review": [
            _source("context_horizon", "memory/context/contextual_self_loop_state.md", ("current_scene", "forgetting_posture", "retrieval_intents", "working_self"), ("context_horizon", "memory_policy"), "current horizon explains what to forget and retrieve", "low"),
            _source("memory_review", "memory/context/memory_self_review_state.md", ("status", "latest_decision", "stable_memory_write", "owner_review_required"), ("memory_policy", "recent_owner_correction"), "memory review state is relevant to selective forgetting", "medium"),
            _source("continuity", "memory/context/continuity_handoff_state.md", ("continuity_mode", "open_loop_count", "self_thought_thread", "proactive_thread"), ("recent_owner_correction", "context_horizon"), "continuity can restore short-context threads", "low"),
            _source("initiative_feedback", "memory/context/initiative_feedback_state.md", ("action", "future_effect", "scoring_bias_only"), ("relevant_feedback_bias",), "feedback bias shapes future recall and initiative", "low"),
        ],
        "initiative_feedback": [
            _source("initiative_lifecycle", "memory/context/initiative_lifecycle_state.md", ("selected_decision", "selected_score", "delivery_level", "pending_feedback_count", "next_step"), ("initiative_lifecycle",), "initiative lifecycle is directly requested by this scene", "low"),
            _source("initiative_feedback", "memory/context/initiative_feedback_state.md", ("action", "future_effect", "source_type", "intent_type", "scoring_bias_only"), ("owner_feedback_signal",), "owner feedback should change future proactive bias", "low"),
            _source("runtime_program_awareness", "memory/context/runtime_program_awareness.md", ("observed_subsystem_count", "known_error_count"), ("initiative_metrics",), "program awareness may expose current initiative metrics", "medium"),
        ],
        "runtime_status": [
            _source("runtime_presence", "memory/context/runtime_self_presence.md", ("bridge_process", "current_turn_state", "active_sessions", "codex_status", "autonomous_maintenance", "qq_outbox"), ("runtime_presence",), "runtime state is the scene target", "low"),
            _source("program_awareness", "memory/context/runtime_program_awareness.md", ("observed_subsystem_count", "known_error_count", "unknown_boundary"), ("program_awareness", "known_errors"), "program awareness summarizes observed subsystems", "low"),
            _source("initiative_lifecycle", "memory/context/initiative_lifecycle_state.md", ("selected_decision", "delivery_level", "pending_feedback_count"), ("program_awareness",), "initiative state is part of runtime status", "low"),
        ],
        "emotional_relation": [
            _source("owner_relation", "memory/people/owner.md", ("owner_relation", "preferred_address", "relationship", "tone"), ("owner_relation",), "owner relation helps current relational posture", "medium"),
            _source("relationship_index", "memory/relationships/index.md", ("owner", "relationship", "trust", "boundary"), ("owner_relation",), "relationship index can resolve current relation", "medium"),
            _source("interaction_journal", "memory/context/interaction_journal_state.md", ("last_interaction_at", "last_topic", "last_user_summary", "last_reply_summary"), ("recent_interaction_tone",), "recent interaction tone prevents context amnesia", "medium"),
        ],
        "project_work": [
            _source("recent_context", "memory/context/recent_context.md", ("current_goal", "task", "project", "next_step"), ("current_project_goal", "owner_latest_instruction"), "recent context can restore current project thread", "medium"),
            _source("runtime_presence", "memory/context/runtime_self_presence.md", ("bridge_process", "current_turn_state", "codex_status"), ("open_test_failures",), "runtime status can affect implementation work", "low"),
            _source("self_code_approval", "memory/context/self_code_approval_state.md", ("status", "approval_id", "owner_decision", "approval_scope"), ("recent_code_changes",), "code approval state constrains project actions", "low"),
        ],
        "casual_chat": [
            _source("owner_relation", "memory/people/owner.md", ("preferred_address", "owner_relation", "tone"), ("owner_relation_if_needed",), "owner relation may help casual tone", "medium"),
            _source("recent_context", "memory/context/recent_context.md", ("last_topic", "recent", "summary"), ("current_message_only",), "recent context can resolve short references", "medium"),
        ],
    }
    return sources.get(scene, sources["casual_chat"])


def _retrieval_pressure_sources(retrieval_pressure: str) -> list[dict[str, Any]]:
    if retrieval_pressure == "high":
        return [
            _source("recent_thread", "memory/context/recent_context.md", ("last_topic", "recent", "summary", "current_goal", "next_step"), ("long_history_evidence", "recent_thread_resolution"), "high retrieval pressure asks for sparse recent-thread evidence", "medium"),
            _source("interaction_journal", "memory/context/interaction_journal_state.md", ("last_interaction_at", "last_topic", "last_user_summary", "last_reply_summary"), ("long_history_evidence", "recent_thread_resolution"), "interaction journal can resolve history-dependent references", "medium"),
            _source("continuity", "memory/context/continuity_handoff_state.md", ("continuity_mode", "open_loop_count", "self_thought_thread", "proactive_thread"), ("recent_thread_resolution", "long_history_evidence"), "continuity can restore an interrupted thread without dumping raw history", "low"),
            _source("memory_braid", "memory/context/memory_braid_state.md", ("status", "last_owner_turn", "relationship_thread", "project_thread"), ("long_history_evidence",), "memory braid can provide compact cross-turn evidence", "medium"),
        ]
    if retrieval_pressure == "medium":
        return [
            _source("recent_thread", "memory/context/recent_context.md", ("last_topic", "recent", "summary", "current_goal", "next_step"), ("recent_thread_resolution", "sparse_evidence_check"), "medium retrieval pressure allows a short recent-thread check", "medium"),
            _source("interaction_journal", "memory/context/interaction_journal_state.md", ("last_topic", "last_user_summary", "last_reply_summary"), ("recent_thread_resolution", "sparse_evidence_check"), "interaction journal may resolve the current reference", "medium"),
        ]
    if retrieval_pressure == "low":
        return [
            _source("recent_thread", "memory/context/recent_context.md", ("last_topic", "recent", "summary"), ("short_reference_resolution",), "low retrieval pressure permits only short reference resolution", "medium"),
        ]
    return []


def _source(label: str, rel: str, keys: tuple[str, ...], intents: tuple[str, ...], why: str, risk: str) -> dict[str, Any]:
    return {
        "label": label,
        "rel": rel,
        "keys": keys,
        "intents": intents,
        "why": why,
        "risk": risk,
    }


def _preview_for_source(root: Path, rel: str, keys: tuple[str, ...]) -> str:
    path = root / rel
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
    fields = _parse_fields(text)
    parts: list[str] = []
    for key in keys:
        value = fields.get(key)
        if value:
            parts.append(f"{key}={value}")
        if len(parts) >= 4:
            break
    if parts:
        return _clip("; ".join(parts), limit=260)
    return _clip(_first_meaningful_line(text), limit=220)


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = _FIELD_RE.match(line) or _FRONTMATTER_RE.match(line)
        if not match:
            continue
        fields[match.group(1)] = _clip(match.group(2), limit=140)
    return fields


def _first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        clean = _scrub(line).strip()
        if not clean or clean in {"---"} or clean.startswith("#"):
            continue
        return clean
    return ""


def _best_intent(source_intents: tuple[str, ...], retrieval_intents: tuple[str, ...]) -> str:
    for intent in source_intents:
        if intent in retrieval_intents:
            return intent
    return source_intents[0] if source_intents else "scene_recall"


def _query_terms(user_text: str) -> set[str]:
    text = _scrub(user_text).lower()
    terms = {part for part in re.split(r"[^0-9a-zA-Z_\u4e00-\u9fff]+", text) if len(part) >= 2}
    return set(list(terms)[:12])


def _candidate_rank(item: RecallItem, query_terms: set[str]) -> tuple[int, int]:
    haystack = f"{item.intent} {item.why_admitted} {item.preview}".lower()
    overlap = sum(1 for term in query_terms if term in haystack)
    risk_rank = {"low": 2, "medium": 1, "high": 0}.get(item.risk, 1)
    return overlap, risk_rank


def _scrub(value: Any) -> str:
    text = str(value or "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[redacted-secret]", text)
    text = _LOCAL_PATH_RE.sub("[local-path]", text)
    return re.sub(r"\s+", " ", text).strip()


def _clip(value: Any, *, limit: int) -> str:
    text = _scrub(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _short_hash(value: Any, *, length: int = 10) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()[:length]


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(_scrub_multiline(text), encoding="utf-8")
    os.replace(tmp, path)


def _scrub_multiline(value: Any) -> str:
    text = str(value or "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[redacted-secret]", text)
    text = _LOCAL_PATH_RE.sub("[local-path]", text)
    return text.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, str):
        return _scrub(value)
    return value
