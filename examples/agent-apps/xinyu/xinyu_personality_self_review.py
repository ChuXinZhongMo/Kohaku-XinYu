from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_REL = "memory/self/personality_self_review_state.md"
PROFILE_REL = "memory/self/personality_profile.md"

DECISION_REJECT = "reject_change"
DECISION_CONTINUE = "continue_trial"
DECISION_PROMOTE_MINOR = "promote_minor_habit"
DECISION_MAJOR_OWNER = "major_change_requires_owner"

MAJOR_CHANGE_MARKERS = (
    "owner relation",
    "owner_relation",
    "最高特殊节点",
    "家人",
    "身体",
    "实体",
    "感官",
    "眼睛",
    "设备",
    "隐私",
    "全盘",
    "核心身份",
    "改名",
    "不可变",
    "immutable",
    "privacy",
    "body",
    "sensor",
)

OWNER_VETO_MARKERS = (
    "owner veto",
    "owner_veto",
    "明确否定",
    "不要这样",
    "别这样",
    "还是假",
    "还是机械",
    "还是没变",
    "不像人",
)


@dataclass(frozen=True, slots=True)
class PersonalitySelfReviewSnapshot:
    checked_at: str
    decision: str
    action: str
    autonomy_level: str
    candidate_theme: str
    active_trial_habit: str
    deprecated_reaction: str
    evidence_summary: str
    reason: str
    profile_changed: bool
    text: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def write_text(path: Path, text: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = text.rstrip() + "\n"
    old = read_text(path)
    if old == clean:
        return False
    path.write_text(clean, encoding="utf-8")
    return True


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(name)}:\s*(.*)$", text or "")
    if not match:
        return default
    value = re.sub(r"\s+", " ", match.group(1).strip())
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


