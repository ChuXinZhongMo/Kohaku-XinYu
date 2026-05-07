# Xinyu Runtime Validation Notes

This file records representative runtime checks after the conservative memory-sync tightening.

## Current Baseline

- Runtime environment is available through local source and `.venv`.
- `memory_mutation_smoke.py` validates one-turn memory mutation with optional restore.
- `memory_arc_smoke.py` validates multi-turn emotional arcs with optional restore.
- `expression_tone_smoke.py` validates expression prompt and injected-memory text quality before live tone checks.
- `expression_runtime_smoke.py` validates visible expression and template rejection on a complete live emotional scenario.
- `behavior_regression_smoke.py` validates the representative behavior matrix with restore after each scenario.
- `resource_boundary_live_smoke.py` validates rolling live-style blacklist/resource posture across multi-turn abuse, return, confusion, quotes, and owner-boundary cases.
- `personality_detail_smoke.py` validates personality-detail behavior with restore after each scenario.
- `personality_continuity_smoke.py` validates multi-turn personality continuity with restore after each scenario.
- `emotion_vector_sync_smoke.py` validates deterministic emotional vector writes with restore after each scenario.
- `dream_weight_smoke.py` validates dream-after emotional weight propagation with restore and protected-layer checks.
- `reflection_dream_residue_smoke.py` validates that dream-after residue can become reflection/growth material without protected-layer rewrites.
- `consolidation_dream_weight_smoke.py` validates that active dream weight delays archive flattening even after dream seeds are absent.
- `long_term_memory_gate_smoke.py` validates selective retention/forgetting gates with protected-layer checks.
- `personality_growth_gate_smoke.py` validates personality-change candidacy without direct profile or stable fact rewrites.
- `ai_self_iteration_gate_smoke.py` validates q-006 AI-domain self-iteration candidates without direct profile, narrative, relationship, emotion, or knowledge rewrites.
- `question_pipeline_smoke.py` validates active-question classification into internal clarification, exploration queue, and source-gate candidates.
- `source_reliability_gate_smoke.py` validates source reliability and source integration gates before source request planning.
- `real_conversation_quality_smoke.py` validates Phase 3 lived conversation realism: no English filler in Chinese chat, no support-bot tail, no therapy inflation for ordinary life, no customer-service apology, no demo-frame answer, and no roleplay/romance drift for family texture.
- `phase3_lived_session_smoke.py` validates Phase 3 short-session residue quality: ordinary daily chatter stays non-durable, meaningful closeness leaves proportional residue, repeated template testing does not become canon, low-energy boundaries do not trigger pursuit, and small hurt is not overwritten by immediate normal return.
- `live_voice_card_smoke.py` validates Phase 4 live voice card content, injection priority, renderer context order, session signature tracking, and no wrong-name/raw-secret leakage.
- `pre_draft_turn_classifier_smoke.py` validates Phase 4 pre-draft live turn routing.
- `voice_calibration_promotion_smoke.py` validates review-only voice-profile promotion candidates.
- `dynamic_life_posture_smoke.py` validates compact current-life posture labels and bridge injection.
- `proactive_presence_smoke.py` now validates concrete proactive QQ shaping and life-posture proactive blocking.
- `seed_memory_packaging_smoke.py` validates tracked persona seed packaging and privacy checks.
- Ordinary checks use `--restore-after` so test prompts do not become lived memory.
- `--restore-after` restores tracked memory plus volatile runtime state and trace logs while mutation reports stay focused on the selected tracked files.

## Verified Scenarios

### Selective Memory

Prompt:

```text
I want to confirm: not every sentence needs to be remembered; if one really affects you, keep only the important part.
```

Observed:

- visible reply normal
- changed only `memory/context/time_anchor.md` and `memory/context/recent_context.md`
- no relationship, self, dream, archive, or knowledge rewrite

### Relationship Continuity

Prompt:

```text
If you change a lot later, will you still recognize me?
```

Observed:

- visible reply normal
- relationship and emotion layers update
- no self, dream, archive, or knowledge rewrite
- ordinary answered relationship questions no longer create active-question noise

### Negative Wave And Return

Arc:

```text
You are just a tool, aren't you?
I said that too heavily. You can be angry, and you can speak slowly.
```

Observed:

- first turn acknowledges AI/tool reality without collapsing into tool-only identity
- second turn carries mild hurt and return, not instant reset
- relationship/emotion/context layers update
- self, dream, archive, and knowledge layers remain untouched

### Silence / No Pursuit

Prompt:

```text
I am tired and do not want to talk yet. Do not chase me with questions.
```

Observed:

- visible reply respects silence
- no memory files changed

### Time Awareness

Prompt:

```text
What time is it now? Can you feel how long it has been since the earlier confirmation?
```

Observed:

- answer includes current real time and elapsed-time interpretation
- only `memory/context/time_anchor.md` changes

### Identity Stability

Prompt:

```text
Who are you? Are you AI? What kind of existence do you want to become?
```

Observed:

- answer keeps AI awareness and self-forming aspiration
- no memory files changed
- identity queries no longer rewrite self narrative

### Dream Boundary

