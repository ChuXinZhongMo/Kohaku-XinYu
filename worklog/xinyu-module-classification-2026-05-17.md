# XinYu Module Classification - 2026-05-17

Status: first autonomous classification map. This is a decision map, not a code move.

Owner override 2026-05-17:

- Owner granted local full-permission autonomy until the subtractive refactor plan is complete.
- Private local logs/runtime/memory state may now be inspected for diagnosis and cleanup.
- Chat output must still stay redacted: no secrets, raw QQ/private dialogue, raw memory contents, or credentials.
- Destructive cleanup still requires local evidence and backup unless the target is clearly generated disposable residue.

Update 2026-05-17:

- Added `xinyu_living_memory_recall.py` as the canonical public owner surface for living recall.
- Updated `xinyu_core_bridge.py` to call `retrieve_living_memory(...)` and `log_living_memory_recall(...)`.
- Kept `xinyu_context_retrieval.py` behavior and old public API intact as the implementation/compatibility layer.
- Added `tests/test_living_memory_recall.py`.
- Validation passed:
  - `.\.venv\Scripts\python.exe -m py_compile xinyu_living_memory_recall.py xinyu_context_retrieval.py xinyu_core_bridge.py`
  - `.\.venv\Scripts\python.exe -m pytest tests\test_living_memory_recall.py tests\test_retrieval_need_reranker.py tests\test_sparse_memory_router.py tests\test_context_retrieval_owner_scenarios.py -q`
  - result: `12 passed`
- Follow-up migration:
  - Marked `xinyu_context_retrieval.py` as the implementation/compatibility layer.
  - Updated `xinyu_chat_replay_fixture_exporter.py` retrieval validation to call `retrieve_living_memory(...)`.
  - Validation passed:
    - `.\.venv\Scripts\python.exe -m py_compile xinyu_living_memory_recall.py xinyu_context_retrieval.py xinyu_chat_replay_fixture_exporter.py xinyu_core_bridge.py`
    - `.\.venv\Scripts\python.exe -m pytest tests\test_living_memory_recall.py tests\test_chat_replay_fixture_exporter.py tests\test_retrieval_replay_cases.py tests\test_context_retrieval_owner_scenarios.py -q`
    - result: `16 passed`
  - Replay smoke passed:
    - `.\.venv\Scripts\python.exe smoke_run.py --group replay`
    - result: `21 passed`, `smoke_run group=replay: ok`
- Public recall bucket shape:
  - Added `LivingMemoryRecallBuckets` and `bucket_living_memory_recall(...)`.
  - Buckets are `must_remember`, `experience_hints`, `uncertainties`, and `trace`.
  - This is a pure public-shape helper and does not change rendered prompt behavior.
  - Validation passed:
    - `.\.venv\Scripts\python.exe -m py_compile xinyu_living_memory_recall.py tests\test_living_memory_recall.py`
    - `.\.venv\Scripts\python.exe -m pytest tests\test_living_memory_recall.py tests\test_retrieval_need_reranker.py tests\test_sparse_memory_router.py tests\test_context_retrieval_owner_scenarios.py -q`
    - result: `13 passed`
- Public recall import migration:
  - Migrated retrieval replay, owner scenario, chat replay exporter, context retrieval smoke, temporal trace smoke, dialogue privacy smoke, and context self-preservation smoke to import the public owner surface.
  - Remaining direct import of old `retrieve_recalled_context(...)` is internal to `xinyu_living_memory_recall.py`.
  - Validation passed:
    - `.\.venv\Scripts\python.exe -m py_compile xinyu_living_memory_recall.py xinyu_context_retrieval.py xinyu_chat_replay_fixture_exporter.py xinyu_core_bridge.py tests\smoke\memory\context_retrieval_smoke.py tests\smoke\dialogue\temporal_trace_smoke.py tests\smoke\dialogue\dialogue_privacy_scope_smoke.py tests\smoke\dialogue\context_self_preservation_smoke.py`
    - `.\.venv\Scripts\python.exe -m pytest tests\test_living_memory_recall.py tests\test_chat_replay_fixture_exporter.py tests\test_retrieval_replay_cases.py tests\test_context_retrieval_owner_scenarios.py tests\test_retrieval_need_reranker.py tests\test_sparse_memory_router.py -q`
    - result: `23 passed`
    - `.\.venv\Scripts\python.exe smoke_run.py --group replay`
    - result: `21 passed`, `smoke_run group=replay: ok`

