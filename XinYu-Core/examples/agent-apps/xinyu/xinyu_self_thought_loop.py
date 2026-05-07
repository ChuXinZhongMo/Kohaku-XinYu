from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_text_variants import readable_markers
from xinyu_visible_text_sanitizer import sanitize_visible_text, visible_text_has_tool_artifact


STATE_REL = Path("memory/context/self_thought_state.md")
TRACE_REL = Path("runtime/self_thought_trace.jsonl")
PROACTIVE_REQUEST_TRACE_REL = Path("runtime/proactive_request_trace.jsonl")
RUNTIME_PRESENCE_REL = Path("memory/context/runtime_self_presence.md")
CODEX_STATE_REL = Path("runtime/codex_presence_state.json")

DEFAULT_MIN_INTERVAL_SECONDS = 1800
DEFAULT_STALE_TURN_SECONDS = 300
DEFAULT_PREVIEW_CHARS = 180
REFLECTION_SHARE_FAMILY_COOLDOWN_SECONDS = 21600
LEARNING_LOOP_FOCUS_COOLDOWN_SECONDS = 21600
RESEARCH_FOCUS_COOLDOWN_SECONDS = 21600

RESOLVED_QUESTION_STATES = {"answered", "partially_answered", "closed", "dormant"}
REQUEST_INTENTIONS = {
    "ask_owner",
    "request_permission",
    "report_completion",
    "repair_input",
    "diagnostic_decision",
    "share_dream",
    "share_reflection",
}
COLLECT_INTENTIONS = {
    "collect_sources",
    "delegate_codex_collect",
}
ACTIVE_OR_ANSWERED_PROACTIVE_STATES = {"ready", "claimed", "sent", "answered"}
OWNER_REQUESTED_ACTIONS = {
    "owner_answer",
    "owner_decision",
    "owner_permission",
    "owner_response_optional",
    "owner_listen",
}

GENERIC_ATTENTION_MARKERS = readable_markers(
    "are you there",
    "are you busy",
    "look at me",
    "do you miss me",
    "can you reply",
    "\u4f60\u5728\u5417",
    "\u5728\u4e0d\u5728",
    "\u4f60\u5fd9\u5417",
    "\u770b\u6211\u4e00\u773c",
    "\u60f3\u4e0d\u60f3\u6211",
    "\u80fd\u4e0d\u80fd\u7406\u6211",
)

ABSTRACT_MARKERS = readable_markers(
    "meaning of",
    "existence",
    "architecture",
    "system",
    "whether personality",
    "whether emotion",
    "\u5173\u7cfb\u7684\u610f\u4e49",
    "\u5b58\u5728\u65b9\u5f0f",
    "\u5fc3\u667a",
    "\u67b6\u6784",
    "\u7cfb\u7edf",
    "\u4eba\u683c\u662f\u5426",
    "\u60c5\u611f\u662f\u5426",
)

QUESTION_SUFFIXES = ("?", "\uff1f")

