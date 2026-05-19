# XinYu Integration Closeout Plan - 2026-05-11

## Goal

Close the interrupted post-Loop-144 integration safely.

The current worktree contains several completed-but-uncommitted integration slices. The next agent should not add new features. It should split the dirty worktree into coherent reviewable commits, validate each slice, and leave the live XinYu runtime in a known-good state.

## Current Baseline

- Branch: `master`
- Last recorded complete loop: Loop 144 in `worklog/24h-refactor-progress.md`
- Current live status after local repair:
  - `xinyu_status.py --json`: ok
  - Core bridge: running on `127.0.0.1:8765`
  - QQ gateway: running on `127.0.0.1:6199`
  - NapCat: reachable on `127.0.0.1:6099`
  - Core source digest and runtime source digest match current source
  - QQ gateway log no longer repeats `core bridge HTTP 502`
- `diagnostics/check_xinyu_health.py --json --workspace D:\XinYu`: warn only because `git_state` is dirty

## Hard Rules

- Do not add new product behavior while closing out this batch.
- Do not edit long-term memory body text.
- Do not run real QQ outbound tests.
- Do not widen v1 real traffic.
- Do not use destructive git commands.
- Do not collapse all changes into one commit.
- Keep each commit reversible with `git revert <commit>`.
- If any slice fails validation twice, stop and split it smaller.

## Recommended Model

GPT-5.4 can continue this work.

Reason: the remaining task is disciplined local engineering work: inspect diffs, group related files, run deterministic smoke tests, fix narrow breakages, record results, and commit. It does not require broad new architecture design. The main risk is accidental overreach, so the agent should follow this plan strictly and avoid inventing new subsystems.

Use GPT-5.5 only if:

- a live-turn behavior regression appears and needs deeper diagnosis,
- several independent validation failures interact,
- the dirty diff turns out to hide an architectural conflict.

## Phase 0 - Reconfirm State

Run from `D:\XinYu`:

```powershell
git status --short --branch
git log --oneline -5
git diff --check
```

Run from `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`:

```powershell
.\.venv\Scripts\python.exe xinyu_status.py --json
```

Expected:

- `xinyu_status.py --json` returns `ok: true`.
- `git diff --check` has no whitespace errors.
- Dirty files are expected, but must be understood before committing.

## Phase 1 - Slice Runtime Freshness And Outbox State

Purpose:

- Close the stale runtime failure loop that made old failures keep driving proactivity.
- Add QQ outbox recent failure/dead summaries so old dead items do not stay actionable forever.

Primary files:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_runtime_failure_freshness.py`
- `XinYu-Core/examples/agent-apps/xinyu/runtime_failure_freshness_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_outbox_state.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_outbox.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_runtime_presence.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_proactivity_scorer.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_impulse_soup.py`
- `XinYu-Core/examples/agent-apps/xinyu/tests/test_runtime_program_awareness.py`
- `XINYU-VALIDATION-MATRIX.md`

Validation:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile xinyu_runtime_failure_freshness.py runtime_failure_freshness_smoke.py xinyu_qq_outbox_state.py xinyu_qq_outbox.py xinyu_runtime_presence.py xinyu_proactivity_scorer.py xinyu_impulse_soup.py
.\.venv\Scripts\python.exe runtime_failure_freshness_smoke.py
.\.venv\Scripts\python.exe qq_outbox_smoke.py
.\.venv\Scripts\python.exe proactivity_scorer_smoke.py
.\.venv\Scripts\python.exe impulse_soup_smoke.py
.\.venv\Scripts\python.exe -m pytest tests\test_runtime_program_awareness.py -q
git -C D:\XinYu diff --check
```

Commit message:

```text
refactor: gate stale runtime failure signals
```

## Phase 2 - Slice Memory Braid, Turn Coherence, Initiative Spine

Purpose:

- Close the live-turn orchestration layer added after Loop 144.
- Keep memory/action/thought coherence as sidecar state, not long-term memory rewrite.
- Record proactive feedback into initiative state.

