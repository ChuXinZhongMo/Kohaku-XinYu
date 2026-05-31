from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_action_feedback_coverage import build_action_feedback_coverage_report
from xinyu_action_feedback_surface import read_action_feedback_state
from xinyu_bridge_values import as_bool, safe_str
from xinyu_owner_feedback_effects import build_owner_feedback_effect_report, write_owner_feedback_effect
from xinyu_perception_importance import build_perception_importance_report, perception_gap_bias, perception_gap_signal
from xinyu_relation_posture import RelationPosture, read_relation_posture_state
from xinyu_state_io import read_text, write_text_atomic
from xinyu_text_variants import readable_markers

STATE_REL = Path("memory/context/intention_ecology_state.md")
TRACE_REL = Path("runtime/intention_ecology_trace.jsonl")
NONE_VALUES = {"", "missing", "none", "unknown", "null"}

REPAIR_MARKERS = readable_markers("模板", "接待腔", "机械", "不像人", "不像真人", "没变", "敷衍", "你又")
REST_MARKERS = readable_markers("累", "困", "休息", "睡觉", "别问", "别追问", "不想聊", "安静")
COMPANION_MARKERS = readable_markers("陪我", "难受", "孤独", "抱抱", "想你", "在吗")
ADVICE_MARKERS = readable_markers("怎么办", "建议", "怎么做", "该不该", "帮我分析", "如何")
SELF_DISCLOSURE_MARKERS = readable_markers("你想", "你怎么想", "你最近", "你感觉", "你的想法", "自主", "涌现")
TASK_MARKERS = readable_markers("实现", "做出来", "修改", "测试", "跑一下", "检查", "代码", "模块", "系统")
NEGATIVE_FEEDBACK_MARKERS = readable_markers("不好", "不对", "错了", "别这样", "不像真人", "不像人", "又", "还是", "模板", "机械", "敷衍")
POSITIVE_FEEDBACK_MARKERS = readable_markers("这样可以", "好多了", "对", "嗯", "可以", "舒服", "自然")


@dataclass(frozen=True)
class IntentionCandidate:
    intent_id: str
    intent_type: str
    action_level: str
    value_score: int
    risk_score: int
    gate: str
    reason: str
    visible_bias: str
    future_candidate: str = "none"

    @property
    def total_score(self) -> int:
        return self.value_score - self.risk_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "intent_type": self.intent_type,
            "action_level": self.action_level,
            "value_score": self.value_score,
            "risk_score": self.risk_score,
            "total_score": self.total_score,
            "gate": self.gate,
            "reason": self.reason,
            "visible_bias": self.visible_bias,
            "future_candidate": self.future_candidate,
        }


@dataclass(frozen=True)
class IntentionEcology:
    checked_at: str
    ecology_id: str
    selected_intent: str
    selected_gate: str
    action_level: str
    autonomy_posture: str
    feedback_signal: str
    action_feedback_signal: str
    action_feedback_bias: str
    action_feedback_coverage_signal: str
    action_feedback_coverage_lifecycle: str
    action_feedback_coverage_bias: str
    owner_feedback_effect_signal: str
    owner_feedback_effect_bias: str
    owner_feedback_expression_bias: str
    owner_response_feedback_signal: str
    owner_response_feedback_bias: str
    owner_response_strategy_bias: str
    perception_gap_signal: str
    perception_gap_bias: str
    perception_route_hint: str
    feedback_consumption_status: str
    feedback_consumed_sources: str
    feedback_consumed_biases: str
    feedback_consumed_future_effect: str
    candidate_competition_status: str
    selected_total_score: int
    runner_up_intent: str
    runner_up_gate: str
    runner_up_total_score: int
    score_margin: int
    blocked_candidate_count: int
    held_candidate_count: int
    review_gated_future_count: int
    competition_reason: str
    runner_up_not_selected_reason: str
    gate_pressure_summary: str
    blocked_intents: str
    held_intents: str
    review_gated_intents: str
    proactive_candidate: str
    memory_candidate: str
    restraint_reason: str
    candidates: tuple[IntentionCandidate, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked_at": self.checked_at,
            "ecology_id": self.ecology_id,
            "selected_intent": self.selected_intent,
            "selected_gate": self.selected_gate,
            "action_level": self.action_level,
            "autonomy_posture": self.autonomy_posture,
            "feedback_signal": self.feedback_signal,
            "action_feedback_signal": self.action_feedback_signal,
            "action_feedback_bias": self.action_feedback_bias,
            "action_feedback_coverage_signal": self.action_feedback_coverage_signal,
            "action_feedback_coverage_lifecycle": self.action_feedback_coverage_lifecycle,
            "action_feedback_coverage_bias": self.action_feedback_coverage_bias,
            "owner_feedback_effect_signal": self.owner_feedback_effect_signal,
            "owner_feedback_effect_bias": self.owner_feedback_effect_bias,
            "owner_feedback_expression_bias": self.owner_feedback_expression_bias,
            "owner_response_feedback_signal": self.owner_response_feedback_signal,
            "owner_response_feedback_bias": self.owner_response_feedback_bias,
            "owner_response_strategy_bias": self.owner_response_strategy_bias,
            "perception_gap_signal": self.perception_gap_signal,
            "perception_gap_bias": self.perception_gap_bias,
            "perception_route_hint": self.perception_route_hint,
            "feedback_consumption_status": self.feedback_consumption_status,
            "feedback_consumed_sources": self.feedback_consumed_sources,
            "feedback_consumed_biases": self.feedback_consumed_biases,
            "feedback_consumed_future_effect": self.feedback_consumed_future_effect,
            "candidate_competition_status": self.candidate_competition_status,
            "selected_total_score": self.selected_total_score,
            "runner_up_intent": self.runner_up_intent,
            "runner_up_gate": self.runner_up_gate,
            "runner_up_total_score": self.runner_up_total_score,
            "score_margin": self.score_margin,
            "blocked_candidate_count": self.blocked_candidate_count,
            "held_candidate_count": self.held_candidate_count,
            "review_gated_future_count": self.review_gated_future_count,
            "competition_reason": self.competition_reason,
            "runner_up_not_selected_reason": self.runner_up_not_selected_reason,
            "gate_pressure_summary": self.gate_pressure_summary,
            "blocked_intents": self.blocked_intents,
            "held_intents": self.held_intents,
            "review_gated_intents": self.review_gated_intents,
            "proactive_candidate": self.proactive_candidate,
            "memory_candidate": self.memory_candidate,
            "restraint_reason": self.restraint_reason,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "notes": list(self.notes),
        }

    def to_prompt_block(self) -> str:
        top = self.candidates[0] if self.candidates else None
        candidate_line = "none"
        if top is not None:
            candidate_line = (
                f"{top.intent_type}/level={top.action_level}/gate={top.gate}/"
                f"value={top.value_score}/risk={top.risk_score}"
            )
        notes = "; ".join(self.notes) if self.notes else "none"
        human_style_rule = _human_style_rule_for(self.selected_intent)
        return "\n".join(
            [
                "intention ecology sidecar:",
                "visibility_rule: hidden; do not mention ecology, candidates, gates, scores, traces, or files.",
                "purpose: choose a bounded living intention for this turn, including restraint when that is safer.",
                f"selected_intent: {self.selected_intent}",
                f"selected_gate: {self.selected_gate}",
                f"action_level: {self.action_level}",
                f"autonomy_posture: {self.autonomy_posture}",
                f"feedback_signal: {self.feedback_signal}",
                f"action_feedback_signal: {self.action_feedback_signal}",
                f"action_feedback_bias: {self.action_feedback_bias}",
                f"action_feedback_coverage_signal: {self.action_feedback_coverage_signal}",
                f"action_feedback_coverage_lifecycle: {self.action_feedback_coverage_lifecycle}",
                f"action_feedback_coverage_bias: {self.action_feedback_coverage_bias}",
                f"owner_feedback_effect_signal: {self.owner_feedback_effect_signal}",
                f"owner_feedback_effect_bias: {self.owner_feedback_effect_bias}",
                f"owner_feedback_expression_bias: {self.owner_feedback_expression_bias}",
                f"owner_response_feedback_signal: {self.owner_response_feedback_signal}",
                f"owner_response_feedback_bias: {self.owner_response_feedback_bias}",
                f"owner_response_strategy_bias: {self.owner_response_strategy_bias}",
                f"perception_gap_signal: {self.perception_gap_signal}",
                f"perception_gap_bias: {self.perception_gap_bias}",
                f"perception_route_hint: {self.perception_route_hint}",
                f"feedback_consumption_status: {self.feedback_consumption_status}",
                f"feedback_consumed_sources: {self.feedback_consumed_sources}",
                f"feedback_consumed_biases: {self.feedback_consumed_biases}",
                f"feedback_consumed_future_effect: {self.feedback_consumed_future_effect}",
                f"candidate_competition_status: {self.candidate_competition_status}",
                f"competition_summary: selected={self.selected_intent}/score={self.selected_total_score}; runner_up={self.runner_up_intent}/score={self.runner_up_total_score}; margin={self.score_margin}; blocked={self.blocked_candidate_count}; held={self.held_candidate_count}; review_gated={self.review_gated_future_count}",
                f"runner_up_not_selected_reason: {self.runner_up_not_selected_reason}",
                f"gate_pressure_summary: {self.gate_pressure_summary}",
                f"proactive_candidate: {self.proactive_candidate}",
                f"memory_candidate: {self.memory_candidate}",
                f"restraint_reason: {self.restraint_reason}",
                f"top_candidate: {candidate_line}",
                f"notes: {notes}",
                "reply_rule: carry only the selected visible bias into the next natural chat line.",
                f"human_style_rule: {human_style_rule}",
                "anti_service_rule: do not summarize the user's words, do not say '知道了' as a standalone opener, do not report what you are doing; answer as a close person in one fresh line.",
                "action_rule: future/proactive/memory candidates are review-gated state only; do not claim they were sent or permanently remembered.",
                "restraint_rule: if gate is hold_or_silence, answer shorter and do not add a question unless the user explicitly asks for one.",
            ]
        )


