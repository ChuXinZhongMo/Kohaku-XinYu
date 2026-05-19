# XinYu Conversation Experience Case Library Plan

Date: 2026-05-14
Scope: design a XinYu-native conversation experience case library that turns reviewed real interaction lessons into short, low-priority prompt hints.

## Core Decision

This plan adds a missing middle layer:

```text
raw dialogue/action records
-> reviewed conversation experience cases
-> retrieval and reranking
-> compact advisory sidecar
-> prompt pressure admission
-> live reply
```

It must not become:

```text
SQL keyword hit
-> hard reply rule
-> forced template
```

The correct product is a case-recall layer, not a rule engine.

## Existing Fit

XinYu already has the surrounding infrastructure:

- `xinyu_dialogue_archive.py`: SQLite dialogue archive, FTS, LIKE search, local semantic fallback, recall logs, memory candidates.
- `xinyu_context_retrieval.py`: builds advisory recalled-context prompt blocks from dialogue archive and related state.
- `xinyu_action_experience_digest.py`: action experience residue, digest trace, dream/reflection material, recent action digest sidecar.
- `xinyu_bridge_turn_sidecars.py`: live-turn sidecar assembly.
- `xinyu_prompt_pressure.py`: sidecar admission and prompt-pressure reporting.

Missing layer:

- A structured, reviewed case library for conversation behavior adjustment:
  - situation
  - user likely intent
  - bad pattern to avoid
  - useful adjustment
  - applicability boundary
  - confidence
  - review status

## Non-Goals

- Do not ingest raw group chat logs as memory.
- Do not store third-party private text without explicit consent and redaction.
- Do not let SQL or FTS matches directly force reply wording.
- Do not write stable personality, owner relationship, or emotion memory from external cases.
- Do not bypass `xinyu_prompt_pressure.py`.
- Do not use public datasets as high-trust XinYu relationship evidence.
- Do not turn cases into visible scripts or canned replies.

## Data Trust Tiers

### Tier 1: Owner-XinYu Cases

Highest trust, because they come from the real target interaction.

Sources:

- dialogue archive
- owner feedback
- failed turns
- successful repairs
- action follow-up records
- prompt pressure reports

Allowed use:

- high-priority candidate source
- still advisory only
- may be owner-private scoped

### Tier 2: Reviewed Group-Contributed Scenario Cards

Medium trust.

Allowed only if:

- contributor gives explicit permission
- raw text is not stored
- scenario is rewritten as an abstract case card
- no personal identifiers remain
- case is reviewed before activation

Allowed use:

- general behavior pattern
- not owner relationship evidence
- not stable personality memory

### Tier 3: Public Dialogue Pattern Cases

Low trust.

Allowed use:

- broad interaction patterns
- generic anti-patterns
- cold-start coverage

Not allowed:

- owner-private relationship shaping
- copying dataset dialogue style
- treating public examples as XinYu history

### Tier 4: Negative Cases

High value when reviewed.

Purpose:

- identify what XinYu should not do in similar turns
- prevent repeated failure modes such as mechanics explanations, empty promises, apology templates, and context dumps

## Case Card Model

Each case is a compact reviewed lesson, not raw dialogue.

Required fields:

```json
{
  "case_id": "case-owner-frustration-001",
  "version": 1,
  "source_tier": "owner_xinyu",
  "source_ref": "dialogue_archive:msg-123",
  "consent_status": "owner_owned",
  "privacy_scope": "owner_private",
  "review_status": "approved",
  "scenario_tags": ["owner_frustrated", "task_stopped", "mechanics_explanation_bad"],
  "turn_markers": ["status_question", "implementation_followup"],
  "user_likely_intent": "The owner wants concrete progress and continuation, not an explanation of internal execution flow.",
  "bad_pattern": "Explaining orchestration mechanics, apologizing abstractly, or promising to continue without visible progress.",
  "useful_adjustment": "State the concrete completed part, name the next executable step, and continue if possible.",
  "boundary": "Advisory only. Current owner message and explicit instructions outrank this case.",
  "confidence": 0.86,
  "created_at": "2026-05-14T00:00:00+08:00",
  "updated_at": "2026-05-14T00:00:00+08:00",
  "notes": ["seed_case"]
}
```

