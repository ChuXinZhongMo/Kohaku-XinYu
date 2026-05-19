# XinYu Memory And Library Manifest - 2026-05-17

Status: redacted boundary manifest. This pass did not read private memory, runtime logs, QQ logs, owner-supplied files, or self-found learning content.

## Boundary Decision

XinYu should keep lived memory separate from external reference material.

```text
memory/   lived continuity, relationship state, self state, emotion state, recent context
library/  papers, web notes, source material, external references, research summaries
cases/    reviewed dialogue/reply cases and replay fixtures
runtime/  disposable traces, cache, temporary candidates, logs
```

The current repository still mixes some library-like material under `memory/knowledge` and some case material under `data/conversation_experience`. Do not move those files until config references and tests are updated.

## Current Memory Inputs From Config

`config.yaml` points prompt context to these memory categories:

| Category | Examples | Sensitivity | Target |
| --- | --- | --- | --- |
| self anchor | `memory/self/core.md`, `memory/self/personality_profile.md`, `memory/self/narrative.md` | private/stable | keep in `memory/self` |
| voice/persona | `memory/self/voice_profile_zh.md`, `memory/context/persona_surface_state.md` | private/stable + runtime residue | keep; compress through persona runtime |
| emotion | `memory/emotions/taxonomy.md`, `memory/emotions/current_state.md` | private | keep in `memory/emotions` |
| relationship/people | `memory/relationships/index.md`, `memory/people/owner.md` | private | keep in `memory/relationships` and `memory/people` |
| recent context | `memory/context/recent_context.md` | private/recent | keep; decay and summarize |
| runtime policies | `memory/context/*policy*.md`, `memory/context/*state*.md` | private/runtime | keep while live, later split policy vs runtime |
| dreams/reflection/archive | `memory/dreams/*`, `memory/archive/*` | private/slow | keep, but treat as advisory |
| knowledge | `memory/knowledge/ai_domain.md`, `memory/knowledge/social_inquiry_policy.md` | mixed | future `library/notes` candidate if external |

## Current External/Case Areas

| Path | Current role | Target |
| --- | --- | --- |
| `data/external/` | public/external dataset rows | `library/datasets` candidate |
| `data/conversation_experience/` | reviewed case library | `cases/conversation` candidate |
| `tests/fixtures/` | redacted replay fixtures | keep under `tests` |
| `project-plans/` | design and research plans | `library/notes` or `archive/plans` candidate |
| extracted paper text in workspace root | external paper text | `library/papers` candidate after source metadata is recorded |

## Retention Rules

- Stable self/relationship memory changes require repeated evidence or explicit owner approval.
- Recent context can decay; it should not become stable memory automatically.
- External sources can inform questions and library notes, but cannot directly rewrite owner-private memory.
- Reviewed conversation cases are behavioral hints, not hard rules.
- Runtime traces and replay candidates are disposable unless promoted through redaction and tests.
- Group/public material must not mutate owner-private relationship memory.

## First Safe Cleanup Actions

1. Keep all current paths in place.
2. Add owner surfaces and manifests first.
3. Update code to treat external knowledge and reviewed cases as providers into `LivingMemoryRecall`, not memory facts.
4. Only move `data/external`, root extracted papers, or `memory/knowledge` items after:
   - config references are updated
   - tests pass
   - a source manifest exists
   - no private memory content is exposed

## Pause Conditions

Pause before moving or editing any file if it contains:

- real QQ dialogue
- owner private memory
- local env values or tokens
- raw logs
- non-redacted learning material
- ambiguous public/private source scope

## Applied Cleanup

2026-05-17:

- Created `D:\XinYu\library\`.
- Created `D:\XinYu\library\papers\`.
- Moved untracked root paper extracts into `library/papers/`:
  - `2406.19108v2_extracted.txt`
  - `2509.22447v1_extracted.txt`
- Verified no repository references before moving.
- Left `memory/knowledge`, `data/external`, and `data/conversation_experience` in place because many live modules/tests still reference those paths.
- Created `D:\XinYu\cases\README.md` as the future reviewed-case boundary while keeping current live data paths intact.

## Manifest Validator Added

2026-05-17 closeout:

- Added `XinYu-Core/examples/agent-apps/xinyu/stores/memory_library_manifest.json`.
- Added `XinYu-Core/examples/agent-apps/xinyu/ops/validation/validate_memory_library_manifest.py`.
- Added `tests/test_memory_library_manifest.py`.

The validator checks path boundaries, denylisted runtime/log/shadow paths,
sensitivity, snapshot rules, and file-count thresholds without reading file
contents.
