# XinYu INTRA-Inspired Retrieval V2 Plan

Date: 2026-05-15
Status: phase_1_3_plus_replay_implemented
Scope: memory/context retrieval, dialogue archive recall, stable memory recall, conversation experience cases

Implementation status:

- 2026-05-15: Phase 1 implemented as deterministic need-aware recall reranking.
- 2026-05-15: Phase 2 implemented as a safe candidate envelope for recalled context and conversation experience cases.
- 2026-05-15: Phase 3 implemented as an optional runtime embedding backend for dialogue semantic retrieval, with hash fallback.
- 2026-05-15: Added deterministic chat replay fixtures for recalled context and conversation experience regressions.
- 2026-05-15: Added a local chat replay exporter that turns live regression/log rows into sanitized replay fixture candidates.
- 2026-05-15: Added safe auto-promotion for replay candidates: strict redaction, validation-before-append, duplicate filtering, and replay test execution.
- 2026-05-15: True INTRA remains a research-only track because current production LLM providers do not expose cross-attention or encoder states.

## Core Decision

Use the paper's retrieval principle, not its full model internals.

INTRA depends on encoder-decoder internals: pre-encoded encoder states, decoder cross-attention queries, retrieval tokens, and attention-space scoring. XinYu currently uses external LLM providers through API-compatible and Codex backends, so the runtime cannot access those internal states.

The practical XinYu adaptation is:

```text
candidate recall
-> current generation need profile
-> need-aware reranking
-> compact recalled-context pack
-> existing prompt pressure and memory gates
```

This should make recall answer-aware without replacing the LLM or bypassing existing safety, privacy, voice, and memory boundaries.

## Why This Fits XinYu

XinYu already has the right outer shell:

- `xinyu_context_retrieval.py`: live recalled-context pack for the current turn.
- `xinyu_dialogue_archive.py`: local dialogue archive with FTS, LIKE, and optional local semantic fallback.
- `xinyu_contextual_self_loop.py`: current scene and retrieval pressure signals.
- `xinyu_contextual_recall.py`: compact state-file recall for runtime context.
- `xinyu_conversation_experience_matcher.py`: reviewed case matching.
- `xinyu_prompt_pressure.py` and sidecars: prompt admission boundaries.

The missing part is not another raw index. The missing part is a scorer that asks:

```text
What evidence does the next answer need?
```

Instead of only:

```text
What text looks similar to the user's words?
```

## Non-Goals

- Do not implement full INTRA over T5Gemma2 in this phase.
- Do not require access to decoder cross-attention or encoder states.
- Do not replace the current external LLM provider stack.
- Do not turn recalled snippets into hard rules.
- Do not increase raw history dumping into the prompt.
- Do not let group/public material shape owner-private relationship memory.
- Do not mutate stable memory from retrieval hits.

## Phase 1: Need-Aware Reranker

Goal:

Add a small, deterministic reranking layer after current candidate collection.

Inputs:

- current user text
- query terms
- visible turn features
- recall intent markers
- source kind, score, summary, relevance, confidence

Outputs:

- reranked `RecalledContextItem` list
- same advisory prompt format as today
- trace notes showing that reranking ran

Initial scoring signals:

- direct recall request boosts dialogue tail and archive
- technical/project work boosts stable memory and project plan context
- self-core architecture questions boost self-core architecture context
- owner pressure/status questions boost recent tail and action/project state
- high source confidence gives a small bonus
- weak query overlap is penalized unless the source is an explicit architecture fallback
- privacy and source gates stay outside the scorer and remain authoritative

Validation:

- context retrieval smoke still passes
- direct "just now" recall still prefers dialogue tail
- technical project recall admits stable memory when relevant
- self-core architecture recall still marks content advisory-only
- new unit tests prove need-aware reranking changes order only when the current turn demands it

## Phase 2: Unified Candidate Envelope

Goal:

Stop each source from inventing unrelated score semantics.

Add a common candidate envelope:

```text
source_type
source_scope
base_score
need_score
authority
freshness
privacy_scope
evidence_kind
admission_reason
boundary
```

Use it for:

- dialogue tail
- dialogue archive
- temporal traces
- stable memory files
- self-core architecture project plans
- conversation experience cases

## Phase 3: Better Retrieval Backend

Goal:

Upgrade recall candidates before reranking.

