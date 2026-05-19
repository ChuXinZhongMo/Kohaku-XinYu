# XinYu P23 Initiative Proactivity Direct Writer Guard Batch

Date: 2026-05-19
Workspace: `D:\XinYu`
Package: P23 `initiative-proactivity-direct-writer-guard`

## Goal

Reduce direct timestamp writer candidates in the initiative, proactivity, uncertainty pause, and voice promotion runtime modules without rewriting old memory/runtime data.

## Completed

- Updated `xinyu_uncertainty_pause.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Guarded emitted state `updated_at` and trace `observed_at` fields.
- Updated `xinyu_voice_promotion_gate.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Guarded review state `created_at`, `updated_at`, and visible `evaluated_at`.
- Updated `xinyu_initiative_orchestrator.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Normalized external `checked_at` and `feedback_at` inputs before use.
  - Guarded lifecycle and feedback markdown timestamp fields.
- Updated `xinyu_initiative_research_shadow.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Guarded shadow report and seeded proactive request timestamp fields.
- Updated `xinyu_proactivity_scorer.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Normalized external `checked_at` inputs.
  - Guarded proactive decision state and trace timestamps.
- Updated `xinyu_proactive_request_loop.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Normalized external `evaluated_at` input.
  - Guarded proactive request state and trace `created_at` timestamps.
- Generated post-P23 reports:
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p23-2026-05-19.md`
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p23-2026-05-19.json`

## Actual Result

- Target group direct writer candidates: `13 -> 0`
- Global post-P23 audit:
  - source_file_count: `469`
  - timestamp_writer_candidate_count: `710`
  - `guarded`: `214`
  - `direct_writer_candidate`: `44`
  - `template_timestamp_candidate`: `193`
  - `report_metadata_candidate`: `79`
  - `reference_only`: `94`
  - residual `unguarded_candidate`: `86`
  - `risky_literal_fallback`: `0`

## Direct Impact

- Initiative/proactivity/voice runtime writers now treat passed-in timestamp strings as untrusted until parseable.
- The human-time recall direction is safer: emitted runtime markers are more consistently machine-parseable ISO times before later temporal reasoning uses them.
- The direct-writer queue is down to cross-cutting runtime/source/memory modules instead of this initiative group.

## Validation

- Focused pytest:
  - `tests/test_timestamp_writer_guard_audit.py`
  - `tests/test_initiative_orchestrator.py`
  - `tests/test_initiative_research_shadow.py`
  - `tests/test_proactive_contract.py`
  - `tests/smoke/initiative/proactivity_scorer_smoke.py`
  - `tests/smoke/initiative/proactive_request_loop_smoke.py`
  - `tests/smoke/voice/voice_calibration_promotion_smoke.py`
  - result: `37 passed`
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

- No memory, runtime, data, queue, trace, archive, creative, or dataset rows were rewritten.
- No timestamp backfill was performed.
- No raw private memory bodies, raw QQ payload bodies, tokens, or secrets were printed.
- No git commit was made.

## Remaining Risks

- `direct_writer_candidate`: `44` remains across source/custom/core/runtime modules.
- `template_timestamp_candidate`: `193`, `report_metadata_candidate`: `79`, and residual `unguarded_candidate`: `86` remain intentionally untouched in this batch.
- The audit still reports some `unguarded_candidate` rows in initiative-adjacent files; those are not direct emitted timestamp writers and need a separate classifier or writer-shape batch.
- Existing old-data queues remain unchanged:
  - `invalid_timestamp_manual_review`: `174`
  - `human_memory_missing_event_time`: `225`

## Next

- Recommended next batch: P24 direct writer guard for source/custom learning/search engine modules.
- Candidate group from post-P23:
  - `custom/github_autonomous_learning_engine.py`
  - `custom/learning_quality_engine.py`
  - `custom/question_pipeline_engine.py`
  - `custom/source_comparison_engine.py`
  - `custom/source_gate_engine.py`
- Keep the scope to one capability group and continue without rewriting old data.
