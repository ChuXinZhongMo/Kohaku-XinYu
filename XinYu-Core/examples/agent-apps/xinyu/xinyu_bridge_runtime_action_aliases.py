from __future__ import annotations

from functools import partialmethod
from typing import Any

import xinyu_bridge_action_routes
from xinyu_bridge_errors import BridgeRequestError


def install_action_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._settle_action_experience = xinyu_bridge_action_routes.settle_action_experience
    runtime_cls._maybe_handle_action_layer_turn = partialmethod(
        xinyu_bridge_action_routes.handle_action_layer_turn,
        bridge_request_error_type=BridgeRequestError,
    )
    runtime_cls._maybe_handle_recent_action_followup_turn = (
        xinyu_bridge_action_routes.handle_recent_action_followup_turn
    )
    runtime_cls._maybe_handle_action_digest_followup_turn = (
        xinyu_bridge_action_routes.handle_action_digest_followup_turn
    )
