# XinYu Subtractive Inventory - 2026-05-17

Status: first autonomous inventory pass. No runtime behavior changed.

## Baseline

- Working directory: `D:\XinYu`
- Existing dirty worktree summary before this inventory:
  - `M`: 105 paths
  - `D`: 212 paths
  - `??`: 105 paths
- This pass treats those as pre-existing owner/worktree changes and does not revert them.
- Private raw state directories were not read: `memory/`, `runtime/`, `logs/`, `learning/self_found/`, `learning/owner_supplied/`.

## Live Startup Path

Current daily entry:

```text
Start-XinYu-Desktop.ps1
-> Start-XinYu-QQ.ps1
-> XinYu-Core/examples/agent-apps/xinyu/start_xinyu_core_bridge.ps1
-> XinYu-Core/examples/agent-apps/xinyu/start_xinyu_qq_gateway.ps1
-> XinYu_Desktop Electron main
```

Current live runtime chain:

```text
NapCatQQ
-> ws://127.0.0.1:6199/ws
-> xinyu_qq_gateway.py
-> http://127.0.0.1:8765/chat
-> xinyu_core_bridge.py
-> XinYu Core
```

Desktop bridge surface:

```text
XinYu_Desktop/src/main/xinyu_gateway.ts
-> http://127.0.0.1:8765/chat
-> http://127.0.0.1:8765/desktop/snapshot
-> ws://127.0.0.1:8766/desktop/events
```

## App File Distribution

Under `XinYu-Core/examples/agent-apps/xinyu`, excluding private runtime/memory/log/learning state:

| Area | Python files | Markdown files | Reading |
| --- | ---: | ---: | --- |
| root app directory | 225 | 43 | overloaded; main cleanup target |
| `custom/` | 79 | 0 | many plugin/engine bridge pairs |
| `tests/` | 313 | 3 | many smoke tests moved into tests tree, but git status shows many old root smoke deletes |
| `xinyu_v1/` | 79 | 0 | shadow/canary system, not production owner |
| `tools/` | 2 | 0 | low-risk support area |
| `project-plans/` | 0 | 20 | planning/reference material |
| `prompts/` | 0 | 13 | persona/writer compression target |

## High-Risk Large Files

| File | Lines | Current role | Subtractive reading |
| --- | ---: | --- | --- |
| `xinyu_core_bridge.py` | 6701 | production HTTP bridge and orchestration surface | still too large; should not receive new feature blocks |
| `xinyu_qq_gateway.py` | 3098 | NapCat/OneBot transport adapter | still too large; should remain transport only |
| `xinyu_dialogue_archive.py` | 1178 | dialogue archive, search, traces, memory candidates | likely store/service owner, not persona owner |
| `xinyu_emotion_council.py` | 1159 | emotion inference/state sidecar | candidate for living-state consolidation |
| `xinyu_proactive_presence.py` | 760 | proactive QQ candidates/ack | candidate for initiative policy consolidation |
| `xinyu_contextual_self_loop.py` | 661 | contextual self-loop state and prompt block | candidate provider into one recall/living-state chain |
| `xinyu_context_retrieval.py` | 605 | current recalled-context owner | best current base for `LivingMemoryRecall` owner |
| `xinyu_sparse_memory_router.py` | 561 | sparse expert route over recall candidates | should be internal scoring/provider component, not separate product surface |

## Config Plugin Surface

`config.yaml` currently declares 32 plugin bridge entries before tool writers. Most are bridge/engine pairs in `custom/`:

- time/context/memory sync
- visible reply guard
- automation and question pipeline
- initiative, slow reprocess, reflection, dream
- source gate/reliability/integration/request/search/comparison
- learner integration and learning quality
- AI self-iteration gate/review
- consolidation, retention, archive output/commit
- personality growth
- inner cycle, desktop thoughts, maintenance schedule

Subtractive reading: this is the main "too many metabolism organs" area. Keep only live plugins with evidence; move research or duplicated gates to `lab` after tests prove no active dependency.

