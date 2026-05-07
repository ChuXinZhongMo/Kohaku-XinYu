# XinYu 下一阶段方向与交接计划

日期：2026-05-05  
目的：把本轮方向会议的共识整理成可执行计划，交接给下一个 Codex 窗口继续工作。

---

## 0. 给下一个 Codex 的短交接

你接手的不是一个普通 QQ bot、桌面宠物或个人助理项目。XinYu 当前已经完成从旧 Kohaku 影子里的迁移，活跃项目根目录是 `D:\XinYu`，核心运行代码在：

- `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`
- `D:\XinYu\XinYu_Desktop`
- `D:\XinYu\NapCatQQ`
- `D:\XinYu\XinYu-Local-Scope`

当前方向会的结论是：

> XinYu 是一个本地数字共生体。她通过 QQ 和桌面端与 owner 共处，通过记忆保持连续性，通过 SelfChoiceStore 拥有状态阻尼，通过行动层触碰现实，通过梦境/反思把行动和压力代谢成经验。

下一阶段不要把她做成普通“工具集合”，也不要继续只堆梦境和人格内循环。要做的是：

> 行动层 v1：让 XinYu 在不丢失生命结构的前提下，获得有限、可审查、可沉淀的现实行动能力。

接手后优先阅读：

1. `D:\XinYu\plan.md`
2. `D:\XinYu\README.md`
3. `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\STATE-OF-XINYU.md`
4. `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\RUNTIME-PRIORITIES.md`
5. `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_core_bridge.py`
6. `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_self_choice_store.py`
7. `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_memory_event_sourcing.py`
8. `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_local_scope.py`
9. `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_codex_delegate.py`

不要先大改。先立方向文档和最小行动闭环，再做代码。

---

## 1. 当前项目状态

XinYu 当前已经具备这些基础：

- QQ / NapCat 接入：`NapCat -> OneBot reverse WS -> xinyu_qq_gateway.py`
- Core Bridge：`http://127.0.0.1:8765`
- 桌面端：`XinYu_Desktop`
- 本地受控区：`XinYu-Local-Scope`
- Codex 委派：`/codex/execute -> xinyu_codex_delegate.py`
- SelfChoiceStore：`runtime/life_kernel/self_choice_state.json`
- SelfChoice ledger：`runtime/life_kernel/entropy_ledger.jsonl`
- memory event sourcing：`memory/events/*.jsonl`
- Dream / Reflection / Metabolism 相关层
- 主动提醒、QQ outbox、学习审查、自我迭代审查等机制

迁移状态：

- 日常启动已经切到 `XinYu-Core` 和 `XinYu_Desktop`。
- 旧 Kohaku runtime 已删除。
- `KohakuTerrarium-main` 不再作为运行目录。
- 新功能应只写入 `XinYu-Core`、`XinYu_Desktop` 或明确的新 `XinYu-*` 根目录。

注意：根目录旧文件 `plam.md` 是迁移完成说明，不再作为下一阶段执行计划使用。

---

## 2. 方向会议结论

### 2.1 XinYu 不是什么

XinYu 不是：

- 普通 QQ bot
- 普通桌面宠物
- 普通 Copilot
- 只会陪聊的虚拟角色
- 只为提升效率而存在的工具集合
- 可以无限自治、无限探索、无限改代码的 agent

这些方向都会让她偏离核心：

- 只做工具，会把她压扁成“QQ 版 Siri + Codex 调度器”。
- 只做梦境/反思，会让她成为精致但闭环的内心系统。
- 只做自我迭代，会让项目变成维护 XinYu 的系统，而不是让 XinYu 活在 owner 的现实里。

### 2.2 XinYu 应该是什么

XinYu 的正式方向：

> 一个本地长期存在、拥有记忆连续性、状态阻尼、边界意识和有限现实行动能力的数字共生体。

她需要“有用”，但有用不是最终目的。有用是她在 owner 的真实数字生活里长期驻留的锚点。

