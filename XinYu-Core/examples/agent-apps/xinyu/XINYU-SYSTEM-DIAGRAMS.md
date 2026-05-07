# XinYu System Diagrams

这份图是给当前 XinYu 本地运行态看的：核心运行链路是 NapCat QQ -> `xinyu_qq_gateway.py` -> `xinyu_core_bridge.py` -> XinYu Agent Runtime。v1 已接入 shadow/canary 观察，但还不是主回复路径。

## 1. 整体架构图

```mermaid
flowchart TB
    Owner[Owner / QQ 私聊] --> NapCat[NapCat / OneBot]
    Group[QQ群 / 群成员] --> NapCat
    NapCat <-->|反向 WebSocket :6199| QQGateway[xinyu_qq_gateway.py]

    QQGateway -->|POST /chat :8765| Bridge[xinyu_core_bridge.py]
    QQGateway -->|POST /qq/outbox/claim| OutboxClaim[Outbox claim]
    QQGateway -->|POST /qq/outbox/ack| OutboxAck[Outbox ack]
    QQGateway -->|POST /codex/execute| CodexEndpoint[Codex delegate endpoint]
    QQGateway -->|POST /learning/*| LearningEndpoint[Learning endpoints]

    subgraph CoreBridge["Core Bridge Runtime"]
        Bridge --> Session[Agent session manager]
        Bridge --> Presence[Runtime presence / health]
        Bridge --> Sidecars[Turn sidecars]
        Bridge --> MainAgent[XinYu Agent Runtime]
        Bridge --> V1Shadow[v1 shadow runner]
        Bridge --> Maintenance[Autonomous maintenance loop]
        Bridge --> Proactive[Proactive / QQ outbox]
        Bridge --> Codex[Codex delegate]
        Bridge --> Learning[Learning pipeline]
    end

    subgraph V1["xinyu_v1 当前状态"]
        V1Shadow --> V1Norm[Normalizer]
        V1Norm --> V1Router[Hybrid router]
        V1Router --> V1Memory[Memory orchestrator]
        V1Router --> V1Emotion[Emotion state machine]
        V1Router --> V1Reason[Local / slow reasoning]
        V1Shadow --> V1Canary[Canary readiness]
        V1Canary -->|达标后只建议| Proactive
    end

    subgraph Memory["Memory / Runtime State"]
        MContext[memory/context/*.md]
        MSelf[memory/self/*.md]
        MEmotion[memory/emotions/*.md]
        MArchive[memory/archive + dialogue archive]
        Runtime[runtime/*.jsonl / state]
        LearningStore[learning/self_found + owner_supplied]
    end

    Sidecars --> MContext
    Sidecars --> MSelf
    Sidecars --> MEmotion
    Sidecars --> MArchive
    Presence --> Runtime
    V1Memory --> Runtime
    V1Canary --> Runtime
    V1Canary --> MContext
    Learning --> LearningStore
    Learning --> MContext
    Codex --> Runtime
    Codex --> Learning
    Proactive --> MContext
    Proactive --> QQGateway
    MainAgent -->|visible reply| Bridge
    Bridge -->|reply| QQGateway
    QQGateway --> NapCat
```

## 2. 单轮消息流程图

