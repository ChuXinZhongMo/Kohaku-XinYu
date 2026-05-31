# XinYu Feedback Consumption Diagnostics

- generated_at: 2026-05-29T16:45:49+08:00
- status: pass
- result: pass
- trace_limit: 200
- claim_boundary: rolling feedback-consumption audit only; does not claim consciousness

## Metrics
- sample_count: 114
- feedback_source_count: 114
- feedback_required_count: 114
- legacy_uninstrumented_count: 0
- consumed_count: 114
- partial_count: 0
- missing_count: 0
- consumption_rate_pct: 100.0
- pass_rate_pct: 80.0
- consumed_streak: 114
- missing_streak: 0
- stage7_closure_min_samples: 3

## Stage 7 Closure Gate
- status: ready
- ready_for_stage8: true
- reason: feedback_consumption_rate_and_streak_satisfy_stage7_gate
- required_samples: 3
- auditable_samples: 114
- consumed_streak: 114
- consumption_rate_pct: 100.0
- next_step: stage8_memory_governance_can_start

## Latest Sample
- source: latest_decision_chain
- checked_at: 2026-05-29T08:45:49.140746+00:00
- ecology_id: decision_chain_latest
- status: consumed
- sources: action_feedback:qq_visible_reply_ack,action_feedback_coverage:runtime_probe_turn_active,owner_feedback_effect:owner_reported_template_voice_failure
- biases: <omitted_long_value:sha256:1b1c0988963c0fbc>
- future_effect: action_feedback_future:confirm_visible_reply_transport_for_next_turn,owner_feedback_future:style_repair_direct_only_ordinary_chat_keeps_current_anchor

## Privacy Boundary
- raw_owner_text_in_report: false
- visible_reply_text_in_report: false
- state_contains_status_counts_refs_only: true
- stable_memory_write: blocked
- consciousness_claim: false

## Notes
- recent_auditable_feedback_sources_are_consumed
- stage7_closure:ready
