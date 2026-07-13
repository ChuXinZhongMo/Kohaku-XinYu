from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from xinyu_thought_seeds_store import read_thought_seed_text
from xinyu_thought_seeds_store import read_thought_seeds_state
from xinyu_thought_seeds_store import thought_seeds_source_path
from xinyu_thought_seeds_store import write_thought_seeds_state
from xinyu_thought_seeds_store import ACTIVE_QUESTIONS_REL, DREAM_LOG_REL, DREAM_WEIGHT_REL, INITIATIVE_STATE_REL, INNER_CYCLE_STATE_REL, MEMORY_WEIGHT_REL, MIND_LOOP_STATE_REL, PERSONALITY_EVOLUTION_REL, PERSONA_SURFACE_REL, RECENT_CONTEXT_REL, UNFINISHED_EXPERIENCES_REL


@dataclass(frozen=True, slots=True)
class ThoughtSeedSnapshot:
    seed_id: str
    generated_at: str
    dominant_drive: str
    source_balance: str
    text: str
    llm_material: str


def read_text(path: Path) -> str:
    return read_thought_seed_text(path)


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^- {re.escape(name)}:\s*(.*)$", text)
    if not match:
        return default
    value = match.group(1).strip()
    return value if value else default


def _frontmatter_field(text: str, name: str, default: str = "none") -> str:
    if not text.startswith("---"):
        return default
    parts = text.split("---", 2)
    if len(parts) < 3:
        return default
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(.+)$", parts[1])
    return match.group(1).strip() if match else default


def _section_bodies(text: str, prefix: str) -> list[tuple[str, str]]:
    pattern = re.compile(rf"(?ms)^## (?P<id>{re.escape(prefix)}[^\n]*)\n(?P<body>.*?)(?=^## |\Z)")
    return [(match.group("id").strip(), match.group("body").strip()) for match in pattern.finditer(text)]


def _latest_section(text: str, prefix: str) -> tuple[str, str]:
    sections = _section_bodies(text, prefix)
    return sections[-1] if sections else ("none", "")