```mermaid
sequenceDiagram
    participant U as QQ 用户 / Owner
    participant N as NapCat
    participant G as xinyu_qq_gateway.py
    participant B as xinyu_core_bridge.py
    participant S as Sidecars
    participant A as XinYu Agent Runtime
    participant V as v1 shadow
    participant M as Memory / Runtime
    participant O as QQ outbox

    U->>N: 发送私聊 / 群消息
    N->>G: OneBot WebSocket event
    G->>G: 白名单、群触发、附件、合并片段
    G->>B: POST /chat

    B->>M: record_turn_started
    B->>S: curiosity / private thought / uncertainty reply mark
    B->>S: event sourcing
    B->>V: shadow_payload(payload)
    V->>M: v1 raw event + shadow trace
    V->>M: canary readiness state
    V-->>B: route / trace_id / notes, no visible reply

    B->>S: persona observe / context retrieval / continuity handoff
    B->>A: inject live context + user event
    A-->>B: draft chunks

    alt Owner self-code / Codex task
        B->>B: approval / watchdog / route check
        B->>O: enqueue report or generated artifact if needed
        B-->>G: short visible status
    else Normal chat
        B->>B: optional renderer
        B->>B: final reply guard / dedupe / empty fallback
        B->>S: expression learning / learning closed loop
        B->>M: residue, archive, candidates, memory self-review
        B->>M: interaction journal / dialogue tail
        B->>O: promised followup / sticker / proactive sync if needed
        B-->>G: final reply
    end

    G->>N: OneBot send message
    N-->>U: 可见回复
    G->>B: /internal/message/ack 或 /qq/outbox/ack
    B->>M: sent reply index / dispatch state
    B->>M: record_turn_finished
```

## 3. 后台运转图

```mermaid
flowchart LR
    Start([Core 启动]) --> Health[/health ready/]
    Health --> InitDelay[autonomous initial delay]
    InitDelay --> Loop{每个 maintenance interval}

    Loop --> AutoSession[维护专用 Agent session]
    AutoSession --> MaintenanceTurn[注入 autonomous maintenance event]
    MaintenanceTurn --> SidecarRun[维护侧车批处理]

    subgraph MaintenanceSidecars["维护侧车"]
        Watched[watched source check]
        Digest[daily digest]
        ReviewInbox[review inbox maintenance]
        Goldmark[goldmark dehydration]
        SelfThought[self thought loop]
        LearningClosed[learning closed-loop self-thought]
        ProactiveLoop[proactive request loop]
        MemoryReview[memory self-review]
    end

    SidecarRun --> Watched
    SidecarRun --> Digest
    SidecarRun --> ReviewInbox
    SidecarRun --> Goldmark
    SidecarRun --> SelfThought
    SelfThought --> LearningClosed
    SelfThought --> ProactiveLoop
    SidecarRun --> MemoryReview

    Watched --> State[memory/context state files]
    Digest --> State
    ReviewInbox --> State
    Goldmark --> State
    SelfThought --> State
    LearningClosed --> State
    ProactiveLoop --> ProactiveState[proactive_request_state.md]
    MemoryReview --> State

    ProactiveState -->|ready + owner enabled + cooldown ok| QQOutbox[qq_outbox_queue.json]
    V1Ready[v1 canary readiness] -->|只在 shadow 达标后建议| QQOutbox
    CodexDone[Codex completion / artifacts] --> QQOutbox
    Followup[promised followup] --> QQOutbox

    QQOutbox --> GatewayClaim[QQ gateway claim]
    GatewayClaim --> QQSend[OneBot send]
    QQSend --> GatewayAck[ack result]
    GatewayAck --> DispatchState[dispatch state / sent reply index]

    SidecarRun --> RuntimeTrace[runtime traces jsonl]
    DispatchState --> RuntimeTrace
    State --> RuntimePresence[runtime_program_awareness.md]
    RuntimeTrace --> RuntimePresence

    RuntimePresence --> Sleep[sleep until next interval]
    Sleep --> Loop
```

## 当前主边界

- `xinyu_core_bridge.py` 仍是主控制面：聊天、学习、Codex、主动发送、健康检查都从这里汇合。
- `xinyu_qq_gateway.py` 是当前 QQ 适配层；AstrBot 不在当前链路里。
- v1 现在是 shadow/canary：记录路线、观察错误率、达标后给 owner 发建议，但不自动切全量。
- 稳定记忆写入不是模型直接改文件，而是经由 event sourcing、archive、candidate extraction、memory self-review 等门控侧车。
- 主动联系不直接发送：先生成 request/outbox，再由 gateway claim/ack，避免无状态乱发。
