from __future__ import annotations

"""QQ / private-reply / learning-trial field collectors for xinyu_status.

Extracted from xinyu_status_collect to shrink the god collector module.
Behavior-preserving: pure helpers only; no intentional logic change.
"""

import json
import re
from pathlib import Path
from typing import Any

from xinyu_decision_chain_latest import build_decision_chain_latest_report

from xinyu_status_models import (
    DEFAULT_AUTONOMY_DECISION_WINDOW_MINUTES,
    _as_status_str_list,
    _bounded_status_value,
    _note_metric,
    _private_id_hash,
    _status_int,
    extract_int_value,
    extract_value,
    load_json,
    read_text,
)


def qq_group_reply_boundary_fields(root: Path, config_path: Path | None = None) -> dict[str, str]:
    cfg = load_json(config_path or (root / "xinyu_qq_gateway.config.json"))
    if not cfg:
        return {
            "qq_group_reply_boundary_status": "config_missing",
            "qq_group_reply_allowed_group_count": "0",
            "qq_group_shadow_only_group_count": "0",
            "qq_group_trigger_mode": "missing",
            "qq_group_followup_window_seconds": "missing",
            "qq_group_latest_trigger_reason": "missing",
            "qq_group_latest_reply_boundary": "unknown",
        }

    allowed_hashes = {
        digest
        for digest in (_private_id_hash(item) for item in _as_status_str_list(cfg.get("allowed_group_ids")))
        if digest
    }
    shadow_hashes = {
        digest
        for digest in (_private_id_hash(item) for item in _as_status_str_list(cfg.get("group_shadow_allowed_group_ids")))
        if digest
    }
    shadow_only_hashes = shadow_hashes - allowed_hashes
    group_state = read_text(root / "memory/context/group_shadow_state.md")
    latest_group_hash = extract_value(group_state, "group_id_hash", "missing")
    latest_trigger = extract_value(group_state, "trigger_reason", "missing")
    latest_policy = extract_value(group_state, "reply_policy", "missing")

    if cfg.get("private_only") is True or cfg.get("allow_group_messages") is False:
        status = "group_reply_disabled"
        latest_boundary = "group_reply_disabled"
    elif latest_group_hash in allowed_hashes:
        status = "recent_group_reply_allowed"
        latest_boundary = "reply_allowed_if_triggered"
    elif latest_group_hash in shadow_only_hashes:
        status = "recent_group_no_reply_by_boundary"
        latest_boundary = "shadow_only_no_reply"
    elif latest_trigger == "group_not_allowed":
        status = "recent_group_no_reply_by_boundary"
        latest_boundary = "not_reply_allowed"
    elif latest_trigger in {"group_trigger_required", "group_mention_required", "group_prefix_required"}:
        status = "recent_group_waiting_for_trigger"
        latest_boundary = latest_trigger
    elif latest_trigger == "missing":
        status = "no_recent_group_shadow"
        latest_boundary = "unknown"
    else:
        status = "configured"
        latest_boundary = latest_trigger

    return {
        "qq_group_reply_boundary_status": status,
        "qq_group_reply_allowed_group_count": str(len(allowed_hashes)),
        "qq_group_shadow_only_group_count": str(len(shadow_only_hashes)),
        "qq_group_trigger_mode": _bounded_status_value(cfg.get("group_trigger_mode"), "missing"),
        "qq_group_followup_window_seconds": _bounded_status_value(
            cfg.get("group_followup_window_seconds"),
            "missing",
        ),
        "qq_group_latest_trigger_reason": _bounded_status_value(latest_trigger, "missing"),
        "qq_group_latest_reply_policy": _bounded_status_value(latest_policy, "missing"),
        "qq_group_latest_reply_boundary": latest_boundary,
    }


def _load_jsonl_tail(path: Path, *, max_lines: int = 1000) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max_lines:]:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _qq_trace_generation_groups(
    rows: list[dict[str, Any]],
) -> tuple[dict[tuple[int, int], list[dict[str, Any]]], list[tuple[int, int]]]:
    by_key: dict[tuple[int, int], list[dict[str, Any]]] = {}
    row_keys: list[tuple[int, int]] = []
    generation = 0
    max_seen_seq = 0
    seq_to_key: dict[int, tuple[int, int]] = {}
    for row in rows:
        seq = _status_int(row.get("arrival_seq"))
        if max_seen_seq and seq < max_seen_seq and (max_seen_seq - seq) >= 5:
            generation += 1
            max_seen_seq = 0
            seq_to_key = {}
        key = seq_to_key.setdefault(seq, (generation, seq))
        by_key.setdefault(key, []).append(row)
        row_keys.append(key)
        max_seen_seq = max(max_seen_seq, seq)
    return by_key, row_keys


