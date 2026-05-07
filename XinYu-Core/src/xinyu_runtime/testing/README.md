# testing/

Reusable test infrastructure for XinYu Runtime. Provides fake/mock
primitives for testing the agent framework without real LLMs or external
services. `ScriptedLLM` plays back predetermined responses with configurable
streaming simulation. `TestAgentBuilder` constructs lightweight agent setups
(Controller + Executor + OutputRouter) without config files. `OutputRecorder`
and `EventRecorder` capture all output and events for test assertions.

## Files

| File | Description |
|------|-------------|
| `__init__.py` | Re-exports all test primitives |
| `llm.py` | `ScriptedLLM`, `ScriptEntry`: deterministic LLM that follows a script of predefined responses |
| `agent.py` | `TestAgentBuilder`: builder for creating test agents with injected fakes and builtin tools |
| `output.py` | `OutputRecorder`: captures writes, streaming chunks, and activity notifications for assertions |
| `events.py` | `EventRecorder`, `RecordedEvent`: records events with timing and source information |

## Dependencies

- `xinyu_runtime.builtins.tool_catalog` (get_builtin_tool)
- `xinyu_runtime.core.controller` (Controller, ControllerConfig)
- `xinyu_runtime.core.events` (TriggerEvent)
- `xinyu_runtime.core.executor` (Executor)
- `xinyu_runtime.core.registry` (Registry)
- `xinyu_runtime.core.session` (Session)
- `xinyu_runtime.llm.base` (LLMProvider, ChatResponse)
- `xinyu_runtime.llm.message` (Message)
- `xinyu_runtime.modules.output.base` (BaseOutputModule)
- `xinyu_runtime.modules.output.router` (OutputRouter)
- `xinyu_runtime.parsing` (ToolCallEvent, CommandResultEvent)

