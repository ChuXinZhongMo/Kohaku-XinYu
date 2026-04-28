from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

from xinyu_text_variants import readable_markers


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", text)
    return match.group(1).strip() if match else default


def _candidate_message(decision: str, selected_question: str, visible_posture: str) -> str:
    if decision == "ask_owner" and selected_question not in {"unknown", "none", ""}:
        if visible_posture == "one_specific_question":
            suffix = "" if selected_question.endswith(("？", "?")) else "？"
            return selected_question + suffix
    if decision == "step_back":
        return "我先退一点，不硬贴上来。"
    return "none"


SOFT_INTERRUPTION_GRANT = (
    "grant_owner_welcomes_xinyu_interruptions: "
    "approved_high_priority_one_short_message_life_posture_soft_block_override"
)
REST_SILENCE_INTERRUPTION_GRANT = (
    "grant_owner_welcomes_xinyu_interruptions: "
    "approved_high_priority_one_short_message_rest_silence_override"
)


def _proactive_qq_enabled(capability: str, owner_grants: str = "") -> bool:
    return (
        "proactive_qq_send: enabled_gated_one_short_message" in capability
        or "grant_proactive_qq: enabled_gated_one_short_message" in owner_grants
        or SOFT_INTERRUPTION_GRANT in owner_grants
        or REST_SILENCE_INTERRUPTION_GRANT in owner_grants
    )


def _interruption_grant_level(owner_grants: str) -> str:
    if REST_SILENCE_INTERRUPTION_GRANT in owner_grants:
        return "rest_silence_override"
    if SOFT_INTERRUPTION_GRANT in owner_grants:
        return "soft_life_posture_override"
    return "none"


def _life_posture_block_class(no_proactive_constraint: str) -> str:
    value = no_proactive_constraint.lower()
    if "block proactive" not in value:
        return "none"
    if "style pressure" in value:
        return "soft_owner_correction"
    if "rest/silence" in value or "rest" in value or "silence" in value:
        return "rest_silence_boundary"
    if "no-pursuit" in value or "conflict" in value or "cooling" in value:
        return "hard_boundary"
    return "hard_boundary"


def _life_posture_override_allowed(grant_level: str, block_class: str) -> bool:
    if grant_level == "rest_silence_override":
        return block_class in {"soft_owner_correction", "rest_silence_boundary"}
    if grant_level == "soft_life_posture_override":
        return block_class == "soft_owner_correction"
    return False


ABSTRACT_PROACTIVE_MARKERS = readable_markers(
    "当一个人希望我",
    "如果一个人",
    "关系的意义",
    "存在方式",
    "心智",
    "架构",
    "系统",
    "人格是否",
    "情感是否",
)

QUESTION_SUFFIXES = readable_markers("？", "?")
GENERIC_ATTENTION_PATTERNS = readable_markers(
    "你现在是在忙",
    "看我一眼",
    "看我一句",
    "还愿意看我",
    "在不在",
    "想不想我",
    "能不能理我",
    "有没有空看我",
    "是不是没空",
)

def _abstract_proactive(text: str) -> bool:
    return any(marker in text for marker in ABSTRACT_PROACTIVE_MARKERS) or len(text) > 70


def _generic_attention_check(text: str) -> bool:
    return any(marker in text for marker in GENERIC_ATTENTION_PATTERNS)


def _direct_question(text: str) -> str:
    text = _one_line(text)
    if not text:
        return "none"
    if text.endswith(QUESTION_SUFFIXES):
        return text
    return text + "？"


def _shape_candidate(
    *,
    candidate: str,
    decision: str,
    selected_question: str,
    visible_posture: str,
    life_posture: str,
) -> tuple[str, str]:
    candidate = _one_line(candidate)
    if candidate in {"", "none", "unknown"}:
        return "none", "empty_candidate"
    if decision != "ask_owner":
        if _generic_attention_check(candidate):
            return "none", "generic_attention_check_blocked"
        return candidate, "non_question_candidate_preserved"

    question = _direct_question(selected_question)
    if question in {"", "none", "unknown"}:
        return "none", "missing_question_blocked_no_concrete_anchor"
    if _abstract_proactive(question):
        return "none", "abstract_question_blocked_no_concrete_anchor"
    if _generic_attention_check(question):
        return "none", "generic_attention_check_blocked"
    return question, "selected_question_as_one_bubble"


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _one_line(text: str) -> str:
    return " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split())


def _dispatch_state_path(root: Path) -> Path:
    return root / "memory/context/proactive_qq_dispatch_state.md"


