# XinYu Failure Scenarios

The canonical scenario pack is in:

```text
failure-scenarios/
```

It contains sanitized JSON scenarios for:

- owner-private greeting fast route
- stuck before route decision
- pre-model timeout containment
- model injection timeout
- renderer empty reply recovery
- stale running cancellation
- proactive candidate collision with a live owner reply

The scenario pack is intended for public research evidence. It asserts trace stages, expected health/operator state, visible behavior, memory impact, recovery action, and privacy notes.

Generate sanitized example traces with:

```powershell
.\.venv\Scripts\python.exe failure-scenarios\generate_sanitized_trace_examples.py
```

Validate with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\failure_scenarios\test_failure_scenarios.py -q
```
