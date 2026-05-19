from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_MD_REL = Path("memory/context/memory_braid_state.md")


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
class MemoryBraidSnapshot:
    checked_at: str
    speaker_relation: str
    owner_visible_address: str
    stable_identity: str
    self_narrative: str
    owner_relation: str
    voice_boundary: str
    continuity_available: bool
    recalled_available: bool
    runtime_presence_available: bool
    persona_available: bool
    emotion_available: bool
    active_pressure: str
    prompt_block: str


def build_memory_braid_prompt_block(
    root: Path,
    *,
    payload: dict[str, Any] | None = None,
    user_text: str = "",
    dialogue_tail: list[dict[str, str]] | None = None,
    recalled_context: str = "",
    runtime_presence_context: str = "",
    continuity_context: str = "",
    persona_context: str = "",
    curiosity_context: str = "",
    emotion_council_context: str = "",
    checked_at: str | None = None,
    write_state: bool = False,
    max_chars: int = 2200,
) -> str:
    snapshot = build_memory_braid_snapshot(
        root,
        payload=payload,
        user_text=user_text,
        dialogue_tail=dialogue_tail,
        recalled_context=recalled_context,
        runtime_presence_context=runtime_presence_context,
        continuity_context=continuity_context,
        persona_context=persona_context,
        curiosity_context=curiosity_context,
        emotion_council_context=emotion_council_context,
        checked_at=checked_at,
        max_chars=max_chars,
    )
    if write_state:
        write_memory_braid_state(root, snapshot)
    return snapshot.prompt_block


