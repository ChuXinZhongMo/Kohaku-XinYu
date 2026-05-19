# XinYu Recall Adjacent Boundaries - 2026-05-17

Status: applied as a behavior-preserving contextual/offline recall boundary
batch.

## Batch Scope

- Capability group: recall-adjacent contextual modules and conversation
  experience hints.
- Goal: ensure modules near recall are visibly classified as providers,
  renderer/offline packs, observability, or lab replay, not as competing live
  memory recall owners.

## Completed

- Added shared canonical owner references to:
  - `xinyu_contextual_recall.py`
  - `xinyu_contextual_self_loop.py`
  - `xinyu_contextual_self_observatory.py`
  - `xinyu_contextual_self_replay.py`
  - `xinyu_conversation_experience_matcher.py`
  - `xinyu_conversation_experience_sidecar.py`
- Added role/boundary constants:
  - contextual recall: renderer/offline context pack, not canonical living
    memory recall
  - contextual self loop: runtime scene/pressure provider
  - contextual self observatory: observability/no behavior change
  - contextual self replay: ops/lab public dataset replay
  - conversation experience matcher: advisory case provider
  - conversation experience sidecar: hidden advisory prompt provider
- Added tests proving these modules point back to
  `xinyu_living_memory_recall.run_living_memory_recall_algorithm` as the
  canonical owner while preserving their provider/offline roles.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_contextual_recall.py xinyu_contextual_self_loop.py xinyu_contextual_self_observatory.py xinyu_contextual_self_replay.py xinyu_conversation_experience_matcher.py xinyu_conversation_experience_sidecar.py xinyu_runtime_context.py xinyu_core_bridge.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_contextual_recall.py tests\test_contextual_self_loop.py tests\test_contextual_self_observatory.py tests\test_contextual_self_replay.py tests\test_conversation_experience_matcher.py tests\test_conversation_experience_sidecar.py tests\test_conversation_experience_replay_cases.py tests\test_prompt_pressure.py
.\.venv\Scripts\python.exe tests\smoke\dialogue\conversation_experience_cases_smoke.py
.\.venv\Scripts\python.exe tests\smoke\dialogue\conversation_experience_sidecar_smoke.py
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/xinyu_contextual_recall.py XinYu-Core/examples/agent-apps/xinyu/xinyu_contextual_self_loop.py XinYu-Core/examples/agent-apps/xinyu/xinyu_contextual_self_observatory.py XinYu-Core/examples/agent-apps/xinyu/xinyu_contextual_self_replay.py XinYu-Core/examples/agent-apps/xinyu/xinyu_conversation_experience_matcher.py XinYu-Core/examples/agent-apps/xinyu/xinyu_conversation_experience_sidecar.py XinYu-Core/examples/agent-apps/xinyu/tests/test_contextual_recall.py XinYu-Core/examples/agent-apps/xinyu/tests/test_conversation_experience_matcher.py
```

Results:

- Focused contextual/conversation tests: `46 passed`.
- Dialogue smokes: `conversation_experience_cases_smoke ok`,
  `conversation_experience_sidecar_smoke ok`.
- Quick smoke: `smoke_run group=quick: ok`.
- Diff check: clean.

## Not Changed

- No runtime recall scoring changed.
- No contextual prompt pack content changed except exported role constants.
- No public/private case matching behavior changed.
- No raw private memory, QQ logs, or secrets were read or printed.
- No git commit was made.

## Remaining

- Provider labels now exist, but the module classification worklog should be
  refreshed later with these new boundaries.
- Deletion/archive proof remains incomplete for many pre-existing deleted root
  smoke wrappers and archived manifests.
- Memory/library path fallback cleanup still has old live compatibility paths
  by design.

## Next Batch

Move to deletion/archive evidence or module classification refresh. The safest
next target is an evidence-only audit of pre-existing deleted/archived smoke and
operator wrappers, followed by a small validation update rather than broad
deletion.
