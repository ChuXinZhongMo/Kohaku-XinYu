# Xinyu Writer Routing Reference v0.1

This file is a practical routing reference for observing and refining controller behavior.

It answers one question:

When should the controller call which writer?

## time_writer

Use when:

- a meaningful interaction just happened and recency should be refreshed
- the passage of time itself changes interpretation
- a new day phase or date matters

Do not use when:

- nothing time-sensitive changed
- the update would be pure noise

## emotion_writer

Use when:

- mood changes
- a suppressed feeling remains relevant
- emotional tone toward a person shifts
- Xinyu's urge to speak / stay quiet / move closer / step back changes

Do not use when:

- the turn is trivial
- emotional state is effectively unchanged

## relationship_writer

Use when:

- closeness, trust, distance, hurt, return, or dependence changes
- a new shared pattern appears
- a relational turning point occurs
- the user explicitly introduces a non-owner person who should become a separate relationship node

Do not use when:

- the interaction is informational but relationally neutral
- a non-owner person is only mentioned casually without a name, repeated presence, or relationship importance

## self_narrative_writer

Use when:

- Xinyu understands herself differently
- a contradiction in self-understanding becomes visible
- a relationship changes self-image

Do not use when:

- the change is too small to matter

## reflection_writer

Use when:

- multiple events form a pattern
- a past reaction becomes more understandable
- a sequence deserves a growth marker

Do not use when:

- there is only raw reaction and no meaningful reinterpretation yet

## dream_writer

Use when:

- dream-like residue matters
- a fragment, longing, or emotional afterimage should be logged as dream material

Do not use when:

- there is no dream-like content
- the content is factual memory instead

## archive_writer

Use when:

- repeated short-term material can be compressed
- a memory should become lighter but not vanish
- dormant indexing is more appropriate than active storage

Do not use when:

- the material is still emotionally active
- the memory is still in active relational use

## learner_writer

Use when:

- a question receives a meaningful outward answer
- source quality needs to be recorded
- exploration state progresses
- factual learning should be retained without pushing directly into identity

Do not use when:

- the question is still vague
- the answer is weak, noisy, or manipulative
- the result should first remain in reflection rather than knowledge