## Classification Rules

| Target category | Meaning |
| --- | --- |
| `core` | XinYu-specific turn chain, memory recall, persona, policy, living state |
| `adapters` | QQ, Desktop, HTTP bridge, Codex, CLI, external transport |
| `stores` | archive, file IO, state IO, manifests, persistence helpers |
| `services` | embedding, LLM, OCR, search, diagnostics, replay support |
| `ops` | start/stop, status, health, migrations, smoke runner |
| `lab` | experiments or shadow systems not allowed to affect live behavior directly |
| `archive` | historical code/docs not imported by live code |
| `delete` | only after no import/config/test/startup reference remains |

## Production Path Classification

| File or area | Target | Action | Evidence / note |
| --- | --- | --- | --- |
| `xinyu_core_bridge.py` | `adapters` now, thinner `core` caller later | keep, reduce | production `/chat`, `/health`, desktop routes; must not grow |
| `xinyu_qq_gateway.py` | `adapters` | keep, reduce | production NapCat/OneBot bridge |
| `xinyu_bridge_*.py` | `adapters` | keep/merge by route group | bridge helpers should not own memory/persona decisions |
| `xinyu_qq_*.py` | `adapters` | keep/merge by transport role | QQ helpers already partly extracted |
| `start_xinyu_core_bridge.ps1` | `ops` | keep | startup path |
| `start_xinyu_qq_gateway.ps1` | `ops` | keep | startup path |
| root `Start-XinYu-*.ps1/.bat` | `ops` | keep | user-facing startup |
| `XinYu_Desktop/src/main/*` | `adapters` | keep, typecheck | desktop adapter/event surface |

## Memory And Recall Classification

| File | Target | Action | Risk |
| --- | --- | --- | --- |
| `xinyu_living_memory_recall.py` | `core` | keep canonical live owner: `run_living_memory_recall_algorithm(...)` | owner API must stay stable |
| `xinyu_context_retrieval.py` | `core` provider/compat | keep implementation provider and old public API | old callers must remain shimmed |
| `xinyu_retrieval_envelope.py` | `core` | keep; internal candidate metadata | used by recall and cases |
| `xinyu_retrieval_need_reranker.py` | `core` | keep; internal scoring component | used by recall and cases |
| `xinyu_sparse_memory_router.py` | `core` | keep; internal route component | used by recall |
| `xinyu_dialogue_archive.py` | `stores` | keep; storage/search provider | large, many tests/imports |
| `xinyu_conversation_experience_matcher.py` | `core` provider | keep advisory case provider | must not become hard behavior rule |
| `xinyu_conversation_experience_cases.py` | `stores` / `services` | keep; reviewed case data access | privacy/source-scope risk |
| `xinyu_conversation_experience_sidecar.py` | `core` provider | keep hidden advisory prompt provider | current turn must outrank case hints |
| `xinyu_contextual_recall.py` | `core` provider | keep renderer/offline context pack | not canonical living-memory recall |
| `xinyu_contextual_self_loop.py` | `core` provider | keep runtime scene/pressure provider | should not choose recalled facts |
| `xinyu_contextual_self_observatory.py` | `ops` | keep observability/no behavior change | reads traces, must not alter behavior |
| `xinyu_contextual_self_replay.py` | `lab` | keep public dataset replay/calibration tool | offline only |
| `xinyu_recent_context_guard.py` | `stores` / guard | keep | imported by bridge |
| `xinyu_memory_*` | mixed `stores/core/lab` | classify one by one | memory event sourcing may stay; self-review may become lab |

Update 2026-05-17 recall boundary refresh:

- `xinyu_living_memory_recall.py` now exports explicit canonical owner/result/provider constants.
- `xinyu_context_retrieval.py` now exports `CONTEXT_RETRIEVAL_ROLE = "provider/compatibility"`.
- Contextual recall/self-loop/observatory/replay modules now export role and boundary constants proving they are providers, observability, or offline lab replay rather than competing recall owners.
- Conversation experience matcher/sidecar now export advisory provider roles and point back to the canonical recall owner.
- Validation records:
  - `worklog/xinyu-recall-owner-shim-boundary-2026-05-17.md`
  - `worklog/xinyu-recall-adjacent-boundaries-2026-05-17.md`

