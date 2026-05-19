# XinYu Live Memory Recall Boundary Batch

日期：2026-05-18
范围：Batch 1，canonical live memory recall 继续收束

## 已完成

- 新增 `ops/validation/live_memory_recall_boundary_audit.py`。
- 新增 `tests/test_live_memory_recall_boundary_audit.py`。
- 生成报告 `worklog/xinyu-live-memory-recall-boundary-audit-2026-05-18.md`。
- 报告结论：`xinyu_living_memory_recall.run_living_memory_recall_algorithm` 是 live recall canonical owner；`xinyu_context_retrieval` 当前只作为 `provider/compatibility`，没有发现 live 路径直接绕用旧 provider。

## 直接影响

- 以后继续删、并、迁移召回入口时，不再靠人工记忆判断哪些是旧入口。
- 如果新代码又直接 import `xinyu_context_retrieval` 作为 live recall 入口，审计会失败。
- 本 batch 没改召回排序、候选读取、prompt 渲染逻辑，只加了边界证据和回归测试。

## 验证

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests\test_live_memory_recall_boundary_audit.py tests\test_living_memory_recall.py tests\test_runtime_context.py -q
.\.venv\Scripts\python.exe ops\validation\live_memory_recall_boundary_audit.py --repo-root D:\XinYu --output D:\XinYu\worklog\xinyu-live-memory-recall-boundary-audit-2026-05-18.md
.\.venv\Scripts\python.exe tests\smoke\memory\context_retrieval_smoke.py
```

结果：

- `18 passed`
- `context_retrieval_smoke ok`
- audit status: `pass`

## 未完成

- `xinyu_context_retrieval.retrieve_recalled_context` 仍是 provider 内部的候选收集实现，不在本 batch 强行拆分。
- `xinyu_contextual_recall` 仍保留为 renderer/offline fallback；当前边界清楚，不应直接并进 live path。

## 下一步

进入 Batch 2：读取 P0 结构化记忆 triage，只处理路径、类型和引用元信息；选择低风险 runtime cursor / decision / trace / extract 类建立 store 边界计划，不移动私人正文。
