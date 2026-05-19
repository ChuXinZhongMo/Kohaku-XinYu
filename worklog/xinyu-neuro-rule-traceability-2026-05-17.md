# XinYu Neuro Rule Traceability - 2026-05-17

Status: applied as a single neuro-inspired rule traceability migration.

## Batch Scope

- Capability group: neuro-inspired engineering rules in recall and emotion
  flows.
- Goal: make runtime flows directly reference the structured rule IDs from
  `xinyu_neuro_memory_rules.py`, without changing recall ranking or emotion
  council behavior.

## Completed

- Updated `xinyu_neuro_memory_rules.py`.
  - Added `NEURO_RULE_IDS_BY_FLOW`.
  - Added `rule_ids_for_flow(flow)`.
- Updated `xinyu_living_memory_recall.py`.
  - Recall algorithm notes now include
    `neuro_rules:hippocampal_index_not_dump,goal_gated_retrieval`.
- Updated `xinyu_emotion_council.py`.
  - Emotion council result includes `neuro_rule_ids`.
  - Emotion council notes now include
    `neuro_rules:emotion_modulates_not_proves`.
- Updated tests:
  - `tests/test_neuro_memory_rules.py`
  - `tests/test_living_memory_recall.py`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_neuro_memory_rules.py xinyu_living_memory_recall.py xinyu_emotion_council.py
.\.venv\Scripts\python.exe -m pytest tests\test_neuro_memory_rules.py tests\test_living_memory_recall.py tests\test_sparse_memory_router.py tests\test_retrieval_need_reranker.py
.\.venv\Scripts\python.exe tests\smoke\initiative\emotion_council_smoke.py
.\.venv\Scripts\python.exe tests\smoke\memory\context_retrieval_smoke.py
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/xinyu_neuro_memory_rules.py XinYu-Core/examples/agent-apps/xinyu/xinyu_living_memory_recall.py XinYu-Core/examples/agent-apps/xinyu/xinyu_emotion_council.py XinYu-Core/examples/agent-apps/xinyu/tests/test_neuro_memory_rules.py XinYu-Core/examples/agent-apps/xinyu/tests/test_living_memory_recall.py
```

Results:

- Focused pytest set: 17 passed.
- Emotion council smoke: passed.
- Context retrieval smoke: passed.
- Diff check: whitespace clean; only CRLF normalization warning.

## DoD Impact

- Neuro-inspired rules are no longer only parallel documentation/tests.
- Recall flow now traces hippocampal-index and goal-gated retrieval rules.
- Emotion flow now traces emotion-modulation boundary directly.
- Write-flow rules are mapped for later use by memory write/gate modules.

## Not Changed

- No recall scoring/routing behavior was changed.
- No emotion lens scoring behavior was changed by this batch.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Duplicate bridge/helper consolidation remains open.
- Manual/trace/legacy `memory/knowledge` strings remain as compatibility or ops
  surfaces.
- Final audit still needs to list kept/merged/archived/deleted/remaining risks.

## Next Batch

Handle one duplicate-consolidation batch around bridge helper reuse, then run a
final audit pass.
