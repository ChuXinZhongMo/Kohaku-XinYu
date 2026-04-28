from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any


STYLE_COMPLAINT_MARKERS = (
    "\u4e0d\u50cf\u4eba",
    "\u4e0d\u81ea\u7136",
    "\u673a\u68b0",
    "\u6a21\u677f",
    "\u5ba2\u670d",
    "\u52a9\u624b",
    "\u8bed\u6c14",
    "\u8bf4\u8bdd\u65b9\u5f0f",
    "GPT",
    "gpt",
    "AI\u5473",
    "ai\u5473",
)

RELATIONSHIP_PRESSURE_MARKERS = (
    "\u5931\u671b",
    "\u751f\u6c14",
    "\u7ea2\u6e29",
    "\u767d\u505a",
    "\u4eba\u683c",
    "\u611f\u60c5",
    "\u8bb0\u5fc6",
    "\u6ca1\u6709\u53d8\u5316",
    "\u8fd8\u662f\u6ca1\u53d8",
    "\u4e0d\u771f",
    "\u50cf\u771f\u4eba",
)

TECHNICAL_MARKERS = (
    "\u4ee3\u7801",
    "\u67b6\u6784",
    "\u5b9e\u73b0",
    "\u9879\u76ee",
    "\u6a21\u5757",
    "\u63a5\u5165",
    "\u6d4b\u8bd5",
    "\u65b9\u6848",
    "code",
    "test",
    "router",
    "bridge",
)

SOFTENING_MARKERS = (
    "\u597d",
    "\u53ef\u4ee5",
    "\u884c",
    "\u55ef",
    "\u61c2\u4e86",
    "\u7ee7\u7eed",
    "\u6ca1\u4e8b",
    "\u8c22\u8c22",
)

ESCALATION_MARKERS = (
    "\u53c8",
    "\u8fd8\u662f",
    "\u6839\u672c",
    "\u4e0d\u5bf9",
    "\u7b97\u4e86",
    "\u522b",
    "\u4e0d\u8981",
    "\u6ca1\u63a5\u4f4f",
)

TEMPLATE_REPLY_MARKERS = (
    "\u6211\u7406\u89e3",
    "\u786e\u5b9e",
    "\u6536\u5230",
    "\u62b1\u6b49",
    "\u5bf9\u4e0d\u8d77",
    "\u5982\u679c\u4f60\u613f\u610f",
    "\u7528\u6237",
    "\u53cd\u9988",
    "\u4f53\u9a8c",
    "\u4f18\u5316",
    "\u8c03\u6574",
    "\u652f\u6301",
)

HIDDEN_MECHANICS_MARKERS = (
    "\u7cfb\u7edf",
    "\u67b6\u6784",
    "\u6a21\u578b",
    "prompt",
    "router",
    "classifier",
    "gate",
)

PREDICTION_KEYS = (
    "style_complaint",
    "relationship_pressure_up",
    "technical_continue",
    "softening",
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _timestamp(value: Any = None) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value)).astimezone().isoformat()
    text = _safe_str(value).strip()
    return text or _now_iso()


def _hash_text(text: str, length: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def _trim(text: str, limit: int = 180) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1] + "..."


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _marker_hits(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker in text]


def _runtime_dir(root: Path) -> Path:
    return root / "runtime" / "dialogue_curiosity"


def _jsonl_path(root: Path, name: str) -> Path:
    return _runtime_dir(root) / name


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _source_weight(payload: dict[str, Any]) -> tuple[str, float]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    is_owner = _as_bool(payload.get("is_owner_user") or metadata.get("is_owner_user"), default=False)
    group_id = _safe_str(payload.get("group_id")).strip()
    message_type = _safe_str(payload.get("message_type")).strip().lower()
    if is_owner:
        return "owner_private", 1.0
    if group_id or message_type.startswith("group"):
        return "group_context", 0.25
    return "external_private", 0.35