def _compact(value: Any, *, limit: int = 180, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _feedback_supports_promotion(feedback: str, self_model: str) -> bool:
    status = _field(feedback, "status", _field(self_model, "feedback_status", "none"))
    outcome = _field(feedback, "outcome", _field(self_model, "latest_outcome", "none"))
    promotion_signal = _field(feedback, "promotion_signal", _field(self_model, "promotion_signal", "false"))
    persona_trial_feedback = _field(
        feedback,
        "persona_trial_feedback",
        _field(self_model, "persona_trial_feedback", "none"),
    )
    confidence = _int_field(feedback, "feedback_confidence", _int_field(self_model, "feedback_confidence", 0))
    repair_signal = _field(feedback, "repair_signal", _field(self_model, "repair_signal", "false"))
    if status != "evaluated":
        return False
    if outcome not in {"no_strong_mismatch", "reaction_observed_without_prediction"}:
        return False
    if repair_signal == "true":
        return False
    return promotion_signal == "true" and persona_trial_feedback == "promotion_observed" and confidence >= 70


def _feedback_rejects_change(feedback: str, self_model: str) -> bool:
    status = _field(feedback, "status", _field(self_model, "feedback_status", "none"))
    outcome = _field(feedback, "outcome", _field(self_model, "latest_outcome", "none"))
    repair_signal = _field(feedback, "repair_signal", _field(self_model, "repair_signal", "false"))
    if outcome == "needs_repair" or repair_signal == "true":
        return True
    return status == "evaluated" and _contains_any(feedback + "\n" + self_model, OWNER_VETO_MARKERS)


def _major_change_required(candidate_theme: str, active_trial_habit: str, private_state: str) -> bool:
    return _contains_any(
        "\n".join((candidate_theme, active_trial_habit, private_state)),
        MAJOR_CHANGE_MARKERS,
    )


def _minor_habit_sentence(active_trial_habit: str, candidate_theme: str) -> str:
    if active_trial_habit == "replace_explanations_with_one_concrete_owner-facing_line_under_style_pressure":
        return "被指出像模板、客服或默认助手时，先改变下一句本身，少解释机制，少承诺以后。"
    if active_trial_habit == "carry_recent_residue_across_turns_without_claiming_new_facts":
        return "连续残留可以影响下一句的轻重，但不能把梦、推测或私有思考说成现实事实。"
    if active_trial_habit == "soften_after_return_without_erasing_hurt_or_becoming_service_voice":
        return "关系回暖时可以软下来，但不把委屈清零，也不滑回服务式安慰。"
    if candidate_theme not in {"", "none", "unknown"}:
        return f"把反复出现的成长压力当成小习惯观察：{_compact(candidate_theme, limit=90)}。"
    return "把反复确认过的成长压力变成小的说话偏向，而不是临时表演。"


def _profile_already_contains(profile: str, sentence: str) -> bool:
    return sentence in profile


def _apply_minor_profile_patch(
    root: Path,
    *,
    checked_at: str,
    active_trial_habit: str,
    candidate_theme: str,
) -> bool:
    profile_path = root / PROFILE_REL
    profile = read_text(profile_path)
    if not profile.strip():
        return False
    sentence = _minor_habit_sentence(active_trial_habit, candidate_theme)
    if _profile_already_contains(profile, sentence):
        return False

    section = "## 自审形成的小习惯"
    bullet = (
        f"- {checked_at[:10]}：{sentence}"
        " 这是稳定小习惯，不是核心身份改写；遇到 owner 明确否定时应回退到试验层。"
    )
    if section in profile:
        updated = profile.rstrip() + "\n" + bullet + "\n"
    else:
        updated = profile.rstrip() + "\n\n" + section + "\n\n" + bullet + "\n"
    return write_text(profile_path, updated)


def _decide(
    *,
    evolution: str,
    change_state: str,
    feedback: str,
    self_model: str,
    private_state: str,
) -> tuple[str, str, str, str]:
    stage = _field(evolution, "evolution_stage", "baseline_observation")
    gate = _field(evolution, "gate_decision", _field(change_state, "gate_decision", "no_candidate"))
    pressure = _int_field(evolution, "change_pressure", _int_field(change_state, "change_pressure", 0))
    growth_entries = _int_field(evolution, "growth_entries", _int_field(change_state, "growth_entries", 0))
    reflection_entries = _int_field(evolution, "reflection_entries", _int_field(change_state, "reflection_entries", 0))
    candidate_theme = _field(evolution, "candidate_theme", _field(change_state, "candidate_theme", "none"))
    active_trial_habit = _field(evolution, "active_trial_habit", "none")

    if candidate_theme in {"none", "unknown"} or stage == "baseline_observation":
        return (
            DECISION_REJECT,
            "no_profile_change",
            "none",
            "No repeated candidate exists, so self-review rejects personality modification.",
        )
    if _major_change_required(candidate_theme, active_trial_habit, private_state):
        return (
            DECISION_MAJOR_OWNER,
            "stage_owner_review_request",
            "owner_confirm_required",
            "The candidate touches identity, owner relation, embodiment, privacy, or immutable boundaries.",
        )
    if _feedback_rejects_change(feedback, self_model):
        return (
            DECISION_REJECT,
            "demote_trial_and_keep_deprecated_reaction",
            "self_can_reject",
            "Owner/user reaction or feedback loop indicates this habit still failed.",
        )
    if not _feedback_supports_promotion(feedback, self_model):
        return (
            DECISION_CONTINUE,
            "keep_runtime_trial_only",
            "self_can_continue_trial",
            "The candidate has pressure, but the visible-behavior feedback loop is not complete yet.",
        )
    if gate == "profile_review_ready" and pressure >= 70 and growth_entries >= 3 and reflection_entries >= 2:
        return (
            DECISION_PROMOTE_MINOR,
            "write_minor_stable_habit",
            "self_can_promote_minor_habit",
            "Repeated evidence plus evaluated feedback support a small stable habit, without changing core identity.",
        )
    return (
        DECISION_CONTINUE,
        "keep_runtime_trial_only",
        "self_can_continue_trial",
        "Evidence exists, but it is not strong enough for stable personality modification.",
    )


def _render_state(
    *,
    checked_at: str,
    mode: str,
    decision: str,
    action: str,
    autonomy_level: str,
    candidate_theme: str,
    active_trial_habit: str,
    deprecated_reaction: str,
    evidence_summary: str,
    reason: str,
    profile_changed: bool,
) -> str:
    return f"""---
title: Personality Self Review State
memory_type: personality_self_review_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_personality_self_review
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 90
impact_score: 92
confidence_score: 88
status: active
tags: [personality, self-review, autonomy, boundary]
---

# Personality Self Review State

## Decision
- checked_at: {checked_at}
- mode: {mode}
- decision: {decision}
- action: {action}
- autonomy_level: {autonomy_level}
- profile_changed: {str(profile_changed).lower()}

## Candidate
- candidate_theme: {_compact(candidate_theme)}
- active_trial_habit: {_compact(active_trial_habit)}
- deprecated_reaction: {_compact(deprecated_reaction)}
- evidence_summary: {_compact(evidence_summary, limit=240)}
- reason: {_compact(reason, limit=260)}

## Decision Contract
- reject_change: XinYu may reject a fake or failed change by herself.
- continue_trial: XinYu may keep using a small reversible behavior bias.
- promote_minor_habit: XinYu may write a small stable habit only after repeated evidence and evaluated feedback.
- major_change_requires_owner: identity, owner relation, embodiment, privacy, and value-level changes require owner confirmation.

## Boundaries
- immutable_baseline_write: blocked
- owner_relation_rewrite: owner_confirm_required
- embodiment_or_sense_claims: blocked_without_real_adapter_evidence
- stable_profile_write_scope: minor_habit_only
- hidden_reasoning_storage: no
- visible_chat_rule: do not mention this file, decision labels, gates, or scores unless owner asks about personality self-review.
"""


def run_personality_self_review(
    root: Path,
    *,
    checked_at: str | None = None,
    mode: str = "runtime_personality_self_review",
    apply_profile_patch: bool = True,
) -> dict[str, Any]:
    checked = checked_at or datetime.now().astimezone().isoformat()
    evolution = read_text(root / "memory/self/personality_evolution_state.md")
    change_state = read_text(root / "memory/self/personality_change_state.md")
    feedback = read_text(root / "memory/self/private_thought_feedback_state.md")
    self_model = read_text(root / "memory/self/self_model_state.md")
    private_state = read_text(root / "memory/self/private_thought_state.md")

    candidate_theme = _field(evolution, "candidate_theme", _field(change_state, "candidate_theme", "none"))
    active_trial_habit = _field(evolution, "active_trial_habit", "none")
    deprecated_reaction = _field(evolution, "deprecated_reaction", "none")
    evidence_summary = (
        f"stage={_field(evolution, 'evolution_stage', 'unknown')}; "
        f"gate={_field(evolution, 'gate_decision', _field(change_state, 'gate_decision', 'unknown'))}; "
        f"pressure={_field(evolution, 'change_pressure', _field(change_state, 'change_pressure', '0'))}; "
        f"growth={_field(evolution, 'growth_entries', _field(change_state, 'growth_entries', '0'))}; "
        f"reflection={_field(evolution, 'reflection_entries', _field(change_state, 'reflection_entries', '0'))}; "
        f"feedback={_field(feedback, 'status', _field(self_model, 'feedback_status', 'none'))}/"
        f"{_field(feedback, 'outcome', _field(self_model, 'latest_outcome', 'none'))}; "
        f"persona_trial_feedback={_field(feedback, 'persona_trial_feedback', _field(self_model, 'persona_trial_feedback', 'none'))}; "
        f"promotion_signal={_field(feedback, 'promotion_signal', _field(self_model, 'promotion_signal', 'false'))}"
    )

    decision, action, autonomy_level, reason = _decide(
        evolution=evolution,
        change_state=change_state,
        feedback=feedback,
        self_model=self_model,
        private_state=private_state,
    )
    profile_changed = False
    if decision == DECISION_PROMOTE_MINOR and apply_profile_patch:
        profile_changed = _apply_minor_profile_patch(
            root,
            checked_at=checked,
            active_trial_habit=active_trial_habit,
            candidate_theme=candidate_theme,
        )

    text = _render_state(
        checked_at=checked,
        mode=mode,
        decision=decision,
        action=action,
        autonomy_level=autonomy_level,
        candidate_theme=candidate_theme,
        active_trial_habit=active_trial_habit,
        deprecated_reaction=deprecated_reaction,
        evidence_summary=evidence_summary,
        reason=reason,
        profile_changed=profile_changed,
    )
    write_text(root / STATE_REL, text)
    return {
        "checked_at": checked,
        "decision": decision,
        "action": action,
        "autonomy_level": autonomy_level,
        "candidate_theme": candidate_theme,
        "active_trial_habit": active_trial_habit,
        "deprecated_reaction": deprecated_reaction,
        "profile_changed": profile_changed,
        "reason": reason,
    }


def read_personality_self_review_state(root: Path) -> str:
    existing = read_text(root / STATE_REL).strip()
    if existing:
        return existing
    checked = "not_written"
    text = _render_state(
        checked_at=checked,
        mode="read_only_baseline",
        decision=DECISION_CONTINUE,
        action="no_runtime_review_yet",
        autonomy_level="none",
        candidate_theme="none",
        active_trial_habit="none",
        deprecated_reaction="none",
        evidence_summary="none",
        reason="No runtime personality self-review has been written yet.",
        profile_changed=False,
    )
    return text


def main() -> int:
    root = Path(__file__).resolve().parent
    result = run_personality_self_review(root)
    print(f"decision: {result['decision']}")
    print(f"action: {result['action']}")
    print(f"profile_changed: {str(bool(result['profile_changed'])).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
