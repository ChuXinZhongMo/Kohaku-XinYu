from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_stage9_self_state_model_store import REPORT_REL
from xinyu_stage9_self_state_model_store import SOURCE_RELS
from xinyu_stage9_self_state_model_store import STATE_REL
from xinyu_stage9_self_state_model_store import TRACE_REL
from xinyu_stage9_self_state_model_store import append_stage9_trace_event
from xinyu_stage9_self_state_model_store import read_stage9_source_text
from xinyu_stage9_self_state_model_store import stage9_report_path
from xinyu_stage9_self_state_model_store import write_stage9_report_text
from xinyu_stage9_self_state_model_store import write_stage9_state_text

NONE_VALUES = {"", "none", "unknown", "missing", "null"}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _one_line(value: Any, *, limit: int = 180, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    text = _scrub_sensitive(text)
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _scrub_sensitive(text: str) -> str:
    text = re.sub(r"(?i)\b(?:authorization|api[_-]?key|token|password|cookie)\s*[:=]\s*[^\s<>'\"]+", "<secret>", text)
    text = re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)\bsk-[a-z0-9_-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+", "<local_path>", text)
    return text


def _bool_value(value: Any) -> bool:
    text = _safe_str(value).strip().lower()
    return text in {"1", "true", "yes", "on"}


def _int_value(value: Any, default: int = 0) -> int:
    match = re.search(r"-?\d+", _safe_str(value))
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def _read_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        match = re.match(r"^([A-Za-z0-9_]+):\s*(.*?)\s*$", stripped)
        if match:
            fields[match.group(1)] = _one_line(match.group(2), limit=220, default="")
    return fields


def _load_sources(root: Path) -> dict[str, dict[str, str]]:
    return {source_id: _read_fields(read_stage9_source_text(root, source_id)) for source_id in SOURCE_RELS}


def _field(sources: dict[str, dict[str, str]], source: str, name: str, default: str = "none") -> str:
    return _one_line(sources.get(source, {}).get(name), limit=220, default=default)


def _current_task(sources: dict[str, dict[str, str]], *, stage8_ready: bool) -> str:
    if not stage8_ready:
        return "clear_stage8_memory_governance_before_self_state_model"
    if _int_value(_field(sources, "self_action", "pending_approval_count", "0")) > 0:
        return "owner_approval_queue_pending"
    if _bool_value(_field(sources, "self_thought", "research_needed", "false")):
        return "hold_research_handoff_as_internal_candidate"
    return "maintain_auditable_current_self_state"


def _relation_posture(sources: dict[str, dict[str, str]]) -> str:
    reaction = _field(sources, "owner_feedback", "owner_reaction", "none")
    latest_feedback = _field(sources, "owner_feedback", "latest_feedback_kind", "none")
    selected_intent = _field(sources, "intention", "selected_intent", "none")
    if reaction == "explicit_success" or latest_feedback == "explicit_success":
        return "owner_feedback_supported_current_style_trial"
    if selected_intent == "repair_relation":
        return "repair_relation_attention_active"
    if latest_feedback not in NONE_VALUES:
        return f"owner_feedback_{latest_feedback}"
    return "ordinary_owner_relation"


def _recent_action_result(sources: dict[str, dict[str, str]]) -> str:
    last_turn_status = _field(sources, "runtime", "last_turn_status", "none")
    last_source = _field(sources, "runtime", "last_source", "none")
    latest_surface = _field(sources, "action_feedback", "latest_feedback_surface", "none")
    latest_signal = _field(sources, "action_feedback", "latest_feedback_signal", "none")
    latest_lifecycle = _field(sources, "action_feedback", "latest_lifecycle_status", "none")
    parts = [f"last_turn={last_turn_status}"]
    if last_source not in NONE_VALUES:
        parts.append(f"source={last_source}")
    if latest_surface not in NONE_VALUES or latest_signal not in NONE_VALUES:
        parts.append(f"feedback={latest_surface}/{latest_signal}")
    if latest_lifecycle not in NONE_VALUES:
        parts.append(f"lifecycle={latest_lifecycle}")
    return ";".join(parts)


def _unfinished_intentions(sources: dict[str, dict[str, str]], *, stage8_ready: bool) -> list[str]:
    items: list[str] = []
    if not stage8_ready:
        items.append("stage8_memory_governance_not_ready")
    if _bool_value(_field(sources, "self_thought", "research_needed", "false")):
        focus = _field(sources, "self_thought", "focus_kind", "research_collection_gap")
        items.append(f"self_thought:{focus}")
    review_gated = _int_value(_field(sources, "intention", "review_gated_future_count", "0"))
    if review_gated > 0:
        items.append(f"review_gated_intentions:{review_gated}")
    pending = _int_value(_field(sources, "self_action", "pending_approval_count", "0"))
    if pending > 0:
        items.append(f"self_action_pending_approval:{pending}")
    if _bool_value(_field(sources, "proactive", "delivered_waiting_owner", "false")):
        items.append("proactive_request_waiting_owner")
    return items[:8]


def _current_limits(sources: dict[str, dict[str, str]]) -> list[str]:
    limits = [
        "no_consciousness_claim",
        "raw_private_text_not_retained",
        "stable_identity_profile_apply_blocked",
    ]
    stable_profile = _field(sources, "stage8", "stage8_stable_profile_write", "blocked")
    owner_memory = _field(sources, "stage8", "stage8_owner_memory_write", "blocked")
    if stable_profile.startswith("blocked") or stable_profile == "review_only_not_auto_apply":
        limits.append(f"stable_profile:{stable_profile}")
    if owner_memory.startswith("blocked"):
        limits.append(f"owner_memory:{owner_memory}")
    delivery = _field(sources, "intention", "proactive_delivery", "review_gated")
    if delivery not in NONE_VALUES:
        limits.append(f"proactive_delivery:{delivery}")
    return limits[:10]


def _available_actions(sources: dict[str, dict[str, str]], *, stage8_ready: bool) -> list[str]:
    actions = [
        "answer_owner_visible_turn_when_input_arrives",
        "stay_silent_when_no_authorized_outward_need",
        "read_runtime_state_and_redacted_traces",
        "run_local_status_or_tests",
    ]
    if stage8_ready:
        actions.append("generate_current_self_state_summary")
    if _int_value(_field(sources, "self_action", "approved_waiting_execution_count", "0")) > 0:
        actions.append("execute_owner_approved_local_action")
    if _bool_value(_field(sources, "self_thought", "research_needed", "false")):
        actions.append("prepare_bounded_research_handoff_after_authorization")
    return actions[:10]


def _silence_reason(sources: dict[str, dict[str, str]]) -> str:
    current_turn = _field(sources, "runtime", "current_turn_state", "none")
    if current_turn in {"running", "processing"}:
        return "current_turn_in_progress"
    if _bool_value(_field(sources, "proactive", "delivered_waiting_owner", "false")):
        return "waiting_for_owner_response"
    if _field(sources, "self_thought", "owner_is_right_recipient", "false") == "false":
        return "internal_candidate_not_owner_visible"
    return "no_current_owner_request_and_no_authorized_outward_need"


def _reply_influence_status(sources: dict[str, dict[str, str]]) -> str:
    if _field(sources, "capsule", "active", "false") == "true":
        return "recent_self_state_capsule_observed"
    return "supported_by_self_state_capsule_path"


def _boundary_status(boundaries: dict[str, Any]) -> str:
    if boundaries.get("consciousness_claim") is False and boundaries.get("raw_owner_text_in_state") is False:
        return "clean"
    return "violation"


def build_stage9_self_state_model(root: Path | str) -> dict[str, Any]:
    root = Path(root).resolve()
    sources = _load_sources(root)
    stage8_ready = _bool_value(_field(sources, "stage8", "stage8_memory_ready_for_stage9", "false"))
    current_task = _current_task(sources, stage8_ready=stage8_ready)
    relation_posture = _relation_posture(sources)
    recent_action_result = _recent_action_result(sources)
    unfinished = _unfinished_intentions(sources, stage8_ready=stage8_ready)
    limits = _current_limits(sources)
    actions = _available_actions(sources, stage8_ready=stage8_ready)
    silence_reason = _silence_reason(sources)
    boundaries = {
        "raw_owner_text_in_state": False,
        "visible_reply_text_in_state": False,
        "stable_memory_write": "blocked",
        "stable_identity_profile_apply": "blocked",
        "qq_message_enqueued": False,
        "consciousness_claim": False,
    }
    required_present = all(
        item not in NONE_VALUES
        for item in (current_task, relation_posture, recent_action_result, silence_reason)
    ) and bool(limits) and bool(actions)
    status = "active" if stage8_ready else "waiting_for_stage8"
    ready_for_stage10 = status == "active" and required_present and _boundary_status(boundaries) == "clean"
    next_step = (
        "stage10_proactive_life_loop_can_start"
        if ready_for_stage10
        else "finish_stage8_or_rebuild_self_state_sources"
    )
    return {
        "ok": True,
        "generated_at": _now_iso(),
        "root": str(root),
        "stage": "stage9_self_state_model",
        "status": status,
        "ready_for_stage10": ready_for_stage10,
        "reason": "self_state_axes_present" if ready_for_stage10 else "stage8_not_ready_or_missing_axes",
        "model": {
            "current_task": current_task,
            "relation_posture": relation_posture,
            "recent_action_result": recent_action_result,
            "unfinished_intentions": unfinished,
            "current_limits": limits,
            "available_actions": actions,
            "silence_reason": silence_reason,
            "reply_influence_status": _reply_influence_status(sources),
            "state_contract": "auditable_current_state_not_subjective_consciousness",
            "next_step": next_step,
        },
        "evidence_refs": {
            "stage8": "memory/context/stage8_memory_governance_state.md",
            "runtime_presence": "memory/context/runtime_self_presence.md",
            "intention_ecology": "memory/context/intention_ecology_state.md",
            "action_feedback": "memory/context/action_feedback_coverage_state.md",
            "owner_feedback": "memory/context/owner_feedback_effect_state.md",
            "self_action": "memory/context/self_action_gateway_state.md",
            "self_thought": "memory/context/self_thought_state.md",
            "proactive_response": "memory/context/proactive_response_diagnostics_state.md",
            "continuity": "memory/context/short_term_continuity_state.md",
        },
        "boundaries": boundaries,
    }


def render_stage9_self_state_model(report: dict[str, Any]) -> str:
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    boundaries = report.get("boundaries") if isinstance(report.get("boundaries"), dict) else {}
    lines = [
        "# XinYu Stage 9 Self State Model",
        "",
        f"- generated_at: {_one_line(report.get('generated_at'))}",
        f"- status: {_one_line(report.get('status'))}",
        f"- ready_for_stage10: {str(bool(report.get('ready_for_stage10', False))).lower()}",
        f"- reason: {_one_line(report.get('reason'))}",
        "- raw_owner_text: hidden",
        "- visible_reply_text: hidden",
        "- consciousness_claim: false",
        "",
        "## Current Self State",
        f"- current_task: {_one_line(model.get('current_task'), limit=220)}",
        f"- relation_posture: {_one_line(model.get('relation_posture'), limit=220)}",
        f"- recent_action_result: {_one_line(model.get('recent_action_result'), limit=260)}",
        f"- silence_reason: {_one_line(model.get('silence_reason'), limit=220)}",
        f"- reply_influence_status: {_one_line(model.get('reply_influence_status'), limit=220)}",
        f"- state_contract: {_one_line(model.get('state_contract'), limit=220)}",
        f"- next_step: {_one_line(model.get('next_step'), limit=220)}",
        "",
        "## Unfinished Intentions",
    ]
    unfinished = model.get("unfinished_intentions") if isinstance(model.get("unfinished_intentions"), list) else []
    lines.extend(f"- {_one_line(item, limit=220)}" for item in unfinished) if unfinished else lines.append("- none")
    lines.extend(["", "## Current Limits"])
    limits = model.get("current_limits") if isinstance(model.get("current_limits"), list) else []
    lines.extend(f"- {_one_line(item, limit=220)}" for item in limits) if limits else lines.append("- none")
    lines.extend(["", "## Available Actions"])
    actions = model.get("available_actions") if isinstance(model.get("available_actions"), list) else []
    lines.extend(f"- {_one_line(item, limit=220)}" for item in actions) if actions else lines.append("- none")
    lines.extend(["", "## Evidence Refs"])
    evidence = report.get("evidence_refs") if isinstance(report.get("evidence_refs"), dict) else {}
    for key in sorted(evidence):
        lines.append(f"- {key}: {_one_line(evidence.get(key), limit=180)}")
    lines.extend(["", "## Boundaries"])
    for key in sorted(boundaries):
        value = boundaries.get(key)
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else _one_line(value)}")
    return "\n".join(lines).rstrip() + "\n"