def _qq_rows_with_prepared_links(
    rows: list[dict[str, Any]],
    row_keys: list[tuple[int, int]],
    by_key: dict[tuple[int, int], list[dict[str, Any]]],
    key: tuple[int, int],
) -> list[dict[str, Any]]:
    base_rows = by_key.get(key, [])
    prepared_ids = {
        prepared_seq
        for prepared_seq in (_status_int(row.get("prepared_seq")) for row in base_rows)
        if prepared_seq > 0
    }
    if not prepared_ids:
        return base_rows
    linked: list[dict[str, Any]] = []
    for row, row_key in zip(rows, row_keys):
        if row_key[0] != key[0]:
            continue
        prepared_seq = _status_int(row.get("prepared_seq"))
        if row_key == key or prepared_seq in prepared_ids:
            linked.append(row)
    return linked


def qq_private_reply_flow_fields(root: Path) -> dict[str, str]:
    rows = _load_jsonl_tail(root / "runtime/qq_inbound_trace.jsonl")
    private_rows = [
        row
        for row in rows
        if str(row.get("message_kind") or row.get("message_type") or "").lower() == "private"
        and int(row.get("arrival_seq") or 0) > 0
    ]
    if not private_rows:
        return {
            "qq_private_reply_flow_status": "missing",
            "qq_private_latest_seq": "0",
            "qq_private_latest_route": "missing",
            "qq_private_latest_stage": "missing",
            "qq_private_latest_visible_status": "missing",
            "qq_private_latest_no_reply_reason": "missing",
            "qq_private_latest_chat_seq": "0",
            "qq_private_latest_drop_reason": "missing",
            "qq_private_latest_no_reply_explanation": "missing",
            "qq_private_recent_no_reply_summary": "missing",
            "qq_private_recent_coalesced_wait_count": "0",
            "qq_private_recent_intent_wait_more_count": "0",
            "qq_private_recent_intent_silent_count": "0",
            "qq_private_recent_turn_completion_drop_count": "0",
            "qq_private_recent_stale_drop_count": "0",
            "qq_private_recent_dispatch_error_count": "0",
            "qq_private_recent_rich_owner_only_count": "0",
        }

    recent_private_rows = private_rows[-160:]
    no_reply_counts = {
        "coalesced_wait": 0,
        "intent_wait_more": 0,
        "intent_silent": 0,
        "turn_completion_drop": 0,
        "stale_drop": 0,
        "dispatch_error": 0,
        "rich_owner_only": 0,
    }
    latest_drop_reason = "none"
    for row in recent_private_rows:
        stage = str(row.get("stage") or "").strip()
        route = str(row.get("route") or "").strip()
        drop_reason = str(row.get("drop_reason") or "").strip()
        if stage == "coalesced_wait" and route == "chat":
            no_reply_counts["coalesced_wait"] += 1
        if stage == "dispatch_error":
            no_reply_counts["dispatch_error"] += 1
        if stage == "stale_reply_dropped":
            no_reply_counts["stale_drop"] += 1
            latest_drop_reason = drop_reason or stage
        if stage == "dropped":
            latest_drop_reason = drop_reason or stage
            if drop_reason == "owner_private_intent_wait_more":
                no_reply_counts["intent_wait_more"] += 1
            elif drop_reason == "owner_private_intent_silent":
                no_reply_counts["intent_silent"] += 1
            elif drop_reason.startswith("turn_completion_"):
                no_reply_counts["turn_completion_drop"] += 1
            elif drop_reason in {"sticker_import_private_owner_only", "file_learning_private_owner_only"}:
                no_reply_counts["rich_owner_only"] += 1

    by_key, row_keys = _qq_trace_generation_groups(recent_private_rows)
    latest_generation = row_keys[-1][0]
    latest_key = max((key for key in row_keys if key[0] == latest_generation), key=lambda item: item[1])
    latest_seq = latest_key[1]
    latest_rows = _qq_rows_with_prepared_links(recent_private_rows, row_keys, by_key, latest_key)
    latest_stage = str(latest_rows[-1].get("stage") or "missing")
    latest_route = next(
        (
            str(row.get("route"))
            for row in reversed(latest_rows)
            if str(row.get("route") or "").strip()
        ),
        "missing",
    )

    latest_chat_seq = 0
    latest_chat_key: tuple[int, int] | None = None
    terminal_stages = {
        "reply_sent",
        "stale_reply_dropped",
        "dispatch_error",
        "dispatch_done",
        "dropped",
        "dispatch_start",
    }
    if any(str(row.get("route") or "") == "chat" and str(row.get("stage") or "") in terminal_stages for row in latest_rows):
        latest_chat_seq = latest_seq
        latest_chat_key = latest_key
    else:
        for row, key in zip(reversed(recent_private_rows), reversed(row_keys)):
            seq = int(row.get("arrival_seq") or 0)
            if seq <= 0 or str(row.get("route") or "") != "chat":
                continue
            latest_chat_seq = seq
            latest_chat_key = key
            break

    visible_status = "unknown"
    no_reply_reason = "none"
    stale_target_seq = 0
    if latest_chat_key is not None:
        chat_rows = _qq_rows_with_prepared_links(recent_private_rows, row_keys, by_key, latest_chat_key)
        chat_stages = {str(row.get("stage") or "") for row in chat_rows}
        if "reply_sent" in chat_stages:
            visible_status = "reply_sent"
        elif "stale_reply_dropped" in chat_stages:
            visible_status = "stale_reply_dropped"
            stale_row = next(
                (row for row in reversed(chat_rows) if str(row.get("stage") or "") == "stale_reply_dropped"),
                {},
            )
            drop_reason = str(stale_row.get("drop_reason") or "stale_reply_dropped")
            no_reply_reason = _bounded_status_value(drop_reason)
            match = re.search(r"->(\d+)", drop_reason)
            if match:
                stale_target_seq = int(match.group(1))
        elif "dispatch_error" in chat_stages:
            visible_status = "dispatch_error"
            err = next((str(row.get("error") or "") for row in reversed(chat_rows) if row.get("error")), "")
            no_reply_reason = _bounded_status_value(err or "dispatch_error")
        elif "dispatch_done" in chat_stages:
            done_row = next(
                (row for row in reversed(chat_rows) if str(row.get("stage") or "") == "dispatch_done"),
                {},
            )
            drop_reason = str(done_row.get("drop_reason") or "").strip()
            if drop_reason:
                visible_status = _bounded_status_value(drop_reason)
                no_reply_reason = _bounded_status_value(drop_reason)
            else:
                visible_status = "dispatch_done_no_reply_sent_trace"
                no_reply_reason = "missing_reply_sent_trace"
        elif "dropped" in chat_stages:
            drop_row = next(
                (row for row in reversed(chat_rows) if str(row.get("stage") or "") == "dropped"),
                {},
            )
            drop_reason = str(drop_row.get("drop_reason") or "dropped").strip()
            visible_status = _bounded_status_value(drop_reason)
            no_reply_reason = _bounded_status_value(drop_reason)
        elif "dispatch_start" in chat_stages:
            visible_status = "dispatch_started_no_terminal"
            no_reply_reason = "pending_or_missing_terminal_trace"
        elif "coalesced_wait" in chat_stages:
            visible_status = "coalesced_wait"
            no_reply_reason = "waiting_for_turn_completion"
        else:
            visible_status = "received_no_dispatch"
            no_reply_reason = "no_dispatch_terminal"

    status = visible_status
    if stale_target_seq and latest_chat_key is not None and (latest_chat_key[0], stale_target_seq) in by_key:
        target_rows = by_key[(latest_chat_key[0], stale_target_seq)]
        target_route = next(
            (
                str(row.get("route"))
                for row in reversed(target_rows)
                if str(row.get("route") or "").strip()
            ),
            "",
        )
        target_stages = {str(row.get("stage") or "") for row in target_rows}
        target_has_rich = any(
            int(row.get("sticker_count") or 0) > 0 or int(row.get("image_count") or 0) > 0
            for row in target_rows
        )
        if target_has_rich and "dispatch_error" in target_stages:
            status = "text_reply_dropped_after_rich_input_error"
            err = next((str(row.get("error") or "") for row in reversed(target_rows) if row.get("error")), "")
            no_reply_reason = _bounded_status_value(err or f"newer_{target_route or 'rich'}_input_error")
        elif target_has_rich:
            status = "text_reply_dropped_after_rich_input"
            no_reply_reason = no_reply_reason or "newer_rich_input"

    if no_reply_reason not in {"none", "missing"}:
        latest_drop_reason = no_reply_reason
    elif visible_status == "reply_sent":
        latest_drop_reason = "none"
    no_reply_explanation = _qq_private_no_reply_explanation(
        reason=no_reply_reason,
        visible_status=visible_status,
        status=status,
    )
    summary = ",".join(
        f"{name}:{count}"
        for name, count in no_reply_counts.items()
        if count
    ) or "none"

    return {
        "qq_private_reply_flow_status": status,
        "qq_private_latest_seq": str(latest_seq),
        "qq_private_latest_route": _bounded_status_value(latest_route),
        "qq_private_latest_stage": _bounded_status_value(latest_stage),
        "qq_private_latest_visible_status": _bounded_status_value(visible_status),
        "qq_private_latest_no_reply_reason": _bounded_status_value(no_reply_reason),
        "qq_private_latest_chat_seq": str(latest_chat_seq),
        "qq_private_latest_drop_reason": _bounded_status_value(latest_drop_reason),
        "qq_private_latest_no_reply_explanation": _bounded_status_value(no_reply_explanation),
        "qq_private_recent_no_reply_summary": _bounded_status_value(summary),
        "qq_private_recent_coalesced_wait_count": str(no_reply_counts["coalesced_wait"]),
        "qq_private_recent_intent_wait_more_count": str(no_reply_counts["intent_wait_more"]),
        "qq_private_recent_intent_silent_count": str(no_reply_counts["intent_silent"]),
        "qq_private_recent_turn_completion_drop_count": str(no_reply_counts["turn_completion_drop"]),
        "qq_private_recent_stale_drop_count": str(no_reply_counts["stale_drop"]),
        "qq_private_recent_dispatch_error_count": str(no_reply_counts["dispatch_error"]),
        "qq_private_recent_rich_owner_only_count": str(no_reply_counts["rich_owner_only"]),
    }


