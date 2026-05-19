# XinYu P58 Scene Frame v1 Batch - 2026-05-19

## Scope

Capability group: current-scene intelligence before visible reply.

Goal: add a compact Scene Frame that summarizes current scene, time context,
owner state, task mode, memory relation, reply policy, and uncertainty before
the renderer writes a visible answer.

This batch is intentionally narrow. It does not replace the canonical living
memory recall algorithm and does not create a second recall path.

## Changes Completed

- Added `xinyu_scene_frame.py`.
  - New `SceneFrame` dataclass.
  - New `build_scene_frame(...)` provider.
  - New `render_scene_frame_prompt_block(...)` renderer.
  - Conservative v1 heuristics for:
    - `after_night_shift`
    - `recent_wake_from_rest`
    - `rest_related`
    - `late_night`
    - `time_bound_recall`
    - low-burden reply policy for tired/rest states.
- Integrated Scene Frame into `xinyu_runtime_context.build_renderer_memory_context(...)`.
  - Injects `[runtime/scene_frame]`.
  - Uses `[layer: scene_frame]`.
  - Reuses `contextual_self.current_scene` instead of duplicating full scene ownership.
  - Reads the canonical recall prompt block only as advisory context.
- Added `tests/test_scene_frame.py`.
  - Night-shift tired state.
  - Nap/wake temporal recall relation.
  - Project work direct execution mode.
- Extended `tests/test_runtime_context.py`.
  - Verifies Scene Frame appears in renderer context.
  - Verifies canonical recall is still single-path.
  - Verifies temporal recall drives `memory_relation: time_bound_recall`.

## Direct Runtime Effect

- Before reply rendering, XinYu now has a small scene frame like:
  - current scene: project, memory review, runtime status, emotional relation, etc.
  - time context: ordinary time, late night, after night shift, recent wake from rest.
  - owner state: low energy/tired when stated or inferred from temporal recall.
  - memory relation: current-turn-first, recalled continuity, explicit recall, time-bound recall.
  - reply policy: direct task answer, compact structured answer, warm boundary-aware answer, or short low-burden answer.

For the user's nap example, temporal recall can now surface
`recent_wake_from_nap`, and Scene Frame converts that into:

- `time_context: recent_wake_from_rest`
- `owner_state: low_energy_or_tired`
- `memory_relation: time_bound_recall`
- low-burden reply policy.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_scene_frame.py xinyu_runtime_context.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_scene_frame.py tests\test_runtime_context.py -q`
  - 13 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_scene_frame.py tests\test_runtime_context.py tests\test_temporal_memory_context.py tests\test_living_memory_recall.py -q`
  - 26 passed
- `.\.venv\Scripts\python.exe tests\smoke\memory\memory_braid_smoke.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 593 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after`
  - pass
- `git diff --check -- xinyu_scene_frame.py xinyu_runtime_context.py tests\test_scene_frame.py tests\test_runtime_context.py`
  - pass; only existing LF/CRLF warnings.

## Not Done Yet

- Scene Frame v1 is heuristic and conservative.
- It is not yet a broad multi-scene replay suite.
- It does not yet learn scene policies from failed/approved conversations.
- It does not yet feed back into memory write strength or emotion modulation.

## Next Batch Candidate

P59 Scene Replay Pack:

- Add replay fixtures for:
  - after night shift and tired owner.
  - just woke from nap.
  - late-night technical work.
  - relationship/emotional pressure.
  - runtime maintenance request.
- Verify Scene Frame output and visible reply policy stay coherent across those cases.
- Keep this as tests and small policy refinement only; do not expand into another parallel recall system.

## Recovery Point

Start from `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`.

Recently changed in this batch:

- `xinyu_scene_frame.py`
- `xinyu_runtime_context.py`
- `tests/test_scene_frame.py`
- `tests/test_runtime_context.py`

Recommended resume command:

`.\.venv\Scripts\python.exe -m pytest tests\test_scene_frame.py tests\test_runtime_context.py tests\test_temporal_memory_context.py tests\test_living_memory_recall.py -q`
