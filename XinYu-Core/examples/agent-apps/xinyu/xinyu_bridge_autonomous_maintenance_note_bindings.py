from __future__ import annotations

from functools import wraps
from typing import Any, Callable


NoteDepsFunc = Callable[[], Any]


_DEPS_FORWARDERS = (
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
    "append_autonomous_outward_note",
    "append_goal_outcome_observer_note",
    "append_proactivity_shadow_note",
    "append_emotion_council_note",
    "append_impulse_soup_note",
    "append_initiative_spine_note",
)

_DIRECT_FORWARDERS = (
    "append_self_thought_research_notes",
    "append_desktop_proactive_candidate_ready_note",
    "append_autonomous_outcome_shadow_notes",
    "run_autonomous_self_thought_sidecars",
)

NOTE_BINDING_NAMES = _DEPS_FORWARDERS + _DIRECT_FORWARDERS


def _named_forwarder(module_name: str, name: str, target: Callable[..., Any], func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(target)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    wrapper.__module__ = module_name
    wrapper.__name__ = name
    wrapper.__qualname__ = name
    return wrapper


def bind_note_wrappers(
    namespace: dict[str, Any],
    *,
    module_name: str,
    note_deps_func: NoteDepsFunc,
    facade: Any,
) -> None:
    for name in _DEPS_FORWARDERS:
        target = getattr(facade, name)

        def forward(*args: Any, _target: Callable[..., Any] = target, **kwargs: Any) -> Any:
            return _target(note_deps_func(), *args, **kwargs)

        namespace[name] = _named_forwarder(module_name, name, target, forward)

    for name in _DIRECT_FORWARDERS:
        target = getattr(facade, name)

        def forward(*args: Any, _target: Callable[..., Any] = target, **kwargs: Any) -> Any:
            return _target(*args, **kwargs)

        namespace[name] = _named_forwarder(module_name, name, target, forward)
