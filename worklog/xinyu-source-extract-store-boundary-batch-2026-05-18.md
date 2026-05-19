# XinYu Source Extract Store Boundary Batch

Date: 2026-05-18
Plan: `plan-next-6.md`
Batch: 1 - Source Extract Boundary

## Completed

- Added `stores/source_extracts.py` as the explicit compatibility boundary for `memory/creative/planning/inspiration/safe_extracts.jsonl`.
- Kept the legacy physical path through `SOURCE_EXTRACTS_REL` and `REFERENCE_EXTRACTS_REL`.
- Updated `xinyu_creative_writing.py` to write safe extract JSONL through `write_source_extracts`.
- Updated P0 triage so `safe_extracts.jsonl` is classified as `compat_source_extract_store_exists` with target `stores/source_extracts`.
- Added focused coverage in `tests/test_source_extracts_store.py`.
- Updated `stores/README.md`.

## Validation

- `python -m py_compile stores\source_extracts.py xinyu_creative_writing.py tests\test_source_extracts_store.py`: passed.
- `python -m pytest tests\test_source_extracts_store.py tests\test_memory_structured_p0_triage.py tests\test_creative_writing.py -q`: `16 passed`.
- Refreshed P0 triage:
  - `worklog/xinyu-memory-structured-p0-triage-post-source-extract-store-2026-05-18.md`
  - `worklog/xinyu-memory-structured-p0-triage-post-source-extract-store-2026-05-18.json`

## Not Completed

- `memory/context/impulse_soup_trace.jsonl` still reports `archive_candidate_after_caller_update`.
- `memory/context/qq_outbox_queue.json` remains a high-risk producer/consumer queue and is not safe for autonomous migration.
- No raw JSONL bodies were read, printed, or migrated.

## Next Step

Proceed to Batch 2: define a metadata-only runtime trace boundary for `impulse_soup_trace.jsonl`, update triage, add focused tests, and refresh reports.
