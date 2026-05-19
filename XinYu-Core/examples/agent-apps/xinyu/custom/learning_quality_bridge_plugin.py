"""Low-frequency runtime bridge for Xinyu learning quality checks."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from learning_quality_engine import run_learning_quality
from maintenance_bridge_utils import append_trace, cooldown_ready, maintenance_preflight, read_text, resolve_root
from xinyu_storage_paths import knowledge_file_path

TRACE_REL = "memory/knowledge/learning_quality_trace.log"


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class LearningQualityBridgePlugin(BasePlugin):
    name = "xinyu_learning_quality_bridge"
    priority = 112

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 9000))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        should_continue, reason = maintenance_preflight(
            self._ctx,
            root,
            recommendation_markers=("- learning_quality: yes",),
        )
        if not should_continue:
            return False, reason
        general = read_text(_knowledge(root, "general.md"))
        materials = read_text(_knowledge(root, "source_materials.md"))
        if "## learned-" not in general and "## material-" not in materials:
            return False, "no_learning_inputs"
        return cooldown_ready(
            self._ctx,
            state_key="learning_quality_last_run",
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

            evaluated_at = datetime.now().astimezone().isoformat()
            result = run_learning_quality(
                root,
                evaluated_at=evaluated_at,
                mode="runtime_learning_quality",
            )
            self._ctx.set_state("learning_quality_last_run", evaluated_at)
            _trace(
                root,
                "runtime_learning_quality "
                f"grade={result['quality_grade']} "
                f"learned={result['learned_entries']} "
                f"warnings={result['warning_count']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