## Recall/Memory Retrieval Evidence

Active production import:

```text
xinyu_core_bridge.py
  -> from xinyu_context_retrieval import log_recalled_context, retrieve_recalled_context
```

Current recall owner functions/types:

```text
xinyu_context_retrieval.py
  class RecalledContextItem
  class RecalledContextResult
  def render_recalled_context(...)
  def retrieve_recalled_context(...)
  def log_recalled_context(...)
```

Current internal recall components:

```text
xinyu_sparse_memory_router.py
  def build_sparse_memory_route(...)
  def apply_sparse_memory_route(...)

xinyu_retrieval_need_reranker.py
  def build_retrieval_need_profile(...)
  def rerank_recalled_items_with_report(...)

xinyu_retrieval_envelope.py
  class RetrievalCandidateEnvelope
  def recall_item_envelope(...)
  def case_envelope(...)

xinyu_dialogue_archive.py
  search/archive/log storage owner

xinyu_conversation_experience_matcher.py
  reviewed case matching; advisory hints only

xinyu_contextual_recall.py
  compact state-file prompt block

xinyu_contextual_self_loop.py
  current scene/self-loop snapshot

xinyu_recent_context_guard.py
  recent context health repair
```

Subtractive decision: `xinyu_context_retrieval.py` is the current practical owner. The next slice should introduce a named canonical owner surface, `xinyu_living_memory_recall.py`, and make the bridge use that public surface first. Existing modules become components behind that owner, then get merged or reduced one by one.

## Duplicate Capability Families

| Family | Evidence | First action |
| --- | --- | --- |
| bridge | 65+ bridge-named Python/test files | keep as adapters; block personality/memory decisions from entering bridge files |
| qq | 45+ QQ-named Python/test files | keep as adapter family; continue trimming `xinyu_qq_gateway.py` |
| memory/retrieval/context | 17+ memory family files plus recall/context modules | make `LivingMemoryRecall` the owner surface |
| dialogue/cases/archive | 20+ dialogue/case files | store/service/provider under recall, not separate behavior owner |
| source/learning gates | 22+ source-named files plus many custom plugins | classify live vs lab; avoid chain of gates |
| personality/voice/persona | 9+ personality files plus prompt fragments | compress into runtime persona contract |
| initiative/proactive/self-action | initiative/proactive/self-action modules and smokes | merge policy boundaries; keep permission gates explicit |
| tests/smokes | 313 tests, many old root smoke deletions | do not restore root smokes; rely on `tests/` tree unless command references break |

## Initial Keep/Merge/Lab/Delete Guidance

Keep now:

- `xinyu_core_bridge.py`
- `xinyu_qq_gateway.py`
- `xinyu_context_retrieval.py`
- `xinyu_dialogue_archive.py`
- `xinyu_retrieval_envelope.py`
- `xinyu_retrieval_need_reranker.py`
- `xinyu_sparse_memory_router.py`
- `xinyu_persona_runtime.py`
- `xinyu_visible_persona_voice.py`
- `xinyu_status.py`
- startup scripts

Merge or wrap next:

- recall owner surface over context retrieval/router/reranker/envelope
- contextual recall/self-loop as providers
- conversation experience matcher as advisory provider
- persona/voice prompt fragments into one contract

Move to lab candidate:

- AI self-iteration gate/review
- autonomous search and source-comparison research chain
- personality growth gate beyond stable contract
- dream/reflection/consolidation experiments that are not in the current turn chain

Do not delete yet:

- any config plugin target
- any module imported by `xinyu_core_bridge.py`, `xinyu_qq_gateway.py`, desktop main/preload, startup scripts, or active tests
- any file under private memory/runtime/log/learning state

## Next Required Output

Create the classification map before behavior changes:

```text
worklog/xinyu-module-classification-2026-05-17.md
```

Then implement the first safe recall slice:

```text
add xinyu_living_memory_recall.py
route bridge import through it
keep old context retrieval API as compatibility
run focused retrieval tests
```

