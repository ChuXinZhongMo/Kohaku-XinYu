from __future__ import annotations

import xinyu_bridge_autonomous_thought_sidecars as _thought_sidecars
from xinyu_bridge_autonomous_note_appenders import (
    append_autonomous_outward_note,
    append_creative_writing_note,
    append_daily_digest_note,
    append_emotion_council_note,
    append_github_learning_note,
    append_goal_ecology_note,
    append_goal_outcome_observer_note,
    append_goldmark_dehydrate_note,
    append_impulse_soup_note,
    append_initiative_spine_note,
    append_learning_closed_loop_self_thought_note,
    append_proactive_request_note,
    append_proactivity_shadow_note,
    append_review_inbox_note,
    append_self_action_gateway_note,
    append_self_action_patch_executor_note,
    append_self_exploration_note,
    append_self_thought_loop_note,
    append_watched_source_note,
)
from xinyu_bridge_autonomous_note_dispatch_map import (
    DepBindings as _DepBindings,
    NOTE_APPENDERS as _NOTE_APPENDERS,
    NoteAppendSpec as _NoteAppendSpec,
    append_note as _append_note,
)


run_autonomous_self_thought_sidecars = _thought_sidecars.run_autonomous_self_thought_sidecars
append_self_thought_research_notes = _thought_sidecars.append_self_thought_research_notes
append_autonomous_outcome_shadow_notes = _thought_sidecars.append_autonomous_outcome_shadow_notes


__all__ = (
    "run_autonomous_self_thought_sidecars",
    "append_watched_source_note",
    "append_github_learning_note",
    "append_daily_digest_note",
    "append_creative_writing_note",
    "append_review_inbox_note",
    "append_goldmark_dehydrate_note",
    "append_goal_ecology_note",
    "append_self_action_gateway_note",
    "append_self_action_patch_executor_note",
    "append_self_thought_loop_note",
    "append_proactive_request_note",
    "append_self_exploration_note",
    "append_learning_closed_loop_self_thought_note",
    "append_self_thought_research_notes",
    "append_autonomous_outcome_shadow_notes",
    "append_autonomous_outward_note",
    "append_goal_outcome_observer_note",
    "append_proactivity_shadow_note",
    "append_emotion_council_note",
    "append_impulse_soup_note",
    "append_initiative_spine_note",
)