Work items:

- replace default hash semantic fallback with a real multilingual embedding path where dependencies are available
- reuse `xinyu_runtime.session.embedding.create_embedder()` where practical
- keep FTS as an always-available fallback
- add hybrid RRF between FTS, semantic, and source-specific scores
- preserve local/private storage defaults

## Phase 4: Optional Model-Aware Rerank

Only after Phase 1-3 are stable:

- add an optional small cross-encoder or LLM-judge reranker for top candidates
- keep it default-off
- enforce strict prompt budget and privacy boundaries
- log decisions without raw private text

This is the closest practical substitute for INTRA's decoder-query signal while XinYu remains on external LLM APIs.

## Phase 5: True INTRA Research Track

Only worth starting if XinYu gains a local, controllable encoder-decoder model.

Requirements:

- local model with accessible encoder states and decoder cross-attention
- chunk encoder cache
- retrieval-token training or adaptation path
- GPU/storage budget for token-level memories
- a benchmark proving better recall than Phase 1-4

Until then, full INTRA is a research branch, not the product path.

## Implemented Slice

Implemented:

1. Added `xinyu_retrieval_need_reranker.py`.
2. Added `xinyu_retrieval_envelope.py`.
3. Integrated need-aware reranking at the end of `retrieve_recalled_context()`.
4. Applied the same need-profile alignment to conversation experience case matching.
5. Added optional runtime embedding support to dialogue semantic retrieval through `XINYU_DIALOGUE_SEMANTIC_EMBEDDING_PROVIDER`.
6. Added focused tests for direct recall, project recall, self-core recall ordering, semantic fallback, and owner scenario regressions.
7. Added JSONL replay fixtures and deterministic runners for real owner follow-up, local-control, status, archive, self-core, privacy-leak, group-status, and quiet-chat cases.
8. Added `xinyu_chat_replay_fixture_exporter.py` to convert local live-chat/regression rows into sanitized, review-marked replay candidates under `runtime/replay_candidates`.
9. Added `--auto-promote-safe` to strict-redact, validate, dedupe, and append low-risk candidates to formal replay fixtures.
10. Added `smoke_run.py --group replay` as the cheap pre-change regression entry for retrieval replay, conversation experience replay, and exporter tests.
11. Kept the rendered prompt shape unchanged.

Validation:

- `python -m pytest examples/agent-apps/xinyu/tests/test_retrieval_need_reranker.py examples/agent-apps/xinyu/tests/test_conversation_experience_matcher.py examples/agent-apps/xinyu/tests/test_conversation_experience_sidecar.py examples/agent-apps/xinyu/tests/test_prompt_pressure.py examples/agent-apps/xinyu/tests/test_dialogue_semantic_backend.py examples/agent-apps/xinyu/tests/test_context_retrieval_owner_scenarios.py`
- `python examples/agent-apps/xinyu/tests/smoke/memory/context_retrieval_smoke.py`
- `python examples/agent-apps/xinyu/tests/smoke/dialogue/conversation_experience_sidecar_smoke.py`
- `python examples/agent-apps/xinyu/tests/smoke/dialogue/dialogue_semantic_retrieval_smoke.py`
- `python -m py_compile` on the touched runtime modules

Latest validation:

- `python -m pytest examples/agent-apps/xinyu/tests/test_retrieval_replay_cases.py examples/agent-apps/xinyu/tests/test_conversation_experience_replay_cases.py`
- `python -m pytest examples/agent-apps/xinyu/tests`
- `python examples/agent-apps/xinyu/tests/smoke/memory/context_retrieval_smoke.py`
- `python examples/agent-apps/xinyu/tests/smoke/dialogue/conversation_experience_sidecar_smoke.py`
- `python examples/agent-apps/xinyu/tests/smoke/dialogue/dialogue_semantic_retrieval_smoke.py`
- `python -m py_compile` on runtime retrieval modules and replay test runners

Local log-to-replay workflow:

- `python xinyu_chat_replay_fixture_exporter.py --source runtime/regression/last_live_chat_baseline.json --include-passing-context --auto-promote-safe --run-replay-tests`
- Low-risk cases are strict-redacted, validated, deduped, and appended automatically.
- Higher-risk cases remain in `runtime/replay_candidates/*.jsonl` for manual review.
- `python smoke_run.py --group replay`
