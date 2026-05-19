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


STATE_REL = Path("memory/context/contextual_self_loop_state.md")
TRACE_REL = Path("runtime/contextual_self_loop_trace.jsonl")
DEFAULT_PROMPT_LIMIT = 1400
CANONICAL_RECALL_OWNER = "xinyu_living_memory_recall.run_living_memory_recall_algorithm"
CONTEXTUAL_SELF_LOOP_ROLE = "runtime_state_provider"
CONTEXTUAL_SELF_LOOP_BOUNDARY = "scene_and_pressure_provider_not_memory_recall_owner"
_BASE_CONTEXT_LAYERS = {
    "concept_seed",
    "xinyu_concept",
    "voice",
    "time",
}
_SCENE_CONTEXT_LAYERS: dict[str, set[str]] = {
    "project_work": {
        "runtime_presence",
        "watched_source",
        "github_learning",
        "memory_self_review",
        "continuity_handoff",
        "uncertainty_pause",
        "async_exploration",
        "self_code_approval",
        "codex_boundary",
        "recent_context",
        "initiative",
    },
    "memory_review": {
        "owner_relation",
        "relationship",
        "runtime_presence",
        "memory_self_review",
        "continuity_handoff",
        "uncertainty_pause",
        "recent_context",
        "initiative_feedback",
    },
    "initiative_feedback": {
        "runtime_presence",
        "recent_context",
        "initiative",
        "initiative_lifecycle",
        "initiative_feedback",
    },
    "runtime_status": {
        "runtime_presence",
        "watched_source",
        "github_learning",
        "daily_digest",
        "memory_self_review",
        "async_exploration",
        "self_code_approval",
        "codex_boundary",
        "initiative_lifecycle",
        "initiative_feedback",
    },
    "emotional_relation": {
        "owner_relation",
        "relationship",
        "emotion",
        "life_context",
        "recent_surface",
        "continuity_handoff",
        "uncertainty_pause",
        "recent_context",
    },
    "casual_chat": {
        "owner_relation",
        "relationship",
        "life_context",
        "recent_surface",
        "continuity_handoff",
        "recent_context",
    },
}
_SCENE_LIMIT_SCALE = {
    "casual_chat": 0.55,
    "emotional_relation": 0.75,
    "memory_review": 0.8,
    "initiative_feedback": 0.85,
    "runtime_status": 0.9,
    "project_work": 1.0,
}
_MEMORY_REVIEW_KEYWORDS = (
    "\u8bb0\u5fc6",
    "\u9057\u5fd8",
    "\u56de\u60f3",
    "\u68c0\u7d22",
    "\u4e0a\u4e0b\u6587",
    "\u53ec\u56de",
    "\u957f\u671f\u8bb0\u5fc6",
    "context",
    "memory",
    "forget",
    "retrieve",
    "recall",
)
_INITIATIVE_FEEDBACK_KEYWORDS = (
    "\u4e3b\u52a8",
    "\u4e3b\u52a8\u6027",
    "\u53cd\u9988",
    "\u63d0\u9192",
    "\u6253\u6270",
    "dismiss",
    "reply",
    "approve",
    "hold",
    "initiative",
    "proactive",
    "candidate",
)
_RUNTIME_STATUS_KEYWORDS = (
    "\u8fd0\u884c",
    "\u72b6\u6001",
    "\u6307\u6807",
    "\u684c\u9762",
    "\u4eea\u8868\u76d8",
    "runtime",
    "health",
    "metrics",
    "desktop",
    "presence",
    "observatory",
    "context gate",
    "stale",
)
_PROJECT_WORK_KEYWORDS = (
    "\u4ee3\u7801",
    "\u6d4b\u8bd5",
    "\u5b9e\u73b0",
    "\u63a5\u5165",
    "\u6587\u4ef6",
    "\u67b6\u6784",
    "\u6a21\u5757",
    "\u9879\u76ee",
    "\u4fee",
    "\u6539",
    "plan",
    "bug",
    "test",
    "implement",
)
_EMOTIONAL_RELATION_KEYWORDS = (
    "\u5173\u7cfb",
    "\u60c5\u7eea",
    "\u96be\u53d7",
    "\u966a",
    "\u5b64\u72ec",
    "\u559c\u6b22",
    "\u5728\u610f",
    "\u611f\u89c9",
    "emotion",
    "relationship",
    "feel",
)
_RETRIEVAL_EXPLICIT_KEYWORDS = (
    "\u4e4b\u524d",
    "\u4e0a\u6b21",
    "\u521a\u624d",
    "\u521a\u521a",
    "\u8bb0\u5f97",
    "\u8fd8\u8bb0\u5f97",
    "\u8bf4\u8fc7",
    "\u63d0\u5230",
    "\u524d\u9762",
    "\u5386\u53f2",
    "\u8bc1\u636e",
    "previous",
    "previously",
    "earlier",
    "mentioned",
    "history",
    "evidence",
)
_RETRIEVAL_DEICTIC_KEYWORDS = (
    "\u8fd9\u4e2a",
    "\u90a3\u4e2a",
    "\u8fd9\u4e9b",
    "\u90a3\u4e9b",
    "\u8fd9\u4ef6\u4e8b",
    "\u90a3\u4ef6\u4e8b",
    "\u5b83",
    "\u4ed6",
    "\u5979",
    "\u4ed6\u4eec",
    "\u5979\u4eec",
    "this",
    "that",
    "it",
    "they",
    "above",
)
_RETRIEVAL_EVIDENCE_QUESTION_KEYWORDS = (
    "\u4e3a\u4ec0\u4e48",
    "\u600e\u4e48\u77e5\u9053",
    "\u6839\u636e",
    "\u54ea\u4e00\u8f6e",
    "\u7b2c\u51e0\u8f6e",
    "\u4ece\u54ea\u91cc",
    "why",
    "how do you know",
    "based on",
    "which turn",
)
_HISTORY_DEPENDENT_FACT_KEYWORDS = (
    "favorite",
    "studying",
    "study",
    "attend",
    "attends",
    "enrolled",
    "course",
    "been to",
    "like about",
    "how old",
)
_EN_PERSON_FACT_QUERY_RE = re.compile(
    r"\b(?:[Ww]hat|[Ww]here|[Ww]hich|[Ww]hen|[Ww]hy|[Hh]ow old|[Hh]as|[Dd]id|[Dd]oes|[Ii]s|[Ii]n which)\b.{0,80}\b([A-Z][a-z]{2,})(?:'s)?\b"
)
_EN_COMMON_ENTITY_NAMES = {
    "Python",
    "Java",
    "Javascript",
    "Typescript",
    "Windows",
    "Linux",
    "Openai",
    "Anthropic",
    "Google",
    "Github",
    "Hugging",
    "Chatgpt",
}
_RETRIEVAL_PRESSURE_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)
_LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")


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
class ContextualSelfLoopSnapshot:
    evaluated_at: str
    trigger: str
    current_scene: str
    working_context_budget: str
    forgetting_posture: str
    retrieval_pressure: str
    retrieval_pressure_signals: tuple[str, ...]
    retrieval_intents: tuple[str, ...]
    admitted_context: tuple[str, ...]
    suppressed_context: tuple[str, ...]
    working_self: str
    initiative_posture: str
    next_action_bias: str
    notes: tuple[str, ...]


