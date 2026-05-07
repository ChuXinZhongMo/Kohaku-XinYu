# Xinyu Execution Order v0.1

This file defines the intended order once work moves from scaffold-building into live runtime validation and iterative tuning.

## Phase A: Keep Scaffold Stable

1. preserve file integrity
2. preserve naming consistency
3. preserve routing clarity

## Phase B: Check Runtime Readiness

1. run `check_runtime_env.py`
2. run `validate_scaffold.py`
3. confirm local environment blockers

## Phase C: First Live Runtime

1. run the first minimal CLI session
2. follow `FIRST-RUN-PLAN.md`
3. keep scope narrow

## Phase D: First Review

1. fill `SESSION-REVIEW.md`
2. compare with `TEST-SCENARIOS.md`
3. compare with `RUNTIME-PRIORITIES.md`
4. inspect key memory files

## Phase E: First Tightening Pass

1. review `FAILURE-MODES.md`
2. apply `PROMPT-TUNING.md`
3. update prompts conservatively

## Phase F: Second Runtime

1. re-run with narrowed prompts
2. check writer selectivity
3. check relationship elasticity
4. check time realism

## Phase G: Controlled Expansion

Only after earlier phases are stable:

1. enable stronger reflection behavior
2. test archive behavior
3. test dream boundary carefully
4. begin exploration-stage validation
5. later test learner-stage integration

## Core Rule

Never unlock more complexity before the earlier layer feels stable.
