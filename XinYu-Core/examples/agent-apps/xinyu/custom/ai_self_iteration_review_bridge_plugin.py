"""Runtime bridge for owner-visible AI self-iteration review proposals."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext

from ai_self_iteration_review_engine import (
    extract_value,
    owner_review_granted,
    run_ai_self_iteration_review,
)
from maintenance_bridge_utils import (
    append_trace,
    cooldown_ready,
    maintenance_preflight,
    read_text_optional,
    resolve_root,
)

TRACE_REL = "memory/self/ai_self_iteration_review_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


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
        _trace(resolve_root(context), "on_load ok")

    def _cooldown_ready(self) -> tuple[bool, str]:
        ready, reason = cooldown_ready(
            self._ctx,
            state_key="ai_self_iteration_review_last_run",
            min_interval_seconds=self._min_interval_seconds,
        )
        if not ready:
            return False, reason

        if not self._ctx:
            return True, reason
        last_run = self._ctx.get_state("ai_self_iteration_review_last_run")
        if not last_run:
            return True, "never_run"
        try:
            datetime.fromisoformat(str(last_run))
        except Exception:
            return True, "bad_last_run"
        return True, "cooldown_ready"

    def _should_run(self, root: Path) -> tuple[bool, str]:
        should_continue, reason = maintenance_preflight(self._ctx, root)
        if not should_continue:
            return False, reason

        gate = read_text_optional(root / "memory/self/ai_self_iteration_state.md")
        gate_status = extract_value(gate, "gate_status")
        if gate_status != "growth_review_candidate":
            return False, f"gate_status:{gate_status}"

        review = read_text_optional(root / "memory/self/ai_self_iteration_review_state.md")
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
        root = resolve_root(self._ctx)
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
