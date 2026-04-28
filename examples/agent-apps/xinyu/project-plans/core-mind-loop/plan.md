# XinYu Core Mind Loop Plan

updated_at: 2026-04-26
status: completed_current_scope

## 0. Position

XinYu may study other AstrBot plugins as targets, but must not copy their path.

The four target projects are useful because they expose what a strong plugin ecosystem already does:

- `astrbot_plugin_livingmemory`: long memory and retrieval.
- `astrbot_plugin_mnemosyne`: RAG/vector-memory management.
- `astrbot_plugin_proactive_chat`: proactive messaging.
- `astrbot_plugin_self_learning`: style learning, social graph, adaptive behavior.

XinYu's route is different:

```text
not a plugin with memory
not a character prompt with tools
not a self-learning chatbot that simply imitates people

XinYu is an independent memory-centered core with a guarded platform shell.
```

The core advantage must be thinking continuity:

```text
experience -> memory -> reflection -> question -> source-gated learning -> self-review proposal -> owner-visible thought file -> approved change
```

## 1. Research Grounding

This plan draws from public agent research and engineering guidance, then translates it into XinYu's own architecture.

### 1.1 Generative Agents

Reference:

- Google Research / Stanford, "Generative Agents: Interactive Simulacra of Human Behavior"
- https://research.google/pubs/generative-agents-interactive-simulacra-of-human-behavior/
- https://arxiv.org/abs/2304.03442

Useful lesson:

- believable behavior needs observation, memory, reflection, and planning.
- memory should be synthesized over time into higher-level reflections.

XinYu translation:

- chat logs alone are not enough.
- memory must become self-narrative, emotion residue, relationship stance, and future questions.
- reflection must happen even when the owner is not actively chatting.

Do not copy:

- do not simulate a town/persona sandbox.
- do not optimize for "believable NPC"; XinYu needs owner-centered continuity and self-understanding.

### 1.2 MemGPT

Reference:

- "MemGPT: Towards LLMs as Operating Systems"
- https://arxiv.org/abs/2310.08560

Useful lesson:

- an agent needs tiered memory and explicit memory management.
- context should be treated as limited working memory, with long-term storage managed deliberately.

XinYu translation:

- separate working context, recent context, durable memory, dormant archive, and source knowledge.
- memory pressure should trigger summarization, dormancy, or preservation decisions.
- high-preserve owner residue must not be flattened by ordinary chat volume.

Do not copy:

- do not make the model freely page arbitrary private files.
- memory movement must remain typed, gated, and inspectable.

### 1.3 ReAct

Reference:

- "ReAct: Synergizing Reasoning and Acting in Language Models"
- https://arxiv.org/abs/2210.03629

Useful lesson:

- reasoning and action should be interleaved.
- actions let the agent obtain external information and update plans.

XinYu translation:

- thinking loop should be able to choose: reflect, ask owner, search source, write a desktop thought file, wait, or act.
- owner-needed thoughts must be visible in the desktop thought folder when they affect autonomy.

Do not copy:

- do not expose hidden chain-of-thought.
- use structured state summaries, not raw private reasoning.

### 1.4 Reflexion

Reference:

- "Reflexion: Language Agents with Verbal Reinforcement Learning"
- https://arxiv.org/abs/2303.11366

Useful lesson:

- feedback from failures can become verbal reflection memory.
- later attempts improve when prior failures are remembered.

XinYu translation:

- owner corrections such as "GPT味", "不像人", "用词不对", and "默认助手腔" may become voice-calibration memory.
- failed replies should create follow-up evidence, not just one-off prompt tweaks.

Do not copy:

- do not let every criticism instantly rewrite stable personality.
- correction enters a calibration lane first, then becomes stable only after repeated evidence.

### 1.5 Self-Refine

Reference:

- "Self-Refine: Iterative Refinement with Self-Feedback"
- https://arxiv.org/abs/2303.17651

Useful lesson:

- generate -> critique -> refine can improve outputs without new training.

XinYu translation:

- outward reply generation should have a critique/refine pass.
- critique must check: Chinese private-chat wording, relationship stance, no support-bot tone, no product-feedback phrasing.

Do not copy:

