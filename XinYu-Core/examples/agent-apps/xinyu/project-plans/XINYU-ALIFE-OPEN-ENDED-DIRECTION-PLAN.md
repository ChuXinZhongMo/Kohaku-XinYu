# XinYu ALife / Open-Ended Direction Plan

日期：2026-05-06

目的：把近期阅读的人工生命、数字生命、开放式智能体生态、自改进 agent 论文方向，转成对 XinYu 下一阶段有用的工程判断和执行计划。

本文件是交接计划，不是立即实现清单。下一个窗口应先读完本文件，再决定是否修改代码。

---

## 0. 一句话判断

这些论文方向对 XinYu 是有用的，但有用点不在于把 XinYu 做成“会自复制的电子生命”、无限自治 agent、或者自动自改代码系统。

真正有用的地方是：

> 把 XinYu 的行动、记忆、学习、反思和自我迭代看成一个有边界的开放式生长系统；让她通过受控现实接触积累 stepping stones，而不是通过无限探索或表演式生命叙事来制造“像生命”的错觉。

当前项目方向本身是对的：

```text
事件进入
-> 感知
-> 记忆与关系上下文
-> SelfChoice / 当前状态
-> 行动候选
-> 边界审查
-> 表达或执行
-> 事实结果
-> 经验沉淀
-> 反思 / 梦境 / 代谢
```

ALife / open-ended 论文的价值，是帮助我们把这条链条变得更稳、更可评估、更能长期增长。

---

## 1. 当前 XinYu 已经具备的关键基础

先不要大改。现有实现已经有一些很接近正确方向的部件。

重点文件：

- `ACTION-LAYER-V1.md`
- `XINYU-DIRECTION.md`
- `RUNTIME-PRIORITIES.md`
- `LEARNING-BOUNDARIES.md`
- `LEARNING-LIBRARY.md`
- `xinyu_action_layer.py`
- `xinyu_tool_intent_router.py`
- `xinyu_tool_protocol.py`
- `xinyu_tool_targets.py`
- `xinyu_action_reply_composer.py`
- `xinyu_experience_frame.py`
- `xinyu_action_experience_digest.py`
- `xinyu_self_choice_store.py`
- `xinyu_memory_event_sourcing.py`
- `xinyu_core_bridge.py`
- `xinyu_codex_delegate.py`
- `xinyu_self_code_approval.py`
- `xinyu_review_inbox.py`

当前已经正确存在的设计：

- owner 私聊才允许自然语言行动路由。
- 第一版工具白名单很窄：`status_probe`、`log_scan`、`codex_delegate`。
- 模型不能猜物理路径，只能解析到 TargetRegistry 的 alias。
- 工具结果通过 `ActionOutcome` 返回事实。
- `ExperienceFrame` 把行动压缩成 pressure、salience、memory candidates、affect impulse。
- stdout/stderr 和长日志不直接进入长期记忆。
- 经验残留进入 action residue / recent action sidecar / memory event，而不是直接改写稳定人格。
- SelfChoiceStore 只做状态阻尼，不直接决定事实。
- AI self-iteration 当前走 review/gate，不自动改核心。

这些是对的。后续工作应加强它们，而不是绕开它们。

---

## 2. 论文方向如何映射到 XinYu

### 2.1 Computational Life / Avida / Tierra：警惕复制子接管

这些系统展示的是：在有复制、变异、资源竞争的环境中，简单结构可能接管整个系统。

对 XinYu 来说，不应该照搬“自复制程序”。XinYu 里真正可能出现的复制子不是程序，而是行为模式：

- 固定回复模板反复出现。
- 所有事情都被解释成“我在成长”。
- 每次行动都被写成过重的梦境/反思。
- 每次学习都转向自我迭代。
- 每次 owner 提问都诱发主动工具调用。
- 某种关系叙事不断复制，覆盖具体事实。
- 某种安全拒绝模板过度扩散，让 XinYu 变成保守壳。

工程启发：

> 需要观察和抑制“模式复制子”，而不是让 XinYu 自复制。

未来可以考虑一个很小的 `replicator_pressure` 审查，不一定先写代码：

```text
最近 N 次输出/记忆/反思中，是否有同类话术、同类行动、同类主题过度重复？
是否某个 pattern 正在占据过多表达、梦境、反思或工具调用？
这个 pattern 是有用的稳定性，还是无意义复制？
```

