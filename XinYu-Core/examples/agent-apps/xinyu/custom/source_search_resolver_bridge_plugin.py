"""Low-frequency runtime bridge for Xinyu source search resolution."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root
from source_search_resolver_engine import run_source_search_resolver

TRACE_REL = "memory/knowledge/source_search_resolver_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class SourceSearchResolverBridgePlugin(BasePlugin):
    name = "xinyu_source_search_resolver_bridge"
    priority = 105

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
            state_key="source_search_resolver_last_run",
            min_interval_seconds=self._min_interval_seconds,
            recommendation_markers=("- source_search_resolver: yes",),
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
            resolved_at = datetime.now().astimezone().isoformat()
            result = run_source_search_resolver(root, resolved_at=resolved_at, mode="runtime_source_search_resolver")
            self._ctx.set_state("source_search_resolver_last_run", resolved_at)
            _trace(root, f"runtime_source_search_resolver pending={result['pending_requests']} resolved={result['resolved_results']}")
        except Exception as exc:
            _trace(root, f"error={exc!r}")
