"""Low-frequency bridge from self-thought research handoff to bounded research gates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import (
    append_trace,
    cooldown_ready,
    maintenance_preflight,
    read_text_optional,
    resolve_root,
)
from research_handoff_engine import run_research_handoff_loop

TRACE_REL = "runtime/research_handoff_bridge_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class ResearchHandoffBridgePlugin(BasePlugin):
    name = "xinyu_research_handoff_bridge"
    priority = 108

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 1800))
        self._execution_level = str(opts.get("execution_level", "activate"))
        self._allow_live_search = bool(opts.get("allow_live_search", False))
        self._allow_codex = bool(opts.get("allow_codex", False))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        should_continue, reason = maintenance_preflight(self._ctx, root)
        if not should_continue:
            return False, reason

        state = read_text_optional(root / "memory/context/self_thought_state.md")
        if "- research_needed: true" not in state:
            return False, "research_not_needed"
        return cooldown_ready(
            self._ctx,
            state_key="research_handoff_last_run",
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
            evaluated_at = datetime.now().astimezone().isoformat()
            result = run_research_handoff_loop(
                root,
                evaluated_at=evaluated_at,
                execution_level=self._execution_level,
                allow_live_search=self._allow_live_search,
                allow_codex=self._allow_codex,
            )
            self._ctx.set_state("research_handoff_last_run", evaluated_at)
            _trace(
                root,
                "runtime_research_handoff "
                f"status={result['status']} route={result['route']} "
                f"activation={result['activation_permission']} provider_results={result['provider_results']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