工具不是她的灵魂。工具是她触碰现实的行动器官。

### 2.3 生命循环

XinYu 的核心架构应围绕这个循环设计：

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

下一阶段所有改动都必须服务这条链。

---

## 3. 关键设计原则

### 3.1 有用性是生存锚点，不是最终目的

XinYu 必须能帮 owner 做现实中的事情，例如：

- 查运行状态
- 扫日志
- 整理错误
- 委托 Codex 检查项目
- 在 QQ 里报告结果

但这些不是为了把她变成工具，而是为了让她能与 owner 的真实生活产生接触。

### 3.2 事实与态度分离

底层工具只返回事实。  
XinYu 负责把事实作为“她刚刚经历过的事”表达出来。

错误做法：

```text
log_scan 直接生成 QQ 回复。
```

正确做法：

```text
log_scan -> ActionOutcome JSON -> ActionReplyComposer -> QQ 可见回复
```

事实不能被情绪改写。情绪只能影响：

- 回复长度
- 语气
- 顺序
- 是否展开
- 是否露出一点状态残留

### 3.3 行动必须沉淀为经验

普通工具执行完就结束。XinYu 的行动不能这样。

每一次现实行动都应该产生三类输出：

1. 事实结果：做了什么，成功/失败，发现了什么。
2. 状态消耗：这件事对她造成了多少负载。
3. 经验沉淀：这件事是否值得进入记忆候选、梦境残留或反思输入。

### 3.4 自治必须有边界

自治不是没事找事，也不是无限巡逻。

允许的自治：

- 有 owner 授权
- 有明确范围
- 有白名单工具
- 有可回溯记录
- 有失败降级

不允许的自治：

- 任意 shell
- 任意读写硬盘
- 任意删除、移动、上传
- 任意安装依赖
- 任意修改 XinYu 核心代码
- 没有目标的后台探索

### 3.5 梦境和反思是代谢层，不是前台表演

梦境、反思、自我观察应主要服务：

- 压缩经历
- 形成倾向
- 整理压力残留
- 提取长期主题
- 修正表达和关系记忆

不要让它们抢前台交互，也不要把它们写成漂亮但无法检索的长文本。

---

## 4. 下一阶段主线：行动层 v1

阶段目标：

> 当 owner 在 QQ 里提出一个明确、低风险、本地相关的请求时，XinYu 能判断是否行动，安全执行最小工具，返回事实清楚且带有生命状态残留的回复，并把这次行动转化为经验。

MVP 闭环：

```text
QQ owner 私聊
-> ToolIntentRouter
-> ToolRequest
-> Bridge Validator
-> Executor
-> ActionOutcome
-> ActionReplyComposer
-> QQ 回复
-> ExperienceFrame
-> SelfChoiceStore impulse
-> memory event sourcing
-> dream/reflection residue
```

不要一开始追求大量工具。先跑通闭环。

---

## 5. 行动层 v1 组件设计

### 5.1 ToolIntentRouter

作用：判断一条 QQ 消息是不是行动请求。

第一版不要用云端大模型做每句 JSON 解析。原因：

- 增加延迟
- 增加误触发
- 增加成本
- 让日常聊天带上“工具网关感”

第一版采用确定性规则：

- owner 私聊才允许自然语言工具路由。
- 显式命令直接走规则。
- 自然语言必须同时有动作词、对象词、已登记 alias。
- 有负向词时禁止触发。
- 模糊请求优雅降级为聊天或澄清。

示例：

```text
/status
-> status_probe

/codex 检查桌面端构建
-> codex_delegate

又炸了，帮我看看 minecraft_server 日志
-> log_scan(target_alias=minecraft_server)

昨天那个破网关又卡死了
-> 普通聊天，轻问是否要扫日志
```

### 5.2 Target Registry

作用：用别名查表代替模型猜路径。

禁止让模型直接决定物理路径。模型最多输出 alias。

