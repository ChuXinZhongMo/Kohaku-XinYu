from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from stores.slow_state_modulator_state import SLOW_STATE_REL as STATE_REL
from stores.slow_state_modulator_state import read_slow_state_payload
from stores.slow_state_modulator_state import write_slow_state_payload
from xinyu_turn_residue import TurnResidue, read_turn_residue


FATIGUE_HALF_LIFE_HOURS = 2.5
RELATION_HALF_LIFE_HOURS = 8.0
CORRECTION_HALF_LIFE_HOURS = 4.0
INITIATIVE_HALF_LIFE_HOURS = 6.0


@dataclass(frozen=True, slots=True)
class SlowState:
    updated_at: str
    fatigue_load: int
    relation_guard: int
    correction_pressure: int
    initiative_dampening: int
    reply_policy: str
    initiative_policy: str
    recall_policy: str
    emotion_policy: str
    active_policies: tuple[str, ...]
    evidence_signals: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["active_policies"] = list(self.active_policies)
        data["evidence_signals"] = list(self.evidence_signals)
        data["notes"] = list(self.notes)
        return data


def build_slow_state(
    root: Path,
    *,
    user_text: str = "",
    scene_frame: Any | None = None,
    triage_decision: Any | None = None,
    response_error_decision: Any | None = None,
    turn_residue: TurnResidue | Any | None = None,
    previous_state: SlowState | dict[str, Any] | None = None,
    evaluated_at: datetime | str | None = None,
    persist: bool = False,
) -> SlowState:
    del user_text
    now = _coerce_datetime(evaluated_at) or datetime.now().astimezone()
    previous = _state_from_any(previous_state) or read_slow_state(root, evaluated_at=now)
    residue = turn_residue
    if residue is None:
        try:
            residue = read_turn_residue(root, at=now)
        except Exception:
            residue = None

    base = _decayed_values(previous, now=now)
    signals: list[str] = []
    fatigue = base["fatigue_load"]
    relation = base["relation_guard"]
    correction = base["correction_pressure"]
    initiative = base["initiative_dampening"]

    scene_owner = _value(scene_frame, "owner_state")
    scene_time = _value(scene_frame, "time_context")
    scene_reply = _value(scene_frame, "reply_policy")
    scene_task = _value(scene_frame, "task_mode")
    triage_lane = _value(triage_decision, "primary_lane")
    triage_reply = _value(triage_decision, "reply_policy")
    error_class = _value(response_error_decision, "error_class")

    if scene_owner == "low_energy_or_tired" or scene_time in {"after_night_shift", "recent_wake_from_rest", "rest_related"}:
        fatigue = max(fatigue, 72 if scene_time == "after_night_shift" else 62)
        initiative = max(initiative, 48)
        signals.append(f"scene_low_energy:{scene_time or scene_owner}")
    if scene_reply in {"short_direct_low_burden", "short_gentle_low_burden", "warm_low_burden"}:
        fatigue = max(fatigue, 58)
        signals.append(f"scene_reply_low_burden:{scene_reply}")
    if triage_lane == "rest_low_burden" or triage_reply in {"short_gentle_low_burden", "short_direct_progress_update"}:
        fatigue = max(fatigue, 64)
        initiative = max(initiative, 52)
        signals.append("triage_rest_low_burden")
    if triage_lane in {"relationship_boundary", "emotional_support"} or scene_task == "relational_support":
        relation = max(relation, 66)
        initiative = max(initiative, 40)
        signals.append("relation_or_emotion_context")
    if error_class in {"style_surface_failure", "overexplained_repair", "template_reply_mismatch"}:
        correction = max(correction, 78)
        relation = max(relation, 42)
        initiative = max(initiative, 62)
        signals.append(f"response_error:{error_class}")
    elif error_class in {"task_not_executed", "internal_label_leak", "unsupported_recall_claim"}:
        correction = max(correction, 58)
        initiative = max(initiative, 38)
        signals.append(f"response_error:{error_class}")

    if residue is not None and bool(getattr(residue, "active", False)):
        strength = _bounded_int(getattr(residue, "decayed_strength", 0))
        pressure = _safe_text(getattr(residue, "pressure", "")).lower()
        if pressure == "relationship":
            relation = max(relation, min(90, strength))
            initiative = max(initiative, min(70, strength // 2 + 25))
            signals.append("turn_residue:relationship")
        elif pressure == "style":
            correction = max(correction, min(90, strength))
            initiative = max(initiative, min(75, strength // 2 + 30))
            signals.append("turn_residue:style")
        elif pressure == "task":
            correction = max(correction, min(60, strength))
            signals.append("turn_residue:task")

    state = _make_state(
        updated_at=now.isoformat(),
        fatigue_load=fatigue,
        relation_guard=relation,
        correction_pressure=correction,
        initiative_dampening=initiative,
        evidence_signals=tuple(dict.fromkeys(signals or ("decayed_previous_state",))),
    )
    if persist:
        write_slow_state(root, state)
    return state


def read_slow_state(root: Path, *, evaluated_at: datetime | str | None = None) -> SlowState:
    raw = read_slow_state_payload(root, default={})
    if not raw:
        return _make_state(updated_at=_now_iso(evaluated_at))
    state = _state_from_any(raw)
    if state is None:
        return _make_state(updated_at=_now_iso(evaluated_at))
    now = _coerce_datetime(evaluated_at)
    if now is None:
        return state
    decayed = _decayed_values(state, now=now)
    return _make_state(
        updated_at=now.isoformat(),
        fatigue_load=decayed["fatigue_load"],
        relation_guard=decayed["relation_guard"],
        correction_pressure=decayed["correction_pressure"],
        initiative_dampening=decayed["initiative_dampening"],
        evidence_signals=("read_decay",),
    )


def write_slow_state(root: Path, state: SlowState) -> None:
    write_slow_state_payload(root, state.to_json_dict())


def render_slow_state_prompt_block(state: SlowState) -> str:
    lines = [
        "## Slow State Modulator",
        "purpose: allostatic slow variables; bias pacing, initiative, recall threshold, and emotion tone without creating facts.",
        f"- fatigue_load: {state.fatigue_load}",
        f"- relation_guard: {state.relation_guard}",
        f"- correction_pressure: {state.correction_pressure}",
        f"- initiative_dampening: {state.initiative_dampening}",
        f"- reply_policy: {state.reply_policy}",
        f"- initiative_policy: {state.initiative_policy}",
        f"- recall_policy: {state.recall_policy}",
        f"- emotion_policy: {state.emotion_policy}",
        f"- active_policies: {', '.join(state.active_policies) if state.active_policies else 'none'}",
        f"- evidence_signals: {', '.join(state.evidence_signals) if state.evidence_signals else 'none'}",
        "- boundary: slow state cannot create facts, override current owner text, or write stable memory.",
    ]
    if state.notes:
        lines.append("- notes: " + ", ".join(state.notes))
    return "\n".join(lines).strip()


def _make_state(
    *,
    updated_at: str,
    fatigue_load: int = 0,
    relation_guard: int = 0,
    correction_pressure: int = 0,
    initiative_dampening: int = 0,
    evidence_signals: tuple[str, ...] = (),
) -> SlowState:
    fatigue = _bounded_int(fatigue_load)
    relation = _bounded_int(relation_guard)
    correction = _bounded_int(correction_pressure)
    initiative = _bounded_int(initiative_dampening)
    policies: list[str] = []
    if fatigue >= 55:
        policies.append("low_burden_reply")
    if relation >= 55:
        policies.append("relationship_guarded_warmth")
    if correction >= 55:
        policies.append("show_correction_by_action")
    if initiative >= 55:
        policies.append("hold_optional_proactive")

    reply_policy = "steady_compact"
    if correction >= 70:
        reply_policy = "short_present_tense_no_postmortem"
    elif fatigue >= 60:
        reply_policy = "low_burden_short"
    elif relation >= 60:
        reply_policy = "warm_boundary_aware"

    initiative_policy = "normal_gated"
    if initiative >= 60 or fatigue >= 65:
        initiative_policy = "suppress_optional_proactive"
    elif relation >= 55 or correction >= 55:
        initiative_policy = "hold_until_owner_context_settles"

    recall_policy = "normal_current_turn_first"
    if fatigue >= 55:
        recall_policy = "prefer_recent_time_bound_context_keep_short"
    if correction >= 60:
        recall_policy = "prefer_recent_corrections_and_current_turn"
    if relation >= 60:
        recall_policy = "prefer_recent_relationship_residue_review_only"

    emotion_policy = "normal_shadow_bias"
    if relation >= 60:
        emotion_policy = "allow_guarded_or_warm_residue_without_fact_claim"
    if correction >= 70:
        emotion_policy = "allow_guarded_style_pressure_without_stable_rewrite"

    return SlowState(
        updated_at=updated_at,
        fatigue_load=fatigue,
        relation_guard=relation,
        correction_pressure=correction,
        initiative_dampening=initiative,
        reply_policy=reply_policy,
        initiative_policy=initiative_policy,
        recall_policy=recall_policy,
        emotion_policy=emotion_policy,
        active_policies=tuple(policies),
        evidence_signals=evidence_signals,
        notes=(
            "allostasis_slow_variable_mapping",
            "advisory_only_current_turn_wins",
            "no_private_memory_body_output",
        ),
    )


def _decayed_values(state: SlowState, *, now: datetime) -> dict[str, int]:
    updated = _coerce_datetime(state.updated_at)
    if updated is None:
        return {
            "fatigue_load": state.fatigue_load,
            "relation_guard": state.relation_guard,
            "correction_pressure": state.correction_pressure,
            "initiative_dampening": state.initiative_dampening,
        }
    elapsed_hours = max(0.0, (now - updated).total_seconds() / 3600.0)
    return {
        "fatigue_load": _decay(state.fatigue_load, elapsed_hours, FATIGUE_HALF_LIFE_HOURS),
        "relation_guard": _decay(state.relation_guard, elapsed_hours, RELATION_HALF_LIFE_HOURS),
        "correction_pressure": _decay(state.correction_pressure, elapsed_hours, CORRECTION_HALF_LIFE_HOURS),
        "initiative_dampening": _decay(state.initiative_dampening, elapsed_hours, INITIATIVE_HALF_LIFE_HOURS),
    }


def _decay(value: int, elapsed_hours: float, half_life: float) -> int:
    if value <= 0:
        return 0
    decayed = value * math.pow(0.5, elapsed_hours / half_life)
    return _bounded_int(round(decayed))


def _state_from_any(value: Any) -> SlowState | None:
    if isinstance(value, SlowState):
        return value
    if not isinstance(value, dict):
        return None
    try:
        return _make_state(
            updated_at=_safe_text(value.get("updated_at")) or datetime.now().astimezone().isoformat(),
            fatigue_load=_bounded_int(value.get("fatigue_load")),
            relation_guard=_bounded_int(value.get("relation_guard")),
            correction_pressure=_bounded_int(value.get("correction_pressure")),
            initiative_dampening=_bounded_int(value.get("initiative_dampening")),
            evidence_signals=tuple(_safe_text(item) for item in value.get("evidence_signals", []) if _safe_text(item))
            or ("loaded_previous_state",),
        )
    except Exception:
        return None


def _coerce_datetime(value: datetime | str | None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = _safe_text(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _value(obj: Any | None, key: str) -> str:
    if obj is None:
        return ""
    if isinstance(obj, dict):
        return _safe_text(obj.get(key)).strip().lower()
    return _safe_text(getattr(obj, key, "")).strip().lower()


def _bounded_int(value: Any) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = 0
    return max(0, min(100, number))


def _now_iso(value: datetime | str | None = None) -> str:
    parsed = _coerce_datetime(value)
    return (parsed or datetime.now().astimezone()).isoformat()


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)
