# XinYu P22 Goal Learning Direct Writer Guard Batch

Date: 2026-05-19
Workspace: `D:\XinYu`
Package: P22 `goal-learning-direct-writer-guard`

## Goal

Reduce direct timestamp writer candidates in goal ecology, self-choice, and learning state writers.

## Completed

- Updated `ops/validation/timestamp_writer_guard_audit.py`.
  - Recognizes local ISO helpers `_iso(...)` and `now_iso(...)` as guarded timestamp sources.
- Updated `xinyu_learning_library.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - OCR/extraction trace `recorded_at` and learning item metadata `created_at` now guard emitted timestamps at the field line.
- Updated `xinyu_learning_closed_loop.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Learning loop state/trace writes now guard emitted `updated_at` and `observed_at` fields at the field line.
- Updated `xinyu_self_chosen_goal_ecology.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Goal outcome state, trace, return metadata, and markdown frontmatter now guard emitted timestamps at the field line.
- `xinyu_self_choice_store.py` needed no code change; its existing `_iso(...)` helper is now recognized by the audit.
- Generated post-P22 reports:
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p22-2026-05-19.md`
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p22-2026-05-19.json`

## Actual Result

- Target group direct writer candidates: `12 -> 0`
- Global post-P22 audit:
  - source_file_count: `469`
  - timestamp_writer_candidate_count: `710`
  - `guarded`: `198`
  - `direct_writer_candidate`: `57`
  - `template_timestamp_candidate`: `195`
  - `report_metadata_candidate`: `80`
  - `reference_only`: `94`
  - residual `unguarded_candidate`: `86`
  - `risky_literal_fallback`: `0`

## Direct Impact

- Learning and goal runtime state writers now treat external or propagated timestamp text as untrusted until normalized.
- Existing self-choice ISO helper usage is represented correctly in the audit.
- The direct-writer queue is down to smaller scattered modules.

## Validation

- Focused pytest:
  - `tests/test_timestamp_writer_guard_audit.py`
  - `tests/test_learning_closed_loop.py`
  - `tests/test_self_chosen_goal_ecology.py`
  - `tests/test_goal_outcome_observer.py`
  - `tests/test_learning_library_quality.py`
  - `tests/smoke/learning/learning_library_smoke.py`
  - `tests/smoke/life/xinyu_self_choice_store_smoke.py`
  - `tests/smoke/initiative/self_chosen_goal_ecology_smoke.py`
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

- `direct_writer_candidate`: `57` remains across smaller modules.
- `template_timestamp_candidate`: `195`, `report_metadata_candidate`: `80`, and residual `unguarded_candidate`: `86` remain intentionally untouched.
- Existing old-data queues remain unchanged:
  - `invalid_timestamp_manual_review`: `174`
  - `human_memory_missing_event_time`: `225`

## Next

- Recommended next batch: P23 direct writer guard for initiative/proactivity/voice runtime modules.
- Candidate group from post-P22: uncertainty pause, proactivity scorer, proactive request loop, initiative orchestrator/research shadow, voice promotion gate, turn coherence.
- Keep one capability group and continue without rewriting old data.
