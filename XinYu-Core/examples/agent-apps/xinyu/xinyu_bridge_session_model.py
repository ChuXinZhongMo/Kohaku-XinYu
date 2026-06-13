from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentSession:
    key: str
    agent: Any
    prompt_signature: str
    chunks: list[str] = field(default_factory=list)
    dialogue_tail: list[dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
