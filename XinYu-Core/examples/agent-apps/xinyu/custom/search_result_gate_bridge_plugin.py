"""Low-frequency runtime bridge for Xinyu search result gate."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root
from search_result_gate_engine import run_search_result_gate

TRACE_REL = "memory/knowledge/search_result_gate_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class SearchResultGateBridgePlugin(BasePlugin):
    name = "xinyu_search_result_gate_bridge"
    priority = 108

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
            state_key="search_result_gate_last_run",
            min_interval_seconds=self._min_interval_seconds,
            recommendation_markers=("- search_result_gate: yes",),
            turn_mode_missing_reason="not_maintenance_turn",
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
            gated_at = datetime.now().astimezone().isoformat()
            result = run_search_result_gate(root, gated_at=gated_at, mode="runtime_search_result_gate")
            self._ctx.set_state("search_result_gate_last_run", gated_at)
            _trace(root, f"runtime_search_result_gate candidates={result['candidate_results']} accepted={result['accepted_results']} updated={result['updated_requests']}")
        except Exception as exc:
            _trace(root, f"error={exc!r}")
