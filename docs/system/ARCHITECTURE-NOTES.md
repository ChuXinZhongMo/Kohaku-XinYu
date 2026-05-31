# XinYu Architecture Notes

Date: 2026-05-07

This note records the current local XinYu architecture and the reason for preserving it without broad refactoring today.

## Current Stage

XinYu is a local, long-running personal AI system in an early beta / growth-stage runtime form. It is not a clean productized architecture yet, but it is beyond a demo: Desktop, QQ/NapCat, Core, memory, autonomy surfaces, Codex delegation, and v1 shadow/canary paths are all present and running locally.

Current live chain:

```text
Owner
├─ XinYu Desktop
│  └─ HTTP 127.0.0.1:8765 + WS 127.0.0.1:8766
│     └─ xinyu_core_bridge.py
└─ QQ / NapCat
   └─ OneBot reverse WS 127.0.0.1:6199
      └─ xinyu_qq_gateway.py
         └─ HTTP 127.0.0.1:8765
            └─ xinyu_core_bridge.py
```

Core then calls into `xinyu_runtime`, custom plugins/engines, memory/runtime files, v1 shadow/canary modules, Codex delegation, and the configured LLM provider.

## Main Boundaries

- `XinYu-Core/src/xinyu_runtime/`: reusable runtime framework: Agent, Controller, tools, subagents, API/studio, sessions, LLM providers.
- `XinYu-Core/examples/agent-apps/xinyu/`: live local XinYu app: bridge, QQ gateway, custom engines, prompts, tests, v1, local operational scripts.
- `XinYu_Desktop/`: Electron desktop shell. It presents local state and sends owner interactions; it does not own core identity or long-term memory.
- `NapCatQQ/`: local QQ/NapCat runtime environment. It is an external adapter dependency, not XinYu source.
- `XinYu-TinyKernel/`: local TinyKernel service and training workspace. XinYu can call it through a disabled-by-default compose shadow path; it does not send QQ/Desktop output, execute tools, or write stable memory.
- `XinYu-Autonomy/`: owner-visible autonomy exports and live junctions into core state.
- `XinYu-Local-Scope/`: controlled local file area for Inbox, Requests, Workspace, and Outbox.

## Core Assets

The highest-value original assets are the lived structure and behavior across these areas:

- `xinyu_core_bridge.py`: current production bridge and orchestration surface.
- `xinyu_qq_gateway.py`: native QQ/NapCat transport bridge.
- `custom/*.py`: autonomous maintenance, learning, reflection, source gates, memory sync, and related behavior engines.
- `xinyu_v1/`: newer layered runtime direction with routing, memory, reasoning, emotion, and observability.
- `prompts/`, `memory-seeds/`, and policy documents: the language, boundaries, and continuity model.
- `XinYu_Desktop/src/`: local desktop presence surface.

## Current Architectural Risk

The system works, but the live path is structurally concentrated.

- `xinyu_core_bridge.py` is too large and owns too many responsibilities.
- `xinyu_qq_gateway.py` is larger than a transport adapter should be.
- Runtime state is spread across Markdown, JSON, JSONL, SQLite, logs, and projected files.
- The workspace is strongly bound to this local Windows environment and fixed ports.

This is not a reason to rewrite today. It is a reason to preserve the current system, add version history, and only refactor later in small behavior-preserving slices.

## Decision For Today

No broad refactor today.

Rules for the protective phase:

- Do not wash or normalize original naming/style just to make the code look generic.
- Do not bulk-format large source files.
- Do not rewrite bridge/gateway behavior.
- Do not rename core concepts around personality, memory, autonomy, or local scope.
- Do document the current state, generate source manifests, and establish private version history.

Future refactors should be surgical: move one responsibility at a time, keep old behavior observable, and preserve the authorship and design trail.

## Verification Snapshot

Use this command for a redacted live status report:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_status.py --json
```

The report generated during this protective pass should be stored under `artifacts/protection-snapshots/2026-05-07/`.