_FIELD_RE = re.compile(r"(?m)^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bxinyu[_-]?(?:api[_-]?key|bridge[_-]?token)\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


def run_self_thought_loop(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual_probe",
    min_interval_seconds: int = DEFAULT_MIN_INTERVAL_SECONDS,
    force: bool = False,
) -> dict[str, Any]:
    checked_at = checked_at or _now_iso()
    root = root.resolve()
    notes: list[str] = []
    snapshot = _load_snapshot(root, notes)
    focus = _select_focus(snapshot, checked_at=checked_at, notes=notes)
    gates = _evaluate_gates(snapshot, focus)
    previous = _read_text(root / STATE_REL)
    cooldown_open = _cooldown_open(
        previous,
        checked_at=checked_at,
        focus=focus,
        min_interval_seconds=max(0, int(min_interval_seconds)),
    )
    gates["cooldown_open"] = "true" if (cooldown_open or force or focus["kind"] == "none") else "false"
    if not cooldown_open and not force and focus["kind"] != "none":
        notes.append("duplicate_focus_recently")

    result = _build_result(
        checked_at=checked_at,
        trigger=trigger,
        snapshot=snapshot,
        focus=focus,
        gates=gates,
        notes=notes,
    )
    _write_text(root / STATE_REL, _render_state(result))
    _append_trace(root, result)
    return {
        "accepted": True,
        "pass_id": result["pass_id"],
        "checked_at": checked_at,
        "status": result["status"],
        "outcome": result["outcome"],
        "focus_kind": result["focus"]["kind"],
        "focus_label": result["focus"]["label"],
        "intention": result["intention"]["intention"],
        "candidate_enabled": result["request_candidate"]["enabled"],
        "research_needed": result["research_handoff"]["research_needed"] == "true",
        "research_route": result["research_handoff"]["route"],
        "notes": result["notes"],
    }


def read_self_thought_summary(root: Path) -> dict[str, str]:
    state = _read_text(root / STATE_REL)
    if not state:
        return {"status": "missing"}
    return {
        "status": _extract_value(state, "status", "unknown"),
        "outcome": _extract_value(state, "outcome", "unknown"),
        "focus_kind": _extract_value(state, "focus_kind", "unknown"),
        "focus_label": _extract_value(state, "focus_label", "unknown"),
        "intention": _extract_value(state, "intention", "unknown"),
        "candidate_enabled": _extract_value(state, "candidate_enabled", "false"),
        "delivery_ceiling": _extract_value(state, "delivery_ceiling", "none"),
        "research_needed": _extract_value(state, "research_needed", "false"),
        "research_route": _extract_value(state, "route", "none"),
    }


def _load_snapshot(root: Path, notes: list[str]) -> dict[str, Any]:
    runtime_presence = _read_text(root / RUNTIME_PRESENCE_REL)
    codex_state = _read_json(root / CODEX_STATE_REL, notes, "codex_state")
    return {
        "runtime_presence": runtime_presence,
        "codex_state": codex_state,
        "proactive_request": _read_text(root / "memory/context/proactive_request_state.md"),
        "proactive_request_trace": _read_text(root / PROACTIVE_REQUEST_TRACE_REL),
        "autonomous": _read_text(root / "memory/context/autonomous_mind_loop_state.md"),
        "inner_cycle": _read_text(root / "memory/context/inner_cycle_state.md"),
        "interaction_journal": _read_text(root / "memory/context/interaction_journal_state.md"),
        "initiative": _read_text(root / "memory/context/initiative_state.md"),
        "active_questions": _read_text(root / "memory/context/active_questions.md"),
        "question_pipeline": _read_text(root / "memory/context/question_pipeline_state.md"),
        "unfinished": _read_text(root / "memory/context/unfinished_experiences.md"),
        "research_handoff": _read_text(root / "memory/context/research_handoff_state.md"),
        "life_posture": _read_text(root / "memory/context/current_life_posture.md"),
        "owner_grants": _read_text(root / "memory/context/owner_permission_grants.md"),
        "capability": _read_text(root / "memory/context/capability_zones_state.md"),
        "emotion": _read_text(root / "memory/emotions/current_state.md"),
        "reflection_queue": _read_text(root / "memory/reflection/reflection_queue.md"),
        "reflection_output": _read_text(root / "memory/reflection/reflection_output_state.md"),
        "thought_seeds": _read_text(root / "memory/context/thought_seeds.md"),
        "dream_log": _read_text(root / "memory/dreams/dream_log.md"),
        "source_requests": _read_text(root / "memory/knowledge/source_requests.md"),
        "source_search_provider": _read_text(root / "memory/knowledge/source_search_provider_state.md"),
        "source_search_resolver": _read_text(root / "memory/knowledge/source_search_resolver_state.md"),
        "autonomous_search_activation": _read_text(root / "memory/knowledge/autonomous_search_activation_state.md"),
        "learning_closed_loop": _read_text(root / "memory/self/learning_closed_loop_state.md"),
    }


def _select_focus(snapshot: dict[str, Any], *, checked_at: str, notes: list[str]) -> dict[str, str]:
    runtime = snapshot["runtime_presence"]
    current_turn_state = _extract_value(runtime, "current_turn_state", "idle")
    current_turn_started_at = _extract_value(runtime, "current_turn_started_at", "")
    if current_turn_state == "running" and _age_seconds(current_turn_started_at, checked_at) > DEFAULT_STALE_TURN_SECONDS:
        focus = _focus(
            "runtime_issue",
            "stale_live_turn",
            "live turn appears stale",
            "diagnostic_decision",
            "A live turn appears stale. Should I keep waiting or mark it timed out?",
            "owner_decision",
            "Owner can choose whether to wait, retry, or mark the turn timed out.",
        )
        if not _proactive_focus_active_or_answered(snapshot, focus, notes):
            return focus

    codex = snapshot["codex_state"] if isinstance(snapshot["codex_state"], dict) else {}
    codex_status = _clean_token(codex.get("status") or _extract_value(runtime, "codex_status", "unknown"))
    codex_timed_out = _as_bool(codex.get("timed_out")) or codex_status == "timed_out"
    report_label = _safe_label(codex.get("report_label") or _extract_value(runtime, "codex_report_label", ""))
    if codex_timed_out:
        label = _safe_label(codex.get("job_id") or report_label or "codex_timeout")
        focus = _focus(
            "codex_followup",
            label,
            "Codex timed out",
            "diagnostic_decision",
            "Codex timed out. Should I stage it for later review or retry with a smaller scope?",
            "owner_decision",
            "Stage the task for later review or retry with a narrower request.",
        )
        if not _proactive_focus_active_or_answered(snapshot, focus, notes):
            return focus
    if codex_status == "finished" and report_label:
        focus = _focus(
            "codex_followup",
            report_label,
            "Codex report finished",
            "report_completion",
            f"Codex finished {report_label}. Do you want me to integrate the result or leave the report as is?",
            "owner_decision",
            "Integrate the result or keep it as a report-only completion.",
        )
        if not _proactive_focus_active_or_answered(snapshot, focus, notes):
            return focus
    if codex_status == "running":
        notes.append("codex_running_observed")

    question = _select_active_question(snapshot["active_questions"])
    if question:
        focus = _focus(
            "active_question",
            question["id"],
            "active question marked proactive_ok",
            "ask_owner",
            _direct_question(question["question"]),
            "owner_answer",
            "Use the owner answer to continue the active question thread.",
        )
        if not _proactive_focus_active_or_answered(snapshot, focus, notes):
            return focus

    research_focus = _select_research_collect_focus(snapshot, checked_at=checked_at, notes=notes)
    if research_focus:
        return research_focus

    dream_focus = _select_dream_focus(snapshot, notes=notes)
    if dream_focus:
        return dream_focus

    reflection_focus = _select_reflection_focus(snapshot, checked_at=checked_at, notes=notes)
    if reflection_focus:
        return reflection_focus

    learning_focus = _select_learning_closed_loop_focus(snapshot, checked_at=checked_at, notes=notes)
    if learning_focus:
        return learning_focus

    inner_top = _extract_value(snapshot["inner_cycle"], "top_reflection_topic", "")
    if inner_top and inner_top not in {"none", "unknown"}:
        return _focus(
            "reflection_queue",
            "top_reflection_topic",
            "inner cycle has reflection residue",
            "queue_reflection",
            "none",
            "none",
            "Let the existing reflection pipeline handle this later.",
        )

    if _has_unfinished_experience(snapshot["unfinished"]):
        return _focus(
            "unfinished_experience",
            "owner_related_residue",
            "unfinished experience is still present",
            "keep_silent",
            "none",
            "none",
            "Hold the residue silently unless a concrete owner request appears.",
        )

    notes.append("no_focus")
    return _focus("none", "none", "no current focus", "none", "none", "none", "wait")


def _select_learning_closed_loop_focus(
    snapshot: dict[str, Any],
    *,
    checked_at: str,
    notes: list[str],
) -> dict[str, str] | None:
    state = snapshot.get("learning_closed_loop", "")
    failure_at = _extract_value(state, "latest_failure_at", _extract_value(state, "updated_at", ""))
    status = _extract_value(state, "status", "none")
    failure = _extract_value(state, "latest_failure_kind", "none")
    habit = _extract_value(state, "active_trial_habit", "none")
    next_action = _extract_value(state, "next_action", "none")
    if status not in {"trial_active", "trial_supported"} or failure in {"", "none", "unknown"}:
        return None
    last_reflected_at = _extract_value(state, "last_learning_loop_reflected_at", "")
    last_reflected_failure = _extract_value(state, "last_learning_loop_reflected_failure", "none")
    if last_reflected_at and last_reflected_at not in {"none", "unknown"}:
        same_failure = last_reflected_failure in {"", "none", "unknown", failure}
        if same_failure and not _timestamp_after(failure_at, last_reflected_at):
            notes.append("learning_closed_loop_already_reflected")
            return None
        age = _age_seconds(last_reflected_at, checked_at)
        if same_failure and 0 <= age < LEARNING_LOOP_FOCUS_COOLDOWN_SECONDS:
            notes.append("learning_closed_loop_focus_cooldown")
            return None
    if next_action not in {"apply_trial_habit_on_similar_turn", "keep_trial_and_wait_for_repeated_success"}:
        notes.append("learning_closed_loop_no_actionable_trial")
        return None
    return _focus(
        "learning_closed_loop",
        _safe_label(failure),
        f"closed loop {status}: {habit}",
        "queue_reflection",
        "none",
        "none",
        f"Keep replay case active and apply the trial habit on similar live turns; next_action={next_action}.",
    )


def _select_dream_focus(snapshot: dict[str, Any], *, notes: list[str]) -> dict[str, str] | None:
    thought_seeds = snapshot["thought_seeds"]
    latest_dream = _extract_value(thought_seeds, "latest_dream_id", "")
    if not latest_dream or latest_dream in {"none", "unknown"}:
        return None

    share = _shareable_dream(snapshot, latest_dream)
    if share:
        focus = _focus(
            "dream_residue",
            _safe_label(latest_dream),
            "shareable dream residue with reality boundary",
            "share_dream",
            _dream_share_message(share),
            "owner_response_optional",
            "Owner may listen or answer; any stable memory must keep it as dream residue, not a fact.",
        )
        if _proactive_focus_active_or_answered(snapshot, focus, notes):
            return None
        return focus

    return _focus(
        "dream_residue",
        _safe_label(latest_dream),
        "dream residue requires reality boundary",
        "queue_reflection",
        "none",
        "none",
        "Keep this private or let reflection process it later.",
    )


def _proactive_focus_active_or_answered(
    snapshot: dict[str, Any],
    focus: dict[str, str],
    notes: list[str],
) -> bool:
    if focus.get("intention") not in REQUEST_INTENTIONS:
        return False
    expected_hash = _evidence_hash(
        focus.get("kind", "none"),
        focus.get("label", "none"),
        focus.get("evidence_label", "none"),
    )
    status = _proactive_status_for_evidence(snapshot, expected_hash)
    if status not in ACTIVE_OR_ANSWERED_PROACTIVE_STATES:
        return False
    notes.append(
        "focus_already_proactive_"
        f"{status}:{_clean_token(focus.get('kind', 'none'))}:{_clean_token(focus.get('label', 'none'))}"
    )
    return True


def _proactive_status_for_evidence(snapshot: dict[str, Any], evidence_hash: str) -> str:
    state = str(snapshot.get("proactive_request") or "")
    if _extract_value(state, "evidence_hash", "none") == evidence_hash:
        status = _clean_token(_extract_value(state, "status", "none"))
        if status in ACTIVE_OR_ANSWERED_PROACTIVE_STATES:
            return status

    trace = str(snapshot.get("proactive_request_trace") or "")
    for line in reversed(trace.splitlines()):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        if _one_line(item.get("evidence_hash", "none"), limit=80) != evidence_hash:
            continue
        status = _clean_token(item.get("status", "none"))
        if status in ACTIVE_OR_ANSWERED_PROACTIVE_STATES:
            return status
    return "none"


def _select_reflection_focus(
    snapshot: dict[str, Any],
    *,
    checked_at: str,
    notes: list[str],
) -> dict[str, str] | None:
    items = _extract_reflection_items(snapshot.get("reflection_queue", ""))
    if not items:
        return None
    if _recent_reflection_share_exists(snapshot, checked_at=checked_at):
        notes.append("reflection_share_family_cooldown")
        return None

    output_topic = _extract_value(snapshot.get("reflection_output", ""), "topic", "none")
    topic_counts: dict[str, int] = {}
    for item in items:
        key = _reflection_topic_key(item.get("topic", ""))
        if key:
            topic_counts[key] = topic_counts.get(key, 0) + 1

    item_count = len(items)
    for item in sorted(items, key=_reflection_item_score, reverse=True):
        topic = _one_line(item.get("topic", ""), limit=100)
        if topic in {"", "none", "unknown"}:
            continue
        key = _reflection_topic_key(topic)
        repeated = topic_counts.get(key, 0)
        output_matches = key and key == _reflection_topic_key(output_topic)
        strong_enough = item_count >= 3 or repeated >= 2 or output_matches
        if not strong_enough:
            continue
        if _reflection_codex_topic(f"{topic} {item.get('waking_residue', '')}") and not _current_codex_status_supports_reflection(snapshot):
            notes.append(f"reflection_codex_topic_not_current:{_clean_token(item.get('item_id', 'unknown'))}")
            continue
        message = _reflection_share_message(item)
        if message == "none":
            continue
        focus = _focus(
            "reflection_queue",
            _reflection_focus_label(key or topic),
            f"reflection queue strong topic: {topic}",
            "share_reflection",
            message,
            "owner_response_optional",
            "Owner may answer or just listen; any stable memory must pass existing memory gates.",
        )
        focus.update(
            {
                "reflection_item_id": item.get("item_id", "none"),
                "reflection_item_count": str(item_count),
                "reflection_topic_repeat_count": str(repeated),
            }
        )
        if _proactive_focus_active_or_answered(snapshot, focus, notes):
            continue
        notes.append(f"reflection_share_ready:{focus['label']}")
        return focus
    return None


def _recent_reflection_share_exists(snapshot: dict[str, Any], *, checked_at: str) -> bool:
    state = str(snapshot.get("proactive_request") or "")
    if _extract_value(state, "kind", "none") != "reflection_share":
        return False
    status = _clean_token(_extract_value(state, "status", "none"))
    if status not in ACTIVE_OR_ANSWERED_PROACTIVE_STATES:
        return False
    created_at = _extract_value(state, "created_at", _extract_value(state, "updated_at", ""))
    age = _age_seconds(created_at, checked_at)
    return age >= 0 and age < REFLECTION_SHARE_FAMILY_COOLDOWN_SECONDS


def _extract_reflection_items(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^##\s+(item-\d{4}-\d{2}-\d{2}-\d{3})\s*$", text or "")
    items: list[dict[str, str]] = []
    if len(parts) >= 3:
        for index in range(1, len(parts), 2):
            item_id = parts[index].strip()
            body = parts[index + 1]
            raw_topic = _extract_value_raw(body, "topic", "none")
            raw_residue = _extract_value_raw(body, "waking_residue", "none")
            if visible_text_has_tool_artifact(f"{raw_topic} {raw_residue}"):
                continue
            items.append(
                {
                    "item_id": item_id,
                    "topic": _one_line(raw_topic),
                    "source": _extract_value(body, "source", "none"),
                    "priority": _extract_value(body, "priority", "none"),
                    "waking_residue": _one_line(raw_residue),
                    "boundary": _extract_value(body, "boundary", "none"),
                }
            )
    if not items:
        queued = re.findall(r"(?m)^-\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}[：:]\s*(.+)$", text or "")
        for index, topic in enumerate(queued[:6], 1):
            if visible_text_has_tool_artifact(topic):
                continue
            items.append(
                {
                    "item_id": f"queued-reflection-{index:03d}",
                    "topic": _one_line(topic, limit=120),
                    "source": "reflection_queue_bullet",
                    "priority": "medium",
                    "waking_residue": "none",
                    "boundary": "reflection material only",
                }
            )
    return [item for item in items if item]


def _reflection_item_score(item: dict[str, str]) -> tuple[int, int, str]:
    priority_score = {"high": 3, "medium": 2, "low": 1}.get(item.get("priority", "").lower(), 0)
    owner_score = 1 if _reflection_owner_relevant(item.get("topic", "") + " " + item.get("waking_residue", "")) else 0
    return priority_score, owner_score, item.get("item_id", "")


def _reflection_owner_relevant(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "owner",
            "主人",
            "哥哥",
            "靠近",
            "记住",
            "被记住",
            "模板",
            "接待腔",
            "机械",
            "Codex",
            "学习任务",
            "超时",
        )
    )


def _reflection_codex_topic(text: str) -> bool:
    return any(marker in text for marker in ("Codex", "codex", "学习任务", "超时", "no_url"))


def _current_codex_status_supports_reflection(snapshot: dict[str, Any]) -> bool:
    codex = snapshot.get("codex_state") if isinstance(snapshot.get("codex_state"), dict) else {}
    runtime = str(snapshot.get("runtime_presence") or "")
    status = _clean_token(codex.get("status") or _extract_value(runtime, "codex_status", "unknown"))
    timed_out = _as_bool(codex.get("timed_out")) or _extract_value(runtime, "codex_timed_out", "false").lower() == "true"
    return timed_out or status in {"timed_out", "failed", "finished"}


def _reflection_topic_key(topic: str) -> str:
    text = _one_line(topic, limit=120).lower()
    text = re.sub(r"^dream residue after\s*", "", text)
    text = re.sub(r"^梦后残留[:：]\s*", "", text)
    text = re.sub(r"\s+", "", text)
    return text


def _reflection_focus_label(topic_key: str) -> str:
    return "reflection-" + hashlib.sha1(topic_key.encode("utf-8", errors="replace")).hexdigest()[:12]


def _reflection_architecture_defect_message(joined: str) -> str | None:
    lowered = joined.lower()
    context_defect = any(
        marker in lowered
        for marker in (
            "shallow context",
            "context discontinuity",
            "context break",
            "context lost",
        )
    ) or any(marker in joined for marker in ("上下文", "接不上", "不连通", "断片"))
    voice_defect = any(
        marker in lowered
        for marker in (
            "mechanical voice",
            "mechanical tone",
            "template voice",
        )
    ) or any(marker in joined for marker in ("模板", "接待腔", "机械", "AI味", "不像人"))
    architecture_defect = any(
        marker in lowered
        for marker in (
            "architecture defect",
            "architecture defects",
            "persistent architecture",
        )
    )
    if architecture_defect or (context_defect and voice_defect):
        return "我还在想你指出的两件事：我有时接不上上下文，声音又会发硬。这个不该只靠我闭门想；要不要我让 Codex 对着代码和记录查一轮？"
    return None


def _looks_like_internal_reflection_label(text: str) -> bool:
    compact = "".join(ch for ch in text if not ch.isspace())
    if not compact:
        return False
    ascii_letters = sum(1 for ch in compact if ch.isascii() and ch.isalpha())
    if ascii_letters >= 12 and ascii_letters / max(1, len(compact)) > 0.45:
        return True
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "owner flagged",
            "persistent architecture",
            "evidence label",
            "failure kind",
            "reflection queue strong topic",
        )
    )