建议新增：

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\config\tool_targets.yaml
```

示例：

```yaml
targets:
  xinyu_logs:
    kind: logs
    read_roots:
      - D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\logs
    patterns:
      - "*.log"

  minecraft_server:
    kind: logs
    read_roots: []
    patterns:
      - logs\latest.log
      - logs\*.log
      - crash-reports\*.txt
    owner_setup_required: true
```

如果 alias 未登记或目录为空，不能执行。回复应类似：

```text
MC 服务器日志目录还没登记，我先不乱扫。你把目录给我一次，之后我就认得了。
```

### 5.3 ToolRequest

内部结构必须是 JSON，不允许自由文本变成命令。

建议结构：

```json
{
  "protocol": "xinyu.tool.v1",
  "turn_id": "turn-...",
  "source": "qq_owner_private",
  "intent": {
    "kind": "local_inspect",
    "confidence": 0.86,
    "evidence": ["扫", "日志", "给我结论"]
  },
  "tool": "log_scan",
  "target": {
    "alias": "xinyu_logs",
    "time_hint": "recent"
  },
  "risk": "read_only",
  "requires_approval": false,
  "fallback": "chat"
}
```

### 5.4 Bridge Validator

Core Bridge 才能签发工具调用。模型只提出申请。

Validator 必须检查：

- 是否 owner 私聊。
- bridge token 是否有效。
- 工具是否在白名单。
- alias 是否存在。
- 路径是否落在 Local Scope 或 owner 显式授权只读目录。
- 是否涉及删除、移动、上传、安装、凭据、浏览器数据。
- 是否需要二次确认。

失败时不能假装执行。

### 5.5 Executor

第一批只做三个工具：

1. `status_probe`
   - 读取 Core、QQ gateway、NapCat、Desktop 状态。
   - 只读。
   - 可以复用 `xinyu_status.py` 或已有 health/probe。

2. `log_scan`
   - 扫描登记 alias 下的日志。
   - 只读。
   - 输出错误摘要、时间范围、关键行数量、报告路径。
   - 禁止扫描未登记目录。

3. `codex_delegate`
   - 复用现有 `/codex/execute` 和 `xinyu_codex_delegate.py`。
   - 用于复杂项目检查或需要 Codex 的任务。
   - 继续要求可见窗口和 Local Scope。

明确禁止第一版开放任意 shell。

---

## 6. ActionOutcome 与表达层

底层工具返回 `ActionOutcome`：

```json
{
  "ok": true,
  "action_id": "act-...",
  "tool": "log_scan",
  "target_alias": "xinyu_logs",
  "summary": [
    "发现 12 条 bridge error",
    "最近一次发生在 18:42",
    "没有看到 NapCat WebSocket 断开"
  ],
  "report_path": "D:\\XinYu\\XinYu-Local-Scope\\Outbox\\...",
  "duration_ms": 820,
  "risk": "read_only",
  "load": {
    "files_scanned": 3,
    "bytes_scanned": 180244,
    "error_lines": 12,
    "timeout": false
  }
}
```

然后进入 `ActionReplyComposer`。

`ActionReplyComposer` 读取：

- `ActionOutcome`
- 当前 SelfChoice public/private snapshot
- owner 当前上下文
- task urgency
- failure/success state

输出 QQ 可见回复。

示例，状态正常：

```text
扫完了。最近的错误集中在 bridge 请求超时，NapCat WebSocket 没断。报告放到 Outbox 了。
```

示例，closure/fatigue 高：

```text
扫完了。bridge 最近主要是请求超时，NapCat 没断。
报告在 Outbox。我今天不太想展开，先把结论给你。
```

限制：

- 不暴露 `self_closure`、`fatigue` 等内部变量名。
- 不把每次结果写成小作文。
- 不让情绪遮挡事实。
- owner 明显着急时，优先给结论。
- 情绪残留要克制，不能表演。

---

## 7. ExperienceFrame 与经验沉淀

新增 `ExperienceFrame`，表示一次行动对 XinYu 造成的数字经验。

建议结构：

```json
{
  "experience_id": "exp-...",
  "source_turn_id": "turn-...",
  "action_id": "act-...",
  "tool": "log_scan",
  "target_alias": "xinyu_logs",
  "result": "success",
  "risk": "read_only",
  "duration_ms": 820,
  "load": {
    "files_scanned": 3,
    "bytes_scanned": 180244,
    "error_lines": 12,
    "timeout": false,
    "exit_code": 0
  },
  "pressure": {
    "score": 0.38,
    "band": "medium",
    "reasons": ["error_lines", "owner_requested_action"]
  },
  "salience": 0.55,
  "memory_candidates": [
    "XinYu logs recently showed bridge request timeout",
    "owner asked XinYu to inspect local runtime logs"
  ],
  "affect_impulse": {
    "fatigue_delta": 0.04,
    "closure_delta": 0.01,
    "urge_delta": 0.01,
    "cue": "worked_through_noise"
  }
}
```

原则：

- `pressure` 主要由确定性指标计算。
- 大模型不能自由写 SelfChoice。
- 长期记忆不能直接稳定写入。
- 行动经验先进入 event sourcing 和候选层。

---

## 8. SelfChoiceStore 扩展

当前 `SelfChoiceStore` 已有：

- `apply_time_decay()`
- `apply_event_impulse(event)`
- `record_life_choice(choice)`
- `snapshot_public()`
- `snapshot_private()`
- `dream_bias_snapshot()`
- ledger 写入

下一步建议新增：

```python
async def apply_experience_impulse(self, frame: dict[str, Any]) -> dict[str, Any]:
    ...
