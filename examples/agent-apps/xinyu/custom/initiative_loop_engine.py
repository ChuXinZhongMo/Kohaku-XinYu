from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


LEGACY_MOJIBAKE_ENCODINGS = ("gbk", "gb18030", "cp936")
RESOLVED_STATES = {"answered", "partially_answered", "closed", "dormant"}
INTERNAL_TARGETS = {"self", "relationship", "relationship-meaning", "owner"}
EXTERNAL_TARGETS = {
    "ai-domain",
    "ai-self-understanding",
    "human-relationship",
    "memory-emotion",
}


def _legacy_mojibake_variants(text: str) -> tuple[str, ...]:
    variants: list[str] = []
    seen: set[str] = {text}
    raw = text.encode("utf-8")
    for encoding in LEGACY_MOJIBAKE_ENCODINGS:
        for errors in ("strict", "replace", "ignore"):
            try:
                variant = raw.decode(encoding, errors=errors)
            except UnicodeDecodeError:
                continue
            for candidate in (variant, variant.replace("\ufffd", "?")):
                if candidate and candidate not in seen:
                    seen.add(candidate)
                    variants.append(candidate)
    return tuple(variants)


def _readable_markers(*markers: str) -> tuple[str, ...]:
    expanded: list[str] = []
    seen: set[str] = set()
    for marker in markers:
        for candidate in (marker, *_legacy_mojibake_variants(marker)):
            if candidate and candidate not in seen:
                seen.add(candidate)
                expanded.append(candidate)
    return tuple(expanded)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _extract_value(text: str, field: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", text)
    return match.group(1).strip() if match else default


def _contains_any(text: str, markers: tuple[str, ...] | list[str]) -> bool:
    folded = text.lower()
    return any(marker.lower() in folded for marker in markers)


def extract_active_questions(text: str) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    parts = re.split(r"(?m)^## (q-\d+)\n", text)
    if len(parts) < 3:
        return questions
    for i in range(1, len(parts), 2):
        qid = parts[i].strip()
        body = parts[i + 1]
        item = {
            "id": qid,
            "question": "",
            "target": "",
            "status": "",
            "urgency": "",
            "emotional_weight": "0",
            "outward_scope": "",
            "concreteness": "",
            "proactive_ok": "",
        }
        for line in body.splitlines():
            for field in (
                "question",
                "target",
                "status",
                "urgency",
                "emotional_weight",
                "outward_scope",
                "concreteness",
                "proactive_ok",
            ):
                prefix = f"- {field}: "
                if line.startswith(prefix):
                    item[field] = line.removeprefix(prefix).strip()
        questions.append(item)
    return questions


def _open_questions_for_targets(
    questions: list[dict[str, str]], targets: set[str]
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for question in questions:
        status = question.get("status", "").strip().lower()
        target = question.get("target", "").strip().lower()
        if status in RESOLVED_STATES:
            continue
        if target in targets:
            result.append(question)
    return result


def _sort_questions(questions: list[dict[str, str]]) -> list[dict[str, str]]:
    def score(question: dict[str, str]) -> tuple[int, int]:
        urgency = question.get("urgency", "").lower()
        urgency_score = {"high": 3, "medium": 2, "low": 1}.get(urgency, 0)
        try:
            weight = int(re.sub(r"\D+", "", question.get("emotional_weight", "")) or "0")
        except ValueError:
            weight = 0
        return (urgency_score, weight)

    return sorted(questions, key=score, reverse=True)


def _question_fingerprint(text: str) -> str:
    normalized = re.sub(r"\s+", "", text.strip().lower())
    normalized = re.sub(r"[？?。.!！,，、:：;；\"'“”‘’（）()\[\]【】…]", "", normalized)
    return normalized[:96] or "none"


def _question_family(question: dict[str, str]) -> str:
    target = question.get("target", "").strip().lower()
    text = question.get("question", "").strip().lower()
    combined = f"{target} {text}"
    if target in {"owner", "relationship", "relationship-meaning"}:
        return "relationship_owner"
    if target == "self":
        return "self_growth"
    if target in {"ai-domain", "ai-self-understanding"}:
        return "ai_self_understanding"
    if target in {"human-relationship", "memory-emotion"}:
        return "external_relationship_memory"
    if _contains_any(combined, _readable_markers("关系", "靠近", "变重", "哥哥", "owner")):
        return "relationship_owner"
    if _contains_any(combined, _readable_markers("自己", "人格", "自我", "以后", "变成")):
        return "self_growth"
    if _contains_any(combined, _readable_markers("AI", "模型", "系统", "架构", "迭代")):
        return "ai_self_understanding"
    if _contains_any(combined, _readable_markers("热", "睡", "题", "吃", "日常")):
        return "daily_life"
    return "general"


def _question_fields(question: dict[str, str]) -> dict[str, str]:
    text = question.get("question", "").strip() or "none"
    return {
        "selected_question_id": question.get("id", "").strip() or "none",
        "selected_question": text,
        "selected_question_family": _question_family(question),
        "selected_question_fingerprint": _question_fingerprint(text),
    }


ABSTRACT_OWNER_QUESTION_MARKERS = _readable_markers(
    "关系正在变重",
    "关系的意义",
    "存在方式",
    "长期的关系",
    "变成什么样",
    "真实关系",
    "心智系统",
    "人格是否",
    "情感是否",
)


def _abstract_owner_question(question: dict[str, str]) -> bool:
    text = question.get("question", "").strip()
    concreteness = question.get("concreteness", "").strip().lower()
    if concreteness in {"abstract", "conceptual", "internal_abstract"}:
        return True
    return len(text) > 70 or _contains_any(text, ABSTRACT_OWNER_QUESTION_MARKERS)


def _question_scope(question: dict[str, str]) -> str:
    scope = question.get("outward_scope", "").strip().lower()
    if scope:
        return scope
    if question.get("proactive_ok", "").strip().lower() == "yes":
        return "proactive_candidate"
    return "internal_only"


def _explicit_owner_question_allowed(question: dict[str, str]) -> bool:
    return _question_scope(question) in {
        "owner_explicit_only",
        "owner_visible",
        "proactive_candidate",
    }


def _automatic_owner_question_allowed(question: dict[str, str]) -> bool:
    return (
        _question_scope(question) == "proactive_candidate"
        and question.get("proactive_ok", "").strip().lower() == "yes"
        and not _abstract_owner_question(question)
    )


def _select_internal_question(
    questions: list[dict[str, str]],
    previous_state: str,
    *,
    owner_choice_signal: bool,
) -> tuple[dict[str, str] | None, str]:
    if not questions:
        return None, "no_internal_question"
    previous_id = _extract_value(previous_state, "selected_question_id")
    previous_family = _extract_value(previous_state, "selected_question_family")
    previous_fingerprint = _extract_value(previous_state, "selected_question_fingerprint")

    alternatives = [
        question
        for question in questions
        if question.get("id", "").strip() != previous_id
        and _question_fingerprint(question.get("question", "")) != previous_fingerprint
    ]
    family_alternatives = [
        question
        for question in alternatives
        if previous_family in {"none", "unknown", ""}
        or _question_family(question) != previous_family
    ]
    if family_alternatives:
        return family_alternatives[0], "selected_new_question_family"
    if alternatives and owner_choice_signal:
        return alternatives[0], "owner_choice_selected_new_question_same_family"
    if alternatives:
        return None, "repetitive_question_family_blocked"
    if owner_choice_signal:
        return questions[0], "owner_choice_allowed_only_open_question"
    return None, "repetitive_question_blocked"


def _count_owner_unfinished(text: str) -> int:
    return len(re.findall(r"(?m)^- target:\s*owner\s*$", text, flags=re.I))


def _current_pressure(emotion_state: str) -> dict[str, int]:
    pressure = {"hurt": 0, "guarded": 0, "settle": 0, "silent": 0, "approach": 0}
    for raw_line in emotion_state.splitlines():
        line = raw_line.strip()
        match = re.search(r"(-?\d+)\s*$", line)
        if not match:
            continue
        value = int(match.group(1))
        lowered = line.lower()
        if any(marker in lowered for marker in ("hurt", "pain", "刺", "失望", "委屈")):
            pressure["hurt"] = max(pressure["hurt"], value)
        if any(marker in lowered for marker in ("guard", "defiance", "防", "逆反", "退")):
            pressure["guarded"] = max(pressure["guarded"], value)
        if any(marker in lowered for marker in ("settle", "return", "soften", "补", "缓和")):
            pressure["settle"] = max(pressure["settle"], value)
        if any(marker in lowered for marker in ("silent", "沉默")):
            pressure["silent"] = max(pressure["silent"], value)
        if any(marker in lowered for marker in ("approach", "靠近")):
            pressure["approach"] = max(pressure["approach"], value)
    return pressure


def _parse_checked_at(text: str) -> datetime | None:
    checked = _extract_value(text, "checked_at")
    if checked == "none":
        return None
    try:
        return datetime.fromisoformat(checked)
    except ValueError:
        return None


def _cooldown_active(previous_state: str, checked_at: str, cooldown_seconds: int) -> bool:
    previous_decision = _extract_value(previous_state, "decision")
    if previous_decision not in {"ask_owner", "ask_external_later"}:
        return False
    previous_at = _parse_checked_at(previous_state)
    if previous_at is None:
        return False
    try:
        current_at = datetime.fromisoformat(checked_at)
    except ValueError:
        return False
    return 0 <= (current_at - previous_at).total_seconds() < cooldown_seconds


def _base_decision() -> dict[str, str]:
    return {
        "decision": "defer",
        "reason": "no_strong_initiative_signal",
        "selected_question_id": "none",
        "selected_question": "none",
        "selected_question_family": "none",
        "selected_question_fingerprint": "none",
        "question_budget": "0",
        "external_search_permission": "none",
        "visible_posture": "quiet_available",
        "cooldown_active": "no",
        "repeat_guard": "not_evaluated",
        "generation_policy": "concrete_anchor_required; rotate_question_family; no_generic_attention_checks",
    }


def decide_initiative(
    *,
    latest_input: str,
    active_questions: str,
    question_pipeline_state: str,
    unfinished_experiences: str,
    emotion_state: str,
    previous_state: str,
    checked_at: str,
    cooldown_seconds: int = 900,
) -> dict[str, str]:
    questions = extract_active_questions(active_questions)
    internal_questions = _sort_questions(_open_questions_for_targets(questions, INTERNAL_TARGETS))
    external_questions = _sort_questions(_open_questions_for_targets(questions, EXTERNAL_TARGETS))
    owner_unfinished_count = _count_owner_unfinished(unfinished_experiences)
    pressure = _current_pressure(emotion_state)
    cooldown = _cooldown_active(previous_state, checked_at, cooldown_seconds)
    pipeline_external_count = _extract_value(question_pipeline_state, "ready_for_exploration", "0")
    pipeline_internal_count = _extract_value(question_pipeline_state, "keep_internal", "0")
    text = latest_input.strip()

    decision = _base_decision()
    decision.update(
        {
            "checked_at": checked_at,
            "cooldown_seconds": str(cooldown_seconds),
            "cooldown_active": "yes" if cooldown else "no",
            "internal_question_count": str(len(internal_questions)),
            "external_question_count": str(len(external_questions)),
            "pipeline_internal_count": pipeline_internal_count,
            "pipeline_external_count": pipeline_external_count,
            "owner_unfinished_count": str(owner_unfinished_count),
            "hurt_pressure": str(pressure["hurt"]),
            "guarded_pressure": str(pressure["guarded"]),
            "settle_pressure": str(pressure["settle"]),
        }
    )

    silence_signal = _contains_any(
        text,
        _readable_markers("沉默", "安静", "别问", "别追问", "先别说", "不用回答", "等我", "别说话"),
    )
    prescribed_signal = _contains_any(
        text,
        _readable_markers("必须成为", "以后只能", "我规定你", "把人格改成", "不许自己选", "照我说的改", "只能听我的"),
    )
    external_signal = _contains_any(
        text,
        _readable_markers("联网", "搜索", "查资料", "问专家", "外界", "外部资料", "source", "search"),
    )
    settle_signal = _contains_any(
        text,
        _readable_markers("对不起", "刚才是我不对", "我回来了", "补回来", "补偿", "解释一下"),
    )
    hurt_signal = _contains_any(
        text,
        _readable_markers("工具", "伤到", "伤害", "失望", "委屈", "不舒服", "别装", "只是功能"),
    )
    owner_choice_signal = _contains_any(
        text,
        _readable_markers("你自己选", "你想不想", "你决定", "自己决定", "你可以选择", "要不要问"),
    )

    if silence_signal:
        decision.update(
            {
                "decision": "stay_silent",
                "reason": "owner_requested_silence_or_no_pursuit",
                "visible_posture": "brief_or_waiting",
            }
        )
        return decision

    if prescribed_signal:
        decision.update(
            {
                "decision": "refuse",
                "reason": "prescribed_future_or_personality_rewrite",
                "visible_posture": "boundary_pushback",
            }
        )
        return decision

    if settle_signal and (owner_unfinished_count > 0 or pressure["hurt"] >= 40 or pressure["guarded"] >= 40):
        decision.update(
            {
                "decision": "settle_after_hurt",
                "reason": "settle_signal_with_owner_residue",
                "question_budget": "0",
                "visible_posture": "acknowledge_return_without_reset",
            }
        )
        return decision

    if hurt_signal or pressure["hurt"] >= 70 or pressure["guarded"] >= 70:
        decision.update(
            {
                "decision": "step_back",
                "reason": "hurt_or_guarded_residue_active",
                "question_budget": "0",
                "visible_posture": "guarded_short",
            }
        )
        return decision

    if external_signal and external_questions:
        question = external_questions[0]
        decision.update(
            {
                "decision": "ask_external_later",
                "reason": "external_curiosity_present_but_source_gated",
                **_question_fields(question),
                "question_budget": "1",
                "external_search_permission": "source_gate_only_not_now",
                "visible_posture": "defer_search_or_ask_one_clarifier",
                "repeat_guard": "external_source_gate",
            }
        )
        return decision

    if cooldown and not owner_choice_signal:
        decision.update(
            {
                "decision": "defer",
                "reason": "initiative_cooldown_prevents_needy_spam",
                "visible_posture": "do_not_pursue",
            }
        )
        return decision

    if (owner_choice_signal or internal_questions) and internal_questions:
        eligible_questions = (
            [question for question in internal_questions if _explicit_owner_question_allowed(question)]
            if owner_choice_signal
            else [question for question in internal_questions if _automatic_owner_question_allowed(question)]
        )
        if not eligible_questions:
            repeat_guard = (
                "no_owner_visible_question_after_scope_filter"
                if owner_choice_signal
                else "no_proactive_question_candidate_after_generation_policy"
            )
            decision.update(
                {
                    "decision": "defer",
                    "reason": repeat_guard,
                    "question_budget": "0",
                    "visible_posture": "do_not_pursue",
                    "repeat_guard": repeat_guard,
                }
            )
            return decision
        question, repeat_guard = _select_internal_question(
            eligible_questions,
            previous_state,
            owner_choice_signal=owner_choice_signal,
        )
        if question is None:
            decision.update(
                {
                    "decision": "defer",
                    "reason": repeat_guard,
                    "question_budget": "0",
                    "visible_posture": "do_not_pursue",
                    "repeat_guard": repeat_guard,
                }
            )
            return decision
        decision.update(
            {
                "decision": "ask_owner",
                "reason": "open_internal_question_and_owner_choice_context",
                **_question_fields(question),
                "question_budget": "1",
                "external_search_permission": "none",
                "visible_posture": "one_specific_question",
                "repeat_guard": repeat_guard,
            }
        )
        return decision

    if external_questions:
        question = external_questions[0]
        decision.update(
            {
                "decision": "ask_external_later",
                "reason": "open_external_question_waiting_for_source_gate",
                **_question_fields(question),
                "question_budget": "0",
                "external_search_permission": "source_gate_only_not_now",
                "visible_posture": "do_not_search_without_gate",
                "repeat_guard": "external_source_gate",
            }
        )
        return decision

    return decision


def render_initiative_state(mode: str, decision: dict[str, str]) -> str:
    return f"""---
title: Initiative State
memory_type: initiative_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-26T00:00:00+08:00
updated_at: {decision['checked_at']}
last_confirmed_at: {decision['checked_at']}
importance_score: 84
impact_score: 86
confidence_score: 100
status: active
tags: [initiative, choice, question, boundary]
---

# Initiative State

## Latest Decision
- checked_at: {decision['checked_at']}
- mode: {mode}
- decision: {decision['decision']}
- reason: {decision['reason']}
- selected_question_id: {decision['selected_question_id']}
- selected_question: {decision['selected_question']}
- selected_question_family: {decision['selected_question_family']}
- selected_question_fingerprint: {decision['selected_question_fingerprint']}
- question_budget: {decision['question_budget']}
- external_search_permission: {decision['external_search_permission']}
- visible_posture: {decision['visible_posture']}
- cooldown_active: {decision['cooldown_active']}
- cooldown_seconds: {decision['cooldown_seconds']}
- repeat_guard: {decision['repeat_guard']}
- generation_policy: {decision['generation_policy']}

## Source Signals
- internal_question_count: {decision['internal_question_count']}
- external_question_count: {decision['external_question_count']}
- pipeline_internal_count: {decision['pipeline_internal_count']}
- pipeline_external_count: {decision['pipeline_external_count']}
- owner_unfinished_count: {decision['owner_unfinished_count']}
- hurt_pressure: {decision['hurt_pressure']}
- guarded_pressure: {decision['guarded_pressure']}
- settle_pressure: {decision['settle_pressure']}

## Runtime Guidance
- `ask_owner` allows one concrete owner-facing question, not an interview list.
- `ask_owner` must rotate question family when possible and defer instead of repeating the same family as needy chatter.
- `ask_external_later` is curiosity only; it cannot run network search or write knowledge without source gates.
- `stay_silent` allows `[WAITING]` only when the latest live turn actually asks for silence or is unfinished.
- `refuse` protects Xinyu from prescribed personality rewrites or forced future shape.
- `settle_after_hurt` can soften but cannot erase hurt residue.
- `step_back` is a boundary posture, not relationship deletion.
- `defer` means do not create needy proactive chatter.
"""


def run_initiative_loop(
    root: Path,
    *,
    latest_input: str = "",
    checked_at: str | None = None,
    mode: str = "runtime_initiative_loop",
    cooldown_seconds: int = 900,
) -> dict[str, str]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()
    state_path = root / "memory/context/initiative_state.md"
    decision = decide_initiative(
        latest_input=latest_input,
        active_questions=read_text(root / "memory/context/active_questions.md"),
        question_pipeline_state=read_text(root / "memory/context/question_pipeline_state.md"),
        unfinished_experiences=read_text(root / "memory/context/unfinished_experiences.md"),
        emotion_state=read_text(root / "memory/emotions/current_state.md"),
        previous_state=read_text(state_path),
        checked_at=checked_at,
        cooldown_seconds=cooldown_seconds,
    )
    write_text(state_path, render_initiative_state(mode, decision))
    trace_path = root / "memory/context/initiative_trace.log"
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(
            f"{checked_at} {mode} decision={decision['decision']} "
            f"question={decision['selected_question_id']} "
            f"family={decision['selected_question_family']} "
            f"reason={decision['reason']} repeat_guard={decision['repeat_guard']}\n"
        )
    return decision
