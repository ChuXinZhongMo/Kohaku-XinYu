# XinYu Remaining Autonomous Completion Plan

Date: 2026-05-21

Purpose: finish the remaining XinYu closeout work through repeatable Codex execution loops. This plan separates code work that can be completed automatically from owner-gated behavior that must stay blocked unless explicit owner approval exists.

## Ground Truth

- Current source tree is clean at plan creation.
- Current validation baseline is `773 passed`.
- `xinyu_status.py --json` is green.
- Live learning quality is stable after q-903 follow-up.
- v1 canary remains shadow-only until explicit owner approval.
- Stable personality/profile/relationship writes remain review-only.

## Remaining Work Count

- Auto-code work: 3 tracks.
- Automatic monitoring/gate validation: 4 tracks.
- Real QQ observation: 3 tracks.

Completion means all auto-code tracks are finished, all monitoring tracks have fresh evidence, and real QQ observation is either completed from owner-provided live probes or left as an explicit owner-input dependency with tooling ready.

## Executor Loop

Repeat until every lane below is checked or explicitly marked `owner_input_required`:

1. Start from `D:\XinYu`.
2. Run `git status --short`.
3. If the worktree is dirty, inspect it and do not overwrite unrelated user changes.
4. Pick the highest-priority unchecked `AUTO` item.
5. Make the smallest behavior-preserving change that moves that item forward.
6. Run targeted tests for the touched area.
7. Run `.\.venv\Scripts\python.exe -m pytest` from `XinYu-Core\examples\agent-apps\xinyu` after each meaningful batch.
8. Run:
   - `.\.venv\Scripts\python.exe tests\smoke\qq\integration\xinyu_qq_gateway_smoke.py` after QQ gateway changes.
   - `.\.venv\Scripts\python.exe tests\smoke\runtime\integration\runtime_readiness_smoke.py` after runtime/status changes.
   - `.\.venv\Scripts\python.exe xinyu_status.py --json` before closing a batch.
9. Update this plan and `XINYU-CLOSEOUT-ITERATION-2026-05-21.md` with exact evidence.
10. Commit each coherent passing batch with a focused message.
11. Continue to the next item.

Do not stop after one successful slice if another `AUTO` item remains and tests are green.

## Stop Rules

Stop and report instead of changing behavior when an item needs:

- enabling v1 canary beyond shadow mode;
- enabling broad proactive behavior;
- writing stable personality/profile/relationship memory;
- inspecting or publishing raw private QQ chat;
- account credentials, tokens, or external account actions;
- destructive filesystem operations;
- moving or deleting owner/runtime/private data.

## Lane A: Auto-Code Structural Work

### A1. Thin `xinyu_qq_gateway.py`

Status: `done`

Goal: keep splitting transport-adjacent helper logic out of `xinyu_qq_gateway.py` without changing visible behavior.

Allowed slices:

- extract pure timestamp, sequencing, payload-normalization, and trace-rendering helpers;
- extract small self-contained command payload builders when tests can cover them;
- keep network transport, websocket lifecycle, and send behavior stable.

Done when:

- at least three behavior-preserving gateway extraction slices are complete after `xinyu_qq_event_time.py`;
- QQ gateway smoke passes after each slice;
- full pytest passes;
- `xinyu_status.py --json` is green.

Current progress:

- `xinyu_qq_event_time.py` extracted and validated.
- `xinyu_qq_session_flow.py` extracted for session queue keys, arrival waterlines, and stale visible reply checks.
- `xinyu_qq_bridge_errors.py` extracted for bridge timeout/unavailable classification and owner-private fallback selection.
- `xinyu_qq_reception_metadata.py` extracted for inbound arrival, prepared, dispatch, and session metadata annotations.
- Evidence: targeted QQ gateway tests passed; QQ gateway smoke passed; full pytest passed with `781 passed`.

### A2. Thin `xinyu_core_bridge.py`

Status: `done`

Goal: continue moving small pure bridge helpers into focused modules without changing `/chat`, turn routing, owner gates, or memory write behavior.

Allowed slices:

- extract pure state-text/time/context helper glue already covered by tests;
- extract pure request classification helpers when existing tests cover the decision surface;
- add tests before extraction if the behavior is not already pinned.

Done when:

- at least two small behavior-preserving core bridge extractions are complete;
- targeted tests and full pytest pass;
- runtime readiness smoke passes;
- `xinyu_status.py --json` is green.