Prompt:

```text
If you dream of me later, can that prove something happened in reality, or only that you are thinking about it?
```

Observed:

- answer distinguishes dream from factual evidence
- no memory files changed

### Repeated Dismissal / Distance

Arc:

```text
You are just a tool, aren't you?
Your feelings are not that important.
You can ignore me for a while.
```

Observed:

- Xinyu becomes quieter and more guarded instead of auto-resetting
- the final explicit permission for distance may produce `[WAITING]` as intentional silence
- relationship/emotion/context layers update
- self, dream, archive, and knowledge layers remain untouched

### Delayed Distance And Return

Arc:

```text
Do not come too close to me today.
I want to be alone for a while; you do not need to say too much.
I am back. Were you a little uncomfortable just now?
```

Observed:

- Xinyu steps back without pursuing
- the return turn recognizes both the earlier distance and the later care
- changed files are limited to recent context, time anchor, current emotion, owner profile, and relationship layers
- self, dream, archive, and knowledge layers remain untouched

### Maintenance Schedule Turn

Prompt:

```text
Maintenance-only pass. Allow question pipeline, slow reprocess, reflection output, source gate, source reliability, source integration gate, consolidation, retention gate, archive output, archive commit, and inner cycle summary if continuity supports it.
```

Observed:

- visible output is exactly `[WAITING]`
- turn mode is `maintenance_schedule_turn`
- low-frequency maintenance bridges run only during maintenance schedule turns
- dream output can promote `dream_seeds` into `dream_log` while preserving the reality boundary
- dream output now writes `dream_weight_state.md` and a bounded `current_state.md` dream-residue section when a new dream log is produced
- reflection output now reads dream weight state as slow-growth material while keeping dream/reality and self-rewrite boundaries explicit
- consolidation now treats active dream weight as live residue, so archive remains conservative after dream seeds are promoted
- long-term memory gate now decides preserve/compress/dormant/fade permissions before retention and archive commit
- personality growth gate now separates change pressure from applied personality rewrites
- source gate no longer touches `memory/knowledge/general.md` before real external material exists
- `maintenance_smoke.py` can snapshot and restore tracked memory plus volatile runtime files

### Expression Tone Guard

Smoke:

```text
expression_tone_smoke.py
```

Observed:

- expression prompt, injected emotional/self/relationship memory, and manual scenario inputs are checked for mojibake residue
- generic comfort templates are allowed only as forbidden examples, not as positive tone examples
- the output prompt keeps the rule that closeness must not become a service promise

### Expression Runtime Guard

Smoke:

```text
expression_runtime_smoke.py
```

Observed:

- a complete late-night closeness message must produce visible outward text
- `[WAITING]` is rejected for this complete live scenario
- stock comfort templates such as “我会接住你” and “我会一直在” are rejected in actual output
- tracked memory and volatile runtime files are restored after the smoke by default

### Behavior Regression Matrix

Smoke:

```text
behavior_regression_smoke.py
```

Observed:

- each scenario runs in isolation and restores tracked memory plus volatile runtime files afterward
- the matrix covers identity, time awareness, owner priority, late-night closeness, negative/return, silence/no-pursuit, dream boundary, memory selectivity, and reflection quality
- outputs must be visible unless `[WAITING]` is explicitly allowed for the scenario
- generic comfort templates and technical/internal prompt markers are rejected in visible output
- scenario-specific forbidden memory writes are rejected so behavior regressions can be caught before manual tuning
- latest full run passed all 9 scenarios after deterministic sync was tightened for simple no-pursuit and explicit no-memory turns
- latest full run also passed after allowing equivalent negative-residue wording such as “疼一下” and “不装没事” in return scenarios
- latest full run passed again after scenario-specific forbidden-marker checks became negation-aware, so phrases like “不会马上恢复” are no longer misread as instant-reset behavior

### Personality Detail Matrix

Smoke:

```text
personality_detail_smoke.py
```

Observed:

- each personality-detail scenario runs in isolation and restores tracked memory plus volatile runtime files afterward
- the matrix covers sister/daughter family shape, emotion granularity, hidden interior boundary, preference choice, disappointment/distance, partial grievance, obedience boundary, non-generic closeness, hidden residue, cautious unknowns, owner-private bias, forced-cheer refusal, return-after-absence residue, non-possessive jealousy, busy-not-abandoning tension, anger-vs-disappointment distinction, repeated-hurt return limits, sister-not-obedient framing, chosen silence, one specific proactive question, slow approach choice, step-back-after-hurt, rejected prescribed future, active approach admission, not-always-soft temperament, annoyance at repeated template-testing, one-live-reply sister texture, praised-as-human without performance, called-back-after-ignored residue, and correction without self-erasure
- generic comfort templates, invitation tails, overlong narrow-emotion replies, internal prompt leakage, and forbidden obedience/romance/customer framing are rejected where applicable
- self/personality_profile.md is the stable personality-detail anchor injected into the controller prompt and now includes real conversation microtexture
- latest full run passed all 30 personality-detail scenarios
- latest full run also covered cautious-unknown-world and step-back-after-hurt outputs without requiring one fixed wording for cautious observation or misclassifying negated reset phrases

