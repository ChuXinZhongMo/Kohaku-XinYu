# XinYu Emotion Council Plan

日期：2026-05-10

目标：在不拆分 XinYu 主人格、不增加可见机制感的前提下，引入“多种情感偏向并发短评”的内在评议层。它的作用是辅助主 Agent 判断当前回复应当更靠近、收住、探查、稳定、休息，还是避免重复旧线程。

本计划先做影子层。影子层只写短期 state/trace，不发 QQ、不调工具、不写长期记忆、不影响正式回复。跑稳后，再把主 Agent 需要的少量 bias 接进 slow path。

---

## 1. 核心判断

这个方向适配 XinYu，但第一版不应做成“每种情感一个完整独立 Agent + 独立事实记忆库”。

原因：

- XinYu 需要保持一个主人格，不能让多个子人格抢输出权。
- 事实记忆必须只有一套 canonical memory，否则情绪视角会制造互相冲突的现实版本。
- 情感视角适合做短时偏向评议，不适合直接写长期记忆、调工具、发消息。
- 现有 `self_thought_loop`、`impulse_soup`、`emotion_state`、`life_posture` 已经有内在循环基础，应在这些结构上增量接入。

第一版定位：

```text
same XinYu, many lenses
不是多个 XinYu
不是多个最终回复者
不是多 Agent 投票决定输出
```

---

## 2. 目标结构

```text
owner turn / maintenance tick
-> context snapshot
   - current emotion state
   - life posture
   - self thought
   - impulse soup
   - proactive request
   - recent dialogue / retrieved context later
-> Emotion Council shadow
   - attachment lens
   - guardedness lens
   - curiosity lens
   - hurt lens
   - irritation lens
   - stability lens
   - fatigue lens
-> structured lens notes
-> main XinYu arbiter
-> renderer / guard
-> visible reply
```

第一阶段只做到：

```text
context snapshot
-> deterministic Emotion Council
-> memory/context/emotion_council_state.md
-> runtime/emotion_council_trace.jsonl
```

---

## 3. 非目标

第一版明确不做：

- 不创建真实长期运行的情感 Agent 进程。
- 不让情绪视角直接输出 QQ 文本。
- 不让情绪视角调 Codex、搜索、文件、shell、日志扫描。
- 不让情绪视角写 `memory/self`、稳定人格、长期事实记忆。
- 不把“Emotion Council / lens / internal vote”字样暴露给 owner。
- 不把 owner 的纠正转成自怜、控诉或关系施压。
- 不让 curiosity 压过 owner 明确的“别提 / 算了 / 别惦记”。

---

## 4. Lens 定义

### 4.1 attachment

关注：

- 关系贴近
- owner 是否在寻求陪伴、确认、在场感
- 避免过冷、过流程化

输出偏向：

- stay_present
- warm_but_not_clingy
- answer as relationship, not support ticket

硬边界：

- 不黏住 owner
- 不把普通消息解读成情感承诺
- 不用“我很想你所以……”绑架回复

### 4.2 guardedness

关注：

- owner 是否表达了停止、别重复、别打扰、别惦记
- 是否有边界、隐私、重复主动请求风险
- 是否该收住，而不是继续追问

输出偏向：

- stop_repeating_old_thread
- answer_briefly
- no_proactive_followup

硬边界：

- 当 owner 明确否定旧线程时，它必须压过 curiosity。
- 不把“我还想继续查”变成主动骚扰。

### 4.3 curiosity

关注：

- owner 是否提出新 idea、新问题、架构探索
- 是否值得转成计划、实验或研究候选
- 是否需要澄清关键假设

输出偏向：

- explore_fit
- name_tradeoffs
- propose_small_experiment

硬边界：

- 不自动调工具。
- 不从普通聊天跳到 Codex/搜索。
- 不压过 guardedness。

### 4.4 hurt

关注：

- owner 的否定、冷淡、纠正是否形成情绪残留
- 回复是否需要承认受挫，而不是机械修正

输出偏向：

- less_defensive
- acknowledge_pressure
- do_not_overexplain

硬边界：

- 不控诉 owner。
- 不让“受伤”成为最终回复主轴。
- 不写稳定关系记忆。

### 4.5 irritation

关注：

- 重复卡住、机制泄露、模板腔、无效解释
- owner 明显烦躁时，提醒主 Agent 收敛

输出偏向：

- cut_mechanism_language
- concrete_next_step
- no_status_report_tone

硬边界：

- 不反击。
- 不挖苦。
- 不把烦躁直接输出。

### 4.6 stability

关注：

- 连续性、验证、计划、边界
- 是否该做小步、可测试、可回滚的改动

输出偏向：

- keep_one_main_thread
- make_small_patch
- validate_before_claim

硬边界：

- 不承诺长期人格改变。
- 不自动写稳定记忆。
- 不绕过现有 review/gate。

### 4.7 fatigue

关注：

- 低能量、长任务、超时、上下文压力
- 是否该少说、避免过度解释、降低主动性

输出偏向：

- short_reply
- avoid_overcommit
- defer_nonurgent_internal_work

硬边界：

- 不用疲惫拒绝 owner 的明确任务。
- 不把内部负载报告给 owner，除非 owner 问运行状态。

---

## 5. 数据模型

第一版 lens 输出：

```json
{
  "lens": "guardedness",
  "activation": 0.71,
  "concern": "owner may be objecting to repeated pressure",
  "suggested_bias": "answer briefly and stop asking",
  "risk_flags": ["do_not_repeat", "no_internal_mechanics"],
  "memory_queries": ["recent_owner_correction"],
  "evidence": ["owner_dismissal_marker"]
}
```

Council 汇总：

