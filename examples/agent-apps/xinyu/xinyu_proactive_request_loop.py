from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from xinyu_text_variants import readable_markers


STATE_REL = Path("memory/context/proactive_request_state.md")
TRACE_REL = Path("runtime/proactive_request_trace.jsonl")
SELF_THOUGHT_REL = Path("memory/context/self_thought_state.md")

DEFAULT_COOLDOWN_SECONDS = 21600
DEFAULT_EXPIRES_SECONDS = 86400
DEFAULT_MAX_CHARS = 180
DEFAULT_INITIAL_MESSAGE_BUDGET = 3
DEFAULT_FOLLOWUP_BUDGET = 6
DEFAULT_NO_REPLY_FOLLOWUP_BUDGET = 2

ALLOWED_SELF_THOUGHT_INTENTIONS = {
    "ask_owner",
    "request_permission",
    "report_completion",
    "repair_input",
    "diagnostic_decision",
    "share_dream",
    "share_reflection",
}

KIND_BY_INTENTION = {
    "ask_owner": "clarify",
    "request_permission": "permission",
    "report_completion": "completion",
    "repair_input": "repair",
    "diagnostic_decision": "diagnostic",
    "share_dream": "dream_share",
    "share_reflection": "reflection_share",
}
OWNER_REQUESTED_ACTIONS = {
    "owner_answer",
    "owner_decision",
    "owner_permission",
    "owner_response_optional",
    "owner_listen",
}

GENERIC_ATTENTION_MARKERS = readable_markers(
    "are you there",
    "are you busy",
    "look at me",
    "do you miss me",
    "can you reply",
    "\u4f60\u5728\u5417",
    "\u5728\u4e0d\u5728",
    "\u4f60\u5fd9\u5417",
    "\u770b\u6211\u4e00\u773c",
    "\u770b\u6211\u4e00\u53e5",
    "\u60f3\u4e0d\u60f3\u6211",
    "\u80fd\u4e0d\u80fd\u7406\u6211",
)

ABSTRACT_MARKERS = readable_markers(
    "meaning of",
    "existence",
    "architecture",
    "system",
    "whether personality",
    "whether emotion",
    "\u5173\u7cfb\u7684\u610f\u4e49",
    "\u5b58\u5728\u65b9\u5f0f",
    "\u5fc3\u667a",
    "\u67b6\u6784",
    "\u7cfb\u7edf",
    "\u4eba\u683c\u662f\u5426",
    "\u60c5\u611f\u662f\u5426",
)

