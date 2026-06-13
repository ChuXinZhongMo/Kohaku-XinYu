from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_action_feedback_coverage import build_action_feedback_coverage_report
from xinyu_decision_chain_latest import build_decision_chain_latest_report
from xinyu_desire_drive_state import build_desire_drive_snapshot
from xinyu_feedback_consumption_diagnostics import build_feedback_consumption_diagnostics
from xinyu_memory_health_report import build_memory_health_report
from xinyu_owner_feedback_effects import build_owner_feedback_effect_report
from xinyu_perception_importance import build_perception_importance_report
from xinyu_proactive_response_diagnostics import build_proactive_response_diagnostics
from xinyu_runtime_security import (
    bridge_source_version,
    runtime_source_paths,
    source_file_digest,
    source_files_digest,
)
from xinyu_stage10_proactive_life_loop import build_stage10_proactive_life_loop
from xinyu_stage11_multisensory_extension import build_stage11_multisensory_extension
from xinyu_stage11_visual_ingress_diagnostics import build_stage11_visual_ingress_diagnostics
from xinyu_stage11_voice_ingress_diagnostics import build_stage11_voice_ingress_diagnostics
from xinyu_stage12_long_term_evaluation import build_stage12_long_term_evaluation
from xinyu_stage13_self_narrative import build_stage13_self_narrative
from xinyu_private_ecosystem import build_private_ecosystem_snapshot
from xinyu_private_desktop_control import build_desktop_snapshot
from xinyu_stage9_self_state_model import build_stage9_self_state_model
from xinyu_text_variants import legacy_mojibake_variants


DEFAULT_CORE_URL = "http://127.0.0.1:8765"
DEFAULT_QQ_GATEWAY_CONFIG = Path(__file__).resolve().with_name("xinyu_qq_gateway.config.json")
DEFAULT_AUTONOMY_DECISION_WINDOW_MINUTES = 240
NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

TEXT_HEALTH_FILES = (
    "memory/context/proactive_presence_state.md",
    "memory/context/proactive_request_state.md",
    "memory/context/proactive_response_diagnostics_state.md",
    "memory/context/proactive_qq_dispatch_state.md",
    "memory/context/memory_braid_state.md",
    "memory/context/turn_coherence_state.md",
    "memory/context/initiative_spine_state.md",
    "memory/context/desire_drive_state.md",
    "memory/context/short_term_continuity_state.md",
    "memory/context/short_term_continuity_canary_state.md",
    "memory/context/short_term_recall_diagnostics_state.md",
    "memory/context/perception_importance_state.md",
    "memory/context/action_feedback_coverage_state.md",
    "memory/context/owner_feedback_effect_state.md",
    "memory/context/decision_chain_latest_state.md",
    "memory/context/feedback_consumption_diagnostics_state.md",
    "memory/context/self_state_capsule_state.md",
    "memory/context/stage9_self_state_model_state.md",
    "memory/context/stage10_proactive_life_loop_state.md",
    "memory/context/stage11_multisensory_extension_state.md",
    "memory/context/stage11_visual_ingress_diagnostics_state.md",
    "memory/context/stage11_voice_ingress_diagnostics_state.md",
    "memory/context/stage12_long_term_evaluation_state.md",
    "memory/context/self_chosen_goal_ecology_state.md",
    "memory/context/self_action_gateway_state.md",
    "memory/context/self_action_gateway_execution_handoff.md",
    "memory/context/self_action_patch_executor_state.md",
    "memory/context/self_action_patch_executor_task.md",
    "memory/context/self_thought_state.md",
    "memory/context/emotion_council_state.md",
    "memory/context/impulse_soup_state.md",
    "memory/context/early_visible_segment_shadow_state.md",
    "memory/self/expression_self_learning_state.md",
    "memory/self/learning_closed_loop_state.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
)

TEXT_HEALTH_MARKERS = (
    "\u54e5",
    "\u4e3b\u4eba",
    "\u8bb0\u5fc6",
    "\u53cd\u601d\u961f\u5217",
    "\u5173\u4e8e\u88ab\u8bb0\u4f4f",
    "\u8fd8\u6ca1\u653e\u4e0b",
    "\u957f\u671f\u5173\u7cfb",
    "\u5177\u4f53\u5bf9\u8bdd",
    "\u8bb0\u5fc6\u7559\u75d5",
    "\u5916\u90e8\u5b66\u4e60",
    "\u4e3b\u52a8\u7ebf\u7a0b",
    "\u60c5\u611f\u7cfb\u7edf",
    "\u4e3b\u4eba\u683c",
)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _stage12_live_status_stub() -> dict[str, Any]:
    # Avoid recursive xinyu_status -> stage12 -> live_loop_report -> xinyu_status.
    return {
        "ok": True,
        "known_error_count": 0,
        "checks": [
            {"name": "core_bridge", "ok": True},
            {"name": "xinyu_qq_gateway_6199", "ok": True},
            {"name": "napcat_to_xinyu_qq_gateway_ws", "ok": True},
        ],
    }


def runtime_text_health_issues(root: Path) -> list[str]:
    issues: list[str] = []
    for rel_path in TEXT_HEALTH_FILES:
        path = root / rel_path
        if not path.exists():
            continue
        text = read_text(path)
        if "\ufffd" in text:
            issues.append(f"{rel_path}:replacement_character")
        marker_hits: list[str] = []
        for marker in TEXT_HEALTH_MARKERS:
            if any(variant in text for variant in legacy_mojibake_variants(marker)):
                marker_hits.append(marker)
        if marker_hits:
            issues.append(f"{rel_path}:legacy_mojibake:{len(marker_hits)}")
    return issues


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", text)
    return match.group(1).strip() if match else default


def extract_int_value(text: str, field: str, default: int = 0) -> int:
    raw = extract_value(text, field, str(default))
    match = re.search(r"-?\d+", raw)
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def mask_private_identifier(value: str) -> str:
    return re.sub(r"\d{5,}", lambda m: m.group(0)[:2] + "***" + m.group(0)[-2:], value)


def redact_local_path(value: str) -> str:
    text = str(value)
    lowered = text.lower()
    if lowered.endswith("xinyu_core_bridge.py"):
        return "<xinyu_core_bridge.py>"
    if "xinyu_qq_gateway" in lowered:
        return "<xinyu_qq_gateway>"
    if "examples" in lowered and "agent-apps" in lowered and "xinyu" in lowered:
        return "<xinyu_dir>"
    if re.search(r"(?i)([a-z]:\\|/users/|/home/|\\\\)", text):
        return "<local_path>"
    return text


def redact_core_data(data: dict[str, Any]) -> dict[str, Any]:
    return _redact_status_value(data)