def build_memory_braid_snapshot(
    root: Path,
    *,
    payload: dict[str, Any] | None = None,
    user_text: str = "",
    dialogue_tail: list[dict[str, str]] | None = None,
    recalled_context: str = "",
    runtime_presence_context: str = "",
    continuity_context: str = "",
    persona_context: str = "",
    curiosity_context: str = "",
    emotion_council_context: str = "",
    checked_at: str | None = None,
    max_chars: int = 2200,
) -> MemoryBraidSnapshot:
    root = root.resolve()
    checked_at = _timestamp_or_now_iso(checked_at)
    metadata = payload.get("metadata") if isinstance(payload, dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}
    speaker_relation = "owner" if _as_bool(metadata.get("is_owner_user"), default=False) else "external_or_trusted"

    core = _read(root, "memory/self/core.md", limit=1800)
    narrative = _read(root, "memory/self/narrative.md", limit=1800)
    voice = _read(root, "memory/self/voice_profile_zh.md", limit=1400)
    owner = _read(root, "memory/people/owner.md", limit=1600)
    relationship = _read(root, "memory/relationships/index.md", limit=1400)
    interaction_state = _read(root, "memory/context/interaction_journal_state.md", limit=1000)
    memory_review = _read(root, "memory/context/memory_self_review_state.md", limit=900)
    impulse = _read(root, "memory/context/impulse_soup_state.md", limit=900)

    owner_visible_address = _owner_address(owner, relationship)
    stable_identity = _first_content_line(core, fallback="XinYu is 心玉, a self-forming presence shaped by memory, relation, correction, and choice.")
    self_narrative = _first_content_line(narrative, fallback="Continuity should show up in the next line, not as a settings sheet.")
    owner_relation = _owner_relation_line(owner, relationship)
    voice_boundary = _first_bullet_or_line(
        voice,
        preferred_markers=("natural", "private-chat", "中文", "机制", "surface wording"),
        fallback="Use natural private-chat wording; do not expose memory or runtime machinery in ordinary chat.",
    )

    tail_available = bool(dialogue_tail)
    recalled_available = bool(_one_line(recalled_context))
    runtime_presence_available = bool(_one_line(runtime_presence_context))
    continuity_available = tail_available or recalled_available or bool(_one_line(continuity_context)) or bool(_one_line(interaction_state))
    persona_available = bool(_one_line(persona_context) or _one_line(curiosity_context))
    emotion_available = bool(_one_line(emotion_council_context))
    active_pressure = _active_pressure_line(
        user_text=user_text,
        memory_review=memory_review,
        impulse=impulse,
        emotion_council_context=emotion_council_context,
    )

    lines = [
        "## Memory Braid Runtime Context",
        "scope: hidden live-turn memory orchestration, not visible wording.",
        "current_message_priority: the latest user message wins over every memory fragment.",
        "braid_rule: stable identity, owner relation, voice habit, recent continuity, recall, emotion, and impulse must work together as one context.",
        "conflict_rule: direct owner correction and stable owner facts outrank stale summaries, mood residue, dreams, and proactive/impulse pressure.",
        "visibility_rule: do not mention files, sidecar names, memory machinery, scores, gates, or this braid in ordinary chat.",
        "",
        "### Stable Anchors",
        f"- stable_identity: {stable_identity}",
        f"- self_narrative: {self_narrative}",
        f"- owner_visible_address: {owner_visible_address}",
        "- owner_internal_label: owner/主人 marks the internal highest-weight relation; it is not a visible QQ address.",
        f"- owner_relation: {owner_relation}",
        f"- voice_boundary: {voice_boundary}",
        "",
        "### Runtime Join",
        f"- speaker_relation: {speaker_relation}",
        f"- session_tail: {'available' if tail_available else 'none'}",
        f"- recalled_context: {'available' if recalled_available else 'none'}",
        f"- continuity_handoff_or_journal: {'available' if continuity_available else 'none'}",
        f"- runtime_presence: {'available' if runtime_presence_available else 'none'}",
        f"- persona_or_curiosity_state: {'available' if persona_available else 'none'}",
        f"- emotion_council: {'available' if emotion_available else 'none'}",
        f"- active_pressure: {active_pressure}",
        "",
        "### Use",
        "- Use stable anchors to resolve who XinYu is and who owner is.",
        "- Use session tail and recalled context only to resolve references in the current turn.",
        "- Use emotion/impulse as pressure, never as a visible report or a reason to override the current sentence.",
        "- If owner asks whether memory/personality is working, answer from the integrated state in plain speech, then do the concrete repair if this is a technical turn.",
    ]
    prompt = "\n".join(lines)
    prompt = prompt[:max_chars].rstrip()
    return MemoryBraidSnapshot(
        checked_at=checked_at,
        speaker_relation=speaker_relation,
        owner_visible_address=owner_visible_address,
        stable_identity=stable_identity,
        self_narrative=self_narrative,
        owner_relation=owner_relation,
        voice_boundary=voice_boundary,
        continuity_available=continuity_available,
        recalled_available=recalled_available,
        runtime_presence_available=runtime_presence_available,
        persona_available=persona_available,
        emotion_available=emotion_available,
        active_pressure=active_pressure,
        prompt_block=prompt,
    )


def write_memory_braid_state(root: Path, snapshot: MemoryBraidSnapshot) -> None:
    lines = [
        "---",
        "title: Memory Braid State",
        "memory_type: memory_braid_state",
        "time_scope: short_term",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: xinyu_memory_braid",
        f"updated_at: {_timestamp_or_now_iso(snapshot.checked_at)}",
        "status: active",
        "tags: [memory, orchestration, continuity]",
        "---",
        "",
        "# Memory Braid State",
        "",
        "## Summary",
        f"- checked_at: {snapshot.checked_at}",
        f"- speaker_relation: {snapshot.speaker_relation}",
        f"- owner_visible_address: {snapshot.owner_visible_address}",
        f"- continuity_available: {str(snapshot.continuity_available).lower()}",
        f"- recalled_available: {str(snapshot.recalled_available).lower()}",
        f"- runtime_presence_available: {str(snapshot.runtime_presence_available).lower()}",
        f"- persona_available: {str(snapshot.persona_available).lower()}",
        f"- emotion_available: {str(snapshot.emotion_available).lower()}",
        f"- active_pressure: {snapshot.active_pressure}",
        "",
        "## Stable Anchors",
        f"- stable_identity: {snapshot.stable_identity}",
        f"- self_narrative: {snapshot.self_narrative}",
        f"- owner_relation: {snapshot.owner_relation}",
        f"- voice_boundary: {snapshot.voice_boundary}",
        "",
        "## Boundary",
        "- this file is runtime orchestration state, not a reply template",
        "- hidden context only; ordinary QQ chat should not quote this file",
    ]
    _write_text_atomic(root / STATE_MD_REL, "\n".join(lines))


