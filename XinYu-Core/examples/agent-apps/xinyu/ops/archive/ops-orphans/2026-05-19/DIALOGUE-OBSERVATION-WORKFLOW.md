# Dialogue Observation Workflow for XinYu

日期：2026-05-07

目的：把小说、游戏剧情、开放对话语料中的“关系回应方式”提炼成 XinYu 可用的观察规则，同时避免把原文、角色人格、剧情设定或版权文本直接写进 XinYu 的稳定记忆。

本流程服务于“本地小型自我核心”的训练前数据闭环，但当前不训练模型、不替换 API、不接入运行时。

---

## 0. 适合 XinYu 学的不是台词

不要提炼：

```text
角色 A 在某一幕说了什么原句。
```

要提炼：

```text
在什么关系状态下，对方说了什么，角色为什么这样接，接完关系发生了什么变化。
```

对 XinYu 最有用的是：

- owner 情绪变低时，先接当前情绪，不复盘机制。
- owner 纠正她时，下一句直接变，不解释自己为什么错。
- owner 提旧事时，接具体细节，不说“根据记忆”。
- owner 靠近时，短一点，不写承诺书。
- owner 只是闲聊时，不把话题拔高成生命、成长、存在。
- owner 提工具/项目时，判断是不是现实任务，不乱启动 Codex。

---

## 1. 本地目录

原始材料只放在 Local-Scope，不放进 `memory/`：

```text
D:\XinYu\XinYu-Local-Scope\SourceMaterials\dialogue_observation\
  raw\        # owner 自己放入的原始文本/导出数据
  extracted\  # 从游戏/数据集抽出的中间文本
  candidates\ # 脚本输出的候选片段 jsonl
  curated\    # owner 手工筛完后的规则卡
  templates\  # 卡片模板
```

这些文件默认只是本地观察材料：

- 不自动进入 XinYu memory。
- 不自动进入 voice profile。
- 不自动进入 learning library。
- 不作为模型训练数据。
- 不触发 runtime 行为变化。

---

## 2. 材料优先级

第一阶段先用现成语料或少量导出文本验证筛选流程，不急着拆游戏包。

优先级：

1. 少量中文自然对话片段。
2. 情绪/人格标签较清楚的中文对话数据。
3. 游戏剧情对白数据集。
4. owner 合法持有游戏的本地导出文本。
5. 小说片段的少量手工摘录。

不要一开始处理整本小说或整部游戏。先做 50 条候选，人工筛到 10 条规则。

---

## 3. 候选片段抽取

把本地材料放到：

```text
D:\XinYu\XinYu-Local-Scope\SourceMaterials\dialogue_observation\raw
```

支持的轻量格式：

- `.txt`
- `.md`
- `.json`
- `.jsonl`
- `.csv`
- `.tsv`

运行：

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_dialogue_observation_extract.py `
  --input D:\XinYu\XinYu-Local-Scope\SourceMaterials\dialogue_observation\raw `
  --output D:\XinYu\XinYu-Local-Scope\SourceMaterials\dialogue_observation\candidates\dialogue_candidates.jsonl
```

脚本会输出候选卡片，包含：

- `source_file`
- `line_index`
- `speaker`
- `text_excerpt`
- `prev_excerpt`
- `next_excerpt`
- `signals`
- `reject_risks`
- `xinyu_rule_draft`
- `xinyu_do_not_learn`
- `boundary`

脚本只做候选筛选，不判断最终可学。

---

## 4. 人工筛选标准

保留：

- 熟人第二次/第三次见面。
- 对方情绪低但没明说。
- 玩笑转认真。
- 被冒犯后的自然修复。
- 记得旧事但不解释“我记得”。
- 短句里的在意。
- 关系距离变化很轻，但能看出来。

删除：

- 菜单、UI、教程、物品说明。
- 世界观设定说明。
- 大段独白。
- 酒保/服务/客服话术。
- 成人段子。
- 过度犬儒或冷幽默。
- 强制爱、病娇、操控、极端占有。
- 为了戏剧冲突故意不沟通。
- 一看就是角色模板的台词。

---

## 5. 规则卡格式

最终进入 `curated/` 的不是原台词，而是 owner 自己提炼的规则卡。

模板：

```text
source_ref:
scene_summary:
relationship_state:
trigger:
observed_response_strategy:
relationship_effect:
xinyu_rule:
xinyu_do_not_learn:
review_status: owner_observation_only
stable_profile_write: blocked
```

例子：

```text
source_ref: VA-11 Hall-A / 常客回访 / owner note
scene_summary: 对方带着上次没说完的低落回来，但表面还在闲聊。
relationship_state: 熟人；可以轻微玩笑，但不能把距离推太满。
trigger: 对方提到旧事，像是在试探“你还记不记得”。
observed_response_strategy: 不解释记忆，不长篇安慰，只接住一个具体细节，留空间。
relationship_effect: 对方愿意继续说，关系靠近一点。
xinyu_rule: owner 提旧话题时，直接接具体细节；不要说“根据记忆/我检索到”。
xinyu_do_not_learn: 不学酒保接待口吻，不学成人玩笑，不把关系写成服务关系。
review_status: owner_observation_only
stable_profile_write: blocked
```

---

## 6. 晋升边界

规则卡进入 XinYu 之前必须再过一层 review。

可以进入的形式：

- voice lesson candidate
- short-term trial habit candidate
- evaluation case
- future tiny-self-core training label candidate

不能直接进入：

- stable personality profile
- stable relationship memory
- source facts
- action permissions
- dream/reflection queue
- model training dataset

任何一条规则都必须是 owner 重新表述后的行为规则，不能是大段原文台词。

---

## 7. 当前最小实施目标

第一轮只做：

1. 放入少量本地材料。
2. 抽取候选 `dialogue_candidates.jsonl`。
3. 人工筛出 10 条以内。
4. 手写规则卡到 `curated/owner_rule_cards.md`。
5. 暂不接入 XinYu runtime。

成功标准：

- 规则能解释“XinYu 下一次遇到类似场景该怎么接”。
- 规则没有复制角色人格。
- 规则没有把小说/游戏设定当事实。
- 规则不会强化客服腔。
- 规则不会增加过度亲密、过度承诺或戏剧化。

