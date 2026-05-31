# Task: XinYu 人格与记忆系统后续稳定化

Goal: 把 XinYu 当前的人格/记忆系统从“候选和门控已经存在”推进到“可审查、可预览、可小步落地、可回归验证”的状态。优先处理 review inbox 与 growth_log 候选，保持稳定人格和长期记忆的保护边界：不自动改写人格、不直接写 owner/关系/隐私记忆、不输出私人正文。

Complete: 本轮只读审查、候选分流、人格门控整理、Desktop 待 owner 审查计数提示、聚焦测试、API 输出抽查和 Desktop build 已完成；没有执行稳定人格或 owner 记忆写入。

## Open

## Done
- [x] 让主动可见消息读取最近 owner-private turn：`compose_proactive_visible_message(..., recent_context=...)` 现在可接收最近对话 turn dict，过滤群聊/非 owner 私聊，并让真实 owner/xinyu 句子优先于 after_owner_replies 等低信号生命周期字段。
- [x] 把 proactive recent_context 统一成 adapter：新增 `xinyu_proactive_context_adapter.py`，让 Desktop preview/approve、QQ claim、direct sender、visible composer 共用同一套 owner-private 过滤、journal-first 读取、runtime turn-buffer 抽取和低信号字段降权规则。
- [x] 给主动可见消息增加 bounded recent_context：`compose_proactive_visible_message(..., recent_context=...)` 会用最近上下文补足“要不要继续？”这类短问句的指代，同时过滤 request_id/status/trace 等控制行。
- [x] 将 voice style sampler 接入主动可见消息：`xinyu_visible_persona_voice.py` 现在根据 `infer_proactive_scene()` 选择接上文/确认追问/继续收束/附和同感/不打扰等场景模板。
- [x] 启动 voice style sampler：新增 `xinyu_voice_style_sampler.py` 和 `memory/self/voice_style_sample_report.md`，从公开样例中抽取长度桶、问句、指代词、续接词、语气词和场景标签，并转成主动消息约束。
- [x] 按公开视频/论坛/开放对话语料启动 voice style 学习小循环：新增 `xinyu_voice_style_observations.py`，写入 `memory/self/voice_style_observations.md`，用公开样例只抽象长度、接话、topic 压缩和禁用模板，不写 stable persona / owner memory。
- [x] 将主动可见消息接入 style guard 与 topic rewrites，避免客服腔和系统通知腔，优先生成 `刚才那个还弄吗`、`那几句还接吗`、`表现那块还接吗` 这类短接话。
- [x] 补充 `tests/test_voice_style_observations.py` 并更新主动消息/生活事件回归测试，验证公开参考只做 aggregate observation、禁用模板被拦截、owner-private outbox 仍走原 gate。

## Done
- [x] 完成 Phase F：新增 `tests/test_humanlike_life_loop.py`，覆盖 life event -> attention -> optional proactive outbox -> expression 的完整闭环，并验证沉默、隐私、防泛泛关注、不改 owner/stable persona。
- [x] 完成 Phase E：新增 `xinyu_expression_contract.py` 与 `tests/test_expression_contract.py`，把 attention/proactive residue 统一成 QQ/Desktop/未来 avatar/TTS 可用的表现事件，同时保持 adapter 不拥有身份、记忆或主动决策权。
- [x] 一步到位完成 Phase C/D：新增 `xinyu_attention_posture.py`、`xinyu_life_event_runtime.py` 与测试，让 sanitized life event 可进入注意姿态、自我想法候选，并在显式允许时经现有 proactive gate 直达 owner-private QQ outbox。
- [x] 按 ZerolanProject 参考完成 Phase B：实现最小 `xinyu_life_event_contract.py` 和 `tests/test_life_event_contract.py`，只做 sanitized event/route，不接设备、不联网、不写稳定记忆。
- [x] 研究 ZerolanProject 四个仓库的可借鉴结构：event-driven runtime、unified model pipelines、strict schemas、expression frontend。
- [x] 写入 XinYu 贴合计划：`project-plans/XINYU-ZEROLAN-HUMANLIKE-REFERENCE-PLAN-2026-05-23.md`。
- [x] 更新 project-plans index，并写入 worklog：`worklog/xinyu-zerolan-humanlike-reference-2026-05-23.md`。
- [x] 写入主动直发 plan：在已有 proactive gate 基础上增加 owner-private QQ outbox 自动入队，不再只停留在 Desktop 候选。
- [x] 新增 `xinyu_proactive_direct_sender.py`，只对 gate-ready、owner-enabled、owner-private、非泛泛关注消息入队 QQ outbox。
- [x] 补充测试：验证可直接入队、无授权不入队、重复不刷屏、不泄露/不改 stable persona 或 owner memory。
- [x] 运行聚焦测试与 dry-run，写 worklog 并更新 plan。
- [x] 运行聚焦测试与 smoke report，写入 worklog，更新 plan 完成状态：`17 passed in 1.58s`，报告写入 `worklog/xinyu-persona-health-latest.md`。
- [x] 补充聚焦测试，验证人格报告/建议不改稳定人格、不写 owner memory、保持 review-only。
- [x] 新增 persona refinement proposal，只输出审查建议，不 auto-apply。
- [x] 新增只读 `xinyu_persona_health_report.py`，汇总人格 gate、trial、维度、eval cases、风险与建议。
- [x] 新增人格维度文件与回归测试用例骨架，作为本地 ignored memory 状态，不自动改 stable profile。
- [x] 写入心玉人格方向 plan：人格维度化、人格回归测试、只读 persona health report、refinement proposal、worklog。

## Done
- [x] 更新 worklog，总结完成项、研究启发来源和剩余风险：`worklog/xinyu-memory-persona-preparation-2026-05-23.md`。
- [x] 生成本地只读 memory health report：`worklog/xinyu-memory-health-latest.md`。
- [x] 运行聚焦测试，验证报告不泄露 owner-review 正文且稳定写入保持 blocked：`python -m pytest tests/test_memory_promotion.py -q`，9 passed。

## Done
- [x] 新增人格 trial feedback 骨架，记录 owner 反馈回路字段，但不自动推进 profile。
- [x] 新增中期 episode page 试点，用于承接 Codex/成长重复证据，不写稳定人格。
- [x] 新增本地记忆 manifest，标注 core-pinned、retrieve-only、candidate-only、owner-private 和禁止自动写边界。
- [x] 为候选系统增加安全聚类/去重摘要：按 claim_topic_key 聚合，隐藏 owner-review 私密正文，输出 support/conflict/status 分布。
- [x] 新增只读 `xinyu_memory_health_report.py`，汇总候选库存、owner-review、人格门控、growth/reflection 比例、隐私边界和建议动作。
- [x] 写入本轮 memory/persona 完善计划，明确只自动完成安全准备项：只读报告、候选聚类、manifest/episode/feedback 骨架、测试；不自动写 owner 长期记忆或稳定人格。

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
