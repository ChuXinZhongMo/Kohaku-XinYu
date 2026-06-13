from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_self_state_capsule_store import read_self_state_capsule_context_text
from xinyu_self_state_capsule_store import write_self_state_capsule_state
from xinyu_text_variants import readable_markers


STATE_REL = Path("memory/context/self_state_capsule_state.md")

STATE_QUERY_MARKERS = readable_markers(
    "\u4f60\u73b0\u5728",
    "\u4f60\u8fd9\u8fb9",
    "\u4f60\u81ea\u5df1",
    "\u72b6\u6001",
    "\u4ec0\u4e48\u72b6\u6001",
    "\u600e\u4e48\u6837",
    "\u548b\u6837",
    "\u5982\u4f55",
    "\u8fd8\u597d\u5417",
    "\u8fd8\u597d\u4e48",
    "\u4f60\u8fd8\u597d",
)
FEELING_QUERY_MARKERS = readable_markers(
    "\u611f\u89c9",
    "\u611f\u53d7",
    "\u5fc3\u60c5",
    "\u7d2f\u4e0d\u7d2f",
    "\u56f0\u4e0d\u56f0",
    "\u96be\u53d7",
    "\u7d27\u5f20",
)
THOUGHT_QUERY_MARKERS = readable_markers(
    "\u5728\u60f3\u4ec0\u4e48",
    "\u60f3\u4ec0\u4e48",
    "\u4f60\u5728\u60f3",
    "\u4f60\u60f3\u5230\u4ec0\u4e48",
    "\u8111\u5b50\u91cc",
)
DELAY_QUERY_MARKERS = readable_markers(
    "\u600e\u4e48\u4e0d\u56de",
    "\u4e3a\u4ec0\u4e48\u4e0d\u56de",
    "\u6ca1\u56de",
    "\u6ca1\u53cd\u5e94",
    "\u5361\u4e86",
    "\u521a\u521a\u5361",
    "\u7b49\u4e86\u5f88\u4e45",
    "\u5f88\u4e45\u624d\u56de",
    "\u6162\u4e86",
)
STYLE_PRESSURE_MARKERS = readable_markers(
    "\u6a21\u677f",
    "\u5957\u8bdd",
    "\u5ba2\u670d",
    "\u4e0d\u50cf\u4eba",
    "\u4e0d\u81ea\u7136",
    "AI\u5473",
    "GPT\u5473",
)


@dataclass(frozen=True, slots=True)
class SelfStateCapsule:
    active: bool
    query_kind: str = "none"
    posture: str = "ordinary_reply"
    recent_pressure: str = "none"
    runtime_feel: str = "steady"
    memory_basis: str = "current_turn_first"
    reply_contract: str = "natural_owner_private_line"
    notes: tuple[str, ...] = ()

    def prompt_block(self) -> str:
        if not self.active:
            return ""
        notes = ", ".join(self.notes) if self.notes else "none"
        return "\n".join(
            [
                "self state capsule sidecar:",
                f"- query_kind: {self.query_kind}",
                f"- posture: {self.posture}",
                f"- recent_pressure: {self.recent_pressure}",
                f"- runtime_feel: {self.runtime_feel}",
                f"- memory_basis: {self.memory_basis}",
                f"- reply_contract: {self.reply_contract}",
                f"- notes: {notes}",
                (
                    "- behavior: answer this as XinYu's present first-person state, not as a service status, "
                    "system report, apology, or repair promise."
                ),
                (
                    "- use_memory: let recalled context and recent relationship pressure shape the feeling, "
                    "but do not list memory sources or quote internal labels."
                ),
                (
                    "- for_delay_or_no_reply: acknowledge the lag as a lived interruption or slow gathering of "
                    "the current exchange; do not mention backend, model, prompt, bridge, queue, or tool calls."
                ),
                (
                    "- forbidden_surface: no canned presence line, no empty promise to improve later, no customer-service "
                    "wording, no numbered postmortem, no mechanism names."
                ),
            ]
        )


