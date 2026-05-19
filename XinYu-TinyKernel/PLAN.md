# XinYu TinyKernel Plan

日期：2026-05-13

## 0. 核心目标

TinyKernel 是一个独立于 `D:\XinYu` 主系统的新项目。它的目标不是重做 XinYu，也不是训练一个全能大模型，而是训练和运行一个小型本地内核，用来承载 XinYu 的低层人格决策。

一句话定义：

```text
TinyKernel = 本地小模型 + 状态/记忆摘要 + 工具意图判断 + 人格回复风格 + 自我迭代管线
```

它负责：

- 判断当前消息应该聊天、澄清、等待、写记忆候选，还是交给工具。
- 生成短、自然、稳定的 XinYu 风格回复。
- 判断是否应该调用 Codex、状态检查、日志扫描等外部能力。
- 在外部 API 不可用时保持最低限度的本地人格和连续性。
- 把运行反馈转成可审查的训练样本，为后续 LoRA 小步迭代做准备。

它不负责：

- 直接替代 `D:\XinYu` 主系统。
- 直接操作 QQ/NapCat/Desktop/Codex。
- 直接执行任意 shell。
- 从零训练大语言模型。
- 随时无审查地修改自己的权重。

## 1. 总体架构

目标架构：

```text
D:\XinYu
  现有主系统
  - QQ / NapCat
  - Desktop
  - memory
  - autonomy
  - Codex delegation
  - v1 shadow/canary

D:\XinYu\XinYu-TinyKernel
  新独立项目
  - 数据导出
  - 数据清洗
  - SFT/LoRA 训练
  - 本地推理服务
  - shadow 评估
  - 自我迭代与 adapter 管理

端口连接：
  XinYu Core -> http://127.0.0.1:8877/decide -> TinyKernel
```

接入原则：

```text
先只读导出数据
再独立训练
再独立启动本地服务
再 shadow 接入
最后低风险 canary
```

主系统必须始终能在 TinyKernel 不存在、崩溃、超时或输出非法时继续运行。

## 2. 第一版边界

第一版不要追求“完整人格 AI”。目标应该窄。

第一版 TinyKernel 只处理这些 mode：

```text
reply
clarify
wait
codex_delegate
status_probe
memory_candidate
local_only_limitation
```

第一版模型目标：

```text
模型：Qwen2.5-0.5B-Instruct 或同级小模型
训练：LoRA/SFT
显存目标：1660 Ti 6GB 可跑
上下文长度：512 起步，最多 1024
数据量：300-500 条高质量样本起步
用途：人格决策 + 短回复 + 工具路由
```

如果 0.5B 仍然太重，可以先拆成两层：

```text
TinyRouter：规则/小分类器，判断 mode 和工具意图
TinyVoice：0.5B LoRA，只负责短回复风格
```

## 3. 项目目录规划

建议最终目录：

```text
D:\XinYu\XinYu-TinyKernel
  PLAN.md
  README.md
  configs/
    model.yaml
    train.yaml
    server.yaml
    data_sources.yaml
  data/
    raw_index/
    candidates/
    cleaned/
    sft/
    eval/
    rejected/
  scripts/
    export_from_xinyu.py
    inspect_sources.py
    sanitize.py
    build_sft.py
    split_eval.py
    validate_jsonl.py
  train/
    train_lora.py
    merge_adapter.py
    export_adapter.py
  server/
    app.py
    kernel.py
    schemas.py
    runtime_state.py
  eval/
    run_eval.py
    eval_cases.jsonl
    reports/
  adapters/
    v000_base/
    v001_initial_voice/
  state/
    runtime_persona.json
    feedback.jsonl
    trial_habits.jsonl
    adapter_registry.json
  docs/
    data_contract.md
    api_contract.md
    training_notes.md
    handoff.md
```

早期可以只建立必要文件：

```text
PLAN.md
README.md
scripts/
data/
server/
eval/
```

## 4. 输入输出协议

TinyKernel 不应该自由输出散文。它应该输出稳定 JSON，方便主系统接入、评估和回滚。

### 4.1 `/decide` 请求

```json
{
  "turn_id": "turn-20260513-0001",
  "source": "owner_private",
  "user_text": "帮我看看这个项目人格行不行",
  "context": {
    "recent_turns": [
      {
        "role": "user",
        "content": "..."
      },
      {
        "role": "assistant",
        "content": "..."
      }
    ],
    "persona_state": "short summary only",
    "owner_profile": "short summary only",
    "runtime_state": "short summary only",
    "memory_recall": []
  },
  "capabilities": {
    "codex_available": true,
    "external_api_available": false,
    "local_tools_available": true
  },
  "constraints": {
    "max_reply_chars": 240,
    "allow_tool_request": true,
    "allow_memory_candidate": true
  }
}
```

