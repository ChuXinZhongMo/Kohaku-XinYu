# XinYu 后续自治执行计划 3

Date: 2026-05-18
Working directory: `D:\XinYu`

## Goal

`plan-next-2.md` 已完成。本计划继续做减、做空、做清晰，优先处理仍然低风险、能提高后续自治稳定性的缺口。

## Execution Rules

- 每个 batch 只处理一个能力组。
- 先侦察，再小范围修改，再聚焦测试，再写 worklog。
- 不提交 git。
- 不打印 secrets、token、原始 QQ 内容、私人记忆正文。
- 不使用 destructive git 命令。
- mutation-capable smoke 必须使用 `--restore-after`，并尽量加 `--diff-lines 0`。
- 本计划完成后继续审计缺口；若仍有高价值低风险项，生成 `plan-next-4.md` 并继续。

## Batch 1: Mutation-Capable Smoke Safety Guard

Goal: 防止 source learning / memory smoke 手动运行时污染 ignored `memory/**`。

Tasks:
- 侦察 `tests/smoke/learning/integration/*_smoke.py` 的 `--restore-after` 支持面。
- 增加一个 ops validation guard，列出会 mutate memory 且支持 restore 的 smoke。
- 若改动面足够小，给最容易误用的 source learning smokes 增加安全提示或默认保护测试。
- 不改变 quick smoke 的既有语义，除非测试证明安全。

Acceptance:
- 有自动化测试覆盖 guard。
- guard 不读取 memory 正文。
- worklog 写明哪些 smoke 必须带 restore。

## Batch 2: Source Engine Dead Helper Prune

Goal: 删除或压缩已被 `xinyu_state_io` import 覆盖的本地 I/O helper 定义，减少重复代码。

Scope:
- `custom/learner_integration_engine.py`
- `custom/source_integration_gate_engine.py`

Tasks:
- 确认 `read_text` / `write_text` / `extract_value` 没有被外部依赖为本地实现。
- 删除被覆盖的本地定义，保留旧导入后的函数名。
- 跑 source parser/learning focused tests。

Acceptance:
- 行为不变。
- source material parser tests and learning closed loop tests pass.

## Batch 3: P0 Triage Scanner Performance

Goal: 让 `memory_structured_p0_triage.py` 从重复全树扫描变成一次性索引或窄扫描。

Tasks:
- 侦察当前 `find_reference_files` 性能瓶颈。
- 用一次 `rg --files` / 一次内容扫描或缓存机制替代每个 item 重复扫描。
- 保持不读取/打印 memory bodies 的隐私边界。
- 跑 triage tests，并刷新 P0 triage reports。

Acceptance:
- 测试通过。
- 报告内容等价或更精确。
- 生成报告时间明显下降，记录前后耗时。

## Batch 4: Low-Risk Durable Runtime State Store Boundary

Goal: 再收一个 P0 durable runtime state，但避开 QQ/private 高风险队列。

Preferred candidate:
- `memory/context/daily_digest.json`

Tasks:
- 侦察 `services/daily_digest.py` 和相关 tests/smokes。
- 增加轻量 store owner，旧路径保留兼容 fallback。
- 更新 P0 triage target/decision。

Acceptance:
- 至少一个 durable runtime state 有明确 store owner。
- focused tests/smoke pass。
- 不打印 digest body。

## Batch 5: Validation, Audit, and Next Plan Decision

Tasks:
- `git diff --check`
- Full app pytest.
- Quick smoke with `--restore-after`.
- Desktop typecheck/build if touched or final closeout requires it.
- Refresh change package plan/group audit.
- Write final audit.
- 若仍有高价值低风险项，生成下一份 plan 并继续。
