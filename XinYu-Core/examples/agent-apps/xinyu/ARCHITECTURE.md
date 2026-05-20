# XinYu Architecture

This diagram reflects the post-intervention API architecture.

```mermaid
flowchart LR
    Owner[Owner / QQ] --> NapCat[NapCat OneBot]
    NapCat --> Gateway[xinyu_qq_gateway.py<br/>transport, normalize, claim/ack]
    Gateway --> Core[xinyu_core_bridge.py<br/>/chat, /health, /turn/*]
    Core --> Runtime[XinYu Runtime<br/>model, renderer, sidecars]
    Runtime --> Gateway

    Core --> RouteTrace[runtime/turn_route_trace.jsonl]
    Core --> Presence[memory/context/runtime_self_presence.md]
    Core --> Inspector[xinyu_local_inspector.py]
    Core --> Intervention[Turn Intervention API<br/>current, cancel, retry, skip, continue]
    Core --> Memory[Dialogue Archive<br/>memory candidates]
    Core --> Proactive[Proactive Request<br/>state, claim, ack, lifecycle trace]
    Core --> Dashboard[runtime/local_inspector_dashboard.html]

    Inspector --> Intervention
    Proactive --> Gateway
```

## Boundaries

- QQ gateway is transport only.
- Core bridge owns route decisions, memory sidecars, expression guards, proactive policy, and intervention state.
- Stable memory writes are gated; runtime observations first become candidates or traces.
- The inspector and dashboard expose sanitized operator facts, not raw private chat.

## Main Runtime Paths

- Live chat: `/chat`
- Health: `/health`
- Turn inspection: `/turn/current`
- Turn recovery: `/turn/cancel`, `/turn/retry-lightweight`, `/turn/skip-sidecar`, `/turn/continue`, `/turn/status-message`
- Proactive delivery: `/proactive`, `/proactive/ack`, `/qq/outbox/claim`, `/qq/outbox/ack`
- Local inspector: `xinyu_local_inspector.py`
