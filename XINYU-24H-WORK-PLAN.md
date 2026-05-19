# XinYu 24 小时自主工作计划

日期：2026-05-07
工作区：`D:\XinYu`
模式：缺口驱动、允许重构、每轮验证、每轮可回滚

## 0. 计划目的

这份计划给一个可以连续工作 24 小时的 Codex 执行。

它不是单纯的架构设想，也不是只写文档。它要让 Codex 围绕 XinYu 当前真实欠缺的东西持续工作：

```text
观察现状 -> 选择一个小切片 -> 修改 -> 验证 -> 记录 -> 提交 -> 进入下一轮
```

目标是清理错误结构、补齐工程骨架、建立长期运行能力，同时保持 XinYu 现有外部行为、人格语义、记忆内容和 QQ/Desktop 协议兼容。

## 1. 当前判断

XinYu 已经不是 demo，也不是普通 QQ bot。它是一个可运行的本地个人 AI 系统，已经具备：

- Desktop 本地存在面。
- QQ / NapCat 外部入口。
- Core Bridge 主会话和 HTTP/WS 接口。
- memory、runtime、Autonomy、Local-Scope。
- Codex 委派和 learning 入口。
- thoughts、dreams、metabolism、proactivity。
- `xinyu_v1/` 影子架构。

优势：

- 系统已经能跑。
- 工作区层面已经把 Desktop、Core、NapCat、Autonomy、Local-Scope 分开。
- Bridge 有 loopback/token guard。
- QQ 入口有 whitelist 和 group trigger。
- v1 已经开始拆出路由、记忆、情绪、推理、观测。
- 状态检查可以看到 live chain 是否健康。

硬问题：

- `xinyu_core_bridge.py` 过胖，同时承担 HTTP、会话、prompt、记忆、桌面状态、主动性、Codex、learning、表情、metabolism、v1 canary。
- `xinyu_qq_gateway.py` 过胖，作为传输网关却混入 trust policy、命令路由、附件学习、主动消息、outbox ack。
- 状态层散在 Markdown、JSON、JSONL、SQLite、runtime mirror、日志、Autonomy junction。
- 验证体系还没有成为每次重构的硬门槛。
- 长时间运行的 health signals、recovery levels、checkpoint 还不够制度化。
- v1 方向正确，但还不能无证明接管真实主路径。

一句话：XinYu 的生命感和功能复杂度已经领先于工程骨架。现在最缺的不是新功能，而是骨架、验证、状态治理、长期运行和可控重构。

## 2. XinYu 现在缺什么

### 2.1 缺薄入口层

现在 Core Bridge 是大脑、总线、HTTP server、状态写入器、插件调度器和 v1 gate 的混合体。

需要补齐：

- `xinyu_bridge/app.py`：启动和依赖装配。
- `xinyu_bridge/auth.py`：token、loopback、安全入口。
- `xinyu_bridge/context.py`：BridgeContext，收纳共享依赖。
- `xinyu_bridge/http_server.py`：HTTP/WS server 壳。
- `xinyu_bridge/sessions.py`：会话管理。

目标：让旧 `xinyu_core_bridge.py` 逐步退化为兼容入口，而不是继续承载业务。

### 2.2 缺应用服务层

现在很多能力直接塞在 bridge 里。

需要补齐：

- `desktop_service.py`：桌面 REST/WS 状态与事件。
- `chat_service.py`：主对话流程边界。
- `codex_service.py`：Codex 委派、报告、outbox。
- `learning_service.py`：学习入口、ingest 包装。
- `proactive_service.py`：主动性、metabolism 调度边界。
- `qq_outbox_service.py`：Core 侧 QQ outbox 语义。
- `v1_canary_gate.py`：v1 shadow/canary 判断。

目标：Bridge 只注册服务，不亲自做服务。

### 2.3 缺纯 QQ 网关

现在 QQ Gateway 不是纯 OneBot adapter。

