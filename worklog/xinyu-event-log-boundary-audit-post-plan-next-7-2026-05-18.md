# XinYu Event Log Boundary Audit

This report scans source path references against `stores/event_boundary_manifest.json`.
It does not read or print JSONL event bodies, raw QQ payloads, tokens, or private memory bodies.

- status: pass
- manifest_ok: True
- stream_count: 3
- undeclared_reference_count: 0

## Streams

- `memory/context/interaction_journal.jsonl` | stream=interaction_journal | decision=pass_declared_boundary | refs=1 | undeclared=0
  - reference_examples:
    - `xinyu_interaction_journal.py`
- `memory/context/proactive_request_history.jsonl` | stream=proactive_request_history | decision=pass_declared_boundary | refs=1 | undeclared=0
  - reference_examples:
    - `xinyu_core_bridge.py`
- `memory/relationships/owner_recent_events.jsonl` | stream=owner_recent_events | decision=pass_declared_boundary | refs=1 | undeclared=0
  - reference_examples:
    - `xinyu_persona_state.py`
