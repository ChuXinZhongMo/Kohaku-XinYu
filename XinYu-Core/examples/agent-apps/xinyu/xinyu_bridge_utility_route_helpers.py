from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xinyu_bridge_utility_common import ensure_open
from xinyu_bridge_utility_common import ensure_payload
from xinyu_bridge_utility_common import payload_or_empty
from xinyu_bridge_utility_common import sessions
from xinyu_bridge_utility_goldmark import goldmark_mark_request
from xinyu_bridge_utility_learning_proxy import learning_ingest
from xinyu_bridge_utility_learning_proxy import learning_observe
from xinyu_bridge_utility_learning_proxy import learning_study
from xinyu_bridge_utility_message import _drop_dialogue_tail
from xinyu_bridge_utility_message import _drop_live_session_tail
from xinyu_bridge_utility_message import _extend_notes
from xinyu_bridge_utility_message import message_ack
from xinyu_bridge_utility_message import message_drop
from xinyu_bridge_utility_package import package_install
from xinyu_bridge_utility_probe import probe
from xinyu_bridge_utility_probe import runtime_probe
from xinyu_bridge_utility_review import review_inbox_command
from xinyu_bridge_utility_sticker import sticker_import


@dataclass(frozen=True, slots=True)
class UtilityRouteDeps:
    bridge_request_error_type: Callable[[Any, str], Exception]
    learning_bridge_error_type: type[Exception]
    bad_request_status: Any
    service_unavailable_status: Any
    to_thread: Callable[..., Any]
    handle_review_inbox_command: Callable[..., Any]
    install_python_packages: Callable[..., Any]
    import_sticker_from_payload: Callable[..., Any]
    register_sent_reply_ack: Callable[..., Any]
    record_action_feedback_from_message_ack: Callable[..., Any]
    record_action_feedback_from_message_drop: Callable[..., Any]
    remove_matching_assistant_reply_from_tail: Callable[..., Any]
    save_dialogue_tail: Callable[..., Any]
    remove_matching_assistant_reply: Callable[..., Any]
    retract_archived_assistant_message: Callable[..., Any]
    mark_goldmark_request: Callable[..., Any]


__all__ = [
    "UtilityRouteDeps",
    "ensure_open",
    "ensure_payload",
    "payload_or_empty",
    "sessions",
    "probe",
    "runtime_probe",
    "review_inbox_command",
    "package_install",
    "learning_ingest",
    "learning_study",
    "learning_observe",
    "sticker_import",
    "message_ack",
    "message_drop",
    "goldmark_mark_request",
]
