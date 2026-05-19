# XinYu P05 Memory Event Time Provenance Batch

Date: 2026-05-18
Workspace: `D:\XinYu`
Package: P05 `stores-services-memory-write-path`

## Goal

Preserve adapter event time when the live turn writes archive rows, memory candidates, and temporal traces.

## Completed

- Reused the shared payload event-time parser in `xinyu_dialogue_archive.py`.
- Updated dialogue archive user-message `created_at` to accept the same event-time sources as recall:
  - top-level `event_time`, `recorded_at`, `created_at`, `timestamp`, `time`
  - metadata fallback fields including `qq_event_time_iso` and `desktop_event_time_iso`
  - seconds and milliseconds timestamps
- Updated `xinyu_memory_candidate_extractor.py` so memory candidates use payload event time for `created_at`.
- Updated temporal traces created from memory candidates so both `created_at` and `updated_at` use the same payload event time.
- Added `tests/test_memory_event_time_provenance.py` to prove one event timestamp reaches:
  - dialogue archive user row
  - `memory_candidates.created_at`
  - `temporal_traces.created_at`
  - `temporal_traces.updated_at`

## Direct Impact

- Stored memory evidence now says when the user message happened, not merely when the bridge processed it.
- Later recall can reason from real sequence: if owner slept at 12:30 and woke at 13:30, the stored evidence keeps those times.
- P03 temporal context and P04 adapter time are now connected through both read and write paths.

## Validation

- Syntax:
  - `.venv\Scripts\python.exe -m py_compile xinyu_dialogue_archive.py xinyu_memory_candidate_extractor.py tests\test_memory_event_time_provenance.py`
  - result: passed
- Focused pytest:
  - `tests/test_memory_event_time_provenance.py`
  - `tests/test_bridge_state_text.py`
  - `tests/test_context_retrieval_owner_scenarios.py`
  - `tests/test_dialogue_semantic_backend.py`
  - `tests/test_living_memory_recall.py`
  - `tests/test_temporal_memory_context.py`
  - result: `25 passed`
- Focused smokes:
  - `tests/smoke/dialogue/temporal_trace_smoke.py --restore-after`
  - `tests/smoke/dialogue/dialogue_archive_smoke.py --restore-after`
  - `tests/smoke/dialogue/dialogue_semantic_retrieval_smoke.py --restore-after`
  - result: passed
- Full app pytest:
  - `.venv\Scripts\python.exe -m pytest tests -q`
  - result: `550 passed`
- Quick smoke:
  - `.venv\Scripts\python.exe smoke_run.py --group quick --restore-after`
  - result: passed
- Diff check:
  - `git diff --check`
  - result: passed; CRLF warnings only

## Not Changed

- Assistant archive rows still use assistant reply time. This is intentional: user rows represent user event time; assistant rows represent response time.
- No stable memory file was directly rewritten.
- No private memory bodies, raw QQ payload bodies, tokens, or secrets were printed.
- No git commit was made.

## Remaining Risks

- Older memory rows that were already written before this batch keep their original timestamps.
- Some non-live maintenance or action-event stores still use their own operational timestamps. That is acceptable unless they later feed human-time recall as lived user memories.

## Next

- Recommended next batch: P06 old-memory timestamp backfill/audit plan.
- Do not rewrite private memory bodies automatically; first build a metadata-only audit that counts missing/invalid timestamps without printing contents.