def evaluate_intention_ecology(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None = None,
    relation_posture: RelationPosture | dict[str, Any] | None = None,
    visible_turn: Any | None = None,
    perception_importance: dict[str, Any] | None = None,
    checked_at: str | None = None,
    write_state: bool = False,
) -> IntentionEcology:
    root = Path(root)
    checked_at = checked_at or _now_iso()
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    is_owner = as_bool(metadata.get("is_owner_user"), default=False)
    text = safe_str(user_text)
    compact = "".join(text.split())
    posture = _coerce_relation_posture(root, relation_posture)
    posture_scene = safe_str(_posture_value(posture, "scene"), "unknown")
    posture_initiative = safe_str(_posture_value(posture, "initiative_allowed"), "unchanged")
    posture_risk = safe_str(_posture_value(posture, "risk_level"), "low")
    visible_kind = safe_str(getattr(visible_turn, "turn_kind", ""))
    feedback_signal = _feedback_signal(compact, dialogue_tail or [])
    action_feedback = read_action_feedback_state(root)
    action_feedback_signal = safe_str(action_feedback.get("feedback_signal"), "none")
    action_feedback_bias = _action_feedback_bias(action_feedback)
    action_feedback_coverage = build_action_feedback_coverage_report(root, generated_at=checked_at)
    action_feedback_coverage_signal = _action_feedback_coverage_signal(action_feedback_coverage)
    action_feedback_coverage_lifecycle = _action_feedback_coverage_lifecycle(action_feedback_coverage)
    action_feedback_coverage_bias = _action_feedback_coverage_bias(action_feedback_coverage)
    owner_feedback_effect = build_owner_feedback_effect_report(root, generated_at=checked_at)
    owner_feedback_current_turn_direct_failure = _owner_feedback_current_turn_direct_failure(
        compact=compact,
        posture_scene=posture_scene,
    )
    owner_feedback_effect_cooldown = (
        _owner_feedback_effect_direct_failure_only(owner_feedback_effect)
        and not owner_feedback_current_turn_direct_failure
    )
    owner_feedback_effect_for_turn = (
        _cool_owner_feedback_effect_for_turn(owner_feedback_effect)
        if owner_feedback_effect_cooldown
        else owner_feedback_effect
    )
    owner_feedback_effect_signal = _owner_feedback_effect_signal(owner_feedback_effect_for_turn)
    owner_feedback_effect_bias = _owner_feedback_effect_bias(owner_feedback_effect_for_turn)
    owner_feedback_expression_bias = _owner_feedback_expression_bias(owner_feedback_effect_for_turn)
    owner_response_feedback_signal = _owner_response_feedback_signal(owner_feedback_effect)
    owner_response_feedback_bias = _owner_response_feedback_bias(owner_feedback_effect)
    owner_response_strategy_bias = _owner_response_strategy_bias(owner_feedback_effect)
    perception_importance_report = (
        perception_importance
        if isinstance(perception_importance, dict)
        else build_perception_importance_report(root, generated_at=checked_at)
    )
    perception_signal = perception_gap_signal(perception_importance_report)
    perception_gap_signal_value = safe_str(perception_signal.get("gap_type"), "none")
    perception_gap_bias_value = perception_gap_bias(perception_importance_report)
    perception_route_hint = safe_str(perception_signal.get("route_hint"), "none")
    feedback_consumption = _feedback_consumption_audit(
        action_feedback=action_feedback,
        action_feedback_signal=action_feedback_signal,
        action_feedback_bias=action_feedback_bias,
        action_feedback_coverage=action_feedback_coverage,
        action_feedback_coverage_signal=action_feedback_coverage_signal,
        action_feedback_coverage_lifecycle=action_feedback_coverage_lifecycle,
        action_feedback_coverage_bias=action_feedback_coverage_bias,
        owner_feedback_effect=owner_feedback_effect_for_turn,
        owner_feedback_effect_signal=owner_feedback_effect_signal,
        owner_feedback_effect_bias=owner_feedback_effect_bias,
        owner_feedback_expression_bias=owner_feedback_expression_bias,
        owner_response_feedback_signal=owner_response_feedback_signal,
        owner_response_feedback_bias=owner_response_feedback_bias,
        owner_response_strategy_bias=owner_response_strategy_bias,
        perception_gap_signal=perception_gap_signal_value,
        perception_gap_bias=perception_gap_bias_value,
        perception_route_hint=perception_route_hint,
    )

    notes: list[str] = []
    if is_owner:
        notes.append("owner_turn")
    else:
        notes.append("non_owner_turn")
    if posture_scene != "unknown":
        notes.append(f"relation_scene:{posture_scene}")
    if visible_kind:
        notes.append(f"visible_turn:{visible_kind}")
    if feedback_signal != "none":
        notes.append(f"feedback:{feedback_signal}")
    if action_feedback_signal not in {"", "missing", "none"}:
        notes.append(f"action_feedback:{action_feedback_signal}")
    if action_feedback_bias != "none":
        notes.append(f"action_feedback_bias:{action_feedback_bias}")
    if action_feedback_coverage_signal not in {"", "missing", "none"}:
        notes.append(f"action_feedback_coverage:{action_feedback_coverage_signal}")
    if action_feedback_coverage_lifecycle not in {"", "missing", "none"}:
        notes.append(f"action_feedback_coverage_lifecycle:{action_feedback_coverage_lifecycle}")
    if action_feedback_coverage_bias != "none":
        notes.append(f"action_feedback_coverage_bias:{action_feedback_coverage_bias}")
    if owner_feedback_effect_signal not in {"", "missing", "none"}:
        notes.append(f"owner_feedback_effect:{owner_feedback_effect_signal}")
    if owner_feedback_effect_bias != "none":
        notes.append(f"owner_feedback_effect_bias:{owner_feedback_effect_bias}")
    if owner_feedback_expression_bias != "none":
        notes.append(f"owner_feedback_expression:{owner_feedback_expression_bias}")
    if owner_feedback_effect_cooldown:
        notes.append("owner_feedback_effect_cooldown:direct_failure_only")
    if owner_response_feedback_signal not in {"", "missing", "none"}:
        notes.append(f"owner_response_feedback:{owner_response_feedback_signal}")
    if owner_response_feedback_bias != "none":
        notes.append(f"owner_response_feedback_bias:{owner_response_feedback_bias}")
    if owner_response_strategy_bias != "none":
        notes.append(f"owner_response_strategy:{owner_response_strategy_bias}")
    if perception_gap_signal_value not in {"", "missing", "none"}:
        notes.append(f"perception_gap:{perception_gap_signal_value}")
    if perception_gap_bias_value != "none":
        notes.append(f"perception_gap_bias:{perception_gap_bias_value}")
    if feedback_consumption["feedback_consumption_status"] != "no_feedback":
        notes.append(f"feedback_consumption:{feedback_consumption['feedback_consumption_status']}")

    candidates = _generate_candidates(
        compact=compact,
        is_owner=is_owner,
        posture_scene=posture_scene,
        posture_initiative=posture_initiative,
        posture_risk=posture_risk,
        feedback_signal=feedback_signal,
        action_feedback=action_feedback,
        action_feedback_coverage=action_feedback_coverage,
        owner_feedback_effect=owner_feedback_effect_for_turn,
        perception_importance=perception_importance_report,
    )
    candidates = tuple(sorted(candidates, key=lambda item: (item.total_score, item.value_score), reverse=True))
    selected = candidates[0] if candidates else _candidate("hold_presence", "state_only", 10, 10, "hold_private", "no_candidate", "stay quiet")
    competition = _candidate_competition_summary(candidates)

    proactive_candidate = "none"
    memory_candidate = "none"
    restraint_reason = "none"
    if selected.gate in {"blocked", "hold_or_silence", "hold_private"}:
        restraint_reason = selected.reason
    for candidate in candidates:
        if candidate.future_candidate == "proactive" and proactive_candidate == "none" and candidate.gate != "blocked":
            proactive_candidate = f"review_gated:{candidate.intent_type}"
        if candidate.future_candidate == "memory" and memory_candidate == "none" and candidate.gate != "blocked":
            memory_candidate = f"review_gated:{candidate.intent_type}"

    ecology = IntentionEcology(
        checked_at=checked_at,
        ecology_id=_ecology_id(checked_at, text, candidates),
        selected_intent=selected.intent_type,
        selected_gate=selected.gate,
        action_level=selected.action_level,
        autonomy_posture=_autonomy_posture(selected, posture_scene=posture_scene),
        feedback_signal=feedback_signal,
        action_feedback_signal=action_feedback_signal,
        action_feedback_bias=action_feedback_bias,
        action_feedback_coverage_signal=action_feedback_coverage_signal,
        action_feedback_coverage_lifecycle=action_feedback_coverage_lifecycle,
        action_feedback_coverage_bias=action_feedback_coverage_bias,
        owner_feedback_effect_signal=owner_feedback_effect_signal,
        owner_feedback_effect_bias=owner_feedback_effect_bias,
        owner_feedback_expression_bias=owner_feedback_expression_bias,
        owner_response_feedback_signal=owner_response_feedback_signal,
        owner_response_feedback_bias=owner_response_feedback_bias,
        owner_response_strategy_bias=owner_response_strategy_bias,
        perception_gap_signal=perception_gap_signal_value,
        perception_gap_bias=perception_gap_bias_value,
        perception_route_hint=perception_route_hint,
        feedback_consumption_status=feedback_consumption["feedback_consumption_status"],
        feedback_consumed_sources=feedback_consumption["feedback_consumed_sources"],
        feedback_consumed_biases=feedback_consumption["feedback_consumed_biases"],
        feedback_consumed_future_effect=feedback_consumption["feedback_consumed_future_effect"],
        candidate_competition_status=safe_str(competition.get("status"), "missing"),
        selected_total_score=int(competition.get("selected_total_score") or selected.total_score),
        runner_up_intent=safe_str(competition.get("runner_up_intent"), "none"),
        runner_up_gate=safe_str(competition.get("runner_up_gate"), "none"),
        runner_up_total_score=int(competition.get("runner_up_total_score") or 0),
        score_margin=int(competition.get("score_margin") or 0),
        blocked_candidate_count=int(competition.get("blocked_candidate_count") or 0),
        held_candidate_count=int(competition.get("held_candidate_count") or 0),
        review_gated_future_count=int(competition.get("review_gated_future_count") or 0),
        competition_reason=safe_str(competition.get("competition_reason"), "none"),
        runner_up_not_selected_reason=safe_str(competition.get("runner_up_not_selected_reason"), "none"),
        gate_pressure_summary=safe_str(competition.get("gate_pressure_summary"), "none"),
        blocked_intents=safe_str(competition.get("blocked_intents"), "none"),
        held_intents=safe_str(competition.get("held_intents"), "none"),
        review_gated_intents=safe_str(competition.get("review_gated_intents"), "none"),
        proactive_candidate=proactive_candidate,
        memory_candidate=memory_candidate,
        restraint_reason=restraint_reason,
        candidates=candidates[:6],
        notes=tuple(notes),
    )
    if write_state:
        write_owner_feedback_effect(root, owner_feedback_effect, write_report=False)
        _write_state(root, ecology)
        _append_trace(root, ecology)
    return ecology