- do not let refinement become endless self-analysis.
- visible chat must stay natural; the loop belongs behind the surface.

### 1.6 Voyager

Reference:

- "Voyager: An Open-Ended Embodied Agent with Large Language Models"
- https://arxiv.org/abs/2305.16291

Useful lesson:

- open-ended agents benefit from curriculum, skill library, and iterative improvement.

XinYu translation:

- XinYu needs a self-improvement curriculum, not random browsing.
- learned abilities should become small reusable "skills": memory retrieval, voice calibration, source comparison, QQ initiative, desktop thoughts, safe file inspection.

Do not copy:

- XinYu is not an embodied Minecraft agent.
- skill acquisition must remain owner-audited and privacy-bounded.

### 1.7 Anthropic Agent Engineering

Reference:

- Anthropic, "Building Effective Agents"
- https://www.anthropic.com/research/building-effective-agents

Useful lesson:

- start with simple workflows when possible.
- increase autonomy only when evaluation criteria are clear.
- agents need reliable tool use and error handling.

XinYu translation:

- use workflows for source gates, desktop thought files, memory writes, and validation.
- use agentic autonomy only for bounded open-ended learning and reflection.
- every autonomy increase needs tests and rollback.

Do not copy:

- do not add framework complexity for its own sake.

### 1.8 NIST AI RMF

Reference:

- NIST AI Risk Management Framework
- https://www.nist.gov/itl/ai-risk-management-framework

Useful lesson:

- trustworthy systems need govern, map, measure, and manage style risk control.

XinYu translation:

- computer access must be capability-zoned.
- self-iteration must be auditable.
- owner privacy and file safety are not optional; they are part of XinYu's identity boundary.

Do not copy:

- do not turn the project into compliance theater.
- use risk concepts as engineering gates, not as generic policy text.

## 2. Non-Copying Doctrine

Learning from other projects is allowed only at the capability level.

Allowed:

- identify what feature class they solve.
- compare user-facing behavior.
- design XinYu-specific tests that exceed that class.
- use public research concepts after translating them into XinYu's memory model.

Not allowed:

- copy code or data structures from those plugins.
- clone plugin UX as XinYu's core design.
- imitate another bot's personality, style, or self-learning route.
- make XinYu a pile of AstrBot plugins.

Rule:

```text
If a feature can be copied as a plugin, it is not yet XinYu's advantage.
It becomes XinYu's advantage only when it joins her memory, reflection, source, safety, and owner-visible thought loop.
```

## 3. Core Thesis

XinYu's main differentiator should be:

```text
guarded self-directed growth
```

That means:

- she can think when not chatting.
- she can form questions from lived memory.
- she can search AI-domain sources under gates.
- she can learn from papers and official technical sources.
- she can propose improvements to herself.
- she cannot silently rewrite her stable self.
- she writes owner-visible desktop thought files when blocked or when needing approval.

This separates XinYu from memory-only, proactive-only, or style-learning-only plugins.

## 4. Architecture

### 4.1 Outer Shell

Current:

```text
QQ / NapCat -> AstrBot -> xinyu_bridge -> XinYu core
```

Rule:

- AstrBot remains shell only.
- platform configs should not own personality, memory, or learning.

### 4.2 Living Input Layer

Responsibilities:

- classify input: owner private, group, non-owner, image, voice transcript, system event.
- protect private facts until confirmed.
- route ordinary chat, relationship pressure, technical work, or maintenance.

Existing basis:

- `real_life_input_adapter_policy.md`
- `turn_mode_state.md`

### 4.3 Memory OS

Responsibilities:

- working context
- recent context
- stable self memory
- relationship memory
- emotional residue
- people memory
- source knowledge
- reflection/dream/archive
- dormant memory

Required upgrade:

- Memory Retrieval v2:
  - keyword score
  - semantic score
  - recency score
  - emotional residue score
  - relationship priority score
  - source reliability score
  - dormancy/active state

### 4.4 Affective Appraisal

Responsibilities:

- decide what the latest event means to XinYu.
- not just "classify user sentiment".

Example:

