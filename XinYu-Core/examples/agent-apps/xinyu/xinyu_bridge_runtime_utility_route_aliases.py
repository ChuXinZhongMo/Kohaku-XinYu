from __future__ import annotations

from typing import Any

import xinyu_bridge_utility_routes


def install_utility_route_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls.probe = xinyu_bridge_utility_routes.runtime_probe
    runtime_cls.package_install = xinyu_bridge_utility_routes.package_install
    runtime_cls.learning_ingest = xinyu_bridge_utility_routes.learning_ingest
    runtime_cls.sticker_import = xinyu_bridge_utility_routes.sticker_import
    runtime_cls.learning_study = xinyu_bridge_utility_routes.learning_study
    runtime_cls.learning_observe = xinyu_bridge_utility_routes.learning_observe
    runtime_cls.review_inbox_command = xinyu_bridge_utility_routes.review_inbox_command
    runtime_cls.message_ack = xinyu_bridge_utility_routes.message_ack
    runtime_cls.message_drop = xinyu_bridge_utility_routes.message_drop
    runtime_cls.goldmark_mark_request = xinyu_bridge_utility_routes.goldmark_mark_request
