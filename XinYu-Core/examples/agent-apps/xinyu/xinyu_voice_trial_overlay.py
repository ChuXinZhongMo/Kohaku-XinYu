from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from xinyu_text_variants import readable_markers
from xinyu_voice_trial_overlay_store import read_voice_trial_overlay_state
from xinyu_voice_trial_overlay_store import voice_trial_overlay_state_exists
from xinyu_voice_trial_overlay_store import write_voice_trial_overlay_state


OVERLAY_REL = Path("runtime/life_kernel/voice_trial_overlay.json")
DEFAULT_TURNS = 3
DEFAULT_TTL_MINUTES = 120

STYLE_CORRECTION_MARKERS = readable_markers(
    "像客服",
    "客服腔",
    "接待腔",
    "模板",
    "模版",
    "机械",
    "不像人",
    "不像你",
    "不自然",
    "AI味",
    "GPT味",
    "gpt味",
    "太复盘",
    "复盘太多",
    "别复盘",
    "不要复盘",
    "别解释",
    "少解释",
    "解释太多",
    "别承诺",
    "不要承诺",
    "空泛承诺",
    "别说会改",
    "不要说会改",
    "固定话术",
    "套话",
    "端着",
)

CUSTOMER_TONE_MARKERS = readable_markers("像客服", "客服腔", "接待腔", "反馈", "用户", "体验", "优化")
TEMPLATE_MARKERS = readable_markers("模板", "模版", "固定话术", "套话", "机械", "AI味", "GPT味", "gpt味")
NOT_HUMAN_MARKERS = readable_markers("不像人", "不像你", "不自然", "假人")
OVER_EXPLAIN_MARKERS = readable_markers("太复盘", "复盘太多", "别复盘", "不要复盘", "别解释", "少解释", "解释太多")
NO_PROMISE_MARKERS = readable_markers("别承诺", "不要承诺", "空泛承诺", "别说会改", "不要说会改")
REPAIR_META_AVOID = [
    "self-repair promise",
    "voice self-diagnosis",
    "tone-progress score answer",
    "future-fix promise",
    "safety-shell metaphor",
    "exam-answer posture",
]
LAYERED_VOICE_MARKERS = readable_markers(
    "隔着一层",
    "像隔着一层",
    "隔了一层",
    "像稿子",
    "念稿子",
    "念别人写的稿子",
    "别人写的稿子",
    "像在念",
    "不是她自己",
)
STYLE_CORRECTION_MARKERS = STYLE_CORRECTION_MARKERS + LAYERED_VOICE_MARKERS


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _now() -> datetime:
    return datetime.now().astimezone()


def _trim(text: Any, limit: int = 180) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker and marker in text for marker in markers)


def _markers(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker and marker in text]


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = _safe_str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _owner_private(payload: dict[str, Any] | None) -> bool:
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    is_owner = _as_bool(payload.get("is_owner_user") or metadata.get("is_owner_user"), default=False)
    group_id = _safe_str(payload.get("group_id")).strip()
    message_type = _safe_str(payload.get("message_type")).strip().lower()
    return is_owner and not group_id and not message_type.startswith("group")


def should_record_voice_trial_overlay(user_text: str) -> bool:
    return _contains_any(user_text, STYLE_CORRECTION_MARKERS)


