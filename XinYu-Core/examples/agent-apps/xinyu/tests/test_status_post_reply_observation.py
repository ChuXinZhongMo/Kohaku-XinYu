from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from xinyu_dialogue_archive import store_memory_candidate, update_memory_candidate_status
from xinyu_status import check_qq_gateway_config, check_state, status_fields


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_status_reports_post_reply_self_observation_without_raw_text(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/self/expression_self_learning_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Expression Self Learning State

## Latest Post Reply Observation
- observation_kind: owner_private_reply_self_observation
- self_state_kind: feeling_inquiry
- alive_voice: medium
- mechanical_risk: low
- template_risk: medium
- over_explained_risk: low
- emotional_grounding: present
- self_state_grounding: present
- raw_text_saved: false
- stable_personality_write: no
""",
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["post_reply_observation_kind"] == "owner_private_reply_self_observation"
    assert fields["post_reply_alive_voice"] == "medium"
    assert fields["post_reply_stable_personality_write"] == "no"
    assert checks["post_reply_self_observation"].ok is True
    assert "stable_write=no" in checks["post_reply_self_observation"].detail


def test_status_reports_qq_group_shadow_only_boundary_without_raw_ids(tmp_path: Path) -> None:
    raw_reply_group = "12345678901"
    raw_shadow_only_group = "98765432109"
    config_path = tmp_path / "xinyu_qq_gateway.config.json"
    config_path.write_text(
        json.dumps(
            {
                "enabled": True,
                "core_chat_url": "http://127.0.0.1:8765/chat",
                "codex_command_enabled": True,
                "codex_execute_url": "http://127.0.0.1:8765/codex/execute",
                "codex_command_prefixes": ["/codex"],
                "qq_outbox_enabled": True,
                "qq_outbox_claim_url": "http://127.0.0.1:8765/qq/outbox/claim",
                "qq_outbox_ack_url": "http://127.0.0.1:8765/qq/outbox/ack",
                "owner_user_ids": ["10001"],
                "whitelist_user_ids": ["10001"],
                "allow_group_messages": True,
                "allowed_group_ids": [raw_reply_group],
                "group_trigger_mode": "mention_or_prefix",
                "group_trigger_prefixes": ["心玉"],
                "group_followup_window_seconds": 0,
                "group_shadow_enabled": True,
                "group_shadow_allowed_group_ids": [raw_shadow_only_group],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    shadow_hash = hashlib.sha256(raw_shadow_only_group.encode("utf-8")).hexdigest()[:16]
    state_path = tmp_path / "memory/context/group_shadow_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        f"""# Group Shadow State

- group_id_hash: {shadow_hash}
- triggered: false
- trigger_reason: group_not_allowed
- reply_policy: no_reply_shadow_only
""",
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_qq_gateway_config(tmp_path, config_path)}

    assert fields["qq_group_reply_boundary_status"] == "recent_group_no_reply_by_boundary"
    assert fields["qq_group_latest_reply_boundary"] == "shadow_only_no_reply"
    assert fields["qq_group_shadow_only_group_count"] == "1"
    assert checks["qq_gateway_group_reply_boundary"].ok is True
    assert "latest=shadow_only_no_reply" in checks["qq_gateway_group_reply_boundary"].detail
    assert raw_reply_group not in json.dumps(fields, ensure_ascii=False)
    assert raw_shadow_only_group not in json.dumps(fields, ensure_ascii=False)
    assert raw_reply_group not in checks["qq_gateway_group_reply_boundary"].detail
    assert raw_shadow_only_group not in checks["qq_gateway_group_reply_boundary"].detail


def test_status_reports_latest_inbound_group_shadow_over_stale_private_without_raw_ids(tmp_path: Path) -> None:
    raw_reply_group = "12345678901"
    raw_shadow_only_group = "98765432109"
    raw_group_text = "RAW_GROUP_CHAT_SHOULD_NOT_SURFACE_2233"
    shadow_hash = hashlib.sha256(raw_shadow_only_group.encode("utf-8")).hexdigest()[:16]
    (tmp_path / "xinyu_qq_gateway.config.json").write_text(
        json.dumps(
            {
                "allowed_group_ids": [raw_reply_group],
                "group_shadow_allowed_group_ids": [raw_shadow_only_group],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "recorded_at": "2026-05-29T15:48:05+08:00",
                "arrival_seq": 55,
                "stage": "queued",
                "message_kind": "private",
                "message_type": "private",
                "raw_text": "RAW_PRIVATE_CHAT_SHOULD_NOT_SURFACE_5566",
            },
            {
                "recorded_at": "2026-05-29T15:48:20+08:00",
                "arrival_seq": 55,
                "stage": "dropped",
                "message_kind": "private",
                "message_type": "private",
                "route": "chat",
                "drop_reason": "owner_private_intent_silent",
            },
            {
                "recorded_at": "2026-05-29T15:53:40+08:00",
                "arrival_seq": 56,
                "stage": "queued",
                "message_kind": "group",
                "message_type": "group",
                "group_id_hash": shadow_hash,
                "raw_text": raw_group_text,
            },
            {
                "recorded_at": "2026-05-29T15:53:41+08:00",
                "arrival_seq": 56,
                "stage": "dropped",
                "message_kind": "group",
                "message_type": "group",
                "group_id_hash": shadow_hash,
                "drop_reason": "group_not_allowed",
            },
        ],
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["qq_private_latest_seq"] == "55"
    assert fields["qq_latest_inbound_seq"] == "56"
    assert fields["qq_latest_inbound_scope"] == "group"
    assert fields["qq_latest_inbound_status"] == "group_shadow_only_no_reply"
    assert fields["qq_latest_inbound_no_reply_reason"] == "group_shadow_only_no_reply"
    assert fields["qq_latest_inbound_explanation"] == "latest_group_is_shadow_only_observed_without_visible_reply"
    assert checks["qq_latest_inbound_flow"].ok is True
    assert "seq=56" in checks["qq_latest_inbound_flow"].detail
    assert "scope=group" in checks["qq_latest_inbound_flow"].detail
    assert raw_reply_group not in json.dumps(fields, ensure_ascii=False)
    assert raw_shadow_only_group not in json.dumps(fields, ensure_ascii=False)
    assert raw_group_text not in json.dumps(fields, ensure_ascii=False)
    assert raw_reply_group not in checks["qq_latest_inbound_flow"].detail
    assert raw_shadow_only_group not in checks["qq_latest_inbound_flow"].detail
    assert raw_group_text not in checks["qq_latest_inbound_flow"].detail


def test_status_links_coalesced_private_reply_terminal_to_latest_fragment(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {"arrival_seq": 22, "stage": "queued", "message_kind": "private", "message_type": "private"},
            {"arrival_seq": 22, "stage": "prepared", "message_kind": "private", "route": "chat", "prepared_seq": 2},
            {"arrival_seq": 22, "stage": "coalesced_wait", "message_kind": "private", "route": "chat", "prepared_seq": 2},
            {"arrival_seq": 23, "stage": "queued", "message_kind": "private", "message_type": "private"},
            {"arrival_seq": 23, "stage": "prepared", "message_kind": "private", "route": "chat", "prepared_seq": 3},
            {"arrival_seq": 23, "stage": "coalesced_wait", "message_kind": "private", "route": "chat", "prepared_seq": 3},
            {"arrival_seq": 22, "stage": "dispatch_start", "message_kind": "private", "route": "chat", "prepared_seq": 3},
            {"arrival_seq": 22, "stage": "reply_sent", "message_kind": "private", "route": "chat", "prepared_seq": 3},
        ],
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["qq_private_reply_flow_status"] == "reply_sent"
    assert fields["qq_private_latest_seq"] == "23"
    assert fields["qq_private_latest_chat_seq"] == "23"
    assert fields["qq_private_latest_stage"] == "reply_sent"
    assert fields["qq_private_latest_visible_status"] == "reply_sent"
    assert fields["qq_private_latest_no_reply_reason"] == "none"
    assert fields["qq_private_latest_drop_reason"] == "none"
    assert fields["qq_latest_inbound_status"] == "reply_sent"
    assert fields["qq_latest_inbound_seq"] == "23"
    assert fields["qq_latest_inbound_scope"] == "private"
    assert checks["qq_private_reply_flow"].ok is True
    assert checks["qq_latest_inbound_flow"].ok is True


def test_status_reports_private_text_reply_dropped_after_rich_input_error_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_PRIVATE_CHAT_SHOULD_NOT_SURFACE_9081"
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "recorded_at": "2026-05-28T02:05:49+08:00",
                "arrival_seq": 10,
                "stage": "queued",
                "message_kind": "private",
                "message_type": "private",
                "text_len": len(raw_private),
                "raw_text": raw_private,
            },
            {
                "recorded_at": "2026-05-28T02:05:52+08:00",
                "arrival_seq": 10,
                "stage": "dispatch_start",
                "message_kind": "private",
                "route": "chat",
            },
            {
                "recorded_at": "2026-05-28T02:05:53+08:00",
                "arrival_seq": 11,
                "stage": "prepared",
                "message_kind": "private",
                "message_type": "private",
                "route": "sticker_import",
                "text_len": 0,
                "sticker_count": 1,
            },
            {
                "recorded_at": "2026-05-28T02:06:09+08:00",
                "arrival_seq": 10,
                "stage": "stale_reply_dropped",
                "message_kind": "private",
                "route": "chat",
                "drop_reason": "newer_input_before_visible_send:10->11",
            },
            {
                "recorded_at": "2026-05-28T02:06:16+08:00",
                "arrival_seq": 11,
                "stage": "dispatch_error",
                "message_kind": "private",
                "message_type": "private",
                "route": "sticker_import",
                "sticker_count": 1,
                "error": "BridgeError: core bridge HTTP 500: synthetic sticker import failure",
            },
        ],
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["qq_private_reply_flow_status"] == "text_reply_dropped_after_rich_input_error"
    assert fields["qq_private_latest_visible_status"] == "stale_reply_dropped"
    assert fields["qq_private_latest_chat_seq"] == "10"
    assert fields["qq_private_latest_seq"] == "11"
    assert checks["qq_private_reply_flow"].ok is True
    assert "text_reply_dropped_after_rich_input_error" in checks["qq_private_reply_flow"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["qq_private_reply_flow"].detail


def test_status_private_reply_flow_does_not_merge_arrival_seq_after_restart(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {"arrival_seq": 10, "stage": "queued", "message_kind": "private", "message_type": "private"},
            {"arrival_seq": 10, "stage": "reply_sent", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 11, "stage": "queued", "message_kind": "private", "message_type": "private"},
            {"arrival_seq": 11, "stage": "reply_sent", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 4, "stage": "queued", "message_kind": "private", "message_type": "private"},
            {"arrival_seq": 4, "stage": "dispatch_start", "message_kind": "private", "route": "chat"},
        ],
    )

    fields = status_fields(tmp_path)

    assert fields["qq_private_reply_flow_status"] == "dispatch_started_no_terminal"
    assert fields["qq_private_latest_seq"] == "4"
    assert fields["qq_private_latest_chat_seq"] == "4"
    assert fields["qq_private_latest_visible_status"] == "dispatch_started_no_terminal"


def test_status_surfaces_owner_private_intent_wait_more_drop_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_PRIVATE_FRAGMENT_SHOULD_NOT_SURFACE_710"
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {"arrival_seq": 706, "stage": "queued", "message_kind": "private", "message_type": "private"},
            {"arrival_seq": 706, "stage": "dispatch_start", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 706, "stage": "reply_sent", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 707, "stage": "prepared", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 707, "stage": "coalesced_wait", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 708, "stage": "prepared", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 708, "stage": "coalesced_wait", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 709, "stage": "prepared", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 709, "stage": "coalesced_wait", "message_kind": "private", "route": "chat"},
            {
                "arrival_seq": 710,
                "stage": "prepared",
                "message_kind": "private",
                "message_type": "private",
                "route": "chat",
                "raw_text": raw_private,
                "text_len": len(raw_private),
            },
            {"arrival_seq": 710, "stage": "coalesced_wait", "message_kind": "private", "route": "chat"},
            {
                "arrival_seq": 710,
                "stage": "dropped",
                "message_kind": "private",
                "route": "chat",
                "drop_reason": "owner_private_intent_wait_more",
            },
        ],
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["qq_private_reply_flow_status"] == "owner_private_intent_wait_more"
    assert fields["qq_private_latest_stage"] == "dropped"
    assert fields["qq_private_latest_visible_status"] == "owner_private_intent_wait_more"
    assert fields["qq_private_latest_no_reply_reason"] == "owner_private_intent_wait_more"
    assert fields["qq_private_latest_drop_reason"] == "owner_private_intent_wait_more"
    assert fields["qq_private_latest_no_reply_explanation"] == (
        "intent_gate_treated_latest_chat_as_fragment_and_waited_for_more"
    )
    assert fields["qq_private_recent_coalesced_wait_count"] == "4"
    assert fields["qq_private_recent_intent_wait_more_count"] == "1"
    assert checks["qq_private_reply_flow"].ok is True
    assert "owner_private_intent_wait_more" in checks["qq_private_reply_flow"].detail
    assert "coalesced_wait:4" in checks["qq_private_reply_flow"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["qq_private_reply_flow"].detail


def test_status_reports_private_empty_visible_reply_terminal_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_PRIVATE_EMPTY_REPLY_SHOULD_NOT_SURFACE_2207"
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 5,
                "stage": "queued",
                "message_kind": "private",
                "message_type": "private",
                "text_len": len(raw_private),
                "raw_text": raw_private,
            },
            {"arrival_seq": 5, "stage": "prepared", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 5, "stage": "coalesced_wait", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 6, "stage": "queued", "message_kind": "private", "message_type": "private"},
            {"arrival_seq": 6, "stage": "prepared", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 6, "stage": "coalesced_wait", "message_kind": "private", "route": "chat"},
            {"arrival_seq": 5, "stage": "dispatch_start", "message_kind": "private", "route": "chat"},
            {
                "arrival_seq": 5,
                "stage": "dispatch_done",
                "message_kind": "private",
                "route": "chat",
                "drop_reason": "empty_visible_reply",
            },
        ],
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["qq_private_reply_flow_status"] == "empty_visible_reply"
    assert fields["qq_private_latest_visible_status"] == "empty_visible_reply"
    assert fields["qq_private_latest_no_reply_reason"] == "empty_visible_reply"
    assert fields["qq_private_latest_seq"] == "6"
    assert fields["qq_private_latest_chat_seq"] == "5"
    assert checks["qq_private_reply_flow"].ok is False
    assert "empty_visible_reply" in checks["qq_private_reply_flow"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["qq_private_reply_flow"].detail


def test_status_reports_short_term_continuity_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_OWNER_PRIVATE_LINE_SHOULD_NOT_SURFACE_5544"
    state_path = tmp_path / "memory/context/short_term_continuity_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Short Term Continuity State

- status: active
- direct_reference: true
- recall_status: tail_available
- recall_source: dialogue_archive
- tail_count: 4
- archive_recovered_count: 2
- recent_user_count: 2
- recent_assistant_count: 2
- latest_user_ref: sha256:userhash
- latest_assistant_ref: sha256:assistanthash
- notes: direct_reference_requested, recent_tail_available
- raw_private_body_retained: false
- visible_reply_text_retained: false
"""
        + raw_private,
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["short_term_continuity_status"] == "active"
    assert fields["short_term_continuity_direct_reference"] == "true"
    assert fields["short_term_continuity_recall_status"] == "tail_available"
    assert fields["short_term_continuity_recall_source"] == "dialogue_archive"
    assert fields["short_term_continuity_archive_recovered_count"] == "2"
    assert checks["short_term_continuity_state"].ok is True
    assert "recall=tail_available" in checks["short_term_continuity_state"].detail
    assert "source=dialogue_archive" in checks["short_term_continuity_state"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["short_term_continuity_state"].detail


def test_status_warns_when_direct_reference_tail_is_missing(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/context/short_term_continuity_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Short Term Continuity State

- status: active
- direct_reference: true
- recall_status: tail_missing
- recall_source: none
- tail_count: 0
- archive_recovered_count: 0
- recent_user_count: 0
- recent_assistant_count: 0
""",
        encoding="utf-8",
    )

    checks = {check.name: check for check in check_state(tmp_path)}

    assert checks["short_term_continuity_state"].ok is False
    assert "recall=tail_missing" in checks["short_term_continuity_state"].detail


def test_status_reports_short_term_continuity_canary_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_OWNER_PRIVATE_LINE_SHOULD_NOT_SURFACE_8871"
    state_path = tmp_path / "memory/context/short_term_continuity_canary_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Short Term Continuity Canary State

- status: pass
- direct_reference_count: 3
- recall_available_count: 3
- recall_missing_count: 0
- direct_reference_recall_success_rate_pct: 100.0
- matched_reply_count: 3
- unmatched_reply_count: 0
- which_sentence_recurrence_count: 0
- which_sentence_recurrence_rate_pct: 0.0
- raw_owner_text_in_state: false
- visible_reply_text_in_state: false
"""
        + raw_private,
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["short_term_continuity_canary_status"] == "pass"
    assert fields["short_term_continuity_canary_direct_reference_count"] == "3"
    assert fields["short_term_continuity_canary_recall_success_rate"] == "100.0"
    assert fields["short_term_continuity_canary_which_sentence_recurrence_count"] == "0"
    assert checks["short_term_continuity_canary"].ok is True
    assert "recall_success=100.0" in checks["short_term_continuity_canary"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["short_term_continuity_canary"].detail


def test_status_warns_when_short_term_continuity_canary_needs_check(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/context/short_term_continuity_canary_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Short Term Continuity Canary State

- status: needs_check
- direct_reference_count: 2
- direct_reference_recall_success_rate_pct: 50.0
- matched_reply_count: 2
- unmatched_reply_count: 0
- which_sentence_recurrence_count: 1
- which_sentence_recurrence_rate_pct: 50.0
""",
        encoding="utf-8",
    )

    checks = {check.name: check for check in check_state(tmp_path)}

    assert checks["short_term_continuity_canary"].ok is False
    assert "needs_check" in checks["short_term_continuity_canary"].detail
    assert "which_sentence=1" in checks["short_term_continuity_canary"].detail


def test_status_reports_short_term_recall_diagnostics_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_OWNER_PRIVATE_LINE_SHOULD_NOT_SURFACE_7720"
    state_path = tmp_path / "memory/context/short_term_recall_diagnostics_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Short Term Recall Diagnostics State

- status: pass
- direct_reference_count: 1
- primary_failure_class: none
- working_tail_status: available
- archive_fallback_status: not_needed
- prompt_admission_status: admitted
- prompt_budget_status: ok
- raw_owner_text_in_state: false
- visible_reply_text_in_state: false
"""
        + raw_private,
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["short_term_recall_diagnostics_status"] == "pass"
    assert fields["short_term_recall_diagnostics_failure_class"] == "none"
    assert fields["short_term_recall_diagnostics_working_tail"] == "available"
    assert checks["short_term_recall_diagnostics"].ok is True
    assert "failure=none" in checks["short_term_recall_diagnostics"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["short_term_recall_diagnostics"].detail


def test_status_warns_when_short_term_recall_diagnostics_needs_check(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/context/short_term_recall_diagnostics_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Short Term Recall Diagnostics State

- status: needs_check
- primary_failure_class: read_path
- working_tail_status: missing
- archive_fallback_status: read_path_error
- prompt_admission_status: admitted
- prompt_budget_status: ok
""",
        encoding="utf-8",
    )

    checks = {check.name: check for check in check_state(tmp_path)}

    assert checks["short_term_recall_diagnostics"].ok is False
    assert "failure=read_path" in checks["short_term_recall_diagnostics"].detail


def test_status_reports_action_feedback_coverage_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_ACTION_FEEDBACK_COVERAGE_SHOULD_NOT_SURFACE_6158"
    action_state = tmp_path / "memory/context/action_feedback_state.md"
    action_state.parent.mkdir(parents=True, exist_ok=True)
    action_state.write_text(
        f"""# Action Feedback State

- checked_at: 2026-05-27T15:20:00+08:00
- event_id: actfb-test
- feedback_signal: qq_visible_reply_ack
- action_result: delivered
- future_effect: confirm_visible_reply_transport_for_next_turn
- visible_reply_text: {raw_private}
""",
        encoding="utf-8",
    )
    codex_state = tmp_path / "runtime/codex_presence_state.json"
    codex_state.parent.mkdir(parents=True, exist_ok=True)
    codex_state.write_text(
        json.dumps(
            {
                "updated_at": "2026-05-27T15:21:00+08:00",
                "status": "finished",
                "job_id": "codex-job-coverage",
                "exit_code": 0,
                "timed_out": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["action_feedback_coverage_status"] == "pass"
    assert fields["action_feedback_coverage_observed_surface_count"] == "2"
    assert fields["action_feedback_coverage_non_qq_surface_count"] == "1"
    assert fields["action_feedback_coverage_codex_status"] == "observed"
    assert fields["action_feedback_coverage_codex_lifecycle"] == "succeeded"
    assert fields["action_feedback_coverage_latest_lifecycle"] == "succeeded"
    assert checks["action_feedback_coverage"].ok is True
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["action_feedback_coverage"].detail


def test_status_reports_owner_feedback_effect_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_OWNER_FEEDBACK_EFFECT_STATUS_SHOULD_NOT_SURFACE_2864"
    state_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        f"""# Learning Closed Loop State

## Current Loop
- status: trial_active
- updated_at: 2026-05-27T17:05:00+08:00
- latest_event_id: learnloop-status-owner-effect
- latest_failure_kind: owner_reported_context_discontinuity
- active_trial_habit: use recent concrete context before answering
- expected_next_behavior: anchor the last real turn before abstract explanation
- repair_count: 2
- success_count: 0
- success_streak: 0
- trial_success_count: 0
- trial_success_streak: 0
- latest_success_trial_key: none
- success_evidence_status: none
- promotion_signal: false
- last_owner_reaction: repair_pressure
{raw_private}
""",
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["owner_feedback_effect_status"] == "active"
    assert fields["owner_feedback_effect_signal"] == "owner_reported_context_discontinuity"
    assert fields["owner_feedback_effect_expression_bias"] == "anchor_recent_context_before_reply"
    assert fields["owner_feedback_effect_intention_bias"] == "direct_reference_requires_tail"
    assert fields["owner_feedback_effect_trial_success_count"] == "0"
    assert fields["owner_feedback_effect_trial_success_streak"] == "0"
    assert fields["owner_feedback_effect_success_trial_key"] == "none"
    assert fields["owner_feedback_effect_success_evidence"] == "none"
    assert checks["owner_feedback_effect"].ok is True
    assert "expression_bias=anchor_recent_context_before_reply" in checks["owner_feedback_effect"].detail
    assert "same_key_success=0/0" in checks["owner_feedback_effect"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["owner_feedback_effect"].detail


def test_status_reports_memory_learning_trial_gate_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_MEMORY_LEARNING_TRIAL_GATE_SHOULD_NOT_SURFACE_7042"
    learning_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    learning_path.parent.mkdir(parents=True, exist_ok=True)
    learning_path.write_text(
        f"""# Learning Closed Loop State

## Current Loop
- status: trial_active
- updated_at: 2026-05-28T00:10:00+08:00
- latest_event_id: learnloop-status-trial-gate
- latest_failure_kind: owner_reported_template_voice_failure
- active_trial_key: owner_reported_template_voice_failure
- active_trial_habit: replace_explanations_with_one_concrete_owner-facing_line_under_style_pressure
- expected_next_behavior: replace the next line instead of explaining the mechanism
- repair_count: 12
- success_count: 3
- success_streak: 0
- trial_success_count: 3
- trial_success_streak: 0
- promotion_signal: false
- last_owner_reaction: repair_pressure

## Success Evidence
- latest_success_at: none
- latest_success_event_id: none
- latest_success_trial_key: none
- success_evidence_status: reset_by_failure
- success_evidence_ref: none
{raw_private}
""",
        encoding="utf-8",
    )
    self_review_path = tmp_path / "memory/self/personality_self_review_state.md"
    self_review_path.parent.mkdir(parents=True, exist_ok=True)
    self_review_path.write_text(
        """# Personality Self Review State

## Decision
- decision: continue_trial
- action: keep_runtime_trial_only
- profile_changed: false

## Candidate
- learning_trial_gate_reason: learning_trial_success_gate_not_satisfied:repair_pressure_overloaded:12,trial_success_streak_below_2:0,success_evidence_not_same_trial:reset_by_failure
""",
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["memory_learning_trial_gate"] == "blocked"
    assert fields["memory_learning_trial_active_key"] == "owner_reported_template_voice_failure"
    assert fields["memory_learning_trial_success_key"] == "none"
    assert fields["memory_learning_trial_success_evidence"] == "reset_by_failure"
    assert fields["memory_learning_trial_same_key_success_count"] == "3"
    assert fields["memory_learning_trial_same_key_success_streak"] == "0"
    assert fields["memory_learning_trial_stable_write"] == "blocked"
    assert fields["owner_feedback_effect_realtime_pressure"] == "capped_direct_failure_only"
    assert fields["owner_feedback_effect_expression_bias"] == "style_repair_pressure_capped_keep_current_turn_anchor"
    assert fields["owner_feedback_effect_intention_bias"] == "repair_relation_visible_risk:-2"
    assert checks["memory_learning_trial_gate"].ok is True
    assert checks["owner_feedback_effect"].ok is True
    assert "evidence=reset_by_failure" in checks["memory_learning_trial_gate"].detail
    assert "stable_write=blocked" in checks["memory_learning_trial_gate"].detail
    assert "realtime_pressure=capped_direct_failure_only" in checks["owner_feedback_effect"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["memory_learning_trial_gate"].detail
    assert raw_private not in checks["owner_feedback_effect"].detail


def test_status_gate_reason_not_stale_once_ready_for_self_review(tmp_path: Path) -> None:
    # Two clean same-trial successes -> gate is ready_for_self_review. Even if the
    # self-review file still carries an old blocked reason, status must not surface a
    # stale "not_satisfied / streak_below_2" reason that contradicts the gate.
    learning_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    learning_path.parent.mkdir(parents=True, exist_ok=True)
    learning_path.write_text(
        """# Learning Closed Loop State

## Current Loop
- status: trial_supported
- updated_at: 2026-05-31T19:58:00+08:00
- latest_event_id: learnloop-ready-self-review
- latest_failure_kind: memory_mechanics_leak
- active_trial_key: memory_mechanics_leak
- active_trial_habit: hold the conversation first, no file or state-card reading posture
- expected_next_behavior: answer without exposing memory machinery
- repair_count: 106
- success_count: 7
- success_streak: 2
- trial_success_count: 2
- trial_success_streak: 2
- promotion_signal: possible_after_self_review
- last_owner_reaction: explicit_success

## Success Evidence
- latest_success_at: 2026-05-31T19:58:00+08:00
- latest_success_trial_key: memory_mechanics_leak
- success_evidence_status: same_trial_explicit_owner_success
""",
        encoding="utf-8",
    )
    self_review_path = tmp_path / "memory/self/personality_self_review_state.md"
    self_review_path.parent.mkdir(parents=True, exist_ok=True)
    self_review_path.write_text(
        """# Personality Self Review State

## Decision
- decision: continue_trial
- action: keep_runtime_trial_only
- profile_changed: false

## Candidate
- learning_trial_gate_reason: learning_trial_success_gate_not_satisfied:repair_pressure_overloaded:106,trial_success_streak_below_2:1
""",
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    reason = fields["memory_learning_trial_gate_reason"]

    assert fields["memory_learning_trial_gate"] == "ready_for_self_review"
    assert fields["memory_learning_trial_same_key_success_streak"] == "2"
    # The stale blocked reason must not leak through once the gate is met.
    assert "not_satisfied" not in reason
    assert "streak_below_2" not in reason
    assert "met_pending_self_review" in reason
    assert "same_key_success=2/2" in reason


def test_status_reports_owner_response_feedback_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_OWNER_RESPONSE_STATUS_SHOULD_NOT_SURFACE_2865"
    state_path = tmp_path / "memory/context/proactive_request_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        f"""# Proactive Request State

- status: read_locally
- checked_at: 2026-05-27T17:07:00+08:00
- request_id: proactive-response-status
- request_answer_state: read_locally
- last_ack_status: read_locally
- requested_action: ask_owner
{raw_private}
""",
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["owner_response_feedback_signal"] == "desktop_read_locally"
    assert fields["owner_response_strategy_bias"] == "desktop_followup_without_reasking_same_prompt"
    assert fields["owner_response_intention_bias"] == "proactive_repeat_risk:+4"
    assert checks["owner_response_feedback_effect"].ok is True
    assert "signal=desktop_read_locally" in checks["owner_response_feedback_effect"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["owner_response_feedback_effect"].detail


def test_status_reports_autonomy_decision_chain_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_AUTONOMY_DECISION_STATUS_SHOULD_NOT_SURFACE_4821"
    now = datetime.now(timezone.utc).isoformat()
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "autonomy-status-input",
                "stage": "queued",
                "recorded_at": now,
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "autonomy-status-input",
                "stage": "dispatch_start",
                "recorded_at": now,
            },
        ],
    )
    state_path = tmp_path / "memory/context/intention_ecology_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        f"""# Intention Ecology State

- selected_intent: hold_presence
- selected_gate: hold_or_silence
- action_level: silence
- autonomy_posture: bounded_restraint
- feedback_signal: none
- perception_gap_signal: owner_attention
- perception_gap_bias: owner_attention_current_turn_value:+6;require_short_term_anchor
- perception_route_hint: attention_posture_and_intention_ecology
- proactive_candidate: none
- memory_candidate: none
- restraint_reason: owner_needs_space
- candidate_count: 2
- candidate_competition_status: observed
- selected_total_score: 44
- runner_up_intent: answer_current_turn
- runner_up_gate: current_turn_only
- runner_up_total_score: 28
- score_margin: 16
- blocked_candidate_count: 0
- held_candidate_count: 1
- review_gated_future_count: 0
- competition_reason: selected=hold_presence; runner_up=answer_current_turn; margin=16
- runner_up_not_selected_reason: lower_total_score:margin=16
- gate_pressure_summary: selected_gate=hold_or_silence; runner_up_gate=current_turn_only; blocked=0; held=1; review_gated=0
- blocked_intents: none
- held_intents: hold_presence
- review_gated_intents: none
- proactive_delivery: review_gated
- stable_memory_write: gated
- raw_private_body_retained: false
{raw_private}
""",
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["autonomy_decision_chain_status"] == "observed"
    assert fields["autonomy_decision_selected_candidate"] == "hold_presence"
    assert fields["autonomy_decision_selected_total_score"] == "44"
    assert fields["autonomy_decision_runner_up_intent"] == "answer_current_turn"
    assert fields["autonomy_decision_runner_up_not_selected_reason"] == "lower_total_score:margin=16"
    assert fields["autonomy_decision_gate_pressure_summary"].startswith("selected_gate=hold_or_silence")
    assert fields["autonomy_decision_score_margin"] == "16"
    assert fields["autonomy_decision_held_candidate_count"] == "1"
    assert fields["autonomy_decision_held_intents"] == "hold_presence"
    assert fields["autonomy_decision_gate"] == "hold_or_silence"
    assert fields["autonomy_decision_action_level"] == "silence"
    assert fields["autonomy_decision_action_result"] == "bounded_non_action:hold_or_silence"
    assert fields["autonomy_decision_action_evidence_status"] == "bounded_non_action"
    assert fields["autonomy_decision_restraint_reason"] == "owner_needs_space"
    assert fields["autonomy_decision_perception_gap"] == "owner_attention"
    assert fields["perception_importance_status"] == "pass"
    assert fields["perception_importance_owner_attention_count"] == "1"
    assert checks["autonomy_decision_chain"].ok is True
    assert checks["perception_importance"].ok is True
    assert "result=bounded_non_action:hold_or_silence" in checks["autonomy_decision_chain"].detail
    assert "runner_up_reason=lower_total_score:margin=16" in checks["autonomy_decision_chain"].detail
    assert "evidence=bounded_non_action" in checks["autonomy_decision_chain"].detail
    assert "latest=owner_attention" in checks["perception_importance"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["autonomy_decision_chain"].detail
    assert raw_private not in checks["perception_importance"].detail


def test_status_reports_local_action_evidence_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_AUTONOMY_LOCAL_ACTION_STATUS_SHOULD_NOT_SURFACE_7240"
    now = datetime.now(timezone.utc).isoformat()
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "autonomy-local-action-status-input",
                "stage": "queued",
                "recorded_at": now,
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "autonomy-local-action-status-input",
                "stage": "dispatch_start",
                "recorded_at": now,
            },
        ],
    )
    context = tmp_path / "memory/context"
    context.mkdir(parents=True, exist_ok=True)
    (context / "intention_ecology_state.md").write_text(
        f"""# Intention Ecology State

- selected_intent: do_bounded_task
- selected_gate: current_turn_only
- action_level: visible_reply_or_local_work
- autonomy_posture: bounded_local_work
- feedback_signal: none
- action_feedback_signal: none
- action_feedback_bias: none
- action_feedback_coverage_signal: patch_task_prepared
- action_feedback_coverage_bias: patch_task_prepared_task_risk:-2
- perception_gap_signal: owner_attention
- perception_gap_bias: owner_attention_current_turn_value:+6;require_short_term_anchor
- perception_route_hint: attention_posture_and_intention_ecology
- proactive_candidate: none
- memory_candidate: none
- restraint_reason: none
- candidate_count: 2
- candidate_competition_status: observed
- selected_total_score: 88
- runner_up_intent: answer_current_turn
- runner_up_gate: current_turn_only
- runner_up_total_score: 36
- score_margin: 52
- blocked_candidate_count: 0
- held_candidate_count: 0
- review_gated_future_count: 0
- competition_reason: selected=do_bounded_task; runner_up=answer_current_turn; margin=52
- runner_up_not_selected_reason: lower_total_score:margin=52
- gate_pressure_summary: selected_gate=current_turn_only; runner_up_gate=current_turn_only; blocked=0; held=0; review_gated=0
- blocked_intents: none
- held_intents: none
- review_gated_intents: none
- proactive_delivery: review_gated
- stable_memory_write: gated
- raw_private_body_retained: false
{raw_private}
""",
        encoding="utf-8",
    )
    (context / "attention_posture_state.md").write_text(
        """# Attention Posture State

- attention_target: local_task
- attention_mode: repair_needed
- ignored_event_count: 0
- noted_event_count: 1
- last_route: local_action
- perception_gap_type: owner_attention
- perception_route_hint: attention_posture_and_intention_ecology
- perception_gap_consumed: true
""",
        encoding="utf-8",
    )
    (context / "self_action_patch_executor_state.md").write_text(
        """# Self Action Patch Executor State

- checked_at: 2026-05-27T14:41:00+08:00
- status: prepared
- execution_level: prepare
- queue_id: selfaction-queue-test
- task_id: selfaction-patch-test
- codex_status: not_requested
- report_path: none
""",
        encoding="utf-8",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["autonomy_decision_action_result"] == (
        "local_action_result_observed:patch_executor/patch_task_prepared/prepared"
    )
    assert fields["autonomy_decision_action_evidence_status"] == "verified"
    assert fields["autonomy_decision_action_evidence_surface"] == "patch_executor"
    assert fields["autonomy_decision_action_evidence_signal"] == "patch_task_prepared"
    assert fields["autonomy_decision_action_evidence_result"] == "prepared"
    assert fields["autonomy_decision_action_evidence_lifecycle"] == "prepared"
    assert fields["autonomy_decision_feedback_consumption_status"] == "consumed"
    assert "action_feedback_coverage:patch_task_prepared/prepared" in (
        fields["autonomy_decision_feedback_consumed_sources"]
    )
    assert "action_feedback_coverage_bias:patch_task_prepared_task_risk:-2" in (
        fields["autonomy_decision_feedback_consumed_biases"]
    )
    assert checks["autonomy_decision_chain"].ok is True
    assert "surface=patch_executor" in checks["autonomy_decision_chain"].detail
    assert "signal=patch_task_prepared" in checks["autonomy_decision_chain"].detail
    assert "lifecycle=prepared" in checks["autonomy_decision_chain"].detail
    assert "feedback_consumption=consumed" in checks["autonomy_decision_chain"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["autonomy_decision_chain"].detail


def test_status_reports_feedback_consumption_diagnostics_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_STATUS_FEEDBACK_CONSUMPTION_SHOULD_NOT_SURFACE_4138"
    _write_jsonl(
        tmp_path / "runtime/intention_ecology_trace.jsonl",
        [
            {
                "checked_at": "2026-05-29T13:00:00+08:00",
                "ecology_id": "eco-status-feedback-1",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "action_feedback:qq_visible_reply_ack",
                "feedback_consumed_biases": "action_feedback_bias:route_confirmed_visible_reply_risk:-4",
                "feedback_consumed_future_effect": "action_feedback_future:confirm_visible_reply_transport",
                "raw_private_body": raw_private,
            },
            {
                "checked_at": "2026-05-29T13:01:00+08:00",
                "ecology_id": "eco-status-feedback-2",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "owner_feedback_effect:owner_reported_template_voice_failure",
                "feedback_consumed_biases": "owner_feedback_effect_bias:repair_relation_visible_risk:-2",
                "feedback_consumed_future_effect": "owner_feedback_future:reduce_template_voice",
            },
        ],
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["feedback_consumption_diagnostics_status"] == "pass"
    assert fields["feedback_consumption_sample_count"] == "2"
    assert fields["feedback_consumption_required_count"] == "2"
    assert fields["feedback_consumption_consumed_count"] == "2"
    assert fields["feedback_consumption_rate_pct"] == "100.0"
    assert fields["feedback_consumption_latest_status"] == "consumed"
    assert fields["stage7_feedback_closure_status"] == "collecting_samples"
    assert fields["stage7_feedback_ready_for_stage8"] == "false"
    assert checks["feedback_consumption_diagnostics"].ok is True
    assert "rate=100.0" in checks["feedback_consumption_diagnostics"].detail
    assert "stage7=collecting_samples" in checks["feedback_consumption_diagnostics"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["feedback_consumption_diagnostics"].detail


def test_status_reports_stage8_memory_governance_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_STATUS_STAGE8_MEMORY_GOVERNANCE_SHOULD_NOT_SURFACE_9051"
    _write_jsonl(
        tmp_path / "runtime/intention_ecology_trace.jsonl",
        [
            {
                "checked_at": f"2026-05-29T18:1{index}:00+08:00",
                "ecology_id": f"eco-status-stage8-{index}",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "action_feedback:qq_visible_reply_ack",
                "feedback_consumed_biases": "action_feedback_bias:route_confirmed_visible_reply_risk:-4",
                "feedback_consumed_future_effect": "action_feedback_future:confirm_visible_reply_transport",
            }
            for index in range(3)
        ],
    )
    assert store_memory_candidate(
        tmp_path,
        candidate_id="memcand-status-stage8-owner-review",
        candidate_type="owner_preference",
        source_message_ids=[91],
        source_turn_id="turn-status-stage8",
        candidate_text=f"private owner preference body must stay hidden {raw_private}",
        confidence_score=72,
        target_gate="owner_memory_review",
        target_memory_layer="memory/people/owner.md",
        reason="owner preference needs explicit review",
        risk_flags=["scope:owner_private", "danger:medium"],
        created_at="2026-05-29T18:10:00+08:00",
    )
    assert update_memory_candidate_status(
        tmp_path,
        candidate_id="memcand-status-stage8-owner-review",
        status="owner_review_required",
        review_notes="needs owner decision",
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["stage8_memory_governance_status"] == "active_guarded"
    assert fields["stage8_stage7_ready_for_stage8"] == "true"
    assert fields["stage8_memory_ready_for_stage9"] == "false"
    assert fields["stage8_owner_review_required_count"] == "1"
    assert fields["stage8_owner_review_candidate_text"] == "hidden"
    assert fields["stage8_stable_identity_profile_apply"] == "blocked"
    assert fields["stage8_learning_trial_validation_status"] == "not_required"
    assert fields["stage8_learning_trial_validation_needed_success_count"] == "0"
    assert checks["stage8_memory_governance"].ok is True
    assert "active_guarded" in checks["stage8_memory_governance"].detail
    assert "owner_review=1" in checks["stage8_memory_governance"].detail
    assert "learning_validation=not_required" in checks["stage8_memory_governance"].detail
    assert raw_private not in json.dumps(fields, ensure_ascii=False)
    assert raw_private not in checks["stage8_memory_governance"].detail
