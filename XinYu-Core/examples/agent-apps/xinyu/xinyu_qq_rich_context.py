from __future__ import annotations

from typing import Any

import xinyu_qq_sticker_semantics


STICKER_SEGMENT_TYPES = frozenset({"face", "mface", "dice", "rps"})
RICH_CONTEXT_SEGMENT_TYPES = frozenset({"reply", "forward", "face", "mface", "dice", "rps", "image", "json", "xml", "at"})


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def is_rich_context_segment(segment_type: str) -> bool:
    return segment_type in RICH_CONTEXT_SEGMENT_TYPES


def is_sticker_segment(segment_type: str) -> bool:
    return segment_type in STICKER_SEGMENT_TYPES


def summarize_segment(segment_type: str, data: dict[str, Any]) -> dict[str, Any]:
    if segment_type == "reply":
        reply_id = (
            safe_str(data.get("id")).strip()
            or safe_str(data.get("message_id")).strip()
            or safe_str(data.get("reply_id")).strip()
        )
        return {"kind": "reply", "id": reply_id, "summary": reply_id}
    if segment_type == "forward":
        forward_id = (
            safe_str(data.get("id")).strip()
            or safe_str(data.get("message_id")).strip()
            or safe_str(data.get("forward_id")).strip()
            or safe_str(data.get("forward_msg_id")).strip()
            or safe_str(data.get("resid")).strip()
            or safe_str(data.get("res_id")).strip()
        )
        return {"kind": "forward", "id": forward_id, "summary": forward_id or "merged_forward"}
    if segment_type in STICKER_SEGMENT_TYPES:
        summary = (
            safe_str(data.get("summary")).strip()
            or safe_str(data.get("text")).strip()
            or safe_str(data.get("name")).strip()
            or safe_str(data.get("id")).strip()
            or safe_str(data.get("emoji_id")).strip()
            or segment_type
        )
        semantic = xinyu_qq_sticker_semantics.infer_received_sticker_semantics(summary)
        return {"kind": "sticker", "segment_type": segment_type, "summary": summary, **semantic}
    if segment_type == "image":
        if xinyu_qq_sticker_semantics.image_segment_looks_like_sticker(data):
            summary = (
                safe_str(data.get("summary")).strip()
                or safe_str(data.get("name")).strip()
                or safe_str(data.get("file")).strip()
                or "image_sticker"
            )
            semantic = xinyu_qq_sticker_semantics.infer_received_sticker_semantics(summary)
            return {"kind": "sticker", "segment_type": "image", "summary": summary, **semantic}
        name = (
            safe_str(data.get("summary")).strip()
            or safe_str(data.get("name")).strip()
            or safe_str(data.get("file")).strip()
            or "image"
        )
        return {"kind": "image", "segment_type": "image", "name": name, "summary": name}
    if segment_type in {"json", "xml"}:
        text = safe_str(data.get("data") or data.get("text") or data.get("content")).strip()
        summary = text[:120] if text else segment_type
        return {"kind": segment_type, "segment_type": segment_type, "summary": summary}
    if segment_type == "at":
        qq = safe_str(data.get("qq")).strip()
        return {"kind": "at", "segment_type": "at", "summary": qq}
    return {}
