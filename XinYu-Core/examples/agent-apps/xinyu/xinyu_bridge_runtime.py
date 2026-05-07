from __future__ import annotations

"""
Runtime boundary notes for the XinYu core bridge split.

`xinyu_core_bridge.py` remains the executable entrypoint and owns the live
`XinYuBridgeRuntime` class for this pass. New endpoint-specific behavior belongs
in the neighboring modules:

- `xinyu_bridge_learning.py` for learning ingest/study endpoints.
- `xinyu_bridge_proactive.py` for proactive claim/ack wiring.
- `xinyu_bridge_renderer.py` for outward renderer construction and checks.
- `xinyu_bridge_http.py` for HTTP transport.

The runtime class should keep shrinking by delegating new endpoint logic here
instead of adding more behavior to the entrypoint.
"""

RUNTIME_ENTRYPOINT = "xinyu_core_bridge.XinYuBridgeRuntime"