def qq_latest_inbound_flow_fields(root: Path, config_path: Path | None = None) -> dict[str, str]:
    rows = [
        row
        for row in _load_jsonl_tail(root / "runtime/qq_inbound_trace.jsonl")
        if _status_int(row.get("arrival_seq")) > 0
    ]
    if not rows:
        return {
            "qq_latest_inbound_status": "missing",
            "qq_latest_inbound_seq": "0",
            "qq_latest_inbound_scope": "missing",
            "qq_latest_inbound_stage": "missing",
            "qq_latest_inbound_route": "missing",
            "qq_latest_inbound_no_reply_reason": "missing",
            "qq_latest_inbound_explanation": "missing",
        }

    by_key, row_keys = _qq_trace_generation_groups(rows)
    latest_generation = row_keys[-1][0]
    latest_key = max((key for key in row_keys if key[0] == latest_generation), key=lambda item: item[1])
    latest_seq = latest_key[1]
    latest_rows = _qq_rows_with_prepared_links(rows, row_keys, by_key, latest_key)
    stages = {str(row.get("stage") or "").strip() for row in latest_rows}
    latest_stage = str(latest_rows[-1].get("stage") or "missing").strip() or "missing"
    latest_route = next(
        (
            str(row.get("route") or "").strip()
            for row in reversed(latest_rows)
            if str(row.get("route") or "").strip()
        ),
        "missing",
    )
    message_type = next(
        (
            str(row.get("message_kind") or row.get("message_type") or "").strip().lower()
            for row in latest_rows
            if str(row.get("message_kind") or row.get("message_type") or "").strip()
        ),
        "unknown",
    )
    group_hash = next(
        (str(row.get("group_id_hash") or "").strip() for row in latest_rows if str(row.get("group_id_hash") or "").strip()),
        "",
    )
    scope = "group" if group_hash or message_type.startswith("group") else "private" if message_type == "private" else message_type
    drop_reason = next(
        (str(row.get("drop_reason") or "").strip() for row in reversed(latest_rows) if str(row.get("drop_reason") or "").strip()),
        "",
    )

    status = "received"
    no_reply_reason = "none"
    explanation = "received_no_visible_terminal"
    if "reply_sent" in stages:
        status = "reply_sent"
        explanation = "reply_sent"
    elif "dispatch_error" in stages:
        status = "dispatch_error"
        no_reply_reason = next((str(row.get("error") or "dispatch_error") for row in reversed(latest_rows) if row.get("error")), "dispatch_error")
        explanation = "bridge_or_route_dispatch_error"
    elif "stale_reply_dropped" in stages:
        status = "stale_reply_dropped"
        no_reply_reason = drop_reason or "stale_reply_dropped"
        explanation = "older_visible_reply_was_superseded_by_newer_owner_input"
    elif "dropped" in stages:
        status = _bounded_status_value(drop_reason or "dropped")
        no_reply_reason = status
        explanation = status
    elif "dispatch_start" in stages:
        status = "dispatch_started_no_terminal"
        no_reply_reason = "pending_or_missing_terminal_trace"
        explanation = "dispatch_started_but_terminal_trace_is_not_visible_yet"
    elif "coalesced_wait" in stages:
        status = "coalesced_wait"
        no_reply_reason = "waiting_for_turn_completion"
        explanation = "message_is_waiting_for_turn_completion_or_coalescing"

    if scope == "private":
        explanation = _qq_private_no_reply_explanation(
            reason=no_reply_reason,
            visible_status=status,
            status=status,
        )
    elif scope == "group":
        cfg = load_json(config_path or (root / "xinyu_qq_gateway.config.json"))
        allowed_hashes = {
            digest
            for digest in (_private_id_hash(item) for item in _as_status_str_list(cfg.get("allowed_group_ids")))
            if digest
        }
        shadow_hashes = {
            digest
            for digest in (_private_id_hash(item) for item in _as_status_str_list(cfg.get("group_shadow_allowed_group_ids")))
            if digest
        }
        shadow_only_hashes = shadow_hashes - allowed_hashes
        if drop_reason == "group_not_allowed" and group_hash in shadow_only_hashes:
            status = "group_shadow_only_no_reply"
            no_reply_reason = "group_shadow_only_no_reply"
            explanation = "latest_group_is_shadow_only_observed_without_visible_reply"
        elif drop_reason == "group_not_allowed":
            explanation = "latest_group_is_not_in_visible_reply_allowlist"
        elif no_reply_reason in {"group_trigger_required", "group_mention_required", "group_prefix_required"}:
            explanation = "latest_group_message_needs_mention_or_prefix"
        elif status == "reply_sent":
            explanation = "reply_sent"

    return {
        "qq_latest_inbound_status": _bounded_status_value(status),
        "qq_latest_inbound_seq": str(latest_seq),
        "qq_latest_inbound_scope": _bounded_status_value(scope),
        "qq_latest_inbound_stage": _bounded_status_value(latest_stage),
        "qq_latest_inbound_route": _bounded_status_value(latest_route),
        "qq_latest_inbound_no_reply_reason": _bounded_status_value(no_reply_reason),
        "qq_latest_inbound_explanation": _bounded_status_value(explanation),
    }


