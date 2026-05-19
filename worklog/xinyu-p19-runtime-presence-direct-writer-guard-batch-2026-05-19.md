# XinYu P19 Runtime Presence Direct Writer Guard Batch

Date: 2026-05-19
Workspace: `D:\XinYu`
Package: P19 `runtime-presence-direct-writer-guard`

## Goal

Reduce the highest-frequency `direct_writer_candidate` file without rewriting old runtime or memory data.

## Completed

- Updated `xinyu_runtime_presence.py`.
  - Directly emitted presence trace `observed_at` fields now pass through `_timestamp_or_now_iso(...)` at the emitted dict/return line.
  - Runtime presence markdown frontmatter keeps using `_timestamp_or_now_iso(...)` at the rendered `updated_at` line.
  - Existing stale-codex read behavior is preserved; old codex state timestamps are not normalized to "now" during reads.
- Updated `ops/validation/timestamp_writer_guard_audit.py`.
  - Adds function-scope detection for source audit classification.
  - Treats known default/read scopes as reference-only, not writer candidates.
- Updated `tests/test_timestamp_writer_guard_audit.py`.
  - Adds coverage for default/read timestamp maps inside writer-like files.

## Actual Result

- `xinyu_runtime_presence.py` direct writer candidates: `10 -> 0`
- Global post-P19 audit:
  - source_file_count: `469`
  - timestamp_writer_candidate_count: `709`
  - `guarded`: `144`
  - `direct_writer_candidate`: `87`
  - `template_timestamp_candidate`: `196`
  - `report_metadata_candidate`: `83`
  - `reference_only`: `102`
  - residual `unguarded_candidate`: `97`
  - `risky_literal_fallback`: `0`
- Generated post-P19 reports:
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p19-2026-05-19.md`
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p19-2026-05-19.json`

## Direct Impact

- Runtime presence trace and return metadata now have line-local timestamp guards.
- The audit no longer mistakes runtime presence default/read maps for writer output.
- The direct-writer queue is smaller and more precise for the next batch.

## Validation

- Focused pytest:
  - `tests/test_timestamp_writer_guard_audit.py`
  - `tests/test_runtime_program_awareness.py`
  - `tests/smoke/runtime/runtime_presence_smoke.py`
  - result: `13 passed`
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

- `direct_writer_candidate`: `87` remains across other modules.
- `template_timestamp_candidate`: `196` and `report_metadata_candidate`: `83` are intentionally untouched.
- residual `unguarded_candidate`: `97` still needs separate review.
- Existing old-data queues remain unchanged:
  - `invalid_timestamp_manual_review`: `174`
  - `human_memory_missing_event_time`: `225`

## Next

- Recommended next batch: P20 direct writer guard for the next small high-frequency group.
- Candidate group from post-P19: self-code approval / QQ outbox / review inbox.
- Keep the same rule: one file group, no old data rewrite, no template/report-metadata changes.
