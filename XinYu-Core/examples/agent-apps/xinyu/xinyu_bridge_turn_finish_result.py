from __future__ import annotations

from typing import Any


def build_slow_turn_finish_sidecars_result(
    *,
    post_reply: Any,
    memory: Any,
    delivery: Any,
    after_memory: dict[str, Any],
) -> dict[str, Any]:
    return {
        "uncertainty_pause": post_reply.uncertainty_pause,
        "post_reply_observation": post_reply.post_reply_observation,
        "learning_closed_loop": post_reply.learning_closed_loop,
        "residue_written": post_reply.residue_written,
        "voice_calibrated": post_reply.voice_calibrated,
        "voice_trial_overlay": post_reply.voice_trial_overlay,
        "curiosity_prediction": post_reply.curiosity_prediction,
        "private_thought_link": post_reply.private_thought_link,
        "archive_result": memory.archive_result,
        "candidate_result": memory.candidate_result,
        "memory_self_review": memory.memory_self_review,
        "interaction_journal": memory.interaction_journal,
        "proactive_owner_reply_marked": delivery.proactive_owner_reply_marked,
        "promised_followup": delivery.promised_followup,
        "sticker_reply": delivery.sticker_reply,
        "sticker_tail_recorded": delivery.sticker_tail_recorded,
        "turn_coherence": delivery.turn_coherence,
        "after_memory": after_memory,
    }
