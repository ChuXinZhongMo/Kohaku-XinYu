"""Low-frequency runtime bridge for Xinyu retention gate."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from maintenance_bridge_utils import append_trace, maintenance_should_run, resolve_root
from retention_gate_engine import run_retention_gate
from turn_mode_utils import read_turn_mode

TRACE_REL = "memory/archive/retention_gate_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class RetentionGateBridgePlugin(BasePlugin):
    name = "xinyu_retention_gate_bridge"
    priority = 104

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 9300))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        return maintenance_should_run(
            self._ctx,
            root,
            state_key="retention_gate_last_run",
            min_interval_seconds=self._min_interval_seconds,
            recommendation_markers=("- retention_gate: yes",),
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
            user_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = str(msg.get("content", "") or "")
                    break
            if turn_mode == "live_user_turn" and not user_message.strip():
                _trace(root, "skipped no_user_message")
                return

            should_run, reason = self._should_run(root)
            _trace(root, f"post_llm_call should_run={should_run} reason={reason}")
            if not should_run:
                return

            checked_at = datetime.now().astimezone().isoformat()
            result = run_retention_gate(
                root,
                checked_at=checked_at,
                mode="runtime_retention_gate",
            )
            self._ctx.set_state("retention_gate_last_run", checked_at)
            _trace(
                root,
                "runtime_retention_gate "
                f"tier={result['retention_tier']} "
                f"permission={result['archive_permission']} "
                f"reason={result['gate_reason']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
