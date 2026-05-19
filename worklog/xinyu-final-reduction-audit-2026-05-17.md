# XinYu Final Reduction Audit - 2026-05-17

Status: current Definition of Done satisfied for this reduction pass.

## Scope

- Project root: `D:\XinYu`
- App root: `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`
- Desktop root: `D:\XinYu\XinYu_Desktop`
- No git commit was made.
- No destructive reset/checkout was used.
- No secrets, tokens, raw QQ logs, or raw private memory bodies were printed.

## Definition Of Done Audit

| DoD item | Status | Evidence |
| --- | --- | --- |
| Canonical live memory recall algorithm | satisfied | `xinyu_living_memory_recall.py` owns `CANONICAL_RECALL_OWNER` and `run_living_memory_recall_algorithm`; `xinyu_context_retrieval.py` is marked `provider/compatibility`; `xinyu_contextual_recall.py` is explicitly not the canonical owner; `xinyu_core_bridge.py` calls the canonical algorithm. |
| Old recall entry points are shim/provider | satisfied | `tests/test_living_memory_recall.py` asserts canonical owner/provider boundary; `tests/test_contextual_recall.py` asserts contextual providers are not recall owners. |
| Active module classification | satisfied | `STRUCTURE-NOTES.md` defines the active target buckets: core, adapters, stores, services, ops, lab, archive/delete. Current flat root is treated as compatibility while new or moved code is assigned by ownership rule. `stores/`, `services/`, `ops/`, `tests/smoke/`, and compatibility wrappers are documented. |
| Delete/archive unused code | satisfied for this pass | App-root smoke/manual/diagnostic wrappers are removed from the active app root and live under `tests/smoke/`, `ops/manual/`, `ops/diagnostics/`, `ops/probes/`, or `ops/archive/custom-manifests/`. Git status shows those deletions/moves are still uncommitted. |
| Persona contract/runtime state | satisfied | Separate persona-prompt artifact is gone; stable concept, voice, and reality boundaries flow through `memory/self/system_prompt_memory.md`, `memory/self/personality_profile.md`, `xinyu_persona_contract.py`, `xinyu_persona_runtime.py`, and runtime state surfaces. Voice/persona smokes are in the quick gate and pytest set. |
| Memory/library/cases/runtime boundary | satisfied | `xinyu_storage_paths.py` declares `cases/conversation`, `library/datasets`, and `memory/knowledge` boundaries, with canonical preferred paths and legacy fallback for cases/library. Live knowledge reads were migrated to `knowledge_file_path(...)`; reference strings use `knowledge_ref(...)` where appropriate. |
| Duplicate or near-duplicate modules | satisfied for this pass | Source material claim quality rules are merged into `custom/source_material_quality.py`; old callers import the shared helper. Bridge value helpers remain canonical in `xinyu_bridge_values.py`; `xinyu_core_bridge.py` keeps `_...` aliases as compatibility shims. Maintenance bridge preflight/cooldown/trace logic is shared in `custom/maintenance_bridge_utils.py`; individual plugin classes remain config-compatible entry points. |
| Neuroscience-inspired rules enter runtime | satisfied | `xinyu_neuro_memory_rules.py` exposes `rule_ids_for_flow(...)`; living memory recall records hippocampal-index and goal-gated retrieval rule IDs; emotion council records the emotion-modulation boundary rule ID. |
| Full tests, quick smoke, desktop gates | satisfied | See validation section below. |
| Final kept/merged/archived/deleted/risks audit | satisfied | See sections below. |

## Kept

- Individual `custom/*_bridge_plugin.py` classes are kept as compatibility
  entry points because plugin names, class names, priorities, and per-plugin
  run gates are externally configured behavior.
- `memory/knowledge/*_trace.log` reference strings are kept for trace paths.
  These are observability files, not live data-read path construction.
- `ops/manual/*` scripts are kept as operator-only compatibility surfaces.
- `xinyu_v1/memory/markdown_legacy.py` keeps `memory/knowledge/` as a V1 legacy
  layer mapping.
- The flat app-root Python layout is kept as a compatibility layer while
  ownership buckets are enforced in docs and new/moved code.

## Merged

- Live recall ownership converged on
  `xinyu_living_memory_recall.run_living_memory_recall_algorithm`.
- Knowledge file reads in the source/learning chain were migrated to
  `knowledge_file_path(...)`.
- Canonical knowledge reference strings use `knowledge_ref(...)`.
- Source material claim-quality heuristics were merged into
  `custom/source_material_quality.py`.
- Bridge scalar/string helper ownership remains in `xinyu_bridge_values.py`;
  `xinyu_core_bridge.py` now re-exports `_optional_int` as a compatibility shim.
- Neuroscience-inspired memory/emotion rule IDs are now shared runtime metadata
  instead of only parallel documentation.

## Archived Or Deleted

- App-root smoke files are deleted from the active app root and represented by
  structured smoke locations under `tests/smoke/`.
- App-root manual scripts are deleted from the active app root and represented
  under `ops/manual/`.
- App-root diagnostics/probes are deleted from the active app root and
  represented under `ops/diagnostics/`, `ops/probes/`, or validation folders.
- Old custom manifest files deleted from `custom/` are represented by runtime
  manifests/ops archive locations rather than live imports.

## Remaining Risks

- The worktree is intentionally very dirty: `git status --short` reported 591
  entries during the final audit. This pass did not commit or squash anything.
- Remaining `memory/knowledge` string hits in live Python are intentional
  compatibility/trace/manual/legacy surfaces:
  bridge `TRACE_REL` constants, `automation_bridge_manifest.py`,
  `ops/manual/*`, `xinyu_storage_paths.py`, and `xinyu_v1` legacy mapping.
- Several source-chain bridge plugins still have similar `post_llm_call`
  shells. They are kept because their configured class names and run gates are
  public plugin behavior; their shared guard/cooldown/trace logic already lives
  in `maintenance_bridge_utils.py`.
- Source request/result protocol parsing can be simplified further in a later
  pass, but current behavior is covered by source search/provider/resolution
  and source learning chain smokes.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\source_material_quality.py custom\learner_integration_engine.py custom\source_integration_gate_engine.py
.\.venv\Scripts\python.exe -m pytest tests\test_source_material_quality.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\learner_integration_smoke.py --restore-after --require-integration --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_reliability_gate_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_quality_followup_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe -m py_compile xinyu_core_bridge.py xinyu_bridge_values.py
.\.venv\Scripts\python.exe tests\smoke\bridge\bridge_values_smoke.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300
npm run typecheck
npm run build
git diff --check
```

Results:

- `tests/test_source_material_quality.py`: 2 passed.
- Full pytest: 455 passed.
- Quick smoke: passed.
- Bridge values smoke: passed.
- Source learning chain smokes: passed.
- Desktop typecheck: passed.
- Desktop build: passed.
- Diff check: exit code 0; CRLF normalization warnings only.

## Recovery Point

If another session resumes here:

1. Start at `D:\XinYu`.
2. Read this file and the latest git status.
3. Do not restart the seven-direction plan from scratch.
4. Treat the current DoD as satisfied unless new user requirements add a stricter
   merge/delete threshold.
5. If continuing reduction work, the next non-blocking candidate is
   `custom/source_protocol_utils.py` for request/result parser helpers, with
   source search/provider/resolution and source learning chain smokes as the
   focused gate.
