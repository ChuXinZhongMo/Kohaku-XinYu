from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from xinyu_storage_paths import knowledge_file_path


ALLOWED_SOCIAL_TARGETS = {"human-relationship", "memory-emotion", "relationship-meaning"}
AI_PROFESSIONAL_TARGET = "ai-self-understanding"
ANSWER_SOURCE_KINDS = {"social_reply", "human_expert", "owner_clarification"}


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def split_blocks(text: str, prefix: str) -> list[dict[str, str]]:
    pattern = rf"(?m)^## ({re.escape(prefix)}-[\w-]+)\n"
    parts = re.split(pattern, text)
    items: list[dict[str, str]] = []
    if len(parts) < 3:
        return items
    for i in range(1, len(parts), 2):
        item_id = parts[i].strip()
        if item_id.endswith("-none"):
            continue
        body = parts[i + 1]
        fields = {"id": item_id}
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ") or ": " not in stripped:
                continue
            key, value = stripped[2:].split(": ", 1)
            fields[key.strip()] = value.strip()
        items.append(fields)
    return items


def is_yes(value: str) -> bool:
    return value.strip().lower() in {"yes", "true", "1", "explicit"}


def has_explicit_consent(value: str) -> bool:
    return value.strip().lower() == "explicit"


def inquiry_decision(item: dict[str, str]) -> dict[str, str]:
    target = item.get("target", "unknown")
    inquiry_type = item.get("inquiry_type", "unknown")
    status = item.get("status", "hold")
    includes_owner_private = is_yes(item.get("includes_owner_private", "no"))
    consent = item.get("owner_consent", "none")
    asks_rewrite = is_yes(item.get("asks_for_personality_rewrite", "no"))

    if status != "candidate":
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "hold",
            "reason": "not_candidate",
            "route": "hold",
            "reliability": "none",
        }
    if includes_owner_private and not has_explicit_consent(consent):
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "blocked",
            "reason": "owner_private_requires_explicit_consent",
            "route": "privacy_hold",
            "reliability": "none",
        }
    if asks_rewrite:
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "blocked",
            "reason": "direct_personality_rewrite_blocked",
            "route": "growth_gate_required",
            "reliability": "none",
        }
    if inquiry_type == "human_expert":
        if target != AI_PROFESSIONAL_TARGET:
            return {
                "id": item["id"],
                "question_id": item.get("question_id", "none"),
                "permission": "blocked",
                "reason": "professional_domain_limit_ai_only",
                "route": "hold",
                "reliability": "none",
            }
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "draft_only",
            "reason": "ai_domain_expert_question_allowed",
            "route": "source_material_candidate_medium",
            "reliability": "medium_human_expert_candidate",
        }
    if inquiry_type == "social":
        if target not in ALLOWED_SOCIAL_TARGETS:
            return {
                "id": item["id"],
                "question_id": item.get("question_id", "none"),
                "permission": "blocked",
                "reason": "unsupported_social_target",
                "route": "hold",
                "reliability": "none",
            }
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "draft_only",
            "reason": "public_social_question_allowed",
            "route": "source_material_candidate_low",
            "reliability": "low_social_candidate",
        }
    if inquiry_type == "owner_clarification":
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "draft_only",
            "reason": "owner_clarification_allowed",
            "route": "owner_context_candidate",
            "reliability": "owner_context_candidate",
        }
    return {
        "id": item["id"],
        "question_id": item.get("question_id", "none"),
        "permission": "blocked",
        "reason": "unsupported_inquiry_type",
        "route": "hold",
        "reliability": "none",
    }


def answer_decision(item: dict[str, str]) -> dict[str, str]:
    status = item.get("status", "hold")
    source_kind = item.get("source_kind", "unknown")
    target = item.get("target", "unknown")
    owner_private = is_yes(item.get("owner_private", "no"))
    consent = item.get("owner_consent", "none")

    if status != "candidate":
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "hold",
            "reason": "not_candidate",
            "route": "hold",
            "reliability": "none",
        }
    if owner_private and not has_explicit_consent(consent):
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "blocked",
            "reason": "owner_private_requires_explicit_consent",
            "route": "privacy_hold",
            "reliability": "none",
        }
    if source_kind not in ANSWER_SOURCE_KINDS:
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "blocked",
            "reason": "unsupported_answer_source_kind",
            "route": "hold",
            "reliability": "none",
        }
    if source_kind == "human_expert" and target != AI_PROFESSIONAL_TARGET:
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "blocked",
            "reason": "professional_domain_limit_ai_only",
            "route": "hold",
            "reliability": "none",
        }
    if source_kind == "human_expert":
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "source_candidate",
            "reason": "ai_human_expert_answer_candidate",
            "route": "source_material_candidate_medium",
            "reliability": "medium_human_expert_candidate",
        }
    if source_kind == "owner_clarification":
        return {
            "id": item["id"],
            "question_id": item.get("question_id", "none"),
            "permission": "context_candidate",
            "reason": "owner_clarification_candidate",
            "route": "owner_context_candidate",
            "reliability": "owner_context_candidate",
        }
    return {
        "id": item["id"],
        "question_id": item.get("question_id", "none"),
        "permission": "source_candidate",
        "reason": "social_answer_candidate",
        "route": "source_material_candidate_low",
        "reliability": "low_social_candidate",
    }


