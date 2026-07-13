from __future__ import annotations

from pathlib import Path

from xinyu_action_feedback_coverage import build_action_feedback_coverage_report
from xinyu_desire_drive_state import build_desire_drive_snapshot
from xinyu_feedback_consumption_diagnostics import build_feedback_consumption_diagnostics
from xinyu_bridge_kernel_status import build_kernel_governance_status
from xinyu_memory_health_report import build_memory_health_report
from xinyu_owner_feedback_effects import build_owner_feedback_effect_report
from xinyu_perception_importance import build_perception_importance_report
from xinyu_proactive_response_diagnostics import build_proactive_response_diagnostics
from xinyu_stage10_proactive_life_loop import build_stage10_proactive_life_loop
from xinyu_stage11_multisensory_extension import build_stage11_multisensory_extension
from xinyu_stage11_visual_ingress_diagnostics import build_stage11_visual_ingress_diagnostics
from xinyu_stage11_voice_ingress_diagnostics import build_stage11_voice_ingress_diagnostics
from xinyu_stage12_long_term_evaluation import build_stage12_long_term_evaluation
from xinyu_stage13_self_narrative import build_stage13_self_narrative
from xinyu_private_ecosystem import build_private_ecosystem_snapshot
from xinyu_private_desktop_control import build_desktop_snapshot
from xinyu_stage9_self_state_model import build_stage9_self_state_model

from xinyu_status_models import (
    _stage12_live_status_stub,
    extract_value,
    mask_private_identifier,
    read_text,
    redact_local_path,
)

# Field collectors extracted to xinyu_status_qq_fields (facade re-exports for compatibility).
from xinyu_status_qq_fields import (  # noqa: F401
    _load_jsonl_tail,
    _qq_private_no_reply_explanation,
    _qq_rows_with_prepared_links,
    _qq_trace_generation_groups,
    autonomy_decision_chain_fields,
    learning_trial_gate_fields,
    private_reply_selftest_fields,
    qq_group_reply_boundary_fields,
    qq_latest_inbound_flow_fields,
    qq_private_reply_flow_fields,
)


# Health / port / state checks extracted to xinyu_status_checks (facade re-exports for compatibility).
from xinyu_status_checks import (  # noqa: F401
    check_core,
    check_ports,
    check_qq_gateway_config,
    check_state,
    dispatch_state_detail,
    extract_gateway_version,
    extract_shell_version,
    has_established_local,
    http_json,
    netstat_lines,
    tcp_connect,
)


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
    kernel_governance = build_kernel_governance_status(root)
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
        "kernel_governance_available": str(bool(kernel_governance.get("available", False))).lower(),
        "kernel_pending_review_count": str(kernel_governance.get("pending_review_count", "0")),
        "kernel_writes_blocked": str(bool(kernel_governance.get("writes_blocked", False))).lower(),
        "kernel_cycle_count": str(kernel_governance.get("cycle_count", "0")),
        "kernel_reorganization_pending": str(kernel_governance.get("reorganization_pending", "0")),
        "kernel_world_model_pending": str(kernel_governance.get("world_model_pending", "0")),
        "kernel_slow_signal_count": str(kernel_governance.get("slow_signal_count", "0")),
        "kernel_slow_escalation_threshold": str(kernel_governance.get("slow_escalation_threshold", "3")),
        "kernel_reorg_recommendation": str(kernel_governance.get("reorg_recommendation", "insufficient_data")),
        "kernel_granted_scopes": ",".join(kernel_governance.get("granted_scopes", []) or []) or "none",
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