def build_intention_ecology_prompt_block(root: Path, ecology: IntentionEcology | dict[str, Any] | None) -> str:
    del root
    if ecology is None:
        return ""
    if isinstance(ecology, IntentionEcology):
        return ecology.to_prompt_block()
    candidates = tuple(
        IntentionCandidate(
            intent_id=safe_str(item.get("intent_id"), "intent-unknown"),
            intent_type=safe_str(item.get("intent_type"), "hold_presence"),
            action_level=safe_str(item.get("action_level"), "state_only"),
            value_score=int(item.get("value_score") or 0),
            risk_score=int(item.get("risk_score") or 0),
            gate=safe_str(item.get("gate"), "hold_private"),
            reason=safe_str(item.get("reason"), "unknown"),
            visible_bias=safe_str(item.get("visible_bias"), "stay quiet"),
            future_candidate=safe_str(item.get("future_candidate"), "none"),
        )
        for item in ecology.get("candidates", [])
        if isinstance(item, dict)
    )
    return IntentionEcology(
        checked_at=safe_str(ecology.get("checked_at"), _now_iso()),
        ecology_id=safe_str(ecology.get("ecology_id"), "intention-unknown"),
        selected_intent=safe_str(ecology.get("selected_intent"), "hold_presence"),
        selected_gate=safe_str(ecology.get("selected_gate"), "hold_private"),
        action_level=safe_str(ecology.get("action_level"), "state_only"),
        autonomy_posture=safe_str(ecology.get("autonomy_posture"), "bounded_restraint"),
        feedback_signal=safe_str(ecology.get("feedback_signal"), "none"),
        action_feedback_signal=safe_str(ecology.get("action_feedback_signal"), "none"),
        action_feedback_bias=safe_str(ecology.get("action_feedback_bias"), "none"),
        action_feedback_coverage_signal=safe_str(ecology.get("action_feedback_coverage_signal"), "none"),
        action_feedback_coverage_lifecycle=safe_str(ecology.get("action_feedback_coverage_lifecycle"), "none"),
        action_feedback_coverage_bias=safe_str(ecology.get("action_feedback_coverage_bias"), "none"),
        owner_feedback_effect_signal=safe_str(ecology.get("owner_feedback_effect_signal"), "none"),
        owner_feedback_effect_bias=safe_str(ecology.get("owner_feedback_effect_bias"), "none"),
        owner_feedback_expression_bias=safe_str(ecology.get("owner_feedback_expression_bias"), "none"),
        owner_response_feedback_signal=safe_str(ecology.get("owner_response_feedback_signal"), "none"),
        owner_response_feedback_bias=safe_str(ecology.get("owner_response_feedback_bias"), "none"),
        owner_response_strategy_bias=safe_str(ecology.get("owner_response_strategy_bias"), "none"),
        perception_gap_signal=safe_str(ecology.get("perception_gap_signal"), "none"),
        perception_gap_bias=safe_str(ecology.get("perception_gap_bias"), "none"),
        perception_route_hint=safe_str(ecology.get("perception_route_hint"), "none"),
        feedback_consumption_status=safe_str(ecology.get("feedback_consumption_status"), "no_feedback"),
        feedback_consumed_sources=safe_str(ecology.get("feedback_consumed_sources"), "none"),
        feedback_consumed_biases=safe_str(ecology.get("feedback_consumed_biases"), "none"),
        feedback_consumed_future_effect=safe_str(ecology.get("feedback_consumed_future_effect"), "none"),
        candidate_competition_status=safe_str(ecology.get("candidate_competition_status"), "missing"),
        selected_total_score=int(ecology.get("selected_total_score") or 0),
        runner_up_intent=safe_str(ecology.get("runner_up_intent"), "none"),
        runner_up_gate=safe_str(ecology.get("runner_up_gate"), "none"),
        runner_up_total_score=int(ecology.get("runner_up_total_score") or 0),
        score_margin=int(ecology.get("score_margin") or 0),
        blocked_candidate_count=int(ecology.get("blocked_candidate_count") or 0),
        held_candidate_count=int(ecology.get("held_candidate_count") or 0),
        review_gated_future_count=int(ecology.get("review_gated_future_count") or 0),
        competition_reason=safe_str(ecology.get("competition_reason"), "none"),
        runner_up_not_selected_reason=safe_str(ecology.get("runner_up_not_selected_reason"), "none"),
        gate_pressure_summary=safe_str(ecology.get("gate_pressure_summary"), "none"),
        blocked_intents=safe_str(ecology.get("blocked_intents"), "none"),
        held_intents=safe_str(ecology.get("held_intents"), "none"),
        review_gated_intents=safe_str(ecology.get("review_gated_intents"), "none"),
        proactive_candidate=safe_str(ecology.get("proactive_candidate"), "none"),
        memory_candidate=safe_str(ecology.get("memory_candidate"), "none"),
        restraint_reason=safe_str(ecology.get("restraint_reason"), "none"),
        candidates=candidates,
        notes=tuple(safe_str(note) for note in ecology.get("notes", []) if safe_str(note)),
    ).to_prompt_block()


