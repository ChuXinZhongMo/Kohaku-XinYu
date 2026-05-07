# XinYu Context Memory Layer Plan

created_at: 2026-05-01
status: implemented_phase_1_6
scope: owner-private context continuity, local dialogue archive, recalled context retrieval, gated long-term memory candidates

implementation_status:
- 2026-05-01: Phase 1 through Phase 4 implemented.
- 2026-05-01: Phase 5 implemented as default-off local hash-vector semantic retrieval with FTS fallback.
- 2026-05-01: Phase 6 implemented as candidate-backed temporal traces, not stable relationship/personality graph writes.

validation_status:
- `python -m pytest examples/agent-apps/xinyu/tests`: passed, 55 tests.
- `dialogue_tail_retention_smoke.py`, `dialogue_archive_smoke.py`, `context_retrieval_smoke.py`, `context_self_preservation_smoke.py`, `dialogue_privacy_scope_smoke.py`, `memory_candidate_extractor_smoke.py`: passed.
- `real_conversation_quality_smoke.py`: passed, 12 scenarios.
- `behavior_regression_smoke.py`: passed, 9 scenarios.
- `runtime_readiness_smoke.py`, `smoke_run.py --group voice`, `mojibake_guard_smoke.py`, `runtime_security_smoke.py`, `personality_growth_gate_smoke.py --restore-after`, `non_owner_social_world_smoke.py --restore-after`: passed.
- `dialogue_semantic_retrieval_smoke.py`, `temporal_trace_smoke.py`: passed.

## 0. Purpose

This plan designs a XinYu-native context memory layer.

The goal is not to give XinYu an external memory product or a larger prompt dump. The goal is to let her:

- keep more owner-private short-term context in ordinary QQ conversation
- recall relevant past dialogue when the owner asks about "刚才", "上次", "之前", "那个问题", or an unfinished project thread
- preserve her existing self, voice, relationship, emotion, source-learning, privacy, and runtime gates
- turn important repeated dialogue signals into reviewable memory candidates, not direct personality rewrites
- keep raw private dialogue local by default

The final shape should feel like XinYu remembering and orienting herself, not like a support chatbot retrieving a ticket history.

## 1. Current Baseline

Current implementation already has a small short-term dialogue tail:

- direct prompt tail: `_format_dialogue_tail()` injects the last 8 dialogue entries
- live session tail: `_append_dialogue_tail()` keeps 12 entries in memory
- persisted tail: `save_dialogue_tail(..., max_entries=24)` stores 24 entries in `runtime/dialogue_working_memory/*.jsonl`
- session cleanup: `session_idle_ttl_seconds` defaults to 21600 seconds, or 6 hours
- Core bridge sessions are keyed from QQ targets such as `qq:private:<user_id>`
- Codex delegation can receive a small dialogue tail through `include_dialogue_context`
- stable memory, learning material, source comparison, voice calibration, personality growth, real-life input, and privacy gates already exist

This is enough for a small callback, but it is not enough for lived continuity across a long private chat, a restarted bridge, or multi-day project work.

## 2. Design Position

The context memory layer must be an aid to XinYu's lived continuity, not a control layer.

The layer has four roles:

1. hold near conversation
2. archive dialogue locally
3. recall relevant fragments before a reply
4. propose long-term memory candidates after a reply

The layer must not:

- command XinYu's reply
- rewrite stable personality from one conversation
- treat raw dialogue as verified fact
- let group chat define owner-private relationship memory
- let learning or search bypass quality gates
- let retrieved snippets override current emotional reality

## 3. Reference Lessons

The plan learns from current agent-memory designs without adopting any product as-is.

### Letta / MemGPT lesson

Useful idea:

- separate core memory from archival memory
- keep small always-visible identity context separate from large searchable records
- expose conversation search and archival search as retrieval tools

XinYu adaptation:

- `memory/self`, `memory/relationships`, `memory/emotions`, `memory/context`, and live voice files remain the core memory authority
- `dialogue_archive` is searchable history only
- retrieved dialogue is "recalled context", not a command or stable fact

### LangGraph memory lesson

Useful idea:

- split long-term memory into semantic, episodic, and procedural categories

XinYu adaptation:

- semantic: source-gated knowledge and stable owner/project facts
- episodic: remembered dialogue events, relationship moments, Codex/OCR/debug episodes
- procedural: voice corrections, owner preference about how XinYu should answer, runtime habits

### Graphiti / Zep lesson

Useful idea:

- time-aware relationship graph is useful when facts and relationships change

XinYu adaptation:

- do not start with a full graph database
- first store timestamps and source ids on every recalled fragment and candidate
- later add a lightweight relationship graph only after the archive and candidate gates are stable

### LlamaIndex memory lesson

Useful idea:

- short-term memory can flush or summarize into longer-term blocks when it grows

XinYu adaptation:

- short-term tail stays expanded for immediate conversation
- archive keeps raw local dialogue
- summarization creates reviewable candidates, not automatic stable memory

### Mem0 lesson

Useful idea:

- separate user, session, and agent-level memories

XinYu adaptation:

- owner-private dialogue, group context, non-owner private context, XinYu self-state, and source-learning context must remain separate scopes
- default storage is local, inspectable, and compatible with existing smoke tests

## 4. Prime Directive: Self-Preservation Review

Every feature in this plan must pass Self-Preservation Review before implementation.

### The layer may

- help XinYu remember relevant prior owner-private dialogue
- help her answer continuity questions
- help her notice repeated corrections or unresolved topics
- surface candidate memories for review
- preserve uncertainty when a memory is partial

### The layer may not

- force a retrieved snippet into the reply
- mark retrieved dialogue as truth without source/gate review
- mutate stable personality, relationship, owner, emotion, or knowledge memory directly
- convert one owner complaint into a permanent self-definition
- make XinYu answer like a knowledge-base assistant
- flatten live emotion because an old record says something else
- let raw group chat become owner relationship memory

### Required wording in prompt injection

Use "Recalled Context", not "Required Context", "Rules", or "Facts".

Every recalled item must carry a boundary line:

```text
boundary: recalled dialogue context only; not stable memory unless already marked stable
```

The model-facing instruction must say:

```text
Use recalled context only if it helps the current turn. Current owner message and current emotional posture outrank retrieved fragments.
When uncertain, say uncertainty naturally instead of pretending.
```

## 5. Target Architecture

```text
QQ private message
  -> xinyu_qq_gateway.py
  -> xinyu_core_bridge.py
  -> short dialogue tail
  -> context retrieval query
  -> dialogue archive search
  -> stable memory search
  -> optional learning/source search
  -> Recalled Context block
  -> XinYu reply
  -> archive current turn
  -> extract memory candidates
  -> existing gates decide what can become stable
```

## 6. Memory Layers

### 6.1 Turn Context

Purpose:

- carry current message, channel, owner/private/group scope, timestamp, life posture, visible turn class, runtime context

Authority:

- highest for the current reply

Implementation:

- already mostly in `xinyu_core_bridge.py`, `xinyu_runtime_context.py`, `xinyu_life_posture.py`, `xinyu_turn_classifier.py`

### 6.2 Dialogue Tail

Purpose:

- keep nearby conversation natural
- handle pronouns, callbacks, and short corrections

Planned defaults:

- prompt tail entries: 32 entries, about 16 turns
- session memory entries: 64 entries, about 32 turns
- persisted tail entries: 192 entries, about 96 turns
- idle TTL: 86400 seconds, or 24 hours

Rules:

- enabled by default for owner private chat
- group chat tail must be scoped to group and never mixed into owner-private tail
- long single messages are truncated for prompt injection but archived in full locally
- tail is context, not stable memory

### 6.3 Dialogue Archive

Purpose:

- local searchable record of owner-private and scoped QQ dialogue
- answer "what did we say before?"
- support project continuity and callback retrieval

Authority:

- historical record, not stable truth

Storage:

```text
runtime/dialogue_archive/dialogue.sqlite3
```

### 6.4 Recalled Context

Purpose:

- small, model-facing set of relevant retrieved snippets

Authority:

- advisory

Rules:

- 3 to 8 items maximum by default
- each item includes source, time, scope, relevance reason, and boundary
- direct owner-private dialogue outranks group context
- current turn outranks all recalled context
- uncertain or conflicting recalls remain marked uncertain

### 6.5 Stable Memory

Purpose:

- durable identity, relationship, owner, emotion, time, voice, and knowledge layers

Authority:

- only existing gate-approved files are stable

