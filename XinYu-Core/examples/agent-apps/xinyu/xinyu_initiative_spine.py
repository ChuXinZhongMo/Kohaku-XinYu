from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_MD_REL = Path("memory/context/initiative_spine_state.md")
TRACE_REL = Path("runtime/initiative_spine_trace.jsonl")


@dataclass(frozen=True, slots=True)
class InitiativeSpineSnapshot:
    checked_at: str
    trigger: str
    spine_id: str
    status: str
    emergence_level: str
    internal_pressure: str
    self_thought_lane: str
    emotion_lane: str
    impulse_lane: str
    proactive_lane: str
    action_permission: str
    feedback_lane: str
    next_step: str
    continuity_contract: str
    prompt_block: str


def run_initiative_spine(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
    write_state: bool = True,
    max_chars: int = 1800,
) -> dict[str, Any]:
    snapshot = build_initiative_spine_snapshot(
        root,
        checked_at=checked_at,
        trigger=trigger,
        max_chars=max_chars,
    )
    if write_state:
        write_initiative_spine_state(root, snapshot)
        append_initiative_spine_trace(root, snapshot)
    return {
        "accepted": True,
        "status": snapshot.status,
        "checked_at": snapshot.checked_at,
        "spine_id": snapshot.spine_id,
        "emergence_level": snapshot.emergence_level,
        "internal_pressure": snapshot.internal_pressure,
        "action_permission": snapshot.action_permission,
        "next_step": snapshot.next_step,
        "notes": [
            "initiative_spine_synthesized",
            f"emergence:{snapshot.emergence_level}",
            f"action:{snapshot.action_permission}",
        ],
    }


def build_initiative_spine_prompt_block(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "prompt",
    write_state: bool = False,
    max_chars: int = 1800,
) -> str:
    snapshot = build_initiative_spine_snapshot(
        root,
        checked_at=checked_at,
        trigger=trigger,
        max_chars=max_chars,
    )
    if write_state:
        write_initiative_spine_state(root, snapshot)
        append_initiative_spine_trace(root, snapshot)
    return snapshot.prompt_block


def build_initiative_spine_snapshot(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
    max_chars: int = 1800,
) -> InitiativeSpineSnapshot:
    root = root.resolve()
    checked_at = checked_at or datetime.now().astimezone().isoformat()
    state = _read_source_state(root)
    self_fields = _fields(state["self_thought"])
    emotion_fields = _fields(state["emotion_council"])
    impulse_fields = _fields(state["impulse_soup"])
    request_fields = _fields(state["proactive_request"])
    decision_fields = _fields(state["proactive_decision"])
    learning_fields = _fields(state["learning_closed_loop"])

    self_lane = _self_thought_lane(self_fields)
    emotion_lane = _emotion_lane(emotion_fields)
    impulse_lane = _impulse_lane(impulse_fields)
    proactive_lane = _proactive_lane(request_fields, decision_fields)
    feedback_lane = _feedback_lane(learning_fields, request_fields)
    action_permission = _action_permission(request_fields, decision_fields, impulse_fields)
    internal_pressure = _internal_pressure(self_fields, emotion_fields, impulse_fields, decision_fields, learning_fields)
    emergence_level = _emergence_level(
        internal_pressure=internal_pressure,
        action_permission=action_permission,
        proactive_lane=proactive_lane,
        feedback_lane=feedback_lane,
    )
    status = "active" if emergence_level != "quiet" else "quiet"
    next_step = _next_step(
        emergence_level=emergence_level,
        action_permission=action_permission,
        request_fields=request_fields,
        decision_fields=decision_fields,
        learning_fields=learning_fields,
    )
    spine_id = _spine_id(checked_at, self_fields, impulse_fields, decision_fields, request_fields)
    continuity_contract = _continuity_contract(emergence_level=emergence_level)
    lines = [
        "## Initiative Spine Runtime Context",
        "scope: hidden synthesis of self-thought, emotion, impulse, proactive choice, action permission, and feedback.",
        "not_a_template: true",
        f"spine_id: {spine_id}",
        f"trigger: {trigger}",
        f"status: {status}",
        f"emergence_level: {emergence_level}",
        f"internal_pressure: {internal_pressure}",
        f"self_thought_lane: {self_lane}",
        f"emotion_lane: {emotion_lane}",
        f"impulse_lane: {impulse_lane}",
        f"proactive_lane: {proactive_lane}",
        f"action_permission: {action_permission}",
        f"feedback_lane: {feedback_lane}",
        f"next_step: {next_step}",
        f"continuity_contract: {continuity_contract}",
        "",
        "### Rules",
        "- Treat initiative as one living thread: pressure -> choice -> action permission -> feedback.",
        "- Never bypass the proactive request, scorer, owner-private, cooldown, or safety gates.",
        "- If outward action is blocked, keep the pressure as private bias or state, not as a fake visible claim.",
        "- When a visible reply happens, it should answer the current turn while quietly carrying the relevant initiative bias.",
        "- After owner feedback, update the feedback lane before promoting any stable self/personality change.",
    ]
    prompt = "\n".join(lines)[:max_chars].rstrip()
    return InitiativeSpineSnapshot(
        checked_at=checked_at,
        trigger=trigger,
        spine_id=spine_id,
        status=status,
        emergence_level=emergence_level,
        internal_pressure=internal_pressure,
        self_thought_lane=self_lane,
        emotion_lane=emotion_lane,
        impulse_lane=impulse_lane,
        proactive_lane=proactive_lane,
        action_permission=action_permission,
        feedback_lane=feedback_lane,
        next_step=next_step,
        continuity_contract=continuity_contract,
        prompt_block=prompt,
    )