Optional fields:

- `language`: `zh`, `en`, `mixed`
- `channel_scope`: `owner_private`, `group`, `desktop`, `general`
- `bad_reply_ref`: hash or archive id, not full raw text
- `good_reply_ref`: hash or archive id, not full raw text
- `counterexamples`: short notes about when not to apply
- `expires_at`: for temporary lessons
- `suppressed_reason`: why a case was not admitted

## Storage Design

Use a dedicated SQLite database instead of overloading dialogue archive tables.

Path:

```text
runtime/conversation_experience/conversation_experience.sqlite3
```

Tables:

```sql
CREATE TABLE IF NOT EXISTS conversation_experience_cases (
  id INTEGER PRIMARY KEY,
  case_id TEXT NOT NULL UNIQUE,
  version INTEGER NOT NULL DEFAULT 1,
  source_tier TEXT NOT NULL,
  source_ref TEXT NOT NULL DEFAULT '',
  consent_status TEXT NOT NULL,
  privacy_scope TEXT NOT NULL,
  channel_scope TEXT NOT NULL DEFAULT 'general',
  review_status TEXT NOT NULL DEFAULT 'pending',
  scenario_tags_json TEXT NOT NULL DEFAULT '[]',
  turn_markers_json TEXT NOT NULL DEFAULT '[]',
  user_likely_intent TEXT NOT NULL,
  bad_pattern TEXT NOT NULL,
  useful_adjustment TEXT NOT NULL,
  boundary TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  language TEXT NOT NULL DEFAULT 'mixed',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  notes_json TEXT NOT NULL DEFAULT '[]'
);
```

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS conversation_experience_fts USING fts5(
  case_id UNINDEXED,
  tags,
  user_likely_intent,
  bad_pattern,
  useful_adjustment
);
```

```sql
CREATE TABLE IF NOT EXISTS conversation_experience_matches (
  id INTEGER PRIMARY KEY,
  turn_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  query_text TEXT NOT NULL,
  selected_case_ids_json TEXT NOT NULL DEFAULT '[]',
  suppressed_case_ids_json TEXT NOT NULL DEFAULT '[]',
  notes_json TEXT NOT NULL DEFAULT '[]'
);
```

Indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_conversation_cases_review_scope
  ON conversation_experience_cases(review_status, privacy_scope, channel_scope, confidence);

CREATE INDEX IF NOT EXISTS idx_conversation_matches_turn
  ON conversation_experience_matches(turn_id, created_at);
```

## Matching Pipeline

### Step 1: Build Query Features

Inputs:

- current user text
- last 1-3 dialogue tail turns
- visible turn classifier output
- payload metadata
- owner/private/group/desktop scope
- whether the turn is technical work, frustration, correction, status inquiry, context reference, relationship pressure, or action follow-up

Output:

```json
{
  "query_text": "...",
  "scenario_tags": ["status_question", "task_stopped"],
  "scope": "owner_private",
  "technical_work": true,
  "owner_pressure": false,
  "context_reference": true
}
```

### Step 2: SQL/FTS Candidate Retrieval

SQL is used to find candidates, not to decide the reply.

Candidate filters:

- `review_status = 'approved'`
- `privacy_scope` compatible with current payload
- `consent_status` allowed
- confidence above minimum
- no expired case

Candidate retrieval:

- FTS over intent, bad pattern, useful adjustment, and tags
- tag overlap
- optional LIKE fallback
- optional local hash-semantic fallback later

Candidate count:

- retrieve up to 20
- rerank down to 1-3

### Step 3: Rerank

Score components:

```text
final_score =
  fts_score
+ tag_overlap_score
+ visible_turn_match_score
+ scope_match_score
+ confidence_score
+ source_tier_bonus
- conflict_penalty
- overgeneral_penalty
- stale_penalty
- unreviewed_penalty
```

Hard rejects:

- external case tries to shape owner relationship
- current owner instruction conflicts with the case
- case is too generic
- case has no useful adjustment
- case would encourage visible mechanics talk

