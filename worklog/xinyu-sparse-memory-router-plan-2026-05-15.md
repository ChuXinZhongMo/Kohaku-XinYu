# XinYu Sparse Memory Router Plan - 2026-05-15

## Goal

Build the first practical version of the MoE-style memory idea as sparse memory routing, not model training.

Current turn input should route to a small set of memory experts, retrieve only useful memory lanes, and keep live turn facts above older memory.

## V1 Shape

- Router: heuristic scores from current text, visible turn flags, retrieval need, and live transport metadata.
- Experts: recent dialogue, project/task, tool/plugin, owner relation, emotion residue, identity/voice, world knowledge, failure memory, self core.
- Retrieval: reuse existing recalled_context retrieval and reranker.
- Output: preserve RecalledContextResult, envelope logging, and prompt block compatibility.
- Safety rule: current owner message and live QQ current-turn facts outrank stale runtime memory.

## Implementation Steps

1. Add `xinyu_sparse_memory_router.py`.
2. Route before stable memory scanning so only selected memory refs are read.
3. Apply route score adjustments before the existing need-aware reranker.
4. Add notes for traceability without exposing raw user text.
5. Test expert sparsity, plugin/API routing, and stale QQ runtime demotion.

## Frontend/Runtime Status Integration

- `memory.recall.used` desktop events now include `selectedExperts`, `currentTurnFacts`, and a structured `route` object.
- `route.decisions` exposes each expert score, selected flag, and reason markers without raw user text.
- `/desktop/snapshot` carries the same fields through `recentMemoryEvents`.
- `xinyuState` carries `latest_memory_route_summary`, `latest_memory_route_experts`, and `latest_memory_current_turn_facts` for lightweight front-panel display.
- `recalled_context_log.notes_json.memory_route` records selected experts and live current-turn facts for later analysis.

## Next Iterations

- Add embedding similarity inside each expert lane.
- Feed route decisions into runtime presence metrics.
- Learn expert weights from accepted/rejected recall logs.
- Add contradiction detectors for API quota/local-model status, plugin install state, and desktop frontend health.