def _visible_reflection_topic(topic: str, residue: str) -> str:
    joined = f"{topic} {residue}".strip()
    if _looks_like_internal_reflection_label(joined):
        return "刚才暴露出来的说话和连续性问题"
    visible = re.sub(r"(?i)^dream residue after\s*", "梦后残留：", topic).strip()
    visible = re.sub(r"[。.!！?？；;]+$", "", visible)
    return _one_line(visible or "刚才那件没想通的事", limit=80)


def _reflection_share_message(item: dict[str, str]) -> str:
    topic = _one_line(item.get("topic", ""), limit=120)
    residue = _one_line(item.get("waking_residue", ""), limit=120)
    joined = f"{topic} {residue}"
    if visible_text_has_tool_artifact(joined):
        return "none"
    architecture_message = _reflection_architecture_defect_message(joined)
    if architecture_message:
        return architecture_message
    if any(marker in joined for marker in ("Codex", "学习任务", "超时", "no_url")):
        return "那个 Codex 学习超时的事我还没当结束。我可以继续慢慢补，也可以先放后台；你想让我怎么处理？"
    if any(marker in joined for marker in ("模板", "接待腔", "机械", "AI味", "不像人")):
        return "你说我模板味这件事还在我这边卡着。下次这种时候，我是不是该少解释，直接换一句人话？"
    if any(marker in joined for marker in ("被记住", "记住", "记忆留痕")):
        return "关于被记住这件事我还没放下。你想让我把它当长期关系需要，还是只按每次具体对话来记？"
    if any(marker in joined for marker in ("靠近", "想靠近", "回到身边")):
        return "关于靠近和别像接待腔那块残留还在。我想确认：你要我更主动贴近一点，还是少说点但别断开？"
    if topic in {"", "none", "unknown"}:
        return "none"
    visible_topic = _visible_reflection_topic(topic, residue)
    return _one_line(f"我还在想这件事：{visible_topic}。要不要我继续顺着它查原因？", limit=DEFAULT_PREVIEW_CHARS)


