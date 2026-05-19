from __future__ import annotations

from typing import Any

from xinyu_bridge_payload_policy import owner_private_payload_matches
from xinyu_bridge_state_text import read_text_safe, seconds_since_iso, state_field
from xinyu_bridge_values import safe_str


def proactive_thread_context(runtime: Any, payload: dict[str, Any], current_text: str) -> str:
    if not owner_private_payload_matches(payload):
        return ""
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    desktop_candidate_id = safe_str(metadata.get("desktop_proactive_candidate_id")).strip()
    if desktop_candidate_id:
        request = read_text_safe(runtime.xinyu_dir / "memory/context/proactive_request_state.md")
        request_id = state_field(request, "request_id", "")
        if request_id == desktop_candidate_id:
            candidate = state_field(request, "concrete_question", "") or safe_str(
                metadata.get("desktop_proactive_preview")
            )
            return "\n".join(
                [
                    "desktop proactive reply sidecar:",
                    f"- proactive_candidate_id: {desktop_candidate_id}",
                    f"- proactive_kind: {state_field(request, 'kind', 'proactive')}",
                    f"- proactive_status: {state_field(request, 'status', 'unknown')}",
                    f"- proactive_delivery_level: {state_field(request, 'delivery_level', 'unknown')}",
                    f"- proactive_candidate_message: {candidate}",
                    f"- current_owner_reply_to_candidate: {safe_str(current_text).strip()}",
                    (
                        "- continuity_rule: treat the current owner message as an explicit reply to this "
                        "desktop proactive candidate. Answer from that local thread instead of treating it "
                        "as unrelated chat."
                    ),
                ]
            )
    dispatch = read_text_safe(runtime.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
    if state_field(dispatch, "last_claim_status") not in {"claimed", "sent"}:
        return ""
    request = read_text_safe(runtime.xinyu_dir / "memory/context/proactive_request_state.md")
    request_id = state_field(request, "request_id")
    dispatch_request_id = state_field(dispatch, "proactive_request_id")
    if request_id not in {"", "none", "unknown"} and dispatch_request_id not in {"", "none", "unknown"}:
        if request_id != dispatch_request_id:
            return ""
    if state_field(request, "delivery_level") not in {"queue_owner_private", "claim_ack"}:
        return ""
    if state_field(request, "status") not in {"claimed", "sent", "answered"}:
        return ""
    message = state_field(dispatch, "last_claimed_message")
    if not message or message in {"none", "unknown"}:
        return ""
    age_seconds = seconds_since_iso(state_field(dispatch, "last_claimed_at"), default=999999.0)
    if age_seconds > 6 * 3600:
        return ""
    kind = state_field(request, "kind", "proactive")
    answer_state = state_field(request, "request_answer_state", "pending")
    extra_rules: list[str] = []
    evidence_label = state_field(request, "evidence_label", "")
    if kind == "reflection_share" and "Codex" in evidence_label:
        runtime_presence = read_text_safe(runtime.xinyu_dir / "memory/context/runtime_self_presence.md")
        codex_status = state_field(runtime_presence, "codex_status", "unknown").lower()
        codex_timed_out = state_field(runtime_presence, "codex_timed_out", "false").lower() == "true"
        if codex_status in {"", "unknown", "none"} and not codex_timed_out:
            extra_rules.append(
                "- reflection_share_rule: this proactive line came from an old reflection queue item, "
                "not from a currently running or currently timed-out Codex job. If the owner is confused, "
                "say that directly and do not repeat the decision request."
            )
    return "\n".join(
        [
            "proactive thread sidecar:",
            f"- last_xinyu_proactive_message: {message}",
            f"- proactive_kind: {kind}",
            f"- request_answer_state_before_this_turn: {answer_state}",
            f"- current_owner_message: {safe_str(current_text).strip()}",
            (
                "- continuity_rule: treat the owner message as a likely reply to XinYu's proactive message. "
                "Continue from that concrete thread; do not ask what to talk about when the owner is already "
                "commenting on the proactive message."
            ),
            (
                "- dream_share_rule: if proactive_kind is dream_share and the owner says dreams are illogical, "
                "strange, or asks what XinYu means, answer from XinYu's own dream context instead of asking the "
                "owner to explain the dream."
            ),
            *extra_rules,
        ]
    )
