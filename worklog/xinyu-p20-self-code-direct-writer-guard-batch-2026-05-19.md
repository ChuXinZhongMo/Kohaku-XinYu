# XinYu P20 Self-Code Direct Writer Guard Batch

Date: 2026-05-19
Workspace: `D:\XinYu`
Package: P20 `self-code-direct-writer-guard`

## Goal

Reduce the next direct timestamp writer group inside the self-code approval/watchdog capability.

## Completed

- Updated `xinyu_self_code_approval.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - State `updated_at` and trace `observed_at` writes now guard externally supplied `observed_at` values at the emitted field line.
  - Approval decision, one-time permission semantics, owner-private boundary, and approval hash inputs are unchanged.
- Updated `xinyu_self_code_watchdog.py`.
  - Added `_timestamp_or_now_iso(...)`.
  - Snapshot manifest `created_at` and watchdog trace `observed_at` writes now guard externally supplied or generated timestamps at the emitted field line.
  - Snapshot/restore safety checks and manifest hash checks are unchanged.
- Generated post-P20 reports:
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p20-2026-05-19.md`
  - `worklog/xinyu-timestamp-writer-guard-audit-post-p20-2026-05-19.json`

## Actual Result

- self-code group direct writer candidates: `8 -> 0`
- Global post-P20 audit:
  - source_file_count: `469`
  - timestamp_writer_candidate_count: `709`
  - `guarded`: `152`
  - `direct_writer_candidate`: `79`
  - `template_timestamp_candidate`: `196`
  - `report_metadata_candidate`: `83`
  - `reference_only`: `102`
  - residual `unguarded_candidate`: `97`
  - `risky_literal_fallback`: `0`

## Direct Impact

- Self-code approval and watchdog state/trace writes no longer trust caller-supplied timestamp text blindly.
- The direct-writer queue continues shrinking without touching templates, reports, or old data.

## Validation

- Focused pytest:
  - `tests/test_timestamp_writer_guard_audit.py`
  - `tests/test_self_code_watchdog.py`
  - `tests/smoke/codex/self_code_approval_smoke.py`
  - `tests/smoke/codex/self_code_watchdog_smoke.py`
  - result: `10 passed`
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

- `direct_writer_candidate`: `79` remains across other modules.
- `template_timestamp_candidate`: `196`, `report_metadata_candidate`: `83`, and residual `unguarded_candidate`: `97` remain intentionally untouched.
- Existing old-data queues remain unchanged:
  - `invalid_timestamp_manual_review`: `174`
  - `human_memory_missing_event_time`: `225`

## Next

- Recommended next batch: P21 direct writer guard for user-facing queues/stores.
- Candidate group from post-P20: `xinyu_qq_outbox.py` and `xinyu_review_inbox.py`.
- Keep one capability group, no old data rewrite, no template/report-metadata changes.
