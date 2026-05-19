# XinYu Subtractive Refactor Autonomous Plan - 2026-05-17

## Mission

Make XinYu smaller, clearer, and more alive by compressing the active system into one main runtime chain:

```text
input
-> current turn state
-> one living memory recall algorithm
-> persona and emotion modulation
-> reply or action
-> memory update
```

Every active module must either serve this chain directly, adapt an external interface into it, or move out of the live path.

This is not another feature sprint. The primary output is subtraction:

- fewer active memory paths
- fewer duplicate modules
- clearer directory ownership
- fewer prompt/persona fragments
- cleaner memory and library boundaries
- stronger evidence for what remains

## Operating Rules While Owner Is Away

2026-05-17 owner override:

Owner grants local full-permission autonomy for this subtractive refactor until the plan is complete. I may inspect and modify XinYu local project files, private runtime logs, local state, memory manifests, generated residue, test artifacts, and operational outputs when needed to finish the plan.

This override changes previous pause rules as follows:

- I may read private local logs/runtime/memory state when needed for diagnosis, migration, cleanup, or validation.
- I may create redacted summaries, manifests, backups, and cleanup scripts.
- I may move, archive, or delete files when inventory evidence shows they are generated, obsolete, duplicate, or safely replaced.
- I may run local validation, status, build, test, and cleanup commands without asking again.
- I may update startup/config/test docs to keep the system coherent.

Remaining hard limits:

- Do not print secrets, tokens, raw QQ/private dialogue, raw memory contents, or local credentials into the chat.
- Do not publish, upload, push, message external accounts, or expose local private data.
- Do not use destructive cleanup on personal/private state unless there is a backup or the file is clearly generated disposable residue.
- Do not use `git reset --hard`, `git checkout --`, or broad revert commands.
- Do not commit unless explicitly asked.

I can continue autonomously when the next step is covered by local evidence.

I must pause and leave notes instead of guessing if any of these happen:

- a deletion target is still imported by live code, config, startup scripts, or tests and no compatibility path exists
- a failing baseline cannot be explained after inspecting local logs/state
- two modules have different behavior and no clear owner should be preserved
- a persona change would visibly alter the relationship, boundaries, or emotional stance without a written contract
- a command needs external publishing, account messaging, or irreversible system changes outside `D:\XinYu`
- the worktree contains user edits in the exact file I need to rewrite and I cannot isolate my patch safely

I should not commit unless explicitly asked. I should keep a running change log in this file or a dated follow-up worklog.

## Non-Negotiables

- Preserve the current live launch path unless a replacement has passed validation.
- Do not add a new subsystem to simplify an old subsystem.
- Do not delete legacy code before there is proof it is unused or safely replaced.
- Do not mix UI redesign, persona rewrite, memory deletion, and bridge transport changes in one unreviewable batch.
- Do not treat prompt text as the only personality system. Persona must be anchored in state, policy, and behavior.
- Do not let group/public material mutate owner-private relationship memory.
- Do not dump more raw history into prompts as a substitute for recall quality.
- Do not touch these without a specific redacted procedure: `.xinyu_bridge_token`, `xinyu.local.env`, QQ gateway config, `logs/`, `runtime/`, `memory/`, `learning/self_found/`, `learning/owner_supplied/`.

## Definition Of Done

The task is complete only when all of these are true:

- Active recall has one documented owner algorithm and one public result shape.
- Old recall/rerank/context paths are either adapters into the owner algorithm, moved to `lab/`, moved to `archive/`, or deleted.
- Every active module has a category: `core`, `adapters`, `stores`, `services`, `lab`, `archive`, or `ops`.
- Duplicate or near-duplicate modules are merged or explicitly retired.
- Persona injection is represented by a small stable contract plus runtime state, not many scattered prompt fragments.
- Memory and library storage have separate manifests and do not blur private lived memory with external reference material.
- A short external research note exists with only implementable hypotheses, not vague inspiration.
- Focused Python tests, smoke checks, and desktop type checks have been run or the reason they could not run is recorded.
- A final audit lists kept modules, merged modules, archived modules, deleted modules, and remaining risks.

## 2026-05-17 Seven-Goal Closeout Status

Closeout record:

- `worklog/xinyu-subtractive-seven-goal-closeout-2026-05-17.md`

Owner's seven ideas now have concrete artifacts:

1. Single memory recall algorithm: `xinyu_living_memory_recall.py`,
   `xinyu_bridge_renderer.py`, `xinyu_runtime_context.py`.
2. Useless-code reduction: bridge route extraction, ops moves, archived
   constant-only manifests, compatibility wrappers.
3. Precise classification: `ops/`, `services/`, `stores/`, archive docs, and
   updated index/structure notes.
