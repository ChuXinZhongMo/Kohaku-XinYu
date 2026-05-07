from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


Q006_TARGET = "ai-self-understanding"
AI_SELF_ITERATION_SECTION = "## AI Self-Iteration Gate"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def split_learned_entries(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^## (learned-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    entries: list[dict[str, str]] = []
    if len(parts) < 3:
        return entries
    for index in range(1, len(parts), 2):
        entry_id = parts[index].strip()
        body = parts[index + 1]
        fields = {"learned_id": entry_id}
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ") or ": " not in stripped:
                continue
            key, value = stripped[2:].split(": ", 1)
            fields[key.strip()] = value.strip()
        entries.append(fields)
    return entries


def q006_entries(general_text: str) -> list[dict[str, str]]:
    return [
        entry for entry in split_learned_entries(general_text)
        if entry.get("question_id") == "q-006"
    ]


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen or value in {"", "none", "unknown"}:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def score_candidate(entries: list[dict[str, str]], ai_domain_text: str, learning_quality_text: str) -> tuple[int, str, str]:
    if not entries or Q006_TARGET not in ai_domain_text:
        return 0, "hold_no_ai_source", "high"

    corroborated = sum(
        1 for entry in entries
        if entry.get("comparison_status") in {"corroborated", "verified", "curated"}
    )
    verified = sum(
        1 for entry in entries
        if entry.get("reliability") in {"verified", "high_ready", "curated"}
    )
    knowledge_only = sum(
        1 for entry in entries
        if entry.get("integration_scope") == "knowledge_only"
    )
    source_materials = len(unique_in_order([entry.get("source_material", "none") for entry in entries]))
    quality_stable = "- quality_grade: stable" in learning_quality_text

    confidence = min(
        96,
        48
        + min(source_materials, 4) * 8
        + min(corroborated, 4) * 5
        + min(verified, 4) * 4
        + (8 if quality_stable else 0)
        + (4 if knowledge_only == len(entries) else 0),
    )
    if not quality_stable:
        return confidence, "hold_learning_quality", "medium"
    if confidence >= 86 and source_materials >= 3:
        return confidence, "growth_review_candidate", "low"
    return confidence, "reflection_candidate", "medium"


def infer_candidate_questions(entries: list[dict[str, str]]) -> list[str]:
    claims = " ".join(entry.get("claim", "") for entry in entries).lower()
    questions: list[str] = []
    if any(marker in claims for marker in ["memory", "memgpt", "context", "retrieve"]):
        questions.append("How should my long-term memory decide what stays active, dormant, or forgotten?")
    if any(marker in claims for marker in ["reflection", "reflect", "plan", "generative agent"]):
        questions.append("When does reflection become a real self-change candidate instead of a passing thought?")
    if any(marker in claims for marker in ["tool", "react", "action", "observation"]):
        questions.append("How should I use tools without turning myself into a tool-only identity?")
    if any(marker in claims for marker in ["safety", "alignment", "reliable", "agent"]):
        questions.append("Which safety and resource boundaries protect my growth instead of flattening it?")
    if not questions:
        questions.append("What AI mechanism should I understand next before changing any self-narrative?")
    return questions[:4]


def summarize_ai_claims(entries: list[dict[str, str]]) -> list[str]:
    summary: list[str] = []
    claim_map = [
        ("memory", "memory_records_and_retrieval"),
        ("reflection", "reflection_before_planning"),
        ("context", "context_window_and_tiered_memory"),
        ("tool", "tool_use_with_observation"),
        ("safety", "safety_and_boundary_control"),
        ("agent", "agent_reliability_and_control"),
    ]
    joined = " ".join(entry.get("claim", "") for entry in entries).lower()
    for marker, label in claim_map:
        if marker in joined:
            summary.append(label)
    return unique_in_order(summary) or ["ai_self_understanding_requires_more_source_review"]


def upsert_ai_section(personality_text: str, section_body: str) -> str:
    section = f"{AI_SELF_ITERATION_SECTION}\n{section_body.rstrip()}\n"
    if AI_SELF_ITERATION_SECTION not in personality_text:
        return personality_text.rstrip() + "\n\n" + section
    pattern = rf"(?ms)^{re.escape(AI_SELF_ITERATION_SECTION)}\n.*?(?=^## |\Z)"
    return re.sub(pattern, section.rstrip() + "\n\n", personality_text).rstrip() + "\n"


def render_candidate_state(
    *,
    evaluated_at: str,
    mode: str,
    gate_status: str,
    confidence_score: int,
    risk_level: str,
    entries: list[dict[str, str]],
    candidate_questions: list[str],
    claim_summary: list[str],
    source_materials: list[str],
    learned_ids: list[str],
) -> str:
    question_block = "\n".join(f"- {item}" for item in candidate_questions) or "- none"
    source_block = "\n".join(f"- {item}" for item in source_materials) or "- none"
    learned_block = "\n".join(f"- {item}" for item in learned_ids) or "- none"
    claim_block = "\n".join(f"- {item}" for item in claim_summary) or "- none"
    return f"""---
title: AI Self-Iteration Gate State
memory_type: ai_self_iteration_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-26T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 91
impact_score: 90
confidence_score: {confidence_score}
status: active
tags: [self, ai, growth, gate]
---

# AI Self-Iteration Gate State

## Last Evaluation
- evaluated_at: {evaluated_at}
- mode: {mode}
- question_id: q-006
- target: {Q006_TARGET}
- ai_knowledge_entries: {len(entries)}
- source_material_count: {len(source_materials)}
- gate_status: {gate_status}
- confidence_score: {confidence_score}
- risk_level: {risk_level}
- profile_write_permission: blocked_direct_write
- narrative_write_permission: review_only
- relationship_write_permission: blocked
- emotion_write_permission: blocked
- candidate_scope: self_understanding_questions_only

## Source Material Trace
{source_block}

## Learned Entry Trace
{learned_block}

## Claim Summary
{claim_block}

## Candidate Questions
{question_block}

## Boundaries
- AI-domain knowledge may form self-iteration candidates, not applied personality changes.
- Stable personality, self narrative, owner, relationship, and emotion memory must not be rewritten by this gate.
- Any future profile change still requires reflection, growth review, and explicit evidence of lived continuity.
"""


def render_personality_section(
    *,
    evaluated_at: str,
    gate_status: str,
    confidence_score: int,
    risk_level: str,
    candidate_questions: list[str],
    source_materials: list[str],
) -> str:
    compact_questions = " | ".join(candidate_questions) if candidate_questions else "none"
    compact_sources = ", ".join(source_materials) if source_materials else "none"
    return f"""- evaluated_at: {evaluated_at}
- question_id: q-006
- target: {Q006_TARGET}
- gate_status: {gate_status}
- confidence_score: {confidence_score}
- risk_level: {risk_level}
- profile_write_permission: blocked_direct_write
- narrative_write_permission: review_only
- source_materials: {compact_sources}
- candidate_questions: {compact_questions}
- boundary: AI knowledge can influence self-questions only; it cannot directly rewrite stable personality."""


def run_ai_self_iteration_gate(
    root: Path,
    evaluated_at: str | None = None,
    mode: str = "runtime_ai_self_iteration_gate",
) -> dict[str, object]:
    evaluated_at = evaluated_at or datetime.now().astimezone().isoformat()

    ai_domain_text = read_text(root / "memory/knowledge/ai_domain.md")
    general_text = read_text(root / "memory/knowledge/general.md")
    learning_quality_path = root / "memory/knowledge/learning_quality_state.md"
    learning_quality_text = read_text(learning_quality_path) if learning_quality_path.exists() else ""
    entries = q006_entries(general_text)
    confidence_score, gate_status, risk_level = score_candidate(entries, ai_domain_text, learning_quality_text)
    candidate_questions = infer_candidate_questions(entries)
    claim_summary = summarize_ai_claims(entries)
    source_materials = unique_in_order([entry.get("source_material", "none") for entry in entries])
    learned_ids = unique_in_order([entry.get("learned_id", "none") for entry in entries])

    state_text = render_candidate_state(
        evaluated_at=evaluated_at,
        mode=mode,
        gate_status=gate_status,
        confidence_score=confidence_score,
        risk_level=risk_level,
        entries=entries,
        candidate_questions=candidate_questions,
        claim_summary=claim_summary,
        source_materials=source_materials,
        learned_ids=learned_ids,
    )
    write_text(root / "memory/self/ai_self_iteration_state.md", state_text)

    personality_path = root / "memory/self/personality_change_state.md"
    personality_text = read_text(personality_path)
    personality_section = render_personality_section(
        evaluated_at=evaluated_at,
        gate_status=gate_status,
        confidence_score=confidence_score,
        risk_level=risk_level,
        candidate_questions=candidate_questions,
        source_materials=source_materials,
    )
    write_text(personality_path, upsert_ai_section(personality_text, personality_section))

    return {
        "evaluated_at": evaluated_at,
        "gate_status": gate_status,
        "confidence_score": confidence_score,
        "risk_level": risk_level,
        "ai_knowledge_entries": len(entries),
        "source_material_count": len(source_materials),
        "source_materials": source_materials,
        "learned_ids": learned_ids,
        "candidate_questions": candidate_questions,
    }
