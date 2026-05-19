# XinYu Subtractive Refactor Closeout - 2026-05-17

Status: superseded by seven-goal closeout addendum.

See also:

- `worklog/xinyu-subtractive-seven-goal-closeout-2026-05-17.md`

The original v1 closeout below covered an earlier subtractive pass. The later
seven-goal closeout adds canonical renderer recall reuse, persona contract,
memory/library manifest validation, and source-backed neuro-inspired rules.

## What Changed

### Living Memory Recall

- Added `xinyu_living_memory_recall.py` as the canonical public owner surface.
- Moved the live bridge call path to:

```text
xinyu_core_bridge.py
-> retrieve_living_memory(...)
-> xinyu_context_retrieval.py implementation layer
```

- Kept `xinyu_context_retrieval.py` as implementation/compatibility only.
- Migrated non-owner public imports away from `xinyu_context_retrieval`.
- Added public recall bucket shape:

```text
must_remember
experience_hints
uncertainties
trace
```

### Persona Runtime

- Added a small runtime boundary layer to `xinyu_persona_runtime.py`.
- The boundary now explicitly separates:
  - stable anchor
  - living state
  - voice policy
  - memory change boundary
- No stable personality memory was rewritten.
- No hard persona prompt lock was restored.

### Structure And Storage

- Updated `STRUCTURE-NOTES.md` with target buckets:
  - `core`
  - `adapters`
  - `stores`
  - `services`
  - `ops`
  - `lab`
  - `archive`
- Added library boundary:
  - `library/README.md`
  - `library/papers/README.md`
- Added future cases boundary:
  - `cases/README.md`
- Moved untracked root paper extracts into `library/papers/`:
  - `2406.19108v2_extracted.txt`
  - `2509.22447v1_extracted.txt`

### Runtime Awareness

- Added living recall files to `BRIDGE_RUNTIME_SOURCE_RELS`:
  - `xinyu_living_memory_recall.py`
  - `xinyu_context_retrieval.py`
  - `xinyu_retrieval_envelope.py`
  - `xinyu_retrieval_need_reranker.py`
  - `xinyu_sparse_memory_router.py`
- Restarted Core Bridge after digest-scope changes.

### Smoke Correction

- Updated `bridge_probe_smoke.py` to treat live-maintained projection files as volatile:
  - `context/contextual_recall_state.md`
  - `context/contextual_self_loop_state.md`
  - `context/runtime_program_awareness.md`
- This preserves the original probe guarantee: probe requests must not create sessions or direct memory writes.

### Cleanup

- Deleted untracked temporary probe directory:
  - `D:\XinYu\_tmp_xinyu_probe`
  - files removed: 13115
  - directories removed: 2518
- Removed 51 non-`.venv` `__pycache__` directories under the app tree.
- Did not force-delete access-denied runtime pytest temp directories.

## New Worklogs

- `worklog/xinyu-subtractive-refactor-autonomous-plan-2026-05-17.md`
- `worklog/xinyu-subtractive-inventory-2026-05-17.md`
- `worklog/xinyu-module-classification-2026-05-17.md`
- `worklog/xinyu-memory-library-manifest-2026-05-17.md`
- `worklog/xinyu-neuro-inspired-rules-2026-05-17.md`
- `worklog/xinyu-subtractive-closeout-2026-05-17.md`

## Validation

Passed:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
```

Result:

```text
389 passed
```

Passed:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group replay
.\.venv\Scripts\python.exe smoke_run.py --group voice
.\.venv\Scripts\python.exe smoke_run.py --group privacy
.\.venv\Scripts\python.exe smoke_run.py --group runtime
.\.venv\Scripts\python.exe smoke_run.py --group full
```

Result:

```text
smoke_run group=full: ok
```

Passed:

```powershell
cd D:\XinYu\XinYu_Desktop
npm run build
```

Result:

```text
typecheck passed
electron-vite build passed
```

## Intentionally Not Moved

These areas still have many live imports/config/test references and were not moved:

- `memory/knowledge/`
- `data/external/`
- `data/conversation_experience/`
- live `custom/*_bridge_plugin.py`
- live `xinyu_bridge_*.py`
- live `xinyu_qq_*.py`

Reason:

Moving them now would be path churn rather than safe subtraction. They need a second phase with compatibility loaders or path aliases.

## Remaining Technical Debt

- `xinyu_core_bridge.py` is still too large.
- `xinyu_qq_gateway.py` is still too large.
- `custom/` still has many gate/plugin pairs that should become `lab`, `services`, or one maintenance pipeline.
- `memory/knowledge` still mixes source material, learning state, and knowledge notes.
- `data/conversation_experience` should eventually become `cases/conversation` after loader migration.

## Next Phase Recommendation

Do not start by moving folders.

Next safe phase:

1. Add compatibility loaders for `library/` and `cases/`.
2. Move `data/external` behind a dataset registry alias.
3. Move conversation cases behind a case registry alias.
4. Collapse source/learning gates into one maintenance pipeline.
5. Continue thinning `xinyu_core_bridge.py` and `xinyu_qq_gateway.py` one route group at a time.
