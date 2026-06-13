from __future__ import annotations

from typing import Any

import xinyu_bridge_desktop_self_action_routes
import xinyu_bridge_self_action_qq
from xinyu_self_action_voice import compose_self_action_approval_voice, compose_self_action_prepared_patch_voice


def install_desktop_self_action_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls.desktop_self_action_approval = xinyu_bridge_desktop_self_action_routes.desktop_self_action_approval
    runtime_cls._desktop_attach_self_action_patch_executor = (
        xinyu_bridge_desktop_self_action_routes.desktop_attach_self_action_patch_executor
    )
    runtime_cls._desktop_self_action_pending_item = xinyu_bridge_desktop_self_action_routes.desktop_self_action_pending_item
    runtime_cls._desktop_self_action_approval_reply = staticmethod(
        xinyu_bridge_desktop_self_action_routes.desktop_self_action_approval_reply
    )
    runtime_cls._self_action_approval_message = staticmethod(compose_self_action_approval_voice)
    runtime_cls._self_action_prepared_patch_message = staticmethod(compose_self_action_prepared_patch_voice)
    runtime_cls._self_action_intent_label = staticmethod(xinyu_bridge_desktop_self_action_routes.self_action_intent_label)
    runtime_cls._self_action_reason_label = staticmethod(xinyu_bridge_desktop_self_action_routes.self_action_reason_label)
    runtime_cls._self_action_scope_label = staticmethod(xinyu_bridge_desktop_self_action_routes.self_action_scope_label)
    runtime_cls._self_action_boundary_label = staticmethod(
        xinyu_bridge_desktop_self_action_routes.self_action_boundary_label
    )
    runtime_cls._self_action_approval_effect_label = staticmethod(
        xinyu_bridge_desktop_self_action_routes.self_action_approval_effect_label
    )
    runtime_cls._self_action_goal_label = staticmethod(xinyu_bridge_desktop_self_action_routes.self_action_goal_label)
    runtime_cls._self_action_ecology_context_label = staticmethod(
        xinyu_bridge_desktop_self_action_routes.self_action_ecology_context_label
    )
    runtime_cls._self_action_patch_goal_label = staticmethod(
        xinyu_bridge_desktop_self_action_routes.self_action_patch_goal_label
    )
    runtime_cls._self_action_action_label = staticmethod(xinyu_bridge_desktop_self_action_routes.self_action_action_label)
    runtime_cls._maybe_enqueue_self_action_approval_to_qq = (
        xinyu_bridge_self_action_qq.maybe_enqueue_self_action_approval_to_qq
    )
    runtime_cls._maybe_enqueue_self_action_prepared_patch_to_qq = (
        xinyu_bridge_self_action_qq.maybe_enqueue_self_action_prepared_patch_to_qq
    )