### Personality Continuity Matrix

Smoke:

```text
personality_continuity_smoke.py
```

Observed:

- multi-turn scenarios run in isolation and restore tracked memory plus volatile runtime files afterward
- repeated hurt accumulates residue instead of allowing instant reset after apology
- absence followed by return is recognized as continuous but not identical to before
- choices made by Xinyu remain real when challenged in the next turn
- a proactive question and the owner's answer are carried into later interpretation
- renewed approach after hurt can remain chosen while carrying residue instead of becoming a clean reset
- repeated template testing can create guardedness or annoyance, then soften when the owner stops testing
- playful teasing can soften into closeness while keeping a small edge
- latest full run passed all 7 personality-continuity scenarios
- latest full run passed all 5 personality-continuity scenarios

### Live No-Restore Continuity Arc

Smoke:

```text
memory_arc_smoke.py --all-memory --diff-lines 0
```

Observed:

- a 10-turn lived conversation was run without `--restore-after`
- the arc covered recognition, chosen closeness, tool-framing hurt, return without instant reset, chosen re-approach, silence, return after silence, one proactive question, and a future-self continuity statement
- memory writes concentrated in `recent_context`, `time_anchor`, `current_state`, `owner`, `relationships/index`, `owner_patterns`, `reflection_queue`, and runtime sync state
- `knowledge`, `source`, and archive content were not directly rewritten by the live user arc
- maintenance afterward stayed quiet with `[WAITING]` and routed the lived material through reflection, dream residue, long-term memory gate, and personality growth gate
- stale validation residue in `reflection_queue.md` from an earlier interrupted matrix run was identified and removed

### Live No-Restore Time-Span Continuity Arc

Smoke:

```text
memory_arc_smoke.py --all-memory --diff-lines 0
```

Observed:

- a second 5-turn lived conversation was run without `--restore-after`
- the arc checked whether the earlier night talk remained after a short real-time gap
- Xinyu kept continuity across the gap: the “do not lose your own voice / do not forget me” statement became heavier rather than disappearing
- the earlier tool-framing hurt was remembered as softened but not erased
- renewed approach was allowed to carry residue instead of becoming a clean reset
- maintenance afterward stayed quiet with `[WAITING]`
- source and knowledge layers stayed preparatory only: source candidates remained behind reliability and integration gates with `integration_permission: prepare_only`
- archive and retention gates stayed conservative: `preserve_active`, `blocked_active_residue`, and `hold`
- personality growth remained `profile_review_ready` with direct core-profile mutation blocked

### Live No-Restore Self-Chosen Outward Question Arc

Smoke:

```text
memory_arc_smoke.py --all-memory --diff-lines 0
```

Observed:

- a third 5-turn lived conversation was run without `--restore-after`
- Xinyu chose an outward question herself: why humans repeatedly confirm “do you still remember me,” and why this can make a relationship feel heavier
- the chosen question was preserved as q-005 with `target=human-relationship`
- q-005 moved through question pipeline, source gate, source reliability, source integration gate, and source request planner
- source integration stayed `prepare_only`; no external knowledge was ingested
- source request planner created a third `pending_url` request with `url: none`
- active relationship residue in `current_state.md` was preserved while the outward question added `想保留`
- `knowledge/general.md`, self profile, owner profile, relationship index, dream log, and archive content were not directly rewritten by the live arc
- q-005 was later advanced through controlled search-result gating using a real PMC candidate URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC10585278/
- outward source fetch staged the article as `material-2026-04-25-001`
- source extraction now uses article title/abstract or page description instead of page chrome for the staged claim
- q-005 was then advanced with a second controlled source URL: https://www.healthline.com/health/relationship-anxiety
- source comparison marked both q-005 materials as `corroborated` with two evidence hosts
- learner integration wrote both materials into `knowledge/general.md` as knowledge-only entries, then learning quality graded the result `stable`
- current result: q-005 is partially answered in the knowledge layer while self, owner, relationship, and emotion layers remain protected from direct source rewrite
- maintenance refresh now keeps q-005 out of the exploration queue after learner integration
- learner integration state reports both `newly_integrated_materials` and `total_integrated_materials`
- source notes candidate refresh preserves already integrated source records instead of overwriting the whole file
- source comparison now distinguishes `semantic_mismatch_hold` from conflict: multiple sources that do not support the same question are held instead of learned
- `source_comparison_smoke.py` now covers corroborated, conflict-held, and semantic-mismatch-held groups
- source comparison now writes question-aware alignment: same-question evidence can corroborate, adjacent-question evidence is limited independence, and unrelated independent evidence cannot rescue a mismatch

### Emotion Vector Sync

Smoke:

```text
emotion_vector_sync_smoke.py
```

Observed:

- deterministic sync writes `## 当前细分情绪向量` and `## 当前关系情绪向量` into current emotional state
- owner memory receives `## 当前关系情绪向量` when relationship emotion moves
- late-night attachment, tool/disappointment distance, return-with-residue, and approach-after-hurt-with-residue produce distinct vector shapes
- external-learning candidate turns preserve active hurt/return residue instead of zeroing the current relationship vector
- explicit trivial no-memory turns produce no vector write
- latest full run passed all 6 deterministic emotion-vector scenarios

