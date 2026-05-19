# XinYu P24 Custom Source Learning Direct Writer Guard Batch

Date: 2026-05-19
Workspace: `D:\XinYu`
Package: P24 `custom-source-learning-direct-writer-guard`

## Goal

Reduce direct timestamp writer candidates in custom learning/search/source engine modules without rewriting old memory/runtime data.

## Completed

- Updated `custom/github_autonomous_learning_engine.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Guarded candidate `last_seen_at`, rendered candidate timestamps, and external `checked_at`.
- Updated `custom/learning_quality_engine.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Guarded learning quality state frontmatter and source note timestamp replacements.
- Updated `custom/question_pipeline_engine.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Guarded question pipeline, question states, exploration queue, and source note timestamp writes.
- Updated `custom/source_comparison_engine.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Guarded source material frontmatter, comparison state, and question-state timestamp writes.
- Updated `custom/source_gate_engine.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Guarded source gate state and source note timestamp writes.
- Generated post-P24 reports:
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p24-2026-05-19.md`
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p24-2026-05-19.json`

## Actual Result

- Target group direct writer candidates: `7 -> 0`
- Global post-P24 audit:
  - source_file_count: `469`
  - timestamp_writer_candidate_count: `710`
  - `guarded`: `242`
  - `direct_writer_candidate`: `37`
  - `template_timestamp_candidate`: `173`
  - `report_metadata_candidate`: `79`
  - `reference_only`: `93`
  - residual `unguarded_candidate`: `86`
  - `risky_literal_fallback`: `0`

## Direct Impact

- Learning/search/source custom engines now normalize passed-in timestamps before writing state, notes, or candidate rows.
- Source learning sidecars are safer for later temporal reasoning because their emitted timestamps remain parseable ISO values.
- The remaining direct-writer queue is now mostly scattered runtime/core/source modules outside this custom source-learning group.

## Validation

- Focused validation:
  - `tests/test_timestamp_writer_guard_audit.py`
  - `tests/test_source_material_parser.py`
  - `py_compile` for all five edited custom engines
  - `tests/smoke/learning/github_autonomous_learning_smoke.py`
  - `tests/smoke/learning/integration/source_comparison_smoke.py --restore-after`
  - `tests/smoke/learning/integration/learning_quality_smoke.py --restore-after`
  - `tests/smoke/learning/integration/source_learning_chain_smoke.py --restore-after`
  - isolated temp-root smoke for `question_pipeline_engine` + `source_gate_engine`
  - result: passed
- Full app pytest:
  - `.venv\Scripts\python.exe -m pytest tests -q`
  - result: `574 passed`
- Quick smoke:
  - `.venv\Scripts\python.exe smoke_run.py --group quick --restore-after`
  - result: passed
- Diff check:
  - `git diff --check`
  - result: passed; LF/CRLF warnings only

## Recovery Note

- A first focused attempt ran `question_pipeline_smoke.py` without `--restore-after`, which wrote smoke fixtures into current memory files.
- Restored the affected smoke-state files from the before diff/known fixture state and cleaned one mojibake restoration artifact caught by `mojibake_guard_smoke`.
- Re-ran `mojibake_guard_smoke` and full quick smoke successfully.
- Going forward, mutation smokes must use `--restore-after` or an isolated temp root.

## Not Changed

- No old timestamp backfill was performed.
- No raw private memory bodies, raw QQ payload bodies, tokens, or secrets were printed.
- No git commit was made.

## Remaining Risks

- `direct_writer_candidate`: `37` remains across source/core/runtime modules.
- `template_timestamp_candidate`: `173`, `report_metadata_candidate`: `79`, and residual `unguarded_candidate`: `86` remain intentionally untouched in this batch.
- Existing old-data queues remain unchanged:
  - `invalid_timestamp_manual_review`: `174`
  - `human_memory_missing_event_time`: `225`

## Next

- Recommended next batch: P25 direct writer guard for runtime/service/bridge observation modules.
- Candidate group from post-P24:
  - `services/daily_digest.py`
  - `xinyu_bridge_observation.py`
  - `xinyu_code_awareness.py`
  - `xinyu_group_shadow_observer.py`
  - `xinyu_tinykernel_shadow.py`
- Keep the scope to one capability group and continue without rewriting old data.
