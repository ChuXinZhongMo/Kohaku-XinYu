"""CLI run command  - launch an agent from a config folder."""

import asyncio
from pathlib import Path
from uuid import uuid4

from xinyu_runtime.builtins.cli_rich.app import RichCLIApp
from xinyu_runtime.builtins.cli_rich.input import RichCLIInput
from xinyu_runtime.builtins.cli_rich.output import RichCLIOutput
from xinyu_runtime.core.agent import Agent
from xinyu_runtime.core.config import load_agent_config
from xinyu_runtime.session.resume import _create_io_modules
from xinyu_runtime.session.store import SessionStore
from xinyu_runtime.utils.logging import (
    configure_utf8_stdio,
    enable_stderr_logging,
    get_logger,
    set_level,
)
from xinyu_runtime.utils.paths import readable_dirs, xinyu_path

logger = get_logger(__name__)

_SESSION_DIR = xinyu_path("sessions")


def _session_dirs_for_read() -> list[Path]:
    dirs: list[Path] = []
    for directory in [_SESSION_DIR, *readable_dirs("sessions")]:
        if directory not in dirs and directory.exists():
            dirs.append(directory)
    return dirs or [_SESSION_DIR]


async def _run_agent_rich_cli(agent: Agent) -> None:
    """Run an agent under the rich CLI (prompt_toolkit Application).

    The main loop is driven by RichCLIApp, not agent.run(). We start
    the agent's modules manually, replay any pending resume events into
    real terminal scrollback, then enter the rich CLI loop.
    """
    app = RichCLIApp(agent)
    # Replace the agent's default output with one wired to the rich CLI app
    rich_output = RichCLIOutput(app)
    agent.output_router.default_output = rich_output

    await agent.start()

    # Resume: replay session history to scrollback. Normally agent.run()
    # would do this, but we own the main loop so we have to do it
    # ourselves. Has to happen BEFORE app.run_async() so the writes go
    # to real terminal scrollback (not into prompt_toolkit's screen).
    pending = getattr(agent, "_pending_resume_events", None)
    if pending:
        try:
            app.replay_session(pending)
        except Exception as e:
            logger.debug("Failed to replay session history", error=str(e))
        agent._pending_resume_events = None

    try:
        await app.run()
    finally:
        await agent.stop()


def _has_custom_io(config) -> tuple[bool, bool]:
    """Return whether the creature config uses custom/package input/output."""
    custom_input = config.input.type in {"custom", "package"}
    custom_output = config.output.type in {"custom", "package"}
    return custom_input, custom_output


def _should_capture_session_activity(config, io_mode: str | None) -> bool:
    """Capture session activity only for CLI/rich CLI/TUI I/O.

    When ``kt run`` uses creature-defined custom/package I/O, keep session
    persistence for text/history but do not mirror activity/logging into the
    session event stream. That capture is only intended for the built-in
    terminal UIs.
    """
    if io_mode is not None:
        return io_mode in {"cli", "tui"}
    return config.input.type in {"cli", "tui"} or config.output.type in {
        "cli",
        "tui",
    }


def _resolve_effective_io(config, io_mode: str | None) -> tuple[str, str]:
    """Return the effective (input_type, output_type) for the run.

    Explicit ``--mode`` wins. Otherwise, use the creature's configured
    I/O module types. Used to decide whether the terminal is free for
    stderr logging.
    """
    if io_mode is not None:
        return io_mode, io_mode
    return config.input.type, config.output.type


def _should_log_to_stderr(log_stderr: str, input_type: str, output_type: str) -> bool:
    """Resolve the ``--log-stderr`` flag against the effective I/O types.

    ``auto`` turns on stderr logging when neither input nor output is a
    full-screen UI (``cli``/``tui``), so custom, package, stdout, and
    plain I/O all get terminal logs without corrupting a UI frame.
    """
    if log_stderr == "on":
        return True
    if log_stderr == "off":
        return False
    terminal_ui = {"cli", "tui"}
    return input_type not in terminal_ui and output_type not in terminal_ui


def _warn_io_override_if_needed(config, io_mode: str) -> None:
    """Warn when an explicit CLI mode overrides configured custom I/O."""
    custom_input, custom_output = _has_custom_io(config)
    overridden: list[str] = []
    if custom_input:
        overridden.append(f"input={config.input.type}")
    if custom_output:
        overridden.append(f"output={config.output.type}")
    if not overridden:
        return
    joined = ", ".join(overridden)
    print("Warning: --mode " f"{io_mode} overrides configured custom I/O ({joined}).")


