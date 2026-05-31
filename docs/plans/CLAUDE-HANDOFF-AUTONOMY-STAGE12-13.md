# Claude Handoff: XinYu Autonomy Stage 12 -> Stage 13

created_at: 2026-05-31
owner: Atimea
director: Codex
executor: Claude
scope: XinYu autonomy loop stabilization, Stage 12 gate, Stage 13 preparation

## 0. First Reading

Claude must read these before changing code:

1. `D:\XinYu\docs\system\心玉最终目标.md`
2. `D:\XinYu\docs\system\心玉自我生成长期路线大纲.md`
3. `D:\XinYu\docs\system\XINYU-SYSTEM.md`
4. `D:\XinYu\README.md`
5. `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\README.md`

The project goal is not to make XinYu claim consciousness. The engineering target is a bounded and auditable self-generating loop:

```text
input
-> importance / anomaly judgment
-> internal state and gaps
-> candidate intentions / actions
-> gates and boundaries
-> bounded action
-> real feedback
-> memory / score / strategy update
-> changed future behavior
```

If a change does not strengthen one part of this loop, it is not a core autonomy change.

## 1. Current Repository Shape

Root: `D:\XinYu`

Important top-level areas:

- `XinYu.ps1`: unified local operator entry point for status, start/stop, tests, smoke checks and tree view.
- `scripts\`: Windows startup/shutdown helpers. Current active launchers are under `D:\XinYu\scripts`, not the deleted root-level compatibility files.
- `docs\system\`: final goal, roadmap, system spine and external-project borrowing register.
- `docs\plans\`: active and historical planning documents.
- `XinYu-Core\examples\agent-apps\xinyu\`: active Python runtime, QQ bridge, autonomy loop, memory, perception, reports and tests.
- `XinYu_Desktop\`: Electron/Vite desktop shell.
- `XinYu-TinyKernel\`: standalone local tiny decision-kernel/training project. It is not the live runtime.
- `assets\`: icons, OCR fixtures, cases and reference material.
- `runtime\`: local runtime/dependency area. Treat as machine-local unless a file is clearly a sanitized project artifact.
- `artifacts\`, `worklog\`: generated artifacts and engineering logs.

Current local worktree is very dirty. Do not run destructive commands such as `git reset --hard`, `git checkout --`, broad deletes, or mass formatting. Treat untracked and modified files as user/Codex work in progress.

## 2. Active Runtime Structure

Main app path:

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
```

Core entry points:

- `xinyu_core_bridge.py`: HTTP core bridge. Owns `/chat`, health, turn, learning, Codex and proactive routes.
- `xinyu_qq_gateway.py`: NapCat / OneBot gateway. Transport only: whitelist, group trigger, normalization, OneBot send, outbox claim/ack.
- `xinyu_status.py`: main health/status command. All stage gates should surface here.
- `xinyu.local.env.example`: config template. Never write real secrets into repo files.

Bridge and turn flow:

- `xinyu_bridge_http.py`
- `xinyu_bridge_slow_live_turn.py`
- `xinyu_bridge_turn_sidecars.py`
- `xinyu_bridge_turn_finish_sidecars.py`
- `xinyu_bridge_reply_pipeline.py`
- `xinyu_bridge_semantic_fast_routes.py`
- `xinyu_turn_completion.py`
- `xinyu_turn_classifier.py`
- `xinyu_visible_reply_guard.py`
- `xinyu_visible_text_sanitizer.py`

QQ and outbound action:

- `xinyu_qq_config.py`
- `xinyu_qq_core_client.py`
- `xinyu_qq_outbox.py`
- `xinyu_qq_outbox_dispatcher.py`
- `xinyu_qq_session_flow.py`
- `xinyu_qq_visible_dispatch.py`
- `xinyu_qq_reply_integrity_diagnostics.py`
- `xinyu_private_reply_selftest.py`

Continuity and memory:

- `xinyu_dialogue_working_memory.py`
- `xinyu_dialogue_archive.py`
- `xinyu_short_term_continuity.py`
- `xinyu_short_term_continuity_canary.py`
- `xinyu_short_term_recall_diagnostics.py`
- `xinyu_memory_candidate_extractor.py`
- `xinyu_memory_candidate_review_cli.py`
- `xinyu_memory_promotion.py`
- `xinyu_stage8_memory_review_packet.py`
- `xinyu_stage8_learning_trial_validation_packet.py`
- `xinyu_stage8_duplicate_consolidation_packet.py`

Autonomy loop and stage reports:

- `xinyu_perception_event_layer.py`
- `xinyu_perception_importance.py`
- `xinyu_attention_posture.py`
- `xinyu_relation_posture.py`
- `xinyu_intention_ecology.py`
- `xinyu_decision_chain_latest.py`
- `xinyu_feedback_consumption_diagnostics.py`
- `xinyu_action_feedback_coverage.py`
- `xinyu_owner_feedback_effects.py`
- `xinyu_autonomy_loop_report.py`
- `xinyu_stage9_self_state_model.py`
- `xinyu_stage10_proactive_life_loop.py`
- `xinyu_stage11_multisensory_extension.py`
- `xinyu_stage12_long_term_evaluation.py`

Proactive / life loop:

- `xinyu_proactive_contract.py`
- `xinyu_proactive_presence.py`
- `xinyu_proactive_request_loop.py`
- `xinyu_proactivity_scorer.py`
- `xinyu_proactive_context_adapter.py`
- `xinyu_proactive_direct_sender.py`
- `xinyu_proactive_response_diagnostics.py`

Multisensory:

- `xinyu_image_context.py`
- `xinyu_paddle_ocr_command.py`
- `xinyu_paddlex_voice_stt.py`
- `xinyu_qq_voice_transcript.py`
- `xinyu_stage11_visual_ingress_diagnostics.py`
- `xinyu_stage11_voice_ingress_diagnostics.py`
- `xinyu_tts_output.py`
- `xinyu_speech_controller.py`

Tests:

- `tests\` currently has about 197 `test_*.py` files.
- Prefer targeted tests around touched modules before broader suites.

## 3. Desktop Structure

Path:

```text
D:\XinYu\XinYu_Desktop
```

Stack:

- Electron 31
- Vite 5
- React 18
- TypeScript
- `lucide-react`

Important files:

- `package.json`: scripts are `npm run dev`, `npm run typecheck`, `npm run build`.
- `src\main\index.ts`: Electron main entry.
- `src\main\api_config.ts`: desktop-side API config handling.
- `src\main\qq_environment.ts`: QQ/runtime environment bridge.
- `src\preload\index.ts`: preload API.
- `src\renderer\src\DesktopPanels.tsx`: main panel UI.
- `src\renderer\src\desktopModel.ts`
- `src\renderer\src\desktopTypes.ts`
- `src\renderer\src\style.css`
- `src\renderer\src\styles\qq-panels.css`

Do not make frontend work the main focus unless the Stage 12 gate needs an owner-visible status/config panel.

## 4. TinyKernel Boundary

Path:

```text
D:\XinYu\XinYu-TinyKernel
```

TinyKernel is standalone. It is not live XinYu. It must not own QQ, Desktop, Codex, memory persistence or tool execution.

Allowed role:

- learn a narrow inner decision layer
- suggest reply / clarify / wait / tool intent / memory candidate modes
- serve local fallback or expression/strategy support

Forbidden:

- training directly on raw private runtime files
- writing outside `D:\XinYu\XinYu-TinyKernel`
- treating TinyKernel output as fact source
- letting it execute tools directly

Do not start Stage 13 TinyKernel expansion until Stage 12 is ready.

## 5. Current Runtime Snapshot

Command used:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
python xinyu_status.py
```

Observed on 2026-05-31:

- `core_bridge`: OK, version `0.8.99`.
- `xinyu_qq_gateway_6199`: OK.
- `napcat_to_xinyu_qq_gateway_ws`: OK.
- `qq_private_reply_flow`: `reply_sent`.
- `short_term_continuity_canary`: `pass`, recall success `100.0`.
- `feedback_consumption_diagnostics`: `pass`, `183/183`, rate `100.0`.
- `action_feedback_coverage`: `pass`, 7 surfaces observed, non-QQ surfaces observed.
- `owner_feedback_effect`: WARN, current signal `memory_mechanics_leak`, `future_effect=none`.
- `memory_learning_trial_gate`: `blocked`.
- `stage8_memory_governance`: `active_guarded`, `ready_stage9=false`.
- `stage9_self_state_model`: `active`, `ready_stage10=true`.
- `stage10_proactive_life_loop`: `active`, `ready_stage11=true`.
- `stage11_multisensory_extension`: `active`, `ready_stage12=true`.
- `stage12_long_term_evaluation`: WARN, `active_needs_check`.
- `stage12_ready_for_stage13`: `false`.
- `stage12_live_loop_status`: `needs_check`.
- `stage12_live_loop_required_pass_rate_pct`: latest observed `83.33`.
- `stage12_latest_dialogue_recall_status`: latest observed `no_samples`.
- `stage12_historical_dialogue_recall_debt_status`: `debt_present`, issue count `2`.
- `stage12_next_step`: `tighten_long_term_metrics_before_stage13`.