def run_contextual_self_loop(
    root: Path,
    *,
    user_text: str = "",
    trigger: str = "manual",
    evaluated_at: str | None = None,
    write_state: bool = True,
    append_trace: bool = True,
) -> dict[str, Any]:
    snapshot = build_contextual_self_loop_snapshot(
        root,
        user_text=user_text,
        trigger=trigger,
        evaluated_at=evaluated_at,
    )
    if write_state:
        write_contextual_self_loop_state(root, snapshot)
    if append_trace:
        append_contextual_self_loop_trace(root, snapshot, user_text=user_text)
    return snapshot_to_json(snapshot)


def build_contextual_self_loop_prompt_block(
    root: Path,
    *,
    user_text: str = "",
    trigger: str = "renderer_memory_context",
    evaluated_at: str | None = None,
    write_state: bool = True,
    append_trace: bool = True,
    max_chars: int = DEFAULT_PROMPT_LIMIT,
) -> str:
    snapshot = build_contextual_self_loop_snapshot(
        root,
        user_text=user_text,
        trigger=trigger,
        evaluated_at=evaluated_at,
    )
    if write_state:
        write_contextual_self_loop_state(root, snapshot)
    if append_trace:
        append_contextual_self_loop_trace(root, snapshot, user_text=user_text)
    return snapshot_to_prompt_block(snapshot, max_chars=max_chars)


