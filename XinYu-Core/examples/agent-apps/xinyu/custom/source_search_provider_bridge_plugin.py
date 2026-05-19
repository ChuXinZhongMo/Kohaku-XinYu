"""Low-frequency runtime bridge for Xinyu source search provider adapters."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, cooldown_ready, maintenance_preflight, read_text, resolve_root
from source_search_provider_engine import run_source_search_provider
from xinyu_storage_paths import knowledge_file_path

TRACE_REL = "memory/knowledge/source_search_provider_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class SourceSearchProviderBridgePlugin(BasePlugin):
    name = "xinyu_source_search_provider_bridge"
    priority = 107

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
            recommendation_markers=("- source_search_provider: yes",),
            turn_mode_missing_reason="not_maintenance_turn",
        )
        if not should_continue:
            return False, reason
        activation = read_text(knowledge_file_path(root, "autonomous_search_activation_state.md"))
        if "- activation_permission: provider_allowed" not in activation:
            return False, "activation_not_allowed"
        return cooldown_ready(
            self._ctx,
            state_key="source_search_provider_last_run",
            min_interval_seconds=self._min_interval_seconds,
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
            searched_at = datetime.now().astimezone().isoformat()
            result = run_source_search_provider(
                root,
                searched_at=searched_at,
                mode="runtime_source_search_provider",
                require_activation=True,
            )
            self._ctx.set_state("source_search_provider_last_run", searched_at)
            _trace(root, f"runtime_source_search_provider provider={result['provider']} pending={result['pending_requests']} results={result['provider_results']}")
        except Exception as exc:
            _trace(root, f"error={exc!r}")