def write_initiative_spine_state(root: Path, snapshot: InitiativeSpineSnapshot) -> None:
    lines = [
        "---",
        "title: Initiative Spine State",
        "memory_type: initiative_spine_state",
        "time_scope: short_term",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: xinyu_initiative_spine",
        f"updated_at: {snapshot.checked_at}",
        f"status: {snapshot.status}",
        "tags: [initiative, autonomy, self-thought, emotion, action, feedback]",
        "---",
        "",
        "# Initiative Spine State",
        "",
        "## Summary",
        f"- checked_at: {snapshot.checked_at}",
        f"- trigger: {snapshot.trigger}",
        f"- spine_id: {snapshot.spine_id}",
        f"- status: {snapshot.status}",
        f"- emergence_level: {snapshot.emergence_level}",
        f"- internal_pressure: {snapshot.internal_pressure}",
        f"- self_thought_lane: {snapshot.self_thought_lane}",
        f"- emotion_lane: {snapshot.emotion_lane}",
        f"- impulse_lane: {snapshot.impulse_lane}",
        f"- proactive_lane: {snapshot.proactive_lane}",
        f"- action_permission: {snapshot.action_permission}",
        f"- feedback_lane: {snapshot.feedback_lane}",
        f"- next_step: {snapshot.next_step}",
        f"- continuity_contract: {snapshot.continuity_contract}",
        "",
        "## Boundary",
        "- this file synthesizes initiative state; it is not a visible reply template",
        "- it never authorizes QQ send, tool execution, or stable self rewrite by itself",
        "- initiative must remain tied to current owner context and feedback before promotion",
    ]
    _write_text_atomic(root / STATE_MD_REL, "\n".join(lines))


def append_initiative_spine_trace(root: Path, snapshot: InitiativeSpineSnapshot) -> None:
    event = asdict(snapshot)
    event.pop("prompt_block", None)
    event["event_kind"] = "initiative_spine_synthesized"
    event["observed_at"] = snapshot.checked_at
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _read_source_state(root: Path) -> dict[str, str]:
    return {
        "self_thought": _read(root, "memory/context/self_thought_state.md", limit=5000),
        "emotion_council": _read(root, "memory/context/emotion_council_state.md", limit=5000),
        "impulse_soup": _read(root, "memory/context/impulse_soup_state.md", limit=5000),
        "proactive_request": _read(root, "memory/context/proactive_request_state.md", limit=5000),
        "proactive_decision": _read(root, "memory/context/proactive_decision_state.md", limit=5000),
        "learning_closed_loop": _read(root, "memory/self/learning_closed_loop_state.md", limit=5000),
    }