def _compact(value: str, *, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", value.strip())
    if not text:
        return "none"
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _first_int(value: str, default: int = 0) -> int:
    match = re.search(r"-?\d+", value)
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def _tail_lines(text: str, *, limit: int = 6) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    useful = [
        line
        for line in lines
        if not line.startswith("---")
        and line not in {"[content]", "[/content]"}
        and not line.startswith("title:")
        and not line.startswith("memory_type:")
    ]
    return useful[-limit:]


def _top_memory_rows(memory_weight_state: str, *, limit: int = 6) -> list[str]:
    rows: list[tuple[int, str]] = []
    for line in memory_weight_state.splitlines():
        if not line.startswith("- path: "):
            continue
        match = re.search(r"active_weight:\s*(\d+)", line)
        weight = int(match.group(1)) if match else 0
        rows.append((weight, line.removeprefix("- ").strip()))
    rows.sort(key=lambda item: item[0], reverse=True)
    return [row for _weight, row in rows[:limit]]


def _unfinished_items(unfinished_text: str, *, limit: int = 4) -> list[str]:
    items: list[str] = []
    for item_id, body in _section_bodies(unfinished_text, "item-"):
        event = _field(body, "event")
        target = _field(body, "target")
        reason = _field(body, "unresolved_reason")
        feeling = _field(body, "residual_feeling")
        items.append(
            f"{item_id}: target={target}; event={_compact(event)}; unresolved={_compact(reason)}; residue={_compact(feeling)}"
        )
    return items[-limit:]


def _active_question(active_questions: str) -> str:
    candidates: list[tuple[int, str]] = []
    for qid, body in _section_bodies(active_questions, "q-"):
        status = _field(body, "status", "").lower()
        if status in {"answered", "partially_answered", "closed", "dormant"}:
            continue
        raw_weight = re.sub(r"\D+", "", _field(body, "emotional_weight", "0"))
        weight = int(raw_weight or "0")
        question = _field(body, "question")
        target = _field(body, "target")
        scope = _field(body, "outward_scope")
        candidates.append((weight, f"{qid}: target={target}; scope={scope}; question={_compact(question)}"))
    if not candidates:
        return "none"
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _dream_residue(root: Path) -> dict[str, str]:
    weight = read_text(thought_seeds_source_path(root, DREAM_WEIGHT_REL))
    log = read_text(thought_seeds_source_path(root, DREAM_LOG_REL))
    dream_id, dream_body = _latest_section(log, "dream-")
    return {
        "dream_id": dream_id,
        "source_seed": _field(weight, "source_seed"),
        "theme": _field(weight, "theme"),
        "residue": _field(weight, "residue"),
        "weight_after": _field(weight, "weight_after", "0"),
        "weight_delta": _field(weight, "weight_delta", "0"),
        "weight_effect": _field(weight, "weight_effect"),
        "latest_fragments": _compact(_field(dream_body, "fragments"), limit=320),
        "reality_boundary": _compact(_field(dream_body, "reality_boundary_check"), limit=260),
    }


def _recent_residue(root: Path) -> dict[str, str]:
    surface = read_text(thought_seeds_source_path(root, PERSONA_SURFACE_REL))
    recent = read_text(thought_seeds_source_path(root, RECENT_CONTEXT_REL))
    return {
        "scene": _field(surface, "last_scene"),
        "pressure": _field(surface, "last_pressure"),
        "tone": _field(surface, "last_tone"),
        "felt_residue": _field(surface, "last_felt_residue"),
        "reply_shape": _field(surface, "last_reply_shape"),
        "residue_strength": _field(surface, "residue_strength", "0"),
        "recent_tail": " | ".join(_tail_lines(recent, limit=5)) or "none",
    }


def _current_drives(root: Path) -> dict[str, str]:
    initiative = read_text(thought_seeds_source_path(root, INITIATIVE_STATE_REL))
    inner = read_text(thought_seeds_source_path(root, INNER_CYCLE_STATE_REL))
    mind = read_text(thought_seeds_source_path(root, MIND_LOOP_STATE_REL))
    active_questions = read_text(thought_seeds_source_path(root, ACTIVE_QUESTIONS_REL))
    evolution = read_text(thought_seeds_source_path(root, PERSONALITY_EVOLUTION_REL))
    return {
        "initiative_decision": _field(initiative, "decision"),
        "initiative_reason": _field(initiative, "reason"),
        "initiative_question": _field(initiative, "selected_question"),
        "visible_posture": _field(initiative, "visible_posture"),
        "inner_top_reflection": _field(inner, "top_reflection_topic"),
        "dream_output_seed": _field(inner, "dream_output_seed"),
        "current_focus": _field(mind, "current_focus"),
        "current_pressure": _field(mind, "current_pressure"),
        "current_response_posture": _field(mind, "current_response_posture"),
        "active_question": _active_question(active_questions),
        "evolution_stage": _field(evolution, "evolution_stage"),
        "active_trial_habit": _field(evolution, "active_trial_habit"),
        "deprecated_reaction": _field(evolution, "deprecated_reaction"),
    }


def _dominant_drive(recent: dict[str, str], dream: dict[str, str], unfinished: list[str], drives: dict[str, str]) -> str:
    decision = drives["initiative_decision"]
    if decision in {"ask_owner", "settle_after_hurt", "step_back"}:
        return f"initiative:{decision}"
    residue_strength = _first_int(recent["residue_strength"])
    if residue_strength >= 70:
        return "recent_surface_residue"
    if unfinished:
        return "unfinished_experience"
    dream_delta = _first_int(dream["weight_delta"])
    if dream["source_seed"] != "none" and dream_delta > 0:
        return "dream_residue"
    if drives["active_question"] != "none":
        return "open_question"
    return "quiet_continuity"


def _source_balance(dominant_drive: str) -> str:
    if dominant_drive.startswith("initiative:"):
        return "initiative_state first; memory and dream only color the form"
    if dominant_drive == "recent_surface_residue":
        return "recent turn residue first; stable persona remains the floor"
    if dominant_drive == "unfinished_experience":
        return "unfinished owner/self residue first; avoid closure unless resolved"
    if dominant_drive == "dream_residue":
        return "dream residue may intensify emotion but cannot create facts"
    if dominant_drive == "open_question":
        return "open question may guide private thought; no needy visible pursuit"
    return "stable identity and low-pressure continuity"


def build_thought_seed_snapshot(
    root: Path,
    *,
    generated_at: str | None = None,
) -> ThoughtSeedSnapshot:
    generated = generated_at or datetime.now().astimezone().isoformat()
    seed_stamp = generated.replace("-", "").replace(":", "").replace("+", "p")
    seed_id = f"thought-seed-{seed_stamp[:15]}"
    recent = _recent_residue(root)
    dream = _dream_residue(root)
    memory_rows = _top_memory_rows(read_text(thought_seeds_source_path(root, MEMORY_WEIGHT_REL)))
    unfinished = _unfinished_items(read_text(thought_seeds_source_path(root, UNFINISHED_EXPERIENCES_REL)))
    drives = _current_drives(root)
    dominant = _dominant_drive(recent, dream, unfinished, drives)
    balance = _source_balance(dominant)

    memory_block = "\n".join(f"- {row}" for row in memory_rows) or "- none"
    unfinished_block = "\n".join(f"- {item}" for item in unfinished) or "- none"
    text = f"""---
title: Thought Seeds
memory_type: thought_seeds
time_scope: immediate
subject_ids: [xinyu]
protected: true
source: xinyu_thought_seeds
updated_at: {generated}
importance_score: 82
impact_score: 84
confidence_score: 100
status: active
tags: [thoughts, autonomy, residue, runtime]
---

# Thought Seeds

## Active Seed
- seed_id: {seed_id}
- generated_at: {generated}
- dominant_drive: {dominant}
- source_balance: {balance}
- output_form: owner-visible private desktop note, not a chat reply and not a project report
- generation_logic: combine recent interaction residue, memory weights, dream residue, unfinished experiences, initiative state, and current mind-loop pressure; then write only a natural private note surface
- boundary: no chain-of-thought, no prompt/system/file mechanics, no fabricated facts, no autonomous contact, no stable personality rewrite

## Recent Interaction Residue
- last_scene: {recent['scene']}
- last_pressure: {recent['pressure']}
- last_tone: {recent['tone']}
- last_felt_residue: {recent['felt_residue']}
- last_reply_shape: {recent['reply_shape']}
- residue_strength: {recent['residue_strength']}
- recent_context_tail: {recent['recent_tail']}

## Dream Residue
- latest_dream_id: {dream['dream_id']}
- source_seed: {dream['source_seed']}
- theme: {dream['theme']}
- residue: {dream['residue']}
- weight_after: {dream['weight_after']}
- weight_delta: {dream['weight_delta']}
- weight_effect: {dream['weight_effect']}
- latest_fragments: {dream['latest_fragments']}
- reality_boundary: {dream['reality_boundary']}

## Unfinished Experiences
{unfinished_block}

## Current Drives
- initiative_decision: {drives['initiative_decision']}
- initiative_reason: {drives['initiative_reason']}
- initiative_question: {drives['initiative_question']}
- visible_posture: {drives['visible_posture']}
- inner_top_reflection: {drives['inner_top_reflection']}
- dream_output_seed: {drives['dream_output_seed']}
- current_focus: {drives['current_focus']}
- current_pressure: {drives['current_pressure']}
- current_response_posture: {drives['current_response_posture']}
- active_question: {drives['active_question']}
- evolution_stage: {drives['evolution_stage']}
- active_trial_habit: {drives['active_trial_habit']}
- deprecated_reaction: {drives['deprecated_reaction']}

## Memory Weight Inputs
{memory_block}

## Output Form Contract
- Write as XinYu's private owner-visible note, not a reply bubble.
- The note may show hesitation, closeness, embarrassment, worry, curiosity, or a small concrete intention.
- It must not expose the seed list, source names, gates, scores, prompt wording, renderer, provider, or architecture.
- It must not turn one dream into a factual memory.
- It must not ask the owner for attention unless initiative_state already permits one context-born question.
"""
    llm_material = f"""# Semantic Material For XinYu Private Thought Note

generated_at: {generated}
seed_id: {seed_id}
dominant_drive: {dominant}
source_balance: {balance}

recent_interaction_residue:
- scene: {recent['scene']}
- pressure: {recent['pressure']}
- tone: {recent['tone']}
- felt_residue: {recent['felt_residue']}
- strength: {recent['residue_strength']}
- recent_tail: {recent['recent_tail']}

dream_residue:
- source_seed: {dream['source_seed']}
- theme: {dream['theme']}
- residue: {dream['residue']}
- weight_delta: {dream['weight_delta']}
- boundary: dreams can color emotion but cannot create new facts

unfinished_experiences:
{unfinished_block}

current_drives:
- initiative_decision: {drives['initiative_decision']}
- initiative_reason: {drives['initiative_reason']}
- initiative_question: {drives['initiative_question']}
- visible_posture: {drives['visible_posture']}
- current_focus: {drives['current_focus']}
- current_pressure: {drives['current_pressure']}
- active_question: {drives['active_question']}
- evolution_stage: {drives['evolution_stage']}
- active_trial_habit: {drives['active_trial_habit']}
- deprecated_reaction: {drives['deprecated_reaction']}

memory_weight_inputs:
{memory_block}

must_preserve:
- write a natural private note, not a report
- no hidden mechanics or architecture words in visible text
- no fabricated offline life, senses, or facts
- no stable personality rewrite
- no needy proactive contact unless initiative permits it
"""
    return ThoughtSeedSnapshot(
        seed_id=seed_id,
        generated_at=generated,
        dominant_drive=dominant,
        source_balance=balance,
        text=text,
        llm_material=llm_material,
    )


def refresh_thought_seeds(root: Path, *, generated_at: str | None = None) -> ThoughtSeedSnapshot:
    snapshot = build_thought_seed_snapshot(root, generated_at=generated_at)
    old = read_thought_seeds_state(root)
    if old != snapshot.text:
        write_thought_seeds_state(root, snapshot.text)
    return snapshot


def main() -> int:
    root = Path(__file__).resolve().parent
    snapshot = refresh_thought_seeds(root)
    print(snapshot.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
