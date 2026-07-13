from __future__ import annotations


__all__ = (
    "STATE_MD_REL",
    "TRACE_REL",
)

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_turn_coherence_store import MEMORY_BRAID_STATE_REL
from xinyu_turn_coherence_store import PRIVATE_THOUGHT_STATE_REL
from xinyu_turn_coherence_store import PROACTIVE_REQUEST_STATE_REL
from xinyu_turn_coherence_store import SELF_THOUGHT_STATE_REL
from xinyu_turn_coherence_store import append_turn_coherence_trace_event
from xinyu_turn_coherence_store import read_turn_coherence_source_text
from xinyu_turn_coherence_store import write_turn_coherence_state_text


from xinyu_browser_control import STATE_MD_REL

from xinyu_action_feedback_coverage import TRACE_REL

def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat()


def _parse_iso(value: Any) -> datetime | None:
    text = _one_line(value)
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


@dataclass(frozen=True, slots=True)
class TurnCoherenceSnapshot:
    checked_at: str
    phase: str
    turn_id: str
    turn_spine: str
    speaker_relation: str
    current_turn_intent: str
    memory_lane: str
    thought_lane: str
    action_lane: str
    consistency_contract: str
    prompt_block: str


def build_turn_coherence_prompt_block(
    root: Path,
    *,
    payload: dict[str, Any] | None = None,
    user_text: str = "",
    turn_id: str = "",
    memory_braid_block: str = "",
    recalled_context: str = "",
    continuity_context: str = "",
    runtime_presence_context: str = "",
    persona_context: str = "",
    emotion_council_context: str = "",
    recent_action_context: str = "",
    action_digest_context: str = "",
    checked_at: str | None = None,
    write_state: bool = False,
    max_chars: int = 2200,
) -> str:
    snapshot = build_turn_coherence_snapshot(
        root,
        payload=payload,
        user_text=user_text,
        turn_id=turn_id,
        memory_braid_block=memory_braid_block,
        recalled_context=recalled_context,
        continuity_context=continuity_context,
        runtime_presence_context=runtime_presence_context,
        persona_context=persona_context,
        emotion_council_context=emotion_council_context,
        recent_action_context=recent_action_context,
        action_digest_context=action_digest_context,
        checked_at=checked_at,
        max_chars=max_chars,
    )
    if write_state:
        write_turn_coherence_state(root, snapshot)
        append_turn_coherence_trace(root, snapshot, event_kind="turn_coherence_started")
    return snapshot.prompt_block


def build_turn_coherence_snapshot(
    root: Path,
    *,
    payload: dict[str, Any] | None = None,
    user_text: str = "",
    turn_id: str = "",
    memory_braid_block: str = "",
    recalled_context: str = "",
    continuity_context: str = "",
    runtime_presence_context: str = "",
    persona_context: str = "",
    emotion_council_context: str = "",
    recent_action_context: str = "",
    action_digest_context: str = "",
    checked_at: str | None = None,
    max_chars: int = 2200,
) -> TurnCoherenceSnapshot:
    root = root.resolve()
    checked_at = _timestamp_or_now_iso(checked_at)
    speaker_relation = _speaker_relation(payload)
    current_turn_intent = _classify_turn_intent(user_text)
    memory_lane = _memory_lane(
        root,
        memory_braid_block=memory_braid_block,
        recalled_context=recalled_context,
        continuity_context=continuity_context,
    )
    thought_lane = _thought_lane(
        root,
        persona_context=persona_context,
        emotion_council_context=emotion_council_context,
    )
    action_lane = _action_lane(
        root,
        user_text=user_text,
        runtime_presence_context=runtime_presence_context,
        recent_action_context=recent_action_context,
        action_digest_context=action_digest_context,
    )
    consistency_contract = _consistency_contract(current_turn_intent=current_turn_intent)
    turn_spine = _turn_spine(turn_id=turn_id, current_turn_intent=current_turn_intent)
    lines = [
        "## Turn Coherence Runtime Context",
        "scope: hidden turn-level alignment for memory, thought, and action.",
        "not_a_template: true",
        f"turn_id: {turn_id or 'unknown'}",
        f"turn_spine: {turn_spine}",
        f"speaker_relation: {speaker_relation}",
        f"current_turn_intent: {current_turn_intent}",
        f"memory_lane: {memory_lane}",
        f"thought_lane: {thought_lane}",
        f"action_lane: {action_lane}",
        f"consistency_contract: {consistency_contract}",
        "",
        "### Coherence Rules",
        "- The memory lane, thought lane, visible reply, and action lane must all treat turn_spine as the same active cause.",
        "- The visible reply, memory candidates, private-thought link, and any action/follow-up must all answer the same current user message.",
        "- Do not let background proactive requests, impulse pressure, old dreams, or stale runtime state hijack this turn.",
        "- If the owner is pointing at fragmentation, template behavior, or memory/thought/action mismatch, treat that as a coherence repair turn even when project or architecture words also appear.",
        "- If the current turn asks for action, perform or delegate the bounded action and let memory/thought record that action path.",
        "- If the current turn is ordinary chat, do not create an unrelated action just because an action subsystem has residue.",
        "- If memory says one thing and the owner corrects it now, the owner correction wins for this turn and should become reviewable memory evidence.",
        "- Keep internal labels and mechanics hidden unless the owner is explicitly asking about runtime/design.",
    ]
    prompt = "\n".join(lines)[:max_chars].rstrip()
    return TurnCoherenceSnapshot(
        checked_at=checked_at,
        phase="pre_reply",
        turn_id=turn_id or "unknown",
        turn_spine=turn_spine,
        speaker_relation=speaker_relation,
        current_turn_intent=current_turn_intent,
        memory_lane=memory_lane,
        thought_lane=thought_lane,
        action_lane=action_lane,
        consistency_contract=consistency_contract,
        prompt_block=prompt,
    )