def _self_thought_lane(fields: dict[str, str]) -> str:
    status = fields.get("status") or "missing"
    outcome = fields.get("outcome") or "none"
    focus = fields.get("focus_kind") or "none"
    intention = fields.get("intention") or "none"
    candidate = fields.get("candidate_enabled") or "false"
    return _clip(f"{status}/{outcome}/{focus}/{intention}/candidate={candidate}", 220)


def _emotion_lane(fields: dict[str, str]) -> str:
    status = fields.get("status") or "missing"
    lens = fields.get("strongest_lens") or "none"
    bias = fields.get("output_bias") or fields.get("consensus") or "none"
    return _clip(f"{status}/lens={lens}/bias={bias}", 220)


def _impulse_lane(fields: dict[str, str]) -> str:
    status = fields.get("status") or "missing"
    desire = fields.get("top_desire_shape") or "none"
    energy = fields.get("top_energy") or "0"
    action = fields.get("top_action") or "none"
    outward = fields.get("outward_action_allowed") or "false"
    return _clip(f"{status}/{desire}/energy={energy}/action={action}/outward={outward}", 240)


def _proactive_lane(request: dict[str, str], decision: dict[str, str]) -> str:
    request_status = request.get("status") or "missing"
    request_kind = request.get("kind") or "none"
    answer_state = request.get("request_answer_state") or "none"
    recommendation = decision.get("recommendation") or "none"
    score = decision.get("total_score") or "0"
    source = decision.get("source_type") or "none"
    return _clip(
        f"request={request_status}/{request_kind}/{answer_state}; decision={recommendation}/{source}/score={score}",
        260,
    )


def _feedback_lane(learning: dict[str, str], request: dict[str, str]) -> str:
    status = learning.get("status") or "missing"
    failure = learning.get("latest_failure_kind") or "none"
    next_action = learning.get("next_action") or "none"
    success = learning.get("success_streak") or "0"
    request_feedback = request.get("owner_reply_feedback") or "none"
    return _clip(f"{status}/failure={failure}/next={next_action}/success_streak={success}/request_feedback={request_feedback}", 260)


def _action_permission(request: dict[str, str], decision: dict[str, str], impulse: dict[str, str]) -> str:
    request_status = (request.get("status") or "").lower()
    answer_state = (request.get("request_answer_state") or "").lower()
    recommendation = (decision.get("recommendation") or "").lower()
    shadow_only = (decision.get("shadow_only") or "true").lower() == "true"
    preferred = (decision.get("preferred_channel") or "silent").lower()
    outward = (impulse.get("outward_action_allowed") or "false").lower() == "true"
    if answer_state in {"owner_replied", "answered", "feedback_received"}:
        return "owner_thread_answered_feedback_only"
    if request_status in {"ready", "candidate_only", "claimed", "sent"}:
        return "proactive_request_gate_active"
    if request_status == "answered":
        return "owner_thread_answered_feedback_only"
    if recommendation == "send_now" and shadow_only:
        return "shadow_send_now_requires_non_shadow_gate"
    if recommendation in {"send_now", "inbox"} and preferred in {"qq", "inbox"}:
        return f"candidate_{recommendation}_{preferred}_needs_request_gate"
    if not outward:
        return "inner_only_impulse_boundary"
    return "no_outward_action_without_current_gate"


def _internal_pressure(
    self_fields: dict[str, str],
    emotion_fields: dict[str, str],
    impulse_fields: dict[str, str],
    decision_fields: dict[str, str],
    learning_fields: dict[str, str],
) -> str:
    parts: list[str] = []
    focus = self_fields.get("focus_kind") or "none"
    outcome = self_fields.get("outcome") or "none"
    if focus != "none" or outcome != "none":
        parts.append(f"self={focus}/{outcome}")
    strongest_lens = emotion_fields.get("strongest_lens") or "none"
    if strongest_lens != "none":
        parts.append(f"emotion={strongest_lens}")
    desire = impulse_fields.get("top_desire_shape") or "none"
    energy = _safe_int(impulse_fields.get("top_energy"), 0)
    if desire != "none" or energy > 0:
        parts.append(f"impulse={desire}:{energy}")
    recommendation = decision_fields.get("recommendation") or "none"
    total = _safe_int(decision_fields.get("total_score"), 0)
    if recommendation != "none" or total > 0:
        parts.append(f"decision={recommendation}:{total}")
    repair_count = _safe_int(learning_fields.get("repair_count"), 0)
    success_count = _safe_int(learning_fields.get("success_count"), 0)
    if repair_count or success_count:
        parts.append(f"learning=repair{repair_count}/success{success_count}")
    return _clip("; ".join(parts) if parts else "none", 320)


