from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_REL = Path("memory/context/desire_drive_state.md")
TRACE_REL = Path("runtime/desire_drive_trace.jsonl")

QUIET_DRIVES = {"", "none", "missing", "unknown", "quiet", "quiet_continuity"}
QQ_ONLY_BLOCKS = {
    "qq_send_disabled_for_dream_v0",
    "qq_send_disabled_for_owner_long_idle_v0",
}


@dataclass(frozen=True, slots=True)
class DesireDriveSnapshot:
    checked_at: str
    trigger: str
    drive_id: str
    status: str
    dominant_drive: str
    drive_intensity: int
    autonomy_tension: str
    blocked_by: tuple[str, ...]
    candidate_effect: str
    feedback_effect: str
    next_safe_action: str
    source_summary: str


def run_desire_drive_state(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
    write_state: bool = True,
) -> dict[str, Any]:
    snapshot = build_desire_drive_snapshot(root, checked_at=checked_at, trigger=trigger)
    if write_state:
        write_desire_drive_state(root, snapshot)
        append_desire_drive_trace(root, snapshot)
    return {
        "accepted": True,
        "status": snapshot.status,
        "checked_at": snapshot.checked_at,
        "drive_id": snapshot.drive_id,
        "dominant_drive": snapshot.dominant_drive,
        "drive_intensity": snapshot.drive_intensity,
        "autonomy_tension": snapshot.autonomy_tension,
        "blocked_by": list(snapshot.blocked_by),
        "candidate_effect": snapshot.candidate_effect,
        "feedback_effect": snapshot.feedback_effect,
        "next_safe_action": snapshot.next_safe_action,
        "boundaries": _boundaries(),
    }


def build_desire_drive_snapshot(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
) -> DesireDriveSnapshot:
    root = root.resolve()
    checked = _timestamp_or_now_iso(checked_at)
    trigger = _clean_token(trigger or "manual")
    sources = _read_sources(root)
    thought = _fields(sources["thought"])
    impulse = _fields(sources["impulse"])
    decision = _fields(sources["decision"])
    lifecycle = _fields(sources["lifecycle"])
    spine = _fields(sources["spine"])
    feedback = _fields(sources["feedback"])

    dominant_drive = _dominant_drive(thought, impulse, decision, spine)
    drive_intensity = _drive_intensity(dominant_drive, impulse, decision, spine, lifecycle)
    blocked_by = _blocked_by(decision, lifecycle, spine)
    candidate_effect = _candidate_effect(decision, lifecycle)
    feedback_effect = _clean_value(feedback.get("future_effect") or "none")
    autonomy_tension = _autonomy_tension(
        intensity=drive_intensity,
        blocked_by=blocked_by,
        candidate_effect=candidate_effect,
        decision=decision,
        lifecycle=lifecycle,
        spine=spine,
    )
    next_safe_action = _next_safe_action(
        autonomy_tension=autonomy_tension,
        candidate_effect=candidate_effect,
        blocked_by=blocked_by,
        decision=decision,
        spine=spine,
    )
    status = "quiet" if drive_intensity <= 0 else "active"
    source_summary = _clip(
        " ".join(
            [
                f"dominant={dominant_drive}",
                f"impulse={impulse.get('top_desire_shape', 'none')}:{_safe_int(impulse.get('top_energy'), 0)}",
                f"proactive={decision.get('source_type', 'none')}:{_safe_int(decision.get('total_score'), 0)}",
                f"spine={spine.get('emergence_level', 'none')}",
            ]
        ),
        320,
    )
    return DesireDriveSnapshot(
        checked_at=checked,
        trigger=trigger,
        drive_id=_drive_id(checked, dominant_drive, drive_intensity, candidate_effect),
        status=status,
        dominant_drive=dominant_drive,
        drive_intensity=drive_intensity,
        autonomy_tension=autonomy_tension,
        blocked_by=blocked_by,
        candidate_effect=candidate_effect,
        feedback_effect=feedback_effect,
        next_safe_action=next_safe_action,
        source_summary=source_summary,
    )