def _directions_for(user_text: str) -> tuple[list[str], list[str], list[str]]:
    directions: list[str] = []
    avoid: list[str] = []
    mode_hints: list[str] = []
    if _contains_any(user_text, CUSTOMER_TONE_MARKERS):
        directions.append("use owner-private wording, not customer-service handling")
        avoid.extend(["感谢反馈", "持续优化", "用户体验", "我理解你的感受", *REPAIR_META_AVOID])
        mode_hints.extend(["short_reply", "specific_reply"])
    if _contains_any(user_text, TEMPLATE_MARKERS):
        directions.append("answer with the concrete next line instead of a reusable repair template")
        avoid.extend(["首先/其次/最后", "换句话说", "核心在于", *REPAIR_META_AVOID])
        mode_hints.extend(["short_reply", "no_template"])
    if _contains_any(user_text, NOT_HUMAN_MARKERS):
        directions.append("prefer a small imperfect line over a complete self-explanation")
        avoid.extend(["不像人的自我诊断", "完整复盘", "解释自己为什么不像"])
        mode_hints.extend(["human_private_chat", "less_polished"])
    if _contains_any(user_text, LAYERED_VOICE_MARKERS):
        directions.append("stay inside the current exchange instead of describing the voice failure from outside")
        directions.append("answer with one small present-tense line; let the next reply itself feel closer")
        avoid.extend(["知道该说什么但说不出来", "像在念别人写的稿子", "隔着一层的自我诊断", "完整解释为什么不像自己"])
        mode_hints.extend(["inside_current_turn", "less_self_analysis", "short_reply", "less_polished"])
    if _contains_any(user_text, OVER_EXPLAIN_MARKERS):
        directions.append("do not review the mechanism; continue the chat from the current fact")
        avoid.extend(["复盘结构", "门禁/状态/机制", "长解释"])
        mode_hints.extend(["less_explanation", "current_turn_first"])
    if _contains_any(user_text, NO_PROMISE_MARKERS):
        directions.append("avoid empty future promises; make the current reply itself different")
        avoid.extend(["我以后会", "下次一定", "我会记住并改"])
        mode_hints.extend(["no_empty_promise", "present_tense"])
    if not directions:
        directions.append("make the next owner-private replies shorter, more concrete, and less assistant-like")
        avoid.extend(["报告腔", "模板修复", "空泛承诺", *REPAIR_META_AVOID])
        mode_hints.extend(["short_reply", "specific_reply"])
    return _unique(directions), _unique(avoid), _unique(mode_hints)


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        clean = _trim(item, limit=120)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
    return result


def _overlay_id(recorded_at: str, user_text: str) -> str:
    total = sum((idx + 1) * ord(ch) for idx, ch in enumerate(recorded_at + user_text))
    return f"voice-trial-{total % 1_000_000:06d}"


def _read_state(path: Path) -> dict[str, Any]:
    return read_voice_trial_overlay_state(path)


def _write_state(path: Path, state: dict[str, Any]) -> None:
    write_voice_trial_overlay_state(path, state)


def _parse_time(value: Any) -> datetime | None:
    raw = _safe_str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _expired(state: dict[str, Any], now_dt: datetime) -> bool:
    if _safe_str(state.get("status")) != "active":
        return True
    try:
        remaining = int(state.get("remaining_turns") or 0)
    except (TypeError, ValueError):
        remaining = 0
    if remaining <= 0:
        return True
    expires_at = _parse_time(state.get("expires_at"))
    return bool(expires_at and now_dt >= expires_at)


def record_voice_trial_overlay(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    reply: str = "",
    source: str = "runtime",
    recorded_at: str | None = None,
    turns: int = DEFAULT_TURNS,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
) -> dict[str, Any]:
    if payload is not None and not _owner_private(payload):
        return {"recorded": False, "notes": ["voice_trial_overlay_not_owner_private"]}
    if not should_record_voice_trial_overlay(user_text):
        return {"recorded": False, "notes": ["voice_trial_overlay_no_correction_signal"]}
    now_dt = _now()
    recorded_at = recorded_at or now_dt.isoformat(timespec="seconds")
    directions, avoid, mode_hints = _directions_for(user_text)
    path = root / OVERLAY_REL
    state = {
        "version": 1,
        "status": "active",
        "overlay_id": _overlay_id(recorded_at, user_text),
        "created_at": recorded_at,
        "updated_at": recorded_at,
        "source": source,
        "owner_correction": _trim(user_text),
        "reply_excerpt": _trim(reply, limit=160),
        "correction_markers": _markers(user_text, STYLE_CORRECTION_MARKERS),
        "directions": directions,
        "avoid": avoid,
        "mode_hints": mode_hints,
        "remaining_turns": max(1, min(3, int(turns))),
        "initial_turns": max(1, min(3, int(turns))),
        "expires_at": (now_dt + timedelta(minutes=max(1, int(ttl_minutes)))).isoformat(timespec="seconds"),
        "stable_profile_write": "blocked",
        "stable_relationship_write": "blocked",
        "promotion_gate": "required_for_any_stable_voice_change",
        "notes": [
            "voice_trial_overlay_runtime_only",
            "short_term_owner_private_bias",
            "not_training_data_pipeline",
        ],
    }
    _write_state(path, state)
    return {"recorded": True, "path": str(path), "overlay_id": state["overlay_id"], "notes": ["voice_trial_overlay_recorded"]}