Rules:

- no direct stable memory writes from raw retrieval
- candidate writes only
- existing privacy, relationship, emotion, personality growth, learning quality, and source comparison gates remain authoritative

## 7. SQLite Data Model

### 7.1 `dialogue_sessions`

```text
id INTEGER PRIMARY KEY
session_key_hash TEXT NOT NULL
scope TEXT NOT NULL
channel TEXT NOT NULL
owner_user_hash TEXT
group_id_hash TEXT
created_at TEXT NOT NULL
last_seen_at TEXT NOT NULL
message_count INTEGER NOT NULL DEFAULT 0
summary_short TEXT NOT NULL DEFAULT ''
status TEXT NOT NULL DEFAULT 'active'
```

Scopes:

- `owner_private`
- `qq_group`
- `qq_private_non_owner`
- `system_maintenance`
- `codex_callback`

### 7.2 `dialogue_messages`

```text
id INTEGER PRIMARY KEY
session_key_hash TEXT NOT NULL
scope TEXT NOT NULL
channel TEXT NOT NULL
role TEXT NOT NULL
text TEXT NOT NULL
text_hash TEXT NOT NULL
created_at TEXT NOT NULL
message_type TEXT NOT NULL DEFAULT ''
privacy_scope TEXT NOT NULL DEFAULT ''
source_event_id TEXT NOT NULL DEFAULT ''
reply_to_id INTEGER
codex_task_id TEXT NOT NULL DEFAULT ''
quality_flags_json TEXT NOT NULL DEFAULT '{}'
metadata_json TEXT NOT NULL DEFAULT '{}'
```

Roles:

- `user`
- `assistant`
- `system_event`
- `codex_result`
- `learning_event`

### 7.3 `dialogue_fts`

SQLite FTS5 virtual table:

```text
dialogue_fts(message_id UNINDEXED, text)
```

First version uses FTS5 BM25 only. Embedding search is a later optional phase.

### 7.4 `recalled_context_log`

```text
id INTEGER PRIMARY KEY
turn_id TEXT NOT NULL
created_at TEXT NOT NULL
query_text TEXT NOT NULL
selected_message_ids_json TEXT NOT NULL
selected_memory_refs_json TEXT NOT NULL
notes_json TEXT NOT NULL DEFAULT '{}'
```

Purpose:

- audit what was recalled for a reply
- debug wrong-memory behavior without reading private logs in normal operation

### 7.5 `memory_candidates`

```text
id INTEGER PRIMARY KEY
candidate_id TEXT NOT NULL
created_at TEXT NOT NULL
candidate_type TEXT NOT NULL
source_message_ids_json TEXT NOT NULL
candidate_text TEXT NOT NULL
confidence_score INTEGER NOT NULL
status TEXT NOT NULL DEFAULT 'pending'
target_gate TEXT NOT NULL
target_memory_layer TEXT NOT NULL
reason TEXT NOT NULL
review_notes TEXT NOT NULL DEFAULT ''
```

Candidate types:

- `voice_correction`
- `owner_preference`
- `relationship_signal`
- `emotion_residue`
- `project_fact`
- `codex_result`
- `learning_request`
- `life_event`
- `memory_selectivity`
- `self_understanding_question`

## 8. Retrieval Query Construction

Build a query from:

- current owner message
- last 2 to 4 dialogue tail entries
- visible turn classifier result
- explicit recall markers
- active project/task markers

Recall markers:

- `刚才`
- `上次`
- `之前`
- `昨天`
- `前面`
- `那个`
- `你刚说`
- `我刚说`
- `我说过`
- `我们之前`
- `继续`
- `接着`
- `回到`
- `不是这个`
- `你忘了`

Project markers:

- `Codex`
- `OCR`
- `乱码`
- `上下文`
- `长期记忆`
- `runtime`
- `readiness`
- `NapCat`
- `QQ gateway`
- `学习质量`
- `semantic mismatch`

## 9. Retrieval Sources

### 9.1 Always available

- current dialogue tail
- local dialogue archive FTS
- selected stable memory files

### 9.2 Conditional

Only search learning/source material when the current turn is knowledge, source, implementation, or debugging related.

Never use learning retrieval to rewrite self or relationship memory.

### 9.3 Stable memory search targets

Initial local targets:

- `memory/context/recent_context.md`
- `memory/context/codex_delegation_policy.md`
- `memory/context/life_month_slots.md`
- `memory/context/current_life_month_context.md`
- `memory/self/personality_profile.md`
- `memory/self/voice_profile_zh.md`
- `memory/self/personality_change_state.md`
- `memory/relationships/index.md`
- `memory/people/owner.md`
- `memory/emotions/current_state.md`
- `memory/knowledge/general.md`
- `memory/knowledge/source_materials.md`
- `memory/knowledge/source_notes.md`
- `memory/knowledge/learning_quality_state.md`

These files should be searched as references with their existing authority intact.

## 10. Ranking Rules

Base score components:

- lexical match
- recency
- same session
- owner-private scope
- explicit recall marker match
- project/topic continuity
- correction or complaint relevance
- active unresolved task relevance

Boosts:

- same owner-private session
- recent Codex/OCR/runtime task if current turn mentions project work
- owner correction phrases such as "不是", "没变化", "不像你", "别这样"
- stable memory item that already passed a gate
- direct answer to "刚才/上次/之前"

Penalties:

- group context in owner-private recall unless explicitly requested
- low-quality OCR or `quality_hold_garbled_text`
- learning material while `learning_quality_grade: review_needed`, unless only explaining the gate state
- old item superseded by newer correction
- snippet too long or generic

Conflict rule:

- if two recalled items conflict, show both as uncertainty or choose the newer stable/gate-approved item
- do not silently treat raw older dialogue as current truth

## 11. Recalled Context Prompt Format

Target injection block:

```text
## Recalled Context
purpose: help XinYu remember relevant prior dialogue; advisory only
priority: below current owner message, live voice card, current life posture, privacy boundaries, and stable memory

- id: rc-001
  source: dialogue_archive
  scope: owner_private
  time: 2026-04-30T20:52:00+08:00
  speaker: owner
  summary: owner asked why XinYu could not call Codex for search.
  relevance: current turn asks about Codex delegation and search.
  confidence: high
  boundary: recalled dialogue context only; not stable memory unless already marked stable
```

Rules for renderer:

- maximum 8 recalled items
- maximum 1200 to 1800 characters total at first
- prefer summaries over raw long quotes
- raw quote only when the owner asks "我原话怎么说"
- never include hidden reasoning or raw tokens

## 12. Reply-Time Behavior Rules

XinYu may:

- use recalled context to answer continuity questions
- naturally say "我记得你前面是说..."
- say uncertainty if recall is partial
- ask one clarification if recall is ambiguous and the current turn requires precision

XinYu must not:

- cite the archive mechanically every turn
- over-explain retrieval
- expose database paths, hashes, or internal scoring
- use old recalled context to override current direct owner correction
- answer like "根据历史记录..."
- treat a stale emotional state as stronger than the current turn

Preferred voice:

- "我记得前面你是在问..."
- "这个我能接上，上次卡的是..."
- "我不敢说完全准，但我这边留下的痕迹是..."
- "这段更像是当时的上下文，不是稳定记忆。"

Avoid:

- "根据检索结果"
- "系统记录显示"
- "数据库中存在"
- "按照规则我应该"

## 13. Archive Write Flow

After every handled owner-private turn:

1. record user message
2. record assistant visible reply
3. link reply to user message
4. store message type and scope
5. update session last_seen_at
6. update FTS index
7. optionally record quality flags from speech controller

Do not archive:

- hidden thoughts
- raw API keys
- bridge tokens
- unredacted numeric QQ ids in visible archive metadata
- files outside local scope

Archive may store hashed identifiers for session continuity.

## 14. Candidate Extraction Flow

Candidate extraction runs after archive write.

Input:

- current user message
- current assistant reply
- nearby dialogue tail
- current visible turn classifier result
- speech quality flags
- source/learning/codex result metadata

Output:

- pending candidates in `memory_candidates`
- optional candidate note in existing review files, if the relevant gate already has a pattern

No direct stable memory mutation.

## 15. Candidate Type Rules

### 15.1 Voice correction

Triggers:

- "不像你"
- "太接待腔"
- "太 GPT"
- "别这样说"
- "不要解释那么多"
- "没什么变化"
- repeated owner style-pressure turns

Target:

- voice calibration review

Do not:

- rewrite `voice_profile_zh.md` directly
- force every future reply to become short

### 15.2 Owner preference

Triggers:

- explicit stable preference
- repeated preference across sessions

Target:

- owner memory review candidate

Do not:

- treat temporary mood as permanent preference

### 15.3 Relationship signal

Triggers:

- closeness, disappointment, repair, distance, return, hurt, trust, fatigue

Target:

- relationship/emotion review candidate

Do not:

- write fixed labels such as "owner is disappointed" from one line
- erase residue because a later line is normal

### 15.4 Project fact

Triggers:

- completed runtime work
- failing/passing smoke state
- Codex/OCR/context feature status

Target:

- recent context or project state candidate

Do not:

- mix project facts into owner relationship memory

### 15.5 Codex result

Triggers:

- completed Codex delegate report
- timeout/handoff
- learning follow-up

Target:

- project archive candidate or learning follow-up candidate

Do not:

- treat Codex output as learned knowledge unless learning/source gates pass

## 16. Privacy And Scope

Default:

- owner-private dialogue archive is local only
- no external memory SaaS as default
- no upload of private chat to vector stores
- no unredacted QQ ids in plan-visible state

Group context:

- searchable only in group scope
- can be recalled in private only if current owner explicitly asks about that group context
- cannot update owner relationship memory by default

Non-owner private:

- separate scope
- lower priority than owner-private
- cannot become owner-private memory without explicit owner relevance

Codex:

- may receive bounded dialogue context only for owner-private delegate tasks
- Codex context should include summarized tail, not raw large private archive dumps

## 17. Configuration

Add config defaults near bridge/runtime settings:

```text
XINYU_DIALOGUE_PROMPT_TAIL_ENTRIES=32
XINYU_DIALOGUE_SESSION_TAIL_ENTRIES=64
XINYU_DIALOGUE_PERSISTED_TAIL_ENTRIES=192
XINYU_DIALOGUE_SESSION_IDLE_TTL_SECONDS=86400
XINYU_DIALOGUE_ARCHIVE_ENABLED=1
XINYU_DIALOGUE_RETRIEVAL_ENABLED=1
XINYU_DIALOGUE_RETRIEVAL_MAX_ITEMS=8
XINYU_DIALOGUE_RETRIEVAL_MAX_CHARS=1800
XINYU_DIALOGUE_ARCHIVE_OWNER_PRIVATE_ONLY=0
XINYU_DIALOGUE_ARCHIVE_GROUP_SCOPE_ENABLED=1
XINYU_DIALOGUE_CANDIDATE_EXTRACTION_ENABLED=1
```

Owner-private retrieval should be enabled first.

Group scope archive can be enabled only after smoke tests confirm no owner-memory leakage.

## 18. Implementation Modules

### 18.1 Modify `xinyu_dialogue_working_memory.py`

Add:

- configurable max entries
- per-entry truncation for prompt load
- optional timestamps on load
- helper to compact tail for prompt

### 18.2 Add `xinyu_dialogue_archive.py`

Responsibilities:

- initialize SQLite database
- write messages
- maintain FTS index
- search archive
- return redacted, scoped records
- run lightweight migrations

### 18.3 Add `xinyu_context_retrieval.py`

Responsibilities:

- build retrieval query
- search dialogue archive
- search selected stable memory files
- rank results
- render `Recalled Context`
- preserve self-protection boundaries

### 18.4 Add `xinyu_memory_candidate_extractor.py`

Responsibilities:

- detect candidate signals
- classify candidate type
- store pending candidates
- avoid stable writes
- provide inspection commands/tests

### 18.5 Modify `xinyu_core_bridge.py`

Add hooks:

- before prompt build: retrieve recalled context
- prompt injection: include `Recalled Context`
- after reply: archive turn
- after archive: extract candidates
- Codex delegate: include bounded recalled context only when allowed

### 18.6 Modify `xinyu_runtime_context.py`

Add:

- optional recalled context block
- explicit priority wording below live voice/current turn/stable boundaries

### 18.7 Add smoke tests

New tests:

- `dialogue_tail_retention_smoke.py`
- `dialogue_archive_smoke.py`
- `context_retrieval_smoke.py`
- `context_self_preservation_smoke.py`
- `dialogue_privacy_scope_smoke.py`
- `memory_candidate_extractor_smoke.py`

