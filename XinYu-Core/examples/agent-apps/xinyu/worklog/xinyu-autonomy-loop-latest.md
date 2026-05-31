# XinYu Autonomy Loop Report

- generated_at: 2026-05-28T15:31:01.136111+00:00
- definition: bounded_verifiable_self_generating_autonomy_loop
- result: pass
- claim_boundary: verifies closed-loop evidence only; does not claim consciousness

## Main Loop Checks
- OK runtime_alive (required; external/internal input surface): status_ok=true core=True gateway=True napcat_ws=True known_errors=0
- OK input_anchor_observed (required; input retention): recent private owner QQ input observed
- OK short_term_continuity_anchor_visible (optional; input retention): status=inactive; direct_reference=false; recall_status=not_requested; recall_source=not_requested; tail_count=64; archive_recovered_count=0; recent_user_count=3; recent_assistant_count=5
- OK short_term_continuity_canary (required; input retention): status=pass; direct_reference_count=1; recall_success_rate=100.0; matched_reply_count=1; unmatched_reply_count=0; which_sentence_recurrence_count=0
- OK short_term_recall_diagnostics (required; input retention): status=pass; direct_reference_count=13; failure=none; tail=available; archive=not_needed; prompt=missing; budget=unknown
- OK qq_reply_integrity_diagnostics (required; input retention): status=pass; visible=4; naked_ack=0; missing_working_memory=0; semantic_fast_direct=0; semantic_fast_direct_without_archive=0; semantic_fast_direct_without_visible_ack=0
- OK unified_perception_event_layer (required; unified perception event layer): status=pass; events=11; sources=8; input=1; qq=4; desktop=1; tool=3; system=2; file=0; anomaly=1
- OK perception_importance_judgment (required; importance/anomaly -> internal gap): status=pass; events=11; judged=11; high_attention=2; anomaly=1; gaps=5; owner_attention=1; repair=1; maintenance=2; latest_gap=maintenance_gap; route=gate_repair_before_visible_send
- OK dispatch_reached_core (required; input -> thought boundary): core dispatch started for private input
- OK internal_state_gap_visible (required; internal state / need): selected_intent=do_bounded_task; attention_mode=wants_to_speak; perception_gap=maintenance_gap; perception_gap_count=5
- OK candidate_generated (required; candidate intention/action): candidate_count=2; selected_intent=do_bounded_task
- OK gate_decision_visible (required; gate / boundary): selected_gate=current_turn_only; action_level=visible_reply_or_local_work
- OK silence_or_hold_explained (optional; gate / boundary): selected_gate=current_turn_only; action_level=visible_reply_or_local_work; restraint_reason=none; proactive_candidate=none; memory_candidate=none
- OK truthful_action_result (required; bounded action result): visible_reply_sent_and_qq_ack_observed
- OK visible_send_privacy_guard (required; action privacy boundary): shadow guard passed; raw prompt/reply not saved
- OK feedback_changes_future_surface (required; feedback -> future behavior): feedback_signal=qq_visible_reply_ack; action_result=delivered; future_effect=confirm_visible_reply_transport_for_next_turn; memory_effect=sent_reply_index_updated; intention_feedback_signal=qq_visible_reply_ack; intention_feedback_bias=route_confirmed_visible_reply_risk:-4
- OK multi_action_feedback_coverage (required; feedback -> future behavior): status=pass; observed=7; non_qq=6; future_effects=7; failures=0; latest=patch_executor/patch_task_prepared
- OK multi_action_feedback_consumed_by_intention (required; feedback -> future behavior): coverage_signal=runtime_probe_turn_active; coverage_bias=local_tool_probe_succeeded_task_risk:-3,code_probe_clean_source_claim_risk:-2,codex_delegate_finished_task_risk:-2,patch_task_prepared_task_risk:-2,desktop_dry_run_keeps_proactive_review_gate; non_qq=6; latest=patch_executor/patch_task_prepared
- OK owner_feedback_changes_expression_strategy (required; feedback -> future behavior): status=active; signal=owner_reported_template_voice_failure; expression_bias=style_repair_pressure_capped_keep_current_turn_anchor; intention_bias=repair_relation_visible_risk:-2; future_effect=style_repair_direct_only_ordinary_chat_keeps_current_anchor; realtime_pressure=capped_direct_failure_only; intention_signal=owner_reported_template_voice_failure; intention_bias=repair_relation_visible_risk:-2; intention_expression_bias=style_repair_pressure_capped_keep_current_turn_anchor
- OK owner_response_changes_request_strategy (optional; feedback -> future behavior): signal=none; strategy_bias=none; intention_bias=none; future_effect=none; intention_signal=none; intention_bias=none; intention_strategy_bias=none
- OK proactive_response_feedback_diagnostic (optional; feedback -> future behavior): status=observed; signal=none; waiting=False; timeout=False; age_minutes=7096.0; minutes_until_timeout=none
- OK memory_boundary_held (required; memory boundary): stable_memory_write=gated; raw_private_body_retained=false