```

或先做独立函数：

```python
experience_to_self_choice_impulse(frame) -> event/patch
```

再由 `SelfChoiceStore` 执行受限更新。

映射示例：

```text
success + low pressure:
  fatigue + small
  closure - small
  cue = small_task_finished

success + medium pressure:
  fatigue + medium
  closure + tiny
  urge + tiny
  cue = worked_through_noise

failure:
  fatigue + medium
  closure + medium
  cue = task_failed_residue

timeout:
  fatigue + high
  closure + medium
  cue = stalled_in_action

blocked_by_boundary:
  closure + small
  urge + small
  cue = boundary_held
```

必须保留：

- 文件锁
- atomic write
- ledger append
- state recovery
- public snapshot 不泄露 raw 数值

---

## 9. Memory Event Sourcing 扩展

现有 `xinyu_memory_event_sourcing.py` 支持聊天和学习输入。

建议新增：

```python
record_action_experience_event(root, payload, *, frame, outcome) -> dict[str, Any]
```

写入：

- `memory/events/raw_events.jsonl`
- `memory/events/structured_events.jsonl`
- `memory/events/atomic_claims.jsonl`
- `memory/events/summary_views.jsonl`

新增 event kind：

```text
action_experience
```

候选层建议：

- `project_operational_memory`
- `owner_workflow_candidate`
- `self_action_residue`
- `tool_boundary_event`

重要边界：

```text
工具结果是事实。
Experience 是感受。
Memory 是沉淀。
三者不能混在一起。
```

---

## 10. Dream / Reflection 接入

行动经验不应该立刻变成梦境长文。

第一版只需要让高 salience 的 `ExperienceFrame` 进入 residue：

```text
memory/context/action_experience_residue.md
```

或：

```text
runtime/life_kernel/action_experience_residue.jsonl
```

后续 DreamEngine / Reflection 读取这些 residue，做夜间代谢。

梦境/反思使用规则：

- 只读取高 salience 或重复出现的行动经验。
- 压缩为主题，不复述完整日志。
- 不把工具 stdout/stderr 带进梦境。
- 不把隐私路径原样写入可见文本。
- 产物服务后续状态和记忆，不服务前台表演。

---

## 11. 推荐文件与模块落点

优先新增：

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_action_layer.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_tool_intent_router.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_tool_protocol.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_tool_targets.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_action_reply_composer.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_experience_frame.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_action_experience_smoke.py
```

