"""Low-frequency runtime bridge for public GitHub learning discovery."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from github_autonomous_learning_engine import run_github_autonomous_learning
from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root

TRACE_REL = "memory/context/github_learning_bridge_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class GitHubAutonomousLearningBridgePlugin(BasePlugin):
    name = "xinyu_github_autonomous_learning_bridge"
    priority = 109

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 21600))
        self._max_stage = int(opts.get("max_stage", 1))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        return maintenance_should_run(
            self._ctx,
            root,
            state_key="github_autonomous_learning_last_run",
            min_interval_seconds=self._min_interval_seconds,
        )

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs: Any
    ) -> None:
        if not self._enabled or not self._ctx:
            return
        root = resolve_root(self._ctx)
        try:
            should_run, reason = self._should_run(root)
            _trace(root, f"post_llm_call should_run={should_run} reason={reason}")
            if not should_run:
                return
            checked_at = datetime.now().astimezone().isoformat()
            result = run_github_autonomous_learning(
                root,
                checked_at=checked_at,
                mode="runtime_github_autonomous_learning_bridge",
                max_stage=self._max_stage,
                min_interval_seconds=self._min_interval_seconds,
            )
            self._ctx.set_state("github_autonomous_learning_last_run", checked_at)
            _trace(
                root,
                "runtime_github_autonomous_learning "
                f"status={result['status']} "
                f"candidates={result['candidates_found']} "
                f"staged={result['staged_repos']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
