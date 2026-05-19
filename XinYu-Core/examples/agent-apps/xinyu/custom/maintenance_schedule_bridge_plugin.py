"""Install conservative low-frequency maintenance schedules for Xinyu."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext
from xinyu_runtime.modules.trigger.scheduler import SchedulerTrigger

from maintenance_bridge_utils import append_trace, resolve_root

_DISABLED_VALUES = {"1", "true", "yes", "on", "disabled", "disable", "off"}


TRACE_REL = "memory/context/maintenance_schedule_trace.log"


def _trace(root: Path, line: str) -> None:
    append_trace(root, TRACE_REL, line)


def _render_state(
    evaluated_at: str,
    installed: list[dict[str, str]],
    skipped: list[str],
) -> str:
    installed_block = (
        "\n".join(
            f"## {item['trigger_id']}\n"
            f"- kind: {item['kind']}\n"
            f"- schedule: {item['schedule']}\n"
            f"- purpose: {item['purpose']}\n"
            f"- status: installed\n"
            for item in installed
        )
        if installed
        else "## none\n- status: none\n"
    )
    skipped_block = "\n".join(f"- {item}" for item in skipped) if skipped else "- none"
    return f"""---
title: Maintenance Schedule State
memory_type: maintenance_schedule_state
time_scope: mid_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 83
impact_score: 81
confidence_score: 100
status: active
tags: [maintenance, schedules, triggers]
---

# Maintenance Schedule State

## Last Evaluation
- evaluated_at: {evaluated_at}
- mode: conservative_runtime_install

## Installed Schedules
{installed_block}

## Skipped
{skipped_block}

## Rules
- Only install low-frequency daily schedules.
- Never duplicate an existing maintenance trigger id.
- Do not install high-frequency timers here.
- Schedules are support structure, not permission for noisy self-activity.
"""


class MaintenanceScheduleBridgePlugin(BasePlugin):
    name = "xinyu_maintenance_schedule_bridge"
    priority = 108

    def __init__(self, options: dict[str, Any] | None = None, **_: Any):
        opts = options or {}
        self._ctx: PluginContext | None = None
        self._enabled = bool(opts.get("enabled", True))
        self._install_once = bool(opts.get("install_once", True))
        self._time_anchor_daily_at = str(opts.get("time_anchor_daily_at", "09:10"))
        self._reflection_daily_at = str(opts.get("reflection_daily_at", "03:40"))

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context
        _trace(resolve_root(context), "on_load ok")

    async def on_agent_start(self) -> None:
        if not self._enabled or not self._ctx:
            return

        root = resolve_root(self._ctx)
        try:
            if os.environ.get("XINYU_DISABLE_MAINTENANCE_SCHEDULES", "").strip().lower() in _DISABLED_VALUES:
                _trace(root, "skipped env:XINYU_DISABLE_MAINTENANCE_SCHEDULES")
                return

            agent = getattr(self._ctx, "host_agent", None)
            if not agent or not hasattr(agent, "trigger_manager"):
                _trace(root, "skipped no_agent_or_trigger_manager")
                return

            if self._install_once and self._ctx.get_state("maintenance_schedules_installed"):
                _trace(root, "skipped already_installed_once")
                return

            existing = {info.trigger_id for info in agent.trigger_manager.list()}
            installed: list[dict[str, str]] = []
            skipped: list[str] = []

            plans = [
                {
                    "trigger_id": "xinyu_daily_time_anchor",
                    "kind": "daily",
                    "schedule": self._time_anchor_daily_at,
                    "purpose": "refresh time anchor and quiet continuity alignment",
                    "trigger": SchedulerTrigger(
                        daily_at=self._time_anchor_daily_at,
                        prompt=(
                            "Maintenance-only pass. Refresh time anchor, runtime bridge, and continuity lightly. "
                            "Do not treat this as a human speaking turn. Do not produce social chat or relationship reassurance. "
                            "If any outward text is unavoidable, output exactly [WAITING]."
                        ),
                    ),
                },
                {
                    "trigger_id": "xinyu_daily_reflection",
                    "kind": "daily",
                    "schedule": self._reflection_daily_at,
                    "purpose": "allow slow reflection-oriented maintenance",
                    "trigger": SchedulerTrigger(
                        daily_at=self._reflection_daily_at,
                        prompt=(
                            "Maintenance-only pass. Allow question pipeline, slow reprocess, reflection output, "
                            "source gate, source reliability, source integration gate, source request planner, source search resolver, autonomous search activation, source search provider, public GitHub learning, search result gate, outward source, source comparison, learner integration, learning quality, AI self-iteration gate, consolidation, long-term memory gate, retention gate, archive output, archive commit, personality growth gate, and inner cycle summary if continuity supports it. Do not treat this as a human speaking turn. "
                            "Do not initiate visible chat. If any outward text is unavoidable, output exactly [WAITING]."
                        ),
                    ),
                },
            ]

            for plan in plans:
                trigger_id = plan["trigger_id"]
                if trigger_id in existing:
                    skipped.append(f"{trigger_id}: already_exists")
                    continue
                await agent.add_trigger(plan["trigger"], trigger_id=trigger_id)
                installed.append(
                    {
                        "trigger_id": trigger_id,
                        "kind": plan["kind"],
                        "schedule": plan["schedule"],
                        "purpose": plan["purpose"],
                    }
                )
                _trace(root, f"installed {trigger_id} at {plan['schedule']}")

            evaluated_at = datetime.now().astimezone().isoformat()
            state_text = _render_state(evaluated_at, installed, skipped)
            (root / "memory/context/maintenance_schedule_state.md").write_text(
                state_text,
                encoding="utf-8",
            )
            self._ctx.set_state("maintenance_schedules_installed", True)
            _trace(
                root,
                f"on_agent_start installed={len(installed)} skipped={len(skipped)}",
            )
        except Exception as exc:
            _trace(root, f"error={exc!r}")
