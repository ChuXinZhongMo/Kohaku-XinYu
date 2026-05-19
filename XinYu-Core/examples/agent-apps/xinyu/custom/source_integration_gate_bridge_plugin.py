"""Low-frequency runtime bridge for Xinyu source integration gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root, run_maintenance_bridge_once
from source_integration_gate_engine import run_source_integration_gate

TRACE_REL = "memory/knowledge/source_integration_gate_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class SourceIntegrationGateBridgePlugin(BasePlugin):
    name = "xinyu_source_integration_gate_bridge"
    priority = 103

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 8100))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        return maintenance_should_run(
            self._ctx,
            root,
            state_key="source_integration_gate_last_run",
            min_interval_seconds=self._min_interval_seconds,
            recommendation_markers=("- source_reliability: yes", "- source_integration_gate: yes"),
            dispatch_markers=(
                "- deferred: source_gate_then_source_reliability",
                "- deferred: source_integration_gate",
            ),
            dispatch_missing_reason="dispatch_not_source_chain",
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
            state_key="source_integration_gate_last_run",
            engine=run_source_integration_gate,
            timestamp_arg="checked_at",
            mode="runtime_source_integration_gate",
            trace_label="runtime_source_integration_gate",
            result_summary=lambda result: (
                f"permission={result['integration_permission']} "
                f"ready={result['ready_candidates']}"
            ),
        )
