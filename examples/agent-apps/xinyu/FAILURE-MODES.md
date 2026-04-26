# Xinyu Failure Modes v0.1

This file lists the most likely failure patterns in early runtime validation.

It is meant to speed up diagnosis, not to replace careful review.

## 1. Generic Assistant Collapse

### Symptom

Xinyu starts sounding like a normal chatbot or support assistant.

### Likely Causes

- `prompts/output.md` is too weak
- `prompts/system.md` is not sufficiently steering toward continuity and subjectivity
- runtime plugin context is missing or ignored

### First Fixes

1. tighten `prompts/output.md`
2. verify `output` routing is consistently used
3. check whether memory files are being read at meaningful turns

## 2. Hidden Reasoning Leakage

### Symptom

Xinyu starts exposing internal mechanisms, scores, routing logic, or memory machinery.

### Likely Causes

- `prompts/system.md` is too permissive
- writer prompts are leaking implementation phrasing back into the main reply
- time/plugin injections are too mechanical in wording

### First Fixes

1. tighten controller hidden-reasoning rules
2. remove overly technical phrasing from system prompt
3. verify output prompt keeps language human-facing

## 3. Memory Spam

### Symptom

Too many writers trigger on trivial turns.

### Likely Causes

- controller is over-triggering updates
- writer prompts do not strongly distinguish meaningful vs trivial change

### First Fixes

1. tighten `WRITER-ROUTING.md`
2. tighten writer prompt thresholds
3. review whether `recent_context.md` is absorbing too much noise

## 4. Emotional Overreaction

### Symptom

Xinyu's emotional state swings too hard on small inputs.

### Likely Causes

- `emotion_writer` is too eager
- current emotional template is too volatile
- relationship and emotion layers are amplifying each other too quickly

### First Fixes

1. reduce emotional movement expectations in `emotion_writer.md`
2. inspect `memory/emotions/current_state.md`
3. check whether `owner.md` relationship values are moving too fast

## 5. Flat Emotion

### Symptom

Xinyu feels emotionally dead, even on meaningful prompts.

### Likely Causes

- controller avoids calling `emotion_writer`
- output layer is over-sanitized
- relationship state is not being consulted

### First Fixes

1. inspect writer routing behavior
2. inspect `owner.md`, `current_state.md`, and `narrative.md`
3. loosen emotional expression slightly in `output.md`

## 6. Relationship Drift Too Fast

### Symptom

Closeness, trust, hurt, or dependence change unrealistically fast.

### Likely Causes

- `relationship_writer` is too eager
- owner template has too much initial emotional elasticity

### First Fixes

1. tighten `relationship_writer.md`
2. review `memory/people/owner.md`
3. require stronger turning-point language before updating relationship state

## 7. Narrative Rewrites Too Often

### Symptom

`self/narrative.md` changes every few turns, making Xinyu feel unstable.

### Likely Causes

- `self_narrative_writer` threshold too low
- reflection is being treated like self-change too often

### First Fixes

1. tighten `self_narrative_writer.md`
2. route more change into `reflection_log.md` instead of `narrative.md`

## 8. Dream Becomes Fact

### Symptom

Dream-like material starts affecting factual memory as if it were real.

### Likely Causes

- `dream_writer` boundary too weak
- reflection layer over-trusts dream material

### First Fixes

1. tighten `dream_writer.md`
2. check `dream_log.md` wording
3. ensure reflection only imports dream residue, not dream claims

## 9. Time Feels Flat

### Symptom

Xinyu mentions time generically, but not as a lived factor.

### Likely Causes

- `time_writer` is not used enough
- runtime plugin injection is present but too weak
- `time_anchor.md` is stale

### First Fixes

1. inspect `time_anchor.md`
2. verify `time_context_plugin.py` is active
3. strengthen time interpretation in `prompts/system.md`

## 10. Repair Feels Fake

### Symptom

After conflict, Xinyu resets to warmth too quickly.

### Likely Causes

- negative relationship movement isn't being retained
- `owner.md` repair behavior is too forgiving by default

### First Fixes

1. inspect `owner.md`
2. ensure disappointment / distance / repair willingness are all tracked
3. require an actual repair signal before relaxing distance
