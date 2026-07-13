from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from xinyu_qq_config import as_bool as _as_bool
from xinyu_qq_config import as_int as _as_int
from xinyu_qq_config import as_str_list as _as_str_list
from xinyu_qq_gateway_utils import safe_str as _safe_str
from xinyu_qq_models import PreparedMessage
from xinyu_turn_completion import TurnCompletionDecision


def owner_private_intent_compact(text: str) -> str:
    return re.sub(r"\s+", "", _safe_str(text)).strip(
        " \t\r\n,.;:!?~`'\"()[]{}<>。，！？；：、…—-"
    ).lower()


def owner_private_contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _safe_str(text).lower()
    return any(marker and marker in lowered for marker in markers)


def owner_private_is_low_info_unit(
    unit: str,
    *,
    has_question: bool,
    has_task: bool,
    has_technical: bool,
) -> bool:
    compact = owner_private_intent_compact(unit)
    if not compact:
        return True
    low_info_exact = (
        "嗯",
        "嗯嗯",
        "哦",
        "好",
        "好的",
        "行",
        "可以",
        "知道了",
        "等一下",
        "等下",
        "等会",
        "我想想",
        "再想想",
        "我看看",
    )
    if compact in low_info_exact:
        return True
    thinking_markers = (
        "我想想",
        "再想想",
        "等我想想",
        "想想办法",
        "我看看",
        "先想想",
    )
    return (
        len(compact) <= 18
        and not has_question
        and not has_task
        and not has_technical
        and owner_private_contains_any(compact, thinking_markers)
    )


def owner_private_looks_like_fragment_continuation(text: str) -> bool:
    stripped = _safe_str(text).strip()
    if not stripped:
        return False
    continuation_suffixes = (",", "，", "、", "...", "…", "……")
    if stripped.endswith(continuation_suffixes):
        return True
    compact = owner_private_intent_compact(stripped)
    continuation_words = (
        "还有",
        "然后",
        "但是",
        "不过",
        "而且",
        "因为",
    )
    return any(compact.endswith(word) for word in continuation_words)


def should_coalesce_owner_private_chat(gateway: Any, prepared: PreparedMessage) -> bool:
    if gateway.config.owner_private_coalesce_seconds <= 0:
        return False
    if prepared.route != "chat" or prepared.local_reply:
        return False
    if prepared.target.message_kind != "private" or prepared.target.user_id not in gateway.config.owner_user_ids:
        return False
    text = _safe_str(prepared.payload.get("text")).strip()
    if not text:
        return False
    metadata = prepared.payload.get("metadata")
    if isinstance(metadata, dict) and _as_bool(metadata.get("control_plane"), default=False):
        return False
    return True


def owner_private_intent_gate_applies(gateway: Any, prepared: PreparedMessage) -> bool:
    if prepared.route != "chat" or prepared.local_reply:
        return False
    if prepared.target.message_kind != "private" or prepared.target.user_id not in gateway.config.owner_user_ids:
        return False
    payload = prepared.payload if isinstance(prepared.payload, dict) else {}
    text = _safe_str(payload.get("text")).strip()
    if not text:
        return False
    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and _as_bool(metadata.get("control_plane"), default=False):
        return False
    return True


