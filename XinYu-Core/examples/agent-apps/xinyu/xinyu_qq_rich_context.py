from __future__ import annotations

from typing import Any

import xinyu_qq_sticker_semantics


STICKER_SEGMENT_TYPES = frozenset({"face", "mface", "dice", "rps"})
VOICE_SEGMENT_TYPES = frozenset({"record", "voice", "audio"})
RICH_CONTEXT_SEGMENT_TYPES = frozenset(
    {"reply", "forward", "face", "mface", "dice", "rps", "image", "json", "xml", "at", *VOICE_SEGMENT_TYPES}
)


def safe_str(value: Any, default: str = "") -> str:
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


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


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
    if segment_type in VOICE_SEGMENT_TYPES:
        duration = safe_str(data.get("duration") or data.get("time") or data.get("seconds")).strip()
        summary = "voice_audio"
        if duration:
            summary = f"voice_audio:{duration}s"
        return {"kind": "voice", "segment_type": segment_type, "summary": summary}
    if segment_type in {"json", "xml"}:
        text = safe_str(data.get("data") or data.get("text") or data.get("content")).strip()
        summary = text[:120] if text else segment_type
        return {"kind": segment_type, "segment_type": segment_type, "summary": summary}
    if segment_type == "at":
        qq = safe_str(data.get("qq")).strip()
        return {"kind": "at", "segment_type": "at", "summary": qq}
    return {}


