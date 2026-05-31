from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_self_state_capsule import classify_self_state_query
from xinyu_text_variants import readable_markers


TRACE_REL = Path("runtime/post_reply_self_observation_trace.jsonl")
EXPRESSION_STATE_REL = Path("memory/self/expression_self_learning_state.md")

MECHANICAL_MARKERS = readable_markers(
    "后台",
    "模型",
    "系统",
    "prompt",
    "bridge",
    "queue",
    "tool call",
    "tool_call",
    "sidecar",
    "runtime",
    "API",
    "接口",
    "日志",
)
TECHNICAL_DIAGNOSTIC_MARKERS = readable_markers(
    "后台日志",
    "看下后台",
    "查后台",
    "日志",
    "debug",
    "诊断",
    "runtime",
    "core",
    "gateway",
)
TEMPLATE_MARKERS = readable_markers(
    "我理解",
    "感谢反馈",
    "感谢你的反馈",
    "我会优化",
    "我会继续优化",
    "我会调整",
    "我会改",
    "持续优化",
    "用户体验",
    "作为AI",
    "作为一个AI",
    "如果你愿意",
    "你可以慢慢说",
)
REPORT_SHAPE_MARKERS = readable_markers(
    "首先",
    "其次",
    "最后",
    "总结",
    "本质",
    "核心在于",
    "问题在于",
    "从这个角度",
    "换句话说",
    "也就是说",
    "复盘",
    "自检",
    "机制",
    "链路",
)
STYLE_PRESSURE_MARKERS = readable_markers(
    "模板",
    "模版",
    "客服",
    "接待腔",
    "机械",
    "不像人",
    "不像你",
    "AI味",
    "GPT味",
    "话术",
)
EMOTION_PRESSURE_MARKERS = readable_markers(
    "累",
    "难受",
    "失望",
    "生气",
    "烦",
    "红温",
    "挫败",
    "别安慰",
    "别复盘",
)
GENERIC_SHORT_REPLIES = readable_markers("嗯", "嗯。", "我在", "在。", "好的", "好。")
FIRST_PERSON_MARKERS = readable_markers("我", "有点", "现在", "刚才", "还在", "心里", "脑子")
ACK_COMPATIBLE_USER_MARKERS = readable_markers(
    "嗯",
    "好",
    "行",
    "可以",
    "就这样",
    "先这样",
    "安静",
    "不用回",
    "不用说",
    "不用解释",
    "别说话",
    "别追问",
    "休息",
    "睡",
)


