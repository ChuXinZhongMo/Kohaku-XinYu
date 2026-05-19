"""Low-frequency runtime bridge for Xinyu long-term memory gate."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from long_term_memory_gate_engine import run_long_term_memory_gate
from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root

TRACE_REL = "memory/archive/long_term_memory_gate_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class LongTermMemoryGateBridgePlugin(BasePlugin):
    name = "xinyu_long_term_memory_gate_bridge"
    priority = 103

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 9300))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        return maintenance_should_run(
            self._ctx,
            root,
            state_key="long_term_memory_gate_last_run",
            min_interval_seconds=self._min_interval_seconds,
            recommendation_markers=("- long_term_memory_gate: yes",),
        )

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs: Any
    ) -> None:
        if not self._enabled or not self._ctx:
            return
        root = resolve_root(self._ctx)
        try:
            _trace(root, "post_llm_call entered")
            should_run, reason = self._should_run(root)
            _trace(root, f"post_llm_call should_run={should_run} reason={reason}")
            if not should_run:
                return

            checked_at = datetime.now().astimezone().isoformat()
            result = run_long_term_memory_gate(
                root,
                checked_at=checked_at,
                mode="runtime_long_term_memory_gate",
            )
            self._ctx.set_state("long_term_memory_gate_last_run", checked_at)
            _trace(
                root,
                "runtime_long_term_memory_gate "
                f"action={result['memory_action']} "
                f"forget={result['forget_permission']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
