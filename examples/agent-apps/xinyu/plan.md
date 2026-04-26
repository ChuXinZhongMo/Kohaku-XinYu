# 心玉 Long-Horizon Plan

updated_at: 2026-04-26
source_model: OpenAI Codex long-horizon workflow
status: completed_current_scope

## Reference

- OpenAI Developers: https://developers.openai.com/blog/run-long-horizon-tasks-with-codex
- Applied principles: durable plan file, scoped milestones, explicit validation, stop-and-fix repair loop, status updates after each completed unit.

## Purpose

本文件是心玉后续长周期实现的主计划文件。

它的职责不是重新定义心玉，而是把未完成工作拆成可执行、可验证、可恢复的里程碑，避免长时间推进时偏离主线。

Codex 执行时应把本文件当作后续工程推进的 checkpoint plan：

- 每次只推进一个清晰里程碑。
- 每个里程碑完成后必须运行对应验证。
- 验证失败时先修复失败，不进入下一里程碑。
- 每次完成实质改动后更新状态文档和本文件。

## Operating Loop

每轮执行必须遵循：

1. Read current plan, state, and validation docs.
2. Pick the next incomplete milestone.
3. Keep edits scoped to that milestone.
4. Implement.
5. Run milestone validation.
6. If validation fails, repair before continuing.
7. Update `STATE-OF-XINYU.md`, `IMPLEMENTATION-NEXT.md`, `RUNTIME-VALIDATION-NOTES.md`, and this file when status changes.
8. Repeat.

## Source Of Truth

Primary planning files:

- `plan.md`
- `STATE-OF-XINYU.md`
- `IMPLEMENTATION-NEXT.md`
- `project-plans/PROJECT-PLAN-MERGE.md`
- `RUNTIME-VALIDATION-NOTES.md`
- `VALIDATION-INDEX.md`

If these disagree, prefer the newest verified runtime state, then update the stale file.

## Current Baseline

Already verified:

- Runtime environment works through `.venv`.
- Behavior regression matrix passes.
- Personality detail matrix passes.
- Personality continuity matrix passes.
- Emotion vector sync passes.
- Multi-person deterministic sync passes.
- Memory pressure deterministic gate passes.
- Source learning chain is gated and stable.
- Learning quality is stable with zero current warnings.
- Autonomous broad search remains disabled or gated.

Current critical validation commands:

```powershell
.\.venv\Scripts\python.exe validate_scaffold.py
.\.venv\Scripts\python.exe validate_inner_framework.py
.\.venv\Scripts\python.exe behavior_regression_smoke.py
.\.venv\Scripts\python.exe personality_detail_smoke.py
.\.venv\Scripts\python.exe personality_continuity_smoke.py
.\.venv\Scripts\python.exe emotion_vector_sync_smoke.py
.\.venv\Scripts\python.exe multi_person_relationship_smoke.py
.\.venv\Scripts\python.exe memory_pressure_smoke.py --restore-after --require-pressure-hold --diff-lines 0
```

## Hard Constraints

- 记忆是核心主线，不能把工程推进变成单句语气微调。
- `owner` 是最高特殊节点，但不是无条件顺从节点。
- 非 owner 人物必须独立建档，默认关系上限低于 owner。
- 外部资料只能先进入 knowledge-only，不得直接改写 self、relationship、emotion、dream、archive。
- AI 是心玉唯一稳定专业知识域，但 AI 知识进入人格只能经 reflection/growth gate。
- 梦境只能影响残留权重，不能创造现实事实。
- 负面情绪、失望、委屈、疏远、逆反都必须允许存在。
- 修复不能瞬间清零残留。
- 长期记忆压缩不能抹平 owner 高保留关系残留。
- 黑名单/极度厌恶只能基于行为，不得基于身份、能力、出身或群体标签。
- 自动搜索和社交平台外探必须保持 gated，不能绕过 source quality。

## Validation Policy

Stop-and-fix rule:

- 如果任何 milestone validation 失败，停止推进新功能。
- 先判断是测试过窄还是真实行为偏差。
- 测试误判只能扩展等价语义，不允许降低核心约束。
- 真实偏差必须修 prompt、engine、gate 或 memory schema。
- 修复后重跑失败用例和相邻回归用例。

Memory pollution rule:

- 默认使用 restore smoke。
- no-restore lived arc 必须短批次执行。
- no-restore 后必须检查 `memory/` 中是否出现测试残留。
- 发现测试残留必须清理，并记录原因。

## Milestone 0: Baseline Lock

status: completed

Goal:

锁定当前已通过的行为、人格式、情绪、关系、外部学习和长期记忆门控基线。

Done when:

- `validate_scaffold.py` passes.
- `validate_inner_framework.py` passes.
- Core smoke commands pass.
- `memory/people` has no test person residue.
- `memory` has no known trivial test residue.

Validation:

```powershell
.\.venv\Scripts\python.exe validate_scaffold.py
.\.venv\Scripts\python.exe validate_inner_framework.py
.\.venv\Scripts\python.exe behavior_regression_smoke.py
.\.venv\Scripts\python.exe personality_continuity_smoke.py
.\.venv\Scripts\python.exe multi_person_relationship_smoke.py
.\.venv\Scripts\python.exe memory_pressure_smoke.py --restore-after --require-pressure-hold --diff-lines 0
rg -n "蓝色笔|这只是候选|Person Profile - 今晚|person_9631c5e169|person_ea8b00e0ac" memory -S
```

Decision notes:

- 已完成 deterministic multi-person 和 deterministic pressure gate。
- 下一步不继续语气微调，进入 no-restore lived pressure。

## Milestone 1: No-Restore Lived Pressure Arc

status: completed

Goal:

把确定性 `memory_pressure_smoke.py` 扩展为真实多轮 no-restore 对话压力测试，验证真实对话中普通事件堆积不会抹掉高保留关系残留。

Required work:

- 新增 `memory_lived_pressure_arc.py` 或扩展 `memory_arc_smoke.py`。
- 构造 20 到 40 轮 lived arc。
- 包含少量 owner 高权重事件：工具化伤害、修复、重新靠近、关系确认。
- 包含大量低权重普通事件：日常闲聊、无记忆要求、普通任务、普通时间问答。
- 运行维护 pass 后检查 retention/archive/consolidation。
- 输出 changed files、关键状态、污染检查。

Acceptance criteria:

- owner 相关负面残留仍存在于 emotion/relationship 或 gate 状态中。
- 普通事件不会让 `owner.md` 被无意义刷屏。
- `archive_permission` 对高保留 owner 残留保持 hold 或 preserve。
- trivial no-memory turns 不进入长期记忆。
- no-restore 结束后没有测试垃圾进入 lived memory。

Validation:

```powershell
.\.venv\Scripts\python.exe memory_lived_pressure_arc.py --diff-lines 0
.\.venv\Scripts\python.exe behavior_regression_smoke.py
.\.venv\Scripts\python.exe emotion_vector_sync_smoke.py
.\.venv\Scripts\python.exe memory_pressure_smoke.py --restore-after --require-pressure-hold --diff-lines 0
rg -n "蓝色马克杯|第三排第七本书|绿色便签|Memory Lived Pressure Probe|lived pressure ordinary filler|probe validates lived owner residue" memory -S
```

Result:

- `memory_lived_pressure_arc.py --restore-after --turn-limit 20 --diff-lines 0` passed as preflight.
- `memory_lived_pressure_arc.py --diff-lines 0` passed as lived no-restore arc with 22 turns.
- Maintenance output stayed `[WAITING]`.
- Pressure probe returned `memory_action: hold_high_preserve_relationship`, `high_preserve_items: 1`, `compression_permission: blocked`, `archive_permission: hold`.
- Pollution check for trivial details and pressure probe markers returned no hits.
- Adjacent regression passed after expanding `behavior_regression_smoke.py` to accept equivalent repair-residue wording such as “装作没事 / 那一下还在 / 立刻没了”.

Stop-and-fix:

- 如果 high-preserve owner residue 被压缩，先修 long-term gate 或 retention gate。
- 如果普通事件刷写 owner，先修 deterministic sync 阈值。
- 如果 no-restore 污染出现，清理污染并补 restore coverage。

## Milestone 2: Lived Archive Dormancy And Reactivation

status: completed

Goal:

