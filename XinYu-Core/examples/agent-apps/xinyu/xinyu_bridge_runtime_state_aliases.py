from __future__ import annotations

from typing import Any

from xinyu_bridge_payload_policy import owner_private_payload_matches, trusted_private_payload_matches
from xinyu_bridge_reply_bubbles import (
    looks_like_false_single_bubble_limitation,
    numeric_bubble_units_from_text,
    owner_requested_reply_bubble_units,
)
from xinyu_bridge_session import session_key_from_payload
from xinyu_bridge_state_text import (
    desktop_replace_frontmatter_field,
    desktop_replace_list_field,
    iso_from_timestamp,
    payload_event_time_iso,
    payload_event_timestamp_seconds,
)
from xinyu_bridge_values import payload_text


def install_state_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._iso_from_timestamp = staticmethod(iso_from_timestamp)
    runtime_cls._payload_event_time_iso = staticmethod(payload_event_time_iso)
    runtime_cls._payload_event_timestamp_seconds = staticmethod(payload_event_timestamp_seconds)
    runtime_cls._desktop_replace_frontmatter_field = staticmethod(desktop_replace_frontmatter_field)
    runtime_cls._desktop_replace_list_field = staticmethod(desktop_replace_list_field)
    runtime_cls._payload_text = staticmethod(payload_text)
    runtime_cls._session_key = staticmethod(session_key_from_payload)
    runtime_cls._owner_private_payload_matches = staticmethod(owner_private_payload_matches)
    runtime_cls._trusted_private_payload_matches = staticmethod(trusted_private_payload_matches)
    runtime_cls._owner_requested_reply_bubble_units = staticmethod(owner_requested_reply_bubble_units)
    runtime_cls._numeric_bubble_units_from_text = staticmethod(numeric_bubble_units_from_text)
    runtime_cls._looks_like_false_single_bubble_limitation = staticmethod(
        looks_like_false_single_bubble_limitation
    )