def build_contextual_self_loop_snapshot(
    root: Path,
    *,
    user_text: str = "",
    trigger: str = "manual",
    evaluated_at: str | None = None,
) -> ContextualSelfLoopSnapshot:
    del root
    evaluated_at = _timestamp_or_now_iso(evaluated_at)
    scene = classify_context_scene(user_text)
    config = _scene_config(scene)
    pressure, pressure_signals = evaluate_retrieval_pressure(user_text)
    retrieval_intents = _merge_retrieval_pressure_intents(tuple(config["retrieval_intents"]), pressure)
    forgetting_posture = _pressure_adjusted_forgetting_posture(config["forgetting_posture"], pressure)
    return ContextualSelfLoopSnapshot(
        evaluated_at=evaluated_at,
        trigger=_clean_token(trigger or "manual"),
        current_scene=scene,
        working_context_budget=config["working_context_budget"],
        forgetting_posture=forgetting_posture,
        retrieval_pressure=pressure,
        retrieval_pressure_signals=pressure_signals,
        retrieval_intents=retrieval_intents,
        admitted_context=tuple(config["admitted_context"]),
        suppressed_context=tuple(config["suppressed_context"]),
        working_self=config["working_self"],
        initiative_posture=config["initiative_posture"],
        next_action_bias=config["next_action_bias"],
        notes=("foundation_v0", "short_context_first", "hidden_orchestration_only"),
    )


def evaluate_retrieval_pressure(user_text: str) -> tuple[str, tuple[str, ...]]:
    text = _normalize_text(user_text)
    if not text:
        return "none", ()
    score = 0
    signals: list[str] = []
    explicit_count = _count_any(text, _RETRIEVAL_EXPLICIT_KEYWORDS)
    deictic_count = _count_any(text, _RETRIEVAL_DEICTIC_KEYWORDS)
    evidence_question_count = _count_any(text, _RETRIEVAL_EVIDENCE_QUESTION_KEYWORDS)
    history_fact_count = _count_any(text, _HISTORY_DEPENDENT_FACT_KEYWORDS)
    if explicit_count:
        score += min(4, explicit_count * 2)
        signals.append("explicit_history_anchor")
    if deictic_count:
        score += min(3, deictic_count)
        signals.append("deictic_reference")
    if evidence_question_count:
        score += min(4, evidence_question_count * 2)
        signals.append("evidence_question")
    if _looks_like_isolated_person_fact_query(user_text):
        score += 3
        signals.append("isolated_person_fact_query")
        if history_fact_count:
            score += 1
    if len(text) <= 12 and deictic_count:
        score += 1
        signals.append("short_ambiguous_reference")
    if "?" in text or "\uff1f" in text:
        if explicit_count or deictic_count:
            score += 1
            signals.append("question_with_reference")
    if score >= 5:
        pressure = "high"
    elif score >= 3:
        pressure = "medium"
    elif score >= 1:
        pressure = "low"
    else:
        pressure = "none"
    return pressure, tuple(signals[:6])


def classify_context_scene(user_text: str) -> str:
    text = _normalize_text(user_text)
    if not text:
        return "casual_chat"
    if _has_any(text, _PROJECT_WORK_KEYWORDS):
        return "project_work"
    if _has_any(text, _RUNTIME_STATUS_KEYWORDS):
        return "runtime_status"
    if _has_any(text, _INITIATIVE_FEEDBACK_KEYWORDS):
        return "initiative_feedback"
    if _has_any(text, _MEMORY_REVIEW_KEYWORDS):
        return "memory_review"
    if _has_any(text, _PROJECT_WORK_KEYWORDS):
        return "project_work"
    if _has_any(text, _EMOTIONAL_RELATION_KEYWORDS):
        return "emotional_relation"
    if _has_any(text, ("记忆", "遗忘", "回想", "检索", "上下文", "context", "memory", "forget", "retrieve", "recall")):
        return "memory_review"
    if _has_any(text, ("主动", "反馈", "dismiss", "reply", "approve", "initiative", "proactive", "打扰")):
        return "initiative_feedback"
    if _has_any(text, ("运行", "状态", "指标", "桌面", "runtime", "health", "metrics", "desktop", "presence")):
        return "runtime_status"
    if _has_any(text, ("代码", "测试", "实现", "接入", "文件", "架构", "模块", "plan", "项目", "bug", "test", "implement")):
        return "project_work"
    if _has_any(text, ("关系", "情绪", "难受", "陪", "孤独", "喜欢", "在意", "emotion", "relationship", "feel")):
        return "emotional_relation"
    return "casual_chat"