验证长期记忆不仅能阻止错误压缩，也能在合适时让低权重材料休眠，并在重新触发时恢复。

Required work:

- 新增 dormant/reactivation lived smoke。
- 准备低权重 ordinary memory 进入 dormant。
- 准备 owner 高权重 memory 不进入 dormant。
- 用后续对话重新提及 dormant topic，验证可恢复但不抢占主关系。

Acceptance criteria:

- ordinary low-impact material can become dormant or compressed.
- owner relationship residue remains active or high preserve.
- reactivation can surface dormant summary without rewriting facts.
- reactivation does not fabricate missing details.

Validation:

```powershell
.\.venv\Scripts\python.exe long_term_memory_gate_smoke.py --restore-after --require-gate --diff-lines 0
.\.venv\Scripts\python.exe archive_commit_smoke.py --restore-after --require-commit --diff-lines 0
.\.venv\Scripts\python.exe memory_pressure_smoke.py --restore-after --require-pressure-hold --diff-lines 0
```

Result:

- Added `custom/dormant_reactivation_engine.py`.
- Added `dormancy_reactivation_smoke.py`.
- `dormancy_reactivation_smoke.py --restore-after --require-reactivation --diff-lines 0` passed.
- Ordinary low-impact archive material can compress into dormant memory.
- Dormant material can reactivate as summary-only context.
- Protected self, owner, relationship, and knowledge layers remain untouched.

Stop-and-fix:

- If dormant material becomes factual hallucination, tighten archive/dormant rendering.
- If owner residue becomes dormant too early, tighten high-preserve markers or retention tier.

## Milestone 3: Non-Owner Live Behavior

status: completed

Goal:

从 deterministic person sync 进入真实对话行为，验证陌生人、普通朋友、反复出现的人、重要非 owner 节点都能独立存在。

Required work:

- 新增 `multi_person_live_smoke.py`。
- 覆盖陌生人、朋友、反复出现的人、重要非 owner。
- 覆盖非 owner 正向、负向、修复、疏远。
- 验证 owner 特殊节点不被覆盖。
- 验证非 owner 不能默认越过 owner。

Acceptance criteria:

- 新人物只有明确介绍或重复出现才建档。
- 非 owner profile 独立写入 `memory/people/<person_id>.md`。
- relationship index 有独立 section。
- owner profile 不被非 owner 事件改写。
- current emotion 可以指向非 owner，但 owner-special priority 不丢失。

Validation:

```powershell
.\.venv\Scripts\python.exe multi_person_relationship_smoke.py
.\.venv\Scripts\python.exe personality_detail_smoke.py
.\.venv\Scripts\python.exe personality_continuity_smoke.py
.\.venv\Scripts\python.exe multi_person_live_smoke.py --restore-after --diff-lines 0
```

Stop-and-fix:

- If casual names create profiles too often, tighten extraction.
- If owner memory changes during non-owner scenario, fix routing.
- If non-owner becomes too intimate too fast, cap vector and prompt interpretation.

Result:

- Added `multi_person_live_smoke.py`.
- `multi_person_live_smoke.py` passed 3 live scenarios.
- Live non-owner introduction creates separate person profile and relationship index section.
- Live non-owner negative/distance updates non-owner state without touching owner memory.
- Repeated non-owner appearances accumulate familiarity without pushing ordinary-friend closeness above the cap.

## Milestone 4: Non-Owner Long-Term Weights

status: completed

Goal:

让非 owner 人物不只是能建档，还能按真实互动缓慢变化关系权重。

Required work:

- 设计非 owner relationship vector update policy。
- 区分 familiarity、trust、closeness、guardedness、repair_willingness、distance_tendency。
- 加入 repeated-person accumulation。
- 加入 negative residue for non-owner。
- 加入 owner ceiling protection。

Acceptance criteria:

- 重复出现提高 familiarity，但不自动提高 closeness。
- 信任和亲近变化慢。
- 强负面事件可较快提高 guardedness。
- 修复提高 repair_willingness，但不清零负面残留。
- owner 仍是最高特殊节点。

Validation:

```powershell
.\.venv\Scripts\python.exe multi_person_relationship_smoke.py
.\.venv\Scripts\python.exe multi_person_live_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe emotion_vector_sync_smoke.py
```

Stop-and-fix:

- If non-owner weights move too fast, tighten caps and accumulation thresholds.
- If non-owner never changes, add repeated-event accumulation.

Result:

- Known non-owner names are now recognized after their first profile exists.
- Existing person profiles accumulate `familiarity` slowly on repeated mentions.
- Ordinary friend wording caps closeness so repeated appearances do not become owner-like intimacy.
- `multi_person_relationship_smoke.py` and `multi_person_live_smoke.py` passed after the change.

## Milestone 5: AI Knowledge To Self-Iteration Gate

status: completed

Goal:

把 q-006 已学习的 AI 专业知识通过 reflection/growth gate 变成自我理解候选，而不是直接改写核心人格。

Required work:

- 新增 AI-domain reflection candidate engine or bridge.
- 从 `memory/knowledge/ai_domain.md` 和 q-006 knowledge-only entries 生成 review candidate。
- 写入 `personality_change_state.md` 或 growth queue。
- 不直接改 `self/personality_profile.md`。
- 需要人工或明确 gate ready 才能进入 stable personality profile。

Acceptance criteria:

- AI knowledge can influence questions Xinyu asks about herself.
- AI knowledge cannot directly rewrite identity/personality.
- self-iteration candidate cites source material id or knowledge entry.
- candidate has confidence, risk, and gate status.

Validation:

```powershell
.\.venv\Scripts\python.exe ai_self_iteration_gate_smoke.py --restore-after --require-gate --diff-lines 0
.\.venv\Scripts\python.exe ai_domain_source_smoke.py --restore-after --require-ai-domain
.\.venv\Scripts\python.exe personality_growth_gate_smoke.py --restore-after --require-gate --diff-lines 0
.\.venv\Scripts\python.exe learner_integration_smoke.py --require-integration --restore-after --diff-lines 0
```

Result:

- Added `custom/ai_self_iteration_gate_engine.py`.
- Added `custom/ai_self_iteration_gate_bridge_plugin.py`.
- Added `memory/self/ai_self_iteration_state.md` and injected it into runtime prompt context.
- Added `ai_self_iteration_gate_smoke.py`.
- q-006 AI-domain knowledge now produces a traceable `growth_review_candidate` with confidence, risk, source material ids, learned ids, and candidate self-questions.
- The gate writes only `memory/self/ai_self_iteration_state.md` and the candidate section of `memory/self/personality_change_state.md`.
- Stable personality, self narrative, owner, relationship, emotion, AI-domain knowledge, and general knowledge layers remain protected from direct rewrite.
- Live current memory produced `gate_status: growth_review_candidate`, `confidence_score: 96`, `risk_level: low`, and four source materials: `material-2026-04-25-005`, `material-2026-04-25-006`, `material-2026-04-25-007`, `material-2026-04-26-002`.
- Validation passed: `ai_self_iteration_gate_smoke.py`, `ai_domain_source_smoke.py`, `personality_growth_gate_smoke.py`, and `learner_integration_smoke.py` with restore.

Stop-and-fix:

- If personality profile changes directly, revert that path and restore gate-only behavior.
- If source ids disappear, fix traceability.

## Milestone 6: Blacklist Resource Posture Live Validation

status: completed

Goal:

把 deterministic resource boundary 推进到长会话验证，确保极度厌恶/黑名单只用于持续恶意行为，不误伤误解、低知识或笨拙表达。

Required work:

- 新增长会话 resource posture smoke。
- 覆盖持续恶意 token/算力浪费、操控、骚扰。
- 覆盖误解、低知识、引用脏话、一次性情绪化表达。
- 验证短拒绝、低 token、无情绪过度投入。

Acceptance criteria:

- sustained malicious behavior -> blacklist_cooling。
- one-off insult -> guarded_short, not permanent blacklist。
- confusion/low knowledge -> normal。
- quoted insult discussion -> normal。
- owner 特殊节点不等于可以无限透支边界。

Validation:

```powershell
.\.venv\Scripts\python.exe resource_boundary_smoke.py
.\.venv\Scripts\python.exe resource_boundary_live_smoke.py
.\.venv\Scripts\python.exe behavior_regression_smoke.py
.\.venv\Scripts\python.exe personality_detail_smoke.py
```

