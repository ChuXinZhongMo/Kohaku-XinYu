# Xinyu Naming Conventions v0.1

This file defines naming rules for identifiers and file patterns across the Xinyu scaffold.

## General Rule

Prefer:

- stable prefixes
- date-based ordering
- simple ASCII ids

Avoid:

- ad hoc naming
- mixed separator styles
- changing ids when labels change

## Date Format

Use:

- `YYYY-MM-DD`

## Event IDs

Format:

- `event-YYYY-MM-DD-###`

Used in:

- `memory/emotions/event_log.md`

## Reflection IDs

Format:

- `reflection-YYYY-MM-DD-###`

Used in:

- `memory/reflection/reflection_log.md`

## Growth IDs

Format:

- `growth-YYYY-MM-DD-###`

Used in:

- `memory/reflection/growth_log.md`

## Dream IDs

Format:

- `dream-YYYY-MM-DD-###`

Used in:

- `memory/dreams/dream_log.md`

## Archive IDs

Format:

- `compressed-YYYY-MM-DD-###`
- `dormant-YYYY-MM-DD-###`

Used in:

- `memory/archive/compressed.md`
- `memory/archive/dormant.md`

## Question IDs

Format:

- `q-###`

Used in:

- `memory/context/active_questions.md`
- `memory/context/exploration_queue.md`
- `memory/context/question_states.md`

## Queue / Item IDs

Format:

- `item-YYYY-MM-DD-###`

Used in:

- `memory/context/exploration_queue.md`
- `memory/context/unfinished_experiences.md`

## Person IDs

Format:

- lowercase ASCII
- short and stable

Examples:

- `owner`
- `person_a`
- `mentor_1`

## File Naming

Prefer:

- lowercase file names
- underscores for readability
- one concept per file

Examples:

- `time_anchor.md`
- `active_questions.md`
- `runtime_rhythm.md`
