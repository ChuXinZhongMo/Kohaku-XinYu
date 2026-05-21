# XinYu Closeout Iteration

Date: 2026-05-21

Purpose: continue the remaining XinYu finish work after the complete autonomous execution plan reached closure. This is the active closeout queue for work that can be done without changing owner-controlled gates by surprise.

## Current Ground Truth

- Core and QQ gateway are running locally.
- `XINYU-COMPLETE-AUTONOMOUS-EXECUTION-PLAN.md` is closed; all tasks inside it are checked.
- v1 is ready for owner-private simple-message canary review, but remains shadow-only until explicit owner approval.
- Stable personality/profile writes remain review-only.
- Broad proactive behavior remains bounded by owner gate, cooldown, and audit state.
- Current worktree contains the time-context, ordinary owner-private live-reply fixes, runtime readiness optimization, and q-903 learning-quality cleanup.
- Live learning quality is now stable after q-903 independent-host follow-up.

## Completion Queue

### 1. Preserve Runtime Readiness

- [x] Fix readiness gate timeout risk in `tests/smoke/runtime/mojibake_guard_smoke.py`.
  - Evidence: `.\.venv\Scripts\python.exe tests\smoke\runtime\mojibake_guard_smoke.py` passed in about 6 seconds after pruning excluded directories during traversal.
  - Evidence: `.\.venv\Scripts\python.exe tests\smoke\runtime\integration\runtime_readiness_smoke.py` passed.
- [x] Keep `xinyu_status.py --json` green after each runtime or gateway patch.
  - Evidence: `.\.venv\Scripts\python.exe xinyu_status.py --json` returned `"ok": true` after this closeout pass.
- [x] Keep QQ gateway smoke green after gateway patches.
  - Evidence: `.\.venv\Scripts\python.exe tests\smoke\qq\integration\xinyu_qq_gateway_smoke.py` passed.

### 2. Finish Current Dirty Worktree

- [x] Add unified real-world time context to QQ payloads, live prompt, renderer prompt, and renderer conversation tail.
  - Evidence: targeted time-context tests passed.
- [x] Keep owner-private ordinary greetings/self-state questions on live generation rather than fixed text.
  - Evidence: owner-private regression tests passed in the previous batch.
- [x] Re-run full `pytest` after this closeout batch.
  - Evidence: `.\.venv\Scripts\python.exe -m pytest` passed, `772 passed`.
- [ ] Split current worktree into reviewable commit packages before starting larger refactors.

### 3. Real QQ Observation

- [ ] Run small owner-private no-restore observation batches for:
  - ordinary greetings;
  - "status / how do you feel" self-state questions;
  - template-style complaints;
  - correction-after-delay cases.
- [ ] Inspect shadow flags without storing raw private chat in public artifacts.
- [ ] Convert real owner corrections into reviewable calibration candidates through existing QQ review tooling.

### 4. Learning Quality Review

- [x] Re-check the live q-006 state before changing learning gates.
  - Evidence: `memory/self/ai_self_iteration_state.md` still has q-006 as `growth_review_candidate` with direct stable-memory writes blocked.
  - Evidence: live `learning_quality_state.md` is not currently blocked by q-006 held material.
- [x] Fix q-903 source-diversity follow-up requests so stale `active_questions.md` cannot degrade the target to `general`.
  - Evidence: `source_request_planner_engine.py` now recovers a specific question target from existing same-question requests before planning or normalizing quality follow-ups.
  - Evidence: `tests/test_source_request_planner_targets.py` covers q-903-style target recovery.
  - Evidence: live q-903 pending follow-ups now use `target: human-relationship` and the matching human-relationship query.
- [x] Find or collect independent q-903 source material that passes source comparison before learner integration.
  - Evidence: a temp-directory dry run first rejected weak pages as `semantic_mismatch_hold`, then passed with two relationship-boundary pages after conservative token normalization.
  - Evidence: live q-903 follow-up staged `material-2026-05-21-001` and `material-2026-05-21-002`, compared the q-903 group as `corroborated` across 3 evidence hosts, and integrated both as knowledge-only entries.
  - Evidence: live `learning_quality_state.md` is now `quality_grade: stable` with `warning_count: 0`.
  - Evidence: runtime mirrors were refreshed; `inner_cycle_state.md` and `runtime_bridge_state.md` now report q-903 follow-up as `stable`, `learning_quality_warnings: 0`, and `pending_source_requests: 0`.
- [x] Decide whether each held material is:
  - same-question support;
  - limited-independence support;
  - unrelated and should stay held;
  - rejected.
  - Evidence: q-903 candidates were only applied after source comparison passed; earlier semantic-mismatch candidates were left unapplied.
- [ ] Keep stable self/personality/relationship memory blocked unless review evidence justifies a candidate.

### 5. v1 Canary Decision

- [ ] Keep v1 shadow metrics collecting.
- [ ] Do not enable owner-simple canary automatically.
- [ ] If owner explicitly approves, enable only owner-private simple-message canary and keep fallback to the old main path.

### 6. Structural Debt

- [ ] Continue thinning `xinyu_core_bridge.py` only in behavior-preserving slices.
- [ ] Continue splitting `xinyu_qq_gateway.py` as transport-only modules.
- [ ] Split Desktop renderer and CSS only after backend closeout stays green.

## Stop Rules

Stop and report instead of silently changing behavior when a task needs:

- owner approval to enable canary/proactive/stable-memory gates;
- private QQ transcript inspection;
- credentials or account actions;
- deletion, archive movement, or commit creation.
