"""Low-frequency runtime bridge for Xinyu question pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root
from question_pipeline_engine import run_question_pipeline
from turn_mode_utils import read_turn_mode

TRACE_REL = "memory/context/question_pipeline_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class QuestionPipelineBridgePlugin(BasePlugin):
    name = "xinyu_question_pipeline_bridge"
    priority = 98

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 1800))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        root = resolve_root(context)
        _trace(root, "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        return maintenance_should_run(
            self._ctx,
            root,
            state_key="question_pipeline_last_run",
            min_interval_seconds=self._min_interval_seconds,
            dispatch_markers=("- primary: question_pipeline",),
            dispatch_missing_reason="dispatch_not_primary",
        )

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs: Any
    ) -> None:
        if not self._enabled or not self._ctx:
            return
        root = resolve_root(self._ctx)
        try:
            _trace(root, "post_llm_call entered")
            turn_mode = read_turn_mode(root)
            if turn_mode == "live_user_turn":
                _trace(root, "skipped live_user_turn")
                return

            should_run, reason = self._should_run(root)
            _trace(root, f"post_llm_call should_run={should_run} reason={reason}")
            if not should_run:
                return

            checked_at = datetime.now().astimezone().isoformat()
            result = run_question_pipeline(root, checked_at=checked_at, mode="runtime_question_pipeline")
            self._ctx.set_state("question_pipeline_last_run", checked_at)
            _trace(
                root,
                "runtime_question_pipeline "
                f"internal={len(result['internal_ids'])} "
                f"external={len(result['external_ids'])} "
                f"blocked={len(result['blocked_ids'])}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
