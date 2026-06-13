from __future__ import annotations

from typing import Any

import xinyu_bridge_semantic_fast_routes


def install_semantic_fast_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._owner_private_semantic_fast_decision = (
        xinyu_bridge_semantic_fast_routes.owner_private_semantic_fast_decision
    )
    runtime_cls._maybe_handle_owner_private_semantic_fast_turn = (
        xinyu_bridge_semantic_fast_routes.handle_owner_private_semantic_fast_turn
    )
    runtime_cls._empty_visible_reply_fallback = xinyu_bridge_semantic_fast_routes.empty_visible_reply_fallback
    runtime_cls._owner_private_llm_failover_context = (
        xinyu_bridge_semantic_fast_routes.owner_private_llm_failover_context
    )
