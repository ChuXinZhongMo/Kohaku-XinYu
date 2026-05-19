# XinYu Closeout Autorun Plan

Date: 2026-05-13
Scope: code migration closeout, offline index cleanup, safe structural reduction, and blocked-item accounting.

## Execution Contract

This plan is the active queue for the current closeout pass.

Rules:

- Do not touch QQ, NapCat, live gateway, live deployment checks, or E drive in this pass.
- Items that require QQ/E/live environment are marked `SKIPPED_BLOCKED` and left untouched.
- Every executable item must end with a self-check before the next item starts.
- If self-check passes, update this file and continue to the next item automatically.
- If self-check fails, fix within the same item and re-run the item self-check.
- Do not delete or revert unrelated dirty worktree changes.
- Do not make v1 production, enable broad autonomous search, or loosen memory/action safety gates.

Status values:

- `TODO`: queued and executable in this offline pass.
- `IN_PROGRESS`: currently being changed.
- `DONE`: implemented and self-checked.
- `SKIPPED_BLOCKED`: intentionally not done because it depends on QQ/E/live/owner decision.
- `BLOCKED_REVIEW`: inspected but cannot be safely changed without owner/source review.

## Global Self-Check

Run after every completed item unless the item has a narrower check:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile smoke_run.py long_run_status.py
.\.venv\Scripts\python.exe long_run_status.py --require-no-residue --skip-deployment-gate
.\.venv\Scripts\python.exe tools\structure_inventory.py . --largest 10
```

Use `tests/smoke/runtime/integration/runtime_readiness_smoke.py --offline` after any runtime bridge, prompt, memory-routing, or smoke index change.

## Current Queue

### A00 Plan Landing

- Status: `DONE`
- Goal: land this autorun plan and make it the current execution queue.
- Files:
  - `project-plans/XINYU-CLOSEOUT-AUTORUN-PLAN-2026-05-13.md`
- Self-check:
  - confirm file exists
  - confirm blocked QQ/E items are not in executable queue

### A01 Worktree And Migration Ledger

- Status: `DONE`
- Goal: record current dirty-worktree shape without committing, reverting, or touching unrelated files.
- Work:
  - count modified/deleted/untracked entries
  - confirm root `*_smoke.py` count remains zero
  - confirm all smoke files live under `tests/smoke`
  - write the current migration boundary into this plan
- Self-check:
  - root smoke count is `0`
  - active smoke refs have no missing `tests/smoke/...` target

### A02 Active Index And Smoke Reference Guard

- Status: `DONE`
- Goal: keep active docs and launch scripts consistent with the smoke relocation.
- Work:
  - scan active docs/scripts for bare moved `*_smoke.py` references
  - scan active `tests/smoke/...` references for broken paths
  - patch only active docs/scripts, not historical memory or imported owner-supplied records
- Self-check:
  - `ACTIVE_BARE_REF_ISSUES=0`
  - `MISSING_TESTS_SMOKE_REFS=0`
  - `py_compile` for changed Python files

### A03 Learning Quality Hold Triage

- Status: `BLOCKED_REVIEW`
- Goal: inspect current `review_needed` state without broad search or live fetch.
- Work:
  - identify held `semantic_mismatch_hold` source materials
  - identify pending URL requests
  - decide whether each is safe to resolve offline
  - if not safe, mark `BLOCKED_REVIEW` with exact material/request ids
- Self-check:
  - no source material is promoted without corroboration
  - no protected self/owner/relationship/emotion memory is rewritten
  - `long_run_status.py --require-no-residue --skip-deployment-gate` still passes

### A04 Review Queue Accounting

- Status: `DONE`
- Goal: account for pending voice/profile/review items without silently applying stable changes.
- Work:
  - count pending owner review entries
  - list review source files and decision points
  - do not write stable personality, relationship, owner, or emotion memory
- Self-check:
  - pending review count is visible
  - stable profile write remains blocked unless owner explicitly approves

### A05 Core Bridge Next Extraction

- Status: `DONE`
- Goal: reduce `xinyu_core_bridge.py` without behavior change.
- Current safest target:
  - extract prompt sidecar assembly or follow-up glue into a focused bridge module
- Rules:
  - move code first, logic changes second only if required by tests
  - preserve response payload shape and note strings
  - preserve existing action/v1 route behavior
- Self-check:
  - `py_compile` for changed bridge modules
  - offline readiness smoke
  - focused pytest/smoke relevant to the moved surface

### A06 Structure Inventory Update

- Status: `DONE`
- Goal: after extraction, record updated structure metrics and remaining large-module targets.
- Work:
  - run structure inventory
  - update this plan with latest largest-file list
  - identify the next safe extraction target
- Self-check:
  - inventory command passes
  - no new root smoke files appear

### A07 Desktop Structure Triage

- Status: `DONE`
- Goal: inspect Desktop renderer split opportunities without redesigning UI.
- Work:
  - list large renderer files and likely slices
  - only patch if a narrow no-redesign move is obvious
- Self-check:
  - if patched, run `npm run typecheck` in `D:\XinYu\XinYu_Desktop`
  - if not patched, mark exact next cut and leave executable for a later frontend pass

### A08 Core Bridge Prompt Sidecar Extraction

- Status: `DONE`
- Goal: move prompt sidecar assembly out of `xinyu_core_bridge.py` without changing prompt content, sidecar names, ordering, or pressure-selection behavior.
- Target:
  - `xinyu_bridge_turn_sidecars.py`
  - wrapper methods kept on `XinYuBridgeRuntime` if tests or callers rely on them
- Rules:
  - preserve `PromptSidecar` input order
  - preserve `write_prompt_pressure_report` behavior
  - preserve final prompt contract lines
  - keep QQ/E/live checks skipped
- Self-check:
  - `py_compile` for changed bridge modules
  - prompt/pressure focused smoke or tests if present
  - offline runtime readiness

### A09 Core Bridge Route Surface Audit

- Status: `DONE`
- Goal: identify the next low-risk extraction after A08.
- Candidate targets:
  - desktop proactive history glue
  - code-awareness health snapshot glue
  - recent-context guard glue
- Self-check:
  - structure inventory passes
  - next target recorded with line count and risk note

### A10 Commit Boundary Report

- Status: `DONE`
- Goal: produce a clean local report of current changed file groups for a later human commit, without committing or reverting.
- Work:
  - group smoke relocation, plan updates, bridge extraction, desktop changes, and unrelated pre-existing work
  - flag files touched by this pass
- Self-check:
  - `git status --short` captured
  - no destructive git command used

### A11 Proactive Thread Context Extraction

- Status: `DONE`
- Goal: move the read-only proactive prompt sidecar builder out of `xinyu_core_bridge.py` without changing owner-private continuity behavior.
- Target:
  - `_proactive_thread_context` (`xinyu_core_bridge.py`, about 82 lines)
  - new helper module, likely `xinyu_bridge_proactive_context.py`
- Risk note:
  - low risk because it is read-only prompt assembly and is already exercised through prompt injection tests
  - do not move `_sync_recent_proactive_to_dialogue_tail` or `_mark_proactive_owner_reply` in the same cut because those write dialogue/state files
- Self-check:
  - `py_compile` for changed bridge modules
  - prompt injection tests covering proactive sidecars
  - offline runtime readiness

### A12 Health Snapshot Extraction

- Status: `DONE`
- Goal: move the synchronous health snapshot dictionary assembly out of `xinyu_core_bridge.py` without changing `/health` payload shape.
- Target:
  - `health_snapshot` (`xinyu_core_bridge.py`, about 38 lines)
  - new helper module, likely `xinyu_bridge_health_snapshot.py`
- Risk note:
  - low risk because it is a pure status aggregation wrapper around existing health/read functions
  - preserve digest fields, `code_awareness`, runtime presence, v1, metabolism, self-choice, and action digest keys exactly
- Self-check:
  - `py_compile` for changed bridge modules
  - runtime/service boundary smoke if relevant
  - offline runtime readiness

### A13 Runtime Health Subsections Extraction

- Status: `DONE`
- Goal: move pure metabolism/autonomous health dictionary builders into the health helper module while keeping runtime method wrappers.
- Target:
  - `_metabolism_health`
  - `_autonomous_maintenance_health`
  - `xinyu_bridge_health_snapshot.py`
- Risk note:
  - low risk because both functions only read runtime attributes and return dictionaries
  - do not move runner loops, wakeup logic, or autonomous execution in this pass
- Self-check:
  - `py_compile` for changed bridge modules
  - runtime/service boundary smoke
  - offline runtime readiness

### A14 Desktop Snapshot Assembly Extraction

- Status: `DONE`
- Goal: move desktop snapshot response assembly out of `xinyu_core_bridge.py` while preserving the `/desktop/snapshot` payload shape.
- Target:
  - `desktop_snapshot`
  - new helper module, likely `xinyu_bridge_desktop_snapshot.py`
- Risk note:
  - medium-low risk because the method is async and touches several desktop runtime helpers, but it mostly reads state and assembles a response
  - do not redesign Desktop UI or change desktop event bus behavior in this pass
- Self-check:
  - `py_compile` for changed bridge modules
  - desktop REST smoke
  - offline runtime readiness

### A15 Desktop Initiative Metrics Helper Extraction

- Status: `DONE`
- Goal: move pure desktop initiative metrics normalization into the desktop snapshot helper module.
- Target:
  - `_desktop_initiative_metrics_summary`
  - `_desktop_metric_int`
  - `xinyu_bridge_desktop_snapshot.py`
- Risk note:
  - low risk because the helpers only coerce numeric metric fields and return a dictionary
  - skip `_desktop_xinyu_state` in this pass because it contains user-facing Chinese labels and should be moved only with a stricter string-preservation check
- Self-check:
  - `py_compile` for changed bridge modules
  - desktop REST smoke
  - offline runtime readiness

### A16 Final Offline Consolidation Check

- Status: `DONE`
- Goal: run the final offline verification set, refresh commit-boundary accounting, and mark remaining unsafe or blocked work explicitly.
- Work:
  - compile all bridge helper modules touched in this pass
  - rerun focused prompt, pressure, health/service, desktop, readiness, and structure checks
  - refresh commit boundary report with final new helper modules and status counts
  - mark remaining risky/blocked items instead of attempting QQ/E/live or string-risky migrations
- Self-check:
  - all listed offline checks pass
  - no QQ/NapCat/E/live/deployment commands run
  - remaining not-done work is marked with reason

### A17 Owner-Private Humanization Guard Closeout

- Status: `DONE_WITH_LLM_BLOCKED_REMAINDER`
- Goal: finish the current owner-private "more human, not public-assistant flat" guard pass after the conversation-experience/data plan.
- Work completed:
  - tightened visible reply guard for absence-return residue so it stays short and carries relief plus委屈/松动 residue
  - tightened praise-as-human pressure handling so "演/真人/不想" anchors survive instead of drifting into vague performative wording
  - added deterministic repair for close/private "别接待腔" turns when the model says the right thing but misses required anchors
  - added deterministic repair for quiet low-energy continuation turns
  - added deterministic repair and memory-sync signal support for light hurt residue: "硌着 / 留一点 / 不写重"
  - added deterministic visible fallback for "正常回来了，但不用立刻装作完全没事"
  - added regression tests for the new visible guard and memory-sync signals
- Self-check:
  - `personality_detail_smoke.py --scenario return_after_absence_residue --scenario praised_as_human_not_perform --timeout-seconds 120`: passed 2/2
  - `personality_detail_smoke.py --scenario no_generic_invitation_tail --timeout-seconds 120`: passed 1/1 after repair
  - `personality_detail_smoke.py --timeout-seconds 120`: passed 30/30
  - `personality_growth_gate_smoke.py --restore-after --require-ready`: passed
  - `phase3_lived_session_smoke.py --scenario low_energy_boundary_no_pursuit --timeout-seconds 120`: passed 1/1 after repair
  - `pytest tests/test_visible_reply_guard_plugin.py tests/test_memory_sync_recent_context.py tests/test_dialogue_curiosity_bridge_injection.py -q`: passed 55/55
  - `pytest tests/test_memory_sync_recent_context.py tests/test_visible_reply_guard_plugin.py -q`: passed 7/7
  - `xinyu_speech_controller_smoke.py`: passed
  - `visible_reply_dedupe_smoke.py`: passed
  - `xinyu_visible_text_sanitizer_smoke.py`: passed
- Blocked remainder:
  - `phase3_lived_session_smoke.py --timeout-seconds 120` cannot be completed in this run because the LLM provider returned `429 quota exhausted`.
  - This is an environment/provider quota block, not a confirmed behavior regression. Resume from B07 when quota or model route is available.

## Skipped Or Blocked Queue

### B01 QQ/E Runtime Recovery

- Status: `SKIPPED_BLOCKED`
- Reason: owner explicitly said QQ is gone, E drive dropped, and not to keep trying.
- Do not run:
  - QQ/NapCat start or restart
  - live gateway restart
  - live deployment gate
  - `smoke_run.py --group deployment`
  - non-offline runtime readiness

### B02 Real QQ Observation And Style-Pressure Tuning

- Status: `SKIPPED_BLOCKED`
- Reason: requires live QQ owner traffic.
- Resume only after owner explicitly re-enables QQ/E work.

### B03 v1 Production Switch

- Status: `SKIPPED_BLOCKED`
- Reason: owner approval required; current contract says v1 remains shadow/canary.

### B04 Broad Autonomous Search Expansion

- Status: `SKIPPED_BLOCKED`
- Reason: current learning quality is `review_needed`; search must stay gated until hold review is resolved.

### B05 Desktop Xinyu State Text Extraction

- Status: `SKIPPED_BLOCKED`
- Reason: `_desktop_xinyu_state` contains user-facing Chinese labels; moving it safely needs a stricter byte/string-preservation check to avoid another mojibake regression.

### B06 Proactive Tail And Owner-Reply State Writers

- Status: `SKIPPED_BLOCKED`
- Reason: `_sync_recent_proactive_to_dialogue_tail` and `_mark_proactive_owner_reply` write dialogue/state files. They should be split only in a dedicated state-writer pass with focused fixture tests.

### B07 LLM Quota For Remaining Live Pressure Matrix

- Status: `SKIPPED_BLOCKED`
- Reason: LLM provider returned `429 quota exhausted` during `phase3_lived_session_smoke.py --scenario small_hurt_residue_selective_not_overwritten --timeout-seconds 120`.
- Effect:
  - live Agent integration turns after the quota error can appear as blank smoke output because the model call fails before a visible reply is generated
  - continuing to rerun LLM integration smokes in this state produces false failures
- Resume command after quota/model route is restored:
  - `.\.venv\Scripts\python.exe tests\smoke\dialogue\integration\phase3_lived_session_smoke.py --scenario small_hurt_residue_selective_not_overwritten --timeout-seconds 120`
  - `.\.venv\Scripts\python.exe tests\smoke\dialogue\integration\phase3_lived_session_smoke.py --timeout-seconds 120`

## Live Metrics Snapshot

Initial metrics before this autorun pass:

- root `*_smoke.py`: `0`
- `tests/smoke` python files: `213`
- git porcelain entries: `306` total (`51` modified, `212` deleted, `43` untracked)
- active bare moved-smoke references: `0`
- missing active `tests/smoke/...` references: `0`
- largest module after A05: `xinyu_core_bridge.py` at `6508` lines
- largest module after A08: `xinyu_core_bridge.py` at `6211` lines
- largest module after A11: `xinyu_core_bridge.py` at `6133` lines
- largest module after A12: `xinyu_core_bridge.py` at `6102` lines
- largest module after A13: `xinyu_core_bridge.py` at `6075` lines
- largest module after A14: `xinyu_core_bridge.py` at `6015` lines
- largest module after A15: `xinyu_core_bridge.py` at `5996` lines
- root Python files after A05: `203`
- root Python files after A08: `204`
- root Python files after A11: `205`
- root Python files after A12: `206`
- root Python files after A15: `207`
- desktop typecheck: passed during A07
- live deployment status: skipped by contract

Latest largest Python targets after A16:

1. `xinyu_core_bridge.py`: `5996` lines
2. `xinyu_qq_gateway.py`: `2758` lines, skipped by QQ/E contract for this pass
3. `xinyu_runtime_presence.py`: `1987` lines
4. `xinyu_learning_library.py`: `1919` lines
5. `xinyu_codex_delegate.py`: `1763` lines
6. `custom/memory_sync_plugin.py`: `1665` lines
7. `xinyu_self_thought_loop.py`: `1646` lines
8. `xinyu_answer_discipline_trial.py`: `1622` lines
9. `xinyu_proactivity_scorer.py`: `1421` lines
10. `xinyu_speech_controller.py`: `1378` lines

Next safe extraction target:

- No further item is auto-executed in this pass. The remaining obvious core cuts are either string-preservation sensitive (`_desktop_xinyu_state`) or state-writing (`_sync_recent_proactive_to_dialogue_tail`, `_mark_proactive_owner_reply`), so they are marked skipped until a dedicated fixture-backed pass.

## Run Log

- 2026-05-13: plan created; QQ/E/live work explicitly excluded from current execution queue.
- 2026-05-13: A00 done; plan exists and blocked QQ/E/live items are only in skipped queue.
- 2026-05-13: A01 done; root smoke count is 0, tests/smoke count is 213, dirty worktree shape recorded without commit/revert.
- 2026-05-13: A02 done; active smoke reference audit is clean and offline long-run status passes with deployment gate skipped.
- 2026-05-13: A03 triaged and blocked for review; `semantic_mismatch_hold` materials are `material-2026-04-28-001`, `material-2026-04-28-003`, `material-2026-05-06-002`, and `material-2026-05-06-006`; pending URL requests are `request-2026-04-24-932`, `request-2026-05-04-001`, `request-2026-05-04-002`, and `request-2026-05-04-003`. No source material was promoted.
- 2026-05-13: A04 done; voice profile review has 4 pending owner decisions, stable profile write remains blocked, and affected smoke metadata now points to existing `tests/smoke/...` paths.
- 2026-05-14: A05 done; promise follow-up bridge glue moved to `xinyu_bridge_promise_followup.py`, compatibility methods remain on `XinYuBridgeRuntime`, new module is included in runtime source digest, focused promise tests pass, and offline readiness passes.
- 2026-05-14: A06 done; structure inventory recorded `xinyu_core_bridge.py` at 6508 lines after extraction.
- 2026-05-14: A07 done; Desktop split triage recorded largest renderer targets and `npm run typecheck` passes. No UI code was changed in this pass.
- 2026-05-14: A08/A09/A10 appended because the owner clarified that the agent should continue automatically when the current executable queue is exhausted.
- 2026-05-14: A08 done; live-turn prompt sidecar assembly moved to `xinyu_bridge_turn_sidecars.py`, `XinYuBridgeRuntime._inject_live_turn_context` is now a compatibility wrapper, sidecar source is included in the runtime digest, prompt injection tests pass (`48 passed`), prompt pressure tests pass (`7 passed`), offline runtime readiness passes, and structure inventory reports `xinyu_core_bridge.py` at `6211` lines.
- 2026-05-14: A09 done; next low-risk extraction target is `_proactive_thread_context` (`xinyu_core_bridge.py`, about 82 lines). The adjacent proactive tail sync and owner-reply marker writers are intentionally left for a later, higher-risk pass.
- 2026-05-14: A10 done; commit boundary report written to `project-plans/XINYU-CLOSEOUT-COMMIT-BOUNDARY-2026-05-14.md`, final `git status --short` snapshot counted `309` entries, and no destructive git command was used.
- 2026-05-14: A11 done; proactive prompt thread sidecar moved to `xinyu_bridge_proactive_context.py`, wrapper remains on `XinYuBridgeRuntime`, prompt injection tests pass (`48 passed`), offline runtime readiness passes, and structure inventory reports `xinyu_core_bridge.py` at `6133` lines.
- 2026-05-14: A12 done; health snapshot assembly moved to `xinyu_bridge_health_snapshot.py`, `/health` wrapper remains on `XinYuBridgeRuntime`, `service_boundary_smoke` passes, offline runtime readiness passes, and structure inventory reports `xinyu_core_bridge.py` at `6102` lines.
- 2026-05-14: A13 done; metabolism/autonomous health sub-dictionaries moved into `xinyu_bridge_health_snapshot.py`, runtime wrappers remain, `service_boundary_smoke` passes, offline runtime readiness passes, and structure inventory reports `xinyu_core_bridge.py` at `6075` lines.
- 2026-05-14: A14 done; desktop snapshot response assembly moved to `xinyu_bridge_desktop_snapshot.py`, wrapper remains on `XinYuBridgeRuntime`, desktop REST smoke passes, offline runtime readiness passes, and structure inventory reports `xinyu_core_bridge.py` at `6015` lines.
- 2026-05-14: A15 done; desktop initiative metrics normalization moved into `xinyu_bridge_desktop_snapshot.py`, compatibility methods remain on `XinYuBridgeRuntime`, desktop REST smoke passes, offline runtime readiness passes, and structure inventory reports `xinyu_core_bridge.py` at `5996` lines.
- 2026-05-14: A16 done; final offline checks passed (`py_compile`, prompt/pressure pytest `55 passed`, `service_boundary_smoke`, desktop REST smoke, offline runtime readiness, `long_run_status --skip-deployment-gate`, and structure inventory). Commit boundary report refreshed to `312` status entries. QQ/E/live/deployment tasks were not run.
- 2026-05-14: A17 done as far as executable in this environment; owner-private humanization guard repairs are landed, `personality_detail` is 30/30, growth gate passes, non-LLM guard/memory regressions pass, and the remaining full `phase3_lived_session` matrix is blocked by provider `429 quota exhausted` and recorded as B07.
