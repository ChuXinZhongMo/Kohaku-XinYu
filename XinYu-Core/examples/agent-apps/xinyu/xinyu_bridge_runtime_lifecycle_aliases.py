from __future__ import annotations

from typing import Any

import xinyu_bridge_runtime_lifecycle


def install_lifecycle_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._ensure_self_choice_ready = xinyu_bridge_runtime_lifecycle.ensure_self_choice_ready
    runtime_cls.start_background_tasks = xinyu_bridge_runtime_lifecycle.start_background_tasks
    runtime_cls.shutdown = xinyu_bridge_runtime_lifecycle.shutdown