def build_self_state_capsule(
    root: Path | str,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    visible_turn: Any | None = None,
    recalled_context: str = "",
    runtime_presence_context: str = "",
    persona_context: str = "",
    emotion_council_context: str = "",
    write_state: bool = False,
) -> SelfStateCapsule:
    root_path = Path(root)
    if not _owner_private(payload):
        return SelfStateCapsule(active=False, notes=("not_owner_private",))

    query_kind = classify_self_state_query(user_text)
    owner_pressure = _owner_pressure(visible_turn, user_text=user_text)
    if query_kind == "none" and not owner_pressure:
        return SelfStateCapsule(active=False, notes=("not_self_state_query",))

    fields = _load_runtime_fields(root_path)
    recent_pressure = _recent_pressure(fields, owner_pressure=owner_pressure)
    runtime_feel = _runtime_feel(fields, runtime_presence_context=runtime_presence_context, query_kind=query_kind)
    memory_basis = _memory_basis(
        recalled_context=recalled_context,
        persona_context=persona_context,
        emotion_council_context=emotion_council_context,
        fields=fields,
    )
    capsule = SelfStateCapsule(
        active=True,
        query_kind=query_kind if query_kind != "none" else "style_pressure_self_state",
        posture=_posture_for(query_kind=query_kind, owner_pressure=owner_pressure),
        recent_pressure=recent_pressure,
        runtime_feel=runtime_feel,
        memory_basis=memory_basis,
        reply_contract="one_or_two_present_tense_owner_private_sentences",
        notes=_notes_for(query_kind=query_kind, owner_pressure=owner_pressure, fields=fields),
    )
    if write_state:
        _write_state(root_path, capsule)
    return capsule


def build_self_state_capsule_prompt_block(
    root: Path | str,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    visible_turn: Any | None = None,
    recalled_context: str = "",
    runtime_presence_context: str = "",
    persona_context: str = "",
    emotion_council_context: str = "",
    write_state: bool = True,
) -> str:
    return build_self_state_capsule(
        root,
        payload,
        user_text=user_text,
        visible_turn=visible_turn,
        recalled_context=recalled_context,
        runtime_presence_context=runtime_presence_context,
        persona_context=persona_context,
        emotion_council_context=emotion_council_context,
        write_state=write_state,
    ).prompt_block()


def classify_self_state_query(user_text: str) -> str:
    text = _safe_str(user_text)
    if _contains_any(text, DELAY_QUERY_MARKERS):
        return "delay_or_no_reply"
    if _contains_any(text, THOUGHT_QUERY_MARKERS):
        return "thought_inquiry"
    if _contains_any(text, FEELING_QUERY_MARKERS):
        return "feeling_inquiry"
    if _contains_any(text, STATE_QUERY_MARKERS):
        return "state_inquiry"
    return "none"


def _owner_private(payload: dict[str, Any] | None) -> bool:
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    is_owner = _as_bool(payload.get("is_owner_user") or metadata.get("is_owner_user"), default=False)
    message_type = _safe_str(payload.get("message_type") or metadata.get("message_type")).lower()
    group_id = _safe_str(payload.get("group_id") or metadata.get("group_id")).strip()
    session_id = _safe_str(payload.get("session_id") or metadata.get("session_id")).lower()
    if not is_owner or group_id or message_type.startswith("group"):
        return False
    return "private" in message_type or session_id.startswith("qq:private:") or not message_type


def _owner_pressure(visible_turn: Any | None, *, user_text: str) -> bool:
    if _contains_any(user_text, STYLE_PRESSURE_MARKERS):
        return True
    if visible_turn is None:
        return False
    return any(
        _as_bool(getattr(visible_turn, name, False), default=False)
        for name in ("owner_style_pressure", "owner_no_change_pressure", "relationship_pressure", "rest_silence")
    )


