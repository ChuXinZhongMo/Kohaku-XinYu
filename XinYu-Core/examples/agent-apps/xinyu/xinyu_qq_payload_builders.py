from __future__ import annotations

from typing import Any

from xinyu_codex_delegate import looks_like_owner_local_write_request
from xinyu_image_context import is_image_learning_payload
from xinyu_qq_config import as_bool as _as_bool
from xinyu_qq_event_time import event_time_iso as _event_time_iso
from xinyu_qq_event_time import event_timestamp_seconds as _event_timestamp_seconds
from xinyu_qq_gateway_utils import safe_str as _safe_str
from xinyu_qq_models import ReplyTarget
import xinyu_qq_sticker_context


def build_goldmark_mark_payload(
    gateway: Any,
    event: dict[str, Any],
    *,
    target: ReplyTarget,
    reply_message_id: str,
    owner_note: str,
    text: str,
) -> dict[str, Any]:
    event_timestamp = _event_timestamp_seconds(event)
    return {
        "platform": "qq",
        "adapter": _gateway_name(gateway),
        "adapter_message_id": reply_message_id,
        "route": "chat",
        "owner_note": owner_note[:500],
        "session_id": gateway._session_id(target),
        "user_id": target.user_id,
        "source_message_id": _safe_str(event.get("message_id")).strip(),
        "command_text": text,
        "timestamp": event_timestamp,
        "metadata": {
            "gateway": _gateway_name(gateway),
            "gateway_version": _gateway_version(gateway),
            "source": "qq_gateway_goldmark_command",
            "qq_event_time_iso": _event_time_iso(event_timestamp),
            "qq_event_time_unix": event_timestamp,
            "onebot_post_type": _safe_str(event.get("post_type")),
            "onebot_message_type": _safe_str(event.get("message_type")),
            "is_owner_user": True,
            "control_plane": True,
        },
    }


def goldmark_result_reply(response: dict[str, Any]) -> str:
    if response.get("marked"):
        mark_id = _safe_str(response.get("mark_id")).strip()
        return f"标好了。{mark_id}" if mark_id else "标好了。"
    error = _safe_str(response.get("error")).strip()
    if error == "target_not_found":
        return "没找到这条回复的索引。确认你回复的是心玉刚发出的那条消息，再试一次。"
    if error == "invalid_target":
        return "这条不能标：目标回复没有有效 turn，或者被安全检查挡住了。"
    return "标记没写进去。"


def goldmark_error_reply(error_text: str) -> str:
    lowered = error_text.lower()
    if "target_not_found" in lowered or "404" in lowered:
        return "没找到这条回复的索引。确认你回复的是心玉刚发出的那条消息，再试一次。"
    if "invalid_target" in lowered or "409" in lowered:
        return "这条不能标：目标回复没有有效 turn，或者被安全检查挡住了。"
    return "标记失败，Core 没接住这次请求。"


def build_self_action_approval_payload(
    gateway: Any,
    event: dict[str, Any],
    *,
    target: ReplyTarget,
    text: str,
    command: dict[str, str],
    reply_message_id: str = "",
) -> dict[str, Any]:
    event_timestamp = _event_timestamp_seconds(event)
    decision = _safe_str(command.get("decision"), "approved")
    authorize_existing = _as_bool(command.get("authorize_existing"), default=decision != "denied")
    return {
        "queueId": _safe_str(command.get("queue_id"), "latest") or "latest",
        "decision": "denied" if decision == "denied" else "approved",
        "reason": _safe_str(command.get("reason")),
        "execute": decision != "denied",
        "authorizeCodex": decision != "denied",
        "authorizeExisting": authorize_existing,
        "decidedBy": "owner_qq",
        "platform": "qq",
        "adapter": _gateway_name(gateway),
        "message_type": "private_self_action_approval_command",
        "session_id": gateway._session_id(target),
        "user_id": target.user_id,
        "sender_name": gateway._sender_name(event),
        "message_id": _safe_str(event.get("message_id")),
        "reply_message_id": reply_message_id,
        "raw_command": text,
        "timestamp": event_timestamp,
        "metadata": {
            "gateway": _gateway_name(gateway),
            "gateway_version": _gateway_version(gateway),
            "source": "qq_gateway_self_action_approval_command",
            "qq_event_time_iso": _event_time_iso(event_timestamp),
            "qq_event_time_unix": event_timestamp,
            "is_owner_user": target.user_id in gateway.config.owner_user_ids,
            "control_plane": True,
            "quoted_self_action_message": bool(reply_message_id),
            "qq_reply_message_id": reply_message_id,
        },
    }