def _qq_private_no_reply_explanation(*, reason: str, visible_status: str, status: str) -> str:
    reason = str(reason or "").strip()
    visible_status = str(visible_status or "").strip()
    status = str(status or "").strip()
    if status == "text_reply_dropped_after_rich_input_error":
        return "newer_rich_private_input_caused_text_reply_drop_and_route_error"
    if status == "text_reply_dropped_after_rich_input":
        return "newer_rich_private_input_superseded_older_text_reply"
    if reason == "owner_private_intent_wait_more":
        return "intent_gate_treated_latest_chat_as_fragment_and_waited_for_more"
    if reason == "owner_private_intent_silent":
        return "intent_gate_treated_latest_chat_as_low_info_or_status_update"
    if reason.startswith("turn_completion_"):
        return "turn_completion_gate_held_or_waited_instead_of_generating"
    if visible_status == "coalesced_wait":
        return "owner_private_messages_are_being_coalesced_before_generation"
    if visible_status == "dispatch_started_no_terminal":
        return "dispatch_started_but_terminal_trace_is_not_visible_yet"
    if visible_status == "dispatch_error":
        return "bridge_or_route_dispatch_error"
    if visible_status == "stale_reply_dropped":
        return "older_visible_reply_was_superseded_by_newer_owner_input"
    if visible_status == "empty_visible_reply":
        return "model_or_renderer_returned_no_visible_reply"
    if visible_status == "reply_sent":
        return "reply_sent"
    if visible_status == "received_no_dispatch":
        return "private_message_received_without_dispatch_terminal"
    if reason and reason != "none":
        return reason
    return "none"


