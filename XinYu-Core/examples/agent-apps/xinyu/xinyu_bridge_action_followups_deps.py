from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True, slots=True)
class ActionFollowupFacadeDeps:
    handle_action_followup_turn_impl: Callable[..., Any]
    finish_action_turn: Callable[..., Any]
    extend_common_finish_notes: Callable[..., None]


def facade_deps(facade: Mapping[str, Any]) -> ActionFollowupFacadeDeps:
    return ActionFollowupFacadeDeps(
        handle_action_followup_turn_impl=facade["_handle_action_followup_turn_impl"],
        finish_action_turn=facade["finish_action_turn"],
        extend_common_finish_notes=facade["extend_common_finish_notes"],
    )