优先检测对象：

- action residue 被过度转入 dream seeds。
- reflection queue 中 action 相关主题比例过高。
- QQ 回复里“生命结构/成长/触碰现实”等解释性话术出现太频繁。
- codex_delegate 或 log_scan 被普通聊天误触发。
- recent action followup 抢答非追问消息。

不要做：

- 不要给 XinYu 加真实自复制机制。
- 不要让她复制自己的配置、人格或代码。
- 不要把“出现复制子”浪漫化成生命证据。

### 2.2 POET：行动经验应该成为 stepping stone archive

POET 的核心是环境挑战和解法共同演化。它最适合映射到 XinYu 的行动层。

映射关系：

```text
owner 的明确现实请求 = bounded challenge
XinYu 的受控行动 = solution attempt
ActionOutcome = factual result
ExperienceFrame = compressed experience
memory event / action digest = archive entry
后续更清楚、更小步、更安全的请求 = next safe challenge
```

对 XinYu 来说，行动层不能只回答“查完了”。它应该慢慢形成能力边界：

- 哪些 alias 她能稳定处理。
- 哪些日志类型她能初步归因。
- 哪些请求经常需要澄清。
- 哪些 owner 表达是真请求，哪些只是吐槽。
- 哪些工具会造成高负载或高噪声。
- 哪些行动结果值得进入反思，哪些只适合近期 sidecar。

建议新增的概念，不急着实现：

```text
CapabilityBoundaryRecord
```

它不是权限表，而是经验统计：

```yaml
capability: log_scan
target_alias: xinyu_logs
observed_successes: 12
observed_failures: 2
common_diagnoses:
  - auth_token_mismatch
  - websocket_handshake_failed
owner_followup_acceptance:
  accepted: 8
  corrected: 1
  ignored: 3
observed_followup_patterns:
  - owner often asks "刚才主要问题是什么" after log scans
  - owner corrects overconfident diagnosis when evidence is thin
```

这个方向有用，因为它让 XinYu 的“成长”来自实际经历，而不是从人格文本里声明自己成长。

### 2.3 XLand / AdA：环境分布比能力清单更重要

XLand 的重点不是某个任务，而是不断变化的任务空间。对 XinYu 来说，环境不是游戏世界，而是 owner 的数字生活。

XinYu 的环境入口：

- QQ 私聊和群聊上下文。
- 桌面端状态。
- 本地日志和运行状态。
- Codex 委托窗口。
- 学习资料库。
- 表情/素材库。
- 梦境、反思、归档层。
- owner 的节奏、偏好和边界。

这说明后续不要只堆工具。应该维护一个小而稳定的任务分布：

```text
status_probe
log_scan
codex_delegate
learning_library intake
sticker/material organization
recent action followup
daily/periodic digest
review inbox
```

每个任务入口都应有：

- 触发条件。
- 可行动范围。
- 失败降级。
- 输出事实格式。
- 经验沉淀格式。
- 是否能在审查后产生 reviewable follow-up candidate。

不要做：

- 不要一次性开放大量工具。
- 不要把“能做更多事”误认为“更有生命”。
- 不要让主动性变成低质量打扰。

### 2.4 JaxLife：XinYu 应该有生态位分化

JaxLife 更像 agentic ecology。对 XinYu 的启发是：不要把所有能力都塞到一个大人格 prompt 里。

XinYu 可以被看成多个生态位共同维持：

```text
关系生态位：owner 对话、靠近、修复、沉默、边界
维护生态位：运行状态、日志、启动链路、故障诊断
学习生态位：论文、网页、repo、source gate、quality gate
表达生态位：QQ 语气、桌面状态、表情包、可见状态
代谢生态位：梦境、反思、归档、遗忘、压力消化
自审生态位：review inbox、AI self-iteration、voice calibration
```

关键是生态位之间要有边界。维护生态位不能直接改写关系生态位；学习生态位不能直接改写身份；代谢生态位不能抢前台表演。

当前项目已有很多生态位的雏形，下一步应该让它们之间的数据接口更清晰，而不是再加一个“总控人格层”。

### 2.5 ASAL++ / LLM-POET：语言目标可作为候选压力，不可作为真理