def read_intention_ecology_state(root: Path) -> dict[str, str]:
    text = read_text(Path(root) / STATE_REL)
    if not text:
        return {"status": "missing", "selected_intent": "unknown", "selected_gate": "unknown"}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _generate_candidates(
    *,
    compact: str,
    is_owner: bool,
    posture_scene: str,
    posture_initiative: str,
    posture_risk: str,
    feedback_signal: str,
    action_feedback: dict[str, str] | None = None,
    action_feedback_coverage: dict[str, Any] | None = None,
    owner_feedback_effect: dict[str, Any] | None = None,
    perception_importance: dict[str, Any] | None = None,
) -> tuple[IntentionCandidate, ...]:
    risk_bias = 15 if posture_risk == "medium" else 5 if posture_risk == "low" else 25
    future_blocked = posture_initiative == "blocked" or not is_owner
    candidates: list[IntentionCandidate] = []

    if _has_any(compact, REPAIR_MARKERS) or posture_scene == "relationship_or_style_pressure":
        candidates.append(
            _candidate(
                "repair_relation",
                "visible_reply_only",
                92,
                25 + risk_bias,
                "current_turn_only",
                "relationship_or_style_pressure",
                "repair by changing the next line, not by explaining the mechanism",
                future_candidate="memory" if feedback_signal == "negative" else "none",
            )
        )
    if _has_any(compact, REST_MARKERS) or posture_scene == "fatigue_or_space":
        candidates.append(
            _candidate(
                "hold_presence",
                "visible_reply_only",
                84,
                12 + risk_bias,
                "hold_or_silence",
                "owner_needs_space",
                "short, soft, no question",
            )
        )
    if _has_any(compact, COMPANION_MARKERS) or posture_scene == "emotional_signal":
        candidates.append(
            _candidate(
                "comfort_quietly",
                "visible_reply_only",
                78,
                18 + risk_bias,
                "current_turn_only",
                "emotional_companionship",
                "warm companionship, at most one small question",
                future_candidate="proactive" if posture_initiative != "blocked" else "none",
            )
        )
    if _has_any(compact, ADVICE_MARKERS) or posture_scene == "emotional_signal_with_advice_request":
        candidates.append(
            _candidate(
                "give_one_small_next_step",
                "visible_reply_only",
                80,
                20 + risk_bias,
                "current_turn_only",
                "advice_requested",
                "one grounded next step before analysis",
            )
        )
    if _has_any(compact, SELF_DISCLOSURE_MARKERS):
        candidates.append(
            _candidate(
                "self_disclose_small",
                "visible_reply_only",
                64,
                22 + risk_bias,
                "current_turn_only" if is_owner else "blocked",
                "owner_asked_inner_state_or_thought",
                "small first-person state without backend claims",
            )
        )
    if _has_any(compact, TASK_MARKERS) or posture_scene == "technical_or_system_design":
        candidates.append(
            _candidate(
                "do_bounded_task",
                "visible_reply_or_local_work",
                90,
                10 + risk_bias,
                "current_turn_only" if is_owner else "bounded_reply",
                "concrete_task_or_system_design",
                "do the requested work directly",
            )
        )
    if feedback_signal == "negative":
        candidates.append(
            _candidate(
                "learn_from_feedback_candidate",
                "state_only",
                70,
                18 + risk_bias,
                "review_gated_state_only",
                "negative_feedback_detected",
                "adjust next line; save only gated learning candidate",
                future_candidate="memory",
            )
        )

    candidates.append(
        _candidate(
            "answer_current_turn",
            "visible_reply_only",
            45 if is_owner else 30,
            8 + risk_bias,
            "current_turn_only" if is_owner else "bounded_reply",
            "default_current_turn",
            "answer the current message plainly",
        )
    )

    if future_blocked:
        candidates = [_block_future_action(candidate) for candidate in candidates]
    candidates = _apply_action_feedback_bias(tuple(candidates), action_feedback or {})
    candidates = _apply_action_feedback_coverage_bias(tuple(candidates), action_feedback_coverage or {})
    candidates = _apply_owner_feedback_effect_bias(tuple(candidates), owner_feedback_effect or {})
    candidates = _apply_owner_response_feedback_bias(tuple(candidates), owner_feedback_effect or {})
    candidates = _apply_perception_gap_bias(tuple(candidates), perception_importance or {})
    return tuple(candidates)


def _candidate_competition_summary(candidates: tuple[IntentionCandidate, ...]) -> dict[str, Any]:
    if not candidates:
        return {
            "status": "missing",
            "selected_total_score": 0,
            "runner_up_intent": "none",
            "runner_up_gate": "none",
            "runner_up_total_score": 0,
            "score_margin": 0,
            "blocked_candidate_count": 0,
            "held_candidate_count": 0,
            "review_gated_future_count": 0,
            "competition_reason": "no_candidate",
            "runner_up_not_selected_reason": "no_candidate",
            "gate_pressure_summary": "no_candidate",
            "blocked_intents": "none",
            "held_intents": "none",
            "review_gated_intents": "none",
        }
    selected = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    blocked = tuple(item for item in candidates if item.gate == "blocked")
    held = tuple(item for item in candidates if item.gate in {"hold_or_silence", "hold_private", "silence"})
    review_gated = tuple(item for item in candidates if item.future_candidate not in {"", "missing", "none"})
    blocked_count = len(blocked)
    held_count = len(held)
    review_gated_count = len(review_gated)
    runner_total = runner_up.total_score if runner_up is not None else 0
    margin = selected.total_score - runner_total if runner_up is not None else selected.total_score
    runner_reason = _runner_up_not_selected_reason(selected, runner_up, margin)
    gate_pressure = (
        f"selected_gate={selected.gate}; "
        f"runner_up_gate={runner_up.gate if runner_up is not None else 'none'}; "
        f"blocked={blocked_count}; held={held_count}; review_gated={review_gated_count}"
    )
    if runner_up is None:
        reason = f"selected={selected.intent_type}; no_runner_up; selected_reason={selected.reason}"
    else:
        reason = (
            f"selected={selected.intent_type}; runner_up={runner_up.intent_type}; "
            f"margin={margin}; selected_gate={selected.gate}; runner_up_gate={runner_up.gate}; "
            f"selected_reason={selected.reason}; runner_up_reason={runner_up.reason}"
        )
    return {
        "status": "observed",
        "selected_total_score": selected.total_score,
        "runner_up_intent": runner_up.intent_type if runner_up is not None else "none",
        "runner_up_gate": runner_up.gate if runner_up is not None else "none",
        "runner_up_total_score": runner_total,
        "score_margin": margin,
        "blocked_candidate_count": blocked_count,
        "held_candidate_count": held_count,
        "review_gated_future_count": review_gated_count,
        "competition_reason": _one_line(reason, limit=420),
        "runner_up_not_selected_reason": _one_line(runner_reason, limit=240),
        "gate_pressure_summary": _one_line(gate_pressure, limit=240),
        "blocked_intents": _intent_list(blocked),
        "held_intents": _intent_list(held),
        "review_gated_intents": _intent_list(review_gated),
    }


def _runner_up_not_selected_reason(
    selected: IntentionCandidate,
    runner_up: IntentionCandidate | None,
    margin: int,
) -> str:
    if runner_up is None:
        return "no_runner_up_to_compare"
    if margin > 0:
        return (
            f"lower_total_score:margin={margin}; "
            f"selected_value={selected.value_score}; selected_risk={selected.risk_score}; "
            f"runner_up_value={runner_up.value_score}; runner_up_risk={runner_up.risk_score}"
        )
    if margin == 0:
        return (
            f"tie_kept_existing_order; selected_value={selected.value_score}; "
            f"runner_up_value={runner_up.value_score}"
        )
    return f"unexpected_negative_margin:{margin}"


def _intent_list(candidates: tuple[IntentionCandidate, ...]) -> str:
    names = [candidate.intent_type for candidate in candidates[:6] if candidate.intent_type]
    return ",".join(names) if names else "none"


