from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xinyu_state_io import read_text, write_text_atomic


STATE_REL = Path("memory/context/action_feedback_state.md")
TRACE_REL = Path("runtime/action_feedback_trace.jsonl")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _fingerprint(value: Any) -> str:
    text = _safe_str(value).strip()
    if not text:
        return ""
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _parse_timestamp(value: Any) -> datetime | None:
    text = _safe_str(value).strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _timestamp_not_before(left: Any, right: Any) -> bool:
    left_time = _parse_timestamp(left)
    right_time = _parse_timestamp(right)
    if left_time is None or right_time is None:
        return False
    compare_right = right_time
    if left_time.tzinfo is not None and right_time.tzinfo is not None:
        compare_right = right_time.astimezone(left_time.tzinfo)
    elif left_time.tzinfo is not None and right_time.tzinfo is None:
        compare_right = right_time.replace(tzinfo=left_time.tzinfo)
    elif left_time.tzinfo is None and right_time.tzinfo is not None:
        left_time = left_time.replace(tzinfo=right_time.tzinfo)
    return left_time >= compare_right


def _event_id(*parts: Any) -> str:
    seed = "|".join(_safe_str(part) for part in parts)
    return "actfb-" + hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()[:16]


def _target_kind(payload: dict[str, Any]) -> str:
    target = payload.get("target") if isinstance(payload.get("target"), dict) else {}
    return _safe_str(payload.get("message_type") or target.get("message_kind") or "unknown").strip() or "unknown"


def _write_state(root: Path, event: dict[str, Any]) -> None:
    checked_at = _safe_str(event.get("checked_at"), _now_iso())
    text = f"""---
title: Action Feedback State
memory_type: action_feedback_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_action_feedback_surface
updated_at: {checked_at}
status: active
tags: [autonomy, action-result, feedback, future-behavior]
---

# Action Feedback State

## Latest Action Feedback
- status: active
- checked_at: {checked_at}
- event_id: {_safe_str(event.get("event_id"))}
- feedback_signal: {_safe_str(event.get("feedback_signal"), "none")}
- feedback_source: {_safe_str(event.get("feedback_source"), "unknown")}
- action_result: {_safe_str(event.get("action_result"), "unknown")}
- route: {_safe_str(event.get("route"), "unknown")}
- target_kind: {_safe_str(event.get("target_kind"), "unknown")}
- future_effect: {_safe_str(event.get("future_effect"), "none")}
- scoring_effect: {_safe_str(event.get("scoring_effect"), "none")}
- memory_effect: {_safe_str(event.get("memory_effect"), "none")}
- source_message_ref: {_safe_str(event.get("source_message_ref"), "")}
- adapter_message_ref: {_safe_str(event.get("adapter_message_ref"), "")}
- turn_ref: {_safe_str(event.get("turn_ref"), "")}

## Boundaries
- raw_private_body_retained: false
- visible_reply_text_retained: false
- stable_memory_write: blocked
"""
    write_text_atomic(root / STATE_REL, text)


