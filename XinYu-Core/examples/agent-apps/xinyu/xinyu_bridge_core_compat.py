from __future__ import annotations

import xinyu_bridge_codex_markers
import xinyu_bridge_codex_runtime
import xinyu_bridge_context
import xinyu_bridge_desktop_proactive_routes
import xinyu_bridge_desktop_recent_routes
import xinyu_bridge_renderer
import xinyu_bridge_runtime_dialogue_aliases
from v1_canary_gate import payload_has_attachment_signal as _payload_has_attachment_signal
from xinyu_action_experience_digest import (
    compose_action_digest_followup,
    digest_action_experience_residue,
)
from xinyu_action_reply_composer import compose_action_reply
from xinyu_bridge_autonomous_maintenance import AUTONOMOUS_MAINTENANCE_PROMPT
from xinyu_bridge_bootstrap import ensure_repo_src as _ensure_repo_src
from xinyu_bridge_desktop_actions import desktop_scrub_action_markers as _desktop_scrub_action_markers
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_session import AgentSession
from xinyu_bridge_state_text import parse_iso as _parse_iso
from xinyu_bridge_state_text import payload_path as _payload_path
from xinyu_bridge_state_text import seconds_since_iso as _seconds_since_iso
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import as_int as _as_int
from xinyu_bridge_values import as_str_set as _as_str_set
from xinyu_bridge_values import compact_text as _compact_text
from xinyu_bridge_values import contains_any as _contains_any
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import optional_int as _optional_int
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_experience_frame import (
    build_experience_frame,
    compose_recent_action_followup,
    write_action_experience_residue,
    write_recent_action_experience,
)
from xinyu_initiative_orchestrator import record_initiative_feedback
from xinyu_life_month_slots import refresh_current_life_month_context
from xinyu_memory_event_sourcing import record_action_experience_event, record_chat_event
from xinyu_memory_weights import refresh_memory_weight_state
from xinyu_private_thought_events import record_private_thought_reply_link
from xinyu_visible_state_hygiene import sanitize_visible_state_files

# K-002: Safe Self Model access (kernel is independent)
try:
    from kernel import get_kernel_self_model
except Exception:
    def get_kernel_self_model(self_id: str = "xinyu_main", persist_path=None):
        return {"self_id": self_id, "core_statements": [], "error": "kernel not available"}

CODEX_DEFAULT_TIMEOUT_SECONDS = xinyu_bridge_codex_runtime.CODEX_DEFAULT_TIMEOUT_SECONDS
CODEX_VISIBLE_WINDOW_TITLE = xinyu_bridge_codex_runtime.CODEX_VISIBLE_WINDOW_TITLE
CODEX_GENERATED_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
CODEX_DELEGATE_OPEN = xinyu_bridge_codex_markers.CODEX_DELEGATE_OPEN
CODEX_DELEGATE_CLOSE = xinyu_bridge_codex_markers.CODEX_DELEGATE_CLOSE
CODEX_DELEGATE_PATTERNS = xinyu_bridge_codex_markers.CODEX_DELEGATE_PATTERNS
WAIT_TO_THINK_PATTERNS = xinyu_bridge_codex_runtime.WAIT_TO_THINK_PATTERNS

DESKTOP_RECENT_TURNS_MAX = xinyu_bridge_desktop_recent_routes.DESKTOP_RECENT_TURNS_MAX
DESKTOP_RECENT_MEMORY_EVENTS_MAX = xinyu_bridge_desktop_recent_routes.DESKTOP_RECENT_MEMORY_EVENTS_MAX
DESKTOP_PROACTIVE_HISTORY_MAX = xinyu_bridge_desktop_proactive_routes.DESKTOP_PROACTIVE_HISTORY_MAX
DESKTOP_PROACTIVE_HISTORY_REL = xinyu_bridge_desktop_proactive_routes.DESKTOP_PROACTIVE_HISTORY_REL
DESKTOP_PROACTIVE_INBOX_STATUSES = xinyu_bridge_desktop_proactive_routes.DESKTOP_PROACTIVE_INBOX_STATUSES
DESKTOP_PROACTIVE_FINAL_STATUSES = xinyu_bridge_desktop_proactive_routes.DESKTOP_PROACTIVE_FINAL_STATUSES
DEBUG_PROMPT_DUMP_ENV = xinyu_bridge_renderer.DEBUG_PROMPT_DUMP_ENV
DEBUG_LIVE_SYSTEM_PROMPT_REL = xinyu_bridge_renderer.DEBUG_LIVE_SYSTEM_PROMPT_REL
V1_OWNER_SIMPLE_CANARY_ENV = xinyu_bridge_runtime_dialogue_aliases.V1_OWNER_SIMPLE_CANARY_ENV
V1_CANARY_GREETING_TEXTS = xinyu_bridge_runtime_dialogue_aliases.V1_CANARY_GREETING_TEXTS
V1_CANARY_ACK_TEXTS = xinyu_bridge_runtime_dialogue_aliases.V1_CANARY_ACK_TEXTS

