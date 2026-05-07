"""Low-frequency bridge from self-thought research handoff to bounded research gates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from research_handoff_engine import run_research_handoff_loop
from turn_mode_utils import read_turn_mode


def _default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_root(ctx: PluginContext | None) -> Path:
    candidate = Path(ctx.working_dir) if ctx else _default_root()
    if (candidate / "memory").exists():
        return candidate
    return _default_root()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _trace(root: Path, line: str) -> None:
    trace_path = root / "runtime/research_handoff_bridge_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


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
        _trace(_resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        if not self._ctx:
            return False, "no_context"
        turn_mode = read_turn_mode(root)
        if turn_mode != "maintenance_schedule_turn":
            return False, f"turn_mode:{turn_mode or 'unknown'}"
        state = _read(root / "memory/context/self_thought_state.md")
        if "- research_needed: true" not in state:
            return False, "research_not_needed"
        last_run = self._ctx.get_state("research_handoff_last_run")
        if last_run:
            try:
                last_dt = datetime.fromisoformat(str(last_run))
                delta = (datetime.now().astimezone() - last_dt).total_seconds()
                if delta < self._min_interval_seconds:
                    return False, f"cooldown:{int(delta)}"
            except Exception:
                pass
        return True, "ready"

    async def post_llm_call(self, messages: list[dict], response: str, usage: dict, **kwargs: Any) -> None:
        if not self._enabled or not self._ctx:
            return
        root = _resolve_root(self._ctx)
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
