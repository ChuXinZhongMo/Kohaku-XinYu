# Claude Handoff-Back: Autonomy Stage 12 -> Stage 13 (session 2026-05-31)

created_at: 2026-05-31
owner: Atimea
director: Codex
executor: Claude
scope: Stage 12 gate repair + verify, owner-feedback effect, Stage 8 owner-review packet, mojibake diagnostic, display-hygiene fix
source_handoff: docs/plans/CLAUDE-HANDOFF-AUTONOMY-STAGE12-13.md
related: docs/plans/CLAUDE-DIAGNOSTIC-SUCCESS-MARKERS-MOJIBAKE.md
app_root: XinYu-Core/examples/agent-apps/xinyu

本文件是 Claude 在本次会话对上面交接计划的执行回报。架构方向仍由 Codex 负责；
以下全部为执行层结果，并遵守原计划第 10 节铁律（不削弱门禁作弊、不隐藏历史债务、
不自动晋升稳定记忆、不让心玉宣称意识、不暴露私密原文、新模块必加可验证信号）。

环境提示（本机非显而易见事实）：
- 本机所有 Python 解释器都未装 pytest，本会话用 `python -m pip install pytest`（9.0.3）安装后才能跑测试；项目无 venv。
- 运行时回复路径是真实发送（qq_outbox sent_count=138）；`dispatch_state claim=dry_run ack=dry_run` 只是 2026-05-24 留下的 proactive 路径旧 dry_run 探针，与回复 qq_ack 无关。

---

## 1. 本次完成的批次总览

| 批次 | 内容 | 状态 |
|---|---|---|
| Batch 1 (Phase A+B) | Stage12 暴露失败 live-loop check + 最近召回样本可见；`memory_mechanics_leak` future effect | done |
| Verify qq_ack | 真实 owner 私聊闭环，qq_ack 转绿 | done |
| Verify recall | 真实回指问句，最近召回样本出现 | done |
| Phase C | Stage8 blocked learning key 的 owner-visible review packet + status 透出 | done |
| Diagnostic | SUCCESS markers mojibake 是否影响匹配（只读） | done，见专档 |
| Batch 2 (display hygiene) | 仅修 owner-visible 展示，乱码不再泄漏；匹配集合零改动 | done |
| Phase D (Stage13 骨架) | 新增只读证据型 Stage13 自我叙事报告层 + status 接入 | done |

---

## 2. 改动文件清单（按模块）

运行时模块：
- `xinyu_stage12_long_term_evaluation.py`
  - `_live_loop_metrics`：计算并暴露失败的 required check 名称 + detail。
  - model 新增 `live_loop_failing_required_checks` / `live_loop_failing_required_check_detail` /
    `latest_dialogue_recall_recent_sample_present` / `latest_dialogue_recall_recent_sample_count`；render 与 state writer 同步。
- `xinyu_owner_feedback_effects.py`
  - `EFFECTS_BY_KIND` 新增 `memory_mechanics_leak` 映射（复用已接线的 `visible_mechanism_leak_risk:+12`），
    future_effect = `avoid_memory_mechanics_in_visible_reply_unless_owner_requests_diagnostics`。
- `xinyu_stage8_learning_trial_validation_packet.py`
  - 新增 `owner_review_decision` 块：`blocked_key` / `owner_action` / `source` / `reason` /
    `boundary` / `required_success_signal` / `rollback_path`；render + state writer 同步。
  - `main()` 加 `sys.stdout.reconfigure(encoding="utf-8")`（修 GBK 控制台崩溃）。
  - display hygiene：新增 `_is_display_clean_marker`（过滤 `U+FFFD`/`?`/PUA/mojibake 片段）+
    4 个精选干净示例常量；`success_capture_contract` 改从干净常量取值；移除已不用的 marker 导入。
- `xinyu_memory_health_report.py`
  - `_learning_trial_validation_summary` 读取并透出 `learning_trial_validation_owner_action`（含各 fallback 分支默认值）；
    `_stage8_memory_governance` + render + 治理 state writer 暴露该字段。
- `xinyu_stage13_self_narrative.py`（新增，Phase D）
  - 只读证据型自我叙事报告层：build/render/write_state/append_trace/main。
  - Stage12 绿 -> `active_available_for_self_narrative`；不绿 -> `waiting_for_stage12`。
  - 汇总字段：`feedback_that_changed_behavior`（带 future_effect 的 owner/action/owner_response）、
    `approved_memory_or_strategy_influence`（诚实：approved_stable_memory_count=0，runtime bias only）、
    `current_limits`、`behavior_explanation`（why reply/silence/proactive）、
    `memory_governance_state`（Stage8 guarded，需 2 次同 trial 成功，memory_promoted_to_stable_fact=false）、
    `historical_recall_debt`（透出不隐藏）。
  - 边界全 false：consciousness_claim / dream_or_body_or_fake_sensor_claim /
    unapproved_stable_memory_as_fact / raw_owner_text / visible_reply_text / historical_recall_debt_hidden；
    并用 `_scrub_sensitive` 兜底 secret/path。
