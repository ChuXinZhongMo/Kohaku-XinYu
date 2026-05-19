from __future__ import annotations

import hashlib
import time
from typing import Any, Callable

from kernel import decide
from schemas import normalize_emotion_bias


EmotionFn = Callable[[dict[str, Any]], dict[str, Any] | None]
PersonaFn = Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any] | None]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _heuristic_emotion_biases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    text = _safe_text(payload.get("user_text"))
    candidates: list[dict[str, Any]] = []
    if any(marker in text for marker in ("别", "不要", "不用", "算了", "停", "边界", "隐私")):
        candidates.append(
            {
                "lens": "guardedness",
                "activation": 0.66,
                "reply_bias": "短一点，不追问，不重复旧话题，尊重当前边界。",
                "risk_flags": ["no_proactive_followup", "do_not_repeat", "respect_boundary"],
                "confidence": 0.78,
            }
        )
    if any(marker.lower() in text.lower() for marker in ("idea", "想法", "路线", "架构", "论文", "研究", "可行", "为什么", "怎么", "分析", "实验")):
        candidates.append(
            {
                "lens": "curiosity",
                "activation": 0.66,
                "reply_bias": "探索可行性，点出小实验，不急着接管实现。",
                "risk_flags": ["name_small_experiment", "avoid_unasked_implementation", "keep_question_concrete"],
                "confidence": 0.78,
            }
        )
    return [item for item in (normalize_emotion_bias(candidate) for candidate in candidates) if item is not None]


def _fallback_persona(payload: dict[str, Any], emotion_biases: list[dict[str, Any]]) -> dict[str, Any]:
    base = decide(payload)
    reply = _safe_text(base.get("reply"))
    if not reply:
        if emotion_biases:
            strongest = max(emotion_biases, key=lambda item: float(item.get("activation", 0.0)))
            if strongest.get("lens") == "guardedness":
                reply = "好，我先收住，不往下追。"
            elif strongest.get("lens") == "curiosity":
                reply = "可行，先做一个小实验验证这条链路。"
        reply = reply or "我先按最小可验证路线推进。"
    return {"reply": reply[:240], "confidence": 0.62, "notes": ["compose_fallback_persona"]}


def compose_shadow(
    payload: dict[str, Any],
    *,
    emotion_fns: list[EmotionFn] | None = None,
    persona_fn: PersonaFn | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    text = _safe_text(payload.get("user_text"))
    raw_biases: list[dict[str, Any]] = []
    notes = ["compose_shadow", "shadow_only"]

    if emotion_fns is not None:
        for emotion_fn in emotion_fns:
            try:
                candidate = emotion_fn(payload)
            except Exception as exc:
                notes.append(f"emotion_error:{type(exc).__name__}")
                continue
            normalized = normalize_emotion_bias(candidate or {})
            if normalized is None:
                notes.append("emotion_bias_invalid")
                continue
            raw_biases.append(normalized)
    else:
        raw_biases.extend(_heuristic_emotion_biases(payload))
        notes.append("heuristic_emotion_biases")

    emotion_biases = sorted(raw_biases, key=lambda item: float(item.get("activation", 0.0)), reverse=True)[:4]
    try:
        persona = persona_fn(payload, emotion_biases) if persona_fn else _fallback_persona(payload, emotion_biases)
    except Exception as exc:
        persona = _fallback_persona(payload, emotion_biases)
        notes.append(f"persona_error:{type(exc).__name__}")

    reply = _safe_text((persona or {}).get("reply"))
    confidence = float((persona or {}).get("confidence") or 0.5)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "event_kind": "tinykernel_compose_shadow",
        "ok": bool(reply),
        "shadow_only": True,
        "turn_id": _safe_text(payload.get("turn_id")),
        "request_hash": text_hash(text),
        "request_chars": len(text),
        "mode": "reply",
        "reply_candidate": reply[:240],
        "emotion_biases": emotion_biases,
        "selected_bias": emotion_biases[0] if emotion_biases else {},
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "elapsed_ms": elapsed_ms,
        "notes": notes + list((persona or {}).get("notes") or []),
    }