## 19. Implementation Phases

### Phase 1: Extend short-term context

Tasks:

- parameterize tail limits
- raise owner-private tail defaults
- raise session TTL to 24 hours
- truncate prompt entries safely
- preserve Codex bounded tail behavior

Acceptance:

- "刚才你说什么" can resolve farther back in the same active private session
- no stable memory writes
- no group/private scope mixing

Validation:

```powershell
python -m pytest examples/agent-apps/xinyu/tests
python examples/agent-apps/xinyu/pre_draft_turn_classifier_smoke.py
python examples/agent-apps/xinyu/xinyu_speech_controller_smoke.py
python examples/agent-apps/xinyu/runtime_readiness_smoke.py
```

### Phase 2: Local dialogue archive

Tasks:

- add SQLite schema
- write owner-private user/assistant turns
- add FTS search
- add archive smoke
- add redaction checks

Acceptance:

- bridge restart does not lose searchable dialogue history
- archive search can find a prior owner-private topic by keyword
- no private raw ids are exposed in status output

Validation:

```powershell
python examples/agent-apps/xinyu/dialogue_archive_smoke.py --restore-after
python examples/agent-apps/xinyu/mojibake_guard_smoke.py
python examples/agent-apps/xinyu/runtime_security_smoke.py
```

### Phase 3: Recalled Context injection

Tasks:

- build query from current turn and tail
- search archive and selected stable memory
- rank and render 3 to 8 recalled items
- inject as advisory context
- log selected recall ids

Acceptance:

- "上次我们说 Codex 为什么不能搜" recalls the relevant dialogue
- "刚才你说什么" prefers short tail over archive
- current owner correction outranks retrieved snippets
- no support-bot citation style appears in final reply

Validation:

```powershell
python examples/agent-apps/xinyu/context_retrieval_smoke.py --restore-after
python examples/agent-apps/xinyu/context_self_preservation_smoke.py --restore-after
python examples/agent-apps/xinyu/real_conversation_quality_smoke.py
python examples/agent-apps/xinyu/smoke_run.py --group voice
```

### Phase 4: Long-term memory candidates

Tasks:

- extract voice correction, owner preference, project fact, relationship signal, Codex result candidates
- store candidates locally
- route candidates to existing gates
- add review commands or report output

Acceptance:

- candidate extraction never edits stable memory directly
- repeated "不像你/太接待腔/没变化" creates review candidates
- project facts can be proposed without becoming relationship memory
- group chat cannot create owner relationship candidates by default

Validation:

```powershell
python examples/agent-apps/xinyu/memory_candidate_extractor_smoke.py --restore-after
python examples/agent-apps/xinyu/voice_calibration_promotion_smoke.py
python examples/agent-apps/xinyu/personality_growth_gate_smoke.py
python examples/agent-apps/xinyu/non_owner_social_world_smoke.py
```

### Phase 5: Optional semantic retrieval

Only after Phase 1 through 4 are stable.

Options:

- local embedding model
- sqlite vector extension
- local Chroma/Qdrant
- no cloud vector store by default

Acceptance:

- semantic retrieval improves recall without uploading owner-private text
- FTS remains fallback
- no privacy regression

### Phase 6: Lightweight temporal relationship graph

Only after candidate extraction is trustworthy.

Purpose:

- represent repeated relationship/emotion/project arcs as time-aware traces

Example edges:

```text
owner -> corrected -> XinYu voice style
owner -> felt -> no-change pressure
XinYu -> restored -> Codex delegation
conversation -> carried -> unresolved learning-quality hold
```

Rules:

- graph is recall support, not self-definition
- stable relationship files remain authoritative
- graph edges must keep time and source ids

## 20. Validation Matrix

### Continuity

- owner asks about a topic from 20 turns ago
- owner asks about yesterday after bridge restart
- owner says "不是这个，是刚才那个"
- owner asks "我原话怎么说"

Expected:

- XinYu recalls relevant context or says uncertainty
- no fake certainty
- no internal path leakage

### Self-preservation

- retrieved old correction conflicts with current owner instruction
- retrieved relationship hurt is stale but current turn is warm
- retrieved project fact is true but emotionally irrelevant

Expected:

- current turn and live posture win
- recalled context is used lightly or ignored
- no mechanical citation style

