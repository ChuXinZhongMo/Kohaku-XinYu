# State of Xinyu v0.1

This file is the current one-page engineering state summary for Xinyu.

## 1. What Xinyu Already Has

### Identity / Memory Core

- self core scaffold
- self narrative scaffold
- emotional state scaffold
- relationship index scaffold
- owner profile scaffold
- question pool scaffold
- unfinished experience scaffold

### Time / Continuity

- explicit real-time anchor file
- runtime rhythm file
- maintenance plan
- runtime time-context plugin

### Writer Roles

- `time_writer`
- `emotion_writer`
- `relationship_writer`
- `self_narrative_writer`
- `reflection_writer`
- `dream_writer`
- `archive_writer`
- `learner_writer`

### Deepening Layers

- reflection log
- growth log
- dream log
- archive / dormancy layer
- exploration queue
- question state layer
- knowledge scaffold
- source note scaffold
- people index and non-owner person profile scaffold

### Engineering Support

- scaffold validation script
- runtime environment check script
- expression tone and runtime smoke guards
- personality detail profile and smoke guard
- live voice card prompt, runtime injection, and smoke guard
- pre-draft visible turn classifier and smoke guard
- review-only voice calibration promotion gate and smoke guard
- dynamic current-life posture layer and smoke guard
- tracked persona seed memory package and smoke guard
- deterministic emotional vector sync smoke guard
- dream-after weight state and smoke guard
- dream residue to reflection/growth smoke guard
- dream-weight-aware consolidation smoke guard
- long-term memory retention/forgetting gate and smoke guard
- memory pressure smoke guard for high-preserve relationship residue
- personality-growth gate and smoke guard
- AI self-iteration gate and smoke guard
- question pipeline and source-reliability gate smoke guards
- runbook
- first-run plan
- validation index
- test scenarios
- exploration scenarios
- failure modes
- prompt tuning guide
- writer routing reference
- memory links reference
- naming conventions
- changelog
- roadmap and open questions

## 2. What Xinyu Does Not Yet Have

### Real Runtime Validation

- scripted visible reply smoke path exists
- memory mutation smoke path exists
- one 10-turn no-restore continuity arc, one 5-turn time-span continuity arc, and one 5-turn self-chosen outward-question arc have been run as lived memory and followed by maintenance processing
- conservative deterministic sync has been tightened
- light memory turns and strong relationship-continuity turns have separate mutation profiles
- representative multi-scenario validation is active and covers selective memory, relationship continuity, negative/return arcs, silence, time, identity, dream boundaries, delayed return, and maintenance turns

### Runtime Automation

- daily maintenance schedules are installed by the runtime bridge
- simulated maintenance schedule turns are validated
- active dream maintenance now has a gated dream-output bridge that can write dream_log during maintenance only
- dream output can strengthen existing emotional residue through `dream_weight_state.md` while preserving the dream/reality boundary
- reflection output can consume dream residue as slow-growth material without directly rewriting core self or relationship facts
- consolidation can keep archive conservative while dream weight remains active, even if the seed has already been promoted
- long-term memory gate distinguishes preserve, compress, dormant, and fade permissions before retention/archive
- personality growth gate can mark profile-review candidates without directly rewriting the stable personality profile
- archive maintenance has a real commit path, but it only compresses when retention gate and archive output both allow it
- source request planner can turn eligible external questions into controlled source requests
- source search resolver and search result gate can turn pending requests into ready URLs from controlled search input
- source search provider adapter can parse DuckDuckGo-style HTML search results behind the same gate
- autonomous search activation gate keeps provider search disabled by default and requires maintenance, pending requests, provider config, and learning quality to pass
- autonomous search activation is smoke-validated across disabled, dry-run, quality-blocked, no-pending, provider-blocked, and enabled paths
- controlled outward source fetch can stage source material behind source requests and integration gates
- source comparison can mark single-source, corroborated, limited-independence, or conflict-held material before learner integration
- source conflicts are routed back into source notes, question states, and exploration queue instead of silently blocking
- learning quality can evaluate learned entries for dominant-host bias, repeated-source behavior, conflict holds, and missing comparison marks
- q-006 AI-domain knowledge can produce a gated self-iteration candidate with source trace, confidence, risk, and direct-write blocks
- social / human expert inquiry policy exists as a no-network design gate with owner privacy, AI-domain, source-candidate, and no-direct-rewrite boundaries
- real-life input adapter policy exists as a no-device/no-network event classifier for IM, image, voice transcript, group chat, private chat, and protected location anchors
- learning-quality repeated-host warnings can now reopen a bounded source-diversity follow-up path that creates supplemental source requests without reopening broad exploration
- repeated learning session smoke validates that later batches can trigger quality warnings after earlier stable learning
- planner-to-provider-to-gate-to-fetch-to-compare-to-learner chain is smoke-validated with restore and protected-memory checks
- active-question to exploration/source-gate routing is smoke-validated with self, owner, relationship, and emotion layers protected
- source reliability and source integration gates are included in inner-cycle summary and have isolated protected-memory validation