Meaning:

XinYu is not blocked at the early architecture level. It has working transport, short-term recall canary, feedback consumption, action feedback coverage, Stage 9 self-state, Stage 10 proactive life loop and Stage 11 multisensory input. The current blocker is Stage 12: long-term evaluation is not clean enough to start Stage 13.

## 6. Local Code Intelligence Status

Command used:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\projects\_tools\code-intel-pipeline\check-code-intel-tools.ps1 -RepoPath D:\XinYu -Json
```

Result:

- `rg`: found.
- `git`: found.
- `repowise`: found.
- `sentrux`: missing.
- Understand Anything graph/plugin: missing.
- Sentrux rules/baseline: missing.

Claude should not claim structural pipeline coverage is clean. Use `rg`, targeted tests and status reports until Sentrux / Understand are installed or repaired.

## 7. Immediate Direction

Do not start by adding personality, dream text, emotion vocabulary or more proactive messages.

The next engineering objective is:

```text
Make Stage 12 pass cleanly, while preserving the historical debt signal.
```

Stage 13 can only start when:

- `stage12_long_term_evaluation_status=active_ready_for_stage13`
- `stage12_ready_for_stage13=true`
- `stage12_gate_live_loop_required_checks_pass=true`
- latest dialogue recall has real recent samples and passes
- feedback consumption stays clean
- raw private leak count remains zero
- stable memory miswrite count remains zero
- owner-visible canary is still ready

## 8. Claude Work Plan

### Phase A: Stage 12 diagnosis and gate repair

Goal: turn current Stage 12 from `active_needs_check` to `active_ready_for_stage13` without hiding historical debt.

Files to inspect first:

- `xinyu_stage12_long_term_evaluation.py`
- `xinyu_status.py`
- `xinyu_live_loop_report.py`
- `xinyu_short_term_continuity_canary.py`
- `xinyu_short_term_recall_diagnostics.py`
- `xinyu_dialogue_working_memory.py`
- `xinyu_dialogue_archive.py`
- `tests\test_stage12_long_term_evaluation.py`
- `tests\test_short_term_continuity_canary.py`
- `tests\test_short_term_recall_diagnostics.py`

Tasks:

1. Find why latest Stage 12 recall reports `no_samples` even though private chat is active.
2. Make recent-sample detection deterministic and visible in `xinyu_status.py`.
3. Keep old recall failures as historical debt, but do not let stale historical debt block the recent gate.
4. Find which live-loop required check is failing when pass rate is below 100%.
5. Add or update tests so this exact state is covered.

Acceptance:

```text
python xinyu_status.py
```

must show:

- latest recall status is `pass`, not `no_samples`
- live loop gate passes or reports the exact failing check
- Stage 12 does not regress privacy boundaries

Targeted tests:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
python -m pytest tests\test_stage12_long_term_evaluation.py tests\test_short_term_continuity_canary.py tests\test_short_term_recall_diagnostics.py tests\test_live_loop_report.py -q
```

### Phase B: Owner feedback effect for "memory mechanics leak"

Goal: owner correction must change future behavior. Current `owner_feedback_effect` has `memory_mechanics_leak` but `future_effect=none`, which weakens the autonomy loop.

Files to inspect first:

- `xinyu_owner_feedback_effects.py`
- `xinyu_feedback_consumption_diagnostics.py`
- `xinyu_visible_text_sanitizer.py`
- `xinyu_expression_contract.py`
- `xinyu_decision_chain_latest.py`
- `tests\test_owner_feedback_effects.py`
- `tests\test_feedback_consumption_diagnostics.py`
- `tests\test_expression_contract.py`

Tasks:

1. Define a concrete future effect for `memory_mechanics_leak`.
2. The effect should bias future visible replies away from exposing memory machinery unless the owner explicitly asks for diagnostics.
3. Do not suppress useful technical diagnostics in Codex/operator contexts.
4. Surface the effect in status/report fields.

Suggested future effect:

```text
avoid_memory_mechanics_in_visible_reply_unless_owner_requests_diagnostics
```

Acceptance:

- `owner_feedback_effect_future_effect` is no longer `none` for this signal.
- Feedback consumption still reports consumed.
- Visible reply behavior has a test proving the bias is applied.

Targeted tests:

```powershell
python -m pytest tests\test_owner_feedback_effects.py tests\test_feedback_consumption_diagnostics.py tests\test_expression_contract.py -q
```

### Phase C: Memory governance unlock path, not automatic promotion

Goal: make the path from trial learning to stable memory review clearer without bypassing owner approval.

Current state:

- `memory_learning_trial_gate=blocked`
- `stage8_memory_governance=active_guarded`
- `stable_profile_write=blocked_review_only_not_auto_apply`
- `owner_memory_write=blocked_owner_review_required`

Files to inspect first:

- `xinyu_stage8_learning_trial_validation_packet.py`
- `xinyu_stage8_memory_review_packet.py`
- `xinyu_memory_candidate_review_cli.py`
- `xinyu_memory_promotion.py`
- `xinyu_review_inbox.py`
- `tests\test_stage8_learning_trial_validation_packet.py`
- `tests\test_stage8_memory_review_packet.py`
- `tests\test_memory_promotion.py`

Tasks:

1. Do not auto-promote stable memory.
2. Produce an owner-visible review packet for the active blocked learning key.
3. Ensure the packet explains source, reason, boundary, required success signal and rollback path.
4. Add status fields that tell owner what exactly needs approval or more samples.

Acceptance:

- Stage 8 remains guarded.
- The owner can see what would be approved.
- No private raw body is exposed.
- Stable memory writes remain blocked unless explicit owner approval exists.

Targeted tests:

```powershell
python -m pytest tests\test_stage8_learning_trial_validation_packet.py tests\test_stage8_memory_review_packet.py tests\test_memory_promotion.py tests\test_memory_review_inbox_integration.py -q
```

### Phase D: Stage 13 skeleton only after Stage 12 passes

Do not implement full Stage 13 until Stage 12 is green.

When Stage 12 is green, create a minimal Stage 13 report module only:

Possible files:

- `xinyu_stage13_self_narrative.py`
- `tests\test_stage13_self_narrative.py`

Stage 13 must not claim subjective consciousness. It should only summarize:

- which verified feedback changed expression
- which approved memory or strategy influenced behavior
- which current limits still constrain action
- why a reply, silence or proactive candidate happened

Acceptance:

- Stage 13 report is generated from verifiable fields only.
- No dreams, fake body, fake sensor claims or unverified facts.
- `xinyu_status.py` exposes Stage 13 as `available` or `waiting_for_stage12`, not as "consciousness complete".

### Phase E: Frontend only if needed for owner review

Frontend work is secondary unless Phase B/C needs an owner-visible review panel.

Relevant files:

- `D:\XinYu\XinYu_Desktop\src\renderer\src\DesktopPanels.tsx`
- `D:\XinYu\XinYu_Desktop\src\renderer\src\desktopModel.ts`
- `D:\XinYu\XinYu_Desktop\src\renderer\src\desktopTypes.ts`
- `D:\XinYu\XinYu_Desktop\src\main\api_config.ts`

Checks:

```powershell
cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

## 9. Command Checklist for Claude

Start every session:

```powershell
cd D:\XinYu
git status --short
.\XinYu.ps1 status
```

If `XinYu.ps1 status` fails, fall back to:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
python xinyu_status.py
```

Before editing a module:

```powershell
rg -n "target_symbol_or_status_field" D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
```

After editing:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
python -m pytest <targeted-tests> -q
python xinyu_status.py
```

Only run full tests when targeted tests pass:

```powershell
python -m pytest tests -q
```

## 10. Rules for Claude

- Do not revert unrelated changes.
- Do not delete untracked files.
- Do not move large directories unless explicitly asked.
- Do not write API keys or tokens into repo files.
- Do not hide Stage 12 failures by weakening gates.
- Do not remove historical recall debt; keep it visible as debt.
- Do not promote stable memory automatically.
- Do not make XinYu claim consciousness.
- Do not use AGPL or other strong-copyleft project code directly. Borrow ideas only, and register external borrowing in `D:\XinYu\docs\system\外部项目借鉴登记.md`.
- Any new module must add at least one test, trace, report field or status signal.

## 11. Expected First Claude PR / Patch Batch

The first batch should be narrow:

1. Diagnose `stage12_latest_dialogue_recall_status=no_samples`.
2. Fix or expose the missing recent-sample path.
3. Diagnose the non-passing Stage 12 live-loop check.
4. Add tests for the real failure mode.
5. Add `memory_mechanics_leak` future effect.
6. Rerun targeted tests and `python xinyu_status.py`.

Do not start TinyKernel or Stage 13 code in the first batch.

## 12. What "Done" Means for This Handoff

Claude's first handoff back to Codex should include:

- changed files
- exact tests run
- `xinyu_status.py` key Stage 12 lines
- whether `stage12_ready_for_stage13` is true
- any remaining blocker with exact status field names
- whether private raw text or visible reply text leaked into reports

Codex remains the architecture director. Claude's role is execution under this plan.