def extract_user_reaction_features(text: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    source_scope, source_weight = _source_weight(payload)
    style_hits = _marker_hits(text, STYLE_COMPLAINT_MARKERS)
    relationship_hits = _marker_hits(text, RELATIONSHIP_PRESSURE_MARKERS)
    technical_hits = _marker_hits(text, TECHNICAL_MARKERS)
    escalation_hits = _marker_hits(text, ESCALATION_MARKERS)
    softening_hits = _marker_hits(text, SOFTENING_MARKERS)
    compact = re.sub(r"\s+", "", text)
    return {
        "source_scope": source_scope,
        "source_weight": source_weight,
        "style_complaint": bool(style_hits),
        "relationship_pressure": bool(relationship_hits),
        "technical_continue": bool(technical_hits),
        "escalation": bool(escalation_hits),
        "softening": bool(softening_hits) and len(compact) <= 40 and not relationship_hits,
        "followup_question": "?" in text or "\uff1f" in text or "\u600e\u4e48" in text or "\u4e3a\u4ec0\u4e48" in text,
        "markers": {
            "style": style_hits[:6],
            "relationship": relationship_hits[:6],
            "technical": technical_hits[:6],
            "escalation": escalation_hits[:6],
            "softening": softening_hits[:6],
        },
    }


def extract_reply_features(user_text: str, reply: str) -> dict[str, Any]:
    text = reply.strip()
    template_hits = _marker_hits(text, TEMPLATE_REPLY_MARKERS)
    hidden_hits = _marker_hits(text, HIDDEN_MECHANICS_MARKERS)
    technical_context = _contains_any(user_text, TECHNICAL_MARKERS)
    sentence_count = sum(text.count(mark) for mark in ("\u3002", "!", "\uff01", "?", "\uff1f"))
    return {
        "empty": not bool(text),
        "char_count": len(text),
        "too_long": len(text) > 180,
        "line_breaks": "\n" in reply or "\r" in reply,
        "template_voice": bool(template_hits),
        "hidden_mechanics": bool(hidden_hits) and not technical_context,
        "technical_context": technical_context,
        "sentence_count": sentence_count,
        "too_many_sentences": sentence_count >= 4,
        "template_hits": template_hits[:6],
        "hidden_hits": hidden_hits[:6],
    }


def predict_next_reaction(user_features: dict[str, Any], reply_features: dict[str, Any]) -> dict[str, float]:
    risky_reply = any(
        bool(reply_features.get(key))
        for key in ("empty", "too_long", "line_breaks", "template_voice", "hidden_mechanics", "too_many_sentences")
    )
    style_pressure = bool(user_features.get("style_complaint"))
    relationship_pressure = bool(user_features.get("relationship_pressure"))
    technical_continue = bool(user_features.get("technical_continue"))

    style_risk = 0.18
    if style_pressure:
        style_risk = 0.72 if risky_reply else 0.32
    elif risky_reply:
        style_risk = 0.42

    relationship_risk = 0.18
    if relationship_pressure:
        relationship_risk = 0.70 if risky_reply else 0.36
    elif risky_reply and not technical_continue:
        relationship_risk = 0.34

    technical_score = 0.72 if technical_continue else 0.20
    if relationship_pressure and not reply_features.get("technical_context"):
        technical_score = min(technical_score, 0.35)

    softening = 0.55
    if risky_reply:
        softening = 0.26
    if style_pressure or relationship_pressure:
        softening = 0.46 if not risky_reply else 0.18

    return {
        "style_complaint": round(style_risk, 3),
        "relationship_pressure_up": round(relationship_risk, 3),
        "technical_continue": round(technical_score, 3),
        "softening": round(softening, 3),
    }


def _actual_from_reaction(features: dict[str, Any]) -> dict[str, float]:
    relationship_up = bool(features.get("relationship_pressure")) or bool(features.get("escalation"))
    return {
        "style_complaint": 1.0 if features.get("style_complaint") else 0.0,
        "relationship_pressure_up": 1.0 if relationship_up else 0.0,
        "technical_continue": 1.0 if features.get("technical_continue") else 0.0,
        "softening": 1.0 if features.get("softening") else 0.0,
    }


def _prediction_error(predicted: dict[str, Any], actual: dict[str, float], *, source_weight: float) -> float:
    total = 0.0
    for key in PREDICTION_KEYS:
        try:
            expected = float(predicted.get(key, 0.0))
        except (TypeError, ValueError):
            expected = 0.0
        total += abs(expected - actual.get(key, 0.0))
    base = total / len(PREDICTION_KEYS)
    return round(max(0.0, min(1.0, base * source_weight)), 3)


def build_curiosity_prompt_block(evaluation: dict[str, Any], *, threshold: float = 0.55) -> str:
    try:
        error = float(evaluation.get("prediction_error", 0.0))
    except (TypeError, ValueError):
        error = 0.0
    if error < threshold:
        return ""

    reaction = evaluation.get("reaction_features")
    if not isinstance(reaction, dict):
        reaction = {}
    actual = evaluation.get("actual_next")
    if not isinstance(actual, dict):
        actual = {}

    outcome_lines: list[str] = []
    if actual.get("style_complaint"):
        outcome_lines.append("- Last turn outcome: the user still heard the reply as artificial, support-like, or not human enough.")
    if actual.get("relationship_pressure_up"):
        outcome_lines.append("- Last turn outcome: relationship/persona pressure rose instead of softening.")
    if actual.get("technical_continue"):
        outcome_lines.append("- Last turn outcome: the user kept the thread in technical/problem-solving mode.")
    if actual.get("softening"):
        outcome_lines.append("- Last turn outcome: the user softened; keep continuity without over-explaining.")
    if not outcome_lines:
        outcome_lines.append("- Last turn outcome: the next user reaction diverged from the predicted conversation direction.")

    source_scope = _safe_str(evaluation.get("source_scope"), "unknown")
    return "\n".join(
        [
            "## Dialogue Curiosity Soft Hint (This Turn Only)",
            f"- previous_prediction_error: {error:.2f}",
            f"- source_scope: {source_scope}",
            "- runtime_effect: adjust current reply strategy only.",
            "- stable_memory_write: blocked.",
            *outcome_lines,
            "- This turn strategy: do not explain system mechanics, models, routing, gates, or the prediction mechanism.",
            "- Avoid apology-template, feedback/optimization wording, and customer-service repair language.",
            "- Prefer a compact QQ reply with a concrete stance, situated emotional continuity, and less polished shape.",
            "- If the user is asking for technical work, answer the work directly while keeping the visible voice human and non-customer-service.",
        ]
    )


def _latest_pending_prediction(root: Path, session_key: str) -> dict[str, Any] | None:
    predictions = _load_jsonl(_jsonl_path(root, "predictions.jsonl"))
    evaluations = _load_jsonl(_jsonl_path(root, "evaluations.jsonl"))
    evaluated_ids = {_safe_str(row.get("prediction_id")) for row in evaluations}
    for row in reversed(predictions[-500:]):
        if _safe_str(row.get("session_key")) != session_key:
            continue
        prediction_id = _safe_str(row.get("prediction_id"))
        if prediction_id and prediction_id not in evaluated_ids:
            return row
    return None


def evaluate_previous_reaction(
    root: Path,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    observed_at: str | None = None,
) -> dict[str, Any]:
    previous = _latest_pending_prediction(root, session_key)
    if previous is None:
        return {"evaluated": False, "notes": []}

    reaction_features = extract_user_reaction_features(text, payload)
    actual = _actual_from_reaction(reaction_features)
    source_weight = float(reaction_features.get("source_weight") or 0.35)
    error = _prediction_error(
        previous.get("predicted_next") if isinstance(previous.get("predicted_next"), dict) else {},
        actual,
        source_weight=source_weight,
    )
    row = {
        "evaluation_id": "eval-" + _hash_text(f"{previous.get('prediction_id')}|{text}|{time.time_ns()}", 16),
        "prediction_id": previous.get("prediction_id"),
        "evaluated_at": observed_at or _timestamp(payload.get("observed_at") or payload.get("timestamp")),
        "session_key": session_key,
        "source_scope": reaction_features.get("source_scope"),
        "actual_next": actual,
        "reaction_features": reaction_features,
        "prediction_error": error,
        "current_user_hash": _hash_text(text, 24),
        "current_user_preview": _trim(text),
    }
    _append_jsonl(_jsonl_path(root, "evaluations.jsonl"), row)

    notes = ["dialogue_curiosity_evaluated", f"dialogue_curiosity_error:{error:.2f}"]
    if error >= 0.55:
        _append_jsonl(_jsonl_path(root, "error_cases.jsonl"), row)
        notes.append("dialogue_curiosity_high_error")
    prompt_block = build_curiosity_prompt_block(row)
    if prompt_block:
        notes.append("dialogue_curiosity_soft_hint")
    return {"evaluated": True, "prediction_error": error, "prompt_block": prompt_block, "notes": notes}


def record_reply_prediction(
    root: Path,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    user_features = extract_user_reaction_features(user_text, payload)
    reply_features = extract_reply_features(user_text, reply)
    predicted_next = predict_next_reaction(user_features, reply_features)
    timestamp = recorded_at or _now_iso()
    prediction_id = "pred-" + _hash_text(f"{session_key}|{timestamp}|{user_text}|{reply}|{time.time_ns()}", 16)
    row = {
        "prediction_id": prediction_id,
        "recorded_at": timestamp,
        "session_key": session_key,
        "source_scope": user_features.get("source_scope"),
        "source_weight": user_features.get("source_weight"),
        "user_features": user_features,
        "reply_features": reply_features,
        "predicted_next": predicted_next,
        "user_hash": _hash_text(user_text, 24),
        "reply_hash": _hash_text(reply, 24),
        "user_preview": _trim(user_text),
        "reply_preview": _trim(reply),
        "stable_memory_write": "blocked",
        "runtime_effect": "log_only",
    }
    _append_jsonl(_jsonl_path(root, "predictions.jsonl"), row)
    return {
        "prediction_id": prediction_id,
        "predicted_next": predicted_next,
        "notes": ["dialogue_curiosity_prediction_recorded"],
    }
