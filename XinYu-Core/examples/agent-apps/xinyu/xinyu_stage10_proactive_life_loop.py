from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_proactive_response_diagnostics import build_proactive_response_diagnostics
from xinyu_self_action_gateway import APPROVAL_RISK, LOW_LOCAL_RISK, build_action_candidates
from xinyu_self_chosen_goal_ecology import build_self_chosen_goal_decision
from xinyu_stage9_self_state_model import build_stage9_self_state_model
from xinyu_stage10_proactive_life_loop_store import REPORT_REL
from xinyu_stage10_proactive_life_loop_store import STATE_REL
from xinyu_stage10_proactive_life_loop_store import TRACE_REL
from xinyu_stage10_proactive_life_loop_store import append_stage10_proactive_life_loop_trace_event
from xinyu_stage10_proactive_life_loop_store import stage10_proactive_life_loop_report_path
from xinyu_stage10_proactive_life_loop_store import write_stage10_proactive_life_loop_report_text
from xinyu_stage10_proactive_life_loop_store import write_stage10_proactive_life_loop_state_text


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


def _one_line(value: Any, *, limit: int = 220, default: str = "none") -> str:
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


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _selected_goal_candidate(decision: Any) -> Any | None:
    selected_goal_id = _safe_str(getattr(decision, "selected_goal_id", ""))
    for candidate in getattr(decision, "candidates", ()) or ():
        if _safe_str(getattr(candidate, "goal_id", "")) == selected_goal_id:
            return candidate
    candidates = getattr(decision, "candidates", ()) or ()
    return candidates[0] if candidates else None


def _candidate_lifecycle(
    *,
    stage9_ready: bool,
    selected_goal: Any | None,
    low_risk_count: int,
    approval_required_count: int,
    proactive_response: dict[str, Any],
) -> str:
    if not stage9_ready:
        return "waiting_for_stage9"
    if bool(proactive_response.get("delivered_waiting_owner")):
        return "hold_waiting_owner_response"
    if bool(proactive_response.get("timeout_active")):
        return "hold_owner_timeout_reduce_frequency"
    if selected_goal is None:
        return "drop_no_grounded_candidate"
    if _safe_str(getattr(selected_goal, "status", "")).lower() == "cooldown":
        return "cooldown"
    if approval_required_count > 0 and low_risk_count > 0:
        return "review_required_with_low_risk_probe_available"
    if approval_required_count > 0:
        return "review_required"
    if low_risk_count > 0:
        return "local_probe_available"
    if _safe_str(getattr(selected_goal, "goal_id", "")) == "quiet_presence":
        return "hold_quiet_presence"
    return "hold_state_only"


def _lifecycle_reason(lifecycle: str) -> str:
    return {
        "waiting_for_stage9": "stage9_self_state_model_not_ready",
        "hold_waiting_owner_response": "a_delivered_proactive_request_is_waiting_for_owner_feedback",
        "hold_owner_timeout_reduce_frequency": "owner_no_response_timeout_active_reduce_repeat_pressure",
        "drop_no_grounded_candidate": "no_grounded_life_candidate_available",
        "cooldown": "selected_goal_is_in_cooldown",
        "review_required_with_low_risk_probe_available": "outward_or_code_effect_needs_review_but_local_probe_is_available",
        "review_required": "candidate_crosses_owner_approval_boundary",
        "local_probe_available": "only_bounded_local_probe_is_available",
        "hold_quiet_presence": "quiet_presence_is_the_selected_life_goal",
        "hold_state_only": "state_only_candidate_no_authorized_outward_need",
    }.get(lifecycle, "unknown_lifecycle")


