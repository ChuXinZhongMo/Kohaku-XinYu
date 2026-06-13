from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


TraceRouteStage = Callable[..., Any]


@dataclass(slots=True)
class ReplyPipelinePayload:
    runtime: Any
    session: Any
    payload: dict[str, Any]
    reply: str
    draft_reply: str
    user_text: str
    recalled_context: Any
    life_reply_policy: dict[str, Any]
    trace_route_stage: TraceRouteStage
    blocked_by_delegate: bool
    codex_delegate_blocked: bool
