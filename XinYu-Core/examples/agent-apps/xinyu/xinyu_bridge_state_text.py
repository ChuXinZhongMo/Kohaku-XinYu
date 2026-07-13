from __future__ import annotations

from xinyu_bridge_state_text_fields import (
    TIMESTAMP_FIELD_NAMES,
    _replacement_value,
    read_text_safe,
    replace_frontmatter_field,
    replace_list_field,
    state_field,
)
from xinyu_bridge_state_text_time import (
    _coerce_event_datetime,
    _datetime_from_timestamp,
    _payload_event_datetime,
    _payload_event_datetime_with_source,
    build_payload_time_context_block,
    iso_from_timestamp,
    parse_iso,
    payload_event_time_iso,
    payload_event_timestamp_seconds,
    payload_path,
    seconds_since_iso,
)


desktop_replace_frontmatter_field = replace_frontmatter_field
desktop_replace_list_field = replace_list_field

__all__ = (
    "TIMESTAMP_FIELD_NAMES",
    "_coerce_event_datetime",
    "_datetime_from_timestamp",
    "_payload_event_datetime",
    "_payload_event_datetime_with_source",
    "_replacement_value",
    "annotations",
    "build_payload_time_context_block",
    "desktop_replace_frontmatter_field",
    "desktop_replace_list_field",
    "iso_from_timestamp",
    "parse_iso",
    "payload_event_time_iso",
    "payload_event_timestamp_seconds",
    "payload_path",
    "read_text_safe",
    "replace_frontmatter_field",
    "replace_list_field",
    "seconds_since_iso",
    "state_field",
)