PROMISE_FOLLOWUP_USER_MARKERS = xinyu_bridge_runtime_dialogue_aliases.PROMISE_FOLLOWUP_USER_MARKERS
PROMISE_FOLLOWUP_REPLY_MARKERS = xinyu_bridge_runtime_dialogue_aliases.PROMISE_FOLLOWUP_REPLY_MARKERS
PROMISE_FOLLOWUP_DONE_MARKERS = xinyu_bridge_runtime_dialogue_aliases.PROMISE_FOLLOWUP_DONE_MARKERS
PROMISE_FOLLOWUP_STATE_REL = xinyu_bridge_runtime_dialogue_aliases.PROMISE_FOLLOWUP_STATE_REL
OWNER_DIRECT_CODEX_DELEGATE_MARKERS = xinyu_bridge_codex_runtime.OWNER_DIRECT_CODEX_DELEGATE_MARKERS
OWNER_DIRECT_CODEX_SUPPORT_MARKERS = xinyu_bridge_codex_runtime.OWNER_DIRECT_CODEX_SUPPORT_MARKERS
OWNER_DIRECT_CODEX_NEGATIVE_MARKERS = xinyu_bridge_codex_runtime.OWNER_DIRECT_CODEX_NEGATIVE_MARKERS
OWNER_SELF_CODE_EDIT_GRANT_MARKERS = xinyu_bridge_codex_runtime.OWNER_SELF_CODE_EDIT_GRANT_MARKERS
OWNER_SELF_CODE_START_MARKERS = xinyu_bridge_codex_runtime.OWNER_SELF_CODE_START_MARKERS
OWNER_SELF_CODE_NEGATIVE_MARKERS = xinyu_bridge_codex_runtime.OWNER_SELF_CODE_NEGATIVE_MARKERS
OWNER_SELF_CODE_GRANT_CUES = xinyu_bridge_codex_runtime.OWNER_SELF_CODE_GRANT_CUES

PROMPT_CONTEXT_SIGNATURE_FILES = xinyu_bridge_context.PROMPT_CONTEXT_SIGNATURE_FILES

__all__ = (
    "AUTONOMOUS_MAINTENANCE_PROMPT",
    "AgentSession",
    "BridgeRequestError",
    "CODEX_DEFAULT_TIMEOUT_SECONDS",
    "CODEX_DELEGATE_CLOSE",
    "CODEX_DELEGATE_OPEN",
    "CODEX_DELEGATE_PATTERNS",
    "CODEX_GENERATED_IMAGE_SUFFIXES",
    "CODEX_VISIBLE_WINDOW_TITLE",
    "DEBUG_LIVE_SYSTEM_PROMPT_REL",
    "DEBUG_PROMPT_DUMP_ENV",
    "DESKTOP_PROACTIVE_FINAL_STATUSES",
    "DESKTOP_PROACTIVE_HISTORY_MAX",
    "DESKTOP_PROACTIVE_HISTORY_REL",
    "DESKTOP_PROACTIVE_INBOX_STATUSES",
    "DESKTOP_RECENT_MEMORY_EVENTS_MAX",
    "DESKTOP_RECENT_TURNS_MAX",
    "OWNER_DIRECT_CODEX_DELEGATE_MARKERS",
    "OWNER_DIRECT_CODEX_NEGATIVE_MARKERS",
    "OWNER_DIRECT_CODEX_SUPPORT_MARKERS",
    "OWNER_SELF_CODE_EDIT_GRANT_MARKERS",
    "OWNER_SELF_CODE_GRANT_CUES",
    "OWNER_SELF_CODE_NEGATIVE_MARKERS",
    "OWNER_SELF_CODE_START_MARKERS",
    "PROMISE_FOLLOWUP_DONE_MARKERS",
    "PROMISE_FOLLOWUP_REPLY_MARKERS",
    "PROMISE_FOLLOWUP_STATE_REL",
    "PROMISE_FOLLOWUP_USER_MARKERS",
    "PROMPT_CONTEXT_SIGNATURE_FILES",
    "V1_CANARY_ACK_TEXTS",
    "V1_CANARY_GREETING_TEXTS",
    "V1_OWNER_SIMPLE_CANARY_ENV",
    "WAIT_TO_THINK_PATTERNS",
    "_as_bool",
    "_as_int",
    "_as_str_set",
    "_compact_text",
    "_contains_any",
    "_dedupe",
    "_desktop_scrub_action_markers",
    "_ensure_repo_src",
    "_optional_int",
    "_parse_iso",
    "_payload_has_attachment_signal",
    "_payload_path",
    "_safe_str",
    "_seconds_since_iso",
    "build_experience_frame",
    "compose_action_digest_followup",
    "compose_action_reply",
    "compose_recent_action_followup",
    "digest_action_experience_residue",
    "record_action_experience_event",
    "record_chat_event",
    "record_initiative_feedback",
    "record_private_thought_reply_link",
    "refresh_current_life_month_context",
    "refresh_memory_weight_state",
    "sanitize_visible_state_files",
    "write_action_experience_residue",
    "write_recent_action_experience",
    "xinyu_bridge_codex_markers",
    "xinyu_bridge_codex_runtime",
    "xinyu_bridge_context",
    "xinyu_bridge_desktop_proactive_routes",
    "xinyu_bridge_desktop_recent_routes",
    "get_kernel_self_model",
    "xinyu_bridge_renderer",
    "xinyu_bridge_runtime_dialogue_aliases",
)
