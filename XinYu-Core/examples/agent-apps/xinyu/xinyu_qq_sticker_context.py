from __future__ import annotations

from typing import Any

from xinyu_qq_config import as_bool as _as_bool
from xinyu_qq_gateway_utils import safe_str as _safe_str
import xinyu_qq_normalizer


def learning_reason_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "owner supplied QQ file"
    without_cq = xinyu_qq_normalizer.strip_cq_segments(stripped)
    return without_cq or "owner supplied QQ file"


def sticker_followup_text(
    rich_context: dict[str, Any],
    sticker_payload: dict[str, Any],
    sticker_context: dict[str, Any],
) -> str:
    vision_meaning = _safe_str(sticker_context.get("vision_meaning")).strip()
    if vision_meaning:
        # The vision model actually looked at the sticker; trust its read over
        # the local CLIP label (which mislabels, e.g. 困惑 -> "shy 0.60").
        return f"我刚发了一张表情包。{vision_meaning}"[:500]
    if _as_bool(sticker_context.get("import_completed"), default=False):
        label = _safe_str(sticker_context.get("mood_label") or sticker_context.get("mood")).strip()
        meaning = _safe_str(sticker_context.get("meaning")).strip()
        summary = "我刚发了一张表情包。"
        if label:
            summary = f"我刚发了一张偏{label}的表情包。"
        if meaning:
            summary += f"大概是{meaning}。"
        return summary[:500]
    return (
        _safe_str(rich_context.get("fallback_text")).strip()
        or _safe_str(sticker_payload.get("summary") or sticker_payload.get("file_name")).strip()
        or "我刚发了一个表情包。"
    )


def first_sticker_import_item(sticker_response: dict[str, Any]) -> dict[str, Any]:
    items = sticker_response.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                return item
    return {}


def sticker_context_from_import_response(
    sticker_payload: dict[str, Any],
    sticker_response: dict[str, Any],
) -> dict[str, Any]:
    item = first_sticker_import_item(sticker_response)
    import_completed = any(
        key in sticker_response for key in ("accepted", "imported", "mood", "destination", "items", "failed")
    )
    accepted = _as_bool(sticker_response.get("accepted"), default=False)
    imported = _as_bool(sticker_response.get("imported"), default=False)
    mood = _safe_str(item.get("mood") or sticker_response.get("mood")).strip()
    mood_label = _safe_str(sticker_response.get("mood_label") or mood).strip()
    confidence = _safe_str(item.get("confidence") or sticker_response.get("confidence")).strip()
    meaning = _safe_str(item.get("meaning")).strip()
    destination = _safe_str(sticker_response.get("destination") or item.get("destination")).strip()
    ocr_text = _safe_str(item.get("ocr_text")).strip()
    clip_mood = _safe_str(item.get("clip_mood")).strip()
    clip_confidence = _safe_str(item.get("clip_confidence")).strip()
    file_name = _safe_str(sticker_payload.get("file_name") or sticker_payload.get("name")).strip()
    notes = ["sticker_import_completed" if import_completed else "sticker_import_pending"]
    if not accepted and import_completed:
        notes.append("sticker_import_not_accepted")
    if imported:
        notes.append("sticker_imported")
    summary_parts: list[str] = []
    if import_completed:
        if accepted and imported:
            summary_parts.append("这张 QQ 表情已经收进本地表情库")
        elif accepted:
            summary_parts.append("这张 QQ 表情已经接收，但还没有稳定分类")
        else:
            summary_parts.append("这张 QQ 表情暂时没有成功入库")
    if file_name:
        summary_parts.append(f"文件名/摘要：{file_name}")
    if mood_label or mood:
        summary_parts.append(f"分类：{mood_label or mood}")
    if confidence:
        summary_parts.append(f"置信度：{confidence}")
    if clip_mood:
        clip_note = f"CLIP 判断：{clip_mood}"
        if clip_confidence:
            clip_note += f" ({clip_confidence})"
        summary_parts.append(clip_note)
    if meaning:
        summary_parts.append(f"语义：{meaning}")
    if destination:
        summary_parts.append(f"入库位置：{destination}")
    available = bool(import_completed and (accepted or mood or ocr_text or clip_mood or destination))
    return {
        "available": available,
        "kind": "sticker",
        "import_completed": import_completed,
        "accepted": accepted,
        "imported": imported,
        "mood": mood,
        "mood_label": mood_label,
        "confidence": confidence,
        "meaning": meaning,
        "destination": destination,
        "ocr_text": ocr_text,
        "vision_summary": "；".join(summary_parts)[:1200],
        "notes": notes,
    }


def enrich_sticker_segments_with_import_context(value: Any, sticker_context: dict[str, Any]) -> list[dict[str, Any]]:
    segments = value if isinstance(value, list) else []
    enriched: list[dict[str, Any]] = []
    updated = False
    for item in segments:
        if not isinstance(item, dict):
            continue
        record = dict(item)
        if not updated and _safe_str(record.get("kind")) == "sticker":
            mood = _safe_str(sticker_context.get("mood")).strip()
            meaning = _safe_str(sticker_context.get("meaning")).strip()
            confidence = _safe_str(sticker_context.get("confidence")).strip()
            if mood:
                record["mood"] = mood
            if meaning:
                record["meaning"] = meaning
            if confidence:
                record["confidence"] = confidence
            updated = True
        enriched.append(record)
    return enriched