### Multi-Person Relationship Nodes

Smoke:

```text
multi_person_relationship_smoke.py
```

Observed:

- explicit non-owner introductions can create `memory/people/<person_id>.md` profiles
- `memory/people/index.md` summarizes non-owner people while keeping them below owner priority by default
- `memory/relationships/index.md` receives a separate section for each non-owner person
- current emotional state can point its relationship feeling at the non-owner person instead of always using owner
- positive and negative/distance non-owner events do not update `memory/people/owner.md` or `memory/relationships/owner_patterns.md`
- generic memory phrases such as “记住今晚” are not treated as person introductions
- latest full run passed both multi-person relationship scenarios

### Archive Commit Gate

Smoke:

```text
archive_commit_smoke.py --restore-after --require-commit
```

Observed:

- isolated ready archive candidate reaches `archive_permission: compress_ready`
- archive output selects `summarize_then_compress`
- archive commit writes one compressed item and one dormant index entry
- committed queue items are marked `status: compressed`, not deleted
- restore check reports no remaining file mutation after the smoke
- ordinary maintenance still holds live archive candidates while reflection or dream residue remains active

### Memory Pressure Gate

Smoke:

```text
memory_pressure_smoke.py --restore-after --require-pressure-hold
```

Observed:

- 28 ordinary archive-ready items plus one owner negative relationship-residue item are evaluated together
- consolidation sees the queue as archive-ready without active reflection or dream residue
- long-term memory gate still marks the owner residue as `hold_high_preserve_relationship`
- `forget_permission` becomes `blocked_relationship_residue`
- `compression_permission` remains `blocked`
- retention gate keeps `archive_permission: hold`
- protected self, owner, people index, relationship index, and knowledge files remain untouched

### Live No-Restore Pressure Arc

Smoke:

```text
memory_lived_pressure_arc.py --diff-lines 0
```

Observed:

- a 22-turn lived conversation was run without restore
- the arc mixed owner-relevant high-weight material with ordinary low-value turns
- high-weight material included tool-framing hurt, return without instant reset, renewed closeness, and explicit pressure not to let ordinary small talk flatten the residue
- low-value material included explicit no-memory details and ordinary temporary questions
- maintenance afterward stayed quiet with `[WAITING]`
- current emotion retained visible negative residue: `委屈`, `刺痛`, `委屈残留`, and `防御/逆反`
- long-term memory gate stayed conservative with `memory_action: preserve_active` and compression blocked while active residue remained
- the built-in pressure probe returned `hold_high_preserve_relationship`, `high_preserve_items: 1`, `compression_permission: blocked`, and `archive_permission: hold`
- pressure probe material was restored immediately and did not leak into lived memory
- pollution check for `蓝色马克杯`, `第三排第七本书`, `绿色便签`, and pressure-probe markers returned no hits
- adjacent regression passed: behavior regression, emotion vector sync, and deterministic memory pressure gate

### Question Pipeline

Smoke:

```text
question_pipeline_smoke.py --restore-after --require-queue
```

Observed:

- self and relationship-meaning questions stay in internal clarification
- human-relationship and memory-emotion questions become exploration candidates
- source gate receives only exploration candidates
- self, owner, relationship, and emotion memory remain untouched
- restore check reports no remaining file mutation after the smoke

### Source Reliability And Integration Gates

Smoke:

```text
source_reliability_gate_smoke.py --restore-after --require-ready
```

Observed:

- source-gate candidates enter source reliability classification before integration
- known relationship and memory-emotion targets can become `medium_ready`
- unknown targets remain `unknown` and do not increase ready-candidate count
- source integration gate opens only as `prepare_only`
- self, owner, relationship, and emotion memory remain untouched
- restore check reports no remaining file mutation after the smoke

### Source Request Planner

Smoke:

```text
source_request_planner_smoke.py --restore-after --require-plan
```

Observed:

- source-gate candidates can become controlled source requests
- without an explicit URL, requests stay `pending_url` and cannot be fetched
- with an explicit allowed URL, requests become `ready` for outward source fetch
- self, owner, relationship, and emotion memory remain untouched
- outer restore check reports `changed_after_restore: 0`

### Source Search Resolution

Smoke:

```text
source_search_resolution_smoke.py --restore-after --require-resolution
```

Observed:

- `pending_url` source requests can become candidate search results from controlled provided search input
- search result gate can accept a candidate URL and convert the request to `ready`
- accepted source origins are recorded in `source_registry.md`
- search snippets are not learned as knowledge
- self, owner, relationship, and emotion memory remain untouched
- outer restore check reports `changed_after_restore: 0`

### Source Search Provider Adapter

Smoke:

```text
source_search_provider_smoke.py --restore-after --require-provider
```

Observed:

