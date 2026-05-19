# Stores

Persistence helpers live here. They can read or write app-local state files,
but they should not own turn policy, persona behavior, or transport routing.

- `state_service.py` provides atomic text/JSON writes, JSON reads, and JSONL append helpers. The app-root `state_service.py` is only a compatibility wrapper.
- `review_state.py` owns the review inbox cursor/decision store contract. It still writes to the legacy `memory/context/review_inbox_*.json` paths as a compatibility fallback, but callers should depend on this store boundary instead of hard-coding those memory paths.
- `self_action_queue.py` owns the self-action approval queue contract. It still reads and writes the legacy `memory/context/self_action_gateway_approval_queue.jsonl` path as a compatibility fallback, but runtime and desktop callers should depend on this store boundary instead of hard-coding the queue path.
- `persona_runtime_overlay.py` owns the Goldmark persona/runtime overlay contract. It still reads and writes the legacy `memory/self/goldmark_positive_overlay.json` path as compatibility storage, but mark, dehydration, and runtime context callers should depend on this store boundary.
- `daily_digest_state.py` owns the ephemeral daily digest JSON contract. It still reads and writes the legacy `memory/context/daily_digest.json` path as compatibility storage; digest state markdown and trace logging remain in the service layer.
- `impulse_soup_state.py` owns the impulse soup JSON contract. It still reads and writes the legacy `memory/context/impulse_soup_state.json` path as compatibility storage; impulse markdown summaries and trace logging remain in `xinyu_impulse_soup.py`.
- `slow_state_modulator_state.py` owns the allostatic slow-state JSON contract. It still reads and writes the legacy `memory/context/slow_state_modulator_state.json` path as compatibility storage; prompt rendering remains in `xinyu_slow_state_modulator.py`.
- `sticker_send_state.py` owns the generated sticker send cooldown/recent-send JSON contract. It still reads and writes the legacy `memory/context/sticker_send_state.generated.json` path as compatibility storage.
- `source_extracts.py` owns the safe creative source-extract JSONL contract. It keeps the legacy `memory/creative/planning/inspiration/safe_extracts.jsonl` path as compatibility storage and only writes already-sanitized extract metadata supplied by the creative writing service.
- `event_boundary_manifest.json` records metadata-only ownership for compatibility JSONL event streams. It does not authorize body migration, snapshots, or stable-memory writes.
- `runtime_trace_manifest.json` records metadata-only ownership for compatibility runtime trace streams. It keeps trace bodies out of stable memory and restricts raw readers to declared owner/projection modules.
- `queue_boundary_manifest.json` records metadata-only ownership for compatibility runtime queues. It keeps private queue bodies out of stable memory and restricts raw readers to declared producer/consumer/projection modules.
- `orphan_runtime_state_manifest.json` records metadata-only hold decisions for zero-reference runtime JSON files. It blocks deletion and body migration until an owner/archive decision is reviewed.
- `memory_library_manifest.json` records the redacted boundaries between lived memory, external library material, reviewed cases, learning material, runtime traces, and logs.