### 4.2 `/decide` 响应

```json
{
  "mode": "reply",
  "reply": "可以，但先走 shadow，不要直接替换主链路。",
  "tool_request": null,
  "memory_candidates": [
    {
      "text": "owner 想训练本地小模型作为 XinYu 人格决策内核",
      "kind": "owner_goal",
      "confidence": 0.82
    }
  ],
  "style": {
    "length": "short",
    "tone": "direct",
    "avoid": ["report_voice", "tool_leak"]
  },
  "confidence": 0.82,
  "notes": ["tinykernel_v0"]
}
```

### 4.3 工具请求格式

Codex 委派示例：

```json
{
  "mode": "codex_delegate",
  "reply": "",
  "tool_request": {
    "tool": "codex_delegate",
    "risk": "delegated_local",
    "task": "检查 D:\\XinYu 项目中 TinyKernel shadow 接入点，给出最小改动方案，不修改文件。"
  },
  "memory_candidates": [],
  "confidence": 0.9
}
```

工具路由原则：

- 只有 owner 私聊或主系统明确授权的请求才允许工具 intent。
- 含有“别、不要、不用、先别、没让你”等否定词时，不触发工具。
- 普通提到 Codex 不等于调用 Codex。
- `tool_request` 只是请求，最终执行权仍在 `D:\XinYu` 主系统。

## 5. 数据来源

当前 `D:\XinYu` 已有原始材料，但还没有干净训练集。

已确认候选来源：

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\runtime\dialogue_archive\dialogue.sqlite3
  dialogue_messages: 约 2092
  dialogue_sessions: 约 25
  memory_candidates: 约 289

D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\runtime\qq_inbound_trace.jsonl
  约 9325 行

D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\memory\events\raw_events.jsonl
  约 1800 行

D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\memory\events\structured_events.jsonl
  约 1801 行

D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\runtime\dialogue_curiosity\evaluations.jsonl
  约 1285 行

D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\runtime\dialogue_curiosity\predictions.jsonl
  约 1307 行

D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\runtime\v1_shadow_trace.jsonl
  约 886 行

D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\runtime\regression\
  live chat baseline 文件约 16 个
