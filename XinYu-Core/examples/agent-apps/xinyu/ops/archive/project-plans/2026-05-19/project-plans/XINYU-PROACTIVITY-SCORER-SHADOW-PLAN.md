# XinYu Proactivity Scorer Shadow Plan

日期：2026-05-07

## 目标

这一阶段的目标不是让 XinYu 更频繁地发消息，而是让她在主动前先形成可审计的判断：

```text
我现在有一个想法
但它不一定值得说出来
即使值得说，也不一定现在说
即使现在说，也不一定走 QQ
```

第一版只做 shadow mode：评分、记录、解释，不改变真实 QQ 发送行为。

## 非目标

- 不新增 Electron -> NapCat HTTP 直连。
- 不绕过 `xinyu_qq_gateway.py`、`proactive_qq_dispatch_state.md` 或现有 ack 机制。
- 不开放梦境、情绪、孤独类内容自动发 QQ。
- 不继续深挖 Dream v1 表现力，除非它继续污染主动候选。
- 不用小模型主控主动决策。

## 当前架构判断

当前可用链路已经是：

```text
NapCat / OneBot
-> xinyu_qq_gateway.py
-> xinyu_core_bridge.py
-> self_thought_state
-> proactive_request_state
-> proactive_qq_dispatch_state
-> ack / feedback
```

因此主动系统应继续保持：

```text
Core 决策
Gateway 发送
Electron 只做状态探针和展示
```

Electron 可提供环境信号，例如锁屏、空闲、全屏、桌面是否活跃，但不能直接成为 QQ 发送者。

## Dream v1 冻结

Dream v1 当前只作为主动候选来源之一，不作为主线继续扩展。

已保留能力：

- internal dream log 继续保留 `source_seed`、`dream_weight`、`reflection_candidate` 等结构化字段。
- owner-facing dream 去掉代码、报告、日志、权重、seed 字段。
- 梦面由符号重组器生成，避免固定“没有门牌的夜路”模板。
- 旧梦导出时自动净化，避免历史报告味继续暴露。

主动系统第一版不允许梦境直接发 QQ。梦境最多进入 inbox 或 shadow trace。

## 候选模型

新增统一候选结构：

```text
ProactiveCandidate
- candidate_id
- source_type
- source_ref
- intent_type
- owner_visible_text
- content_preview
- utility_hint
- emotional_weight
- novelty_hint
- confidence
- risk_flags
- created_at
- expires_at
```

第一版候选来源：

```text
task_done
task_failed
runtime_error
reflection_question
dream_residue
style_repair
owner_long_idle
```

第一版不追求新增大量候选，而是把现有状态统一读成候选：

- `memory/context/proactive_request_state.md`
- `memory/context/self_thought_state.md`
- `memory/context/runtime_program_awareness.md`
- `memory/dreams/dream_output_state.md`
- `memory/dreams/dream_log.md`
- `memory/reflection/reflection_queue.md`
- `memory/context/qq_outbox_dispatch_state.md`

## 评分模型

新增 `ProactivityScore`：

```text
positive:
- utility_score
- urgency_score
- owner_relevance
- novelty_score
- inner_pressure

negative:
- interruption_cost
- repetition_penalty
- uncertainty_penalty
- flavor_penalty
- stale_penalty

derived:
- total_score
- confidence
- hard_blocks
- reasons_positive
- reasons_negative
```

建议权重：

```text
total_score =
  utility_score
+ urgency_score
+ owner_relevance
+ novelty_score
+ inner_pressure
- interruption_cost
- repetition_penalty
- uncertainty_penalty
- flavor_penalty
- stale_penalty
```

评分范围统一为 0-100，最后 clamp 到 0-100。

## 类型阈值

第一版阈值偏保守。

```text
task_failed / runtime_error:
  inbox >= 45
  send_now >= 70

task_done:
  inbox >= 50
  send_now >= 75

reflection_question / style_repair:
  inbox >= 55
  send_now >= 90

dream_residue:
  inbox >= 60
  send_now >= 95
  qq_send hard-blocked in v0

owner_long_idle:
  inbox >= 70
  send_now hard-blocked in v0
```

Shadow mode 下不会真实 send_now，只记录如果自动发送开启会如何推荐。

## Interruption Gate

Scorer 判断内容值不值得主动，Interruption Gate 判断现在能不能打扰。

需要读取或派生：

```text
owner_recent_private_minutes
desktop_active
system_idle_state
screen_locked
fullscreen
quiet_hours
last_proactive_sent_at
last_owner_reply_to_proactive_at
unanswered_proactive_count
same_type_last_sent_at
```

硬阻断：

```text
screen_locked + dream/emotion -> hold
quiet_hours + non_urgent -> hold
unanswered_proactive_count >= 2 -> hold
same_type_cooldown_active -> hold
owner recently rejected/annoyed -> hold
owner-facing text leaks internal marker -> drop
```

