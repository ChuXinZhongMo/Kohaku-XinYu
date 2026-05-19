# XinYu P67 Slow State Modulator Batch - 2026-05-19

## Scope

Plan: `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md`

Batch: E / allostasis and slow-variable mapping.

Goal: add a small slow-state modulator so fatigue, relationship guard,
correction pressure, and initiative dampening can persist briefly and decay by
time. The modulator biases reply pacing, initiative, recall, and emotion policy;
it cannot create facts, override the current owner turn, or write stable memory.

## Changes Completed

- Added `xinyu_slow_state_modulator.py`.
  - Defines `SlowState`.
  - Persists optional state at `memory/context/slow_state_modulator_state.json`.
  - Reads previous state and applies half-life decay:
    - fatigue: 2.5h
    - relationship guard: 8h
    - correction pressure: 4h
    - initiative dampening: 6h
  - Consumes advisory inputs:
    - Scene Frame.
    - turn triage decision.
    - response error loop decision.
    - turn residue.
  - Outputs:
    - reply policy.
    - initiative policy.
    - recall policy.
    - emotion policy.
  - Renders metadata only, not raw owner text.
- Added `tests/test_slow_state_modulator.py`.
  - Covers night-shift fatigue and persistence.
  - Covers decay over elapsed time.
  - Covers style-error correction pressure.
  - Covers relationship guard.
  - Covers turn residue consumption.
  - Covers prompt redaction.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_slow_state_modulator.py tests\test_slow_state_modulator.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_slow_state_modulator.py tests\test_scene_frame.py tests\test_life_reply_policy_scene_frame.py tests\test_turn_triage_gate.py tests\test_response_error_loop.py -q`
  - 33 passed
- `git diff --check -- xinyu_slow_state_modulator.py tests\test_slow_state_modulator.py`
  - pass

Full suite and desktop build were not run because this batch adds a focused
provider/store and no bridge injection yet.

## Direct Effect

- XinYu can now carry short-lived fatigue/correction/relation pressure instead
  of resetting every turn.
- Slow state gives concrete policy hooks for:
  - shorter replies after low-energy scenes.
  - holding optional proactive behavior after corrections or fatigue.
  - preferring recent corrections/relationship residue in recall policy.
  - allowing guarded emotion bias without fact claims or stable rewrites.

## Remaining

- Batch F: module ecology audit.
- Later integration batch: wire triage/error/immune/slow-state prompt blocks into
  runtime context in a narrow advisory pass.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Recently changed:

- `xinyu_slow_state_modulator.py`
- `tests/test_slow_state_modulator.py`

Recommended resume check:

`.\.venv\Scripts\python.exe -m pytest tests\test_slow_state_modulator.py tests\test_scene_frame.py tests\test_life_reply_policy_scene_frame.py tests\test_turn_triage_gate.py tests\test_response_error_loop.py -q`
