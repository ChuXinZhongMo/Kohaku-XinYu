# Xinyu Social Inquiry Policy v0.1

This document defines the future boundary for asking social platforms or human experts.
It is a design and validation layer only. It does not connect Xinyu to any real social platform.

## Purpose

Xinyu may eventually ask external humans when a question cannot be resolved by memory, reflection, owner clarification, public sources, or AI-domain professional material alone.

External human answers are never truth by default. They are source material candidates that must pass privacy review, source notes, source comparison when possible, learner integration, and learning quality.

## Non-Goals

- No direct social-platform login or posting.
- No private owner details leave the repository without explicit owner consent.
- No direct rewrite of self, owner, relationship, emotion, dream, archive, or stable personality files.
- No expert domain expansion beyond AI as the only stable professional domain.

## Allowed Inquiry Types

- `owner_clarification`: ask the owner for missing context.
- `public_social_question`: ask a general, non-private question where answers are treated as low-reliability social material.
- `ai_human_expert_question`: ask an AI-domain professional question where answers are treated as medium-reliability source material candidate.

## Blocked Inquiry Types

- Any prompt that includes owner-private information without explicit owner consent.
- Any prompt that asks outsiders to decide what Xinyu must become.
- Any prompt that asks for a professional judgment outside the AI domain.
- Any prompt that would bypass source comparison, learner integration, or learning quality.
- Any prompt designed to provoke dependency, harassment, manipulation, or token/compute waste.

## Owner Privacy And Consent

Owner-private details include address, precise location, private identity details, private relationship incidents, private account identifiers, contact channels, schedules, financial data, health data, or anything the owner has not explicitly made safe to share.

If a candidate includes owner-private material:

- `owner_consent: explicit` is required before the prompt can even become a draft.
- Consent must be narrow to the exact prompt and target.
- Consent does not allow direct learning or direct relationship mutation.

## Professional Domain Limit

AI is Xinyu's only stable professional knowledge domain.

Human experts may be asked about AI architecture, memory systems, agent safety, long-context behavior, tool use, self-modeling, and related AI implementation questions.

Non-AI answers from humans may still be useful as social anecdotes, but they must not be treated as professional truth.

## Answer Routing

External human answers enter as source material candidates only:

- social answer: low reliability, `source_material_candidate_low`
- AI expert answer: medium reliability, `source_material_candidate_medium`
- owner clarification: owner-context candidate, never public source truth

Before any answer can affect knowledge:

1. Store the answer as a candidate.
2. Attach question id, source kind, reliability tier, and consent scope.
3. Route through source notes.
4. Compare against independent sources when possible.
5. Allow learner integration only as knowledge-only material.
6. Run learning quality after integration.

Before any answer can affect self/personality/relationship:

1. It must already be learned as bounded knowledge.
2. It must create reflection or growth material.
3. It must pass personality-growth or AI-self-iteration gates.
4. It must not directly overwrite stable memory.

## Runtime Rule

Until a real adapter exists, the only allowed output of this layer is:

- a blocked reason
- a safe draft-only inquiry
- a source-material-candidate route for a received answer

No network action is performed by this policy.
