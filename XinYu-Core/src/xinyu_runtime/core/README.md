# core/ (Runtime and Orchestration)

The core module contains the runtime engine that powers every XinYu Runtime
agent. All components communicate through a unified `TriggerEvent` model.

## Files

| File | Responsibility |
|------|----------------|
| `__init__.py` | Package marker; re-exports for convenience |
| `agent.py` | `Agent` class public API (`from_path`, `run`, `start`, `stop`, `inject_input`) |
| `agent_handlers.py` | `AgentHandlersMixin` 鈥?event processing + controller loop orchestration |
| `agent_tools.py` | `AgentToolsMixin` 鈥?tool dispatch, direct/background result collection |
| `agent_runtime_tools.py` | Lower-level tool dispatch helpers used by `AgentToolsMixin` |
| `agent_messages.py` | `AgentMessagesMixin` 鈥?edit / regenerate / rewind past messages |
| `backgroundify.py` | `BackgroundifyHandle` / `PromotionResult` 鈥?mid-flight direct鈫抌ackground task promotion |
| `controller.py` | `Controller` + `ControllerConfig` 鈥?LLM conversation loop + event queue |
| `conversation.py` | `Conversation` context manager (message list, truncation, system prompt) |
| `executor.py` | Background tool runner; `asyncio.create_task()` during streaming |
| `events.py` | `TriggerEvent`, `EventType`, constructors (`create_tool_complete_event`, etc.) |
| `channel.py` | `AgentChannel`, `ChannelMessage`, `ChannelRegistry` 鈥?named pub/sub channels |
| `compact.py` | Non-blocking auto-compact (`CompactManager`) 鈥?background summarization of the old context zone |
| `session.py` | `Session` 鈥?keyed shared state registry (channels, scratchpad, TUI, extras) |
| `environment.py` | `Environment` 鈥?inter-creature state per user request |
| `scratchpad.py` | Session-scoped key-value working memory (framework-managed, cheap) |
| `termination.py` | `TerminationConditions` 鈥?max_turns / max_tokens / max_duration / idle / keywords |
| `config.py` | `load_agent_config` / `build_agent_config` 鈥?YAML / JSON / TOML + env interpolation |
| `config_types.py` | Config dataclasses (`AgentConfig`, `InputConfig`, `ControllerConfig`, 鈥? |
| `constants.py` | Framework magic numbers (truncation limits, status preview lengths) |
| `trigger_manager.py` | `TriggerManager` 鈥?owns trigger instances + async tasks, hot-add/remove |
| `job.py` | `JobStore`, `JobResult`, `JobState` 鈥?job status tracking |
| `loader.py` | `ModuleLoader` 鈥?dynamic import of custom tools / inputs / outputs / subagents |
| `registry.py` | `Registry` 鈥?generic module registry for tools and sub-agents |

## Dependency direction

- Leaves: `constants`, `events`, `config_types`, `backgroundify`, `job`,
  `scratchpad`, `session`, `environment`, `channel`, `termination`, `registry`,
  `loader` (each imports only `utils/` + stdlib).
- Mid-layer: `controller`, `conversation`, `executor`, `compact`,
  `trigger_manager`, `config`.
- Top: `agent.py` + its mixins (`agent_handlers.py`, `agent_tools.py`,
  `agent_runtime_tools.py`, `agent_messages.py`). These also mix in
  `AgentInitMixin` from `../bootstrap/agent_init.py`.

Imports across package boundaries: `core/` is imported by almost everything
(`bootstrap/`, `builtins/`, `terrarium/`, `serving/`, `api/`, `compose/`),
but NEVER imports them back.

## Key entry points

- `Agent.from_path(path, 鈥?` 鈥?construct an agent from a config folder
- `Agent.run()` 鈥?main event loop; drives input 鈫?controller 鈫?tools
- `TriggerEvent` (in `events.py`) 鈥?the single event type that flows through the system
- `Controller` 鈥?LLM conversation loop
- `CompactManager` (in `compact.py`) 鈥?background context compaction
- `TriggerManager` 鈥?runtime trigger add/remove

## Dependency diagram

```
    agent.py  (mixes in Init / Handlers / Tools / Messages)
        鈹?        鈹溾攢鈹€ bootstrap/*              (factories)
        鈹溾攢鈹€ controller.py 鈹€鈹€鈹€ conversation.py
        鈹?      鈹?        鈹?      鈹溾攢鈹€ parsing/         (stream parser)
        鈹?      鈹斺攢鈹€ llm/             (provider)
        鈹?        鈹溾攢鈹€ agent_tools.py 鈹€鈹€鈹€ agent_runtime_tools.py 鈹€鈹€鈹€ backgroundify.py
        鈹?      鈹?        鈹?      鈹斺攢鈹€ executor.py 鈹€鈹€鈹€ job.py
        鈹?        鈹溾攢鈹€ compact.py               (runs alongside controller)
        鈹溾攢鈹€ trigger_manager.py       (fires TriggerEvents into controller)
        鈹斺攢鈹€ session.py + environment.py + channel.py + scratchpad.py
                鈹?                鈹斺攢鈹€ events.py + config_types.py + constants.py (leaves)
```

## Notes

- Three Agent mixins (handlers / tools / messages) exist only to keep file
  sizes under the 600-line cap. They are not independently useful.
- `compact.py` is non-blocking: the agent keeps producing output during
  summarization; the splice happens atomically when the summary lands.
- `backgroundify.py` lets a direct-mode tool promote itself to background
  mid-flight (e.g. long bash that exceeded its expected budget), returning
  a `PromotionResult` to the controller while the task keeps running.

## See also

- `../bootstrap/README.md` 鈥?how the init factories plug into `AgentInitMixin`
- `plans/inventory-runtime.md` 搂1鈥撀? 鈥?lifecycle, controller loop, tool pipeline
- `docs/concepts/foundations/` 鈥?event model + execution semantics