def _emergence_level(*, internal_pressure: str, action_permission: str, proactive_lane: str, feedback_lane: str) -> str:
    if internal_pressure == "none":
        return "quiet"
    if action_permission == "proactive_request_gate_active":
        return "outward_candidate_gated"
    if action_permission == "owner_thread_answered_feedback_only":
        return "feedback_absorption"
    if "send_now" in proactive_lane and "shadow" in action_permission:
        return "shadow_initiative_pressure"
    if "trial_active" in feedback_lane or "repair" in feedback_lane:
        return "inner_learning_pressure"
    return "inner_pressure_only"


def _next_step(
    *,
    emergence_level: str,
    action_permission: str,
    request_fields: dict[str, str],
    decision_fields: dict[str, str],
    learning_fields: dict[str, str],
) -> str:
    if action_permission == "proactive_request_gate_active":
        question = request_fields.get("concrete_question") or "prepared proactive request"
        return _clip(f"hold one grounded proactive thread; visible question={question}", 260)
    if action_permission == "owner_thread_answered_feedback_only":
        return "absorb owner reply into learning/memory gates before new initiative"
    if emergence_level == "shadow_initiative_pressure":
        source = decision_fields.get("source_type") or "unknown"
        return f"convert shadow pressure from {source} into request gate or keep silent"
    next_action = learning_fields.get("next_action") or ""
    if next_action and next_action != "none":
        return _clip(f"apply learning next_action={next_action} only when current turn matches", 220)
    return "keep initiative private until a current turn or proactive gate makes it grounded"


def _continuity_contract(*, emergence_level: str) -> str:
    if emergence_level in {"outward_candidate_gated", "shadow_initiative_pressure"}:
        return "initiative-first: preserve why XinYu wants to speak, then gate whether speaking is deserved"
    if emergence_level == "feedback_absorption":
        return "feedback-first: owner reaction changes the next initiative before any stable self rewrite"
    if emergence_level == "inner_learning_pressure":
        return "learning-first: pressure becomes a behavior habit, not a report"
    return "quiet-first: keep pressure internal unless the current context earns action"


def _spine_id(checked_at: str, *field_sets: dict[str, str]) -> str:
    material = "|".join(
        [
            checked_at[:19],
            *(fields.get(key, "") for fields in field_sets for key in ("pass_id", "decision_id", "request_id", "top_thoughtlet_id")),
        ]
    )
    digest = hashlib.sha256(material.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"initiative-{checked_at.replace('-', '').replace(':', '').replace('+', 'T')[:15]}-{digest}"


def _fields(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for key, value in re.findall(r"(?m)^\s*-?\s*([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$", text or ""):
        clean_key = key.strip()
        clean_value = _one_line(value)
        if clean_key and clean_value:
            data[clean_key] = clean_value
    return data


def _read(root: Path, rel_path: str, *, limit: int) -> str:
    try:
        text = (root / rel_path).read_text(encoding="utf-8-sig", errors="replace").strip()
    except OSError:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit]


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]}.tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _clip(value: Any, limit: int = 180) -> str:
    text = _one_line(value)
    if len(text) <= limit:
        return text or "none"
    return text[: max(0, limit - 3)].rstrip() + "..."


def _one_line(value: Any) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Synthesize XinYu initiative spine state.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--trigger", default="manual_cli")
    args = parser.parse_args()
    result = run_initiative_spine(args.root, trigger=args.trigger)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
