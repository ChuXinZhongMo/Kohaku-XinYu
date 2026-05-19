# XinYu Queue Boundary Audit

This report scans source path references against `stores/queue_boundary_manifest.json`.
It does not read or print queue bodies, raw QQ payloads, tokens, or private memory bodies.

- status: pass
- manifest_ok: True
- queue_count: 1
- undeclared_reference_count: 0

## Queues

- `memory/context/qq_outbox_queue.json` | queue=qq_outbox | decision=pass_declared_queue_boundary | refs=4 | undeclared=0
  - reference_examples:
    - `start_xinyu_core_bridge.ps1`
    - `xinyu_qq_gateway.py`
    - `xinyu_qq_outbox.py`
    - `xinyu_runtime_presence.py`