def build_review_admin_payload(
    gateway: Any,
    event: dict[str, Any],
    *,
    target: ReplyTarget,
    text: str,
    command: dict[str, Any],
) -> dict[str, Any]:
    event_timestamp = _event_timestamp_seconds(event)
    return {
        "batch_id": "latest",
        "command": _safe_str(command.get("command")),
        "indices": command.get("indices", []),
        "mod_text": _safe_str(command.get("mod_text")),
        "raw_command": text,
        "platform": "qq",
        "adapter": _gateway_name(gateway),
        "message_type": "private_review_admin_command",
        "session_id": gateway._session_id(target),
        "user_id": target.user_id,
        "sender_name": gateway._sender_name(event),
        "message_id": _safe_str(event.get("message_id")),
        "timestamp": event_timestamp,
        "metadata": {
            "gateway": _gateway_name(gateway),
            "gateway_version": _gateway_version(gateway),
            "source": "qq_gateway_review_admin_command",
            "qq_event_time_iso": _event_time_iso(event_timestamp),
            "qq_event_time_unix": event_timestamp,
            "is_owner_user": target.user_id in gateway.config.owner_user_ids,
            "control_plane": True,
        },
    }


def build_chat_payload(
    gateway: Any,
    event: dict[str, Any],
    *,
    target: ReplyTarget,
    text: str,
    rich_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session_id = gateway._session_id(target)
    message_type = f"{target.message_kind}_text"
    rich_context = rich_context or gateway._extract_rich_message_context(event)
    event_timestamp = _event_timestamp_seconds(event)
    metadata = {
        "gateway": _gateway_name(gateway),
        "gateway_version": _gateway_version(gateway),
        "source": "onebot_message_event",
        "qq_event_time_iso": _event_time_iso(event_timestamp),
        "qq_event_time_unix": event_timestamp,
        "source_channel": (
            "owner_private"
            if target.message_kind == "private" and target.user_id in gateway.config.owner_user_ids
            else ("qq_group" if target.message_kind == "group" else "qq_private")
        ),
        "qq_gateway_live_current_turn": True,
        "qq_current_turn_transport": _gateway_name(gateway),
        "qq_current_turn_message_kind": target.message_kind,
        "onebot_post_type": _safe_str(event.get("post_type")),
        "onebot_message_type": _safe_str(event.get("message_type")),
        "is_owner_user": target.user_id in gateway.config.owner_user_ids,
        "is_trusted_user": gateway._is_trusted_user_id(target.user_id),
        "user_trust_level": gateway._trust_level_for_user_id(target.user_id),
    }
    if rich_context.get("segments"):
        metadata["qq_rich_message"] = True
        metadata["qq_rich_summary"] = _safe_str(rich_context.get("summary"))[:1200]
        metadata["qq_message_segments"] = rich_context.get("segments", [])[:12]
        metadata["qq_sticker_count"] = int(rich_context.get("sticker_count") or 0)
        metadata["qq_image_count"] = int(rich_context.get("image_count") or 0)
        metadata["qq_voice_count"] = int(rich_context.get("voice_count") or 0)
        metadata["qq_audio_count"] = int(rich_context.get("audio_count") or 0)
        metadata["qq_record_count"] = int(rich_context.get("record_count") or 0)
        metadata["qq_forward_count"] = int(rich_context.get("forward_count") or 0)
    reply_message_id = _safe_str(rich_context.get("reply_message_id")).strip()
    if reply_message_id:
        metadata["qq_reply_message_id"] = reply_message_id
    forward_ids = rich_context.get("forward_message_ids")
    if isinstance(forward_ids, list) and forward_ids:
        metadata["qq_forward_message_ids"] = forward_ids[:6]
    return {
        "platform": "qq",
        "adapter": _gateway_name(gateway),
        "message_type": message_type,
        "session_id": session_id,
        "user_id": target.user_id,
        "sender_name": gateway._sender_name(event),
        "group_id": target.group_id or None,
        "bot_id": _safe_str(event.get("self_id")),
        "message_id": _safe_str(event.get("message_id")),
        "text": text,
        "raw_message": _safe_str(event.get("raw_message"), text),
        "timestamp": event_timestamp,
        "metadata": metadata,
    }


def build_learning_ingest_payload(
    gateway: Any,
    event: dict[str, Any],
    *,
    target: ReplyTarget,
    material: dict[str, str],
    text: str,
) -> dict[str, Any]:
    name = _safe_str(material.get("name"), "qq-file").strip() or "qq-file"
    reason_text = xinyu_qq_sticker_context.learning_reason_text(text)
    event_timestamp = _event_timestamp_seconds(event)
    payload: dict[str, Any] = {
        "origin": "owner_supplied",
        "reason": reason_text,
        "question_id": "qq-file-learning",
        "title": name,
        "label": name,
        "file_name": name,
        "file_id": _safe_str(material.get("file_id")).strip(),
        "busid": _safe_str(material.get("busid")).strip(),
        "stage": gateway.config.qq_file_learning_stage,
        "curated": gateway.config.qq_file_learning_curated,
        "timestamp": event_timestamp,
        "metadata": {
            "gateway": _gateway_name(gateway),
            "gateway_version": _gateway_version(gateway),
            "source": "qq_file_message",
            "qq_event_time_iso": _event_time_iso(event_timestamp),
            "qq_event_time_unix": event_timestamp,
            "onebot_post_type": _safe_str(event.get("post_type")),
            "onebot_message_type": _safe_str(event.get("message_type")),
            "message_id": _safe_str(event.get("message_id")),
            "session_id": gateway._session_id(target),
            "user_id": target.user_id,
            "group_id": target.group_id or "",
            "sender_name": gateway._sender_name(event),
            "segment_type": _safe_str(material.get("segment_type")),
            "file_id": _safe_str(material.get("file_id")).strip(),
            "busid": _safe_str(material.get("busid")).strip(),
            "is_owner_user": target.user_id in gateway.config.owner_user_ids,
            "is_trusted_user": gateway._is_trusted_user_id(target.user_id),
            "user_trust_level": gateway._trust_level_for_user_id(target.user_id),
        },
    }
    file_url = _safe_str(material.get("url")).strip()
    file_path = _safe_str(material.get("path")).strip()
    if file_url:
        payload["file_url"] = file_url
    elif file_path:
        payload["file_path"] = file_path
    return payload


def build_sticker_import_payload(
    gateway: Any,
    event: dict[str, Any],
    *,
    target: ReplyTarget,
    material: dict[str, str],
    text: str,
) -> dict[str, Any]:
    name = _safe_str(material.get("name"), "qq-sticker").strip() or "qq-sticker"
    event_timestamp = _event_timestamp_seconds(event)
    payload: dict[str, Any] = {
        "origin": "qq_owner_sticker",
        "platform": "qq",
        "adapter": _gateway_name(gateway),
        "message_type": "private_sticker_import",
        "session_id": gateway._session_id(target),
        "user_id": target.user_id,
        "sender_name": gateway._sender_name(event),
        "group_id": target.group_id or "",
        "message_id": _safe_str(event.get("message_id")),
        "timestamp": event_timestamp,
        "file_name": name,
        "name": name,
        "summary": _safe_str(material.get("summary")).strip(),
        "file_id": _safe_str(material.get("file_id")).strip(),
        "owner_text": text.strip()[:500],
        "use_clip": gateway.config.qq_sticker_import_use_clip,
        "use_ocr": gateway.config.qq_sticker_import_use_ocr,
        "metadata": {
            "gateway": _gateway_name(gateway),
            "gateway_version": _gateway_version(gateway),
            "source": "qq_sticker_message",
            "qq_event_time_iso": _event_time_iso(event_timestamp),
            "qq_event_time_unix": event_timestamp,
            "onebot_post_type": _safe_str(event.get("post_type")),
            "onebot_message_type": _safe_str(event.get("message_type")),
            "message_id": _safe_str(event.get("message_id")),
            "session_id": gateway._session_id(target),
            "user_id": target.user_id,
            "group_id": target.group_id or "",
            "sender_name": gateway._sender_name(event),
            "segment_type": _safe_str(material.get("segment_type")),
            "file_id": _safe_str(material.get("file_id")).strip(),
            "is_owner_user": target.user_id in gateway.config.owner_user_ids,
            "is_trusted_user": gateway._is_trusted_user_id(target.user_id),
            "user_trust_level": gateway._trust_level_for_user_id(target.user_id),
            "control_plane": True,
        },
    }
    file_url = _safe_str(material.get("url")).strip()
    file_path = _safe_str(material.get("path")).strip()
    if file_url:
        payload["file_url"] = file_url
    elif file_path:
        payload["file_path"] = file_path
    return payload


def build_sticker_followup_chat_payload(
    gateway: Any,
    event: dict[str, Any],
    *,
    target: ReplyTarget,
    sticker_payload: dict[str, Any],
    sticker_response: dict[str, Any] | None = None,
    vision_meaning: str = "",
) -> dict[str, Any] | None:
    if target.message_kind != "private":
        return None
    sticker_response = sticker_response if isinstance(sticker_response, dict) else {}
    rich_context = gateway._extract_rich_message_context(event)
    if not rich_context.get("segments"):
        return None
    sticker_context = xinyu_qq_sticker_context.sticker_context_from_import_response(
        sticker_payload,
        sticker_response,
    )
    if _safe_str(vision_meaning).strip():
        sticker_context = {
            **sticker_context,
            "vision_meaning": _safe_str(vision_meaning).strip(),
            "vision_inferred": True,
        }
    text = xinyu_qq_sticker_context.sticker_followup_text(rich_context, sticker_payload, sticker_context)
    payload = build_chat_payload(gateway, event, target=target, text=text, rich_context=rich_context)
    metadata = dict(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {})
    import_completed = _as_bool(sticker_context.get("import_completed"), default=False)
    if import_completed:
        metadata["qq_message_segments"] = xinyu_qq_sticker_context.enrich_sticker_segments_with_import_context(
            metadata.get("qq_message_segments"),
            sticker_context,
        )
    metadata.update(
        {
            "source": "qq_sticker_context_reaction",
            "sticker_followup_before_import": not import_completed,
            "sticker_followup_after_import": import_completed,
            "sticker_import_queued": not import_completed,
            "sticker_import_completed": import_completed,
            "sticker_import_accepted": _as_bool(sticker_context.get("accepted"), default=False),
            "sticker_imported": _as_bool(sticker_context.get("imported"), default=False),
            "sticker_mood": _safe_str(sticker_context.get("mood")),
            "sticker_mood_label": _safe_str(sticker_context.get("mood_label")),
            "sticker_confidence": _safe_str(sticker_context.get("confidence")),
            "sticker_destination": _safe_str(sticker_context.get("destination")),
            "sticker_import_material_id": _safe_str(sticker_response.get("material_id")),
            "sticker_import_item_id": _safe_str(sticker_response.get("learning_item_id")),
            "sticker_file_name": _safe_str(sticker_payload.get("file_name") or sticker_payload.get("name")),
            "attachment_followup_mode": "sticker_context_reaction",
        }
    )
    if import_completed:
        metadata["qq_image_context"] = sticker_context
        metadata["qq_image_context_available"] = _as_bool(sticker_context.get("available"), default=False)
        metadata["qq_image_context_notes"] = (
            sticker_context.get("notes", [])[:8] if isinstance(sticker_context.get("notes"), list) else []
        )
    payload["metadata"] = metadata
    return payload


def build_attachment_followup_chat_payload(
    gateway: Any,
    event: dict[str, Any],
    *,
    target: ReplyTarget,
    learning_payload: dict[str, Any],
    learning_response: dict[str, Any],
    image_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    image_context = image_context if isinstance(image_context, dict) else {}
    is_image_attachment = is_image_learning_payload(learning_payload, learning_response)
    has_image_context = bool(image_context.get("available"))
    rich_context = gateway._extract_rich_message_context(event)
    has_rich_context = bool(rich_context.get("segments"))
    if not learning_response.get("extracted_text") and not has_image_context and not (
        is_image_attachment and has_rich_context
    ):
        return None
    if target.message_kind != "private":
        return None
    text = _safe_str(learning_payload.get("reason")).strip()
    if not text or text == "owner supplied QQ file":
        text = (
            _safe_str(rich_context.get("fallback_text")).strip()
            or (
                "我刚发了一张图片。"
                if is_image_attachment
                else "我刚发了一个附件。"
            )
        )
    payload = build_chat_payload(gateway, event, target=target, text=text, rich_context=rich_context)
    metadata = dict(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {})
    metadata.update(
        {
            "source": "qq_attachment_followup_after_learning_ingest",
            "attachment_learning_item_id": _safe_str(learning_response.get("learning_item_id")),
            "attachment_material_id": _safe_str(learning_response.get("material_id")),
            "attachment_extracted_text_path": _safe_str(learning_response.get("extracted_text_path")),
            "attachment_followup_after_ingest": True,
            "attachment_followup_mode": "read_then_natural_reaction",
        }
    )
    if image_context or is_image_attachment:
        if not image_context:
            image_context = {"available": False, "kind": "image", "notes": ["image_context_unavailable"]}
        metadata["qq_image_context"] = image_context
        metadata["qq_image_context_available"] = bool(image_context.get("available"))
        metadata["qq_image_context_notes"] = image_context.get("notes", [])[:8]
    payload["metadata"] = metadata
    return payload


def build_package_install_payload(
    gateway: Any,
    event: dict[str, Any],
    *,
    target: ReplyTarget,
    package_text: str,
    text: str,
) -> dict[str, Any]:
    session_id = gateway._session_id(target)
    event_timestamp = _event_timestamp_seconds(event)
    return {
        "packages": package_text,
        "current_text": text,
        "session_id": session_id,
        "source": "qq_gateway_package_install_message",
        "requested_by": target.user_id,
        "message_id": _safe_str(event.get("message_id")),
        "timestamp": event_timestamp,
        "metadata": {
            "gateway": _gateway_name(gateway),
            "gateway_version": _gateway_version(gateway),
            "source": "qq_gateway_package_install_message",
            "qq_event_time_iso": _event_time_iso(event_timestamp),
            "qq_event_time_unix": event_timestamp,
            "onebot_post_type": _safe_str(event.get("post_type")),
            "onebot_message_type": _safe_str(event.get("message_type")),
            "session_id": session_id,
            "user_id": target.user_id,
            "sender_name": gateway._sender_name(event),
            "is_owner_user": target.user_id in gateway.config.owner_user_ids,
            "is_trusted_user": gateway._is_trusted_user_id(target.user_id),
            "user_trust_level": gateway._trust_level_for_user_id(target.user_id),
        },
    }


def build_codex_payload(
    gateway: Any,
    event: dict[str, Any],
    *,
    target: ReplyTarget,
    task_text: str,
) -> dict[str, Any]:
    session_id = gateway._session_id(target)
    event_timestamp = _event_timestamp_seconds(event)
    metadata = {
        "gateway": _gateway_name(gateway),
        "gateway_version": _gateway_version(gateway),
        "source": "qq_gateway_codex_execute_message",
        "qq_event_time_iso": _event_time_iso(event_timestamp),
        "qq_event_time_unix": event_timestamp,
        "onebot_post_type": _safe_str(event.get("post_type")),
        "onebot_message_type": _safe_str(event.get("message_type")),
        "is_owner_user": True,
        "owner_local_write_approved": looks_like_owner_local_write_request(task_text),
        "codex_auxiliary_brain": True,
        "direct_cli_execution": False,
    }
    return {
        "platform": "qq",
        "adapter": _gateway_name(gateway),
        "message_type": "private_codex_command",
        "session_id": session_id,
        "user_id": target.user_id,
        "sender_name": gateway._sender_name(event),
        "group_id": None,
        "bot_id": _safe_str(event.get("self_id")),
        "message_id": _safe_str(event.get("message_id")),
        "text": f"用 Codex 辅助慢脑处理这个任务：{task_text}",
        "raw_owner_task": task_text,
        "source": "qq_gateway_codex_execute_message",
        "background": gateway.config.codex_background,
        "auto_study": gateway.config.codex_auto_study,
        "timeout_seconds": gateway.config.codex_timeout_seconds,
        "visible_window": gateway.config.codex_visible_window,
        "window_title": gateway.config.codex_window_title,
        "network_access": gateway.config.codex_network_access,
        "timestamp": event_timestamp,
        "metadata": metadata,
    }


# Fallbacks only — do not import xinyu_qq_gateway here (circular import under
# prepare_message: gateway -> payload_builders -> gateway breaks private chat).
_DEFAULT_GATEWAY_NAME = "xinyu_native_qq_gateway"
_DEFAULT_GATEWAY_VERSION = "0.1.31"


def _gateway_name(gateway: Any) -> str:
    name = getattr(gateway, "gateway_name", None)
    if name:
        return str(name)
    return _DEFAULT_GATEWAY_NAME


def _gateway_version(gateway: Any) -> str:
    version = getattr(gateway, "gateway_version", None)
    if version:
        return str(version)
    return _DEFAULT_GATEWAY_VERSION
