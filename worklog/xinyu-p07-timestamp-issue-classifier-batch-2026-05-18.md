# XinYu P07 Timestamp Issue Classifier Batch

Date: 2026-05-18
Workspace: `D:\XinYu`
Package: P07 `ops-validation-memory-time-classifier`

## Goal

Classify P06 timestamp audit issues before any old-memory backfill or cleanup.

## Completed

- Added `ops/validation/timestamp_issue_classifier.py`.
- Added `tests/test_timestamp_issue_classifier.py`.
- Updated `ops/validation/timestamp_provenance_audit.py` with `--issue-limit` so the classifier can process all issue records, not only the first review sample.
- Regenerated full issue reports:
  - `worklog/xinyu-timestamp-provenance-audit-2026-05-18.md`
  - `worklog/xinyu-timestamp-provenance-audit-2026-05-18.json`
  - issue_limit: `10000`
- Generated classifier reports:
  - `worklog/xinyu-timestamp-issue-classifier-2026-05-18.md`
  - `worklog/xinyu-timestamp-issue-classifier-2026-05-18.json`

## Actual Classifier Summary

- status: `hold`
- classified_issue_count: `2220`
- class_counts:
  - `operational_timestamp_not_human_memory`: `1805`
  - `human_memory_missing_event_time`: `225`
  - `invalid_timestamp_manual_review`: `174`
  - `safe_index_or_docs_no_backfill_needed`: `12`
  - `metadata_timestamp_review`: `4`

## Direct Impact

- Most timestamp issues are now separated from human-memory backfill.
- The risky set is smaller:
  - 225 likely human-memory rows/files missing event time
  - 174 invalid timestamp records needing manual review
- We should not bulk backfill everything. Operational/runtime rows should not be treated as lived memory.

## Validation

- Syntax:
  - `.venv\Scripts\python.exe -m py_compile ops\validation\timestamp_issue_classifier.py tests\test_timestamp_issue_classifier.py`
  - result: passed
- Focused pytest:
  - `tests/test_timestamp_issue_classifier.py`
  - `tests/test_timestamp_provenance_audit.py`
  - result: `4 passed`
- Full app pytest:
  - `.venv\Scripts\python.exe -m pytest tests -q`
  - result: `554 passed`
- Quick smoke:
  - `.venv\Scripts\python.exe smoke_run.py --group quick --restore-after`
  - result: passed
- Diff check:
  - `git diff --check`
  - result: passed; CRLF warnings only

## Not Changed

- No old data was rewritten.
- No timestamp backfill was performed.
- The classifier reads only the P06 metadata-only JSON report.
- No private memory bodies, raw QQ payload bodies, tokens, timestamp values, or secrets were printed.
- No git commit was made.

## Remaining Risks

- Classification is path/zone/count based. It intentionally avoids reading bodies, so some `human_memory_missing_event_time` items may become safe after manual schema review.
- The `invalid_timestamp_manual_review` class needs a dedicated safe review rule before any edit.

## Next

- Recommended next batch: P08 safe remediation queue.
- Create a non-destructive review queue for only:
  - `human_memory_missing_event_time`
  - `invalid_timestamp_manual_review`
  - `metadata_timestamp_review`
- The queue should include paths and issue classes only, not bodies or timestamp values.
- Do not auto-backfill yet.
