from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_text_variants import LEGACY_MOJIBAKE_FRAGMENTS


PACKET_REL = Path("worklog") / "xinyu-stage8-learning-trial-validation-latest.md"
STATE_REL = Path("memory/context/stage8_learning_trial_validation_state.md")
LEARNING_STATE_REL = Path("memory/self/learning_closed_loop_state.md")
LEARNING_TRACE_REL = Path("runtime/learning_closed_loop_trace.jsonl")
SUCCESS_GATE_TARGET_STREAK = 2
NONE_VALUES = {"", "none", "unknown", "missing", "null"}
# Display hygiene only: the matcher keeps legacy mojibake variants (for tolerating
# historically mis-decoded input), but owner-visible packets must show readable
# examples, never the U+FFFD / mojibake variant forms.
_MOJIBAKE_FRAGMENT_SET = frozenset(LEGACY_MOJIBAKE_FRAGMENTS)
# Curated readable examples for the owner-visible contract. Each entry must stay a
# real member of the corresponding matcher set (guarded by tests) so display never
# drifts from what is actually accepted, while never exposing mojibake variants.
ACCEPTED_SUCCESS_DISPLAY_EXAMPLES = (
    "自然多了",
    "像人了",
    "像你了",
    "这句可以",
    "这样可以",
    "这次可以",
    "这次修复有效",
    "修复有效",
    "改对了",
    "改好了",
    "接住了",
    "没模板味了",
    "不机械了",
    "没gpt味了",
)
STYLE_SUCCESS_DISPLAY_EXAMPLES = (
    "没模板味了",
    "没有模板味了",
    "不模板了",
    "不再模板",
    "模板味少了",
    "不像客服了",
    "不机械了",
    "没AI味了",
    "没gpt味了",
    "修复有效",
    "改对了",
    "改好了",
)
REPLY_CONTEXT_DISPLAY_EXAMPLES = (
    "这句",
    "这次",
    "这样",
    "刚才",
    "现在",
    "回复",
    "说法",
    "语气",
    "自然",
    "接住",
)
CANCEL_DISPLAY_EXAMPLES = (
    "但是",
    "但还是",
    "不过",
    "然而",
    "仍然",
    "依旧",
    "还有点",
    "还是有",
    "还不行",
    "没改",
    "没变化",
    "不行",
)


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
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _read_text(path: Path, *, limit: int = 80000) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")[:limit]
    except OSError:
        return ""


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        return default
    return _one_line(match.group(1), limit=260, default=default)


def _int_field(text: str, name: str, default: int = 0) -> int:
    raw = _field(text, name, str(default))
    match = re.search(r"-?\d+", raw)
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def _latest_jsonl_row(path: Path, *, max_lines: int = 300) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return {}
    for line in reversed(lines[-max(1, int(max_lines)) :]):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return {}


def _is_display_clean_marker(marker: str) -> bool:
    """Owner-visible display filter: drop U+FFFD / ?-replacement / mojibake variants.

    The matching set in xinyu_learning_closed_loop keeps these variants on purpose;
    this only governs what gets printed into the owner-facing packet.
    """
    if "�" in marker or "?" in marker:
        return False
    # Legacy GBK/CP936 mis-decodes often land in the private-use area.
    if any(0xE000 <= ord(ch) <= 0xF8FF for ch in marker):
        return False
    return not any(fragment in marker for fragment in _MOJIBAKE_FRAGMENT_SET)


def _sample_markers(markers: tuple[str, ...], *, limit: int = 10) -> list[str]:
    samples: list[str] = []
    seen: set[str] = set()
    for marker in markers:
        clean = _one_line(marker, limit=80, default="")
        if not clean or clean in seen:
            continue
        if not _is_display_clean_marker(clean):
            continue
        seen.add(clean)
        samples.append(clean)
        if len(samples) >= limit:
            break
    return samples