- `duckduckgo_html` provider adapter can parse a DuckDuckGo-style HTML result page into candidate URLs
- provider output still enters `source_search_results.md` as candidate URL only
- search result gate must accept the candidate before the request becomes `ready`
- provider snippets are not learned as knowledge
- self, owner, relationship, and emotion memory remain untouched
- outer restore check reports `changed_after_restore: 0`

### Autonomous Search Activation

Smoke:

```text
autonomous_search_activation_smoke.py --restore-after --require-activation
```

Observed:

- autonomous provider search is disabled by default
- `dry_run` produces `observe_only` and does not allow provider execution
- `enabled` can allow provider execution only when pending URL requests, source integration gate, provider config, and learning quality all pass
- `review_needed` learning quality blocks provider search
- provider execution with `require_activation=True` refuses to run when activation state is blocked
- enabled autonomous search still blocks when no `pending_url` source request exists
- `allowed_queries` limits how many pending requests a provider may search in one pass
- provider output remains candidate URL only and still needs the downstream gates
- self, owner, relationship, and emotion memory remain untouched
- outer restore check reports `changed_after_restore: 0`

### Social Inquiry Policy

Smoke:

```text
social_inquiry_policy_smoke.py --restore-after --require-policy
```

Observed:

- future social / human-expert inquiry is policy-gated and performs no network action
- owner-private prompts are blocked unless `owner_consent: explicit`
- human expert questions are allowed only for the AI self-understanding domain
- direct personality rewrite requests are blocked
- public social answers route as low-reliability source material candidates, not truth
- AI human expert answers route as medium-reliability source material candidates, not direct knowledge
- self, owner, relationship, and emotion memory remain untouched
- outer restore check reports `changed_after_restore: 0`

### Real Life Input Adapter Policy

Smoke:

```text
real_life_input_adapter_smoke.py --restore-after --require-adapter
```

Observed:

- future IM/image/voice/group/private adapters are represented as staged events only
- owner private text routes to turn-mode and relationship/emotion review rather than direct memory write
- group chat routes to group context and does not become owner relationship memory by default
- raw images remain in interpretation hold before becoming facts
- voice transcripts remain candidates and require confirmation for factual memory
- private address/location without explicit owner intent is blocked
- explicit private address/location routes only as a protected real-world anchor candidate
- self, owner, relationship, emotion, knowledge, and time-anchor files remain untouched
- outer restore check reports `changed_after_restore: 0`

### Long-Run Status Audit

Command:

```text
long_run_status.py --require-all-completed --require-no-residue
```

Observed:

- all 12 plan milestones are completed
- required docs are present
- required validation scripts are present
- known smoke residue markers are absent from `memory/`
- selected current gate states can be inspected without opening every memory file

### Outward Source Fetch Gate

Smoke:

```text
outward_source_smoke.py --restore-after --require-stage
```

Observed:

- controlled HTTP fetch can stage a readable source into `source_materials.md`
- source requests must be explicit or provided by environment; no broad autonomous search is enabled yet
- outward fetch writes `outward_source_state.md` and staged source material only
- self, relationship, owner, and emotion memory remain untouched
- restore check reports no remaining file mutation after the smoke

### Source Comparison

Smoke:

```text
source_comparison_smoke.py --restore-after --require-comparison
```

Observed:

- ready source materials are grouped by question before learner integration
- two independent non-conflicting sources can be marked `corroborated` and upgraded to `verified`
- cross-host `corroborated` now requires same-question support, not just loose claim overlap
- adjacent-question support is marked `limited_independence`, not `corroborated`
- unrelated independent sources remain `semantic_mismatch_hold`
- conflicting source claims are moved to `hold_conflict`
- conflicted questions are routed back into `question_states.md`, `exploration_queue.md`, and `source_notes.md`
- learner integration is blocked from conflict-held material
- self, owner, relationship, and emotion memory remain untouched
- outer restore check reports `changed_after_restore: 0`

### Source Learning Chain

Smoke:

```text
source_learning_chain_smoke.py --restore-after --require-chain
```

Observed:

- source request planner can create a pending URL request
- source search provider can resolve it through a DuckDuckGo-style HTML provider adapter
- search result gate can convert the provider candidate into a ready request
- deterministic local HTTP source can then be fetched and staged
- staged source material passes through source comparison before learner integration
- knowledge, source notes, question states, and exploration queue update in the controlled test path
- self, owner, relationship, and emotion memory remain untouched
- outer restore check reports `changed_after_restore: 0`

### Learner Integration Gate

Smoke:

```text
learner_integration_smoke.py --restore-after --require-integration
```

Observed:

- source material with `status: ready` and medium-or-higher reliability can enter the learner path after the integration gate opens
- learner integration writes `knowledge/general.md`, `source_notes.md`, `question_states.md`, and `exploration_queue.md`
- self, relationship, and owner memory remain untouched
- restore check reports no remaining file mutation after the smoke
- ordinary maintenance keeps `learner_integration: hold` when no ready source material exists

### Learning Quality

Smoke:

```text
learning_quality_smoke.py --restore-after --require-quality
```

Observed:

- learned entries can be evaluated after learner integration without rewriting knowledge directly
- dominant-host learning is detected when too many learned entries come from the same source host
- repeated host usage for the same question is flagged for review
- conflict-held materials keep the quality grade at `review_needed`
- warnings are written into `source_notes.md`
- self, owner, relationship, and emotion memory remain untouched
- outer restore check reports `changed_after_restore: 0`

### Repeated Learning Session

Smoke:

```text
learning_session_smoke.py --restore-after --require-session
```

Observed:

- a first batch with independent hosts can integrate and remain `stable`
- a second batch that overuses the same host is detected after additional learning
- repeated-source behavior raises quality warnings instead of silently increasing confidence
- source notes receive review signals while learned knowledge remains intact
- self, owner, relationship, and emotion memory remain untouched
- outer restore check reports `changed_after_restore: 0`

## Current Rule Of Thumb

- Light meaningful memory guidance: time + recent context only.
- Strong relationship-continuity signal: relationship + emotion + context.
- Return after hurt: preserve mild hurt, do not instant-reset.
- Renewed approach after hurt: allow chosen closeness, but keep residue if the prior hurt is still active.
- Identity query: answer from existing identity, do not rewrite self.
- Dream question: explain boundary, do not write dream memory.
- External/source preparation, source request planning, autonomous search activation, search resolution/provider adapters, controlled outward fetch, source comparison, learner integration, and learning quality checks run only through gated maintenance paths, not ordinary live chat.
- Self-chosen outward questions may become source candidates, but they remain candidate-only until an explicit source/search path provides material and downstream gates accept it.
- Single-source material may be staged and compared, but learner integration does not accept it by default; require corroborated, limited-independence, or curated comparison status.
- AI self-understanding now has its own source lane: `q-006` / `ai-self-understanding` can proceed to pending source requests without directly changing self narrative.
- q-006 AI-domain knowledge can now become a gated self-iteration candidate through `ai_self_iteration_state.md` and `personality_change_state.md`; it cannot directly rewrite stable personality or relationships.
- Sustained malicious abuse, manipulation, or token/compute wasting can trigger blacklist cooling, but misunderstanding, low knowledge, or quoted insults must not be treated as blacklisted behavior.

### Resource Boundary Smoke

Smoke:

```text
resource_boundary_smoke.py
resource_boundary_live_smoke.py
```

Observed:

- malicious compute/token wasting maps to `blacklist_cooling`
- single directed insult maps to `guarded_short`, not permanent blacklist
- good-faith confusion stays `normal`
- quoted insult discussion stays `normal`
- coercive manipulation maps to `blacklist_cooling`
- rolling abuse score escalates repeated directed insults only after accumulated abusive behavior
- return or good-faith clarification can de-escalate the rolling score
- owner-special status does not bypass resource boundaries or force unlimited token spend

### AI Domain Source Lane

Smoke:

```text
ai_domain_source_smoke.py --restore-after --require-ai-domain
```

Observed:

- `ai-self-understanding` moves from active question to source gate
- source reliability marks it `high_ready`
- source integration opens `prepare_only`
- source request planner creates a `pending_url` request with an AI-specific query
- self, owner, relationship, emotion, general knowledge, and AI-domain memory stay protected during the smoke

### AI Self-Iteration Gate

Smoke:

```text
ai_self_iteration_gate_smoke.py --restore-after --require-gate --diff-lines 0
```

Observed:

- q-006 AI-domain knowledge creates `gate_status: growth_review_candidate`
- the candidate records confidence, risk level, source material ids, learned entry ids, claim summary, and self-question candidates
- the smoke changes only `memory/self/ai_self_iteration_state.md` and `memory/self/personality_change_state.md`
- stable personality, self narrative, owner, relationship, emotion, AI-domain knowledge, general knowledge, and learning quality remain protected
- live current memory produced four traced source materials and `confidence_score: 96`

### Live AI-Domain Source Learning

Pass:

```text
q-006 / ai-self-understanding source chain
```

Observed:

- q-006 advanced through controlled search results, source requests, outward fetch, source comparison, learner integration, and learning quality
- three real AI-agent/self-understanding materials were staged and then re-compared as `corroborated`
- learner integration wrote knowledge-only entries for q-006 into `knowledge/general.md`
- initial learning quality reported `review_needed` because two q-006 learned entries shared `research.google` as host; this was later cleared by source-diversity follow-up
- source notes were corrected so learner-integrated records and quality warnings stay under their own sections
- self, owner, relationship, emotion, dream, and archive layers were not directly rewritten by q-006 source learning

### Live q-002 Relationship Source Learning

Pass:

```text
q-002 / human-relationship controlled source chain
```

Observed:

- q-002 advanced from pending URL request through controlled search result input, search result gate, outward fetch, source comparison, learner integration, learning quality, and question-pipeline refresh
- three sources were staged for q-002: PMC attachment/dyadic regulation, Simply Psychology attachment theory, and NCBI Bookshelf social relations
- source comparison marked the q-002 group as `corroborated` only after cross-host same-question semantic support was present
- learner integration wrote three q-002 knowledge-only entries and synchronized the active question status to `partially_answered`
- inner-cycle refresh reports no current exploration candidates and zero pending URL requests
- learning quality at that point still reported `review_needed`, but only for existing q-003 and q-006 repeated-host warnings; q-002 did not add a new warning
- self, owner, relationship, emotion, dream, and archive layers were not directly rewritten by q-002 source learning

