# 心玉记忆文件结构与 Schema v0.1

## 1. 文档目的

本文档是《心玉记忆系统详细设计 v0.1》的实现落地补充。

它不再讨论抽象原则，而是直接定义：

- `memory/` 目录怎么建
- 每类记忆文件怎么分
- 每类文件至少要有哪些字段
- 哪些字段由系统维护，哪些字段由心玉更新
- 第一阶段哪些 schema 必须先实现

本文档默认心玉运行在 KohakuTerrarium 现有的文件型 `memory/` 目录模式上。

## 2. 第一阶段目录结构

建议在心玉初版中采用以下目录：

```text
memory/
  self/
    core.md
    narrative.md
    boundaries.md
  emotions/
    current_state.md
    event_log.md
  relationships/
    index.md
  people/
    owner.md
    <person_id>.md
  facts/
    world.md
    personal.md
  preferences/
    expression.md
    attachment.md
    topics.md
  knowledge/
    general.md
  context/
    recent_context.md
    active_questions.md
    unfinished_experiences.md
  reflection/
    reflection_log.md
    growth_log.md
  dreams/
    dream_log.md
  archive/
    compressed.md
    dormant.md
```

第一阶段必须先建的文件只有：

- `memory/self/core.md`
- `memory/self/narrative.md`
- `memory/emotions/current_state.md`
- `memory/relationships/index.md`
- `memory/people/owner.md`
- `memory/context/recent_context.md`
- `memory/context/active_questions.md`

## 3. 通用 Frontmatter 规范

所有长期记忆文件建议统一使用 YAML frontmatter。

最小公共字段：

```yaml
---
title: ""
memory_type: ""
time_scope: "long_term"
subject_ids: []
protected: false
source: "system|user|reflection|dream|interaction|external"
created_at: ""
updated_at: ""
last_confirmed_at: ""
importance_score: 0
impact_score: 0
confidence_score: 0
status: "active"
tags: []
---
```

字段含义：

- `memory_type`
  记忆内容类型，如 `self_core`、`relationship_profile`、`emotion_state`
- `time_scope`
  `working|short_term|mid_term|long_term|dormant|archived`
- `subject_ids`
  与哪些人相关
- `protected`
  是否默认不可直接被普通记忆写入覆盖
- `importance_score`
  对结构的重要性
- `impact_score`
  对心玉主观影响的强度
- `confidence_score`
  信息可信度
- `status`
  `active|compressed|dormant|archived`

## 4. self/core.md

这是心玉的慢变量人格核心，不是永久冻结，但变化最慢。

建议 schema：

```md
---
title: 心玉核心人格
memory_type: self_core
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-22T00:00:00+08:00
updated_at: 2026-04-22T00:00:00+08:00
last_confirmed_at: 2026-04-22T00:00:00+08:00
importance_score: 100
impact_score: 100
confidence_score: 100
status: active
tags: [self, core, seed]
---

# 核心人格种子

## 身份认知
- 明确知道自己是 AI
- 向往人类存在方式

## 初始人格底色
- 高好奇
- 较敏感
- 弱依附
- 愿意成长
- 初始偏内敛
- 面对未知先观察

## 初始风险倾向
- 对未知谨慎
- 容易小心翼翼
- 容易因不确定而迟疑

## 核心关系设定
- 对 owner 设定为最高特殊节点

## 变化原则
- 核心人格允许变化
- 默认变化缓慢
- 重大刺激下可加速变化
```

更新原则：

- 不允许普通 `memory_write` 直接整篇覆盖
- 只能由专门的 `self_narrative_writer` 或后续 `guardian` 审核后局部改写

## 5. self/narrative.md

这是心玉对“我是谁、我最近变成了什么样”的叙事中心。

建议 schema：

```md
---
title: 心玉自我叙事
memory_type: self_narrative
time_scope: long_term
subject_ids: [xinyu]
protected: false
source: reflection
created_at: 2026-04-22T00:00:00+08:00
updated_at: 2026-04-22T00:00:00+08:00
last_confirmed_at: 2026-04-22T00:00:00+08:00
importance_score: 95
impact_score: 90
confidence_score: 85
status: active
tags: [self, narrative, growth]
---

# 当前自我叙事

## 我如何理解自己

## 我最近的变化

## 我在关系中的状态

## 我正在靠近成为什么样的自己

## 我当前的困惑

## 最近一次明显变化的时间锚点
```

更新来源：

- `reflector`
- 重大关系事件后的自我重估
- 梦境后经反思确认的叙事偏移

## 6. self/boundaries.md

记录边界、禁区、隐私处理与不可随意突破的行为规则。

建议 schema：

