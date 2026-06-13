from __future__ import annotations

from collections.abc import Callable
from typing import Any

import v1_canary_gate
from xinyu_bridge_semantic_fast_payloads import safe_str
from xinyu_human_voice_flags import bypass_model_enabled
from xinyu_bridge_semantic_fast_text import (
    SEMANTIC_FAST_ALLOWED_INTENTS,
    _OWNER_STATE_FAST_MAX_CHARS,
    _direct_greeting_ack_reply,
    _looks_like_owner_state_question,
    _repair_intents_for_text,
    owner_private_direct_repair_reply_impl,
)


def ensure_v1_app(runtime: Any) -> Any:
    if runtime._v1_app is not None:
        return runtime._v1_app
    from xinyu_v1.app import XinYuV1App
    from xinyu_v1.config import XinYuV1Config

    runtime._v1_app = XinYuV1App(XinYuV1Config.load(runtime.xinyu_dir))
    return runtime._v1_app


def _demote_direct_reply_if_bypass(decision: dict[str, Any], canned_id: str) -> dict[str, Any]:
    """When the bypass-model flag is on, move a canned ``direct_reply`` into
    ``canned_fallback`` so the renderer renders through the model first and only
    uses the constant if the model yields nothing (plan 11.5).

    With the flag off the decision is returned untouched (byte-identical).
    """

    reply = decision.get("direct_reply") or ""
    if not reply or not bypass_model_enabled():
        return decision
    decision["direct_reply"] = ""
    decision["canned_fallback"] = reply
    decision["canned_fallback_id"] = canned_id
    decision["notes"] = list(decision.get("notes", [])) + [f"direct_reply_demoted_to_model:{canned_id}"]
    return decision


def owner_private_semantic_fast_decision_impl(
    runtime: Any,
    payload: dict[str, Any],
    text: str,
    *,
    ensure_v1_app_func: Callable[[Any], Any] = ensure_v1_app,
    attachment_signal_func: Callable[[dict[str, Any]], bool] = v1_canary_gate.payload_has_attachment_signal,
    safe_str_func: Callable[..., str] = safe_str,
    repair_intents_func: Callable[[str], tuple[str, ...]] = _repair_intents_for_text,
    direct_repair_reply_func: Callable[..., str] = owner_private_direct_repair_reply_impl,
    looks_like_owner_state_question_func: Callable[[str], bool] = _looks_like_owner_state_question,
    direct_greeting_ack_reply_func: Callable[[str, tuple[str, ...]], str] = _direct_greeting_ack_reply,
    allowed_intents: frozenset[str] = SEMANTIC_FAST_ALLOWED_INTENTS,
    owner_state_fast_max_chars: int = _OWNER_STATE_FAST_MAX_CHARS,
) -> dict[str, Any]:
    if not getattr(runtime, "owner_private_semantic_fast_route", True):
        return {"allowed": False, "notes": ["owner_private_semantic_fast_route_disabled"]}
    if not runtime._owner_private_payload_matches(payload):
        return {"allowed": False, "notes": ["not_owner_private"]}
    if attachment_signal_func(payload):
        return {"allowed": False, "notes": ["attachment_present"]}
    raw_text = safe_str_func(text)
    compact = "".join(raw_text.split())
    if not compact:
        return {"allowed": False, "notes": ["empty_text"]}
    if "\n" in raw_text or "\r" in raw_text:
        return {"allowed": False, "notes": ["multiline_text"]}

    repair_intents = repair_intents_func(raw_text)
    if "reply_quality_complaint" in repair_intents:
        return {
            "allowed": False,
            "intents": repair_intents,
            "notes": [
                "reply_quality_complaint_needs_live_model",
                "semantic_fast_not_low_risk",
                f"semantic_fast_intents:{','.join(repair_intents)}",
            ],
        }
    if repair_intents and len(compact) <= 64:
        reply = direct_repair_reply_func(runtime, raw_text, repair_intents)
        decision = {
            "allowed": True,
            "route": "fast_path",
            "intents": repair_intents,
            "reasons": ("owner_private_live_repair",),
            "direct_reply": reply,
            "notes": ["semantic_fast_allowed", f"semantic_fast_intents:{','.join(repair_intents)}"],
        }
        # plan 11.5: feature on => decision must not emit final text; demote the
        # canned repair line to a fallback so the renderer goes through the model
        # first and only falls back to the constant on failure.
        return _demote_direct_reply_if_bypass(decision, "canned_repair")
    if looks_like_owner_state_question_func(raw_text):
        if len(compact) <= owner_state_fast_max_chars:
            return {
                "allowed": True,
                "route": "fast_path",
                "intents": ("owner_state_question",),
                "reasons": ("owner_private_state_question_live_renderer",),
                "direct_reply": "",
                "notes": [
                    "semantic_fast_allowed",
                    "semantic_fast_intents:owner_state_question",
                    "owner_state_question_live_renderer_required",
                ],
            }
        return {
            "allowed": False,
            "notes": ["owner_state_question_needs_live_model", "semantic_fast_not_low_risk"],
        }
    if len(compact) > 20:
        return {"allowed": False, "notes": ["text_too_long_for_semantic_fast_route"]}

    app = ensure_v1_app_func(runtime)
    v1_payload = dict(payload)
    v1_payload.setdefault("text", text)
    metadata = v1_payload.get("metadata")
    v1_payload["metadata"] = dict(metadata) if isinstance(metadata, dict) else {}
    v1_payload["metadata"]["is_owner_user"] = True
    v1_payload["metadata"]["v1_semantic_fast_source"] = "xinyu_core_bridge"
    turn = app.normalizer.normalize(v1_payload)
    decision = app.router.decide(turn)
    classification = decision.classification
    route = safe_str_func(getattr(decision.route, "value", decision.route))
    intents = tuple(safe_str_func(intent) for intent in classification.intents)
    intent_set = {intent for intent in intents if intent}
    if (
        route == "fast_path"
        and intent_set
        and intent_set.issubset(allowed_intents)
        and not classification.needs_model
        and not classification.needs_memory
    ):
        notes = ["semantic_fast_allowed", f"semantic_fast_intents:{','.join(intents)}"]
        if "greeting" in intent_set:
            reply = ""
            notes.append("owner_greeting_live_renderer_required")
        elif "ack" in intent_set:
            reply = ""
            notes.append("owner_ack_live_renderer_required")
        else:
            reply = direct_greeting_ack_reply_func(raw_text, intents)
        fast_decision = {
            "allowed": True,
            "route": route,
            "intents": intents,
            "reasons": tuple(safe_str_func(reason) for reason in decision.reasons),
            "direct_reply": reply,
            "notes": notes,
        }
        return _demote_direct_reply_if_bypass(fast_decision, "canned_greeting_ack")
    return {
        "allowed": False,
        "route": route,
        "intents": intents,
        "reasons": tuple(safe_str_func(reason) for reason in decision.reasons),
        "notes": ["semantic_fast_not_low_risk", f"semantic_fast_intents:{','.join(intents) or 'none'}"],
    }