Primary files:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_memory_braid.py`
- `XinYu-Core/examples/agent-apps/xinyu/memory_braid_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_turn_coherence.py`
- `XinYu-Core/examples/agent-apps/xinyu/turn_coherence_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_initiative_spine.py`
- `XinYu-Core/examples/agent-apps/xinyu/initiative_spine_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/proactive_feedback_spine_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_turn_pipeline.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_runtime_context.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_core_bridge.py`
- `XinYu-Core/examples/agent-apps/xinyu/smoke_run.py`

Validation:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile xinyu_memory_braid.py memory_braid_smoke.py xinyu_turn_coherence.py turn_coherence_smoke.py xinyu_initiative_spine.py initiative_spine_smoke.py proactive_feedback_spine_smoke.py xinyu_bridge_turn_pipeline.py xinyu_runtime_context.py xinyu_core_bridge.py smoke_run.py
.\.venv\Scripts\python.exe memory_braid_smoke.py
.\.venv\Scripts\python.exe turn_coherence_smoke.py
.\.venv\Scripts\python.exe initiative_spine_smoke.py
.\.venv\Scripts\python.exe proactive_feedback_spine_smoke.py
.\.venv\Scripts\python.exe bridge_probe_smoke.py
git -C D:\XinYu diff --check
```

Commit message:

```text
feat: add live turn coherence sidecars
```

## Phase 3 - Slice Emotion Council And Speech Guards

Purpose:

- Add emotion council as shadow/prompt-gated sidecar.
- Prevent visible mechanics leaks.
- Preserve owner visible address behavior.
- Keep visible reply policy conservative.

Primary files:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_emotion_council.py`
- `XinYu-Core/examples/agent-apps/xinyu/emotion_council_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/project-plans/XINYU-EMOTION-COUNCIL-PLAN.md`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_speech_controller.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_speech_controller_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_renderer.py`
- `XinYu-Core/examples/agent-apps/xinyu/bridge_renderer_guard_flags_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/mojibake_guard_smoke.py`

Validation:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile xinyu_emotion_council.py emotion_council_smoke.py xinyu_speech_controller.py xinyu_speech_controller_smoke.py xinyu_bridge_renderer.py bridge_renderer_guard_flags_smoke.py mojibake_guard_smoke.py
.\.venv\Scripts\python.exe emotion_council_smoke.py
.\.venv\Scripts\python.exe xinyu_speech_controller_smoke.py
.\.venv\Scripts\python.exe bridge_renderer_guard_flags_smoke.py
.\.venv\Scripts\python.exe mojibake_guard_smoke.py
git -C D:\XinYu diff --check
```

Commit message:

```text
feat: add emotion council shadow guardrails
```

## Phase 4 - Slice Proactive Request And Review Inbox Integration

Purpose:

- Close any remaining changed proactive request/review inbox/self-thought behavior.
- Ensure owner feedback on proactive requests is absorbed instead of spawning new initiative blindly.

Primary files:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_proactive_request_loop.py`
- `XinYu-Core/examples/agent-apps/xinyu/proactive_request_loop_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_review_inbox.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_review_inbox_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_self_thought_loop.py`
- `XinYu-Core/examples/agent-apps/xinyu/self_thought_loop_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/tests/test_learning_closed_loop.py`