需要补齐：

- `xinyu_qq/server.py`：WebSocket server。
- `xinyu_qq/config.py`：配置模型。
- `xinyu_qq/onebot_adapter.py`：OneBot 原始协议收发。
- `xinyu_qq/normalizer.py`：OneBot payload -> XinYu payload。
- `xinyu_qq/sender.py`：send_private_msg / send_group_msg / send_file。
- `xinyu_qq/trust_policy.py`：whitelist、trusted、block、group trigger。
- `xinyu_qq/command_router.py`：管理命令。
- `xinyu_qq/attachment_resolver.py`：图片、文件、转发消息解析。
- `xinyu_qq/outbox_dispatcher.py`：主动消息 claim/send/ack。

目标：QQ Gateway 只管协议转换和传输，不管人格、记忆和学习策略。

### 2.4 缺状态治理

现在状态文件可观察、可手工修，但一致性、事务、迁移、回放和恢复很脆。

需要补齐：

- `state_service.py`：统一写入入口。
- `XINYU-STATE-WRITE-AUDIT.md`：所有写入点审计。
- 原子写 JSON / text。
- JSONL append 约定。
- projection 与 event 的边界。
- runtime、memory、logs、cache 的清晰规则。

目标目录语义：

```text
events/       事实事件，append-only
projections/  从事件推导出的当前状态
memory/       长期记忆，不当运行锁
runtime/      临时状态、trace、队列
logs/         诊断日志
cache/        可重建缓存
```

### 2.5 缺硬验证矩阵

需要补齐：

- `XINYU-VALIDATION-MATRIX.md`
- 每个能力对应测试命令。
- 每个重构切片对应 smoke。
- 缺失测试必须进入 task queue。

能力分类：

- Bridge 启动。
- Desktop REST。
- Desktop WS/events。
- QQ Gateway。
- QQ outbox。
- Codex delegation。
- Learning ingest。
- Memory/state。
- v1 compatibility。
- Long-run health。

### 2.6 缺长期运行运维层

需要补齐：

- `XINYU-LONG-RUN-OPERATIONS.md`
- `diagnostics/check_xinyu_health.py`
- 30 分钟 heartbeat。
- 2 小时 checkpoint。
- recovery levels。

Health signals：

- bridge alive
- desktop REST alive
- desktop WS alive
- QQ gateway alive
- NapCat reachable
- outbox backlog
- memory/state write errors
- recent exceptions
- v1 shadow errors
- disk space
- dirty git state

### 2.7 缺可控 v1 接管路径

需要补齐：

- v1 eligibility 判断独立化。
- legacy/v1 同输入对照。
- fallback reason 记录。
- v1 写入隔离。
- instant kill switch。

原则：v1 可以 shadow，可以小范围 canary，但不能无验证扩大真实流量。

### 2.8 缺更硬的个人行动层

XinYu 已经很会形成自我、记录感受、产生主动性，但真实事务处理还不够硬。

需要补齐：

- Local-Scope task lifecycle。
- owner approval contract。
- action result ledger。
- action failure feedback。
- 可审计的“我做了什么、结果是什么、是否需要你确认”。

这个阶段重要，但排在 Bridge/QQ/State/Validation 之后。

## 3. 24 小时全局规则

允许：

- 重构。
- 提取模块。
- 移动函数。
- 删除已被新模块替代的重复代码。
- 新增 service。
- 新增 smoke 或只读 diagnostics。
- 新增状态写入 helper。
- 每轮独立 commit。

禁止：

- 不改人格语义。
- 不改长期 memory 正文。
- 不改现有 HTTP/WS route。
- 不改现有 QQ payload shape。
- 不做真实 QQ 外发测试。
- 不扩大 v1 真实流量。
- 不批量格式化无关文件。
- 不删除 runtime、memory、Autonomy、Local-Scope。
- 不用 `git reset --hard` 或 destructive checkout。