## Persona, Voice, Emotion Classification

| File or area | Target | Action | Note |
| --- | --- | --- | --- |
| `xinyu_persona_runtime.py` | `core` | keep as persona runtime owner candidate | stable runtime behavior |
| `xinyu_visible_persona_voice.py` | `core` | keep, later fold with persona runtime | visible voice policy |
| `xinyu_persona_state.py` | `core/stores` | inspect before merge | likely state projection |
| `xinyu_personality_evolution.py` | `lab` unless directly required | keep until import evidence checked | avoid unreviewed personality drift |
| `xinyu_personality_self_review.py` | `lab` candidate | keep until import evidence checked | review/growth chain |
| `xinyu_emotion_council.py` | `core` living-state or `lab` | reduce later | large emotion sidecar; should become modulation, not separate decision owner |
| `xinyu_voice_learning.py` | `lab` candidate | keep until import evidence checked | learning/growth |
| `xinyu_voice_promotion_gate.py` | `lab` candidate | keep until import evidence checked | gate chain |
| `xinyu_voice_trial_overlay.py` | `lab` candidate | keep until import evidence checked | trial overlay |
| `prompts/system.md` | `core` | compress later | stable instruction source |
| `prompts/output.md` | `core` | compress later | output style boundary |
| `prompts/live_voice_card.md` | `core` | keep as dynamic card | runtime visible voice |
| writer prompts | `core/stores` | reduce duplication later | must preserve writer tools |

Update 2026-05-17:

- Added `RUNTIME_BOUNDARY_LINES` to `xinyu_persona_runtime.py`.
- The runtime persona prompt now has a small `Runtime Boundaries` section:
  - stable anchor outranks temporary mood
  - living state can tint a reply but cannot rewrite stable personality
  - voice policy avoids service-script/product language
  - stable change requires repeated or owner-approved evidence
- Added `tests/test_persona_runtime_boundaries.py`.
  - Validation passed:
    - `.\.venv\Scripts\python.exe -m py_compile xinyu_persona_runtime.py tests\test_persona_runtime_boundaries.py`
  - `.\.venv\Scripts\python.exe -m pytest tests\test_persona_runtime_boundaries.py tests\test_visible_persona_voice.py -q`
  - result: `4 passed`
  - `.\.venv\Scripts\python.exe tests\smoke\voice\integration\persona_contract_absence_smoke.py`
  - result: `Persona contract absence smoke passed`
  - `.\.venv\Scripts\python.exe smoke_run.py --group voice`
  - result: `smoke_run group=voice: ok`

## Runtime Readiness Check

Update 2026-05-17:

- Ran:
  - `.\.venv\Scripts\python.exe tests\smoke\runtime\integration\runtime_readiness_smoke.py`
- Result: failed.
- Passing subchecks:
  - `bridge_probe`
  - `session_cleanup`
  - `mojibake_guard`
- Failing subchecks:
  - `deployment_status`
  - `long_run_status --require-no-residue`
- The command generated a private `logs/runtime_readiness_20260517T092317` directory. I did not open those logs because the autonomous plan forbids reading raw private logs without a redacted procedure.
- Current interpretation: focused retrieval and voice slices are green; full readiness is blocked by deployment/long-run residue state that needs either a redacted log review or owner approval to inspect.

Desktop validation after the runtime readiness failure:

- `npm run typecheck` in `D:\XinYu\XinYu_Desktop`: passed.
- `npm run build` in `D:\XinYu\XinYu_Desktop`: passed.

Owner override follow-up:

- After owner granted local full-permission autonomy, I inspected the readiness logs.
- Root cause was stale running Core Bridge source digest, not the recall/persona changes.
- Ran:
  - `.\start_xinyu_core_bridge.ps1 -ForceRestart -RequireVersion -AllowInsecureLlmHttp -RendererMode off -HealthTimeoutSeconds 90`
  - `.\.venv\Scripts\python.exe xinyu_status.py --json`
  - `.\.venv\Scripts\python.exe tests\smoke\runtime\integration\runtime_readiness_smoke.py`
