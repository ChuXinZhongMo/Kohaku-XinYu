"""Low-frequency runtime bridge for Xinyu source request planning."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root
from source_request_planner_engine import run_source_request_planner

TRACE_REL = "memory/knowledge/source_request_planner_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class SourceRequestPlannerBridgePlugin(BasePlugin):
    name = "xinyu_source_request_planner_bridge"
    priority = 104

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
            state_key="source_request_planner_last_run",
            min_interval_seconds=self._min_interval_seconds,
            recommendation_markers=("- source_request_planner: yes",),
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

            planned_at = datetime.now().astimezone().isoformat()
            result = run_source_request_planner(
                root,
                planned_at=planned_at,
                mode="runtime_source_request_planner",
            )
            self._ctx.set_state("source_request_planner_last_run", planned_at)
            _trace(
                root,
                "runtime_source_request_planner "
                f"permission={result['permission']} "
                f"candidates={result['source_candidates']} "
                f"planned={result['planned_requests']} "
                f"ready={result['ready_requests']} "
                f"pending_url={result['pending_url_requests']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