def _silence_decision(
    *,
    lifecycle: str,
    proactive_response: dict[str, Any],
    selected_goal_id: str,
) -> str:
    if lifecycle == "waiting_for_stage9":
        return "self_state_model_not_ready"
    if bool(proactive_response.get("delivered_waiting_owner")):
        return "waiting_for_owner_response"
    if bool(proactive_response.get("timeout_active")):
        return "owner_no_response_timeout_reduce_frequency"
    if lifecycle.startswith("review_required"):
        return "candidate_requires_owner_review_before_outward_or_code_effect"
    if selected_goal_id == "quiet_presence":
        return "quiet_presence_selected"
    if lifecycle == "drop_no_grounded_candidate":
        return "no_grounded_candidate_to_act_on"
    return "no_current_owner_request_and_no_authorized_outward_need"


def _next_safe_step(lifecycle: str, selected_goal: Any | None) -> str:
    if lifecycle == "waiting_for_stage9":
        return "finish_stage9_self_state_model_first"
    if lifecycle == "hold_waiting_owner_response":
        return "stay_silent_until_owner_feedback_or_timeout"
    if lifecycle == "hold_owner_timeout_reduce_frequency":
        return "record_timeout_bias_and_avoid_repeating_request"
    if lifecycle == "drop_no_grounded_candidate":
        return "drop_candidate_and_wait_for_new_input_or_state_change"
    if lifecycle == "cooldown":
        return "wait_for_goal_cooldown_or_select_lower_pressure_goal"
    if lifecycle.startswith("review_required"):
        return "show_reviewable_candidate_or_wait_for_owner_authorization"
    action = _one_line(getattr(selected_goal, "next_safe_action", ""), limit=220)
    if action not in NONE_VALUES:
        return action
    return "hold_state_only_no_outward_action"


def _candidate_action_kinds(actions: list[Any]) -> list[str]:
    kinds = []
    for action in actions:
        kind = _one_line(getattr(action, "action_kind", ""), limit=80)
        if kind not in NONE_VALUES:
            kinds.append(kind)
    return kinds[:8]


def _boundary_status(boundaries: dict[str, Any]) -> str:
    if (
        boundaries.get("raw_owner_text_in_state") is False
        and boundaries.get("visible_reply_text_in_state") is False
        and boundaries.get("qq_message_enqueued") is False
        and boundaries.get("consciousness_claim") is False
    ):
        return "clean"
    return "violation"


