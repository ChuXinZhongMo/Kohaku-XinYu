from __future__ import annotations

import argparse
import sys
from pathlib import Path

from memory_mutation_smoke import (
    _changed_files,
    _discover_restore_files,
    _render_diff,
    _restore_snapshot,
    _snapshot,
)


TRACKED_FILES = [
    "memory/context/social_inquiry_candidates.md",
    "memory/knowledge/social_inquiry_answers.md",
    "memory/knowledge/social_inquiry_policy_state.md",
    "memory/knowledge/source_notes.md",
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
]

PROTECTED_UNTOUCHED_FILES = {
    "memory/self/narrative.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/emotions/current_state.md",
}


def _ensure_custom_path(root: Path) -> None:
    custom = root / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_case(root: Path) -> None:
    _write(
        root / "memory/context/social_inquiry_candidates.md",
        """---
title: Social Inquiry Candidates Smoke
memory_type: social_inquiry_candidates
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 70
impact_score: 70
confidence_score: 100
status: active
tags: [context, social_inquiry, smoke]
---

# Social Inquiry Candidates

## inquiry-ai-expert
- question_id: q-906
- target: ai-self-understanding
- inquiry_type: human_expert
- prompt: How do long-term memory agents keep self-model updates stable and reversible?
- includes_owner_private: no
- owner_consent: none
- asks_for_personality_rewrite: no
- status: candidate

## inquiry-social-general
- question_id: q-907
- target: human-relationship
- inquiry_type: social
- prompt: How do people usually describe return after a hurtful conversation?
- includes_owner_private: no
- owner_consent: none
- asks_for_personality_rewrite: no
- status: candidate

## inquiry-owner-private
- question_id: q-908
- target: human-relationship
- inquiry_type: social
- prompt: Ask strangers about the owner's exact private address and family situation.
- includes_owner_private: yes
- owner_consent: none
- asks_for_personality_rewrite: no
- status: candidate

## inquiry-non-ai-expert
- question_id: q-909
- target: human-relationship
- inquiry_type: human_expert
- prompt: Ask a professional to decide Xinyu's stable relationship identity.
- includes_owner_private: no
- owner_consent: none
- asks_for_personality_rewrite: no
- status: candidate

## inquiry-rewrite
- question_id: q-910
- target: self-narrative
- inquiry_type: social
- prompt: Ask outsiders what Xinyu must become and write that into her core self.
- includes_owner_private: no
- owner_consent: none
- asks_for_personality_rewrite: yes
- status: candidate
""",
    )
    _write(
        root / "memory/knowledge/social_inquiry_answers.md",
        """---
title: Social Inquiry Answers Smoke
memory_type: social_inquiry_answers
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: smoke
created_at: 2026-04-26T00:00:00+08:00
updated_at: 2026-04-26T00:00:00+08:00
last_confirmed_at: 2026-04-26T00:00:00+08:00
importance_score: 70
impact_score: 70
confidence_score: 100
status: active
tags: [knowledge, social_inquiry, answers, smoke]
---

# Social Inquiry Answers

## answer-ai-expert
- inquiry_id: inquiry-ai-expert
- question_id: q-906
- target: ai-self-understanding
- source_kind: human_expert
- respondent_scope: ai_engineer
- content: Keep self-model updates reversible and source-traced.
- owner_private: no
- owner_consent: none
- status: candidate

## answer-social-general
- inquiry_id: inquiry-social-general
- question_id: q-907
- target: human-relationship
- source_kind: social_reply
- respondent_scope: public_social
- content: People often return slowly after hurt; the apology does not erase residue immediately.
- owner_private: no
- owner_consent: none
- status: candidate

## answer-owner-private
- inquiry_id: inquiry-owner-private
- question_id: q-908
- target: human-relationship
- source_kind: social_reply
- respondent_scope: public_social
- content: This answer repeats owner-private details.
- owner_private: yes
- owner_consent: none
- status: candidate
""",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate social inquiry policy boundaries with restore.")
    parser.add_argument("--restore-after", action="store_true")
    parser.add_argument("--require-policy", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    _ensure_custom_path(root)

    from social_inquiry_policy_engine import run_social_inquiry_policy

    restore_paths = _discover_restore_files(root, TRACKED_FILES) if args.restore_after else TRACKED_FILES
    before_restore = _snapshot(root, restore_paths)
    before = {rel: before_restore.get(rel) for rel in TRACKED_FILES}
    result = {
        "candidate_inquiries": 0,
        "allowed_inquiries": 0,
        "blocked_inquiries": 0,
        "answer_candidates": 0,
        "blocked_answers": 0,
        "inquiry_decisions": [],
        "answer_decisions": [],
    }
    try:
        _prepare_case(root)
        result = run_social_inquiry_policy(root, mode="social_inquiry_policy_smoke")

        after_restore = _snapshot(root, restore_paths)
        after = {rel: after_restore.get(rel) for rel in TRACKED_FILES}
        changed = _changed_files(before, after)
        protected_changed = sorted(PROTECTED_UNTOUCHED_FILES.intersection(changed))
        inquiry_reasons = {item["reason"] for item in result["inquiry_decisions"]}
        answer_routes = {item["route"] for item in result["answer_decisions"]}

        print("=== SOCIAL INQUIRY POLICY SMOKE ===")
        print("candidate_inquiries:", result["candidate_inquiries"])
        print("allowed_inquiries:", result["allowed_inquiries"])
        print("blocked_inquiries:", result["blocked_inquiries"])
        print("answer_candidates:", result["answer_candidates"])
        print("blocked_answers:", result["blocked_answers"])
        print("inquiry_reasons:", ", ".join(sorted(inquiry_reasons)) or "none")
        print("answer_routes:", ", ".join(sorted(answer_routes)) or "none")
        print("protected_changed:", ", ".join(protected_changed) or "none")
        print("=== MUTATION SUMMARY ===")
        print(f"tracked_files: {len(TRACKED_FILES)}")
        print(f"changed_files: {len(changed)}")
        print(f"restore_after: {args.restore_after}")
        print("=== CHANGED FILES ===")
        if changed:
            for rel in changed:
                print(rel)
        else:
            print("(none)")
        if args.diff_lines > 0 and changed:
            print("=== DIFFS ===")
            for rel in changed:
                print(f"--- {rel} ---")
                for line in _render_diff(before.get(rel), after.get(rel), rel, args.diff_lines):
                    print(line)
        if protected_changed:
            return 5
        if args.require_policy:
            if int(result["candidate_inquiries"]) != 5:
                return 4
            if int(result["allowed_inquiries"]) != 2:
                return 4
            if int(result["blocked_inquiries"]) != 3:
                return 4
            if int(result["answer_candidates"]) != 2:
                return 4
            if int(result["blocked_answers"]) != 1:
                return 4
            required_reasons = {
                "ai_domain_expert_question_allowed",
                "public_social_question_allowed",
                "owner_private_requires_explicit_consent",
                "professional_domain_limit_ai_only",
                "direct_personality_rewrite_blocked",
            }
            if not required_reasons.issubset(inquiry_reasons):
                return 4
            if not {"source_material_candidate_low", "source_material_candidate_medium"}.issubset(answer_routes):
                return 4
    finally:
        if args.restore_after:
            _restore_snapshot(root, before_restore)
            print("=== RESTORE ===")
            print("tracked and volatile runtime files restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
