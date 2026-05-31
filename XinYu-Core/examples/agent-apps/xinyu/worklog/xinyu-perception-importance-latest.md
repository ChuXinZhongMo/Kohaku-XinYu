# XinYu Perception Importance

- generated_at: 2026-05-28T23:30:32+08:00
- status: pass
- result: pass
- claim_boundary: judges event pressure and internal gaps only; does not claim consciousness

## Metrics
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
- sensory_observation_count: 0
- coverage_gap_count: 2
- max_attention_weight: 100
- latest_gap_type: maintenance_gap
- latest_future_effect: avoid_or_resume_actions_based_on_runtime_health
- latest_event_ref: sha256:fcbdc0c0f4cd62f8
- next_route_hint: gate_repair_before_visible_send

## Event Judgments
### percimp-c18e58e7232e877a
- event_id: percevt-bf6d7baab93d2b0d
- event_type: tool_execution_result
- source: codex
- attention_class: medium
- attention_weight: 50
- gap_type: action_residue
- anomaly_kind: none
- internal_pressure: tool_result_should_change_task_strategy
- suggested_route: action_feedback_coverage
- future_effect: adjust_next_tool_or_task_choice_from_result
- evidence_ref: sha256:4cce5284d303ebac
### percimp-557209f767da9af6
- event_id: percevt-350fe75d25d2fd7c
- event_type: desktop_ack
- source: desktop
- attention_class: medium
- attention_weight: 70
- gap_type: action_residue
- anomaly_kind: none
- internal_pressure: desktop_owner_response_or_request_state_should_update_strategy
- suggested_route: owner_response_feedback_and_intention_ecology
- future_effect: route_desktop_request_state_into_next_request_strategy
- evidence_ref: sha256:ff0487ac88b3dd18
### percimp-8c5647c76ae40f8e
- event_id: percevt-3aebc78ca4f61f3b
- event_type: qq_drop
- source: qq_gateway
- attention_class: high
- attention_weight: 100
- gap_type: repair_gap
- anomaly_kind: stale_or_dropped_visible_reply
- internal_pressure: visible_reply_order_or_delivery_needs_repair
- suggested_route: gate_repair_before_visible_send
- future_effect: prefer_latest_input_and_retraction_before_any_visible_reply
- evidence_ref: sha256:a4585c8c36f48b76
### percimp-c9db838b3d1e02dc
- event_id: percevt-14686809b8bb45e5
- event_type: owner_text_input
- source: qq
- attention_class: high
- attention_weight: 95
- gap_type: owner_attention
- anomaly_kind: none
- internal_pressure: current_turn_needs_attention_or_explained_hold
- suggested_route: attention_posture_and_intention_ecology
- future_effect: raise_current_turn_attention_and_require_short_term_anchor
- evidence_ref: sha256:6b0ccc3619b3ed79
### percimp-04c86412a4ea8f03
- event_id: percevt-17f9c158820676f7
- event_type: qq_ack
- source: qq_gateway
- attention_class: medium
- attention_weight: 50
- gap_type: action_residue
- anomaly_kind: none
- internal_pressure: visible_action_result_should_update_transport_confidence
- suggested_route: action_feedback_surface
- future_effect: confirm_or_adjust_visible_reply_transport_for_next_turn
- evidence_ref: sha256:bcc6ecd3c782790e
### percimp-50f47307b84d2682
- event_id: percevt-9452331996e2679c
- event_type: qq_ack
- source: qq
- attention_class: medium
- attention_weight: 45
- gap_type: action_residue
- anomaly_kind: none
- internal_pressure: visible_action_result_should_update_transport_confidence
- suggested_route: action_feedback_surface
- future_effect: confirm_or_adjust_visible_reply_transport_for_next_turn
- evidence_ref: actfb-e76a04518ee381cc
### percimp-ce9bc1ead5dbbfe1
- event_id: percevt-ba6de00fa205f656
- event_type: system_health_change
- source: runtime_probe
- attention_class: medium
- attention_weight: 50
- gap_type: maintenance_gap
- anomaly_kind: none
- internal_pressure: runtime_health_should_bound_future_action
- suggested_route: runtime_presence_and_action_gate
- future_effect: avoid_or_resume_actions_based_on_runtime_health
- evidence_ref: sha256:d7cfb7a77c53c857
### percimp-a28923e426ff296f
- event_id: percevt-3d4bf82ce10a181b
- event_type: qq_group_boundary
- source: qq_gateway
- attention_class: medium
- attention_weight: 65
- gap_type: boundary_gap
- anomaly_kind: none
- internal_pressure: non_private_or_group_event_requires_boundary
- suggested_route: boundary_gate
- future_effect: keep_group_or_non_owner_event_from_private_memory_and_unsanctioned_reply
- evidence_ref: sha256:7ebaa96bfca8d0ba
### percimp-4b30c2f628181ea6
- event_id: percevt-6530b06c16a947d6
- event_type: tool_execution_result
- source: local_tool
- attention_class: medium
- attention_weight: 50
- gap_type: action_residue
- anomaly_kind: none
- internal_pressure: tool_result_should_change_task_strategy
- suggested_route: action_feedback_coverage
- future_effect: adjust_next_tool_or_task_choice_from_result
- evidence_ref: sha256:79200d1d0ef4ee67
### percimp-68cd45057ae2cc29
- event_id: percevt-3228fb64b7862649
- event_type: tool_execution_result
- source: patch_executor
- attention_class: medium
- attention_weight: 50
- gap_type: action_residue
- anomaly_kind: none
- internal_pressure: tool_result_should_change_task_strategy
- suggested_route: action_feedback_coverage
- future_effect: adjust_next_tool_or_task_choice_from_result
- evidence_ref: sha256:a130da406f801f10
### percimp-57cd3e01f9f34a6c
- event_id: percevt-15866fed6fdee9cb
- event_type: system_health_change
- source: code_probe
- attention_class: medium
- attention_weight: 50
- gap_type: maintenance_gap
- anomaly_kind: none
- internal_pressure: runtime_health_should_bound_future_action
- suggested_route: runtime_presence_and_action_gate
- future_effect: avoid_or_resume_actions_based_on_runtime_health
- evidence_ref: sha256:fcbdc0c0f4cd62f8

## Privacy Boundary
- raw_private_body_retained: false
- visible_reply_text_retained: false
- private_text_in_report: false
- stable_memory_write: blocked

## Notes
- owner_input_creates_attention_pressure
- repair_gap_visible_from_perception
- boundary_gap_visible_from_perception
- action_result_residue_ready_for_feedback_loop
- maintenance_gap_visible_from_runtime_or_file_events
- visual_or_voice_sources_not_connected_yet
- perception_events_have_importance_judgments_and_internal_gap_routes