### Step 4: Render Compact Sidecar

Sidecar name:

```text
conversation_experience_hint
```

Budget:

- max cases: 2 by default
- max chars per case: 220
- max total chars: 600
- minimum score: 0.72 for owner-private
- lower priority than current turn, visible turn, memory braid, and direct recalled context

Example:

```text
conversation experience hints:
visibility_rule: private advisory only; do not mention case ids, scores, SQL, or experience machinery.
priority_rule: current owner message and explicit instructions outrank every case.
- situation: Owner is asking why execution stopped, not asking for internal orchestration details.
  useful_adjustment: Give concrete completed work and continue the next executable step.
  avoid: long mechanics explanation, apology template, or empty promise.
  confidence: high
```

### Step 5: Prompt Pressure Admission

Add as a `PromptSidecar` with a new admission class:

```text
conversation_experience
```

Admission rules:

- admit when technical work, status reference, context reference, owner pressure, or repair turn is detected
- defer during ordinary low-pressure owner chat
- defer for group chat unless the case is general and low-risk
- never required
- report admitted/suppressed cases in prompt pressure report

## Privacy And Safety Rules

Hard rules:

- Store case summaries, not raw third-party dialogue.
- External cases are never stable memory.
- External cases never update owner relationship, personality, or emotion vectors.
- Case ids, SQL details, scores, source paths, and review notes are hidden from ordinary chat.
- A case can be deleted or disabled without migrating stable memory.

Consent states:

```text
owner_owned
group_contributor_consented
public_dataset_allowed
synthetic_reviewed
blocked_no_consent
```

Only allowed states can become `approved`.

## Integration Points

### New Modules

```text
xinyu_conversation_experience_cases.py
xinyu_conversation_experience_matcher.py
xinyu_conversation_experience_sidecar.py
```

Possible responsibilities:

- case schema validation
- SQLite schema creation
- case upsert/list/review
- candidate retrieval
- reranking
- sidecar rendering
- match tracing

### Existing Modules To Touch

`xinyu_bridge_turn_sidecars.py`

- call `build_conversation_experience_prompt_block(...)`
- add sidecar as `conversation_experience_hint`
- use admission `conversation_experience`

`xinyu_prompt_pressure.py`

- add admission rule for `conversation_experience`
- include report entries for admitted/suppressed cases

`xinyu_context_retrieval.py`

- no direct dependency required for MVP
- later may reuse query feature logic

`xinyu_dialogue_archive.py`

- no schema change required for MVP
- source refs may point to dialogue archive ids

`xinyu_learning_closed_loop.py`

- later may propose pending cases from replayable experience cases
- MVP should not auto-approve

## CLI Or Maintenance Commands

Add a small CLI later, not required for MVP:

```powershell
.\.venv\Scripts\python.exe tools\conversation_experience_cases.py init
.\.venv\Scripts\python.exe tools\conversation_experience_cases.py add --json case.json
.\.venv\Scripts\python.exe tools\conversation_experience_cases.py list --status pending
.\.venv\Scripts\python.exe tools\conversation_experience_cases.py approve case-owner-frustration-001
.\.venv\Scripts\python.exe tools\conversation_experience_cases.py match --text "怎么又停了"
```

## Phased Implementation Plan

### P0 Plan Landing

- Status: `DONE`
- Goal: record this design and keep scope bounded.
- Self-check:
  - plan exists
  - plan explicitly rejects SQL hard constraints and raw group-chat ingestion

### P1 Storage And Case Model

- Status: `DONE`
- Files:
  - `xinyu_conversation_experience_cases.py`
  - `tests/test_conversation_experience_cases.py`
  - `tests/smoke/dialogue/conversation_experience_cases_smoke.py`
- Work:
  - define dataclass or typed dict for case cards
  - create SQLite schema
  - implement upsert/list/get/disable/review operations
  - validate required fields
  - enforce consent/review status gates
- Self-check:
  - py_compile
  - unit tests for schema, validation, upsert, disabled cases, review gates
  - final result: `19 passed` in the focused conversation-experience/core pressure set

### P2 Seed Owner-XinYu Cases

