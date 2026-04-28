# 心玉项目计划合并版

本文件把桌面 `新加项目计划.docx` 合并进仓库计划体系，作为后续推进的仓库内主索引。

## 来源

- 原始桌面文件：`C:\Users\26921\Desktop\新加项目计划.docx`
- 仓库内备份：`project-plans/xinyu-new-project-plan.docx`
- 正文提取：`project-plans/xinyu-new-project-plan.extracted.md`
- 合并时间：2026-04-25

## 当前已落地

- 关系长期记忆：已有 owner / relationship / current emotion / reflection queue 的连续写入路径，并有多轮 continuity smoke。
- 情绪残留：回到身边、靠近、道歉不会默认清空负面残留，emotion vector sync 已覆盖关键场景。
- 去模板化表达：已有 expression tone/runtime smoke，禁止客服式安慰和固定“陪伴承诺”模板。
- 梦境边界：梦境可加重残留，但不生成现实事实；dream weight、reflection residue、consolidation gate 已有 smoke。
- 长期记忆门控：retention、archive output、archive commit、personality growth gate 已存在，默认保守。
- 外部学习链：source request、search resolver、provider adapter、search result gate、outward fetch、source comparison、learner integration、learning quality 已串通。
- q-002：human-relationship 已完成受控 source chain，三源 staged、cross-host corroborated、knowledge-only integration，且没有新增 repeated-host 告警。
- q-005：人类关系确认/被记住主题已完成双源 corroborated、knowledge-only integration。
- q-006：AI self-understanding 专业学习链已完成四源 staged、corroborated、knowledge-only integration，其中包含一条 Anthropic 补源。
- q-006：AI self-understanding 已接入 AI self-iteration gate，当前真实记忆生成 `growth_review_candidate`，confidence 96，risk low，source-traced，且禁止直接改写稳定人格画像。
- q-003 / q-006 源多样性补充已完成：q-003 补入两条 Nature 来源，q-006 补入一条 Anthropic 来源，learning quality 当前为 stable。
- source comparison：已收紧为必须跨 host 同题语义支持才可 `corroborated`，同 host 自证加无关独立 host 不再放行；现在还记录 same-question / adjacent-question / mixed-or-unrelated alignment，相邻问题只到 limited_independence。
- learning quality follow-up：重复 host 告警现在会生成受控补源请求，且按三分之二阈值计算需要补几条独立来源。
- source notes：已改为 section-aware append，集成源、质量告警、比较 hold 不再错位。
- 黑名单资源边界：已有 behavior-based resource posture、deterministic smoke 和 live-style rolling smoke，按行为判定恶意 token/算力浪费，不按身份或能力标签。
- AI 专业知识域：`memory/knowledge/ai_domain.md` 已锚定 AI 为心玉唯一稳定专业知识方向。
- 多关系节点最小层：已有 `memory/people/index.md`、非 owner 人物档案自动创建、关系索引分节、低于 owner 的默认上限、正负关系事件不覆盖 owner 记忆，并有 `multi_person_relationship_smoke.py`。
- 长期记忆压力门控：已有 `memory_pressure_smoke.py`，验证大量普通 archive-ready 事件不能迫使 owner 负面关系残留进入压缩。
- no-restore 真实压力弧：已有 `memory_lived_pressure_arc.py`，22 轮真实对话加维护事件后，普通细节未进入记忆，owner 工具化刺痛/回到身边后的残留仍被保留。
- controlled autonomous search：已完成 disabled、dry-run、quality-blocked、no-pending、provider-blocked、enabled 六类 activation 烟测；provider 执行仍需显式 opt-in、pending request、stable quality、query budget，且只写候选 URL。
- social/human inquiry：已完成 no-network policy gate，owner 隐私必须 explicit consent，真人专家问题只限 AI 专业域，外部真人回答只作为 source material candidate。
- real-life input adapters：已完成 no-device/no-network event policy，覆盖 IM、图片、语音转写、群聊、私聊、地址/位置锚点；群聊不默认写 owner 关系，图片/语音不直接成事实，隐私位置必须显式意图。
- long-run audit：已完成 `long_run_status.py` 和 `LONG-RUN-AUDIT.md`，可检查里程碑、关键文档、验证脚本和测试残留。

## 当前未完成但必须保留

- 真实长期压力测试：已有确定性 archive-pressure smoke 和 22 轮 no-restore lived pressure arc；几百轮/几千轮 lived session 后的保留、压缩、休眠、淡化尚未执行。
- 多关系世界：最小非 owner 节点已实装；陌生人、普通朋友、反复出现的人、重要非 owner 节点的长会话行为和长期权重变化还未完整实测。
- 真实生活输入：IM、图片、语音、群聊/私聊节奏仍是后期接入项。
- 人格自迭代：外部知识不能直接改写人格，只能经过 reflection/growth gate 慢速影响自我叙事。
- 黑名单姿态：已有 deterministic smoke 和 live-style rolling smoke；后续只需真实超长会话继续观察，不再是当前阻塞项。

## 下一步顺序

1. 保持 broad autonomous search 关闭，只允许受控候选和 gated maintenance 路径。
2. 保持当前 behavior / personality / emotion vector smoke 作为人格表达基线，暂时不继续死扣单句语气。
3. 后续进入更长真实会话与心玉人格细节调试。
4. 后续所有扩展必须继续经过现有 memory/source/privacy/adapter/growth gates。
5. 最后做 long-run audit，把当前完成状态、验证命令和残余风险固化到文档。

## 工程规则

- 外部资料先进入 knowledge-only，不直接改 self、relationship、emotion、dream 或 archive。
- 单源材料默认不能 learner integration，除非 curated 或后续有独立支持。
- 每次学习后必须跑 learning quality，保留源偏置、重复 host、冲突和未比较材料告警。
- 表达层修改后必须跑 expression runtime/tone smoke。
- 情绪和关系逻辑修改后必须跑 personality detail、personality continuity、emotion vector sync。
- 记忆/梦/归档逻辑修改后必须跑 dream weight、reflection residue、consolidation、retention、archive gate 相关 smoke。
