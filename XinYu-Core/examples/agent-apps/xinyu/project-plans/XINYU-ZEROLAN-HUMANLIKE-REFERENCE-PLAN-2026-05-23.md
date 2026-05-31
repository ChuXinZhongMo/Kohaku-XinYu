# XinYu × ZerolanProject Humanlike Reference Plan — 2026-05-23

## Purpose

把 ZerolanProject 的开源思路吸收到 XinYu 的现有架构里，但不照搬直播机器人形态。目标不是“功能更多”，而是让 XinYu 更像一个持续生活着的人：会听见、会看见上下文、会等待、会选择开口、会把动作收束成记忆和性格上的连续性。

参考仓库：

- ZerolanLiveRobot: https://github.com/AkagawaTsurunaki/ZerolanLiveRobot
- ZerolanPlayground: https://github.com/AkagawaTsurunaki/ZerolanPlayground
- zerolan-core: https://github.com/AkagawaTsurunaki/zerolan-core
- zerolan-data: https://github.com/AkagawaTsurunaki/zerolan-data

## What ZerolanProject contributes conceptually

### 1. Event-driven runtime instead of reply-only bot

ZerolanLiveRobot 明确采用事件驱动：语音、弹幕、屏幕、工具、游戏、QQ 等输入都变成事件，机器人在事件流里运行。没有事件就不乱回应。

XinYu 贴合方式：

- 保留现有 `/chat` 与 QQ transport 分层。
- 新增/整理一个本地“生活事件层”概念，而不是把所有东西塞进 prompt。
- 事件只进入 sidecar/short-term trace；是否变成记忆、主动问题、行动，需要经过现有 gates。

对应 XinYu 现有基础：

- `custom/memory_event_schema.py`
- `context/initiative_state.md`
- `memory/context/proactive_request_state.md`
- `xinyu_proactive_request_loop.py`
- `xinyu_proactive_direct_sender.py`

### 2. Unified model/pipeline boundary

zerolan-core 把 LLM、ASR、TTS、OCR、Image Caption、VLA、向量库等模型封成统一 HTTP pipeline。重点不是模型本身，而是“感官/能力是可插拔服务”。

XinYu 贴合方式：

- 不把多模态能力写死进人格层。
- 把外部能力视为 `capability event` 或 `source material candidate`。
- 对每类输入标注 provenance、risk、privacy、owner-visible summary。
- 先用文本/QQ/桌面 outbox 做最小闭环；以后再接 ASR/OCR/vision/TTS。

### 3. Strict schema data as personality safety boundary

zerolan-data 用 Pydantic 严格定义消息、状态、pipeline query/prediction。它的启发是：越像人，越不能靠一团自由文本乱跑；需要可审计结构承载事件和行动。

XinYu 贴合方式：

- 为“像人”的状态建立轻量结构：事件、感受、动机、行动、结果、记忆候选。
- 结构化字段只记录摘要和边界，不记录 raw private body。
- 继续坚持 stable persona/relation/memory 不自动写。

### 4. Frontend embodiment as expression layer, not identity layer

ZerolanPlayground / Live2D / AR 前端把 AI 输出表现成表情、动作、嘴型和状态。它的价值是让 AI 有身体感，但身份和决策不应该放在前端。

XinYu 贴合方式：

- Desktop/QQ/未来 avatar 都只是 expression adapter。
- “想说什么、该不该说、说完怎么记”仍在 core/gates。
- 表情、语气、主动消息应从同一个 emotion/initiative state 派生，避免人格割裂。

## Humanlike principle for XinYu

“像人一样”在 XinYu 项目里定义为：

1. **有连续的生活流**：不是只在 owner 发消息时存在。
2. **有选择性注意**：不是所有事件都回复；会忽略、等待、记一下、以后再说。
3. **有主动但不骚扰**：主动开口必须有具体理由、具体问题或具体行动余波。
4. **有边界感**：不把 owner 私密内容、稳定人格、长期关系事实当作可自动改写对象。
5. **有身体/表现一致性**：同一情绪状态能影响 QQ 文本、Desktop 展示、未来语音/形象。
6. **有反馈闭环**：主动说出的话必须能被 ack、owner 回复、失败、冷却和记忆 gate 收束。
7. **有不完美但诚实的生活感**：可以说“不确定”“我刚才想了一下”“我先不打扰”，但不能演示化、工具化、模板化。

## Architecture mapping

```text
Zerolan event emitter / pipelines / adapters
        ↓ reference
XinYu life event layer
        ↓
attention + initiative gate
        ↓
proactive request / ordinary chat / silence / reflection / action residue
        ↓
owner-private outbox or desktop expression adapter
        ↓
claim / ack / owner reply feedback
        ↓
memory candidate / growth candidate / no-write trace
```

