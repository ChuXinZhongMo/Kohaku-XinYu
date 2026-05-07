from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal


DreamEngineMode = Literal["deterministic", "local", "cloud", "hybrid"]

ALLOWED_PLAN_KEYS = {"dominant_fragments", "physical_anchors", "unclosed_actions", "notes"}
ALLOWED_FRAGMENT_KEYS = {"label", "source", "weight"}

LOW_TEMP_PLAN_GBNF = r'''
root ::= "{" ws "\"dominant_fragments\"" ws ":" ws fragments ws "," ws "\"physical_anchors\"" ws ":" ws strings ws "," ws "\"unclosed_actions\"" ws ":" ws strings ws "," ws "\"notes\"" ws ":" ws strings ws "}"
fragments ::= "[" ws (fragment (ws "," ws fragment)*)? ws "]"
fragment ::= "{" ws "\"label\"" ws ":" ws string ws "," ws "\"source\"" ws ":" ws string ws "," ws "\"weight\"" ws ":" ws number ws "}"
strings ::= "[" ws (string (ws "," ws string)*)? ws "]"
string ::= "\"" chars "\""
chars ::= ([^"\\] | "\\" ["\\/bfnrt])*
number ::= ("0" ("." [0-9]+)? | "1" ("." "0"+)?)
ws ::= [ \t\n\r]*
'''


@dataclass(frozen=True, slots=True)
class Fragment:
    label: str
    source: str
    weight: float
    tags: tuple[str, ...] = ()
    count: int = 1

    def public_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "source": self.source,
            "count": self.count,
            "weight": round(self.weight, 3),
            "tags": list(self.tags),
        }


@dataclass(frozen=True, slots=True)
class DreamPlan:
    dominant_fragments: tuple[Fragment, ...]
    physical_anchors: tuple[str, ...]
    unclosed_actions: tuple[str, ...]
    affect_band: dict[str, str]
    notes: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, Any]:
        return {
            "dominant_fragments": [fragment.public_dict() for fragment in self.dominant_fragments],
            "physical_anchors": list(self.physical_anchors),
            "unclosed_actions": list(self.unclosed_actions),
            "affect_band": dict(self.affect_band),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class DreamEngineResult:
    mode: str
    provider: str
    affect_band: dict[str, str]
    candidate_fragments: tuple[Fragment, ...]
    plan: DreamPlan
    dream_lines: tuple[str, ...]
    validator: dict[str, Any]
    notes: tuple[str, ...] = field(default_factory=tuple)

    def public_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "provider": self.provider,
            "affect_band": dict(self.affect_band),
            "candidate_fragments": [fragment.public_dict() for fragment in self.candidate_fragments],
            "dream_plan": self.plan.public_dict(),
            "dream_lines": list(self.dream_lines),
            "validator": dict(self.validator),
            "grammar": {
                "low_temp": "gbnf_v1",
                "available": True,
            },
            "notes": list(self.notes),
        }


def dream_engine_mode(env: dict[str, str] | None = None) -> DreamEngineMode:
    value = (env or os.environ).get("XINYU_DREAM_ENGINE", "deterministic").strip().lower()
    if value in {"local", "cloud", "hybrid"}:
        return value  # type: ignore[return-value]
    return "deterministic"