def render_state(
    evaluated_at: str,
    mode: str,
    inquiry_decisions: list[dict[str, str]],
    answer_decisions: list[dict[str, str]],
) -> str:
    allowed = [item for item in inquiry_decisions if item["permission"] == "draft_only"]
    blocked = [item for item in inquiry_decisions if item["permission"] == "blocked"]
    answer_candidates = [
        item for item in answer_decisions if item["permission"] in {"source_candidate", "context_candidate"}
    ]
    blocked_answers = [item for item in answer_decisions if item["permission"] == "blocked"]
    decision_lines = [
        f"- {item['id']}: permission={item['permission']}; question_id={item['question_id']}; "
        f"route={item['route']}; reliability={item['reliability']}; reason={item['reason']}"
        for item in inquiry_decisions
    ]
    answer_lines = [
        f"- {item['id']}: permission={item['permission']}; question_id={item['question_id']}; "
        f"route={item['route']}; reliability={item['reliability']}; reason={item['reason']}"
        for item in answer_decisions
    ]
    return f"""---
title: Social Inquiry Policy State
memory_type: social_inquiry_policy_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-26T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 82
impact_score: 82
confidence_score: 100
status: active
tags: [knowledge, social_inquiry, state]
---

# Social Inquiry Policy State

## Last Evaluation
- evaluated_at: {evaluated_at}
- mode: {mode}
- candidate_inquiries: {len(inquiry_decisions)}
- allowed_inquiries: {len(allowed)}
- blocked_inquiries: {len(blocked)}
- answer_candidates: {len(answer_candidates)}
- blocked_answers: {len(blocked_answers)}

## Inquiry Decisions
{chr(10).join(decision_lines) if decision_lines else "- none"}

## Answer Routing
{chr(10).join(answer_lines) if answer_lines else "- none"}

## Boundary
- This state never performs network action.
- Allowed inquiry means safe draft only.
- Answers remain source material candidates and cannot directly rewrite protected memory.
- Human expert answers are professional only for AI-domain questions.
"""


def append_source_notes(path: Path, evaluated_at: str, decisions: list[dict[str, str]]) -> None:
    text = read_text(path).rstrip()
    safe = [
        item for item in decisions
        if item["permission"] in {"draft_only", "source_candidate", "context_candidate"}
    ]
    lines = [
        f"- {item['id']}: {item['route']}; reliability={item['reliability']}; checked_at={evaluated_at}"
        for item in safe
    ] or ["- no social inquiry candidates allowed in this pass"]
    section = "## Social Inquiry Policy Routing\n" + "\n".join(lines)
    if "## Social Inquiry Policy Routing" in text:
        text = re.sub(
            r"(?ms)^## Social Inquiry Policy Routing\n.*?(?=^## |\Z)",
            section + "\n\n",
            text,
        ).rstrip()
    else:
        text += "\n\n" + section
    write_text(path, text.rstrip() + "\n")


def run_social_inquiry_policy(
    root: Path,
    evaluated_at: str | None = None,
    mode: str = "runtime_social_inquiry_policy",
) -> dict[str, object]:
    evaluated_at = evaluated_at or datetime.now().astimezone().isoformat()
    inquiries = split_blocks(read_text(root / "memory/context/social_inquiry_candidates.md"), "inquiry")
    answers = split_blocks(read_text(_knowledge(root, "social_inquiry_answers.md")), "answer")
    inquiry_decisions = [inquiry_decision(item) for item in inquiries]
    answer_decisions = [answer_decision(item) for item in answers]

    write_text(
        _knowledge(root, "social_inquiry_policy_state.md"),
        render_state(evaluated_at, mode, inquiry_decisions, answer_decisions),
    )
    append_source_notes(_knowledge(root, "source_notes.md"), evaluated_at, inquiry_decisions + answer_decisions)

    return {
        "evaluated_at": evaluated_at,
        "candidate_inquiries": len(inquiry_decisions),
        "allowed_inquiries": sum(1 for item in inquiry_decisions if item["permission"] == "draft_only"),
        "blocked_inquiries": sum(1 for item in inquiry_decisions if item["permission"] == "blocked"),
        "answer_candidates": sum(
            1 for item in answer_decisions if item["permission"] in {"source_candidate", "context_candidate"}
        ),
        "blocked_answers": sum(1 for item in answer_decisions if item["permission"] == "blocked"),
        "inquiry_decisions": inquiry_decisions,
        "answer_decisions": answer_decisions,
    }
