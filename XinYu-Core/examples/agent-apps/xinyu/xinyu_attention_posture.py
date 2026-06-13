from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_attention_posture_store import read_attention_life_event_trace_rows
from xinyu_attention_posture_store import read_attention_posture_text
from xinyu_attention_posture_store import write_attention_life_event_trace_rows
from xinyu_attention_posture_store import write_attention_posture_text
from xinyu_life_event_contract import LifeEvent, event_to_short_trace, normalize_life_event, route_life_event
from xinyu_perception_importance import build_perception_importance_report, perception_gap_signal

STATE_REL = Path("memory/context/attention_posture_state.md")
TRACE_REL = Path("memory/context/life_event_trace.jsonl")
SELF_THOUGHT_REL = Path("memory/context/self_thought_state.md")


def update_attention_posture(root: Path, event_payload: dict[str, Any], *, evaluated_at: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    evaluated_at = evaluated_at or _now_iso()
    event = normalize_life_event(event_payload)
    route = route_life_event(event)
    previous = read_attention_posture(root)
    state = _next_posture(previous, event, route, evaluated_at=evaluated_at)
    _write_attention_state(root, state)
    _append_life_event_trace(root, event)
    self_thought_written = False
    if route["route"] == "owner_private_question":
        _write_self_thought_candidate(root, event, route, evaluated_at=evaluated_at)
        self_thought_written = True
    return {
        "accepted": True,
        "event": event.to_dict(),
        "route": route,
        "attention": state,
        "self_thought_written": self_thought_written,
        "notes": route["notes"],
    }


def update_attention_from_perception_importance(
    root: Path,
    report: dict[str, Any] | None = None,
    *,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    evaluated_at = evaluated_at or _now_iso()
    perception_report = (
        report
        if isinstance(report, dict)
        else build_perception_importance_report(root, generated_at=evaluated_at)
    )
    signal = perception_gap_signal(perception_report)
    previous = read_attention_posture(root)
    gap_type = signal.get("gap_type", "none")
    if gap_type in {"", "missing", "unknown", "none", "null"}:
        return {
            "accepted": False,
            "perception_gap": signal,
            "attention": previous,
            "notes": ["no_perception_gap_to_consume"],
        }
    state = _next_posture_from_perception_gap(previous, signal, evaluated_at=evaluated_at)
    _write_attention_state(root, state)
    return {
        "accepted": True,
        "perception_gap": signal,
        "attention": state,
        "self_thought_written": False,
        "notes": ["perception_gap_consumed_by_attention_posture"],
    }


def read_attention_posture(root: Path) -> dict[str, str]:
    text = read_attention_posture_text(root / STATE_REL)
    if not text:
        return {
            "status": "missing",
            "attention_target": "none",
            "attention_mode": "available",
            "interruptibility": "normal",
            "owner_private_priority": "normal",
            "ignored_event_count": "0",
            "noted_event_count": "0",
            "last_event_id": "none",
            "last_event_type": "none",
            "last_route": "none",
            "last_proactive_reason": "none",
            "perception_gap_type": "none",
            "perception_route_hint": "none",
            "perception_attention_weight": "0",
            "perception_future_effect": "none",
            "perception_gap_bias": "none",
            "perception_gap_consumed": "false",
        }
    fields = _extract_fields(text)
    return {
        "status": fields.get("status", "active"),
        "updated_at": fields.get("updated_at", "unknown"),
        "attention_target": fields.get("attention_target", "none"),
        "attention_mode": fields.get("attention_mode", "available"),
        "interruptibility": fields.get("interruptibility", "normal"),
        "owner_private_priority": fields.get("owner_private_priority", "normal"),
        "ignored_event_count": fields.get("ignored_event_count", "0"),
        "noted_event_count": fields.get("noted_event_count", "0"),
        "last_event_id": fields.get("last_event_id", "none"),
        "last_event_type": fields.get("last_event_type", "none"),
        "last_route": fields.get("last_route", "none"),
        "last_proactive_reason": fields.get("last_proactive_reason", "none"),
        "perception_gap_type": fields.get("perception_gap_type", "none"),
        "perception_route_hint": fields.get("perception_route_hint", "none"),
        "perception_attention_weight": fields.get("perception_attention_weight", "0"),
        "perception_future_effect": fields.get("perception_future_effect", "none"),
        "perception_gap_bias": fields.get("perception_gap_bias", "none"),
        "perception_gap_consumed": fields.get("perception_gap_consumed", "false"),
    }


def _next_posture(previous: dict[str, str], event: LifeEvent, route: dict[str, Any], *, evaluated_at: str) -> dict[str, str]:
    route_name = str(route["route"])
    ignored = _int(previous.get("ignored_event_count", "0"))
    noted = _int(previous.get("noted_event_count", "0"))
    if route_name == "ignore":
        ignored += 1
    else:
        noted += 1
    if route_name == "owner_private_question":
        attention_mode = "wants_to_speak"
        interruptibility = "high_for_owner_private"
        owner_priority = "high"
        target = "owner_private"
        reason = event.summary
    elif route_name == "initiative_candidate":
        attention_mode = "holding_question"
        interruptibility = "normal"
        owner_priority = "elevated"
        target = event.event_type
        reason = event.summary
    elif route_name == "action_residue":
        attention_mode = "processing_residue"
        interruptibility = "normal"
        owner_priority = "normal"
        target = event.event_type
        reason = event.summary
    elif route_name == "memory_candidate":
        attention_mode = "noting_for_later"
        interruptibility = "normal"
        owner_priority = "normal"
        target = event.event_type
        reason = "none"
    elif route_name == "short_trace":
        attention_mode = "quietly_noted"
        interruptibility = "normal"
        owner_priority = "normal"
        target = event.event_type
        reason = "none"
    else:
        attention_mode = "available"
        interruptibility = "low"
        owner_priority = "normal"
        target = "none"
        reason = "none"
    return {
        "status": "active",
        "updated_at": evaluated_at,
        "attention_target": target,
        "attention_mode": attention_mode,
        "interruptibility": interruptibility,
        "owner_private_priority": owner_priority,
        "ignored_event_count": str(ignored),
        "noted_event_count": str(noted),
        "last_event_id": event.event_id,
        "last_event_type": event.event_type,
        "last_route": route_name,
        "last_proactive_reason": reason,
        "perception_gap_type": previous.get("perception_gap_type", "none"),
        "perception_route_hint": previous.get("perception_route_hint", "none"),
        "perception_attention_weight": previous.get("perception_attention_weight", "0"),
        "perception_future_effect": previous.get("perception_future_effect", "none"),
        "perception_gap_bias": previous.get("perception_gap_bias", "none"),
        "perception_gap_consumed": previous.get("perception_gap_consumed", "false"),
        "stable_persona_write": "blocked",
        "owner_memory_write": "blocked",
        "raw_private_body_retained": "false",
    }


def _next_posture_from_perception_gap(
    previous: dict[str, str],
    signal: dict[str, str],
    *,
    evaluated_at: str,
) -> dict[str, str]:
    gap_type = signal.get("gap_type", "none")
    noted = _int(previous.get("noted_event_count", "0")) + 1
    ignored = _int(previous.get("ignored_event_count", "0"))
    if gap_type == "owner_attention":
        attention_mode = "wants_to_speak"
        interruptibility = "high_for_owner_private"
        owner_priority = "high"
        target = "owner_private"
    elif gap_type == "repair_gap":
        attention_mode = "repair_needed"
        interruptibility = "high_for_repair"
        owner_priority = "elevated"
        target = "reply_order_or_delivery"
    elif gap_type == "maintenance_gap":
        attention_mode = "maintenance_needed"
        interruptibility = "normal"
        owner_priority = "normal"
        target = "runtime_or_source_state"
    elif gap_type == "boundary_gap":
        attention_mode = "boundary_holding"
        interruptibility = "low"
        owner_priority = "normal"
        target = "external_or_group_boundary"
    elif gap_type == "action_residue":
        attention_mode = "processing_residue"
        interruptibility = "normal"
        owner_priority = "normal"
        target = "action_feedback"
    elif gap_type == "sensory_observation":
        attention_mode = "observation_noted"
        interruptibility = "normal"
        owner_priority = "normal"
        target = "sensory_observation"
    else:
        attention_mode = "quietly_noted"
        interruptibility = "normal"
        owner_priority = "normal"
        target = "perception_event"

    return {
        "status": "active",
        "updated_at": evaluated_at,
        "attention_target": target,
        "attention_mode": attention_mode,
        "interruptibility": interruptibility,
        "owner_private_priority": owner_priority,
        "ignored_event_count": str(ignored),
        "noted_event_count": str(noted),
        "last_event_id": signal.get("event_id", "none"),
        "last_event_type": "perception_importance",
        "last_route": signal.get("route_hint", "none"),
        "last_proactive_reason": signal.get("future_effect", "none"),
        "perception_gap_type": gap_type,
        "perception_route_hint": signal.get("route_hint", "none"),
        "perception_attention_weight": signal.get("attention_weight", "0"),
        "perception_future_effect": signal.get("future_effect", "none"),
        "perception_gap_bias": signal.get("bias", "none"),
        "perception_gap_consumed": "true",
        "stable_persona_write": "blocked",
        "owner_memory_write": "blocked",
        "raw_private_body_retained": "false",
    }


def _write_attention_state(root: Path, state: dict[str, str]) -> None:
    text = f"""---
title: Attention Posture State
memory_type: attention_posture_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_attention_posture
updated_at: {state['updated_at']}
status: active
tags: [attention, initiative, life_event, boundary]
---

# Attention Posture State

## Current Posture
- status: {state['status']}
- updated_at: {state['updated_at']}
- attention_target: {state['attention_target']}
- attention_mode: {state['attention_mode']}
- interruptibility: {state['interruptibility']}
- owner_private_priority: {state['owner_private_priority']}
- ignored_event_count: {state['ignored_event_count']}
- noted_event_count: {state['noted_event_count']}
- last_event_id: {state['last_event_id']}
- last_event_type: {state['last_event_type']}
- last_route: {state['last_route']}
- last_proactive_reason: {state['last_proactive_reason']}
- perception_gap_type: {state.get('perception_gap_type', 'none')}
- perception_route_hint: {state.get('perception_route_hint', 'none')}
- perception_attention_weight: {state.get('perception_attention_weight', '0')}
- perception_future_effect: {state.get('perception_future_effect', 'none')}
- perception_gap_bias: {state.get('perception_gap_bias', 'none')}
- perception_gap_consumed: {state.get('perception_gap_consumed', 'false')}

## Boundaries
- stable_persona_write: {state['stable_persona_write']}
- owner_memory_write: {state['owner_memory_write']}
- raw_private_body_retained: {state['raw_private_body_retained']}
- device_capture: disabled
- network_access: disabled
"""
    write_attention_posture_text(root / STATE_REL, text)


def _append_life_event_trace(root: Path, event: LifeEvent) -> None:
    path = root / TRACE_REL
    rows = read_attention_life_event_trace_rows(path)
    trace = event_to_short_trace(event)
    rows = [row for row in rows if row.get("event_id") != event.event_id]
    rows.append(trace)
    write_attention_life_event_trace_rows(path, rows)


def _write_self_thought_candidate(root: Path, event: LifeEvent, route: dict[str, Any], *, evaluated_at: str) -> None:
    text = f"""---
title: Self Thought State
memory_type: self_thought_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_attention_posture
updated_at: {evaluated_at}
status: active
tags: [self_thought, life_event, proactive]
---

# Self Thought State

## Latest Pass
- pass_id: lifeevent-{event.event_id}
- focus_kind: life_event_question
- focus_label: {event.event_type}
- evidence_label: {event.summary}
- evidence_hash: {event.evidence_hash}

## Inner Intention
- intention_id: intent-{event.event_id}
- intention: ask_owner

## Request Candidate
- candidate_enabled: true
- concrete_question: {event.summary}
- requested_action: owner_answer
- why_now: life event routed to owner_private_question after attention gate
- after_owner_replies: update the life-event thread and continue only if owner replies

## Boundaries
- source_route: {route['route']}
- stable_persona_write: blocked
- owner_memory_write: blocked_without_owner_reply_and_memory_gates
- raw_private_body_retained: false
"""
    write_attention_posture_text(root / SELF_THOUGHT_REL, text)


def _extract_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update XinYu attention posture from a sanitized life event JSON object.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--event-json", required=True)
    parser.add_argument("--evaluated-at", default=None)
    args = parser.parse_args(argv)
    payload = json.loads(args.event_json)
    if not isinstance(payload, dict):
        raise SystemExit("event-json must be an object")
    result = update_attention_posture(args.root, payload, evaluated_at=args.evaluated_at)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