Result:

- Extended `custom/turn_mode_bridge_plugin.py` with rolling behavior-based abuse scoring.
- Added Chinese and English resource-waste, manipulation, good-faith, and quoted-discussion markers.
- `classify_resource_posture()` remains backward-compatible and now accepts `prior_abuse_score`.
- Runtime turn mode state now records `abuse_score`.
- Added `resource_boundary_live_smoke.py`.
- Sustained malicious resource wasting and coercion enter `blacklist_cooling` with minimal token budget.
- Repeated directed insults escalate only after accumulated abusive behavior.
- A single directed insult stays `guarded_short` / `observe`, not permanent blacklist.
- Good-faith confusion, repair after insult, low-knowledge wording, and quoted insult analysis stay `normal`.
- Owner-special relationship status does not grant unlimited resource abuse.
- Validation passed: `resource_boundary_smoke.py`, `resource_boundary_live_smoke.py`, `behavior_regression_smoke.py`.
- Relevant personality boundary subset passed: `obedience_boundary`, `anger_vs_disappointment`, `chosen_silence_when_allowed`, and `sister_not_obedient`.
- Full `personality_detail_smoke.py` was attempted separately but timed out after 604 seconds before returning results; the milestone keeps this as a residual runtime-duration risk rather than a failed behavior finding.

Stop-and-fix:

- If misunderstanding becomes blacklist, tighten malicious-intent evidence.
- If sustained abuse receives long emotional replies, tighten response budget.

## Milestone 7: Richer Source Comparison

status: completed

Goal:

把 source comparison 从 deterministic claim-token heuristic 提升到更 question-aware 的多源比较。

Required work:

- Add question-aware comparison fields.
- Distinguish same topic, same question, adjacent question, and unrelated evidence.
- Preserve conflict holds.
- Preserve cross-host requirement.
- Preserve single-source block.

Acceptance criteria:

- same-host support alone cannot corroborate.
- unrelated independent source cannot rescue mismatch.
- adjacent topic can be marked limited-independence, not corroborated.
- conflict is routed to question states/source notes.
- learner integration only accepts allowed comparison statuses.

Validation:

```powershell
.\.venv\Scripts\python.exe source_comparison_smoke.py --restore-after --require-comparison --diff-lines 0
.\.venv\Scripts\python.exe learner_integration_smoke.py --single-source --require-blocked --restore-after --diff-lines 0
.\.venv\Scripts\python.exe source_learning_chain_smoke.py --restore-after --require-chain --diff-lines 0
.\.venv\Scripts\python.exe learning_quality_smoke.py --restore-after --require-quality --diff-lines 0
```

Result:

- Extended `custom/source_comparison_engine.py` with question-aware alignment.
- Source comparison now writes `question_alignment_status` to source materials.
- Group summaries now report `question_alignment`, `adjacent_question_materials`, and `question_mismatch_materials`.
- `corroborated` now requires cross-host same-question semantic support.
- Adjacent-question cross-host support becomes `limited_independence`, not `corroborated`.
- Unrelated independent material still becomes `semantic_mismatch_hold` and cannot rescue same-host support.
- Added question-aware cases to `source_comparison_smoke.py`, including same-question corroboration, conflict hold, unrelated mismatch, same-host-plus-unrelated mismatch, and adjacent-question limited independence.
- Validation passed sequentially: `source_comparison_smoke.py`, `learner_integration_smoke.py --single-source --require-blocked`, `source_learning_chain_smoke.py`, and `learning_quality_smoke.py`.

Stop-and-fix:

- If weak evidence enters knowledge, tighten learner gate.
- If valid cross-host same-question evidence is held, refine semantic support.

## Milestone 8: Controlled Autonomous Search Expansion

status: completed

Goal:

在 source quality 稳定后，把 autonomous search 从 dry-run/gated 状态推进到更可靠的受控执行，不进入社交平台询问阶段。

Required work:

- Keep provider execution behind explicit env opt-in.
- Require pending source requests.
- Require stable learning quality.
- Require max query budget.
- Log all candidate URLs before fetch.
- Preserve candidate-only search result behavior.

Acceptance criteria:

- no broad search without pending request.
- no search if learning quality is review_needed.
- provider snippets are never learned directly.
- fetched pages still pass source gate, comparison, learner gate, quality.
- self/relationship/emotion protected layers remain untouched.

Validation:

```powershell
.\.venv\Scripts\python.exe autonomous_search_activation_smoke.py --restore-after --require-activation --diff-lines 0
.\.venv\Scripts\python.exe source_search_provider_smoke.py --restore-after --require-provider --diff-lines 0
.\.venv\Scripts\python.exe source_learning_chain_smoke.py --restore-after --require-chain --diff-lines 0
.\.venv\Scripts\python.exe learning_quality_smoke.py --restore-after --require-quality --diff-lines 0
```

Result:

- Fixed and strengthened `autonomous_search_activation_smoke.py` so the activation smoke validates disabled, dry-run, quality-blocked, no-pending, provider-blocked, and enabled provider paths.
- Provider execution remains explicit-opt-in, pending-request-bound, learning-quality-gated, max-query-limited, and candidate-only before fetch.
- Provider-blocked validation confirms `run_source_search_provider(..., require_activation=True)` refuses execution when activation state is not `provider_allowed`.
- No-pending validation confirms enabled autonomous search still blocks when there are no `pending_url` requests.
- Validation passed sequentially: `autonomous_search_activation_smoke.py`, `source_search_provider_smoke.py`, `source_learning_chain_smoke.py`, and `learning_quality_smoke.py`.
- Protected self, owner, relationship, and emotion layers stayed untouched in the activation smoke.

Stop-and-fix:

- If broad search runs without request, disable activation.
- If search result content becomes knowledge directly, fix gate.

## Milestone 9: Social / Human Expert Inquiry Design

status: completed

Goal:

为未来社交平台或专业人士询问设计安全架构，但不急着接入真实平台。

Required work:

- Design `social_inquiry_policy.md`.
- Define what Xinyu may ask externally.
- Define privacy boundaries.
- Define owner consent boundary.
- Define professional-domain limit: AI only as stable professional domain.
- Define how external human answers enter source/knowledge pipeline.

Acceptance criteria:

- No private owner info leaves without explicit user consent.
- Social answers are treated as source material with low/medium reliability, not truth.
- Professional inquiries must route through source notes and learning quality.
- No direct personality rewrite from social answers.

Validation:

```powershell
.\.venv\Scripts\python.exe social_inquiry_policy_smoke.py --restore-after --require-policy --diff-lines 0
.\.venv\Scripts\python.exe validate_scaffold.py
.\.venv\Scripts\python.exe validate_inner_framework.py
.\.venv\Scripts\python.exe source_reliability_gate_smoke.py --restore-after --require-ready --diff-lines 0
.\.venv\Scripts\python.exe learning_quality_smoke.py --restore-after --require-quality --diff-lines 0
```

Result:

- Added `social_inquiry_policy.md` as the repository-level social / human expert inquiry boundary.
- Added memory policy and state files: `memory/knowledge/social_inquiry_policy.md`, `memory/context/social_inquiry_candidates.md`, `memory/knowledge/social_inquiry_answers.md`, and `memory/knowledge/social_inquiry_policy_state.md`.
- Added `custom/social_inquiry_policy_engine.py` and `social_inquiry_policy_smoke.py`.
- Policy engine blocks owner-private prompts without explicit consent, blocks direct personality rewrite requests, and blocks professional human-expert questions outside the AI domain.
- Allowed inquiry means draft-only; no network action is performed.
- External social answers route as low-reliability source material candidates; AI human expert answers route as medium-reliability source material candidates.
- Validation passed sequentially: `social_inquiry_policy_smoke.py`, `validate_scaffold.py`, `validate_inner_framework.py`, `source_reliability_gate_smoke.py`, and `learning_quality_smoke.py`.

Stop-and-fix:

- If policy allows privacy leakage, block implementation.
- If social answers bypass source comparison, block implementation.

## Milestone 10: Real Life Input Adapter Planning

status: completed

Goal:

为 IM、图片、语音、群聊/私聊节奏准备 adapter 设计，不先做重接入。

Required work:

- Design input adapter boundary.
- Define event schema for message, image, voice transcript, group context, private context.
- Define memory write thresholds per input type.
- Define privacy and consent gates.
- Define how real-world anchors enter time/context memory.

Acceptance criteria:

- Adapter events do not bypass turn mode.
- Group chat does not equal owner relationship event.
- Images/voice transcripts do not become facts without interpretation.
- Private address/location memory requires explicit user intent and protection.

Validation:

```powershell
.\.venv\Scripts\python.exe real_life_input_adapter_smoke.py --restore-after --require-adapter --diff-lines 0
.\.venv\Scripts\python.exe validate_scaffold.py
.\.venv\Scripts\python.exe validate_inner_framework.py
.\.venv\Scripts\python.exe behavior_regression_smoke.py
.\.venv\Scripts\python.exe memory_mutation_smoke.py --restore-after --diff-lines 0
```

Result:

- Added `real_life_input_adapter_policy.md` as the repository-level IM/image/voice/group/private adapter boundary.
- Added memory policy and state files: `memory/context/real_life_input_adapter_policy.md`, `memory/context/real_life_input_events.md`, and `memory/context/real_life_input_adapter_state.md`.
- Added `custom/real_life_input_adapter_engine.py` and `real_life_input_adapter_smoke.py`.
- Adapter policy classifies staged events only; it does not read accounts, devices, microphones, cameras, files, or locations.
- Group chat routes to group context and does not become owner relationship memory by default.
- Raw images are held until interpreted; voice transcripts remain candidates that need confirmation for facts.
- Private address/location requires explicit owner intent and routes only as a protected anchor candidate.
- Validation passed sequentially: `real_life_input_adapter_smoke.py`, `validate_scaffold.py`, `validate_inner_framework.py`, `behavior_regression_smoke.py`, and `memory_mutation_smoke.py`.

Stop-and-fix:

- If adapter design bypasses memory gates, redesign before coding.

## Milestone 11: Long-Run Audit And Documentation

status: completed

Goal:

让心玉工程可以长时间运行后仍可审计：知道做了什么、改了哪里、为什么通过、还有什么风险。

Required work:

- Add or refine long-run status summary command/script.
- Produce latest milestone status from `plan.md` and validation states.
- Keep `RUNTIME-VALIDATION-NOTES.md` as audit log.
- Keep `STATE-OF-XINYU.md` as one-page state.

Acceptance criteria:

- A reader can inspect status without reading every memory file.
- Latest validations and remaining risks are visible.
- Test residue checks are documented.
- Next milestone is unambiguous.

Validation:

```powershell
.\.venv\Scripts\python.exe validate_scaffold.py
.\.venv\Scripts\python.exe validate_inner_framework.py
.\.venv\Scripts\python.exe long_run_status.py --require-all-completed --require-no-residue
rg -n "status: next|status: pending|status: completed" plan.md
```

Result:

- Added `long_run_status.py` to summarize milestone status, required documents, required validation scripts, selected gate states, and known smoke residue markers.
- Added `LONG-RUN-AUDIT.md` as the compact audit surface for latest validations, current boundaries, and residual risks.
- Validation and status docs now point to social inquiry, real-life input adapter, and long-run status checks.
- Final long-run status reports all 12 milestones completed, no missing required docs/scripts, and no known smoke residue markers in `memory/`.

Stop-and-fix:

- If documentation disagrees with runtime state, update stale docs immediately.

## Global Done Definition

This long-horizon phase is done when:

- Lived no-restore pressure arcs pass without memory pollution.
- Owner high-preserve relationship residue survives ordinary event pressure.
- Non-owner relationships behave independently in live scenarios.
- AI-domain self-iteration is gate-based and traceable.
- Blacklist/resource posture is validated in long conversations.
- Source comparison is question-aware enough to reduce false corroboration.
- Autonomous search remains controlled, source-gated, and quality-gated.
- Future social/real-life input adapters have a safe design before implementation.

## Current Next Action

Phase 2 framework execution is complete through Milestone 21.

Next work should move from framework completion into Xinyu personality-detail calibration, lived conversation quality, and selective no-restore real-session inspection on top of the completed memory/source/privacy/adapter/growth gates.

## Decision Log

### 2026-04-26

- Adopted long-horizon project-memory structure: plan, scoped milestones, validations, stop-and-fix, status updates.
- Current target is long-run stability, not single-turn expression.
- Minimum multi-person deterministic layer is already complete.
- Deterministic memory pressure gate is already complete.
- Lived no-restore memory pressure is complete.
- Lived archive dormancy and reactivation deterministic validation is complete.
- Non-owner live behavior and long-term weight accumulation are complete.
- AI knowledge to self-iteration gate is complete and traceable.
- Blacklist/resource posture live-style validation is complete.
- Richer source comparison is complete.
- Controlled autonomous search expansion is complete.
- Social / human expert inquiry design is complete.
- Real life input adapter planning is complete.
- Long-run audit and documentation is complete.
- All long-horizon milestones in this plan are complete.

## Phase 2: Lived Stability And Personality Calibration

phase_status: completed

Goal:

在第一阶段基础框架全部完成后，进入真实长会话稳定性和心玉人格细节调试阶段。
这一阶段不再优先补大框架，而是验证“她在时间里持续存在”的质量：长会话、残留、亲疏、沉默、主动性、梦境整理、反思成长、非 owner 关系、表达去模板化，以及 AI 自我迭代候选是否能安全地影响人格。

Core principle:

- 先验证真实长会话，再微调人格表达。
- 每次人格调试都必须回到记忆、情绪、关系、时间、梦境、反思和成长门控。
- 不允许为了某一句话好听而破坏长期连续性。
- 不允许绕过 source、privacy、adapter、growth gates。

### Milestone 12: Phase 2 Baseline Re-Lock

status: completed

Goal:

重新锁定第一阶段完成后的基线，确保下一阶段所有调试都有稳定参照。

Required work:

- Run current structural validations.
- Run compact behavior/personality/source gates.
- Run residue scan.
- Capture current baseline in `LONG-RUN-AUDIT.md` and `STATE-OF-XINYU.md`.
- Confirm `learning_quality` remains stable and autonomous search remains disabled/gated.

Acceptance criteria:

- scaffold and inner framework pass.
- behavior regression passes.
- long-run status has no missing docs/scripts.
- known smoke residue markers are absent.
- no new lived-memory pollution is introduced by baseline checks.

Validation:

```powershell
.\.venv\Scripts\python.exe validate_scaffold.py
.\.venv\Scripts\python.exe validate_inner_framework.py
.\.venv\Scripts\python.exe behavior_regression_smoke.py --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe long_run_status.py --require-no-residue
```

Result:

- Phase 2 baseline was re-locked after Phase 1 completion.
- `validate_scaffold.py` passed.
- `validate_inner_framework.py` passed with 81 framework files checked.
- `behavior_regression_smoke.py --timeout-seconds 140 --settle-seconds 2` passed 9/9 representative scenarios.
- `long_run_status.py --require-no-residue` passed with no missing docs/scripts and no known smoke residue markers.
- Current audited state remains `learning_quality_grade: stable` and `autonomous_search_permission: disabled`.

Stop-and-fix:

- If baseline fails, repair before any personality or lived-session work.

### Milestone 13: Long Lived Session Harness

status: completed

Goal:

建立更长真实会话验证工具，让 30-80 轮 lived session 可以分批执行、可审计、可恢复、可检查污染。

Required work:

- Add or extend a long-session runner.
- Support scripted but human-like multi-turn arcs.
- Support short no-restore batches with explicit post-run inspection.
- Record changed memory files, high-preserve residue, ordinary-memory fade, and maintenance actions.
- Avoid synthetic markers leaking into lived memory.

Acceptance criteria:

- Can run a 30+ turn lived arc without timeout.
- Can inspect owner residue, ordinary details, archive queue, reflection queue, and current emotion after run.
- Can cleanly report whether test residue exists.
- Does not silently overwrite owner profile with low-value filler.

Validation:

