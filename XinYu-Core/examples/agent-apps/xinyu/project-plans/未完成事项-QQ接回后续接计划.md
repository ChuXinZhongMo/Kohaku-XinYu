# 未完成事项：QQ接回后续接计划

更新时间：2026-05-14

## 当前阶段结论

地基阶段已经完成，可以阶段性收口。

已经完成：

- answer discipline 校准地基；
- contextual recall / evidence sufficiency / answer discipline 串联；
- dry trial；
- synthetic shadow replay；
- log shadow replay；
- safe-suite；
- dashboard；
- 可见回复守卫 shadow 接入；
- initiative research shadow 研究层；
- 全量测试通过。

最近验证结果：

- `.venv\Scripts\python.exe -m pytest -q`：297 passed；
- `python .\xinyu_answer_discipline_trial.py --root . --safe-suite --strict-gate`：通过；
- `python .\xinyu_initiative_research_shadow.py --root . --strict-gate`：通过。

## 2026-05-14 接回后进度

E / QQ 环境恢复后，原来因运行链路不可用而遗漏的事项已经做过一次真实接回：

- `D:\XinYu` 可用，`E:\` 已恢复可访问；
- core bridge `127.0.0.1:8765` 监听中；
- QQ gateway `127.0.0.1:6199` 监听中，并有 NapCat 本机 WebSocket 连接；
- NapCat WebUI `127.0.0.1:6099` 可达；
- core bridge / source digest / runtime source digest 已对齐；
- `xinyu_status.py`、`xinyu_code_awareness.py`、`tests/smoke/runtime/integration/deployment_status_smoke.py` 的 runtime digest 范围已统一；
- 可见回复守卫已接入真实发送前 shadow-only 路径：
  - direct QQ reply：`xinyu_qq_gateway.py`；
  - QQ outbox text/caption send：`xinyu_qq_outbox_dispatcher.py`；
  - shadow recorder：`xinyu_qq_visible_send_shadow.py`；
  - coverage：`tests/test_visible_send_shadow.py`；
- shadow 记录只保留 hash、flags、constraint、route/source、哈希后的 session/turn/message id；
- 不阻断、不改写真实发送内容、不保存 raw prompt/raw reply/私聊原文/QQ id；
- 已修正 3 条早期 shadow 记录里的短占位 `reply_hash`，现在全部为完整 `sha256:<64 hex>`。

接回后的验证结果：

- `D:\XinYu\Python312\python.exe xinyu_status.py --json`：ok；
- `D:\XinYu\Python312\python.exe tests\smoke\runtime\integration\deployment_status_smoke.py --json`：ok；
- `.venv\Scripts\python.exe tests\smoke\runtime\integration\runtime_readiness_smoke.py`：ok；
- `.venv\Scripts\python.exe -m pytest -q`：297 passed；
- `runtime/answer_discipline_visible_send_shadow.jsonl`：26 条，raw 保存计数 0，明文 raw/prompt/reply/text/id 字段命中 0，非法 reply hash 0。
- core bridge / QQ gateway 已按当前磁盘源码重启，`xinyu_status.py --json` digest 检查全绿；
- `diagnostics/check_xinyu_health.py --json --workspace D:\XinYu`：live probes 和 recent exceptions 均 ok，整体 `warn` 只来自当前 dirty worktree。

当前还没有开放的新行为：

- 没有开启额外自动主动 QQ 外发；
- 没有把 shadow guard 升级为拦截；
- 没有写稳定人格/关系长期记忆；
- 没有把校准材料或私聊原文写入报告。

剩余观察项：

- 继续观察真实 QQ 对话中的 shadow flags：internal label leak、无证据过度自信、模板化闲聊、普通闲聊误伤；
- 若 `/health` 或 gateway poll error 在当前链路稳定后重新持续复现，再单独修稳定性；当前 live probe、deployment status、runtime readiness 都通过；
- 主动性仍维持现有 owner gate / cooldown / shadow 边界，后续是否扩大必须另行确认。

## 为什么暂时停在这里

下一阶段需要真实 QQ / bridge 链路。

目前 E 盘环境还没有恢复，QQ 相关运行链路还没有接回来。继续堆功能的收益不高，真正应该做的是等 QQ 接回后进入真实链路验证和线上影子调校。

## 下次续接入口

下次从这里开始：

1. 恢复 E 盘环境。
2. 接回 QQ / bridge / gateway 运行链路。
3. 先跑 QQ 接入 smoke test。
4. 再把可见回复守卫接入真实发送前的 shadow-only 检查。
5. 观察真实对话 replay / shadow 报告。
6. 稳定后再决定是否开放更真实的主动性。

## 下次不要直接做的事

不要一上来就：

- 开启自动主动外发；
- 改真实 QQ 发送行为；
- 写稳定长期人格记忆；
- 宣称自我涌现或意识；
- 把 calibration 失败直接写进长期偏好；
- 把私聊原文、raw prompt、raw reply 写进报告。

## 下次优先任务

### 1. QQ 链路恢复检查

目标：确认真实运行环境可用。

需要检查：

- QQ gateway 是否能启动；
- bridge 是否能收到消息；
- bridge 是否能构造回复；
- outward renderer 是否可用；
- 发送前是否有最终拦截点；
- smoke tests 是否通过。

建议先跑：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

然后按当时环境补跑 QQ/bridge 相关 smoke。

### 2. 可见回复守卫接入真实发送前

目标：先只记录，不拦截真实发送。

接入策略：

- 找到最终发送前的 reply text；
- 调用 `xinyu_answer_discipline_visible_guard.py`；
- 只写 shadow report / runtime event；
- 不改变真实发送内容；
- 不阻断发送；
- 不保存 raw reply，只保存 hash、flags、constraint_id。

只有在 shadow 稳定后，才考虑从“只记录”升级为“软拦截”。

### 3. 真实交互影子调校

目标：用真实对话观察守卫是否误伤。

重点指标：

- internal label leak count；
- high/no-evidence overconfidence count；
- template-like casual reply count；
- visible guard failure count；
- ordinary casual reply false-positive count；
- recall support alignment；
- initiative restraint alignment。

报告仍必须 leak-free。

### 4. 主动性下一步

当前 initiative research shadow 只证明：

- 系统能克制；
- 有 recall 支撑时能浮到本地候选；
- 没有外发；
- 研究报告不宣称自我涌现。

下一步如果要往主动性走，应该先做：

- local-only owner inbox；
- owner ack；
- cooldown；
- failure rollback；
- negative feedback bias；
- replay gate。

仍然不要直接自动 QQ 外发。

## 关键文件

- `xinyu_answer_discipline_trial.py`
- `xinyu_answer_discipline_visible_guard.py`
- `xinyu_initiative_research_shadow.py`
- `tests/test_answer_discipline_trial.py`
- `tests/test_initiative_research_shadow.py`
- `project-plans/XINYU-ANSWER-DISCIPLINE-CALIBRATION-PLAN.md`
- `runtime/xinyu_calibration_dashboard.json`
- `runtime/initiative_research_shadow_report.json`

## 当前安全边界

必须继续保持：

- calibration 不写长期记忆；
- shadow report 不保存私聊原文；
- shadow report 不保存 raw prompt；
- shadow report 不保存 raw reply；
- 不保存凭证；
- 不主动外发；
- 不绕过 owner approval；
- 不把研究指标解释成意识或自我涌现。

## 一句话续接提示

等 E 盘恢复、QQ 接回后，从“真实桥接链路 smoke test + 可见回复守卫发送前 shadow 接入”开始。
