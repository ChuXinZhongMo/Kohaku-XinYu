"""Low-frequency runtime bridge for Xinyu source search resolution."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from source_search_resolver_engine import run_source_search_resolver
from turn_mode_utils import read_turn_mode


def _default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_root(ctx: PluginContext | None) -> Path:
    candidate = Path(ctx.working_dir) if ctx else _default_root()
    if (candidate / "memory").exists():
        return candidate
    return _default_root()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _trace(root: Path, line: str) -> None:
    trace_path = root / "memory/knowledge/source_search_resolver_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


class SourceSearchResolverBridgePlugin(BasePlugin):
    name = "xinyu_source_search_resolver_bridge"
    priority = 105

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 8400))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(_resolve_root(context), "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        if not self._ctx:
            return False, "no_context"
        if read_turn_mode(root) != "maintenance_schedule_turn":
            return False, "not_maintenance_turn"
        recommendations = _read(root / "memory/context/maintenance_recommendations.md")
        if "- source_search_resolver: yes" not in recommendations:
            return False, "recommendation_not_yes"
        last_run = self._ctx.get_state("source_search_resolver_last_run")
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
            resolved_at = datetime.now().astimezone().isoformat()
            result = run_source_search_resolver(root, resolved_at=resolved_at, mode="runtime_source_search_resolver")
            self._ctx.set_state("source_search_resolver_last_run", resolved_at)
            _trace(root, f"runtime_source_search_resolver pending={result['pending_requests']} resolved={result['resolved_results']}")
        except Exception as exc:
            _trace(root, f"error={exc!r}")