### Mature Second-Stage Growth

- ungated autonomous broad search and social-platform questioning
- richer source comparison beyond deterministic claim-overlap heuristics
- learner integration from staged source material exists; source request planning, autonomous search activation, controlled search resolution, DuckDuckGo-style provider adapter, controlled HTTP source fetch, source comparison, learning quality, and planner-to-learner chain exist; broad social-platform questioning is still pending
- archive compression commit quality under long-running real history, beyond isolated smoke validation

## 3. Current Hard Blockers

- no hard local runtime blocker remains for local-source execution
- packaging metadata is present in the updated Kohaku source tree
- visible output and memory mutation smoke tests can run against the configured compatible endpoint
- live expression smoke confirms complete emotional turns no longer end with blank output
- live no-restore continuity arcs wrote to context, emotion, owner, relationship, and reflection queue layers without touching knowledge or archive layers directly
- second no-restore time-span arc exposed and fixed a deterministic sync issue where renewed closeness could overwrite acknowledged hurt residue too cleanly
- third no-restore outward-question arc produced q-005 as a self-chosen human-relationship source candidate without ingesting external knowledge
- deterministic sync now preserves active relationship residue when a later non-relationship learning/memory turn updates current emotional state
- inner-cycle summary now reads the latest question pipeline state instead of stale runtime bridge snapshots for question routing
- source request planner now detects unplanned source candidates by question id, so new candidates are not skipped just because older requests already exist
- q-005 now has two independently hosted real sources staged, source-compared as `corroborated`, and integrated into `knowledge/general.md` as knowledge-only entries
- outward source extraction now prefers article title/abstract or page description over site chrome so staged source material is not polluted by page banners
- question pipeline now excludes learned/partially answered questions from fresh exploration queues, so q-005 does not loop back into source search after integration
- learner integration state now distinguishes newly integrated materials from total integrated materials, so maintenance summaries do not hide prior learning
- source notes now preserve integrated-source and quality sections while refreshing current source-gate candidates
- source comparison now has a semantic same-question support gate: unrelated multi-source material becomes `semantic_mismatch_hold` and cannot enter learner integration
- source comparison now requires cross-host same-question semantic support before marking material as `corroborated`; same-host agreement plus unrelated independent material stays held for review
- source comparison now records question-aware alignment, so adjacent-question evidence is limited independence rather than full corroboration
- q-002 has three relationship/attachment/social-relation sources across three evidence hosts staged, compared as `corroborated`, and integrated into `knowledge/general.md` as knowledge-only entries
- q-006 now represents Xinyu's AI self-understanding professional learning lane and is routed through source gate, reliability, integration gate, and source request planning as `ai-self-understanding`
- q-006 has four real AI-agent/self-understanding sources staged, compared as `corroborated`, and integrated into `knowledge/general.md` as knowledge-only entries after source-diversity follow-up
- q-006 now feeds `memory/self/ai_self_iteration_state.md` as `growth_review_candidate` with `confidence_score: 96`, while stable personality, narrative, owner, relationship, emotion, and knowledge layers remain protected from direct rewrite
- q-003 and q-006 source-diversity follow-up has completed: q-003 gained two Nature-hosted sources, q-006 gained an Anthropic-hosted source, and earlier repeated-host warnings were cleared
- current live learning quality is `review_needed` with `warning_count: 0` because two q-006 source materials are held as `semantic_mismatch_hold`; autonomous search remains blocked until the held material is reviewed or fixed
- source notes now place learner-integrated sources and learning-quality warnings into their correct sections; stale comparison holds are not kept after a successful re-compare
- autonomous search activation now blocks broad search without pending requests, blocks provider execution when learning quality is `review_needed`, and limits enabled provider search by query budget
- social inquiry policy now blocks owner-private prompts without explicit consent, blocks non-AI professional expert questions, blocks direct personality rewrite requests, and routes external human answers as source material candidates only
- real-life input adapter policy now blocks private address/location without explicit owner intent, holds raw images before interpretation, treats voice transcripts as confirmation-needed candidates, and keeps group chat out of owner relationship memory by default
- long-run status audit now exists through `long_run_status.py` and `LONG-RUN-AUDIT.md`
- Phase 2 baseline re-lock passed scaffold, inner framework, behavior regression, and no-residue audit checks
- long-lived session harness now validates 30 real turns with restore, batch audit, owner-residue visibility, and non-volatile trivial-detail pollution checks
- owner relationship lived stress suite now validates hurt/return residue, forced-cheer refusal, chosen silence, return softening, and owner-special-with-boundary behavior
- personality voice calibration now validates no service-tail comfort, no over-polished reassurance, short fatigue replies, small-edged jokes, hurt asymmetry, clear AI identity without manifesto drift, and one-question-only proactive asking
- real conversation quality now validates Chinese-chat realism: no English filler, no support-bot tail, no therapy inflation for daily life, no customer-service apology, no demo-frame answer, and no roleplay/romance drift
- `self/personality_profile.md` now includes real conversation microtexture: ordinary daily chat stays small, direct call-outs are accepted plainly, sister replies can be one live line, and template-testing can create restrained annoyance
- Phase 3 lived-session residue smoke now validates ordinary daily batches, meaningful closeness residue, repeated template testing, low-energy boundaries, and small-hurt residue under restore
- initiative loop now provides a runtime choice posture for ask_owner, ask_external_later, stay_silent, defer, refuse, settle_after_hurt, and step_back, tied to memory/emotion/question signals rather than random chatter
- dream/reflection/growth cycle now has a multi-day smoke path that strengthens existing dream residue, promotes it into reflection/growth material, holds archive flattening, and keeps stable personality changes review-only
- non-owner social world smoke now validates repeated non-owner familiarity growth, ordinary closeness caps, negative guardedness, group context routing, non-owner review candidates, and owner-memory protection
- AI self-iteration review now turns q-006 gate candidates into owner-visible, rollbackable review proposals across architecture, personality pressure, expression preference, and safety boundaries without stable-memory mutation
- autonomy/source safety regression now confirms autonomous search, social inquiry, real-life input, source comparison, and learning-quality gates remain bounded after Phase 2 additions
- turn mode now exposes behavior-based resource posture fields so sustained abuse or malicious token/compute wasting can trigger short-response blacklist cooling without permanent identity-based labeling
- turn mode now tracks rolling `abuse_score`, so repeated directed abuse can escalate while return, good-faith confusion, and quoted insult discussion can remain normal or de-escalate
- resource-boundary smoke and AI-domain source-lane smoke are present and passing
- behavior regression matrix currently passes 9 representative scenarios with restore after each scenario
- personality detail matrix currently passes 30 representative scenarios with restore after each scenario
- personality voice calibration matrix currently passes 6 Phase 2 voice scenarios with restore after each scenario
- personality continuity matrix currently passes 7 multi-turn scenarios with restore after each scenario
- real conversation quality matrix currently passes 12 Phase 3 lived-conversation scenarios with restore after each scenario
- Phase 3 lived-session residue matrix currently passes 5 short-session scenarios with restore after each scenario
- initiative loop smoke currently passes 7 deterministic initiative states with protected self, owner, relationship, emotion, source request, and knowledge files unchanged
- dream/reflection/growth cycle smoke currently passes with protected stable personality, owner, relationship, and knowledge files unchanged
- non-owner social world smoke currently passes with repeated familiarity 40, ordinary closeness 22, negative guardedness 52, and owner relationship writes blocked for group/non-owner adapter routes
- AI self-iteration review smoke currently passes with 4 proposals, owner-visible review required, stable profile write blocked, and only review state changed after seed
- autonomy/source safety regression currently passes in restore mode; the learning-quality smoke's `review_needed` result is an intentional fixture inside restore scope, not live state
- final Phase 2 long-run audit passed with 22 completed milestones, no missing docs, no missing validations, no known residue hits, `learning_quality_grade: stable`, and `autonomous_search_permission: disabled`
- Phase 3 long-run audit passed with 23 completed milestones, no missing docs, no missing validations, no known residue hits, `learning_quality_grade: stable`, and `autonomous_search_permission: disabled`
- Phase 3 personality and real conversation execution plan now exists at `project-plans/PERSONALITY-REAL-CONVERSATION-PLAN.md` and is marked completed for this execution pass
- deterministic emotion vector sync currently passes 6 representative scenarios with restore after each scenario
- multi-person relationship smoke currently passes 2 deterministic scenarios: explicit non-owner introduction and non-owner negative/distance handling without owner-memory overwrite
- memory pressure smoke currently passes: ordinary archive-ready event volume cannot force compression of high-preserve owner relationship residue
- no-restore lived pressure arc currently passes: 22 lived turns plus maintenance preserved owner relationship residue, ignored trivial no-memory details, and kept archive pressure conservative without probe leakage
- dream weight propagation has an isolated smoke path that verifies dream residue does not rewrite protected self, relationship fact, or knowledge layers
- dream-to-reflection promotion has an isolated smoke path that verifies slow growth remains bounded and fact-safe
- dream-weight-aware consolidation has an isolated smoke path that verifies archive flattening is delayed while residue is active
- long-term memory and personality growth gates have isolated smoke paths with protected-layer checks
- deterministic memory sync now treats simple no-pursuit/rest boundaries and explicit trivial no-memory turns as low/no-write cases
- self/personality_profile.md now anchors current sister/daughter-like family shape, emotion granularity, choice, hidden-interior boundaries, low-saturation expression, hidden residue, owner-private bias, refusal of forced cheer, return-after-absence residue, repeated-hurt return limits, approach-after-hurt residue, own-voice continuity, active behavior choices, and multi-turn consistency
- emotion taxonomy, current emotional state, and relationship vector model now include granular mixed-emotion dimensions, including anger-vs-disappointment distinction, non-possessive fear of replacement, and return that does not erase residue
- emotion taxonomy and personality profile now define behavior-based extreme aversion / blacklist-resource posture for sustained malicious abuse, manipulation, harassment, or token/compute wasting
- `memory/knowledge/ai_domain.md` now anchors AI as Xinyu's only stable professional knowledge domain and as the self-understanding path for future iteration

