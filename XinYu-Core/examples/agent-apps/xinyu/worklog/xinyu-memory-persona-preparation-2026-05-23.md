# XinYu 记忆/人格完善准备记录（2026-05-23）

## 本轮目标
把前面研究比较得到的可执行准备项落到本地：只做安全的准备、诊断、聚类和骨架文件；不自动写 owner 长期记忆，不自动修改稳定人格，不暴露 owner-review 候选正文。

## 已完成

### 1. 本地计划
- 更新 `D:\XinYu\plan.md`，列出本轮 memory/persona 完善计划与完成状态。
- 计划明确只自动完成安全准备项：只读报告、候选聚类、manifest、episode page、trial feedback 骨架、测试。

### 2. 只读 memory health report
- 新增 `xinyu_memory_health_report.py`。
- 功能：
  - 汇总 memory candidate 库存。
  - 统计 status/type/target 分布。
  - 统计 owner_review_required 与 owner/private 范围候选。
  - 按 `claim_topic_key` 聚类候选，输出 support/conflict/status 分布。
  - 读取人格 gate 状态，汇总 stable profile write 是否阻断。
  - 渲染 Markdown 报告。
- 写出报告：`worklog/xinyu-memory-health-latest.md`。

### 3. 安全候选聚类
- `build_memory_candidate_clusters()` 会按候选 claim topic 聚合。
- owner/private 或 owner-review 候选正文统一显示为 `hidden_private_or_owner_review_required`。
- owner-review 报告项只显示：candidate_id、类型、目标层、gate/risk 摘要，不显示正文。

### 4. Memory manifest
- 新增本地记忆 manifest：`memory/MEMORY-MANIFEST.md`。
- 内容包括：
  - core-pinned memory。
  - retrieve-only memory。
  - candidate-only memory。
  - owner-private / relationship memory 边界。
  - mid-term episode page 规则。
  - stable write boundaries。
  - 后续混合检索准备原则。
- 该文件在当前仓库规则下位于 ignored memory 目录，是本地状态文件，不进入 git status。

### 5. 中期 episode page 试点
- 新增：`memory/episodes/codex_timeout_recovery_episode.md`。
- 用于承接 Codex/background task timeout/follow-up 的重复成长证据。
- 明确：只做中期证据页，不写稳定人格，不写 owner memory。

### 6. 人格 trial feedback 骨架
- 新增：`memory/self/personality_trial_feedback.md`。
- 记录 runtime-only personality trial 的 owner 反馈字段。
- 明确：`stable_profile_write_permission: review_only_not_auto_apply`。

### 7. 测试
- 更新 `tests/test_memory_promotion.py`，新增：
  - health report 隐藏 owner-review 正文。
  - owner memory / stable personality 写入保持 blocked。
  - related candidates 可以聚类，且不泄露 private text。
- 验证命令：
  - `python -m pytest tests/test_memory_promotion.py -q`
- 结果：`9 passed in 1.48s`。

## 本轮 health report 结果摘要
来自 `worklog/xinyu-memory-health-latest.md`：

- total candidates: 351
- owner_review_required_count: 1
- private_or_owner_scoped_count: 107
- duplicate_cluster_count: 20
- status counts:
  - applied_growth_log: 1
  - observe_more_owner_preference: 86
  - observe_more_relationship_signal: 56
  - owner_review_required: 1
  - self_approved_recent_context: 164
  - self_approved_voice_review: 43
- personality gate:
  - evolution_stage: active_trial
  - gate_decision: profile_review_ready
  - trial_permission: runtime_trial_only
  - stable_profile_write_permission: review_only_not_auto_apply
  - profile_changed: false
- privacy boundary:
  - owner_review_candidate_text: hidden
  - owner_memory_write: blocked_without_explicit_owner_apply
  - stable_personality_write: blocked_review_only

## 研究启发映射

- Mem0：吸收 add-only、实体/主题 key、多信号检索、时间感知的方向；本轮先落为只读聚类与候选库存报告。
- Zep/Graphiti：吸收 temporal/provenance/validity-window 思路；本轮先落为 episode page 与 manifest 边界，未引入外部图数据库。
- MemoryOS：吸收 short/mid/long 分层；本轮先增加 mid-term episode page 试点。
- Letta/MemGPT：吸收 core memory block 与 archival memory 分离；本轮先增加 `MEMORY-MANIFEST.md`。
- Agent Memory survey：吸收 formation/evolution/retrieval 生命周期；本轮先补 health report 和聚类作为 evolution/maintenance 准备。

## 保持阻断的事项
- 未写入 `memory/people/owner.md`。
- 未修改 `memory/self/personality_profile.md`。
- 未 apply owner-review 候选。
- 未把 owner-review 候选正文写入报告或 Desktop 可见摘要。
- 未接入外部 memory 服务或上传候选内容。

## 建议下一步
1. 把 `worklog/xinyu-memory-health-latest.md` 的 top clusters 做成 Desktop 只读健康面板。
2. 为 owner/private cluster 增加 owner-only review flow，但正文仍不能进入普通日志。
3. 给 episode page 增加自动链接安全 candidate IDs 的命令，但仍不写稳定人格。
4. 后续再评估轻量 temporal facts JSONL/SQLite，不直接引入 Neo4j/Graphiti。