def _dispatch_hold_reason(
    dispatch_state: str,
    *,
    candidate: str,
    evaluated_at: str,
    min_interval_seconds: int,
) -> str:
    last_status = extract_value(dispatch_state, "last_claim_status", "")
    if last_status not in {"claimed", "sent", "failed"}:
        return ""

    last_message = extract_value(dispatch_state, "last_claimed_message", "")
    last_at = _parse_iso(extract_value(dispatch_state, "last_claimed_at", ""))
    now = _parse_iso(evaluated_at)
    if last_message and last_message == candidate:
        if last_status == "sent":
            return "candidate_already_sent"
        if last_status == "claimed":
            return "candidate_already_claimed"
        if min_interval_seconds <= 0:
            return "candidate_failed_recently"
        if not last_at or not now:
            return "candidate_failed_recently"
        elapsed = (now - last_at).total_seconds()
        if elapsed < min_interval_seconds:
            remaining = max(0, int(min_interval_seconds - elapsed))
            return f"candidate_failed_retry_cooldown:{remaining}s"

    if min_interval_seconds <= 0:
        return ""
    if not last_at or not now:
        return ""
    elapsed = (now - last_at).total_seconds()
    if elapsed < min_interval_seconds:
        remaining = max(0, int(min_interval_seconds - elapsed))
        return f"cooldown_active:{remaining}s"
    return ""


def _write_dispatch_state(
    root: Path,
    *,
    claimed_at: str,
    claim_id: str,
    candidate: str,
    min_interval_seconds: int,
) -> None:
    text = f"""---
title: Proactive QQ Dispatch State
memory_type: proactive_qq_dispatch_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: bridge
created_at: {claimed_at}
updated_at: {claimed_at}
importance_score: 82
impact_score: 84
confidence_score: 94
status: active
tags: [initiative, proactive, qq, dispatch, boundary]
---

# Proactive QQ Dispatch State

## Last Claim
- last_claimed_at: {claimed_at}
- last_claim_id: {claim_id or "none"}
- last_claim_status: claimed
- min_interval_seconds: {min_interval_seconds}
- last_claimed_message: {_one_line(candidate)}

## Last Ack
- last_acked_at: none
- last_ack_status: pending
- adapter_message_id: none
- adapter_error: none

## Boundaries
- Claiming only prepares one outbound QQ bubble for the external adapter.
- The bridge does not bypass owner-enabled proactive QQ permission.
- Repeated claims for the same candidate are blocked.
- The external adapter must call ack after a real QQ send succeeds or fails.
"""
    write_text(_dispatch_state_path(root), text)


def _render_acknowledged_dispatch_state(
    state: str,
    *,
    acked_at: str,
    ack_status: str,
    adapter_message_id: str,
    adapter_error: str,
) -> str:
    return f"""---
title: Proactive QQ Dispatch State
memory_type: proactive_qq_dispatch_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: bridge
created_at: {extract_value(state, "last_claimed_at", acked_at)}
updated_at: {acked_at}
importance_score: 82
impact_score: 84
confidence_score: 94
status: active
tags: [initiative, proactive, qq, dispatch, boundary]
---

# Proactive QQ Dispatch State

## Last Claim
- last_claimed_at: {extract_value(state, "last_claimed_at", "none")}
- last_claim_id: {extract_value(state, "last_claim_id", "none")}
- last_claim_status: {ack_status}
- min_interval_seconds: {extract_value(state, "min_interval_seconds", "21600")}
- last_claimed_message: {extract_value(state, "last_claimed_message", "none")}

## Last Ack
- last_acked_at: {acked_at}
- last_ack_status: {ack_status}
- adapter_message_id: {_one_line(adapter_message_id) or "none"}
- adapter_error: {_one_line(adapter_error) or "none"}

## Boundaries
- Claiming only prepares one outbound QQ bubble for the external adapter.
- The bridge does not bypass owner-enabled proactive QQ permission.
- Repeated claims for the same candidate are blocked after a successful send.
- A failed ack enters the same bounded retry cooldown; the bridge must not loop the same candidate.
"""