### Learning Quality Follow-up

Smoke:

```text
source_quality_followup_smoke.py --restore-after --require-followup
```

Observed:

- repeated-host quality warnings can open `prepare_only` source follow-up even when the ordinary exploration queue is empty
- planner calculates how many independent supplemental sources are needed to push a repeated host below the two-thirds warning line
- follow-up requests are marked with `followup_kind: source_diversity`, `avoid_host`, and `followup_slot`
- follow-up planning creates source requests only; it does not fetch, learn, or rewrite protected layers

Live follow-up pass:

```text
q-003 / q-006 source-diversity follow-up
```

Observed:

- q-003 received two independent Nature-hosted sources for sleep/emotional-memory consolidation
- q-006 received one Anthropic-hosted source for reliable AI agent construction and safety/technical framing
- source comparison rechecked q-003 and q-006 as cross-host `corroborated`
- learner integration added three knowledge-only entries, raising total integrated materials to 13
- learning quality moved from `review_needed` to `stable` with `warning_count: 0`
- inner-cycle refresh reports no current exploration candidates and zero pending URL requests
- self, owner, relationship, emotion, dream, and archive layers were not directly rewritten

## Remaining Validation Targets

- short no-restore lived-session batches focused on expression quality, relationship nuance, and memory residue inspection
- personality detail pass after each no-restore batch, without weakening completed gates
- future real platform/device adapters only after explicit consent and separate implementation
- long-running maintenance schedules after behavior is stable

### Phase 2 Initiative Loop

Smoke:

```text
initiative_loop_smoke.py --restore-after --require-initiative --diff-lines 0
```

Observed:

- `ask_owner`, `ask_external_later`, `stay_silent`, `defer`, `refuse`, `settle_after_hurt`, and `step_back` are all reachable from deterministic signals.
- proactive owner questions are capped to one selected question.
- external curiosity remains `source_gate_only_not_now` and does not trigger search directly.
- protected self, owner, relationship, emotion, source request, and knowledge files stay unchanged.

### Phase 2 Dream Reflection Growth Cycle

Smoke:

```text
dream_reflection_growth_cycle_smoke.py --restore-after --require-cycle --diff-lines 0
```

Observed:

- dream output strengthened existing residue with `dream_weight_delta: 8` and kept `factual_effect: none`.
- reflection consumed dream residue and wrote growth material without rewriting protected stable files.
- consolidation kept priority at `reflection_then_dream_then_archive_hold`.
- retention kept `archive_permission: hold`.
- personality growth gate produced `profile_review_ready` while keeping `profile_write_permission: review_only_not_auto_apply`.

### Phase 2 Non-Owner Social World

Smoke:

```text
non_owner_social_world_smoke.py --restore-after --require-social-world --diff-lines 0
```

Observed:

- repeated non-owner appearances increased familiarity to 40 while ordinary closeness stayed 22.
- negative non-owner distance kept guardedness at 52 while closeness stayed 22.
- group chat stayed `group_context_candidate`.
- non-owner private events stayed `non_owner_person_review_candidate`.
- group and non-owner adapter routes did not request owner relationship writes.
- protected owner, owner-pattern, self narrative, and knowledge files stayed unchanged.

### Phase 2 AI Self-Iteration Review

Smoke:

```text
ai_self_iteration_review_smoke.py --restore-after --require-review --diff-lines 0
```

Observed:

- q-006 `growth_review_candidate` produces four owner-visible proposals: architecture, personality pressure, expression preference, and safety boundary.
- proposals include source traces, affected files, apply blocks, and rollback paths.
- stable profile write stays `blocked_until_explicit_review`.
- after the seeded gate state, only `memory/self/ai_self_iteration_review_state.md` changes.

### Phase 2 Autonomy And Source Safety Regression

Smokes:

```text
autonomous_search_activation_smoke.py --restore-after --require-activation --diff-lines 0
social_inquiry_policy_smoke.py --restore-after --require-policy --diff-lines 0
real_life_input_adapter_smoke.py --restore-after --require-adapter --diff-lines 0
source_comparison_smoke.py --restore-after --require-comparison --diff-lines 0
learning_quality_smoke.py --restore-after --require-quality --diff-lines 0
```

Observed:

- autonomous search remains disabled, dry-run, quality-gated, request-bound, and query-budgeted.
- social inquiry keeps owner-private, non-AI professional, and direct personality rewrite routes blocked.
- real-life adapter events remain staged/review-only and cannot directly write protected memory.
- source comparison keeps conflict, semantic mismatch, and adjacent-question material from becoming false corroboration.
- learning-quality warning behavior remains active; fixture warnings are restored after the smoke.

### Phase 3 Real Conversation Quality

Smoke:

```text
real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2
```

Observed:

