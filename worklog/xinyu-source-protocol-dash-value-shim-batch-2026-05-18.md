# XinYu Source Protocol Dash Value Shim Batch

日期：2026-05-18
范围：Batch 3，source protocol 剩余兼容入口清理

## 已完成

- `custom/source_request_planner_engine.py`
  - `extract_value(...)` 保留旧函数名，内部改为转调 `source_protocol_utils.extract_dash_value(...)`。
- `custom/source_search_provider_engine.py`
  - `extract_value(...)` 保留旧函数名，内部改为转调 `source_protocol_utils.extract_dash_value(...)`。
- `tests/test_source_protocol_utils.py`
  - 增加旧 wrapper 行为测试，确认旧名字仍可用，默认值语义不变。

## 直接影响

- source request planner / search provider 不再各自维护一份 `- field: value` 提取正则。
- 旧入口仍存在，调用方不用改。
- 本 batch 没改 request/result 渲染、搜索 provider、URL gate、source learning 主流程。

## 验证

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile custom\source_protocol_utils.py custom\source_request_planner_engine.py custom\source_search_provider_engine.py custom\source_search_resolver_engine.py custom\search_result_gate_engine.py custom\source_integration_gate_engine.py
.\.venv\Scripts\python.exe -m pytest tests\test_source_protocol_utils.py tests\test_learning_closed_loop.py -q
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_request_planner_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_search_provider_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after
```

结果：

- `py_compile` 通过
- `20 passed`
- source request planner smoke 通过
- source search provider smoke 通过
- source learning chain smoke 通过

## 未完成

- 仍有部分 source/learning 模块保留本地 `extract_value` 或更复杂 material parser；这些已超出“纯 source protocol dash value”小批次。
- `source_comparison_engine`、`learner_integration_engine`、`learning_quality_engine` 的 material/claim 解析可在后续单独做 material protocol batch。

## 下一步

进入 Batch 4：对 archive/delete 候选做引用检查，先生成证据，再只处理低风险项。
