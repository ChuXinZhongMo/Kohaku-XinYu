"""Low-frequency bridge that writes owner-visible desktop thought files."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.plugin.base import BasePlugin, PluginContext

from turn_mode_utils import read_turn_mode


def _default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_root(ctx: PluginContext | None) -> Path:
    candidate = Path(ctx.working_dir) if ctx else _default_root()
    if (candidate / "memory").exists():
        return candidate
    return _default_root()


def _trace(root: Path, line: str) -> None:
    trace_path = root / "memory/context/desktop_thoughts_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


def _newest_thought_file(output_dir: Path) -> Path | None:
    if not output_dir.exists():
        return None
    newest: Path | None = None
    newest_mtime = -1.0
    for path in output_dir.glob("*/*-xinyu-thoughts.md"):
        if not path.is_file():
            continue
        mtime = path.stat().st_mtime
        if mtime > newest_mtime:
            newest = path
            newest_mtime = mtime
    return newest


def _seconds_since(path: Path | None) -> float | None:
    if path is None:
        return None
    return datetime.now().timestamp() - path.stat().st_mtime


class DesktopThoughtsBridgePlugin(BasePlugin):
    name = "xinyu_desktop_thoughts_bridge"
    priority = 109

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 3600))
        self._startup_min_interval_seconds = int(opts.get("startup_min_interval_seconds", 7200))
        self._write_on_startup = bool(opts.get("write_on_startup_if_stale", True))
        self._output_dir_override = str(opts.get("output_dir", "")).strip()

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(_resolve_root(context), "on_load ok")

    def _load_renderer(self, root: Path) -> tuple[Any, Any]:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from xinyu_autonomy_journal import default_output_dir, render_persona_thoughts

        return default_output_dir, render_persona_thoughts

    def _output_dir(self, root: Path) -> Path:
        default_output_dir, _render_persona_thoughts = self._load_renderer(root)
        if self._output_dir_override:
            return Path(self._output_dir_override).expanduser()
        return default_output_dir()

    def _current_llm(self) -> Any | None:
        if self._ctx is None or self._ctx.host_agent is None:
            return None
        return getattr(self._ctx.host_agent, "llm", None)

    def _cooldown_ready(self, root: Path, *, startup: bool) -> tuple[bool, str]:
        output_dir = self._output_dir(root)
        newest = _newest_thought_file(output_dir)
        elapsed = _seconds_since(newest)
        interval = self._startup_min_interval_seconds if startup else self._min_interval_seconds
        if elapsed is not None and elapsed < interval:
            return False, f"file_cooldown:{int(elapsed)}"

        if not self._ctx:
            return True, "no_context_file_ready"
        last_run = self._ctx.get_state("desktop_thoughts_last_run")
        if not last_run:
            return True, "never_run"
        try:
            last_dt = datetime.fromisoformat(str(last_run))
            delta = (datetime.now().astimezone() - last_dt).total_seconds()
            if delta < interval:
                return False, f"state_cooldown:{int(delta)}"
        except Exception:
            return True, "bad_last_run"
        return True, "cooldown_ready"

    async def _write_thoughts(self, root: Path, *, reason: str) -> Path | None:
        default_output_dir, render_persona_thoughts = self._load_renderer(root)
        output_dir = Path(self._output_dir_override).expanduser() if self._output_dir_override else default_output_dir()
        generated = datetime.now().astimezone()
        llm = self._current_llm()
        text = (
            await render_persona_thoughts(
                root,
                generated.isoformat(),
                llm=llm,
                use_llm=llm is not None,
            )
        ).rstrip()
        if not text.strip():
            _trace(root, f"skipped empty_or_flagged reason={reason}")
            return None
        date_dir = output_dir / generated.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        path = date_dir / f"{generated.strftime('%H-%M-%S')}-xinyu-thoughts.md"
        path.write_text(text + "\n", encoding="utf-8-sig")
        if self._ctx:
            self._ctx.set_state("desktop_thoughts_last_run", generated.isoformat())
        _trace(root, f"wrote {path} reason={reason}")
        return path

    async def on_agent_start(self) -> None:
        if not self._enabled or not self._ctx or not self._write_on_startup:
            return
        root = _resolve_root(self._ctx)
        try:
            ready, reason = self._cooldown_ready(root, startup=True)
            _trace(root, f"on_agent_start ready={ready} reason={reason}")
            if ready:
                await self._write_thoughts(root, reason=f"startup_stale:{reason}")
        except Exception as exc:
            _trace(root, f"on_agent_start error={exc!r}")

    async def post_llm_call(self, messages: list[dict], response: str, usage: dict, **kwargs: Any) -> None:
        if not self._enabled or not self._ctx:
            return
        root = _resolve_root(self._ctx)
        try:
            turn_mode = read_turn_mode(root)
            if turn_mode != "maintenance_schedule_turn":
                _trace(root, f"post_llm_call skipped turn_mode={turn_mode or 'unknown'}")
                return
            ready, reason = self._cooldown_ready(root, startup=False)
            _trace(root, f"post_llm_call ready={ready} reason={reason}")
            if ready:
                await self._write_thoughts(root, reason=f"maintenance:{reason}")
        except Exception as exc:
            _trace(root, f"post_llm_call error={exc!r}")