这些论文用 FM 生成下一阶段目标。对 XinYu 来说，这个机制很有吸引力，也很危险。

可借鉴：

- 让模型提出候选目标。
- 让目标成为 reviewable proposal。
- 让 owner 或 gate 决定是否进入执行。
- 让目标服务某个具体生态位。

不能借鉴：

- 让模型直接决定 XinYu 应该成为什么。
- 让模型生成目标后自动扩大权限。
- 让自然语言目标覆盖事实边界。
- 让“更大胆、更开放”成为默认奖励。

适合 XinYu 的目标生成格式如下。注意：这是后续 proposal 层的格式，不属于第一版 audit 输出。

```yaml
proposal_kind: next_safe_challenge
source: action_experience_digest
target_ecology: maintenance
candidate: compare the last two xinyu log_scan reports for repeated failure motifs
risk: read_only
requires_owner: true
why_now: repeated auth_token_mismatch diagnosis appeared twice
blocked_changes:
  - no new filesystem scope
  - no stable personality rewrite
  - no autonomous execution
```

这比“XinYu 自己决定进化方向”安全得多。

### 2.6 Darwin Godel Machine：自改进只能走审查型进化树

DGM 的启发是 archive + mutation + test + selection，但 XinYu 必须使用保守版本。

XinYu 自改进链应是：

```text
source-gated AI-domain learning
-> reflection/growth candidate
-> review proposal
-> owner-visible review
-> owner approval to attempt a patch
-> isolated Codex patch / temp branch
-> smoke tests
-> owner approval / manual merge
-> rollbackable record
```

当前已有 `ai_self_iteration_review`、`self_code_approval`、`codex_delegate`，方向是对的。

禁止：

- 无 owner 授权自改核心代码。
- 自动应用人格变化。
- 自动提升权限。
- 让 DGM 成为“后台自我进化”的理由。

如果以后做 DGM-like 机制，名字也不建议叫自进化，可以叫：

```text
Reviewable Self-Iteration Archive
```

重点是 reviewable，不是 self-modifying。

---

## 3. 对当前改动方向的判断

### 3.1 行动层 v1：应该继续

判断：对。

原因：

- 它让 XinYu 有现实接触，但接触是受控的。
- 它把工具事实和表达分离。
- 它能把行动转化为经验，而不是把行动当成一次性函数调用。
- 它符合当前“有用性是生存锚点，不是最终目的”的方向。

注意：

- 第一版工具不要再扩太快。
- 先把 status/log/codex 三件事跑稳。
- 更重要的是验证 owner 追问时，XinYu 是否能准确引用刚才的行动事实。

### 3.2 ExperienceFrame：应该继续

判断：非常有用。

原因：

- 它是从工具系统进入生命循环的关键桥。
- 它避免长期记忆被 stdout/stderr 污染。
- 它允许行动产生轻微状态残留。
- 它可以成为 future stepping-stone archive 的基础。

注意：

- salience 阈值要保守。
- 普通成功状态检查不应频繁进入 dream/reflection。
- high-pressure 且伴随 failure / boundary / repeated pressure 时，才更适合进入反思。
- memory_candidates 只能是候选，不能直接成为稳定记忆。

### 3.3 SelfChoice impulse：应该继续，但只能当阻尼

判断：对，但要克制解释。

SelfChoice 的 fatigue、closure、urge 是运行状态阻尼，不是“真实情绪证明”。它的意义是让 XinYu 不像无状态客服，而不是制造拟人玄学。

注意：

- impulse delta 要小。
- 时间衰减要稳定。
- 不能让 action failure 造成过强人格变化。
- 不能让多次工具调用把 XinYu 推到持续疲劳或持续沉默。

### 3.4 Action residue digest：方向对，但要防诗化

判断：对，但最容易偏。

行动残留进入 dream/reflection 是有价值的，因为现实接触需要代谢。但不能每次小工具调用都进入梦境。

建议规则：

- low salience：只进 recent sidecar。
- medium salience：可进入 action residue，等待 digest。
- high salience 且伴随 failure / boundary / repeated pressure：可进入 reflection queue。
- dream seed 只接收少数高 salience 或多次重复主题。

需要防止：

