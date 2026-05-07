# session/

Session persistence backed by the XinYu session store. Stores everything needed to
resume an agent or terrarium in a single `.xinyu` file (SQLite): conversation
snapshots, append-only event logs, channel message history, sub-agent
conversations, scratchpad state, token usage, and full-text search indexes.
`SessionOutput` is an output module that captures all agent events without
modifying the processing loop. `resume.py` rebuilds agents and terrariums
from saved state.

## Files

| File | Description |
|------|-------------|
| `__init__.py` | Re-exports `SessionStore` |
| `store.py` | `SessionStore`: persistent storage with 8 table groups (meta, state, events, channels, subagents, jobs, conversation, fts) via the XinYu session store |
| `output.py` | `SessionOutput`: output module that records text chunks, tool activity, and processing state to the store |
| `resume.py` | `resume_agent`, `resume_terrarium`: rebuild from `.xinyu` file, inject saved conversation and scratchpad |

## Dependencies

- `xinyu_runtime.builtins.inputs` (create_builtin_input, for resume IO)
- `xinyu_runtime.builtins.outputs` (create_builtin_output, for resume IO)
- `xinyu_runtime.core.agent` (Agent)
- `xinyu_runtime.core.conversation` (Conversation)
- `xinyu_runtime.modules.output.base` (OutputModule)
- `xinyu_runtime.terrarium.config` (load_terrarium_config)
- `xinyu_runtime.terrarium.runtime` (TerrariumRuntime)
- `xinyu_runtime.utils.logging`
- Third-party: `kohakuvault` (KVault, TextVault)


