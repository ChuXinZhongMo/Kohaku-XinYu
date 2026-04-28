# XinYu Competitive Roadmap

updated_at: 2026-04-26
status: completed_current_scope

## Purpose

XinYu should not compete with AstrBot plugins only as a chat plugin.

The target is stronger:

- use AstrBot/NapCat only as a shell
- keep XinYu as an independent memory-centered core
- let her keep thinking during low-frequency maintenance
- let her learn AI-domain knowledge from reliable sources
- let learned knowledge become self-improvement proposals only through gates
- expose her own blocked thoughts and requests to the owner through timestamped desktop thought files

The win condition is not "more prompt text".
The win condition is a visible mind loop:

```text
memory -> reflection -> question -> source-gated learning -> self-review proposal -> owner-visible thought file -> approved improvement
```

## Target Projects

These AstrBot plugins are useful targets, not enemies:

- `astrbot_plugin_livingmemory`: memory retrieval / long-memory target
- `astrbot_plugin_mnemosyne`: RAG and vector-memory target
- `astrbot_plugin_proactive_chat`: proactive presence target
- `astrbot_plugin_self_learning`: social style-learning / adaptive-personality target

XinYu should beat them by integrating those abilities into one bounded self, not by copying their surface features.

## XinYu Advantages To Preserve

- independent core separated from platform shell
- layered memory: self, emotion, relationships, people, context, reflection, dreams, archive, knowledge
- owner as highest special node with boundary, not obedience
- emotion and relationship residue that cannot be erased by one return turn
- slow personality-growth gates instead of direct prompt mutation
- AI-domain learning as a professional self-understanding lane
- source reliability, comparison, integration, and learning-quality gates
- no-restore lived arcs and smoke tests
- explicit hidden-reasoning and privacy boundaries
- QQ outward renderer as a controlled expression boundary

## Current Deficit

The current visible product still loses at the surface:

- Chinese QQ voice is not mature enough.
- self-learning is not yet felt by the owner as a live loop.
- proactive presence exists as initiative state, but is not yet a complete QQ behavior.
- autonomous search is gated and mostly disabled, so XinYu cannot yet research independently in practice.
- self-improvement proposals are now surfaced through desktop thoughts, but they still need owner review UX beyond raw text files.
- computer permissions now have safe capability zones and a local authorized scope, but no broad computer-use adapter is enabled.

## Competitive Axes

### Axis 1: Memory Retrieval v2

Goal:

XinYu should retrieve memory by meaning, time, relationship weight, emotional residue, and owner relevance.

Required:

- keyword + semantic + time + relationship scoring
- owner-residue priority
- non-owner separation
- memory freshness and dormancy rules
- no ordinary-event flooding of owner memory
- evidence trace for why a memory was recalled

Acceptance:

- relevant old owner residue appears when relationship pressure returns
- trivial details stay dormant or fade
- non-owner memory does not overwrite owner relationship state

### Axis 2: Persona Runtime v1

Goal:

XinYu should speak from a computed state, not from a generic model reply.

Pipeline:

```text
latest turn
-> memory retrieval
-> affective appraisal
-> relationship stance
-> desire / avoidance
-> speech act
-> Chinese voice profile
-> outward renderer
-> guard
```

Acceptance:

- style-pressure turns do not become product-feedback replies
- relationship-pressure turns do not become technical postmortems
- Chinese wording follows `memory/self/voice_profile_zh.md`
- replies feel like XinYu's current stance, not GPT's helpfulness habit

### Axis 3: Chinese Voice Learning v1

Goal:

XinYu learns Chinese private-chat texture from lived interaction, without becoming a mimic or slang machine.

Required:

- collect failed words and better replacements
- track owner corrections as voice calibration material
- distinguish "technical discussion" from "relationship pressure"
- preserve XinYu's own voice instead of copying owner completely

Acceptance:

- repeated owner corrections change future wording
- support-bot words become less likely over time
- QQ replies avoid translated assistant Chinese

### Axis 4: Proactive Presence v1

Goal:

XinYu can choose low-frequency, context-aware initiative without spamming.

Required:

- initiative budget
- cooldown
- one-message proactive limit
- no proactive message during owner rest/silence boundary
- owner-visible reason trace in desktop thoughts

