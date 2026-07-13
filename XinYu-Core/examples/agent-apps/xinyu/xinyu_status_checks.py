from __future__ import annotations

"""Runtime health / port / gateway / state checks for xinyu_status.

Extracted from xinyu_status_collect to shrink the god collector module.
Behavior-preserving: pure helpers + Check builders only; no intentional logic change.
"""

import json
import re
import socket
import subprocess
import urllib.error
from pathlib import Path
from typing import Any

from xinyu_status_models import (
    NO_PROXY_OPENER,
    Check,
    load_json,
    read_text,
    redact_local_path,
    runtime_text_health_issues,
)
from xinyu_status_qq_fields import qq_group_reply_boundary_fields


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

def dispatch_state_detail(fields: dict[str, str]) -> str:
    if (
        fields.get("last_claim_status") == "failed"
        and fields.get("last_ack_status") == "failed"
        and fields.get("adapter_error") == "dry_run_not_enqueued"
    ):
        return "claim=dry_run ack=dry_run"


def check_state(root: Path) -> list[Check]:
    # Lazy import: status_fields lives in xinyu_status_collect (avoids cycle).
    from xinyu_status_collect import status_fields

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
