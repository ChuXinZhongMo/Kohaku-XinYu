# Task: XinYu 人格与记忆系统后续稳定化

Goal: 把 XinYu 当前的人格/记忆系统从“候选和门控已经存在”推进到“可审查、可预览、可小步落地、可回归验证”的状态。优先处理 review inbox 与 growth_log 候选，保持稳定人格和长期记忆的保护边界：不自动改写人格、不直接写 owner/关系/隐私记忆、不输出私人正文。

Complete: 本轮只读审查、候选分流、人格门控整理、Desktop 待 owner 审查计数提示、聚焦测试、API 输出抽查和 Desktop build 已完成；没有执行稳定人格或 owner 记忆写入。

## Open

## Done
- [x] 运行聚焦测试：`python -m pytest tests/test_memory_promotion.py -q`，7 passed，覆盖 growth candidate 列表、owner-review 正文隐藏、dry-run、apply 防护。
- [x] 运行 Desktop 类型检查：`npm run typecheck` 通过。
- [x] 运行 Desktop 构建：`npm run build` 通过。
- [x] 抽查 Core API 输出：`owner_review_required_count=1`，`candidate_text_preview=hidden_owner_review_required`，`body_hidden=True`。
- [x] Desktop 成长候选面板新增待 owner 审查计数和只读提示；正文隐藏，只显示 ID、类型、目标层、风险标签。
- [x] 为待处理候选生成 owner 可审查的只读报告：`worklog/xinyu-persona-memory-review-plan-2026-05-23.md`，区分 applied growth、owner_review_required、人格 trial 状态和阻断边界。
- [x] 对已批准且目标为 `memory/reflection/growth_log.md` 的候选检查 dry-run/apply 状态：pending=0，applied=1，无需新增 preview，稳定人格未写入。
- [x] 小步处理安全候选：当前没有可自动处理的 approved growth 候选；owner preference 候选保持 owner_review_required，不自动写 owner memory。
- [x] 检查人格门控状态：`profile_review_ready / active_trial` 已整理到 worklog，结论为 continue runtime trial，不直接改 `personality_profile.md`。
- [x] 写 worklog，总结本轮处理了什么、哪些仍需 owner 决策、哪些边界保持阻断。
- [x] 盘点 review inbox、memory candidates、growth candidates 的当前状态：唯一候选 209 个；growth_log pending=0、applied=1；仍有 owner_review_required=1，未打印私人正文。
- [x] 确认当前系统状态：稳定人格简洁，成长证据处于 candidate / trial / review 层，stable profile 写入为 review-only。
- [x] Desktop 已接入成长候选只读面板，前端显示 apply 命令但阻断直接写入。