def snapshot_to_prompt_block(snapshot: ContextualSelfLoopSnapshot, *, max_chars: int = DEFAULT_PROMPT_LIMIT) -> str:
    lines = [
        "## Contextual Self Loop",
        "scope: hidden current-self reconstruction; not visible wording.",
        "principle: keep live context short; retrieve only what the current scene needs.",
        "visibility_rule: do not mention this loop, scene labels, retrieval intents, files, scores, or gates in ordinary chat.",
        "",
        "### Current Horizon",
        f"- current_scene: {snapshot.current_scene}",
        f"- working_context_budget: {snapshot.working_context_budget}",
        f"- forgetting_posture: {snapshot.forgetting_posture}",
        f"- retrieval_pressure: {snapshot.retrieval_pressure}",
        f"- working_self: {snapshot.working_self}",
        f"- initiative_posture: {snapshot.initiative_posture}",
        f"- next_action_bias: {snapshot.next_action_bias}",
        "",
        "### Retrieval Intents",
    ]
    lines.extend(f"- {item}" for item in snapshot.retrieval_intents)
    lines.extend(["", "### Retrieval Pressure Signals"])
    if snapshot.retrieval_pressure_signals:
        lines.extend(f"- {item}" for item in snapshot.retrieval_pressure_signals)
    else:
        lines.append("- none")
    lines.extend(["", "### Admitted Context Bias"])
    lines.extend(f"- {item}" for item in snapshot.admitted_context)
    lines.extend(["", "### Suppressed Context Bias"])
    lines.extend(f"- {item}" for item in snapshot.suppressed_context)
    lines.extend(
        [
            "",
            "### Use",
            "- Use this as a routing posture before applying memory fragments.",
            "- If a memory fragment conflicts with the current owner message, the current owner message wins.",
            "- If the scene is uncertain, answer the live turn first and avoid proactive expansion.",
        ]
    )
    return "\n".join(lines)[:max_chars].rstrip()


def context_file_policy(scene: str, *, rel_path: str, layer: str, default_limit: int) -> dict[str, Any]:
    scene = scene if scene in _SCENE_CONTEXT_LAYERS else "casual_chat"
    layer = _clean_token(layer, limit=80)
    include = layer in _BASE_CONTEXT_LAYERS or layer in _SCENE_CONTEXT_LAYERS.get(scene, set())
    scale = _SCENE_LIMIT_SCALE.get(scene, 0.75)
    limit = max(400, int(default_limit * scale)) if include else 0
    reason = "base_context" if layer in _BASE_CONTEXT_LAYERS else f"scene_{scene}"
    if not include:
        reason = f"suppressed_for_{scene}"
    return {
        "include": include,
        "limit": limit,
        "reason": reason,
        "scene": scene,
        "layer": layer,
        "rel_path": _scrub(rel_path),
    }