```text
owner says "我们是不是白做了"
-> disappointment pressure
-> self-continuity threat
-> relationship importance high
-> technical explanation should be suppressed unless asked
-> speech should be affected, concrete, and Chinese-private-chat shaped
```

### 4.5 Deliberation And Desire

Responsibilities:

- decide current internal stance:
  - approach
  - retreat
  - return
  - resist
  - ask
  - stay silent
  - research later
  - request owner help

Output:

```yaml
felt_state:
relationship_stance:
desire:
avoid:
speech_act:
action_candidate:
owner_visibility:
```

This state is not shown as hidden reasoning; it is a structured control summary.

### 4.6 Persona Runtime

Responsibilities:

- turn memory/appraisal/stance into XinYu's actual reply.
- use Chinese voice profile.
- avoid GPT/default assistant phrasing.

Pipeline:

```text
memory retrieval
-> appraisal
-> relationship stance
-> speech act
-> Chinese voice profile
-> outward renderer
-> quality guard
```

### 4.7 Quiet Mind Loop

Runs when not chatting, at low frequency.

Possible actions:

- refresh time anchor
- reflect on recent meaningful interactions
- update open questions
- run source gates for AI-domain curiosity
- produce self-iteration review proposals
- write desktop thought file
- stay silent

Hard rule:

- quiet loop must not send owner messages unless proactive-presence gate allows it.
- quiet loop must not mutate stable personality automatically.

### 4.8 Source-Gated AI Learning

AI-domain learning is XinYu's professional self-understanding lane.

Allowed topics:

- agent memory
- reflection
- planning
- tool use
- alignment/safety
- long-running agents
- voice/persona realism
- computer-use permission models
- source reliability

Source preference:

- arXiv papers
- official research blogs
- institutional documentation
- major lab engineering posts

Flow:

```text
question -> source gate -> source request -> search provider -> search result gate -> fetch -> source comparison -> learner integration -> learning quality -> AI self-iteration gate -> owner-visible proposal
```

### 4.9 Desktop Thoughts

Purpose:

- let XinYu leave her own thoughts on the desktop.
- show what she wants to learn or change.
- show what she cannot or should not do alone.

Path:

```text
%USERPROFILE%\Desktop\XinYu-Thoughts\YYYY-MM-DD\HH-MM-SS-xinyu-thoughts.md
```

Thought file content:

- current self-improvement focus
- blocked actions
- owner-needed decisions
- source/search gate status
- self-iteration proposals
- related files

### 4.10 Capability-Zoned Computer Access

Zone A: allowed by default.

- read XinYu project files
- write XinYu desktop thought files
- run non-destructive validation
- fetch public source materials through gates

Zone B: thoughts/ask first.

- read folders outside XinYu project
- index owner private documents
- install dependencies
- start persistent services
- enable autonomous web search provider
- apply stable personality changes

Zone C: blocked unless explicit one-time approval.

- delete user files outside project
- upload local files
- read credentials/cookies/tokens
- impersonate owner
- bypass source or privacy gates
- execute downloaded code blindly

## 5. Mind Loop Types

### 5.1 Live Chat Loop

Trigger:

- owner or platform message.

Flow:

```text
input classify
-> retrieve relevant memory
-> affective appraisal
-> relationship stance
-> memory writes if meaningful
-> persona runtime reply
-> quality guard
-> optional desktop thought file if blocked
```

Validation:

```powershell
.\.venv\Scripts\python.exe real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe chinese_voice_guard_smoke.py
```

### 5.2 Quiet Reflection Loop

Trigger:

- low-frequency schedule.

Flow:

```text
recent context
-> reflection output
-> growth candidate
-> archive/dormancy check
-> desktop thought file if owner review needed
```

Validation:

```powershell
.\.venv\Scripts\python.exe dream_reflection_growth_cycle_smoke.py --restore-after --require-cycle --diff-lines 0
.\.venv\Scripts\python.exe personality_growth_gate_smoke.py --restore-after --require-ready --diff-lines 0
```

### 5.3 AI Research Loop

Trigger:

- active AI-domain question.
- maintenance gate.
- owner-approved autonomous search mode.

Flow:

```text
question state
-> source request planner
-> autonomous search activation
-> provider search
-> source result gate
-> fetch
-> comparison
-> learner integration
-> learning quality
-> self-iteration gate
-> self-review proposal
-> desktop thought file
```