def private_reply_selftest_fields(root: Path) -> dict[str, str]:
    state = load_json(root / "runtime/private_reply_selftest_state.json")
    if not state:
        return {
            "private_reply_selftest_status": "missing",
            "private_reply_selftest_checked_at": "missing",
            "private_reply_selftest_reply_sent": "missing",
            "private_reply_selftest_empty_visible_drop": "missing",
            "private_reply_selftest_dispatch_error": "missing",
            "private_reply_selftest_send_count": "0",
            "private_reply_selftest_ack_count": "0",
            "private_reply_selftest_model_present": "missing",
            "private_reply_selftest_model_route": "missing",
            "private_reply_selftest_model_visible_chars": "0",
            "private_reply_selftest_model_completion_tokens": "0",
            "private_reply_selftest_empty_stage_count": "0",
            "private_reply_selftest_real_qq_send": "missing",
            "private_reply_selftest_real_ack_written": "missing",
            "private_reply_selftest_raw_text_included": "missing",
            "private_reply_selftest_visible_reply_included": "missing",
        }
    trace = state.get("trace") if isinstance(state.get("trace"), dict) else {}
    send = state.get("send") if isinstance(state.get("send"), dict) else {}
    ack = state.get("ack") if isinstance(state.get("ack"), dict) else {}
    model = state.get("model") if isinstance(state.get("model"), dict) else {}
    privacy = state.get("privacy") if isinstance(state.get("privacy"), dict) else {}
    notes = model.get("model_notes")
    return {
        "private_reply_selftest_status": _bounded_status_value(state.get("status")),
        "private_reply_selftest_checked_at": _bounded_status_value(state.get("checked_at")),
        "private_reply_selftest_reply_sent": str(bool(trace.get("reply_sent"))).lower(),
        "private_reply_selftest_empty_visible_drop": str(bool(trace.get("empty_visible_drop"))).lower(),
        "private_reply_selftest_dispatch_error": str(bool(trace.get("dispatch_error"))).lower(),
        "private_reply_selftest_send_count": str(_status_int(send.get("captured_send_count"))),
        "private_reply_selftest_ack_count": str(_status_int(ack.get("captured_ack_count"))),
        "private_reply_selftest_model_present": str(bool(model.get("present"))).lower(),
        "private_reply_selftest_model_route": _bounded_status_value(model.get("route")),
        "private_reply_selftest_model_visible_chars": _note_metric(notes, "visible_chars:"),
        "private_reply_selftest_model_completion_tokens": _note_metric(notes, "completion_tokens:"),
        "private_reply_selftest_empty_stage_count": str(_status_int(model.get("empty_visible_stage_count"))),
        "private_reply_selftest_real_qq_send": str(bool(send.get("real_qq_send"))).lower(),
        "private_reply_selftest_real_ack_written": str(bool(ack.get("real_ack_written"))).lower(),
        "private_reply_selftest_raw_text_included": str(bool(privacy.get("raw_user_text_included"))).lower(),
        "private_reply_selftest_visible_reply_included": str(bool(privacy.get("visible_reply_text_included"))).lower(),
    }


