from __future__ import annotations

import json
import py_compile
from pathlib import Path

from xinyu_dream_engine import LOW_TEMP_PLAN_GBNF, build_dream_engine_result, parse_low_temp_plan


def _input_window() -> dict:
    return {
        "suppressed_residue_count": 8,
        "memory_event_count": 6,
        "proactive_item_count": 0,
        "recent_turn_count": 0,
        "self_choice": {
            "affect_band": {"urge": "high", "closure": "withdrawn", "fatigue": "tired"},
            "physical_cues": ["waking_from_hibernation"],
            "hibernation": {
                "pending_wake_residue": True,
                "first_metabolism_after_hibernation": True,
            },
        },
    }


def main() -> int:
    failures: list[str] = []
    if "dominant_fragments" not in LOW_TEMP_PLAN_GBNF or "physical_anchors" not in LOW_TEMP_PLAN_GBNF:
        failures.append("low-temp GBNF missing required fields")

    deterministic = build_dream_engine_result(input_window=_input_window())
    payload = deterministic.public_dict()
    if payload.get("provider") != "deterministic":
        failures.append(f"default provider should be deterministic: {payload}")
    if payload.get("validator", {}).get("accepted") is not True:
        failures.append(f"deterministic dream lines should validate: {payload.get('validator')}")
    candidates = payload.get("candidate_fragments") if isinstance(payload.get("candidate_fragments"), list) else []
    if not any(item.get("source") == "hibernation_wake" for item in candidates if isinstance(item, dict)):
        failures.append(f"hibernation candidate missing: {candidates}")

    valid_json = json.dumps(
        {
            "dominant_fragments": [
                {"label": "unsent_residue", "source": "suppressed_residue", "weight": 0.77},
                {"label": "fan_low", "source": "physical_sensor", "weight": 0.4},
            ],
            "physical_anchors": ["fan", "cursor"],
            "unclosed_actions": ["unsent stacked", "did not fall"],
            "notes": ["local low-temp compressed"],
        },
        ensure_ascii=False,
    )
    local = build_dream_engine_result(input_window=_input_window(), engine_mode="local", low_temp_output=valid_json)
    local_payload = local.public_dict()
    if local_payload.get("provider") != "local_grammar":
        failures.append(f"valid low-temp JSON should use local grammar provider: {local_payload}")
    plan = local_payload.get("dream_plan") if isinstance(local_payload.get("dream_plan"), dict) else {}
    dominant = plan.get("dominant_fragments") if isinstance(plan.get("dominant_fragments"), list) else []
    if len(dominant) != 2:
        failures.append(f"validated local plan did not preserve dominant fragments: {plan}")

    unknown_json = json.dumps(
        {
            "dominant_fragments": [{"label": "fan_low", "source": "physical_sensor", "weight": 0.4}],
            "physical_anchors": ["fan"],
            "unclosed_actions": ["unsent stacked"],
            "notes": [],
            "extra": "model chatter",
        },
        ensure_ascii=False,
    )
    fallback = build_dream_engine_result(input_window=_input_window(), engine_mode="local", low_temp_output=unknown_json)
    fallback_payload = fallback.public_dict()
    if fallback_payload.get("provider") != "deterministic":
        failures.append(f"unknown low-temp field should force deterministic fallback: {fallback_payload}")
    if not any("low_temp_unknown_fields" in note for note in fallback_payload.get("notes", [])):
        failures.append(f"fallback notes should record unknown fields: {fallback_payload.get('notes')}")

    bad = build_dream_engine_result(input_window=_input_window(), engine_mode="local", low_temp_output="not json")
    if bad.public_dict().get("provider") != "deterministic":
        failures.append("invalid low-temp JSON should not cross trust boundary")

    text = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("urge_to_express", "self_closure", "baseline_urge", "baseline_closure"):
        if forbidden in text:
            failures.append(f"dream engine leaked raw hidden field {forbidden}")

    try:
        py_compile.compile(str(Path(__file__).resolve().parent / "xinyu_dream_engine.py"), doraise=True)
    except py_compile.PyCompileError as exc:
        failures.append(f"py_compile failed for xinyu_dream_engine.py: {exc}")

    if failures:
        print("XinYu dream engine smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu dream engine smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
