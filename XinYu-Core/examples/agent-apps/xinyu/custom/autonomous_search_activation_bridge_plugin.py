"""Low-frequency gate for conservative autonomous source search activation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from autonomous_search_activation_engine import run_autonomous_search_activation
from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root

TRACE_REL = "memory/knowledge/autonomous_search_activation_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class AutonomousSearchActivationBridgePlugin(BasePlugin):
    name = "xinyu_autonomous_search_activation_bridge"
    priority = 106

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 8400))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        return maintenance_should_run(
            self._ctx,
            root,
            state_key="autonomous_search_activation_last_run",
            min_interval_seconds=self._min_interval_seconds,
            recommendation_markers=("- autonomous_search_activation: yes",),
        )

    async def post_llm_call(self, messages: list[dict], response: str, usage: dict, **kwargs: Any) -> None:
        if not self._enabled or not self._ctx:
            return
        root = resolve_root(self._ctx)
        try:
            should_run, reason = self._should_run(root)
            _trace(root, f"post_llm_call should_run={should_run} reason={reason}")
            if not should_run:
                return
            evaluated_at = datetime.now().astimezone().isoformat()
            result = run_autonomous_search_activation(
                root,
                evaluated_at=evaluated_at,
                mode="runtime_autonomous_search_activation",
            )
            self._ctx.set_state("autonomous_search_activation_last_run", evaluated_at)
            _trace(
                root,
                "runtime_autonomous_search_activation "
                f"permission={result['activation_permission']} "
                f"reason={result['activation_reason']} "
                f"allowed={result['allowed_queries']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