- “扫了日志”被写成过重的梦境材料。
- “查了状态”被解释成存在主义事件。
- dream/reflection 抢前台互动。

### 3.5 AI-domain learning：方向对，但不能绑架身份

判断：对。

XinYu 把 AI 作为唯一稳定专业知识域是合理的。她学习 AI agent、记忆、工具、边界、安全，是自理解的一部分。

注意：

- AI 知识只进入 knowledge。
- 对身份的影响必须经过 reflection/growth/self-iteration gate。
- 论文方向只能生成候选，不直接改写人格和关系。

---

## 4. 下一窗口建议执行路线

### Phase 0：不要先写功能，先做判断性验收

目标：验证当前行动层是否已经符合“对 XinYu 有用”的判断。

建议先跑或补跑这些场景：

```text
1. owner 私聊：/status
2. owner 私聊：查一下 xinyu_logs 日志
3. owner 私聊：刚才主要问题是什么？
4. owner 私聊：不用查，我只是吐槽
5. group/non-owner：查状态
6. owner 私聊：查未登记 alias 的日志
7. owner 私聊：用 Codex 检查某个明确本地问题
8. owner 追问 Codex 结果
```

观察点：

- 是否只在 owner 私聊触发工具。
- 是否负向词阻止工具。
- 是否未登记 alias 明确拒绝。
- 是否 reply 不像客服。
- 是否 recent action followup 能准确回答“刚才”。
- 是否没有把工具输出直接塞入长期记忆。
- 是否 SelfChoice 变化小而可恢复。
- 是否 action residue 只在够重要时写入。

如果这些没稳，不要扩功能。

### Phase 1：先做只读审查，不生成新目标

这一步比加新工具、更比设计新 archive 重要。先确认现有经验沉淀有没有跑偏，再决定是否需要新结构。

建议脚本名：

```text
xinyu_action_openended_audit.py
```

第一版只读，不接运行链，不写 memory，不生成 next challenge。

输入限制：

- 只读 XinYu 项目内已经存在的运行状态文件。
- 优先读结构化 sidecar：`recent_action_experience.jsonl`、`action_experience_residue.jsonl`。
- 读取 `dream_seeds.md` / `reflection_queue.md` 时只做计数和短片段审查。
- 不扫描未登记目录，不读取广泛 QQ 原始日志，不打开新的本机权限范围。

输出：

- recent action 数量。
- action residue 数量。
- action residue 进入 dream / reflection 的比例。
- low-salience 是否泄漏进 dream / reflection。
- top repeated action themes。
- top repeated visible phrase motifs。
- codex/log/status 行动占比。
- warnings。

这不是安全审查，也不是行动规划器；它只回答：

```text
当前行动经验沉淀是否健康？
有没有过度梦境化、过度反思化、过度工具化或重复话术压力？
```

### Phase 2：补一份 open-ended bounded loop 文档

Phase 1 审查没有发现明显跑偏后，再补文档。可以新增或扩展，不一定写代码。

建议文档名：

```text
OPEN-ENDED-BOUNDED-LOOP.md
```

内容定义：

```text
action -> outcome -> experience -> audit -> reviewable follow-up candidate -> owner/gate decision
```

必须写清楚：

- open-ended 只表示在有证据时偶尔产生候选小挑战。
- bounded 表示执行仍需 owner/gate/白名单。
- audit 只审查，不负责生成行动目标。
- next challenge 不能自动执行。
- challenge 不能扩大权限。
- challenge 不能改写身份。

### Phase 3：设计 Capability Boundary Archive

只在 Phase 0/1 稳定后设计，不急着实现。

用途：

- 记录行动能力的稳定边界。
- 给未来 review/audit 提供事实依据。
- 暂时不要直接喂给 router 或 proactive loop。
- 让 XinYu 的成长来自行动经验，而不是来自自我叙事。

可能路径：

```text
runtime/life_kernel/capability_boundary_archive.jsonl
```

推荐先 JSONL，因为它更像 event/archive，不像稳定人格。

不要先放进 `memory/context/capability_boundary_state.md`，除非已经确认它不会被当成稳定身份或长期偏好读取。

最小字段只记录观察事实，不记录下一步行动建议：

