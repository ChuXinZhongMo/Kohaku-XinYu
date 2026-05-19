"""Low-frequency runtime bridge for Xinyu source comparison."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, cooldown_ready, maintenance_preflight, read_text, resolve_root
from source_comparison_engine import run_source_comparison
from xinyu_storage_paths import knowledge_file_path

TRACE_REL = "memory/knowledge/source_comparison_trace.log"


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class SourceComparisonBridgePlugin(BasePlugin):
    name = "xinyu_source_comparison_bridge"
    priority = 110

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 8400))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        should_continue, reason = maintenance_preflight(
            self._ctx,
            root,
            recommendation_markers=("- source_comparison: yes",),
        )
        if not should_continue:
            return False, reason
        source_materials = read_text(_knowledge(root, "source_materials.md"))
        if "- status: ready" not in source_materials:
            return False, "no_ready_material"
        return cooldown_ready(
            self._ctx,
            state_key="source_comparison_last_run",
            min_interval_seconds=self._min_interval_seconds,
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

            compared_at = datetime.now().astimezone().isoformat()
            result = run_source_comparison(
                root,
                compared_at=compared_at,
                mode="runtime_source_comparison",
            )
            self._ctx.set_state("source_comparison_last_run", compared_at)
            _trace(
                root,
                "runtime_source_comparison "
                f"ready={result['ready_materials']} "
                f"groups={result['compared_groups']} "
                f"corroborated={result['corroborated_materials']} "
                f"conflict={result['conflict_materials']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
