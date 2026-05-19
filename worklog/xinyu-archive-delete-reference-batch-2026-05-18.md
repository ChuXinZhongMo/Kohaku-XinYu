# XinYu Archive/Delete Reference Batch

日期：2026-05-18
范围：Batch 4，P07 archive/delete 引用检查

## 已完成

- 新增 `ops/validation/archive_delete_reference_audit.py`。
- 新增 `tests/test_archive_delete_reference_audit.py`。
- 生成报告：
  - `worklog/xinyu-archive-delete-reference-audit-2026-05-18.md`
  - `worklog/xinyu-archive-delete-reference-audit-2026-05-18.json`

## 审计结论

- total_candidates: 242
- accept_delete_relocated: 235
- accept_delete_no_live_refs: 7
- hold_delete_referenced: 0

这些候选已经处于 git deleted 状态。本 batch 没有额外删除文件，只补齐“为什么可以接受这些删除/迁移”的引用证据。

## 直接影响

- 旧根目录 smoke/manual/diagnostic 文件的删除不再只是肉眼判断。
- 235 个候选确认已有同名替代位置，主要在 `tests/smoke/`、`ops/manual/`、`ops/probes/`、`ops/diagnostics/`。
- 7 个 custom manifest 候选没有 live 引用，可接受删除。
- 审计工具排除了 memory/runtime/data/library/cases 等敏感目录，也排除了自身测试 fixture，避免把验证样例当成真实引用。

## 验证

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests\test_archive_delete_reference_audit.py tests\test_git_change_group_audit.py -q
.\.venv\Scripts\python.exe ops\validation\archive_delete_reference_audit.py --repo-root D:\XinYu --output D:\XinYu\worklog\xinyu-archive-delete-reference-audit-2026-05-18.md --max-examples 6
.\.venv\Scripts\python.exe ops\validation\archive_delete_reference_audit.py --repo-root D:\XinYu --json --output D:\XinYu\worklog\xinyu-archive-delete-reference-audit-2026-05-18.json --max-examples 6
```

结果：

- `5 passed`
- archive/delete audit generated successfully

## 未完成

- 本 batch 不提交 git，不接受/拒绝 staging；只是给 P07 生成证据。
- 如果后续出现新的 deleted cleanup candidate，需要重新跑该审计。

## 下一步

进入 Batch 5：全局验证、change package plan 刷新、最终审计刷新；完成后按续接规则生成下一份计划。
