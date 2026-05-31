# Claude Stage 8 Acceptance Note: memory_mechanics_leak trial 0 -> 2

created_at: 2026-05-31
owner: Atimea
director: Codex
executor: Claude
mode: runtime_progress_no_code_change
related: docs/plans/CLAUDE-HANDOFF-BACK-AUTONOMY-STAGE12-13.md (Phase C)
app_root: XinYu-Core/examples/agent-apps/xinyu

## 1. 这一步做了什么（无代码改动）

回主线 Stage 8 记忆治理：通过**真实 owner 私聊**，让 `memory_mechanics_leak`
trial 在不触发 guard 的干净回合里拿到 **2 次连续同 trial 明确成功反馈**，
把学习 trial 从长期 `blocked` 推进到 `ready_for_self_review`。

本步骤未改任何代码、未改任何 state 文件去过门、未削弱 guard、未伪造 success。
仅运行了只读 status / 只读 trace 观察，以及刷新 owner-visible 验证包（从真实
state 重算的派生报告，不写学习状态）。

## 2. 如何达成（trace 证据）

`runtime/learning_closed_loop_trace.jsonl` 关键行：
- 19:34:41 `success=True failures=[] guard=[] trial=memory_mechanics_leak`（第 1 次）
- 19:35–19:51 多轮 `success=False failures=[] guard=[]`（中性话，未命中标记，
  但 evid 仍 same_trial，streak 未归零）
- 19:58:08 `success=True failures=[] guard=['empty_visible_reply_regenerated'] trial=memory_mechanics_leak`（第 2 次）
  - 注：`empty_visible_reply_regenerated` 不在 CRITICAL_GUARD_FAILURES 集，
    不产生 failure（`failures=[]` 确认），success 正常计入。

全过程 **0 次** `visible_memory_mechanics_naturalized` guard、**0 次** 任何 failure。
说明 XinYu 在普通聊天里没有泄漏记忆机制，owner 措辞也没误触发别的 failure。

## 3. 当前权威 status 字段（可复现）

只读复跑：
```
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
python xinyu_status.py
python xinyu_stage8_learning_trial_validation_packet.py   # blockers 应为空 / satisfied
```

观察值（2026-05-31 19:58 后）：
- `memory_learning_trial_gate: ready_for_self_review`（不再 blocked）
- `memory_learning_trial_same_key_success_count: 2`
- `memory_learning_trial_same_key_success_streak: 2`
- `memory_learning_trial_success_evidence: same_trial_explicit_owner_success`
- `memory_learning_trial_last_owner_reaction: explicit_success`
- `memory_learning_trial_promotion_signal: possible_after_self_review`
- `stage8_learning_trial_validation_status: satisfied`
- `stage8_learning_trial_validation_needed_success_count: 0`
- `stage8_learning_trial_owner_action: owner_explicit_apply_required_no_auto_promotion`
- `stage13_needed_same_trial_success_count: 0`
- `stage13_learning_trial_owner_action: owner_explicit_apply_required_no_auto_promotion`

## 4. 边界仍然守住（无自动晋升）

- `memory_learning_trial_stable_write: blocked`
- `stage8_stable_profile_write: blocked_review_only_not_auto_apply`
- `stage8_owner_memory_write: blocked_owner_review_required`
- `stage13_memory_promoted_to_stable_fact: false`

`ready_for_self_review` / `satisfied` 仅代表「可进入 owner 审查」，**不等于已写稳定记忆**。
是否 apply 仍需 owner 单独显式决定，无自动晋升。

## 5. gate_reason 审计不一致 —— 已诊断并修复（有界，含测试）

现象（修复前）：`memory_learning_trial_gate` 已是 `ready_for_self_review`（2/2），
但 `reason=` 仍是 `learning_trial_success_gate_not_satisfied:...streak_below_2:1`。

根因：`xinyu_status.py:learning_trial_gate_fields` 的 `gate_reason` 读自
`memory/self/personality_self_review_state.md`（L918）。live-blocker 重算只在
`gate == "blocked" and gate_reason in none_values` 时执行（L938），所以门禁转为非
blocked、而 self-review 文件仍残留旧 blocked reason 时，旧 reason 原样透出、与门禁矛盾。

修复（只改显示侧 reason，不改门禁判定）：对非 blocked 门禁归一化 reason —
`not_required` -> `learning_trial_not_required`；`ready_for_self_review` ->
`learning_trial_success_gate_met_pending_self_review:same_key_success=N/M,promotion_signal=...`；
`satisfied` 缺省补 `learning_trial_success_gate_satisfied`。blocked 路径不变。
新增测试 `test_status_gate_reason_not_stale_once_ready_for_self_review`。

验证：当前 live `memory_learning_trial_gate: satisfied reason=learning_trial_success_gate_satisfied`，
不再出现 stale `not_satisfied`。广回归 94 passed，Stage12 仍绿、Stage13 仍 available。

## 6. 顺带产生的治理 backlog（不挡 trial）

对话期间 stage8 多出 `owner_review_required` 候选 1 条 + duplicate 簇 1 个
（`candidates` 395、`owner_review=1`、`duplicates=1`）。属正常记忆候选治理 backlog，
不挡学习 trial 门，后续可用 Stage 8 审查包决定是否批准（仍不自动晋升）。

## 7. 待 Codex 决定的下一步

1. 验收本次 trial 推进（ready_for_self_review / satisfied / needed=0）。
2. 是否进入 owner 审查 -> apply（显式、无自动晋升）该 trial 的稳定落地。
3. 是否要 Claude 只读诊断第 5 节的 gate_reason 不一致。
4. 是否处理第 6 节的 owner_review_required 候选。