def write_desire_drive_state(root: Path, snapshot: DesireDriveSnapshot) -> Path:
    lines = [
        "---",
        "title: Desire Drive State",
        "memory_type: desire_drive_state",
        "time_scope: short_term",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: xinyu_desire_drive_state",
        f"updated_at: {snapshot.checked_at}",
        f"status: {snapshot.status}",
        "tags: [desire, autonomy, initiative, boundary]",
        "---",
        "",
        "# Desire Drive State",
        "",
        "## Summary",
        f"- checked_at: {snapshot.checked_at}",
        f"- trigger: {snapshot.trigger}",
        f"- drive_id: {snapshot.drive_id}",
        f"- status: {snapshot.status}",
        f"- dominant_drive: {snapshot.dominant_drive}",
        f"- drive_intensity: {snapshot.drive_intensity}",
        f"- autonomy_tension: {snapshot.autonomy_tension}",
        f"- blocked_by: {_join_or_none(snapshot.blocked_by)}",
        f"- candidate_effect: {snapshot.candidate_effect}",
        f"- feedback_effect: {snapshot.feedback_effect}",
        f"- next_safe_action: {snapshot.next_safe_action}",
        f"- source_summary: {snapshot.source_summary}",
        "",
        "## Boundaries",
    ]
    for key, value in _boundaries().items():
        lines.append(f"- {key}: {value}")
    path = root / STATE_REL
    _write_text_atomic(path, "\n".join(lines).rstrip() + "\n")
    return path


def append_desire_drive_trace(root: Path, snapshot: DesireDriveSnapshot) -> Path:
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    event = asdict(snapshot)
    event["event_kind"] = "desire_drive_state_observed"
    event["observed_at"] = snapshot.checked_at
    event["boundaries"] = _boundaries()
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def _read_sources(root: Path) -> dict[str, str]:
    return {
        "thought": _read(root / "memory/context/thought_seeds.md", limit=5000),
        "impulse": _read(root / "memory/context/impulse_soup_state.md", limit=5000),
        "decision": _read(root / "memory/context/proactive_decision_state.md", limit=5000),
        "lifecycle": _read(root / "memory/context/initiative_lifecycle_state.md", limit=5000),
        "spine": _read(root / "memory/context/initiative_spine_state.md", limit=5000),
        "feedback": _read(root / "memory/context/initiative_feedback_state.md", limit=3000),
    }


def _dominant_drive(
    thought: dict[str, str],
    impulse: dict[str, str],
    decision: dict[str, str],
    spine: dict[str, str],
) -> str:
    for value in (
        thought.get("dominant_drive"),
        impulse.get("top_desire_shape"),
        decision.get("source_type"),
        spine.get("emergence_level"),
    ):
        cleaned = _clean_value(value)
        if cleaned.lower() not in QUIET_DRIVES:
            return cleaned
    return "quiet_continuity"


def _drive_intensity(
    dominant_drive: str,
    impulse: dict[str, str],
    decision: dict[str, str],
    spine: dict[str, str],
    lifecycle: dict[str, str],
) -> int:
    values = [
        _safe_int(impulse.get("top_energy"), 0),
        _safe_int(decision.get("total_score"), 0),
    ]
    if dominant_drive.lower() not in QUIET_DRIVES:
        values.append(40)
    if _clean_value(spine.get("emergence_level")).lower() not in QUIET_DRIVES:
        values.append(55)
    if _clean_value(lifecycle.get("selected_decision")).lower() == "desktop_inbox":
        values.append(max(values or [0]) + 10)
    return _clamp(max(values or [0]))


def _blocked_by(
    decision: dict[str, str],
    lifecycle: dict[str, str],
    spine: dict[str, str],
) -> tuple[str, ...]:
    blocks = [
        block
        for block in _split_tokens(decision.get("hard_blocks"))
        if block not in QQ_ONLY_BLOCKS
    ]
    selected = _clean_value(lifecycle.get("selected_decision")).lower()
    if selected == "blocked":
        blocks.append("initiative_gate_blocked")
    elif selected == "hold_private" and _safe_int(lifecycle.get("held_count"), 0) > 0:
        blocks.append("initiative_gate_held_private")
    action_permission = _clean_value(spine.get("action_permission")).lower()
    if action_permission in {"inner_only_impulse_boundary", "shadow_send_now_requires_non_shadow_gate"}:
        blocks.append(action_permission)
    return tuple(dict.fromkeys(block for block in blocks if block))


