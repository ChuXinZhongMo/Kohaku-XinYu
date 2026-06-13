from __future__ import annotations

from typing import Any

from xinyu_bridge_desktop_projection import desktop_avatar_url
from xinyu_bridge_desktop_projection import desktop_display_id
from xinyu_bridge_desktop_projection import desktop_group_avatar_url
from xinyu_bridge_desktop_projection import desktop_hash
from xinyu_bridge_desktop_projection import desktop_marker_count
from xinyu_bridge_desktop_projection import desktop_privacy_for_payload
from xinyu_bridge_desktop_projection import desktop_proactive_expired
from xinyu_bridge_desktop_projection import desktop_recall_count
from xinyu_bridge_desktop_projection import desktop_session_kind
from xinyu_bridge_desktop_projection import desktop_text_preview
from xinyu_bridge_desktop_projection import desktop_top_recall_sources


def install_desktop_projection_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._desktop_marker_count = staticmethod(desktop_marker_count)
    runtime_cls._desktop_recall_count = staticmethod(desktop_recall_count)
    runtime_cls._desktop_top_recall_sources = staticmethod(desktop_top_recall_sources)
    runtime_cls._desktop_proactive_expired = staticmethod(desktop_proactive_expired)
    runtime_cls._desktop_session_kind = staticmethod(desktop_session_kind)
    runtime_cls._desktop_display_id = staticmethod(desktop_display_id)
    runtime_cls._desktop_avatar_url = staticmethod(desktop_avatar_url)
    runtime_cls._desktop_group_avatar_url = staticmethod(desktop_group_avatar_url)
    runtime_cls._desktop_privacy_for_payload = staticmethod(desktop_privacy_for_payload)
    runtime_cls._desktop_hash = staticmethod(desktop_hash)
    runtime_cls._desktop_text_preview = staticmethod(desktop_text_preview)