def _gate_blockers(fields: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    status = _safe_str(fields.get("status"), "none")
    active_trial_key = _safe_str(fields.get("active_trial_key"), "none")
    latest_success_trial_key = _safe_str(fields.get("latest_success_trial_key"), "none")
    success_evidence_status = _safe_str(fields.get("success_evidence_status"), "none")
    last_owner_reaction = _safe_str(fields.get("last_owner_reaction"), "none")
    promotion_signal = _safe_str(fields.get("promotion_signal"), "false")
    trial_success_count = int(fields.get("trial_success_count") or 0)
    trial_success_streak = int(fields.get("trial_success_streak") or 0)
    if active_trial_key.lower() in NONE_VALUES:
        blockers.append("missing_active_trial_key")
    if status != "trial_supported":
        blockers.append(f"status_not_trial_supported:{status}")
    if latest_success_trial_key.lower() in NONE_VALUES:
        blockers.append("missing_success_trial_key")
    elif active_trial_key.lower() not in NONE_VALUES and latest_success_trial_key != active_trial_key:
        blockers.append(f"success_trial_key_mismatch:{latest_success_trial_key}")
    if success_evidence_status != "same_trial_explicit_owner_success":
        blockers.append(f"success_evidence_not_same_trial:{success_evidence_status}")
    if trial_success_count < SUCCESS_GATE_TARGET_STREAK:
        blockers.append(f"trial_success_count_below_{SUCCESS_GATE_TARGET_STREAK}:{trial_success_count}")
    if trial_success_streak < SUCCESS_GATE_TARGET_STREAK:
        blockers.append(f"trial_success_streak_below_{SUCCESS_GATE_TARGET_STREAK}:{trial_success_streak}")
    if last_owner_reaction != "explicit_success":
        blockers.append(f"last_owner_reaction_not_explicit_success:{last_owner_reaction}")
    if promotion_signal not in {"true", "possible_after_self_review"} and trial_success_streak < SUCCESS_GATE_TARGET_STREAK:
        blockers.append(f"promotion_signal_not_ready:{promotion_signal}")
    return blockers


def _needed_success_count(fields: dict[str, Any], blockers: list[str]) -> int:
    if not blockers:
        return 0
    trial_success_streak = int(fields.get("trial_success_streak") or 0)
    success_evidence_status = _safe_str(fields.get("success_evidence_status"), "none")
    last_owner_reaction = _safe_str(fields.get("last_owner_reaction"), "none")
    if success_evidence_status != "same_trial_explicit_owner_success" or last_owner_reaction != "explicit_success":
        return SUCCESS_GATE_TARGET_STREAK
    return max(0, SUCCESS_GATE_TARGET_STREAK - trial_success_streak)


def _learning_fields(text: str) -> dict[str, Any]:
    return {
        "status": _field(text, "status", "missing"),
        "latest_failure_kind": _field(text, "latest_failure_kind", "none"),
        "active_trial_key": _field(text, "active_trial_key", _field(text, "latest_failure_kind", "none")),
        "active_trial_habit": _field(text, "active_trial_habit", "none"),
        "expected_next_behavior": _field(text, "expected_next_behavior", "none"),
        "repair_count": _int_field(text, "repair_count", 0),
        "success_count": _int_field(text, "success_count", 0),
        "success_streak": _int_field(text, "success_streak", 0),
        "trial_success_count": _int_field(text, "trial_success_count", _int_field(text, "success_count", 0)),
        "trial_success_streak": _int_field(text, "trial_success_streak", _int_field(text, "success_streak", 0)),
        "promotion_signal": _field(text, "promotion_signal", "false").lower(),
        "last_owner_reaction": _field(text, "last_owner_reaction", "none"),
        "latest_success_at": _field(text, "latest_success_at", "none"),
        "latest_success_trial_key": _field(text, "latest_success_trial_key", "none"),
        "success_evidence_status": _field(text, "success_evidence_status", "none"),
    }


def _owner_review_decision(
    fields: dict[str, Any],
    *,
    blockers: list[str],
    needed: int,
) -> dict[str, Any]:
    active_trial_key = _safe_str(fields.get("active_trial_key"), "none")
    last_owner_reaction = _safe_str(fields.get("last_owner_reaction"), "none")
    repair_count = int(fields.get("repair_count") or 0)
    trial_success_streak = int(fields.get("trial_success_streak") or 0)
    success_evidence_status = _safe_str(fields.get("success_evidence_status"), "none")
    if "repair" in last_owner_reaction.lower():
        origin = "owner_repair_pressure"
    elif last_owner_reaction.lower() not in NONE_VALUES:
        origin = last_owner_reaction
    else:
        origin = "runtime_post_reply_or_guard_observation"
    if not blockers:
        owner_action = "owner_explicit_apply_required_no_auto_promotion"
        reason = (
            f"gate_satisfied: {SUCCESS_GATE_TARGET_STREAK} consecutive same-trial explicit owner success captured; "
            "awaiting explicit owner apply, not auto-promoted"
        )
    elif needed > 0:
        owner_action = f"collect_{needed}_more_same_trial_explicit_owner_success"
        reason = (
            f"blocked: needs {needed} more consecutive same-trial explicit owner success after a real visible reply "
            f"(current_streak={trial_success_streak}, evidence={success_evidence_status})"
        )
    else:
        owner_action = "owner_resolve_blockers_then_recheck"
        reason = "blocked: trial key/status mismatch must be resolved before counting success"
    return {
        "blocked_key": active_trial_key,
        "owner_action": owner_action,
        "source": (
            f"runtime_learning_closed_loop_trial:{active_trial_key} "
            f"(origin={origin}, repair_observations={repair_count}, raw_owner_text_excluded)"
        ),
        "reason": reason,
        "boundary": [
            "runtime_trial_bias_only",
            "stable_profile_write:blocked",
            "owner_memory_write:blocked_owner_review_required",
            "no_auto_promotion_to_stable_memory",
            "raw_owner_text_hidden_counts_and_keys_only",
        ],
        "required_success_signal": {
            "consecutive_same_trial_explicit_owner_success_required": SUCCESS_GATE_TARGET_STREAK,
            "still_needed": needed,
            "must_match_active_trial_key": active_trial_key,
            "valid_scope": "owner_private_chat_after_an_actual_xinyu_visible_reply",
            "what_counts": "owner explicitly confirms the changed behavior was better for this same trial",
            "what_resets_streak": "an owner repair or cancel marker",
        },
        "rollback_path": [
            "no_stable_memory_written_yet:nothing_to_revert_at_stable_layer",
            "single_owner_repair_or_cancel_resets_trial_success_streak_to_zero",
            "trial_bias_is_runtime_only:clearing_learning_closed_loop_state_removes_it",
            "any_future_stable_apply_is_a_separate_explicit_owner_action_reversible_by_removing_the_written_line",
        ],
    }


def build_stage8_learning_trial_validation_packet(root: Path) -> dict[str, Any]:
    root = root.resolve()
    learning_text = _read_text(root / LEARNING_STATE_REL)
    fields = _learning_fields(learning_text)
    blockers = _gate_blockers(fields)
    needed = _needed_success_count(fields, blockers)
    latest_trace = _latest_jsonl_row(root / LEARNING_TRACE_REL)
    packet_status = "satisfied" if not blockers else "blocked_waiting_for_owner_success"
    owner_review_decision = _owner_review_decision(fields, blockers=blockers, needed=needed)
    return {
        "ok": True,
        "generated_at": _now_iso(),
        "root": str(root),
        "stage": "stage8_memory_governance",
        "packet_status": packet_status,
        "mode": "read_only_learning_trial_validation_packet",
        "learning_trial": fields,
        "owner_review_decision": owner_review_decision,
        "gate": {
            "learning_trial_success_gate": "satisfied" if not blockers else "blocked",
            "blockers": blockers,
            "required_consecutive_success_count": SUCCESS_GATE_TARGET_STREAK,
            "needed_consecutive_success_count": needed,
            "success_must_match_active_trial_key": True,
            "stable_profile_write": "blocked",
        },
        "latest_trace_summary": {
            "event_id": _one_line(latest_trace.get("event_id"), limit=100),
            "owner_private": bool(latest_trace.get("owner_private", False)),
            "success": bool(latest_trace.get("success", False)),
            "failure_count": len(latest_trace.get("failures", []) or []) if isinstance(latest_trace.get("failures"), list) else 0,
            "failure_kinds": [
                _one_line(item, limit=100, default="")
                for item in (latest_trace.get("failures", []) or [])[:6]
                if _safe_str(item).strip()
            ]
            if isinstance(latest_trace.get("failures"), list)
            else [],
            "active_trial_key": _one_line(latest_trace.get("active_trial_key"), limit=120),
            "success_evidence_status": _one_line(latest_trace.get("success_evidence_status"), limit=120),
        },
        "success_capture_contract": {
            "valid_scope": "owner_private_chat_after_xinyu_visible_reply",
            "accepted_success_marker_examples": _sample_markers(ACCEPTED_SUCCESS_DISPLAY_EXAMPLES, limit=14),
            "style_trial_success_examples": _sample_markers(STYLE_SUCCESS_DISPLAY_EXAMPLES, limit=14),
            "generic_success_requires_reply_context_markers": _sample_markers(REPLY_CONTEXT_DISPLAY_EXAMPLES, limit=10),
            "cancel_markers_that_turn_success_into_failure": _sample_markers(CANCEL_DISPLAY_EXAMPLES, limit=12),
            "mixed_feedback_policy": "success_words_plus_cancel_marker_is_failure",
        },
        "next_actions": [
            "do_not_promote_stable_profile_yet",
            "wait_for_real_owner_private_feedback_after_actual_reply",
            "count_only_same_trial_explicit_success",
            "rerun_memory_health_after_two_consecutive_successes",
        ],
        "boundaries": {
            "raw_owner_text_in_packet": False,
            "visible_reply_text_in_packet": False,
            "candidate_body_in_packet": False,
            "stable_memory_write": "blocked",
            "stable_identity_profile_apply": "blocked",
            "candidate_status_changed": False,
            "qq_message_enqueued": False,
            "consciousness_claim": False,
        },
    }


def render_stage8_learning_trial_validation_packet(packet: dict[str, Any]) -> str:
    trial = packet.get("learning_trial") if isinstance(packet.get("learning_trial"), dict) else {}
    gate = packet.get("gate") if isinstance(packet.get("gate"), dict) else {}
    trace = packet.get("latest_trace_summary") if isinstance(packet.get("latest_trace_summary"), dict) else {}
    contract = packet.get("success_capture_contract") if isinstance(packet.get("success_capture_contract"), dict) else {}
    decision = packet.get("owner_review_decision") if isinstance(packet.get("owner_review_decision"), dict) else {}
    required_signal = decision.get("required_success_signal") if isinstance(decision.get("required_success_signal"), dict) else {}
    lines = [
        "# XinYu Stage 8 Learning Trial Validation Packet",
        "",
        f"- generated_at: {_one_line(packet.get('generated_at'))}",
        f"- packet_status: {_one_line(packet.get('packet_status'))}",
        f"- mode: {_one_line(packet.get('mode'))}",
        "- raw_owner_text: hidden",
        "- visible_reply_text: hidden",
        "- stable_profile_write: blocked",
        "",
        "## Owner Review Decision",
        f"- blocked_key: {_one_line(decision.get('blocked_key'))}",
        f"- owner_action: {_one_line(decision.get('owner_action'), limit=120)}",
        f"- source: {_one_line(decision.get('source'), limit=240)}",
        f"- reason: {_one_line(decision.get('reason'), limit=240)}",
        f"- boundary: {', '.join(decision.get('boundary', []) or []) or 'none'}",
        (
            "- required_success_signal: "
            f"required={_one_line(required_signal.get('consecutive_same_trial_explicit_owner_success_required'), default='0')}, "
            f"still_needed={_one_line(required_signal.get('still_needed'), default='0')}, "
            f"must_match_active_trial_key={_one_line(required_signal.get('must_match_active_trial_key'))}, "
            f"valid_scope={_one_line(required_signal.get('valid_scope'), limit=120)}"
        ),
        f"- rollback_path: {'; '.join(decision.get('rollback_path', []) or []) or 'none'}",
        "",
        "## Gate",
        f"- learning_trial_success_gate: {_one_line(gate.get('learning_trial_success_gate'))}",
        f"- required_consecutive_success_count: {_one_line(gate.get('required_consecutive_success_count'), default='0')}",
        f"- needed_consecutive_success_count: {_one_line(gate.get('needed_consecutive_success_count'), default='0')}",
        f"- success_must_match_active_trial_key: {str(bool(gate.get('success_must_match_active_trial_key', True))).lower()}",
        "",
        "## Current Trial",
        f"- status: {_one_line(trial.get('status'))}",
        f"- latest_failure_kind: {_one_line(trial.get('latest_failure_kind'))}",
        f"- active_trial_key: {_one_line(trial.get('active_trial_key'))}",
        f"- active_trial_habit: {_one_line(trial.get('active_trial_habit'), limit=260)}",
        f"- expected_next_behavior: {_one_line(trial.get('expected_next_behavior'), limit=260)}",
        f"- repair_count: {_one_line(trial.get('repair_count'), default='0')}",
        f"- trial_success_count: {_one_line(trial.get('trial_success_count'), default='0')}",
        f"- trial_success_streak: {_one_line(trial.get('trial_success_streak'), default='0')}",
        f"- latest_success_trial_key: {_one_line(trial.get('latest_success_trial_key'))}",
        f"- success_evidence_status: {_one_line(trial.get('success_evidence_status'))}",
        f"- last_owner_reaction: {_one_line(trial.get('last_owner_reaction'))}",
        "",
        "## Blockers",
    ]
    blockers = gate.get("blockers") if isinstance(gate.get("blockers"), list) else []
    if not blockers:
        lines.append("- none")
    else:
        lines.extend(f"- {_one_line(item, limit=180)}" for item in blockers)
    lines.extend(
        [
            "",
            "## Latest Trace Summary",
            f"- event_id: {_one_line(trace.get('event_id'), limit=100)}",
            f"- owner_private: {str(bool(trace.get('owner_private', False))).lower()}",
            f"- success: {str(bool(trace.get('success', False))).lower()}",
            f"- failure_count: {_one_line(trace.get('failure_count'), default='0')}",
            f"- active_trial_key: {_one_line(trace.get('active_trial_key'), limit=120)}",
            f"- success_evidence_status: {_one_line(trace.get('success_evidence_status'), limit=120)}",
            "",
            "## Success Capture Contract",
            f"- valid_scope: {_one_line(contract.get('valid_scope'), limit=160)}",
            f"- accepted_success_marker_examples: {', '.join(contract.get('accepted_success_marker_examples', []) or [])}",
            f"- style_trial_success_examples: {', '.join(contract.get('style_trial_success_examples', []) or [])}",
            f"- generic_success_requires_reply_context_markers: {', '.join(contract.get('generic_success_requires_reply_context_markers', []) or [])}",
            f"- cancel_markers_that_turn_success_into_failure: {', '.join(contract.get('cancel_markers_that_turn_success_into_failure', []) or [])}",
            f"- mixed_feedback_policy: {_one_line(contract.get('mixed_feedback_policy'), limit=180)}",
            "",
            "## Boundaries",
        ]
    )
    boundaries = packet.get("boundaries") if isinstance(packet.get("boundaries"), dict) else {}
    for key in sorted(boundaries):
        value = boundaries.get(key)
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else _one_line(value)}")
    lines.extend(["", "## Next Actions"])
    for item in packet.get("next_actions", []) or []:
        lines.append(f"- {_one_line(item, limit=220)}")
    return "\n".join(lines).rstrip() + "\n"


