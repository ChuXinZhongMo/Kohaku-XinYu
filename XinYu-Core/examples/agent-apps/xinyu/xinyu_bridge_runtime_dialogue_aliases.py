from __future__ import annotations

from typing import Any

from xinyu_bridge_runtime_promise_followup_aliases import (
    PROMISE_FOLLOWUP_DONE_MARKERS,
    PROMISE_FOLLOWUP_REPLY_MARKERS,
    PROMISE_FOLLOWUP_STATE_REL,
    PROMISE_FOLLOWUP_USER_MARKERS,
    install_promise_followup_aliases,
)
from xinyu_bridge_runtime_semantic_fast_aliases import install_semantic_fast_aliases
from xinyu_bridge_runtime_v1_aliases import (
    V1_CANARY_ACK_TEXTS,
    V1_CANARY_GREETING_TEXTS,
    V1_OWNER_SIMPLE_CANARY_ENV,
    install_v1_aliases,
)


def install_runtime_dialogue_aliases(runtime_cls: type[Any]) -> type[Any]:
    install_v1_aliases(runtime_cls)
    install_semantic_fast_aliases(runtime_cls)
    install_promise_followup_aliases(runtime_cls)
    return runtime_cls
