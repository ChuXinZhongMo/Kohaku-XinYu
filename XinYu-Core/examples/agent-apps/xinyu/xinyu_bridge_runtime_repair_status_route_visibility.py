from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


RUNTIME_REPAIR_STATUS_OK_REPLY = (
    "刚才那句“还没”是旧进程在回。现在 core 已重启，gateway 也连着，"
    "新代码已经加载；下一轮会走新的记忆、思维、动作一致性链路。"
)
RUNTIME_REPAIR_STATUS_GATEWAY_WARN_REPLY = (
    "core 已经是新代码了，但 QQ gateway 这边我没确认到监听状态。"
    "先别信“还没”那种旧尾巴，我还得看 gateway。"
)
RUNTIME_REPAIR_STATUS_CORE_WARN_REPLY = "还没完全好。当前 core 没对上新源码状态，我不能装作修完。"

_DIRECT_STATUS_MARKERS = ("还没修", "修好了吗", "修好了么", "修完了吗", "修完了么")
_NOW_STATUS_MARKERS = ("现在好了吗", "现在好了么", "现在好了嗎", "现在好了没")
_TIME_SCOPE_MARKERS = ("现在", "这次", "刚才")
_REPAIR_RESULT_MARKERS = ("好了", "好了吗", "好了么", "修好", "解决")
_RUNTIME_SCOPE_MARKERS = ("系统", "状态", "记忆", "思维", "动作", "回复", "qq", "bridge", "gateway", "core")


@dataclass(frozen=True, slots=True)
class RuntimeRepairStatusVisibility:
    reply: str
    status: str
    guard_flags: Any


def looks_like_runtime_repair_status_question(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "").lower()
    if not compact:
        return False
    if any(marker in compact for marker in _DIRECT_STATUS_MARKERS):
        return True
    if any(marker in compact for marker in _NOW_STATUS_MARKERS):
        return True
    return bool(
        any(marker in compact for marker in _TIME_SCOPE_MARKERS)
        and any(marker in compact for marker in _REPAIR_RESULT_MARKERS)
        and any(marker in compact for marker in _RUNTIME_SCOPE_MARKERS)
    )


def runtime_repair_status_visible_reply(*, core_ok: bool, gateway_ok: bool) -> tuple[str, str]:
    if core_ok and gateway_ok:
        return RUNTIME_REPAIR_STATUS_OK_REPLY, "ok"
    if core_ok:
        return RUNTIME_REPAIR_STATUS_GATEWAY_WARN_REPLY, "warn"
    return RUNTIME_REPAIR_STATUS_CORE_WARN_REPLY, "warn"


def build_runtime_repair_status_visibility(
    payload: dict[str, Any],
    *,
    text: str,
    core_ok: bool,
    gateway_ok: bool,
    final_reply_guard_func: Callable[..., tuple[str, Any]],
) -> RuntimeRepairStatusVisibility:
    reply, status = runtime_repair_status_visible_reply(core_ok=core_ok, gateway_ok=gateway_ok)
    guarded_reply, guard_flags = final_reply_guard_func(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if guarded_reply:
        reply = guarded_reply
    return RuntimeRepairStatusVisibility(reply=reply, status=status, guard_flags=guard_flags)


__all__ = [
    "RuntimeRepairStatusVisibility",
    "build_runtime_repair_status_visibility",
    "looks_like_runtime_repair_status_question",
    "runtime_repair_status_visible_reply",
]