冷却建议：

```text
task/status: 30 min
reflection/style: 6 h
dream/flavor: 24 h
owner_long_idle: 12 h
```

## 决策输出

新增统一决策结构：

```text
ProactiveDecision
- decision_id
- checked_at
- candidate_id
- source_type
- intent_type
- total_score
- recommendation: send_now | inbox | hold | drop
- preferred_channel: qq | desktop | inbox | silent
- shadow_only: true
- hard_blocks
- reasons_positive
- reasons_negative
- next_review_after
```

推荐语义：

```text
send_now:
  如果真实发送开放，可以立即进入发送链路。

inbox:
  只进入桌面主动 inbox，不外发 QQ。

hold:
  候选仍有价值，但当前时机不对。

drop:
  内容质量、风险或重复度不值得保留。
```

## Trace 文件

新增两个文件：

```text
memory/context/proactive_decision_trace.jsonl
memory/context/proactive_decision_state.md
```

`jsonl` 保存机器可读完整记录。

`md` 保存最近一次或最近 N 次人类可读摘要。

示例：

```text
## Latest Shadow Decision
- checked_at: 2026-05-07T...
- candidate_id: proshadow-...
- source_type: dream_residue
- preview: 我梦见没有天花板的旧图书馆...
- total_score: 63
- recommendation: inbox
- preferred_channel: inbox
- shadow_only: true
- hard_blocks: qq_send_disabled_for_dream_v0
- positive: novelty_score, inner_pressure
- negative: flavor_penalty, interruption_cost, dream_daily_cooldown
```

## Desktop 展示

桌面端可后续读取 `proactive_decision_state.md` 或 Core snapshot，展示：

```text
主动性影子决策
- 她想说什么
- 为什么想说
- 为什么没说
- 如果开启自动发送会走哪里
```

第一版可以只写文件，不改桌面 UI。

## Feedback Loop v0

第一版只记录反馈，不改变发送行为。

反馈类型：

```text
explicit_positive:
  owner 回复、继续聊、要求展开

explicit_negative:
  owner 嫌烦、说别发、说像模板、说没意义

implicit_positive:
  owner 打开 desktop
  owner 点开 proactive inbox
  owner 之后主动问起该主题

silence:
  不视为负反馈，只增加冷却或降低急迫度
```

建议影响：

```text
explicit_positive -> 同类轻微降阈值
explicit_negative -> 同类大幅升阈值 + cooldown
implicit_positive -> 记录 seen，不直接降阈值
silence -> urgency_decay，不扣内容质量分
```

## 第一轮实现范围

建议新增：

```text
xinyu_proactivity_scorer.py
proactivity_scorer_smoke.py
```

建议修改：

```text
xinyu_core_bridge.py
  在 autonomous_maintenance 后调用 scorer shadow mode。

xinyu_runtime_presence.py 或相关状态读卡
  可选：把最新 proactive_decision_state 纳入 runtime awareness。
```

第一轮不修改：

```text
xinyu_qq_gateway.py
proactive_qq_dispatch_state.md 的真实 claim/ack 行为
Electron 主进程 QQ 发送路径
```

## Smoke 覆盖

至少覆盖：

```text
1. dream_residue 不推荐 QQ send
2. task_failed 可推荐 send_now，但 shadow_only=true
3. screen_locked 阻断 dream/emotion
4. unanswered_proactive_count >= 2 触发 hold
5. owner-facing text 泄露 Codex/source_seed/dream_weight 时 drop
6. repeated same candidate 触发 repetition_penalty
7. jsonl trace 和 md state 都写入
```

## 验收标准

第一版完成后必须满足：

- 不增加真实 QQ 主动发送频率。
- 不绕过现有 gateway / outbox / ack。
- 每次主动候选都有可审计分数。
- 梦境、情绪类候选默认不会发 QQ。
- 任务失败、运行异常类候选能在 shadow 中显示较高优先级。
- 决策原因能被 owner 看懂。
- 后续可以根据 trace 调阈值，而不是凭感觉改 prompt。

## 后续阶段

### Phase 2: Review Trace

运行 2-3 天，人工审查：

```text
它想说的东西有没有意义？
是不是太频繁？
哪些 hold 应该 inbox？
哪些 inbox 应该 drop？
任务类有没有漏报？
梦和情绪类是否仍然自我感动？
```

### Phase 3: Conservative Dispatch

只开放：

```text
task_failed
runtime_error
task_done
```

仍不开放：

```text
dream_residue -> QQ
owner_long_idle -> QQ
generic emotional check-in -> QQ
```

### Phase 4: Adaptive Feedback

用 owner 明确反馈和隐式反馈调整阈值、冷却和类型惩罚。

## 一句话原则

先让 XinYu 拥有“冲动和克制的记录”，再让她拥有真正的主动出口。
