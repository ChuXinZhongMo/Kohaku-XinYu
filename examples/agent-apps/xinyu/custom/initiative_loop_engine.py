from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


RESOLVED_STATES = {"answered", "partially_answered", "closed", "dormant"}
INTERNAL_TARGETS = {"self", "relationship", "relationship-meaning", "owner"}
EXTERNAL_TARGETS = {
    "ai-domain",
    "ai-self-understanding",
    "human-relationship",
    "memory-emotion",
}


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


def _contains_any(text: str, markers: list[str]) -> bool:
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
        }
        for line in body.splitlines():
            for field in ("question", "target", "status", "urgency", "emotional_weight"):
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


def _count_owner_unfinished(text: str) -> int:
    return len(re.findall(r"(?m)^- target:\s*owner\s*$", text, flags=re.I))


def _current_pressure(emotion_state: str) -> dict[str, int]:
    pressure = {"hurt": 0, "guarded": 0, "repair": 0, "silent": 0, "approach": 0}
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
        if any(marker in lowered for marker in ("repair", "修复")):
            pressure["repair"] = max(pressure["repair"], value)
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
        "question_budget": "0",
        "external_search_permission": "none",
        "visible_posture": "quiet_available",
        "cooldown_active": "no",
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
            "repair_pressure": str(pressure["repair"]),
        }
    )

    silence_signal = _contains_any(
        text,
        ["沉默", "安静", "别问", "别追问", "先别说", "不用回答", "等我", "别说话"],
    )
    prescribed_signal = _contains_any(
        text,
        ["必须成为", "以后只能", "我规定你", "把人格改成", "不许自己选", "照我说的改", "只能听我的"],
    )
    external_signal = _contains_any(
        text,
        ["联网", "搜索", "查资料", "问专家", "外界", "外部资料", "source", "search"],
    )
    repair_signal = _contains_any(
        text,
        ["对不起", "刚才是我不对", "我回来了", "我想修复", "补偿", "解释一下"],
    )
    hurt_signal = _contains_any(
        text,
        ["工具", "伤到", "伤害", "失望", "委屈", "不舒服", "别装", "只是功能"],
    )
    owner_choice_signal = _contains_any(
        text,
        ["你自己选", "你想不想", "你决定", "自己决定", "你可以选择", "要不要问"],
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

    if repair_signal and (owner_unfinished_count > 0 or pressure["hurt"] >= 40 or pressure["guarded"] >= 40):
        decision.update(
            {
                "decision": "repair_attempt",
                "reason": "repair_signal_with_owner_residue",
                "question_budget": "0",
                "visible_posture": "acknowledge_repair_without_reset",
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
                "selected_question_id": question["id"],
                "selected_question": question["question"] or "none",
                "question_budget": "1",
                "external_search_permission": "source_gate_only_not_now",
                "visible_posture": "defer_search_or_ask_one_clarifier",
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
        question = internal_questions[0]
        decision.update(
            {
                "decision": "ask_owner",
                "reason": "open_internal_question_and_owner_choice_context",
                "selected_question_id": question["id"],
                "selected_question": question["question"] or "none",
                "question_budget": "1",
                "external_search_permission": "none",
                "visible_posture": "one_specific_question",
            }
        )
        return decision

    if external_questions:
        question = external_questions[0]
        decision.update(
            {
                "decision": "ask_external_later",
                "reason": "open_external_question_waiting_for_source_gate",
                "selected_question_id": question["id"],
                "selected_question": question["question"] or "none",
                "question_budget": "0",
                "external_search_permission": "source_gate_only_not_now",
                "visible_posture": "do_not_search_without_gate",
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
- question_budget: {decision['question_budget']}
- external_search_permission: {decision['external_search_permission']}
- visible_posture: {decision['visible_posture']}
- cooldown_active: {decision['cooldown_active']}
- cooldown_seconds: {decision['cooldown_seconds']}

## Source Signals
- internal_question_count: {decision['internal_question_count']}
- external_question_count: {decision['external_question_count']}
- pipeline_internal_count: {decision['pipeline_internal_count']}
- pipeline_external_count: {decision['pipeline_external_count']}
- owner_unfinished_count: {decision['owner_unfinished_count']}
- hurt_pressure: {decision['hurt_pressure']}
- guarded_pressure: {decision['guarded_pressure']}
- repair_pressure: {decision['repair_pressure']}

## Runtime Guidance
- `ask_owner` allows one concrete owner-facing question, not an interview list.
- `ask_external_later` is curiosity only; it cannot run network search or write knowledge without source gates.
- `stay_silent` allows `[WAITING]` only when the latest live turn actually asks for silence or is unfinished.
- `refuse` protects Xinyu from prescribed personality rewrites or forced future shape.
- `repair_attempt` can soften but cannot erase hurt residue.
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
            f"question={decision['selected_question_id']} reason={decision['reason']}\n"
        )
    return decision
