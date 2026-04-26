"""Runtime bridge for Xinyu initiative and choice posture."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.plugin.base import BasePlugin, PluginContext

from initiative_loop_engine import run_initiative_loop
from turn_mode_utils import read_turn_mode


def _default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_root(ctx: PluginContext | None) -> Path:
    candidate = Path(ctx.working_dir) if ctx else _default_root()
    if (candidate / "memory").exists():
        return candidate
    return _default_root()


def _trace(root: Path, line: str) -> None:
    trace_path = root / "memory/context/initiative_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


class InitiativeLoopBridgePlugin(BasePlugin):
    name = "xinyu_initiative_loop_bridge"
    priority = 99

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._cooldown_seconds = int(opts.get("cooldown_seconds", 900))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(_resolve_root(context), "on_load ok")

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs: Any
    ) -> None:
        if not self._enabled or not self._ctx:
            return
        root = _resolve_root(self._ctx)
        try:
            turn_mode = read_turn_mode(root)
            if turn_mode not in {"live_user_turn", "maintenance_schedule_turn"}:
                _trace(root, f"skipped turn_mode={turn_mode or 'unknown'}")
                return
            latest_input = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    latest_input = str(msg.get("content", "") or "")
                    break
            checked_at = datetime.now().astimezone().isoformat()
            result = run_initiative_loop(
                root,
                latest_input=latest_input,
                checked_at=checked_at,
                mode="runtime_initiative_loop",
                cooldown_seconds=self._cooldown_seconds,
            )
            _trace(
                root,
                "runtime_initiative_loop "
                f"decision={result['decision']} question={result['selected_question_id']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
