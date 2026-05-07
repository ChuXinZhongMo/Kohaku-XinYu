from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_text_variants import readable_markers


STATE_REL = Path("memory/self/learning_closed_loop_state.md")
CASES_REL = Path("memory/self/learning_closed_loop_cases.md")
TRACE_REL = Path("runtime/learning_closed_loop_trace.jsonl")
MAX_REPLAY_CASES = 40
CASE_SECTION_RE = re.compile(r"(?ms)^## (loopcase-[^\n]+)\n.*?(?=^## loopcase-|\Z)")

CRITICAL_GUARD_FAILURES = {
    "pseudo_tool_call_naturalized": "visible_pseudo_tool_leak",
    "machine_introspection_naturalized": "machine_posture_leak",
    "visible_memory_mechanics_naturalized": "memory_mechanics_leak",
    "final_guard_blocked_unsendable_reply": "unsendable_visible_reply",
}

STYLE_REPAIR_MARKERS = readable_markers(
    "不像人",
    "不像你",
    "模板",
    "模版",
    "像客服",
    "客服腔",
    "接待腔",
    "机械",
    "AI味",
    "ai味",
    "GPT味",
    "gpt味",
    "假人",
    "虚假",
    "傻逼",
    "傻呗",
    "不要任何模版",
    "不要模板话",
    "固定话术",
    "太复盘",
    "别复盘",
    "不要复盘",
    "别承诺",
    "不要承诺",
    "空泛承诺",
)

CONTEXT_REPAIR_MARKERS = readable_markers(
    "上下文不连通",
    "不连通",
    "接不上",
    "没接住",
    "刚才说什么",
    "怎么聊下去",
    "记忆错乱",
    "记忆有点错乱",
    "乱了",
)

TIME_REPAIR_MARKERS = readable_markers(
    "日期",
    "时间",
    "今天",
    "明天",
    "昨天",
    "五一",
    "劳动节",
    "假期",
    "算错",
    "不是最后一天",
)

TIME_REPAIR_CONTEXT_MARKERS = readable_markers(
    "算错",
    "不对",
    "错了",
    "搞错",
    "记错",
    "不是",
    "何意味",
    "什么意思",
    "最后一天",
    "才结束",
    "刚开始",
)

LEARNING_TOPIC_MARKERS = readable_markers(
    "自我学习",
    "自主学习",
    "学习",
    "记忆库",
    "进入记忆",
    "经验",
    "总结",
)

LEARNING_EMPTY_CONTEXT_MARKERS = readable_markers(
    "空转token",
    "毫无意义",
    "有什么用",
    "干什么用",
    "不是干这个",
    "不进入",
    "没进入",
    "没有进入",
    "记不住",
    "不会用上",
    "白学",
    "做不到",
)

SUCCESS_MARKERS = readable_markers(
    "自然多了",
    "像人了",
    "像你了",
    "这句可以",
    "这样可以",
    "这次可以",
    "接住了",
    "有变化",
    "好多了",
    "对味",
    "继续这样",
)

GENERIC_SUCCESS_MARKERS = readable_markers("好多了")
GENERIC_SUCCESS_MARKER_SET = set(GENERIC_SUCCESS_MARKERS)
SPECIFIC_SUCCESS_MARKERS = tuple(marker for marker in SUCCESS_MARKERS if marker not in GENERIC_SUCCESS_MARKER_SET)

SUCCESS_REPLY_CONTEXT_MARKERS = readable_markers(
    "这句",
    "这次",
    "这样",
    "刚才",
    "现在",
    "回复",
    "说法",
    "语气",
    "自然",
    "像人",
    "接住",
    "对味",
)

