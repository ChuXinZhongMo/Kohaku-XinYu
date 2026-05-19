"""Low-frequency runtime bridge for Xinyu personality growth gate."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root
from personality_growth_gate_engine import run_personality_growth_gate

TRACE_REL = "memory/self/personality_growth_gate_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class PersonalityGrowthGateBridgePlugin(BasePlugin):
    name = "xinyu_personality_growth_gate_bridge"
    priority = 107

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 10800))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        return maintenance_should_run(
            self._ctx,
            root,
            state_key="personality_growth_gate_last_run",
            min_interval_seconds=self._min_interval_seconds,
            recommendation_markers=("- personality_growth_gate: yes",),
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

            checked_at = datetime.now().astimezone().isoformat()
            result = run_personality_growth_gate(
                root,
                checked_at=checked_at,
                mode="runtime_personality_growth_gate",
            )
            self._ctx.set_state("personality_growth_gate_last_run", checked_at)
            _trace(
                root,
                "runtime_personality_growth_gate "
                f"decision={result['gate_decision']} "
                f"pressure={result['change_pressure']} "
                f"self_review={result.get('self_review_decision', 'unknown')} "
                f"self_review_action={result.get('self_review_action', 'unknown')} "
                f"self_review_autonomy={result.get('self_review_autonomy_level', 'unknown')} "
                f"profile_changed={result.get('self_review_profile_changed', False)}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