def write_stage8_learning_trial_validation_packet(
    root: Path,
    packet: dict[str, Any],
    *,
    output: Path | None = None,
) -> Path:
    root = root.resolve()
    path = output if output is not None else root / PACKET_REL
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_stage8_learning_trial_validation_packet(packet), encoding="utf-8")
    return path


def write_stage8_learning_trial_validation_state(
    root: Path,
    packet: dict[str, Any],
    *,
    packet_path: Path | None = None,
) -> Path:
    root = root.resolve()
    path = root / STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    trial = packet.get("learning_trial") if isinstance(packet.get("learning_trial"), dict) else {}
    gate = packet.get("gate") if isinstance(packet.get("gate"), dict) else {}
    decision = packet.get("owner_review_decision") if isinstance(packet.get("owner_review_decision"), dict) else {}
    target_packet_path = packet_path or (root / PACKET_REL)
    text = f"""---
title: Stage 8 Learning Trial Validation State
memory_type: stage8_learning_trial_validation_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_stage8_learning_trial_validation_packet
updated_at: {packet.get('generated_at', 'unknown')}
status: active
tags: [autonomy, memory, governance, learning-trial, stage8]
---

# Stage 8 Learning Trial Validation State

## Gate
- validation_status: {packet.get('packet_status', 'missing')}
- learning_trial_success_gate: {gate.get('learning_trial_success_gate', 'missing')}
- active_trial_key: {trial.get('active_trial_key', 'none')}
- required_consecutive_success_count: {gate.get('required_consecutive_success_count', 0)}
- needed_consecutive_success_count: {gate.get('needed_consecutive_success_count', 0)}
- trial_success_count: {trial.get('trial_success_count', 0)}
- trial_success_streak: {trial.get('trial_success_streak', 0)}
- success_evidence_status: {trial.get('success_evidence_status', 'none')}
- last_owner_reaction: {trial.get('last_owner_reaction', 'none')}
- packet_path: {target_packet_path.as_posix()}

## Owner Review Decision
- owner_action: {decision.get('owner_action', 'none')}
- blocked_key: {decision.get('blocked_key', 'none')}
- decision_reason: {_one_line(decision.get('reason'), limit=240)}

## Boundaries
- raw_owner_text_in_state: false
- visible_reply_text_in_state: false
- stable_memory_write: blocked
- stable_identity_profile_apply: blocked
- qq_message_enqueued: false
- consciousness_claim: false
"""
    path.write_text(text, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Build a redacted Stage 8 learning trial validation packet.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    packet = build_stage8_learning_trial_validation_packet(args.root)
    if args.write:
        packet_path = write_stage8_learning_trial_validation_packet(args.root, packet, output=args.output)
        state_path = write_stage8_learning_trial_validation_state(args.root, packet, packet_path=packet_path)
        packet["packet_path"] = str(packet_path)
        packet["state_path"] = str(state_path)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_stage8_learning_trial_validation_packet(packet))
    return 0 if packet.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
