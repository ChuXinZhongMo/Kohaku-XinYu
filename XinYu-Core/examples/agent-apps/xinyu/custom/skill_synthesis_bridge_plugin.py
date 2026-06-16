"""Low-frequency runtime bridge for skill synthesis.

Distils corroborated memory candidates into reusable skill artifacts on the slow
maintenance lane. Deterministic and file-only, so it is also safe to run on the
isolated heavy-maintenance worker.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import (
    append_trace,
    cooldown_ready,
    maintenance_preflight,
    resolve_root,
    run_maintenance_bridge_once,
)

TRACE_REL = "memory/skills/skill_synthesis_trace.log"
STATE_KEY = "skill_synthesis_last_run"


def _ensure_root_on_path(root: Path) -> None:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


class SkillSynthesisBridgePlugin(BasePlugin):
    name = "xinyu_skill_synthesis_bridge"
    priority = 102

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 21600))
        self._min_evidence = int(opts.get("min_evidence", 2))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        root = resolve_root(context)
        _ensure_root_on_path(root)
        append_trace(root, TRACE_REL, "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        # When the isolated heavy-maintenance subprocess is enabled it owns the
        # skill-synthesis lane, so the inline plugin defers to avoid double-running.
        if os.environ.get("XINYU_HEAVY_MAINTENANCE_SUBPROCESS", "").strip().lower() not in {"0", "false", "no", "off"}:
            return False, "delegated_to_heavy_maintenance_subprocess"
        # Otherwise gate on the slow maintenance turn + cooldown only. Synthesis is a
        # cheap, deterministic no-op when there is no corroborated evidence, so it
        # needs no dedicated recommendation marker in the suggestion pipeline.
        should_continue, reason = maintenance_preflight(self._ctx, root)
        if not should_continue:
            return False, reason
        return cooldown_ready(
            self._ctx,
            state_key=STATE_KEY,
            min_interval_seconds=self._min_interval_seconds,
        )

    async def post_llm_call(self, messages: list[dict], response: str, usage: dict, **kwargs: Any) -> None:
        if not self._enabled or not self._ctx:
            return
        root = resolve_root(self._ctx)
        _ensure_root_on_path(root)
        from xinyu_skill_synthesis import run_skill_synthesis

        run_maintenance_bridge_once(
            self._ctx,
            root,
            trace_rel=TRACE_REL,
            should_run=self._should_run,
            state_key=STATE_KEY,
            engine=lambda root_path, **kw: run_skill_synthesis(root_path, min_evidence=self._min_evidence, **kw),
            timestamp_arg="checked_at",
            mode="runtime_skill_synthesis",
            trace_label="runtime_skill_synthesis",
            result_summary=lambda result: (
                f"created={result.get('created', 0)} updated={result.get('updated', 0)} "
                f"clusters={result.get('clusters', 0)}"
            ),
        )
