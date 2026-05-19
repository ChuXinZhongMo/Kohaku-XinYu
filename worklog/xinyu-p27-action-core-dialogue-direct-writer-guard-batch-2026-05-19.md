# XinYu P27 Action Core Dialogue Direct Writer Guard Batch

Date: 2026-05-19
Workspace: `D:\XinYu`
Package: P27 `action-core-dialogue-direct-writer-guard`

## Goal

Reduce direct timestamp writer candidates in action digest, core bridge, dialogue overlay, and expression self-learning modules without rewriting old memory/runtime data.

## Completed

- Updated `xinyu_action_experience_digest.py`.
  - Added `_timestamp_or_now_iso(...)` with ISO parsing fallback.
  - Normalized digest `produced_at`.
  - Guarded digest state `updated_at`, last digest `produced_at`, and trace `created_at`.
- Updated `xinyu_core_bridge.py`.
  - Added a bridge-local `_timestamp_or_now_iso(...)`.
  - Guarded external plugin trace `observed_at`.
  - Guarded proactive request `updated_at` replacement.
- Updated `xinyu_dialogue_rule_trial_overlay.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Normalized overlay activation time.
  - Guarded overlay `activated_at`, `updated_at`, and `last_applied_at`.
- Updated `xinyu_expression_self_learning.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Normalized expression-learning `observed_at` and source-request creation time.
  - Guarded state `updated_at`/`observed_at` and trace `observed_at`.
- Generated post-P27 reports:
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p27-2026-05-19.md`
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p27-2026-05-19.json`

## Actual Result

- Target group direct writer candidates: `5 -> 0`
- Global direct writer candidates: `23 -> 18`
- Global post-P27 audit:
  - source_file_count: `469`
  - timestamp_writer_candidate_count: `710`
  - `guarded`: `287`
  - `direct_writer_candidate`: `18`
  - `template_timestamp_candidate`: `167`
  - `report_metadata_candidate`: `75`
  - `reference_only`: `84`
  - residual `unguarded_candidate`: `85`
  - `risky_literal_fallback`: `0`

## Direct Impact

- Action residue digestion now keeps produced/created timestamps parseable before state and trace writes.
- Core bridge trace/state replacements no longer write raw intermediate time strings directly.
- Short-term dialogue rule overlays now normalize activation/application/clear times.
- Expression self-learning state, trace, and source-request bridge now reject malformed observed times.

## Validation

- Focused pytest:
  - `tests/test_timestamp_writer_guard_audit.py`
  - `tests/test_expression_self_learning.py`
  - `tests/test_dialogue_curiosity_bridge_injection.py`
  - `tests/test_bridge_state_text.py`
  - `tests/test_bridge_external_plugin_routes.py`
  - result: `87 passed`
- Focused smokes:
  - `tests/smoke/life/xinyu_action_experience_digest_smoke.py`: passed
  - `tests/smoke/dialogue/xinyu_dialogue_rule_trial_overlay_smoke.py`: passed
  - `tests/smoke/initiative/proactive_feedback_spine_smoke.py`: passed
  - `tests/smoke/tools/xinyu_external_plugins_smoke.py`: passed
- Full app pytest:
  - `.venv\Scripts\python.exe -m pytest tests -q`
  - result: `574 passed`
- Quick smoke:
  - `.venv\Scripts\python.exe smoke_run.py --group quick --restore-after`
  - result: passed
- Diff check:
  - `git diff --check`
  - result: passed; LF/CRLF warnings only

## Not Changed

- No old timestamp backfill was performed.
- No raw private memory bodies, raw QQ payload bodies, tokens, or secrets were printed intentionally.
- No git commit was made.

## Remaining Direct Writer Candidates

- `learning/self_found/.../selected_files/src/BRAIN/chat_with_ai.py:88` `timestamp`
- `xinyu_creative_writing.py:1080` `updated_at`
- `xinyu_goal_outcome_observer.py:121` `observed_at`
- `xinyu_goal_outcome_observer.py:499` `updated_at`
- `xinyu_impulse_soup.py:682` `updated_at`
- `xinyu_initiative_spine.py:183` `updated_at`
- `xinyu_memory_braid.py:184` `updated_at`
- `xinyu_memory_event_sourcing.py:157` `timestamp`
- `xinyu_qq_gateway.py:1656` `updated_at`
- `xinyu_self_action_gateway.py:860` `updated_at`
- `xinyu_self_action_patch_executor.py:243` `created_at`
- `xinyu_sent_reply_index.py:200` `last_seen_at`
- `xinyu_sent_reply_index.py:209` `updated_at`
- `xinyu_sticker_import.py:876` `updated_at`
- `xinyu_turn_coherence.py:243` `updated_at`
- `xinyu_turn_coherence.py:286` `observed_at`
- `xinyu_v1/emotion/persistence.py:56` `updated_at`
- `xinyu_voice_learning.py:176` `updated_at`

## Remaining Risks

- `direct_writer_candidate`: `18` remains across goal/initiative/memory/QQ/self-action/sticker/voice modules and one external self-found learning sample.
- `personality_continuity_smoke` remains externally blocked by current LLM 429 quota exhaustion from P26 diagnostics.
- Existing old-data queues remain unchanged:
  - `invalid_timestamp_manual_review`: `174`
  - `human_memory_missing_event_time`: `225`

## Next

- Recommended next batch: P28 goal/initiative/memory/turn direct writer guard.
- Candidate group:
  - `xinyu_goal_outcome_observer.py`
  - `xinyu_impulse_soup.py`
  - `xinyu_initiative_spine.py`
  - `xinyu_memory_braid.py`
  - `xinyu_memory_event_sourcing.py`
  - `xinyu_turn_coherence.py`
- Continue with reconnaissance first, then minimal timestamp guard edits, focused tests, full validation, and worklog update.