def finish_turn_coherence(
    root: Path,
    *,
    turn_id: str,
    payload: dict[str, Any] | None = None,
    user_text: str = "",
    reply: str = "",
    action_result: str = "none",
    memory_changed: bool = False,
    final_guard_flags: list[str] | tuple[str, ...] | None = None,
    component_notes: dict[str, Any] | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    checked_at = _timestamp_or_now_iso(checked_at)
    current_turn_intent = _classify_turn_intent(user_text)
    memory_lane = "changed" if memory_changed else "observed"
    thought_lane = _finish_thought_lane(component_notes or {})
    action_lane = _finish_action_lane(
        action_result=action_result,
        component_notes=component_notes or {},
        current_turn_intent=current_turn_intent,
    )
    contract = _consistency_contract(current_turn_intent=current_turn_intent)
    turn_spine = _turn_spine(turn_id=turn_id, current_turn_intent=current_turn_intent)
    flags = [str(flag) for flag in (final_guard_flags or []) if str(flag).strip()]
    notes = ["turn_coherence_finished", f"turn_intent:{current_turn_intent}", f"action_lane:{action_lane}"]
    if flags:
        notes.append("final_guard_seen")
    snapshot = TurnCoherenceSnapshot(
        checked_at=checked_at,
        phase="post_reply",
        turn_id=turn_id or "unknown",
        turn_spine=turn_spine,
        speaker_relation=_speaker_relation(payload),
        current_turn_intent=current_turn_intent,
        memory_lane=memory_lane,
        thought_lane=thought_lane,
        action_lane=action_lane,
        consistency_contract=contract,
        prompt_block="",
    )
    write_turn_coherence_state(
        root,
        snapshot,
        reply_preview=_clip(reply, 220),
        final_guard_flags=flags,
        component_notes=component_notes or {},
    )
    append_turn_coherence_trace(
        root,
        snapshot,
        event_kind="turn_coherence_finished",
        extra={
            "reply_hash": _hash_text(reply, 16) if reply else "",
            "reply_preview": _clip(reply, 120),
            "final_guard_flags": flags,
            "component_notes": _compact_component_notes(component_notes or {}),
        },
    )
    return {
        "written": True,
        "turn_id": snapshot.turn_id,
        "current_turn_intent": current_turn_intent,
        "memory_lane": memory_lane,
        "thought_lane": thought_lane,
        "action_lane": action_lane,
        "notes": notes,
    }


def write_turn_coherence_state(
    root: Path,
    snapshot: TurnCoherenceSnapshot,
    *,
    reply_preview: str = "",
    final_guard_flags: list[str] | tuple[str, ...] | None = None,
    component_notes: dict[str, Any] | None = None,
) -> None:
    flag_lines = "\n".join(f"- {flag}" for flag in (final_guard_flags or [])) or "- none"
    component_lines = "\n".join(
        f"- {key}: {', '.join(_as_note_list(value)[:4]) or 'none'}"
        for key, value in (component_notes or {}).items()
    ) or "- none"
    lines = [
        "---",
        "title: Turn Coherence State",
        "memory_type: turn_coherence_state",
        "time_scope: short_term",
        "subject_ids: [xinyu]",
        "protected: true",
        "source: xinyu_turn_coherence",
        f"updated_at: {_timestamp_or_now_iso(snapshot.checked_at)}",
        "status: active",
        "tags: [turn, coherence, memory, thought, action]",
        "---",
        "",
        "# Turn Coherence State",
        "",
        "## Summary",
        f"- checked_at: {snapshot.checked_at}",
        f"- phase: {snapshot.phase}",
        f"- turn_id: {snapshot.turn_id}",
        f"- turn_spine: {snapshot.turn_spine}",
        f"- speaker_relation: {snapshot.speaker_relation}",
        f"- current_turn_intent: {snapshot.current_turn_intent}",
        f"- memory_lane: {snapshot.memory_lane}",
        f"- thought_lane: {snapshot.thought_lane}",
        f"- action_lane: {snapshot.action_lane}",
        f"- consistency_contract: {snapshot.consistency_contract}",
        f"- reply_preview: {reply_preview or 'none'}",
        "",
        "## Final Guard Flags",
        flag_lines,
        "",
        "## Component Notes",
        component_lines,
        "",
        "## Boundary",
        "- this file aligns memory, thought, and action for one turn; it is not a reply template",
        "- memory/thought/action should use the same turn_spine before creating new residue or follow-up",
        "- ordinary QQ chat must not quote this file or its field names",
    ]
    write_turn_coherence_state_text(root, "\n".join(lines))


def append_turn_coherence_trace(
    root: Path,
    snapshot: TurnCoherenceSnapshot,
    *,
    event_kind: str,
    extra: dict[str, Any] | None = None,
) -> None:
    event = {
        "event_kind": event_kind,
        "observed_at": _timestamp_or_now_iso(snapshot.checked_at),
        **snapshot_to_json(snapshot),
    }
    event.update(extra or {})
    append_turn_coherence_trace_event(root, event)


def snapshot_to_json(snapshot: TurnCoherenceSnapshot) -> dict[str, Any]:
    data = asdict(snapshot)
    data.pop("prompt_block", None)
    return data


def _speaker_relation(payload: dict[str, Any] | None) -> str:
    metadata = payload.get("metadata") if isinstance(payload, dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}
    if _as_bool(metadata.get("is_owner_user"), default=False):
        return "owner"
    if _as_bool(metadata.get("is_trusted_user"), default=False):
        return "trusted_contact"
    return "external_or_group"


def _classify_turn_intent(user_text: str) -> str:
    compact = re.sub(r"\s+", "", user_text or "").lower()
    if not compact:
        return "empty"
    if any(marker in compact for marker in ("叫我什么", "称呼", "我是谁")):
        return "identity_or_address_check"
    if any(marker in compact for marker in ("记忆", "思维", "动作", "割裂", "一致", "串起来", "人格")):
        return "coherence_pressure"
    if any(
        marker in compact
        for marker in (
            "一致性",
            "串联",
            "串在一起",
            "接起来",
            "统一起来",
            "相互独立",
            "各自玩各自",
            "一起工作",
            "模板",
            "模版",
            "活生生",
            "不像人",
            "像人",
            "心声",
            "情感",
        )
    ):
        return "coherence_pressure"
    if any(
        marker in compact
        for marker in (
            "修复",
            "改代码",
            "实现",
            "测试",
            "检查",
            "debug",
            "部署",
            "项目",
            "架构",
            "还没修",
            "修好",
            "修完",
            "现在好了吗",
            "现在好了么",
            "现在好了嗎",
            "现在好了没",
        )
    ):
        return "technical_or_repair_action"
    if any(marker in compact for marker in ("查", "搜索", "看看", "找一下", "调用", "codex")):
        return "bounded_action_or_lookup"
    return "ordinary_chat"


def _turn_spine(*, turn_id: str, current_turn_intent: str) -> str:
    turn = _one_line(turn_id) or "unknown"
    intent = _one_line(current_turn_intent) or "ordinary_chat"
    return f"{turn}|{intent}"


def _memory_lane(root: Path, *, memory_braid_block: str, recalled_context: str, continuity_context: str) -> str:
    if _one_line(memory_braid_block):
        return "memory_braid_active"
    state = _read(root, MEMORY_BRAID_STATE_REL, limit=1200)
    if _one_line(state):
        return "memory_braid_state_available"
    if _one_line(recalled_context) or _one_line(continuity_context):
        return "context_recall_or_continuity_available"
    return "stable_memory_only"


def _thought_lane(root: Path, *, persona_context: str, emotion_council_context: str) -> str:
    private_state = _read(root, PRIVATE_THOUGHT_STATE_REL, limit=1200)
    self_thought = _read(root, SELF_THOUGHT_STATE_REL, limit=1200)
    active_private = _field(private_state, "event_id")
    self_focus = _field(self_thought, "focus_kind") or _field(self_thought, "focus")
    parts: list[str] = []
    if active_private and active_private != "none":
        parts.append(f"private_thought={active_private}")
    if self_focus and self_focus != "none":
        parts.append(f"self_thought={self_focus}")
    if _one_line(persona_context):
        parts.append("persona_sidecar")
    if _one_line(emotion_council_context):
        parts.append("emotion_council_hidden")
    return ";".join(parts) if parts else "quiet_observation"


def _action_lane(
    root: Path,
    *,
    user_text: str,
    runtime_presence_context: str,
    recent_action_context: str,
    action_digest_context: str,
) -> str:
    intent = _classify_turn_intent(user_text)
    proactive = _read(root, PROACTIVE_REQUEST_STATE_REL, limit=900)
    if intent in {"technical_or_repair_action", "bounded_action_or_lookup"}:
        return "current_turn_may_require_bounded_action"
    if intent == "coherence_pressure":
        return "current_turn_requests_coherence_repair"
    if _field(proactive, "status") in {"ready", "active"}:
        return "background_proactive_exists_but_current_turn_wins"
    if _one_line(recent_action_context) or _one_line(action_digest_context):
        return "recent_action_context_available_for_followup_only"
    if "codex_status: running" in runtime_presence_context.lower():
        return "codex_running_background_only"
    return "no_action_unless_current_turn_requests"


def _finish_thought_lane(component_notes: dict[str, Any]) -> str:
    parts: list[str] = []
    if _as_note_list(component_notes.get("private_thought_link")):
        parts.append("private_thought_linked_to_visible_reply")
    if _as_note_list(component_notes.get("private_thought_outcome")):
        parts.append("private_thought_outcome_observed")
    if _as_note_list(component_notes.get("emotion_council")):
        parts.append("emotion_council_observed")
    if _as_note_list(component_notes.get("persona_sidecar")):
        parts.append("persona_state_observed")
    if _as_note_list(component_notes.get("learning_closed_loop")):
        parts.append("learning_closed_loop_observed")
    return ";".join(parts) if parts else "observed"


def _finish_action_lane(
    *,
    action_result: str,
    component_notes: dict[str, Any],
    current_turn_intent: str,
) -> str:
    if action_result and action_result != "none":
        return action_result
    if current_turn_intent == "coherence_pressure":
        return "coherence_reply_or_repair_recorded"
    if _as_note_list(component_notes.get("promised_followup")):
        return "promised_followup_considered"
    if _as_note_list(component_notes.get("sticker_reply")):
        return "sticker_reply_considered"
    return "no_action_taken"


def _consistency_contract(*, current_turn_intent: str) -> str:
    if current_turn_intent in {"technical_or_repair_action", "bounded_action_or_lookup"}:
        return "action-first: memory and thought should record the chosen action path, not drift into unrelated reflection"
    if current_turn_intent == "coherence_pressure":
        return "coherence-first: explain or repair the integration gap, then align memory/thought/action records to that repair"
    if current_turn_intent == "identity_or_address_check":
        return "identity-first: stable owner/persona facts win over stale relationship labels"
    return "conversation-first: memory, thought, and action remain background unless the current sentence needs them"


def _compact_component_notes(component_notes: dict[str, Any]) -> dict[str, list[str]]:
    return {str(key): _as_note_list(value)[:6] for key, value in component_notes.items()}


def _as_note_list(value: Any) -> list[str]:
    if isinstance(value, dict):
        raw = value.get("notes", [])
    else:
        raw = value
    if isinstance(raw, (list, tuple)):
        return [_clip(item, 80) for item in raw if _one_line(item)]
    if _one_line(raw):
        return [_clip(raw, 80)]
    return []


def _field(text: str, key: str) -> str:
    match = re.search(rf"(?im)^\s*-?\s*{re.escape(key)}\s*:\s*(.*?)\s*$", text or "")
    return _one_line(match.group(1)) if match else ""


def _read(root: Path, rel_path: str | Path, *, limit: int) -> str:
    return read_turn_coherence_source_text(root, rel_path, limit=limit)


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


def _one_line(value: Any) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def _clip(value: Any, limit: int = 180) -> str:
    text = _one_line(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _hash_text(text: str, length: int = 16) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]

