"""Low-frequency runtime bridge for Xinyu learner integration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from learner_integration_engine import run_learner_integration
from maintenance_bridge_utils import append_trace, cooldown_ready, maintenance_preflight, read_text, resolve_root
from xinyu_storage_paths import knowledge_file_path

TRACE_REL = "memory/knowledge/learner_integration_trace.log"


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class LearnerIntegrationBridgePlugin(BasePlugin):
    name = "xinyu_learner_integration_bridge"
    priority = 111

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
            recommendation_markers=("- learner_integration: yes",),
        )
        if not should_continue:
            return False, reason
        source_materials = read_text(_knowledge(root, "source_materials.md"))
        if "- status: ready" not in source_materials:
            return False, "no_ready_material"
        return cooldown_ready(
            self._ctx,
            state_key="learner_integration_last_run",
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

            integrated_at = datetime.now().astimezone().isoformat()
            result = run_learner_integration(
                root,
                integrated_at=integrated_at,
                mode="runtime_learner_integration",
            )
            self._ctx.set_state("learner_integration_last_run", integrated_at)
            _trace(
                root,
                "runtime_learner_integration "
                f"permission={result['permission']} "
                f"ready={result['ready_materials']} "
                f"integrated={result['integrated_materials']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
