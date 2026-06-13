from __future__ import annotations

from typing import Any

from xinyu_bridge_values import as_bool, safe_str
from xinyu_prompt_pressure import PromptSidecar


def _sidecar(
    name: str,
    *parts: str,
    required: bool = False,
    admission: str = "support",
) -> PromptSidecar | None:
    candidate = PromptSidecar.from_parts(name, parts, required=required, admission=admission)
    return candidate if candidate.parts else None


def collect_transport_sidecars(metadata: dict[str, Any]) -> list[PromptSidecar]:
    sidecars: list[PromptSidecar] = []

    def add(name: str, *parts: str, required: bool = False, admission: str = "support") -> None:
        candidate = _sidecar(name, *parts, required=required, admission=admission)
        if candidate is not None:
            sidecars.append(candidate)

    if as_bool(metadata.get("attachment_followup_after_ingest"), default=False):
        add(
            "attachment_followup",
            "attachment followup:",
            (
                "The owner just sent a readable attachment. Read the attachment context now. "
                "Respond from your own reading of it in this turn when something is worth saying; "
                "do not use a fixed acknowledgement or report template."
            ),
            admission="current_turn",
        )
    if as_bool(metadata.get("qq_coalesced_owner_messages"), default=False):
        add(
            "qq_fragment_coalescing",
            "qq fragment coalescing sidecar:",
            (
                "The owner sent consecutive QQ fragments that the gateway merged into one turn. "
                f"fragment_count: {safe_str(metadata.get('qq_coalesced_message_count'), '2')}. "
                "Treat the combined user text as one message and answer only once to the overall meaning; "
                "do not answer each line separately."
            ),
            admission="current_turn",
        )
    if as_bool(metadata.get("qq_segmented_intent_gate"), default=False):
        action = safe_str(metadata.get("qq_segmented_intent_action")) or "reply_now"
        notes = metadata.get("qq_segmented_intent_notes")
        note_text = ", ".join(safe_str(item) for item in notes[:6]) if isinstance(notes, list) else "none"
        add(
            "qq_segmented_intent",
            "qq segmented intent sidecar:",
            (
                "The gateway classified the current owner-private QQ turn before generation. "
                f"action: {action}; notes: {note_text}. "
                "Use the combined current text as one intent. If this is a correction, repair the previous miss; "
                "if this is a task instruction, answer the task rather than giving a bare acknowledgement."
            ),
            admission="current_turn",
        )
    if as_bool(metadata.get("qq_gateway_live_current_turn"), default=False):
        add(
            "qq_current_turn_transport",
            "qq current turn transport sidecar:",
            (
                "This message arrived through the live XinYu QQ native gateway. For this turn, treat QQ private "
                "chat connectivity as currently working; older runtime/status text saying QQ is disconnected is stale "
                "unless there is a fresh current-turn send or bridge error."
            ),
            admission="current_turn",
        )
    if as_bool(metadata.get("qq_group_interest_reply"), default=False):
        reason = safe_str(metadata.get("qq_group_interest_reply_reason")) or "group_interest"
        topic = safe_str(metadata.get("qq_group_interest_topic_label")) or "current group topic"
        score = safe_str(metadata.get("qq_group_interest_score")) or "0"
        add(
            "qq_group_interest_reply",
            "qq group interest sidecar:",
            (
                "This is an unmentioned live group message that the gateway allowed because it matched XinYu's "
                f"bounded interest gate. reason: {reason}; topic: {topic}; score: {score}. "
                "Join as a participant, not as a service bot. Keep it short. Ask at most one concrete question "
                "only if there is a real curiosity gap. After the group answers or the point is clear, stop "
                "pushing the topic and let the group continue naturally. Do not mention gates, scores, memory, "
                "or internal trigger logic."
            ),
            admission="current_turn",
        )

    return sidecars