Validation:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile xinyu_proactive_request_loop.py proactive_request_loop_smoke.py xinyu_review_inbox.py xinyu_review_inbox_smoke.py xinyu_self_thought_loop.py self_thought_loop_smoke.py
.\.venv\Scripts\python.exe proactive_request_loop_smoke.py
.\.venv\Scripts\python.exe xinyu_review_inbox_smoke.py
.\.venv\Scripts\python.exe self_thought_loop_smoke.py
.\.venv\Scripts\python.exe -m pytest tests\test_learning_closed_loop.py -q
git -C D:\XinYu diff --check
```

Commit message:

```text
refactor: connect proactive feedback state
```

## Phase 5 - Slice Live Status, Source Digests, And Proxy Bypass

Purpose:

- Make live status detect whether running code matches source.
- Fix Windows proxy interference for local loopback HTTP checks.
- Stop health diagnostics from treating pre-restart QQ gateway text logs as active errors.

Primary files:

- `XinYu-Core/examples/agent-apps/xinyu/xinyu_runtime_security.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_status.py`
- `XinYu-Core/examples/agent-apps/xinyu/deployment_status_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_core_client.py`
- `XinYu-Core/examples/agent-apps/xinyu/bridge_probe_smoke.py`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_desktop_rest_smoke.py`
- `D:\XinYu\diagnostics\check_xinyu_health.py`

Validation:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile xinyu_runtime_security.py xinyu_status.py deployment_status_smoke.py xinyu_qq_core_client.py bridge_probe_smoke.py xinyu_desktop_rest_smoke.py
.\.venv\Scripts\python.exe qq_core_client_smoke.py
.\.venv\Scripts\python.exe xinyu_status.py --json
.\.venv\Scripts\python.exe deployment_status_smoke.py
.\.venv\Scripts\python.exe bridge_probe_smoke.py

cd D:\XinYu
D:\XinYu\Python312\python.exe -m py_compile diagnostics\check_xinyu_health.py
D:\XinYu\Python312\python.exe diagnostics\check_xinyu_health.py --json --workspace D:\XinYu
git diff --check
```

Expected:

- `xinyu_status.py --json` is ok.
- `deployment_status_smoke.py` is ok.
- Health is `warn` only due to dirty git state before final commits.
- QQ gateway log tail does not contain new `core bridge HTTP 502` lines after the latest `listening on` line.

Commit message:

```text
fix: bypass proxy for local XinYu health checks
```

## Phase 6 - Slice Plugin Lazy Init Fix

Purpose:

- Keep plugin gating robust even if a plugin subclass forgets `super().__init__()`.

Primary files:

- `XinYu-Core/src/xinyu_runtime/modules/plugin/base.py`
- `XinYu-Core/tests/test_plugin_base.py`

Validation:

```powershell
cd D:\XinYu\XinYu-Core
$env:PYTHONPATH = "D:\XinYu\XinYu-Core\src"
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\.venv\Scripts\python.exe -m pytest tests\test_plugin_base.py -q
git -C D:\XinYu diff --check
```

Commit message:

```text
fix: lazily initialize plugin model patterns
```

## Phase 7 - Final Live Verification

After all commits:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_status.py --json
.\.venv\Scripts\python.exe deployment_status_smoke.py
.\.venv\Scripts\python.exe bridge_probe_smoke.py
.\.venv\Scripts\python.exe xinyu_qq_gateway_smoke.py
.\.venv\Scripts\python.exe xinyu_qq_review_smoke.py

cd D:\XinYu
D:\XinYu\Python312\python.exe diagnostics\check_xinyu_health.py --json --workspace D:\XinYu
git status --short --branch
```

Expected:

- Live status ok.
- Deployment smoke ok.
- Bridge probe ok.
- QQ gateway/review smoke ok.
- Health ok or warn only for intentionally untracked plan files.
- No unrelated runtime or memory body files staged.

## Recording

Append a closeout entry to:

```text
worklog/24h-refactor-progress.md
```

Suggested format:

```md
## Closeout - 2026-05-11

- Task: Close interrupted post-Loop-144 integration batch.
- Slices committed:
  - ...
- Commands:
  - ...
- Result:
  - ...
- Risk:
  - ...
- Next:
  - ...
```

## Stop Conditions

Stop and report before committing if:

- `xinyu_status.py --json` fails after the proxy bypass patch.
- QQ gateway starts logging new `core bridge HTTP 502` after restart.
- Any smoke edits memory body files outside expected runtime/state fixtures.
- A slice requires changing prompt/persona semantics to pass.
- A slice changes real QQ outbound behavior.
- v1 canary scope changes.