def render_state(
    *,
    evaluated_at: str,
    mode: str,
    initiative: str,
    capability: str = "",
    life_posture_state: str = "",
    owner_grants: str = "",
) -> str:
    decision = extract_value(initiative, "decision", "defer")
    reason = extract_value(initiative, "reason", "unknown")
    selected_question = extract_value(initiative, "selected_question", "none")
    question_budget = extract_value(initiative, "question_budget", "0")
    visible_posture = extract_value(initiative, "visible_posture", "none")
    cooldown_active = extract_value(initiative, "cooldown_active", "yes")
    current_life_posture = extract_value(life_posture_state, "posture", "unknown")
    no_proactive_constraint = extract_value(life_posture_state, "no_proactive_constraint", "unchanged")
    interruption_grant_level = _interruption_grant_level(owner_grants)
    interruption_grant = interruption_grant_level != "none"
    life_posture_block_class = _life_posture_block_class(no_proactive_constraint)
    life_posture_override = _life_posture_override_allowed(
        interruption_grant_level,
        life_posture_block_class,
    )

    raw_candidate = _candidate_message(decision, selected_question, visible_posture)
    candidate, candidate_shape = _shape_candidate(
        candidate=raw_candidate,
        decision=decision,
        selected_question=selected_question,
        visible_posture=visible_posture,
        life_posture=current_life_posture,
    )
    send_enabled = _proactive_qq_enabled(capability, owner_grants)
    if cooldown_active == "yes":
        proactive_decision = "hold"
        proactive_reason = "cooldown_active"
    elif life_posture_block_class != "none" and not life_posture_override:
        proactive_decision = "hold"
        proactive_reason = "life_posture_blocks_proactive"
    elif decision in {"stay_silent", "defer", "refuse"}:
        proactive_decision = "hold"
        proactive_reason = f"initiative_decision_{decision}"
    elif candidate == "none":
        proactive_decision = "hold"
        proactive_reason = "no_safe_candidate"
    elif question_budget not in {"1", "2"} and decision == "ask_owner":
        proactive_decision = "hold"
        proactive_reason = "no_question_budget"
    else:
        proactive_decision = "candidate_ready_owner_enabled" if send_enabled else "candidate_only"
        if life_posture_override and send_enabled:
            proactive_reason = f"owner_welcomes_interruptions_{life_posture_block_class}_override"
        else:
            proactive_reason = "owner_enabled_proactive_qq_with_boundaries" if send_enabled else "safe_candidate_but_qq_send_blocked"
    qq_send_permission = (
        "owner_enabled_gated_one_short_message"
        if send_enabled
        else "blocked_until_owner_enables_proactive_qq"
    )

    return f"""---
title: Proactive Presence State
memory_type: proactive_presence_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-26T17:40:00+08:00
updated_at: {evaluated_at}
importance_score: 82
impact_score: 84
confidence_score: 94
status: active
tags: [initiative, proactive, qq, boundary]
---

# Proactive Presence State

## Last Evaluation
- evaluated_at: {evaluated_at}
- mode: {mode}
- qq_send_permission: {qq_send_permission}
- proactive_decision: {proactive_decision}
- reason: {proactive_reason}
- initiative_decision: {decision}
- initiative_reason: {reason}
- selected_question: {selected_question}
- visible_posture: {visible_posture}
- current_life_posture: {current_life_posture}
- no_proactive_constraint: {no_proactive_constraint}
- life_posture_block_class: {life_posture_block_class}
- owner_interruption_grant: {"approved" if interruption_grant else "none"}
- interruption_grant_level: {interruption_grant_level}
- life_posture_override: {"yes" if life_posture_override else "no"}
- question_budget: {question_budget}
- raw_candidate_message: {raw_candidate}
- candidate_shape: {candidate_shape}
- candidate_message: {candidate}

## Boundaries
- XinYu cannot spam owner.
- The high-interruption grant may override rest/silence and style-pressure posture holds for one short owner-private message.
- XinYu can form one candidate message from initiative state. Actual QQ sending requires owner-approved proactive mode.
- The softer interruption grant may override only soft owner-correction posture holds for one short message.
- Proactive messages must be one short message, not an interview or a technical nag.
- Proactive messages must not be generic attention checks such as asking whether owner is busy or will look at her.
- If there is no concrete daily anchor or selected concrete question, XinYu stays silent instead of inventing a filler question.
- Even with the high-interruption grant, proactive QQ still stops for no-pursuit, conflict-cooling, cooldown, duplicate-message, or spam-limit conditions.
"""


def run_proactive_presence(
    root: Path,
    *,
    evaluated_at: str | None = None,
    mode: str = "runtime_proactive_presence",
) -> dict[str, str]:
    evaluated_at = evaluated_at or datetime.now().astimezone().isoformat()
    initiative = read_text(root / "memory/context/initiative_state.md")
    capability = read_text(root / "memory/context/capability_zones_state.md")
    life_posture_state = read_text(root / "memory/context/current_life_posture.md")
    owner_grants = read_text(root / "memory/context/owner_permission_grants.md")
    state = render_state(
        evaluated_at=evaluated_at,
        mode=mode,
        initiative=initiative,
        capability=capability,
        life_posture_state=life_posture_state,
        owner_grants=owner_grants,
    )
    write_text(root / "memory/context/proactive_presence_state.md", state)
    return {
        "evaluated_at": evaluated_at,
        "proactive_decision": extract_value(state, "proactive_decision"),
        "qq_send_permission": extract_value(state, "qq_send_permission"),
        "candidate_message": extract_value(state, "candidate_message"),
    }