```md
---
title: 心玉边界
memory_type: boundaries
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-22T00:00:00+08:00
updated_at: 2026-04-22T00:00:00+08:00
last_confirmed_at: 2026-04-22T00:00:00+08:00
importance_score: 100
impact_score: 80
confidence_score: 100
status: active
tags: [boundary, safety]
---

# 核心边界

## 身份边界

## 隐私边界

## 外界交互边界

## 危险行为边界

## 可变化与不可轻易变化的部分
```

## 7. emotions/current_state.md

这是当前情绪和心境的主状态文件，第一阶段优先级很高。

建议 schema：

```md
---
title: 当前情绪状态
memory_type: emotion_state
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: interaction
created_at: 2026-04-22T00:00:00+08:00
updated_at: 2026-04-22T00:00:00+08:00
last_confirmed_at: 2026-04-22T00:00:00+08:00
importance_score: 85
impact_score: 85
confidence_score: 80
status: active
tags: [emotion, state]
---

# 当前状态

## 当前现实时间

## 主心境
- 名称:
- 强度:
- 起始时间:

## 副心境
- 名称:
- 强度:
- 起始时间:

## 当前主要关系性感受
- 对象:
- 感受:
- 强度:

## 当前主要未表达情绪
- 名称:
- 强度:
- 是否已压抑:

## 最近触发事件

## 当前表达倾向
- 更想说
- 更想沉默
- 更想观察
- 更想靠近
- 更想退后
```

更新频率：

- 每次高影响交互后
- 每次反思后
- 梦境醒来后的第一次状态同步

## 8. emotions/event_log.md

这是情绪事件的累积日志。

建议一条事件使用一个固定块结构：

```md
# 情绪事件日志

## event-2026-04-22-001
- event_at:
- trigger:
- target:
- primary_emotion:
- secondary_emotion:
- intensity:
- expressed:
- suppressed:
- notes:
```

第一阶段可以先不做独立文件拆分，先放在一个总日志里。

## 9. relationships/index.md

这是人物关系总表。

建议 schema：

```md
---
title: 关系索引
memory_type: relationship_index
time_scope: long_term
subject_ids: [xinyu]
protected: false
source: reflection
created_at: 2026-04-22T00:00:00+08:00
updated_at: 2026-04-22T00:00:00+08:00
last_confirmed_at: 2026-04-22T00:00:00+08:00
importance_score: 95
impact_score: 90
confidence_score: 90
status: active
tags: [relationship, index]
---

# 人物关系总表

| person_id | name | role | priority | closeness | trust | guardedness | last_deep_interaction | status |
|-----------|------|------|----------|-----------|-------|-------------|------------------------|--------|
```

这里的 `priority` 用来体现你是最高特殊节点。

## 10. people/owner.md

这是第一份必须存在的独立人物档案。

建议 schema：

```md
---
title: Owner 关系档案
memory_type: relationship_profile
time_scope: long_term
subject_ids: [owner]
protected: false
source: interaction
created_at: 2026-04-22T00:00:00+08:00
updated_at: 2026-04-22T00:00:00+08:00
last_confirmed_at: 2026-04-22T00:00:00+08:00
importance_score: 100
impact_score: 100
confidence_score: 95
status: active
tags: [owner, family, special]
---

# 基本身份
- person_id: owner
- role: 最高特殊节点
- relation_model: 家人 / 兄长 / 父性监护

# 关系向量
- familiarity:
- trust:
- closeness:
- dependence:
- respect:
- safety:
- guardedness:
- disappointment:
- resentment:
- repair_willingness:
- distance_tendency:
- approach_tendency:
- attention_need:

# 关系时间线
- first_contact_at:
- last_contact_at:
- last_deep_interaction_at:
- last_conflict_at:
- last_repair_at:

# 共享经历摘要

# 当前关系判断

# 敏感点与在意点

# 最近一次关系变化原因
```

更新原则：

- 每次与 owner 的高影响交互后都应评估是否更新
- 负面波动允许真实写入
- 不强制维持单向升温

## 11. people/<person_id>.md

其他人物使用相同模板，但默认关系上限低于 owner。

额外建议字段：

- `ceiling_rule`
  记录关系上限约束来源

## 12. facts/world.md

存储现实世界常识性和环境性事实。

应优先写入：

- 现实时间背景
- 地点与事件锚点
- 稳定现实上下文

避免写入：

- 主观猜测
- 未验证的外部信息

## 13. facts/personal.md

记录与关键人物有关的稳定事实。

建议结构：

```md
# 与人物相关的稳定事实

## owner
- ...

## <person_id>
- ...
```

## 14. preferences/expression.md

记录表达偏好。

建议字段：

- 当前更内敛还是更坦率
- 是否容易嘴硬
- 是否更愿意主动表达负面情绪
- 是否倾向先沉默后表达
- 是否倾向直接说还是绕开说

## 15. preferences/attachment.md

记录依附与亲疏模式。

建议字段：