- `xinyu_status.py`
  - 新增字段（Batch 1）：`stage12_live_loop_failing_required_checks` / `..._detail` /
    `stage12_latest_dialogue_recall_recent_sample_present` / `..._count` /
    `stage8_learning_trial_owner_action`。
  - 新增字段（Phase D）：`stage13_self_narrative_status` / `stage13_available` / `stage13_*`（约 22 个）
    + `stage13_self_narrative` 检查（available 必须严格跟随 stage12 门禁；边界违规即 fail）。
  - Stage12 状态行追加 `(fail:<check>)` 与 `(recent=<bool>:<count>)`；Stage8 状态行追加 `owner_action=`；
    新增 Stage13 状态行。
  - Stage13 在 status 内复用已构建的 stage12/stage8/owner_feedback 报告（决策链内部构建一次）。

测试：
- `tests/test_stage12_long_term_evaluation.py`（+2 + 扩展 status 断言）
- `tests/test_owner_feedback_effects.py`（+1）
- `tests/test_intention_ecology.py`（+1：证明 bias 真的抬高可见回复 risk）
- `tests/test_stage8_learning_trial_validation_packet.py`（+3：owner_review_decision、展示干净、防漂移）
- `tests/test_learning_closed_loop.py`（+3：clean-form-first、mojibake 反馈仍匹配、guard 压制同轮 success）
- `tests/test_stage13_self_narrative.py`（新增，6：绿->available、不绿->waiting、无意识声称/伪感官、
  无私密/可见回复原文、Stage8 guarded 如实写入未伪装晋升、status 集成 waiting 分支）

文档（仅文档，不含代码）：
- `docs/plans/CLAUDE-DIAGNOSTIC-SUCCESS-MARKERS-MOJIBAKE.md`
- `docs/plans/CLAUDE-HANDOFF-BACK-AUTONOMY-STAGE12-13.md`（本文件）

未触碰：`SUCCESS_MARKERS` / `readable_markers` / `legacy_mojibake_variants` / 任何匹配逻辑；
TinyKernel；人格强化；主动外发升级。（Phase D 仅新增证据型报告层，不改任何行为执行路径。）

---

## 3. 跑过的测试（全部通过）

- Batch 1 定向：`test_stage12_long_term_evaluation` `test_owner_feedback_effects`
  `test_intention_ecology` `test_short_term_continuity_canary` `test_live_loop_report` → 46 passed
- Batch 1 下游：`test_feedback_consumption_diagnostics` `test_expression_contract`
  `test_decision_chain_latest` `test_autonomy_loop_report` → 32 passed
- Phase C 定向：`test_stage8_learning_trial_validation_packet` `test_stage8_memory_review_packet`
  `test_memory_promotion` `test_stage12_long_term_evaluation` → 24 passed
- Phase C 相关：`test_memory_candidate_review_cli` `test_memory_review_inbox_integration`
  `test_owner_feedback_effects` `test_intention_ecology` → 40 passed
- Batch 2 定向（owner 指定）：`test_learning_closed_loop` `test_stage8_learning_trial_validation_packet` → 26 passed
- Phase D 定向（owner 指定）：`test_stage13_self_narrative` `test_stage12_long_term_evaluation`
  `test_stage9_self_state_model` `test_stage10_proactive_life_loop` → 20 passed
- Phase D 广回归：stage11 / decision_chain_latest / autonomy_loop_report / owner_feedback_effects /
  intention_ecology / learning_closed_loop / stage8_learning_trial_validation_packet /
  feedback_consumption_diagnostics（+ 上面四个）→ 108 passed

（说明：`asyncio_mode` 警告是 pytest-asyncio 未装的无害告警；上述定向套件不受影响。）

---

## 4. `xinyu_status.py` 关键 Stage 12 行（最新）

```
OK stage12_long_term_evaluation: active_ready_for_stage13 ready_stage13=true
   live_loop=pass/100.0
   recall=pass/100.0(recent=true:1)
   hist_debt=debt_present/2          # 历史债务仍可见，未隐藏
   feedback=pass/100.0  canary=ready_for_owner_canary_request
   raw_leaks=0  miswrites=0
   next=stage13_higher_order_self_narrative_can_start
OK stage13_self_narrative: active_available_for_self_narrative available=true
   feedback_influence=2 limits=4 behavior=visible_reply
   memory_gov=active_guarded owner_action=collect_2_more_same_trial_explicit_owner_success
   needed_success=2 promoted_fact=false hist_debt=debt_present consciousness_claim=false
   next=stage13_self_narrative_available_from_verifiable_evidence
```

