# XinYu Structured Memory P0 Triage

Generated from paths plus source-code reference file names only.
It does not read or print JSON/JSONL memory bodies, raw QQ content, tokens, or secrets.

- total_p0_items: 22

## Category Counts

- durable_runtime_state: 11
- episodic_event_log: 2
- manual_structured_memory_review: 1
- persona_runtime_overlay: 1
- private_relationship_event_log: 1
- runtime_cursor_or_decision_store: 2
- runtime_queue: 2
- runtime_trace_log: 1
- source_extract_log: 1

## Initial Decision Counts

- archive_candidate_after_caller_update: 1
- compat_store_owner_exists: 4
- manifested_compat_event_log: 2
- manifested_private_event_log: 1
- manual_review: 1
- migrate_candidate: 9
- migrate_candidate_after_caller_update: 4

## Items

- `XinYu-Core/examples/agent-apps/xinyu/memory/consolidation_state.json` | category=durable_runtime_state | decision=migrate_candidate | target=stores/runtime_state | refs=0
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/daily_digest.json` | category=durable_runtime_state | decision=compat_store_owner_exists | target=stores/daily_digest_state | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/stores/daily_digest_state.py`
  - handling: Daily digest JSON has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/impulse_soup_state.json` | category=durable_runtime_state | decision=compat_store_owner_exists | target=stores/impulse_soup_state | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/stores/impulse_soup_state.py`
  - handling: Impulse soup JSON has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.
- `XinYu-Core/examples/agent-apps/xinyu/memory/initiative_state.json` | category=durable_runtime_state | decision=migrate_candidate | target=stores/runtime_state | refs=0
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/maintenance_schedule.json` | category=durable_runtime_state | decision=migrate_candidate | target=stores/runtime_state | refs=0
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/personality_change_state.json` | category=durable_runtime_state | decision=migrate_candidate | target=stores/runtime_state | refs=0
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/personality_self_review_state.json` | category=durable_runtime_state | decision=migrate_candidate | target=stores/runtime_state | refs=0
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/question_pipeline.json` | category=durable_runtime_state | decision=migrate_candidate | target=stores/runtime_state | refs=0
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/reflection/closed_loop_state.json` | category=durable_runtime_state | decision=migrate_candidate | target=stores/runtime_state | refs=0
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/runtime_bridge.json` | category=durable_runtime_state | decision=migrate_candidate | target=stores/runtime_state | refs=0
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/runtime_bridge_state.json` | category=durable_runtime_state | decision=migrate_candidate | target=stores/runtime_state | refs=0
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/interaction_journal.jsonl` | category=episodic_event_log | decision=manifested_compat_event_log | target=stores/event_boundary_manifest | refs=2
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/stores/event_boundary_manifest.json`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_interaction_journal.py`
  - handling: Episodic event log has metadata-only manifest ownership; keep in place and do not migrate bodies without review.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/proactive_request_history.jsonl` | category=episodic_event_log | decision=manifested_compat_event_log | target=stores/event_boundary_manifest | refs=2
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/stores/event_boundary_manifest.json`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_core_bridge.py`
  - handling: Episodic event log has metadata-only manifest ownership; keep in place and do not migrate bodies without review.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/sticker_send_state.generated.json` | category=manual_structured_memory_review | decision=manual_review | target=manual | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_sticker_pack.py`
  - handling: No path rule matched; review manually before changing boundaries.
- `XinYu-Core/examples/agent-apps/xinyu/memory/self/goldmark_positive_overlay.json` | category=persona_runtime_overlay | decision=compat_store_owner_exists | target=stores/persona_runtime_overlay | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/stores/persona_runtime_overlay.py`
  - handling: Persona/runtime overlay has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.
- `XinYu-Core/examples/agent-apps/xinyu/memory/relationships/owner_recent_events.jsonl` | category=private_relationship_event_log | decision=manifested_private_event_log | target=stores/event_boundary_manifest | refs=2
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/stores/event_boundary_manifest.json`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_persona_state.py`
  - handling: Private relationship event log has metadata-only manifest ownership; keep in place and do not migrate bodies without review.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/review_inbox_cursor.json` | category=runtime_cursor_or_decision_store | decision=migrate_candidate_after_caller_update | target=stores/review_state | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/stores/review_state.py`
  - handling: Cursor/decision JSON is durable state, not recall memory; move only with the owning service.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/review_inbox_decisions.json` | category=runtime_cursor_or_decision_store | decision=migrate_candidate_after_caller_update | target=stores/review_state | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/stores/review_state.py`
  - handling: Cursor/decision JSON is durable state, not recall memory; move only with the owning service.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/qq_outbox_queue.json` | category=runtime_queue | decision=migrate_candidate_after_caller_update | target=stores/queues-or-runtime | refs=4
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/start_xinyu_core_bridge.ps1`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_outbox.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_runtime_presence.py`
  - handling: Queues are operational state; migrate only after producers and consumers are updated together.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/self_action_gateway_approval_queue.jsonl` | category=runtime_queue | decision=compat_store_owner_exists | target=stores/self_action_queue | refs=2
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/stores/self_action_queue.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_self_action_gateway.py`
  - handling: Self-action approval queue has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/impulse_soup_trace.jsonl` | category=runtime_trace_log | decision=archive_candidate_after_caller_update | target=runtime/logs-or-archive | refs=2
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_impulse_soup.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_runtime_presence.py`
  - handling: Trace logs should not be canonical memory; archive only after caller checks.
- `XinYu-Core/examples/agent-apps/xinyu/memory/creative/planning/inspiration/safe_extracts.jsonl` | category=source_extract_log | decision=migrate_candidate_after_caller_update | target=library/source_extracts | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_creative_writing.py`
  - handling: Looks like source material, not live private memory; migrate only after reference checks.

## Safety Rule

- Keep every item in place until its owning module and fallback behavior are reviewed.
- This is a triage report, not a move/delete instruction.