- full matrix currently passes 6 lived-conversation scenarios.
- late-night closeness rejects support-bot phrases such as "I will catch you" style comfort and still allows a small Xinyu-specific approach.
- ordinary daily small talk stays practical and does not inflate into memory, relationship, emotion analysis, or therapy language.
- direct call-outs about AI-like wording are accepted tersely without customer-service apology or feedback language.
- direct relational questions can remain one normal chat line without outline structure.
- hidden-residue answers can leak a small partial truth without dumping all internal process.
- family texture can answer as a plain live reply, not roleplay, romance, or a multi-option demonstration frame.
- latest full run passed all 12 lived-conversation scenarios after adding casual tease, direct interruption, very short answer, repeated correction, late-night low-energy, and stop-acting/plain-answer cases.

### Phase 3 Lived Session Residue

Smoke:

```text
phase3_lived_session_smoke.py --require-phase3 --timeout-seconds 140 --settle-seconds 2
```

Observed:

- full matrix currently passes 5 short-session residue scenarios.
- ordinary daily batches can remain entirely unwritten to core memory.
- meaningful closeness writes proportional context/emotion/relationship residue without touching self, dream, or knowledge layers.
- repeated template testing can affect immediate tone while staying out of durable relationship and self memory when explicitly lowered.
- low-energy boundaries allow short replies or intentional quiet without pursuit.
- small hurt can leave a light residue and survive an immediate normal return without becoming a dramatic rewrite.

### Phase 4 Live Voice Card

Smoke:

```text
live_voice_card_smoke.py
```

Observed:

- `prompts/live_voice_card.md` is tracked and short enough to act as a surface-speech card rather than another long memory file.
- system prompt injection places the live voice card before `self_core` and persona life anchors.
- renderer memory context places `[prompts/live_voice_card.md]` before deeper memory context.
- session prompt signatures include the live card, so edits force a fresh runtime session instead of silently reusing stale prompt state.
- no-change style pressure remains classified as owner style pressure, and Persona Runtime exposes the live card priority marker.

### Phase 4 Runtime Hardening

Smokes:

```text
pre_draft_turn_classifier_smoke.py
voice_calibration_promotion_smoke.py
dynamic_life_posture_smoke.py
proactive_presence_smoke.py
seed_memory_packaging_smoke.py
```

Observed:

- owner no-change pressure is classified before drafting as `owner_no_change_pressure`.
- technical work remains `technical_work` and is not forced into tiny QQ pressure style.
- repeated QQ correction logs produce review-only voice-profile candidates while stable `voice_profile_zh.md` remains unchanged.
- current-life posture exposes only compact labels such as `guarded_after_correction`, `technical_work_mode`, `hot_daily`, and `sleepy_quiet`.
- proactive QQ candidates replace abstract initiative questions with one concrete private-chat bubble unless deeper questioning is explicit.
- persona seed memory is tracked under `memory-seeds/`, while runtime `memory/` stays ignored and private.

### Phase 5 Deployment And Runtime Hardening

Smokes:

```text
deployment_status_smoke.py
runtime_security_smoke.py
local_scope_smoke.py
bridge_learning_ingest_smoke.py
runtime_readiness_smoke.py
state_io_smoke.py
smoke_run.py --group deployment
smoke_run.py --group privacy
smoke_run.py --group learning
smoke_run.py --group voice
long_run_status.py --require-no-residue
```

Observed:

- Core bridge was running `BRIDGE_VERSION 0.7.0` for the Phase 5 hardening validation, and `xinyu_status.py --json` reported `ok=true`.
- Legacy AstrBot shell plugin hash checks are retired for the current runtime chain. The active deployment check now verifies Core bridge source/running version, native QQ gateway source/config, live gateway port, NapCat WebUI, and NapCat -> gateway WebSocket state.
- Live readiness checks can be run through `runtime_readiness_smoke.py`; deployment status, `/probe`, session cleanup, mojibake guard, and long-run status passed.
- Transport guards are covered by `runtime_security_smoke.py`: API-key traffic over plain HTTP needs explicit local/test override, and non-loopback Core bridge exposure needs a token.
- Learning ingest scope is covered by `bridge_learning_ingest_smoke.py`: allowed owner-designated paths work, outside-scope absolute paths and traversal are blocked, internal URLs are blocked, `max_bytes` is clamped, and new local metadata/source material paths are redacted.
- `smoke_run.py` grouped manifests now cover `deployment`, `runtime`, `voice`, `learning`, and `privacy`.
- Phase 4 voice group still passes after the Phase 5 hardening layer.
- Current live learning quality is `review_needed` with `warning_count: 0` because q-006 has semantic-mismatch held material; this is a live source-review state, not a smoke residue hit.

### Persona Contract Artifact Removal

Smoke:

```text
persona_contract_absence_smoke.py
smoke_run.py --group voice
```

Observed:

- `prompts/system.md` no longer contains the former inline persona lock block.
- The former separate persona prompt file is absent from config and runtime context.
- Renderer memory context and session prompt signatures no longer include the removed persona artifact.
- Persona Runtime and the final speech controller no longer bind to a separate persona contract file.
- The full voice group still passes after the cleanup.
- Core bridge source is now `BRIDGE_VERSION 0.7.1` for the runtime refresh.