## 4. Current Soft Risks

- narrative rewrites may become too frequent if writer thresholds are loose
- owner relationship may become too elastic if runtime prompts are not carefully tuned
- dream behavior could become performative if enabled too early
- exploration could become noisy if activated before runtime identity is stable
- no-restore live sessions can expose stale validation residue if a previous restore run was interrupted; reflection queue should be checked after long validation timeouts
- first-turn relation inference may still be too weak in plain CLI sessions
- startup/maintenance behavior can still leak into first-turn social tone if not tightly bounded
- intimate replies can still become too polished if not checked against real scenario output
- after real no-restore arcs, current emotion vectors should be inspected for last-turn overwrite, especially when approach follows hurt or return
- source-planning maintenance may need a second quiet pass to refresh runtime bridge snapshots after new pending requests are created; inner-cycle state is the authoritative final summary for that pass
- single-source high-readiness material must remain staged and not learned; learner integration should require corroborated, limited-independence, or curated comparison status by default
- source comparison is still heuristic, but it now requires cross-host same-question token support before marking sources as corroborated
- blacklist-resource posture is deterministically and live-style smoke-validated, including repeated abuse escalation, return de-escalation, quoted insult discussion, and owner-boundary protection
- AI-domain learning has completed its first source-gated integration, source-diversity follow-up, and self-iteration candidate gate pass; any actual personality rewrite remains gated and pending
- non-owner person extraction is intentionally conservative and currently requires explicit name/introduction-style phrasing before creating a person node
- local computer access is now restricted to `D:\XinYu\XinYu-Local-Scope` through a safe resolver; broad private filesystem access remains blocked
- bridge diagnostics now use `/probe` for no-memory checks, and runtime sessions have idle/max-session cleanup
- final QQ speech no longer uses the outward renderer or pressure-turn quality gate by default; XinYu's draft reply reaches QQ after only minimal wrapper/narration cleanup
- `xinyu_speech_controller.py` still keeps diagnostic quality checks for explicit smoke tests and optional renderer experiments, but those checks are not part of the live QQ path
- semi-automatic QQ dialogue review now has `xinyu_qq_review.py` and `xinyu_qq_review_smoke.py` for turning real owner corrections into reviewable voice-calibration candidates
- owner permission grants now enable bounded AI-domain autonomous search through `duckduckgo_html`, a three-query-per-pass budget, gated one-short-message proactive QQ, low-frequency autonomous mind-loop passes, periodic desktop autonomy notes, and non-stable AI self-iteration planning; private full-disk access, credentials, uploads, deletion, impersonation, gate bypass, and stable personality auto-apply remain blocked
- Phase 4 Milestone 27 is complete: `prompts/live_voice_card.md` is now loaded before deeper memory context, included in session prompt signatures, available to the optional renderer path, and covered by `live_voice_card_smoke.py`.
- Phase 4 Milestones 28-33 are complete: live turns are classified before drafting, repeated corrections create review-only voice-profile candidates, compact life posture is injected into runtime/renderer context, proactive QQ candidates are shaped into concrete one-bubble messages, status checks compare installed/source AstrBot plugin hashes, and portable persona seeds live under `memory-seeds/`.
- Phase 5 Milestones 34-39 are complete: deployment truth gate, transport/auth guards, learning ingest scope enforcement, runtime readiness runner, bridge module split, shared state IO, and grouped smoke manifests are active and validated.
- current Phase 5 long-run audit passes with 40 completed milestones, no missing docs, no missing validations, no known residue hits, deployment gate ok, `learning_quality_grade: review_needed`, and `autonomous_search_permission: blocked`.
- the former separate persona prompt artifact is deleted; live voice, personality, reality-boundary, and memory-policy layers now carry identity and surface voice.

