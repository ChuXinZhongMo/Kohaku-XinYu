# XinYu Closeout Iteration

Date: 2026-05-21

Purpose: continue the remaining XinYu finish work after the complete autonomous execution plan reached closure. This closeout queue is now reconciled with the later autonomous completion plan; remaining owner-gated behavior stays blocked unless explicitly approved.

## Current Ground Truth

- Core and QQ gateway are running locally.
- `XINYU-COMPLETE-AUTONOMOUS-EXECUTION-PLAN.md` is closed; all tasks inside it are checked.
- v1 is ready for owner-private simple-message canary review, but remains shadow-only until explicit owner approval.
- Stable personality/profile writes remain review-only.
- Broad proactive behavior remains bounded by owner gate, cooldown, and audit state.
- Current worktree contains the time-context, ordinary owner-private live-reply fixes, runtime readiness optimization, and q-903 learning-quality cleanup.
- Live learning quality is now stable after q-903 independent-host follow-up.
- Real QQ observation was completed from owner-provided live probes using sanitized trace fields only; no raw private transcript is required for this plan.
- Post-restart live chat baseline on 2026-05-22 completed 35/35 cases with 0 errors, 0 empty replies, 0 mechanic leaks, 0 reference misses, and 0 reportish replies; one context case was over the soft chat-length threshold.

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
  - Evidence: `.\.venv\Scripts\python.exe -m pytest` passed, `786 passed`.
- [x] Split current worktree into reviewable commit packages before starting larger refactors.
  - Evidence: closeout work was split into five commits ending at `031dfce`.

### 3. Real QQ Observation

- [x] Run small owner-private no-restore observation batches for:
  - ordinary greetings;
  - "status / how do you feel" self-state questions;
  - template-style complaints;
  - correction-after-delay cases.
  - Evidence: owner-provided live probes were reviewed through sanitized trace fields only, matching the categories prepared in `XINYU-QQ-OBSERVATION-PROBE-CHECKLIST-2026-05-21.md`.
  - Evidence: local live chat baseline `live_chat_baseline_20260522T211158+0800` completed 35/35 accepted cases after the core restart.
- [x] Inspect shadow flags without storing raw private chat in public artifacts.
  - Evidence: `XINYU-REMAINING-AUTONOMOUS-COMPLETION-PLAN-2026-05-21.md` records safe fields from `runtime/qq_inbound_trace.jsonl` and `runtime/answer_discipline_visible_send_shadow.jsonl`; no raw prompt or raw reply was needed in public artifacts.
- [x] Convert real owner corrections into reviewable calibration candidates through existing QQ review tooling.
  - Evidence: the observed correction became a route-rule fix: `reply_quality_complaint` no longer uses owner-private semantic fast direct repair.
  - Evidence: review tooling remains gated, and no stable memory/personality promotion was authorized by this lane.

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
- [x] Keep stable self/personality/relationship memory blocked unless review evidence justifies a candidate.
  - Evidence: gate tests passed; `ai_self_iteration_state.md` keeps profile direct writes blocked, narrative review-only, relationship blocked, and emotion blocked.

### 5. v1 Canary Decision

- [x] Keep v1 shadow metrics collecting.
  - Evidence: `xinyu_status.py --json` reports readiness sample window `200`, error rate `0.000`, and owner approval required.
- [x] Do not enable owner-simple canary automatically.
  - Evidence: status reports `owner_simple_canary: false` and `auto_full_switch: false`.
- [x] If owner explicitly approves, enable only owner-private simple-message canary and keep fallback to the old main path.
  - Evidence: no approval was present in this pass, so the path remains documented and blocked at owner approval.

### 6. Structural Debt

- [x] Continue thinning `xinyu_core_bridge.py` only in behavior-preserving slices.
  - Progress: extracted timestamp normalization and Codex marker parsing helpers; targeted bridge tests, runtime readiness smoke, and full pytest remained green.
- [x] Continue splitting `xinyu_qq_gateway.py` as transport-only modules.
  - Progress: extracted QQ event-time parsing/formatting into `xinyu_qq_event_time.py` and kept the gateway smoke plus time-context tests green.
  - Progress: extracted session flow, bridge error classification, and reception metadata helpers; QQ gateway smoke and full pytest remained green.
- [x] Prepare Desktop renderer and CSS split only after backend closeout stays green.
  - Evidence: `XINYU-DESKTOP-SPLIT-READINESS-2026-05-21.md` records split boundaries; `npm run typecheck` and `npm run build` passed.

## Stop Rules

Stop and report instead of silently changing behavior when a task needs:

- owner approval to enable canary/proactive/stable-memory gates;
- private QQ transcript inspection;
- credentials or account actions;
- deletion, archive movement, or commit creation.
