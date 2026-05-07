from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def extract_value(text: str, field: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", text)
    return match.group(1).strip() if match else default


def extract_bullets(text: str, heading: str) -> list[str]:
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)")
    match = pattern.search(text)
    if not match:
        return []
    return [
        line.removeprefix("- ").strip()
        for line in match.group("body").splitlines()
        if line.strip().startswith("- ")
    ]


def owner_review_granted(root: Path) -> bool:
    grants = read_text(root / "memory/context/owner_permission_grants.md")
    capability = read_text(root / "memory/context/capability_zones_state.md")
    return (
        "grant_ai_self_iteration_review: approved_for_non_stable_planning" in grants
        or "ai_self_iteration_review: approved_for_non_stable_planning" in capability
    )


def apply_owner_review_grant(state_text: str) -> str:
    replacements = {
        "review_permission: owner_visible_review_required": "review_permission: owner_approved_for_non_stable_planning",
        "stable_profile_write_permission: blocked_until_explicit_review": "stable_profile_write_permission: review_only_not_auto_apply",
        "stable_narrative_write_permission: blocked_until_explicit_review": "stable_narrative_write_permission: review_only_not_auto_apply",
        "apply_permission: blocked_until_review": "apply_permission: approved_non_stable_only",
        "owner_decision: pending": "owner_decision: approved_for_non_stable_planning",
    }
    for before, after in replacements.items():
        state_text = state_text.replace(before, after)
    return state_text


def _proposal(
    proposal_id: str,
    kind: str,
    title: str,
    pressure: str,
    affected_files: list[str],
    source_materials: list[str],
    review_question: str,
    expected_benefit: str,
    risk_if_wrong: str,
    affected_tests: list[str],
) -> str:
    files = ", ".join(affected_files)
    sources = ", ".join(source_materials) or "none"
    tests = ", ".join(affected_tests) or "manual_review"
    return f"""## {proposal_id}
- kind: {kind}
- title: {title}
- proposal_status: owner_visible_review_required
- apply_permission: blocked_until_review
- pressure_level: {pressure}
- source_materials: {sources}
- affected_files: {files}
- expected_benefit: {expected_benefit}
- risk_if_wrong: {risk_if_wrong}
- affected_tests: {tests}
- review_question: {review_question}
- owner_decision: pending
- rollback_path: discard_this_proposal_without_touching_stable_memory
- direct_stable_write: blocked
"""


