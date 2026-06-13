from __future__ import annotations

from typing import Any

from xinyu_bridge_desktop_proactive_facade import bind_desktop_proactive_facade as _bind_proactive_facade
import xinyu_bridge_desktop_proactive_route_glue as _proactive_route_glue
from xinyu_bridge_desktop_proactive_state_store import (
    append_desktop_proactive_history_jsonl as append_jsonl,
)
from xinyu_bridge_desktop_proactive_state_store import (
    write_desktop_proactive_request_state_text as atomic_write_text,
)
from xinyu_bridge_desktop_projection import desktop_hash, desktop_text_preview
from xinyu_bridge_state_text import read_text_safe as _read_text_safe
from xinyu_bridge_state_text import state_field as _state_field
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_initiative_orchestrator import record_initiative_feedback
from xinyu_proactive_context_adapter import runtime_owner_private_turns
from xinyu_proactive_presence import _write_dispatch_state as write_proactive_qq_dispatch_state
from xinyu_qq_outbox import enqueue_qq_outbox_message
from xinyu_visible_persona_voice import compose_proactive_visible_message


DESKTOP_PROACTIVE_INBOX_MAX = _proactive_route_glue.DESKTOP_PROACTIVE_INBOX_MAX
DESKTOP_PROACTIVE_HISTORY_MAX = _proactive_route_glue.DESKTOP_PROACTIVE_HISTORY_MAX
DESKTOP_PROACTIVE_HISTORY_REL = _proactive_route_glue.DESKTOP_PROACTIVE_HISTORY_REL
DESKTOP_PROACTIVE_INBOX_STATUSES = _proactive_route_glue.DESKTOP_PROACTIVE_INBOX_STATUSES
DESKTOP_PROACTIVE_ACK_ACTIONS = _proactive_route_glue.DESKTOP_PROACTIVE_ACK_ACTIONS
DESKTOP_PROACTIVE_FINAL_STATUSES = _proactive_route_glue.DESKTOP_PROACTIVE_FINAL_STATUSES

_ensure_payload = _proactive_route_glue.ensure_payload


def _deps() -> _proactive_route_glue.DesktopProactiveDeps:
    return _proactive_route_glue.facade_deps(globals())


def _facade() -> dict[str, Any]:
    return globals()


globals().update(
    _bind_proactive_facade(
        deps_provider=_deps,
        facade_provider=_facade,
        module_name=__name__,
    )
)