def run_agent_cli(
    agent_path: str,
    log_level: str,
    session: str | None = None,
    io_mode: str | None = None,
    llm_override: str | None = None,
    log_stderr: str = "auto",
) -> int:
    """Run an agent from CLI."""

    configure_utf8_stdio(log=True)

    # Setup logging
    set_level(log_level)

    # Check path exists
    path = Path(agent_path)
    if not path.exists():
        print(f"Error: Agent path not found: {agent_path}")
        return 1

    config_file = path / "config.yaml"
    if not config_file.exists():
        config_file = path / "config.yml"
        if not config_file.exists():
            print(f"Error: No config.yaml found in {agent_path}")
            return 1

    config = load_agent_config(str(path))

    input_type, output_type = _resolve_effective_io(config, io_mode)
    if _should_log_to_stderr(log_stderr, input_type, output_type):
        enable_stderr_logging(log_level)

    # If the user does not specify --mode, respect the creature's configured
    # input/output modules exactly. Only explicit --mode should override them.
    resolved_mode = io_mode
    use_rich_cli = resolved_mode == "cli"

    store = None
    session_file = None
    try:
        io_kwargs: dict = {}
        if resolved_mode is not None:
            _warn_io_override_if_needed(config, resolved_mode)
            if use_rich_cli:
                io_kwargs["input_module"] = RichCLIInput()
                io_kwargs["output_module"] = RichCLIOutput(app=None)
            else:
                inp, out = _create_io_modules(resolved_mode)
                io_kwargs["input_module"] = inp
                io_kwargs["output_module"] = out

        # Create agent
        agent = Agent.from_path(str(path), llm_override=llm_override, **io_kwargs)

        # Attach session store (default: ON)
        if session is not None:
            if session == "__auto__":
                _SESSION_DIR.mkdir(parents=True, exist_ok=True)
                session_file = (
                    _SESSION_DIR / f"{agent.config.name}_{id(agent):08x}.xinyu"
                )
            else:
                session_file = Path(session)

            store = SessionStore(session_file)
            store.init_meta(
                session_id=uuid4().hex,
                config_type="agent",
                config_path=str(path),
                pwd=str(Path.cwd()),
                agents=[agent.config.name],
            )
            agent.attach_session_store(
                store,
                capture_activity=_should_capture_session_activity(
                    config, resolved_mode
                ),
            )

        if use_rich_cli:
            asyncio.run(_run_agent_rich_cli(agent))
        else:
            asyncio.run(agent.run())
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        if store:
            store.close()
        if session_file and session_file.exists():
            print("\nSession saved. To resume:")
            print(f"  xinyu-runtime resume {session_file.stem}")


def _resolve_session(query: str | None, last: bool = False) -> Path | None:
    """Resolve a session query to a file path.

    Searches ~/.xinyu/sessions/.
    Accepts: full path, filename, name prefix, or None (list/pick).
    """
    # Full path provided
    if query and Path(query).exists():
        return Path(query)

    # Strip extension from query if present (user may paste from hint)
    if query:
        for ext in (".xinyu", ".kt"):
            if query.endswith(ext):
                query = query[: -len(ext)]
                break

    # Search in default and legacy session directories
    session_dirs = _session_dirs_for_read()
    if not session_dirs:
        return None

    sessions: list[Path] = []
    for session_dir in session_dirs:
        sessions.extend(
            sorted(
                session_dir.glob("*.xinyu"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        )
    # Also check legacy .kt files (pre-.xinyu extension)
    for session_dir in session_dirs:
        sessions.extend(
            sorted(
                session_dir.glob("*.kt"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        )

    if not sessions:
        return None

    # --last: most recent
    if last:
        return sessions[0]

    # No query: list recent and let user pick
    if not query:
        print("Recent sessions:")
        shown = sessions[:10]
        for i, s in enumerate(shown, 1):
            meta = _session_preview(s)
            print(f"  {i}. {s.name}  {meta}")
        print()
        try:
            choice = input(f"Pick [1-{len(shown)}] or name prefix: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(shown):
                return shown[idx]
            return None
        query = choice

    # Prefix match
    matches = [s for s in sessions if s.stem.startswith(query) or query in s.stem]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"Multiple matches for '{query}':")
        for i, s in enumerate(matches[:10], 1):
            meta = _session_preview(s)
            print(f"  {i}. {s.name}  {meta}")
        print()
        try:
            choice = input(f"Pick [1-{len(matches[:10])}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(matches[:10]):
                return matches[idx]
        return None

    # No match in session dir, try as path
    p = Path(query)
    if p.exists():
        return p
    # Try appending extension
    for session_dir in session_dirs:
        for ext in (".xinyu", ".kt"):
            candidate = session_dir / f"{query}{ext}"
            if candidate.exists():
                return candidate

    return None


def _session_preview(path: Path) -> str:
    """Get a short preview of session metadata."""
    try:
        store = SessionStore(path)
        meta = store.load_meta()
        store.close()
        config_type = meta.get("config_type", "?")
        config_path = meta.get("config_path", "")
        name = Path(config_path).name if config_path else "?"
        return f"({config_type}: {name})"
    except Exception as e:
        logger.debug("Failed to read session label", error=str(e))
        return ""


