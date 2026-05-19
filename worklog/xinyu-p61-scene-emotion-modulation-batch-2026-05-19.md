# XinYu P61 Scene Emotion Modulation Batch - 2026-05-19

## Scope

Capability group: Scene Frame emotion modulation.

Goal: let Scene Frame influence a shadow-only emotion modulation path while
avoiding direct memory writes.

## Why Emotion First

Memory write routing is higher risk because it can affect persistent owner,
relationship, or project memory. Emotion council is already shadow-only and has
explicit boundaries:

- no visible reply
- no QQ enqueue
- no tool execution
- no stable memory write

So P61 used emotion modulation first.

## Changes Completed

- Extended `xinyu_emotion_council.run_emotion_council_shadow(...)`.
  - Accepts optional `scene_frame`.
  - If not provided, builds a conservative Scene Frame from current text and time.
  - Stores only Scene Frame labels, not raw private memory bodies.
- Added Scene Frame lens modulation:
  - low energy / time-bound recall / low-burden reply -> boosts `fatigue`.
  - technical execution / runtime status -> boosts `stability`.
  - relational support -> boosts `hurt`.
  - warm boundary-aware reply -> boosts `attachment`.
- Extended emotion council state output.
  - Adds `## Scene Frame Modulation`.
  - Records scene labels:
    - `scene_id`
    - `scene_reply_policy`
    - `scene_time_context`
    - `scene_owner_state`
    - `scene_task_mode`
    - `scene_memory_relation`
- Extended `build_emotion_council_prompt_block(...)`.
  - Includes Scene Frame policy labels when available.
  - Keeps boundary wording as private observation only.
- Added `tests/test_emotion_council_scene_frame.py`.
  - Low-energy nap/wake Scene Frame activates fatigue.
  - Technical Scene Frame activates stability.
  - Residue cache still preserves `no_stable_memory_write`.

## Direct Runtime Effect

- Scene Frame now affects three live paths:
  - renderer prompt context.
  - life reply policy and final reply shaping.
  - shadow-only emotion modulation.
- The nap/wake example can now move through:
  - temporal recall -> Scene Frame -> life reply policy -> emotion council fatigue bias.
- Technical work now biases emotion council toward stability instead of emotional drift.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_emotion_council.py tests\test_emotion_council_scene_frame.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_emotion_council_scene_frame.py tests\test_life_reply_policy_scene_frame.py tests\test_scene_frame.py -q`
  - 14 passed
- `.\.venv\Scripts\python.exe tests\smoke\initiative\emotion_council_smoke.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_emotion_council_scene_frame.py tests\test_life_reply_policy_scene_frame.py tests\test_scene_frame.py tests\test_runtime_context.py tests\test_living_memory_recall.py tests\test_temporal_memory_context.py -q`
  - 37 passed
- `.\.venv\Scripts\python.exe tests\smoke\voice\xinyu_life_reply_policy_smoke.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 604 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after`
  - pass
- `git diff --check -- xinyu_scene_frame.py xinyu_runtime_context.py xinyu_life_reply_policy.py xinyu_core_bridge.py xinyu_emotion_council.py tests\test_scene_frame.py tests\test_runtime_context.py tests\test_life_reply_policy_scene_frame.py tests\test_emotion_council_scene_frame.py`
  - pass; only existing LF/CRLF warnings.

## Not Done Yet

- Scene Frame does not directly alter memory candidate confidence.
- Scene Frame rules are still hand-written v1 heuristics.
- Scene Frame does not yet learn from owner approval/rejection.

## Next Batch Candidate

P62 Scene Frame Closeout Audit:

- Check all Scene Frame call sites.
- Verify it is provider/shim style, not a second recall algorithm.
- Verify private memory body boundaries.
- Write kept/merged/remaining risks for this "full scene intelligence" pass.

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

Recommended resume command:

`.\.venv\Scripts\python.exe -m pytest tests\test_emotion_council_scene_frame.py tests\test_life_reply_policy_scene_frame.py tests\test_scene_frame.py tests\test_runtime_context.py tests\test_living_memory_recall.py tests\test_temporal_memory_context.py -q`