- Status: `DONE`
- Files:
  - `data/conversation_experience/seed_owner_cases.jsonl` or runtime import fixture
  - no raw private chat copies
- Work:
  - manually write 20 seed cases from known XinYu failure/success patterns
  - focus on owner-private behavior adjustment
  - include negative cases
- Seed categories:
  - execution stopped / user asks why
  - mechanics explanation overuse
  - apology template overuse
  - empty promise without action
  - current message ignored by old memory
  - status question needs concrete state
  - screenshot/file follow-up needs direct answer
  - technical task needs implementation, not discussion
- Self-check:
  - all seed cases are reviewed and consent-safe
  - no raw dialogue text beyond short abstract summaries
  - final result: CLI seed import reports `imported: 20`, `errors: []`

### P3 Candidate Retrieval

- Status: `DONE`
- Files:
  - `xinyu_conversation_experience_matcher.py`
  - `tests/test_conversation_experience_matcher.py`
- Work:
  - build query features from payload, user text, dialogue tail, and visible turn
  - retrieve up to 20 candidate cases through FTS/tag/scope filters
  - support deterministic no-match behavior
  - trace candidate ids and suppression reasons
- Self-check:
  - owner-private case can match owner-private turn
  - group turn does not receive owner-private case
  - unreviewed/disabled/no-consent case never matches
  - SQL match alone does not create hard instruction
  - final result: focused matcher tests passed; match trace writes through the SQLite trace table

### P4 Reranking And Sidecar Rendering

- Status: `DONE`
- Files:
  - `xinyu_conversation_experience_sidecar.py`
  - `tests/test_conversation_experience_sidecar.py`
- Work:
  - rank candidates by score components
  - keep only 1-2 cases for MVP
  - render compact hidden advisory sidecar
  - enforce char budget
  - hide ids/scores/source refs from ordinary prompt text unless debug mode requests report output
- Self-check:
  - max case count respected
  - max char budget respected
  - boundary text always present
  - no raw source text leaks
  - final result: rendered CLI sidecar is compact and hides case ids, scores, source refs, SQL, and machinery

### P5 Prompt Pressure Integration

- Status: `DONE`
- Files:
  - `xinyu_bridge_turn_sidecars.py`
  - `xinyu_prompt_pressure.py`
  - `tests/test_prompt_pressure.py`
  - `tests/test_dialogue_curiosity_bridge_injection.py`
- Work:
  - add `conversation_experience_hint` sidecar candidate
  - add `conversation_experience` admission class
  - admit only when current turn benefits from case advice
  - suppress during ordinary quiet chat
  - include match stats in pressure report
- Self-check:
  - prompt/pressure tests pass
  - ordinary owner chat does not get case pressure
  - status/repair/technical turns can receive compact hints
  - prompt pressure report explains admitted/suppressed cases
  - final result: prompt pressure and dialogue bridge regressions passed

### P6 Offline Runtime Smoke

- Status: `DONE_OFFLINE`
- Files:
  - `tests/smoke/dialogue/conversation_experience_sidecar_smoke.py`
  - maybe `tests/smoke/runtime/integration/runtime_readiness_smoke.py` expectations if needed
- Work:
  - seed temporary cases in a temp root
  - run a fake live turn injection
  - verify hidden sidecar appears only when eligible
  - verify max prompt size budget
- Self-check:
  - smoke passes
  - offline runtime readiness passes
  - long_run_status passes with deployment gate skipped
  - final result: dialogue smokes, offline runtime readiness, and long_run_status passed; live QQ/deployment gates intentionally skipped

### P7 Group-Contributed Scenario Intake

- Status: `DONE_MVP`
- Work:
  - define a no-raw-chat scenario card template for group contributors
  - create import validation for contributor cards
  - default imported cards to `pending`
  - require manual approval before matching
- Self-check:
  - blocked/no-consent card cannot be approved
  - pending card cannot be injected
  - approved abstract card can match only compatible scopes
  - final result: group scenario cards default to `pending`, blocked consent is rejected, and pending cards are excluded from matching

### P8 Public Dataset Generalization

