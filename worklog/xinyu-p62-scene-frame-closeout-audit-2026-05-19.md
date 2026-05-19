# XinYu P62 Scene Frame Closeout Audit - 2026-05-19

## Scope

Capability group: Scene Frame v1 closeout audit.

No code changes in this batch. This is a boundary and completion audit for
P58-P61.

## Kept

- Canonical memory recall remains:
  - `xinyu_living_memory_recall.run_living_memory_recall_algorithm(...)`
- Renderer context remains assembled by:
  - `xinyu_runtime_context.build_renderer_memory_context(...)`
- Scene Frame is a provider/advisory layer:
  - `xinyu_scene_frame.build_scene_frame(...)`
  - `xinyu_scene_frame.render_scene_frame_prompt_block(...)`

## Merged / Connected

- Renderer prompt context:
  - `xinyu_runtime_context.py` injects `[runtime/scene_frame]`.
- Life reply policy:
  - `xinyu_life_reply_policy.py` consumes Scene Frame labels.
  - `xinyu_core_bridge.py` builds Scene Frame after canonical recall and passes it to life reply policy.
- Emotion modulation:
  - `xinyu_emotion_council.py` consumes Scene Frame labels as shadow-only lens modulation.

## Boundary Evidence

- `rg` confirms Scene Frame call sites are limited to:
  - `xinyu_runtime_context.py`
  - `xinyu_life_reply_policy.py`
  - `xinyu_core_bridge.py`
  - `xinyu_emotion_council.py`
  - focused tests.
- `rg` confirms canonical recall still lives under:
  - `xinyu_living_memory_recall.py`
  - `run_living_memory_recall_algorithm`
  - `retrieve_living_memory`
- `xinyu_runtime_context.py` still states live chat should pass the canonical recall prompt block instead of running another recall path.
- Scene Frame stores and renders labels only:
  - `scene_id`
  - `time_context`
  - `owner_state`
  - `task_mode`
  - `memory_relation`
  - `reply_policy`
  - `uncertainty`
- No Scene Frame code writes raw memory bodies, QQ content archives, tokens, or private logs.

## Validation

- P61 full validation already passed after the final code change:
  - `.\.venv\Scripts\python.exe -m pytest tests -q`
    - 604 passed
  - `.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after`
    - pass
  - `git diff --check ...`
    - pass; only existing LF/CRLF warnings.
- P62 focused audit validation:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_emotion_council_scene_frame.py tests\test_life_reply_policy_scene_frame.py tests\test_scene_frame.py tests\test_runtime_context.py tests\test_living_memory_recall.py tests\test_temporal_memory_context.py -q`
    - 37 passed

## What Is Now Implemented

- "Full scene intelligence v1" is implemented as a compact current-scene frame.
- It covers:
  - time context.
  - owner recent state when stated or inferred from temporal recall.
  - task mode.
  - memory relation.
  - reply policy.
  - uncertainty.
- It affects:
  - prompt context.
  - reply policy and final reply shaping.
  - shadow-only emotion modulation.

## Remaining Risks

- Scene Frame v1 is heuristic; it does not learn its own rules yet.
- It does not directly change memory candidate confidence or stable write routing.
- It may need more replay fixtures after real owner-chat failures expose new scene types.
- It does not replace careful current-message priority; current owner text must still win.

## Next Optional Batch

No immediate code batch is required for this Scene Frame line.

If continuing later, the next useful work is not another broad framework layer.
The better next step is replay-driven calibration from real failures:

- collect a redacted failed reply case.
- add it as a replay fixture.
- adjust Scene Frame policy only if the replay proves a specific mismatch.

## Recovery Point

Start from `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`.

Recently changed in P58-P61:

- `xinyu_scene_frame.py`
- `xinyu_runtime_context.py`
- `xinyu_life_reply_policy.py`
- `xinyu_core_bridge.py`
- `xinyu_emotion_council.py`
- `tests/test_scene_frame.py`
- `tests/test_runtime_context.py`
- `tests/test_life_reply_policy_scene_frame.py`
- `tests/test_emotion_council_scene_frame.py`

Recommended check:

`.\.venv\Scripts\python.exe -m pytest tests\test_emotion_council_scene_frame.py tests\test_life_reply_policy_scene_frame.py tests\test_scene_frame.py tests\test_runtime_context.py tests\test_living_memory_recall.py tests\test_temporal_memory_context.py -q`