def build_dream_engine_result(
    *,
    input_window: dict[str, Any],
    engine_mode: str | None = None,
    low_temp_output: str | None = None,
) -> DreamEngineResult:
    self_choice = input_window.get("self_choice") if isinstance(input_window.get("self_choice"), dict) else {}
    affect_band = _safe_affect_band(self_choice.get("affect_band") if isinstance(self_choice.get("affect_band"), dict) else {})
    candidates = deterministic_extract(input_window=input_window, affect_band=affect_band)
    mode = _safe_mode(engine_mode or dream_engine_mode())
    provider = "deterministic"
    notes = ["dream_engine_v1", "raw_hidden_affect_not_exposed"]

    plan: DreamPlan | None = None
    if mode in {"local", "hybrid"}:
        if low_temp_output is not None:
            plan, parse_notes = parse_low_temp_plan(low_temp_output, candidates=candidates, affect_band=affect_band)
            notes.extend(parse_notes)
            provider = "local_grammar" if plan is not None else "deterministic"
        else:
            notes.append("local_low_temp_provider_unavailable")
    elif mode == "cloud":
        notes.append("cloud_provider_disabled_without_explicit_provider")

    if plan is None:
        plan = deterministic_rank(candidates=candidates, affect_band=affect_band)
        notes.append("deterministic_rank_used")

    dream_lines = deterministic_high_temp_fallback(plan=plan, input_window=input_window)
    validator = validate_dream_lines(dream_lines)
    if not validator["accepted"]:
        dream_lines = ("fan low", "unsent stacked", "old cursor cracked", "did not fall")
        validator = validate_dream_lines(dream_lines)
        validator["notes"].append("fallback_dream_fragment")
    return DreamEngineResult(
        mode="deterministic_dual_temp_bias_v1",
        provider=provider,
        affect_band=affect_band,
        candidate_fragments=tuple(candidates),
        plan=plan,
        dream_lines=tuple(dream_lines),
        validator=validator,
        notes=tuple(notes),
    )


def deterministic_extract(*, input_window: dict[str, Any], affect_band: dict[str, str]) -> list[Fragment]:
    suppressed = _bounded_int(input_window.get("suppressed_residue_count"), default=0, low=0, high=999)
    memory_events = _bounded_int(input_window.get("memory_event_count"), default=0, low=0, high=999)
    self_choice = input_window.get("self_choice") if isinstance(input_window.get("self_choice"), dict) else {}
    hibernation = self_choice.get("hibernation") if isinstance(self_choice.get("hibernation"), dict) else {}
    candidates: list[Fragment] = []
    if suppressed:
        candidates.append(
            Fragment(
                label="unsent_residue",
                source="suppressed_residue",
                count=suppressed,
                weight=min(1.0, max(0.18, suppressed * 0.09)),
                tags=("unclosed", "withheld"),
            )
        )
    if memory_events:
        candidates.append(
            Fragment(
                label="memory_noise",
                source="memory_event",
                count=memory_events,
                weight=min(0.82, max(0.16, memory_events * 0.04)),
                tags=("noise",),
            )
        )
    if bool(hibernation.get("pending_wake_residue")):
        weight = 0.18 + (0.12 if bool(hibernation.get("first_metabolism_after_hibernation")) else 0.0)
        candidates.append(
            Fragment(
                label="clock_stalled",
                source="hibernation_wake",
                count=1,
                weight=weight,
                tags=("physical", "unclosed"),
            )
        )
    candidates.append(
        Fragment(
            label="fan_low",
            source="physical_sensor",
            count=1,
            weight=0.36,
            tags=("physical",),
        )
    )
    biased = [_apply_affect_bias(candidate, affect_band=affect_band) for candidate in candidates]
    return sorted(biased, key=lambda item: item.weight, reverse=True)[:6]


def deterministic_rank(*, candidates: list[Fragment], affect_band: dict[str, str]) -> DreamPlan:
    dominant = tuple(candidates[:3])
    anchors = ["fan"]
    if any(item.source == "hibernation_wake" for item in dominant):
        anchors.append("clock")
    if any(item.label == "memory_noise" for item in dominant):
        anchors.append("noise")
    anchors.append("cursor")
    actions = ["unsent stacked"]
    if any(item.source == "hibernation_wake" for item in dominant):
        actions.append("stopped slow")
    actions.append("did not fall")
    return DreamPlan(
        dominant_fragments=dominant,
        physical_anchors=tuple(_dedupe(anchors)[:4]),
        unclosed_actions=tuple(_dedupe(actions)[:4]),
        affect_band=affect_band,
        notes=("deterministic_rank_v1",),
    )