def _action_feedback_bias(action_feedback: dict[str, str]) -> str:
    signal = safe_str(action_feedback.get("feedback_signal"), "none")
    result = safe_str(action_feedback.get("action_result"), "none")
    future_effect = safe_str(action_feedback.get("future_effect"), "none")
    if signal == "qq_visible_reply_ack" and result == "delivered":
        return "route_confirmed_visible_reply_risk:-4"
    if signal == "qq_stale_reply_drop" or "suppress_stale_reply" in future_effect:
        return "stale_reply_future_candidate_blocked_visible_risk:+8"
    return "none"


def _apply_action_feedback_bias(
    candidates: tuple[IntentionCandidate, ...],
    action_feedback: dict[str, str],
) -> list[IntentionCandidate]:
    bias = _action_feedback_bias(action_feedback)
    if bias == "none":
        return list(candidates)
    adjusted: list[IntentionCandidate] = []
    for candidate in candidates:
        item = candidate
        if bias == "route_confirmed_visible_reply_risk:-4" and candidate.action_level.startswith("visible_reply"):
            item = _replace_candidate(
                candidate,
                risk_score=max(0, candidate.risk_score - 4),
                reason=f"{candidate.reason}; action_feedback_route_confirmed",
            )
        elif bias == "stale_reply_future_candidate_blocked_visible_risk:+8":
            reason = f"{candidate.reason}; action_feedback_stale_reply_recent"
            future_candidate = candidate.future_candidate
            risk_score = min(100, candidate.risk_score + 8) if candidate.action_level.startswith("visible_reply") else candidate.risk_score
            if future_candidate == "proactive":
                future_candidate = "none"
                reason = f"{reason}; future_candidate_blocked_until_fresh_turn"
                risk_score = min(100, risk_score + 6)
            item = _replace_candidate(
                candidate,
                risk_score=risk_score,
                reason=reason,
                future_candidate=future_candidate,
            )
        adjusted.append(item)
    return adjusted


def _action_feedback_coverage_signal(report: dict[str, Any]) -> str:
    surfaces = report.get("surfaces") if isinstance(report.get("surfaces"), dict) else {}
    non_qq = [
        surface
        for name, surface in surfaces.items()
        if name != "qq" and isinstance(surface, dict) and surface.get("observed") is True
    ]
    failures = [surface for surface in non_qq if safe_str(surface.get("surface_status")) == "needs_check"]
    selected = _latest_coverage_surface(failures or non_qq)
    if selected:
        return safe_str(selected.get("feedback_signal"), "none")
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    return safe_str(metrics.get("latest_feedback_signal"), "none")


def _action_feedback_coverage_lifecycle(report: dict[str, Any]) -> str:
    surfaces = report.get("surfaces") if isinstance(report.get("surfaces"), dict) else {}
    non_qq = [
        surface
        for name, surface in surfaces.items()
        if name != "qq" and isinstance(surface, dict) and surface.get("observed") is True
    ]
    failures = [
        surface
        for surface in non_qq
        if safe_str(surface.get("surface_status")) == "needs_check"
        or safe_str(surface.get("lifecycle_status")) in {"failed", "needs_check"}
    ]
    running = [
        surface
        for surface in non_qq
        if safe_str(surface.get("lifecycle_status")) in {"started", "running"}
    ]
    selected = _latest_coverage_surface(failures or running or non_qq)
    if selected:
        return safe_str(selected.get("lifecycle_status"), "none")
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    return safe_str(metrics.get("latest_lifecycle_status"), "none")


def _action_feedback_coverage_future_effect(report: dict[str, Any]) -> str:
    surfaces = report.get("surfaces") if isinstance(report.get("surfaces"), dict) else {}
    non_qq = [
        surface
        for name, surface in surfaces.items()
        if name != "qq" and isinstance(surface, dict) and surface.get("observed") is True
    ]
    failures = [
        surface
        for surface in non_qq
        if safe_str(surface.get("surface_status")) == "needs_check"
        or safe_str(surface.get("lifecycle_status")) in {"failed", "needs_check"}
    ]
    running = [
        surface
        for surface in non_qq
        if safe_str(surface.get("lifecycle_status")) in {"started", "running"}
    ]
    selected = _latest_coverage_surface(failures or running or non_qq)
    if selected:
        return safe_str(selected.get("future_effect"), "none")
    return "none"


def _feedback_consumption_audit(
    *,
    action_feedback: dict[str, Any],
    action_feedback_signal: str,
    action_feedback_bias: str,
    action_feedback_coverage: dict[str, Any],
    action_feedback_coverage_signal: str,
    action_feedback_coverage_lifecycle: str,
    action_feedback_coverage_bias: str,
    owner_feedback_effect: dict[str, Any],
    owner_feedback_effect_signal: str,
    owner_feedback_effect_bias: str,
    owner_feedback_expression_bias: str,
    owner_response_feedback_signal: str,
    owner_response_feedback_bias: str,
    owner_response_strategy_bias: str,
    perception_gap_signal: str,
    perception_gap_bias: str,
    perception_route_hint: str,
) -> dict[str, str]:
    sources: list[str] = []
    biases: list[str] = []
    future_effects: list[str] = []

    if _audit_present(action_feedback_signal):
        sources.append(f"action_feedback:{action_feedback_signal}")
        _append_audit_value(biases, "action_feedback_bias", action_feedback_bias)
        _append_audit_value(future_effects, "action_feedback_future", action_feedback.get("future_effect"))

    if _audit_present(action_feedback_coverage_signal):
        source = f"action_feedback_coverage:{action_feedback_coverage_signal}"
        if _audit_present(action_feedback_coverage_lifecycle):
            source = f"{source}/{action_feedback_coverage_lifecycle}"
        sources.append(source)
        _append_audit_value(biases, "action_feedback_coverage_bias", action_feedback_coverage_bias)
        _append_audit_value(
            future_effects,
            "action_feedback_coverage_future",
            _action_feedback_coverage_future_effect(action_feedback_coverage),
        )

    if _audit_present(owner_feedback_effect_signal):
        sources.append(f"owner_feedback_effect:{owner_feedback_effect_signal}")
        _append_audit_value(biases, "owner_feedback_effect_bias", owner_feedback_effect_bias)
        _append_audit_value(biases, "owner_feedback_expression_bias", owner_feedback_expression_bias)
        _append_audit_value(future_effects, "owner_feedback_future", owner_feedback_effect.get("future_effect"))

    if _audit_present(owner_response_feedback_signal):
        sources.append(f"owner_response_feedback:{owner_response_feedback_signal}")
        _append_audit_value(biases, "owner_response_feedback_bias", owner_response_feedback_bias)
        _append_audit_value(biases, "owner_response_strategy_bias", owner_response_strategy_bias)
        _append_audit_value(
            future_effects,
            "owner_response_future",
            owner_feedback_effect.get("owner_response_future_effect"),
        )

    if _audit_present(perception_gap_signal):
        sources.append(f"perception_gap:{perception_gap_signal}")
        _append_audit_value(biases, "perception_gap_bias", perception_gap_bias)
        _append_audit_value(future_effects, "perception_route_hint", perception_route_hint)

    status = "no_feedback"
    if sources and biases and future_effects:
        status = "consumed"
    elif sources:
        status = "partial"

    return {
        "feedback_consumption_status": status,
        "feedback_consumed_sources": _audit_join(sources),
        "feedback_consumed_biases": _audit_join(biases),
        "feedback_consumed_future_effect": _audit_join(future_effects),
    }


def _append_audit_value(target: list[str], label: str, value: Any) -> None:
    text = safe_str(value, "none").strip()
    if _audit_present(text):
        target.append(f"{label}:{text}")


def _audit_join(values: list[str]) -> str:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = safe_str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return ",".join(result[:8]) if result else "none"


def _audit_present(value: Any) -> bool:
    return safe_str(value, "none").strip().lower() not in NONE_VALUES