def _candidate_effect(decision: dict[str, str], lifecycle: dict[str, str]) -> str:
    selected = _clean_value(lifecycle.get("selected_decision")).lower()
    if selected == "desktop_inbox":
        return "local_desktop_candidate_visible"
    if selected == "hold_private":
        return "candidate_private_bias_only"
    if selected == "blocked":
        return "candidate_blocked"
    recommendation = _clean_value(decision.get("recommendation")).lower()
    preferred = _clean_value(decision.get("preferred_channel")).lower()
    if recommendation not in QUIET_DRIVES:
        return f"shadow_{recommendation}_{preferred or 'silent'}"
    return "none"


def _autonomy_tension(
    *,
    intensity: int,
    blocked_by: tuple[str, ...],
    candidate_effect: str,
    decision: dict[str, str],
    lifecycle: dict[str, str],
    spine: dict[str, str],
) -> str:
    if intensity <= 0:
        return "quiet"
    if candidate_effect == "local_desktop_candidate_visible":
        return "drive_visible_as_local_candidate"
    if blocked_by and _clean_value(lifecycle.get("selected_decision")).lower() != "desktop_inbox":
        return "drive_blocked_by_gate"
    action_permission = _clean_value(spine.get("action_permission")).lower()
    if action_permission == "proactive_request_gate_active":
        return "outward_candidate_gated"
    recommendation = _clean_value(decision.get("recommendation")).lower()
    preferred = _clean_value(decision.get("preferred_channel")).lower()
    if recommendation in {"inbox", "send_now"} and preferred in {"inbox", "qq"}:
        return "drive_waiting_for_surface_gate"
    return "inner_drive_only"


def _next_safe_action(
    *,
    autonomy_tension: str,
    candidate_effect: str,
    blocked_by: tuple[str, ...],
    decision: dict[str, str],
    spine: dict[str, str],
) -> str:
    if candidate_effect == "local_desktop_candidate_visible":
        return "wait_for_owner_feedback_on_desktop_candidate"
    if _clean_value(spine.get("action_permission")).lower() == "proactive_request_gate_active":
        return "keep_current_proactive_request_gated_until_owner_response"
    if blocked_by:
        return "keep_drive_private_until_blocks_clear"
    if autonomy_tension == "drive_waiting_for_surface_gate":
        source = _clean_value(decision.get("source_type"), "candidate")
        return f"route_{source}_through_initiative_orchestrator"
    return "observe_more_context_before_action"


def _boundaries() -> dict[str, str]:
    return {
        "no_qq_enqueue": "true",
        "no_gateway_bypass": "true",
        "stable_memory_write": "blocked",
        "self_action_approval": "unchanged",
        "raw_owner_text_retained": "false",
        "visible_reply_text_retained": "false",
        "consciousness_claim": "false",
    }


def _fields(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for key, value in re.findall(r"(?m)^\s*-?\s*([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$", text or ""):
        clean_key = key.strip()
        clean_value = _clean_value(value)
        if clean_key and clean_value:
            data[clean_key] = clean_value
    return data


def _read(path: Path, *, limit: int) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
    return text[:limit] if len(text) > limit else text


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return datetime.now().astimezone().isoformat()
    return parsed.astimezone().isoformat()


def _parse_iso(value: Any) -> datetime | None:
    text = _clean_value(value, "")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _drive_id(checked_at: str, dominant_drive: str, intensity: int, candidate_effect: str) -> str:
    material = f"{checked_at[:19]}|{dominant_drive}|{intensity}|{candidate_effect}"
    digest = hashlib.sha256(material.encode("utf-8", errors="replace")).hexdigest()[:12]
    stamp = re.sub(r"[^0-9T]", "", checked_at.replace("-", "").replace(":", ""))[:15]
    return f"desire-drive-{stamp}-{digest}"


def _split_tokens(value: Any) -> list[str]:
    text = _clean_value(value, "")
    if not text or text.lower() == "none":
        return []
    return [
        token.strip()
        for token in re.split(r"[,;\s]+", text)
        if token.strip() and token.strip().lower() != "none"
    ]


def _clean_value(value: Any, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    return text if text else default


def _clean_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.:-]+", "_", value.strip())
    return token.strip("_")[:80] or "manual"


def _safe_int(value: Any, default: int = 0) -> int:
    match = re.search(r"-?\d+", str(value or ""))
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


def _clip(value: str, limit: int) -> str:
    text = _clean_value(value)
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _join_or_none(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"


def main() -> int:
    root = Path(__file__).resolve().parent
    result = run_desire_drive_state(root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