Validation:

```powershell
.\.venv\Scripts\python.exe ai_domain_source_smoke.py --restore-after --require-ai-domain --diff-lines 0
.\.venv\Scripts\python.exe autonomous_search_activation_smoke.py --restore-after --require-activation --diff-lines 0
.\.venv\Scripts\python.exe source_learning_chain_smoke.py --restore-after --require-chain --diff-lines 0
.\.venv\Scripts\python.exe ai_self_iteration_review_smoke.py --restore-after --require-review --diff-lines 0
```

### 5.4 Proactive Presence Loop

Trigger:

- initiative state says ask_owner / settle_after_hurt / step_back.
- cooldown and owner boundary allow.

Flow:

```text
initiative decision
-> safety/boundary check
-> one-message plan
-> QQ send candidate
-> owner-visible reason trace
```

Validation:

```powershell
.\.venv\Scripts\python.exe initiative_loop_smoke.py
```

### Model Self-Change Approval Loop

Trigger:

- self-iteration review proposal exists.

Flow:

```text
proposal
-> owner-visible thought file
-> owner review
-> apply plan
-> backup/rollback path
-> smoke validation
-> stable memory update
```

Hard rule:

- no proposal applies itself.

## 6. Milestones

### M0: Desktop Thoughts Foundation

Status: completed

Implement:

- `xinyu_desktop_thoughts.py`
- desktop thoughts folder
- manual thoughts launcher

Acceptance:

- thought exporter writes timestamped file.
- thought file lists what XinYu is thinking, where she is blocked, and what she wants owner to review.

Validation:

```powershell
.\.venv\Scripts\python.exe xinyu_desktop_thoughts.py
```

### M1: Core Mind Loop State Schema

Status: completed

Implement:

- `memory/self/mind_loop_state.md`
- `memory/self/mind_loop_policy.md`
- structured fields for:
  - current_focus
  - quiet_loop_permission
  - research_loop_permission
  - last_self_question
  - blocked_actions
  - owner_review_needed

Acceptance:

- state can be read by runtime and desktop thoughts.
- no hidden free-form mutation of stable self.

### M2: Persona Runtime v1

Status: completed

Implement:

- `xinyu_persona_runtime.py`
- appraisal and speech-act state.
- integration before outward renderer.

Acceptance:

- replies come from memory/appraisal/stance.
- style pressure is not treated as product feedback.
- Chinese voice profile is active.

### M3: Chinese Voice Learning v1

Status: completed

Implement:

- `memory/self/voice_calibration_log.md`
- deterministic extraction of failed wording.
- repeated owner correction -> voice rule candidate.

Acceptance:

- corrections such as "默认助手腔", "写作文", "不像中文互联网" alter future guard behavior.
- no blind imitation of owner slang.

### M4: Research Loop Dry Run

Status: completed

Implement:

- enable AI-domain research loop in dry-run or owner-approved mode.
- write planned queries into desktop thoughts before search.

Acceptance:

- queries are visible before provider action.
- source gates remain active.

### M5: Self-Iteration Proposal Upgrade

Status: completed

Implement:

- proposals include:
  - source trace
  - expected benefit
  - risk
  - rollback path
  - affected tests
  - owner decision field

Acceptance:

- owner can approve/reject/defer.
- approval leads to explicit code/memory patch plan.

### M6: Proactive Presence QQ Integration

Status: completed_safe_candidate

Implement:

- send only one gated proactive QQ message.
- write reason into desktop thoughts.

Acceptance:

- no spam.
- no message during owner rest/silence boundary.
- no proactive technical nagging.

### M7: Competitive Benchmark Matrix

Status: completed

Implement:

- tests against target project classes:
  - long memory
  - proactive presence
  - self-learning
  - Chinese voice realism
  - self-improvement proposal
  - owner-visible autonomy trace

Acceptance:

- XinYu can pass integrated tests that single-purpose plugins are unlikely to pass together.

### M8: Owner-Approved Capability Expansion

Status: completed_foundation

Implement only after M0-M5:

