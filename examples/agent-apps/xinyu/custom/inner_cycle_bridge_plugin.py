"""Runtime summarizer for Xinyu inner cycle state."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.plugin.base import BasePlugin, PluginContext

from inner_cycle_engine import run_inner_cycle_summary
from turn_mode_utils import read_turn_mode


def _default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_root(ctx: PluginContext | None) -> Path:
    candidate = Path(ctx.working_dir) if ctx else _default_root()
    if (candidate / "memory").exists():
        return candidate
    return _default_root()


def _trace(root: Path, line: str) -> None:
    trace_path = root / "memory/context/inner_cycle_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


class InnerCycleBridgePlugin(BasePlugin):
    name = "xinyu_inner_cycle_bridge"
    priority = 113

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))

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
            _trace(root, "post_llm_call entered")
            checked_at = datetime.now().astimezone().isoformat()
            result = run_inner_cycle_summary(
                root,
                checked_at=checked_at,
                mode="runtime_inner_cycle_summary",
            )
            _trace(
                root,
                "runtime_inner_cycle_summary "
                f"internal={result['internal_clarification']} "
                f"external={result['exploration_candidates']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