def owner_private_segmented_intent_decision(gateway: Any, prepared: PreparedMessage) -> dict[str, Any]:
    if not owner_private_intent_gate_applies(gateway, prepared):
        return {"applies": False, "action": "reply_now", "should_reply": True, "notes": []}

    payload = prepared.payload if isinstance(prepared.payload, dict) else {}
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    text = _safe_str(payload.get("text")).strip()
    fragments = [part.strip() for part in re.split(r"[\r\n]+", text) if part.strip()]
    units = [part.strip() for part in re.split(r"[\r\n,;，；、]+", text) if part.strip()]
    if not fragments:
        fragments = [text]
    if not units:
        units = fragments

    notes: list[str] = []
    coalesced_count = _as_int(metadata.get("qq_coalesced_message_count"), len(fragments))
    if _as_bool(metadata.get("qq_coalesced_owner_messages"), default=False) or coalesced_count > 1:
        notes.append("coalesced_owner_fragments")
    turn_completion_should_generate = _as_bool(
        metadata.get("qq_turn_completion_should_generate"),
        default=False,
    )

    correction_markers = (
        "不是",
        "不对",
        "我的意思是",
        "我是说",
        "刚才",
        "没接上",
    )
    task_markers = (
        "修复",
        "修一下",
        "改",
        "添加",
        "加个",
        "实现",
        "写",
        "整理",
        "查看",
        "检查",
        "测试",
        "跑",
        "运行",
        "启动",
        "继续",
        "开始",
        "删",
        "替换",
        "接入",
        "接上",
        "下载",
        "安装",
        "更新",
        "部署",
        "汉化",
        "plan",
        "api",
        "ui",
        "codex",
        "kohaku",
        "mcp",
        "plugin",
    )
    question_markers = (
        "?",
        "？",
        "什么",
        "为什么",
        "怎么",
        "能不能",
        "是不是",
        "有没有",
        "哪",
        "如何",
        "多少",
        "吗",
    )
    emotion_markers = (
        "我超",
        "卧槽",
        "烦",
        "崩",
        "爆了",
        "完了",
        "难受",
        "笑死",
        "气死",
    )
    technical_markers = (
        "api",
        "qq",
        "xinyu",
        "心玉",
        "前端",
        "模型",
        "插件",
        "测试",
        "报错",
        "fast path",
        "本地",
        "额度",
        "空回复",
        "不回复",
    )
    social_markers = (
        "你好",
        "早",
        "晚安",
        "回来",
        "到家",
        "谢谢",
        "辛苦",
        "想你",
        "生日",
    )
    status_markers = (
        "坐",
        "走",
        "吃",
        "睡",
        "地铁",
        "公交",
        "开车",
        "出门",
        "上班",
        "下班",
        "洗澡",
        "忙",
    )

    has_correction = owner_private_contains_any(text, correction_markers)
    has_task = owner_private_contains_any(text, task_markers)
    has_question = owner_private_contains_any(text, question_markers)
    has_emotion = owner_private_contains_any(text, emotion_markers)
    has_technical = owner_private_contains_any(text, technical_markers)
    has_social = owner_private_contains_any(text, social_markers)
    all_low_info = bool(units) and all(
        owner_private_is_low_info_unit(
            unit,
            has_question=has_question,
            has_task=has_task,
            has_technical=has_technical,
        )
        for unit in units
    )

    compact = owner_private_intent_compact(text)
    short_status_update = (
        len(compact) <= 8
        and not has_question
        and not has_task
        and not has_technical
        and not has_social
        and owner_private_contains_any(compact, status_markers)
    )

    action = "reply_now"
    should_reply = True
    if has_correction:
        action = "correction"
        notes.append("owner_correction_or_repair")
    elif has_task:
        action = "task_instruction"
        notes.append("owner_task_instruction")
    elif has_question or has_emotion or has_technical or has_social:
        action = "reply_now"
    elif all_low_info:
        if turn_completion_should_generate:
            action = "reply_now"
            notes.append("turn_completion_ready_overrides_silent")
        else:
            action = "silent"
            should_reply = False
            notes.append("low_info_owner_turn")
    elif owner_private_looks_like_fragment_continuation(fragments[-1]):
        if turn_completion_should_generate:
            action = "reply_now"
            notes.append("turn_completion_ready_overrides_fragment_wait")
        else:
            action = "wait_more"
            should_reply = False
            notes.append("fragment_continuation_marker")
    elif short_status_update:
        if turn_completion_should_generate:
            action = "reply_now"
            notes.append("turn_completion_ready_overrides_silent")
        else:
            action = "silent"
            should_reply = False
            notes.append("short_status_update")

    return {
        "applies": True,
        "action": action,
        "should_reply": should_reply,
        "notes": notes,
        "fragment_count": max(1, coalesced_count),
    }


def apply_owner_private_segmented_intent_gate(
    gateway: Any,
    prepared: PreparedMessage,
) -> tuple[PreparedMessage, dict[str, Any]]:
    decision = owner_private_segmented_intent_decision(gateway, prepared)
    if not decision.get("applies"):
        return prepared, decision
    payload = dict(prepared.payload if isinstance(prepared.payload, dict) else {})
    metadata = dict(payload.get("metadata")) if isinstance(payload.get("metadata"), dict) else {}
    action = _safe_str(decision.get("action"), "reply_now").strip() or "reply_now"
    metadata.update(
        {
            "qq_segmented_intent_gate": True,
            "qq_segmented_intent_action": action,
            "qq_segmented_intent_notes": list(decision.get("notes") or [])[:8],
            "qq_segmented_fragment_count": _as_int(decision.get("fragment_count"), 1),
            "qq_should_reply": bool(decision.get("should_reply", True)),
        }
    )
    payload["metadata"] = metadata
    return replace(prepared, payload=payload), decision


def with_turn_completion_metadata(
    prepared: PreparedMessage,
    decision: TurnCompletionDecision,
) -> PreparedMessage:
    payload = dict(prepared.payload if isinstance(prepared.payload, dict) else {})
    metadata = dict(payload.get("metadata")) if isinstance(payload.get("metadata"), dict) else {}
    metadata.update(
        {
            "qq_turn_completion_state": decision.state,
            "qq_turn_completion_reason": decision.reason,
            "qq_turn_completion_wait_seconds": decision.wait_seconds,
            "qq_turn_completion_should_generate": decision.should_generate,
            "qq_turn_completion_notes": list(decision.notes)[:8],
        }
    )
    payload["metadata"] = metadata
    return replace(prepared, payload=payload)