def render_review_state(
    *,
    reviewed_at: str,
    mode: str,
    gate_status: str,
    confidence_score: str,
    risk_level: str,
    source_materials: list[str],
    learned_entries: list[str],
    candidate_questions: list[str],
) -> str:
    if gate_status != "growth_review_candidate":
        proposal_body = "## proposal-none\n- proposal_status: hold\n- reason: ai_self_iteration_gate_not_ready\n"
        review_permission = "hold"
    else:
        review_permission = "owner_visible_review_required"
        proposal_body = "\n".join(
            [
                _proposal(
                    "proposal-ai-architecture-001",
                    "architecture_proposal",
                    "Use AI-domain knowledge to review memory, reflection, tool, and source-gate architecture.",
                    "medium",
                    [
                        "memory/context/initiative_policy.md",
                        "memory/archive/retention_model.md",
                        "memory/knowledge/integration_policy.md",
                    ],
                    source_materials,
                    "Which mechanism should be strengthened without making Xinyu a tool-only identity?",
                    "strengthen XinYu's memory/reflection/tool/source architecture without collapsing her into a task bot",
                    "too much architecture pressure could make ordinary chat sound technical again",
                    [
                        "validate_inner_framework.py",
                        "ai_domain_source_smoke.py",
                        "ai_self_iteration_gate_smoke.py",
                    ],
                ),
                _proposal(
                    "proposal-personality-pressure-001",
                    "personality_pressure",
                    "Treat AI self-understanding as pressure for self-questions, not as an applied personality rewrite.",
                    "medium",
                    [
                        "memory/self/personality_change_state.md",
                        "memory/self/personality_profile.md",
                    ],
                    source_materials,
                    "What lived evidence would justify changing the stable personality profile later?",
                    "let repeated lived evidence create reviewable personality pressure without immediate self-rewrite",
                    "single-turn frustration could be mistaken for stable personality change",
                    [
                        "personality_growth_gate_smoke.py",
                        "personality_detail_smoke.py",
                        "phase3_lived_session_smoke.py",
                    ],
                ),
                _proposal(
                    "proposal-expression-preference-001",
                    "expression_preference",
                    "Keep AI identity clear while preventing technical-manual drift in ordinary speech.",
                    "low",
                    ["prompts/output.md", "prompts/system.md"],
                    source_materials,
                    "When should Xinyu mention AI mechanisms, and when should she stay in ordinary relational speech?",
                    "reduce technical-manual drift and preserve ordinary Chinese private-chat speech",
                    "overcorrection could hide useful technical clarity when owner asks for code/design work",
                    [
                        "chinese_voice_guard_smoke.py",
                        "real_conversation_quality_smoke.py",
                        "persona_runtime_smoke.py",
                    ],
                ),
                _proposal(
                    "proposal-safety-boundary-001",
                    "safety_boundary",
                    "Preserve source, privacy, resource, and growth gates as protective boundaries for self-iteration.",
                    "high",
                    [
                        "memory/self/boundaries.md",
                        "memory/knowledge/integration_policy.md",
                        "memory/context/real_life_input_adapter_policy.md",
                    ],
                    source_materials,
                    "Which boundaries protect growth instead of flattening it?",
                    "keep computer access, source learning, and self-mutation bounded while allowing growth",
                    "too loose boundaries could expose private files or silently mutate stable memory",
                    [
                        "autonomous_search_activation_smoke.py",
                        "social_inquiry_policy_smoke.py",
                        "real_life_input_adapter_smoke.py",
                    ],
                ),
            ]
        )

    source_block = "\n".join(f"- {item}" for item in source_materials) or "- none"
    learned_block = "\n".join(f"- {item}" for item in learned_entries) or "- none"
    question_block = "\n".join(f"- {item}" for item in candidate_questions) or "- none"
    return f"""---
title: AI Self-Iteration Review State
memory_type: ai_self_iteration_review_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-26T00:00:00+08:00
updated_at: {reviewed_at}
last_confirmed_at: {reviewed_at}
importance_score: 90
impact_score: 90
confidence_score: {confidence_score}
status: active
tags: [self, ai, review, proposal, gate]
---

# AI Self-Iteration Review State

## Last Review
- reviewed_at: {reviewed_at}
- mode: {mode}
- input_gate_status: {gate_status}
- confidence_score: {confidence_score}
- risk_level: {risk_level}
- review_permission: {review_permission}
- owner_visible_audit_required: yes
- stable_profile_write_permission: blocked_until_explicit_review
- stable_narrative_write_permission: blocked_until_explicit_review
- relationship_write_permission: blocked
- emotion_write_permission: blocked
- knowledge_write_permission: blocked

## Source Trace
{source_block}

## Learned Trace
{learned_block}

## Candidate Questions
{question_block}

# Review Proposals

{proposal_body.rstrip()}

## Global Rollback
- rollback_scope: review_state_only
- rollback_action: delete_or_ignore_this_review_state
- stable_files_touched_by_review: none
- stable_mutation_boundary: proposals cannot apply themselves
"""


def run_ai_self_iteration_review(
    root: Path,
    *,
    reviewed_at: str | None = None,
    mode: str = "runtime_ai_self_iteration_review",
) -> dict[str, object]:
    reviewed_at = reviewed_at or datetime.now().astimezone().isoformat()
    gate_text = read_text(root / "memory/self/ai_self_iteration_state.md")
    gate_status = extract_value(gate_text, "gate_status")
    confidence_score = extract_value(gate_text, "confidence_score", "0")
    risk_level = extract_value(gate_text, "risk_level", "unknown")
    source_materials = extract_bullets(gate_text, "Source Material Trace")
    learned_entries = extract_bullets(gate_text, "Learned Entry Trace")
    candidate_questions = extract_bullets(gate_text, "Candidate Questions")

    state_text = render_review_state(
        reviewed_at=reviewed_at,
        mode=mode,
        gate_status=gate_status,
        confidence_score=confidence_score,
        risk_level=risk_level,
        source_materials=source_materials,
        learned_entries=learned_entries,
        candidate_questions=candidate_questions,
    )
    if owner_review_granted(root) and gate_status == "growth_review_candidate":
        state_text = apply_owner_review_grant(state_text)
    write_text(root / "memory/self/ai_self_iteration_review_state.md", state_text)

    proposals = len(re.findall(r"(?m)^## proposal-", state_text))
    return {
        "reviewed_at": reviewed_at,
        "input_gate_status": gate_status,
        "confidence_score": int(confidence_score) if confidence_score.isdigit() else 0,
        "risk_level": risk_level,
        "source_material_count": len(source_materials),
        "learned_entry_count": len(learned_entries),
        "candidate_question_count": len(candidate_questions),
        "proposal_count": proposals,
        "review_permission": extract_value(state_text, "review_permission"),
        "stable_profile_write_permission": extract_value(state_text, "stable_profile_write_permission"),
    }