def observe_post_reply_self_observation(
    root: Path | str,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    reply: str,
    visible_turn: Any | None = None,
    final_guard_flags: list[str] | tuple[str, ...] = (),
    quality_flags: list[str] | tuple[str, ...] = (),
    recalled_context: str = "",
    observed_at: str | None = None,
    write_state: bool = True,
) -> dict[str, Any]:
    del visible_turn
    root_path = Path(root)
    observed = _timestamp_or_now_iso(observed_at)
    owner_private = _owner_private(payload)
    self_state_kind = classify_self_state_query(user_text) if owner_private else "none"
    style_pressure = owner_private and _contains_any(user_text, STYLE_PRESSURE_MARKERS)
    emotion_pressure = owner_private and _contains_any(user_text, EMOTION_PRESSURE_MARKERS)
    technical_exception = _contains_any(user_text, TECHNICAL_DIAGNOSTIC_MARKERS)

    if not owner_private and not final_guard_flags and not quality_flags:
        return {"recorded": False, "notes": ["post_reply_observation_not_owner_private"]}

    reply_text = _safe_str(reply).strip()
    mechanical_hits = [] if technical_exception else _hits(reply_text, MECHANICAL_MARKERS)
    template_hits = _hits(reply_text, TEMPLATE_MARKERS)
    report_hits = _hits(reply_text, REPORT_SHAPE_MARKERS)
    q_flags = [_compact(flag, limit=80) for flag in quality_flags if _safe_str(flag).strip()]
    guard_flags = [_compact(flag, limit=80) for flag in final_guard_flags if _safe_str(flag).strip()]
    low_information_ack_risk = _low_information_ack_risk(
        owner_private=owner_private,
        user_text=user_text,
        reply=reply_text,
        technical_exception=technical_exception,
        style_pressure=style_pressure,
        emotion_pressure=emotion_pressure,
        self_state_kind=self_state_kind,
    ) or any("low-information acknowledgement" in flag for flag in q_flags)

    notes: list[str] = ["post_reply_observation_recorded"]
    if self_state_kind != "none":
        notes.append(f"post_reply_self_state:{self_state_kind}")
    if style_pressure:
        notes.append("post_reply_owner_style_pressure")
    if emotion_pressure:
        notes.append("post_reply_owner_emotion_pressure")
    if technical_exception:
        notes.append("post_reply_technical_exception")

    mechanical_risk = "high" if mechanical_hits or any("mechanic" in flag or "machine" in flag for flag in guard_flags) else "low"
    template_risk = "high" if template_hits else "medium" if any("template" in flag or "cliche" in flag for flag in q_flags) else "low"
    over_explained_risk = "high" if len(reply_text) > 220 or len(report_hits) >= 2 else "medium" if report_hits or "\n" in reply else "low"
    self_state_grounding = _self_state_grounding(
        self_state_kind=self_state_kind,
        reply=reply_text,
        mechanical_risk=mechanical_risk,
        template_risk=template_risk,
        technical_exception=technical_exception,
    )
    emotional_grounding = _emotional_grounding(
        style_pressure=style_pressure,
        emotion_pressure=emotion_pressure,
        reply=reply_text,
        template_risk=template_risk,
        over_explained_risk=over_explained_risk,
    )
    alive_voice = _alive_voice(
        reply=reply_text,
        mechanical_risk=mechanical_risk,
        template_risk=template_risk,
        over_explained_risk=over_explained_risk,
        self_state_grounding=self_state_grounding,
        emotional_grounding=emotional_grounding,
        low_information_ack_risk=low_information_ack_risk,
    )

    if mechanical_risk == "high":
        notes.append("post_reply_mechanical_risk")
    if template_risk in {"medium", "high"}:
        notes.append("post_reply_template_voice_risk")
    if over_explained_risk in {"medium", "high"}:
        notes.append("post_reply_over_explained_risk")
    if self_state_grounding == "missing":
        notes.append("post_reply_missed_self_state_grounding")
    if emotional_grounding == "missing":
        notes.append("post_reply_missed_emotional_grounding")
    if low_information_ack_risk:
        notes.append("post_reply_low_information_ack_risk")
    if alive_voice == "low":
        notes.append("post_reply_low_alive_voice")

    observation = {
        "recorded": True,
        "observation_kind": "owner_private_reply_self_observation" if owner_private else "reply_self_observation",
        "observed_at": observed,
        "owner_private": owner_private,
        "self_state_kind": self_state_kind,
        "technical_exception": technical_exception,
        "scores": {
            "alive_voice": alive_voice,
            "mechanical_risk": mechanical_risk,
            "template_risk": template_risk,
            "over_explained_risk": over_explained_risk,
            "low_information_ack_risk": "high" if low_information_ack_risk else "low",
            "emotional_grounding": emotional_grounding,
            "self_state_grounding": self_state_grounding,
        },
        "notes": _unique(notes),
    }
    _append_jsonl(
        root_path / TRACE_REL,
        {
            "observed_at": observed,
            "observation_kind": observation["observation_kind"],
            "owner_private": owner_private,
            "self_state_kind": self_state_kind,
            "technical_exception": technical_exception,
            "user_text_hash": _hash(user_text, 24),
            "reply_hash": _hash(reply_text, 24),
            "reply_chars": len(reply_text),
            "scores": observation["scores"],
            "notes": observation["notes"],
            "guard_flags": guard_flags[:8],
            "quality_flags": q_flags[:8],
            "recalled_context_present": bool(_safe_str(recalled_context).strip()),
            "raw_text_saved": False,
        },
    )
    if write_state:
        _write_expression_observation(root_path, observation)
    return observation


def _self_state_grounding(
    *,
    self_state_kind: str,
    reply: str,
    mechanical_risk: str,
    template_risk: str,
    technical_exception: bool,
) -> str:
    if self_state_kind == "none" or technical_exception:
        return "not_applicable"
    if not reply:
        return "missing"
    if mechanical_risk == "high" or template_risk == "high":
        return "missing"
    if _contains_any(reply, FIRST_PERSON_MARKERS):
        return "present"
    return "thin"


def _emotional_grounding(
    *,
    style_pressure: bool,
    emotion_pressure: bool,
    reply: str,
    template_risk: str,
    over_explained_risk: str,
) -> str:
    if not style_pressure and not emotion_pressure:
        return "not_applicable"
    if not reply or template_risk == "high" or over_explained_risk == "high":
        return "missing"
    if reply in GENERIC_SHORT_REPLIES:
        return "thin"
    return "present"