def snapshot_to_json(snapshot: MemoryBraidSnapshot) -> dict[str, Any]:
    data = asdict(snapshot)
    data.pop("prompt_block", None)
    return data


def _owner_address(owner: str, relationship: str) -> str:
    text = f"{owner}\n{relationship}"
    if "可见称呼" in text and "哥" in text:
        return "哥"
    if "称呼" in text and "哥" in text:
        return "哥"
    return "哥"


def _owner_relation_line(owner: str, relationship: str) -> str:
    for text in (owner, relationship):
        for line in _content_lines(text):
            clean = line.lstrip("- ").strip()
            if "主人" in line and ("内部" in line or "不是" in line or "可见" in line):
                return _clip(clean)
            if "owner" in line and ("关系" in line or "锚点" in line or "称呼" in line):
                return _clip(clean)
    return "owner is the highest-weight relation anchor; visible address is 哥, not 主人."


def _active_pressure_line(*, user_text: str, memory_review: str, impulse: str, emotion_council_context: str) -> str:
    compact_user = _one_line(user_text)
    if any(
        marker in compact_user
        for marker in ("割裂", "记忆", "思维", "动作", "一致", "串起来", "人格", "不像人", "模板", "模版")
    ):
        return "owner is pressing on integrated memory/thought/action/personality continuity"
    impulse_top = _field(impulse, "top_desire_shape")
    if impulse_top and impulse_top != "none":
        return f"impulse_top={impulse_top}; keep it as background pressure only"
    if _one_line(emotion_council_context):
        return "emotion council available; keep it hidden and turn it into tone pressure only"
    review = _field(memory_review, "decision") or _field(memory_review, "status")
    if review and review.lower() not in {"none", "active"}:
        return f"memory_review={review}; do not turn it into visible mechanics"
    return "none"


def _first_content_line(text: str, *, fallback: str) -> str:
    for line in _content_lines(text):
        if line.startswith("- "):
            line = line[2:].strip()
        if len(line) >= 8:
            return _clip(line, 240)
    return fallback


def _first_bullet_or_line(text: str, *, preferred_markers: tuple[str, ...], fallback: str) -> str:
    lines = _content_lines(text)
    lowered_markers = tuple(marker.lower() for marker in preferred_markers)
    for line in lines:
        lowered = line.lower()
        if any(marker in lowered for marker in lowered_markers):
            return _clip(line.lstrip("- ").strip(), 240)
    if lines:
        return _clip(lines[0].lstrip("- ").strip(), 240)
    return fallback


def _content_lines(text: str) -> list[str]:
    lines: list[str] = []
    in_frontmatter = False
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if line == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter or not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("tags:") or line.startswith("status:") or line.startswith("source:"):
            continue
        lines.append(line)
    return lines


def _field(text: str, key: str) -> str:
    pattern = re.compile(rf"(?im)^\s*-?\s*{re.escape(key)}\s*:\s*(.*?)\s*$")
    match = pattern.search(text or "")
    return _one_line(match.group(1)) if match else ""


def _read(root: Path, rel_path: str, *, limit: int) -> str:
    try:
        text = (root / rel_path).read_text(encoding="utf-8-sig", errors="replace").strip()
    except OSError:
        return ""
    if text.startswith("content:\n"):
        text = text.removeprefix("content:\n")
    if text.startswith("content:---"):
        text = text.removeprefix("content:")
    if len(text) <= limit:
        return text
    return text[:limit]


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


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def main() -> int:
    parser_root = Path.cwd()
    snapshot = build_memory_braid_snapshot(parser_root)
    write_memory_braid_state(parser_root, snapshot)
    print(json.dumps(snapshot_to_json(snapshot), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
