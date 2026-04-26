"""Runtime bridge for owner-visible AI self-iteration review proposals."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.plugin.base import BasePlugin, PluginContext

from ai_self_iteration_review_engine import (
    extract_value,
    owner_review_granted,
    run_ai_self_iteration_review,
)
from turn_mode_utils import read_turn_mode


def _default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_root(ctx: PluginContext | None) -> Path:
    candidate = Path(ctx.working_dir) if ctx else _default_root()
    if (candidate / "memory").exists():
        return candidate
    return _default_root()


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _trace(root: Path, line: str) -> None:
    trace_path = root / "memory/self/ai_self_iteration_review_trace.log"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat()
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {line}\n")


class AiSelfIterationReviewBridgePlugin(BasePlugin):
    name = "xinyu_ai_self_iteration_review_bridge"
    priority = 107

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._min_interval_seconds = int(opts.get("min_interval_seconds", 10800))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(_resolve_root(context), "on_load ok")

    def _cooldown_ready(self) -> tuple[bool, str]:
        if not self._ctx:
            return False, "no_context"
        last_run = self._ctx.get_state("ai_self_iteration_review_last_run")
        if not last_run:
            return True, "never_run"
        try:
            last_dt = datetime.fromisoformat(str(last_run))
            delta = (datetime.now().astimezone() - last_dt).total_seconds()
            if delta < self._min_interval_seconds:
                return False, f"cooldown:{int(delta)}"
        except Exception:
            return True, "bad_last_run"
        return True, "cooldown_ready"

    def _should_run(self, root: Path) -> tuple[bool, str]:
        turn_mode = read_turn_mode(root)
        if turn_mode != "maintenance_schedule_turn":
            return False, f"turn_mode:{turn_mode or 'unknown'}"

        gate = _read(root / "memory/self/ai_self_iteration_state.md")
        gate_status = extract_value(gate, "gate_status")
        if gate_status != "growth_review_candidate":
            return False, f"gate_status:{gate_status}"

        review = _read(root / "memory/self/ai_self_iteration_review_state.md")
        review_permission = extract_value(review, "review_permission")
        if owner_review_granted(root) and review_permission != "owner_approved_for_non_stable_planning":
            return True, "owner_grant_refresh"
        if extract_value(review, "input_gate_status") != gate_status:
            return True, "review_missing_or_stale"

        return self._cooldown_ready()

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs: Any
    ) -> None:
        if not self._enabled or not self._ctx:
            return
        root = _resolve_root(self._ctx)
        try:
            _trace(root, "post_llm_call entered")
            should_run, reason = self._should_run(root)
            _trace(root, f"post_llm_call should_run={should_run} reason={reason}")
            if not should_run:
                return

            reviewed_at = datetime.now().astimezone().isoformat()
            result = run_ai_self_iteration_review(
                root,
                reviewed_at=reviewed_at,
                mode="runtime_ai_self_iteration_review",
            )
            self._ctx.set_state("ai_self_iteration_review_last_run", reviewed_at)
            _trace(
                root,
                "runtime_ai_self_iteration_review "
                f"permission={result['review_permission']} "
                f"proposals={result['proposal_count']} "
                f"stable_profile={result['stable_profile_write_permission']}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
