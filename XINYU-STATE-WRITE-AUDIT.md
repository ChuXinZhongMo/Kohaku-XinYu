# XinYu State Write Audit

Date: 2026-05-07
Scope: first-pass write-surface audit before introducing broader state governance.

## Directory Semantics

| Directory | Intended meaning | Write rule |
| --- | --- | --- |
| `memory/` | Long-term memory and projected stable state | Do not migrate or rewrite body content without explicit owner approval. Projection-style state files may be audited first. |
| `memory/events/` | Source-traceable memory event streams | Append-only in principle; current helpers may rewrite full JSONL files for dedupe and should be isolated before expansion. |
| `runtime/` | Temporary state, traces, queues, debug snapshots | Safe first migration target for atomic writes and JSONL append helpers. |
| `logs/` | Diagnostic logs | Append-only or tool-owned output; keep out of behavior logic. |
| `cache/` | Rebuildable cache | May be rewritten if regeneration is deterministic and documented. |
| `learning/` | Owner supplied or self-found learning material | Treat as source material, not chat memory. Preserve current redaction and scope checks. |

## Existing Helper Surfaces

| File | Helper behavior | Notes |
| --- | --- | --- |
| `xinyu_state_io.py` | `read_text`, `write_text`, `write_text_atomic`, markdown field helpers | Good seed, but `write_text` is non-atomic and there is no JSON/JSONL helper yet. |
| `xinyu_runtime_presence.py` | Atomic markdown/JSON writes and JSONL append for runtime presence | Strong pattern for presence state, but local to one module. |
| `xinyu_qq_outbox.py` | Atomic JSON queue writes, dispatch state writes, lock file | Good candidate to reuse through future state service without changing queue shape. |
| `xinyu_review_inbox.py` | Atomic JSON/state writes and JSONL append | Similar pattern to QQ outbox. |
| `xinyu_self_choice_store.py` | Atomic state JSON and entropy JSONL ledger | Strong runtime-state pattern with lock handling. |
| `custom/memory_event_schema.py` | JSONL load/dump helpers for memory event files | Dedupe-oriented full rewrites; should remain isolated from runtime append helpers. |
| `xinyu_v1/storage/atomic.py` | v1 atomic text helper | v1-local; do not merge into legacy state writes until boundary is explicit. |
| `xinyu_v1/memory/jsonl_store.py` | v1 JSONL load/dump store | v1-local memory store; no legacy takeover without canary proof. |
| `xinyu_v1/storage/sqlite_meta.py` | v1 SQLite metadata | v1-local. Keep separate from legacy runtime state. |

## Core Bridge Direct Writes

| Area | Current path examples | Category | Current risk | Next action |
| --- | --- | --- | --- | --- |
| Autonomous mind loop trace | `memory/context/autonomous_mind_loop_trace.log` | Log-like trace under memory | Append trace lives in `memory/context`, not `runtime/logs` | Audit only; do not move until readers are known. |
| Autonomous mind loop state | `memory/context/autonomous_mind_loop_state.md` | Projection | Migrated to `state_service.atomic_write_text` in Loop 34 | Keep body shape; validate with `autonomous_state_smoke.py`. |
| Desktop proactive request update | `memory/context/proactive_request_state.md` | Projection | Migrated to `state_service.atomic_write_text` in Loop 27 | Keep field semantics and validate with `xinyu_desktop_proactive_smoke.py`. |
| Promise follow-up state | `memory/context/promise_followup_state.md` | Projection | Migrated to `state_service.atomic_write_text` in Loop 13 | Keep body shape; validate with `promise_followup_state_smoke.py` and focused promise follow-up pytest. |
| Debug live system prompt | `runtime/debug/last_live_system_prompt.txt` | Runtime diagnostic cache | Migrated to `state_service.atomic_write_text(final_newline=False)` in Loop 75 | Runtime diagnostic only; env-gated and owner-private-gated. |
| Codex background traces | `memory/knowledge/codex_*_trace.log` | Log-like traces under memory | Append logs near knowledge material | Audit only; moving paths could break current review workflow. |
| Dialogue tail sync | runtime dialogue tail helpers | Runtime/session state | Helper-owned, not direct bridge text write except save call | Leave behind existing helper boundary. |

## QQ Gateway Direct Writes