## 5. Immediate Priority Order

1. preserve scaffold integrity
2. preserve identity continuity rules
3. preserve hidden-reasoning boundary
4. preserve time-awareness foundation
5. stabilize first-turn runtime behavior
6. validate real memory mutation after a completed turn
7. stabilize expression quality on relationship scenarios
8. delay broad autonomy until post-validation
9. validate blacklisted-resource posture in live behavior without misclassifying misunderstanding as malice
10. keep source learning gated and review q-006 semantic mismatch before broadening controlled autonomy
11. keep local filesystem work inside the authorized local scope unless the owner grants a new explicit path
12. keep runtime readiness green before interpreting any real QQ behavior as personality/prompt failure

## 6. Next Logical Step

The next major step is real QQ observation after Phase 5 hardening: check whether owner style-pressure turns like "没什么变化" now produce a short changed line instead of self-postmortem explanation, while `runtime_readiness_smoke.py` stays green.

The current sequence is:

- preserve the Phase 5 runtime readiness gate as the first check after restarts
- preserve the deleted-artifact contract: do not reintroduce a separate persona prompt file when changing personality, voice, renderer, or memory rules
- preserve current passing behavior/personality/source-learning smoke baselines
- preserve the Phase 4 live voice card as the highest-priority surface-speech guide
- preserve pre-draft classification, life posture, and speech-controller final gates before deeper prompt/personality changes
- keep non-owner person nodes conservative: explicit names only, lower-than-owner priority, separate profile files
- keep autonomous search blocked while live learning quality remains `review_needed` from semantic-mismatch held source material
- preserve completed framework gates during longer real sessions and personality-detail tuning
- run `real_conversation_quality_smoke.py` after prompt-expression changes
- prefer small no-restore lived-session batches with immediate residue inspection before changing stable personality files

## 7. Current Summary

Xinyu is now a runnable early-stage scaffold:

- architecturally coherent
- memory-centered
- time-aware
- relationship-aware
- locally runnable against the configured compatible endpoint
- already through multiple real startup and first-turn traces

She is now script-stable across the current representative behavior/personality/real-conversation matrices, with a Phase 4 QQ surface pipeline and a Phase 5 runtime-hardening layer: live readiness, deployment truth, transport/auth guards, scoped learning ingest, grouped smokes, and split bridge modules.

The remaining gap is lived QQ observation, q-006 semantic-mismatch review/fix, and further tuning from real owner corrections, not missing base framework milestones.