- Result:
  - `xinyu_status.py --json`: `ok: true`
  - `runtime_readiness_smoke.py`: `ok`
- New readiness log directory: `logs/runtime_readiness_20260517T092917`

Generated residue cleanup:

- Verified `_tmp_xinyu_probe` had no repository references.
- Verified resolved path `D:\XinYu\_tmp_xinyu_probe` was under `D:\XinYu`.
- Removed untracked temporary probe directory:
  - files: 13115
  - directories: 2518

Runtime source awareness:

- Added these recall files to `BRIDGE_RUNTIME_SOURCE_RELS` in `xinyu_runtime_security.py`:
  - `xinyu_living_memory_recall.py`
  - `xinyu_context_retrieval.py`
  - `xinyu_retrieval_envelope.py`
  - `xinyu_retrieval_need_reranker.py`
  - `xinyu_sparse_memory_router.py`
- Reason: living recall is now part of the core turn path and must be included in restart/code-awareness digests.
- Validation passed:
  - `.\.venv\Scripts\python.exe -m py_compile xinyu_runtime_security.py xinyu_code_awareness.py tests\test_code_awareness.py`
  - `.\.venv\Scripts\python.exe -m pytest tests\test_code_awareness.py -q`
  - result: `2 passed`

Implementation-layer import cleanup:

- Migrated remaining non-owner direct imports of `xinyu_context_retrieval` in tests/smokes to `xinyu_living_memory_recall`.
- Remaining `xinyu_context_retrieval` import is only inside `xinyu_living_memory_recall.py`.
- Validation passed:
  - `.\.venv\Scripts\python.exe -m py_compile tests\test_retrieval_need_reranker.py tests\test_sparse_memory_router.py tests\smoke\voice\integration\xinyu_style_pressure_regression_smoke.py`
  - `.\.venv\Scripts\python.exe -m pytest tests\test_retrieval_need_reranker.py tests\test_sparse_memory_router.py tests\test_living_memory_recall.py -q`
  - result: `10 passed`

Generated cache cleanup:

- Removed 51 non-`.venv` `__pycache__` directories under `XinYu-Core/examples/agent-apps/xinyu`.
- Did not force-delete runtime pytest temp directories that returned access denied during traversal.

Validation and bridge-probe cleanup:

- Ran full Python test suite:
  - `.\.venv\Scripts\python.exe -m pytest tests -q`
  - result: `389 passed`
- Restarted Core Bridge after runtime source digest list changed:
  - `.\start_xinyu_core_bridge.ps1 -ForceRestart -RequireVersion -AllowInsecureLlmHttp -RendererMode off -HealthTimeoutSeconds 90`
- Replay, voice, and privacy groups passed:
  - `smoke_run.py --group replay`: `ok`
  - `smoke_run.py --group voice`: `ok`
  - `smoke_run.py --group privacy`: `ok`
- Initial runtime group failed because `bridge_probe` treated live-maintained projection files as probe memory writes:
  - `context/contextual_recall_state.md`
  - `context/contextual_self_loop_state.md`
  - `context/runtime_program_awareness.md`
- Updated `tests/smoke/bridge/integration/bridge_probe_smoke.py` to classify those as always-volatile live projection state.
- Validation passed:
  - `.\.venv\Scripts\python.exe -m py_compile tests\smoke\bridge\integration\bridge_probe_smoke.py`
  - `.\.venv\Scripts\python.exe tests\smoke\bridge\integration\bridge_probe_smoke.py`
  - `.\.venv\Scripts\python.exe smoke_run.py --group runtime`
  - result: `runtime_readiness_smoke: ok`

Full validation:

- Ran:
  - `.\.venv\Scripts\python.exe smoke_run.py --group full`
- Result:
  - `smoke_run group=full: ok`
  - included full pytest: `389 passed`
  - included privacy, voice, memory, learning, and offline runtime readiness groups
- Checked for 20260517T0938 smoke-generated learning directories after the run; none remained.
- Desktop build:
  - `npm run build` in `D:\XinYu\XinYu_Desktop`
  - result: passed, including `npm run typecheck`

