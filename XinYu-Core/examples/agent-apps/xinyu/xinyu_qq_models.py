from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ReplyTarget:
    message_kind: str
    user_id: str
    group_id: str


@dataclass(frozen=True)
class PreparedMessage:
    target: ReplyTarget
    payload: dict[str, Any]
    route: str = "chat"
    local_reply: str = ""


@dataclass
class PendingAction:
    connection_id: str
    future: asyncio.Future[dict[str, Any]]


@dataclass
class RecentStickerImportState:
    target: ReplyTarget
    event: dict[str, Any]
    payload: dict[str, Any]
    response: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    error: str = ""
    updated_at: float = field(default_factory=time.time)