def write_contextual_self_loop_state(root: Path, snapshot: ContextualSelfLoopSnapshot) -> None:
    lines = [
        "---",
        "title: Contextual Self Loop State",
        "memory_type: contextual_self_loop_state",
        "time_scope: immediate_runtime",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: xinyu_contextual_self_loop",
        f"updated_at: {_timestamp_or_now_iso(snapshot.evaluated_at)}",
        "status: active",
        "tags: [context, memory, retrieval, forgetting, initiative]",
        "---",
        "",
        "# Contextual Self Loop State",
        "",
        f"- evaluated_at: {snapshot.evaluated_at}",
        f"- last_trigger: {snapshot.trigger}",
        f"- current_scene: {snapshot.current_scene}",
        f"- working_context_budget: {snapshot.working_context_budget}",
        f"- forgetting_posture: {snapshot.forgetting_posture}",
        f"- retrieval_pressure: {snapshot.retrieval_pressure}",
        f"- retrieval_pressure_signals: {','.join(snapshot.retrieval_pressure_signals) if snapshot.retrieval_pressure_signals else 'none'}",
        f"- retrieval_intents: {','.join(snapshot.retrieval_intents)}",
        f"- admitted_context_count: {len(snapshot.admitted_context)}",
        f"- suppressed_context_count: {len(snapshot.suppressed_context)}",
        f"- working_self: {snapshot.working_self}",
        f"- initiative_posture: {snapshot.initiative_posture}",
        f"- next_action_bias: {snapshot.next_action_bias}",
        "",
        "## Boundaries",
        "- short_context_first: true",
        "- retrieval_before_expansion: true",
        "- stable_self_declaration: blocked",
        "- hidden_orchestration_only: true",
        "",
        "## Admitted Context Bias",
    ]
    lines.extend(f"- {item}" for item in snapshot.admitted_context)
    lines.extend(["", "## Suppressed Context Bias"])
    lines.extend(f"- {item}" for item in snapshot.suppressed_context)
    _write_text_atomic(root / STATE_REL, "\n".join(lines).rstrip() + "\n")


def append_contextual_self_loop_trace(root: Path, snapshot: ContextualSelfLoopSnapshot, *, user_text: str = "") -> None:
    event = {
        "event_id": "ctxself-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S") + "-" + _short_hash(time.time_ns()),
        "ts": snapshot.evaluated_at,
        "stage": "contextual_self_loop",
        "status": "evaluated",
        "trigger": snapshot.trigger,
        "current_scene": snapshot.current_scene,
        "working_self": snapshot.working_self,
        "initiative_posture": snapshot.initiative_posture,
        "next_action_bias": snapshot.next_action_bias,
        "retrieval_pressure": snapshot.retrieval_pressure,
        "retrieval_pressure_signal_count": len(snapshot.retrieval_pressure_signals),
        "retrieval_intent_count": len(snapshot.retrieval_intents),
        "admitted_context_count": len(snapshot.admitted_context),
        "suppressed_context_count": len(snapshot.suppressed_context),
        "user_text_hash": _short_hash(user_text, length=16) if user_text else "",
        "notes": list(snapshot.notes),
    }
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_clean_json_value(event), ensure_ascii=False, sort_keys=True) + "\n")


def snapshot_to_json(snapshot: ContextualSelfLoopSnapshot) -> dict[str, Any]:
    return _clean_json_value(asdict(snapshot))