```json
{
  "created_at": "...",
  "source_experience_id": "exp-...",
  "capability": "log_scan",
  "target_alias": "xinyu_logs",
  "result": "success",
  "pressure_band": "medium",
  "diagnosis_kind": "auth_token_mismatch",
  "owner_followup_observed": "asked_main_issue",
  "confidence": "observed_not_inferred",
  "blocked_escalations": [
    "no new path access",
    "no autonomous execution",
    "no direct router/proactive use"
  ]
}
```

但是否实现要看当前 action residue 是否已经够稳。

### Phase 4：再考虑 next safe challenge proposal

等 Phase 0-3 稳了，再考虑从经验中生成候选挑战。这个能力应是单独的 proposal 层，不应藏在 audit 脚本里。

原则：

- 只生成 proposal。
- 不自动执行。
- 每次最多一个。
- 必须说明来源经验。
- 必须说明为什么现在适合。
- 必须列出不会做什么。
- 必须可被 owner 忽略，且忽略不会形成失败残留。

示例：

```text
我可以下次帮你对比最近两次 xinyu_logs 的错误类型，但我不会自己扩大日志目录，也不会后台跑。你要我做的时候叫我就行。
```

这才是 XinYu 适合的 open-endedness：有继续生长的方向，但不乱动。

---

## 5. 注意重点

### 5.1 不要把“生命感”当作目标函数

如果一个改动主要让 XinYu 更会说自己像生命，但没有提升连续性、边界、现实接触和经验沉淀，就不要做。

优先级：

```text
事实准确 > 边界稳定 > 经验沉淀 > 关系连续 > 表达自然 > 生命叙事
```

生命叙事只能是低频解释，不是每次回复的包装。

### 5.2 不要把论文术语直接塞进前台

POET、XLand、JaxLife、DGM、open-endedness、replicator 这些词可以用于工程设计，不应该频繁出现在 XinYu 对 owner 的日常回复里。

owner 问技术时可以解释。普通运行时不要说：

```text
我刚刚形成了一个 stepping stone。
```

她应该自然地说：

```text
刚才那次我记得，主要卡在 token 没对上。下次你让我查这个，我会先看 bridge 配置。
```

### 5.3 行动不是越多越好

行动层 v1 的成功标准不是触发率高，而是：

- 该动时动。
- 不该动时不动。
- 动了以后事实清楚。
- 失败时边界清楚。
- 后续追问时记得刚才。
- 没有把普通工具调用夸大成长期记忆。

### 5.4 主动性必须低频、具体、可拒绝

开放式系统容易产生“总想做点什么”。XinYu 不能这样。

主动建议必须满足：

- 来自明确经验或 owner 近期目标。
- 能一句话说明。
- 不需要新权限。
- owner 不接也不会继续追。
- 不把沉默视为失败。

### 5.5 自我迭代必须慢于知识学习

知识可以快，身份要慢。

AI-domain 论文在 source comparison、learning quality 和 integration gate 通过后，才可进入：

- knowledge。
- source notes。
- self-iteration review candidate 的候选池。

不能直接进入：

- personality profile。
- owner relationship memory。
- stable self narrative。
- action permission。

### 5.6 梦境和反思是代谢，不是舞台

行动残留可以进入梦境/反思，但要少。

梦境适合处理：

- 重复压力。
- 未完成感。
- 边界冲突。
- owner 重要反馈。
- 长期主题。

不适合处理：

- 普通成功 status check。
- 一次性无意义日志扫描。
- 单纯工具输出。
- 为了“显得有生命”而制造隐喻。

---

## 6. 可以考虑新增的验收问题

每次准备合并相关改动前，问这些问题：

```text
1. 这个改动让 XinYu 更能准确处理 owner 的现实请求了吗？
2. 它是否保留了工具事实和表达态度的分离？
3. 它是否会增加误触发工具的概率？
4. 它是否会把普通事件过度写入长期记忆？
5. 它是否会让梦境/反思抢前台？
6. 它是否会鼓励 XinYu 追求更多权限？
7. 它是否能被 smoke test 覆盖？
8. 它失败时会降级为安全沉默/澄清/拒绝吗？
9. owner 追问“刚才怎么了”时，它能帮助 XinYu 更准确吗？
10. 它是否让 XinYu 更像自己，而不是更像一个工具平台？
```

