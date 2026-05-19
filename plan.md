# XinYu 五件事稳定化计划

日期：2026-05-18
工作目录：`D:\XinYu`

## 总目标

上一轮七项减法已经闭环。下一阶段不急着加新功能，而是把这轮减法固化成更稳的地基，再继续向“更像活人，但不装成人”的方向推进。

执行顺序：

1. 版本固化
2. source/learning 链路继续收束
3. bridge plugin 外壳继续收束
4. 人格/活人感评测集
5. memory/library/cases 内容边界整理

每个 batch 规则：

- 只处理一个能力组。
- 先侦察，再小范围修改，再跑聚焦测试。
- 每轮结束写 `D:\XinYu\worklog\...`。
- 不提交 git。
- 不打印 secrets、token、原始 QQ 内容、私人记忆正文。
- 不使用 `git reset --hard` 或 `git checkout --`。
- 如果失败，先修；修不了就写恢复点。

## 1. 版本固化

目标：把当前巨大 dirty worktree 按能力组归档清楚，避免之后“几百个改动混在一起看不懂”。

要做：

- 增加一个只读 git status 分组工具。
- 按能力组标记改动：docs、core、adapters、stores、services、ops、tests、desktop、memory-data、archive/delete、unknown。
- 生成当前改动分组报告。

验收：

- 有可重复运行的分组工具。
- 有报告说明当前 dirty worktree 的大类分布。
- 工具不读取或打印私人记忆正文，只看路径和 git 状态。

直接影响：

- 后续要拆提交、回查风险、继续重构时，不再面对一整坨无法判断的改动。

## 2. Source/Learning 链路继续收束

目标：把 source request、search result、material 等重复协议解析函数收成公共工具。

要做：

- 新增或完善 `custom/source_protocol_utils.py`。
- 先收纯解析/渲染 helper，不改学习主流程。
- 旧模块保留原函数名作为 shim，内部转调公共 helper。

候选模块：

- `custom/source_request_planner_engine.py`
- `custom/source_search_resolver_engine.py`
- `custom/source_search_provider_engine.py`
- `custom/search_result_gate_engine.py`
- `custom/source_integration_gate_engine.py`

验收：

- source request/result 的字段读写不丢字段。
- 相关 smokes 通过：
  - source request planner
  - source search resolver
  - source search provider
  - source learning chain

直接影响：

- 外部资料学习链更稳定，后续改字段协议不用在多个模块重复改。

## 3. Bridge Plugin 外壳继续收束

目标：减少 `source_*_bridge_plugin.py` 等维护插件重复的 `on_load -> should_run -> run engine -> set_state -> trace` 外壳。

要做：

- 在 `custom/maintenance_bridge_utils.py` 增加薄 runner。
- 保留每个 plugin 的类名、name、priority、特殊 gate 和 trace 文案。
- 先迁移低风险同构插件，不强行合并特殊插件。

验收：

- plugin 兼容入口不变。
- maintenance bridge tests 通过。
- source/learning quick smoke 通过。

直接影响：

- 维护插件数量可以保留，但重复样板减少，后续加/改 maintenance plugin 更容易。

## 4. 人格/活人感评测集

目标：不要靠“感觉”调 XinYu 的人格。建立一组可回归的真实对话压力样本。

要做：

- 新增 persona realism evaluation cases。
- 覆盖困倦、撒娇、失望、冷淡、技术讨论、长时间未见、主人要求她像人但不能装成人。
- 断言边界：
  - 不背设定卡。
  - 不自称真实生物。
  - 情绪可以影响语气，但不能改事实。
  - 单轮情绪不能直接改稳定人格。

验收：

- 有 pytest 或 smoke 可以跑。
- 评测使用合成样例，不读取原始私人聊天。
- 失败时能指出是“太工具”“太表演”“越界拟人”“事实被情绪污染”等哪一类。

直接影响：

- 后续调“活生生的人”有尺子，不靠玄学手感。

## 5. Memory/Library/Cases 内容边界整理

目标：结构已经分清，下一步要让内容也更清楚。

要做：

- 增加只读边界审计：扫描路径和 frontmatter 类型，不打印正文。
- 标记疑似混放：
  - 外部资料出现在 memory 稳定层。
  - 对话案例出现在知识库。
  - runtime 临时状态出现在 library/cases。
  - 私人记忆正文被当作公共资料。
- 生成整理建议，不自动删除私人内容。

验收：

- 有边界审计工具。
- 有边界报告。
- 不输出原始私人记忆正文。

直接影响：

- XinYu 不会把资料当记忆，不会把案例当现实，也不会被陈旧内容拖住。

## 总验收

完成后必须通过：

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300

cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

并写最终 worklog，说明：

- 已固化什么。
- 合并了什么。
- 保留了什么兼容入口。
- 哪些内容只审计不自动删除。
- 后续还剩什么风险。
