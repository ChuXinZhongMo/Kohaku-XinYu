from __future__ import annotations

import re
from typing import Any


TECHNICAL_RE = re.compile(
    r"(代码|日志|报错|错误|异常|启动|运行|测试|构建|修|改|实现|文件|接口|端口|token|"
    r"websocket|napcat|core|bridge|codex|python|typescript|react|css|npm|pytest|error|traceback)",
    re.IGNORECASE,
)

QUESTION_TAIL_RE = re.compile(
    r"(。?\s*(要不要|需不需要|你要是想|如果你想|要我|我可以继续|需要的话).{0,42}[？?]\s*)$"
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _band_value(value: str, mapping: dict[str, float], default: float = 0.0) -> float:
    return mapping.get(_safe_str(value).strip().lower(), default)


def _is_technical_turn(user_text: str) -> bool:
    return bool(TECHNICAL_RE.search(user_text or ""))


def build_life_reply_policy(
    *,
    self_choice_public: dict[str, Any] | None = None,
    entropy_state: dict[str, Any] | None = None,
    recent_action_context: str = "",
    user_text: str = "",
    scene_frame: Any | None = None,
) -> dict[str, Any]:
    self_choice = _as_dict(self_choice_public)
    entropy = _as_dict(entropy_state)
    scene_reply_policy = _scene_frame_value(scene_frame, "reply_policy")
    scene_task_mode = _scene_frame_value(scene_frame, "task_mode")
    scene_time_context = _scene_frame_value(scene_frame, "time_context")
    scene_owner_state = _scene_frame_value(scene_frame, "owner_state")
    scene_memory_relation = _scene_frame_value(scene_frame, "memory_relation")
    affect = _as_dict(self_choice.get("affect_band"))
    fatigue_band = _safe_str(affect.get("fatigue"), "clear")
    closure_band = _safe_str(affect.get("closure"), "guarded")
    urge_band = _safe_str(affect.get("urge"), "warm")
    fatigue = _band_value(fatigue_band, {"clear": 0.1, "tired": 0.68, "heavy": 0.82, "spent": 0.92})
    closure = _band_value(closure_band, {"open": 0.1, "guarded": 0.38, "withdrawn": 0.78})
    entropy_level = _coerce_float(entropy.get("entropy_level"), 0.0)
    entropy_band = _safe_str(entropy.get("entropy_band"), "clear")
    cues = [_safe_str(item) for item in _as_list(self_choice.get("physical_cues")) if _safe_str(item)]
    technical = _is_technical_turn(user_text) or scene_task_mode == "technical_execution"

    reasons: list[str] = []
    if fatigue >= 0.65:
        reasons.append(f"fatigue={fatigue_band}")
    if closure >= 0.7:
        reasons.append(f"closure={closure_band}")
    if entropy_level >= 0.66 or entropy_band in {"fracture", "terminal"}:
        reasons.append(f"entropy={entropy_band}:{entropy_level:.2f}")
    if recent_action_context:
        reasons.append("recent_action_residue")
    if cues:
        reasons.append("cue=" + cues[0])
    if scene_reply_policy:
        reasons.append(f"scene_frame={scene_reply_policy}")
    if scene_memory_relation == "time_bound_recall":
        reasons.append("scene_memory_relation=time_bound_recall")

    mode = "steady"
    max_sentences = 4 if technical else 3
    suppress_optional_question = False
    reply_pressure = "normal"

    if entropy_level >= 0.78 or entropy_band == "terminal":
        mode = "overloaded"
        reply_pressure = "compressed"
        max_sentences = 5 if technical else 2
        suppress_optional_question = True
    elif fatigue >= 0.65 or closure >= 0.7:
        mode = "low_energy"
        reply_pressure = "short"
        max_sentences = 5 if technical else 2
        suppress_optional_question = True
    elif recent_action_context:
        mode = "residue_aware"
        reply_pressure = "grounded"
        max_sentences = 5 if technical else 3

    if scene_reply_policy in {"short_direct_low_burden", "short_gentle_low_burden", "warm_low_burden"}:
        mode = "low_energy"
        reply_pressure = "short"
        max_sentences = min(max_sentences, 4 if technical else 2)
        suppress_optional_question = True
    elif scene_reply_policy == "compact_structured_answer":
        if mode == "steady":
            mode = "scene_structured"
        if reply_pressure == "normal":
            reply_pressure = "structured"
        max_sentences = min(max_sentences, 4 if technical else 3)
    elif scene_reply_policy == "warm_boundary_aware":
        if mode == "steady":
            mode = "relation_aware"
        if reply_pressure == "normal":
            reply_pressure = "warm_boundaried"
        max_sentences = min(max_sentences, 3)

    return {
        "version": 1,
        "mode": mode,
        "reply_pressure": reply_pressure,
        "technical_turn": technical,
        "max_sentences": max_sentences,
        "suppress_optional_question": suppress_optional_question,
        "fatigue_band": fatigue_band,
        "closure_band": closure_band,
        "urge_band": urge_band,
        "entropy_band": entropy_band,
        "entropy_level": round(entropy_level, 3),
        "reasons": reasons,
        "scene_frame": {
            "reply_policy": scene_reply_policy,
            "task_mode": scene_task_mode,
            "time_context": scene_time_context,
            "owner_state": scene_owner_state,
            "memory_relation": scene_memory_relation,
        },
        "notes": ["life_reply_policy_v1"],
    }


def build_life_reply_prompt_block(policy: dict[str, Any] | None) -> str:
    policy = _as_dict(policy)
    if not policy:
        return ""
    reasons = ", ".join(_safe_str(item) for item in _as_list(policy.get("reasons")) if _safe_str(item)) or "none"
    suppress = "yes" if bool(policy.get("suppress_optional_question")) else "no"
    scene = _as_dict(policy.get("scene_frame"))
    scene_reply_policy = _safe_str(scene.get("reply_policy"), "none") or "none"
    scene_time_context = _safe_str(scene.get("time_context"), "none") or "none"
    scene_memory_relation = _safe_str(scene.get("memory_relation"), "none") or "none"
    return "\n".join(
        [
            "life reply policy sidecar:",
            f"- mode: {_safe_str(policy.get('mode'), 'steady')}",
            f"- reply_pressure: {_safe_str(policy.get('reply_pressure'), 'normal')}",
            f"- technical_turn: {bool(policy.get('technical_turn'))}",
            f"- max_sentences: {_safe_str(policy.get('max_sentences'), '3')}",
            f"- suppress_optional_question: {suppress}",
            f"- scene_reply_policy: {scene_reply_policy}",
            f"- scene_time_context: {scene_time_context}",
            f"- scene_memory_relation: {scene_memory_relation}",
            f"- reasons: {reasons}",
            (
                "- behavior: let these internal conditions affect pacing and initiative. "
                "If pressure is short/compressed, answer in fewer sentences and avoid adding a new optional question. "
                "For technical turns, keep necessary facts but remove filler. Do not mention these labels unless the owner asks about the system."
            ),
        ]
    )


def apply_life_reply_policy(
    reply: str,
    *,
    policy: dict[str, Any] | None = None,
    user_text: str = "",
) -> dict[str, Any]:
    text = _safe_str(reply).strip()
    policy = _as_dict(policy)
    notes: list[str] = []
    if not text or not policy:
        return {"reply": text, "changed": False, "notes": notes}

    suppress_question = bool(policy.get("suppress_optional_question"))
    technical = bool(policy.get("technical_turn")) or _is_technical_turn(user_text)
    max_sentences = int(policy.get("max_sentences") or (5 if technical else 3))
    mode = _safe_str(policy.get("mode"), "steady")
    next_text = text

    if suppress_question:
        stripped = QUESTION_TAIL_RE.sub("", next_text).strip()
        if stripped and stripped != next_text:
            next_text = stripped
            notes.append("life_reply_optional_question_removed")

    if not technical and mode in {"low_energy", "overloaded"}:
        compact = _limit_sentences(next_text, max_sentences=max_sentences)
        if compact and compact != next_text:
            next_text = compact
            notes.append(f"life_reply_shortened:{mode}")

    return {"reply": next_text, "changed": next_text != text, "notes": notes}


def _limit_sentences(text: str, *, max_sentences: int) -> str:
    parts = _split_sentences(text)
    if len(parts) <= max_sentences:
        return text
    return "".join(parts[:max_sentences]).strip()


def _split_sentences(text: str) -> list[str]:
    pieces = re.findall(r".+?(?:[。！？!?]+|$)", text, flags=re.S)
    return [piece.strip() for piece in pieces if piece.strip()]


def _coerce_float(value: Any, default: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result < 0.0:
        return 0.0
    if result > 1.0:
        return 1.0
    return result


def _scene_frame_value(scene_frame: Any | None, key: str) -> str:
    if scene_frame is None:
        return ""
    if isinstance(scene_frame, dict):
        return _safe_str(scene_frame.get(key)).strip()
    return _safe_str(getattr(scene_frame, key, "")).strip()
