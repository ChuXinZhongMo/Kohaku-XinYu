# XinYu

XinYu is a local owner-operated interactive agent project. Its goal is long-running continuity: remembering context through reviewed memory layers, recovering from slow or stuck replies with observable traces, and initiating contact only through explicit owner-private proactive gates.

## Runtime Path

```text
NapCat QQ -> xinyu_qq_gateway.py -> xinyu_core_bridge.py -> XinYu runtime
```

The QQ gateway is transport only. Core bridge owns routing, memory, personality/expression policy, proactive policy, and intervention state.

## Operator Tools

```powershell
.\.venv\Scripts\python.exe xinyu_status.py
.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network
.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network dashboard
```

## Research Artifacts

- `INTERACTIVITY-RESEARCH.md`
- `ARCHITECTURE.md`
- `TRACE-SCHEMA.md`
- `FAILURE-SCENARIOS.md`
- `LOCAL-INSPECTOR-DEMO.md`
- `MEMORY-LAYERS.md`
- `PRIVACY-BOUNDARY.md`
- `EXPRESSION-STABILITY.md`

## Local Start

```powershell
.\start_xinyu_core_bridge.ps1 -AllowInsecureLlmHttp
.\start_xinyu_qq_gateway.ps1
```

Stop:

```powershell
.\stop_xinyu_qq_gateway.ps1
.\stop_xinyu_core_bridge.ps1
```
