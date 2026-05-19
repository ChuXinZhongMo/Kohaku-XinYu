# XinYu P04 Adapter Event Time Bridge Batch

Date: 2026-05-18
Workspace: `D:\XinYu`
Package: P04 `adapters-bridges-io`

## Goal

Carry real adapter message time into the canonical temporal recall path so time-aware memory does not depend only on local machine `now()`.

## Completed

- Confirmed QQ gateway chat payloads already send top-level `timestamp` from OneBot `event.time`.
- Confirmed Desktop shell chat payloads already send top-level `timestamp`.
- Added shared bridge payload event-time helpers in `xinyu_bridge_state_text.py`:
  - accepts top-level `event_time`, `recorded_at`, `created_at`, `timestamp`, `time`
  - accepts metadata fallback fields including `qq_event_time_iso` and `desktop_event_time_iso`
  - supports ISO strings, Unix seconds, and Unix milliseconds
- Updated `xinyu_core_bridge.py` chat flow:
  - uses payload event time as canonical recall `evaluated_at`
  - uses payload event timestamp for user input event `received_at`
  - records user dialogue tail with the adapter event time
  - records assistant dialogue tail with actual assistant reply time
- Added tests for:
  - top-level timestamp beating metadata fallback
  - ISO metadata fallback
  - millisecond timestamp coercion
  - core bridge dialogue tail using payload time for user turn

## Direct Impact

- A message recorded at `2026-05-18T13:30:00+08:00` is now treated as that event time by recall, even if the bridge processes it later.
- The nap/wake temporal logic from P03 can reason over the real user turn time instead of the bridge runtime clock.
- Dialogue tail keeps human sequence clearer: user message time means "when owner sent it"; assistant time means "when XinYu answered".

## Validation

- Syntax:
  - `.venv\Scripts\python.exe -m py_compile xinyu_bridge_state_text.py xinyu_core_bridge.py tests\test_bridge_state_text.py`
  - result: passed
- Focused pytest:
  - `tests/test_bridge_state_text.py`
  - result: `7 passed`
- P03/P04 focused regression:
  - `tests/test_bridge_session.py`
  - `tests/test_living_memory_recall.py`
  - `tests/test_temporal_memory_context.py`
  - `tests/test_context_retrieval_owner_scenarios.py`
  - result: `19 passed`
- Full app pytest:
  - `.venv\Scripts\python.exe -m pytest tests -q`
  - result: `549 passed`
- Quick smoke:
  - `.venv\Scripts\python.exe smoke_run.py --group quick --restore-after`
  - result: passed
- Diff check:
  - `git diff --check`
  - result: passed; CRLF warnings only

## Not Changed

- No Desktop TypeScript code was edited; desktop already supplies `timestamp`.
- No QQ gateway code was edited; QQ chat payload already supplies `timestamp`.
- No private memory bodies, raw QQ payload bodies, tokens, or secrets were printed.
- No git commit was made.

## Remaining Risks

- Sticker delivery tail still records assistant-side delivery time only. This is acceptable for P04 because it is not the canonical user recall input path.
- Coalesced QQ messages still collapse several fragments into one payload; timestamp currently follows the prepared payload used by the coalesced message. If finer fragment timing becomes important, add fragment-level event-time metadata later.

## Next

- Resume at the next unfinished DoD item outside P04.
- Recommended next batch: P05 recall write-path/time provenance audit, checking whether memory writes preserve event time when new memory candidates are saved.