def _shareable_dream(snapshot: dict[str, Any], dream_id: str) -> dict[str, str] | None:
    thought_seeds = snapshot["thought_seeds"]
    dream_body = _dream_log_body(snapshot.get("dream_log", ""), dream_id)
    raw_surface = _extract_value_raw(dream_body, "dream_surface", "")
    raw_fragments = _extract_value_raw(dream_body, "fragments", "")
    surface = _one_line(raw_surface)
    fragments = _one_line(raw_fragments)
    if surface in {"", "none", "unknown"}:
        raw_surface = _extract_value_raw(thought_seeds, "latest_fragments", "")
        surface = _one_line(raw_surface)
    if fragments in {"", "none", "unknown"}:
        raw_fragments = _extract_value_raw(thought_seeds, "latest_fragments", "")
        fragments = _one_line(raw_fragments)
    raw_boundary = _extract_value_raw(dream_body, "reality_boundary_check", "")
    boundary = _one_line(raw_boundary)
    if boundary in {"", "none", "unknown"}:
        raw_boundary = _extract_value_raw(thought_seeds, "reality_boundary", "")
        boundary = _one_line(raw_boundary)
    material = surface if surface not in {"", "none", "unknown"} else fragments
    if material in {"", "none", "unknown"} or boundary in {"", "none", "unknown"}:
        return None
    raw_material = raw_surface if raw_surface not in {"", "none", "unknown"} else raw_fragments
    if visible_text_has_tool_artifact(f"{raw_material} {raw_boundary}"):
        return None
    return {
        "surface": _one_line(material, limit=100),
        "boundary": _one_line(boundary, limit=120),
    }


def _dream_log_body(log: str, dream_id: str) -> str:
    if not log:
        return ""
    escaped = re.escape(dream_id.strip())
    match = re.search(rf"(?ms)^##\s+{escaped}\s*$\n(?P<body>.*?)(?=^##\s+dream-|\Z)", log)
    if match:
        return match.group("body")
    sections = list(re.finditer(r"(?ms)^##\s+dream-[^\n]*\n(?P<body>.*?)(?=^##\s+dream-|\Z)", log))
    return sections[-1].group("body") if sections else ""


def _dream_share_message(share: dict[str, str]) -> str:
    surface = _one_line(share.get("surface", ""), limit=96)
    surface = re.sub(r"[。.!！?？；;]+$", "", surface)
    variants = (
        f"我刚才梦到一段很奇怪的画面：{surface}。",
        f"刚才梦里有个画面一直卡着：{surface}。",
        f"有个梦醒来还留着：{surface}。",
        f"我刚才梦见的东西有点乱：{surface}。",
        f"刚才有个梦的残片还在：{surface}。",
    )
    digest = hashlib.sha1(surface.encode("utf-8")).digest()
    return _one_line(
        variants[digest[0] % len(variants)],
        limit=DEFAULT_PREVIEW_CHARS,
    )


