# XinYu P66 Memory Immune Gate Batch - 2026-05-19

## Scope

Plan: `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md`

Batch: D / immune system and danger-theory mapping.

Goal: add a unified pre-write/pre-promotion danger gate for memory candidates.
This provider classifies danger signals and chooses allow/observe/quarantine/
block/owner-review policy. It does not write stable memory and does not render
raw candidate bodies.

## Changes Completed

- Added `xinyu_memory_immune_gate.py`.
  - Defines `MemoryImmuneDecision`.
  - Statuses:
    - `allow_candidate`
    - `observe_more`
    - `quarantine_review_only`
    - `block_candidate`
    - `owner_review_required`
  - Detects:
    - secret/credential material.
    - group-to-owner or group-to-relationship scope mismatch.
    - external material trying to alter stable self/policy.
    - stable self/prompt/permission/policy changes.
    - raw/runtime state direct-memory attempts.
    - low confidence candidates.
    - external source/library material.
  - Routes voice corrections to review-only and owner preference/relationship
    signals to observe-more unless repeated and reviewed.
- Added `tests/test_memory_immune_gate.py`.
  - Covers group relationship blocking.
  - Covers secret blocking and prompt redaction.
  - Covers external stable-persona quarantine.
  - Covers owner-review requirement for policy/stable promotion.
  - Covers voice correction review-only route.
  - Covers single preference observe-more.
  - Covers project recent-context allow.
  - Covers rendered prompt block body hygiene.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_memory_immune_gate.py tests\test_memory_immune_gate.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_memory_immune_gate.py tests\test_memory_event_time_provenance.py tests\test_memory_structured_p0_triage.py tests\test_response_error_loop.py tests\test_turn_triage_gate.py -q`
  - 28 passed
- `git diff --check -- xinyu_memory_immune_gate.py tests\test_memory_immune_gate.py`
  - pass

Full suite and desktop build were not run because this batch adds a standalone
provider with focused boundary tests and no bridge injection yet.

## Direct Effect

- XinYu now has a danger-theory memory write boundary before stable promotion.
- Existing candidate extraction/self-review can keep their jobs, while this gate
  supplies one common risk vocabulary.
- External/group/private/stable-memory boundaries are now testable as a small
  provider instead of scattered rules.

## Remaining

- Batch E: implement slow state modulator.
- Batch F: implement module ecology audit.
- Later integration batch: wire triage/error/immune prompt blocks into runtime
  context in a narrow advisory pass.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Recently changed:

- `xinyu_memory_immune_gate.py`
- `tests/test_memory_immune_gate.py`

Recommended resume check:

`.\.venv\Scripts\python.exe -m pytest tests\test_memory_immune_gate.py tests\test_memory_event_time_provenance.py tests\test_memory_structured_p0_triage.py tests\test_response_error_loop.py tests\test_turn_triage_gate.py -q`
