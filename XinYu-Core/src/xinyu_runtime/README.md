# xinyu_runtime

Primary runtime package for XinYu Runtime.

This package derives from XinYu Runtime and keeps attribution plus a legacy
`xinyu_runtime` compatibility import surface. New XinYu code should import
`xinyu_runtime.*`.

## Top-Level Files

- `__init__.py` -- package marker, version info, attribution
- `__main__.py` -- CLI entry point (`python -m xinyu_runtime ...`)
- `__briefcase__.py` -- Briefcase desktop-app bootstrap
- `packages.py` -- package manager for install / uninstall / edit extension packages
- `registry.json` -- bundled curated package registry

## Subpackages

| Package | Purpose |
| --- | --- |
| `core/` | Agent, controller, executor, events, config, session, registry, compact, runtime tools |
| `bootstrap/` | Agent initialization factories for LLM, tools, IO, subagents, triggers, plugins |
| `builtins/` | Built-in tools, sub-agents, inputs, outputs, TUI, rich CLI, user commands |
| `builtin_skills/` | On-demand markdown documentation for tools and sub-agents |
| `modules/` | Base classes and protocols |
| `terrarium/` | Multi-agent runtime and `TerrariumAPI` |
| `compose/` | Agent composition algebra over `AgentSession` |
| `mcp/` | MCP client manager and meta-tools |
| `serving/` | Transport-agnostic service layer |
| `api/` | FastAPI HTTP and WebSocket server |
| `cli/` | `xinyu-runtime` command dispatcher |
| `session/` | Session persistence via `.xinyu` files plus memory search |
| `llm/` | LLM provider abstraction, Codex OAuth, presets, profiles |
| `parsing/` | Streaming state machine for LLM output |
| `prompt/` | System prompt aggregation, templating, plugin and skill loading |
| `commands/` | Inline framework commands |
| `testing/` | Test infrastructure |
| `utils/` | Shared utilities |

## Compatibility

`src/xinyu_runtime` is now a compatibility layer that forwards Python modules
to `xinyu_runtime`. Keep it until all legacy scripts, old sessions, and the
`kt` command have been verified.

See `../../LICENSE` for the XinYu Runtime-derived license and attribution
requirements.


