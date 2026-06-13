from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from xinyu_autonomous_outward_action_store import append_autonomous_outward_event
from xinyu_autonomous_outward_action_store import read_autonomous_outward_json
from xinyu_autonomous_outward_action_store import read_autonomous_outward_jsonl_rows
from xinyu_autonomous_outward_action_store import read_autonomous_outward_text
from xinyu_autonomous_outward_action_store import write_autonomous_outward_text
from xinyu_private_ecosystem_grants import load_grants, share_block_reasons, share_grant
from xinyu_proactive_direct_sender import send_proactive_direct
from xinyu_proactive_request_loop import run_owner_long_idle_request_loop


STATE_REL = Path("memory/context/autonomous_outward_action_state.md")
TRACE_REL = Path("runtime/autonomous_outward_action_trace.jsonl")
LEDGER_REL = Path("runtime/autonomous_outward_action/ledger.jsonl")

OWNER_ONLY_GRANT = "grant_autonomous_owner_private_outward_action: approved_owner_only_rate_limited_one_short_message"
PROACTIVE_CAPABILITY = "proactive_qq_send: enabled_gated_one_short_message"
PROACTIVE_GRANT = "grant_proactive_qq: enabled_gated_one_short_message"

DEFAULT_MIN_INTERVAL_SECONDS = 300   # 5 min dedup only; quality gate controls actual frequency
DEFAULT_MAX_MESSAGES_PER_DAY = 3
DEFAULT_QUIET_HOURS = "00:00-06:00"
NONE_VALUES = {"", "none", "unknown", "missing", "null"}
OWNER_GRANT_MAX_MESSAGES_PER_DAY = 3
OWNER_LONG_IDLE_MINUTES = 90
OWNER_LONG_IDLE_DIRECT_BLOCK = "owner_long_idle_direct_send_disabled"


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
    text = re.sub(r"(?i)\b(?:authorization|api[_-]?key|token|password|cookie)\s*[:=]\s*[^\s<>'\"]+", "<secret>", text)
    text = re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)\bsk-[a-z0-9_-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+", "<local_path>", text)
    if not text:
        return default
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _read_text(path: Path) -> str:
    return read_autonomous_outward_text(path)


def _write_text(path: Path, text: str) -> None:
    write_autonomous_outward_text(path, text)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    append_autonomous_outward_event(path, row)


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        match = re.search(rf"(?m)^\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    return _one_line(match.group(1), limit=320, default=default) if match else default


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _parse_dt(value: str) -> datetime | None:
    text = _safe_str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _owner_ids(root: Path) -> list[str]:
    data = read_autonomous_outward_json(root / "xinyu_qq_gateway.config.json", default=None)
    raw = data.get("owner_user_ids") if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return []
    return [_one_line(item, limit=80, default="") for item in raw if _one_line(item, limit=80, default="")]


def _grant_present(root: Path) -> bool:
    grants = _read_text(root / "memory/context/owner_permission_grants.md")
    return OWNER_ONLY_GRANT in grants


def _proactive_capability_present(root: Path) -> bool:
    capability = _read_text(root / "memory/context/capability_zones_state.md")
    grants = _read_text(root / "memory/context/owner_permission_grants.md")
    return PROACTIVE_CAPABILITY in capability or PROACTIVE_GRANT in grants


def _self_thought_candidate_ready(root: Path) -> bool:
    state = _read_text(root / "memory/context/self_thought_state.md")
    return (
        _field(state, "candidate_enabled", "false").lower() == "true"
        and _field(state, "owner_is_right_recipient", "false").lower() == "true"
        and _field(state, "concrete_question", "none") not in NONE_VALUES
        and _field(state, "requested_action", "none") not in NONE_VALUES
    )


def _proactive_request_candidate_ready(root: Path) -> bool:
    state = _read_text(root / "memory/context/proactive_request_state.md")
    if _field(state, "status", "none") != "ready":
        return False
    if _field(state, "delivery_level", "none") not in {"queue_owner_private", "claim_ack"}:
        return False
    return _field(state, "concrete_question", "none") not in NONE_VALUES


def _proactive_request_source(root: Path) -> str:
    state = _read_text(root / "memory/context/proactive_request_state.md")
    source = _field(state, "source", "none")
    focus = _field(state, "focus_kind", "none")
    if source == "owner_long_idle" or focus == "owner_long_idle":
        return "owner_long_idle"
    return source


def _candidate_ready(root: Path) -> bool:
    return _self_thought_candidate_ready(root) or _proactive_request_candidate_ready(root)


def _waiting_owner(root: Path) -> bool:
    state = _read_text(root / "memory/context/proactive_request_state.md")
    status = _field(state, "status", "none")
    answer_state = _field(state, "request_answer_state", "none")
    if status == "answered" or answer_state == "owner_replied":
        return False
    return (
        answer_state == "sent_waiting_owner_reply"
        or status in {"queued_qq", "sent", "claimed"}
        or (status not in {"none", "ready", "candidate_only", "blocked", "failed"} and _field(state, "last_ack_status", "none") in {"queued", "sent"})
    )


def _parse_quiet_hours(value: str) -> tuple[time, time] | None:
    text = value.strip()
    if not text:
        return None
    match = re.match(r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$", text)
    if not match:
        return None
    start_h, start_m, end_h, end_m = [int(part) for part in match.groups()]
    if not (0 <= start_h <= 23 and 0 <= end_h <= 23 and 0 <= start_m <= 59 and 0 <= end_m <= 59):
        return None
    return time(start_h, start_m), time(end_h, end_m)


def _in_quiet_hours(evaluated_at: str, quiet_hours: str) -> bool:
    parsed = _parse_quiet_hours(quiet_hours)
    if parsed is None:
        return False
    observed = _parse_dt(evaluated_at)
    if observed is None:
        observed = datetime.now().astimezone()
    current = observed.timetz().replace(tzinfo=None)
    start, end = parsed
    if start <= end:
        return start <= current < end
    return current >= start or current < end


def _ledger_rows(root: Path) -> list[dict[str, Any]]:
    return list(read_autonomous_outward_jsonl_rows(root / LEDGER_REL))


def _sent_count_last_day(root: Path, evaluated_at: str) -> int:
    observed = _parse_dt(evaluated_at) or datetime.now().astimezone()
    if observed.tzinfo is None:
        observed = observed.astimezone()
    start = observed - timedelta(hours=24)
    count = 0
    for row in _ledger_rows(root):
        if row.get("event_kind") != "autonomous_outward_action":
            continue
        if not bool(row.get("queued")):
            continue
        event_time = _parse_dt(_safe_str(row.get("evaluated_at")))
        if event_time is None:
            continue
        if event_time.tzinfo is None:
            event_time = event_time.astimezone()
        if start <= event_time <= observed:
            count += 1
    return count


def _owner_idle_minutes(root: Path, evaluated_at: str) -> int:
    state = _read_text(root / "memory/context/interaction_journal_state.md")
    stored_minutes = _int_value(_field(state, "minutes_since_last_owner_private", "-1"), -1)
    last_owner_at = _field(state, "last_owner_private_at", "none")
    last_owner_dt = _parse_dt(last_owner_at)
    observed = _parse_dt(evaluated_at)
    if last_owner_dt is None or observed is None:
        return stored_minutes
    if last_owner_dt.tzinfo is None:
        last_owner_dt = last_owner_dt.astimezone()
    if observed.tzinfo is None:
        observed = observed.astimezone()
    computed = max(0, int((observed - last_owner_dt).total_seconds() // 60))
    return max(stored_minutes, computed)


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _share_policy(root: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        grants = load_grants(root)
    except Exception:
        return {}, ["owner_private_autonomous_share_unreadable"]
    return share_grant(grants), share_block_reasons(grants)


def _owner_long_idle_due(root: Path, evaluated_at: str) -> bool:
    return _owner_idle_minutes(root, evaluated_at) >= OWNER_LONG_IDLE_MINUTES


def _ensure_prepared_outward_request(root: Path, *, evaluated_at: str, prepare_request: bool) -> dict[str, Any]:
    if not prepare_request:
        return {"prepared": False, "source": "caller_prepared"}
    if _proactive_request_candidate_ready(root):
        return {"prepared": False, "source": "proactive_request"}
    if _self_thought_candidate_ready(root):
        return {"prepared": False, "source": "self_thought"}
    if not _owner_long_idle_due(root, evaluated_at):
        return {"prepared": False, "source": "none"}
    request = run_owner_long_idle_request_loop(
        root,
        evaluated_at=evaluated_at,
        delivery_level="queue_owner_private",
    )
    return {
        "prepared": request.get("status") in {"ready", "candidate_only"},
        "source": "owner_long_idle",
        "status": _one_line(request.get("status"), limit=80),
        "request_id": _one_line(request.get("request_id"), limit=120),
        "notes": list(request.get("notes", []))[:4],
    }


def evaluate_autonomous_outward_policy(
    root: Path,
    *,
    evaluated_at: str | None = None,
    max_messages_per_day: int = DEFAULT_MAX_MESSAGES_PER_DAY,
    quiet_hours: str = DEFAULT_QUIET_HOURS,
) -> dict[str, Any]:
    root = Path(root).resolve()
    evaluated_at = evaluated_at or _now_iso()
    max_messages_per_day = min(max(0, int(max_messages_per_day)), OWNER_GRANT_MAX_MESSAGES_PER_DAY)
    grant_present = _grant_present(root)
    proactive_capability = _proactive_capability_present(root)
    owner_ids = _owner_ids(root)
    candidate_ready = _candidate_ready(root)
    waiting_owner = _waiting_owner(root)
    quiet = _in_quiet_hours(evaluated_at, quiet_hours)
    sent_last_day = _sent_count_last_day(root, evaluated_at)
    share_section, share_blocks = _share_policy(root)

    blocks: list[str] = []
    blocks.extend(share_blocks)
    if not grant_present:
        blocks.append("owner_only_auto_send_grant_missing")
    if not proactive_capability:
        blocks.append("proactive_qq_capability_missing")
    if not owner_ids:
        blocks.append("owner_private_target_missing")
    if not candidate_ready:
        blocks.append("self_thought_candidate_not_ready")
    if _proactive_request_source(root) == "owner_long_idle":
        blocks.append(OWNER_LONG_IDLE_DIRECT_BLOCK)
    if waiting_owner:
        blocks.append("waiting_for_owner_reply")
    if quiet:
        blocks.append("quiet_hours")
    if sent_last_day >= max_messages_per_day:
        blocks.append("daily_budget_exhausted")

    return {
        "allowed": not blocks,
        "evaluated_at": evaluated_at,
        "grant_present": grant_present,
        "proactive_capability": proactive_capability,
        "owner_private_target_count": len(owner_ids),
        "share_active": not share_blocks,
        "share_enabled": bool(share_section.get("enabled")),
        "share_paused": bool(share_section.get("paused", True)),
        "candidate_ready": candidate_ready,
        "waiting_owner": waiting_owner,
        "quiet_hours": quiet_hours,
        "quiet_hours_active": quiet,
        "sent_count_last_24h": sent_last_day,
        "max_messages_per_day": max_messages_per_day,
        "blocks": blocks,
    }


def _message_hash(send_result: dict[str, Any]) -> str:
    text = _safe_str(send_result.get("message_preview"))
    if not text:
        return "none"
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def run_autonomous_outward_action_tick(
    root: Path,
    *,
    evaluated_at: str | None = None,
    min_interval_seconds: int = DEFAULT_MIN_INTERVAL_SECONDS,
    max_messages_per_day: int = DEFAULT_MAX_MESSAGES_PER_DAY,
    quiet_hours: str = DEFAULT_QUIET_HOURS,
    dry_run: bool = False,
    prepare_request: bool = True,
) -> dict[str, Any]:
    root = Path(root).resolve()
    evaluated_at = evaluated_at or _now_iso()
    _share_section, share_blocks = _share_policy(root)
    prepared_request = (
        {"prepared": False, "source": "share_inactive", "notes": share_blocks}
        if share_blocks
        else _ensure_prepared_outward_request(
            root,
            evaluated_at=evaluated_at,
            prepare_request=prepare_request,
        )
    )
    policy = evaluate_autonomous_outward_policy(
        root,
        evaluated_at=evaluated_at,
        max_messages_per_day=max_messages_per_day,
        quiet_hours=quiet_hours,
    )
    send_result: dict[str, Any] = {}
    if policy["allowed"]:
        send_result = send_proactive_direct(
            root,
            evaluated_at=evaluated_at,
            min_interval_seconds=max(0, int(min_interval_seconds)),
            claim_id="auto-owner-private-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S"),
            dry_run=dry_run,
            prepare_request=bool(prepare_request and prepared_request.get("source") == "self_thought"),
        )
        status = _one_line(send_result.get("status"), limit=120)
        queued = bool(send_result.get("queued"))
    else:
        status = "blocked"
        queued = False

    result = {
        "accepted": True,
        "status": status,
        "queued": queued,
        "dry_run": bool(dry_run),
        "prepare_request": bool(prepare_request),
        "evaluated_at": evaluated_at,
        "policy": policy,
        "prepared_request": prepared_request,
        "send_status": _one_line(send_result.get("status"), limit=120),
        "outbox_message_id": _one_line(send_result.get("outbox_message_id"), limit=120),
        "message_hash": _message_hash(send_result),
        "notes": _notes(policy, send_result),
    }
    _write_text(root / STATE_REL, _render_state(result))
    event = {
        "event_kind": "autonomous_outward_action",
        "evaluated_at": evaluated_at,
        "status": result["status"],
        "queued": queued,
        "dry_run": bool(dry_run),
        "prepare_request": bool(prepare_request),
        "prepared_request_source": _one_line(prepared_request.get("source"), limit=80),
        "prepared_request_status": _one_line(prepared_request.get("status"), limit=80),
        "policy_allowed": bool(policy["allowed"]),
        "blocks": list(policy["blocks"]),
        "send_status": result["send_status"],
        "outbox_message_id": result["outbox_message_id"],
        "message_hash": result["message_hash"],
    }
    _append_jsonl(root / TRACE_REL, event)
    _append_jsonl(root / LEDGER_REL, event)
    return result


def _notes(policy: dict[str, Any], send_result: dict[str, Any]) -> list[str]:
    if not policy.get("allowed"):
        return [f"blocked:{item}" for item in policy.get("blocks", [])] or ["blocked:unknown"]
    notes = [f"send:{_one_line(send_result.get('status'), limit=100)}"]
    notes.extend(_one_line(note, limit=100) for note in send_result.get("notes", [])[:4])
    return notes


def _render_state(result: dict[str, Any]) -> str:
    policy = result.get("policy") if isinstance(result.get("policy"), dict) else {}
    prepared = result.get("prepared_request") if isinstance(result.get("prepared_request"), dict) else {}
    notes = "\n".join(f"- {_one_line(note, limit=180)}" for note in result.get("notes", [])) or "- none"
    blocks = ", ".join(_one_line(item, limit=120) for item in policy.get("blocks", [])) or "none"
    return f"""---
title: Autonomous Outward Action State
memory_type: autonomous_outward_action_state
time_scope: immediate_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_autonomous_outward_action
updated_at: {_one_line(result.get('evaluated_at'))}
status: active
tags: [autonomy, outward-action, owner-private, qq, audit]
---

# Autonomous Outward Action State

## Last Evaluation
- evaluated_at: {_one_line(result.get('evaluated_at'))}
- status: {_one_line(result.get('status'))}
- queued: {_bool_text(result.get('queued'))}
- dry_run: {_bool_text(result.get('dry_run'))}
- prepare_request: {_bool_text(result.get('prepare_request'))}
- prepared_request_source: {_one_line(prepared.get('source'))}
- prepared_request_status: {_one_line(prepared.get('status'))}
- send_status: {_one_line(result.get('send_status'))}
- outbox_message_id: {_one_line(result.get('outbox_message_id'))}
- message_hash: {_one_line(result.get('message_hash'))}

## Policy
- allowed: {_bool_text(policy.get('allowed'))}
- blocks: {blocks}
- grant_present: {_bool_text(policy.get('grant_present'))}
- proactive_capability: {_bool_text(policy.get('proactive_capability'))}
- owner_private_target_count: {_one_line(policy.get('owner_private_target_count'), limit=40)}
- share_active: {_bool_text(policy.get('share_active'))}
- share_enabled: {_bool_text(policy.get('share_enabled'))}
- share_paused: {_bool_text(policy.get('share_paused'))}
- candidate_ready: {_bool_text(policy.get('candidate_ready'))}
- waiting_owner: {_bool_text(policy.get('waiting_owner'))}
- quiet_hours: {_one_line(policy.get('quiet_hours'))}
- quiet_hours_active: {_bool_text(policy.get('quiet_hours_active'))}
- sent_count_last_24h: {_one_line(policy.get('sent_count_last_24h'), limit=40)}
- max_messages_per_day: {_one_line(policy.get('max_messages_per_day'), limit=40)}

## Boundaries
- owner_private_only: true
- no_group_dispatch: true
- no_public_post: true
- no_stable_memory_write: true
- one_short_message_only: true
- raw_owner_text_in_state: false
- visible_message_text_in_state: false

## Notes
{notes}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one owner-private autonomous outward action tick.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--evaluated-at", default="")
    parser.add_argument("--min-interval-seconds", type=int, default=DEFAULT_MIN_INTERVAL_SECONDS)
    parser.add_argument("--max-messages-per-day", type=int, default=DEFAULT_MAX_MESSAGES_PER_DAY)
    parser.add_argument("--quiet-hours", default=DEFAULT_QUIET_HOURS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-request-loop", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_autonomous_outward_action_tick(
        args.root,
        evaluated_at=args.evaluated_at or None,
        min_interval_seconds=args.min_interval_seconds,
        max_messages_per_day=args.max_messages_per_day,
        quiet_hours=args.quiet_hours,
        dry_run=args.dry_run,
        prepare_request=not args.skip_request_loop,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_state(result))
    return 0 if result.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