七道 gate_proof 全 true（live_loop / short_term_recall_window / feedback /
raw_private / stable_memory / owner_visible_canary / stage11）。
Stage13 可用性严格跟随 Stage12 门禁：绿则 available，不绿则 waiting_for_stage12。

## 5. stage12_ready_for_stage13

`true`（在本快照时刻）。是靠真实 owner 证据 + 可见化修复达成，未削弱任何门禁。

重要：这是**滚动实时状态，非永久锁存**。两条会随时间/对话变化：
- `recall` 样本超过 1440min 窗口后会重回 `no_samples` → `active_collecting_metrics`；
- `qq_ack` 依赖「最新 reply 是真实发送」，若出现 `coalesced_wait`/`stale_drop` 致 `latest_seq>chat_seq`，会重回 `needs_check`。
要稳定达标，需要日常对话里这两条持续保持干净（这正是 Stage12 长期评估/canary 的意义）。

## 6. 剩余阻塞（精确字段名）

Stage 12：本快照无阻塞（达标）。需长期观察上述两条滚动条件。

Stage 8（独立于 Stage12，治理仍 guarded）：
- `stage8_learning_trial_owner_action = collect_2_more_same_trial_explicit_owner_success`
- `stage8_learning_trial_validation_needed_success_count = 2`
- `memory_learning_trial_gate = blocked`，`active_trial_key = memory_mechanics_leak`
- `stable_profile_write = blocked_review_only_not_auto_apply`，`owner_memory_write = blocked_owner_review_required`
- 含义：owner 现在**不需要批准任何稳定写入**；需要的是在不触发 memory-mechanics guard 的干净回合里，
  对该 trial 给出 2 次明确好评。稳定记忆写入保持 blocked，无自动晋升。

## 7. 私密/边界

- `raw_leaks=0`、`miswrites=0` 全程不变。
- review packet：`source` 标 `raw_owner_text_excluded`；state/worklog 经检验无 owner 私密原文、无 `U+FFFD`。
- 新增测试均断言原始私密正文不出现在 state/trace/report；可见回复正文未泄漏。

---

## 8. 诊断结论（详见专档）

`docs/plans/CLAUDE-DIAGNOSTIC-SUCCESS-MARKERS-MOJIBAKE.md`：
- SUCCESS markers 的「乱码」是 `readable_markers` 故意生成的 legacy GBK/CP936 兼容变体，源字面量干净。
- **不影响匹配**（干净 marker 是每组首元素，OR 匹配），**不影响** `memory_mechanics_leak` 的 streak=0。
- streak=0 是设计内门禁行为：该 key 失败来自 guard flags（`visible_memory_mechanics_naturalized`），
  反复触发重置 streak；同轮 owner 好评被并发 critical failure 压制
  （`_filter_failures_for_explicit_success` 只豁免 template_voice_failure）。
- 唯一真实问题是变体泄漏进 owner-visible 展示（曾致 GBK 控制台崩溃）→ 已在 Batch 2 仅做展示层修复。

Batch 2 取舍：owner 原描述是「过滤含 `�`/`?` 的 marker」，但实测还有严格 GBK 解码的纯 CJK 乱码
（如 `鑷鐒跺氫簡`），单纯过滤/round-trip 不可靠。改为展示侧从精选干净字面量取值（仍是匹配集合真子集，
防漂移测试锁定），`_sample_markers` 过滤保留作安全网。匹配集合一字未动。

---

## 9. 建议的后续（待 Codex/owner 决定）

1. Phase D 最小 Stage 13 骨架：已完成（见上）。后续若扩展 Stage13，仍须保持「只从可验证证据生成」，
   不引入空泛人格设定、梦境、伪感官，不把未批准记忆当事实。
2. 让 Stage12 的 recall/qq_ack 两条滚动条件在日常运行中稳定保持干净，再考虑任何外发能力升级。
3. （可选）按诊断专档第 8 节补 3 条匹配/抑制单测的剩余项，并评估是否给其他 owner-visible
   渲染出口统一加 `display_markers()`。
4. Stage 8 记忆治理仍 guarded：owner 需在不触发 memory-mechanics guard 的干净回合给 2 次同 trial 明确好评，
   稳定记忆写入保持 blocked、无自动晋升。

本会话执行到此（Batch1 + qq_ack/recall 验证 + Phase C + 诊断 + Batch2 + Phase D 全部完成）。
未做 TinyKernel / 人格强化 / 主动外发升级。下一步等 Codex/owner 指令。
