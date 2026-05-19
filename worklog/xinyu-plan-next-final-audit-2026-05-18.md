# XinYu Plan Next Final Audit

日期：2026-05-18
计划文件：`D:\XinYu\plan-next.md`

## 完成项

- Batch 1：live memory recall 边界审计
  - 新增 `ops/validation/live_memory_recall_boundary_audit.py`
  - 结论：live recall owner 仍是 `xinyu_living_memory_recall.run_living_memory_recall_algorithm`
  - `xinyu_context_retrieval` 只作为 provider/compatibility 使用
- Batch 2：P0 review state store 边界
  - 新增 `stores/review_state.py`
  - `review_inbox_cursor.json` / `review_inbox_decisions.json` 的业务读写转到 store API
  - 旧 `memory/context` 物理路径保留为兼容 fallback
- Batch 3：source protocol dash value shim
  - planner/provider 的 `extract_value` 转调 `source_protocol_utils.extract_dash_value`
  - 旧函数名保留
- Batch 4：archive/delete 引用审计
  - 新增 `ops/validation/archive_delete_reference_audit.py`
  - P07 242 个 deleted cleanup candidates 中：
    - 235 个确认已迁移到同名替代位置
    - 7 个确认无 live 引用
    - 0 个 hold
- Batch 5：验证与 change package 刷新
  - 刷新 `worklog/xinyu-change-package-plan-2026-05-18.md/json`

## Kept

- `xinyu_context_retrieval.retrieve_recalled_context` 继续作为召回 provider，不直接拆内部候选收集。
- `xinyu_contextual_recall` 继续作为 renderer/offline fallback，不并入 live recall。
- P0 高风险私人或运行态内容继续原地保留。
- 旧 review inbox JSON 路径继续存在，避免数据迁移风险。

## Merged / Shimmed

- review inbox cursor/decision JSON 读写合并到 `stores.review_state`。
- source planner/provider 的 dash field parser 合并到 `source_protocol_utils.extract_dash_value`。
- archive/delete 证据合并成一个可重复审计工具。

## Archived / Deleted

- 本轮没有额外执行文件删除。
- 对已经处于 git deleted 状态的 P07 候选补齐了引用检查证据。

## Validation

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
git -C D:\XinYu diff --check
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300

cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

结果：

- `git diff --check` 通过，仅有 CRLF normalization warnings
- `489 passed`
- `smoke_run group=quick: ok`
- desktop `npm run typecheck` 通过
- desktop `npm run build` 通过

## Remaining Risks

- dirty worktree 仍有 638 个条目，虽然已分组，但还没有拆成提交包。
- P06 仍有 runtime queue、runtime trace、source extract、durable runtime state、persona runtime overlay 等 P0 结构化记忆边界未继续收束。
- P99 仍有 11 个 unknown paths，需要纳入分类规则。
- source/material/learning 仍有若干本地 parser，可以继续小批次合并。
- 本轮没有运行“所有历史单独 smoke”，只运行了 full pytest、quick smoke 和本轮聚焦 smoke。

## 续接

按 `plan-next.md` 的续接规则，下一步生成 `plan-next-2.md`，优先处理：

1. P99 unknown path 分类收敛。
2. P0 runtime queue/store 边界继续收束。
3. source material parser 继续合并。
4. persona runtime overlay store 边界。
5. 最终验证与下一轮缺口审计。
