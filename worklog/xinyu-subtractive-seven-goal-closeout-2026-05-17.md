# XinYu Subtractive Seven-Goal Closeout - 2026-05-17

Status: seven owner ideas have concrete implementation artifacts and focused validation.

## 1. One Memory Recall Algorithm

Implemented:

- `xinyu_living_memory_recall.py`
  - `run_living_memory_recall_algorithm(...)` is the canonical live entry.
  - `retrieve_living_memory(...)` and `retrieve_recalled_context` are compatibility names that return `run_living_memory_recall_algorithm(...).result`.
- `xinyu_core_bridge.py`
  - live chat calls `run_living_memory_recall_algorithm(...)`.
- `xinyu_bridge_renderer.py` and `xinyu_runtime_context.py`
  - live renderer now receives the already-built canonical recall block.
  - offline renderer/test paths may still use `xinyu_contextual_recall.py`.
- `xinyu_contextual_recall.py`
  - documented as renderer/offline contextual recall, not the canonical live algorithm.

Validation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_living_memory_recall.py tests\test_runtime_context.py tests\test_context_retrieval_owner_scenarios.py tests\test_retrieval_need_reranker.py tests\test_sparse_memory_router.py
.\.venv\Scripts\python.exe tests\smoke\memory\context_retrieval_smoke.py
```

## 2. Remove Useless Code

Implemented in this phase and preceding phase-3 batches:

- route families extracted out of `xinyu_core_bridge.py`
- root operator scripts moved to `ops/diagnostics`, `ops/validation`, `ops/manual`, and `ops/probes`
- constant-only custom manifests archived under `ops/archive/custom-manifests/2026-05-17`
- `state_service`, launch, daily digest, and chat service moved behind compatibility wrappers

No broad deletion was done without reference checks.

## 3. Precise Framework Classification

Implemented:

- app root now has documented categories: `ops`, `services`, `stores`, archive, runtime behavior, memory structure
- `INDEX.md`, `STRUCTURE-NOTES.md`, `VALIDATION-INDEX.md`, and local README files were updated during the refactor
- new manifest boundary lives under `stores/memory_library_manifest.json`

## 4. Persona Reinjection Toward A Living Surface

Implemented:

- `xinyu_persona_contract.py`
  - stable identity, owner relation, agency boundary, memory boundary, emotion boundary
  - positive living-surface rules
  - forbidden-surface rules
- `xinyu_persona_runtime.py`
  - injects the persona contract before current surface state
- `xinyu_speech_controller.py`
  - adds a narrow guard for owner-private "living person / real person / biology / consciousness" meta turns
  - reduces overclaiming replies back to present wording
- `PERSONA-LIVING-SURFACE-RULES.md`
  - human-readable contract and validation anchors

Validation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_persona_runtime_contract.py
.\.venv\Scripts\python.exe tests\smoke\voice\persona_runtime_smoke.py
.\.venv\Scripts\python.exe tests\smoke\voice\chinese_voice_guard_smoke.py
.\.venv\Scripts\python.exe tests\smoke\voice\xinyu_speech_controller_smoke.py
```

## 5. Memory And Library Organization

Implemented:

- `stores/memory_library_manifest.json`
  - metadata-only manifest for `memory`, `memory/knowledge`, `memory/archive`, `memory-seeds`, `data`, `data/external`, `data/conversation_experience`, `learning`, project-level `library`, project-level `cases`, `runtime`, and `logs`
- `ops/validation/validate_memory_library_manifest.py`
  - validates allowlist/denylist, sensitivity, snapshot rules, and file-count thresholds without reading file bodies
- `tests/test_memory_library_manifest.py`
  - covers default manifest and denylisted runtime path handling

Validation:

```powershell
.\.venv\Scripts\python.exe ops\validation\validate_memory_library_manifest.py --json
.\.venv\Scripts\python.exe -m pytest -q tests\test_memory_library_manifest.py
```

## 6. Merge Duplicate Or Near-Duplicate Modules

Implemented:

- recall compatibility names now route through one algorithm surface
- bridge/proactive/desktop/utility/self-action/QQ visible dispatch route families have focused owner modules
- maintenance manifest constants were archived after no-live-reference scans
- launch/store/service helpers now have category owners and root wrappers only

Remaining debt:

- `xinyu_core_bridge.py`, `xinyu_qq_gateway.py`, and some `custom/*_bridge_plugin.py` pairs still need future route-sized thinning.

## 7. Neuroscience-Inspired Engineering Track

Implemented:

- `xinyu_neuro_memory_rules.py`
  - five source-backed engineering rules
  - hippocampal index, goal-gated retrieval, reconsolidation mismatch, emotion modulation, sleep/replay boundary
- `NEURO-INSPIRED-ENGINEERING-RULES.md`
  - readable summary and source anchors
- `MEMORY-REDUCTION-RULES.md`
  - now points to the source-backed rule table
- `tests/test_neuro_memory_rules.py`
  - enforces sources, risk boundaries, adaptations, and test anchors

Source anchors include PubMed/PMC/academic pages for hippocampal indexing,
predictive coding, reconsolidation, emotional arousal, and sleep/replay.

Validation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_neuro_memory_rules.py
```

## Validation Run In This Closeout Batch

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_living_memory_recall.py xinyu_runtime_context.py xinyu_contextual_recall.py xinyu_bridge_renderer.py xinyu_core_bridge.py xinyu_persona_contract.py xinyu_persona_runtime.py xinyu_speech_controller.py xinyu_neuro_memory_rules.py ops\validation\validate_memory_library_manifest.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_living_memory_recall.py tests\test_runtime_context.py tests\test_persona_runtime_contract.py tests\test_memory_library_manifest.py tests\test_neuro_memory_rules.py
.\.venv\Scripts\python.exe ops\validation\validate_memory_library_manifest.py --json
.\.venv\Scripts\python.exe tests\smoke\voice\xinyu_speech_controller_smoke.py
.\.venv\Scripts\python.exe tests\smoke\voice\persona_runtime_smoke.py
.\.venv\Scripts\python.exe tests\smoke\voice\chinese_voice_guard_smoke.py
.\.venv\Scripts\python.exe tests\smoke\memory\context_retrieval_smoke.py
.\.venv\Scripts\python.exe tests\smoke\bridge\bridge_renderer_guard_flags_smoke.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_context_retrieval_owner_scenarios.py tests\test_retrieval_need_reranker.py tests\test_sparse_memory_router.py tests\test_runtime_program_awareness.py
.\.venv\Scripts\python.exe tests\smoke\runtime\state_io_smoke.py
.\.venv\Scripts\python.exe tests\smoke\runtime\service_boundary_smoke.py
.\.venv\Scripts\python.exe tests\smoke\memory\memory_braid_smoke.py
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300
.\.venv\Scripts\python.exe -m pytest tests -q
cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
git diff --check
```

`smoke_run.py --group quick` passed. `git diff --check` passed with CRLF
warnings only. Full pytest passed with `429 passed`. Desktop typecheck and
Desktop build passed.

## Remaining Risks

- Private memory content was not rewritten; the new manifest organizes boundaries but does not migrate contents.
- `memory/knowledge`, `data/external`, and `data/conversation_experience` are still in their old live paths until loaders/aliases are migrated.