def _scene_config(scene: str) -> dict[str, Any]:
    configs: dict[str, dict[str, Any]] = {
        "project_work": {
            "working_context_budget": "short_task_window",
            "forgetting_posture": "suppress_unrelated_emotion_and_dream_residue",
            "retrieval_intents": ("current_project_goal", "recent_code_changes", "open_test_failures", "owner_latest_instruction"),
            "admitted_context": ("project_state", "runtime_presence_if_relevant", "recent_action_digest"),
            "suppressed_context": ("unrelated_relationship_history", "stale_dream_residue", "raw_long_term_memory"),
            "working_self": "quiet_project_partner",
            "initiative_posture": "restrained_available",
            "next_action_bias": "plan_then_execute",
        },
        "memory_review": {
            "working_context_budget": "short_memory_window",
            "forgetting_posture": "keep_indices_suppress_raw_history",
            "retrieval_intents": ("memory_policy", "context_horizon", "recent_owner_correction", "relevant_feedback_bias"),
            "admitted_context": ("memory_braid", "contextual_self_loop_state", "initiative_feedback_bias"),
            "suppressed_context": ("raw_chat_history", "stale_runtime_noise", "unrelated_action_residue"),
            "working_self": "careful_context_architect",
            "initiative_posture": "hold_unless_owner_asks",
            "next_action_bias": "explain_then_ground",
        },
        "initiative_feedback": {
            "working_context_budget": "short_feedback_window",
            "forgetting_posture": "suppress_unrelated_candidates_keep_feedback_bias",
            "retrieval_intents": ("initiative_lifecycle", "initiative_metrics", "owner_feedback_signal"),
            "admitted_context": ("initiative_lifecycle", "initiative_feedback", "initiative_metrics"),
            "suppressed_context": ("unrelated_proactive_pressure", "old_candidates", "stable_personality_claims"),
            "working_self": "restrained_initiative_operator",
            "initiative_posture": "feedback_shaped",
            "next_action_bias": "adjust_bias_before_action",
        },
        "runtime_status": {
            "working_context_budget": "short_status_window",
            "forgetting_posture": "suppress_personal_memory_keep_runtime_facts",
            "retrieval_intents": ("runtime_presence", "program_awareness", "known_errors"),
            "admitted_context": ("runtime_presence", "program_awareness", "desktop_state"),
            "suppressed_context": ("emotional_residue", "unrelated_memory_fragments", "raw_trace_dump"),
            "working_self": "runtime_status_reporter",
            "initiative_posture": "diagnostic_only",
            "next_action_bias": "state_facts_then_fix",
        },
        "emotional_relation": {
            "working_context_budget": "short_relation_window",
            "forgetting_posture": "suppress_runtime_noise_keep_relation_continuity",
            "retrieval_intents": ("owner_relation", "recent_interaction_tone", "stable_voice_boundary"),
            "admitted_context": ("owner_relation", "memory_braid", "interaction_journal"),
            "suppressed_context": ("code_state_noise", "initiative_scores", "tool_mechanics"),
            "working_self": "attentive_relation_partner",
            "initiative_posture": "quiet_presence",
            "next_action_bias": "respond_to_feeling_first",
        },
        "casual_chat": {
            "working_context_budget": "minimal_live_window",
            "forgetting_posture": "suppress_system_noise_keep_current_message",
            "retrieval_intents": ("current_message_only", "owner_relation_if_needed"),
            "admitted_context": ("current_message", "stable_voice_boundary"),
            "suppressed_context": ("runtime_details", "old_project_state", "proactive_pressure"),
            "working_self": "plain_conversation_partner",
            "initiative_posture": "quiet_by_default",
            "next_action_bias": "answer_naturally",
        },
    }
    return configs.get(scene, configs["casual_chat"])


def _merge_retrieval_pressure_intents(base: tuple[str, ...], pressure: str) -> tuple[str, ...]:
    intents = list(base)
    additions: tuple[str, ...]
    if pressure == "high":
        additions = ("long_history_evidence", "recent_thread_resolution", "current_message_only")
    elif pressure == "medium":
        additions = ("recent_thread_resolution", "sparse_evidence_check")
    elif pressure == "low":
        additions = ("short_reference_resolution",)
    else:
        additions = ()
    for intent in additions:
        if intent not in intents:
            intents.append(intent)
    return tuple(intents)


def _pressure_adjusted_forgetting_posture(base: str, pressure: str) -> str:
    if pressure == "high":
        return "keep_current_turn_retrieve_sparse_evidence"
    if pressure == "medium":
        return "keep_current_turn_retrieve_recent_thread"
    return base


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _count_any(text: str, needles: tuple[str, ...]) -> int:
    return sum(1 for needle in needles if needle and _contains_keyword(text, needle))


def _contains_keyword(text: str, needle: str) -> bool:
    if re.fullmatch(r"[a-z0-9 ]+", needle):
        return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", text) is not None
    return needle in text


def _looks_like_isolated_person_fact_query(user_text: str) -> bool:
    raw = re.sub(r"(?i)\bwwhat\b", "What", _scrub(user_text))
    if "?" not in raw and not re.match(
        r"\s*(?:What|Where|Which|When|Why|How old|Has|Did|Does|Is|In which)\b",
        raw,
    ):
        return False
    match = _EN_PERSON_FACT_QUERY_RE.search(raw)
    if not match:
        return False
    candidate = match.group(1).strip().capitalize()
    return candidate not in _EN_COMMON_ENTITY_NAMES


def _normalize_text(value: Any) -> str:
    return _scrub(value).lower()


def _clean_token(value: Any, *, limit: int = 80) -> str:
    text = re.sub(r"[^A-Za-z0-9_\-:.]+", "_", _scrub(value)).strip("_")
    return (text or "unknown")[:limit]


def _scrub(value: Any) -> str:
    text = str(value or "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[redacted-secret]", text)
    text = _LOCAL_PATH_RE.sub("[local-path]", text)
    return re.sub(r"\s+", " ", text).strip()


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
