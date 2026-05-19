# XinYu Neuro-Inspired Rules - 2026-05-17

Status: external inspiration notes. These are candidate engineering rules, not claims that XinYu has biology or sentience.

## Source 1 - Hippocampal Indexing / Reinstatement

Source:

- The Cognitive Neuroscience of Memory Representations, PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC12569790/
- Engram neurons: Encoding, consolidation, retrieval, and forgetting of memory, Nature / Molecular Psychiatry: https://www.nature.com/articles/s41380-023-02137-5

Mechanism:

- Episodic retrieval is described as reinstatement/reactivation of distributed processing patterns.
- The hippocampal index idea treats the hippocampus as an index into wider cortical representations, not as the full content store.

XinYu adaptation:

- Store compact indexes and admission reasons, not full prompt payloads.
- `LivingMemoryRecall` should retrieve source pointers plus short summaries, then reconstruct only the needed context for the current turn.
- Recall output should keep three buckets: must remember, experience hints, uncertainty.

Risk:

- If implemented as raw text stuffing, recall becomes larger and less human-like.
- If treated too literally, it becomes fake biology rather than an engineering rule.

Small test:

- Given a direct recall request, assert the prompt contains a compact recalled block, not a raw transcript dump.
- Given a vague current turn, assert no stale long memory outranks live current-turn facts.

Decision:

- Keep as an active rule for memory recall compression.

## Source 2 - Prediction Error / Reconsolidation

Source:

- Prediction Error and Memory Reactivation: How Incomplete Reminders Drive Reconsolidation, PubMed: https://pubmed.ncbi.nlm.nih.gov/31506189/
- Memory Updating and the Structure of Event Representations, PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC12103877/
- Appraising reconsolidation theory and its empirical validation, PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC7614440/

Mechanism:

- Reactivated memories may update when the current cue creates enough mismatch or surprise.
- Human reconsolidation evidence has boundary conditions, so the rule should be conservative.

XinYu adaptation:

- Long-lived memory writes should require prediction error, correction, repeated pattern, or owner-approved summary.
- A single emotional turn should create residue, not stable identity change.
- Corrections should update confidence and uncertainty before rewriting stable memory.

Risk:

- Over-updating makes XinYu unstable and too suggestible.
- Under-updating makes her feel frozen and unable to learn from correction.

Small test:

- Owner says "不是这个": recall result should include uncertainty/correction notes.
- Stable persona write should not happen from one correction unless explicitly approved.

Decision:

- Keep as the memory write gate.

## Source 3 - Interoception / Allostasis / Affect

Source:

- The Neurobiology of Interoception and Affect, PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC11222051/
- Interoception beyond homeostasis: affect, cognition and mental health, PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC5062092/
- Interoception: The Secret Ingredient, PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC8493823/

Mechanism:

- Affect is tightly linked to predictive regulation and internal state signals.
- Interoceptive/allostatic models suggest mood should change attention, priority, and readiness rather than act as a separate fact source.

XinYu adaptation:

- Emotion should be a weight modulator over recall, initiative, and voice, not a standalone "emotion council" that issues separate decisions.
- Runtime state should include energy/pressure/residue as soft bias.
- A tired-owner turn should reduce verbosity and increase concrete care without inventing bodily sensing.

Risk:

- Anthropomorphic overreach if XinYu claims real body signals.
- Flat behavior if emotion is only decorative text and never affects priority.

Small test:

- When owner says they are tired, persona runtime should prefer compact, concrete, low-demand replies.
- Emotion state should not create factual memory by itself.

Decision:

- Keep as a persona/emotion modulation rule.

## Source 4 - Engram Allocation And Memory Lifespan

Source:

- Engram neurons: Encoding, consolidation, retrieval, and forgetting of memory, Nature / Molecular Psychiatry: https://www.nature.com/articles/s41380-023-02137-5
- Finding the engram, Nature Reviews Neuroscience: https://www.nature.com/articles/nrn4000

Mechanism:

- Memory can be considered across encoding, consolidation, retrieval, and forgetting.
- Engram research emphasizes allocation, consolidation, retrieval, and forgetting as separate stages.

XinYu adaptation:

- Split memory handling into:
  - encode: short current-turn trace
  - consolidate: delayed summary into stable memory
  - retrieve: compact source-indexed recall
  - forget/decay: demote stale runtime context
- Do not keep every event equally available forever.

Risk:

- Without forgetting, prompt pressure rises and personality becomes noisy.
- With aggressive forgetting, continuity breaks.

Small test:

- Runtime traces should be disposable unless promoted.
- Recent context should decay into a shorter summary rather than growing unbounded.

Decision:

- Keep as an offline maintenance rule, not live-turn complexity.

## Source 5 - Goal-Directed Memory Control

Source:

- Flexible Prefrontal Control over Hippocampal Episodic Memory for Goal-Directed Generalization, arXiv: https://arxiv.org/abs/2503.02303

Mechanism:

- Goal/task demands can control which episodic memories are retrieved and generalized.

XinYu adaptation:

- The current turn goal should be an explicit scoring input in `LivingMemoryRecall`.
- Technical work, relationship repair, daily care, and direct recall should select different memory lanes.

Risk:

- If goal classification is wrong, recall will feel confidently irrelevant.

Small test:

- Technical task should prefer project/task memory.
- Relationship repair should prefer recent owner-facing residue and corrections.

Decision:

- Keep as a scoring rule, but use deterministic tests before learned weighting.

## Engineering Summary

The useful cross-domain rule is:

```text
XinYu should not remember by storing more.
XinYu should remember by indexing less, retrieving selectively,
letting current state modulate priority, and consolidating only when evidence deserves it.
```

Immediate implementation consequences:

- `LivingMemoryRecall` remains the single recall owner.
- Stable writes require explicit signals.
- Emotion/persona state modulates scoring and expression.
- Runtime traces decay unless promoted.
- External knowledge stays in library/cases, not private lived memory.

## Closeout Artifacts

2026-05-17:

- Added `XinYu-Core/examples/agent-apps/xinyu/xinyu_neuro_memory_rules.py`.
- Added `XinYu-Core/examples/agent-apps/xinyu/NEURO-INSPIRED-ENGINEERING-RULES.md`.
- Added `XinYu-Core/examples/agent-apps/xinyu/tests/test_neuro_memory_rules.py`.
- Updated `MEMORY-REDUCTION-RULES.md` to point to the source-backed rule table.

The code table keeps the biology as source inspiration only and requires each
rule to have source URLs, a concrete XinYu adaptation, a risk boundary, and test
anchors.