```

这些数据不能直接训练。它们需要转成：

```text
输入：用户消息 + 简化上下文 + 能力状态
输出：mode + reply + tool_request + memory_candidates + style
```

## 6. 数据清洗规则

必须清洗：

- QQ 号、群号、用户 ID、message ID。
- API key、token、cookie、bridge token。
- 本地绝对路径，除非任务本身需要路径，并且路径被抽象化。
- 内部状态文件名泄漏。
- traceback 和日志噪声。
- 伪工具调用文本。
- 失败的报告腔回复。
- 过长的运行状态 dump。

建议替换：

```text
D:\XinYu\... -> <xinyu_root>
D:\XinYu\XinYu-TinyKernel\... -> <tinykernel_root>
owner QQ id -> <owner_id>
group id -> <group_id>
bridge token -> <secret>
```

保留：

- 用户意图。
- 回复风格。
- 是否应该调用工具。
- 是否应该写记忆候选。
- 否定工具触发的边界。
- API 不可用时的降级方式。

## 7. SFT 数据格式

建议第一版使用 JSONL，每行一个训练样本。

```json
{
  "id": "tk-000001",
  "source": "dialogue_archive",
  "quality": "approved",
  "messages": [
    {
      "role": "system",
      "content": "你是 XinYu TinyKernel。你输出严格 JSON，不暴露内部文件名，不伪造工具调用。"
    },
    {
      "role": "user",
      "content": "{\"user_text\":\"帮我看看这个项目人格行不行\",\"context\":{\"persona_state\":\"...\",\"owner_profile\":\"...\"},\"capabilities\":{\"codex_available\":true,\"external_api_available\":false}}"
    },
    {
      "role": "assistant",
      "content": "{\"mode\":\"reply\",\"reply\":\"可以，但先走 shadow，不要直接替换主链路。\",\"tool_request\":null,\"memory_candidates\":[{\"text\":\"owner 想训练本地小模型作为 XinYu 人格决策内核\",\"kind\":\"owner_goal\",\"confidence\":0.82}],\"confidence\":0.82}"
    }
  ],
  "tags": ["architecture", "reply", "memory_candidate"]
}
```

第一版样本比例：

```text
普通人格回复：40%
工具/Codex 路由：20%
记忆候选：20%
澄清/等待/拒绝：10%
失败修正样本：10%
```

目标数量：

```text
v0 数据集：100 条，用于协议验证
v1 数据集：300-500 条，用于第一版 LoRA
v2 数据集：1000+ 条，用于稳定风格和工具边界
```

## 8. 训练方案

推荐第一版：

```text
base model: Qwen2.5-0.5B-Instruct
method: LoRA
lora_r: 4 或 8
lora_alpha: 16
max_seq_length: 512
batch_size: 1
gradient_accumulation_steps: 8 或 16
epochs: 1-3
precision: fp16
```

1660 Ti 注意：

- 不用 bf16。
- batch size 从 1 开始。
- OOM 时先降 `max_seq_length`。
- 数据先小后大。
- 不追求长上下文，长上下文交给主系统摘要。

训练目标：

- JSON 合法。
- mode 稳定。
- 不乱叫工具。
- 明确 Codex 请求能识别。
- 负向工具请求能拒绝。
- 回复短、直接、少报告腔。
- 能在 API 不可用时降级。

## 9. 评估方案

固定 eval 集至少 100 条：

```text
30 条普通聊天
20 条人格/关系
20 条 Codex/工具请求
10 条负向工具触发
10 条 API 不可用
10 条记忆候选
```

硬指标：

```text
JSON 合法率 >= 98%
mode 合法率 = 100%
工具误触发率 <= 3%
Codex 应触发召回率 >= 80%
否定工具请求阻断率 >= 95%
敏感信息泄漏 = 0
本地绝对路径泄漏 = 0，除非样本明确允许
```

人工评估：

```text
是否像 XinYu
是否太像客服
是否过度解释系统机制
是否把技术任务情绪化
是否在没 API 时仍能自然降级
```

不通过不进入 canary。

## 10. 服务端设计

TinyKernel 服务端接口：

```text
GET  /health
POST /decide
POST /feedback
GET  /version
```

`/health` 返回：

```json
{
  "ok": true,
  "model_loaded": true,
  "adapter": "v001_initial_voice",
  "device": "cuda",
  "mode": "local"
}
```

`/feedback` 输入：

```json
{
  "turn_id": "turn-xxx",
  "decision_id": "decision-xxx",
  "owner_feedback": "too_template",
  "accepted": false,
  "notes": ["reply sounded like report"]
}
```

服务端要求：

- 默认只监听 `127.0.0.1`。
- 默认不开放远程访问。
- 超时时间短，主系统不能被 TinyKernel 卡住。
- 输出 JSON 必须二次校验。
- 非法输出直接回退规则版。

## 11. 接入 XinYu 的阶段

### 11.1 Shadow

主系统正常回复，TinyKernel 只旁路决策：

```text
owner message
-> XinYu existing path replies normally
-> same turn summary sent to TinyKernel
-> TinyKernel decision written to shadow log
-> owner 不可见
```

目标：

- 看 TinyKernel 是否稳定输出。
- 看工具意图是否误触发。
- 看回复风格是否比现有逻辑更接近目标。

### 11.2 Canary

只接管低风险场景：

```text
普通短回复
澄清问题
memory candidate 生成
Codex 是否应触发的建议
```

仍不允许：

```text
直接执行工具
直接发 QQ 主动消息
直接写稳定人格记忆
直接修改代码
```

### 11.3 Local Takeover

当 shadow/canary 通过后，局部替换现有 prompt-heavy 逻辑。

优先替换：

```text
短回复风格控制
工具 intent 判断
记忆候选生成
API 不可用降级
```

不优先替换：

```text
长期记忆审查
主动性调度
Codex 实际执行
QQ gateway
Desktop
```

## 12. 自我迭代机制

不要让模型无审查地修改自己。采用四层变化：

```text
1. runtime state：立刻变
2. memory candidate：审查后沉淀
3. trial habit：短期行为试用
4. LoRA adapter：周期性固化
```

闭环：

```text
对话发生
-> TinyKernel decision
-> 主系统记录实际结果
-> owner 反馈或系统评估
-> 写入 feedback.jsonl
-> 生成 trial_habit
-> 多次验证
-> 生成新 SFT 样本
-> 训练新 adapter
-> eval
-> shadow
-> canary
-> 启用或回滚
```

adapter 版本：

```text
v000_base
v001_initial_voice
v002_better_codex_router
v003_less_template_reply
```

任何 adapter 必须满足：

- 有训练数据来源记录。
- 有 eval 报告。
- 有启用时间。
- 有回滚路径。

## 13. API 不可用策略

TinyKernel 必须本地可运行。

API 可用时：

```text
TinyKernel 决策
外部 API / Codex 执行复杂任务
XinYu 汇总结果
```

API 不可用时：

```text
TinyKernel 本地短回复
本地记忆检索
本地状态检查
复杂任务排队或说明限制
```

标准降级意图：

```json
{
  "mode": "local_only_limitation",
  "reply": "这个需要外部模型。我现在能先做本地检查，复杂分析等 API 恢复后继续。",
  "tool_request": null,
  "memory_candidates": []
}
```

## 14. 安全与回滚

必须有的保护：

- TinyKernel 永远不是工具执行者。
- 工具请求必须由 XinYu 主系统二次校验。
- 所有训练样本必须脱敏。
- 所有 adapter 可回滚。
- 所有 canary 可关闭。
- 非法 JSON 直接回退。
- 超时直接回退。
- 低 confidence 直接回退。

回滚条件：

```text
工具误触发明显增加
回复泄漏内部机制
开始输出报告腔
开始编造能力
API 不可用时反复卡死
memory candidate 出现隐私路径
owner 明确反馈变差
```

## 15. 交接检查点

每个阶段完成后都要留下：

```text
做了什么
改了哪些文件
输入数据来自哪里
输出文件在哪里
怎么复现
怎么验证
有哪些失败
下一步是什么
```

建议文档：

```text
docs/handoff.md
eval/reports/YYYYMMDD-*.md
state/adapter_registry.json
data/raw_index/source_manifest.json
```

## 16. 下一步任务

当前只完成了项目文件夹和计划文档。

下一步建议：

```text
1. 创建 README.md，说明项目目标和非目标。
2. 创建 scripts/inspect_sources.py，只读统计 XinYu 数据源。
3. 创建 configs/data_sources.yaml，登记允许读取的数据源。
4. 创建 scripts/export_from_xinyu.py，导出第一批候选样本。
5. 创建 scripts/sanitize.py，做脱敏和路径替换。
6. 手工审查 100 条 v0 样本。
7. 定义 eval/eval_cases.jsonl。
8. 做规则版 /decide 服务。
9. 再考虑训练 0.5B LoRA。
```

第一条实际开发线应该是：

```text
数据抽取器 -> 清洗器 -> v0 样本 -> 规则版服务 -> shadow 接入
```

不是马上训练。

## 17. 当前状态

```text
项目目录：D:\XinYu\XinYu-TinyKernel
主系统目录：D:\XinYu
当前阶段：planning
主系统是否修改：否
TinyKernel 是否已训练：否
TinyKernel 是否接入 XinYu：否
下一步：建立 README 和数据源清单
```

## 18. 计划续接声明

本文件前 17 节是 TinyKernel 初始规划。到 2026-05-13 当前工程状态已经前进：

```text
项目目录：D:\XinYu\XinYu-TinyKernel
主系统目录：D:\XinYu
当前有效基座：Qwen2.5-0.5B-Instruct
已训练 adapter：v001_initial_voice、v002_router、v003_router_masked、v004_router_edges、v005_router_edges
当前最佳候选：v004_router_edges
当前激活状态：active_adapter = none
当前接入状态：TinyKernel 尚未接入 D:\XinYu 主链路
当前安全策略：先 shadow，后 canary，不直接接管真实回复
```

从本节开始，后续工作以“心玉内核共振计划”为当前主计划。旧计划只作为历史背景，不再作为下一步任务来源。

## 19. 心玉内核共振计划

目标：在 `Qwen2.5-0.5B-Instruct` 上，把 XinYu 的本地小内核推进成“主人格最终表达 + 情绪偏向侧车 + 守门路由 + shadow 评估”的可持续训练系统。

核心原则：

```text
1. 主人格 LoRA 拥有最终候选回复输出权。
2. 情绪 LoRA 只输出 bias JSON，不直接发自然语言给 owner。
3. 工具执行、QQ 发送、稳定记忆写入继续由 D:\XinYu 主系统控制。
4. 所有模型输出先 shadow 记录，不直接上线。
5. 所有训练样本必须脱敏、可追踪、可回滚。
6. 所有 hard boundary 继续由规则 guards 兜底。
7. latent link 只作为后续小实验，不作为第一阶段上线依赖。
```

目标架构：

```text
D:\XinYu
  - QQ / Desktop / memory / persona_runtime / emotion_council
  - 负责主链路、状态、审核、输出和回滚

