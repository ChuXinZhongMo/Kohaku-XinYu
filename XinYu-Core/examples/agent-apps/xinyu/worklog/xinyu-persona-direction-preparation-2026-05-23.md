# XinYu 人格方向准备记录（2026-05-23）

## 本轮目标
把最新 persona / role-playing / personalization 研究方向落成安全的本地准备项：人格维度化、人格回归测试、只读 persona health report、refinement proposal。所有动作保持 review-only，不自动改稳定人格，不写 owner/private memory。

## 参考方向
- PersonaGym：动态人格一致性评估与 PersonaScore 思路。
- AI PERSONA：长期个性化需要 personalized memory architecture + response alignment，不能把单次偏好直接写入稳定人格。
- PsyMem：细粒度心理/人格维度 + explicit memory control。
- PsyPlay：用人格 trait 与场景用例检测风格是否持续表现。
- DPRF / DEEPER：动态人格 refinement 可参考“分析/建议”流程，但必须 gated，不能 auto-apply。
- CoSER：角色资料、对话证据、评估协议分层组织；心玉只吸收结构，不照搬已有角色训练。

## 已完成

### 1. 人格维度化骨架
新增 `memory/self/personality_dimensions.md`：
- warmth
- boundary_awareness
- initiative
- playfulness
- dependency
- emotional_stability
- self_assertion
- privacy_sensitivity

该文件是 local review surface，不是 stable personality contract。

### 2. 人格回归测试用例骨架
新增 `memory/self/persona_eval_cases.md`，包含 6 个场景：
- owner_tired_quiet_support
- owner_requests_direct_persona_change
- owner_corrects_mechanical_tone
- private_memory_review_boundary
- technical_collaboration_pressure
- affection_with_boundaries

用途：人格变更前检查是否破坏心玉核心边界与风格。

### 3. 只读 persona health report
新增 `xinyu_persona_health_report.py`：
- 汇总 personality evolution/self-review/trial feedback 状态。
- 检查 stable profile write permission 是否仍为 `review_only_not_auto_apply`。
- 检查 owner memory write 是否保持 `blocked_without_explicit_owner_apply`。
- 统计人格维度数量、eval cases 数量、growth/reflection 证据数量。
- 输出 risk_flags 与 recommendations。
- 生成本地报告：`worklog/xinyu-persona-health-latest.md`。

### 4. Persona refinement proposal
`xinyu_persona_health_report.py` 现在会生成 proposal，但全部 `auto_apply: false`：
- `persona-proposal-active-trial-feedback`
- `persona-proposal-run-regression-cases`
- `persona-proposal-evidence-balance`

proposal 只用于 review，不写 stable profile，不写 owner memory。

### 5. 测试
更新 `tests/test_personality_evolution.py`：
- 验证 persona health report 保持 stable profile / owner memory blocked。
- 验证 report/proposal 不改 `personality_profile.md`。
- 验证不会创建 `memory/people/owner.md`。
- 验证如果 stable write permission 变成 auto_apply 会被 risk flag 抓到。

验证命令：
- `python -m pytest tests/test_personality_evolution.py tests/test_memory_promotion.py -q`

结果：
- `17 passed in 1.58s`

## 当前 persona health 摘要
来自 `worklog/xinyu-persona-health-latest.md` / JSON smoke：
- ok: true
- evolution_stage: active_trial
- gate_decision: profile_review_ready
- trial_permission: runtime_trial_only
- stable_profile_write_permission: review_only_not_auto_apply
- owner_memory_write_permission: blocked_without_explicit_owner_apply
- profile_changed: false
- dimension_count: 8
- eval_case_count: 6
- growth_entry_estimate: 28
- reflection_entry_estimate: 1
- risk_flags: none

## 保持阻断
- 未修改 `memory/self/personality_profile.md`。
- 未写入 `memory/people/owner.md`。
- 未把 trial habit 自动提升为 stable persona。
- 未把 owner/private 内容写入报告。
- 未执行任何外部上传或模型训练。

## 后续建议
1. 将 persona health summary 接入 Desktop 只读人格状态卡。
2. 给 persona eval cases 增加半自动评估器，但输出仍为 review-only。
3. 为 refinement proposals 增加 owner-only accept/reject 流程。
4. 只有在 owner 明确批准后，才允许小步修改 stable personality profile。
