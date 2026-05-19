"""Low-frequency runtime bridge for AI-domain self-iteration candidates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from ai_self_iteration_gate_engine import run_ai_self_iteration_gate
from maintenance_bridge_utils import (
    append_trace,
    cooldown_ready,
    maintenance_preflight,
    read_text_optional,
    resolve_root,
)
from xinyu_storage_paths import knowledge_file_path

TRACE_REL = "memory/self/ai_self_iteration_gate_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class AiSelfIterationGateBridgePlugin(BasePlugin):
    name = "xinyu_ai_self_iteration_gate_bridge"
    priority = 106

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 10800))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        should_continue, reason = maintenance_preflight(
            self._ctx,
            root,
            recommendation_markers=("- ai_self_iteration_gate: yes",),
        )
        if not should_continue:
            return False, reason

        general = read_text_optional(knowledge_file_path(root, "general.md"))
        if "- question_id: q-006" not in general:
            return False, "no_q006_knowledge"

        learning_quality = read_text_optional(knowledge_file_path(root, "learning_quality_state.md"))
        if "- quality_grade: stable" not in learning_quality:
            return False, "learning_quality_not_stable"

        return cooldown_ready(
            self._ctx,
            state_key="ai_self_iteration_gate_last_run",
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
            result = run_ai_self_iteration_gate(
                root,
                evaluated_at=evaluated_at,
                mode="runtime_ai_self_iteration_gate",
            )
            self._ctx.set_state("ai_self_iteration_gate_last_run", evaluated_at)
            _trace(
                root,
                "runtime_ai_self_iteration_gate "
                f"status={result['gate_status']} "
                f"confidence={result['confidence_score']} "
                f"sources={result['source_material_count']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