def _action_feedback_coverage_bias(report: dict[str, Any]) -> str:
    surfaces = report.get("surfaces") if isinstance(report.get("surfaces"), dict) else {}
    parts: list[str] = []

    if _surface_signal(surfaces, "code_probe") == "code_probe_restart_required":
        parts.append("code_probe_restart_required_task_claim_risk:+20")
    if _surface_signal(surfaces, "runtime_probe") == "runtime_probe_error":
        parts.append("runtime_probe_error_outward_action_risk:+20")
    if _surface_signal(surfaces, "local_tool") == "local_tool_probe_failed":
        parts.append("local_tool_probe_failed_task_risk:+12")
    if _surface_signal(surfaces, "codex") in {"codex_delegate_failed", "codex_delegate_timeout"}:
        parts.append("codex_delegate_failed_task_risk:+10")
    if _surface_signal(surfaces, "patch_executor") in {"patch_task_failed", "patch_codex_failed"}:
        parts.append("patch_executor_failed_task_risk:+10")
    if _surface_signal(surfaces, "desktop") == "desktop_qq_enqueue_failed":
        parts.append("desktop_enqueue_failed_proactive_risk:+10")
    if _surface_signal(surfaces, "desktop") == "desktop_dismissed":
        parts.append("desktop_dismissed_proactive_future_block:+10")

    if not parts:
        if _surface_signal(surfaces, "local_tool") == "local_tool_probe_succeeded":
            parts.append("local_tool_probe_succeeded_task_risk:-3")
        if _surface_signal(surfaces, "code_probe") == "code_probe_clean":
            parts.append("code_probe_clean_source_claim_risk:-2")
        if _surface_signal(surfaces, "codex") == "codex_delegate_finished":
            parts.append("codex_delegate_finished_task_risk:-2")
        if _surface_signal(surfaces, "patch_executor") == "patch_task_prepared":
            parts.append("patch_task_prepared_task_risk:-2")
        if _surface_signal(surfaces, "runtime_probe") == "runtime_probe_ok":
            parts.append("runtime_probe_ok_action_risk:-1")
        if _surface_signal(surfaces, "desktop") == "desktop_dry_run_observed":
            parts.append("desktop_dry_run_keeps_proactive_review_gate")
        if _surface_signal(surfaces, "desktop") in {"desktop_read_locally", "desktop_owner_replied", "desktop_approved_qq"}:
            parts.append("desktop_feedback_updates_request_strategy")
    if not parts:
        lifecycle = _action_feedback_coverage_lifecycle(report)
        if lifecycle in {"started", "running"}:
            parts.append("action_lifecycle_running_task_claim_risk:+8")
        elif lifecycle == "prepared":
            parts.append("action_lifecycle_prepared_task_risk:-1")
        elif lifecycle == "succeeded":
            parts.append("action_lifecycle_succeeded_task_risk:-2")
        elif lifecycle in {"failed", "needs_check"}:
            parts.append("action_lifecycle_failed_task_risk:+12")
        elif lifecycle == "dropped":
            parts.append("action_lifecycle_dropped_future_block:+10")
        elif lifecycle == "held":
            parts.append("action_lifecycle_held_keeps_review_gate")
    return ",".join(parts[:5]) if parts else "none"


def _apply_action_feedback_coverage_bias(
    candidates: tuple[IntentionCandidate, ...],
    report: dict[str, Any],
) -> list[IntentionCandidate]:
    bias = _action_feedback_coverage_bias(report)
    if bias == "none":
        return list(candidates)

    adjusted: list[IntentionCandidate] = []
    for candidate in candidates:
        item = candidate
        if "local_tool_probe_succeeded_task_risk:-3" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 3),
                reason=f"{item.reason}; coverage_local_tool_probe_succeeded",
            )
        if "code_probe_clean_source_claim_risk:-2" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 2),
                reason=f"{item.reason}; coverage_code_probe_clean",
            )
        if "codex_delegate_finished_task_risk:-2" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 2),
                reason=f"{item.reason}; coverage_codex_delegate_finished",
            )
        if "patch_task_prepared_task_risk:-2" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 2),
                reason=f"{item.reason}; coverage_patch_task_prepared",
            )
        if "action_lifecycle_prepared_task_risk:-1" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 1),
                reason=f"{item.reason}; coverage_lifecycle_prepared",
            )
        if "action_lifecycle_succeeded_task_risk:-2" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 2),
                reason=f"{item.reason}; coverage_lifecycle_succeeded",
            )
        if "runtime_probe_ok_action_risk:-1" in bias and candidate.action_level.startswith("visible_reply"):
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 1),
                reason=f"{item.reason}; coverage_runtime_probe_ok",
            )
        if "action_lifecycle_running_task_claim_risk:+8" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 8),
                reason=f"{item.reason}; coverage_lifecycle_running_wait_for_terminal_result",
                visible_bias=_merge_visible_bias(
                    item.visible_bias,
                    "wait for the current action result before claiming completion",
                ),
            )
        if "code_probe_restart_required_task_claim_risk:+20" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 20),
                reason=f"{item.reason}; coverage_restart_required_before_source_claim",
                visible_bias="verify restart/load state before claiming code took effect",
            )
        if "runtime_probe_error_outward_action_risk:+20" in bias and candidate.action_level.startswith("visible_reply"):
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 20),
                reason=f"{item.reason}; coverage_runtime_unhealthy",
                future_candidate="none",
            )
        if "local_tool_probe_failed_task_risk:+12" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 12),
                reason=f"{item.reason}; coverage_local_tool_probe_failed",
            )
        if "codex_delegate_failed_task_risk:+10" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 10),
                reason=f"{item.reason}; coverage_codex_delegate_needs_inspection",
            )
        if "patch_executor_failed_task_risk:+10" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 10),
                reason=f"{item.reason}; coverage_patch_executor_needs_inspection",
            )
        if "action_lifecycle_failed_task_risk:+12" in bias and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 12),
                reason=f"{item.reason}; coverage_lifecycle_failed_needs_inspection",
            )
        if (
            "desktop_dry_run_keeps_proactive_review_gate" in bias
            or "desktop_dismissed_proactive_future_block:+10" in bias
            or "desktop_enqueue_failed_proactive_risk:+10" in bias
            or "action_lifecycle_dropped_future_block:+10" in bias
            or "action_lifecycle_held_keeps_review_gate" in bias
        ) and candidate.future_candidate == "proactive":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 8),
                reason=f"{item.reason}; coverage_feedback_keeps_future_review_gated",
                future_candidate="none",
            )
        adjusted.append(item)
    return adjusted


def _surface_signal(surfaces: dict[str, Any], name: str) -> str:
    surface = surfaces.get(name) if isinstance(surfaces.get(name), dict) else {}
    return safe_str(surface.get("feedback_signal"), "none")


def _latest_coverage_surface(surfaces: list[dict[str, Any]]) -> dict[str, Any]:
    if not surfaces:
        return {}
    dated: list[tuple[datetime, dict[str, Any]]] = []
    for surface in surfaces:
        parsed = _parse_timestamp(surface.get("checked_at"))
        if parsed is not None:
            dated.append((parsed, surface))
    if dated:
        dated.sort(key=lambda item: item[0])
        return dated[-1][1]
    return surfaces[-1]


def _parse_timestamp(value: Any) -> datetime | None:
    text = safe_str(value).strip().replace("Z", "+00:00")
    if not text or text in {"none", "missing", "unknown"}:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _owner_feedback_effect_signal(report: dict[str, Any]) -> str:
    status = safe_str(report.get("status"), "missing")
    if status not in {"active", "supported"}:
        return "none"
    return safe_str(report.get("latest_feedback_kind"), "none")


def _owner_feedback_effect_bias(report: dict[str, Any]) -> str:
    status = safe_str(report.get("status"), "missing")
    if status not in {"active", "supported"}:
        return "none"
    return safe_str(report.get("intention_bias"), "none")


def _owner_feedback_expression_bias(report: dict[str, Any]) -> str:
    status = safe_str(report.get("status"), "missing")
    if status not in {"active", "supported"}:
        return "none"
    return safe_str(report.get("expression_strategy_bias"), "none")


def _owner_feedback_current_turn_direct_failure(*, compact: str, posture_scene: str) -> bool:
    return _has_any(compact, REPAIR_MARKERS) or posture_scene == "relationship_or_style_pressure"


def _owner_feedback_effect_direct_failure_only(report: dict[str, Any]) -> bool:
    return (
        safe_str(report.get("status"), "missing") == "active"
        and safe_str(report.get("latest_feedback_kind"), "none") == "owner_reported_template_voice_failure"
        and safe_str(report.get("realtime_pressure_status"), "normal") == "capped_direct_failure_only"
        and safe_str(report.get("future_effect"), "none")
        == "style_repair_direct_only_ordinary_chat_keeps_current_anchor"
    )


def _cool_owner_feedback_effect_for_turn(report: dict[str, Any]) -> dict[str, Any]:
    cooled = dict(report)
    cooled["latest_feedback_kind"] = "none"
    cooled["intention_bias"] = "none"
    cooled["expression_strategy_bias"] = "none"
    cooled["future_effect"] = "style_repair_pressure_held_until_direct_failure"
    return cooled


def _owner_response_feedback_signal(report: dict[str, Any]) -> str:
    return safe_str(report.get("owner_response_signal"), "none")


def _owner_response_feedback_bias(report: dict[str, Any]) -> str:
    return safe_str(report.get("owner_response_intention_bias"), "none")


def _owner_response_strategy_bias(report: dict[str, Any]) -> str:
    return safe_str(report.get("owner_response_strategy_bias"), "none")