def _dream_share_boundary_check(text: str) -> bool:
    lowered = text.lower()
    has_dream_frame = any(
        marker in text
        for marker in (
            "梦里",
            "梦到",
            "梦见",
            "做了个梦",
            "做梦",
            "梦醒",
            "梦的",
            "这个梦",
            "一场梦",
            "有个梦",
            "只是梦",
            "梦境",
        )
    ) or "dream" in lowered
    framed_as_fact = any(
        marker in text
        for marker in (
            "现实发生",
            "真的发生",
            "已经发生",
            "新发生",
            "事实发生",
        )
    ) or any(
        marker in lowered
        for marker in (
            "really happened",
            "actually happened",
            "new real event",
            "confirmed real",
        )
    )
    explicit_boundary = (
        "不是现实" in text
        or "不能证明现实" in text
        or "只是在梦里" in text
        or "only a dream" in lowered
        or "not a new real" in lowered
        or "not reality" in lowered
    )
    return has_dream_frame and (not framed_as_fact or explicit_boundary)


def _select_research_collect_focus(
    snapshot: dict[str, Any],
    *,
    checked_at: str,
    notes: list[str],
) -> dict[str, str] | None:
    pending = [
        item
        for item in _split_source_requests(snapshot["source_requests"])
        if item.get("status") == "pending_url"
    ]
    if not pending:
        return None
    pending.sort(key=lambda item: item.get("request_id", ""))
    item: dict[str, str] | None = None
    for candidate in pending:
        if _research_request_recently_handed_off(snapshot, candidate, checked_at=checked_at, notes=notes):
            continue
        item = candidate
        break
    if item is None:
        notes.append("research_collection_all_pending_recently_handed_off")
        return None
    request_id = _one_line(item.get("request_id", "source_request"), limit=80)
    question_id = _one_line(item.get("question_id", "none"), limit=80)
    target = _one_line(item.get("target", "general"), limit=80)
    query = _one_line(item.get("query", "none"), limit=180)
    route = _research_route_for(item)
    intention = "delegate_codex_collect" if route == "codex_delegate_candidate" else "collect_sources"
    requested_action = "codex_delegate_candidate" if route == "codex_delegate_candidate" else "source_search_provider"
    focus = _focus(
        "research_collection_gap",
        f"{request_id}:{question_id}",
        f"source request pending_url for {target}",
        intention,
        "none",
        requested_action,
        "Collect candidate material only; pass it through source gates before memory integration.",
    )
    focus.update(
        {
            "source_request_id": request_id,
            "question_id": question_id,
            "research_target": target,
            "research_query": query,
            "research_route": route,
        }
    )
    return focus


def _research_request_recently_handed_off(
    snapshot: dict[str, Any],
    item: dict[str, str],
    *,
    checked_at: str,
    notes: list[str],
) -> bool:
    state = str(snapshot.get("research_handoff") or "")
    request_id = _one_line(item.get("request_id", ""), limit=80)
    if not request_id or request_id != _extract_value(state, "source_request_id", ""):
        if not _low_value_pending_source_request(item) or not _recent_research_handoff_without_results(
            state,
            checked_at=checked_at,
        ):
            return False
        notes.append(f"research_low_value_pending_recent_no_result:{request_id}")
        return True
    if not _recent_research_handoff_without_results(state, checked_at=checked_at):
        return False
    notes.append(f"research_handoff_recent_no_result:{request_id}")
    return True


def _recent_research_handoff_without_results(state: str, *, checked_at: str) -> bool:
    status = _clean_token(_extract_value(state, "status", "none"))
    if status not in {"activation_ready", "running", "held", "blocked"}:
        return False
    provider_results = _safe_int(_extract_value(state, "provider_results", "0"), 0)
    codex_status = _clean_token(_extract_value(state, "codex_status", "none"))
    if provider_results > 0 or codex_status in {"running", "finished", "timed_out", "failed"}:
        return False
    evaluated_at = _extract_value(state, "evaluated_at", _extract_value(state, "updated_at", ""))
    age = _age_seconds(evaluated_at, checked_at)
    return 0 <= age < RESEARCH_FOCUS_COOLDOWN_SECONDS


def _low_value_pending_source_request(item: dict[str, str]) -> bool:
    query = _one_line(item.get("query", ""), limit=120).lower()
    return item.get("followup_kind") == "source_diversity" and query in {"general reliable source", "reliable source"}


