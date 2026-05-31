# XinYu 后续自治执行计划 2

日期：2026-05-18
工作目录：`D:\XinYu`

## 目标

上一份 `plan-next.md` 已完成。本计划继续做减、做空、做清晰，优先处理仍能低风险工程化推进的缺口。

## 执行规则

- 每个 batch 只处理一个能力组。
- 先侦察，再小范围修改，再测试，再写 worklog。
- 不提交 git。
- 不打印 secrets、token、原始 QQ 内容、私人记忆正文。
- 不使用 destructive git 命令。
- 每轮结束前刷新或补充 worklog。
- 本计划完成后继续做缺口审计，必要时生成 `plan-next-3.md` 并继续。

## Batch 1：P99 Unknown Path 分类收束

目标：把 change package plan 里的 P99 unknown 从“无法判断”变成明确分类。

当前 P99 代表：
- repo infra：`.gitignore`
- app config：`config.yaml`、`pytest.ini`
- runtime package：`XinYu-Core/src/xinyu_runtime/**`
- diagnostics：`diagnostics/check_xinyu_health.py`
- legacy root memory：`XinYu-Core/memory/`

要做：
- 更新 `git_change_group_audit.py` 的分类规则。
- 更新 `git_change_package_plan.py` 或相关测试，确保 P99 数量下降。
- 刷新 change package plan。

验收：
- P99 unknown 下降，最好归零；如果无法归零，留下原因。
- 分类测试通过。
- change package plan 刷新。

## Batch 2：P0 Runtime Queue Store 边界继续收束

目标：继 `stores/review_state.py` 后，继续给低风险 runtime queue 建 store owner。

候选：
- `memory/context/self_action_gateway_approval_queue.jsonl`
- 避开 `qq_outbox_queue.json`，除非引用和 caller 已完全审清。

要做：
- 找 owner/caller。
- 增加 store wrapper，旧路径保留为兼容 fallback。
- 跑 self action focused tests/smoke。

验收：
- 至少一个 runtime queue P0 项有 store owner。
- 不移动私人队列正文。
- P0 triage 刷新。

## Batch 3：Source Material Parser 继续合并

目标：把 source material / learner / comparison 的重复 material parser 小步收束。

候选：
- `source_comparison_engine.split_material_blocks`
- `learner_integration_engine.split_materials`
- `source_integration_gate_engine.split_materials`

要做：
- 只抽纯 parser/helper，不改 gate 决策。
- 旧函数名保留为 shim。
- 增加 source material parser 聚焦测试。

验收：
- 至少一个 material parser 转调共享 helper。
- source comparison / learner integration / source quality smoke 通过。

## Batch 4：Persona Runtime Overlay Store 边界

目标：给 `memory/self/goldmark_positive_overlay.json` 建 persona runtime store owner。

要做：
- 侦察 `xinyu_goldmark.py` 和 `xinyu_runtime_context.py` 调用。
- 增加 `stores/persona_runtime.py` 或同等轻量 store wrapper。
- 旧路径保留为兼容 fallback。

验收：
- overlay 读写经 store boundary。
- persona/runtime focused tests 通过。

## Batch 5：验证与下一轮缺口审计

目标：确认本计划收束结果可继续。

要做：
- 跑聚焦 pytest。
- 跑 quick smoke。
- 如触碰 desktop，跑 desktop typecheck/build。
- 刷新 change package plan。
- 写最终审计并决定是否生成 `plan-next-3.md`。

验收：
- 本计划 worklog 完整。
- 测试证据完整。
- 剩余风险和下一步明确。