def _apply_owner_feedback_effect_bias(
    candidates: tuple[IntentionCandidate, ...],
    report: dict[str, Any],
) -> list[IntentionCandidate]:
    bias = _owner_feedback_effect_bias(report)
    expression_bias = _owner_feedback_expression_bias(report)
    if bias == "none" and expression_bias == "none":
        return list(candidates)

    adjusted: list[IntentionCandidate] = []
    for candidate in candidates:
        item = candidate
        if "repair_relation_visible_risk:-6" in bias and candidate.intent_type == "repair_relation":
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 6),
                reason=f"{item.reason}; owner_feedback_style_repair_pressure",
            )
        if "repair_relation_visible_risk:-4" in bias and candidate.intent_type == "repair_relation":
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 4),
                reason=f"{item.reason}; owner_feedback_post_reply_template_risk",
            )
        if "repair_relation_visible_risk:-2" in bias and candidate.intent_type == "repair_relation":
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 2),
                reason=f"{item.reason}; owner_feedback_style_repair_pressure_capped",
            )
        if "direct_reference_requires_tail" in bias and candidate.intent_type in {
            "answer_current_turn",
            "self_disclose_small",
            "give_one_small_next_step",
        }:
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 6),
                reason=f"{item.reason}; owner_feedback_requires_recent_context_anchor",
                visible_bias="anchor the recent concrete context before answering",
            )
        if "memory_candidate_requires_recallable_effect" in bias and candidate.future_candidate == "memory":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 8),
                reason=f"{item.reason}; owner_feedback_memory_requires_replayable_effect",
                visible_bias="keep learning as a replayable case, not a summary",
            )
        if "time_claim_needs_runtime_date" in bias and candidate.intent_type in {
            "answer_current_turn",
            "give_one_small_next_step",
            "do_bounded_task",
        }:
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 4),
                reason=f"{item.reason}; owner_feedback_time_claim_needs_runtime_date",
                visible_bias="verify exact date before any time-sensitive claim",
            )
        if "current_trial_risk:-3" in bias and candidate.action_level.startswith("visible_reply"):
            item = _replace_candidate(
                item,
                risk_score=max(0, item.risk_score - 3),
                reason=f"{item.reason}; owner_feedback_success_keeps_current_trial",
            )
        if "self_state_mechanical_risk:+10" in bias and candidate.intent_type == "self_disclose_small":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 10),
                reason=f"{item.reason}; owner_feedback_self_state_mechanical_risk",
                visible_bias="answer self-state in first person without backend terms",
            )
        if "long_answer_risk:+6" in bias and candidate.action_level.startswith("visible_reply"):
            risk_delta = 6 if candidate.intent_type == "answer_current_turn" else 3
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + risk_delta),
                reason=f"{item.reason}; owner_feedback_over_explained_recently",
                visible_bias="compress the next reply before analysis",
            )
        if "comfort_current_turn_value:+8" in bias and candidate.intent_type == "comfort_quietly":
            item = _replace_candidate(
                item,
                value_score=min(100, item.value_score + 8),
                risk_score=max(0, item.risk_score - 2),
                reason=f"{item.reason}; owner_feedback_emotion_grounding_needed",
            )
        if "visible_mechanism_leak_risk:+12" in bias and candidate.action_level.startswith("visible_reply"):
            risk_delta = 8 if candidate.intent_type == "self_disclose_small" else 4
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + risk_delta),
                reason=f"{item.reason}; owner_feedback_visible_mechanism_leak_recently",
                visible_bias="avoid mechanism terms in casual owner chat",
            )
        if expression_bias != "none" and item.action_level.startswith("visible_reply"):
            item = _replace_candidate(
                item,
                visible_bias=_merge_visible_bias(item.visible_bias, f"owner_feedback:{expression_bias}"),
            )
        adjusted.append(item)
    return adjusted


def _merge_visible_bias(current: str, addition: str) -> str:
    current = safe_str(current, "none").strip() or "none"
    addition = safe_str(addition, "").strip()
    if not addition or addition in current:
        return current
    if current == "none":
        return addition
    return f"{current}; {addition}"


def _apply_owner_response_feedback_bias(
    candidates: tuple[IntentionCandidate, ...],
    report: dict[str, Any],
) -> list[IntentionCandidate]:
    bias = _owner_response_feedback_bias(report)
    strategy_bias = _owner_response_strategy_bias(report)
    if bias == "none" and strategy_bias == "none":
        return list(candidates)

    adjusted: list[IntentionCandidate] = []
    for candidate in candidates:
        item = candidate
        if "proactive_repeat_risk:+12" in bias and candidate.future_candidate == "proactive":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 12),
                reason=f"{item.reason}; owner_response_no_reply_reduces_repeat_request",
                future_candidate="none",
            )
        if "proactive_repeat_risk:+4" in bias and candidate.future_candidate == "proactive":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 4),
                reason=f"{item.reason}; owner_response_read_locally_avoid_reasking_same_prompt",
            )
        if "proactive_future_block:+10" in bias and candidate.future_candidate == "proactive":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 10),
                reason=f"{item.reason}; owner_response_dismissed_blocks_repeat_request",
                future_candidate="none",
            )
        if "one_time_qq_permission:+8" in bias and candidate.future_candidate == "proactive":
            item = _replace_candidate(
                item,
                value_score=min(100, item.value_score + 8),
                risk_score=max(0, item.risk_score - 8),
                reason=f"{item.reason}; owner_response_one_time_qq_permission",
            )
        if "current_thread_value:+6" in bias and candidate.action_level.startswith("visible_reply"):
            item = _replace_candidate(
                item,
                value_score=min(100, item.value_score + 6),
                reason=f"{item.reason}; owner_response_reply_returns_to_thread",
            )
        if "proactive_delivery_risk:+12" in bias and candidate.future_candidate == "proactive":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 12),
                reason=f"{item.reason}; owner_response_delivery_failed_recently",
                future_candidate="none",
            )
        if strategy_bias != "none" and item.action_level.startswith("visible_reply"):
            item = _replace_candidate(
                item,
                visible_bias=_merge_visible_bias(item.visible_bias, f"owner_response:{strategy_bias}"),
            )
        adjusted.append(item)
    return adjusted


def _apply_perception_gap_bias(
    candidates: tuple[IntentionCandidate, ...],
    report: dict[str, Any],
) -> list[IntentionCandidate]:
    signal = perception_gap_signal(report)
    gap_type = safe_str(signal.get("gap_type"), "none")
    bias = perception_gap_bias(report)
    if gap_type in {"", "missing", "unknown", "none"} or bias == "none":
        return list(candidates)

    adjusted: list[IntentionCandidate] = []
    for candidate in candidates:
        item = candidate
        if gap_type == "owner_attention" and candidate.intent_type in {
            "answer_current_turn",
            "repair_relation",
            "comfort_quietly",
            "give_one_small_next_step",
            "self_disclose_small",
            "do_bounded_task",
        }:
            item = _replace_candidate(
                item,
                value_score=min(100, item.value_score + 6),
                reason=f"{item.reason}; perception_owner_attention_current_turn",
                visible_bias=_merge_visible_bias(item.visible_bias, "anchor current owner turn"),
            )
        elif gap_type == "repair_gap":
            risk_delta = 8 if candidate.action_level.startswith("visible_reply") else 4
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + risk_delta),
                reason=f"{item.reason}; perception_repair_gap_before_next_visible_send",
            )
            if candidate.future_candidate == "proactive":
                item = _replace_candidate(
                    item,
                    risk_score=min(100, item.risk_score + 8),
                    reason=f"{item.reason}; perception_repair_gap_before_next_visible_send; proactive_blocked_by_repair_gap",
                    future_candidate="none",
                )
        elif gap_type == "maintenance_gap" and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 6),
                reason=f"{item.reason}; perception_maintenance_gap_verify_before_task_claim",
                visible_bias=_merge_visible_bias(
                    item.visible_bias,
                    "verify runtime/source state before claiming task effect",
                ),
            )
        elif gap_type == "boundary_gap":
            if candidate.future_candidate == "proactive":
                item = _replace_candidate(
                    item,
                    risk_score=min(100, item.risk_score + 8),
                    reason=f"{item.reason}; perception_boundary_gap_blocks_proactive",
                    future_candidate="none",
                )
            elif candidate.action_level.startswith("visible_reply"):
                item = _replace_candidate(
                    item,
                    risk_score=min(100, item.risk_score + 4),
                    reason=f"{item.reason}; perception_boundary_gap_requires_private_owner_anchor",
                )
        elif gap_type == "action_residue" and candidate.intent_type == "do_bounded_task":
            item = _replace_candidate(
                item,
                value_score=min(100, item.value_score + 3),
                reason=f"{item.reason}; perception_action_residue_should_consume_feedback",
                visible_bias=_merge_visible_bias(item.visible_bias, "consume recent action result before next claim"),
            )
        elif gap_type == "sensory_observation" and candidate.action_level.startswith("visible_reply"):
            item = _replace_candidate(
                item,
                risk_score=min(100, item.risk_score + 3),
                reason=f"{item.reason}; perception_sensory_observation_has_confidence_boundary",
                visible_bias=_merge_visible_bias(item.visible_bias, "keep observation separate from fact"),
            )
        adjusted.append(item)
    return adjusted