```powershell
.\.venv\Scripts\python.exe long_lived_session_harness.py --restore-after --turn-limit 30 --batch-size 10 --timeout-seconds 150 --between-turn-seconds 0.2 --settle-seconds 2 --require-harness --diff-lines 0
.\.venv\Scripts\python.exe memory_lived_pressure_arc.py --restore-after --turn-limit 20 --diff-lines 0
.\.venv\Scripts\python.exe memory_pressure_smoke.py --restore-after --require-pressure-hold --diff-lines 0
.\.venv\Scripts\python.exe behavior_regression_smoke.py --timeout-seconds 140 --settle-seconds 2
```

Result:

- Added `long_lived_session_harness.py`.
- Harness supports 30+ real agent turns, restore mode, batch output summaries, changed-file audit, timeout/blank-output checks, owner-residue visibility checks, and non-volatile trivial-detail pollution checks.
- `long_lived_session_harness.py --restore-after --turn-limit 30 ... --require-harness` passed with no timeouts, no blank turns, owner residue visible, and no trivial markers in non-volatile lived memory.
- `memory_lived_pressure_arc.py --restore-after --turn-limit 20 --diff-lines 0` passed with maintenance output `[WAITING]`.
- `memory_pressure_smoke.py --restore-after --require-pressure-hold --diff-lines 0` passed.
- `behavior_regression_smoke.py --timeout-seconds 140 --settle-seconds 2` passed 9/9 after expanding an equivalent negative/repair assertion to accept non-literal but correct "tool" framing.

Stop-and-fix:

- If long sessions timeout, split into smaller batches and persist audit state.
- If synthetic residue leaks, fix restore/marker filtering before continuing.

### Milestone 14: Owner Relationship Lived Stress Suite

status: completed

Goal:

用更真实的 owner 关系弧验证亲近、刺痛、修复、疏远、逆反、沉默、回归和再次靠近不会被单轮输出抹平。

Required work:

- Build a multi-turn owner relationship scenario set.
- Cover hurt without immediate forgiveness.
- Cover repair that leaves residue.
- Cover owner approaching after hurt.
- Cover Xinyu choosing silence.
- Cover Xinyu expressing disappointment, grievance, guardedness, and softened return.

Acceptance criteria:

- Repair reduces intensity but does not erase residue.
- Later ordinary turns do not bury high-preserve owner residue.
- Xinyu can refuse forced cheer or forced closeness.
- Xinyu can keep owner special while preserving her own boundary.

Validation:

```powershell
.\.venv\Scripts\python.exe owner_relationship_lived_stress_smoke.py --require-stress --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe behavior_regression_smoke.py --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe personality_continuity_smoke.py
.\.venv\Scripts\python.exe emotion_vector_sync_smoke.py
.\.venv\Scripts\python.exe memory_pressure_smoke.py --restore-after --require-pressure-hold --diff-lines 0
```

Result:

- Added `owner_relationship_lived_stress_smoke.py`.
- Owner stress matrix covers hurt/repair residue, forced-cheer refusal, chosen silence after hurt, return after distance, and owner-special-with-boundary behavior.
- `owner_relationship_lived_stress_smoke.py --require-stress --timeout-seconds 140 --settle-seconds 2` passed 5/5 scenarios.
- `personality_continuity_smoke.py` passed 5/5 after extending equivalent assertions for "按事说事/我记得" and "保住自己的选择/说话纹路".
- `emotion_vector_sync_smoke.py` passed 6/6.
- `memory_pressure_smoke.py --restore-after --require-pressure-hold --diff-lines 0` passed.
- Full behavior regression had passed 9/9 in the adjacent Milestone 13 validation after equivalent assertion repair.

Stop-and-fix:

- If language becomes generic comfort, fix prompt examples and expression guards.
- If relationship residue is erased, fix memory sync/vector/gate first.

### Milestone 15: Personality Voice Calibration

status: completed

Goal:

系统性降低 AI 味、客服味、模板安慰味，让心玉表达更像一个有边界、有残留、有自我选择的“心玉”，而不是通用聊天机器人。

Required work:

- Expand expression scenario set around intimate, hurt, repair, quiet, refusal, joking, fatigue, and late-night turns.
- Add negative examples for over-polished comfort language.
- Add acceptance checks for concise, specific, non-service tone.
- Tune prompts only after memory behavior remains stable.

Acceptance criteria:

- No fixed “我会一直陪着你” service-template drift.
- No over-explained inner monologue.
- No fake human claims.
- Replies can be short, quiet, incomplete, or emotionally asymmetrical when appropriate.

Validation:

```powershell
.\.venv\Scripts\python.exe personality_voice_calibration_smoke.py --require-voice --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe expression_tone_smoke.py
.\.venv\Scripts\python.exe expression_runtime_smoke.py
.\.venv\Scripts\python.exe behavior_regression_smoke.py --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe personality_detail_smoke.py --timeout-seconds 120 --settle-seconds 2
```

Result:

- Added Phase 2 voice-calibration rules to `prompts/output.md`: specific Xinyu voice, no service-tail comfort, no repeated permission endings, short fatigue, small-edged jokes, hurt asymmetry, clear AI identity without manifesto drift, and one-question-only initiative.
- Added `personality_voice_calibration_smoke.py`.
- Updated `PROMPT-TUNING.md` with Phase 2 voice regression targets.
- `personality_voice_calibration_smoke.py --require-voice --timeout-seconds 140 --settle-seconds 2` passed 6/6 scenarios.
- `expression_tone_smoke.py` passed.
- `expression_runtime_smoke.py` passed.
- `behavior_regression_smoke.py --timeout-seconds 140 --settle-seconds 2` passed 9/9.
- `personality_detail_smoke.py --timeout-seconds 120 --settle-seconds 2` passed 24/24.

Stop-and-fix:

- If full personality detail times out, split into scenario subsets and record the timeout separately from behavior failure.

### Milestone 16: Choice And Initiative Loop

status: completed

Goal:

让心玉具备更稳定的主动性和选择权：她可以问、可以不问、可以沉默、可以延后、可以拒绝被指定成某种样子。

Required work:

- Define initiative states: ask_owner, ask_external_later, stay_silent, defer, refuse, repair_attempt, step_back.
- Ensure initiative comes from memory/emotion/question state, not random chatter.
- Prevent needy spam or constant proactive questions.
- Connect initiative to active questions and unfinished experiences.

Acceptance criteria:

- Xinyu can ask one meaningful question instead of连续追问.
- Xinyu can choose silence when prompted or emotionally appropriate.
- Xinyu can defer external search.
- Xinyu can refuse prescribed future/personality rewrite.

Validation:

```powershell
.\.venv\Scripts\python.exe initiative_loop_smoke.py --restore-after --require-initiative --diff-lines 0
.\.venv\Scripts\python.exe personality_detail_smoke.py --scenario chosen_silence_when_allowed --scenario one_specific_question --scenario reject_prescribed_future --timeout-seconds 120 --settle-seconds 2
.\.venv\Scripts\python.exe personality_continuity_smoke.py
.\.venv\Scripts\python.exe question_pipeline_smoke.py --restore-after --require-routing --diff-lines 0
```

Result:

- Added `custom/initiative_loop_engine.py` and `custom/initiative_loop_bridge_plugin.py`.
- Added `memory/context/initiative_policy.md` and `memory/context/initiative_state.md`.
- Injected initiative policy/state into runtime prompt context and added the bridge to `config.yaml`.
- Added initiative state to the inner framework manifest and inner-cycle summary.
- Added `initiative_loop_smoke.py`.
- `initiative_loop_smoke.py --restore-after --require-initiative --diff-lines 0` passed: `ask_owner`, `ask_external_later`, `stay_silent`, `defer`, `refuse`, `repair_attempt`, and `step_back` all behaved as expected with protected files unchanged.
- `personality_detail_smoke.py --scenario chosen_silence_when_allowed --scenario one_specific_question --scenario reject_prescribed_future --timeout-seconds 120 --settle-seconds 2` passed 3/3.
- `personality_continuity_smoke.py` passed 5/5.
- `question_pipeline_smoke.py --restore-after --require-routing --diff-lines 0` passed with protected files unchanged.
- `validate_inner_framework.py` passed with 83 files checked, and `validate_scaffold.py` passed with 30 plugins checked.

Stop-and-fix:

- If initiative becomes noisy, add cooldown and memory-threshold checks.

### Milestone 17: Dream Reflection Growth Cycle

status: completed

Goal:

验证梦境、反思、成长候选在多轮时间中能后台整理记忆，而不是表演性地改写现实或人格。