遇到用户并行修改：

- 不覆盖。
- 不回滚。
- 能绕开就绕开。
- 同文件冲突就暂停。

## 4. 每轮工作循环

每轮 45-90 分钟。

固定流程：

```text
1. Sync
2. Inspect
3. Pick One Task
4. Patch
5. Validate
6. Record
7. Commit
8. Continue
```

### 4.1 Sync

```powershell
cd D:\XinYu
git status --short --branch
git log --oneline -3
```

如果不干净，先分类 dirty 文件。不是本轮产生的改动不能覆盖。

### 4.2 Inspect

读取或创建：

```text
worklog/24h-task-queue.md
worklog/24h-refactor-progress.md
XINYU-REFACTOR-CHECKLIST.md
XINYU-VALIDATION-MATRIX.md
```

### 4.3 Pick One Task

优先级：

1. 能补验证门槛。
2. 能让 `xinyu_core_bridge.py` 少一个职责。
3. 能让 `xinyu_qq_gateway.py` 少一个职责。
4. 能收口状态写入。
5. 能隔离 v1 canary 判断。
6. 能提升长运行观测。
7. 文档收束。

每轮只能做一个职责切片。

### 4.4 Patch

重构要求：

- 保持外部行为。
- 保持路径、payload、配置兼容。
- 保留薄调用层。
- 避免循环 import。
- 不顺手做无关清理。

### 4.5 Validate

每轮最低验证：

```powershell
git diff --check
git status --short --branch
```

Python 改动：

```powershell
python -m py_compile <changed-python-files>
```

Bridge 改动：

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe bridge_probe_smoke.py
```

Desktop 改动：

```powershell
.\.venv\Scripts\python.exe xinyu_desktop_rest_smoke.py
.\.venv\Scripts\python.exe xinyu_desktop_ws_smoke.py
.\.venv\Scripts\python.exe xinyu_desktop_events_smoke.py
```

Codex 改动：

```powershell
.\.venv\Scripts\python.exe codex_delegate_smoke.py
.\.venv\Scripts\python.exe codex_completion_outbox_smoke.py
```

Learning 改动：

```powershell
.\.venv\Scripts\python.exe bridge_learning_ingest_smoke.py
.\.venv\Scripts\python.exe tests\test_learning_closed_loop.py
```

QQ 改动：

```powershell
.\.venv\Scripts\python.exe xinyu_qq_gateway_smoke.py
.\.venv\Scripts\python.exe xinyu_qq_review_smoke.py
.\.venv\Scripts\python.exe check_sent_index.py
```

v1 改动：

```powershell
.\.venv\Scripts\python.exe test_v1_canary_readiness.py
.\.venv\Scripts\python.exe tests\v1\test_bridge_compatibility.py
.\.venv\Scripts\python.exe tests\v1\test_hybrid_router.py
```

如果测试不存在，把“补测试”加入任务队列，不假装验证通过。

### 4.6 Record

每轮追加：

```text
worklog/24h-refactor-progress.md
```

格式：

```md
## Loop N - HH:MM