4. Persona reinjection: `xinyu_persona_contract.py`,
   `PERSONA-LIVING-SURFACE-RULES.md`, speech-controller living-surface guard.
5. Memory/library organization: `stores/memory_library_manifest.json` and
   `ops/validation/validate_memory_library_manifest.py`.
6. Duplicate/near-duplicate merge: recall compatibility names and extracted
   route families now delegate to owner modules.
7. Neuroscience-inspired rules: `xinyu_neuro_memory_rules.py` and
   `NEURO-INSPIRED-ENGINEERING-RULES.md`.

## Target Architecture

```text
XinYu-Core/
  src/xinyu_runtime/
    core/          generic runtime engine, controller, state machine
    llm/           provider and failover services
    parsing/       shared parsing utilities

  examples/agent-apps/xinyu/
    core/          XinYu-specific turn chain, persona, memory recall, policy
    adapters/      QQ, Desktop, HTTP bridge, Codex bridge
    stores/        state access helpers, memory manifests, library manifests
    services/      embedding, OCR, search, diagnostics, replay
    ops/           startup, health, smoke runner, migration
    lab/           experiments not in live path
    archive/       historical code and notes not imported by live code
```

The old flat `examples/agent-apps/xinyu/*.py` layout can remain temporarily, but each file must be assigned to the target category before it is modified.

## Core Compression Model

### One Living Memory Recall Algorithm

Working name: `LivingMemoryRecall`.

Inputs:

- current user text
- speaker and relationship scope
- current turn facts from transport
- recent dialogue tail
- current goal and unfinished promises
- current emotion and energy state
- stable self/person/relationship memory indexes
- external library hits only when the turn asks for knowledge

Candidate sources:

- live current-turn facts
- recent context
- dialogue archive
- owner/person relationship memory
- unfinished tasks and promises
- self-core and persona anchors
- conversation experience cases
- external library references

Score:

```text
score =
  semantic_relevance
+ relationship_relevance
+ current_goal_relevance
+ emotional_salience
+ freshness
+ authority
+ prediction_error
+ source_confidence
- stale_context_penalty
- duplication_penalty
- privacy_or_scope_penalty
- prompt_pressure_penalty
```

Output:

```text
must_remember: facts that should affect this turn
experience_hints: lived or reviewed cases that can gently shape the answer
uncertainties: missing or conflicting context that should prevent overclaiming
trace: redacted source categories, scores, and admission reasons
```

Memory write rule:

Only write long-lived memory when the turn contains at least one of:

- promise or obligation
- relationship change
- strong affective event
- durable preference
- identity/persona correction
- factual correction
- repeated pattern
- prediction error
- owner-approved summary

Everything else stays in recent context or runtime state and can decay.

### Persona As A Runtime Contract

Persona is split into three layers:

- `self_anchor`: stable identity, values, boundaries, relation to owner
- `living_state`: current mood, energy, concerns, unfinished threads
- `voice_policy`: how to express care, refusal, uncertainty, humor, initiative, and silence

Visible behavior should come from the combination:

```text
reply_style = voice_policy(self_anchor, living_state, turn_context, safety_boundary)
```

The goal is continuity and believable situatedness, not claims of biological life.

## Workstream A - Baseline And Inventory

Goal: know what is live before cutting.

Steps:

1. Record current dirty worktree summary.
2. List active startup paths from root scripts, desktop main process, QQ gateway, and core bridge.
3. Build an import and config reference inventory for `examples/agent-apps/xinyu`.
4. Build a duplicate-name inventory for modules containing these terms:
   `memory`, `retrieval`, `context`, `persona`, `voice`, `emotion`, `initiative`, `proactive`, `gate`, `review`, `bridge`, `qq`.
5. Produce `worklog/xinyu-subtractive-inventory-YYYY-MM-DD.md`.

Commands:

```powershell
cd D:\XinYu
git status --short
rg --files XinYu-Core\examples\agent-apps\xinyu -g "*.py" -g "!memory/**" -g "!runtime/**" -g "!logs/**"
rg -n "import |from |module:|prompt_context_files|writers:|tools:" XinYu-Core\examples\agent-apps\xinyu\config.yaml XinYu-Core\examples\agent-apps\xinyu
```

Validation:

- inventory file exists
- every candidate deletion has at least one reference check
- private raw memory and logs are not read

Continue if:

- the live path can be identified
- likely dead code can be separated from uncertain code

Pause if:

- inventory shows a live import cycle that needs a larger design decision
- deleted smoke files in the worktree make the current baseline ambiguous

## Workstream B - Classification Map

Goal: every file gets an owner category before moving or deleting.

Categories:

- `core`: direct turn-chain logic
- `adapters`: QQ, Desktop, HTTP, Codex, NapCat, CLI
- `stores`: file IO, state IO, memory/library manifests
- `services`: LLM, embeddings, OCR, search, diagnostics
- `ops`: health checks, migration, start/stop, smoke runner
- `lab`: experiments and shadow systems
- `archive`: historical material not imported by live path
- `delete`: unused generated residue, obsolete smoke wrappers, superseded code

Steps:

1. Create a classification table with columns:
   `file`, `current role`, `target category`, `live evidence`, `action`, `risk`.
2. Mark all modules as one of:
   `keep`, `merge`, `adapter`, `lab`, `archive`, `delete`.
3. Do not move files yet unless the classification is obvious and tests are cheap.

Output:

- `worklog/xinyu-module-classification-YYYY-MM-DD.md`

Validation:

- all active root-level Python files under xinyu app are covered
- config plugins and prompt writers are covered
- all planned deletes have no live import/config/startup references

## Workstream C - Unify Memory Retrieval

Goal: replace scattered recall logic with one owner algorithm.

Likely current modules to inspect:

- `xinyu_context_retrieval.py`
- `xinyu_retrieval_need_reranker.py`
- `xinyu_retrieval_envelope.py`
- `xinyu_sparse_memory_router.py`
- `xinyu_contextual_recall.py`
- `xinyu_contextual_self_loop.py`
- `xinyu_conversation_experience_matcher.py`
- `xinyu_dialogue_archive.py`
- `xinyu_recent_context_guard.py`
- memory sync and prompt pressure sidecars

Steps:

1. Freeze the current public recall result shape.
2. Add or choose one owner module for `LivingMemoryRecall`.
3. Move scoring constants and candidate envelope semantics into that owner.
4. Convert existing modules into candidate providers or thin compatibility adapters.
5. Ensure current-turn facts outrank stale memory.
6. Ensure conversation cases are hints, not hard rules.
7. Ensure external knowledge library is separate from private lived memory.
8. Log redacted recall traces with source category and score, not raw private text.
9. Retire duplicate rerank/router modules only after tests prove compatibility.

Validation commands:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests\test_retrieval_need_reranker.py tests\test_retrieval_replay_cases.py tests\test_context_retrieval_owner_scenarios.py tests\test_sparse_memory_router.py -q
.\.venv\Scripts\python.exe smoke_run.py --group replay
.\.venv\Scripts\python.exe -m py_compile xinyu_context_retrieval.py xinyu_retrieval_need_reranker.py xinyu_retrieval_envelope.py xinyu_sparse_memory_router.py
```

Continue if:

- rendered prompt shape stays compatible
- replay cases pass or failures are clearly pre-existing
- recall trace is smaller and more legible

Pause if:

- prompt output changes in a way that affects visible personality without a persona contract update
- tests reveal source-scope leakage between public/group material and owner-private memory

## Workstream D - Merge Repeated Functional Modules

Goal: one capability, one owner.

Merge groups:

- `memory/context/retrieval`: into `LivingMemoryRecall`
- `persona/voice/expression`: into persona runtime contract plus voice policy
- `emotion/current state/council/vector`: into living state modulation
- `initiative/proactive/self-thought`: into one initiative policy with explicit permission gates
- `gate/review/self-iteration`: into one review pipeline or lab-only experiments
- `bridge/desktop/qq helpers`: into adapters with no personality or memory decisions

Steps:

1. For each group, identify the owner module.
2. Convert close duplicates into wrappers for one pass.
3. Update imports and tests.
4. Delete wrapper only after no references remain.
5. Record each merge in the classification table.

Validation:

- focused pytest for the touched capability group
- `py_compile` for touched modules
- no new root-level module with a near-duplicate name

## Workstream E - Reframe The Directory Structure

Goal: make the codebase searchable by responsibility.

Phase E1: documentation-first classification.

- Add target structure to `README.md` or a new `STRUCTURE-NOTES.md`.
- No broad moves yet.

Phase E2: safe moves.

- Move only low-risk non-live scripts first.
- Update imports and direct command references.
- Keep compatibility shims if startup or smoke commands still expect old paths.

Phase E3: live module moves.

- Move live modules only after memory retrieval and bridge adapter boundaries are stable.
- Do one capability group per batch.

Validation:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe xinyu_status.py --json

cd D:\XinYu\XinYu_Desktop
npm run typecheck
```

Pause if:

- import path compatibility becomes unclear
- startup scripts need user-facing behavior changes

## Workstream F - Persona Reinjection

Goal: make XinYu feel more continuous and alive with fewer prompt fragments.

Inputs to inspect:

- `prompts/system.md`
- `prompts/output.md`
- `prompts/live_voice_card.md`
- `prompts/emotion_writer.md`
- `prompts/relationship_writer.md`
- `memory/self/core.md`
- `memory/self/personality_profile.md`
- `memory/self/voice_profile_zh.md`
- `memory/context/persona_surface_state.md`