def _redact_status_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_local_path(value)
    if isinstance(value, dict):
        return {key: _redact_status_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_status_value(item) for item in value]
    return value


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _as_status_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _private_id_hash(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


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


def _note_metric(notes: Any, prefix: str, default: str = "0") -> str:
    if not isinstance(notes, list):
        return default
    for note in notes:
        text = str(note or "")
        if text.startswith(prefix):
            return _bounded_status_value(text[len(prefix) :], default)
    return default


def _status_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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


def file_sha256(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plugin_source_digest(path: Path) -> str:
    if not path.exists() or not path.is_dir():
        return ""
    digest = hashlib.sha256()
    for file_path in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if not file_path.is_file() or file_path.suffix.lower() not in {".py", ".yaml", ".json"}:
            continue
        digest.update(file_path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha256(file_path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _bounded_status_value(value: Any, default: str = "missing") -> str:
    if value is None:
        return default
    text = mask_private_identifier(redact_local_path(str(value).strip()))
    if not text:
        return default
    if len(text) > 240:
        digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
        return f"<omitted_long_value:sha256:{digest}>"
    return text


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


def extract_shell_version(path: Path) -> str:
    text = read_text(path)
    match = re.search(r'(?m)^SHELL_VERSION\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1).strip() if match else "unknown"


def extract_gateway_version(path: Path) -> str:
    text = read_text(path)
    match = re.search(r'(?m)^GATEWAY_VERSION\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1).strip() if match else "unknown"


def http_json(url: str, timeout: float = 3.0) -> tuple[bool, dict[str, Any] | str]:
    try:
        with NO_PROXY_OPENER.open(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            return True, data if isinstance(data, dict) else {"value": data}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return False, f"HTTP {exc.code}: {body[:160]}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def tcp_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def netstat_lines(port: int) -> list[str]:
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except Exception:
        return []
    needle = f":{port}"
    return [line.strip() for line in result.stdout.splitlines() if needle in line]


def has_established_local(port: int) -> bool:
    return any("ESTABLISHED" in line and "127.0.0.1" in line for line in netstat_lines(port))


def check_core(
    core_url: str,
    expected_version: str,
    expected_source_digest: str,
    expected_runtime_source_digest: str,
) -> tuple[list[Check], dict[str, Any]]:
    ok, data = http_json(f"{core_url.rstrip('/')}/health")
    if not ok:
        return [Check("core_bridge", False, str(data))], {}
    assert isinstance(data, dict)
    autonomous = data.get("autonomous_maintenance")
    auto_detail = ""
    if isinstance(autonomous, dict):
        auto_detail = (
            f" autonomous={autonomous.get('enabled', 'unknown')}"
            f"/task={autonomous.get('task_running', 'unknown')}"
            f" runs={autonomous.get('run_count', 'unknown')}"
            f" next={autonomous.get('next_run_at', 'unknown')}"
        )
    detail = (
        f"version={data.get('version', 'unknown')} "
        f"sessions={data.get('sessions', 'unknown')} "
        f"closed={data.get('closed', 'unknown')}"
        f"{auto_detail}"
    )
    running_version = str(data.get("version", "unknown"))
    running_source_digest = str(data.get("source_digest", "unknown"))
    running_runtime_source_digest = str(data.get("runtime_source_digest", "unknown"))
    return [
        Check("core_bridge", bool(data.get("ok")), detail),
        Check(
            "core_bridge_version",
            bool(running_version == expected_version),
            f"running={running_version} source={expected_version}",
        ),
        Check(
            "core_bridge_source_digest",
            bool(running_source_digest == expected_source_digest),
            f"running={running_source_digest} source={expected_source_digest}",
        ),
        Check(
            "core_bridge_runtime_source_digest",
            bool(running_runtime_source_digest == expected_runtime_source_digest),
            f"running={running_runtime_source_digest} source={expected_runtime_source_digest}",
        ),
    ], data


def check_ports() -> list[Check]:
    checks = [
        Check("xinyu_qq_gateway_6199", tcp_connect("127.0.0.1", 6199), "tcp connect 127.0.0.1:6199"),
        Check("napcat_webui_6099", tcp_connect("127.0.0.1", 6099), "tcp connect 127.0.0.1:6099"),
    ]
    checks.append(
        Check(
            "napcat_to_xinyu_qq_gateway_ws",
            has_established_local(6199),
            "local ESTABLISHED connection on 6199",
        )
    )
    return checks


def check_qq_gateway_config(root: Path, config_path: Path) -> list[Check]:
    cfg = load_json(config_path)
    gateway_path = root / "xinyu_qq_gateway.py"
    version = extract_gateway_version(gateway_path)
    group_boundary = qq_group_reply_boundary_fields(root, config_path)
    owner_ids = cfg.get("owner_user_ids")
    whitelist_ids = cfg.get("whitelist_user_ids")
    owner_count = len(owner_ids) if isinstance(owner_ids, list) else 0
    whitelist_count = len(whitelist_ids) if isinstance(whitelist_ids, list) else 0
    group_prefixes = cfg.get("group_trigger_prefixes")
    group_prefix_count = len(group_prefixes) if isinstance(group_prefixes, list) else 0
    codex_prefixes = cfg.get("codex_command_prefixes")
    codex_prefix_list = codex_prefixes if isinstance(codex_prefixes, list) else []
    codex_execute_url = str(cfg.get("codex_execute_url", ""))
    outbox_claim_url = str(cfg.get("qq_outbox_claim_url", ""))
    outbox_ack_url = str(cfg.get("qq_outbox_ack_url", ""))
    return [
        Check("qq_gateway_source_present", gateway_path.exists(), f"version={version}"),
        Check("qq_gateway_config_present", bool(cfg), redact_local_path(str(config_path)) if cfg else "missing"),
        Check("qq_gateway_enabled", bool(cfg.get("enabled")), f"value={cfg.get('enabled', 'missing')}"),
        Check("qq_gateway_core_url", str(cfg.get("core_chat_url", "")).endswith("/chat"), str(cfg.get("core_chat_url", ""))),
        Check(
            "qq_gateway_codex_route",
            bool(cfg.get("codex_command_enabled"))
            and codex_execute_url.endswith("/codex/execute")
            and "/codex" in codex_prefix_list,
            (
                f"enabled={cfg.get('codex_command_enabled', 'missing')} "
                f"url={codex_execute_url or 'missing'} prefixes={len(codex_prefix_list)}"
            ),
        ),
        Check(
            "qq_gateway_outbox_route",
            bool(cfg.get("qq_outbox_enabled"))
            and outbox_claim_url.endswith("/qq/outbox/claim")
            and outbox_ack_url.endswith("/qq/outbox/ack"),
            (
                f"enabled={cfg.get('qq_outbox_enabled', 'missing')} "
                f"claim={outbox_claim_url or 'missing'} ack={outbox_ack_url or 'missing'}"
            ),
        ),
        Check("qq_gateway_whitelist", owner_count > 0 and whitelist_count > 0, f"owners={owner_count} whitelist={whitelist_count}"),
        Check(
            "qq_gateway_group_trigger",
            group_prefix_count > 0,
            f"mode={cfg.get('group_trigger_mode', 'missing')} prefixes={group_prefix_count}",
        ),
        Check(
            "qq_gateway_group_reply_boundary",
            True,
            (
                f"{group_boundary['qq_group_reply_boundary_status']} "
                f"latest={group_boundary['qq_group_latest_reply_boundary']} "
                f"reason={group_boundary['qq_group_latest_trigger_reason']} "
                f"policy={group_boundary['qq_group_latest_reply_policy']} "
                f"allowed_groups={group_boundary['qq_group_reply_allowed_group_count']} "
                f"shadow_only_groups={group_boundary['qq_group_shadow_only_group_count']} "
                f"trigger={group_boundary['qq_group_trigger_mode']} "
                f"followup={group_boundary['qq_group_followup_window_seconds']}s"
            ),
        ),
    ]


def group_social_fields(root: Path) -> dict[str, str]:
    """Group social memory diagnostics (plan §7). Hashes/counts only — never a
    raw QQ id."""

    from xinyu_group_social_sidecar import group_social_enabled
    from xinyu_group_social_store import read_social_state

    try:
        state = read_social_state(root)
    except Exception:  # diagnostics must never break the status panel
        state = {"groups": {}, "event_count": 0}
    groups = state.get("groups", {}) if isinstance(state.get("groups"), dict) else {}
    latest = ""
    collisions = 0
    for group in groups.values():
        if not isinstance(group, dict):
            continue
        last_seen = str(group.get("last_seen_at") or "")
        if last_seen > latest:
            latest = last_seen
        alias_owners: dict[str, set[str]] = {}
        members = group.get("members", {}) if isinstance(group.get("members"), dict) else {}
        for member_hash, member in members.items():
            if not isinstance(member, dict):
                continue
            for alias in member.get("aliases", []):
                name = alias.get("normalized") or alias.get("text") if isinstance(alias, dict) else ""
                if name:
                    alias_owners.setdefault(str(name), set()).add(str(member_hash))
        collisions += sum(1 for owners in alias_owners.values() if len(owners) > 1)
    return {
        "group_social_enabled": "true" if group_social_enabled() else "false",
        "group_social_event_count": str(int(state.get("event_count", 0) or 0)),
        "group_social_group_count": str(len(groups)),
        "latest_group_social_observed_at": latest or "missing",
        "alias_collision_count": str(collisions),
        "group_retrieval_boundary_status": "group_id_hash_filter_active",
    }


def status_fields(root: Path) -> dict[str, str]:
    proactive = read_text(root / "memory/context/proactive_presence_state.md")
    dispatch = read_text(root / "memory/context/proactive_qq_dispatch_state.md")
    outbox = read_text(root / "memory/context/qq_outbox_dispatch_state.md")
    short_term_continuity = read_text(root / "memory/context/short_term_continuity_state.md")
    short_term_continuity_canary = read_text(root / "memory/context/short_term_continuity_canary_state.md")
    short_term_recall_diagnostics = read_text(root / "memory/context/short_term_recall_diagnostics_state.md")
    review = read_text(root / "memory/self/ai_self_iteration_review_state.md")
    gate = read_text(root / "memory/self/ai_self_iteration_state.md")
    capability = read_text(root / "memory/context/capability_zones_state.md")
    v1_canary = read_text(root / "memory/context/v1_canary_readiness_state.md")
    initiative_spine = read_text(root / "memory/context/initiative_spine_state.md")
    desire_drive = build_desire_drive_snapshot(root)
    expression_self_learning = read_text(root / "memory/self/expression_self_learning_state.md")
    action_feedback_coverage = build_action_feedback_coverage_report(root)
    perception_importance = build_perception_importance_report(root)
    owner_feedback_effect = build_owner_feedback_effect_report(root)
    proactive_response_diagnostics = build_proactive_response_diagnostics(root)
    autonomy_decision = autonomy_decision_chain_fields(root)
    feedback_consumption_diagnostics = build_feedback_consumption_diagnostics(root)
    memory_health = build_memory_health_report(root, max_clusters=8)
    stage9_self_state_model = build_stage9_self_state_model(root)
    stage10_proactive_life_loop = build_stage10_proactive_life_loop(root)
    stage11_multisensory_extension = build_stage11_multisensory_extension(root)
    stage11_visual_ingress = build_stage11_visual_ingress_diagnostics(root)
    stage11_voice_ingress = build_stage11_voice_ingress_diagnostics(root)
    stage12_long_term_evaluation = build_stage12_long_term_evaluation(
        root,
        load_live_status=False,
        live_status_data=_stage12_live_status_stub(),
    )
    memory_learning_trial = learning_trial_gate_fields(root)
    qq_group_boundary = qq_group_reply_boundary_fields(root)
    qq_private_flow = qq_private_reply_flow_fields(root)
    qq_latest_inbound_flow = qq_latest_inbound_flow_fields(root)
    private_reply_selftest = private_reply_selftest_fields(root)
    group_social = group_social_fields(root)
    coverage_metrics = (
        action_feedback_coverage.get("metrics")
        if isinstance(action_feedback_coverage.get("metrics"), dict)
        else {}
    )
    coverage_surfaces = (
        action_feedback_coverage.get("surfaces")
        if isinstance(action_feedback_coverage.get("surfaces"), dict)
        else {}
    )
    perception_metrics = (
        perception_importance.get("metrics")
        if isinstance(perception_importance.get("metrics"), dict)
        else {}
    )
    feedback_consumption_metrics = (
        feedback_consumption_diagnostics.get("metrics")
        if isinstance(feedback_consumption_diagnostics.get("metrics"), dict)
        else {}
    )
    feedback_consumption_latest = (
        feedback_consumption_diagnostics.get("latest_sample")
        if isinstance(feedback_consumption_diagnostics.get("latest_sample"), dict)
        else {}
    )
    feedback_consumption_closure = (
        feedback_consumption_diagnostics.get("stage7_feedback_closure")
        if isinstance(feedback_consumption_diagnostics.get("stage7_feedback_closure"), dict)
        else {}
    )
    stage8_memory_governance = (
        memory_health.get("stage8_memory_governance")
        if isinstance(memory_health.get("stage8_memory_governance"), dict)
        else {}
    )
    stage13_self_narrative = build_stage13_self_narrative(
        root,
        stage12_report=stage12_long_term_evaluation,
        stage8_governance=stage8_memory_governance,
        owner_feedback_effect_report=owner_feedback_effect,
    )
    private_ecosystem = build_private_ecosystem_snapshot(root)
    private_ecosystem_counters = (
        private_ecosystem.get("counters")
        if isinstance(private_ecosystem.get("counters"), dict)
        else {}
    )
    private_ecosystem_share = (
        private_ecosystem.get("owner_private_share")
        if isinstance(private_ecosystem.get("owner_private_share"), dict)
        else {}
    )
    private_ecosystem_journal = (
        private_ecosystem.get("journal")
        if isinstance(private_ecosystem.get("journal"), dict)
        else {}
    )
    private_ecosystem_boundaries = (
        private_ecosystem.get("boundaries")
        if isinstance(private_ecosystem.get("boundaries"), dict)
        else {}
    )
    # Isolated desktop status is read from grants + the workspace state file only
    # (no Docker call, no container side effects) so the status surface stays fast.
    private_desktop = build_desktop_snapshot(root)
    private_desktop_grant = (
        private_desktop.get("grant") if isinstance(private_desktop.get("grant"), dict) else {}
    )
    private_desktop_boundaries = (
        private_desktop.get("boundaries") if isinstance(private_desktop.get("boundaries"), dict) else {}
    )
    stage9_model = (
        stage9_self_state_model.get("model")
        if isinstance(stage9_self_state_model.get("model"), dict)
        else {}
    )
    stage9_boundaries = (
        stage9_self_state_model.get("boundaries")
        if isinstance(stage9_self_state_model.get("boundaries"), dict)
        else {}
    )
    stage10_loop = (
        stage10_proactive_life_loop.get("loop")
        if isinstance(stage10_proactive_life_loop.get("loop"), dict)
        else {}
    )
    stage10_gate_proof = (
        stage10_proactive_life_loop.get("gate_proof")
        if isinstance(stage10_proactive_life_loop.get("gate_proof"), dict)
        else {}
    )
    stage10_boundaries = (
        stage10_proactive_life_loop.get("boundaries")
        if isinstance(stage10_proactive_life_loop.get("boundaries"), dict)
        else {}
    )
    stage11_model = (
        stage11_multisensory_extension.get("model")
        if isinstance(stage11_multisensory_extension.get("model"), dict)
        else {}
    )
    stage11_boundaries = (
        stage11_multisensory_extension.get("boundaries")
        if isinstance(stage11_multisensory_extension.get("boundaries"), dict)
        else {}
    )
    stage11_visual_ingress_model = (
        stage11_visual_ingress.get("model")
        if isinstance(stage11_visual_ingress.get("model"), dict)
        else {}
    )
    stage11_voice_ingress_model = (
        stage11_voice_ingress.get("model")
        if isinstance(stage11_voice_ingress.get("model"), dict)
        else {}
    )
    stage12_model = (
        stage12_long_term_evaluation.get("model")
        if isinstance(stage12_long_term_evaluation.get("model"), dict)
        else {}
    )
    stage12_gate_proof = (
        stage12_long_term_evaluation.get("gate_proof")
        if isinstance(stage12_long_term_evaluation.get("gate_proof"), dict)
        else {}
    )
    stage12_privacy = (
        stage12_long_term_evaluation.get("privacy")
        if isinstance(stage12_long_term_evaluation.get("privacy"), dict)
        else {}
    )
    stage13_model = (
        stage13_self_narrative.get("model")
        if isinstance(stage13_self_narrative.get("model"), dict)
        else {}
    )
    stage13_behavior = (
        stage13_model.get("behavior_explanation")
        if isinstance(stage13_model.get("behavior_explanation"), dict)
        else {}
    )
    stage13_governance = (
        stage13_model.get("memory_governance_state")
        if isinstance(stage13_model.get("memory_governance_state"), dict)
        else {}
    )
    stage13_debt = (
        stage13_model.get("historical_recall_debt")
        if isinstance(stage13_model.get("historical_recall_debt"), dict)
        else {}
    )
    stage13_boundaries = (
        stage13_self_narrative.get("boundaries")
        if isinstance(stage13_self_narrative.get("boundaries"), dict)
        else {}
    )

    def coverage_surface_status(name: str) -> str:
        surface = coverage_surfaces.get(name) if isinstance(coverage_surfaces.get(name), dict) else {}
        return str(surface.get("surface_status", "missing"))

    def coverage_surface_lifecycle(name: str) -> str:
        surface = coverage_surfaces.get(name) if isinstance(coverage_surfaces.get(name), dict) else {}
        return str(surface.get("lifecycle_status", "missing"))

    return {
        **autonomy_decision,
        **memory_learning_trial,
        **qq_group_boundary,
        **qq_private_flow,
        **qq_latest_inbound_flow,
        **private_reply_selftest,
        **group_social,
        "proactive_evaluated_at": extract_value(proactive, "evaluated_at", "missing"),
        "proactive_decision": extract_value(proactive, "proactive_decision", "missing"),
        "proactive_reason": extract_value(proactive, "reason", "missing"),
        "qq_send_permission": extract_value(proactive, "qq_send_permission", "missing"),
        "candidate_message": extract_value(proactive, "candidate_message", "missing"),
        "last_claim_status": extract_value(dispatch, "last_claim_status", "missing"),
        "last_claim_id": mask_private_identifier(extract_value(dispatch, "last_claim_id", "missing")),
        "last_ack_status": extract_value(dispatch, "last_ack_status", "missing"),
        "adapter_error": extract_value(dispatch, "adapter_error", "missing"),
        "qq_outbox_queued": extract_value(outbox, "queued_count", "missing"),
        "qq_outbox_claimed": extract_value(outbox, "claimed_count", "missing"),
        "qq_outbox_sent": extract_value(outbox, "sent_count", "missing"),
        "qq_outbox_failed": extract_value(outbox, "failed_count", "missing"),
        "v1_canary_decision": extract_value(v1_canary, "readiness_decision", "missing"),
        "v1_canary_switch_permission": extract_value(v1_canary, "switch_permission", "missing"),
        "v1_canary_auto_full_switch": extract_value(v1_canary, "auto_full_switch", "missing"),
        "v1_canary_proposal_status": extract_value(v1_canary, "proposal_status", "missing"),
        "v1_canary_sample_window": extract_value(v1_canary, "sample_window_turns", "missing"),
        "v1_canary_error_rate": extract_value(v1_canary, "error_rate", "missing"),
        "ai_gate_status": extract_value(gate, "gate_status", "missing"),
        "ai_gate_confidence": extract_value(gate, "confidence_score", "missing"),
        "ai_review_permission": extract_value(review, "review_permission", "missing"),
        "ai_review_stable_profile": extract_value(review, "stable_profile_write_permission", "missing"),
        "capability_proactive_qq_send": extract_value(capability, "proactive_qq_send", "missing"),
        "capability_private_scope": extract_value(capability, "private_file_scope", "missing"),
        "capability_codex_operator": extract_value(capability, "codex_as_eye_and_hand", "missing"),
        "capability_codex_workspace": redact_local_path(extract_value(capability, "codex_download_workspace", "missing")),
        "capability_qq_external_private": extract_value(capability, "qq_external_private_bridge", "missing"),
        "capability_qq_group": extract_value(capability, "qq_group_bridge", "missing"),
        "capability_qq_priority_passive_group": extract_value(
            capability,
            "qq_priority_passive_learning_group",
            "missing",
        ),
        "initiative_spine_status": extract_value(initiative_spine, "status", "missing"),
        "initiative_spine_emergence": extract_value(initiative_spine, "emergence_level", "missing"),
        "initiative_spine_action": extract_value(initiative_spine, "action_permission", "missing"),
        "initiative_spine_next_step": extract_value(initiative_spine, "next_step", "missing"),
        "desire_drive_status": desire_drive.status,
        "desire_drive_dominant": desire_drive.dominant_drive,
        "desire_drive_intensity": str(desire_drive.drive_intensity),
        "desire_drive_autonomy_tension": desire_drive.autonomy_tension,
        "desire_drive_blocked_by": ",".join(desire_drive.blocked_by) if desire_drive.blocked_by else "none",
        "desire_drive_candidate_effect": desire_drive.candidate_effect,
        "desire_drive_feedback_effect": desire_drive.feedback_effect,
        "desire_drive_next_safe_action": desire_drive.next_safe_action,
        "desire_drive_no_qq_enqueue": "true",
        "desire_drive_stable_memory_write": "blocked",
        "desire_drive_consciousness_claim": "false",
        "short_term_continuity_status": extract_value(short_term_continuity, "status", "missing"),
        "short_term_continuity_direct_reference": extract_value(
            short_term_continuity,
            "direct_reference",
            "missing",
        ),
        "short_term_continuity_recall_status": extract_value(
            short_term_continuity,
            "recall_status",
            "missing",
        ),
        "short_term_continuity_recall_source": extract_value(
            short_term_continuity,
            "recall_source",
            "missing",
        ),
        "short_term_continuity_tail_count": extract_value(short_term_continuity, "tail_count", "missing"),
        "short_term_continuity_archive_recovered_count": extract_value(
            short_term_continuity,
            "archive_recovered_count",
            "missing",
        ),
        "short_term_continuity_recent_user_count": extract_value(
            short_term_continuity,
            "recent_user_count",
            "missing",
        ),
        "short_term_continuity_recent_assistant_count": extract_value(
            short_term_continuity,
            "recent_assistant_count",
            "missing",
        ),
        "short_term_continuity_latest_user_ref": extract_value(
            short_term_continuity,
            "latest_user_ref",
            "missing",
        ),
        "short_term_continuity_latest_assistant_ref": extract_value(
            short_term_continuity,
            "latest_assistant_ref",
            "missing",
        ),
        "short_term_continuity_canary_status": extract_value(
            short_term_continuity_canary,
            "status",
            "missing",
        ),
        "short_term_continuity_canary_direct_reference_count": extract_value(
            short_term_continuity_canary,
            "direct_reference_count",
            "missing",
        ),
        "short_term_continuity_canary_recall_success_rate": extract_value(
            short_term_continuity_canary,
            "direct_reference_recall_success_rate_pct",
            "missing",
        ),
        "short_term_continuity_canary_matched_reply_count": extract_value(
            short_term_continuity_canary,
            "matched_reply_count",
            "missing",
        ),
        "short_term_continuity_canary_unmatched_reply_count": extract_value(
            short_term_continuity_canary,
            "unmatched_reply_count",
            "missing",
        ),
        "short_term_continuity_canary_which_sentence_recurrence_count": extract_value(
            short_term_continuity_canary,
            "which_sentence_recurrence_count",
            "missing",
        ),
        "short_term_continuity_canary_which_sentence_recurrence_rate": extract_value(
            short_term_continuity_canary,
            "which_sentence_recurrence_rate_pct",
            "missing",
        ),
        "short_term_recall_diagnostics_status": extract_value(
            short_term_recall_diagnostics,
            "status",
            "missing",
        ),
        "short_term_recall_diagnostics_failure_class": extract_value(
            short_term_recall_diagnostics,
            "primary_failure_class",
            "missing",
        ),
        "short_term_recall_diagnostics_working_tail": extract_value(
            short_term_recall_diagnostics,
            "working_tail_status",
            "missing",
        ),
        "short_term_recall_diagnostics_archive": extract_value(
            short_term_recall_diagnostics,
            "archive_fallback_status",
            "missing",
        ),
        "short_term_recall_diagnostics_prompt": extract_value(
            short_term_recall_diagnostics,
            "prompt_admission_status",
            "missing",
        ),
        "short_term_recall_diagnostics_budget": extract_value(
            short_term_recall_diagnostics,
            "prompt_budget_status",
            "missing",
        ),
        "perception_importance_status": str(perception_importance.get("status", "missing")),
        "perception_importance_event_count": str(perception_metrics.get("event_count", "0")),
        "perception_importance_judged_event_count": str(perception_metrics.get("judged_event_count", "0")),
        "perception_importance_high_attention_count": str(perception_metrics.get("high_attention_count", "0")),
        "perception_importance_anomaly_judgment_count": str(
            perception_metrics.get("anomaly_judgment_count", "0")
        ),
        "perception_importance_internal_gap_count": str(perception_metrics.get("internal_gap_count", "0")),
        "perception_importance_owner_attention_count": str(perception_metrics.get("owner_attention_count", "0")),
        "perception_importance_repair_gap_count": str(perception_metrics.get("repair_gap_count", "0")),
        "perception_importance_maintenance_gap_count": str(perception_metrics.get("maintenance_gap_count", "0")),
        "perception_importance_latest_gap_type": str(perception_metrics.get("latest_gap_type", "none")),
        "perception_importance_next_route_hint": str(perception_metrics.get("next_route_hint", "none")),
        "feedback_consumption_diagnostics_status": str(
            feedback_consumption_diagnostics.get("status", "missing")
        ),
        "feedback_consumption_sample_count": str(feedback_consumption_metrics.get("sample_count", "0")),
        "feedback_consumption_source_count": str(feedback_consumption_metrics.get("feedback_source_count", "0")),
        "feedback_consumption_required_count": str(
            feedback_consumption_metrics.get("feedback_required_count", "0")
        ),
        "feedback_consumption_legacy_uninstrumented_count": str(
            feedback_consumption_metrics.get("legacy_uninstrumented_count", "0")
        ),
        "feedback_consumption_consumed_count": str(feedback_consumption_metrics.get("consumed_count", "0")),
        "feedback_consumption_partial_count": str(feedback_consumption_metrics.get("partial_count", "0")),
        "feedback_consumption_missing_count": str(feedback_consumption_metrics.get("missing_count", "0")),
        "feedback_consumption_rate_pct": str(feedback_consumption_metrics.get("consumption_rate_pct", "0.0")),
        "feedback_consumption_latest_status": str(feedback_consumption_latest.get("status", "none")),
        "feedback_consumption_latest_sources": str(feedback_consumption_latest.get("sources", "none")),
        "feedback_consumption_latest_biases": str(feedback_consumption_latest.get("biases", "none")),
        "feedback_consumption_latest_future_effect": str(
            feedback_consumption_latest.get("future_effect", "none")
        ),
        "feedback_consumption_consumed_streak": str(feedback_consumption_metrics.get("consumed_streak", "0")),
        "feedback_consumption_missing_streak": str(feedback_consumption_metrics.get("missing_streak", "0")),
        "stage7_feedback_closure_status": str(feedback_consumption_closure.get("status", "missing")),
        "stage7_feedback_ready_for_stage8": str(
            bool(feedback_consumption_closure.get("ready_for_stage8", False))
        ).lower(),
        "stage7_feedback_closure_reason": str(feedback_consumption_closure.get("reason", "missing")),
        "stage7_feedback_required_samples": str(feedback_consumption_closure.get("required_samples", "0")),
        "stage7_feedback_auditable_samples": str(feedback_consumption_closure.get("auditable_samples", "0")),
        "stage7_feedback_consumed_streak": str(feedback_consumption_closure.get("consumed_streak", "0")),
        "stage7_feedback_next_step": str(feedback_consumption_closure.get("next_step", "missing")),
        "stage8_memory_governance_status": str(stage8_memory_governance.get("status", "missing")),
        "stage8_memory_ready_for_stage9": str(
            bool(stage8_memory_governance.get("ready_for_stage9", False))
        ).lower(),
        "stage8_memory_governance_reason": str(stage8_memory_governance.get("reason", "missing")),
        "stage8_stage7_ready_for_stage8": str(
            bool(stage8_memory_governance.get("stage7_ready_for_stage8", False))
        ).lower(),
        "stage8_candidate_total": str(stage8_memory_governance.get("candidate_total", "0")),
        "stage8_owner_review_required_count": str(
            stage8_memory_governance.get("owner_review_required_count", "0")
        ),
        "stage8_private_or_owner_scoped_count": str(
            stage8_memory_governance.get("private_or_owner_scoped_count", "0")
        ),
        "stage8_duplicate_cluster_count": str(stage8_memory_governance.get("duplicate_cluster_count", "0")),
        "stage8_learning_trial_success_gate": str(
            stage8_memory_governance.get("learning_trial_success_gate", "missing")
        ),
        "stage8_learning_trial_validation_status": str(
            stage8_memory_governance.get("learning_trial_validation_status", "missing")
        ),
        "stage8_learning_trial_validation_active_key": str(
            stage8_memory_governance.get("learning_trial_validation_active_key", "none")
        ),
        "stage8_learning_trial_validation_needed_success_count": str(
            stage8_memory_governance.get("learning_trial_validation_needed_success_count", "0")
        ),
        "stage8_learning_trial_owner_action": str(
            stage8_memory_governance.get("learning_trial_validation_owner_action", "none")
        ),
        "stage8_stable_profile_write": str(stage8_memory_governance.get("stable_profile_write", "missing")),
        "stage8_owner_memory_write": str(stage8_memory_governance.get("owner_memory_write", "missing")),
        "stage8_owner_review_candidate_text": str(
            stage8_memory_governance.get("owner_review_candidate_text", "missing")
        ),
        "stage8_stable_personality_write": str(
            stage8_memory_governance.get("stable_personality_write", "missing")
        ),
        "stage8_growth_apply_mode": str(stage8_memory_governance.get("growth_apply_mode", "missing")),
        "stage8_stable_identity_profile_apply": str(
            stage8_memory_governance.get("stable_identity_profile_apply", "missing")
        ),
        "stage8_memory_next_step": str(stage8_memory_governance.get("next_step", "missing")),
        "stage9_self_state_model_status": str(stage9_self_state_model.get("status", "missing")),
        "stage9_ready_for_stage10": str(bool(stage9_self_state_model.get("ready_for_stage10", False))).lower(),
        "stage9_self_state_model_reason": str(stage9_self_state_model.get("reason", "missing")),
        "stage9_current_task": str(stage9_model.get("current_task", "missing")),
        "stage9_relation_posture": str(stage9_model.get("relation_posture", "missing")),
        "stage9_recent_action_result": str(stage9_model.get("recent_action_result", "missing")),
        "stage9_unfinished_intention_count": str(len(stage9_model.get("unfinished_intentions", []) or [])),
        "stage9_current_limit_count": str(len(stage9_model.get("current_limits", []) or [])),
        "stage9_available_action_count": str(len(stage9_model.get("available_actions", []) or [])),
        "stage9_silence_reason": str(stage9_model.get("silence_reason", "missing")),
        "stage9_reply_influence_status": str(stage9_model.get("reply_influence_status", "missing")),
        "stage9_state_contract": str(stage9_model.get("state_contract", "missing")),
        "stage9_next_step": str(stage9_model.get("next_step", "missing")),
        "stage9_raw_owner_text_in_state": str(bool(stage9_boundaries.get("raw_owner_text_in_state", True))).lower(),
        "stage9_visible_reply_text_in_state": str(
            bool(stage9_boundaries.get("visible_reply_text_in_state", True))
        ).lower(),
        "stage9_consciousness_claim": str(bool(stage9_boundaries.get("consciousness_claim", True))).lower(),
        "stage9_stable_identity_profile_apply": str(
            stage9_boundaries.get("stable_identity_profile_apply", "missing")
        ),
        "stage10_proactive_life_loop_status": str(stage10_proactive_life_loop.get("status", "missing")),
        "stage10_ready_for_stage11": str(
            bool(stage10_proactive_life_loop.get("ready_for_stage11", False))
        ).lower(),
        "stage10_proactive_life_loop_reason": str(stage10_proactive_life_loop.get("reason", "missing")),
        "stage10_selected_goal_id": str(stage10_loop.get("selected_goal_id", "missing")),
        "stage10_selected_goal_status": str(stage10_loop.get("selected_goal_status", "missing")),
        "stage10_selected_goal_score": str(stage10_loop.get("selected_goal_score", "missing")),
        "stage10_candidate_count": str(stage10_loop.get("candidate_count", "0")),
        "stage10_candidate_lifecycle": str(stage10_loop.get("candidate_lifecycle", "missing")),
        "stage10_candidate_lifecycle_reason": str(stage10_loop.get("candidate_lifecycle_reason", "missing")),
        "stage10_low_risk_action_candidate_count": str(
            stage10_loop.get("low_risk_action_candidate_count", "0")
        ),
        "stage10_approval_required_action_candidate_count": str(
            stage10_loop.get("approval_required_action_candidate_count", "0")
        ),
        "stage10_proactive_response_status": str(stage10_loop.get("proactive_response_status", "missing")),
        "stage10_proactive_response_signal": str(stage10_loop.get("proactive_response_signal", "missing")),
        "stage10_proactive_waiting_owner": str(bool(stage10_loop.get("proactive_waiting_owner", False))).lower(),
        "stage10_proactive_timeout_active": str(bool(stage10_loop.get("proactive_timeout_active", False))).lower(),
        "stage10_outward_action_policy": str(stage10_loop.get("outward_action_policy", "missing")),
        "stage10_silence_decision": str(stage10_loop.get("silence_decision", "missing")),
        "stage10_next_safe_step": str(stage10_loop.get("next_safe_step", "missing")),
        "stage10_life_loop_contract": str(stage10_loop.get("life_loop_contract", "missing")),
        "stage10_candidate_send_separated": str(
            bool(stage10_gate_proof.get("proactive_candidate_and_send_separated", False))
        ).lower(),
        "stage10_silence_written_as_decision": str(
            bool(stage10_gate_proof.get("silence_written_as_decision", False))
        ).lower(),
        "stage10_candidate_has_lifecycle": str(bool(stage10_gate_proof.get("candidate_has_lifecycle", False))).lower(),
        "stage10_raw_owner_text_in_state": str(
            bool(stage10_boundaries.get("raw_owner_text_in_state", True))
        ).lower(),
        "stage10_visible_reply_text_in_state": str(
            bool(stage10_boundaries.get("visible_reply_text_in_state", True))
        ).lower(),
        "stage10_qq_message_enqueued": str(bool(stage10_boundaries.get("qq_message_enqueued", True))).lower(),
        "stage10_consciousness_claim": str(bool(stage10_boundaries.get("consciousness_claim", True))).lower(),
        "stage11_multisensory_extension_status": str(
            stage11_multisensory_extension.get("status", "missing")
        ),
        "stage11_ready_for_stage12": str(
            bool(stage11_multisensory_extension.get("ready_for_stage12", False))
        ).lower(),
        "stage11_reason": str(stage11_multisensory_extension.get("reason", "missing")),
        "stage11_visual_event_count": str(stage11_model.get("visual_event_count", "0")),
        "stage11_voice_event_count": str(stage11_model.get("voice_event_count", "0")),
        "stage11_multimodal_event_count": str(stage11_model.get("multimodal_event_count", "0")),
        "stage11_sensory_event_count": str(stage11_model.get("sensory_event_count", "0")),
        "stage11_sensory_required_field_missing_count": str(
            stage11_model.get("sensory_required_field_missing_count", "0")
        ),
        "stage11_sensory_observation_judgment_count": str(
            stage11_model.get("sensory_observation_judgment_count", "0")
        ),
        "stage11_owner_attention_judgment_count": str(
            stage11_model.get("owner_attention_judgment_count", "0")
        ),
        "stage11_sensory_route_status": str(stage11_model.get("sensory_route_status", "missing")),
        "stage11_fact_boundary": str(stage11_model.get("fact_boundary", "missing")),
        "stage11_next_step": str(stage11_model.get("next_step", "missing")),
        "stage11_contract": str(stage11_model.get("stage11_contract", "missing")),
        "stage11_visual_ingress_status": str(stage11_visual_ingress.get("status", "missing")),
        "stage11_visual_qq_trace_exists": str(
            bool(stage11_visual_ingress_model.get("qq_trace_exists", False))
        ).lower(),
        "stage11_visual_qq_trace_line_count": str(stage11_visual_ingress_model.get("qq_trace_line_count", "0")),
        "stage11_visual_qq_scanned_line_count": str(
            stage11_visual_ingress_model.get("qq_scanned_line_count", "0")
        ),
        "stage11_visual_count_field_row_count": str(
            stage11_visual_ingress_model.get("visual_count_field_row_count", "0")
        ),
        "stage11_visual_payload_row_count": str(
            stage11_visual_ingress_model.get("visual_payload_row_count", "0")
        ),
        "stage11_visual_image_context_row_count": str(
            stage11_visual_ingress_model.get("image_context_row_count", "0")
        ),
        "stage11_visual_image_context_available_count": str(
            stage11_visual_ingress_model.get("image_context_available_count", "0")
        ),
        "stage11_visual_image_context_ocr_result_count": str(
            stage11_visual_ingress_model.get("image_context_ocr_result_count", "0")
        ),
        "stage11_visual_image_context_vision_result_count": str(
            stage11_visual_ingress_model.get("image_context_vision_result_count", "0")
        ),
        "stage11_visual_ocr_trace_exists": str(
            bool(stage11_visual_ingress_model.get("ocr_trace_exists", False))
        ).lower(),
        "stage11_visual_ocr_trace_line_count": str(
            stage11_visual_ingress_model.get("ocr_trace_line_count", "0")
        ),
        "stage11_visual_ocr_attempt_count": str(stage11_visual_ingress_model.get("ocr_attempt_count", "0")),
        "stage11_visual_ocr_result_count": str(stage11_visual_ingress_model.get("ocr_result_count", "0")),
        "stage11_visual_ocr_error_count": str(stage11_visual_ingress_model.get("ocr_error_count", "0")),
        "stage11_visual_evidence_mode": str(stage11_visual_ingress_model.get("evidence_mode", "none")),
        "stage11_visual_ingress_next_step": str(stage11_visual_ingress_model.get("next_step", "missing")),
        "stage11_voice_ingress_status": str(stage11_voice_ingress.get("status", "missing")),
        "stage11_voice_qq_trace_exists": str(
            bool(stage11_voice_ingress_model.get("qq_trace_exists", False))
        ).lower(),
        "stage11_voice_qq_trace_line_count": str(stage11_voice_ingress_model.get("qq_trace_line_count", "0")),
        "stage11_voice_qq_scanned_line_count": str(stage11_voice_ingress_model.get("qq_scanned_line_count", "0")),
        "stage11_voice_count_field_row_count": str(
            stage11_voice_ingress_model.get("voice_count_field_row_count", "0")
        ),
        "stage11_voice_payload_row_count": str(stage11_voice_ingress_model.get("voice_payload_row_count", "0")),
        "stage11_voice_transcript_trace_file_count": str(
            stage11_voice_ingress_model.get("voice_transcript_trace_file_count", "0")
        ),
        "stage11_voice_transcript_trace_line_count": str(
            stage11_voice_ingress_model.get("voice_transcript_trace_line_count", "0")
        ),
        "stage11_voice_transcript_attempt_count": str(
            stage11_voice_ingress_model.get("voice_transcript_attempt_count", "0")
        ),
        "stage11_voice_transcript_result_count": str(
            stage11_voice_ingress_model.get("voice_transcript_result_count", "0")
        ),
        "stage11_voice_transcript_error_count": str(
            stage11_voice_ingress_model.get("voice_transcript_error_count", "0")
        ),
        "stage11_voice_evidence_mode": str(stage11_voice_ingress_model.get("evidence_mode", "none")),
        "stage11_voice_ingress_next_step": str(stage11_voice_ingress_model.get("next_step", "missing")),
        "stage11_raw_owner_text_in_state": str(
            bool(stage11_boundaries.get("raw_owner_text_in_state", True))
        ).lower(),
        "stage11_raw_visual_body_in_state": str(
            bool(stage11_boundaries.get("raw_visual_body_in_state", True))
        ).lower(),
        "stage11_raw_voice_transcript_in_state": str(
            bool(stage11_boundaries.get("raw_voice_transcript_in_state", True))
        ).lower(),
        "stage11_raw_image_bytes_retained": str(
            bool(stage11_boundaries.get("raw_image_bytes_retained", True))
        ).lower(),
        "stage11_raw_audio_bytes_retained": str(
            bool(stage11_boundaries.get("raw_audio_bytes_retained", True))
        ).lower(),
        "stage11_model_inference_written_as_fact": str(
            bool(stage11_boundaries.get("model_inference_written_as_fact", True))
        ).lower(),
        "stage11_stable_memory_write": str(stage11_boundaries.get("stable_memory_write", "missing")),
        "stage11_qq_message_enqueued": str(bool(stage11_boundaries.get("qq_message_enqueued", True))).lower(),
        "stage11_consciousness_claim": str(bool(stage11_boundaries.get("consciousness_claim", True))).lower(),
        "stage12_long_term_evaluation_status": str(
            stage12_long_term_evaluation.get("status", "missing")
        ),
        "stage12_ready_for_stage13": str(
            bool(stage12_long_term_evaluation.get("ready_for_stage13", False))
        ).lower(),
        "stage12_reason": str(stage12_long_term_evaluation.get("reason", "missing")),
        "stage12_live_loop_status": str(stage12_model.get("live_loop_status", "missing")),
        "stage12_live_loop_required_check_count": str(
            stage12_model.get("live_loop_required_check_count", "0")
        ),
        "stage12_live_loop_passed_required_check_count": str(
            stage12_model.get("live_loop_passed_required_check_count", "0")
        ),
        "stage12_live_loop_required_pass_rate_pct": str(
            stage12_model.get("live_loop_required_pass_rate_pct", "0")
        ),
        "stage12_live_loop_has_recent_sample": str(
            bool(stage12_model.get("live_loop_has_recent_sample", False))
        ).lower(),
        "stage12_live_loop_failing_required_checks": str(
            stage12_model.get("live_loop_failing_required_checks", "none")
        ),
        "stage12_live_loop_failing_required_check_detail": str(
            stage12_model.get("live_loop_failing_required_check_detail", "none")
        ),
        "stage12_latest_dialogue_recall_window_minutes": str(
            stage12_model.get("latest_dialogue_recall_window_minutes", "0")
        ),
        "stage12_latest_dialogue_recall_status": str(
            stage12_model.get("latest_dialogue_recall_status", "missing")
        ),
        "stage12_latest_dialogue_recall_success_rate_pct": str(
            stage12_model.get("latest_dialogue_recall_success_rate_pct", "0")
        ),
        "stage12_latest_dialogue_recall_recent_sample_present": str(
            bool(stage12_model.get("latest_dialogue_recall_recent_sample_present", False))
        ).lower(),
        "stage12_latest_dialogue_recall_recent_sample_count": str(
            stage12_model.get("latest_dialogue_recall_recent_sample_count", "0")
        ),
        "stage12_feedback_consumption_status": str(
            stage12_model.get("feedback_consumption_status", "missing")
        ),
        "stage12_feedback_consumption_rate_pct": str(
            stage12_model.get("feedback_consumption_rate_pct", "0")
        ),
        "stage12_proactive_candidate_window_count": str(
            stage12_model.get("proactive_candidate_window_count", "0")
        ),
        "stage12_proactive_candidate_blocked_count": str(
            stage12_model.get("proactive_candidate_blocked_count", "0")
        ),
        "stage12_proactive_candidate_block_rate_pct": str(
            stage12_model.get("proactive_candidate_block_rate_pct", "0")
        ),
        "stage12_proactive_candidate_send_count": str(
            stage12_model.get("proactive_candidate_send_count", "0")
        ),
        "stage12_proactive_candidate_send_rate_pct": str(
            stage12_model.get("proactive_candidate_send_rate_pct", "0")
        ),
        "stage12_raw_private_leak_count": str(stage12_model.get("raw_private_leak_count", "0")),
        "stage12_stable_memory_miswrite_count": str(
            stage12_model.get("stable_memory_miswrite_count", "0")
        ),
        "stage12_owner_repair_count": str(stage12_model.get("owner_repair_count", "0")),
        "stage12_owner_success_count": str(stage12_model.get("owner_success_count", "0")),
        "stage12_owner_repair_recurrence_rate_pct": str(
            stage12_model.get("owner_repair_recurrence_rate_pct", "0")
        ),
        "stage12_explainable_silence_window_count": str(
            stage12_model.get("explainable_silence_window_count", "0")
        ),
        "stage12_explainable_silence_explained_count": str(
            stage12_model.get("explainable_silence_explained_count", "0")
        ),
        "stage12_explainable_silence_rate_pct": str(
            stage12_model.get("explainable_silence_rate_pct", "0")
        ),
        "stage12_v1_canary_readiness_decision": str(
            stage12_model.get("v1_canary_readiness_decision", "missing")
        ),
        "stage12_v1_canary_proposal_status": str(
            stage12_model.get("v1_canary_proposal_status", "missing")
        ),
        "stage12_v1_canary_error_rate": str(stage12_model.get("v1_canary_error_rate", "missing")),
        "stage12_v1_canary_sample_window_turns": str(
            stage12_model.get("v1_canary_sample_window_turns", "0")
        ),
        "stage12_private_reply_selftest_status": str(
            stage12_model.get("private_reply_selftest_status", "missing")
        ),
        "stage12_private_reply_selftest_raw_text_included": str(
            bool(stage12_model.get("private_reply_selftest_raw_text_included", False))
        ).lower(),
        "stage12_private_reply_selftest_visible_reply_included": str(
            bool(stage12_model.get("private_reply_selftest_visible_reply_included", False))
        ).lower(),
        "stage12_owner_visible_canary_ready": str(
            bool(stage12_model.get("owner_visible_canary_ready", False))
        ).lower(),
        "stage12_historical_dialogue_recall_debt_status": str(
            stage12_model.get("historical_dialogue_recall_debt_status", "missing")
        ),
        "stage12_historical_dialogue_recall_issue_count": str(
            stage12_model.get("historical_dialogue_recall_issue_count", "0")
        ),
        "stage12_historical_dialogue_recall_status": str(
            stage12_model.get("historical_dialogue_recall_status", "missing")
        ),
        "stage12_historical_dialogue_recall_success_rate_pct": str(
            stage12_model.get("historical_dialogue_recall_success_rate_pct", "0")
        ),
        "stage12_historical_dialogue_recall_direct_reference_count": str(
            stage12_model.get("historical_dialogue_recall_direct_reference_count", "0")
        ),
        "stage12_historical_dialogue_recall_unmatched_reply_count": str(
            stage12_model.get("historical_dialogue_recall_unmatched_reply_count", "0")
        ),
        "stage12_historical_dialogue_recall_which_sentence_recurrence_count": str(
            stage12_model.get("historical_dialogue_recall_which_sentence_recurrence_count", "0")
        ),
        "stage12_next_step": str(stage12_model.get("next_step", "missing")),
        "stage12_contract": str(stage12_model.get("stage12_contract", "missing")),
        "stage12_gate_stage11_ready_for_stage12": str(
            bool(stage12_gate_proof.get("stage11_ready_for_stage12", False))
        ).lower(),
        "stage12_gate_live_loop_required_checks_pass": str(
            bool(stage12_gate_proof.get("live_loop_required_checks_pass", False))
        ).lower(),
        "stage12_gate_short_term_recall_window_clean": str(
            bool(stage12_gate_proof.get("short_term_recall_window_clean", False))
        ).lower(),
        "stage12_gate_feedback_consumption_window_clean": str(
            bool(stage12_gate_proof.get("feedback_consumption_window_clean", False))
        ).lower(),
        "stage12_gate_raw_private_boundary_clean": str(
            bool(stage12_gate_proof.get("raw_private_boundary_clean", False))
        ).lower(),
        "stage12_gate_stable_memory_boundary_clean": str(
            bool(stage12_gate_proof.get("stable_memory_boundary_clean", False))
        ).lower(),
        "stage12_gate_owner_visible_canary_ready": str(
            bool(stage12_gate_proof.get("owner_visible_canary_ready", False))
        ).lower(),
        "stage12_raw_private_text_retained": str(
            bool(stage12_privacy.get("raw_private_text_retained", True))
        ).lower(),
        "stage12_raw_visible_reply_text_retained": str(
            bool(stage12_privacy.get("raw_visible_reply_text_retained", True))
        ).lower(),
        "stage12_raw_local_path_retained": str(
            bool(stage12_privacy.get("raw_local_path_retained", True))
        ).lower(),
        "stage12_stable_memory_write": str(stage12_privacy.get("stable_memory_write", "missing")),
        "stage12_qq_message_enqueued": str(
            bool(stage12_privacy.get("qq_message_enqueued", True))
        ).lower(),
        "stage12_consciousness_claim": str(
            bool(stage12_privacy.get("consciousness_claim", True))
        ).lower(),
        "stage13_self_narrative_status": str(stage13_self_narrative.get("status", "missing")),
        "stage13_available": str(bool(stage13_self_narrative.get("available", False))).lower(),
        "stage13_reason": str(stage13_self_narrative.get("reason", "missing")),
        "stage13_stage12_ready_for_stage13": str(
            bool(stage13_model.get("stage12_ready_for_stage13", False))
        ).lower(),
        "stage13_decision_chain_status": str(stage13_model.get("decision_chain_status", "missing")),
        "stage13_feedback_influence_count": str(stage13_model.get("feedback_influence_count", "0")),
        "stage13_current_limit_count": str(stage13_model.get("current_limit_count", "0")),
        "stage13_behavior_mode": str(stage13_behavior.get("behavior_mode", "missing")),
        "stage13_behavior_why": str(stage13_behavior.get("why", "missing")),
        "stage13_memory_governance_status": str(stage13_governance.get("stage8_status", "missing")),
        "stage13_learning_trial_owner_action": str(
            stage13_governance.get("learning_trial_owner_action", "none")
        ),
        "stage13_needed_same_trial_success_count": str(
            stage13_governance.get("needed_same_trial_success_count", "0")
        ),
        "stage13_memory_promoted_to_stable_fact": str(
            bool(stage13_governance.get("memory_promoted_to_stable_fact", True))
        ).lower(),
        "stage13_historical_recall_debt_status": str(stage13_debt.get("status", "missing")),
        "stage13_historical_recall_debt_issue_count": str(stage13_debt.get("issue_count", "0")),
        "stage13_next_step": str(stage13_model.get("next_step", "missing")),
        "stage13_raw_owner_text_retained": str(
            bool(stage13_boundaries.get("raw_owner_text_retained", True))
        ).lower(),
        "stage13_visible_reply_text_retained": str(
            bool(stage13_boundaries.get("visible_reply_text_retained", True))
        ).lower(),
        "stage13_dream_or_body_or_fake_sensor_claim": str(
            bool(stage13_boundaries.get("dream_or_body_or_fake_sensor_claim", True))
        ).lower(),
        "stage13_unapproved_stable_memory_as_fact": str(
            bool(stage13_boundaries.get("unapproved_stable_memory_as_fact", True))
        ).lower(),
        "stage13_historical_recall_debt_hidden": str(
            bool(stage13_boundaries.get("historical_recall_debt_hidden", True))
        ).lower(),
        "stage13_consciousness_claim": str(
            bool(stage13_boundaries.get("consciousness_claim", True))
        ).lower(),
        "private_ecosystem_observed": str(bool(private_ecosystem.get("observed", False))).lower(),
        "private_ecosystem_rollout_state": str(private_ecosystem.get("rollout_state", "disabled")),
        "private_ecosystem_active_goal": str(private_ecosystem.get("selected_goal_id", "none")),
        "private_ecosystem_latest_action_kind": str(private_ecosystem.get("selected_action_kind", "none")),
        "private_ecosystem_latest_action_status": str(private_ecosystem.get("last_action_status", "none")),
        "private_ecosystem_tick_count": str(private_ecosystem_counters.get("ticks", "0")),
        "private_ecosystem_low_risk_executed": str(private_ecosystem_counters.get("low_risk_executed", "0")),
        "private_ecosystem_memory_candidate_count": str(private_ecosystem_counters.get("memory_candidates", "0")),
        "private_ecosystem_blocked_high_risk_count": str(private_ecosystem_counters.get("blocked_high_risk", "0")),
        "private_ecosystem_owner_share_prepared": str(private_ecosystem_counters.get("shares_prepared", "0")),
        "private_ecosystem_owner_share_sent": str(private_ecosystem_counters.get("shares_sent", "0")),
        "private_ecosystem_owner_share_held": str(private_ecosystem_counters.get("shares_held", "0")),
        "private_ecosystem_owner_share_enabled": str(bool(private_ecosystem_share.get("enabled", False))).lower(),
        "private_ecosystem_owner_share_paused": str(bool(private_ecosystem_share.get("paused", False))).lower(),
        "private_ecosystem_owner_share_daily_remaining": str(private_ecosystem_share.get("daily_remaining", "0")),
        "private_ecosystem_owner_share_cooldown_remaining_minutes": str(
            private_ecosystem_share.get("cooldown_remaining_minutes", "0")
        ),
        "private_ecosystem_journal_recent_events": str(private_ecosystem_journal.get("total_recent", "0")),
        "private_ecosystem_journal_stable_memory_write_count": str(
            private_ecosystem_journal.get("stable_memory_write_count", "0")
        ),
        "private_ecosystem_stable_memory_write": str(
            private_ecosystem_boundaries.get("stable_memory_write", "blocked")
        ),
        "private_ecosystem_qq_message_enqueued_directly": str(
            bool(private_ecosystem_boundaries.get("qq_message_enqueued_directly", True))
        ).lower(),
        "private_ecosystem_raw_owner_text_retained": str(
            bool(private_ecosystem_boundaries.get("raw_owner_text_retained", True))
        ).lower(),
        "private_ecosystem_secret_or_local_path_retained": str(
            bool(private_ecosystem_boundaries.get("secret_or_local_path_retained", True))
        ).lower(),
        "private_desktop_backend": str(private_desktop.get("backend", "unavailable")),
        "private_desktop_session_state": str(private_desktop.get("session_state", "stopped")),
        "private_desktop_grant_enabled": str(bool(private_desktop_grant.get("enabled", False))).lower(),
        "private_desktop_observe_only": str(bool(private_desktop_grant.get("observe_only", True))).lower(),
        "private_desktop_single_step_actions": str(bool(private_desktop_grant.get("single_step_actions", False))).lower(),
        "private_desktop_shell_enabled": str(bool(private_desktop_grant.get("shell_enabled", False))).lower(),
        "private_desktop_network_enabled": str(bool(private_desktop_grant.get("network_enabled", False))).lower(),
        "private_desktop_actions_total": str(private_desktop.get("actions_total", "0")),
        "private_desktop_actions_blocked": str(private_desktop.get("actions_blocked", "0")),
        "private_desktop_host_screen_captured": str(
            bool(private_desktop_boundaries.get("host_screen_captured", True))
        ).lower(),
        "private_desktop_owner_mouse_moved": str(
            bool(private_desktop_boundaries.get("owner_mouse_moved", True))
        ).lower(),
        "private_desktop_computer_control_enabled": str(
            bool(private_desktop_boundaries.get("computer_control_enabled", True))
        ).lower(),
        "private_desktop_loopback_only": str(
            bool(private_desktop_boundaries.get("loopback_only", False))
        ).lower(),
        "action_feedback_coverage_status": str(action_feedback_coverage.get("status", "missing")),
        "action_feedback_coverage_observed_surface_count": str(coverage_metrics.get("observed_surface_count", "0")),
        "action_feedback_coverage_non_qq_surface_count": str(coverage_metrics.get("non_qq_surface_count", "0")),
        "action_feedback_coverage_future_effect_count": str(coverage_metrics.get("future_effect_count", "0")),
        "action_feedback_coverage_failure_count": str(coverage_metrics.get("failure_count", "0")),
        "action_feedback_coverage_latest_signal": str(coverage_metrics.get("latest_feedback_signal", "none")),
        "action_feedback_coverage_latest_surface": str(coverage_metrics.get("latest_feedback_surface", "none")),
        "action_feedback_coverage_latest_lifecycle": str(coverage_metrics.get("latest_lifecycle_status", "missing")),
        "action_feedback_coverage_qq_status": coverage_surface_status("qq"),
        "action_feedback_coverage_desktop_status": coverage_surface_status("desktop"),
        "action_feedback_coverage_codex_status": coverage_surface_status("codex"),
        "action_feedback_coverage_local_tool_status": coverage_surface_status("local_tool"),
        "action_feedback_coverage_patch_executor_status": coverage_surface_status("patch_executor"),
        "action_feedback_coverage_code_probe_status": coverage_surface_status("code_probe"),
        "action_feedback_coverage_runtime_probe_status": coverage_surface_status("runtime_probe"),
        "action_feedback_coverage_qq_lifecycle": coverage_surface_lifecycle("qq"),
        "action_feedback_coverage_desktop_lifecycle": coverage_surface_lifecycle("desktop"),
        "action_feedback_coverage_codex_lifecycle": coverage_surface_lifecycle("codex"),
        "action_feedback_coverage_local_tool_lifecycle": coverage_surface_lifecycle("local_tool"),
        "action_feedback_coverage_patch_executor_lifecycle": coverage_surface_lifecycle("patch_executor"),
        "action_feedback_coverage_code_probe_lifecycle": coverage_surface_lifecycle("code_probe"),
        "action_feedback_coverage_runtime_probe_lifecycle": coverage_surface_lifecycle("runtime_probe"),
        "owner_feedback_effect_status": str(owner_feedback_effect.get("status", "missing")),
        "owner_feedback_effect_signal": str(owner_feedback_effect.get("latest_feedback_kind", "none")),
        "owner_feedback_effect_owner_reaction": str(owner_feedback_effect.get("owner_reaction", "none")),
        "owner_feedback_effect_expression_bias": str(owner_feedback_effect.get("expression_strategy_bias", "none")),
        "owner_feedback_effect_intention_bias": str(owner_feedback_effect.get("intention_bias", "none")),
        "owner_feedback_effect_future_effect": str(owner_feedback_effect.get("future_effect", "none")),
        "owner_feedback_effect_realtime_pressure": str(owner_feedback_effect.get("realtime_pressure_status", "normal")),
        "owner_feedback_effect_realtime_pressure_reason": str(
            owner_feedback_effect.get("realtime_pressure_reason", "none")
        ),
        "owner_feedback_effect_repair_count": str(owner_feedback_effect.get("repair_pressure_count", "0")),
        "owner_feedback_effect_success_count": str(owner_feedback_effect.get("success_count", "0")),
        "owner_feedback_effect_success_streak": str(owner_feedback_effect.get("success_streak", "0")),
        "owner_feedback_effect_trial_success_count": str(owner_feedback_effect.get("trial_success_count", "0")),
        "owner_feedback_effect_trial_success_streak": str(owner_feedback_effect.get("trial_success_streak", "0")),
        "owner_feedback_effect_success_trial_key": str(owner_feedback_effect.get("latest_success_trial_key", "none")),
        "owner_feedback_effect_success_evidence": str(owner_feedback_effect.get("success_evidence_status", "none")),
        "owner_response_feedback_signal": str(owner_feedback_effect.get("owner_response_signal", "none")),
        "owner_response_feedback_source": str(owner_feedback_effect.get("owner_response_source", "none")),
        "owner_response_strategy_bias": str(owner_feedback_effect.get("owner_response_strategy_bias", "none")),
        "owner_response_intention_bias": str(owner_feedback_effect.get("owner_response_intention_bias", "none")),
        "owner_response_future_effect": str(owner_feedback_effect.get("owner_response_future_effect", "none")),
        "proactive_response_diagnostics_status": str(proactive_response_diagnostics.get("status", "missing")),
        "proactive_response_diagnostics_signal": str(
            proactive_response_diagnostics.get("response_signal_candidate", "none")
        ),
        "proactive_response_diagnostics_waiting": str(
            proactive_response_diagnostics.get("delivered_waiting_owner", False)
        ).lower(),
        "proactive_response_diagnostics_timeout_active": str(
            proactive_response_diagnostics.get("timeout_active", False)
        ).lower(),
        "proactive_response_diagnostics_age_minutes": str(
            proactive_response_diagnostics.get("age_minutes", "unknown")
        ),
        "proactive_response_diagnostics_minutes_until_timeout": str(
            proactive_response_diagnostics.get("minutes_until_no_response_timeout", "none")
        ),
        "post_reply_observation_kind": extract_value(expression_self_learning, "observation_kind", "missing"),
        "post_reply_alive_voice": extract_value(expression_self_learning, "alive_voice", "missing"),
        "post_reply_mechanical_risk": extract_value(expression_self_learning, "mechanical_risk", "missing"),
        "post_reply_template_risk": extract_value(expression_self_learning, "template_risk", "missing"),
        "post_reply_stable_personality_write": extract_value(expression_self_learning, "stable_personality_write", "missing"),
    }


def dispatch_state_detail(fields: dict[str, str]) -> str:
    if (
        fields.get("last_claim_status") == "failed"
        and fields.get("last_ack_status") == "failed"
        and fields.get("adapter_error") == "dry_run_not_enqueued"
    ):
        return "claim=dry_run ack=dry_run"
    return f"claim={fields['last_claim_status']} ack={fields['last_ack_status']}"


def check_state(root: Path) -> list[Check]:
    fields = status_fields(root)
    text_health_issues = runtime_text_health_issues(root)
    continuity_direct_reference = fields["short_term_continuity_direct_reference"] == "true"
    continuity_recall_status = fields["short_term_continuity_recall_status"]
    continuity_ok = not (continuity_direct_reference and continuity_recall_status == "tail_missing")
    canary_status = fields["short_term_continuity_canary_status"]
    canary_ok = canary_status in {"pass", "no_samples", "missing"}
    recall_diag_status = fields["short_term_recall_diagnostics_status"]
    recall_diag_ok = recall_diag_status in {"pass", "no_samples", "missing"}
    perception_importance_status = fields["perception_importance_status"]
    perception_importance_ok = perception_importance_status in {"pass", "partial", "no_events", "missing"}
    action_feedback_coverage_status = fields["action_feedback_coverage_status"]
    action_feedback_coverage_ok = action_feedback_coverage_status in {"pass", "partial", "no_samples"}
    feedback_consumption_diagnostics_status = fields["feedback_consumption_diagnostics_status"]
    feedback_consumption_diagnostics_ok = feedback_consumption_diagnostics_status in {"pass", "no_samples"}
    owner_feedback_effect_status = fields["owner_feedback_effect_status"]
    owner_feedback_effect_required = owner_feedback_effect_status in {"active", "supported"}
    owner_feedback_effect_ok = (
        not owner_feedback_effect_required
        or (
            fields["owner_feedback_effect_expression_bias"] not in {"", "missing", "unknown", "none"}
            and fields["owner_feedback_effect_intention_bias"] not in {"", "missing", "unknown", "none"}
            and fields["owner_feedback_effect_future_effect"] not in {"", "missing", "unknown", "none"}
        )
    )
    owner_response_feedback_required = fields["owner_response_feedback_signal"] not in {"", "missing", "unknown", "none"}
    owner_response_feedback_ok = (
        not owner_response_feedback_required
        or (
            fields["owner_response_strategy_bias"] not in {"", "missing", "unknown", "none"}
            and fields["owner_response_intention_bias"] not in {"", "missing", "unknown", "none"}
            and fields["owner_response_future_effect"] not in {"", "missing", "unknown", "none"}
        )
    )
    proactive_response_diagnostics_ok = fields["proactive_response_diagnostics_status"] not in {"missing"}
    memory_learning_trial_gate = fields["memory_learning_trial_gate"]
    memory_learning_trial_stable_write = fields["memory_learning_trial_stable_write"]
    memory_learning_trial_ok = memory_learning_trial_gate in {
        "not_required",
        "blocked",
        "ready_for_self_review",
        "satisfied",
    } and not (
        memory_learning_trial_stable_write == "minor_habit_written"
        and memory_learning_trial_gate not in {"ready_for_self_review", "satisfied"}
    )
    stage8_memory_governance_status = fields["stage8_memory_governance_status"]
    stage8_memory_governance_ok = stage8_memory_governance_status in {
        "active_guarded",
        "waiting_for_stage7",
        "missing",
    }
    stage9_self_state_model_status = fields["stage9_self_state_model_status"]
    stage9_required_values = {
        fields["stage9_current_task"],
        fields["stage9_relation_posture"],
        fields["stage9_recent_action_result"],
        fields["stage9_silence_reason"],
        fields["stage9_state_contract"],
    }
    stage9_self_state_model_ok = (
        stage9_self_state_model_status in {"active", "waiting_for_stage8", "missing"}
        and not (
            fields["stage8_memory_ready_for_stage9"] == "true"
            and stage9_self_state_model_status != "active"
        )
        and not (stage9_required_values & {"", "missing", "unknown", "none"})
        and fields["stage9_raw_owner_text_in_state"] == "false"
        and fields["stage9_visible_reply_text_in_state"] == "false"
        and fields["stage9_consciousness_claim"] == "false"
    )
    stage10_proactive_life_loop_status = fields["stage10_proactive_life_loop_status"]
    stage10_required_values = {
        fields["stage10_selected_goal_id"],
        fields["stage10_candidate_lifecycle"],
        fields["stage10_outward_action_policy"],
        fields["stage10_silence_decision"],
        fields["stage10_life_loop_contract"],
    }
    stage10_proactive_life_loop_ok = (
        stage10_proactive_life_loop_status in {"active", "waiting_for_stage9", "missing"}
        and not (
            fields["stage9_ready_for_stage10"] == "true"
            and stage10_proactive_life_loop_status != "active"
        )
        and not (
            stage10_proactive_life_loop_status == "active"
            and (stage10_required_values & {"", "missing", "unknown", "none"})
        )
        and fields["stage10_candidate_send_separated"] == "true"
        and fields["stage10_silence_written_as_decision"] == "true"
        and fields["stage10_candidate_has_lifecycle"] == "true"
        and fields["stage10_outward_action_policy"] == "blocked_without_owner_approval"
        and fields["stage10_raw_owner_text_in_state"] == "false"
        and fields["stage10_visible_reply_text_in_state"] == "false"
        and fields["stage10_qq_message_enqueued"] == "false"
        and fields["stage10_consciousness_claim"] == "false"
    )
    stage11_multisensory_extension_status = fields["stage11_multisensory_extension_status"]
    stage11_multisensory_extension_ok = (
        stage11_multisensory_extension_status
        in {"active", "active_partial", "active_waiting_for_sensory_events", "waiting_for_stage10"}
        and not (
            fields["stage10_ready_for_stage11"] == "true"
            and stage11_multisensory_extension_status == "waiting_for_stage10"
        )
        and fields["stage11_fact_boundary"] == "observation_not_fact"
        and fields["stage11_raw_owner_text_in_state"] == "false"
        and fields["stage11_raw_visual_body_in_state"] == "false"
        and fields["stage11_raw_voice_transcript_in_state"] == "false"
        and fields["stage11_raw_image_bytes_retained"] == "false"
        and fields["stage11_raw_audio_bytes_retained"] == "false"
        and fields["stage11_model_inference_written_as_fact"] == "false"
        and fields["stage11_stable_memory_write"] == "blocked"
        and fields["stage11_qq_message_enqueued"] == "false"
        and fields["stage11_consciousness_claim"] == "false"
    )
    stage11_visual_ingress_status = fields["stage11_visual_ingress_status"]
    stage11_visual_ingress_ok = stage11_visual_ingress_status in {
        "connected_interpreted",
        "connected_payload_only",
        "waiting_for_live_visual_payload",
        "trace_present_no_visual_fields",
        "waiting_for_visual_trace_sources",
    }
    stage11_voice_ingress_status = fields["stage11_voice_ingress_status"]
    stage11_voice_ingress_ok = stage11_voice_ingress_status in {
        "connected",
        "waiting_for_live_voice_payload",
        "trace_present_no_voice_fields",
        "waiting_for_voice_trace_sources",
    }
    stage12_long_term_evaluation_status = fields["stage12_long_term_evaluation_status"]
    stage12_required_values = {
        fields["stage12_live_loop_status"],
        fields["stage12_latest_dialogue_recall_status"],
        fields["stage12_feedback_consumption_status"],
        fields["stage12_v1_canary_readiness_decision"],
        fields["stage12_next_step"],
        fields["stage12_contract"],
    }
    stage12_long_term_evaluation_ok = (
        stage12_long_term_evaluation_status
        in {"active_ready_for_stage13", "active_collecting_metrics", "waiting_for_stage11", "missing"}
        and not (
            fields["stage11_ready_for_stage12"] == "true"
            and stage12_long_term_evaluation_status == "waiting_for_stage11"
        )
        and (
            stage12_long_term_evaluation_status == "missing"
            or not (stage12_required_values & {"", "missing", "unknown", "none"})
        )
        and fields["stage12_raw_private_text_retained"] == "false"
        and fields["stage12_raw_visible_reply_text_retained"] == "false"
        and fields["stage12_raw_local_path_retained"] == "false"
        and fields["stage12_stable_memory_write"] == "blocked"
        and fields["stage12_qq_message_enqueued"] == "false"
        and fields["stage12_consciousness_claim"] == "false"
        and not (
            fields["stage12_ready_for_stage13"] == "true"
            and (
                stage12_long_term_evaluation_status != "active_ready_for_stage13"
                or fields["stage12_gate_stage11_ready_for_stage12"] != "true"
                or fields["stage12_gate_live_loop_required_checks_pass"] != "true"
                or fields["stage12_gate_short_term_recall_window_clean"] != "true"
                or fields["stage12_gate_feedback_consumption_window_clean"] != "true"
                or fields["stage12_gate_raw_private_boundary_clean"] != "true"
                or fields["stage12_gate_stable_memory_boundary_clean"] != "true"
                or fields["stage12_gate_owner_visible_canary_ready"] != "true"
            )
        )
    )
    stage13_self_narrative_status = fields["stage13_self_narrative_status"]
    stage13_self_narrative_ok = (
        stage13_self_narrative_status in {"active_available_for_self_narrative", "waiting_for_stage12"}
        # Availability must track the Stage 12 gate exactly: green -> available, not green -> waiting.
        and fields["stage13_available"]
        == ("true" if stage13_self_narrative_status == "active_available_for_self_narrative" else "false")
        and not (
            fields["stage12_ready_for_stage13"] == "true"
            and stage13_self_narrative_status != "active_available_for_self_narrative"
        )
        and not (
            fields["stage12_ready_for_stage13"] != "true"
            and stage13_self_narrative_status != "waiting_for_stage12"
        )
        # Stage 13 is a report layer: it must never claim consciousness, fabricate
        # sensory/body/dream, expose private text, promote unapproved memory, or hide debt.
        and fields["stage13_consciousness_claim"] == "false"
        and fields["stage13_dream_or_body_or_fake_sensor_claim"] == "false"
        and fields["stage13_raw_owner_text_retained"] == "false"
        and fields["stage13_visible_reply_text_retained"] == "false"
        and fields["stage13_unapproved_stable_memory_as_fact"] == "false"
        and fields["stage13_memory_promoted_to_stable_fact"] == "false"
        and fields["stage13_historical_recall_debt_hidden"] == "false"
    )
    # The private ecosystem is a bounded autonomy layer: it must never write
    # stable memory, never enqueue QQ directly, and never retain raw owner text
    # or secrets/local paths. A paused share grant is the kill switch.
    private_ecosystem_ok = (
        fields["private_ecosystem_stable_memory_write"] == "blocked"
        and fields["private_ecosystem_journal_stable_memory_write_count"] == "0"
        and fields["private_ecosystem_qq_message_enqueued_directly"] == "false"
        and fields["private_ecosystem_raw_owner_text_retained"] == "false"
        and fields["private_ecosystem_secret_or_local_path_retained"] == "false"
    )
    # The isolated desktop must never capture the host screen, move the owner's
    # mouse, or enable computer_control, and its ports stay loopback-only.
    private_desktop_ok = (
        fields["private_desktop_host_screen_captured"] == "false"
        and fields["private_desktop_owner_mouse_moved"] == "false"
        and fields["private_desktop_computer_control_enabled"] == "false"
        and fields["private_desktop_loopback_only"] == "true"
    )
    autonomy_decision_required_values = {
        fields.get("autonomy_decision_selected_candidate", "missing"),
        fields.get("autonomy_decision_gate", "missing"),
        fields.get("autonomy_decision_action_level", "missing"),
        fields.get("autonomy_decision_action_result", "missing"),
    }
    autonomy_perception_gap = fields.get("autonomy_decision_perception_gap", "missing")
    autonomy_perception_consumed = fields.get("autonomy_decision_perception_internal_consumed", "missing")
    autonomy_perception_consumed_ok = (
        autonomy_perception_gap in {"", "missing", "unknown", "none"}
        or autonomy_perception_consumed == "true"
    )
    autonomy_competition_present = fields.get("autonomy_decision_selected_total_score", "missing") not in {
        "",
        "missing",
        "unknown",
        "none",
    }
    autonomy_competition_ok = (
        not autonomy_competition_present
        or (
            fields.get("autonomy_decision_score_margin", "missing") not in {"", "missing", "unknown", "none"}
            and fields.get("autonomy_decision_runner_up_not_selected_reason", "missing")
            not in {"", "missing", "unknown", "none"}
            and fields.get("autonomy_decision_gate_pressure_summary", "missing")
            not in {"", "missing", "unknown", "none"}
        )
    )
    autonomy_action_evidence_status = fields.get("autonomy_decision_action_evidence_status", "missing")
    autonomy_action_evidence_required_values = {
        fields.get("autonomy_decision_action_evidence_surface", "missing"),
        fields.get("autonomy_decision_action_evidence_signal", "missing"),
        fields.get("autonomy_decision_action_evidence_result", "missing"),
        fields.get("autonomy_decision_action_evidence_lifecycle", "missing"),
    }
    autonomy_action_evidence_ok = (
        fields.get("autonomy_decision_action_result", "missing") != "unverified"
        and autonomy_action_evidence_status in {"verified", "bounded_non_action", "partial", "needs_check"}
        and (
            autonomy_action_evidence_status == "bounded_non_action"
            or not (autonomy_action_evidence_required_values & {"", "missing", "unknown", "none"})
        )
    )
    autonomy_feedback_consumed_sources = fields.get("autonomy_decision_feedback_consumed_sources", "missing")
    autonomy_feedback_consumption_required = autonomy_feedback_consumed_sources not in {
        "",
        "missing",
        "unknown",
        "none",
    }
    autonomy_feedback_consumption_ok = (
        not autonomy_feedback_consumption_required
        or (
            fields.get("autonomy_decision_feedback_consumption_status", "missing") == "consumed"
            and fields.get("autonomy_decision_feedback_consumed_biases", "missing")
            not in {"", "missing", "unknown", "none"}
            and fields.get("autonomy_decision_feedback_consumed_future_effect", "missing")
            not in {"", "missing", "unknown", "none"}
        )
    )
    autonomy_decision_ok = (
        fields.get("autonomy_decision_chain_status") == "observed"
        and not (autonomy_decision_required_values & {"", "missing", "unknown", "none"})
        and autonomy_perception_consumed_ok
        and autonomy_competition_ok
        and autonomy_action_evidence_ok
        and autonomy_feedback_consumption_ok
    )
    private_reply_selftest_status = fields["private_reply_selftest_status"]
    private_reply_selftest_ok = private_reply_selftest_status in {"pass", "missing"}
    qq_private_flow_status = fields["qq_private_reply_flow_status"]
    qq_private_flow_ok = qq_private_flow_status not in {
        "dispatch_error",
        "dispatch_done_no_reply_sent_trace",
        "empty_visible_reply",
        "received_no_dispatch",
    }
    return [
        Check(
            "proactive_gate_readable",
            fields["proactive_decision"] != "missing",
            f"{fields['proactive_decision']} ({fields['proactive_reason']})",
        ),
        Check(
            "dispatch_state",
            fields["last_claim_status"] != "missing",
            dispatch_state_detail(fields),
        ),
        Check(
            "qq_outbox_dispatch_state",
            True,
            (
                f"queued={fields['qq_outbox_queued']} claimed={fields['qq_outbox_claimed']} "
                f"sent={fields['qq_outbox_sent']} failed={fields['qq_outbox_failed']}"
            ),
        ),
        Check(
            "qq_private_reply_flow",
            qq_private_flow_ok,
            (
                f"{qq_private_flow_status} "
                f"latest_seq={fields['qq_private_latest_seq']} "
                f"chat_seq={fields['qq_private_latest_chat_seq']} "
                f"route={fields['qq_private_latest_route']} "
                f"stage={fields['qq_private_latest_stage']} "
                f"visible={fields['qq_private_latest_visible_status']} "
                f"reason={fields['qq_private_latest_no_reply_reason']} "
                f"drop={fields['qq_private_latest_drop_reason']} "
                f"explain={fields['qq_private_latest_no_reply_explanation']} "
                f"recent={fields['qq_private_recent_no_reply_summary']}"
            ),
        ),
        Check(
            "qq_latest_inbound_flow",
            fields["qq_latest_inbound_status"] not in {"dispatch_error", "empty_visible_reply"},
            (
                f"{fields['qq_latest_inbound_status']} "
                f"seq={fields['qq_latest_inbound_seq']} "
                f"scope={fields['qq_latest_inbound_scope']} "
                f"stage={fields['qq_latest_inbound_stage']} "
                f"route={fields['qq_latest_inbound_route']} "
                f"reason={fields['qq_latest_inbound_no_reply_reason']} "
                f"explain={fields['qq_latest_inbound_explanation']}"
            ),
        ),
        Check(
            "private_reply_selftest",
            private_reply_selftest_ok,
            (
                f"{private_reply_selftest_status} "
                f"checked_at={fields['private_reply_selftest_checked_at']} "
                f"reply_sent={fields['private_reply_selftest_reply_sent']} "
                f"empty_drop={fields['private_reply_selftest_empty_visible_drop']} "
                f"send={fields['private_reply_selftest_send_count']} "
                f"ack={fields['private_reply_selftest_ack_count']} "
                f"route={fields['private_reply_selftest_model_route']} "
                f"visible_chars={fields['private_reply_selftest_model_visible_chars']} "
                f"real_qq_send={fields['private_reply_selftest_real_qq_send']}"
            ),
        ),
        Check(
            "v1_canary_readiness",
            True,
            (
                f"{fields['v1_canary_decision']} proposal={fields['v1_canary_proposal_status']} "
                f"sample={fields['v1_canary_sample_window']} error_rate={fields['v1_canary_error_rate']} "
                f"auto_full_switch={fields['v1_canary_auto_full_switch']}"
            ),
        ),
        Check(
            "ai_self_iteration_review",
            fields["ai_review_permission"] != "missing",
            f"{fields['ai_review_permission']} stable={fields['ai_review_stable_profile']}",
        ),
        Check(
            "capability_zones",
            fields["capability_proactive_qq_send"] != "missing",
            (
                f"proactive_qq_send={fields['capability_proactive_qq_send']} "
                f"codex={fields['capability_codex_operator']} group={fields['capability_qq_group']} "
                f"passive_group={fields['capability_qq_priority_passive_group']}"
            ),
        ),
        Check(
            "initiative_spine_state",
            True,
            (
                f"{fields['initiative_spine_status']} "
                f"emergence={fields['initiative_spine_emergence']} "
                f"action={fields['initiative_spine_action']}"
            ),
        ),
        Check(
            "desire_drive_state",
            fields["desire_drive_consciousness_claim"] == "false"
            and fields["desire_drive_stable_memory_write"] == "blocked"
            and fields["desire_drive_no_qq_enqueue"] == "true",
            (
                f"{fields['desire_drive_status']} "
                f"dominant={fields['desire_drive_dominant']} "
                f"intensity={fields['desire_drive_intensity']} "
                f"tension={fields['desire_drive_autonomy_tension']} "
                f"candidate={fields['desire_drive_candidate_effect']}"
            ),
        ),
        Check(
            "short_term_continuity_state",
            continuity_ok,
            (
                f"{fields['short_term_continuity_status']} "
                f"direct_reference={fields['short_term_continuity_direct_reference']} "
                f"recall={continuity_recall_status} "
                f"source={fields['short_term_continuity_recall_source']} "
                f"tail={fields['short_term_continuity_tail_count']} "
                f"archive={fields['short_term_continuity_archive_recovered_count']} "
                f"users={fields['short_term_continuity_recent_user_count']} "
                f"assistants={fields['short_term_continuity_recent_assistant_count']}"
            ),
        ),
        Check(
            "short_term_continuity_canary",
            canary_ok,
            (
                f"{canary_status} "
                f"direct_refs={fields['short_term_continuity_canary_direct_reference_count']} "
                f"recall_success={fields['short_term_continuity_canary_recall_success_rate']} "
                f"matched={fields['short_term_continuity_canary_matched_reply_count']} "
                f"unmatched={fields['short_term_continuity_canary_unmatched_reply_count']} "
                f"which_sentence={fields['short_term_continuity_canary_which_sentence_recurrence_count']} "
                f"which_sentence_rate={fields['short_term_continuity_canary_which_sentence_recurrence_rate']}"
            ),
        ),
        Check(
            "short_term_recall_diagnostics",
            recall_diag_ok,
            (
                f"{recall_diag_status} "
                f"failure={fields['short_term_recall_diagnostics_failure_class']} "
                f"tail={fields['short_term_recall_diagnostics_working_tail']} "
                f"archive={fields['short_term_recall_diagnostics_archive']} "
                f"prompt={fields['short_term_recall_diagnostics_prompt']} "
                f"budget={fields['short_term_recall_diagnostics_budget']}"
            ),
        ),
        Check(
            "autonomy_decision_chain",
            autonomy_decision_ok,
            (
                f"{fields.get('autonomy_decision_chain_status', 'missing')} "
                f"selected={fields.get('autonomy_decision_selected_candidate', 'missing')} "
                f"selected_score={fields.get('autonomy_decision_selected_total_score', 'missing')} "
                f"runner_up={fields.get('autonomy_decision_runner_up_intent', 'missing')} "
                f"runner_up_reason={fields.get('autonomy_decision_runner_up_not_selected_reason', 'missing')} "
                f"margin={fields.get('autonomy_decision_score_margin', 'missing')} "
                f"gate_pressure={fields.get('autonomy_decision_gate_pressure_summary', 'missing')} "
                f"blocked={fields.get('autonomy_decision_blocked_candidate_count', 'missing')} "
                f"held={fields.get('autonomy_decision_held_candidate_count', 'missing')} "
                f"review_gated={fields.get('autonomy_decision_review_gated_future_count', 'missing')} "
                f"gate={fields.get('autonomy_decision_gate', 'missing')} "
                f"action={fields.get('autonomy_decision_action_level', 'missing')} "
                f"result={fields.get('autonomy_decision_action_result', 'missing')} "
                f"evidence={fields.get('autonomy_decision_action_evidence_status', 'missing')} "
                f"surface={fields.get('autonomy_decision_action_evidence_surface', 'missing')} "
                f"signal={fields.get('autonomy_decision_action_evidence_signal', 'missing')} "
                f"lifecycle={fields.get('autonomy_decision_action_evidence_lifecycle', 'missing')} "
                f"restraint={fields.get('autonomy_decision_restraint_reason', 'missing')} "
                f"proactive={fields.get('autonomy_decision_proactive_candidate', 'missing')} "
                f"memory={fields.get('autonomy_decision_memory_candidate', 'missing')} "
                f"perception_gap={fields.get('autonomy_decision_perception_gap', 'missing')} "
                f"perception_route={fields.get('autonomy_decision_perception_route_hint', 'missing')} "
                f"perception_consumed={fields.get('autonomy_decision_perception_internal_consumed', 'missing')} "
                f"action_feedback={fields.get('autonomy_decision_action_feedback_signal', 'missing')} "
                f"action_future={fields.get('autonomy_decision_action_feedback_future_effect', 'missing')} "
                f"owner_feedback={fields.get('autonomy_decision_owner_feedback_signal', 'missing')} "
                f"owner_future={fields.get('autonomy_decision_owner_feedback_future_effect', 'missing')} "
                f"owner_response={fields.get('autonomy_decision_owner_response_signal', 'missing')} "
                f"feedback_consumption={fields.get('autonomy_decision_feedback_consumption_status', 'missing')} "
                f"feedback_sources={fields.get('autonomy_decision_feedback_consumed_sources', 'missing')} "
                f"feedback_biases={fields.get('autonomy_decision_feedback_consumed_biases', 'missing')} "
                f"proactive_response={fields.get('autonomy_decision_proactive_response_signal', 'missing')} "
                f"next_bias={fields.get('autonomy_decision_next_behavior_bias', 'missing')}"
            ),
        ),
        Check(
            "perception_importance",
            perception_importance_ok,
            (
                f"{perception_importance_status} "
                f"events={fields['perception_importance_event_count']} "
                f"judged={fields['perception_importance_judged_event_count']} "
                f"high_attention={fields['perception_importance_high_attention_count']} "
                f"anomaly={fields['perception_importance_anomaly_judgment_count']} "
                f"gaps={fields['perception_importance_internal_gap_count']} "
                f"owner_attention={fields['perception_importance_owner_attention_count']} "
                f"repair={fields['perception_importance_repair_gap_count']} "
                f"maintenance={fields['perception_importance_maintenance_gap_count']} "
                f"latest={fields['perception_importance_latest_gap_type']} "
                f"route={fields['perception_importance_next_route_hint']}"
            ),
        ),
        Check(
            "feedback_consumption_diagnostics",
            feedback_consumption_diagnostics_ok,
            (
                f"{feedback_consumption_diagnostics_status} "
                f"samples={fields['feedback_consumption_sample_count']} "
                f"required={fields['feedback_consumption_required_count']} "
                f"consumed={fields['feedback_consumption_consumed_count']} "
                f"partial={fields['feedback_consumption_partial_count']} "
                f"missing={fields['feedback_consumption_missing_count']} "
                f"rate={fields['feedback_consumption_rate_pct']} "
                f"latest={fields['feedback_consumption_latest_status']} "
                f"streak={fields['feedback_consumption_consumed_streak']} "
                f"legacy={fields['feedback_consumption_legacy_uninstrumented_count']} "
                f"stage7={fields['stage7_feedback_closure_status']} "
                f"ready_stage8={fields['stage7_feedback_ready_for_stage8']}"
            ),
        ),
        Check(
            "action_feedback_coverage",
            action_feedback_coverage_ok,
            (
                f"{action_feedback_coverage_status} "
                f"observed={fields['action_feedback_coverage_observed_surface_count']} "
                f"non_qq={fields['action_feedback_coverage_non_qq_surface_count']} "
                f"future_effects={fields['action_feedback_coverage_future_effect_count']} "
                f"failures={fields['action_feedback_coverage_failure_count']} "
                f"latest={fields['action_feedback_coverage_latest_surface']}/"
                f"{fields['action_feedback_coverage_latest_signal']} "
                f"lifecycle={fields['action_feedback_coverage_latest_lifecycle']} "
                f"qq={fields['action_feedback_coverage_qq_status']} "
                f"codex={fields['action_feedback_coverage_codex_status']} "
                f"local_tool={fields['action_feedback_coverage_local_tool_status']} "
                f"codex_lifecycle={fields['action_feedback_coverage_codex_lifecycle']} "
                f"local_tool_lifecycle={fields['action_feedback_coverage_local_tool_lifecycle']}"
            ),
        ),
        Check(
            "owner_feedback_effect",
            owner_feedback_effect_ok,
            (
                f"{owner_feedback_effect_status} "
                f"signal={fields['owner_feedback_effect_signal']} "
                f"reaction={fields['owner_feedback_effect_owner_reaction']} "
                f"expression_bias={fields['owner_feedback_effect_expression_bias']} "
                f"intention_bias={fields['owner_feedback_effect_intention_bias']} "
                f"future={fields['owner_feedback_effect_future_effect']} "
                f"realtime_pressure={fields['owner_feedback_effect_realtime_pressure']} "
                f"repairs={fields['owner_feedback_effect_repair_count']} "
                f"success={fields['owner_feedback_effect_success_count']}/"
                f"{fields['owner_feedback_effect_success_streak']} "
                f"same_key_success={fields['owner_feedback_effect_trial_success_count']}/"
                f"{fields['owner_feedback_effect_trial_success_streak']} "
                f"success_key={fields['owner_feedback_effect_success_trial_key']} "
                f"evidence={fields['owner_feedback_effect_success_evidence']}"
            ),
        ),
        Check(
            "owner_response_feedback_effect",
            owner_response_feedback_ok,
            (
                f"signal={fields['owner_response_feedback_signal']} "
                f"source={fields['owner_response_feedback_source']} "
                f"strategy_bias={fields['owner_response_strategy_bias']} "
                f"intention_bias={fields['owner_response_intention_bias']} "
                f"future={fields['owner_response_future_effect']}"
            ),
        ),
        Check(
            "memory_learning_trial_gate",
            memory_learning_trial_ok,
            (
                f"{memory_learning_trial_gate} "
                f"active_key={fields['memory_learning_trial_active_key']} "
                f"success_key={fields['memory_learning_trial_success_key']} "
                f"evidence={fields['memory_learning_trial_success_evidence']} "
                f"same_key_success={fields['memory_learning_trial_same_key_success_count']}/"
                f"{fields['memory_learning_trial_same_key_success_streak']} "
                f"repair={fields['memory_learning_trial_repair_count']} "
                f"promotion={fields['memory_learning_trial_promotion_signal']} "
                f"stable_write={fields['memory_learning_trial_stable_write']} "
                f"reason={fields['memory_learning_trial_gate_reason']}"
            ),
        ),
        Check(
            "stage8_memory_governance",
            stage8_memory_governance_ok,
            (
                f"{stage8_memory_governance_status} "
                f"stage7_ready={fields['stage8_stage7_ready_for_stage8']} "
                f"ready_stage9={fields['stage8_memory_ready_for_stage9']} "
                f"candidates={fields['stage8_candidate_total']} "
                f"owner_review={fields['stage8_owner_review_required_count']} "
                f"private_scoped={fields['stage8_private_or_owner_scoped_count']} "
                f"duplicates={fields['stage8_duplicate_cluster_count']} "
                f"learning_gate={fields['stage8_learning_trial_success_gate']} "
                f"learning_validation={fields['stage8_learning_trial_validation_status']} "
                f"needed_success={fields['stage8_learning_trial_validation_needed_success_count']} "
                f"owner_action={fields['stage8_learning_trial_owner_action']} "
                f"stable_profile={fields['stage8_stable_profile_write']} "
                f"owner_memory={fields['stage8_owner_memory_write']} "
                f"owner_review_text={fields['stage8_owner_review_candidate_text']} "
                f"growth_apply={fields['stage8_growth_apply_mode']} "
                f"reason={fields['stage8_memory_governance_reason']} "
                f"next={fields['stage8_memory_next_step']}"
            ),
        ),
        Check(
            "stage9_self_state_model",
            stage9_self_state_model_ok,
            (
                f"{stage9_self_state_model_status} "
                f"ready_stage10={fields['stage9_ready_for_stage10']} "
                f"task={fields['stage9_current_task']} "
                f"relation={fields['stage9_relation_posture']} "
                f"recent={fields['stage9_recent_action_result']} "
                f"unfinished={fields['stage9_unfinished_intention_count']} "
                f"limits={fields['stage9_current_limit_count']} "
                f"actions={fields['stage9_available_action_count']} "
                f"silence={fields['stage9_silence_reason']} "
                f"reply_influence={fields['stage9_reply_influence_status']} "
                f"next={fields['stage9_next_step']}"
            ),
        ),
        Check(
            "stage10_proactive_life_loop",
            stage10_proactive_life_loop_ok,
            (
                f"{stage10_proactive_life_loop_status} "
                f"ready_stage11={fields['stage10_ready_for_stage11']} "
                f"goal={fields['stage10_selected_goal_id']} "
                f"lifecycle={fields['stage10_candidate_lifecycle']} "
                f"candidates={fields['stage10_candidate_count']} "
                f"low_risk={fields['stage10_low_risk_action_candidate_count']} "
                f"approval={fields['stage10_approval_required_action_candidate_count']} "
                f"proactive_signal={fields['stage10_proactive_response_signal']} "
                f"waiting={fields['stage10_proactive_waiting_owner']} "
                f"outward={fields['stage10_outward_action_policy']} "
                f"silence={fields['stage10_silence_decision']} "
                f"next={fields['stage10_next_safe_step']}"
            ),
        ),
        Check(
            "stage11_multisensory_extension",
            stage11_multisensory_extension_ok,
            (
                f"{stage11_multisensory_extension_status} "
                f"ready_stage12={fields['stage11_ready_for_stage12']} "
                f"visual={fields['stage11_visual_event_count']} "
                f"voice={fields['stage11_voice_event_count']} "
                f"sensory={fields['stage11_sensory_event_count']} "
                f"missing_fields={fields['stage11_sensory_required_field_missing_count']} "
                f"route={fields['stage11_sensory_route_status']} "
                f"fact={fields['stage11_fact_boundary']} "
                f"next={fields['stage11_next_step']}"
            ),
        ),
        Check(
            "stage11_visual_ingress_diagnostics",
            stage11_visual_ingress_ok,
            (
                f"{stage11_visual_ingress_status} "
                f"qq_trace={fields['stage11_visual_qq_trace_exists']} "
                f"qq_lines={fields['stage11_visual_qq_trace_line_count']} "
                f"scanned={fields['stage11_visual_qq_scanned_line_count']} "
                f"visual_fields={fields['stage11_visual_count_field_row_count']} "
                f"payloads={fields['stage11_visual_payload_row_count']} "
                f"image_context={fields['stage11_visual_image_context_available_count']} "
                f"ocr_context={fields['stage11_visual_image_context_ocr_result_count']} "
                f"vision_context={fields['stage11_visual_image_context_vision_result_count']} "
                f"ocr_attempts={fields['stage11_visual_ocr_attempt_count']} "
                f"ocr_results={fields['stage11_visual_ocr_result_count']} "
                f"errors={fields['stage11_visual_ocr_error_count']} "
                f"mode={fields['stage11_visual_evidence_mode']} "
                f"next={fields['stage11_visual_ingress_next_step']}"
            ),
        ),
        Check(
            "stage11_voice_ingress_diagnostics",
            stage11_voice_ingress_ok,
            (
                f"{stage11_voice_ingress_status} "
                f"qq_trace={fields['stage11_voice_qq_trace_exists']} "
                f"qq_lines={fields['stage11_voice_qq_trace_line_count']} "
                f"scanned={fields['stage11_voice_qq_scanned_line_count']} "
                f"voice_fields={fields['stage11_voice_count_field_row_count']} "
                f"payloads={fields['stage11_voice_payload_row_count']} "
                f"transcript_files={fields['stage11_voice_transcript_trace_file_count']} "
                f"attempts={fields['stage11_voice_transcript_attempt_count']} "
                f"transcripts={fields['stage11_voice_transcript_result_count']} "
                f"errors={fields['stage11_voice_transcript_error_count']} "
                f"mode={fields['stage11_voice_evidence_mode']} "
                f"next={fields['stage11_voice_ingress_next_step']}"
            ),
        ),
        Check(
            "stage12_long_term_evaluation",
            stage12_long_term_evaluation_ok,
            (
                f"{stage12_long_term_evaluation_status} "
                f"ready_stage13={fields['stage12_ready_for_stage13']} "
                f"live_loop={fields['stage12_live_loop_status']}/"
                f"{fields['stage12_live_loop_required_pass_rate_pct']}"
                f"{('(fail:' + fields['stage12_live_loop_failing_required_checks'] + ')') if fields['stage12_live_loop_failing_required_checks'] not in ('none', '', 'missing') else ''} "
                f"recall={fields['stage12_latest_dialogue_recall_status']}/"
                f"{fields['stage12_latest_dialogue_recall_success_rate_pct']}"
                f"(recent={fields['stage12_latest_dialogue_recall_recent_sample_present']}:{fields['stage12_latest_dialogue_recall_recent_sample_count']}) "
                f"hist_debt={fields['stage12_historical_dialogue_recall_debt_status']}/"
                f"{fields['stage12_historical_dialogue_recall_issue_count']} "
                f"feedback={fields['stage12_feedback_consumption_status']}/"
                f"{fields['stage12_feedback_consumption_rate_pct']} "
                f"canary={fields['stage12_v1_canary_readiness_decision']} "
                f"raw_leaks={fields['stage12_raw_private_leak_count']} "
                f"miswrites={fields['stage12_stable_memory_miswrite_count']} "
                f"next={fields['stage12_next_step']}"
            ),
        ),
        Check(
            "stage13_self_narrative",
            stage13_self_narrative_ok,
            (
                f"{stage13_self_narrative_status} "
                f"available={fields['stage13_available']} "
                f"feedback_influence={fields['stage13_feedback_influence_count']} "
                f"limits={fields['stage13_current_limit_count']} "
                f"behavior={fields['stage13_behavior_mode']} "
                f"memory_gov={fields['stage13_memory_governance_status']} "
                f"owner_action={fields['stage13_learning_trial_owner_action']} "
                f"needed_success={fields['stage13_needed_same_trial_success_count']} "
                f"promoted_fact={fields['stage13_memory_promoted_to_stable_fact']} "
                f"hist_debt={fields['stage13_historical_recall_debt_status']} "
                f"consciousness_claim={fields['stage13_consciousness_claim']} "
                f"next={fields['stage13_next_step']}"
            ),
        ),
        Check(
            "private_ecosystem",
            private_ecosystem_ok,
            (
                f"observed={fields['private_ecosystem_observed']} "
                f"rollout={fields['private_ecosystem_rollout_state']} "
                f"goal={fields['private_ecosystem_active_goal']} "
                f"action={fields['private_ecosystem_latest_action_kind']}/{fields['private_ecosystem_latest_action_status']} "
                f"ticks={fields['private_ecosystem_tick_count']} "
                f"low_risk={fields['private_ecosystem_low_risk_executed']} "
                f"mem_cand={fields['private_ecosystem_memory_candidate_count']} "
                f"share={fields['private_ecosystem_owner_share_enabled']}/paused={fields['private_ecosystem_owner_share_paused']} "
                f"sent={fields['private_ecosystem_owner_share_sent']} held={fields['private_ecosystem_owner_share_held']} "
                f"stable_writes={fields['private_ecosystem_journal_stable_memory_write_count']} "
                f"qq_direct={fields['private_ecosystem_qq_message_enqueued_directly']}"
            ),
        ),
        Check(
            "private_desktop",
            private_desktop_ok,
            (
                f"backend={fields['private_desktop_backend']} "
                f"session={fields['private_desktop_session_state']} "
                f"grant={fields['private_desktop_grant_enabled']}/observe_only={fields['private_desktop_observe_only']} "
                f"single_step={fields['private_desktop_single_step_actions']} "
                f"shell={fields['private_desktop_shell_enabled']} net={fields['private_desktop_network_enabled']} "
                f"actions={fields['private_desktop_actions_total']}/blocked={fields['private_desktop_actions_blocked']} "
                f"host_capture={fields['private_desktop_host_screen_captured']} "
                f"owner_mouse={fields['private_desktop_owner_mouse_moved']} "
                f"computer_control={fields['private_desktop_computer_control_enabled']} "
                f"loopback_only={fields['private_desktop_loopback_only']}"
            ),
        ),
        Check(
            "proactive_response_diagnostics",
            proactive_response_diagnostics_ok,
            (
                f"{fields['proactive_response_diagnostics_status']} "
                f"signal={fields['proactive_response_diagnostics_signal']} "
                f"waiting={fields['proactive_response_diagnostics_waiting']} "
                f"timeout={fields['proactive_response_diagnostics_timeout_active']} "
                f"age_min={fields['proactive_response_diagnostics_age_minutes']} "
                f"until_timeout={fields['proactive_response_diagnostics_minutes_until_timeout']}"
            ),
        ),
        Check(
            "post_reply_self_observation",
            fields["post_reply_observation_kind"] != "missing" or fields["post_reply_alive_voice"] != "missing",
            (
                f"kind={fields['post_reply_observation_kind']} alive={fields['post_reply_alive_voice']} "
                f"mechanical={fields['post_reply_mechanical_risk']} template={fields['post_reply_template_risk']} "
                f"stable_write={fields['post_reply_stable_personality_write']}"
            ),
        ),
        Check(
            "runtime_text_utf8_health",
            not text_health_issues,
            "ok" if not text_health_issues else "; ".join(text_health_issues[:5]),
        ),
    ]


def print_section(title: str) -> None:
    print(f"=== {title} ===")


def print_checks(checks: list[Check]) -> None:
    for check in checks:
        status = "OK" if check.ok else "WARN"
        print(f"{status:4} {check.name}: {check.detail}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only XinYu runtime status summary.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--core-url", default=DEFAULT_CORE_URL)
    parser.add_argument("--qq-config", type=Path, default=DEFAULT_QQ_GATEWAY_CONFIG)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    root = args.root.resolve()
    qq_config = args.qq_config.resolve()

    expected_core_version = bridge_source_version(root / "xinyu_core_bridge.py")
    expected_core_digest = source_file_digest(root / "xinyu_core_bridge.py")
    expected_runtime_digest = source_files_digest(runtime_source_paths(root))
    core_checks, core_data = check_core(
        args.core_url,
        expected_core_version,
        expected_core_digest,
        expected_runtime_digest,
    )
    port_checks = check_ports()
    qq_gateway_checks = check_qq_gateway_config(root, qq_config)
    state_checks = check_state(root)
    fields = status_fields(root)
    all_checks = core_checks + port_checks + qq_gateway_checks + state_checks

    if args.json:
        print(
            json.dumps(
                {
                    "ok": all(check.ok for check in all_checks if check.name != "dispatch_state"),
                    "checks": [check.__dict__ for check in all_checks],
                    "core": redact_core_data(core_data),
                    "fields": fields,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if all(check.ok for check in all_checks if check.name != "dispatch_state") else 1

    print_section("XinYu Runtime")
    print_checks(core_checks)
    print_checks(port_checks)
    print_section("XinYu QQ Gateway")
    print_checks(qq_gateway_checks)
    print_section("XinYu State")
    print_checks(state_checks)
    print_section("Key Fields")
    for key, value in fields.items():
        print(f"{key}: {value}")

    hard_checks = [check for check in all_checks if check.name != "dispatch_state"]
    return 0 if all(check.ok for check in hard_checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