def _alive_voice(
    *,
    reply: str,
    mechanical_risk: str,
    template_risk: str,
    over_explained_risk: str,
    self_state_grounding: str,
    emotional_grounding: str,
    low_information_ack_risk: bool,
) -> str:
    if not reply:
        return "low"
    if low_information_ack_risk:
        return "low"
    if mechanical_risk == "high" or template_risk == "high" or over_explained_risk == "high":
        return "low"
    if self_state_grounding == "missing" or emotional_grounding == "missing":
        return "low"
    if template_risk == "medium" or over_explained_risk == "medium":
        return "medium"
    return "high"


def _low_information_ack_risk(
    *,
    owner_private: bool,
    user_text: str,
    reply: str,
    technical_exception: bool,
    style_pressure: bool,
    emotion_pressure: bool,
    self_state_kind: str,
) -> bool:
    if not owner_private or technical_exception:
        return False
    if reply not in GENERIC_SHORT_REPLIES:
        return False
    compact_user = re.sub(r"\s+", "", _safe_str(user_text)).strip()
    if not compact_user:
        return False
    if compact_user in GENERIC_SHORT_REPLIES:
        return False
    if len(compact_user) <= 4 and _contains_any(compact_user, ACK_COMPATIBLE_USER_MARKERS):
        return False
    if _contains_any(compact_user, readable_markers("不用回", "不用说", "别说话", "安静", "休息", "睡")):
        return False
    return (
        style_pressure
        or emotion_pressure
        or self_state_kind != "none"
        or len(compact_user) > 8
        or "?" in user_text
        or "？" in user_text
    )


def _write_expression_observation(root: Path, observation: dict[str, Any]) -> None:
    path = root / EXPRESSION_STATE_REL
    existing = _read(path).strip()
    prefix = existing.split("\n## Latest Post Reply Observation", 1)[0].rstrip() if existing else _default_expression_state()
    scores = observation.get("scores") if isinstance(observation.get("scores"), dict) else {}
    notes = observation.get("notes") if isinstance(observation.get("notes"), list) else []
    block = "\n".join(
        [
            "## Latest Post Reply Observation",
            f"- observed_at: {_compact(observation.get('observed_at'), limit=80)}",
            f"- observation_kind: {_compact(observation.get('observation_kind'), limit=80)}",
            f"- self_state_kind: {_compact(observation.get('self_state_kind'), limit=80)}",
            f"- alive_voice: {_compact(scores.get('alive_voice'), limit=40)}",
            f"- mechanical_risk: {_compact(scores.get('mechanical_risk'), limit=40)}",
            f"- template_risk: {_compact(scores.get('template_risk'), limit=40)}",
            f"- over_explained_risk: {_compact(scores.get('over_explained_risk'), limit=40)}",
            f"- low_information_ack_risk: {_compact(scores.get('low_information_ack_risk'), limit=40)}",
            f"- emotional_grounding: {_compact(scores.get('emotional_grounding'), limit=40)}",
            f"- self_state_grounding: {_compact(scores.get('self_state_grounding'), limit=40)}",
            f"- notes: {_compact(','.join(_safe_str(note) for note in notes), limit=240)}",
            "- raw_text_saved: false",
            "- stable_personality_write: no",
        ]
    )
    _write(path, f"{prefix}\n\n{block}\n")


def _default_expression_state() -> str:
    now = _timestamp_or_now_iso(None)
    return f"""---
title: Expression Self Learning State
memory_type: expression_self_learning_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_post_reply_self_observation
updated_at: {now}
status: active
tags: [self, expression, learning, anti-template]
---

# Expression Self Learning State"""


def _owner_private(payload: dict[str, Any] | None) -> bool:
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    is_owner = _as_bool(payload.get("is_owner_user") or metadata.get("is_owner_user"), default=False)
    group_id = _safe_str(payload.get("group_id") or metadata.get("group_id")).strip()
    message_type = _safe_str(payload.get("message_type") or metadata.get("message_type")).lower()
    return is_owner and not group_id and not message_type.startswith("group")


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _safe_str(text).lower()
    return any(marker and marker.lower() in lowered for marker in markers)


def _hits(text: str, markers: tuple[str, ...]) -> list[str]:
    lowered = _safe_str(text).lower()
    return [marker for marker in markers if marker and marker.lower() in lowered][:8]


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = _safe_str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _compact(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def _timestamp_or_now_iso(value: Any) -> str:
    text = _safe_str(value).strip()
    if text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            return parsed.astimezone().isoformat()
        except ValueError:
            pass
    return datetime.now().astimezone().isoformat()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
