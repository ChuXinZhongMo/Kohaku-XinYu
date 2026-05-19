"""Low-frequency runtime bridge for Xinyu outward source fetch."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root
from outward_source_engine import run_outward_source

TRACE_REL = "memory/knowledge/outward_source_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class OutwardSourceBridgePlugin(BasePlugin):
    name = "xinyu_outward_source_bridge"
    priority = 109

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
            state_key="outward_source_last_run",
            min_interval_seconds=self._min_interval_seconds,
            recommendation_markers=("- outward_source: yes",),
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

            fetched_at = datetime.now().astimezone().isoformat()
            result = run_outward_source(
                root,
                fetched_at=fetched_at,
                mode="runtime_outward_source",
            )
            self._ctx.set_state("outward_source_last_run", fetched_at)
            _trace(
                root,
                "runtime_outward_source "
                f"permission={result['permission']} "
                f"fetched={result['fetched_sources']} "
                f"staged={result['staged_materials']} "
                f"reason={result['skipped_reason']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
