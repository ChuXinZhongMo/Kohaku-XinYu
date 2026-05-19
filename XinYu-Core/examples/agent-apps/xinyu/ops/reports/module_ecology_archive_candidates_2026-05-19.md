# XinYu Module Ecology Audit

Generated from module paths and source/doc references only.
It does not read or print memory, runtime, QQ payload, library, cases, or data bodies.

- item_count: 135
- kept: 0
- merged: 0
- archived: 135
- deleted: 0

## Bucket Counts

- core: 11
- lab: 105
- ops: 19

## Decision Counts

- archive_candidate_lab_stale: 105
- archive_candidate_no_live_refs: 30

## Lifecycle Summary

- kept: active modules with live references or tests stay in place.
- merged: duplicate/shim modules stay as compatibility entrances until callers move.
- archived: stale lab or unreferenced active-bucket modules need archive-before-delete review.
- deleted: worktree deletions remain candidates until archive/delete reference audit passes.

## Remaining Risks

- archive candidates are advisory until owners confirm they are not active runtime niches

## Items

- `ACTION-LAYER-V1.md` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `DIALOGUE-OBSERVATION-WORKFLOW.md` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `EXECUTION-ORDER.md` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `NAMING-CONVENTIONS.md` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `PUBLIC-DATA-REPLAY.md` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `XINYU-DIRECTION.md` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `XINYU-SYSTEM-DIAGRAMS.md` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `XINYU-SYSTEM-UTILIZATION-AUDIT.md` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `codex-qq-20260506T160933/codex-qq-20260506T160933-report.md` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `context/desktop_thoughts_state.md` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `emotions/stickers/manifest.example.json` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `learning/owner_supplied/20260506T192719+0800_codex-qq-20260506T191818-report.md_14a7a340/codex-qq-20260506T191818-report.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/owner_supplied/20260506T193342+0800_codex-qq-20260506T192321-report.md_8ae8715b/codex-qq-20260506T192321-report.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/DATA/KNOWLEDGEBASE/finance_data_converted.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/DATA/email_schema.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/DATA/msg.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/DATA/phone_details.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/DATA/tools.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/BRAIN/RAG.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/BRAIN/chat_with_ai.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/BRAIN/code_gen.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/BRAIN/gem_func_call.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/BRAIN/local_func_call.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/BRAIN/text_to_info.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/CONVERSATION/speech_to_text.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/CONVERSATION/t_s.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/CONVERSATION/test_speech.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/CONVERSATION/text_speech.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/CONVERSATION/text_to_speech.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/Email_send.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/app_op.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/get_env.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/greet_time.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/incog.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/internet_search.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/link_op.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/phone_call.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/random_respon.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/searxsearch.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/Tools/youtube_downloader.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/FUNCTION/run_function.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/KEYBOARD/key_lst.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/KEYBOARD/key_prs_lst.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/VISION/gem_eye.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/src/VISION/local_eye.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8/selected_files/ui.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `ops/manual/manual_archive_commit.py` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `ops/manual/manual_archive_output.py` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `ops/manual/manual_consolidation.py` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `ops/manual/manual_maintenance_recommendation.py` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `ops/manual/manual_retention_gate.py` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `ops/manual/manual_source_integration_gate.py` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `ops/manual/manual_source_reliability.py` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `project-plans/XINYU-ANSWER-DISCIPLINE-CALIBRATION-PLAN.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-CLOSEOUT-AUTORUN-PLAN-2026-05-13.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-CLOSEOUT-COMMIT-BOUNDARY-2026-05-14.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-CODEX-HANDOFF-2026-05-05.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-CONVERSATION-EXPERIENCE-CASE-LIBRARY-PLAN.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-DIALOGUE-DATASET-SELECTION-AND-EXPERIENCE-LIBRARY-PLAN-2026-05-14.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-EMOTION-COUNCIL-PLAN.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-INNER-INTENTION-TO-PROACTIVE-SYSTEM-DESIGN.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-INTRA-INSPIRED-RETRIEVAL-V2-PLAN-2026-05-15.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-LIFE-KERNEL-PLAN.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-OWNER-PRIVATE-NEGATIVE-EXPRESSION-AUDIT-2026-05-14.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-PROACTIVE-CONCRETE-REQUEST-LOOP-PLAN.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-PROACTIVITY-SCORER-SHADOW-PLAN.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-SELF-CHOICE-STORE-PLAN.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/XINYU-SELF-THOUGHT-IDLE-LOOP-PLAN.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `project-plans/未完成事项-QQ接回后续接计划.md` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_bootstrap_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_cli_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_codex_aliases_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_context_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_debug_prompt_dump_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_desktop_actions_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_desktop_projection_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_desktop_service_aliases_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_desktop_state_text_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_errors_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_learning_sidecars_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_loop_thread_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_memory_snapshot_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_null_input_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_payload_attachment_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_payload_policy_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_promises_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_recent_sticker_reply_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_reply_bubbles_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_reply_text_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_session_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_state_text_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/bridge/bridge_trusted_search_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/codex/xinyu_tool_artifact_hygiene_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/desktop/xinyu_desktop_events_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/desktop/xinyu_desktop_ws_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/dialogue/group_shadow_state_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/initiative/automation_bridge_live_turn_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/initiative/autonomous_state_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/initiative/impulse_soup_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/initiative/proactivity_scorer_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/initiative/xinyu_tinykernel_shadow_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/life/dream_journal_export_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/integration/qq_recent_sticker_state_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_attachment_material_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_cli_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_config_helpers_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_core_client_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_forward_context_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_gateway_constants_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_gateway_utils_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_models_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_normalizer_aliases_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_rich_context_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_sticker_semantics_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_trust_aliases_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_trust_config_persistence_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/qq_trust_policy_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/xinyu_qq_config_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/qq/xinyu_qq_server_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/runtime/runtime_failure_freshness_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/voice/xinyu_visible_state_hygiene_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tests/smoke/voice/xinyu_visible_text_sanitizer_smoke.py` | bucket=lab | niche=shadow_experiment_or_test_asset | decision=archive_candidate_lab_stale | refs=0 | tests=0
- `tools/structure_inventory.py` | bucket=ops | niche=operator_validation_or_docs | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_sticker_reference_index.py` | bucket=core | niche=live_turn_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_v1/cli/inspect_memory.py` | bucket=core | niche=memory_or_recall_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_v1/cli/migrate_memory.py` | bucket=core | niche=memory_or_recall_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_v1/gateway/maintenance_gateway.py` | bucket=core | niche=live_turn_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_v1/integrations/legacy_custom_engines.py` | bucket=core | niche=live_turn_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_v1/integrations/napcat_contract.py` | bucket=core | niche=live_turn_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_v1/memory/chroma_store.py` | bucket=core | niche=live_turn_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_v1/memory/qdrant_store.py` | bucket=core | niche=live_turn_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_v1/observability/audit_log.py` | bucket=core | niche=live_turn_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_v1/reasoning/conflict_resolver.py` | bucket=core | niche=live_turn_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
- `xinyu_v1/storage/sqlite_meta.py` | bucket=core | niche=live_turn_core | decision=archive_candidate_no_live_refs | refs=0 | tests=0