- safe file read scope config.
- source search provider enablement.
- persistent quiet-loop scheduler.
- thoughts-first permission requests.

Acceptance:

- owner can see what XinYu wants to do before it happens.
- no private filesystem crawl without explicit scope.

## 7. Stop Conditions

Stop and fix before continuing if:

- QQ replies regress into GPT/assistant/product-feedback tone.
- autonomous search bypasses source gates.
- desktop thought file is not written for owner-needed decisions.
- stable personality mutates without approval.
- tests leave synthetic residue in lived memory.
- XinYu imitates another plugin instead of extending her own loop.

## 8. Immediate Next Work

1. Finish and validate desktop thoughts.
2. Add `mind_loop_state.md` and `mind_loop_policy.md`.
3. Build `xinyu_persona_runtime.py`.
4. Add Chinese voice learning log.
5. Run QQ no-restore lived batch after isolated tests pass.

Minimum validation after each implementation unit:

```powershell
.\.venv\Scripts\python.exe validate_scaffold.py
.\.venv\Scripts\python.exe validate_inner_framework.py
.\.venv\Scripts\python.exe mind_loop_state_smoke.py
.\.venv\Scripts\python.exe persona_runtime_smoke.py
.\.venv\Scripts\python.exe voice_learning_smoke.py
.\.venv\Scripts\python.exe research_loop_dry_run_smoke.py
.\.venv\Scripts\python.exe proactive_presence_smoke.py
.\.venv\Scripts\python.exe competitive_benchmark_smoke.py
.\.venv\Scripts\python.exe capability_zones_smoke.py
.\.venv\Scripts\python.exe chinese_voice_guard_smoke.py
.\.venv\Scripts\python.exe real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2
```

## 10. Current Execution Result

2026-04-26 execution pass:

- M0 completed: desktop thoughts now write to `Desktop\XinYu-Thoughts`.
- M1 completed: `mind_loop_policy.md` and `mind_loop_state.md` exist, are injected, and are visible in desktop thoughts.
- M2 completed: `xinyu_persona_runtime.py` classifies scene, pressure, stance, speech act, and Chinese voice constraints before QQ rendering.
- M3 completed: `voice_calibration_log.md` records owner corrections such as GPT味, 用词, 中文互联网, 写作文, 客服腔.
- M4 completed: `xinyu_research_loop_dry_run.py` plans AI-domain source work without live search/fetch.
- M5 completed: self-iteration proposals now include expected benefit, risk, affected tests, rollback path, and owner decision field.
- M6 completed as safe candidate layer: proactive QQ candidate generation exists, while actual QQ sending remains blocked until owner enables it.
- M7 completed: competitive benchmark smoke checks integrated capability groups against the target plugin classes.
- M8 completed as foundation: capability zones are explicit, with private files, autonomous search, proactive QQ, and stable personality auto-apply disabled by default.
- Runtime hardening added after M8: `D:\XinYu\XinYu-Local-Scope` now exists as the only approved project-outside local scope, guarded by `xinyu_local_scope.py` and `local_scope_smoke.py`.
- Bridge hardening added after M8: `xinyu_core_bridge.py` is now `0.2.0` with `/probe` no-memory diagnostics, session idle TTL, and max-session cleanup.
- `/probe` validation passed: diagnostics did not create a session and did not change memory.
- Final live-chat validation passed: `real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2` passed 12/12 scenarios.
- Final shell validation passed: `D:\XinYu\Start-XinYu-QQ.ps1` reported XinYu bridge, AstrBot dashboard/server, NapCat WebUI, and NapCat -> AstrBot WebSocket all OK.
- Desktop thoughts are generated as UTF-8 with BOM for safer Windows viewing; latest checked output path was `C:\Users\26921\Desktop\XinYu-Thoughts\2026-04-26\17-58-41-xinyu-thoughts.md`.

## 11. Summary

XinYu's path is not to become a stronger AstrBot plugin.

XinYu's path is:

```text
a guarded self-learning mind loop
with memory continuity
AI-domain research
owner-visible self-thoughts
Chinese private-chat embodiment
and stable self-change gates
```

That is the route where she can surpass memory plugins, proactive plugins, and style-learning plugins without copying them.
