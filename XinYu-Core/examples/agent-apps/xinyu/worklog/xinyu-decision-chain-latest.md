# XinYu Decision Chain Latest

- generated_at: 2026-06-09T13:03:00.642949+00:00
- status: observed
- result: pass
- claim_boundary: latest bounded decision chain only; does not claim consciousness

## Decision Chain
- input_anchor: observed
- perception_gap: owner_attention
- perception_route_hint: voice_to_text_input_gate
- perception_internal_consumed: true
- internal_state: answer_current_turn
- candidate_count: 1
- selected_candidate: answer_current_turn
- selected_total_score: 45
- runner_up_intent: none
- runner_up_gate: none
- runner_up_total_score: 0
- score_margin: 45
- blocked_candidate_count: 0
- held_candidate_count: 0
- review_gated_future_count: 0
- competition_reason: selected=answer_current_turn; no_runner_up; selected_reason=default_current_turn; action_feedback_route_confirmed; owner_feedback_success_keeps_current_trial; perception_owner_attention_current_turn
- runner_up_not_selected_reason: no_runner_up_to_compare
- gate_pressure_summary: selected_gate=current_turn_only; runner_up_gate=none; blocked=0; held=0; review_gated=0
- blocked_intents: none
- held_intents: none
- review_gated_intents: none
- gate: current_turn_only
- action_level: visible_reply_only
- action_result: visible_reply_sent_and_qq_ack_observed
- action_evidence_surface: qq
- action_evidence_signal: qq_visible_reply_ack
- action_evidence_result: delivered
- action_evidence_lifecycle: acked
- action_evidence_future_effect: confirm_visible_reply_transport_for_next_turn
- restraint_reason: none
- proactive_candidate: none
- memory_candidate: none
- action_feedback_signal: qq_visible_reply_ack
- action_feedback_future_effect: confirm_visible_reply_transport_for_next_turn
- owner_feedback_signal: explicit_success
- owner_feedback_future_effect: keep_supported_trial_without_promoting_stable_personality
- owner_response_signal: none
- owner_response_future_effect: none
- feedback_consumption_status: consumed
- feedback_consumed_sources: action_feedback:qq_visible_reply_ack,action_feedback_coverage:patch_task_prepared/running,owner_feedback_effect:explicit_success,perception_gap:owner_attention
- feedback_consumed_biases: <omitted_long_value:sha256:f3c60b4c14154e66>
- feedback_consumed_future_effect: <omitted_long_value:sha256:d2e48f645b339594>
- proactive_response_signal: none
- proactive_response_future_effect: none
- next_behavior_bias: current_trial_risk:-3
- action_evidence_status: verified

## Source Checks
- perception_importance_judgment: ok=true required=true
- perception_gap_consumed_by_internal_state: ok=true required=true
- candidate_competition_auditable: ok=true required=true
- silence_or_hold_explained: ok=true required=false
- truthful_action_result: ok=true required=true
- feedback_changes_future_surface: ok=true required=true
- owner_feedback_changes_expression_strategy: ok=true required=true
- owner_response_changes_request_strategy: ok=true required=false
- feedback_consumption_auditable: ok=true required=true
- proactive_response_feedback_diagnostic: ok=true required=false

## Privacy Boundary
- raw_owner_text_retained: false
- visible_reply_text_retained: false
- prompt_text_retained: false
- state_contains_refs_status_and_bounded_labels_only: true
- consciousness_claim: false

## Notes
- action_evidence:verified
- perception_gap:owner_attention
- action_feedback:qq_visible_reply_ack
- owner_feedback:explicit_success
- feedback_consumption:consumed
- raw_text_not_retained