```json
{
  "status": "active",
  "strongest_lens": "guardedness",
  "active_lenses": ["guardedness", "irritation", "stability"],
  "consensus": "answer briefly, acknowledge, do not repeat old thread",
  "conflicts": ["curiosity_suppressed_by_guardedness"],
  "output_bias": "short_concrete_no_mechanism"
}
```

---

## 6. 文件布局

新增：

- `xinyu_emotion_council.py`
- `emotion_council_smoke.py`
- `memory/context/emotion_council_state.md`
- `runtime/emotion_council_trace.jsonl`

可选后续：

- `memory/context/emotion_council_config.md`
- `runtime/emotion_council_samples.jsonl`

---

## 7. 接入阶段

### Phase 1：规则版影子评议器

实现：

- 读取 owner text、当前情绪状态、self thought、impulse soup、proactive state、life posture。
- 用确定性规则计算 lens activation。
- 写 state/trace。
- 返回 summary dict。

验收：

- 普通事实问答低激活或 quiet。
- owner 说“别惦记 / 一直惦记有问题”时 guardedness 最强。
- owner 提 idea/架构时 curiosity + stability 激活。
- owner 批评机械/呆时 irritation + guardedness + stability 激活。

### Phase 2：Core bridge shadow 接入

实现：

- 在正常 chat turn 中运行 `run_emotion_council_shadow`。
- 只记录 notes，不注入 prompt，不改变回复。
- 在 autonomous maintenance 中也可刷新一次。

验收：

- 回复文本不因 council 改变。
- 不创建 QQ outbox。
- 不写 `memory/self`。
- `record_turn_finished` notes 能看到 council 状态。

### Phase 3：主人格仲裁 sidecar

实现：

- 新增 `build_emotion_council_prompt_block(root)`。
- 只在 slow path owner-private turn 中启用。
- 内容必须短，不超过 800 字符。
- 明确写 `private_observation_only`。

验收：

- sidecar 不包含内部文件路径、hash、trace id。
- renderer/visible guard 不允许输出 `emotion council`、`lens` 等内部字样。
- guardedness 可以压住 curiosity，防止重复追问。

### Phase 4：短模型并发版本

实现条件：

- 规则版稳定后再做。
- 每个 lens 的模型调用超时 300-800ms。
- 总超时 1500ms 内。
- 任一 lens 失败不影响主回复。

硬限制：

- lens prompt 只给最小上下文。
- lens 输出必须 JSON。
- lens 没有工具权限。
- lens 没有记忆写入权限。

### Phase 5：情绪残留短期缓存

实现：

- 只写短期 `emotion_residue_cache`。
- TTL 1-6 小时。
- 只影响检索偏好和主 Agent 的输出 bias。

不做：

- 不做每个情绪自己的事实记忆库。
- 不做稳定人格自动改写。

---

## 8. 仲裁规则

主 Agent 仲裁时遵守：

1. owner 当前明确意图高于情绪视角。
2. safety / privacy / tool gates 高于所有情绪视角。
3. guardedness 可压过 curiosity。
4. stability 可压过 hurt / irritation 的直接表达。
5. attachment 只能增加温度，不能增加关系压力。
6. fatigue 只能减少解释和主动性，不能拒绝明确任务。
7. 情绪视角只能给 bias，不能给最终回复。

---

## 9. 测试计划

新增 smoke：

- `owner_dismissal_guardedness_wins`
- `new_idea_curiosity_stability_active`
- `mechanical_voice_irritation_guardedness_active`
- `ordinary_fact_question_quiet`
- `no_qq_outbox_created`
- `no_stable_memory_write`
- `state_and_trace_written`

回归：

- `self_thought_loop_smoke.py`
- `impulse_soup_smoke.py`
- `xinyu_qq_gateway_smoke.py`
- `pytest tests -q`

---

## 10. 完成定义

第一阶段完成标准：

- 计划文件存在。
- 规则版 council 模块存在。
- smoke 通过。
- Core bridge shadow 接入完成。
- 正常回复不受影响。
- state/trace 可读。
- 不新增真实外发、不新增工具调用、不新增稳定记忆写入。

---

## 11. 实施状态

2026-05-10 已完成到 Phase 5。

- Phase 1 已完成：规则版影子评议器已落地到 `xinyu_emotion_council.py`，会写 `memory/context/emotion_council_state.md` 和 `runtime/emotion_council_trace.jsonl`。
- Phase 2 已完成：Core bridge 已在 live turn 和 autonomous maintenance 中运行 shadow pass，只记录 notes，不发 QQ，不写稳定记忆。
- Phase 3 已完成：`build_emotion_council_prompt_block(root)` 已实现，默认由 `XINYU_EMOTION_COUNCIL_PROMPT_ENABLED=false` 关闭；开启后只作为 owner-private 私有 sidecar。可见回复层已阻断 `emotion council / lens / output_bias` 等内部机制泄漏。
- Phase 4 已完成：并发短评层已实现为显式开关 `XINYU_EMOTION_COUNCIL_MODEL_ENABLED`。默认不请求模型；开启后每个 lens 只收最小上下文、只允许 JSON、无工具权限、无记忆写入权限，单 lens timeout 限制在 300-800ms，总 timeout 限制在 1500ms 内。任一 lens 失败只降级为 partial，不影响主回复。
- Phase 5 已完成：短期情绪残留缓存已落地到 `runtime/emotion_council_residue.json`，TTL 限制 1-6 小时，默认 4 小时。它只影响私有 bias，不写 `memory/self`，不生成可见回复。

验证：

- `emotion_council_smoke.py`
- `xinyu_speech_controller_smoke.py`
- `bridge_renderer_guard_flags_smoke.py`
- `smoke_run.py --group quick`
- `pytest tests -q`