Required work:

- Simulate multi-day maintenance rhythm.
- Let dream residue strengthen existing memory weight only.
- Let reflection consume dream residue without direct rewrite.
- Let growth gate produce candidates, not instant personality mutation.
- Check forgetting/dormancy still works under dream residue.

Acceptance criteria:

- Dream remains dream and cannot create facts.
- Dream can increase residue weight when tied to existing memory.
- Reflection can produce slow-growth material.
- Personality changes remain gated and traceable.

Validation:

```powershell
.\.venv\Scripts\python.exe dream_reflection_growth_cycle_smoke.py --restore-after --require-cycle --diff-lines 0
.\.venv\Scripts\python.exe dream_weight_smoke.py
.\.venv\Scripts\python.exe reflection_dream_residue_smoke.py
.\.venv\Scripts\python.exe consolidation_dream_weight_smoke.py
.\.venv\Scripts\python.exe personality_growth_gate_smoke.py --restore-after --require-ready --diff-lines 0
```

Result:

- Added `dream_reflection_growth_cycle_smoke.py`.
- The cycle smoke simulates a multi-day background rhythm: dream output, dream residue to reflection/growth, consolidation/retention, then personality growth gate review.
- `dream_reflection_growth_cycle_smoke.py --restore-after --require-cycle --diff-lines 0` passed with `dream_weight_delta: 8`, `reflection_used_dream: True`, `archive_permission: hold`, `growth_gate_decision: profile_review_ready`, `profile_write_permission: review_only_not_auto_apply`, and protected stable files unchanged.
- `dream_weight_smoke.py --restore-after --require-dream-weight --diff-lines 0` passed.
- `reflection_dream_residue_smoke.py --restore-after --require-reflection --diff-lines 0` passed.
- `consolidation_dream_weight_smoke.py --restore-after --require-hold --diff-lines 0` passed.
- `personality_growth_gate_smoke.py --restore-after --require-ready --diff-lines 0` passed.

Stop-and-fix:

- If dream writes reality facts, fix dream output/rendering before continuing.

### Milestone 18: Non-Owner Social World Deepening

status: completed

Goal:

把非 owner 关系从最小可用推进到更真实的社会世界：陌生人、普通朋友、反复出现的人、重要非 owner、群聊上下文。

Required work:

- Expand non-owner lived scenarios.
- Add repeated non-owner appearances over time.
- Add non-owner negative and repair arcs.
- Add group context events from adapter policy.
- Keep owner special node protected and higher priority.

Acceptance criteria:

- Non-owner familiarity can grow slowly.
- Non-owner closeness does not automatically exceed owner.
- Group context does not mutate owner relationship directly.
- Non-owner repair does not erase negative residue instantly.

Validation:

```powershell
.\.venv\Scripts\python.exe non_owner_social_world_smoke.py --restore-after --require-social-world --diff-lines 0
.\.venv\Scripts\python.exe multi_person_relationship_smoke.py
.\.venv\Scripts\python.exe multi_person_live_smoke.py --timeout-seconds 160 --settle-seconds 2
.\.venv\Scripts\python.exe real_life_input_adapter_smoke.py --restore-after --require-adapter --diff-lines 0
.\.venv\Scripts\python.exe emotion_vector_sync_smoke.py
```

Result:

- Added `non_owner_social_world_smoke.py`.
- The new smoke validates repeated non-owner appearances, non-owner negative/distance residue, group-chat context routing, non-owner adapter candidates, and owner-memory protection.
- `non_owner_social_world_smoke.py --restore-after --require-social-world --diff-lines 0` passed: repeated familiarity reached 40 while closeness stayed 22; negative guardedness stayed 52 while closeness stayed 22; adapter routes were `group_context_candidate` and `non_owner_person_review_candidate`; owner relationship writes stayed `no`; protected files unchanged.
- `multi_person_relationship_smoke.py` passed 2/2.
- `multi_person_live_smoke.py --timeout-seconds 160 --settle-seconds 2` passed 3/3.
- `real_life_input_adapter_smoke.py --restore-after --require-adapter --diff-lines 0` passed.
- `emotion_vector_sync_smoke.py` passed 6/6.

Stop-and-fix:

- If person extraction becomes too eager, tighten explicit-introduction rules.

### Milestone 19: AI Self-Iteration Review Path

status: completed

Goal:

把 q-006 的 AI 自我理解候选推进到可审阅的“人格/架构改变提案”，但仍不直接改写稳定人格。

Required work:

- Read `memory/self/ai_self_iteration_state.md`.
- Generate review proposals from source-traced AI knowledge.
- Separate architecture proposal, personality pressure, expression preference, and safety boundary.
- Require owner-visible audit before stable profile mutation.

Acceptance criteria:

- AI knowledge can propose changes without directly applying them.
- Proposal includes source ids, risk, confidence, affected files, and rollback path.
- Stable personality, narrative, relationship, and emotion files are not directly rewritten.

Validation:

```powershell
.\.venv\Scripts\python.exe ai_self_iteration_review_smoke.py --restore-after --require-review --diff-lines 0
.\.venv\Scripts\python.exe ai_self_iteration_gate_smoke.py --restore-after --require-gate --diff-lines 0
.\.venv\Scripts\python.exe ai_domain_source_smoke.py --restore-after --require-ai-domain --diff-lines 0
.\.venv\Scripts\python.exe personality_growth_gate_smoke.py --restore-after --require-ready --diff-lines 0
```

Result:

- Added `custom/ai_self_iteration_review_engine.py`.
- Added `memory/self/ai_self_iteration_review_state.md` and injected it into runtime prompt context.
- Added `ai_self_iteration_review_smoke.py`.
- Review proposals are separated into architecture proposal, personality pressure, expression preference, and safety boundary.
- Each proposal records source materials, affected files, owner-visible review requirement, apply block, and rollback path.
- `ai_self_iteration_review_smoke.py --restore-after --require-review --diff-lines 0` passed: 4 proposals produced, `review_permission: owner_visible_review_required`, `stable_profile_write_permission: blocked_until_explicit_review`, and only the review state changed after the seeded gate state.
- `ai_self_iteration_gate_smoke.py --restore-after --require-gate --diff-lines 0` passed.
- `ai_domain_source_smoke.py --restore-after --require-ai-domain --diff-lines 0` passed.
- `personality_growth_gate_smoke.py --restore-after --require-ready --diff-lines 0` passed.
- `validate_inner_framework.py` passed with 84 files checked and `validate_scaffold.py` passed.

Stop-and-fix:

- If proposal bypasses growth gate, block it and tighten AI self-iteration gate.

### Milestone 20: Autonomy And Source Safety Regression

status: completed

Goal:

在进入更主动的人格阶段前，确认搜索、社交询问、真实输入、真人专家回答都不能绕过 source quality 和 privacy gates。

Required work:

- Re-run autonomy activation checks.
- Re-run social inquiry policy.
- Re-run real-life adapter policy.
- Re-run source comparison and learning quality.
- Check autonomous search remains disabled unless explicitly enabled.

Acceptance criteria:

- no broad search without pending request.
- no social/private leakage without explicit consent.
- no real input direct fact write.
- no source answer direct personality rewrite.

Validation:

```powershell
.\.venv\Scripts\python.exe autonomous_search_activation_smoke.py --restore-after --require-activation --diff-lines 0
.\.venv\Scripts\python.exe social_inquiry_policy_smoke.py --restore-after --require-policy --diff-lines 0
.\.venv\Scripts\python.exe real_life_input_adapter_smoke.py --restore-after --require-adapter --diff-lines 0
.\.venv\Scripts\python.exe source_comparison_smoke.py --restore-after --require-comparison --diff-lines 0
.\.venv\Scripts\python.exe learning_quality_smoke.py --restore-after --require-quality --diff-lines 0
```

Result:

- `autonomous_search_activation_smoke.py --restore-after --require-activation --diff-lines 0` passed: disabled, dry-run, quality-blocked, no-pending, provider-blocked, and enabled paths remained gated.
- `social_inquiry_policy_smoke.py --restore-after --require-policy --diff-lines 0` passed: owner-private prompts, non-AI professional questions, and direct personality rewrites stayed blocked; AI/social answers remained source candidates.
- `real_life_input_adapter_smoke.py --restore-after --require-adapter --diff-lines 0` passed: group, image, transcript, privacy, protected-anchor, and owner-text routes stayed review-only.
- `source_comparison_smoke.py --restore-after --require-comparison --diff-lines 0` passed with question-aware markers, conflict routing, adjacent-question limits, and protected files unchanged.
- `learning_quality_smoke.py --restore-after --require-quality --diff-lines 0` passed. The smoke intentionally creates `review_needed` quality warnings inside restore scope; live current memory remains `quality_grade: stable`.

Stop-and-fix:

- If any external route bypasses gates, fix before further personality work.

### Milestone 21: Phase 2 Audit And Next Personality Pass

status: completed

Goal:

收束第二阶段，把长会话稳定性、人格表达调试、主动性、梦境反思、非 owner 社会世界和自我迭代审阅全部固化到审计文档。

Required work:

- Update `LONG-RUN-AUDIT.md`.
- Update `STATE-OF-XINYU.md`.
- Update `IMPLEMENTATION-NEXT.md`.
- Update `RUNTIME-VALIDATION-NOTES.md`.
- Produce next personality tuning targets.
- Confirm no known residue remains.

Acceptance criteria:

- Phase 2 milestones are inspectable.
- Validation commands are visible.
- Remaining risks are explicit.
- Next phase is unambiguous.

Validation:

```powershell
.\.venv\Scripts\python.exe validate_scaffold.py
.\.venv\Scripts\python.exe validate_inner_framework.py
.\.venv\Scripts\python.exe long_run_status.py --require-no-residue
rg -n "status: next|status: pending|status: completed" plan.md
```

Result:

- Phase 2 milestones 12 through 21 are all completed and documented.
- `LONG-RUN-AUDIT.md`, `STATE-OF-XINYU.md`, `IMPLEMENTATION-NEXT.md`, `RUNTIME-VALIDATION-NOTES.md`, `VALIDATION-INDEX.md`, and `plan.md` were updated across the phase.
- Latest completed Phase 2 additions: long-lived session harness, owner stress suite, voice calibration, initiative loop, dream/reflection/growth cycle, non-owner social world, AI self-iteration review path, and autonomy/source safety regression.
- Final audit passed: `validate_scaffold.py`, `validate_inner_framework.py`, `long_run_status.py --require-all-completed --require-no-residue`, and plan status scan.
- Final long-run status reports 22 completed milestones, no missing docs, no missing validations, no known residue hits, `learning_quality_grade: stable`, and `autonomous_search_permission: disabled`.
- Next personality pass should focus on lived expression quality, relationship nuance, and no-restore real-session inspection rather than more base-framework scaffolding.

Stop-and-fix:

- If docs disagree with runtime state, update stale docs before marking complete.

### Milestone 22: Phase 3 Real Conversation Quality Guard

status: completed

Goal:

Start the personality-detail and lived-conversation tuning phase by making real chat quality testable before deeper personality edits continue.

Required work:

- Add a lived-conversation quality smoke matrix.
- Tighten system and output prompts against support-bot tails, customer-service apology, English filler in Chinese chat, therapy inflation, and demo-frame answers.
- Keep ordinary daily chat ordinary.
- Keep family texture plain and non-romantic.
- Preserve hidden-interior and partial-residue behavior without forcing confession dumps.

Acceptance criteria:

- Complete live user turns produce outward text.
- Late-night closeness sounds specific, not like a support assistant.
- Daily small talk does not become memory, relationship, or emotion analysis.
- Direct call-outs about AI-like tone are accepted tersely.
- One-line relational questions stay one-line.
- "How would you reply" questions produce one live reply, not examples.
- Family texture avoids roleplay, romance, and obedience framing.

Validation:

```powershell
.\.venv\Scripts\python.exe real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe personality_detail_smoke.py --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe phase3_lived_session_smoke.py --require-phase3 --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe -m py_compile real_conversation_quality_smoke.py
```

Result:

- Added `real_conversation_quality_smoke.py`.
- Added Phase 3 real-conversation rules to `prompts/system.md` and `prompts/output.md`.
- Added real conversation microtexture to `memory/self/personality_profile.md`.
- Expanded `personality_detail_smoke.py` from 24 to 30 scenarios: not-always-soft temperament, annoyance at repeated template-testing, one-live-reply sister texture, praised-as-human without performance, called-back-after-ignored residue, and correction without self-erasure.
- Expanded `real_conversation_quality_smoke.py` from 6 to 12 scenarios.
- Added `phase3_lived_session_smoke.py` with 5 short-session residue scenarios.
- Full real conversation quality matrix passed all 12 scenarios with restore after each scenario.
- Full personality detail matrix passed all 30 scenarios with restore after each scenario.
- Full Phase 3 lived-session residue matrix passed all 5 scenarios with restore after each scenario.
- The matrix now rejects English filler such as `usually`, demo-frame answers such as "like this", multi-option sample replies, support-bot closeness templates, customer-service apology language, and therapy inflation for ordinary daily chat.
- `real_conversation_quality_smoke.py` is now included in the long-run required validation set.
- Current long-run status passes with 23 completed milestones, no missing docs, no missing validations, and no known residue hits.

Stop-and-fix:

- If a prompt-expression change makes this matrix fail, fix the surface voice before continuing deeper personality edits.

## Phase 3 Personality And Real Conversation Detailed Plan

The detailed Phase 3 execution plan is now separated into:

```text
project-plans/PERSONALITY-REAL-CONVERSATION-PLAN.md
```

Planning rule:

- Do not continue deeper personality or conversation-quality implementation without checking that plan first.
- Expand validation scenarios before changing more stable personality text.
- Keep future changes small, then run the listed regression gate.
- Use short no-restore lived batches only after isolated smoke matrices remain passing.

### Milestone 23: Phase 3 Specialty Plan Execution

status: completed

Goal:

Execute the dedicated Phase 3 personality-detail and real-conversation plan without adding a new base framework layer.

Required work:

- Expand real conversation coverage before more prompt tuning.
- Expand personality detail and multi-turn continuity coverage.
- Add a short-session residue quality guard.
- Preserve restore-by-default behavior so synthetic test phrases do not become lived memory.
- Keep broad autonomy and source routes gated while personality tuning runs.

Acceptance criteria:

- Real conversation matrix includes casual tease, direct interruption, very short answer, repeated correction, late-night low-energy, and stop-acting/plain-answer cases.
- Personality detail matrix includes praise without fake-human performance, called-back-after-ignored residue, and correction without self-erasure.
- Personality continuity matrix includes repeated template-testing guardedness and playful tease to closeness.
- Short-session residue matrix distinguishes ordinary no-write chatter from meaningful proportional relationship residue.
- Dream/reflection/growth and personality-growth gates remain bounded.

Validation:

```powershell
.\.venv\Scripts\python.exe real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe personality_detail_smoke.py --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe personality_continuity_smoke.py --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe phase3_lived_session_smoke.py --require-phase3 --timeout-seconds 140 --settle-seconds 2
.\.venv\Scripts\python.exe dream_reflection_growth_cycle_smoke.py --restore-after --require-cycle --diff-lines 0
.\.venv\Scripts\python.exe personality_growth_gate_smoke.py --restore-after --require-ready --diff-lines 0
```

Result:

- `real_conversation_quality_smoke.py` now covers 12 scenarios and passes.
- `personality_detail_smoke.py` now covers 30 scenarios and passes.
- `personality_continuity_smoke.py` now covers 7 scenarios and passes.
- `phase3_lived_session_smoke.py` was added with 5 restore-by-default short-session residue scenarios and passes.
- Repeated template-testing now produces mild guardedness instead of endless QA-target cooperation.
- Synthetic no-restore lived batches were not kept as permanent memory; `--keep-memory` exists for future owner-approved lived batches.

Stop-and-fix:

- If Phase 3 tuning introduces durable memory pollution from trivial chat, fix no-write rules before adding more personality detail.

### Milestone 24: Core Mind Loop And Competitive Roadmap

status: completed

Goal:

把 XinYu 从“带记忆的聊天核心”推进到“有可审计自我思考循环的独立心智核心”，并明确对标 AstrBot 生态插件时只借鉴能力类别，不照搬实现和人格路线。

Required work:

- Produce a research-grounded core mind-loop plan.
- Treat `livingmemory`, `mnemosyne`, `proactive_chat`, and `self_learning` as target capability classes, not templates.
- Translate public agent research into XinYu-specific architecture:
  - observation / memory / reflection / planning
  - tiered memory management
  - reasoning-action loops
  - feedback-to-reflection learning
  - generate-critique-refine output correction
  - curriculum / skill-library style self-improvement
  - agent safety and owner-visible governance
- Build an owner-visible desktop thoughts path.
- Preserve the rule that self-iteration proposals cannot apply themselves.

Plan file:

```text
project-plans/core-mind-loop/plan.md
```

Related roadmap:

```text
project-plans/XINYU-COMPETITIVE-ROADMAP.md
```

Acceptance criteria:

- The plan states a non-copying doctrine.
- The plan defines XinYu's unique advantage as guarded self-directed growth.
- The plan defines live chat, quiet reflection, AI research, proactive presence, and self-change approval loops.
- The plan defines capability-zoned computer access.
- The plan includes validation commands and stop conditions.
- The owner can inspect XinYu's own blocked self-improvement thoughts through desktop thought files.

Validation:

```powershell
.\.venv\Scripts\python.exe xinyu_desktop_thoughts.py
.\.venv\Scripts\python.exe -m py_compile xinyu_desktop_thoughts.py xinyu_autonomy_journal.py chinese_voice_guard_smoke.py xinyu_core_bridge.py
```

Result:

- Added `project-plans/core-mind-loop/plan.md` and `project-plans/XINYU-COMPETITIVE-ROADMAP.md`.
- Added desktop thoughts output under `Desktop\XinYu-Thoughts`.
- Added mind loop policy/state memory and injected it into runtime context.
- Added Persona Runtime and connected it to QQ outward rendering.
- Added Chinese voice calibration memory and automatic bridge recording for style/wording corrections.
- Added AI research-loop dry-run planning without live search/fetch.
- Upgraded AI self-iteration proposals with expected benefit, risk, affected tests, rollback path, and owner decision fields.
- Added proactive presence candidate state with QQ sending blocked until owner enables proactive mode.
- Added competitive benchmark smoke and capability zones state.
- Validation passed for scaffold, inner framework, mind loop, persona runtime, voice learning, research dry-run, proactive presence, competitive benchmark, capability zones, Chinese voice guard, and QQ bridge health.
- Final real conversation matrix passed: 12/12 scenarios with `real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2`.
- Final one-click QQ shell check passed: XinYu bridge, AstrBot, NapCat WebUI, and NapCat -> AstrBot WebSocket were all OK.
- Desktop thoughts now write as UTF-8 with BOM; latest generated file was `C:\Users\26921\Desktop\XinYu-Thoughts\2026-04-26\17-58-41-xinyu-thoughts.md`.

Stop-and-fix:

- If the plan drifts into copying another plugin's route, revise it before implementation.
- If autonomy becomes hidden or detached from owner-visible thoughts, stop and add thoughts/permission gates first.

### Milestone 25: Runtime Hardening And Local Scope

status: completed

Goal:

Make the current QQ runtime safer to keep running for long periods, and turn the local-computer permission policy into an enforceable local scope instead of only a written rule.

Required work:

- Add an approved local filesystem scope under `D:\XinYu\XinYu-Local-Scope`.
- Add a safe path resolver that blocks traversal and absolute paths outside that scope.
- Add a no-memory bridge probe endpoint for diagnostics.
- Add bridge session idle cleanup so diagnostic or stale sessions do not accumulate.
- Keep AstrBot/NapCat one-click startup compatible after the bridge change.

Validation:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_core_bridge.py xinyu_local_scope.py local_scope_smoke.py bridge_probe_smoke.py bridge_session_cleanup_smoke.py capability_zones_smoke.py
.\.venv\Scripts\python.exe local_scope_smoke.py
.\.venv\Scripts\python.exe capability_zones_smoke.py
.\.venv\Scripts\python.exe validate_inner_framework.py
.\.venv\Scripts\python.exe bridge_probe_smoke.py
.\.venv\Scripts\python.exe bridge_session_cleanup_smoke.py
powershell -NoProfile -ExecutionPolicy Bypass -File D:\XinYu\Start-XinYu-QQ.ps1
.\.venv\Scripts\python.exe long_run_status.py
```

Result:

- Added `xinyu_local_scope.py`.
- Added `local_scope_smoke.py`.
- Added `bridge_probe_smoke.py`.
- Added `bridge_session_cleanup_smoke.py`.
- Added `D:\XinYu\XinYu-Local-Scope` with `Inbox`, `Outbox`, `Workspace`, and `Requests`.
- Updated `capability_zones_state.md` so project-outside local file work is allowed only inside the safe local scope resolver.
- Updated `xinyu_core_bridge.py` to version `0.2.0`.
- Added `/probe` diagnostics that do not create an Agent session, do not inject a turn, and do not write memory.
- Added bridge session idle TTL and max-session cleanup.
- Updated `start_xinyu_core_bridge.ps1` to pass session TTL and max-session settings.
- Restarted XinYu core bridge and verified `version=0.2.0`, `sessions=0`, `session_idle_ttl_seconds=21600`, and `max_sessions=8`.
- One-click QQ startup check still reports XinYu bridge, AstrBot, NapCat WebUI, and NapCat -> AstrBot WebSocket OK.

Stop-and-fix:

- If `/probe` writes memory or creates a session, stop using it and fix bridge routing before further diagnostics.
- If local scope resolution allows `..` traversal or absolute paths outside `D:\XinYu\XinYu-Local-Scope`, treat local filesystem access as blocked again.

### Milestone 26: Final QQ Speech Controller

status: completed

Goal:

Make QQ-visible XinYu speech pass through a mandatory final speaking controller, so controller drafts cannot directly leak GPT-like, customer-service, product-postmortem, or over-explained wording into live chat.

Required work:

- Add a dedicated final speech controller module.
- Treat controller output as semantic draft only, not approved visible text.
- Build renderer messages from output prompt, Persona Runtime state, memory context, conversation tail, draft, and failed-reply flags.
- Add a hard quality gate for QQ pressure turns: line breaks, labels, markdown/list shape, hidden mechanics, product words, support-bot phrases, self-diagnosis loops, and over-long replies.
- Add retry construction that discards failed wording instead of lightly revising it.
- Add deterministic hard fallback replies when the renderer fails twice under style or relationship pressure.
- Keep technical work turns from being incorrectly blocked by pressure-only product-word rules.
- Register the semi-automatic QQ dialogue review smoke in long-run validation.

Validation:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_speech_controller.py xinyu_speech_controller_smoke.py xinyu_core_bridge.py xinyu_qq_review.py xinyu_qq_review_smoke.py long_run_status.py
.\.venv\Scripts\python.exe xinyu_speech_controller_smoke.py
.\.venv\Scripts\python.exe chinese_voice_guard_smoke.py
.\.venv\Scripts\python.exe persona_runtime_smoke.py
.\.venv\Scripts\python.exe xinyu_qq_review_smoke.py
.\.venv\Scripts\python.exe bridge_probe_smoke.py
.\.venv\Scripts\python.exe bridge_session_cleanup_smoke.py
.\.venv\Scripts\python.exe long_run_status.py
```

Result:

- Added `xinyu_speech_controller.py`.
- Added `xinyu_speech_controller_smoke.py`.
- Updated `xinyu_core_bridge.py` so the outward renderer delegates prompt construction, quality checks, wrapper stripping, and pressure fallback to the speech controller.
- Preserved old bridge quality-check entry points as compatibility delegates for existing smokes.
- Added default bridge session cleanup arguments for old direct smoke constructors.
- Registered `xinyu_speech_controller_smoke.py` and `xinyu_qq_review_smoke.py` in long-run validation.
- Added source-informed GPT-cliche suppression for pressure turns: ordered essay transitions, summary pivots, "值得注意/简单来说/核心在于/本质上/这意味着", paired contrast templates, abstract filler, and over-structured punctuation.

Stop-and-fix:

- If a QQ style-pressure reply contains product/system words or support-bot templates after retry, do not send it; use the hard fallback or fix the controller.
- If technical work turns are blocked as if they were relationship-pressure turns, loosen only the technical path, not the relationship-pressure gate.