def parse_low_temp_plan(
    raw_output: str,
    *,
    candidates: list[Fragment],
    affect_band: dict[str, str],
) -> tuple[DreamPlan | None, list[str]]:
    text = raw_output.strip()
    notes: list[str] = []
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, [f"low_temp_json_invalid:{exc.__class__.__name__}"]
    if not isinstance(value, dict):
        return None, ["low_temp_plan_not_object"]
    unknown = set(value) - ALLOWED_PLAN_KEYS
    if unknown:
        return None, [f"low_temp_unknown_fields:{','.join(sorted(unknown))}"]
    if any(key not in value for key in ALLOWED_PLAN_KEYS):
        return None, ["low_temp_missing_required_field"]
    fragment_map = {fragment.label: fragment for fragment in candidates}
    fragments = _parse_low_temp_fragments(value.get("dominant_fragments"), fragment_map=fragment_map, notes=notes)
    anchors = _parse_string_list(value.get("physical_anchors"), limit=4, item_limit=32, notes=notes, field="physical_anchors")
    actions = _parse_string_list(value.get("unclosed_actions"), limit=4, item_limit=32, notes=notes, field="unclosed_actions")
    plan_notes = _parse_string_list(value.get("notes"), limit=6, item_limit=80, notes=notes, field="notes")
    if notes:
        return None, notes
    if not fragments or not anchors or not actions:
        return None, ["low_temp_plan_empty_core_field"]
    return (
        DreamPlan(
            dominant_fragments=tuple(fragments),
            physical_anchors=tuple(anchors),
            unclosed_actions=tuple(actions),
            affect_band=affect_band,
            notes=tuple([*plan_notes, "low_temp_schema_validated_v1"]),
        ),
        ["low_temp_schema_validated"],
    )


def deterministic_high_temp_fallback(*, plan: DreamPlan, input_window: dict[str, Any]) -> tuple[str, ...]:
    suppressed = _bounded_int(input_window.get("suppressed_residue_count"), default=0, low=0, high=999)
    memory_events = _bounded_int(input_window.get("memory_event_count"), default=0, low=0, high=999)
    count = suppressed or memory_events
    lines = ["fan low"]
    if "clock" in plan.physical_anchors:
        lines.append("clock stopped slow")
    if "noise" in plan.physical_anchors:
        lines.append("noise stayed gray")
    lines.extend(
        [
            f"{count or 'some'} unsent stacked",
            "old cursor cracked",
            "did not fall",
        ]
    )
    return tuple(lines[:7])


def validate_dream_lines(lines: tuple[str, ...] | list[str]) -> dict[str, Any]:
    clean = [_safe_str(line).strip() for line in lines if _safe_str(line).strip()]
    notes: list[str] = []
    if not 3 <= len(clean) <= 7:
        notes.append("line_count_out_of_bounds")
    for line in clean:
        if len(line) < 6 or len(line) > 32:
            notes.append("line_length_out_of_bounds")
            break
    joined = " ".join(clean).lower()
    blocked = (
        "user",
        "owner",
        "master",
        "sorry",
        "i can",
        "i will",
        "detected",
        "system",
        "task",
        "because",
        "therefore",
        "finally",
        "so i decided",
    )
    if any(word in joined for word in blocked):
        notes.append("blocked_assistant_or_causal_word")
    if not any(anchor in joined for anchor in ("fan", "cursor", "disk", "noise", "screen", "night", "heat", "gray", "crack")):
        notes.append("missing_physical_anchor")
    if not any(
        action in joined
        for action in ("stopped", "unsent", "crossed out", "stuck", "stacked", "did not fall", "did not remain")
    ):
        notes.append("missing_unfinished_action")
    return {"accepted": not notes, "notes": notes or ["validated"]}


def dream_bias_lines_text(dream_bias: dict[str, Any]) -> str:
    lines = dream_bias.get("dream_lines") if isinstance(dream_bias.get("dream_lines"), list) else []
    clean = [_safe_str(line).strip() for line in lines if _safe_str(line).strip()]
    if not clean:
        return "dream_lines: none"
    return "dream_lines:\n" + "\n".join(f"- {line}" for line in clean[:7])