def autonomy_decision_chain_fields(root: Path) -> dict[str, str]:
    try:
        report = build_decision_chain_latest_report(
            root,
            window_minutes=DEFAULT_AUTONOMY_DECISION_WINDOW_MINUTES,
        )
    except Exception as exc:
        return {"autonomy_decision_chain_status": f"error:{type(exc).__name__}"}

    chain = report.get("decision_chain") if isinstance(report.get("decision_chain"), dict) else {}
    if not chain:
        return {"autonomy_decision_chain_status": "missing"}

    fields = {
        "autonomy_decision_chain_status": "observed",
        "autonomy_decision_input_anchor": chain.get("input_anchor", "missing"),
        "autonomy_decision_perception_gap": chain.get("perception_gap", "missing"),
        "autonomy_decision_perception_route_hint": chain.get("perception_route_hint", "missing"),
        "autonomy_decision_perception_internal_consumed": chain.get("perception_internal_consumed", "missing"),
        "autonomy_decision_internal_state": chain.get("internal_state", "missing"),
        "autonomy_decision_candidate_count": chain.get("candidate_count", "missing"),
        "autonomy_decision_selected_candidate": chain.get("selected_candidate", "missing"),
        "autonomy_decision_selected_total_score": chain.get("selected_total_score", "missing"),
        "autonomy_decision_runner_up_intent": chain.get("runner_up_intent", "missing"),
        "autonomy_decision_runner_up_gate": chain.get("runner_up_gate", "missing"),
        "autonomy_decision_runner_up_total_score": chain.get("runner_up_total_score", "missing"),
        "autonomy_decision_score_margin": chain.get("score_margin", "missing"),
        "autonomy_decision_blocked_candidate_count": chain.get("blocked_candidate_count", "missing"),
        "autonomy_decision_held_candidate_count": chain.get("held_candidate_count", "missing"),
        "autonomy_decision_review_gated_future_count": chain.get("review_gated_future_count", "missing"),
        "autonomy_decision_competition_reason": chain.get("competition_reason", "missing"),
        "autonomy_decision_runner_up_not_selected_reason": chain.get(
            "runner_up_not_selected_reason",
            "missing",
        ),
        "autonomy_decision_gate_pressure_summary": chain.get("gate_pressure_summary", "missing"),
        "autonomy_decision_blocked_intents": chain.get("blocked_intents", "missing"),
        "autonomy_decision_held_intents": chain.get("held_intents", "missing"),
        "autonomy_decision_review_gated_intents": chain.get("review_gated_intents", "missing"),
        "autonomy_decision_gate": chain.get("gate", "missing"),
        "autonomy_decision_action_level": chain.get("action_level", "missing"),
        "autonomy_decision_action_result": chain.get("action_result", "missing"),
        "autonomy_decision_action_evidence_status": report.get("action_evidence_status", "missing"),
        "autonomy_decision_action_evidence_surface": chain.get("action_evidence_surface", "missing"),
        "autonomy_decision_action_evidence_signal": chain.get("action_evidence_signal", "missing"),
        "autonomy_decision_action_evidence_result": chain.get("action_evidence_result", "missing"),
        "autonomy_decision_action_evidence_lifecycle": chain.get("action_evidence_lifecycle", "missing"),
        "autonomy_decision_action_evidence_future_effect": chain.get(
            "action_evidence_future_effect",
            "missing",
        ),
        "autonomy_decision_restraint_reason": chain.get("restraint_reason", "missing"),
        "autonomy_decision_proactive_candidate": chain.get("proactive_candidate", "missing"),
        "autonomy_decision_memory_candidate": chain.get("memory_candidate", "missing"),
        "autonomy_decision_action_feedback_signal": chain.get("action_feedback_signal", "missing"),
        "autonomy_decision_action_feedback_future_effect": chain.get(
            "action_feedback_future_effect",
            "missing",
        ),
        "autonomy_decision_owner_feedback_signal": chain.get("owner_feedback_signal", "missing"),
        "autonomy_decision_owner_feedback_future_effect": chain.get(
            "owner_feedback_future_effect",
            "missing",
        ),
        "autonomy_decision_owner_response_signal": chain.get("owner_response_signal", "missing"),
        "autonomy_decision_owner_response_future_effect": chain.get(
            "owner_response_future_effect",
            "missing",
        ),
        "autonomy_decision_feedback_consumption_status": chain.get("feedback_consumption_status", "missing"),
        "autonomy_decision_feedback_consumed_sources": chain.get("feedback_consumed_sources", "missing"),
        "autonomy_decision_feedback_consumed_biases": chain.get("feedback_consumed_biases", "missing"),
        "autonomy_decision_feedback_consumed_future_effect": chain.get(
            "feedback_consumed_future_effect",
            "missing",
        ),
        "autonomy_decision_proactive_response_signal": chain.get(
            "proactive_response_signal",
            "missing",
        ),
        "autonomy_decision_proactive_response_future_effect": chain.get(
            "proactive_response_future_effect",
            "missing",
        ),
        "autonomy_decision_next_behavior_bias": chain.get("next_behavior_bias", "missing"),
    }
    return {key: _bounded_status_value(value) for key, value in fields.items()}