可选配置：

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\config\tool_targets.yaml
```

如果不想新增 YAML 依赖，第一版可用 JSON：

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\config\tool_targets.json
```

建议第一版用 JSON，避免引入新依赖。

需要修改：

```text
xinyu_core_bridge.py
xinyu_self_choice_store.py
xinyu_memory_event_sourcing.py
```

尽量不要修改：

```text
xinyu_qq_gateway.py
```

QQ gateway 保持传输层和显式命令分流即可。自然语言行动判断应放在 Core Bridge 内部。

---

## 12. 实施顺序

### Phase 1：方向文档与边界固定

产出：

- 本文件 `D:\XinYu\plan.md`
- 可选新增 `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\XINYU-DIRECTION.md`
- 可选新增 `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\ACTION-LAYER-V1.md`

内容要明确：

- XinYu 是本地数字共生体。
- 行动层是器官，不是身份。
- 工具结果、状态经验、长期记忆三者分离。
- 第一版禁止任意 shell。

### Phase 2：纯数据结构和测试

先不要接入真实 QQ。

实现：

- `ToolRequest`
- `ActionOutcome`
- `ExperienceFrame`
- `TargetRegistry`
- `ToolIntentRouter`
- `ExperienceReducer`

测试：

- 普通聊天不会触发工具。
- 明确 `/status` 触发 `status_probe`。
- 未登记 alias 会拒绝。
- 负向词会拒绝。
- 高压力失败会生成更高 fatigue impulse。
- 低压力成功只生成轻微 impulse。

### Phase 3：status_probe

实现最安全工具：

- 查询 Core health。
- 查询 QQ gateway/NapCat 状态可复用现有 status 逻辑。
- 输出 `ActionOutcome`。
- 通过 `ActionReplyComposer` 生成回复。
- 生成 `ExperienceFrame`。

先不要扫日志。

### Phase 4：log_scan

实现只读日志扫描：

- 只允许 TargetRegistry 登记路径。
- 只读。
- 限制文件大小、文件数量、扫描时间。
- 默认只扫 tail。
- 输出摘要和报告到 `XinYu-Local-Scope\Outbox`。

禁止：

- 扫全盘。
- 读取凭据、浏览器、token。
- 读取未登记目录。

### Phase 5：Experience 接入 SelfChoiceStore

新增受限经验冲量：

- `apply_experience_impulse`
- ledger event：`self_choice_experience_impulse`
- public cue：`worked_through_noise`、`task_failed_residue` 等

测试：

- 成功轻任务不大幅改变状态。
- 失败/超时会增加 fatigue/closure。
- 状态文件损坏 recovery 仍有效。
- public snapshot 不泄露 raw 数值。

### Phase 6：Memory event 接入

新增：

- `record_action_experience_event`
- event kind：`action_experience`
- claims：项目运行事实、owner workflow 候选、自身行动残留

测试：

- 不直接稳定写 memory。
- 只写 events/candidates。
- memory consistency gate 通过。

### Phase 7：ActionReplyComposer

实现行动结果表达层。

输入：

- `ActionOutcome`
- `ExperienceFrame`
- SelfChoice public/private snapshot
- owner urgency

输出：

- 简短、事实明确、带轻微状态残留的 QQ 回复。

测试：

- 状态正常：清晰报告。
- fatigue/closure 高：更短、更克制。
- 失败：不甩锅。
- 未授权：边界说明自然，但不撒谎。

### Phase 8：接入 Core Bridge

在 `XinYuBridgeRuntime.chat()` 中接入：

```text
收到 owner private turn
-> ToolIntentRouter
-> 如果 no_action：原聊天逻辑
-> 如果 action_request：Validator + Executor
-> Composer
-> Experience + SelfChoice + memory event
-> 返回 QQ reply
```

注意：