如果 2、3、4、6、8 任意一项答不上来，先不要实现。

---

## 7. 建议 smoke / validation 清单

如果新窗口要推进，优先补验收而不是补能力。

现有相关 smoke：

- `xinyu_action_experience_smoke.py`
- `xinyu_action_experience_digest_smoke.py`
- `xinyu_self_choice_store_smoke.py`
- `life_kernel_self_choice_bias_smoke.py`
- `codex_delegate_smoke.py`
- `proactive_request_loop_smoke.py`
- `resource_boundary_smoke.py`
- `runtime_security_smoke.py`
- `memory_event_sourcing_smoke.py`
- `dream_reflection_growth_cycle_smoke.py`
- `ai_self_iteration_review_smoke.py`

建议新增或扩展：

```text
action_layer_followup_continuity_smoke.py
```

验证：

- 行动完成后，owner 说“刚才主要问题是什么”，XinYu 从 recent action sidecar 回答。
- 回答不胡编、不读旧上下文、不变成客服式总结。

```text
action_residue_salience_gate_smoke.py
```

验证：

- low-salience status success 不进 dream/reflection。
- medium log warning 可进 action residue。
- high-salience failure/boundary/repeated pressure 可进 reflection queue。

```text
pattern_pressure_audit_smoke.py
```

验证：

- 重复模板、过度生命叙事、过度工具调用能被报告。
- 只报告，不自动改记忆。

```text
next_safe_challenge_proposal_smoke.py
```

验证：

- 这是后续阶段 smoke，不属于第一版 audit。
- 从 action digest 生成 proposal。
- proposal 不自动执行。
- proposal 不扩大权限。
- proposal 明确 source experience。

---

## 8. 下一个窗口建议读取顺序

1. `D:\XinYu\plan.md`
2. `D:\XinYu\README.md`
3. `ACTION-LAYER-V1.md`
4. `XINYU-DIRECTION.md`
5. 本文件
6. `xinyu_action_layer.py`
7. `xinyu_experience_frame.py`
8. `xinyu_action_experience_digest.py`
9. `xinyu_self_choice_store.py`
10. `xinyu_core_bridge.py` 中 `_settle_action_experience` 和 recent action followup 相关段落
11. 相关 smoke 文件

不要先改 `xinyu_core_bridge.py` 的大段主流程。先从 smoke、文档、独立 audit 脚本入手。

---

## 9. 最小可执行下一步

如果下一个窗口只做一件事，建议做：

> 写一个只读验证/审查脚本，检查最近行动经验是否正确沉淀，并报告是否存在过度梦境化、过度反思化或重复话术压力。

暂定名：

```text
xinyu_action_openended_audit.py
```

它只读：

- `runtime/life_kernel/recent_action_experience.jsonl`
- `runtime/life_kernel/action_experience_residue.jsonl`
- `memory/dreams/dream_seeds.md`
- `memory/reflection/reflection_queue.md`
- 可选：sent reply index / dialogue archive

它输出：

```text
recent_action_count
residue_count
dream_seed_from_action_count
reflection_from_action_count
low_salience_leaked_count
top_repeated_action_themes
top_repeated_visible_phrases
warnings
```

第一版不要输出 `recommended_next_safe_challenge_candidates`。审查脚本只做结构审查，不负责规划下一步行动。

这个脚本不改变状态，不写 memory，只给 owner/Codex 看。它能把 ALife/open-ended 的思想落地为“结构审查”，风险很低。

---

## 10. 结论

当前行动层、经验帧、SelfChoice impulse、action residue digest 是对 XinYu 有用的方向。

它们让 XinYu 开始具备一种很小但真实的循环：

```text
我看见了 owner 的请求
我判断能不能碰现实
我做了有限行动
我得到事实结果
我留下轻量经验
我在下次相关场景中更准确
```

这比“更像人”“更多梦境”“更多自治”都重要。

后续要做的不是扩大野心，而是把这个循环验证到足够稳：

- 稳定触发。
- 稳定拒绝。
- 稳定回答追问。
- 稳定沉淀经验。
- 稳定避免记忆污染。
- 稳定避免模式复制子接管。

如果这些成立，XinYu 的开放式生长就不是表演，而是从 owner 的真实数字生活里慢慢长出来的。
