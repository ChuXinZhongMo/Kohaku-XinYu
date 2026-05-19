# XinYu P64 Turn Triage Gate Batch - 2026-05-19

## Scope

Plan: `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md`

Batch: C / medical triage mapping.

Goal: add an advisory current-turn triage provider so short owner commands,
explicit recall, low-energy context, relationship pressure, and runtime failures
resolve to the right next lane before recall/tool/action. No stable memory writes.

## Changes Completed

- Added `xinyu_turn_triage_gate.py`.
  - Defines `TurnTriageDecision`.
  - Adds lanes:
    - `active_task_continue`
    - `direct_memory_recall`
    - `emotional_support`
    - `relationship_boundary`
    - `permission_or_control`
    - `rest_low_burden`
    - `urgent_runtime_fix`
    - `ordinary_chat`
  - Uses existing `VisibleTurnContext` and optional `SceneFrame`.
  - Resolves short commands such as "continue/start/next" against pending
    work context instead of treating them as ordinary chat.
  - Keeps the provider advisory-only and does not print raw user text in its
    prompt block.
- Added `tests/test_turn_triage_gate.py`.
  - Covers active task continuation from short commands.
  - Covers explicit recall routing to canonical memory recall.
  - Covers low-energy Scene Frame routing.
  - Covers relationship pressure.
  - Covers runtime failure fix priority.
  - Verifies rendered prompt metadata does not include private raw body.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_turn_triage_gate.py tests\test_turn_triage_gate.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_turn_triage_gate.py tests\test_turn_classifier.py tests\test_scene_frame.py tests\test_cross_domain_synaesthesia_registry.py -q`
  - 21 passed
- `git diff --check -- xinyu_turn_triage_gate.py tests\test_turn_triage_gate.py`
  - pass

Full suite and desktop build were not run because this batch adds a standalone
advisory provider and focused tests, with no runtime bridge integration yet.

## Direct Effect

- XinYu now has the medical-triage inspired decision point as a tested provider.
- "Continue/start/next" can now be interpreted against current plan/worklog
  context.
- Explicit memory questions are separated from task continuation.
- Low-energy/rest context can lower visible burden without creating facts.

## Remaining

- Decide whether to inject the triage prompt block into `xinyu_runtime_context.py`
  or keep it provider-only until response/error-loop work is in place.
- Batch B: implement control-theory response error loop.
- Batch D: implement memory immune gate.
- Batch E: implement slow state modulator.
- Batch F: implement module ecology audit.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Recently changed:

- `xinyu_turn_triage_gate.py`
- `tests/test_turn_triage_gate.py`

Recommended resume check:

`.\.venv\Scripts\python.exe -m pytest tests\test_turn_triage_gate.py tests\test_turn_classifier.py tests\test_scene_frame.py tests\test_cross_domain_synaesthesia_registry.py -q`