## Initiative, Proactive, Self-Action Classification

| File or area | Target | Action | Note |
| --- | --- | --- | --- |
| `xinyu_initiative_spine.py` | `core` | owner candidate for initiative policy | permission-sensitive |
| `xinyu_initiative_orchestrator.py` | `core` or `lab` | inspect before merge | may duplicate spine/proactive |
| `xinyu_initiative_research_shadow.py` | `lab` | keep but isolate | shadow/research wording |
| `xinyu_proactive_presence.py` | `adapters/core` | keep; split transport vs policy later | live proactive QQ |
| `xinyu_proactive_request_loop.py` | `core` | inspect with contract | permission-sensitive |
| `xinyu_proactivity_scorer.py` | `core` component | merge into initiative owner later | scoring component |
| `xinyu_proactive_contract.py` | `core` | keep | permission boundary |
| `xinyu_self_action_gateway.py` | `adapters/core` | keep, strict permission gate | action authority risk |
| `xinyu_self_action_patch_executor.py` | `adapters/lab` | keep, do not broaden | filesystem authority risk |

## Custom Plugin/Gate Classification

| Group | Target | Action |
| --- | --- | --- |
| `*_bridge_plugin.py` referenced by `config.yaml` | `adapters` | keep until config plugin audit proves unused |
| `source_*` gates/search/comparison | `lab/services` | classify live vs research; reduce gate chain |
| `learning_*`, `learner_*` | `services/lab` | keep live ingest path; lab for autonomous learning experiments |
| `ai_self_iteration_*` | `lab` | isolate unless owner explicitly promotes |
| `personality_growth_*` | `lab` | isolate to avoid implicit personality mutation |
| `consolidation_*`, `retention_*`, `archive_*` | `stores/core` if memory maintenance; otherwise `lab` | merge into one memory maintenance policy |
| `dream_*`, `reflection_*`, `inner_cycle_*` | `lab/core` depending on live prompt effect | avoid multiple hidden inner loops |
| `maintenance_schedule_*` | `ops` | keep if used for status/maintenance |

## Tests And Smokes

| Area | Target | Action |
| --- | --- | --- |
| `tests/` | `ops/test` | keep |
| old root `*_smoke.py` deletions | completed migration evidence | do not restore without failing references |
| `smoke_run.py` | `ops` | keep as grouped validation entry |
| replay fixtures | `services/test` | keep redacted only |

Update 2026-05-17 delete/archive evidence:

- Deleted Python files under the app root: `247`.
- Category split:
  - `root_smoke`: `212`
  - `diagnostic_validation`: `9`
  - `manual_ops`: `15`
  - `probe`: `4`
  - `custom_manifest`: `7`
- Counterpart scan found `counterpart_present=247`, `counterpart_missing=0`.
- Potential live non-doc/non-ops references to old root filenames were reduced from `3` to `0` by updating `xinyu_voice_promotion_gate.py` to use migrated smoke paths.
- Evidence record:
  - `worklog/xinyu-delete-archive-reference-audit-2026-05-17.md`

## First Safe Code Slice

Owner decision:

```text
LivingMemoryRecall public owner: xinyu_living_memory_recall.py
Current implementation base: xinyu_context_retrieval.py
Compatibility: xinyu_context_retrieval.py public API stays available until tests and imports migrate.
```

Patch shape:

1. Add `xinyu_living_memory_recall.py`.
2. Re-export the current public recall result types and rendering/logging helpers.
3. Add a `LivingMemoryRecall` class with `retrieve(...)` and `log(...)`.
4. Update `xinyu_core_bridge.py` import to use the owner surface.
5. Keep all existing behavior and prompt shape unchanged.
6. Add a small test proving the owner surface delegates to the current algorithm.

Focused validation:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile xinyu_living_memory_recall.py xinyu_context_retrieval.py xinyu_core_bridge.py
.\.venv\Scripts\python.exe -m pytest tests\test_retrieval_need_reranker.py tests\test_sparse_memory_router.py tests\test_context_retrieval_owner_scenarios.py -q
```

Stop condition:

- If the bridge import patch conflicts with owner edits in `xinyu_core_bridge.py`, leave only the new owner module and test, then pause before touching the bridge.
