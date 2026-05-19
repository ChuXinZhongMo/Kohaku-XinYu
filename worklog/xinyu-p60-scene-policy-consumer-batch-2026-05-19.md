# XinYu P60 Scene Policy Consumer Batch - 2026-05-19

## Scope

Capability group: Scene Frame consumer path.

Goal: make Scene Frame affect an existing reply-policy flow instead of remaining
only a renderer prompt block.

## Changes Completed

- Extended `xinyu_life_reply_policy.build_life_reply_policy(...)`.
  - Accepts optional `scene_frame`.
  - Reads Scene Frame fields as a provider input:
    - `reply_policy`
    - `task_mode`
    - `time_context`
    - `owner_state`
    - `memory_relation`
  - Maps Scene Frame reply policies into existing life reply policy behavior:
    - `short_direct_low_burden`
    - `short_gentle_low_burden`
    - `warm_low_burden`
    - `compact_structured_answer`
    - `warm_boundary_aware`
    - `direct_task_answer`
- Extended `xinyu_life_reply_policy.build_life_reply_prompt_block(...)`.
  - Exposes scene policy as prompt-side policy facts.
  - Does not expose private memory bodies.
- Extended `xinyu_core_bridge._build_life_reply_policy(...)`.
  - Builds a Scene Frame after canonical living recall is available.
  - Passes visible turn, canonical recall context, and evaluated turn time into Scene Frame.
  - Passes Scene Frame into life reply policy.
- Extended `xinyu_scene_frame._visible_turn_scene(...)`.
  - Boolean visible-turn fields now map to project/emotional scene where available.
- Added `tests/test_life_reply_policy_scene_frame.py`.
  - Low-burden nap/wake Scene Frame affects reply shaping.
  - Technical Scene Frame marks the turn as technical.
  - Relationship pressure Scene Frame creates warm boundary-aware policy.

## Direct Runtime Effect

- A time-bound recall such as "recent_wake_from_nap" can now become:
  - Scene Frame: `time_context: recent_wake_from_rest`
  - Scene Frame: `reply_policy: short_gentle_low_burden`
  - Life reply policy: `mode: low_energy`
  - Life reply policy: `reply_pressure: short`
  - Final reply shaping: optional tail questions are suppressed and non-technical replies can be shortened.
- Technical work inferred by Scene Frame can mark the life reply policy as technical even when the old regex misses it.
- Relationship pressure can make the life reply policy relation-aware without adding another prompt system.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_scene_frame.py xinyu_life_reply_policy.py xinyu_core_bridge.py tests\test_life_reply_policy_scene_frame.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_life_reply_policy_scene_frame.py tests\test_scene_frame.py tests\test_runtime_context.py -q`
  - 22 passed
- `.\.venv\Scripts\python.exe tests\smoke\voice\xinyu_life_reply_policy_smoke.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_dialogue_curiosity_bridge_injection.py tests\test_living_memory_recall.py tests\test_temporal_memory_context.py tests\test_life_reply_policy_scene_frame.py -q`
  - 66 passed
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 602 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after`
  - pass
- `git diff --check -- xinyu_scene_frame.py xinyu_life_reply_policy.py xinyu_core_bridge.py tests\test_life_reply_policy_scene_frame.py tests\test_scene_frame.py xinyu_runtime_context.py tests\test_runtime_context.py`
  - pass; only existing LF/CRLF warnings.

## Not Done Yet

- Scene Frame now affects reply policy, but not memory write strength.
- Scene Frame now affects reply policy, but not emotion-council modulation.
- Scene Frame remains heuristic v1; no learning loop updates its rules yet.

## Next Batch Candidate

P61 Scene Write/Emotion Boundary:

- Inspect memory candidate extraction and emotion modulation paths.
- Choose the smaller safe target:
  - add Scene Frame metadata to memory candidate routing, or
  - add Scene Frame policy to emotion-council prompt/modulation.
- Keep private memory bodies out of logs and tests.
- Add focused tests first, then minimal implementation.

## Recovery Point

Start from `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`.

Recently changed in P58-P60:

- `xinyu_scene_frame.py`
- `xinyu_runtime_context.py`
- `xinyu_life_reply_policy.py`
- `xinyu_core_bridge.py`
- `tests/test_scene_frame.py`
- `tests/test_runtime_context.py`
- `tests/test_life_reply_policy_scene_frame.py`

Recommended resume command:

`.\.venv\Scripts\python.exe -m pytest tests\test_life_reply_policy_scene_frame.py tests\test_scene_frame.py tests\test_runtime_context.py tests\test_living_memory_recall.py tests\test_temporal_memory_context.py -q`