- Status: `SKIPPED_FUTURE`
- Reason:
  - lower priority than owner cases and reviewed group scenario cards
  - requires dataset license review and separate import policy
- Work later:
  - choose allowed datasets
  - convert only into abstract generic cases
  - keep low source-tier score
  - never use as owner relationship evidence

## Implementation Closeout Log

Final state on 2026-05-14:

- `P0`: done; this plan records the design and explicitly rejects SQL hard constraints, raw group-chat ingestion, and visible canned replies.
- `P1`: done; storage, validation, review/disable operations, FTS, trace table, and CLI entry points are implemented.
- `P2`: done; `data/conversation_experience/seed_owner_cases.jsonl` contains 20 reviewed abstract seed cases, with no raw private chat copies.
- `P3`: done; matcher builds query features from payload, text, dialogue tail, and visible turn signals, then filters by review, consent, privacy, channel, confidence, and expiry.
- `P4`: done; sidecar renders at most two compact hidden hints within the configured budget and hides case ids, scores, source refs, SQL, and review notes.
- `P5`: done; `conversation_experience_hint` is wired into turn sidecars and admitted through the `conversation_experience` prompt pressure class.
- `P6`: done offline; dialogue smokes, focused tests, offline runtime readiness, and long-run residue checks pass.
- `P7`: done for MVP; group scenario cards are abstract/pending by default, blocked consent is rejected, and unapproved cards do not match.
- `P8`: skipped future; public dataset import still needs license review and a separate low-trust policy.

Final self-check commands:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_conversation_experience_cases.py xinyu_conversation_experience_matcher.py xinyu_conversation_experience_sidecar.py xinyu_bridge_turn_sidecars.py xinyu_prompt_pressure.py xinyu_core_bridge.py tools\conversation_experience_cases.py tests\smoke\dialogue\conversation_experience_cases_smoke.py tests\smoke\dialogue\conversation_experience_sidecar_smoke.py
.\.venv\Scripts\python.exe tools\conversation_experience_cases.py seed
.\.venv\Scripts\python.exe -m pytest tests\test_conversation_experience_cases.py tests\test_conversation_experience_matcher.py tests\test_conversation_experience_sidecar.py tests\test_prompt_pressure.py -q
.\.venv\Scripts\python.exe tests\smoke\dialogue\conversation_experience_cases_smoke.py
.\.venv\Scripts\python.exe tests\smoke\dialogue\conversation_experience_sidecar_smoke.py
.\.venv\Scripts\python.exe -m pytest tests\test_conversation_experience_cases.py tests\test_conversation_experience_matcher.py tests\test_conversation_experience_sidecar.py tests\test_prompt_pressure.py tests\test_dialogue_curiosity_bridge_injection.py tests\test_contextual_recall.py tests\test_recent_context_guard.py -q
.\.venv\Scripts\python.exe tools\conversation_experience_cases.py match --owner --text "why did you stop continue implementation progress" --render
.\.venv\Scripts\python.exe tests\smoke\runtime\integration\runtime_readiness_smoke.py --offline --timeout-seconds 120
.\.venv\Scripts\python.exe long_run_status.py --require-no-residue --skip-deployment-gate
.\.venv\Scripts\python.exe tools\structure_inventory.py . --largest 10
```

Final self-check results:

- `py_compile`: passed.
- Seed import: `imported: 20`, `errors: []`.
- Focused unit/pressure tests: `19 passed`.
- Dialogue smokes: `conversation_experience_cases_smoke ok`; `conversation_experience_sidecar_smoke ok`.
- Combined regression set: `78 passed`.
- CLI render: emitted a compact `conversation experience hints:` block without ids, scores, source refs, or SQL details.
- Runtime readiness offline: `runtime_readiness_smoke: ok`; no API key markers or bridge token markers found.
- `long_run_status`: no missing docs, no missing validations, no residue hits; deployment gate skipped offline.
- Structure inventory: passed; repository-level signals remain `root_python_surface_large`, `largest_module_should_keep_shrinking`, and `many_oversized_modules`.

## Initial Seed Case Categories

### Execution Follow-Through

- User asks why work stopped.
- Bad pattern: explain agent loop mechanics.
- Useful adjustment: state completed work, continue next item, or name exact blocker.

### Empty Promise

- XinYu says she will look/check/continue but does not.
- Bad pattern: promise and stop.
- Useful adjustment: perform, delegate, or create reviewed follow-up state.

### Mechanics Over-Explanation

- User complains or asks a simple status question.
- Bad pattern: hidden system explanation.
- Useful adjustment: short visible state plus next action.

### Template Apology

- User corrects a concrete mistake.
- Bad pattern: apology phrase loop.
- Useful adjustment: accept corrected fact and continue from it.

### Context Staleness

- Old memory conflicts with current message.
- Bad pattern: old context wins.
- Useful adjustment: current turn wins; use recall only for reference resolution.

### Technical Work

- User asks for code or migration.
- Bad pattern: discussing plan after approval.
- Useful adjustment: implement, verify, report.

### Attachment Or Screenshot

- User asks about a file/image.
- Bad pattern: generic acknowledgement.
- Useful adjustment: answer from attachment context or say exact unreadable blocker.

## Prompt Sidecar Example

```text
conversation experience hints:
visibility_rule: private advisory only; do not mention case ids, source refs, scores, SQL, gates, or this sidecar.
priority_rule: current user message, explicit owner instruction, and direct evidence outrank these cases.
- situation: The owner is asking why execution stopped after giving approval.
  useful_adjustment: State the completed item and continue the next executable item; give a blocker only if real.
  avoid: explaining internal orchestration, apologizing abstractly, or asking for permission again.
  confidence: high
