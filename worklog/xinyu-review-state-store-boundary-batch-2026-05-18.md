# XinYu Review State Store Boundary Batch

日期：2026-05-18
范围：Batch 2，P0 结构化记忆边界收束

## 已完成

- 新增 `stores/review_state.py`，把 review inbox cursor / decisions 的读写边界收进 `stores/review_state`。
- 更新 `xinyu_review_inbox.py`，让业务模块通过 store API 读写：
  - `memory/context/review_inbox_cursor.json`
  - `memory/context/review_inbox_decisions.json`
- 保留旧物理路径作为兼容 fallback，没有移动或读取私人 JSON 正文。
- 更新 `stores/README.md`，明确 review state 的 store 边界。
- 新增 `tests/test_review_state_store.py`。
- 刷新 P0 triage 报告：
  - `worklog/xinyu-memory-structured-p0-triage-post-review-store-2026-05-18.md`
  - `worklog/xinyu-memory-structured-p0-triage-post-review-store-2026-05-18.json`

## 直接影响

- P0 中 `runtime_cursor_or_decision_store` 这一类已经有明确 owner。
- 旧路径仍在，现有运行态和 smoke 不需要迁移数据。
- 后续如果要真正搬目录，只需要改 `stores/review_state.py`，不需要在业务模块里散改路径。

## 验证

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile stores\review_state.py xinyu_review_inbox.py
.\.venv\Scripts\python.exe -m pytest tests\test_review_state_store.py tests\test_memory_structured_p0_triage.py -q
.\.venv\Scripts\python.exe tests\smoke\tools\xinyu_review_inbox_smoke.py
.\.venv\Scripts\python.exe ops\validation\memory_structured_p0_triage.py --repo-root D:\XinYu --output D:\XinYu\worklog\xinyu-memory-structured-p0-triage-post-review-store-2026-05-18.md
.\.venv\Scripts\python.exe ops\validation\memory_structured_p0_triage.py --repo-root D:\XinYu --json --output D:\XinYu\worklog\xinyu-memory-structured-p0-triage-post-review-store-2026-05-18.json
```

结果：

- `py_compile` 通过
- `4 passed`
- `xinyu_review_inbox_smoke ok`

## 未完成

- P0 仍有 runtime queue、runtime trace、source extract、durable runtime state、persona runtime overlay 等类需要后续分批收束。
- 本 batch 不处理 `qq_outbox_queue.json`、私人关系事件、Goldmark overlay，避免高风险迁移。

## 下一步

进入 Batch 3：继续清理 source protocol 剩余兼容入口，优先找可 shim 化的解析 helper；保留特殊逻辑并写原因。
