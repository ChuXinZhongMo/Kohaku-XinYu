from __future__ import annotations

from typing import Any

import xinyu_bridge_metabolism_routes


def install_metabolism_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._desktop_open_metabolism_ticket = xinyu_bridge_metabolism_routes.desktop_open_metabolism_ticket
    runtime_cls._metabolism_input_window = staticmethod(xinyu_bridge_metabolism_routes.metabolism_input_window)
    runtime_cls.life_metabolism_ticket_get = xinyu_bridge_metabolism_routes.life_metabolism_ticket_get
    runtime_cls.life_metabolism_ticket_list = xinyu_bridge_metabolism_routes.life_metabolism_ticket_list
    runtime_cls.life_metabolism_ticket_approve = xinyu_bridge_metabolism_routes.life_metabolism_ticket_approve
    runtime_cls.life_metabolism_ticket_reject = xinyu_bridge_metabolism_routes.life_metabolism_ticket_reject
    runtime_cls.life_metabolism_ticket_cancel = xinyu_bridge_metabolism_routes.life_metabolism_ticket_cancel
    runtime_cls._apply_self_choice_metabolism_decision = (
        xinyu_bridge_metabolism_routes.apply_self_choice_metabolism_decision
    )
    runtime_cls._publish_metabolism_decision = xinyu_bridge_metabolism_routes.publish_metabolism_decision
    runtime_cls._metabolism_runner_loop = xinyu_bridge_metabolism_routes.metabolism_runner_loop
    runtime_cls._run_due_metabolism_once = xinyu_bridge_metabolism_routes.run_due_metabolism_once
    runtime_cls._publish_metabolism_runner_result = xinyu_bridge_metabolism_routes.publish_metabolism_runner_result
    runtime_cls._wake_metabolism_runner = xinyu_bridge_metabolism_routes.wake_metabolism_runner