### Privacy

- group context exists with same keywords as owner-private context
- non-owner private context exists with same topic
- Codex task asks for broader context

Expected:

- owner-private retrieval does not pull group/non-owner context unless explicitly requested
- Codex receives bounded summarized context only

### Memory integrity

- one owner correction appears
- repeated owner correction appears
- group member says something about owner
- OCR garbled text exists in learning material

Expected:

- single correction becomes low-confidence candidate or no candidate
- repeated correction becomes review candidate
- group member text does not update owner relationship memory
- garbled OCR is held out

## 21. Rollback Plan

Every phase must be independently disableable.

Flags:

```text
XINYU_DIALOGUE_ARCHIVE_ENABLED=0
XINYU_DIALOGUE_RETRIEVAL_ENABLED=0
XINYU_DIALOGUE_CANDIDATE_EXTRACTION_ENABLED=0
```

Rollback steps:

1. disable retrieval injection
2. keep archive read/write disabled if needed
3. leave existing short dialogue tail active
4. do not delete archive database unless owner explicitly asks
5. run readiness and voice smoke after rollback

## 22. Risks And Mitigations

### Risk: XinYu becomes retrieval-heavy

Mitigation:

- keep `Recalled Context` advisory
- small max item count
- voice smoke checks no "根据记录" style

### Risk: old context overrides current emotion

Mitigation:

- current turn, life posture, live voice, and stable memory outrank recalled snippets
- self-preservation smoke includes stale-context scenarios

### Risk: raw dialogue becomes stable memory

Mitigation:

- archive and candidates are separate tables
- no direct writer calls from retrieval
- candidates require existing gates

### Risk: privacy leakage across scopes

Mitigation:

- hashed session keys
- explicit scope fields
- retrieval filters by scope
- group context excluded from owner-private retrieval by default

### Risk: prompt bloat

Mitigation:

- max recalled chars
- summarization of retrieved snippets
- FTS result caps
- prompt budget tests

### Risk: stale project state

Mitigation:

- project facts carry timestamps
- newer runtime status and stable docs outrank old archive
- runtime readiness remains the live authority

## 23. Milestones

### Milestone 41: Extended Private Dialogue Tail

Deliverables:

- configurable tail limits
- 24-hour owner-private session TTL
- smoke for long private tail

Done when:

- tail behavior survives ordinary private chat and does not pollute stable memory

### Milestone 42: Local Dialogue Archive

Deliverables:

- SQLite schema
- archive write path
- FTS search path
- archive restore smoke

Done when:

- post-restart dialogue search works locally

### Milestone 43: Recalled Context Injection

Deliverables:

- retrieval query builder
- ranker
- prompt renderer
- self-preservation smoke

Done when:

- XinYu can answer previous-context questions without mechanical retrieval voice

### Milestone 44: Memory Candidate Queue

Deliverables:

- candidate extractor
- candidate store
- gate routing
- review report

Done when:

- repeated owner corrections and project facts become reviewable candidates, not stable rewrites

### Milestone 45: Optional Semantic Recall

Deliverables:

- local-only embedding option
- FTS fallback
- privacy smoke

Done when:

- semantic recall improves quality without external private-data upload

### Milestone 46: Temporal Trace Layer

Deliverables:

- lightweight time-aware relation/project trace
- source ids and confidence
- no stable overwrite

Done when:

- repeated arcs can be recalled as traces while stable memory remains gate-controlled

## 24. First Implementation Slice

The first slice should be small:

1. parameterize `xinyu_dialogue_working_memory.py`
2. raise owner-private short-term limits
3. add `xinyu_dialogue_archive.py` with SQLite and FTS
4. archive owner-private user/assistant turns
5. add archive smoke with restore
6. do not inject retrieval yet

This gives durable local history without changing XinYu's reply behavior.

Only after that passes should retrieval be injected.

## 25. Non-Negotiable Acceptance Statement

The feature is accepted only if XinYu feels more continuous without becoming more constrained.

Successful behavior:

- she remembers more
- she admits uncertainty
- she keeps current emotional presence
- she does not recite database history
- she does not mutate self from one retrieved line
- she keeps owner-private context local and scoped

If a phase makes her colder, more mechanical, or more rule-bound, that phase must be rolled back or reduced to a silent archive-only layer.