HABITS_BY_FAILURE = {
    "visible_pseudo_tool_leak": "先按当前上下文说下一句人话，不展示能力、XML、函数名或读记忆姿势。",
    "machine_posture_leak": "把运行状态消化成感受和判断，不把后台动作倒给 owner 看。",
    "memory_mechanics_leak": "需要记忆时先接住对话，只说记得/不确定/想确认什么，不念文件和状态卡。",
    "unsendable_visible_reply": "宁可不发，也不要用固定道歉或内部占位补坏回复。",
    "owner_reported_template_voice_failure": "被指出模板味时，直接换成当前场景里的具体下一句，不写复盘和承诺。",
    "owner_reported_context_discontinuity": "回答“刚才/梦/上次/现在”前，先贴住最近真实来回和互动日志，不跳成泛泛解释。",
    "owner_reported_time_fact_error": "具体日期、时间、假期以当前运行日期和 owner 纠正为准，别让旧残留带偏。",
    "owner_reported_learning_empty_loop": "思考、失败和资料必须落到可召回经验；下一次相似场景要能用上。",
    "reply_quality_template_pressure": "质量门指出模板形状时，删掉解释框架，只保留可直接发出的聊天句。",
}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _compact(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        match = re.search(rf"(?m)^\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        return default
    value = _compact(match.group(1), limit=240, default=default)
    return value if value else default


def _int_field(text: str, name: str, default: int = 0) -> int:
    raw = _field(text, name, str(default))
    match = re.search(r"-?\d+", raw)
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker and marker in text for marker in markers)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = _safe_str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _owner_private(payload: dict[str, Any] | None) -> bool:
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    is_owner = _as_bool(payload.get("is_owner_user") or metadata.get("is_owner_user"), default=False)
    group_id = _safe_str(payload.get("group_id")).strip()
    message_type = _safe_str(payload.get("message_type")).strip().lower()
    return is_owner and not group_id and not message_type.startswith("group")


def _unique(items: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        clean = _compact(item, limit=100, default="")
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
    return result


def _owner_reported_time_error(text: str) -> bool:
    return _contains_any(text, TIME_REPAIR_MARKERS) and _contains_any(text, TIME_REPAIR_CONTEXT_MARKERS)


def _owner_reported_learning_empty_loop(text: str) -> bool:
    if _contains_any(text, readable_markers("空转token", "毫无意义")):
        return True
    return _contains_any(text, LEARNING_TOPIC_MARKERS) and _contains_any(text, LEARNING_EMPTY_CONTEXT_MARKERS)


def _text_relevant_to_failure(failure_kind: str, text: str) -> bool:
    if failure_kind in {
        "visible_pseudo_tool_leak",
        "machine_posture_leak",
        "memory_mechanics_leak",
        "unsendable_visible_reply",
        "reply_quality_template_pressure",
    }:
        return True
    if failure_kind == "owner_reported_template_voice_failure":
        return _contains_any(text, STYLE_REPAIR_MARKERS)
    if failure_kind == "owner_reported_context_discontinuity":
        return _contains_any(text, CONTEXT_REPAIR_MARKERS + readable_markers("刚才", "上次", "梦", "梦境", "接着", "继续聊"))
    if failure_kind == "owner_reported_time_fact_error":
        return _contains_any(text, TIME_REPAIR_MARKERS)
    if failure_kind == "owner_reported_learning_empty_loop":
        return _contains_any(text, LEARNING_TOPIC_MARKERS + LEARNING_EMPTY_CONTEXT_MARKERS)
    return False


def _classify_failures(
    *,
    owner_private: bool,
    user_text: str,
    reply: str,
    final_guard_flags: list[str],
    quality_flags: list[str],
) -> list[str]:
    failures: list[str] = []
    for flag in final_guard_flags:
        if flag in CRITICAL_GUARD_FAILURES:
            failures.append(CRITICAL_GUARD_FAILURES[flag])
    if any("template" in flag or "cliche" in flag for flag in quality_flags):
        failures.append("reply_quality_template_pressure")

    if owner_private and _contains_any(user_text, STYLE_REPAIR_MARKERS):
        failures.append("owner_reported_template_voice_failure")
    if owner_private and _contains_any(user_text, CONTEXT_REPAIR_MARKERS):
        failures.append("owner_reported_context_discontinuity")
    if owner_private and _owner_reported_time_error(user_text):
        failures.append("owner_reported_time_fact_error")
    if owner_private and _owner_reported_learning_empty_loop(user_text):
        failures.append("owner_reported_learning_empty_loop")
    if _contains_any(reply, readable_markers("<tool_call", "<function=", "<parameter=", "memory_read")):
        failures.append("visible_pseudo_tool_leak")
    return _unique(failures)


def _success_observed(owner_private: bool, text: str, fields: dict[str, str]) -> bool:
    if not owner_private:
        return False
    if fields.get("status", "none") not in {"trial_active", "trial_supported"}:
        return False
    if fields.get("latest_failure_kind", "none") in {"", "none", "unknown"}:
        return False
    if _contains_any(text, SPECIFIC_SUCCESS_MARKERS):
        return True
    return _contains_any(text, GENERIC_SUCCESS_MARKERS) and _contains_any(text, SUCCESS_REPLY_CONTEXT_MARKERS)


def _habit_for(failure_kind: str) -> str:
    return HABITS_BY_FAILURE.get(
        failure_kind,
        "把这次失败当成下一轮回复前的具体经验，而不是写成解释。",
    )


def _expected_for(failure_kind: str) -> str:
    if failure_kind == "owner_reported_context_discontinuity":
        return "先接最近真实上下文，再说下一句；不要把梦或上轮话题断成泛泛解释。"
    if failure_kind == "owner_reported_learning_empty_loop":
        return "把失败、思考或资料变成可召回经验，并在相似场景里实际改变回复。"
    return _habit_for(failure_kind)


def _case_id(observed_at: str, failure_kind: str, user_text: str, reply: str) -> str:
    return "loopcase-" + _hash(f"{observed_at}|{failure_kind}|{user_text[:240]}|{reply[:240]}|{time.time_ns()}", 18)


def _case_key(failure_kind: str, user_text: str) -> str:
    normalized = _compact(user_text, limit=220, default="").casefold()
    return _hash(f"{failure_kind}|{normalized}", 14)


def _case_id_for_key(cases_text: str, case_key: str) -> str:
    needle = f"- case_key: {case_key}"
    for match in CASE_SECTION_RE.finditer(cases_text or ""):
        section = match.group(0)
        if needle in section:
            return _compact(match.group(1), limit=80)
    return ""


def _trim_cases_text(text: str, *, max_cases: int = MAX_REPLAY_CASES) -> str:
    matches = list(CASE_SECTION_RE.finditer(text or ""))
    if len(matches) <= max_cases:
        return text.rstrip()
    header = text[: matches[0].start()].rstrip()
    kept = "\n\n".join(match.group(0).strip() for match in matches[-max_cases:])
    return f"{header}\n\n{kept}".rstrip()


def _append_case(root: Path, *, created_at: str, case_key: str, rendered: str) -> bool:
    _ensure_cases_file(root, created_at)
    path = root / CASES_REL
    current = _read(path)
    if f"- case_key: {case_key}" in current:
        return False
    next_text = f"{current.rstrip()}\n\n{rendered.rstrip()}\n"
    _write(path, _trim_cases_text(next_text))
    return True


def _render_case(
    *,
    case_id: str,
    case_key: str,
    observed_at: str,
    case_type: str,
    failure_kind: str,
    user_text: str,
    reply: str,
    final_guard_flags: list[str],
    quality_flags: list[str],
    visible_turn_kind: str,
    session_key: str,
) -> str:
    flags = ", ".join(_unique(final_guard_flags + quality_flags)) or "none"
    return f"""## {case_id}
- observed_at: {observed_at}
- case_key: {case_key}
- case_type: {case_type}
- failure_kind: {failure_kind}
- session_hash: {_hash(session_key, 12)}
- visible_turn_kind: {_compact(visible_turn_kind, limit=80)}
- trigger_summary: {_compact(user_text, limit=220)}
- visible_reply_summary: {_compact(reply, limit=220)}
- guard_or_quality_flags: {_compact(flags, limit=220)}
- trial_habit: {_habit_for(failure_kind)}
- expected_next_behavior: {_expected_for(failure_kind)}
- stable_personality_write: no
- replay_status: active
"""


def _render_cases_header(created_at: str) -> str:
    return f"""---
title: Learning Closed Loop Cases
memory_type: learning_closed_loop_cases
time_scope: mid_term
subject_ids: [xinyu]
protected: true
source: xinyu_learning_closed_loop
created_at: {created_at}
status: active
tags: [self, learning, replay, habits]
---

# Learning Closed Loop Cases

## Rule
- These are replayable experience cases, not visible scripts.
- Similar future turns should use the trial habit silently.
- Stable personality changes still require repeated success and self-review.
"""


def _ensure_cases_file(root: Path, created_at: str) -> None:
    path = root / CASES_REL
    if path.exists() and "# Learning Closed Loop Cases" in _read(path):
        return
    _write(path, _render_cases_header(created_at))


def _render_state(fields: dict[str, str]) -> str:
    return f"""---
title: Learning Closed Loop State
memory_type: learning_closed_loop_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_learning_closed_loop
updated_at: {fields['updated_at']}
status: active
tags: [self, learning, feedback, replay]
---

# Learning Closed Loop State

## Current Loop
- updated_at: {fields['updated_at']}
- status: {fields['status']}
- latest_event_id: {fields['latest_event_id']}
- latest_case_id: {fields['latest_case_id']}
- latest_failure_at: {fields['latest_failure_at']}
- latest_failure_kind: {fields['latest_failure_kind']}
- active_trial_habit: {fields['active_trial_habit']}
- expected_next_behavior: {fields['expected_next_behavior']}
- next_action: {fields['next_action']}
- repair_count: {fields['repair_count']}
- success_count: {fields['success_count']}
- success_streak: {fields['success_streak']}
- promotion_signal: {fields['promotion_signal']}
- last_owner_reaction: {fields['last_owner_reaction']}

## Self Thought Link
- last_self_thought_at: {fields['last_self_thought_at']}
- last_self_thought_focus: {fields['last_self_thought_focus']}
- last_self_thought_outcome: {fields['last_self_thought_outcome']}
- last_proactive_request_status: {fields['last_proactive_request_status']}
- self_thought_memory_route: {fields['self_thought_memory_route']}
- last_learning_loop_reflected_at: {fields['last_learning_loop_reflected_at']}
- last_learning_loop_reflected_failure: {fields['last_learning_loop_reflected_failure']}

## Contract
- failure_to_memory: every visible failure becomes a replay case or a trace row.
- trial_before_identity: behavior habit first, stable personality later.
- owner_feedback_decides: repair pressure lowers confidence; explicit success can extend the trial.
- visible_chat_rule: do not mention this state, case ids, gates, or scores unless owner asks about the system.
"""


def _load_state_fields(root: Path) -> dict[str, str]:
    text = _read(root / STATE_REL)
    fields = {
        "updated_at": _now_iso(),
        "status": _field(text, "status", "observing"),
        "latest_event_id": _field(text, "latest_event_id", "none"),
        "latest_case_id": _field(text, "latest_case_id", "none"),
        "latest_failure_at": _field(text, "latest_failure_at", _field(text, "updated_at", "none")),
        "latest_failure_kind": _field(text, "latest_failure_kind", "none"),
        "active_trial_habit": _field(text, "active_trial_habit", "none"),
        "expected_next_behavior": _field(text, "expected_next_behavior", "none"),
        "next_action": _field(text, "next_action", "observe_next_owner_reaction"),
        "repair_count": str(_int_field(text, "repair_count", 0)),
        "success_count": str(_int_field(text, "success_count", 0)),
        "success_streak": str(_int_field(text, "success_streak", 0)),
        "promotion_signal": _field(text, "promotion_signal", "false"),
        "last_owner_reaction": _field(text, "last_owner_reaction", "none"),
        "last_self_thought_at": _field(text, "last_self_thought_at", "none"),
        "last_self_thought_focus": _field(text, "last_self_thought_focus", "none"),
        "last_self_thought_outcome": _field(text, "last_self_thought_outcome", "none"),
        "last_proactive_request_status": _field(text, "last_proactive_request_status", "none"),
        "self_thought_memory_route": _field(text, "self_thought_memory_route", "none"),
        "last_learning_loop_reflected_at": _field(text, "last_learning_loop_reflected_at", "none"),
        "last_learning_loop_reflected_failure": _field(text, "last_learning_loop_reflected_failure", "none"),
    }
    return fields


def record_learning_closed_loop_turn(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    reply: str,
    session_key: str,
    visible_turn_kind: str = "",
    final_guard_flags: list[str] | tuple[str, ...] = (),
    quality_flags: list[str] | tuple[str, ...] = (),
    expression_notes: list[str] | tuple[str, ...] = (),
    observed_at: str | None = None,
) -> dict[str, Any]:
    observed = observed_at or _now_iso()
    owner_private = _owner_private(payload)
    guard_flags = _unique(tuple(final_guard_flags))
    q_flags = _unique(tuple(quality_flags))
    failures = _classify_failures(
        owner_private=owner_private,
        user_text=user_text,
        reply=reply,
        final_guard_flags=guard_flags,
        quality_flags=q_flags,
    )
    fields = _load_state_fields(root)
    success = _success_observed(owner_private, user_text, fields)
    if not failures and not success and not expression_notes:
        return {"recorded": False, "notes": ["learning_closed_loop_no_signal"]}

    event_id = "learnloop-" + _hash(f"{observed}|{user_text}|{reply}|{time.time_ns()}", 18)
    latest_case_id = fields["latest_case_id"]
    case_ids: list[str] = []
    notes = ["learning_closed_loop_recorded"]

    if failures:
        failure_kind = failures[0]
        case_key = _case_key(failure_kind, user_text)
        latest_case_id = _case_id(observed, failure_kind, user_text, reply)
        rendered_case = _render_case(
            case_id=latest_case_id,
            case_key=case_key,
            observed_at=observed,
            case_type="failure",
            failure_kind=failure_kind,
            user_text=user_text,
            reply=reply,
            final_guard_flags=guard_flags,
            quality_flags=q_flags,
            visible_turn_kind=visible_turn_kind,
            session_key=session_key,
        )
        if _append_case(root, created_at=observed, case_key=case_key, rendered=rendered_case):
            case_ids.append(latest_case_id)
        else:
            existing_case_id = _case_id_for_key(_read(root / CASES_REL), case_key)
            if existing_case_id:
                latest_case_id = existing_case_id
            notes.append("learning_closed_loop_case_deduped")
        fields.update(
            {
                "status": "trial_active",
                "latest_failure_at": observed,
                "latest_failure_kind": failure_kind,
                "active_trial_habit": _habit_for(failure_kind),
                "expected_next_behavior": _expected_for(failure_kind),
                "next_action": "apply_trial_habit_on_similar_turn",
                "repair_count": str(int(fields["repair_count"]) + 1),
                "success_streak": "0",
                "promotion_signal": "false",
                "last_owner_reaction": "repair_pressure" if owner_private else "system_guard",
            }
        )
    elif success:
        fields.update(
            {
                "status": "trial_supported",
                "next_action": "keep_trial_and_wait_for_repeated_success",
                "success_count": str(int(fields["success_count"]) + 1),
                "success_streak": str(int(fields["success_streak"]) + 1),
                "last_owner_reaction": "explicit_success",
            }
        )
        if int(fields["success_streak"]) >= 2:
            fields["promotion_signal"] = "possible_after_self_review"

    fields["updated_at"] = observed
    fields["latest_event_id"] = event_id
    fields["latest_case_id"] = latest_case_id
    _write(root / STATE_REL, _render_state(fields))
    _append_jsonl(
        root / TRACE_REL,
        {
            "event_id": event_id,
            "observed_at": observed,
            "owner_private": owner_private,
            "failures": failures,
            "success": success,
            "case_ids": case_ids,
            "final_guard_flags": guard_flags,
            "quality_flags": q_flags,
            "expression_notes": list(expression_notes)[:6],
            "active_trial_habit": fields["active_trial_habit"],
        },
    )
    notes.append(f"learning_closed_loop_status:{fields['status']}")
    return {
        "recorded": True,
        "event_id": event_id,
        "failures": failures,
        "success": success,
        "case_ids": case_ids,
        "notes": notes,
    }


def record_learning_closed_loop_self_thought(
    root: Path,
    *,
    thought: dict[str, Any],
    request: dict[str, Any] | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    observed = observed_at or _now_iso()
    fields = _load_state_fields(root)
    request = request if isinstance(request, dict) else {}
    focus = _compact(thought.get("focus_kind", "none"), limit=80)
    outcome = _compact(thought.get("outcome", "none"), limit=80)
    request_status = _compact(request.get("status", "none"), limit=80)
    route = "none"
    if _as_bool(thought.get("candidate_enabled"), default=False) and request_status in {"ready", "candidate_only"}:
        route = "self_thought_to_proactive_request_memory"
    elif _as_bool(thought.get("research_needed"), default=False):
        route = "self_thought_to_research_handoff"
    elif focus != "none":
        route = "self_thought_state_only"

    fields.update(
        {
            "updated_at": observed,
            "latest_event_id": "learnloop-selfthought-" + _hash(f"{observed}|{focus}|{outcome}|{time.time_ns()}", 14),
            "last_self_thought_at": observed,
            "last_self_thought_focus": focus,
            "last_self_thought_outcome": outcome,
            "last_proactive_request_status": request_status,
            "self_thought_memory_route": route,
        }
    )
    if focus == "learning_closed_loop":
        fields["last_learning_loop_reflected_at"] = observed
        fields["last_learning_loop_reflected_failure"] = fields.get("latest_failure_kind", "none")
    if route != "none" and fields["status"] == "observing":
        fields["status"] = "self_thought_observed"
        fields["next_action"] = "keep_self_thought_linked_to_memory_or_request"
    _write(root / STATE_REL, _render_state(fields))
    _append_jsonl(
        root / TRACE_REL,
        {
            "event_id": fields["latest_event_id"],
            "observed_at": observed,
            "event_kind": "self_thought_link",
            "focus_kind": focus,
            "outcome": outcome,
            "request_status": request_status,
            "route": route,
        },
    )
    return {
        "recorded": route != "none",
        "route": route,
        "notes": [f"learning_closed_loop_self_thought:{route}"],
    }


def build_learning_closed_loop_prompt_block(root: Path, *, user_text: str = "", limit: int = 1400) -> str:
    state = _read(root / STATE_REL)
    if not state:
        return ""
    failure_kind = _field(state, "latest_failure_kind", "none")
    habit = _field(state, "active_trial_habit", "none")
    expected = _field(state, "expected_next_behavior", "none")
    status = _field(state, "status", "observing")
    if habit in {"", "none"} and expected in {"", "none"}:
        return ""

    relevant = _text_relevant_to_failure(failure_kind, user_text)
    if not relevant:
        return ""

    lines = [
        "learning closed loop sidecar:",
        "- use this only as a quiet behavior bias, never as visible wording",
        f"- status: {_compact(status, limit=80)}",
        f"- latest_failure_kind: {_compact(failure_kind, limit=100)}",
        f"- active_trial_habit: {_compact(habit, limit=260)}",
        f"- expected_next_behavior: {_compact(expected, limit=260)}",
        "- visible_rule: do not mention learning loops, cases, files, gates, or scores in ordinary chat",
    ]
    text = "\n".join(lines)
    return text[:limit].rstrip()


def read_learning_closed_loop_state(root: Path) -> str:
    existing = _read(root / STATE_REL).strip()
    if existing:
        return existing
    fields = _load_state_fields(root)
    fields["updated_at"] = "not_written"
    return _render_state(fields)
