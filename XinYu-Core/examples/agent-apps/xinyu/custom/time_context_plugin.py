"""Runtime time-context plugin for Xinyu."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext


class TimeContextPlugin(BasePlugin):
    name = "xinyu_time_context"
    priority = 85

    def __init__(
        self,
        inject_timezone: bool = True,
        inject_day_phase: bool = True,
        options: dict[str, Any] | None = None,
        **_: Any,
    ):
        opts = options or {}
        self._inject_timezone = bool(opts.get("inject_timezone", inject_timezone))
        self._inject_day_phase = bool(opts.get("inject_day_phase", inject_day_phase))
        self._ctx: PluginContext | None = None

    async def on_load(self, context: PluginContext) -> None:
        self._ctx = context

    def _now(self) -> datetime:
        fixed_now = os.environ.get("XINYU_TIME_CONTEXT_FIXED_NOW", "").strip()
        if fixed_now:
            try:
                return datetime.fromisoformat(fixed_now.replace("Z", "+00:00")).astimezone()
            except ValueError:
                pass
        return datetime.now().astimezone()

    async def pre_llm_call(self, messages: list[dict], **kwargs) -> list[dict] | None:
        now = self._now()
        parts = [
            f"Current real time: {now.isoformat()}",
            f"Current date: {now.date().isoformat()}",
        ]

        if self._inject_timezone:
            parts.append(f"Timezone: {now.tzinfo}")

        if self._inject_day_phase:
            hour = now.hour
            if 5 <= hour < 12:
                phase = "morning"
            elif 12 <= hour < 18:
                phase = "afternoon"
            elif 18 <= hour < 23:
                phase = "evening"
            else:
                phase = "late night"
            parts.append(f"Day phase: {phase}")

        parts.append(
            "Interpret memory through real elapsed time: recent, lingering, distant, overdue, or faded."
        )

        injection = {
            "role": "system",
            "content": "[Plugin: xinyu_time_context]\n" + "\n".join(parts),
        }

        insert_idx = 1
        for i, msg in enumerate(messages):
            if msg.get("role") == "system":
                insert_idx = i + 1
                break

        modified = list(messages)
        modified.insert(insert_idx, injection)
        return modified