Steps:

1. Extract a short `Persona Runtime Contract`:
   identity, relationship boundary, agency boundary, memory boundary, emotional expression boundary.
2. Compress stable persona instructions into one canonical source.
3. Move temporary mood and recent concerns into living state, not stable persona.
4. Remove repeated voice rules from scattered prompts.
5. Add regression cases for:
   owner tired/low-energy turn,
   direct factual question,
   correction from owner,
   uncertainty,
   refusal/boundary,
   ordinary casual chat.
6. Verify she does not become theatrical, over-intimate, preachy, or mechanically assistant-like.

Validation:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests\test_visible_persona_voice.py tests\test_prompt_pressure.py tests\test_turn_classifier.py -q
```

Pause if:

- stable memory files need real content edits beyond structural compression
- owner relationship assumptions are ambiguous

## Workstream G - Memory And Library Cleanup

Goal: separate lived memory, external knowledge, cases, and runtime residue.

Target:

```text
memory/
  self/
  people/
  relationships/
  context/
  emotions/
  archive/

library/
  papers/
  web/
  datasets/
  notes/

cases/
  conversation/
  replay/

runtime/
  cache/
  logs/
  traces/
```

Rules:

- Do not read or rewrite raw private memory unless the task has a redacted manifest path.
- First create manifests: path, category, owner, sensitivity, retention policy.
- Move external papers and datasets out of lived memory.
- Keep runtime traces disposable.
- Keep owner-supplied material private and clearly scoped.

Outputs:

- `worklog/xinyu-memory-library-manifest-YYYY-MM-DD.md`
- optional redacted `library/README.md`

Validation:

- no config path breaks
- prompt context files still resolve
- memory writer tools still point to intended files

## Workstream H - External Inspiration Track

Goal: borrow mechanisms from neuroscience and adjacent fields without building vague metaphors.

Research questions:

- Hippocampal indexing: how can XinYu store indexes instead of full prompt payloads?
- Reconsolidation: when should a memory be updated because the present contradicts it?
- Emotional salience: how should mood change recall priority without fabricating facts?
- Consolidation: what offline process can compress recent traces into stable schema?
- Predictive processing: how can prediction error drive curiosity, follow-up, and memory writes?
- Human relationship memory: how should repeated interaction change defaults over time?

Procedure:

1. Search only for primary papers, reviews, or official academic sources.
2. Save links and short implementable notes, not long copied text.
3. Convert each useful idea into one candidate rule.
4. Reject ideas that require fake biology, hidden sentience claims, or opaque behavior.
5. Keep this track in `library/notes/` or `worklog/`, not live code, until a rule is chosen.

Output format:

```text
source:
mechanism:
XinYu adaptation:
risk:
small test:
decision:
```

## Workstream I - Validation And Closeout

Goal: prove the reduced system is smaller and still works.

Baseline tiers:

Cheap checks after every small patch:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile <touched files>
```

Focused Python checks after each capability slice:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest <focused tests> -q
```

Retrieval replay after memory changes:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe smoke_run.py --group replay
```

Runtime readiness after bridge or core changes:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe tests\smoke\runtime\integration\runtime_readiness_smoke.py
```

Desktop after adapter or event-shape changes:

```powershell
cd D:\XinYu\XinYu_Desktop
npm run typecheck
```

Full closeout:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe xinyu_status.py --json

cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

Closeout report:

- changed files
- deleted files
- archived files
- modules merged
- active recall owner
- persona contract owner
- memory/library boundary status
- tests run
- failures or skipped checks
- remaining manual decisions for owner

## Autonomous Execution Order

1. Workstream A: baseline and inventory.
2. Workstream B: classification map.
3. Workstream C: one living memory recall algorithm.
4. Workstream D: merge repeated functional modules that now have clear owners.
5. Workstream E1: document target structure.
6. Workstream F: persona runtime contract and prompt compression.
7. Workstream G: redacted memory/library manifests.
8. Workstream H: external inspiration notes.
9. Workstream E2/E3: move files only after owners and tests are stable.
10. Workstream I: final validation and closeout.

Do not skip A and B. Deletion without inventory is forbidden.

## Batch Size Rules

Each autonomous batch should satisfy all of these:

- one capability group only
- preferably fewer than 12 edited source files
- tests selected before edits
- rollback path is obvious from the patch
- plan/checklist updated before moving on

If a batch wants to touch more than one group, split it.

## First Safe Batch After This Plan

The first implementation batch should not delete code.

Do:

1. Create the inventory report.
2. Create the classification table.
3. Identify the active recall entry point and all recall-related modules.
4. Choose the `LivingMemoryRecall` owner module.
5. Add no behavior change except optional trace/readme notes.

Then run focused retrieval tests if available.

Only after that should code consolidation begin.