def learning_trial_gate_fields(root: Path) -> dict[str, str]:
    learning = read_text(root / "memory/self/learning_closed_loop_state.md")
    self_review = read_text(root / "memory/self/personality_self_review_state.md")

    active_trial_habit = extract_value(learning, "active_trial_habit", "none")
    active_trial_key = extract_value(learning, "active_trial_key", extract_value(learning, "latest_failure_kind", "none"))
    latest_success_key = extract_value(learning, "latest_success_trial_key", "none")
    success_evidence = extract_value(learning, "success_evidence_status", "none")
    repair_count = extract_int_value(learning, "repair_count", 0)
    success_count = extract_int_value(learning, "success_count", 0)
    success_streak = extract_int_value(learning, "success_streak", 0)
    trial_success_count = extract_int_value(learning, "trial_success_count", success_count)
    trial_success_streak = extract_int_value(learning, "trial_success_streak", success_streak)
    promotion_signal = extract_value(learning, "promotion_signal", "false").lower()
    last_owner_reaction = extract_value(learning, "last_owner_reaction", "none")
    review_decision = extract_value(self_review, "decision", "missing")
    review_action = extract_value(self_review, "action", "missing")
    profile_changed = extract_value(self_review, "profile_changed", "missing")
    gate_reason = extract_value(self_review, "learning_trial_gate_reason", "none")

    none_values = {"", "missing", "none", "unknown"}
    if active_trial_habit in none_values and active_trial_key in none_values:
        gate = "not_required"
    elif "learning_trial_success_gate_satisfied" in gate_reason:
        gate = "satisfied"
    elif (
        trial_success_count >= 2
        and trial_success_streak >= 2
        and latest_success_key not in none_values
        and success_evidence == "same_trial_explicit_owner_success"
        and last_owner_reaction == "explicit_success"
        and promotion_signal in {"true", "possible_after_self_review"}
    ):
        gate = "ready_for_self_review"
    else:
        gate = "blocked"

    stable_write = "minor_habit_written" if profile_changed == "true" else "blocked"
    if gate == "blocked" and gate_reason in none_values:
        blockers: list[str] = []
        if repair_count >= 8 and trial_success_streak < 2:
            blockers.append(f"repair_pressure_overloaded:{repair_count}")
        if trial_success_count < 2:
            blockers.append(f"trial_success_count_below_2:{trial_success_count}")
        if trial_success_streak < 2:
            blockers.append(f"trial_success_streak_below_2:{trial_success_streak}")
        if success_evidence != "same_trial_explicit_owner_success":
            blockers.append(f"success_evidence_not_same_trial:{success_evidence}")
        if last_owner_reaction != "explicit_success":
            blockers.append(f"last_owner_reaction_not_explicit_success:{last_owner_reaction}")
        gate_reason = "learning_trial_success_gate_not_satisfied:" + ",".join(blockers[:6])
    elif gate == "not_required":
        gate_reason = "learning_trial_not_required"
    elif gate == "ready_for_self_review":
        # Once the success gate is met, never surface a stale blocked reason that the
        # self-review file may still hold from when the streak was lower. Describe the
        # live state so the "why" stays consistent with the gate.
        gate_reason = (
            "learning_trial_success_gate_met_pending_self_review:"
            f"same_key_success={trial_success_count}/{trial_success_streak},"
            f"promotion_signal={promotion_signal}"
        )
    elif gate == "satisfied" and gate_reason in none_values:
        gate_reason = "learning_trial_success_gate_satisfied"

    fields = {
        "memory_learning_trial_gate": gate,
        "memory_learning_trial_active_key": active_trial_key,
        "memory_learning_trial_success_key": latest_success_key,
        "memory_learning_trial_success_evidence": success_evidence,
        "memory_learning_trial_repair_count": str(repair_count),
        "memory_learning_trial_success_count": str(success_count),
        "memory_learning_trial_success_streak": str(success_streak),
        "memory_learning_trial_same_key_success_count": str(trial_success_count),
        "memory_learning_trial_same_key_success_streak": str(trial_success_streak),
        "memory_learning_trial_promotion_signal": promotion_signal,
        "memory_learning_trial_last_owner_reaction": last_owner_reaction,
        "memory_learning_trial_self_review_decision": review_decision,
        "memory_learning_trial_self_review_action": review_action,
        "memory_learning_trial_profile_changed": profile_changed,
        "memory_learning_trial_stable_write": stable_write,
        "memory_learning_trial_gate_reason": gate_reason,
    }
    return {key: _bounded_status_value(value) for key, value in fields.items()}
