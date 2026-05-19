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
- keep_as_memory_event_log_pending_manifest: 1
- keep_until_event_boundary_is_defined: 2
- keep_until_persona_store_boundary_exists: 1
- manual_review: 1
- migrate_candidate: 9
- migrate_candidate_after_caller_update: 7

## Items

- `XinYu-Core/examples/agent-apps/xinyu/memory/consolidation_state.json` | category=durable_runtime_state | decision=migrate_candidate | target=stores/runtime_state | refs=0
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/daily_digest.json` | category=durable_runtime_state | decision=migrate_candidate_after_caller_update | target=stores/runtime_state | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/services/daily_digest.py`
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/impulse_soup_state.json` | category=durable_runtime_state | decision=migrate_candidate_after_caller_update | target=stores/runtime_state | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_impulse_soup.py`
  - handling: State JSON should be owned by a store/service; keep in place until the owner module migrates.
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
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/interaction_journal.jsonl` | category=episodic_event_log | decision=keep_until_event_boundary_is_defined | target=memory/events-or-stores | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_interaction_journal.py`
  - handling: Event logs need an explicit event boundary before migration.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/proactive_request_history.jsonl` | category=episodic_event_log | decision=keep_until_event_boundary_is_defined | target=memory/events-or-stores | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_core_bridge.py`
  - handling: Event logs need an explicit event boundary before migration.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/sticker_send_state.generated.json` | category=manual_structured_memory_review | decision=manual_review | target=manual | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_sticker_pack.py`
  - handling: No path rule matched; review manually before changing boundaries.
- `XinYu-Core/examples/agent-apps/xinyu/memory/self/goldmark_positive_overlay.json` | category=persona_runtime_overlay | decision=keep_until_persona_store_boundary_exists | target=stores/persona_runtime | refs=2
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_runtime_context.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_goldmark.py`
  - handling: Persona/runtime overlay should move only after persona runtime store ownership is explicit.
- `XinYu-Core/examples/agent-apps/xinyu/memory/relationships/owner_recent_events.jsonl` | category=private_relationship_event_log | decision=keep_as_memory_event_log_pending_manifest | target=memory/relationships | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_persona_state.py`
  - handling: Private relationship events may be stable memory; keep in place until a manifest/type contract exists.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/review_inbox_cursor.json` | category=runtime_cursor_or_decision_store | decision=migrate_candidate_after_caller_update | target=stores/review_state | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_review_inbox.py`
  - handling: Cursor/decision JSON is durable state, not recall memory; move only with the owning service.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/review_inbox_decisions.json` | category=runtime_cursor_or_decision_store | decision=migrate_candidate_after_caller_update | target=stores/review_state | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_review_inbox.py`
  - handling: Cursor/decision JSON is durable state, not recall memory; move only with the owning service.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/qq_outbox_queue.json` | category=runtime_queue | decision=migrate_candidate_after_caller_update | target=stores/queues-or-runtime | refs=4
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_runtime_presence.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_outbox.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway.py`
    - `XinYu-Core/examples/agent-apps/xinyu/start_xinyu_core_bridge.ps1`
  - handling: Queues are operational state; migrate only after producers and consumers are updated together.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/self_action_gateway_approval_queue.jsonl` | category=runtime_queue | decision=migrate_candidate_after_caller_update | target=stores/queues-or-runtime | refs=2
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_bridge_desktop_snapshot.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_self_action_gateway.py`
  - handling: Queues are operational state; migrate only after producers and consumers are updated together.
- `XinYu-Core/examples/agent-apps/xinyu/memory/context/impulse_soup_trace.jsonl` | category=runtime_trace_log | decision=archive_candidate_after_caller_update | target=runtime/logs-or-archive | refs=2
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_runtime_presence.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_impulse_soup.py`
  - handling: Trace logs should not be canonical memory; archive only after caller checks.
- `XinYu-Core/examples/agent-apps/xinyu/memory/creative/planning/inspiration/safe_extracts.jsonl` | category=source_extract_log | decision=migrate_candidate_after_caller_update | target=library/source_extracts | refs=1
  - reference_examples:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_creative_writing.py`
  - handling: Looks like source material, not live private memory; migrate only after reference checks.

## Safety Rule

- Keep every item in place until its owning module and fallback behavior are reviewed.
- This is a triage report, not a move/delete instruction.
