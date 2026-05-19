"""Low-frequency runtime bridge for Xinyu dream output."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from dream_output_engine import has_unconsumed_dream_seed, run_dream_output
from maintenance_bridge_utils import (
    append_trace,
    cooldown_ready,
    maintenance_preflight,
    read_text_optional,
    resolve_root,
)
from turn_mode_utils import read_turn_mode

TRACE_REL = "memory/dreams/dream_output_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


class DreamOutputBridgePlugin(BasePlugin):
    name = "xinyu_dream_output_bridge"
    priority = 101

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 7200))
        self._export_enabled = bool(opts.get("export_enabled", True))
        self._export_on_load = bool(opts.get("export_on_load", True))
        self._output_dir_override = str(opts.get("output_dir", "")).strip()

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        root = resolve_root(context)
        _trace(root, "on_load ok")
        if self._export_enabled and self._export_on_load:
            self._export_dreams(root, reason="on_load")

    def _export_dreams(self, root: Path, *, reason: str) -> dict[str, object] | None:
        if not self._export_enabled:
            return None
        try:
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from xinyu_dream_journal import export_dream_journal

            output_dir = Path(self._output_dir_override).expanduser() if self._output_dir_override else None
            result = export_dream_journal(root, output_dir=output_dir)
            _trace(
                root,
                f"export_dreams reason={reason} count={result['dream_count']} "
                f"latest={result['latest_path']}",
            )
            return result
        except Exception as exc:
            _trace(root, f"export_error reason={reason} error={exc!r}")
            return None

    def _should_run(self, root: Path) -> tuple[bool, str]:
        should_continue, reason = maintenance_preflight(
            self._ctx,
            root,
            recommendation_markers=("- dream_output: yes",),
        )
        if not should_continue:
            return False, reason

        dream_seeds = read_text_optional(root / "memory/dreams/dream_seeds.md")
        if not has_unconsumed_dream_seed(dream_seeds):
            return False, "no_unconsumed_dream_seed"

        return cooldown_ready(
            self._ctx,
            state_key="dream_output_last_run",
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
            if read_turn_mode(root) == "maintenance_schedule_turn":
                self._export_dreams(root, reason="maintenance_turn")
            should_run, reason = self._should_run(root)
            _trace(root, f"post_llm_call should_run={should_run} reason={reason}")
            if not should_run:
                return

            produced_at = datetime.now().astimezone().isoformat()
            result = run_dream_output(
                root,
                produced_at=produced_at,
                mode="runtime_dream_output",
            )
            self._ctx.set_state("dream_output_last_run", produced_at)
            self._export_dreams(root, reason="runtime_dream_output")
            _trace(
                root,
                "runtime_dream_output "
                f"seed_id={result['seed_id']} "
                f"theme={result['theme']} "
                f"wrote_log={result['wrote_log']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