def prompt_sidecar_from_payload(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return ""
    lines: list[str] = []
    if _as_bool(metadata.get("qq_rich_message"), default=False):
        lines.extend(
            [
                (
                    "The current QQ message contains non-text rich segments. Interpret them as conversation "
                    "context; do not expose raw segment syntax unless the owner asks for debugging."
                ),
                f"summary: {safe_str(metadata.get('qq_rich_summary'))[:600] or 'none'}",
                f"sticker_count: {safe_str(metadata.get('qq_sticker_count'), '0')}",
                f"image_count: {safe_str(metadata.get('qq_image_count'), '0')}",
                f"forward_count: {safe_str(metadata.get('qq_forward_count'), '0')}",
            ]
        )
        segments = metadata.get("qq_message_segments")
        low_information_sticker = False
        if isinstance(segments, list):
            for index, item in enumerate(segments[:6], start=1):
                if not isinstance(item, dict):
                    continue
                kind = safe_str(item.get("kind"), "segment")
                label = safe_str(item.get("summary") or item.get("name") or item.get("id"))[:180]
                mood = safe_str(item.get("mood")).strip()
                meaning = safe_str(item.get("meaning")).strip()
                confidence = safe_str(item.get("confidence")).strip().lower()
                if kind == "sticker" and confidence == "low":
                    low_information_sticker = True
                suffix = f" mood={mood}" if mood else ""
                if meaning:
                    suffix += f" meaning={meaning[:160]}"
                lines.append(f"- segment {index}: {kind} {label}{suffix}".rstrip())
        sticker_count = _as_int(metadata.get("qq_sticker_count"), 0)
        if sticker_count > 0 and low_information_sticker and not _as_bool(
            metadata.get("qq_image_context_available"), default=False
        ):
            lines.extend(
                [
                    (
                        "Sticker content note: QQ only supplied a generic sticker label and no visual "
                        "image context for this turn."
                    ),
                    (
                        "Do not claim you saw an empty/blank frame or the actual sticker content. "
                        "If needed, say the visual content is unavailable from QQ metadata and answer "
                        "from the surrounding conversation."
                    ),
                ]
            )
        if _as_bool(metadata.get("sticker_import_queued"), default=False):
            lines.append("Sticker library import is queued in the background; do not wait for it before replying.")
        if _as_bool(metadata.get("sticker_import_completed"), default=False):
            lines.extend(
                [
                    "Sticker library import completed before this reply.",
                    (
                        "sticker_import_result: "
                        f"accepted={safe_str(metadata.get('sticker_import_accepted'))} "
                        f"imported={safe_str(metadata.get('sticker_imported'))} "
                        f"mood={safe_str(metadata.get('sticker_mood'))} "
                        f"label={safe_str(metadata.get('sticker_mood_label'))} "
                        f"confidence={safe_str(metadata.get('sticker_confidence'))} "
                        f"destination={safe_str(metadata.get('sticker_destination'))[:240]}"
                    ),
                ]
            )

    reply_id = safe_str(metadata.get("qq_reply_message_id")).strip()
    reply_context = metadata.get("qq_reply_context")
    if reply_id or isinstance(reply_context, dict):
        lines.extend(
            [
                "The current QQ message is replying to/quoting an earlier message.",
                f"quoted_message_id: {reply_id or safe_str((reply_context or {}).get('message_id'))}",
            ]
        )
        if isinstance(reply_context, dict):
            quoted_text = safe_str(reply_context.get("text")).strip()
            quoted_rich = safe_str(reply_context.get("rich_summary")).strip()
            sender = safe_str(reply_context.get("sender_name") or reply_context.get("user_id")).strip()
            if sender:
                lines.append(f"quoted_sender: {sender[:120]}")
            if quoted_text:
                lines.extend(["quoted_text:", quoted_text[:1200]])
            if quoted_rich:
                lines.append(f"quoted_rich_summary: {quoted_rich[:800]}")
    forward_context = metadata.get("qq_forward_context")
    if isinstance(forward_context, dict) or _as_bool(metadata.get("qq_forward_context_available"), default=False):
        forward_context_dict = forward_context if isinstance(forward_context, dict) else {}
        forward_ids = metadata.get("qq_forward_message_ids")
        if not isinstance(forward_ids, list):
            forward_ids = forward_context_dict.get("forward_ids")
        messages = forward_context_dict.get("messages")
        lines.extend(
            [
                "The current QQ message includes a forwarded/merged chat record.",
                (
                    "Read the forwarded chat as owner-supplied context for this turn. "
                    "Do not describe it as unavailable if the forwarded_text lines are present."
                ),
                f"forward_ids: {','.join(safe_str(item) for item in (forward_ids or [])[:4]) or 'none'}",
                f"forward_message_count: {safe_str(forward_context_dict.get('message_count'), '0')}",
            ]
        )
        if isinstance(messages, list):
            for index, item in enumerate(messages[:8], start=1):
                if not isinstance(item, dict):
                    continue
                sender = safe_str(item.get("sender_name") or item.get("user_id")).strip() or "unknown"
                text = safe_str(item.get("text") or item.get("rich_summary") or item.get("raw_message")).strip()
                if not text:
                    continue
                lines.append(f"- forwarded {index} {sender[:80]}: {text[:600]}")
    image_context = metadata.get("qq_image_context")
    if isinstance(image_context, dict) or _as_bool(metadata.get("qq_image_context_available"), default=False):
        image_context_dict = image_context if isinstance(image_context, dict) else {}
        image_available = _as_bool(
            image_context_dict.get("available"),
            default=_as_bool(metadata.get("qq_image_context_available"), default=False),
        )
        if image_available:
            lines.extend(
                [
                    "The current QQ image has been processed into image context.",
                    (
                        "Use OCR and visual summary as owner-supplied context for this turn. "
                        "If the summary says uncertain, keep that uncertainty in the reply."
                    ),
                ]
            )
        else:
            lines.extend(
                [
                    (
                        "The current QQ image was received, but no readable OCR text or visual "
                        "summary is available for this turn."
                    ),
                    (
                        "Do not use previous attachments, documents, or paper context as if they "
                        "described this image. If the owner asks about the image, say the current "
                        "image content is unavailable or unclear."
                    ),
                ]
            )
        ocr_text = safe_str(image_context_dict.get("ocr_text")).strip()
        vision_summary = safe_str(image_context_dict.get("vision_summary")).strip()
        notes = image_context_dict.get("notes")
        if isinstance(notes, list) and notes:
            lines.append("image_context_notes: " + ",".join(safe_str(note) for note in notes[:6]))
        if ocr_text:
            lines.extend(["image_ocr_text:", ocr_text[:1200]])
        if vision_summary:
            lines.extend(["image_visual_summary:", vision_summary[:1200]])
    if not lines:
        return ""
    return "\n".join(lines[:32])
