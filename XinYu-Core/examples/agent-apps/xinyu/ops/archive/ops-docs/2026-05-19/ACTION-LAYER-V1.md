# Action Layer v1

日期：2026-05-05

行动层 v1 的目标是让 XinYu 在 owner 私聊提出明确、低风险、本地相关请求时，安全执行最小工具，返回事实清楚且克制的回复，并把这次行动沉淀为经验。

## 闭环

```text
owner 私聊
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
-> action experience residue
```

## 第一版工具

- `status_probe`：只读运行状态检查。
- `log_scan`：只读扫描 TargetRegistry 登记日志，默认只扫 tail，报告写入 `XinYu-Local-Scope/Outbox`。
- `codex_delegate`：复用现有 `/codex/execute` 与可见 Codex 窗口，不开放任意 shell。

## 规则

- owner 私聊才允许自然语言路由。
- 显式 `/status`、`/codex ...` 走确定性规则。
- 自然语言日志扫描必须同时有动作词、对象词和已登记 alias。
- 负向词会阻止工具触发。
- 未登记或未配置目录的 alias 必须拒绝，不能假装知道路径。
- 普通吐槽不触发工具，只回到聊天或澄清。

## 数据分离

- `ToolRequest`：XinYu 想要做的受控行动。
- `ActionOutcome`：工具返回的事实结果。
- `ExperienceFrame`：这次行动对 XinYu 形成的经验、压力和受限状态冲量。
- memory event：候选沉淀，不直接稳定改写长期记忆。