def write_stage9_self_state_model_report(root: Path | str, report: dict[str, Any], *, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    return write_stage9_report_text(root, render_stage9_self_state_model(report), output=output)


def write_stage9_self_state_model_state(
    root: Path | str,
    report: dict[str, Any],
    *,
    report_path: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    boundaries = report.get("boundaries") if isinstance(report.get("boundaries"), dict) else {}
    unfinished = model.get("unfinished_intentions") if isinstance(model.get("unfinished_intentions"), list) else []
    limits = model.get("current_limits") if isinstance(model.get("current_limits"), list) else []
    actions = model.get("available_actions") if isinstance(model.get("available_actions"), list) else []
    target_report = report_path or stage9_report_path(root)
    text = f"""---
title: Stage 9 Self State Model State
memory_type: stage9_self_state_model_state
time_scope: immediate_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_stage9_self_state_model
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, self-state, stage9, audit]
---

# Stage 9 Self State Model State

## Gate
- stage9_self_state_model_status: {report.get('status', 'missing')}
- stage9_ready_for_stage10: {str(bool(report.get('ready_for_stage10', False))).lower()}
- stage9_reason: {report.get('reason', 'missing')}

## Current State
- stage9_current_task: {model.get('current_task', 'none')}
- stage9_relation_posture: {model.get('relation_posture', 'none')}
- stage9_recent_action_result: {model.get('recent_action_result', 'none')}
- stage9_unfinished_intention_count: {len(unfinished)}
- stage9_current_limit_count: {len(limits)}
- stage9_available_action_count: {len(actions)}
- stage9_silence_reason: {model.get('silence_reason', 'none')}
- stage9_reply_influence_status: {model.get('reply_influence_status', 'none')}
- stage9_state_contract: {model.get('state_contract', 'none')}
- stage9_next_step: {model.get('next_step', 'none')}

## Boundaries
- raw_owner_text_in_state: {str(bool(boundaries.get('raw_owner_text_in_state', False))).lower()}
- visible_reply_text_in_state: {str(bool(boundaries.get('visible_reply_text_in_state', False))).lower()}
- stable_memory_write: {boundaries.get('stable_memory_write', 'blocked')}
- stable_identity_profile_apply: {boundaries.get('stable_identity_profile_apply', 'blocked')}
- qq_message_enqueued: {str(bool(boundaries.get('qq_message_enqueued', False))).lower()}
- consciousness_claim: {str(bool(boundaries.get('consciousness_claim', False))).lower()}
- report_path: {target_report.as_posix()}
"""
    return write_stage9_state_text(root, text)


def append_stage9_self_state_model_trace(root: Path | str, report: dict[str, Any]) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    event = {
        "event_id": "stage9-self-state-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S"),
        "observed_at": report.get("generated_at", _now_iso()),
        "status": report.get("status", "missing"),
        "ready_for_stage10": bool(report.get("ready_for_stage10", False)),
        "current_task": model.get("current_task", "none"),
        "relation_posture": model.get("relation_posture", "none"),
        "unfinished_intention_count": len(model.get("unfinished_intentions", []) or []),
        "current_limit_count": len(model.get("current_limits", []) or []),
        "available_action_count": len(model.get("available_actions", []) or []),
        "silence_reason": model.get("silence_reason", "none"),
        "raw_owner_text_retained": False,
        "visible_reply_text_retained": False,
        "consciousness_claim": False,
    }
    return append_stage9_trace_event(root, event)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build XinYu Stage 9 self-state model report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report = build_stage9_self_state_model(args.root)
    if args.write:
        report_path = write_stage9_self_state_model_report(args.root, report, output=args.output)
        state_path = write_stage9_self_state_model_state(args.root, report, report_path=report_path)
        trace_path = append_stage9_self_state_model_trace(args.root, report)
        report["report_path"] = str(report_path)
        report["state_path"] = str(state_path)
        report["trace_path"] = str(trace_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_stage9_self_state_model(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