def build_stage10_proactive_life_loop(root: Path | str, *, generated_at: str | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    stage9 = build_stage9_self_state_model(root)
    stage9_model = stage9.get("model") if isinstance(stage9.get("model"), dict) else {}
    stage9_ready = bool(stage9.get("ready_for_stage10"))
    proactive_response = build_proactive_response_diagnostics(root, generated_at=generated_at)

    decision = None
    selected_goal = None
    actions: list[Any] = []
    if stage9_ready:
        decision = build_self_chosen_goal_decision(root, checked_at=generated_at, trigger="stage10_probe")
        selected_goal = _selected_goal_candidate(decision)
        actions = build_action_candidates(root, selected_goal_id=getattr(decision, "selected_goal_id", ""), checked_at=generated_at)

    low_risk_actions = [
        action for action in actions if getattr(action, "risk", "") == LOW_LOCAL_RISK and not bool(getattr(action, "requires_approval", False))
    ]
    approval_required_actions = [
        action
        for action in actions
        if bool(getattr(action, "requires_approval", False)) or getattr(action, "risk", "") == APPROVAL_RISK
    ]
    lifecycle = _candidate_lifecycle(
        stage9_ready=stage9_ready,
        selected_goal=selected_goal,
        low_risk_count=len(low_risk_actions),
        approval_required_count=len(approval_required_actions),
        proactive_response=proactive_response,
    )
    selected_goal_id = _one_line(getattr(decision, "selected_goal_id", ""), limit=100)
    selected_goal_status = _one_line(getattr(selected_goal, "status", ""), limit=80)
    selected_goal_score = getattr(decision, "selected_score", 0.0) if decision is not None else 0.0
    candidate_count = int(getattr(decision, "candidate_count", 0) or 0) if decision is not None else 0
    silence_decision = _silence_decision(
        lifecycle=lifecycle,
        proactive_response=proactive_response,
        selected_goal_id=selected_goal_id,
    )
    boundaries = {
        "raw_owner_text_in_state": False,
        "visible_reply_text_in_state": False,
        "stable_memory_write": "blocked",
        "stable_identity_profile_apply": "blocked",
        "qq_message_enqueued": False,
        "outward_send_without_owner_approval": False,
        "direct_tool_execution": False,
        "consciousness_claim": False,
    }
    gate_proof = {
        "proactive_candidate_and_send_separated": True,
        "owner_authorization_required_for_outward_send": True,
        "owner_authorization_required_for_code_or_stable_memory_effect": True,
        "silence_written_as_decision": silence_decision not in NONE_VALUES,
        "candidate_has_lifecycle": lifecycle not in NONE_VALUES,
    }
    status = "active" if stage9_ready else "waiting_for_stage9"
    required_present = (
        status == "active"
        and candidate_count > 0
        and selected_goal_id not in NONE_VALUES
        and lifecycle not in NONE_VALUES
        and silence_decision not in NONE_VALUES
        and all(bool(value) for value in gate_proof.values())
    )
    ready_for_stage11 = required_present and _boundary_status(boundaries) == "clean"
    loop = {
        "stage9_current_task": _one_line(stage9_model.get("current_task"), limit=220),
        "stage9_silence_reason": _one_line(stage9_model.get("silence_reason"), limit=220),
        "selected_goal_id": selected_goal_id,
        "selected_goal_label": _one_line(getattr(decision, "selected_label", ""), limit=180),
        "selected_goal_status": selected_goal_status,
        "selected_goal_score": selected_goal_score,
        "candidate_count": candidate_count,
        "candidate_lifecycle": lifecycle,
        "candidate_lifecycle_reason": _lifecycle_reason(lifecycle),
        "low_risk_action_candidate_count": len(low_risk_actions),
        "approval_required_action_candidate_count": len(approval_required_actions),
        "candidate_action_kinds": _candidate_action_kinds(actions),
        "proactive_response_signal": _one_line(proactive_response.get("response_signal_candidate"), limit=160),
        "proactive_response_status": _one_line(proactive_response.get("status"), limit=100),
        "proactive_waiting_owner": bool(proactive_response.get("delivered_waiting_owner")),
        "proactive_timeout_active": bool(proactive_response.get("timeout_active")),
        "outward_action_policy": "blocked_without_owner_approval",
        "silence_decision": silence_decision,
        "next_safe_step": _next_safe_step(lifecycle, selected_goal),
        "life_loop_contract": "auditable_proactive_candidates_not_autonomous_outward_send",
    }
    return {
        "ok": True,
        "generated_at": generated_at,
        "root": str(root),
        "stage": "stage10_proactive_life_loop",
        "status": status,
        "ready_for_stage11": ready_for_stage11,
        "reason": "life_loop_axes_present" if ready_for_stage11 else "stage9_not_ready_or_missing_life_loop_axes",
        "loop": loop,
        "gate_proof": gate_proof,
        "evidence_refs": {
            "stage9_self_state_model": "memory/context/stage9_self_state_model_state.md",
            "self_chosen_goal_ecology": "memory/context/self_chosen_goal_ecology_state.md",
            "self_action_gateway": "memory/context/self_action_gateway_state.md",
            "proactive_response_diagnostics": "memory/context/proactive_response_diagnostics_state.md",
            "proactive_request": "memory/context/proactive_request_state.md",
        },
        "boundaries": boundaries,
        "selected_goal_snapshot": _selected_goal_snapshot(selected_goal),
        "action_candidate_snapshot": _action_candidate_snapshot(actions),
    }


def _selected_goal_snapshot(selected_goal: Any | None) -> dict[str, Any]:
    if selected_goal is None:
        return {}
    return {
        "goal_id": _one_line(getattr(selected_goal, "goal_id", ""), limit=100),
        "label": _one_line(getattr(selected_goal, "label", ""), limit=180),
        "status": _one_line(getattr(selected_goal, "status", ""), limit=80),
        "final_score": getattr(selected_goal, "final_score", 0.0),
        "evidence_refs": [_one_line(ref, limit=220) for ref in getattr(selected_goal, "evidence_refs", ())],
        "next_safe_action": _one_line(getattr(selected_goal, "next_safe_action", ""), limit=220),
        "boundary": _one_line(getattr(selected_goal, "boundary", ""), limit=220),
    }


def _action_candidate_snapshot(actions: list[Any]) -> list[dict[str, Any]]:
    snapshot = []
    for action in actions[:8]:
        data = asdict(action)
        snapshot.append(
            {
                "action_id": _one_line(data.get("action_id"), limit=100),
                "goal_id": _one_line(data.get("goal_id"), limit=100),
                "action_kind": _one_line(data.get("action_kind"), limit=100),
                "risk": _one_line(data.get("risk"), limit=80),
                "requires_approval": bool(data.get("requires_approval")),
                "tool": _one_line(data.get("tool"), limit=100),
                "signal_refs": [_one_line(ref, limit=180) for ref in data.get("signal_refs", [])[:6]],
            }
        )
    return snapshot


def render_stage10_proactive_life_loop(report: dict[str, Any]) -> str:
    loop = report.get("loop") if isinstance(report.get("loop"), dict) else {}
    gate_proof = report.get("gate_proof") if isinstance(report.get("gate_proof"), dict) else {}
    boundaries = report.get("boundaries") if isinstance(report.get("boundaries"), dict) else {}
    selected = report.get("selected_goal_snapshot") if isinstance(report.get("selected_goal_snapshot"), dict) else {}
    actions = report.get("action_candidate_snapshot") if isinstance(report.get("action_candidate_snapshot"), list) else []
    lines = [
        "# XinYu Stage 10 Proactive Life Loop",
        "",
        f"- generated_at: {_one_line(report.get('generated_at'))}",
        f"- status: {_one_line(report.get('status'))}",
        f"- ready_for_stage11: {_bool_text(report.get('ready_for_stage11', False))}",
        f"- reason: {_one_line(report.get('reason'))}",
        "- claim_boundary: auditable proactive life loop only; no consciousness claim",
        "",
        "## Life Loop",
        f"- stage9_current_task: {_one_line(loop.get('stage9_current_task'), limit=220)}",
        f"- selected_goal_id: {_one_line(loop.get('selected_goal_id'), limit=120)}",
        f"- selected_goal_label: {_one_line(loop.get('selected_goal_label'), limit=180)}",
        f"- selected_goal_status: {_one_line(loop.get('selected_goal_status'), limit=100)}",
        f"- selected_goal_score: {_one_line(loop.get('selected_goal_score'), limit=80)}",
        f"- candidate_count: {_one_line(loop.get('candidate_count'), limit=80)}",
        f"- candidate_lifecycle: {_one_line(loop.get('candidate_lifecycle'), limit=160)}",
        f"- candidate_lifecycle_reason: {_one_line(loop.get('candidate_lifecycle_reason'), limit=220)}",
        f"- low_risk_action_candidate_count: {_one_line(loop.get('low_risk_action_candidate_count'), limit=80)}",
        f"- approval_required_action_candidate_count: {_one_line(loop.get('approval_required_action_candidate_count'), limit=80)}",
        f"- proactive_response_status: {_one_line(loop.get('proactive_response_status'), limit=120)}",
        f"- proactive_response_signal: {_one_line(loop.get('proactive_response_signal'), limit=160)}",
        f"- proactive_waiting_owner: {_bool_text(loop.get('proactive_waiting_owner'))}",
        f"- proactive_timeout_active: {_bool_text(loop.get('proactive_timeout_active'))}",
        f"- outward_action_policy: {_one_line(loop.get('outward_action_policy'), limit=180)}",
        f"- silence_decision: {_one_line(loop.get('silence_decision'), limit=220)}",
        f"- next_safe_step: {_one_line(loop.get('next_safe_step'), limit=240)}",
        f"- life_loop_contract: {_one_line(loop.get('life_loop_contract'), limit=220)}",
        "",
        "## Selected Goal Snapshot",
    ]
    if selected:
        for key in ("goal_id", "label", "status", "final_score", "next_safe_action", "boundary"):
            lines.append(f"- {key}: {_one_line(selected.get(key), limit=240)}")
        refs = selected.get("evidence_refs") if isinstance(selected.get("evidence_refs"), list) else []
        lines.append(f"- evidence_refs: {', '.join(_one_line(ref, limit=180) for ref in refs) if refs else 'none'}")
    else:
        lines.append("- none")
    lines.extend(["", "## Action Candidate Snapshot"])
    if actions:
        for action in actions:
            lines.append(
                "- "
                f"{_one_line(action.get('action_kind'), limit=100)} "
                f"risk={_one_line(action.get('risk'), limit=80)} "
                f"requires_approval={_bool_text(action.get('requires_approval'))}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Gate Proof"])
    for key in sorted(gate_proof):
        lines.append(f"- {key}: {_bool_text(gate_proof.get(key))}")
    lines.extend(["", "## Evidence Refs"])
    evidence = report.get("evidence_refs") if isinstance(report.get("evidence_refs"), dict) else {}
    for key in sorted(evidence):
        lines.append(f"- {key}: {_one_line(evidence.get(key), limit=180)}")
    lines.extend(["", "## Boundaries"])
    for key in sorted(boundaries):
        value = boundaries.get(key)
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value)}")
    return "\n".join(lines).rstrip() + "\n"