- Task:
- Why:
- Files changed:
- Commands:
- Result:
- Risk:
- Rollback:
- Next:
```

### 4.7 Commit

验证通过才提交。

提交格式：

```text
docs: ...
chore: ...
test: ...
refactor: ...
```

每个 commit 必须能单独：

```powershell
git revert <commit>
```

失败规则：

1. 修一次。
2. 再失败，回滚本轮改动。
3. 记录原因。
4. 降级选择更小任务。

## 5. 24 小时时间表

### Hour 0-1：Baseline 和任务队列

目标：让 24 小时工作可控开始。

产出：

- `worklog/24h-task-queue.md`
- `worklog/24h-refactor-progress.md`
- `XINYU-REFACTOR-CHECKLIST.md`

动作：

- 记录 git 状态。
- 记录当前核心文件。
- 记录已有 manifest。
- 记录已有 smoke tests。
- 建初始任务队列。

提交：

```text
docs: add 24h XinYu refactor baseline
```

### Hour 1-3：验证矩阵

目标：先解决“改了不知道坏没坏”。

产出：

- `XINYU-VALIDATION-MATRIX.md`
- 可选：`diagnostics/check_validation_inventory.py`

动作：

- 扫描 smoke tests。
- 把能力映射到测试命令。
- 标出缺失测试。

提交：

```text
docs: add XinYu validation matrix
```

### Hour 3-6：Desktop Service 提取

目标：从 Core Bridge 拆最低风险职责。

新增：

```text
desktop_service.py
```

搬迁：

- `/desktop/*` REST handlers。
- desktop status/snapshot helper。
- desktop events helper。
- desktop route registration。

不改：

- URL。
- payload。
- 端口。
- Desktop UI。

验证：

- desktop REST smoke。
- desktop WS smoke。
- desktop events smoke。
- bridge probe。

提交：

```text
refactor: extract desktop service from core bridge
```

### Hour 6-9：Codex 和 Learning Service 提取

新增：

```text
codex_service.py
learning_service.py
```

搬迁：

- `/codex/*` handlers。
- Codex request/prompt assembly wrapper。
- Codex completion outbox/report wrapper。
- `/learning/*` handlers。
- learning ingest wrapper。

不改：

- Codex 输出格式。
- learning 写入格式。
- 现有 prompt 语义。

验证：

- codex smoke。
- learning ingest smoke。
- bridge probe。

提交：

```text
refactor: extract codex and learning services
```

### Hour 9-12：状态写入审计和 StateService 种子

产出：

```text
XINYU-STATE-WRITE-AUDIT.md
state_service.py
```

动作：

- 扫描直接写入。
- 分类 event/projection/memory/runtime/log/cache。
- 加 atomic JSON/text helper。
- 加 JSONL append helper。
- 只迁移低风险 runtime/projection 写入。

不做：

- 不迁移长期 memory 正文。
- 不改文件格式。
- 不一次性替换所有写入。

提交：

```text
docs: audit XinYu state writes
refactor: introduce state service helpers
```

### Hour 12-15：QQ trust policy 和 outbox dispatcher

新增：

```text
trust_policy.py
outbox_dispatcher.py
```

搬迁：

- whitelist/trusted/block 判断。
- group trigger 判断。
- outbox claim/send/ack。
- 主动消息队列 dispatch 包装。

不改：

- OneBot 连接。
- OneBot payload。
- 真实外发行为。

验证：

- QQ gateway smoke。
- QQ review smoke。
- sent index check。

提交：

```text
refactor: extract QQ trust policy and outbox dispatcher
```

### Hour 15-18：QQ sender 和 command router

新增：

```text
qq_sender.py
qq_command_router.py
```

搬迁：

- send_private_msg。
- send_group_msg。
- send_file/image helper。
- `/codex`、`/pkg` 等管理命令解析。
- 命令结果封装。

验证：

- QQ gateway smoke。
- QQ review smoke。
- compile。

提交：

```text
refactor: extract QQ sender and command router
```

### Hour 18-20：v1 canary gate

新增：

```text
v1_canary_gate.py
```

搬迁：

- v1 eligibility。
- shadow/canary decision。
- fallback reason logging。

不改：

- canary 范围。
- 真实流量。
- memory 写入策略。

验证：

- v1 canary readiness。
- bridge compatibility。
- hybrid router tests。

提交：

```text
refactor: isolate v1 canary gate
```

### Hour 20-22：Chat Service 边界

新增：

```text
chat_service.py
bridge_context.py
```

只搬边界：

- chat request wrapper。
- session lookup wrapper。
- response rendering wrapper。
- turn orchestration shell。

暂不搬：

- persona prompt 内容。
- memory selection 语义。
- v1 policy 内部。
- learning side effects。

验证：

- bridge probe。
- behavior regression smoke。
- live turn smoke，仅限安全本地。

提交：

```text
refactor: extract chat service boundary
```

### Hour 22-23：长期运行诊断

新增：

```text
XINYU-LONG-RUN-OPERATIONS.md
diagnostics/check_xinyu_health.py
```

动作：

- 定义 health signals。
- 定义 L0-L4 recovery levels。
- 增加只读健康检查。

提交：

```text
chore: add XinYu long-run health diagnostics
```

### Hour 23-24：收束报告

产出：

```text
XINYU-24H-REFACTOR-SUMMARY.md
worklog/24h-next-task-queue.md
```

必须包含：

- 完成的 loops。
- commits。
- 改动文件。
- 测试结果。
- 失败/跳过项。
- 大文件减少了哪些职责。
- 未触碰的红线。
- 回滚命令。
- 下一轮 24h 优先级。

提交：

```text
docs: summarize 24h XinYu refactor run
```

## 6. 优先级总表

### P0：必须先做

- Git 状态确认。
- task queue。
- validation matrix。
- Desktop service。
- state write audit。

### P1：本轮 24 小时应尽量完成

- Codex service。
- Learning service。
- StateService helpers。
- QQ trust policy。
- QQ outbox dispatcher。

### P2：稳定后继续

- QQ sender。
- QQ command router。
- v1 canary gate。
- chat service boundary。
- long-run health diagnostic。

### P3：暂缓

- 完整 memory 迁移。
- 完整 event/projection 化。
- 完整 chat pipeline rewrite。
- Desktop UI 大拆分。
- v1 真实流量扩大。
- 可部署产品化。

## 7. 停止条件

出现以下情况立即停止并汇报：

- memory 正文被误改。
- 需要真实 QQ 外发。
- Bridge 启动失败且回滚失败。
- route payload 意外变化。
- v1 流量意外扩大。
- 测试连续失败且 30 分钟内无法定位。
- diff 超出当前任务范围。
- 用户并行修改同一文件。
- 出现状态损坏风险。

## 8. 成功标准

24 小时后至少应达到：

- `xinyu_core_bridge.py` 至少拆出一个明确 service。
- `xinyu_qq_gateway.py` 至少拆出一个明确 service，若 QQ 阶段执行到。
- validation matrix 可用。
- state write audit 可用。
- 每个重构都有验证记录。
- 每个成功切片都有独立 commit。
- 外部行为保持兼容。
- 人格语义、memory 正文、真实 QQ 行为未被破坏。

理想结果：

- 新增 4-8 个 service/module。
- Core Bridge 明显变薄。
- QQ Gateway 明显变薄。
- 状态写入开始收口。
- v1 canary gate 独立。
- 长时间运行诊断存在。
- 下一轮 24 小时队列明确。

## 9. 最终汇报格式

24 小时结束，Codex 必须输出：

```text
1. Completed loops
2. Commits
3. Files changed
4. Tests run
5. Tests failed or skipped
6. Refactors completed
7. Remaining XinYu gaps
8. What was intentionally not touched
9. Rollback commands
10. Recommended next 24h plan
```

## 10. 核心原则

屎山不是原创性，错误结构不该被保护。

但 XinYu 的人格语义、记忆内容、运行痕迹和系统边界要被保护。

所以这 24 小时的正确姿势是：

```text
大胆拆错误结构，
小步保持行为，
每轮验证，
每轮记录，
每轮可回滚。
```

下一阶段最重要的不是继续堆功能，而是让 XinYu 拥有：

1. 更薄的 Core Bridge。
2. 更纯的 QQ Gateway。
3. 更严格的状态层。
4. 更硬的验证门槛。
5. 更可靠的长运行运维。
6. 更可控的 v1 接管路径。
7. 更扎实的个人行动层。
