from __future__ import annotations

from typing import Any, Awaitable, Callable, NamedTuple


class TurnFinishServiceDeps(NamedTuple):
    record_uncertainty_pause: Callable[..., dict[str, Any]]
    observe_post_reply_self_observation: Callable[..., dict[str, Any]]
    record_learning_closed_loop: Callable[..., dict[str, Any]]
    write_turn_residue: Callable[..., bool]
    record_owner_voice_sidecars: Callable[..., tuple[dict[str, Any], bool]]
    record_curiosity_prediction: Callable[..., dict[str, Any]]
    record_private_thought_link: Callable[..., dict[str, Any]]
    archive_dialogue_turn: Callable[..., dict[str, Any]]
    log_living_memory_recall: Callable[..., bool]
    extract_memory_candidates: Callable[..., dict[str, Any]]
    run_memory_self_review: Callable[..., dict[str, Any]]
    record_interaction_journal: Callable[..., dict[str, Any]]
    schedule_promised_followup: Callable[..., dict[str, Any]]
    maybe_enqueue_sticker_reply: Callable[..., Awaitable[dict[str, Any]]]
    turn_action_result: Callable[..., str]
    finish_turn_coherence: Callable[..., dict[str, Any]]
    memory_snapshot: Callable[..., dict[str, Any]]
