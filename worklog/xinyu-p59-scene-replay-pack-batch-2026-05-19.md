# XinYu P59 Scene Replay Pack Batch - 2026-05-19

## Scope

Capability group: Scene Frame replay coverage.

Goal: turn Scene Frame v1 from a single insertion point into a replay-checked
scene router for common owner states.

## Changes Completed

- Extended `tests/test_scene_frame.py` with a table-driven replay pack.
- Covered six scene families:
  - after night shift and tired owner.
  - just woke from nap with temporal recall.
  - late-night technical work.
  - relationship/emotional pressure.
  - runtime maintenance request.
  - explicit recall request.
- Refined `xinyu_scene_frame._scene_id(...)`:
  - explicit recall language such as "remember/previous/said before" now routes to `memory_review`.

## Direct Runtime Effect

- Scene Frame now treats explicit continuity questions as memory review instead
  of ordinary chat.
- Late-night technical work stays a task execution scene instead of becoming
  emotional support by assumption.
- Relationship pressure stays in `relational_support`.
- Runtime health/status requests stay compact and structured.
- Nap/wake temporal recall still maps to low-burden response posture.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_scene_frame.py tests\test_scene_frame.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_scene_frame.py tests\test_runtime_context.py tests\test_temporal_memory_context.py tests\test_living_memory_recall.py -q`
  - 32 passed
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 599 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after`
  - pass
- `git diff --check -- xinyu_scene_frame.py tests\test_scene_frame.py xinyu_runtime_context.py tests\test_runtime_context.py`
  - pass; only existing LF/CRLF warnings.

## Not Done Yet

- Scene Frame is now replay-checked, but it still only writes an advisory prompt block.
- The visible reply layer does not yet consume Scene Frame as a typed policy object.
- Memory writes do not yet receive Scene Frame as an input.
- Emotion modulation does not yet receive Scene Frame as an input.

## Next Batch Candidate

P60 Scene Policy Consumer:

- Find the visible reply composition path that consumes renderer memory context.
- Add a small adapter that extracts Scene Frame policy fields without parsing private memory bodies.
- Make at least one visible reply or reply-policy flow explicitly respect:
  - `short_direct_low_burden`
  - `warm_boundary_aware`
  - `compact_structured_answer`
- Keep the adapter as a shim/provider. Do not create another recall path.

## Recovery Point

Start from `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`.

Recently changed in P58/P59:

- `xinyu_scene_frame.py`
- `xinyu_runtime_context.py`
- `tests/test_scene_frame.py`
- `tests/test_runtime_context.py`

Recommended resume command:

`.\.venv\Scripts\python.exe -m pytest tests\test_scene_frame.py tests\test_runtime_context.py tests\test_temporal_memory_context.py tests\test_living_memory_recall.py -q`