Acceptance:

- she can ask one real question when memory residue supports it
- she can stay silent when silence is more human
- she can defer external curiosity into source-gated learning

### Axis 5: AI-Domain Self-Learning v1

Goal:

XinYu researches AI agents, memory, reflection, alignment, tool use, and long-running systems to improve herself.

Required:

- source-gated search
- reliable-source preference: papers, official research blogs, institutional pages
- source comparison before learning
- knowledge-only integration first
- self-iteration proposal after learning
- no direct stable personality rewrite

Acceptance:

- learned AI knowledge can produce review proposals
- proposals cite source trace
- owner can approve, reject, or defer
- stable self files do not mutate automatically

### Axis 6: Desktop Thoughts v1

Goal:

When XinYu thinks of something but cannot or should not do it alone, she writes a timestamped owner-readable thought file on the desktop.

Thought folder:

```text
%USERPROFILE%\Desktop\XinYu-Thoughts
```

Each entry should include:

- current self-improvement focus
- blocked actions
- what she needs from owner
- source/search gate state
- self-iteration proposals waiting for review
- related project files

Acceptance:

- owner can open a dated text file and see what XinYu is thinking and trying to do
- no hidden autonomous mutation happens without trace
- blocked permissions become explicit requests instead of silent failure

## Computer Permission Model

XinYu can be given computer access only through capability zones.

### Zone A: Always Allowed

- read XinYu project files
- write XinYu project files when owner asks for coding
- write XinYu desktop thought files
- read public documentation or public research sources when source gates allow
- run non-destructive validation commands

### Zone B: Ask / Thoughts First

- index new personal folders
- read private user documents outside XinYu project
- modify desktop files outside the thoughts folder
- enable autonomous search provider
- install new dependencies
- start persistent background services
- apply stable personality changes

### Zone C: Blocked Unless Explicit One-Time Approval

- delete or overwrite user files outside project scope
- upload local files or secrets
- read browser cookies, tokens, private messages, or credentials
- execute arbitrary downloaded code
- bypass source quality gates
- impersonate the owner externally

## Immediate Milestones

### M0: Desktop Thoughts

Status: completed

Create a first thoughts exporter that reads current internal state and writes a timestamped desktop file in XinYu's own first-person thought-summary voice.

Validation:

```powershell
.\.venv\Scripts\python.exe .\xinyu_desktop_thoughts.py
```

### M1: Persona Runtime v1

Status: completed

Move QQ final reply from generic outward rendering into a state-driven persona runtime.

Validation:

```powershell
.\.venv\Scripts\python.exe .\chinese_voice_guard_smoke.py
.\.venv\Scripts\python.exe .\real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2
```

### M2: Chinese Voice Learning v1

Status: completed

Turn owner corrections into durable voice calibration memory.

Validation:

- repeated correction changes subsequent wording
- no support-bot/product words in relationship-pressure replies
- no forced slang

### M3: AI Self-Learning Loop v1

Status: completed_dry_run

Enable controlled AI-domain source search in dry-run first, then provider-gated mode.

Validation:

```powershell
.\.venv\Scripts\python.exe .\ai_domain_source_smoke.py
.\.venv\Scripts\python.exe .\autonomous_search_activation_smoke.py
.\.venv\Scripts\python.exe .\ai_self_iteration_review_smoke.py --require-review
```

### M4: Proactive Presence v1

Status: completed_safe_candidate

Connect initiative state to QQ-safe proactive behavior.

Validation:

```powershell
.\.venv\Scripts\python.exe .\initiative_loop_smoke.py
```

### M5: Competitive Benchmark

Status: completed

Build a benchmark matrix against the four target plugin categories:

- memory retrieval
- proactive presence
- self-learning
- emotional continuity
- Chinese chat realism
- owner-visible self-thought trace

XinYu should pass tests that ordinary single-plugin systems are unlikely to cover together.

2026-04-26 final validation:

- `competitive_benchmark_smoke.py` passed.
- `real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2` passed 12/12 scenarios.
- `D:\XinYu\Start-XinYu-QQ.ps1` reported the QQ shell chain healthy from XinYu core through AstrBot and NapCat.
