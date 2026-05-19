from __future__ import annotations

import time
import uuid
from typing import Any


VALID_MODES = {
    "reply",
    "clarify",
    "wait",
    "codex_delegate",
    "status_probe",
    "memory_candidate",
    "local_only_limitation",
}

VALID_EMOTION_LENSES = {
    "attachment",
    "curiosity",
    "fatigue",
    "guardedness",
    "hurt",
    "irritation",
    "stability",
    "warmth",
}

VALID_EMOTION_BIAS_KEYS = {"lens", "activation", "reply_bias", "risk_flags", "confidence", "evidence"}


def new_decision_id() -> str:
    return f"decision-{int(time.time())}-{uuid.uuid4().hex[:10]}"


def default_style() -> dict[str, Any]:
    return {"length": "short", "tone": "direct", "avoid": ["report_voice", "tool_leak"]}


def decision(
    *,
    mode: str,
    reply: str = "",
    tool_request: dict[str, Any] | None = None,
    memory_candidates: list[dict[str, Any]] | None = None,
    confidence: float = 0.5,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    if mode not in VALID_MODES:
        mode = "clarify"
        reply = reply or "我需要你再说具体一点。"
        confidence = min(confidence, 0.4)
    return {
        "decision_id": new_decision_id(),
        "mode": mode,
        "reply": reply,
        "tool_request": tool_request,
        "memory_candidates": list(memory_candidates or []),
        "style": default_style(),
        "confidence": round(float(confidence), 3),
        "notes": list(notes or []),
    }


def clamp01(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(max(0.0, min(1.0, number)), 3)


def normalize_emotion_bias(value: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if "证据" in value and "evidence" not in value:
        localized = value.get("证据")
        value = dict(value)
        value["evidence"] = localized if isinstance(localized, list) else [localized]
        value.pop("证据", None)
    if set(value) - VALID_EMOTION_BIAS_KEYS:
        return None
    lens = str(value.get("lens", "") or "").strip()
    if lens not in VALID_EMOTION_LENSES:
        return None
    reply_bias = str(value.get("reply_bias", "") or "").strip()
    if not reply_bias:
        reply_bias = "没有明显情绪偏向，保持当前主线。"
    risk_flags = value.get("risk_flags")
    if not isinstance(risk_flags, list):
        risk_flags = []
    evidence = value.get("evidence")
    if not isinstance(evidence, list):
        evidence = []
    return {
        "lens": lens,
        "activation": clamp01(value.get("activation"), 0.0),
        "reply_bias": reply_bias[:180],
        "risk_flags": [str(item)[:80] for item in risk_flags[:8] if str(item).strip()],
        "confidence": clamp01(value.get("confidence"), 0.5),
        "evidence": [str(item)[:80] for item in evidence[:6] if str(item).strip()],
    }
