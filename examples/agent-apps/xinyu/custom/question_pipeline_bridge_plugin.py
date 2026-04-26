"""Low-frequency runtime bridge for Xinyu question pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.plugin.base import BasePlugin, PluginContext

from question_pipeline_engine import run_question_pipeline
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
    trace_path = root / "memory/context/question_pipeline_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


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
        root = _resolve_root(context)
        _trace(root, "on_load ok")

    def _should_run(self, root: Path) -> tuple[bool, str]:
        if not self._ctx:
            return False, "no_context"
        turn_mode = read_turn_mode(root)
        if turn_mode != "maintenance_schedule_turn":
            return False, f"turn_mode:{turn_mode or 'unknown'}"
        dispatch = _read(root / "memory/context/maintenance_dispatch_state.md")
        if "- primary: question_pipeline" not in dispatch:
            return False, "dispatch_not_primary"

        last_run = self._ctx.get_state("question_pipeline_last_run")
        if last_run:
            try:
                last_dt = datetime.fromisoformat(str(last_run))
                delta = (datetime.now().astimezone() - last_dt).total_seconds()
                if delta < self._min_interval_seconds:
                    return False, f"cooldown:{int(delta)}"
            except Exception:
                pass
        return True, "ready"

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs: Any
    ) -> None:
        if not self._enabled or not self._ctx:
            return
        root = _resolve_root(self._ctx)
        try:
            _trace(root, "post_llm_call entered")
            turn_mode = read_turn_mode(root)
            user_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = str(msg.get("content", "") or "")
                    break
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
