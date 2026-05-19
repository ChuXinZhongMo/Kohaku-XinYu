"""Low-frequency runtime bridge for Xinyu source reliability preparation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root, run_maintenance_bridge_once
from source_reliability_engine import run_source_reliability

TRACE_REL = "memory/knowledge/source_reliability_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class SourceReliabilityBridgePlugin(BasePlugin):
    name = "xinyu_source_reliability_bridge"
    priority = 102

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 7800))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        return maintenance_should_run(
            self._ctx,
            root,
            state_key="source_reliability_last_run",
            min_interval_seconds=self._min_interval_seconds,
            recommendation_markers=("- source_gate: yes",),
            dispatch_markers=("- deferred: source_gate",),
            dispatch_missing_reason="dispatch_not_source_gate",
        )

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs: Any
    ) -> None:
        if not self._enabled or not self._ctx:
            return
        root = resolve_root(self._ctx)
        run_maintenance_bridge_once(
            self._ctx,
            root,
            trace_rel=TRACE_REL,
            should_run=self._should_run,
            state_key="source_reliability_last_run",
            engine=run_source_reliability,
            timestamp_arg="checked_at",
            mode="runtime_source_reliability",
            trace_label="runtime_source_reliability",
            result_summary=lambda result: f"candidate_count={result['candidate_count']}",
        )