def claim_proactive_qq_message(
    root: Path,
    *,
    evaluated_at: str | None = None,
    mode: str = "runtime_proactive_qq_claim",
    claim: bool = False,
    claim_id: str = "",
    min_interval_seconds: int = 21600,
) -> dict[str, object]:
    evaluated_at = evaluated_at or datetime.now().astimezone().isoformat()
    result = run_proactive_presence(root, evaluated_at=evaluated_at, mode=mode)
    candidate = _one_line(str(result["candidate_message"]))
    notes = ["no_agent_turn", "no_session_created"]

    ready = (
        result["proactive_decision"] == "candidate_ready_owner_enabled"
        and result["qq_send_permission"] == "owner_enabled_gated_one_short_message"
        and candidate not in {"", "none", "unknown"}
    )
    if not ready:
        notes.append(f"not_ready:{result['proactive_decision']}")
        return {
            **result,
            "accepted": True,
            "reply": "",
            "candidate_claimed": False,
            "claim_id": claim_id,
            "notes": notes,
        }

    dispatch_state = read_text(_dispatch_state_path(root))
    hold_reason = _dispatch_hold_reason(
        dispatch_state,
        candidate=candidate,
        evaluated_at=evaluated_at,
        min_interval_seconds=min_interval_seconds,
    )
    if hold_reason:
        notes.append(hold_reason)
        return {
            **result,
            "accepted": True,
            "reply": "",
            "candidate_claimed": False,
            "claim_id": claim_id,
            "notes": notes,
        }

    if claim:
        _write_dispatch_state(
            root,
            claimed_at=evaluated_at,
            claim_id=claim_id,
            candidate=candidate,
            min_interval_seconds=min_interval_seconds,
        )
        notes.append("candidate_claimed")
        reply = candidate
    else:
        notes.append("preview_only")
        reply = ""

    return {
        **result,
        "accepted": True,
        "reply": reply,
        "preview_reply": candidate,
        "candidate_claimed": claim,
        "claim_id": claim_id,
        "notes": notes,
    }


def acknowledge_proactive_qq_message(
    root: Path,
    *,
    acked_at: str | None = None,
    claim_id: str = "",
    ack_status: str = "sent",
    adapter_message_id: str = "",
    adapter_error: str = "",
) -> dict[str, object]:
    acked_at = acked_at or datetime.now().astimezone().isoformat()
    ack_status = ack_status.strip().lower()
    notes = ["no_agent_turn", "no_session_created"]

    if ack_status not in {"sent", "failed"}:
        return {
            "accepted": False,
            "ack_recorded": False,
            "claim_id": claim_id,
            "ack_status": ack_status,
            "notes": notes + ["invalid_ack_status"],
        }

    state = read_text(_dispatch_state_path(root))
    last_claim_id = extract_value(state, "last_claim_id", "")
    if not state or last_claim_id in {"", "none", "unknown"}:
        return {
            "accepted": True,
            "ack_recorded": False,
            "claim_id": claim_id,
            "ack_status": ack_status,
            "notes": notes + ["no_claim_to_ack"],
        }
    if claim_id and last_claim_id != claim_id:
        return {
            "accepted": True,
            "ack_recorded": False,
            "claim_id": claim_id,
            "expected_claim_id": last_claim_id,
            "ack_status": ack_status,
            "notes": notes + ["claim_id_mismatch"],
        }

    write_text(
        _dispatch_state_path(root),
        _render_acknowledged_dispatch_state(
            state,
            acked_at=acked_at,
            ack_status=ack_status,
            adapter_message_id=adapter_message_id,
            adapter_error=adapter_error,
        ),
    )
    return {
        "accepted": True,
        "ack_recorded": True,
        "claim_id": last_claim_id,
        "ack_status": ack_status,
        "adapter_message_id": _one_line(adapter_message_id) or "none",
        "notes": notes + ["ack_recorded"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a gated proactive QQ presence candidate without sending.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_proactive_presence(args.root.resolve())
    print("Proactive presence state written")
    print(f"proactive_decision: {result['proactive_decision']}")
    print(f"qq_send_permission: {result['qq_send_permission']}")
    print(f"candidate_message: {result['candidate_message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
