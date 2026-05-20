# XinYu Interactivity Research Package

XinYu is a local, owner-operated interactive agent project focused on long-running continuity rather than single-turn chat quality. The research question is how a personal agent can keep conversational momentum, memory boundaries, visible expression, and operator control understandable during real use.

## Research Focus

- Long-running owner-private interaction with observable turn state.
- Recovery from slow or stuck replies without hiding failures behind canned text.
- Proactive contact that is explainable, owner-private, rate-limited, and reversible.
- Memory candidates that require provenance and review before becoming stable memory.
- Public evidence artifacts that avoid private QQ IDs, raw owner chat, tokens, and local paths.

## Current Architecture

See `ARCHITECTURE.md` for the operator-facing diagram. The short version is:

```text
QQ/NapCat -> xinyu_qq_gateway.py -> xinyu_core_bridge.py -> XinYu runtime
                                     |-> turn route trace
                                     |-> intervention API
                                     |-> memory candidate review
                                     |-> proactive claim/ack lifecycle
                                     |-> local inspector/dashboard
```

The QQ gateway is transport only. Core bridge owns routing, turn state, memory sidecars, expression guards, and proactive policy.

## Evidence Included

- `failure-scenarios/`: sanitized regression scenarios for stuck turns, timeouts, renderer failures, stale cancellation, and proactive/live reply collision.
- `TRACE-SCHEMA.md`: public trace field reference.
- `LOCAL-INSPECTOR-DEMO.md`: screenshot-safe operator demo instructions.
- `MEMORY-LAYERS.md` and `PRIVACY-BOUNDARY.md`: memory and privacy constraints.
- `EXPRESSION-STABILITY.md`: expression regression boundaries.
- `GRANT-PROGRESS-REPORT-TEMPLATE.md`: progress report template for research updates.

## Evaluation Approach

Each scenario should be judged by:

- whether trace and health explain where the turn stopped
- whether visible behavior remains honest and non-template
- whether recovery can be triggered without editing raw files
- whether memory effects stay in runtime/candidate layers until reviewed
- whether public artifacts remain sanitized

## Current Limitations

- The project is local-first and not a reproducible hosted service.
- Many runtime files are intentionally private and excluded from public evidence.
- The v1 stack is still canary/shadow for selected paths, not the full runtime.
- The dashboard is intentionally minimal; the CLI inspector is the stable operator surface.
