# XinYu P65 Response Error Loop Batch - 2026-05-19

## Scope

Plan: `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md`

Batch: B / control theory feedback mapping.

Goal: add a tested response error loop provider that turns visible reply
failures into bounded next-turn correction policy. It classifies failure and
chooses a correction path; it does not generate replies, write stable memory, or
rewrite persona.

## Changes Completed

- Added `xinyu_response_error_loop.py`.
  - Defines `ResponseErrorLoopDecision`.
  - Classifies:
    - blank reply.
    - internal label/path/hash leak.
    - unsupported recall/history overclaim.
    - duplicate visible reply.
    - template reply mismatch.
    - style surface failure.
    - overexplained repair / empty promise.
    - task not executed.
    - stale context override.
    - relationship pressure misread as product feedback.
  - Consumes existing providers where available:
    - `evaluate_visible_reply_for_answer_discipline(...)`.
    - `dedupe_visible_reply(...)`.
    - `classify_visible_turn(...)`.
  - Renders a prompt block containing only metadata, not raw owner text.
- Added `tests/test_response_error_loop.py`.
  - Covers guard failures, unsupported recall, duplicate reply, style pressure,
    overexplained repair, task non-execution, no-error path, and prompt redaction.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_response_error_loop.py tests\test_response_error_loop.py`
  - pass
- Initial focused pytest had a command selection error:
  - `tests\test_visible_reply_guard.py` does not exist.
  - This was not a code failure.
- Corrected focused validation:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_response_error_loop.py tests\test_answer_discipline_trial.py tests\test_turn_triage_gate.py tests\test_visible_reply_guard_plugin.py -q`
  - 44 passed
- `git diff --check -- xinyu_response_error_loop.py tests\test_response_error_loop.py`
  - pass

Full suite and desktop build were not run because this batch adds a standalone
provider with focused coverage and no bridge injection yet.

## Direct Effect

- XinYu now has a control-theory inspired feedback loop:
  - observe visible failure.
  - classify error.
  - choose correction path.
  - bound memory/persona side effects.
- Repeated owner corrections no longer need to become ad hoc prompt patches.
- The loop explicitly says when no retry is needed.

## Remaining

- Decide runtime injection order with `xinyu_turn_triage_gate.py`.
- Batch D: implement memory immune gate.
- Batch E: implement slow state modulator.
- Batch F: implement module ecology audit.
- Later integration batch: add advisory prompt blocks to runtime context after
  enough standalone tests are stable.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Recently changed:

- `xinyu_response_error_loop.py`
- `tests/test_response_error_loop.py`

Recommended resume check:

`.\.venv\Scripts\python.exe -m pytest tests\test_response_error_loop.py tests\test_answer_discipline_trial.py tests\test_turn_triage_gate.py tests\test_visible_reply_guard_plugin.py -q`