def _append_trace(root: Path, event: dict[str, Any]) -> None:
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def record_action_feedback_event(
    root: Path,
    *,
    feedback_signal: str,
    feedback_source: str,
    action_result: str,
    route: str,
    target_kind: str,
    future_effect: str,
    scoring_effect: str,
    memory_effect: str,
    source_message_id: Any = "",
    adapter_message_id: Any = "",
    turn_id: Any = "",
    checked_at: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    checked_at = checked_at or _now_iso()
    event = {
        "checked_at": checked_at,
        "event_id": _event_id(checked_at, feedback_signal, route, source_message_id, adapter_message_id, turn_id),
        "feedback_signal": feedback_signal,
        "feedback_source": feedback_source,
        "action_result": action_result,
        "route": route,
        "target_kind": target_kind,
        "future_effect": future_effect,
        "scoring_effect": scoring_effect,
        "memory_effect": memory_effect,
        "source_message_ref": _fingerprint(source_message_id),
        "adapter_message_ref": _fingerprint(adapter_message_id),
        "turn_ref": _fingerprint(turn_id),
        "raw_private_body_retained": False,
        "visible_reply_text_retained": False,
        "stable_memory_write": "blocked",
    }
    _write_state(root, event)
    _append_trace(root, event)
    return {"recorded": True, "event_id": event["event_id"], "feedback_signal": feedback_signal}


def record_action_feedback_from_message_ack(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    ack_result: dict[str, Any] | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    ack_result = ack_result if isinstance(ack_result, dict) else {}
    indexed = bool(ack_result.get("indexed") or ack_result.get("accepted", True))
    route = _safe_str(payload.get("route") or payload.get("source_route") or "chat", "chat").strip() or "chat"
    return record_action_feedback_event(
        root,
        feedback_signal="qq_visible_reply_ack" if route == "chat" else "qq_outbox_delivery_ack",
        feedback_source="internal_message_ack",
        action_result="delivered" if indexed else "ack_seen_index_failed",
        route=route,
        target_kind=_target_kind(payload),
        future_effect="confirm_visible_reply_transport_for_next_turn",
        scoring_effect="keep_current_route_available",
        memory_effect="sent_reply_index_updated" if indexed else "sent_reply_index_not_updated",
        source_message_id=payload.get("source_message_id") or payload.get("message_id"),
        adapter_message_id=payload.get("adapter_message_id"),
        turn_id=payload.get("turn_id"),
        checked_at=checked_at,
    )


def record_action_feedback_from_message_drop(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    drop_result: dict[str, Any] | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    drop_result = drop_result if isinstance(drop_result, dict) else {}
    route = _safe_str(payload.get("route") or payload.get("source_route") or "chat", "chat").strip() or "chat"
    memory_effect = "unsent_reply_retracted"
    if drop_result.get("archive_deleted") is False and drop_result.get("tail_removed") is False:
        memory_effect = "unsent_reply_retraction_attempted"
    return record_action_feedback_event(
        root,
        feedback_signal="qq_stale_reply_drop",
        feedback_source="internal_message_drop",
        action_result="unsent_retracted",
        route=route,
        target_kind=_target_kind(payload),
        future_effect="prefer_latest_owner_input_and_suppress_stale_reply_memory",
        scoring_effect="raise_newer_input_waterline_before_visible_send",
        memory_effect=memory_effect,
        source_message_id=payload.get("source_message_id") or payload.get("message_id"),
        adapter_message_id=payload.get("adapter_message_id"),
        turn_id=payload.get("turn_id"),
        checked_at=checked_at,
    )


def read_action_feedback_state(root: Path) -> dict[str, str]:
    text = read_text(Path(root) / STATE_REL)
    if not text:
        return {"status": "missing", "feedback_signal": "missing", "future_effect": "missing"}
    return _parse_fields(text)


def build_action_feedback_prompt_block(root: Path, *, max_chars: int = 900) -> str:
    fields = read_action_feedback_state(root)
    signal = fields.get("feedback_signal", "missing")
    if signal in {"", "missing", "none"}:
        return ""
    lines = [
        "action feedback sidecar:",
        "visibility_rule: hidden; do not mention feedback state, hashes, routes, files, or scoring.",
        f"feedback_signal: {signal}",
        f"action_result: {fields.get('action_result', 'unknown')}",
        f"future_effect: {fields.get('future_effect', 'none')}",
        f"scoring_effect: {fields.get('scoring_effect', 'none')}",
        f"memory_effect: {fields.get('memory_effect', 'none')}",
        "reply_rule: let the result shape the next choice quietly; never claim raw private text was saved.",
    ]
    block = "\n".join(lines)
    return block[: max(0, int(max_chars))]


def record_action_feedback_from_live_report(
    root: Path,
    live_report: dict[str, Any],
    *,
    checked_at: str | None = None,
) -> dict[str, Any]:
    checks = {
        _safe_str(check.get("name")): bool(check.get("ok"))
        for check in live_report.get("checks", [])
        if isinstance(check, dict)
    }
    evidence = live_report.get("evidence") if isinstance(live_report.get("evidence"), dict) else {}
    ack = evidence.get("latest_chat_ack") if isinstance(evidence.get("latest_chat_ack"), dict) else {}
    reply = evidence.get("latest_reply_sent") if isinstance(evidence.get("latest_reply_sent"), dict) else {}
    private_input = evidence.get("latest_private_input") if isinstance(evidence.get("latest_private_input"), dict) else {}
    stale_drop = evidence.get("latest_stale_reply_drop") if isinstance(evidence.get("latest_stale_reply_drop"), dict) else {}
    ack_present = bool(ack.get("present"))
    ack_source = _safe_str(ack.get("source_message_id"))
    reply_source = _safe_str(reply.get("message_id"))
    ack_matches_reply = bool(ack_present and ack_source and reply_source and ack_source == reply_source)
    if checks.get("qq_ack") or ack_matches_reply:
        return record_action_feedback_event(
            root,
            feedback_signal="qq_visible_reply_ack",
            feedback_source="live_loop_report",
            action_result="delivered",
            route=_safe_str(ack.get("route"), "chat"),
            target_kind=_safe_str(ack.get("message_type"), "private"),
            future_effect="confirm_visible_reply_transport_for_next_turn",
            scoring_effect="keep_current_route_available",
            memory_effect="sent_reply_index_observed",
            source_message_id=ack.get("source_message_id"),
            adapter_message_id=ack.get("adapter_message_id"),
            checked_at=checked_at,
        )
    stale_is_current = _timestamp_not_before(stale_drop.get("recorded_at"), private_input.get("recorded_at"))
    if checks.get("stale_reply_drop_guard") and stale_is_current:
        return record_action_feedback_event(
            root,
            feedback_signal="qq_stale_reply_drop",
            feedback_source="live_loop_report",
            action_result="unsent_retracted",
            route="chat",
            target_kind=_safe_str(stale_drop.get("message_kind"), "private"),
            future_effect="prefer_latest_owner_input_and_suppress_stale_reply_memory",
            scoring_effect="raise_newer_input_waterline_before_visible_send",
            memory_effect="unsent_reply_retraction_observed",
            source_message_id=stale_drop.get("message_id"),
            checked_at=checked_at,
        )
    return {"recorded": False, "feedback_signal": "none", "notes": ["no_live_action_feedback"]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update XinYu action feedback state from live loop evidence.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--core-url", default="http://127.0.0.1:8765")
    parser.add_argument("--window-minutes", type=int, default=120)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    from xinyu_live_loop_report import _load_live_status
    from xinyu_live_loop_report import build_report as build_live_loop_report

    root = args.root.resolve()
    status_data, status_error = _load_live_status(root, args.core_url)
    report = build_live_loop_report(
        root,
        status_data=status_data,
        status_error=status_error,
        now=datetime.now(timezone.utc),
        window_minutes=max(1, int(args.window_minutes)),
    )
    result = record_action_feedback_from_live_report(root, report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"recorded={str(result.get('recorded')).lower()} feedback_signal={result.get('feedback_signal')}")
    return 0 if result.get("recorded") else 1


if __name__ == "__main__":
    raise SystemExit(main())
