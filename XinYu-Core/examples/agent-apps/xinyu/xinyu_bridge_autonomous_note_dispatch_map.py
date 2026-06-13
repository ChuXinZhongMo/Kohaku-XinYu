from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import xinyu_bridge_autonomous_action_sidecars as _action_sidecars
import xinyu_bridge_autonomous_intake_sidecars as _intake_sidecars
import xinyu_bridge_autonomous_shadow_sidecars as _shadow_sidecars
import xinyu_bridge_autonomous_thought_sidecars as _thought_sidecars


DepBindings = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class NoteAppendSpec:
    func: Callable[..., Any]
    deps: DepBindings

    def append(
        self,
        deps: Any,
        runtime: Any,
        notes: list[str],
        *,
        checked_at: str,
        **kwargs: Any,
    ) -> Any:
        injected = {kwarg: getattr(deps, attr) for kwarg, attr in self.deps}
        injected.update(kwargs)
        return self.func(runtime, notes, checked_at=checked_at, **injected)


NOTE_APPENDERS: dict[str, NoteAppendSpec] = {
    "watched_source": NoteAppendSpec(
        _intake_sidecars.append_watched_source_note,
        (("run_watched_source_check_func", "run_watched_source_check"),),
    ),
    "github_learning": NoteAppendSpec(
        _intake_sidecars.append_github_learning_note,
        (
            ("sys_module", "sys"),
            ("load_run_github_autonomous_learning_func", "_load_run_github_autonomous_learning"),
        ),
    ),
    "daily_digest": NoteAppendSpec(
        _intake_sidecars.append_daily_digest_note,
        (("run_daily_digest_maintenance_func", "run_daily_digest_maintenance"),),
    ),
    "creative_writing": NoteAppendSpec(
        _intake_sidecars.append_creative_writing_note,
        (("run_creative_writing_maintenance_func", "run_creative_writing_maintenance"),),
    ),
    "review_inbox": NoteAppendSpec(
        _intake_sidecars.append_review_inbox_note,
        (("run_review_inbox_maintenance_func", "run_review_inbox_maintenance"),),
    ),
    "goldmark_dehydrate": NoteAppendSpec(
        _intake_sidecars.append_goldmark_dehydrate_note,
        (("run_goldmark_dehydration_maintenance_func", "run_goldmark_dehydration_maintenance"),),
    ),
    "goal_ecology": NoteAppendSpec(
        _action_sidecars.append_goal_ecology_note,
        (("run_self_chosen_goal_ecology_func", "_run_self_chosen_goal_ecology"),),
    ),
    "self_action_gateway": NoteAppendSpec(
        _action_sidecars.append_self_action_gateway_note,
        (("run_self_action_gateway_func", "_run_self_action_gateway"),),
    ),
    "self_action_patch_executor": NoteAppendSpec(
        _action_sidecars.append_self_action_patch_executor_note,
        (("run_self_action_patch_executor_func", "_run_self_action_patch_executor"),),
    ),
    "self_thought_loop": NoteAppendSpec(
        _thought_sidecars.append_self_thought_loop_note,
        (("run_self_thought_loop_func", "run_self_thought_loop"),),
    ),
    "proactive_request": NoteAppendSpec(
        _thought_sidecars.append_proactive_request_note,
        (("run_proactive_request_loop_func", "run_proactive_request_loop"),),
    ),
    "self_exploration": NoteAppendSpec(
        _thought_sidecars.append_self_exploration_note,
        (("run_autonomous_self_exploration_tick_func", "run_autonomous_self_exploration_tick"),),
    ),
    "learning_closed_loop_self_thought": NoteAppendSpec(
        _thought_sidecars.append_learning_closed_loop_self_thought_note,
        (
            ("timestamp_or_now_iso_func", "timestamp_or_now_iso"),
            ("record_learning_closed_loop_self_thought_func", "record_learning_closed_loop_self_thought"),
        ),
    ),
    "autonomous_outward": NoteAppendSpec(
        _thought_sidecars.append_autonomous_outward_note,
        (("run_autonomous_outward_action_tick_func", "run_autonomous_outward_action_tick"),),
    ),
    "goal_outcome_observer": NoteAppendSpec(
        _shadow_sidecars.append_goal_outcome_observer_note,
        (("run_goal_outcome_observer_func", "run_goal_outcome_observer"),),
    ),
    "proactivity_shadow": NoteAppendSpec(
        _shadow_sidecars.append_proactivity_shadow_note,
        (
            ("run_proactivity_scorer_shadow_func", "run_proactivity_scorer_shadow"),
            ("run_initiative_orchestrator_func", "run_initiative_orchestrator"),
        ),
    ),
    "emotion_council": NoteAppendSpec(
        _shadow_sidecars.append_emotion_council_note,
        (("run_emotion_council_shadow_func", "run_emotion_council_shadow"),),
    ),
    "impulse_soup": NoteAppendSpec(
        _shadow_sidecars.append_impulse_soup_note,
        (("run_impulse_soup_func", "run_impulse_soup"),),
    ),
    "initiative_spine": NoteAppendSpec(
        _shadow_sidecars.append_initiative_spine_note,
        (
            ("run_initiative_spine_func", "run_initiative_spine"),
            ("run_desire_drive_state_func", "run_desire_drive_state"),
            ("run_contextual_self_observatory_func", "run_contextual_self_observatory"),
            ("timestamp_or_now_iso_func", "timestamp_or_now_iso"),
        ),
    ),
}


def append_note(
    name: str,
    deps: Any,
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    **kwargs: Any,
) -> Any:
    return NOTE_APPENDERS[name].append(deps, runtime, notes, checked_at=checked_at, **kwargs)