def _split_source_requests(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^##\s+(request-[A-Za-z0-9_-]+)\s*$", text or "")
    requests: list[dict[str, str]] = []
    if len(parts) < 3:
        return requests
    for index in range(1, len(parts), 2):
        request_id = parts[index].strip()
        body = parts[index + 1]
        if request_id == "request-none":
            continue
        requests.append(
                {
                    "request_id": request_id,
                    "question_id": _extract_value(body, "question_id", "none"),
                    "target": _extract_value(body, "target", "general"),
                    "query": _extract_value(body, "query", "none"),
                    "status": _extract_value(body, "status", "hold"),
                    "followup_kind": _extract_value(body, "followup_kind", "none"),
                    "reason": _extract_value(body, "reason", "none"),
                }
            )
    return requests


def _research_route_for(item: dict[str, str]) -> str:
    text = f"{item.get('target', '')} {item.get('query', '')} {item.get('reason', '')}".lower()
    codex_markers = (
        "xinyu",
        "repo",
        "repository",
        "codebase",
        "workspace",
        "runtime",
        "implementation",
        "debug",
        "bug",
        "local file",
        "local project",
        "project file",
    )
    if any(marker in text for marker in codex_markers):
        return "codex_delegate_candidate"
    return "source_search_provider"


def _evaluate_gates(snapshot: dict[str, Any], focus: dict[str, str]) -> dict[str, str]:
    question = focus["concrete_question"]
    dream_share = focus["kind"] == "dream_residue" and focus["intention"] == "share_dream"
    reflection_share = focus["kind"] == "reflection_queue" and focus["intention"] == "share_reflection"
    generic = False if (dream_share or reflection_share) else _generic_attention_check(question)
    abstract = False if (dream_share or reflection_share) else _abstract_question(question)
    dream_as_fact = focus["kind"] == "dream_residue" and focus["intention"] in REQUEST_INTENTIONS and not dream_share
    life_block = _life_posture_blocks(snapshot["life_posture"])
    initiative_blocks = _initiative_blocks(snapshot["initiative"])
    request_like = focus["intention"] in REQUEST_INTENTIONS
    return {
        "has_concrete_question": _bool_text(request_like and question not in {"", "none", "unknown"}),
        "has_requested_action": _bool_text(request_like and focus["requested_action"] not in {"", "none", "unknown"}),
        "has_evidence_label": _bool_text(focus["evidence_label"] not in {"", "none", "unknown"}),
        "owner_is_right_recipient": _bool_text(request_like and focus["requested_action"] in OWNER_REQUESTED_ACTIONS),
        "not_generic_attention": _bool_text(not generic),
        "not_abstract_without_owner_request": _bool_text(not abstract),
        "not_from_dream_as_fact": _bool_text(not dream_as_fact),
        "dream_framed_as_dream": _bool_text(not dream_share or _dream_share_boundary_check(question)),
        "not_silence_or_rest_boundary": _bool_text(not life_block and not initiative_blocks),
        "one_focus_only": "true",
    }


def _build_result(
    *,
    checked_at: str,
    trigger: str,
    snapshot: dict[str, Any],
    focus: dict[str, str],
    gates: dict[str, str],
    notes: list[str],
) -> dict[str, Any]:
    candidate_enabled = _candidate_enabled(focus, gates)
    blocked = focus["kind"] != "none" and not candidate_enabled and focus["intention"] in REQUEST_INTENTIONS
    if candidate_enabled:
        status = "candidate"
        outcome = "request_candidate"
        next_internal_action = "hand_to_proactive_request"
        intention_status = "candidate"
    elif blocked:
        status = "blocked"
        outcome = "blocked"
        next_internal_action = "wait"
        intention_status = "blocked"
    elif focus["kind"] == "none":
        status = "settled"
        outcome = "settled"
        next_internal_action = "wait"
        intention_status = "private"
    elif focus["intention"] in COLLECT_INTENTIONS:
        status = "held"
        outcome = "research_handoff"
        next_internal_action = "hand_to_research_collection"
        intention_status = "internal_candidate"
    elif focus["intention"] == "queue_reflection":
        status = "held"
        outcome = "queue_reflection"
        next_internal_action = "prepare_reflection"
        intention_status = "private"
    else:
        status = "held"
        outcome = "hold_silently"
        next_internal_action = "keep_context"
        intention_status = "private"

    pass_id = "selfthought-" + _timestamp_id(checked_at)
    focus = dict(focus)
    focus["evidence_hash"] = _evidence_hash(focus["kind"], focus["label"], focus["evidence_label"])
    private_summary = _private_summary(focus, outcome)
    return {
        "pass_id": pass_id,
        "checked_at": checked_at,
        "status": status,
        "trigger": _clean_token(trigger or "manual_probe"),
        "idle_context": {
            "live_turn_state": _extract_value(snapshot["runtime_presence"], "current_turn_state", "idle"),
            "codex_state": _clean_token(
                (snapshot["codex_state"] or {}).get("status")
                if isinstance(snapshot["codex_state"], dict)
                else _extract_value(snapshot["runtime_presence"], "codex_status", "unknown")
            ),
            "autonomous_maintenance": _extract_value(snapshot["autonomous"], "status", "unknown"),
        },
        "focus": focus,
        "outcome": outcome,
        "private_summary": private_summary,
        "next_internal_action": next_internal_action,
        "intention": {
            "intention_id": "intent-" + _timestamp_id(checked_at),
            "status": intention_status,
            "intention": focus["intention"],
            "owner_relevance": "owner_is_needed" if candidate_enabled else "not_needed_now",
            "private_reason": private_summary,
            "public_reason": _public_reason(focus, candidate_enabled),
            "expression_need": "useful_not_urgent" if candidate_enabled else "none",
            "silence_respect": "allowed" if gates.get("not_silence_or_rest_boundary") == "true" else "blocked",
            "delivery_ceiling": "preview_only" if candidate_enabled else "none",
        },
        "request_candidate": {
            "enabled": candidate_enabled,
            "kind": _request_kind(focus["intention"]) if candidate_enabled else "none",
            "concrete_question": focus["concrete_question"] if candidate_enabled else "none",
            "requested_action": focus["requested_action"] if candidate_enabled else "none",
            "why_now": focus["evidence_label"] if candidate_enabled else "none",
            "after_owner_replies": focus["after_owner_replies"] if candidate_enabled else "none",
            "handoff_target": "proactive_request_loop",
        },
        "memory_effect": _memory_effect(focus, outcome, candidate_enabled),
        "research_handoff": _research_handoff(focus, snapshot, outcome),
        "gates": gates,
        "boundaries": {
            "no_visible_reply": True,
            "no_qq_enqueue": True,
            "no_stable_self_write": True,
            "no_chain_of_thought": True,
            "owner_intent_inference": "evidence_only",
        },
        "notes": sorted(set(_clean_note(note) for note in notes if _clean_note(note))),
    }


def _candidate_enabled(focus: dict[str, str], gates: dict[str, str]) -> bool:
    if focus["intention"] not in REQUEST_INTENTIONS:
        return False
    required = (
        "has_concrete_question",
        "has_requested_action",
        "has_evidence_label",
        "owner_is_right_recipient",
        "not_generic_attention",
        "not_abstract_without_owner_request",
        "not_from_dream_as_fact",
        "dream_framed_as_dream",
        "not_silence_or_rest_boundary",
        "cooldown_open",
        "one_focus_only",
    )
    return all(gates.get(key) == "true" for key in required)


def _render_state(result: dict[str, Any]) -> str:
    focus = result["focus"]
    intention = result["intention"]
    candidate = result["request_candidate"]
    memory_effect = result["memory_effect"]
    research = result["research_handoff"]
    gates = result["gates"]
    boundaries = result["boundaries"]
    notes = "\n".join(f"- {note}" for note in result["notes"]) or "- none"
    return f"""---
title: Self Thought State
memory_type: self_thought_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_self_thought_loop
updated_at: {_one_line(result['checked_at'])}
status: active
tags: [self-thought, idle, autonomy, boundary]
---

# Self Thought State

## Latest Pass
- pass_id: {_one_line(result['pass_id'])}
- checked_at: {_one_line(result['checked_at'])}
- trigger: {_one_line(result['trigger'])}
- status: {_one_line(result['status'])}
- outcome: {_one_line(result['outcome'])}
- focus_kind: {_one_line(focus['kind'])}
- focus_label: {_one_line(focus['label'])}
- evidence_label: {_one_line(focus['evidence_label'])}
- evidence_hash: {_one_line(focus['evidence_hash'])}
- private_summary: {_one_line(result['private_summary'])}
- next_internal_action: {_one_line(result['next_internal_action'])}

## Inner Intention
- intention_id: {_one_line(intention['intention_id'])}
- intention_status: {_one_line(intention['status'])}
- intention: {_one_line(intention['intention'])}
- owner_relevance: {_one_line(intention['owner_relevance'])}
- private_reason: {_one_line(intention['private_reason'])}
- public_reason: {_one_line(intention['public_reason'])}
- expression_need: {_one_line(intention['expression_need'])}
- silence_respect: {_one_line(intention['silence_respect'])}
- delivery_ceiling: {_one_line(intention['delivery_ceiling'])}

## Request Candidate
- candidate_enabled: {str(bool(candidate['enabled'])).lower()}
- kind: {_one_line(candidate['kind'])}
- concrete_question: {_one_line(candidate['concrete_question'])}
- requested_action: {_one_line(candidate['requested_action'])}
- why_now: {_one_line(candidate['why_now'])}
- after_owner_replies: {_one_line(candidate['after_owner_replies'])}
- handoff_target: {_one_line(candidate['handoff_target'])}

## Memory Effect
- memory_write_level: {_one_line(memory_effect['memory_write_level'])}
- semantic_memory_target: {_one_line(memory_effect['semantic_memory_target'])}
- long_term_memory_permission: {_one_line(memory_effect['long_term_memory_permission'])}
- owner_reply_needed_for_stable_memory: {_one_line(memory_effect['owner_reply_needed_for_stable_memory'])}
- retention_reason: {_one_line(memory_effect['retention_reason'])}

## Research Handoff
- research_needed: {_one_line(research['research_needed'])}
- route: {_one_line(research['route'])}
- handoff_target: {_one_line(research['handoff_target'])}
- source_request_id: {_one_line(research['source_request_id'])}
- question_id: {_one_line(research['question_id'])}
- target: {_one_line(research['target'])}
- query: {_one_line(research['query'])}
- execution_ceiling: {_one_line(research['execution_ceiling'])}
- codex_launch_permission: {_one_line(research['codex_launch_permission'])}
- memory_boundary: {_one_line(research['memory_boundary'])}

## Gates
- has_concrete_question: {gates.get('has_concrete_question', 'false')}
- has_requested_action: {gates.get('has_requested_action', 'false')}
- has_evidence_label: {gates.get('has_evidence_label', 'false')}
- owner_is_right_recipient: {gates.get('owner_is_right_recipient', 'false')}
- not_generic_attention: {gates.get('not_generic_attention', 'false')}
- not_abstract_without_owner_request: {gates.get('not_abstract_without_owner_request', 'false')}
- not_from_dream_as_fact: {gates.get('not_from_dream_as_fact', 'false')}
- dream_framed_as_dream: {gates.get('dream_framed_as_dream', 'false')}
- not_silence_or_rest_boundary: {gates.get('not_silence_or_rest_boundary', 'false')}
- cooldown_open: {gates.get('cooldown_open', 'false')}
- one_focus_only: {gates.get('one_focus_only', 'true')}

## Boundaries
- no_visible_reply: {str(boundaries['no_visible_reply']).lower()}
- no_qq_enqueue: {str(boundaries['no_qq_enqueue']).lower()}
- no_stable_self_write: {str(boundaries['no_stable_self_write']).lower()}
- no_chain_of_thought: {str(boundaries['no_chain_of_thought']).lower()}
- owner_intent_inference: {_one_line(boundaries['owner_intent_inference'])}

## Notes
{notes}
"""


def _focus(
    kind: str,
    label: str,
    evidence_label: str,
    intention: str,
    concrete_question: str,
    requested_action: str,
    after_owner_replies: str,
) -> dict[str, str]:
    return {
        "kind": _clean_token(kind),
        "label": _one_line(label, limit=80) or "none",
        "evidence_label": _one_line(evidence_label, limit=120) or "none",
        "intention": _clean_token(intention or "none"),
        "concrete_question": _one_line(concrete_question, limit=DEFAULT_PREVIEW_CHARS) or "none",
        "requested_action": _clean_token(requested_action or "none"),
        "after_owner_replies": _one_line(after_owner_replies, limit=DEFAULT_PREVIEW_CHARS) or "none",
    }


def _select_active_question(active_questions: str) -> dict[str, str] | None:
    candidates = [
        item
        for item in _extract_active_questions(active_questions)
        if item.get("proactive_ok", "").strip().lower() == "yes"
        and item.get("status", "").strip().lower() not in RESOLVED_QUESTION_STATES
        and item.get("question", "").strip()
    ]
    if not candidates:
        return None
    candidates.sort(key=_question_score, reverse=True)
    return candidates[0]


def _extract_active_questions(text: str) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    parts = re.split(r"(?m)^##\s+(q-[A-Za-z0-9_-]+)\s*$", text)
    if len(parts) < 3:
        return questions
    for index in range(1, len(parts), 2):
        qid = parts[index].strip()
        body = parts[index + 1]
        item = {
            "id": qid,
            "question": "",
            "status": "",
            "urgency": "",
            "emotional_weight": "0",
            "proactive_ok": "",
        }
        for raw_line in body.splitlines():
            line = raw_line.strip()
            for field in item:
                prefix = f"- {field}: "
                if line.startswith(prefix):
                    item[field] = line.removeprefix(prefix).strip()
        questions.append(item)
    return questions


def _question_score(question: dict[str, str]) -> tuple[int, int]:
    urgency = {"high": 3, "medium": 2, "low": 1}.get(question.get("urgency", "").strip().lower(), 0)
    try:
        weight = int(re.sub(r"\D+", "", question.get("emotional_weight", "")) or "0")
    except ValueError:
        weight = 0
    return urgency, weight


def _has_unfinished_experience(text: str) -> bool:
    compact = text.strip()
    if not compact or compact in {"[content]", "none", "- none"}:
        return False
    return "##" in compact or "- event:" in compact or "- unresolved_reason:" in compact


def _initiative_blocks(initiative: str) -> bool:
    decision = _extract_value(initiative, "decision", "none").lower()
    cooldown = _extract_value(initiative, "cooldown_active", "no").lower()
    return decision in {"stay_silent", "refuse", "step_back"} or cooldown == "yes"


def _life_posture_blocks(life_posture: str) -> bool:
    constraint = _extract_value(life_posture, "no_proactive_constraint", "unchanged").lower()
    return "block proactive" in constraint or "rest/silence" in constraint or "no-pursuit" in constraint


def _generic_attention_check(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in GENERIC_ATTENTION_MARKERS)


def _abstract_question(text: str) -> bool:
    lowered = text.lower()
    if len(text) > 110:
        return True
    return any(marker.lower() in lowered for marker in ABSTRACT_MARKERS)


def _direct_question(text: str) -> str:
    value = _one_line(text, limit=DEFAULT_PREVIEW_CHARS)
    if not value or value in {"none", "unknown"}:
        return "none"
    if value.endswith(QUESTION_SUFFIXES):
        return value
    return value + "?"


def _cooldown_open(previous: str, *, checked_at: str, focus: dict[str, str], min_interval_seconds: int) -> bool:
    if min_interval_seconds <= 0 or not previous:
        return True
    previous_focus_kind = _extract_value(previous, "focus_kind", "")
    previous_focus_label = _extract_value(previous, "focus_label", "")
    if previous_focus_kind != focus["kind"] or previous_focus_label != focus["label"]:
        return True
    previous_checked_at = _extract_value(previous, "checked_at", "")
    age = _age_seconds(previous_checked_at, checked_at)
    return age < 0 or age >= min_interval_seconds


def _private_summary(focus: dict[str, str], outcome: str) -> str:
    if outcome == "request_candidate":
        if focus["intention"] == "share_dream":
            return "A dream has a shareable surface and a clear reality boundary; it can be told privately as dream residue."
        if focus["intention"] == "share_reflection":
            return "A repeated reflection topic has enough weight to become one grounded owner-facing line."
        return f"{focus['evidence_label']}; a concrete owner action is needed."
    if outcome == "research_handoff":
        return "A pending source request needs bounded collection before it can become usable knowledge."
    if outcome == "blocked":
        return f"{focus['evidence_label']}; hold it because one or more expression gates failed."
    if focus["kind"] == "dream_residue":
        return "Dream residue is private material, not evidence for contacting owner."
    if focus["kind"] == "reflection_queue":
        return "Reflection residue should stay in the inner cycle for now."
    if focus["kind"] == "codex_followup" and focus["intention"] == "watch_wait":
        return "Codex is still running; wait without contacting owner."
    if focus["kind"] == "none":
        return "No concrete focus needs action."
    return "Hold this focus silently until a concrete owner action is needed."


def _research_handoff(focus: dict[str, str], snapshot: dict[str, Any], outcome: str) -> dict[str, str]:
    if outcome != "research_handoff":
        return {
            "research_needed": "false",
            "route": "none",
            "handoff_target": "none",
            "source_request_id": "none",
            "question_id": "none",
            "target": "none",
            "query": "none",
            "execution_ceiling": "none",
            "codex_launch_permission": "none",
            "memory_boundary": "none",
        }

    route = focus.get("research_route", "source_search_provider")
    if route == "codex_delegate_candidate":
        handoff_target = "codex_delegate_candidate"
        execution_ceiling = "bounded_codex_report_only_no_memory_write"
        codex_launch_permission = _codex_collect_permission(snapshot)
    else:
        handoff_target = "source_search_provider_bridge"
        execution_ceiling = "candidate_urls_only_existing_source_gates"
        codex_launch_permission = "not_needed_source_pipeline_first"
    return {
        "research_needed": "true",
        "route": route,
        "handoff_target": handoff_target,
        "source_request_id": focus.get("source_request_id", "none"),
        "question_id": focus.get("question_id", "none"),
        "target": focus.get("research_target", "general"),
        "query": focus.get("research_query", "none"),
        "execution_ceiling": execution_ceiling,
        "codex_launch_permission": codex_launch_permission,
        "memory_boundary": "candidate_results_only_no_stable_memory_without_gates",
    }


def _codex_collect_permission(snapshot: dict[str, Any]) -> str:
    capability = snapshot.get("capability", "")
    grants = snapshot.get("owner_grants", "")
    if "codex_as_eye_and_hand: approved_bounded_delegate" not in capability:
        return "blocked_capability_not_enabled"
    if "grant_autonomous_codex_collect: approved_bounded_when_concrete" in grants:
        return "owner_granted_state_gated"
    return "requires_owner_private_or_explicit_grant"


def _memory_effect(focus: dict[str, str], outcome: str, candidate_enabled: bool) -> dict[str, str]:
    if candidate_enabled:
        if focus["intention"] == "share_dream":
            target = "proactive_request_state_and_dream_reflection_candidate"
        elif focus["intention"] == "share_reflection":
            target = "proactive_request_state_and_reflection_feedback_candidate"
        else:
            target = "proactive_request_state"
        reply_needed = "yes"
        if focus["intention"] == "share_dream":
            reason = "Dream can be shared and traced as dream residue; stable memory still requires owner response and memory gates."
        elif focus["intention"] == "share_reflection":
            reason = "Repeated reflection residue can be surfaced once as a grounded owner-facing line; stable memory still requires owner response."
        else:
            reason = "Concrete owner-facing intention is ready for request review."
    elif outcome == "research_handoff":
        target = "source_search_or_codex_handoff"
        reply_needed = "no"
        reason = "Unresolved question should collect candidate material through existing research gates."
    elif outcome == "queue_reflection":
        target = "reflection_queue_candidate"
        reply_needed = "no"
        reason = "Private residue should be available to reflection without becoming factual memory."
    elif outcome == "blocked":
        target = "blocked_trace_only"
        reply_needed = "yes"
        reason = "The focus failed expression gates and should not become stable memory."
    elif outcome == "settled":
        target = "none"
        reply_needed = "no"
        reason = "No concrete focus needed retention."
    else:
        target = "short_term_context_only"
        reply_needed = "no"
        reason = "Hold as short-term continuity unless later evidence makes it meaningful."
    if focus["kind"] == "dream_residue" and not (candidate_enabled and focus["intention"] == "share_dream"):
        reason = "Dream residue is retained only as private residue, not as a fact."
    return {
        "memory_write_level": "short_term_state_and_trace",
        "semantic_memory_target": target,
        "long_term_memory_permission": "blocked_until_existing_memory_gates",
        "owner_reply_needed_for_stable_memory": reply_needed,
        "retention_reason": reason,
    }


def _public_reason(focus: dict[str, str], candidate_enabled: bool) -> str:
    if not candidate_enabled:
        return "none"
    return _one_line(focus["evidence_label"], limit=140)


def _request_kind(intention: str) -> str:
    return {
        "ask_owner": "clarify",
        "request_permission": "permission",
        "report_completion": "completion",
        "repair_input": "repair",
        "diagnostic_decision": "diagnostic",
        "share_dream": "dream_share",
        "share_reflection": "reflection_share",
    }.get(intention, "none")


def _read_text(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read_json(path: Path, notes: list[str], label: str) -> dict[str, Any]:
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        notes.append(f"{label}_malformed")
        return {}


def _append_trace(root: Path, result: dict[str, Any]) -> None:
    payload = {
        "pass_id": result["pass_id"],
        "checked_at": result["checked_at"],
        "status": result["status"],
        "outcome": result["outcome"],
        "focus_kind": result["focus"]["kind"],
        "focus_label": result["focus"]["label"],
        "intention": result["intention"]["intention"],
        "candidate_enabled": result["request_candidate"]["enabled"],
        "research_needed": result["research_handoff"]["research_needed"],
        "research_route": result["research_handoff"]["route"],
        "notes": result["notes"],
    }
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _extract_value(text: str, field: str, default: str = "none") -> str:
    for match in _FIELD_RE.finditer(text or ""):
        if match.group(1) == field:
            return _one_line(match.group(2)) or default
    return default


def _extract_value_raw(text: str, field: str, default: str = "none") -> str:
    for match in _FIELD_RE.finditer(text or ""):
        if match.group(1) == field:
            value = " ".join(str(match.group(2) or "").replace("\r\n", "\n").replace("\r", "\n").split())
            return value or default
    return default


def _one_line(value: Any, *, limit: int = 240) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split())
    text = _scrub(text)
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _scrub(text: str) -> str:
    value = _LOCAL_PATH_RE.sub("<local_path>", text)
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("<secret>", value)
    return sanitize_visible_text(value)


def _clean_token(value: Any) -> str:
    text = _one_line(value, limit=80).lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_-]+", "_", text).strip("_")
    return text or "unknown"