def read_voice_trial_overlay(root: Path) -> dict[str, Any]:
    return _read_state(root / OVERLAY_REL)


def build_voice_trial_overlay_prompt_block(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str = "",
    consume_turn: bool = True,
    now_dt: datetime | None = None,
) -> str:
    if not _owner_private(payload):
        return ""
    now_dt = now_dt or _now()
    path = root / OVERLAY_REL
    state = _read_state(path)
    if not state:
        return ""
    if _expired(state, now_dt):
        if _safe_str(state.get("status")) == "active":
            state["status"] = "expired"
            state["updated_at"] = now_dt.isoformat(timespec="seconds")
            _write_state(path, state)
        return ""

    try:
        remaining_before = int(state.get("remaining_turns") or 0)
    except (TypeError, ValueError):
        remaining_before = 0
    remaining_after = max(0, remaining_before - 1) if consume_turn else remaining_before
    if consume_turn:
        state["remaining_turns"] = remaining_after
        state["last_applied_at"] = now_dt.isoformat(timespec="seconds")
        state["last_owner_text"] = _trim(user_text, limit=160)
        if remaining_after <= 0:
            state["status"] = "expired_turns_consumed"
        _write_state(path, state)

    directions = state.get("directions") if isinstance(state.get("directions"), list) else []
    avoid = state.get("avoid") if isinstance(state.get("avoid"), list) else []
    mode_hints = state.get("mode_hints") if isinstance(state.get("mode_hints"), list) else []
    direction_text = "; ".join(_trim(item, limit=160) for item in directions[:4]) or "shorter, concrete, less assistant-like"
    avoid_text = "; ".join(_trim(item, limit=120) for item in avoid[:10]) or "empty promises; reports about style"
    hints_text = ", ".join(_trim(item, limit=80) for item in mode_hints[:6]) or "short_reply"
    return "\n".join(
        [
            "voice trial overlay sidecar:",
            "- scope: owner_private_short_term",
            f"- overlay_id: {_safe_str(state.get('overlay_id'), 'unknown')}",
            f"- remaining_turns_after_this_turn: {remaining_after}",
            f"- expires_at: {_safe_str(state.get('expires_at'), 'unknown')}",
            f"- correction_summary: {_trim(state.get('owner_correction'), limit=160)}",
            f"- behavior_bias: {direction_text}",
            f"- mode_hints: {hints_text}",
            f"- avoid: {avoid_text}",
            "- boundary: short-term runtime overlay only; do not mention overlays, gates, files, or scores.",
            "- stable_profile_write: blocked; promotion/review gate is still required for stable voice changes.",
        ]
    )


def clear_voice_trial_overlay(root: Path) -> bool:
    path = root / OVERLAY_REL
    if not voice_trial_overlay_state_exists(path):
        return False
    state = _read_state(path)
    state["status"] = "cleared"
    state["remaining_turns"] = 0
    state["reply_excerpt"] = ""
    state["updated_at"] = _now().isoformat(timespec="seconds")
    _write_state(path, state)
    return True