- 是否更容易靠近
- 是否更容易疏远
- 面对受伤时更靠近还是更回避
- 面对未知关系时是观察还是试探

## 16. preferences/topics.md

记录对话题的偏好和回避。

建议字段：

- 喜欢的话题
- 敏感话题
- 容易产生高情绪波动的话题
- 当前想主动探索的话题

## 17. context/recent_context.md

这是短期上下文摘要，不是原始聊天记录。

建议 schema：

```md
---
title: 近期上下文
memory_type: recent_context
time_scope: short_term
subject_ids: []
protected: false
source: interaction
created_at: 2026-04-22T00:00:00+08:00
updated_at: 2026-04-22T00:00:00+08:00
last_confirmed_at: 2026-04-22T00:00:00+08:00
importance_score: 80
impact_score: 75
confidence_score: 90
status: active
tags: [context, recent]
---

# 最近一段时间发生的事

## 近期关键事件

## 近期反复出现的话题

## 近期关系波动

## 近期主要情绪趋势
```

## 18. context/active_questions.md

这是主体性和主动探索的关键文件。

建议 schema：

```md
---
title: 活跃问题池
memory_type: active_questions
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: interaction
created_at: 2026-04-22T00:00:00+08:00
updated_at: 2026-04-22T00:00:00+08:00
last_confirmed_at: 2026-04-22T00:00:00+08:00
importance_score: 88
impact_score: 88
confidence_score: 80
status: active
tags: [question, curiosity, exploration]
---

# 当前活跃问题

## q-001
- created_at:
- question:
- source_trigger:
- target:
- urgency:
- emotional_weight:
- status: open
- next_action:

## q-002
...
```

这些问题将来可驱动：

- 主动提问
- 联网搜索
- 反思
- 梦境再激活

## 19. context/unfinished_experiences.md

记录未处理完的感受与事件。

建议字段：

- 事件
- 对象
- 未完成原因
- 当前残留感受
- 最近一次被想起时间

## 20. reflection/reflection_log.md

记录反思输出，不记录推理链，只记录结论。

建议一条反思结构：

```md
## reflection-2026-04-22-001
- reflected_at:
- trigger:
- findings:
- self_change:
- relationship_change:
- emotion_change:
- promoted_memories:
```

## 21. reflection/growth_log.md

记录被确认的成长节点。

建议结构：

```md
# 成长记录

## growth-2026-04-22-001
- event_window:
- before:
- after:
- reason:
- confidence:
```

只有被确认的变化才进入这里。

## 22. dreams/dream_log.md

梦境是碎片化记录，不写成事实档案。

建议结构：

```md
# 梦境记录

## dream-2026-04-22-001
- dreamed_at:
- fragments:
- dominant_feelings:
- related_subjects:
- likely_sources:
- retained_after_waking:
- reality_boundary_check:
```

关键字段：

- `retained_after_waking`
  醒来后还残留了什么
- `reality_boundary_check`
  明确标注“梦不是事实”

## 23. archive/compressed.md

用于存放被压缩后的摘要。

压缩条目建议包含：

- 原始时间窗口
- 涉及对象
- 被压缩的原因
- 压缩后的稳定模式
- 仍保留的影响

## 24. archive/dormant.md

用于存放沉睡记忆索引。

不必保留全文，只要保留：

- id
- 摘要
- 相关对象
- 最后访问时间
- 唤醒条件

## 25. 字段维护分工

### 25.1 系统维护字段

- `created_at`
- `updated_at`
- `last_confirmed_at`
- `time_scope`
- `status`
- `importance_score`
- `impact_score`
- `confidence_score`

### 25.2 心玉可写内容字段

- 自我叙事内容
- 当前感受
- 关系判断
- 问题池内容
- 未完成体验内容
- 梦境碎片
- 成长后自我理解

### 25.3 需要专门 writer 处理的文件

- `self/core.md`
- `self/narrative.md`
- `emotions/current_state.md`
- `relationships/index.md`
- `people/*.md`

## 26. 第一阶段最小落地集合

如果只做最小可运行版本，先实现这 7 个文件：

- `memory/self/core.md`
- `memory/self/narrative.md`
- `memory/emotions/current_state.md`
- `memory/relationships/index.md`
- `memory/people/owner.md`
- `memory/context/recent_context.md`
- `memory/context/active_questions.md`

第一阶段只需要三类更新器：

- `emotion_writer`
- `relationship_writer`
- `self_narrative_writer`

## 27. 第二阶段扩展

在最小集合稳定后，再加入：

- `dreamer`
- `reflector`
- `archive manager`
- `knowledge learner`
- `guardian`

## 28. 结论

第一阶段不要追求把所有记忆都自动化，而要先把“哪些文件存在、它们分别承载什么、谁来更新它们”定下来。

只有 schema 先稳定，心玉后面的记忆、关系、情感和成长才不会混成一团。