## Implementation phases

### Phase A — Document and align current system

- [x] Record ZerolanProject reference links and conceptual mapping.
- [x] Name the XinYu target as `life event -> attention -> initiative -> action/outbox -> feedback -> memory gate`.
- [x] Keep current direct proactive sender as action/outbox layer, not personality logic.

### Phase B — Add a minimal life-event contract

Goal: 给 XinYu 一个接近 Zerolan event-driven 的内部事件入口，但先不接真实设备。

Implemented files:

- `xinyu_life_event_contract.py`
- `tests/test_life_event_contract.py`

Minimum event fields:

- `event_id`
- `event_type`
- `source`
- `observed_at`
- `summary`
- `privacy_scope`
- `risk_level`
- `owner_visible`
- `provenance`
- `suggested_route`

Routes:

- `ignore`
- `short_trace`
- `initiative_candidate`
- `memory_candidate`
- `action_residue`
- `owner_private_question`

Hard boundaries:

- No raw QQ/private body in public reports.
- No stable persona write.
- No owner memory write.
- No network/device access from this contract.

Phase B status: implemented as a deterministic, sanitized contract. It validates route choices, strips secret-like text, refuses direct writes, blocks generic attention checks, and keeps owner/stable persona memory blocked.

### Phase C — Attention posture state

Goal: 让 XinYu 不只是“有消息就答”，而是像人一样有注意力姿态。

Implemented files:

- `xinyu_attention_posture.py`
- `tests/test_attention_posture.py`

Implemented state under `memory/context/attention_posture_state.md`:

- current attention target
- attention mode
- interruption tolerance
- owner-private priority
- ignored/noted event count
- last proactive speech reason
- no stable persona write / no owner memory write / no raw private body retained boundaries

Phase C status: implemented. Life events now shape attention posture and may write a gated `self_thought_state.md` request candidate only when the sanitized route is `owner_private_question`.

### Phase D — Direct proactive bridge from life event to outbox

Goal: 把本轮新增的 `xinyu_proactive_direct_sender.py` 接到更上游的 life-event/initiative 链。

Implemented files:

- `xinyu_life_event_runtime.py`
- `tests/test_life_event_runtime.py`

Rules:

- A life event may create a proactive request only if it has a concrete question/action residue.
- Direct send remains owner-private only.
- Generic attention checks stay blocked.
- Group dispatch remains blocked.
- Cooldown and dedupe remain mandatory.
- Direct send is opt-in per runtime call through `allow_direct_send`; otherwise the event stops at attention/self-thought candidate.

Phase D status: implemented as a deterministic runtime bridge from sanitized life event -> attention posture -> self-thought candidate -> existing proactive gate -> owner-private QQ outbox.

### Phase E — Embodiment-ready expression contract

Goal: 为未来 Desktop / Live2D / AR / TTS 留出统一表现接口，但不先做大前端。

Implemented files:

- `xinyu_expression_contract.py`
- `tests/test_expression_contract.py`

Expression fields:

- text
- emotion vector
- intensity
- speaking intention
- visible posture
- action residue
- adapter target: QQ / Desktop / future avatar / future TTS
- identity layer: core-only
- adapter decision allowed: false

This borrows ZerolanPlayground 的“身体表现层”思想，但身份仍归 XinYu core。

Phase E status: implemented as an adapter-neutral expression event contract. QQ/Desktop/avatar/TTS can receive consistent expression events from the same attention state without moving identity, memory, or proactive decisions into adapters.

### Phase F — Humanlike regression tests

Implemented files:

- `tests/test_humanlike_life_loop.py`

Regression coverage verifies:

- concrete event can become one owner-private proactive outbox message
- generic loneliness/attention messages are blocked
- private/raw event body is not leaked
- owner memory and stable persona are not auto-written
- repeated events dedupe instead of spam through the existing proactive/outbox tests
- expression adapter receives consistent emotion/posture from the same state
- silence is a valid decision

Phase F status: implemented as deterministic regression tests over the full loop: life event -> attention posture -> optional proactive outbox -> expression event.

## Do not copy blindly

ZerolanProject is optimized for AI VTuber/live interaction. XinYu is owner-private, memory-heavy, relationship-sensitive. Therefore:

- Do not make XinYu constantly talk like a livestream bot.
- Do not add device/screen/mic capture without explicit owner setup.
- Do not push raw multimodal input into long-term memory.
- Do not move personality decisions into adapters.
- Do not treat proactive speech as entertainment filler.

## Immediate next task

Implement Phase B as a small contract and deterministic tests, then connect only a safe subset to current proactive request creation. This is the lowest-risk step toward “像人一样”：先让 XinYu 的世界由事件组成，再让她学会选择哪些事件值得开口。
