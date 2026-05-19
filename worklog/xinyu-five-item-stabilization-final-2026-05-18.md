# XinYu Five-Item Stabilization Final Audit - 2026-05-18

Status: complete for the five planned stabilization batches.

Working roots:

- repo: `D:\XinYu`
- app: `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`
- desktop: `D:\XinYu\XinYu_Desktop`

## Scope

This round followed `D:\XinYu\plan.md` and completed five items:

1. Version solidification.
2. Source/learning protocol parser consolidation.
3. Bridge plugin shell consolidation.
4. Persona realism evaluation.
5. Memory/library/cases boundary audit.

No git commit was made. No private memory body, raw QQ content, token, or secret was printed.

## 1. Version Solidification

Completed:

- Added `ops/validation/git_change_group_audit.py`.
- Added `tests/test_git_change_group_audit.py`.
- Generated repeatable change-group reports:
  - `D:\XinYu\worklog\xinyu-change-group-audit-2026-05-18.md`
  - `D:\XinYu\worklog\xinyu-change-group-audit-2026-05-18.json`
  - `D:\XinYu\worklog\xinyu-change-group-audit-2026-05-18-worklog.md`

Direct impact:

- The large dirty worktree can now be grouped by capability area instead of being reviewed as one mixed pile.
- The audit only uses git status paths and does not inspect private content bodies.

## 2. Source/Learning Protocol Parser Consolidation

Completed:

- Added canonical helper module `custom/source_protocol_utils.py`.
- Migrated repeated parsing behavior behind compatibility shims in:
  - `custom/source_request_planner_engine.py`
  - `custom/source_search_resolver_engine.py`
  - `custom/search_result_gate_engine.py`
  - `custom/source_integration_gate_engine.py`
- Added `tests/test_source_protocol_utils.py`.
- Wrote `D:\XinYu\worklog\xinyu-source-protocol-utils-2026-05-18.md`.

Direct impact:

- Source request/result parsing now has one main helper layer.
- Old entry points remain available, so existing flows do not need to change their imports yet.

## 3. Bridge Plugin Shell Consolidation

Completed:

- Extended `custom/maintenance_bridge_utils.py` with `run_maintenance_bridge_once(...)`.
- Migrated these bridge plugins to the shared runner while keeping their public plugin classes and names:
  - `custom/source_gate_bridge_plugin.py`
  - `custom/source_reliability_bridge_plugin.py`
  - `custom/source_integration_gate_bridge_plugin.py`
- Updated `tests/test_maintenance_bridge_utils.py`.
- Wrote `D:\XinYu\worklog\xinyu-maintenance-bridge-runner-2026-05-18.md`.

Direct impact:

- The repeated `should_run -> run engine -> set_state -> trace` shell is now shared.
- Plugin compatibility is preserved; this is a consolidation, not a forced public API break.

## 4. Persona Realism Evaluation

Completed:

- Added `xinyu_persona_realism_eval.py`.
- Added `tests/test_persona_realism_eval.py`.
- Added smoke test `tests/smoke/voice/persona_realism_eval_smoke.py`.
- Wrote `D:\XinYu\worklog\xinyu-persona-realism-eval-2026-05-18.md`.

The evaluator uses synthetic samples only and checks for these failure modes:

- rolecard-style language
- false biological claims
- internal state leaks
- theatrical persona performance
- emotion stated as fact
- overly long responses
- technical work being emotionalized
- generic tool-flat phrasing

Direct impact:

- XinYu's "alive" feeling now has a regression ruler.
- The rule is not "pretend to be human"; the rule is more natural expression while preserving factual boundaries.

## 5. Memory/Library/Cases Boundary Audit

Completed:

- Added `ops/validation/memory_library_cases_audit.py`.
- Added `tests/test_memory_library_cases_audit.py`.
- Generated boundary reports:
  - `D:\XinYu\worklog\xinyu-memory-library-cases-boundary-audit-2026-05-18.md`
  - `D:\XinYu\worklog\xinyu-memory-library-cases-boundary-audit-2026-05-18.json`
  - `D:\XinYu\worklog\xinyu-memory-library-cases-boundary-audit-2026-05-18-worklog.md`

Latest audit summary:

- total files scanned: 2287
- main zones:
  - runtime: 1815
  - memory: 307
  - memory.runtime_or_self: 124
  - memory.knowledge: 28
  - library: 5
  - legacy.library: 4
  - cases: 2
  - legacy.cases: 2
- concern counts:
  - runtime_file_has_stable_memory_frontmatter: 284
  - structured_data_inside_memory_review: 22
  - legacy_fallback_review: 6

Direct impact:

- Memory, public library, cases, runtime, and legacy fallback paths now have a repeatable boundary audit.
- The tool reports paths and metadata classifications only; it does not print private bodies.

## Validation

Passed:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300

cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

Focused validations also passed for:

- `tests/test_git_change_group_audit.py`
- `tests/test_source_protocol_utils.py`
- `tests/test_source_material_quality.py`
- source request planner/resolver/provider/learning-chain smokes
- `tests/test_maintenance_bridge_utils.py`
- source reliability gate smoke
- `tests/test_persona_realism_eval.py`
- persona realism eval smoke
- `tests/test_memory_library_cases_audit.py`

## Kept, Merged, Archived, Deleted

Kept:

- Existing public imports, plugin classes, names, and compatibility entry points.
- Existing memory/library/cases/runtime content in place.
- Existing dirty worktree state; this round did not perform destructive cleanup.

Merged:

- Source protocol parsing helpers into `custom/source_protocol_utils.py`.
- Maintenance bridge runner shell into `custom/maintenance_bridge_utils.py`.

Archived/deleted:

- No additional content was archived or deleted in this five-item stabilization round.
- Boundary audit intentionally stops before moving or deleting private or legacy content.

## Remaining Risks

- `git status --short` still contains a very large dirty tree; latest count observed after this final worklog was added was 609 entries.
- Boundary audit found review items, especially runtime files with stable-memory frontmatter and structured data under memory. These require per-file decisions before any move/delete.
- The persona evaluator is a first regression ruler. It catches obvious failures, but it does not replace human review for nuanced long dialogue.
- Compatibility shims remain by design; a later round can remove them only after dependent callers are audited.

## Recovery Point

If execution resumes later:

1. Start from this file and the five batch worklogs listed above.
2. Re-run `git status --short` and `ops/validation/git_change_group_audit.py`.
3. Pick the next task from the remaining risks instead of restarting the five completed batches.