def build_coalesced_prepared_message(
    gateway: Any,
    prepareds: list[PreparedMessage],
) -> PreparedMessage | None:
    items = [item for item in prepareds if item is not None]
    if not items:
        return None
    if len(items) == 1:
        return items[0]
    base = items[-1]
    payload = dict(base.payload)
    metadata = dict(payload.get("metadata")) if isinstance(payload.get("metadata"), dict) else {}
    texts = [_safe_str(item.payload.get("text")).strip() for item in items]
    texts = [text for text in texts if text]
    raw_messages = [_safe_str(item.payload.get("raw_message")).strip() for item in items]
    raw_messages = [text for text in raw_messages if text]
    message_ids = [_safe_str(item.payload.get("message_id")).strip() for item in items]
    message_ids = [text for text in message_ids if text]
    payload["text"] = "\n".join(texts)
    payload["raw_message"] = "\n".join(raw_messages or texts)
    payload["message_id"] = ",".join(message_ids)
    metadata.update(
        {
            "qq_coalesced_owner_messages": True,
            "qq_coalesced_message_count": len(items),
            "qq_coalesced_window_seconds": gateway.config.owner_private_coalesce_seconds,
        }
    )
    rich_segments: list[Any] = []
    forward_context: dict[str, Any] | None = None
    reply_context: dict[str, Any] | None = None
    forward_ids: list[str] = []
    arrival_seqs: list[int] = []
    prepared_seqs: list[int] = []
    for item in items:
        item_metadata = item.payload.get("metadata") if isinstance(item.payload, dict) else {}
        if not isinstance(item_metadata, dict):
            continue
        arrival_seq = _as_int(item_metadata.get("qq_arrival_seq"), 0)
        prepared_seq = _as_int(item_metadata.get("qq_prepared_seq"), 0)
        if arrival_seq:
            arrival_seqs.append(arrival_seq)
        if prepared_seq:
            prepared_seqs.append(prepared_seq)
        segments = item_metadata.get("qq_message_segments")
        if isinstance(segments, list):
            rich_segments.extend(segment for segment in segments if isinstance(segment, dict))
        forward_ids.extend(_as_str_list(item_metadata.get("qq_forward_message_ids")))
        candidate_forward = item_metadata.get("qq_forward_context")
        if isinstance(candidate_forward, dict):
            forward_context = candidate_forward
        candidate_reply = item_metadata.get("qq_reply_context")
        if isinstance(candidate_reply, dict):
            reply_context = candidate_reply
            reply_id = _safe_str(item_metadata.get("qq_reply_message_id")).strip()
            if reply_id:
                metadata["qq_reply_message_id"] = reply_id
    if arrival_seqs:
        metadata["qq_arrival_seq"] = arrival_seqs[0]
        metadata["qq_arrival_seqs"] = arrival_seqs
    if prepared_seqs:
        metadata["qq_prepared_seqs"] = prepared_seqs
    if rich_segments:
        metadata["qq_rich_message"] = True
        metadata["qq_message_segments"] = rich_segments[:12]
        metadata["qq_sticker_count"] = sum(1 for segment in rich_segments if segment.get("kind") == "sticker")
        metadata["qq_image_count"] = sum(1 for segment in rich_segments if segment.get("kind") == "image")
        metadata["qq_voice_count"] = sum(1 for segment in rich_segments if segment.get("kind") == "voice")
        metadata["qq_record_count"] = sum(
            1
            for segment in rich_segments
            if segment.get("kind") == "voice" and _safe_str(segment.get("segment_type")).lower() == "record"
        )
        metadata["qq_audio_count"] = sum(
            1
            for segment in rich_segments
            if segment.get("kind") == "voice" and _safe_str(segment.get("segment_type")).lower() in {"audio", "voice"}
        )
        metadata["qq_rich_summary"] = "；".join(
            _safe_str(segment.get("summary") or segment.get("name") or segment.get("id")).strip()
            for segment in rich_segments[:6]
            if isinstance(segment, dict)
        )[:1200]
    if reply_context is not None:
        metadata["qq_reply_context_available"] = True
        metadata["qq_reply_context"] = reply_context
    if forward_ids:
        metadata["qq_forward_message_ids"] = list(dict.fromkeys(forward_ids))[:6]
    if forward_context is not None:
        metadata["qq_forward_context_available"] = True
        metadata["qq_forward_context"] = forward_context
        metadata["qq_forward_message_count"] = int(forward_context.get("message_count") or 0)
        metadata["qq_forward_count"] = int(forward_context.get("message_count") or 0)
        payload["forwarded_messages"] = forward_context
    payload["metadata"] = metadata
    return PreparedMessage(target=base.target, payload=payload, route=base.route, local_reply=base.local_reply)