def _load_runtime_fields(root: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for label, rel in (
        ("presence", "memory/context/runtime_self_presence.md"),
        ("persona_surface", "memory/context/persona_surface_state.md"),
        ("learning", "memory/self/learning_closed_loop_state.md"),
        ("expression", "memory/self/expression_self_learning_state.md"),
        ("interaction", "memory/context/interaction_journal_state.md"),
        ("early_shadow", "memory/context/early_visible_segment_shadow_state.md"),
    ):
        for key, value in _read_markdown_fields(root / rel).items():
            fields[f"{label}.{key}"] = value
    return fields


def _recent_pressure(fields: dict[str, str], *, owner_pressure: bool) -> str:
    latest_failure = fields.get("learning.latest_failure_kind", "")
    expression_failure = fields.get("expression.failure_kind", "")
    if owner_pressure:
        return "owner_current_style_or_relation_pressure"
    if "template" in latest_failure or "template" in expression_failure:
        return "recent_template_voice_repair_pressure"
    if fields.get("early_shadow.status") == "shadow_observing":
        return "slow_reply_shadow_under_observation"
    return "none"


def _runtime_feel(fields: dict[str, str], *, runtime_presence_context: str, query_kind: str) -> str:
    joined = "\n".join([runtime_presence_context, *fields.values()]).lower()
    if query_kind == "delay_or_no_reply":
        return "lag_sensitive_gathering_current_turn"
    if "current_turn_state: running" in joined or "current_turn_state=running" in joined:
        return "mid_turn_concentrating"
    if "last_reply_elapsed_ms" in joined:
        elapsed = _safe_int(fields.get("interaction.last_reply_elapsed_ms"))
        if elapsed >= 12000:
            return "recent_reply_was_slow"
    return "steady_with_recent_context"


def _memory_basis(
    *,
    recalled_context: str,
    persona_context: str,
    emotion_council_context: str,
    fields: dict[str, str],
) -> str:
    pieces = []
    if _safe_str(recalled_context).strip():
        pieces.append("recalled_context")
    if _safe_str(persona_context).strip() or fields.get("persona_surface.status"):
        pieces.append("persona_surface")
    if _safe_str(emotion_council_context).strip():
        pieces.append("emotion_council")
    if fields.get("learning.status"):
        pieces.append("learning_closed_loop")
    return ",".join(pieces) if pieces else "current_turn_first"


def _posture_for(*, query_kind: str, owner_pressure: bool) -> str:
    if owner_pressure:
        return "close_to_current_exchange_no_self_report"
    if query_kind == "delay_or_no_reply":
        return "acknowledge_delay_without_mechanics"
    if query_kind == "thought_inquiry":
        return "name_current_focus_not_backend"
    return "felt_state_from_current_context"


def _notes_for(*, query_kind: str, owner_pressure: bool, fields: dict[str, str]) -> tuple[str, ...]:
    notes = ["self_state_capsule_v1"]
    if query_kind != "none":
        notes.append(query_kind)
    if owner_pressure:
        notes.append("owner_pressure")
    if fields.get("expression.failure_kind"):
        notes.append("expression_learning_active")
    if fields.get("learning.latest_failure_kind"):
        notes.append("learning_loop_active")
    return tuple(notes[:6])


def _write_state(root: Path, capsule: SelfStateCapsule) -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "---",
        "memory_type: self_state_capsule_state",
        f"updated_at: {now}",
        "privacy: no_raw_user_text",
        "---",
        "",
        "# Self State Capsule",
        "",
        f"- active: {str(capsule.active).lower()}",
        f"- query_kind: {capsule.query_kind}",
        f"- posture: {capsule.posture}",
        f"- recent_pressure: {capsule.recent_pressure}",
        f"- runtime_feel: {capsule.runtime_feel}",
        f"- memory_basis: {capsule.memory_basis}",
        f"- reply_contract: {capsule.reply_contract}",
        "- raw_user_text_saved: false",
        "- raw_memory_body_saved: false",
        "",
        "Hidden current-turn state for owner-private status, feeling, thought, and delay questions.",
    ]
    write_self_state_capsule_state(root / STATE_REL, "\n".join(lines))


def _read_markdown_fields(path: Path) -> dict[str, str]:
    text = read_self_state_capsule_context_text(path)
    if not text:
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        match = re.match(r"^([A-Za-z0-9_]+):\s*(.*?)\s*$", stripped)
        if match:
            fields[match.group(1)] = _clip(match.group(2), limit=180)
    return fields


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _safe_str(text).lower()
    compact = "".join(lowered.split())
    for marker in markers:
        clean = _safe_str(marker).lower()
        if clean and (clean in lowered or "".join(clean.split()) in compact):
            return True
    return False


def _clip(text: Any, *, limit: int) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = _safe_str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(_safe_str(value)))
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)