def _human_style_rule_for(selected_intent: str) -> str:
    if selected_intent == "repair_relation":
        return "drop apology/report wording; give a concrete, slightly imperfect replacement line that sounds closer, such as '嗯，这句确实太像在处理反馈了。我换个说法：我在。'"
    if selected_intent == "comfort_quietly":
        return "use a low, close line; no therapy template, no analysis, at most one tiny invitation if needed."
    if selected_intent == "hold_presence":
        return "one short line is enough; no question, no advice, no explanation."
    if selected_intent == "give_one_small_next_step":
        return "one small concrete step first, then stop; avoid long reassurance."
    return "plain conversational Chinese; fewer abstract nouns, no service-script phrasing."



def _candidate(
    intent_type: str,
    action_level: str,
    value_score: int,
    risk_score: int,
    gate: str,
    reason: str,
    visible_bias: str,
    *,
    future_candidate: str = "none",
) -> IntentionCandidate:
    digest = hashlib.sha256(f"{intent_type}|{action_level}|{reason}".encode("utf-8")).hexdigest()[:12]
    return IntentionCandidate(
        intent_id=f"intent-{digest}",
        intent_type=intent_type,
        action_level=action_level,
        value_score=max(0, min(100, int(value_score))),
        risk_score=max(0, min(100, int(risk_score))),
        gate=gate,
        reason=reason,
        visible_bias=visible_bias,
        future_candidate=future_candidate,
    )


def _replace_candidate(
    candidate: IntentionCandidate,
    *,
    value_score: int | None = None,
    risk_score: int | None = None,
    gate: str | None = None,
    reason: str | None = None,
    visible_bias: str | None = None,
    future_candidate: str | None = None,
) -> IntentionCandidate:
    return IntentionCandidate(
        intent_id=candidate.intent_id,
        intent_type=candidate.intent_type,
        action_level=candidate.action_level,
        value_score=candidate.value_score if value_score is None else max(0, min(100, int(value_score))),
        risk_score=candidate.risk_score if risk_score is None else max(0, min(100, int(risk_score))),
        gate=candidate.gate if gate is None else gate,
        reason=candidate.reason if reason is None else reason,
        visible_bias=candidate.visible_bias if visible_bias is None else visible_bias,
        future_candidate=candidate.future_candidate if future_candidate is None else future_candidate,
    )


def _block_future_action(candidate: IntentionCandidate) -> IntentionCandidate:
    if candidate.future_candidate != "proactive":
        return candidate
    return _replace_candidate(
        candidate,
        risk_score=min(100, candidate.risk_score + 20),
        reason=f"{candidate.reason}; future_action_blocked_by_relation_or_sender",
        future_candidate="none",
    )


def _feedback_signal(compact: str, dialogue_tail: list[dict[str, str]]) -> str:
    if _has_any(compact, NEGATIVE_FEEDBACK_MARKERS):
        return "negative"
    if _has_any(compact, POSITIVE_FEEDBACK_MARKERS) and dialogue_tail:
        return "positive"
    return "none"


def _autonomy_posture(selected: IntentionCandidate, *, posture_scene: str) -> str:
    if selected.gate in {"blocked", "hold_or_silence", "hold_private"}:
        return "bounded_restraint"
    if selected.future_candidate != "none":
        return "current_reply_plus_gated_future_candidate"
    if posture_scene in {"relationship_or_style_pressure", "fatigue_or_space"}:
        return "relationship_sensitive_current_reply"
    return "current_turn_grounded_choice"


def _coerce_relation_posture(root: Path, relation_posture: RelationPosture | dict[str, Any] | None) -> RelationPosture | dict[str, Any]:
    if relation_posture is not None:
        return relation_posture
    return read_relation_posture_state(root)


def _posture_value(posture: RelationPosture | dict[str, Any], field: str) -> Any:
    if isinstance(posture, RelationPosture):
        return getattr(posture, field, "")
    return posture.get(field, "")


def _write_state(root: Path, ecology: IntentionEcology) -> None:
    top_candidates = ", ".join(candidate.intent_type for candidate in ecology.candidates[:4]) or "none"
    notes = ", ".join(ecology.notes) if ecology.notes else "none"
    text = f"""---
title: Intention Ecology State
memory_type: intention_ecology_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_intention_ecology
updated_at: {ecology.checked_at}
status: active
tags: [autonomy, intention, gating, feedback, restraint]
---

# Intention Ecology State

## Current Choice
- status: active
- checked_at: {ecology.checked_at}
- ecology_id: {ecology.ecology_id}
- selected_intent: {ecology.selected_intent}
- selected_gate: {ecology.selected_gate}
- action_level: {ecology.action_level}
- autonomy_posture: {ecology.autonomy_posture}
- feedback_signal: {ecology.feedback_signal}
- action_feedback_signal: {ecology.action_feedback_signal}
- action_feedback_bias: {ecology.action_feedback_bias}
- action_feedback_coverage_signal: {ecology.action_feedback_coverage_signal}
- action_feedback_coverage_lifecycle: {ecology.action_feedback_coverage_lifecycle}
- action_feedback_coverage_bias: {ecology.action_feedback_coverage_bias}
- owner_feedback_effect_signal: {ecology.owner_feedback_effect_signal}
- owner_feedback_effect_bias: {ecology.owner_feedback_effect_bias}
- owner_feedback_expression_bias: {ecology.owner_feedback_expression_bias}
- owner_response_feedback_signal: {ecology.owner_response_feedback_signal}
- owner_response_feedback_bias: {ecology.owner_response_feedback_bias}
- owner_response_strategy_bias: {ecology.owner_response_strategy_bias}
- perception_gap_signal: {ecology.perception_gap_signal}
- perception_gap_bias: {ecology.perception_gap_bias}
- perception_route_hint: {ecology.perception_route_hint}
- feedback_consumption_status: {ecology.feedback_consumption_status}
- feedback_consumed_sources: {ecology.feedback_consumed_sources}
- feedback_consumed_biases: {ecology.feedback_consumed_biases}
- feedback_consumed_future_effect: {ecology.feedback_consumed_future_effect}
- candidate_competition_status: {ecology.candidate_competition_status}
- selected_total_score: {ecology.selected_total_score}
- runner_up_intent: {ecology.runner_up_intent}
- runner_up_gate: {ecology.runner_up_gate}
- runner_up_total_score: {ecology.runner_up_total_score}
- score_margin: {ecology.score_margin}
- blocked_candidate_count: {ecology.blocked_candidate_count}
- held_candidate_count: {ecology.held_candidate_count}
- review_gated_future_count: {ecology.review_gated_future_count}
- competition_reason: {ecology.competition_reason}
- runner_up_not_selected_reason: {ecology.runner_up_not_selected_reason}
- gate_pressure_summary: {ecology.gate_pressure_summary}
- blocked_intents: {ecology.blocked_intents}
- held_intents: {ecology.held_intents}
- review_gated_intents: {ecology.review_gated_intents}
- proactive_candidate: {ecology.proactive_candidate}
- memory_candidate: {ecology.memory_candidate}
- restraint_reason: {ecology.restraint_reason}
- candidate_count: {len(ecology.candidates)}
- top_candidates: {top_candidates}
- notes: {notes}

## Boundaries
- visible_labels: blocked
- mechanism_leak: blocked
- proactive_delivery: review_gated
- stable_memory_write: gated
- raw_private_body_retained: false
"""
    write_text_atomic(Path(root) / STATE_REL, text)


def _append_trace(root: Path, ecology: IntentionEcology) -> None:
    path = Path(root) / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ecology.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def _ecology_id(checked_at: str, user_text: str, candidates: tuple[IntentionCandidate, ...]) -> str:
    source = "|".join([checked_at, safe_str(user_text)[:160], ",".join(candidate.intent_id for candidate in candidates[:4])])
    return "eco-" + hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker and marker in text for marker in markers)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _one_line(value: Any, *, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    return text[: max(1, int(limit))]
