# XinYu Knowledge Path Boundary Pass - 2026-05-17

Status: applied as a low-risk subtractive boundary change. This pass did not
move, read, or summarize private memory contents.

## Purpose

`memory/knowledge/*` is still a mixed legacy bucket: some files are runtime
state, some are source-learning notes, and some may later belong under
`library/notes`. Direct path strings make that migration expensive.

This pass starts shrinking that surface by routing high-traffic learning and
automation reads through `xinyu_storage_paths.knowledge_file_path(...)`.

## Applied Changes

- Added `knowledge_dir(root)` and `knowledge_file_path(root, filename)` to
  `xinyu_storage_paths.py`.
- Kept the current live target as `memory/knowledge/`; no data movement.
- Added filename validation so callers cannot pass nested path fragments through
  the knowledge file helper.
- Updated AI self-iteration gate bridge/engine reads to use the helper.
- Updated the automation bridge's dense source/learning snapshot reads to use
  the helper.
- Updated the chat replay fixture exporter to resolve owner seed cases through
  `seed_owner_cases_path(...)` instead of hard-coding legacy
  `data/conversation_experience`.
- Added focused tests for plain roots, workspace-root resolution, and nested
  filename rejection.

## Next Candidate

Continue replacing direct `memory/knowledge/*` paths in source-learning engines
(`autonomous_search_activation_engine`, `learner_integration_engine`,
`learning_quality_engine`) after this pass stays green.