## Current State
### decision_chain
- input_anchor: observed
- perception_gap: maintenance_gap
- perception_route_hint: gate_repair_before_visible_send
- internal_state: do_bounded_task
- candidate_count: 2
- selected_candidate: do_bounded_task
- gate: current_turn_only
- action_level: visible_reply_or_local_work
- action_result: visible_reply_sent_and_qq_ack_observed
- restraint_reason: none
- proactive_candidate: none
- memory_candidate: none
- action_feedback_signal: qq_visible_reply_ack
- action_feedback_future_effect: confirm_visible_reply_transport_for_next_turn
- owner_feedback_signal: owner_reported_template_voice_failure
- owner_feedback_future_effect: style_repair_direct_only_ordinary_chat_keeps_current_anchor
- owner_response_signal: none
- owner_response_future_effect: none
- proactive_response_signal: none
- proactive_response_future_effect: none
- next_behavior_bias: repair_relation_visible_risk:-2
### intention
- selected_intent: do_bounded_task
- selected_gate: current_turn_only
- action_level: visible_reply_or_local_work
- autonomy_posture: current_turn_grounded_choice
- feedback_signal: none
- action_feedback_signal: qq_visible_reply_ack
- action_feedback_bias: route_confirmed_visible_reply_risk:-4
- action_feedback_coverage_signal: runtime_probe_turn_active
- action_feedback_coverage_bias: local_tool_probe_succeeded_task_risk:-3,code_probe_clean_source_claim_risk:-2,codex_delegate_finished_task_risk:-2,patch_task_prepared_task_risk:-2,desktop_dry_run_keeps_proactive_review_gate
- owner_feedback_effect_signal: owner_reported_template_voice_failure
- owner_feedback_effect_bias: repair_relation_visible_risk:-2
- owner_feedback_expression_bias: style_repair_pressure_capped_keep_current_turn_anchor
- owner_response_feedback_signal: none
- owner_response_feedback_bias: none
- owner_response_strategy_bias: none
- proactive_candidate: none
- memory_candidate: none
- restraint_reason: none
- proactive_delivery: review_gated
- stable_memory_write: gated
- raw_private_body_retained: false
### attention
- attention_mode: wants_to_speak
- attention_target: owner_private
- last_route: owner_private_question
- ignored_event_count: 0
- noted_event_count: 6
### relation
- scene: technical_or_system_design
- user_need: direct_answer_or_implementation
- response_posture: answer_directly
- initiative_allowed: local_only
### self_thought
- candidate_enabled: false
- status: held
- route: codex_delegate_candidate
### short_term_continuity
- status: inactive
- direct_reference: false
- recall_status: not_requested
- recall_source: not_requested
- tail_count: 64
- archive_recovered_count: 0
- recent_user_count: 3
- recent_assistant_count: 5
- latest_user_ref: sha256:71b2849576aa411d
- latest_assistant_ref: sha256:f9d90f95dd296033
### short_term_continuity_canary
- status: pass
- direct_reference_count: 1
- recall_success_rate: 100.0
- matched_reply_count: 1
- unmatched_reply_count: 0
- which_sentence_recurrence_count: 0
### short_term_recall_diagnostics
- status: pass
- primary_failure_class: none
- working_tail_status: available
- archive_fallback_status: not_needed
- prompt_admission_status: missing
- prompt_budget_status: unknown
### qq_reply_integrity_diagnostics
- status: pass
- visible_chat_reply_count: 4
- naked_ack_visible_reply_count: 0
- visible_reply_missing_working_memory_count: 0
- semantic_fast_direct_reply_count: 0
- semantic_fast_direct_reply_without_archive_count: 0
- semantic_fast_direct_reply_without_visible_ack_count: 0
- working_memory_file_count: 36
- working_memory_row_count: 1186
### perception_event_layer
- status: pass
- event_count: 11
- source_count: 8
- event_type_count: 7
- input_event_count: 1
- qq_event_count: 4
- desktop_event_count: 1
- tool_result_event_count: 3
- system_health_event_count: 2
- file_change_event_count: 0
- visual_event_count: 0
- voice_event_count: 0
- importance_ready_count: 11
- anomaly_count: 1
- latest_event_type: system_health_change
- latest_event_source: code_probe
- latest_event_ref: sha256:4c8fb5a779cd0516
### perception_importance
- status: pass
- event_count: 11
- judged_event_count: 11
- high_attention_count: 2
- anomaly_judgment_count: 1
- internal_gap_count: 5
- owner_attention_count: 1
- repair_gap_count: 1
- boundary_gap_count: 1
- action_residue_count: 6
- maintenance_gap_count: 2
- coverage_gap_count: 2
- max_attention_weight: 100
- latest_gap_type: maintenance_gap
- latest_future_effect: avoid_or_resume_actions_based_on_runtime_health
- next_route_hint: gate_repair_before_visible_send
### action_feedback
- feedback_signal: qq_visible_reply_ack
- action_result: delivered
- future_effect: confirm_visible_reply_transport_for_next_turn
- scoring_effect: keep_current_route_available
- memory_effect: sent_reply_index_updated
- stable_memory_write: blocked
- raw_private_body_retained: false
- visible_reply_text_retained: false
### action_feedback_coverage
- status: pass
- observed_surface_count: 7
- non_qq_surface_count: 6
- future_effect_count: 7
- failure_count: 0
- latest_feedback_signal: patch_task_prepared
- latest_feedback_surface: patch_executor
- qq_feedback_status: observed
- desktop_feedback_status: observed
- codex_feedback_status: observed
- local_tool_feedback_status: observed
- patch_executor_feedback_status: observed
- code_probe_status: observed
- runtime_probe_status: observed
### owner_feedback_effect
- status: active
- latest_feedback_kind: owner_reported_template_voice_failure
- owner_reaction: repair_pressure
- expression_strategy_bias: style_repair_pressure_capped_keep_current_turn_anchor
- intention_bias: repair_relation_visible_risk:-2
- future_effect: style_repair_direct_only_ordinary_chat_keeps_current_anchor
- repair_pressure_count: 94
- success_count: 3
- success_streak: 0
- promotion_signal: false
- feedback_event_ref: sha256:df5e2a85d03a086f
- owner_response_signal: none
- owner_response_source: none
- owner_response_strategy_bias: none
- owner_response_intention_bias: none
- owner_response_future_effect: none
- owner_response_event_ref: sha256:ff0487ac88b3dd18
### proactive_response_diagnostics
- status: observed
- response_signal_candidate: none
- request_status: dry_run
- request_answer_state: not_requested
- last_ack_status: dry_run
- delivery_level: queue_owner_private
- delivered_waiting_owner: False
- timeout_active: False
- age_minutes: 7096.0
- minutes_until_no_response_timeout: none
- next_no_response_timeout_at: none
- future_effect_if_timeout: none
- request_event_ref: sha256:ff0487ac88b3dd18

## Privacy Boundary
- raw_owner_text_in_report: false
- visible_reply_text_in_report: false
- stable_personality_claim: false
- consciousness_claim: false