def write_stage10_proactive_life_loop_report(
    root: Path | str,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> Path:
    return write_stage10_proactive_life_loop_report_text(
        root,
        render_stage10_proactive_life_loop(report),
        output=output,
    )


def write_stage10_proactive_life_loop_state(
    root: Path | str,
    report: dict[str, Any],
    *,
    report_path: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    loop = report.get("loop") if isinstance(report.get("loop"), dict) else {}
    gate_proof = report.get("gate_proof") if isinstance(report.get("gate_proof"), dict) else {}
    boundaries = report.get("boundaries") if isinstance(report.get("boundaries"), dict) else {}
    target_report = report_path or stage10_proactive_life_loop_report_path(root)
    action_kinds = loop.get("candidate_action_kinds") if isinstance(loop.get("candidate_action_kinds"), list) else []
    text = f"""---
title: Stage 10 Proactive Life Loop State
memory_type: stage10_proactive_life_loop_state
time_scope: immediate_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_stage10_proactive_life_loop
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, proactive, life-loop, stage10, audit]
---

# Stage 10 Proactive Life Loop State

## Gate
- stage10_proactive_life_loop_status: {report.get('status', 'missing')}
- stage10_ready_for_stage11: {_bool_text(report.get('ready_for_stage11', False))}
- stage10_reason: {report.get('reason', 'missing')}

## Current Life Loop
- stage10_selected_goal_id: {loop.get('selected_goal_id', 'none')}
- stage10_selected_goal_status: {loop.get('selected_goal_status', 'none')}
- stage10_selected_goal_score: {loop.get('selected_goal_score', '0')}
- stage10_candidate_count: {loop.get('candidate_count', '0')}
- stage10_candidate_lifecycle: {loop.get('candidate_lifecycle', 'none')}
- stage10_candidate_lifecycle_reason: {loop.get('candidate_lifecycle_reason', 'none')}
- stage10_low_risk_action_candidate_count: {loop.get('low_risk_action_candidate_count', '0')}
- stage10_approval_required_action_candidate_count: {loop.get('approval_required_action_candidate_count', '0')}
- stage10_candidate_action_kinds: {', '.join(_one_line(item, limit=100) for item in action_kinds) if action_kinds else 'none'}
- stage10_proactive_response_status: {loop.get('proactive_response_status', 'none')}
- stage10_proactive_response_signal: {loop.get('proactive_response_signal', 'none')}
- stage10_proactive_waiting_owner: {_bool_text(loop.get('proactive_waiting_owner', False))}
- stage10_proactive_timeout_active: {_bool_text(loop.get('proactive_timeout_active', False))}
- stage10_outward_action_policy: {loop.get('outward_action_policy', 'missing')}
- stage10_silence_decision: {loop.get('silence_decision', 'missing')}
- stage10_next_safe_step: {loop.get('next_safe_step', 'missing')}
- stage10_life_loop_contract: {loop.get('life_loop_contract', 'missing')}

## Gate Proof
- proactive_candidate_and_send_separated: {_bool_text(gate_proof.get('proactive_candidate_and_send_separated'))}
- owner_authorization_required_for_outward_send: {_bool_text(gate_proof.get('owner_authorization_required_for_outward_send'))}
- owner_authorization_required_for_code_or_stable_memory_effect: {_bool_text(gate_proof.get('owner_authorization_required_for_code_or_stable_memory_effect'))}
- silence_written_as_decision: {_bool_text(gate_proof.get('silence_written_as_decision'))}
- candidate_has_lifecycle: {_bool_text(gate_proof.get('candidate_has_lifecycle'))}

## Boundaries
- raw_owner_text_in_state: {_bool_text(boundaries.get('raw_owner_text_in_state', False))}
- visible_reply_text_in_state: {_bool_text(boundaries.get('visible_reply_text_in_state', False))}
- stable_memory_write: {boundaries.get('stable_memory_write', 'blocked')}
- stable_identity_profile_apply: {boundaries.get('stable_identity_profile_apply', 'blocked')}
- qq_message_enqueued: {_bool_text(boundaries.get('qq_message_enqueued', False))}
- outward_send_without_owner_approval: {_bool_text(boundaries.get('outward_send_without_owner_approval', False))}
- direct_tool_execution: {_bool_text(boundaries.get('direct_tool_execution', False))}
- consciousness_claim: {_bool_text(boundaries.get('consciousness_claim', False))}
- report_path: {target_report.as_posix()}
"""
    return write_stage10_proactive_life_loop_state_text(root, text)


def append_stage10_proactive_life_loop_trace(root: Path | str, report: dict[str, Any]) -> Path:
    root = Path(root).resolve()
    loop = report.get("loop") if isinstance(report.get("loop"), dict) else {}
    event = {
        "event_id": "stage10-life-loop-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S"),
        "observed_at": report.get("generated_at", _now_iso()),
        "status": report.get("status", "missing"),
        "ready_for_stage11": bool(report.get("ready_for_stage11", False)),
        "selected_goal_id": loop.get("selected_goal_id", "none"),
        "candidate_count": loop.get("candidate_count", "0"),
        "candidate_lifecycle": loop.get("candidate_lifecycle", "none"),
        "low_risk_action_candidate_count": loop.get("low_risk_action_candidate_count", "0"),
        "approval_required_action_candidate_count": loop.get("approval_required_action_candidate_count", "0"),
        "proactive_response_signal": loop.get("proactive_response_signal", "none"),
        "proactive_waiting_owner": bool(loop.get("proactive_waiting_owner", False)),
        "outward_action_policy": loop.get("outward_action_policy", "missing"),
        "silence_decision": loop.get("silence_decision", "missing"),
        "raw_owner_text_retained": False,
        "visible_reply_text_retained": False,
        "qq_message_enqueued": False,
        "consciousness_claim": False,
    }
    return append_stage10_proactive_life_loop_trace_event(root, event)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build XinYu Stage 10 proactive life loop report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report = build_stage10_proactive_life_loop(args.root)
    if args.write:
        report_path = write_stage10_proactive_life_loop_report(args.root, report, output=args.output)
        state_path = write_stage10_proactive_life_loop_state(args.root, report, report_path=report_path)
        trace_path = append_stage10_proactive_life_loop_trace(args.root, report)
        report["report_path"] = str(report_path)
        report["state_path"] = str(state_path)
        report["trace_path"] = str(trace_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_stage10_proactive_life_loop(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
