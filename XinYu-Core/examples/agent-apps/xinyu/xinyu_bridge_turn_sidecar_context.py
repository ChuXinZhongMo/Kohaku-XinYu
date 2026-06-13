from __future__ import annotations

from typing import Any

from xinyu_bridge_turn_sidecar_state import TurnSidecarBlocks
from xinyu_bridge_values import as_bool, as_int
from xinyu_owner_active_corrections import build_owner_active_corrections_block


def _current_image_context_unavailable(payload: dict[str, Any]) -> bool:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return False
    if as_int(metadata.get("qq_image_count"), 0) <= 0:
        return False
    return not as_bool(metadata.get("qq_image_context_available"), default=False)


def collect_context_sidecars(
    deps: Any,
    add_sidecar: Any,
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    turn_id: str,
    dialogue_tail: list[dict[str, str]],
    live_state: Any,
    blocks: TurnSidecarBlocks,
    persona_context: str,
    curiosity_context: str,
    recalled_context: str,
    runtime_presence_context: str,
    continuity_context: str,
    uncertainty_pause_context: str,
    life_reply_context: str,
    emotion_council_context: str,
) -> None:
    current_visible_turn = live_state.visible_turn
    safe_str = deps.safe_str

    persona_block = safe_str(persona_context).strip()
    if persona_block:
        add_sidecar("persona", "persona sidecar:", persona_block[:1200], admission="support")

    curiosity_block = safe_str(curiosity_context).strip()
    if curiosity_block:
        add_sidecar("curiosity", "curiosity sidecar:", curiosity_block[:1200], admission="support")

    emotion_council_block = safe_str(emotion_council_context).strip()
    if emotion_council_block:
        add_sidecar("emotion_council", emotion_council_block[:1200], admission="support")

    life_reply_block = safe_str(life_reply_context).strip()
    if life_reply_block:
        add_sidecar("life_reply", life_reply_block, admission="support")

    if blocks.recent_action:
        add_sidecar("recent_action", blocks.recent_action, admission="episodic")
    if blocks.action_digest:
        add_sidecar("action_digest", blocks.action_digest, admission="episodic")
    if blocks.action_feedback:
        add_sidecar("action_feedback", blocks.action_feedback, admission="episodic")

    owner_continuity_hint = deps.build_owner_context_hint(
        runtime.xinyu_dir,
        user_text=text,
        dialogue_tail=dialogue_tail,
    )
    if live_state.is_owner and owner_continuity_hint:
        add_sidecar("owner_continuity_hint", owner_continuity_hint, admission="current_turn")

    recalled_block = safe_str(recalled_context).strip()
    if recalled_block:
        add_sidecar("recalled_context", "recalled context sidecar:", recalled_block, admission="core")

    voice_trial_block = deps.build_voice_trial_overlay_prompt_block(runtime.xinyu_dir, payload, user_text=text)
    if voice_trial_block:
        add_sidecar("voice_trial_overlay", voice_trial_block, admission="support")

    dialogue_rule_trial_block = deps.build_dialogue_rule_trial_overlay_prompt_block(
        runtime.xinyu_dir,
        payload,
        user_text=text,
    )
    if dialogue_rule_trial_block:
        add_sidecar("dialogue_rule_trial_overlay", dialogue_rule_trial_block, admission="support")

    if live_state.is_owner:
        owner_corrections_block = build_owner_active_corrections_block(
            runtime.xinyu_dir,
            dialogue_tail=dialogue_tail,
            latest_user_text=text,
        )
        if owner_corrections_block:
            add_sidecar("owner_active_corrections", owner_corrections_block, admission="current_turn")

    learning_loop_block = deps.build_learning_closed_loop_prompt_block(runtime.xinyu_dir, user_text=text)
    if learning_loop_block:
        add_sidecar("learning_closed_loop", learning_loop_block, admission="repair")

    conversation_experience_block = deps.build_conversation_experience_prompt_block(
        runtime.xinyu_dir,
        payload,
        user_text=text,
        dialogue_tail=dialogue_tail,
        visible_turn=current_visible_turn,
        turn_id=turn_id,
    )
    if conversation_experience_block:
        add_sidecar(
            "conversation_experience_hint",
            conversation_experience_block,
            admission="conversation_experience",
        )

    proactive_block = runtime._proactive_thread_context(payload, text)
    if proactive_block:
        add_sidecar("proactive_thread", proactive_block, admission="proactive_reply")

    daily_digest_block = deps.build_daily_digest_prompt_block(runtime.xinyu_dir)
    if daily_digest_block:
        add_sidecar("daily_digest", daily_digest_block, admission="digest")

    goldmark_block = deps.build_goldmark_auth_prompt_block(runtime.xinyu_dir)
    if goldmark_block:
        add_sidecar("goldmark_auth", goldmark_block, admission="background")

    qq_rich_block = runtime._qq_rich_message_sidecar(payload)
    if qq_rich_block:
        add_sidecar("qq_rich_message", "qq rich message sidecar:", qq_rich_block, admission="current_turn")

    attachment_block = ""
    if not _current_image_context_unavailable(payload):
        attachment_block = deps.load_recent_attachment_context(runtime.xinyu_dir, runtime._session_key(payload), text)
    if attachment_block:
        add_sidecar("recent_attachment", "recent attachment sidecar:", attachment_block, admission="current_turn")

    runtime_presence_block = safe_str(runtime_presence_context).strip()
    if runtime_presence_block:
        add_sidecar("runtime_presence", "runtime presence sidecar:", runtime_presence_block[:2200], admission="status")

    continuity_block = safe_str(continuity_context).strip()
    if continuity_block:
        add_sidecar("continuity_handoff", continuity_block, admission="continuity")

    uncertainty_block = safe_str(uncertainty_pause_context).strip()
    if uncertainty_block:
        add_sidecar("uncertainty_pause", uncertainty_block, admission="current_turn")

    if live_state.is_owner and runtime._looks_like_time_fact_correction(text):
        today = deps.datetime.now().astimezone().date().isoformat()
        add_sidecar(
            "factual_time_correction",
            "factual/time correction sidecar:",
            (
                f"current_runtime_date: {today}. The owner is correcting a concrete "
                "time/date/holiday fact from XinYu's previous reply. Treat the owner "
                "correction and current runtime date as authoritative over stale memory, "
                "mood residue, or old time-anchor wording. Continue the chat from the "
                "corrected fact in one ordinary line; do not use apology/report wording "
                "such as 我算错了 / 刚才那句说岔了 / 别理 / 抱歉 / 不好意思 / 我会改."
            ),
            admission="current_turn",
        )
