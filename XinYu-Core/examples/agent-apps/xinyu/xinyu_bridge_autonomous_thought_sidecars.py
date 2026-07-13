from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_autonomous_thought_appenders import (
    append_autonomous_outward_note,
    append_learning_closed_loop_self_thought_note,
    append_proactive_request_note,
    append_self_exploration_note,
    append_self_thought_loop_note,
)
from xinyu_bridge_autonomous_thought_desktop import append_desktop_proactive_candidate_ready_note
from xinyu_bridge_autonomous_thought_flow import (
    _BASE_THOUGHT_SIDECAR_METHODS,
    _append_base_thought_sidecar_notes,
    append_autonomous_outcome_shadow_notes,
    append_self_thought_research_notes,
    run_autonomous_self_thought_sidecars,
)
from xinyu_bridge_autonomous_thought_payloads import (
    autonomous_outward_kwargs,
    learning_closed_loop_self_thought_kwargs,
    proactive_request_kwargs,
    self_exploration_kwargs,
    self_thought_loop_kwargs,
)
from xinyu_bridge_autonomous_note_responses import (
    autonomous_outward_is_queued,
    autonomous_outward_summary,
    bounded_closed_loop_notes,
    desktop_candidate_request_notes,
    proactive_request_summary,
    request_allows_desktop_candidate,
    self_exploration_summary,
    self_thought_research_summary,
    self_thought_summary,
)
from xinyu_bridge_autonomous_trace_helpers import append_autonomous_error
from xinyu_bridge_values import as_bool

__all__ = (
    "Any",
    "Callable",
    "_BASE_THOUGHT_SIDECAR_METHODS",
    "_append_base_thought_sidecar_notes",
    "annotations",
    "append_autonomous_error",
    "append_autonomous_outcome_shadow_notes",
    "append_autonomous_outward_note",
    "append_desktop_proactive_candidate_ready_note",
    "append_learning_closed_loop_self_thought_note",
    "append_proactive_request_note",
    "append_self_exploration_note",
    "append_self_thought_loop_note",
    "append_self_thought_research_notes",
    "as_bool",
    "autonomous_outward_is_queued",
    "autonomous_outward_kwargs",
    "autonomous_outward_summary",
    "bounded_closed_loop_notes",
    "desktop_candidate_request_notes",
    "learning_closed_loop_self_thought_kwargs",
    "proactive_request_kwargs",
    "proactive_request_summary",
    "request_allows_desktop_candidate",
    "run_autonomous_self_thought_sidecars",
    "self_exploration_kwargs",
    "self_exploration_summary",
    "self_thought_loop_kwargs",
    "self_thought_research_summary",
    "self_thought_summary",
)