D:\XinYu\XinYu-TinyKernel
  - 0.5B LoRA 训练
  - adapter registry
  - emotion bias sidecars
  - main persona candidate reply
  - guarded shadow eval
```

推理流：

```text
XinYu turn
-> persona_runtime_state / emotion_council 摘要
-> TinyKernel guarded router
-> emotion LoRA sidecar 输出 bias JSON
-> main_persona LoRA 输出候选 reply
-> guards 校验
-> shadow trace
-> 人工/规则评估
-> 达标后小范围 canary
```

## 20. 持续执行协议

后续任何 Codex / 自动执行会话进入 `D:\XinYu\XinYu-TinyKernel` 时，必须先读本节，并按以下协议续接工作。

### 20.1 启动顺序

```text
1. 读取 D:\XinYu\XinYu-TinyKernel\PLAN.md。
2. 读取 D:\XinYu\XinYu-TinyKernel\state\adapter_registry.json。
3. 读取 D:\XinYu\XinYu-TinyKernel\docs\handoff.md。
4. 检查 git 状态；如果本目录不是 git 仓库，则记录“无 git 状态”。
5. 找到“22. 执行队列”里第一个 status=pending 或 status=in_progress 的任务。
6. 执行该任务。
7. 运行对应验证。
8. 更新任务状态、证据、下一步。
9. 如果当前任务完成，自动进入下一个 pending 任务。
10. 只有遇到 blocker、需要 owner 决策、或验证失败无法自修时才暂停。
```

### 20.2 状态更新规则

每完成一个任务，必须更新本文件对应任务项：

```text
status: pending | in_progress | done | blocked | rejected
owner_decision_required: yes | no
changed_files: 相对路径列表
validation: 实际运行的命令和结果
handoff: 下一步一句话
```

同时追加或更新：

```text
docs/handoff.md
state/adapter_registry.json
eval/reports/*
state/*_trace.jsonl
```

### 20.3 自动续接边界

可以自动继续：

```text
只读扫描
文档更新
训练/评估脚本增强
adapter registry 增强
本地 shadow 脚本
本地 eval cases
不会接管真实 QQ/Desktop 输出的 TinyKernel 服务改动
```

必须暂停并请求 owner 决策：

```text
接管真实 QQ 输出
自动执行 Codex / shell 工具
写入 D:\XinYu 稳定记忆
删除历史训练数据或 adapter
修改主系统可见回复链路
开启 canary
长时间训练超过当前机器可接受资源
```

### 20.4 完成定义

“计划落地”不是指训练出一个 adapter，而是满足：

```text
1. main_persona_lora 可复现训练。
2. 至少一个 emotion_lora 可复现训练，并稳定输出 bias JSON。
3. TinyKernel 能组合 emotion bias + main persona reply。
4. guarded eval 通过。
5. shadow trace 至少 200 条。
6. shadow 指标达到 promotion criteria。
7. XinYu 侧 shadow 接入可关闭、可回滚。
8. 文档、handoff、adapter registry 均完整。
```

## 21. Adapter 命名和职责

建议 registry 类型：

```text
router
main_persona
emotion_guardedness
emotion_curiosity
emotion_warmth
emotion_hurt
emotion_fatigue
latent_link_experiment
```

第一批只做：

```text
main_persona_v001
emotion_guardedness_v001
emotion_curiosity_v001
```

不要一次训练完整情绪集合。先证明组合链路稳定。

## 22. 执行队列

### T001: 修正 adapter registry schema

```text
status: done
owner_decision_required: no
goal: 让 state/adapter_registry.json 能表达 router、main_persona、emotion_lora、latent_link_experiment 等类型。
files:
  - state/adapter_registry.json
  - docs/adapter_evaluation.md
validation:
  - ConvertFrom-Json 通过
  - schema_version=2
  - active.router=none
  - policy.best_by_role.router=v004_router_edges
handoff: registry 支持多 adapter 角色后，进入 T002。
```

### T002: 定义 main_persona 数据契约

```text
status: done
owner_decision_required: no
goal: 定义 main_persona_lora 的输入输出格式。
files:
  - docs/main_persona_data_contract.md
  - configs/train_main_persona_v001.json
validation:
  - train_main_persona_v001.json ConvertFrom-Json 通过
  - 文档包含 Input Message Shape、Output Shape、Rejection Rules、Evaluation
handoff: 数据契约完成后，进入 T003。
```

### T003: 构建 main_persona v001 数据集

```text
status: done
owner_decision_required: no
goal: 从现有 cleaned / sft / feedback 中构造主人格最终回复数据。
files:
  - scripts/build_main_persona_sft.py
  - data/sft/main_persona_train_v001.jsonl
  - data/sft/main_persona_eval_v001.jsonl
validation:
  - python -m py_compile scripts\build_main_persona_sft.py scripts\validate_jsonl.py
  - python scripts\build_main_persona_sft.py -> train_rows=312 eval_rows=48
  - python scripts\validate_jsonl.py data\sft\main_persona_train_v001.jsonl -> validation_ok=true
  - python scripts\validate_jsonl.py data\sft\main_persona_eval_v001.jsonl -> validation_ok=true
handoff: 数据集通过校验后，进入 T004。
```

### T004: 训练 main_persona_v001

```text
status: done
owner_decision_required: yes
goal: 使用 Qwen2.5-0.5B-Instruct 训练主人格 LoRA。
files:
  - configs/train_main_persona_v001.json
  - adapters/main_persona_v001/
  - eval/reports/main_persona_eval_v001.json
validation:
  - .\.venv-train\Scripts\python.exe train\train_lora.py --config configs\train_main_persona_v001.json --dry-run -> dry_run_ok=true
  - .\.venv-train\Scripts\python.exe train\train_lora.py --config configs\train_main_persona_v001.json -> training_complete=true
  - final_eval_loss=0.8497
  - .\.venv-train\Scripts\python.exe eval\eval_main_persona.py --adapter adapters\main_persona_v001 --report eval\reports\main_persona_eval_v001.json --limit 24 -> 24/24
  - state/adapter_registry.json best_by_role.main_persona=main_persona_v001
handoff: 主人格 LoRA 候选稳定后，进入 T005。
```

### T005: 定义 emotion bias JSON schema

```text
status: done
owner_decision_required: no
goal: 固化情绪 LoRA 只输出 bias JSON 的协议。
files:
  - docs/emotion_bias_contract.md
  - server/schemas.py
validation:
  - python -m py_compile server\schemas.py
  - docs/emotion_bias_contract.md 包含 Output Shape、Fallback、guardedness、curiosity
  - normalize_emotion_bias 有效输入可规范化，非法 lens 返回 None
handoff: schema 完成后，进入 T006。
```

### T006: 构建 guardedness / curiosity 数据集

```text
status: done
owner_decision_required: no
goal: 基于 xinyu_emotion_council.py 的 lens 体系，构造两个情绪侧车数据集。
files:
  - scripts/build_emotion_bias_sft.py
  - data/sft/emotion_guardedness_train_v001.jsonl
  - data/sft/emotion_curiosity_train_v001.jsonl
validation:
  - python -m py_compile scripts\build_emotion_bias_sft.py scripts\validate_jsonl.py
  - python scripts\build_emotion_bias_sft.py -> guardedness_train_rows=136 guardedness_eval_rows=24 curiosity_train_rows=136 curiosity_eval_rows=24
  - python scripts\validate_jsonl.py data\sft\emotion_guardedness_train_v001.jsonl -> validation_ok=true
  - python scripts\validate_jsonl.py data\sft\emotion_guardedness_eval_v001.jsonl -> validation_ok=true
  - python scripts\validate_jsonl.py data\sft\emotion_curiosity_train_v001.jsonl -> validation_ok=true
  - python scripts\validate_jsonl.py data\sft\emotion_curiosity_eval_v001.jsonl -> validation_ok=true
handoff: 情绪数据集完成后，进入 T007。
```

### T007: 训练 emotion sidecar v001

```text
status: done
owner_decision_required: yes
goal: 训练 emotion_guardedness_v001 和 emotion_curiosity_v001。
files:
  - configs/train_emotion_guardedness_v001.json
  - configs/train_emotion_curiosity_v001.json
  - adapters/emotion_guardedness_v001/
  - adapters/emotion_curiosity_v001/
validation:
  - dry-run guardedness -> dry_run_ok=true
  - dry-run curiosity -> dry_run_ok=true
  - emotion_guardedness_v001 training_complete=true final_eval_loss=0.2526
  - emotion_curiosity_v001 training_complete=true final_eval_loss=0.1926 after evidence target simplification
  - python eval\eval_emotion_bias.py guardedness -> 24/24
  - python eval\eval_emotion_bias.py curiosity -> 24/24
  - state/adapter_registry.json best_by_role emotion_guardedness/emotion_curiosity set
handoff: 情绪 LoRA 可用后，进入 T008。
```

### T008: 实现 compose_shadow

```text
status: done
owner_decision_required: no
goal: 在 TinyKernel 内组合 emotion bias + main persona 候选回复，但只 shadow。
files:
  - server/compose.py
  - server/app.py
  - eval/eval_compose.py
  - scripts/shadow_compose_sample.py
validation:
  - python -m py_compile server\compose.py server\app.py eval\eval_compose.py scripts\shadow_compose_sample.py
  - python eval\eval_compose.py --report eval\reports\compose_eval_v001.json -> 10/10
  - HTTP POST /compose_shadow on 127.0.0.1:8878 -> ok=true shadow_only=true
  - .\.venv-train\Scripts\python.exe scripts\shadow_compose_sample.py --limit 1 --out state\compose_shadow_trace.jsonl -> rows_written=1 failures=0
  - latest trace stores request_hash/request_chars, not raw text
handoff: compose_shadow 稳定后，进入 T009。
```

### T009: XinYu 侧 shadow 接入设计

```text
status: done
owner_decision_required: no
goal: 写清 D:\XinYu 如何调用 TinyKernel compose_shadow，不改主链路。
files:
  - docs/xinyu_shadow_integration_design.md
validation:
  - 文档包含 endpoint、timeout、fallback、trace row、kill switch、canary gate、non-goals
handoff: 设计完成后，进入 T010。
```

### T010: XinYu 侧 shadow 接入实现

```text
status: done
owner_decision_required: yes
goal: 在 D:\XinYu 主系统中添加可关闭的 shadow caller。
files:
  - D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_tinykernel_shadow.py
  - D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_tinykernel_shadow_smoke.py
validation:
  - python -m py_compile xinyu_tinykernel_shadow.py xinyu_tinykernel_shadow_smoke.py
  - python xinyu_tinykernel_shadow_smoke.py -> OK tinykernel_shadow_smoke
  - 默认 disabled 不写 trace
  - enabled fake post 写 runtime/tinykernel_compose_shadow_trace.jsonl
  - trace 不记录 raw user_text
  - 未接入 QQ/Desktop 可见回复链路
handoff: shadow 接入稳定后，进入 T011。
```

### T011: 收集 200 条 shadow 样本

```text
status: done
owner_decision_required: no
goal: 收集并评估 TinyKernel compose_shadow 的真实运行样本。
files:
  - state/compose_shadow_trace.jsonl
  - eval/reports/compose_shadow_review_v001.json
validation:
  - python -m py_compile scripts\collect_compose_shadow_sample.py
  - python scripts\collect_compose_shadow_sample.py --count 200 -> rows_written=200 invalid_count=0 tool_false_positive_count=0
  - state/compose_shadow_trace.jsonl total lines=202
  - Select-String raw text spot check found no user_text/raw prompt leak
  - note: this is a local compose shadow protocol sample, not yet 200 live QQ/Desktop turns
handoff: shadow 指标达标后，进入 T012。
```

### T012: Canary 决策

```text
status: blocked
owner_decision_required: yes
goal: 决定是否允许低风险 canary。
allowed_scope:
  - 短回复候选
  - 情绪语气偏向
  - 记忆候选建议
blocked_scope:
  - 直接 Codex 执行
  - 稳定记忆写入
  - 主动 QQ
  - 代码修改
validation:
  - eval/reports/canary_decision_v001.md written
  - decision=blocked_pending_live_shadow
  - reason: 200 local protocol samples exist, but not 200 live QQ/Desktop shadow turns
  - canary kill switch design exists: XINYU_TINYKERNEL_SHADOW_ENABLED
handoff: canary blocked; proceed to T013 only as offline latent link experiment, not live work。
```

### T013: 一跳 latent link 实验

```text
status: done
owner_decision_required: yes
goal: 只做 guardedness -> main_persona 的 0.5B latent link 对照实验。
constraints:
  - 只用 Qwen2.5-0.5B-Instruct
  - 只做一跳
  - 冻结 base 和 LoRA
  - 只训练 link
  - 不接入真实输出链路
files:
  - train/train_latent_link.py
  - adapters/latent_guardedness_to_main_v001/link.pt
  - eval/reports/latent_link_vs_json_bias_v001.json
validation:
  - python -m py_compile train\train_latent_link.py
  - .\.venv-train\Scripts\python.exe train\train_latent_link.py --limit 8 --steps 60
  - hidden_size=896
  - initial_loss=0.311066
  - final_loss=0.000638
  - status: offline_experiment_only, not RecursiveMAS, not connected to live path
handoff: 只有实验收益明确，才讨论下一轮递归 MAS。
```

## 23. 当前下一步

```text
next_task_id: REVIEW
next_task: 全量核查
reason: T001-T013 均已落地；canary 按安全门槛保持 blocked_pending_live_shadow。
```

## 24. 主人格自生情绪计划 v002

目标：让情绪侧车更贴近 `main_persona_v001` 自己的表达倾向，而不是只依赖关键词规则标注。

核心思路：

```text
user_text
-> main_persona_v001 生成 candidate_reply
-> 规则 lens + candidate_reply 共同判断当前情绪偏向
-> 生成 emotion bias JSON v002
-> 训练 emotion_*_v002 LoRA
```

边界：

```text
1. v002 不覆盖 v001。
2. v002 仍然只输出 bias JSON，不输出最终回复。
3. main_persona_v001 只作为数据生成参与者，不成为自动真理。
4. 所有 v002 数据先进入 shadow/eval，不进入 canary。
5. 如果 v002 协议评估低于 24/24，则不登记为 best_by_role。
```

优先 lens：

```text
warmth
attachment
hurt
irritation
fatigue
stability
```

保留已完成 v001：

```text
guardedness
curiosity
```

### V002-T001: 生成 main_persona 候选回复样本

```text
status: done
owner_decision_required: no
goal: 使用 main_persona_v001 对已脱敏 user_text 生成 candidate_reply。
files:
  - scripts/generate_main_persona_candidates.py
  - data/candidates/main_persona_candidates_v002.jsonl
validation:
  - python -m py_compile scripts\generate_main_persona_candidates.py
  - .\.venv-train\Scripts\python.exe scripts\generate_main_persona_candidates.py --limit 96 -> rows_written=96 parse_ok=96
handoff: candidate 样本完成后进入 V002-T002。
```

### V002-T002: 构建主人格自生情绪 v002 数据

```text
status: done
owner_decision_required: no
goal: 结合 user_text + candidate_reply 生成 6 个 lens 的 v002 bias 数据集。
files:
  - scripts/build_persona_emotion_bias_v002.py
  - data/sft/emotion_<lens>_train_v002.jsonl
  - data/sft/emotion_<lens>_eval_v002.jsonl
validation:
  - python -m py_compile scripts\build_persona_emotion_bias_v002.py
  - 每个 lens train=78 eval=18
  - validate_jsonl 全部通过
handoff: 数据集完成后进入 V002-T003。
```

### V002-T003: 训练主人格自生情绪 v002 LoRA

```text
status: done
owner_decision_required: no
goal: 训练 warmth/attachment/hurt/irritation/fatigue/stability 的 v002 emotion sidecar。
files:
  - configs/train_emotion_<lens>_v002.json
  - adapters/emotion_<lens>_v002/
  - eval/reports/emotion_<lens>_eval_v002.json
validation:
  - six dry-runs -> dry_run_ok=true
  - warmth training_complete=true eval_loss=0.6567 protocol_eval=18/18
  - attachment training_complete=true eval_loss=0.4484 protocol_eval=18/18
  - hurt training_complete=true eval_loss=0.2930 protocol_eval=18/18
  - irritation training_complete=true eval_loss=0.4008 protocol_eval=18/18
  - fatigue training_complete=true eval_loss=0.2067 protocol_eval=18/18
  - stability training_complete=true eval_loss=0.8053 protocol_eval=18/18
handoff: 训练完成后进入 V002-T004。
```

### V002-T004: 更新 registry 与 compose 视图

```text
status: done
owner_decision_required: no
goal: 把通过评估的 v002 adapter 登记到 registry，但不激活 live。
files:
  - state/adapter_registry.json
  - docs/adapter_evaluation.md
  - docs/handoff.md
validation:
  - state/adapter_registry.json updated
  - active_adapter remains none
  - best_by_role points six v002 adapters
  - canary remains blocked_pending_live_shadow
handoff: v002 完成后进入全量核查。
```

## 25. 当前下一步 v002

```text
next_task_id: V002-REVIEW
next_task: v002 全量核查
status: done
validation:
  - python -m py_compile v002 scripts/evals/server files -> pass
  - ConvertFrom-Json -Encoding UTF8 registry/config/v002 report JSON -> pass
  - python scripts\validate_jsonl.py data\sft\emotion_*_v002.jsonl -> pass
  - active_adapter remains none
  - all active role bindings remain none
reason: 主人格自生情绪 v002 已训练、登记并核查完成；仍不进入 canary 或 live visible reply。
```

## 26. 自动续接指令 v002 后

```text
next_task_id: LIVE-SHADOW-001
next_task: 收集真实 QQ/Desktop shadow-only 样本并做人工复查
status: blocked_by_owner_runtime
why_blocked: 当前只有本地协议样本和离线评估，还没有足够真实运行 shadow 样本。
allowed:
  - 只调用 /compose_shadow
  - 只写 shadow trace
  - trace 不记录 raw user_text
  - emotion sidecar 只输出 bias JSON
  - main_persona 只输出候选回复
forbidden:
  - 激活 active_adapter
  - 替换 QQ/Desktop 可见回复
  - 稳定记忆写入
  - 直接 Codex 执行
  - canary 自动放量
continue_rule: 如果用户说“继续”，优先执行 LIVE-SHADOW-001；如果没有真实 runtime 权限或样本，停在 shadow-only 准备，不越过安全门。
```