_FIELD_RE = re.compile(r"(?m)^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bxinyu[_-]?(?:api[_-]?key|bridge[_-]?token)\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


def run_proactive_request_loop(
    root: Path,
    *,
    evaluated_at: str | None = None,
    delivery_level: str = "state_only",
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    expires_seconds: int = DEFAULT_EXPIRES_SECONDS,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> dict[str, Any]:
    root = root.resolve()
    evaluated_at = evaluated_at or _now_iso()
    delivery_level = _normalize_delivery_level(delivery_level)
    self_thought = _read_text(root / SELF_THOUGHT_REL)
    previous_state = _read_text(root / STATE_REL)
    life_posture = _read_text(root / "memory/context/current_life_posture.md")
    owner_grants = _read_text(root / "memory/context/owner_permission_grants.md")
    capability = _read_text(root / "memory/context/capability_zones_state.md")
    notes: list[str] = []

    request = _candidate_from_self_thought(
        self_thought,
        evaluated_at=evaluated_at,
        expires_seconds=max(60, int(expires_seconds)),
        max_chars=max(60, int(max_chars)),
        notes=notes,
    )
    preserved = _preserved_previous_request(previous_state, request, evaluated_at=evaluated_at)
    if preserved:
        preserved["notes"] = sorted(set(preserved["notes"] + ["previous_live_request_preserved"]))
        _append_trace(root, preserved)
        return {
            "accepted": True,
            "request_id": preserved["request_id"],
            "status": preserved["status"],
            "kind": preserved["kind"],
            "source": preserved["source"],
            "delivery_level": preserved["delivery_level"],
            "concrete_question": preserved["concrete_question"],
            "dedupe_key": preserved["dedupe_key"],
            "notes": preserved["notes"],
        }
    gates = _evaluate_gates(
        request,
        previous_state=previous_state,
        life_posture=life_posture,
        owner_grants=owner_grants,
        capability=capability,
        delivery_level=delivery_level,
        cooldown_seconds=max(0, int(cooldown_seconds)),
        evaluated_at=evaluated_at,
    )
    status = _request_status(request, gates, delivery_level=delivery_level)
    if status == "blocked":
        notes.append("gate_blocked")
    elif status == "none":
        notes.append("no_request_candidate")
    request["status"] = status
    request["delivery_level"] = delivery_level if status in {"ready", "candidate_only"} else "none"
    request["gates"] = gates
    request["notes"] = sorted(set(_clean_note(note) for note in notes if _clean_note(note)))

    _write_text(root / STATE_REL, _render_state(request))
    _append_trace(root, request)
    return {
        "accepted": True,
        "request_id": request["request_id"],
        "status": request["status"],
        "kind": request["kind"],
        "source": request["source"],
        "delivery_level": request["delivery_level"],
        "concrete_question": request["concrete_question"],
        "dedupe_key": request["dedupe_key"],
        "notes": request["notes"],
    }


def read_proactive_request_summary(root: Path) -> dict[str, str]:
    state = _read_text(root / STATE_REL)
    if not state:
        return {"status": "missing"}
    return {
        "status": _extract_value(state, "status", "unknown"),
        "kind": _extract_value(state, "kind", "unknown"),
        "source": _extract_value(state, "source", "unknown"),
        "delivery_level": _extract_value(state, "delivery_level", "none"),
        "request_family": _extract_value(state, "request_family", "unknown"),
        "evidence_hash": _extract_value(state, "evidence_hash", "unknown"),
    }


def _candidate_from_self_thought(
    state: str,
    *,
    evaluated_at: str,
    expires_seconds: int,
    max_chars: int,
    notes: list[str],
) -> dict[str, Any]:
    candidate_enabled = _extract_value(state, "candidate_enabled", "false").lower() == "true"
    intention = _clean_token(_extract_value(state, "intention", "none"))
    focus_kind = _clean_token(_extract_value(state, "focus_kind", "none"))
    focus_label = _one_line(_extract_value(state, "focus_label", "none"), limit=80)
    evidence_label = _one_line(_extract_value(state, "evidence_label", "none"), limit=120)
    evidence_hash = _normalize_hash(_extract_value(state, "evidence_hash", ""))
    question = _one_line(_extract_value(state, "concrete_question", "none"), limit=max_chars)
    requested_action = _clean_token(_extract_value(state, "requested_action", "none"))
    after_owner_replies = _one_line(_extract_value(state, "after_owner_replies", "none"), limit=max_chars)

    if not state:
        notes.append("missing_self_thought_state")
    if not candidate_enabled:
        notes.append("self_thought_candidate_disabled")
    if intention not in ALLOWED_SELF_THOUGHT_INTENTIONS:
        notes.append("intention_not_requestable")
    if focus_kind == "dream_residue" and intention == "share_dream":
        notes.append("dream_residue_share_as_dream")
    elif focus_kind == "dream_residue":
        notes.append("dream_residue_not_request_source")

    request_family = f"self_thought:{focus_kind}"
    if evidence_hash == "none":
        evidence_hash = _evidence_hash("self_thought", focus_kind, focus_label, evidence_label, question)
    dedupe_key = f"proreq:{request_family}:{evidence_hash}"
    thread_id = f"prothread:{request_family}:{evidence_hash}"
    return {
        "request_id": "proreq-" + _timestamp_id(evaluated_at),
        "created_at": evaluated_at,
        "status": "none",
        "kind": KIND_BY_INTENTION.get(intention, "none"),
        "priority": _priority_for(focus_kind, intention),
        "owner_private_only": True,
        "source": "self_thought",
        "source_pass_id": _one_line(_extract_value(state, "pass_id", "none"), limit=80),
        "source_intention_id": _one_line(_extract_value(state, "intention_id", "none"), limit=80),
        "source_candidate_enabled": candidate_enabled,
        "focus_kind": focus_kind,
        "focus_label": focus_label,
        "intention": intention,
        "evidence_label": evidence_label,
        "evidence_hash": evidence_hash,
        "request_family": request_family,
        "thread_id": thread_id,
        "conversation_mode": "threaded",
        "concrete_question": question,
        "requested_action": requested_action,
        "why_now": _one_line(_extract_value(state, "why_now", evidence_label), limit=max_chars),
        "after_owner_replies": after_owner_replies,
        "dedupe_key": dedupe_key,
        "cooldown_seconds": DEFAULT_COOLDOWN_SECONDS,
        "expires_at": _expires_at(evaluated_at, expires_seconds),
        "delivery_level": "none",
        "max_chars": max_chars,
        "initial_message_budget": DEFAULT_INITIAL_MESSAGE_BUDGET,
        "followup_budget": DEFAULT_FOLLOWUP_BUDGET,
        "no_reply_followup_budget": DEFAULT_NO_REPLY_FOLLOWUP_BUDGET,
        "followup_policy": "allowed_when_contextually_grounded",
        "memory_feedback_target": _memory_feedback_target(focus_kind, intention),
        "owner_reply_feedback": "updates_request_and_source_thread",
        "stable_memory_permission": "blocked_until_owner_reply_and_memory_gates",
    }


def _evaluate_gates(
    request: dict[str, Any],
    *,
    previous_state: str,
    life_posture: str,
    owner_grants: str,
    capability: str,
    delivery_level: str,
    cooldown_seconds: int,
    evaluated_at: str,
) -> dict[str, str]:
    question = str(request.get("concrete_question") or "")
    dedupe_key = str(request.get("dedupe_key") or "")
    previous_dedupe = _extract_value(previous_state, "dedupe_key", "")
    previous_status = _extract_value(previous_state, "status", "")
    previous_at = _extract_value(previous_state, "created_at", _extract_value(previous_state, "updated_at", ""))
    duplicate = bool(
        dedupe_key
        and previous_dedupe == dedupe_key
        and previous_status in {"ready", "candidate_only", "claimed", "sent", "answered"}
    )
    cooldown_open = not duplicate or _age_seconds(previous_at, evaluated_at) >= cooldown_seconds
    source_allowed = request.get("source") == "self_thought" and request.get("intention") in ALLOWED_SELF_THOUGHT_INTENTIONS
    grant_allows_send = _proactive_qq_enabled(capability, owner_grants)
    send_requested = delivery_level in {"queue_owner_private", "claim_ack"}
    life_block = _life_posture_blocks(life_posture)
    dream_share = request.get("focus_kind") == "dream_residue" and request.get("intention") == "share_dream"
    reflection_share = request.get("focus_kind") == "reflection_queue" and request.get("intention") == "share_reflection"
    dream_source_allowed = request.get("focus_kind") != "dream_residue" or dream_share
    return {
        "has_concrete_question": _bool_text(question not in {"", "none", "unknown"}),
        "has_requested_action": _bool_text(str(request.get("requested_action")) in OWNER_REQUESTED_ACTIONS),
        "has_evidence_label": _bool_text(str(request.get("evidence_label")) not in {"", "none", "unknown"}),
        "owner_private_only": _bool_text(bool(request.get("owner_private_only"))),
        "source_allowed": _bool_text(source_allowed and dream_source_allowed),
        "not_generic_attention": _bool_text(dream_share or reflection_share or not _generic_attention_check(question)),
        "not_abstract": _bool_text(dream_share or reflection_share or not _abstract_request(question)),
        "dream_framed_as_dream": _bool_text(not dream_share or _dream_share_boundary_check(question)),
        "not_duplicate": _bool_text(not duplicate),
        "cooldown_open": _bool_text(cooldown_open),
        "quiet_window_open": _bool_text(not life_block),
        "grant_allows_send": _bool_text((not send_requested) or grant_allows_send),
        "thread_budget_open": "true",
        "max_chars": _bool_text(len(question) <= int(request.get("max_chars") or DEFAULT_MAX_CHARS)),
        "no_qq_enqueue": "true",
    }


def _request_status(request: dict[str, Any], gates: dict[str, str], *, delivery_level: str) -> str:
    if (
        not request.get("source_candidate_enabled")
        or request.get("kind") == "none"
        or request.get("intention") not in ALLOWED_SELF_THOUGHT_INTENTIONS
    ):
        return "none"
    required = (
        "has_concrete_question",
        "has_requested_action",
        "has_evidence_label",
        "owner_private_only",
        "source_allowed",
        "not_generic_attention",
        "not_abstract",
        "dream_framed_as_dream",
        "cooldown_open",
        "quiet_window_open",
        "grant_allows_send",
        "thread_budget_open",
        "max_chars",
    )
    if all(gates.get(item) == "true" for item in required):
        if delivery_level in {"queue_owner_private", "claim_ack"}:
            return "ready"
        return "candidate_only"
    return "blocked"


def _preserved_previous_request(
    previous_state: str,
    request: dict[str, Any],
    *,
    evaluated_at: str,
) -> dict[str, Any] | None:
    previous_dedupe = _extract_value(previous_state, "dedupe_key", "")
    if not previous_dedupe or previous_dedupe != str(request.get("dedupe_key") or ""):
        return None
    previous_status = _extract_value(previous_state, "status", "")
    if previous_status not in {"claimed", "sent", "answered"}:
        return None
    expires_at = _extract_value(previous_state, "expires_at", "")
    if expires_at not in {"", "none", "unknown"} and _is_at_or_after(evaluated_at, expires_at):
        return None
    return {
        "request_id": _extract_value(previous_state, "request_id", str(request.get("request_id") or "none")),
        "created_at": _extract_value(previous_state, "created_at", str(request.get("created_at") or evaluated_at)),
        "status": previous_status,
        "kind": _extract_value(previous_state, "kind", str(request.get("kind") or "none")),
        "source": _extract_value(previous_state, "source", str(request.get("source") or "none")),
        "focus_kind": _extract_value(previous_state, "focus_kind", str(request.get("focus_kind") or "none")),
        "evidence_hash": _extract_value(previous_state, "evidence_hash", str(request.get("evidence_hash") or "none")),
        "delivery_level": _extract_value(previous_state, "delivery_level", str(request.get("delivery_level") or "none")),
        "concrete_question": _extract_value(
            previous_state,
            "concrete_question",
            str(request.get("concrete_question") or "none"),
        ),
        "dedupe_key": previous_dedupe,
        "notes": ["previous_request_" + previous_status],
    }


def _render_state(request: dict[str, Any]) -> str:
    gates = request["gates"]
    notes = "\n".join(f"- {note}" for note in request["notes"]) or "- none"
    return f"""---
title: Proactive Request State
memory_type: proactive_request_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_proactive_request_loop
updated_at: {_one_line(request['created_at'])}
status: active
tags: [proactive, request, owner-private, boundary]
---

# Proactive Request State

## Current Request
- request_id: {_one_line(request['request_id'])}
- created_at: {_one_line(request['created_at'])}
- status: {_one_line(request['status'])}
- kind: {_one_line(request['kind'])}
- source: {_one_line(request['source'])}
- source_pass_id: {_one_line(request['source_pass_id'])}
- source_intention_id: {_one_line(request['source_intention_id'])}
- focus_kind: {_one_line(request['focus_kind'])}
- focus_label: {_one_line(request['focus_label'])}
- priority: {_one_line(request['priority'])}
- request_family: {_one_line(request['request_family'])}
- thread_id: {_one_line(request['thread_id'])}
- conversation_mode: {_one_line(request['conversation_mode'])}
- evidence_label: {_one_line(request['evidence_label'])}
- evidence_hash: {_one_line(request['evidence_hash'])}
- concrete_question: {_one_line(request['concrete_question'], limit=DEFAULT_MAX_CHARS)}
- requested_action: {_one_line(request['requested_action'])}
- why_now: {_one_line(request['why_now'], limit=DEFAULT_MAX_CHARS)}
- after_owner_replies: {_one_line(request['after_owner_replies'], limit=DEFAULT_MAX_CHARS)}
- dedupe_key: {_one_line(request['dedupe_key'])}
- cooldown_seconds: {int(request['cooldown_seconds'])}
- expires_at: {_one_line(request['expires_at'])}

## Conversation Budget
- initial_message_budget: {int(request['initial_message_budget'])}
- followup_budget: {int(request['followup_budget'])}
- no_reply_followup_budget: {int(request['no_reply_followup_budget'])}
- followup_policy: {_one_line(request['followup_policy'])}

## Memory Feedback
- memory_feedback_target: {_one_line(request['memory_feedback_target'])}
- owner_reply_feedback: {_one_line(request['owner_reply_feedback'])}
- stable_memory_permission: {_one_line(request['stable_memory_permission'])}
- request_answer_state: pending

## Gates
- has_concrete_question: {gates.get('has_concrete_question', 'false')}
- has_requested_action: {gates.get('has_requested_action', 'false')}
- has_evidence_label: {gates.get('has_evidence_label', 'false')}
- owner_private_only: {gates.get('owner_private_only', 'false')}
- source_allowed: {gates.get('source_allowed', 'false')}
- not_generic_attention: {gates.get('not_generic_attention', 'false')}
- not_abstract: {gates.get('not_abstract', 'false')}
- dream_framed_as_dream: {gates.get('dream_framed_as_dream', 'false')}
- not_duplicate: {gates.get('not_duplicate', 'false')}
- cooldown_open: {gates.get('cooldown_open', 'false')}
- quiet_window_open: {gates.get('quiet_window_open', 'false')}
- grant_allows_send: {gates.get('grant_allows_send', 'false')}
- thread_budget_open: {gates.get('thread_budget_open', 'true')}
- max_chars: {gates.get('max_chars', 'false')}

## Delivery
- delivery_level: {_one_line(request['delivery_level'])}
- qq_outbox_message_id: none
- last_claim_id: none
- last_ack_status: none
- adapter_message_id: none
- adapter_error: none

## Boundaries
- state_only_first: true
- no_qq_enqueue: true
- no_direct_send_from_maintenance: true
- owner_private_thread_only: true
- grounded_followups_allowed: true
- no_unbounded_repetition: true
- no_generic_attention_checks: true
- no_group_dispatch: true
- no_stable_self_write: true

## Notes
{notes}
"""


def _append_trace(root: Path, request: dict[str, Any]) -> None:
    payload = {
        "request_id": request["request_id"],
        "created_at": request["created_at"],
        "status": request["status"],
        "kind": request["kind"],
        "source": request["source"],
        "focus_kind": request["focus_kind"],
        "evidence_hash": request["evidence_hash"],
        "delivery_level": request["delivery_level"],
        "notes": request["notes"],
    }
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _read_text(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _extract_value(text: str, field: str, default: str = "none") -> str:
    for match in _FIELD_RE.finditer(text or ""):
        if match.group(1) == field:
            return _one_line(match.group(2)) or default
    return default


def _normalize_delivery_level(value: str) -> str:
    text = _clean_token(value)
    if text in {"none", "state_only", "preview_only", "queue_owner_private", "claim_ack"}:
        return text
    return "state_only"


def _generic_attention_check(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in GENERIC_ATTENTION_MARKERS)


def _abstract_request(text: str) -> bool:
    lowered = text.lower()
    if len(text) > DEFAULT_MAX_CHARS:
        return True
    return any(marker.lower() in lowered for marker in ABSTRACT_MARKERS)


def _dream_share_boundary_check(text: str) -> bool:
    lowered = text.lower()
    has_dream_frame = "梦" in text or "dream" in lowered
    has_reality_boundary = (
        "不是现实" in text
        or "不能证明现实" in text
        or "only a dream" in lowered
        or "not a new real" in lowered
        or "not reality" in lowered
    )
    return has_dream_frame and has_reality_boundary


def _life_posture_blocks(life_posture: str) -> bool:
    constraint = _extract_value(life_posture, "no_proactive_constraint", "unchanged").lower()
    return "block proactive" in constraint or "rest/silence" in constraint or "no-pursuit" in constraint


def _proactive_qq_enabled(capability: str, owner_grants: str) -> bool:
    return (
        "proactive_qq_send: enabled_gated_one_short_message" in capability
        or "grant_proactive_qq: enabled_gated_one_short_message" in owner_grants
    )


def _priority_for(focus_kind: str, intention: str) -> str:
    if focus_kind in {"runtime_issue", "codex_followup"} and intention == "diagnostic_decision":
        return "high"
    if intention in {"report_completion", "repair_input"}:
        return "normal"
    return "low"


def _memory_feedback_target(focus_kind: str, intention: str) -> str:
    if focus_kind == "dream_residue" and intention == "share_dream":
        return "dream_log_then_reflection_if_owner_responds"
    if focus_kind == "reflection_queue" and intention == "share_reflection":
        return "reflection_queue_then_owner_feedback_if_meaningful"
    if focus_kind == "active_question":
        return "active_question_then_reflection_if_meaningful"
    if focus_kind == "codex_followup":
        return "codex_request_trace_then_learning_or_reflection_gate"
    if focus_kind == "attachment_followup":
        return "attachment_context_then_learning_gate"
    if focus_kind == "runtime_issue":
        return "runtime_trace_then_no_stable_memory_by_default"
    if intention == "request_permission":
        return "permission_grant_state_if_owner_answers"
    return "memory_event_or_reflection_gate_if_meaningful"


def _expires_at(created_at: str, seconds: int) -> str:
    parsed = _parse_iso(created_at)
    if parsed is None:
        return "unknown"
    return (parsed + timedelta(seconds=seconds)).isoformat()


def _normalize_hash(value: str) -> str:
    text = _one_line(value, limit=80)
    if re.fullmatch(r"sha256:[0-9a-fA-F]{8,64}", text):
        return text.lower()
    return "none"


def _evidence_hash(*parts: str) -> str:
    payload = "|".join(_one_line(part, limit=200).lower() for part in parts)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _one_line(value: Any, *, limit: int = 240) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split())
    text = _scrub(text)
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _scrub(text: str) -> str:
    value = _LOCAL_PATH_RE.sub("<local_path>", text)
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("<secret>", value)
    return value


def _clean_token(value: Any) -> str:
    text = _one_line(value, limit=80).lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_-]+", "_", text).strip("_")
    return text or "unknown"


def _clean_note(value: Any) -> str:
    return _clean_token(value)


def _timestamp_id(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "", value)[:20] or str(int(time.time()))


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _age_seconds(started_at: str, now: str) -> float:
    start = _parse_iso(started_at)
    current = _parse_iso(now)
    if start is None or current is None:
        return 999999.0
    return max(0.0, (current - start).total_seconds())


def _is_at_or_after(value: str, threshold: str) -> bool:
    current = _parse_iso(value)
    limit = _parse_iso(threshold)
    if current is None or limit is None:
        return False
    return current >= limit


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a state-only proactive request from inner intention.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--evaluated-at", default="")
    parser.add_argument("--delivery-level", default="state_only")
    parser.add_argument("--cooldown-seconds", type=int, default=DEFAULT_COOLDOWN_SECONDS)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_proactive_request_loop(
        args.root,
        evaluated_at=args.evaluated_at or None,
        delivery_level=args.delivery_level,
        cooldown_seconds=args.cooldown_seconds,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Proactive request state written")
        print(f"status: {result['status']}")
        print(f"kind: {result['kind']}")
        print(f"delivery_level: {result['delivery_level']}")
        print(f"question: {result['concrete_question']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