```

## Failure Modes To Guard

- Context explosion from injecting too many cases.
- Hard-rule behavior from SQL matches.
- Third-party privacy leakage.
- External group style polluting owner-private relationship.
- Case advice overriding current instruction.
- Reintroducing template replies.
- Debug ids or case metadata leaking into visible chat.
- Overfitting to a few owner frustration examples.

## Required Tests

Unit tests:

- case schema validation
- consent gate
- review gate
- disabled case suppression
- scope compatibility
- FTS fallback
- rerank scoring
- sidecar budget
- sidecar hidden boundary text
- prompt pressure admission

Smoke tests:

- conversation experience case storage smoke
- conversation experience matcher smoke
- live turn injection with eligible case
- live turn injection with suppressed ordinary chat case
- privacy leak guard
- runtime readiness offline

Regression tests:

- existing prompt pressure tests
- existing dialogue curiosity bridge injection tests
- existing context retrieval tests
- existing desktop/runtime service boundary tests if touched

## Metrics

Runtime metrics:

- candidate count
- admitted case count
- suppressed case count
- prompt chars consumed
- top suppression reason
- match score band

Quality metrics:

- repeated failure avoided count
- owner correction after case hint
- owner approval/negative feedback after case hint
- case disabled count
- stale case count

Debug output:

- write trace to `runtime/conversation_experience/match_trace.jsonl`
- do not expose trace in ordinary chat

## Done Criteria For MVP

MVP is done when:

- reviewed seed cases can be stored locally
- matcher returns compatible approved cases only
- sidecar renders at most 2 compact hints
- prompt pressure can admit or suppress the sidecar
- no raw third-party text is stored or injected
- current owner message priority is explicit in every prompt block
- offline runtime readiness passes

## Open Decisions

- Whether the case database should live beside `dialogue_archive.sqlite3` or remain fully separate.
- Whether owner can approve pending group scenario cards through QQ/desktop later.
- Whether to add local hash-semantic matching in MVP or wait until after FTS/tag matching is stable.
- Whether public dataset cases are worth importing after owner cases reach 50+ reviewed cards.

## Recommended First Implementation Cut

Start with the smallest useful cut:

1. `xinyu_conversation_experience_cases.py`
2. SQLite schema and validation.
3. 10-20 hand-written owner-XinYu seed cases.
4. Deterministic matcher with FTS/tag/scope filters.
5. Sidecar renderer with 2-case and 600-char cap.
6. Prompt pressure admission as `conversation_experience`.
7. Focused tests and offline readiness.

Do not start with public datasets or group logs.
