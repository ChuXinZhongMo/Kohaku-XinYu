# terrarium/

Multi-agent orchestration runtime. The terrarium is a **pure wiring layer**
with no intelligence of its own: it loads standalone creature configs,
creates channels between them, injects channel triggers, and manages
lifecycle. Intelligence lives in creatures (and in the optional root agent
that sits OUTSIDE the terrarium).

## Files

| File | Responsibility |
|------|----------------|
| `__init__.py` | Re-exports `TerrariumRuntime`, `TerrariumAPI`, configs, hot-plug, observer |
| `runtime.py` | `TerrariumRuntime` 鈥?lifecycle orchestration (start, stop, channel wiring) with `HotPlugMixin` |
| `api.py` | `TerrariumAPI` 鈥?programmatic facade wrapping a `TerrariumRuntime` |
| `config.py` | `TerrariumConfig`, `CreatureConfig`, `ChannelConfig`, `load_terrarium_config`, `build_channel_topology_prompt` |
| `factory.py` | `build_creature`, `build_root_agent` 鈥?construct Agent instances; wire triggers and topology prompt |
| `creature.py` | `CreatureHandle` 鈥?wrapper around an `Agent` with terrarium metadata (channels, config) |
| `output_wiring.py` | `TerrariumOutputWiringResolver` 鈥?resolves `output_wiring` targets to live `Agent` instances and dispatches `creature_output` events |
| `hotplug.py` | `HotPlugMixin` 鈥?add / remove creatures and channels at runtime without restart |
| `observer.py` | `ChannelObserver`, `ObservedMessage` 鈥?non-destructive channel message recording |
| `output_log.py` | `OutputLogCapture`, `LogEntry` 鈥?tee wrapper that captures creature output for observability |
| `persistence.py` | `attach_session_store`, `build_conversation_from_messages` 鈥?session store wiring and resume helpers |
| `tool_manager.py` | `TerrariumToolManager` 鈥?shared state for terrarium management tools (stored in environment) |
| `tool_registration.py` | `ensure_terrarium_tools_registered` 鈥?lazy import of terrarium tools to avoid circular imports |
| `cli.py` | CLI subcommands (`kt terrarium run` / `resume` / `list`), TUI + headless drivers |
| `cli_output.py` | `CLIOutput` 鈥?minimal prefixed-stdout output for headless terrarium mode |

## Dependency direction

Imported by: `cli/` (via `cli/__init__.py` and `cli_rich/`), `api/` (indirectly
via `serving/`), `serving/manager.py`, `builtins/tools/terrarium_*.py`
(lazy).

Imports: `core/` (Agent, channel, conversation, environment, session),
`builtins/inputs.NoneInput`, `builtins/tool_catalog` (for the root agent),
`modules/output`, `modules/trigger/channel`, `session/store`, `utils/logging`.

One-way dependency: `terrarium/` 鈫?`core/`, never `core/` 鈫?`terrarium/`.

## Key entry points

- `TerrariumRuntime(config).start()` 鈥?construct + start all creatures
- **`TerrariumAPI(runtime)`** 鈥?the stable programmatic facade. Most external
  callers (HTTP API, root-agent tools, tests) talk to the terrarium through
  this, not through `TerrariumRuntime` directly. Exposes:
  - channel ops: `channel_list`, `channel_read`, `channel_send`, `observe`
  - creature ops: `creature_list`, `creature_start`, `creature_stop`, `status`
  - lifecycle: `stop`, `status`
- `build_creature(name, config, ...)` / `build_root_agent(config, runtime)`
  鈥?the two Agent-construction factories
- `HotPlugMixin.add_creature` / `remove_creature` / `add_channel`
- `ChannelObserver.observe(channel_name)` 鈥?non-destructive stream
- `load_terrarium_config(path)` 鈥?parse terrarium YAML

## Notes

- A terrarium has NO LLM of its own. The optional root agent sits OUTSIDE
  the terrarium (a normal creature with terrarium tools bound) 鈥?it is the
  user's interface; the terrarium obeys its orders through `TerrariumAPI`.
- **Output wiring** is installed on every creature's agent during
  `TerrariumRuntime.start()` via `_install_output_wiring_resolver()`. Each
  creature's `_finalize_processing` (in `core/agent_handlers.py`) calls
  `resolver.emit(...)` at turn-end; the resolver constructs a
  `creature_output` `TriggerEvent` and pushes it via
  `asyncio.create_task(target._process_event(event))` per target 鈥?fire-
  and-forget so the source's turn-finalisation doesn't block on slow
  receivers. See `core/output_wiring.py` for the core protocol + no-op
  default resolver (used by standalone agents).
- `tool_registration.py` exists purely to break the
  `core 鈫?builtins/tools 鈫?terrarium 鈫?core` circular import cycle. Tools
  are registered only on first terrarium use.
- `ChannelObserver` never consumes messages from a channel 鈥?it attaches a
  callback so observers and normal listeners co-exist.
- Session persistence works exactly like single-agent sessions, but each
  creature gets its own `.xinyu` file; the terrarium writes a sidecar
  index linking them.

## See also

- `../core/README.md` 鈥?`Agent` + channel primitives
- `../serving/manager.py` 鈥?`XinYuManager.terrarium_*` methods (HTTP layer)
- `../builtins/tools/terrarium_*.py` 鈥?the tools the root agent uses to drive the terrarium
- `docs/concepts/multi-agent/` 鈥?creature vs terrarium vs root agent model


