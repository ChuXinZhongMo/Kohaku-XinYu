# XinYu 后续自治执行计划

日期：2026-05-18
工作目录：`D:\XinYu`

## 总目标

前一阶段已经完成五项稳定化收束；下一阶段继续把 XinYu 做减、做空、做清晰。执行方式保持长期自治：每个 batch 只处理一个能力组，先侦察，再小范围修改，再测试，最后更新 worklog。只要 DoD 仍有未完成项，就直接进入下一批。

## 执行边界

- 不提交 git。
- 不打印 secrets、token、原始 QQ 内容、私人记忆正文。
- 不使用 `git reset --hard`、`git checkout --` 等破坏性回滚。
- 遇到测试失败先修复；修复不了就写清楚恢复点、影响范围和下一步。
- 对记忆库、资料库、cases、runtime 的内容整理先做引用检查和边界判定，不盲目移动私人数据。
- 每轮结束前写入 `D:\XinYu\worklog\...`，说明已完成、未完成、测试证据和下一步。

## Batch 1：记忆召回主算法继续收束

目标：让 live memory recall 进一步靠近“一条主算法”，其它路径只保留 shim、provider 或兼容入口。

侦察范围：
- `xinyu_context_retrieval.py`
- `xinyu_memory_braid.py`
- `xinyu_sparse_memory_router.py`
- `xinyu_runtime_context.py`
- 相关 recall、retrieval、memory braid 测试和 smoke

要做：
- 找出当前仍各自实现召回排序、过滤、融合、裁剪的重复路径。
- 选定 canonical recall 算法所在文件，补齐或暴露稳定入口。
- 将低风险旧入口改成转调 canonical 算法，保留原函数名和返回形状。
- 增加或扩展聚焦测试，证明旧入口仍兼容。

验收：
- 至少一个重复召回入口被收成 shim/provider。
- 聚焦 recall 测试通过。
- quick smoke 或相关 memory smoke 通过。
- 写入 batch worklog。

## Batch 2：P0 结构化记忆边界收束

目标：从 P0 triage 的 22 个结构化记忆候选中选低风险项，推进 store 边界或迁移计划。

要做：
- 读取 P0 triage 报告，只看路径、类型和结构元信息，不打印私人正文。
- 避开高风险私密队列和原始聊天数据，优先处理 runtime cursor、decision store、trace log、extract log 等低风险项。
- 为可迁移项建立明确 store 归属、兼容 fallback 或只读审计清单。
- 必要时增加边界验证脚本或测试。

验收：
- P0 中至少一类低风险项有明确归属或兼容策略。
- 无私人正文输出。
- 写入 batch worklog。

## Batch 3：Source protocol 剩余兼容入口清理

目标：继续减少 source request/result/material 协议的散落解析逻辑。

要做：
- 根据 `xinyu-source-protocol-shim-prune-2026-05-18.md` 的剩余清单继续引用检查。
- 把仍可安全收束的解析、URL gate、request split、result shape helper 转调 `custom/source_protocol_utils.py`。
- 对保留的特殊逻辑写清楚原因。

验收：
- 至少一个剩余旧 helper 被 shim 化，或形成明确保留证据。
- source 相关聚焦测试和 smoke 通过。
- 写入 batch worklog。

## Batch 4：P07 archive/delete 引用检查

目标：对候选废代码先证明“无人引用”，再归档或删除低风险项。

要做：
- 生成 P07 候选引用检查报告，只基于路径、符号、import、测试引用，不读取私人内容。
- 对确认为无人引用的低风险代码执行归档或删除。
- 对仍有引用或用途不明的项留下 `archive/delete` 建议，不强行处理。

验收：
- 有可重复运行的引用检查证据。
- 至少一个低风险废代码项被归档/删除，或全部候选被证明不能安全处理。
- 写入 batch worklog。

## Batch 5：全局验证与最终审计刷新

目标：把本阶段改动收束成可恢复、可继续、可审计的状态。

要做：
- 运行必要的 pytest、quick smoke。
- 如果触碰 desktop，运行 desktop typecheck/build。
- 刷新最终审计：kept、merged、archived、deleted、remaining risks。
- 更新 change package plan 报告，确认 dirty worktree 仍可分组理解。

验收：
- 聚焦测试通过。
- quick smoke 通过；若无法跑完整套，worklog 必须写明阻塞和恢复命令。
- 最终审计列出本阶段完成项和剩余风险。

## 自动循环

1. 读取最新 worklog 和 git status。
2. 找出本计划中尚未满足的最高优先级 batch。
3. 写本 batch 小计划。
4. 执行代码、文档、测试修改。
5. 跑聚焦测试。
6. 跑必要 smoke。
7. 更新 worklog。
8. 如果仍未完成，直接回到第 2 步继续。

## 续接规则

本计划的 Batch 1-5 完成后，不把“计划完成”当作停止条件。完成后必须再做一次缺口审计：

- 对照原始七个方向和 Definition of Done，列出仍可工程化推进的缺口。
- 把缺口按风险和收益重新分批，写入下一份 `plan-*.md`。
- 直接进入下一份计划的 Batch 1。
- 只有当剩余项都属于私人内容人工决策、高风险数据迁移、外部依赖缺失，或收益明显低于风险时，才写最终停机审计。
