# Xinyu Changelog

## 2026-04-22

### Phase 1: Foundational Memory Scaffold

- created `examples/agent-apps/xinyu/`
- added initial `config.yaml`
- added `prompts/system.md`
- added `prompts/output.md`
- created first-pass memory files for:
  - self core
  - self narrative
  - emotional state
  - owner relationship
  - relationship index
  - recent context
  - active questions

### Phase 2: Design Documentation

- added `docs/xinyu/memory-system-v0.1.md`
- added `docs/xinyu/memory-schema-v0.1.md`

### Phase 3: Writer Scaffold

- added `emotion_writer`
- added `relationship_writer`
- added `self_narrative_writer`
- added emotion event log

### Phase 4: Time / Reflection / Dream / Archive Structure

- added `time_writer`
- added `reflection_writer`
- added `dream_writer`
- added `archive_writer`
- added:
  - `time_anchor.md`
  - `runtime_rhythm.md`
  - `maintenance_plan.md`
  - `reflection_log.md`
  - `growth_log.md`
  - `dream_log.md`
  - `compressed.md`
  - `dormant.md`

### Phase 5: Runtime Guidance and Validation Files

- added `README.md`
- added `RUNBOOK.md`
- added `TEST-SCENARIOS.md`
- added `WRITER-ROUTING.md`
- added `MEMORY-LINKS.md`
- added `FAILURE-MODES.md`
- added `PROMPT-TUNING.md`
- added `SESSION-REVIEW.md`
- added `FIRST-RUN-PLAN.md`
- added `RUNTIME-PRIORITIES.md`
- added `VALIDATION-INDEX.md`

### Phase 6: Runtime Utility Scripts

- added `validate_scaffold.py`
- added `check_runtime_env.py`

### Phase 7: Runtime Plugin

- added `custom/time_context_plugin.py`
- added plugin wiring in `config.yaml`

### Phase 8: Second-Stage Exploration Scaffold

- added:
  - `EXPLORATION-LOOP.md`
  - `EXPLORATION-SCENARIOS.md`
  - `LEARNING-BOUNDARIES.md`
  - `LEARNER-ROUTING.md`
  - `SECOND-STAGE-ROADMAP.md`
  - `STRUCTURE-NOTES.md`
- added:
  - `exploration_queue.md`
  - `question_states.md`
  - `knowledge/general.md`
  - `knowledge/source_notes.md`
- added `learner_writer`

## Current Status Summary

Xinyu is currently:

- structurally scaffolded
- memory-centered
- time-aware at the prompt and file level
- equipped with staged writer roles
- equipped with validation, review, and tuning documentation

Xinyu is not yet:

- runtime-validated in a complete environment
- running live trigger maintenance loops
- performing real external exploration
- performing real dream / archive behavior beyond scaffold level
