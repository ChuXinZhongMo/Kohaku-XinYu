# XinYu Stage 8 Learning Trial Validation Packet

- generated_at: 2026-05-31T19:58:56+08:00
- packet_status: satisfied
- mode: read_only_learning_trial_validation_packet
- raw_owner_text: hidden
- visible_reply_text: hidden
- stable_profile_write: blocked

## Owner Review Decision
- blocked_key: memory_mechanics_leak
- owner_action: owner_explicit_apply_required_no_auto_promotion
- source: runtime_learning_closed_loop_trial:memory_mechanics_leak (origin=explicit_success, repair_observations=106, raw_owner_text_excluded)
- reason: gate_satisfied: 2 consecutive same-trial explicit owner success captured; awaiting explicit owner apply, not auto-promoted
- boundary: runtime_trial_bias_only, stable_profile_write:blocked, owner_memory_write:blocked_owner_review_required, no_auto_promotion_to_stable_memory, raw_owner_text_hidden_counts_and_keys_only
- required_success_signal: required=2, still_needed=0, must_match_active_trial_key=memory_mechanics_leak, valid_scope=owner_private_chat_after_an_actual_xinyu_visible_reply
- rollback_path: no_stable_memory_written_yet:nothing_to_revert_at_stable_layer; single_owner_repair_or_cancel_resets_trial_success_streak_to_zero; trial_bias_is_runtime_only:clearing_learning_closed_loop_state_removes_it; any_future_stable_apply_is_a_separate_explicit_owner_action_reversible_by_removing_the_written_line

## Gate
- learning_trial_success_gate: satisfied
- required_consecutive_success_count: 2
- needed_consecutive_success_count: 0
- success_must_match_active_trial_key: true

## Current Trial
- status: trial_supported
- latest_failure_kind: memory_mechanics_leak
- active_trial_key: memory_mechanics_leak
- active_trial_habit: 需要记忆时先接住对话，只说记得/不确定/想确认什么，不念文件和状态卡。
- expected_next_behavior: 需要记忆时先接住对话，只说记得/不确定/想确认什么，不念文件和状态卡。
- repair_count: 106
- trial_success_count: 2
- trial_success_streak: 2
- latest_success_trial_key: memory_mechanics_leak
- success_evidence_status: same_trial_explicit_owner_success
- last_owner_reaction: explicit_success

## Blockers
- none

## Latest Trace Summary
- event_id: learnloop-6e3a7ebe7aab6481b2
- owner_private: true
- success: true
- failure_count: 0
- active_trial_key: memory_mechanics_leak
- success_evidence_status: same_trial_explicit_owner_success

## Success Capture Contract
- valid_scope: owner_private_chat_after_xinyu_visible_reply
- accepted_success_marker_examples: 自然多了, 像人了, 像你了, 这句可以, 这样可以, 这次可以, 这次修复有效, 修复有效, 改对了, 改好了, 接住了, 没模板味了, 不机械了, 没gpt味了
- style_trial_success_examples: 没模板味了, 没有模板味了, 不模板了, 不再模板, 模板味少了, 不像客服了, 不机械了, 没AI味了, 没gpt味了, 修复有效, 改对了, 改好了
- generic_success_requires_reply_context_markers: 这句, 这次, 这样, 刚才, 现在, 回复, 说法, 语气, 自然, 接住
- cancel_markers_that_turn_success_into_failure: 但是, 但还是, 不过, 然而, 仍然, 依旧, 还有点, 还是有, 还不行, 没改, 没变化, 不行
- mixed_feedback_policy: success_words_plus_cancel_marker_is_failure

## Boundaries
- candidate_body_in_packet: false
- candidate_status_changed: false
- consciousness_claim: false
- qq_message_enqueued: false
- raw_owner_text_in_packet: false
- stable_identity_profile_apply: blocked
- stable_memory_write: blocked
- visible_reply_text_in_packet: false

## Next Actions
- do_not_promote_stable_profile_yet
- wait_for_real_owner_private_feedback_after_actual_reply
- count_only_same_trial_explicit_success
- rerun_memory_health_after_two_consecutive_successes