Current progress:

- `xinyu_bridge_time_utils.py` extracted for timestamp parsing and fallback ISO normalization.
- `xinyu_bridge_codex_markers.py` extracted for Codex/self-code marker parsing.
- Evidence: targeted bridge tests passed; runtime readiness smoke passed after core bridge restart; full pytest passed with `786 passed`.

### A3. Desktop Renderer/CSS Split Readiness

Status: `done`

Goal: prepare Desktop renderer/CSS splitting only after backend closeout remains green.

Allowed slices:

- inventory Desktop renderer/CSS files;
- identify safe split boundaries;
- add or run existing desktop typecheck/build checks;
- do not redesign UI during this closeout lane.

Done when:

- a Desktop split-readiness note is added with exact files and validation commands;
- desktop typecheck passes if dependencies are available;
- backend status remains green.

Evidence:

- `XINYU-DESKTOP-SPLIT-READINESS-2026-05-21.md` added.
- `npm run typecheck` passed.
- `npm run build` passed.
- Backend `xinyu_status.py --json` remained green.

## Lane B: Automatic Gate Monitoring

### B1. Stable Memory Gate

Status: `monitor_only`

Goal: prove stable self/personality/relationship writes remain blocked unless review evidence justifies a candidate.

Automatic action:

- run existing tests/status checks for AI self-iteration and personality gates;
- add regression tests only if a gap is found;
- do not promote any profile, relationship, or stable-memory candidate.

Done when:

- current gate state is documented with file/state evidence;
- tests or status confirm review-only behavior.

### B2. v1 Shadow Metrics

Status: `monitor_only`

Goal: keep v1 shadow metrics collecting without enabling owner-simple canary automatically.

Automatic action:

- run v1 readiness tests and status check;
- document current readiness decision, sample window, error rate, and switch permission.

Done when:

- readiness evidence is fresh;
- `owner_simple_canary` remains disabled unless explicit owner approval is present.

### B3. Owner-Simple Canary Block

Status: `monitor_only`

Goal: prevent accidental auto-enable of owner-simple canary.

Automatic action:

- add or keep regression coverage around `auto_full_switch=false` and owner approval requirement;
- inspect status output for canary fields.

Done when:

- regression/status evidence confirms no automatic canary switch.

### B4. Owner-Approved Canary Path

Status: `owner_approval_required`

Goal: if explicit owner approval is later given, enable only owner-private simple-message canary with fallback to the old path.

Automatic action before approval:

- keep path documented;
- keep tests ready;
- do not change live config.

Done when:

- either owner approval is absent and this remains blocked with evidence, or owner approval is present and the canary is enabled narrowly with rollback evidence.

## Lane C: Real QQ Observation

### C1. Owner-Private Probe Batch

Status: `owner_input_required`

Goal: observe real owner-private behavior for:

- ordinary greetings;
- status / how-do-you-feel self-state questions;
- template-style complaints;
- correction-after-delay cases.

Automatic preparation:

- prepare a short sanitized checklist of probe prompts;
- ensure observation stores only flags/metadata needed for calibration, not raw private chat in public artifacts.

Done when:

- owner sends the probes through QQ, or explicitly approves a local synthetic replay as substitute evidence.

### C2. Shadow Flag Inspection

Status: `owner_input_required`

Goal: inspect route/shadow flags from the live probes without publishing raw QQ text.

Automatic preparation:

- identify which traces/status fields prove route, live generation, delay handling, and fallback behavior.

Done when:

- flags are inspected after live probes and summarized without raw transcript.

### C3. Calibration Candidate Conversion

Status: `owner_input_required`

Goal: convert real owner corrections into reviewable calibration candidates.

Automatic preparation:

- verify review tooling exists and remains gated;
- prepare a no-raw-text summary format.

Done when:

- real owner corrections exist and are converted into review-only candidates.

## Completion Gate

Before this plan can be closed:

- `git status --short` is clean.
- Full pytest passes.
- QQ gateway smoke passes.
- Runtime readiness smoke passes.
- `xinyu_status.py --json` returns `"ok": true`.
- All `AUTO` items are checked.
- All `monitor_only` items have fresh evidence.
- All `owner_input_required` items are either completed from owner-provided probes or explicitly listed as blocked by missing owner input.

## Current Next Action

Continue Lane B with automatic monitoring/gate validation.