| Area | Current path examples | Category | Current risk | Next action |
| --- | --- | --- | --- | --- |
| Trusted user config | `xinyu_qq_gateway.config.json` | Configuration | Runtime command can persist trust changes to config | Migrated to `state_service.atomic_write_json(sort_keys=False)` in Loop 74 after trust policy extraction; keep config shape and validate with `qq_trust_config_persistence_smoke.py`. |
| Inbound/rich/sticker traces | `runtime/qq_inbound_trace.jsonl`, `runtime/qq_rich_context_trace.jsonl`, `runtime/qq_sticker_import_trace.jsonl` | Runtime traces | Migrated to `state_service.append_jsonl` in Loop 35 | Keep row fields; validate with `qq_runtime_trace_smoke.py` and QQ gateway smoke. |
| Recent sticker state | `runtime/qq_recent_sticker_state.json` | Runtime projection | Migrated to `state_service.atomic_write_json` in Loop 36 | Keep row fields; validate with `qq_recent_sticker_state_smoke.py`. |
| Group shadow observations | `runtime/group_shadow/group_shadow_observations.jsonl`, `memory/context/group_shadow_state.md` | Runtime trace plus projection | Migrated to `state_service.append_jsonl` and `atomic_write_text` in Loop 37 | Keep no-reply/stable-memory-blocked boundary fields; validate with `group_shadow_state_smoke.py`. |
| Review output | Local-Scope review markdown/jsonl via `xinyu_qq_review.py` | Owner review artifact | Tool-owned output | Keep separate from runtime state service. |
| Gateway ack spool | `runtime/gateway_ack_spool.jsonl` | Runtime transport state | Already has dedicated tests | Do not rewrite without `tests/test_gateway_ack_spool.py`. |

## Memory And Custom Engine Writes

| Family | Examples | Category | Migration posture |
| --- | --- | --- | --- |
| Dream/reflection/archive engines | `custom/dream_output_engine.py`, `custom/reflection_output_engine.py`, `custom/archive_commit_engine.py` | Long-term memory and archive projections | Do not migrate in this run without explicit, focused tests and owner approval for memory body risk. |
| Source/learning engines | `custom/source_*`, `custom/learner_integration_engine.py`, `xinyu_learning_library.py` | Knowledge/source material | Keep current source gate semantics. Do not reclassify as runtime cache. |
| Proactivity engines | `xinyu_proactivity_scorer.py`, `xinyu_impulse_soup.py`, `xinyu_proactive_request_loop.py` | Projections plus runtime traces | Good future state-service candidates after bridge and QQ splits. |
| Persona/voice self-learning | `xinyu_voice_learning.py`, `xinyu_voice_promotion_gate.py`, expression learning | Review-only memory state | Do not alter stable profile writes or promotion gates. |

## First Migration Candidates

1. Add a small `state_service.py` or extend `xinyu_state_io.py` with:
   - `atomic_write_text(path, text, newline=True)`
   - `atomic_write_json(path, data, sort_keys=False)`
   - `append_jsonl(path, row)`
   - `read_json(path, default)`
2. Migrate only runtime/projection writes first:
   - `xinyu_core_bridge.py` proactive request state update. Done in Loop 27.
   - `xinyu_core_bridge.py` promise follow-up state. Done in Loop 13.
   - `xinyu_core_bridge.py` autonomous mind loop state. Done in Loop 34.
   - QQ runtime trace appends after QQ trust/outbox extraction. Done in Loop 35.
   - QQ trusted-user config persistence. Done in Loop 74.
   - Core debug live system prompt runtime cache. Done in Loop 75.
3. Leave long-term memory body writes in existing modules until the owner approves a memory-body migration slice.

## Required Validation For State Changes

- `git diff --check`
- `python -m py_compile <changed-python-files>`
- `state_io_smoke.py`
- Relevant feature smoke for the touched caller:
  - Core bridge: `bridge_probe_smoke.py`
  - Desktop/proactive state: `xinyu_desktop_rest_smoke.py`
  - QQ state: `xinyu_qq_gateway_smoke.py`, `qq_outbox_smoke.py`, `check_sent_index.py`
  - v1 state: v1 pytest gate from `XINYU-VALIDATION-MATRIX.md`

## Explicit Non-Changes In This Audit

- No memory body content was changed.
- No runtime state files were deleted or moved.
- No QQ outbound behavior was exercised.
- No v1 traffic behavior was changed.
- One low-risk projection writer was wired into `state_service.py`; broader memory body writes were not migrated.