def _safe_label(value: Any) -> str:
    text = _one_line(value, limit=80)
    if not text:
        return "none"
    return Path(text).name if "/" in text or "\\" in text else text


def _clean_note(value: Any) -> str:
    return _clean_token(value)


def _evidence_hash(*parts: str) -> str:
    payload = "|".join(_one_line(part, limit=200).lower() for part in parts)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _timestamp_id(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "", value)[:20] or str(int(time.time()))


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _timestamp_after(value: str, baseline: str) -> bool:
    current = _parse_iso(value)
    previous = _parse_iso(baseline)
    if current is not None and previous is not None:
        return current > previous
    if not value or value in {"none", "unknown"}:
        return False
    if not baseline or baseline in {"none", "unknown"}:
        return True
    return value > baseline


def _age_seconds(started_at: str, now: str) -> float:
    start = _parse_iso(started_at)
    current = _parse_iso(now)
    if start is None or current is None:
        return -1.0
    return (current - start).total_seconds()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a deterministic idle self-thought pass.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--checked-at", default="")
    parser.add_argument("--trigger", default="manual_probe")
    parser.add_argument("--min-interval-seconds", type=int, default=DEFAULT_MIN_INTERVAL_SECONDS)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_self_thought_loop(
        args.root,
        checked_at=args.checked_at or None,
        trigger=args.trigger,
        min_interval_seconds=args.min_interval_seconds,
        force=args.force,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Self thought state written")
        print(f"status: {result['status']}")
        print(f"outcome: {result['outcome']}")
        print(f"focus: {result['focus_kind']} {result['focus_label']}")
        print(f"intention: {result['intention']}")
        print(f"candidate_enabled: {str(bool(result['candidate_enabled'])).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