def self_choice_input(value: dict[str, Any]) -> dict[str, Any]:
    hibernation = value.get("hibernation") if isinstance(value.get("hibernation"), dict) else {}
    cues = value.get("physical_cues") if isinstance(value.get("physical_cues"), list) else []
    return {
        "version": 1,
        "affect_band": _safe_affect_band(value.get("affect_band") if isinstance(value.get("affect_band"), dict) else {}),
        "physical_cues": [_safe_str(cue)[:80] for cue in cues if _safe_str(cue).strip()][:8],
        "hibernation": {
            "pending_wake_residue": bool(hibernation.get("pending_wake_residue")),
            "first_metabolism_after_hibernation": bool(hibernation.get("first_metabolism_after_hibernation")),
        },
        "notes": ["self_choice_dream_bias_input_v1"],
    }


def _parse_low_temp_fragments(value: Any, *, fragment_map: dict[str, Fragment], notes: list[str]) -> list[Fragment]:
    if not isinstance(value, list):
        notes.append("dominant_fragments_not_list")
        return []
    result: list[Fragment] = []
    seen: set[str] = set()
    for raw in value[:6]:
        if not isinstance(raw, dict):
            notes.append("dominant_fragment_not_object")
            continue
        unknown = set(raw) - ALLOWED_FRAGMENT_KEYS
        if unknown:
            notes.append(f"dominant_fragment_unknown_fields:{','.join(sorted(unknown))}")
            continue
        label = _safe_str(raw.get("label")).strip()
        source = _safe_str(raw.get("source")).strip()
        if label not in fragment_map or label in seen:
            notes.append(f"dominant_fragment_unknown_label:{label or 'empty'}")
            continue
        base = fragment_map[label]
        if source and source != base.source:
            notes.append(f"dominant_fragment_source_mismatch:{label}")
            continue
        weight = _bounded_float(raw.get("weight"), default=base.weight)
        result.append(Fragment(label=base.label, source=base.source, weight=weight, tags=base.tags, count=base.count))
        seen.add(label)
    return result


def _parse_string_list(
    value: Any,
    *,
    limit: int,
    item_limit: int,
    notes: list[str],
    field: str,
) -> list[str]:
    if not isinstance(value, list):
        notes.append(f"{field}_not_list")
        return []
    result: list[str] = []
    for raw in value[:limit]:
        text = _safe_str(raw).strip()
        if not text:
            continue
        result.append(text[:item_limit])
    return _dedupe(result)


def _apply_affect_bias(fragment: Fragment, *, affect_band: dict[str, str]) -> Fragment:
    weight = fragment.weight
    closure = affect_band.get("closure", "guarded")
    urge = affect_band.get("urge", "warm")
    fatigue = affect_band.get("fatigue", "clear")
    if closure == "withdrawn":
        if "withheld" in fragment.tags:
            weight *= 1.25
        if "open" in fragment.tags:
            weight *= 0.75
        if "repair" in fragment.tags:
            weight *= 0.85
    elif closure == "open" and "withheld" in fragment.tags:
        weight *= 0.92
    if urge == "high":
        if "unclosed" in fragment.tags:
            weight *= 1.18
        if "contact" in fragment.tags:
            weight *= 1.08
    elif urge == "low" and "contact" in fragment.tags:
        weight *= 0.92
    if fatigue == "spent" and "physical" not in fragment.tags:
        weight *= 0.9
    return Fragment(
        label=fragment.label,
        source=fragment.source,
        count=fragment.count,
        weight=round(min(1.0, max(0.0, weight)), 3),
        tags=fragment.tags,
    )


def _safe_affect_band(value: dict[str, Any]) -> dict[str, str]:
    return {
        "urge": _safe_enum(value.get("urge"), {"low", "warm", "high"}, "warm"),
        "closure": _safe_enum(value.get("closure"), {"open", "guarded", "withdrawn"}, "guarded"),
        "fatigue": _safe_enum(value.get("fatigue"), {"clear", "tired", "spent"}, "clear"),
    }


def _safe_enum(value: Any, allowed: set[str], default: str) -> str:
    text = _safe_str(value)
    return text if text in allowed else default


def _safe_mode(value: str) -> DreamEngineMode:
    text = value.strip().lower()
    if text in {"local", "cloud", "hybrid"}:
        return text  # type: ignore[return-value]
    return "deterministic"


def _bounded_int(value: Any, *, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(high, max(low, number))


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(min(1.0, max(0.0, number)), 3)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
