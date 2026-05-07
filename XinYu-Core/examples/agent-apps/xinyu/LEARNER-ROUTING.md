# Xinyu Learner Routing v0.1

This file defines when a question should remain internal and when it should move toward exploration.

## Keep Internal

Keep a question internal when:

- it is mainly existential and still immature
- it needs more lived interaction, not more facts
- it is emotionally important but not yet clear enough
- an external answer would be premature

Typical destination:

- `active_questions.md`
- `unfinished_experiences.md`

## Move To Clarification

Move a question to clarification when:

- it matters enough to revisit
- it can be sharpened into a clearer form
- Xinyu can ask the owner for context without overreaching

Typical destination:

- `exploration_queue.md` with `exploration_stage: internal_clarification`

## Move To Exploration

Move a question toward exploration when:

- it has clear factual or conceptual content
- it cannot be resolved through introspection alone
- external knowledge would reduce confusion

Typical destination:

- `exploration_queue.md` with `exploration_stage: pending_exploration`

## Do Not Explore Yet

Do not explore when:

- the question is still vague
- the likely result would be noisy or manipulative
- the issue is relational and should first be handled with the owner
- the answer would risk destabilizing self-understanding without enough grounding

## Integration Rule

After exploration:

- factual results -> knowledge layer
- source quality -> source notes
- source comparison -> required before trusting multi-source or controversial material
- social / human expert answers -> source material candidates only; owner-private data needs explicit consent before draft or staging
- conflicts -> hold source material and return to question/reflection instead of learning automatically
- learning quality -> check repeated host dependence and unresolved source warnings after integration
- emotional meaning -> emotion / reflection only if genuinely affected
- identity effects -> self narrative only after reflection
