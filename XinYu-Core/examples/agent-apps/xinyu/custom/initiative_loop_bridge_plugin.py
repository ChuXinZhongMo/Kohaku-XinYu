"""Runtime bridge for Xinyu initiative and choice posture."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from initiative_loop_engine import run_initiative_loop
from maintenance_bridge_utils import append_trace, resolve_root
from turn_mode_utils import read_turn_mode

TRACE_REL = "memory/context/initiative_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


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
        _trace(resolve_root(context), "on_load ok")

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs: Any
    ) -> None:
        if not self._enabled or not self._ctx:
            return
        root = resolve_root(self._ctx)
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