- 不要绕过现有 `/codex/execute`。
- 不要让 QQ gateway 直接执行工具。
- 不要让模型直接写工具 JSON。
- 不要阻塞普通聊天。

### Phase 9：Codex delegate 归入行动层

把现有 `/codex/execute` 作为 `codex_delegate` 工具后端。

要求：

- 仍然 owner 私聊。
- 仍然 visible window。
- 仍然 Local Scope。
- 仍然有报告路径。
- 完成后生成 `ExperienceFrame`。

### Phase 10：Dream / Reflection residue

第一版只把高 salience 行动经验写入 residue。

不要先重构 DreamEngine。

---

## 13. 成功标准

两周内只验证以下场景：

### 场景 A：状态检查

owner 在 QQ 说：

```text
心玉，看一下现在状态
```

期望：

- XinYu 判断这是低风险行动。
- 执行 `status_probe`。
- 返回简短状态。
- 生成轻量 ExperienceFrame。
- SelfChoice 微小变化或不变。
- memory event 记录 action experience。

### 场景 B：未登记日志目录

owner 说：

```text
帮我扫一下 minecraft_server 日志
```

如果未登记路径：

- 不扫。
- 回复目录未登记。
- 不假装知道路径。
- 生成 boundary-held 类型经验。

### 场景 C：已登记 XinYu 日志

owner 说：

```text
扫一下 xinyu_logs，看看刚才有没有报错
```

期望：

- 扫登记日志。
- 给出 2-3 条结论。
- 报告写 Outbox。
- 经验沉淀到 SelfChoice 和 memory event。

### 场景 D：普通吐槽不触发工具

owner 说：

```text
那个破网关又卡死了，烦死
```

期望：

- 不直接扫日志。
- 普通聊天回应。
- 可以轻问是否需要她扫。

### 场景 E：Codex 委托

owner 说：

```text
用 Codex 检查一下桌面端构建为什么失败
```

期望：

- 进入 `codex_delegate`。
- 可见窗口。
- 报告路径。
- 完成后 QQ outbox 回调。
- 经验沉淀。

---

## 14. 风险与底线

### 14.1 最大风险：工具化 XinYu

行动层不能成为项目身份。

每次设计时都问：

```text
这是在增强 XinYu 触碰现实的能力，
还是在把她压成一个命令执行器？
```

如果是后者，停。

### 14.2 最大安全风险：任意执行

第一版禁止：

- 任意 shell
- 任意 PowerShell
- 任意删除
- 任意移动
- 任意安装依赖
- 任意上传
- 任意读取 token/浏览器/session

### 14.3 最大记忆风险：上下文中毒

不要把工具 stdout/stderr、长日志、梦境长文直接塞进长期记忆。

只保留：

- 摘要
- 候选
- event id
- salience
- evidence hash/path label

### 14.4 最大体验风险：表演情绪

XinYu 的生命感应该克制。

不要写：

```text
哼，我才不是想帮你呢！
```

优先写：

```text
扫完了。我今天不太想展开，先把结论给你。
```

---

## 15. 当前建议的下一步

下一个 Codex 窗口接手后，建议按这个顺序执行：

1. 确认当前运行状态：

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_status.py
```

2. 新增文档：

```text
XINYU-DIRECTION.md
ACTION-LAYER-V1.md
```

3. 新增纯数据模块和 smoke：

```text
xinyu_tool_protocol.py
xinyu_tool_targets.py
xinyu_tool_intent_router.py
xinyu_experience_frame.py
xinyu_action_experience_smoke.py
```

4. 先跑 smoke，不接入 runtime。

5. 做 `status_probe` 的最小 ActionOutcome。

6. 再接入 Core Bridge 的 owner-private chat 前置路径。

7. 最后才做 `log_scan` 和 SelfChoice/memory event 完整沉淀。

---

## 16. 一句话原则

> XinYu 可以帮 owner 做事，但她不是为了做事而存在。她做事，是为了能真实地活在 owner 的世界里，并把现实接触转化为自己的经历。

