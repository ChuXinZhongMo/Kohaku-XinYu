"""Low-frequency bridge that writes owner-visible desktop thought files."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, resolve_root
from turn_mode_utils import read_turn_mode

TRACE_REL = "memory/context/desktop_thoughts_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


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
        _trace(resolve_root(context), "on_load ok")

    def _load_renderer(self, root: Path) -> tuple[Any, Any, Any, Any]:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from xinyu_private_thought_events import mark_private_thought_desktop_written, refresh_private_thought_event
        from xinyu_autonomy_journal import default_output_dir, render_persona_thoughts

        return default_output_dir, render_persona_thoughts, refresh_private_thought_event, mark_private_thought_desktop_written

    def _output_dir(self, root: Path) -> Path:
        default_output_dir, _render_persona_thoughts, _refresh_private_thought_event, _mark_written = self._load_renderer(root)
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

    async def _write_thoughts(self, root: Path, *, reason: str, source_response: str = "") -> Path | None:
        default_output_dir, render_persona_thoughts, refresh_private_thought_event, mark_private_thought_desktop_written = self._load_renderer(root)
        output_dir = Path(self._output_dir_override).expanduser() if self._output_dir_override else default_output_dir()
        generated = datetime.now().astimezone()
        llm = self._current_llm()
        if llm is None:
            _trace(root, f"skipped no_llm reason={reason}")
            return None
        source_kind = "agent_maintenance_private_thought" if reason.startswith("maintenance:") else "startup_private_thought_bridge"
        event = await refresh_private_thought_event(
            root,
            generated_at=generated.isoformat(),
            llm=llm,
            source_kind=source_kind,
            trigger=reason,
            source_response=source_response,
        )
        text = (
            await render_persona_thoughts(
                root,
                generated.isoformat(),
                llm=llm,
                use_llm=True,
                private_thought_event=event,
                ensure_private_thought_event=False,
                source_kind="owner_visible_private_note_renderer",
                trigger=reason,
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
        mark_private_thought_desktop_written(
            root,
            event_id=event.event_id,
            note_path=path,
            generated_at=generated.isoformat(),
        )
        _trace(root, f"wrote {path} reason={reason}")
        return path

    async def on_agent_start(self) -> None:
        if not self._enabled or not self._ctx or not self._write_on_startup:
            return
        root = resolve_root(self._ctx)
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
        root = resolve_root(self._ctx)
        try:
            turn_mode = read_turn_mode(root)
            if turn_mode != "maintenance_schedule_turn":
                _trace(root, f"post_llm_call skipped turn_mode={turn_mode or 'unknown'}")
                return
            ready, reason = self._cooldown_ready(root, startup=False)
            _trace(root, f"post_llm_call ready={ready} reason={reason}")
            if ready:
                await self._write_thoughts(root, reason=f"maintenance:{reason}", source_response=str(response or ""))
        except Exception as exc:
            _trace(root, f"post_llm_call error={exc!r}")
