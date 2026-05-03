import React from 'react'
import ReactDOM from 'react-dom/client'
import {
  Activity,
  Bell,
  Brain,
  Clock3,
  Database,
  Eye,
  Heart,
  MessageSquare,
  Radio,
  Send,
  Sparkles,
  Wifi,
  X,
  Zap
} from 'lucide-react'
import './style.css'

type JsonRecord = Record<string, unknown>

type DesktopEvent = {
  id?: string
  type: string
  ts?: string
  payload?: JsonRecord
  severity?: string
}

type Snapshot = {
  snapshotAt?: string
  lastEventId?: string
  services?: unknown[]
  health?: JsonRecord
  eventBus?: JsonRecord
  proactiveInbox?: unknown[]
  recentTurns?: unknown[]
  recentMemoryEvents?: unknown[]
  notes?: string[]
}

type GatewayStatus = {
  connected?: boolean
  connecting?: boolean
  lastEventId?: string
  lastError?: string
  httpUrl?: string
  wsUrl?: string
  snapshotAt?: string
}

type AppState = {
  snapshot: Snapshot | null
  gateway: GatewayStatus | null
  events: DesktopEvent[]
  commands: CommandState[]
  proactiveActions: Record<string, ProactiveAction>
  proactiveInbox: unknown[]
  recentTurns: unknown[]
  recentMemoryEvents: unknown[]
  selected: unknown
}

type CommandState = {
  commandId: string
  textPreview: string
  status: 'sending' | 'accepted' | 'started' | 'finished' | 'failed'
  message: string
  turnId?: string
  createdAt: string
}

type ProactiveAction = 'read_locally' | 'approve_qq' | 'dismiss'

const avatarSrc = './xinyu-avatar.png'
const characterSrc = './xinyu-character.png'

const finalProactiveStatuses = new Set([
  'sent',
  'answered',
  'failed',
  'expired',
  'blocked',
  'none',
  'read_locally',
  'dismissed',
  'queued_qq'
])

function App(): JSX.Element {
  const [input, setInput] = React.useState('')
  const [state, setState] = React.useState<AppState>({
    snapshot: null,
    gateway: null,
    events: [],
    commands: [],
    proactiveActions: {},
    proactiveInbox: [],
    recentTurns: [],
    recentMemoryEvents: [],
    selected: null
  })

  React.useEffect(() => {
    let mounted = true
    window.xinyu.getSnapshot().then((snapshot) => {
      if (!mounted) return
      setState((current) => applySnapshot(current, snapshot))
    })
    window.xinyu.getGatewayStatus().then((gateway) => {
      if (!mounted) return
      setState((current) => ({ ...current, gateway: asRecord(gateway) as GatewayStatus }))
    })
    const offEvent = window.xinyu.onCoreEvent((event) => {
      setState((current) => applyEvent(current, event))
    })
    const offStatus = window.xinyu.onGatewayStatus((gateway) => {
      setState((current) => ({ ...current, gateway: asRecord(gateway) as GatewayStatus }))
    })
    return () => {
      mounted = false
      offEvent()
      offStatus()
    }
  }, [])

  const connected = Boolean(state.gateway?.connected)
  const statusText = connected ? '在线' : state.gateway?.connecting ? '连接中' : '离线'
  const sending = state.commands.some((command) => ['sending', 'accepted', 'started'].includes(command.status))
  const stats = buildStats(state)

  async function submitChat(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const text = input.trim()
    if (!text || sending) {
      return
    }
    const commandId = createCommandId()
    const command: CommandState = {
      commandId,
      textPreview: compact(text, 180),
      status: 'sending',
      message: '正在提交到聊天接口',
      createdAt: new Date().toISOString()
    }
    setInput('')
    setState((current) => ({
      ...current,
      commands: [command, ...current.commands].slice(0, 12),
      selected: command
    }))
    const result = asRecord(await window.xinyu.sendChat({ text, commandId }))
    if (result.accepted === false) {
      setInput((current) => current || text)
      setState((current) => updateCommand(current, commandId, 'failed', String(result.error || 'chat_request_failed')))
      return
    }
    setState((current) => updateCommand(current, commandId, 'accepted', 'HTTP /chat returned', String(result.turnId || '')))
  }

  async function ackProactive(candidateId: string, action: ProactiveAction): Promise<void> {
    if (!candidateId || state.proactiveActions[candidateId]) {
      return
    }
    setState((current) => ({
      ...current,
      proactiveActions: { ...current.proactiveActions, [candidateId]: action },
      selected: { candidateId, action, status: '正在提交主动提醒回执' }
    }))
    const result = asRecord(await window.xinyu.ackProactive({ candidateId, action }))
    if (result.accepted === false) {
      setState((current) => {
        const { [candidateId]: _removed, ...rest } = current.proactiveActions
        return {
          ...current,
          proactiveActions: rest,
          selected: result
        }
      })
      return
    }
    setState((current) => ({ ...current, selected: result }))
  }

  return (
    <main className="app-shell">
      <div className="soft-grid" />
      <header className="titlebar">
        <div className="brand-lockup">
          <img src={avatarSrc} alt="心玉" />
          <div>
          <h1>心玉</h1>
            <p>私有频道</p>
          </div>
        </div>
        <div className="title-actions">
          <div className={`connection-pill ${connected ? 'ok' : 'warn'}`}>
            <Radio size={15} />
            <span>{statusText}</span>
          </div>
          <div className="sync-pill">
            <Clock3 size={14} />
            <span>{formatTime(state.snapshot?.snapshotAt || state.gateway?.snapshotAt)}</span>
          </div>
        </div>
      </header>

      <section className="workspace">
        <aside className="identity-rail">
          <IdentityPanel connected={connected} stats={stats} gateway={state.gateway} />
          <ServicePanel
            gateway={state.gateway}
            services={state.snapshot?.services || []}
            onSelect={(item) => setState((current) => ({ ...current, selected: item }))}
          />
        </aside>

        <section className="conversation-stage">
          <ConversationHeader connected={connected} stats={stats} />
          <ChatTimeline
            commands={state.commands}
            turns={state.recentTurns}
            snapshotAt={state.snapshot?.snapshotAt}
            onSelect={(item) => setState((current) => ({ ...current, selected: item }))}
          />
          <ChatInput value={input} sending={sending} onChange={setInput} onSubmit={submitChat} />
        </section>

        <aside className="intel-rail">
          <ProactiveInbox
            items={state.proactiveInbox}
            pending={state.proactiveActions}
            onAck={ackProactive}
            onSelect={(item) => setState((current) => ({ ...current, selected: item }))}
          />
          <MemoryShelf
            items={state.recentMemoryEvents}
            onSelect={(item) => setState((current) => ({ ...current, selected: item }))}
          />
          <EventStream events={state.events} onSelect={(item) => setState((current) => ({ ...current, selected: item }))} />
          <Inspector selected={state.selected || state.snapshot || {}} />
        </aside>
      </section>
    </main>
  )
}

function IdentityPanel(props: {
  connected: boolean
  stats: ReturnType<typeof buildStats>
  gateway: GatewayStatus | null
}): JSX.Element {
  return (
    <section className="identity-panel">
      <div className="mascot-scene">
        <div className="mascot-ring" />
        <img className="character-art" src={characterSrc} alt="心玉形象" />
        <span className={`live-dot ${props.connected ? 'ok' : 'warn'}`} />
      </div>
      <div className="identity-copy">
        <p className="eyebrow">心玉频道</p>
        <h2>心玉の疗养室</h2>
        <p>私聊、记忆回声和主动提醒都在这里。</p>
      </div>
      <div className="stat-grid">
        <StatChip label="对话" value={String(props.stats.turns)} icon={<MessageSquare size={14} />} />
        <StatChip label="记忆" value={String(props.stats.memories)} icon={<Brain size={14} />} />
        <StatChip label="提醒" value={String(props.stats.proactive)} icon={<Bell size={14} />} />
        <StatChip label="事件" value={String(props.stats.events)} icon={<Activity size={14} />} />
      </div>
      <div className="endpoint-line">
        <Wifi size={14} />
        <span>{props.gateway?.httpUrl || 'http://127.0.0.1:8765'}</span>
      </div>
    </section>
  )
}

function StatChip(props: { label: string; value: string; icon: React.ReactNode }): JSX.Element {
  return (
    <div className="stat-chip">
      {props.icon}
      <strong>{props.value}</strong>
      <span>{props.label}</span>
    </div>
  )
}

function ServicePanel(props: {
  services: unknown[]
  gateway: GatewayStatus | null
  onSelect: (item: unknown) => void
}): JSX.Element {
  const rows = [
    {
      service: 'desktop_ws',
      status: props.gateway?.connected ? 'ready' : props.gateway?.connecting ? 'connecting' : 'offline',
      message: props.gateway?.wsUrl || ''
    },
    ...props.services.map(asRecord)
  ]
  return (
    <section className="rail-section">
      <SectionTitle icon={<Zap size={15} />} title="运行状态" />
      <div className="service-list">
        {rows.map((row, index) => {
          const status = String(row.status || 'unknown')
          return (
            <button className="service-row" key={`${String(row.service || 'service')}-${index}`} onClick={() => props.onSelect(row)}>
              <span className={`status-light ${status === 'ready' ? 'ok' : 'warn'}`} />
              <span>{serviceLabel(String(row.service || 'service'))}</span>
              <strong>{serviceStatusLabel(status)}</strong>
            </button>
          )
        })}
      </div>
      {props.gateway?.lastError ? <div className="error-note">{props.gateway.lastError}</div> : null}
    </section>
  )
}

function ConversationHeader(props: { connected: boolean; stats: ReturnType<typeof buildStats> }): JSX.Element {
  return (
    <header className="conversation-header">
      <div>
        <p className="eyebrow">专属频道</p>
        <h2>和心玉的茶话会</h2>
      </div>
      <div className="room-meta">
        <span className={props.connected ? 'meta-ok' : 'meta-warn'}>{props.connected ? '核心在线' : '核心离线'}</span>
        <span>{props.stats.lastLatency}</span>
      </div>
    </header>
  )
}

function ChatTimeline(props: {
  turns: unknown[]
  commands: CommandState[]
  snapshotAt?: string
  onSelect: (item: unknown) => void
}): JSX.Element {
  const turns = props.turns.slice(-8).map(asRecord)
  const renderedCommandIds = new Set(turns.map((turn) => String(turn.commandId || '')).filter(Boolean))
  const renderedTurnIds = new Set(turns.map((turn) => String(turn.turnId || '')).filter(Boolean))
  const pendingCommands = props.commands
    .filter((command) => command.status !== 'finished')
    .filter((command) => !isCommandRenderedByTurn(command, renderedCommandIds, renderedTurnIds))
    .slice()
    .reverse()
  return (
    <div className="chat-timeline">
      <div className="notice-bubble">
        <Sparkles size={15} />
        <span>私有频道已同步到 {formatTime(props.snapshotAt)}。</span>
      </div>

      {turns.length === 0 && pendingCommands.length === 0 ? (
        <div className="message-row xinyu">
          <img src={avatarSrc} alt="" className="message-avatar" />
          <button className="message-bubble" onClick={() => props.onSelect({ type: 'welcome' })}>
          <span className="speaker">心玉</span>
          <p>我在。核心服务接上以后，最近的私聊和记忆会在这里展开。</p>
          </button>
        </div>
      ) : null}

      {turns.map((turn, index) => (
        <React.Fragment key={`${String(turn.turnId || index)}-${index}`}>
          <div className="message-row owner">
            <button className="message-bubble" onClick={() => props.onSelect(turn)}>
              <span className="speaker">你</span>
              <p>{String(turn.textPreview || '...')}</p>
              <small>{formatTurnMeta(turn)}</small>
            </button>
          </div>
          <div className="message-row xinyu">
            <img src={avatarSrc} alt="" className="message-avatar" />
            <button className="message-bubble" onClick={() => props.onSelect(turn)}>
              <span className="speaker">心玉</span>
              <p>{String(turn.replyPreview || statusLabel(String(turn.status || 'finished')))}</p>
              <small>{formatLatency(turn)}</small>
            </button>
          </div>
        </React.Fragment>
      ))}

      {pendingCommands.map((command) => (
        <div className="message-row owner pending" key={command.commandId}>
          <button className="message-bubble" onClick={() => props.onSelect(command)}>
            <span className="speaker">你</span>
            <p>{command.textPreview}</p>
            <small>{commandStatusLabel(command.status)}</small>
          </button>
        </div>
      ))}
    </div>
  )
}

function isCommandRenderedByTurn(command: CommandState, commandIds: Set<string>, turnIds: Set<string>): boolean {
  return commandIds.has(command.commandId) || Boolean(command.turnId && turnIds.has(command.turnId))
}

function ChatInput(props: {
  value: string
  sending: boolean
  onChange: (value: string) => void
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
}): JSX.Element {
  return (
    <form className="composer" onSubmit={props.onSubmit}>
      <input
        value={props.value}
        onChange={(event) => props.onChange(event.currentTarget.value)}
        placeholder="今晚想让心玉接住什么？"
        disabled={props.sending}
      />
      <button type="submit" disabled={props.sending || !props.value.trim()} title="发送">
        <Send size={16} />
      </button>
    </form>
  )
}

function ProactiveInbox(props: {
  items: unknown[]
  pending: Record<string, ProactiveAction>
  onAck: (candidateId: string, action: ProactiveAction) => void
  onSelect: (item: unknown) => void
}): JSX.Element {
  return (
    <section className="intel-section proactive-section">
      <SectionTitle icon={<Bell size={15} />} title="主动提醒" count={props.items.length} />
      {!props.items.length ? <EmptyState text="暂无候选" /> : null}
      {props.items
        .slice()
        .reverse()
        .slice(0, 5)
        .map((item, index) => {
          const row = asRecord(item)
          const candidateId = String(row.candidateId || '')
          const pendingAction = candidateId ? props.pending[candidateId] : undefined
          const disabled = Boolean(pendingAction)
          return (
            <article className="proactive-item" key={`${candidateId || index}-${index}`}>
              <button className="proactive-copy" onClick={() => props.onSelect(item)}>
              <strong>{String(row.focusLabel || row.kind || '心玉提醒')}</strong>
                <span>{String(row.candidatePreview || row.whyNowPreview || '...')}</span>
              <small>{proactiveStatusLabel(String(row.status || 'ready'))} / {deliveryLabel(String(row.deliveryLevel || 'local'))}</small>
              </button>
              <div className="icon-row">
                <button disabled={disabled || !candidateId} onClick={() => props.onAck(candidateId, 'read_locally')} title="本地已读">
                  <Eye size={14} />
                </button>
                <button disabled={disabled || !candidateId} onClick={() => props.onAck(candidateId, 'approve_qq')} title="同意发 QQ">
                  <Send size={14} />
                </button>
                <button disabled={disabled || !candidateId} onClick={() => props.onAck(candidateId, 'dismiss')} title="忽略">
                  <X size={14} />
                </button>
              </div>
            </article>
          )
        })}
    </section>
  )
}

function MemoryShelf(props: { items: unknown[]; onSelect: (item: unknown) => void }): JSX.Element {
  return (
    <section className="intel-section">
      <SectionTitle icon={<Brain size={15} />} title="记忆回声" count={props.items.length} />
      {!props.items.length ? <EmptyState text="还没有召回" /> : null}
      <div className="mini-list">
        {props.items
          .slice()
          .reverse()
          .slice(0, 5)
          .map((item, index) => {
            const row = asRecord(item)
            return (
              <button className="mini-row" key={`${String(row.eventId || index)}-${index}`} onClick={() => props.onSelect(item)}>
                <span>{memoryStatusLabel(String(row.status || 'memory'))}</span>
                <strong>{String(row.itemCount || 0)}</strong>
                <small>{String(row.turnId || row.recallTurnId || row.eventId || '未知')}</small>
              </button>
            )
          })}
      </div>
    </section>
  )
}

function EventStream(props: { events: DesktopEvent[]; onSelect: (event: DesktopEvent) => void }): JSX.Element {
  return (
    <section className="intel-section">
      <SectionTitle icon={<Activity size={15} />} title="事件流" count={props.events.length} />
      {!props.events.length ? <EmptyState text="等待核心事件" /> : null}
      <div className="event-list">
        {props.events.slice(0, 8).map((event) => (
          <button className={`event-row ${event.severity || ''}`} key={event.id || `${event.type}-${event.ts}`} onClick={() => props.onSelect(event)}>
            <span>{eventLabel(event.type)}</span>
            <small>{formatTime(event.ts)}</small>
          </button>
        ))}
      </div>
    </section>
  )
}

function Inspector(props: { selected: unknown }): JSX.Element {
  return (
    <section className="intel-section inspector-section">
      <SectionTitle icon={<Database size={15} />} title="详情" />
      <pre className="json-view">{JSON.stringify(props.selected || {}, null, 2)}</pre>
    </section>
  )
}

function SectionTitle(props: { icon: React.ReactNode; title: string; count?: number }): JSX.Element {
  return (
    <div className="section-title">
      <span>{props.icon}</span>
      <h3>{props.title}</h3>
      {typeof props.count === 'number' ? <em>{props.count}</em> : null}
    </div>
  )
}

function EmptyState(props: { text: string }): JSX.Element {
  return (
    <div className="empty-state">
      <Heart size={14} />
      <span>{props.text}</span>
    </div>
  )
}

function applySnapshot(current: AppState, value: unknown): AppState {
  const snapshot = asRecord(value) as Snapshot
  const proactiveInbox = Array.isArray(snapshot.proactiveInbox) ? snapshot.proactiveInbox : []
  const activeCandidateIds = new Set(proactiveInbox.map((item) => String(asRecord(item).candidateId || '')).filter(Boolean))
  const proactiveActions = Object.fromEntries(
    Object.entries(current.proactiveActions).filter(([candidateId]) => activeCandidateIds.has(candidateId))
  ) as Record<string, ProactiveAction>
  return {
    ...current,
    snapshot,
    proactiveActions,
    proactiveInbox,
    recentTurns: Array.isArray(snapshot.recentTurns) ? snapshot.recentTurns : [],
    recentMemoryEvents: Array.isArray(snapshot.recentMemoryEvents) ? snapshot.recentMemoryEvents : [],
    selected: current.selected || snapshot
  }
}

function applyEvent(current: AppState, value: unknown): AppState {
  const event = asRecord(value) as DesktopEvent
  if (!event.type) {
    return current
  }
  const payload = asRecord(event.payload)
  const next: AppState = {
    ...current,
    events: [event, ...current.events].slice(0, 80)
  }
  if (event.type === 'chat.turn.started') {
    next.recentTurns = appendLimited(current.recentTurns, { ...payload, status: 'started' }, 'turnId')
    const commandId = String(payload.commandId || '')
    if (commandId) {
      return updateCommand(next, commandId, 'started', '核心已开始处理', String(payload.turnId || ''))
    }
  } else if (event.type === 'chat.turn.finished') {
    next.recentTurns = appendLimited(current.recentTurns, payload, 'turnId')
    const commandId = String(payload.commandId || '')
    if (commandId) {
      return updateCommand(next, commandId, 'finished', '核心已完成回复', String(payload.turnId || ''))
    }
  } else if (event.type === 'memory.recall.used') {
    next.recentMemoryEvents = appendLimited(current.recentMemoryEvents, { eventId: event.id, ts: event.ts, ...payload }, 'eventId')
  } else if (event.type === 'proactive.candidate.ready') {
    next.proactiveInbox = upsertByKey(current.proactiveInbox, payload, 'candidateId')
  } else if (event.type === 'proactive.delivery.updated') {
    const status = String(payload.status || '')
    const candidateId = String(payload.candidateId || '')
    if (candidateId) {
      const { [candidateId]: _removed, ...rest } = next.proactiveActions
      next.proactiveActions = rest
    }
    if (finalProactiveStatuses.has(status)) {
      next.proactiveInbox = current.proactiveInbox.filter((item) => String(asRecord(item).candidateId || '') !== candidateId)
    } else {
      next.proactiveInbox = upsertByKey(current.proactiveInbox, payload, 'candidateId')
    }
  }
  return next
}

function updateCommand(
  current: AppState,
  commandId: string,
  status: CommandState['status'],
  message: string,
  turnId = ''
): AppState {
  return {
    ...current,
    commands: current.commands.map((command) => {
      if (command.commandId !== commandId) {
        return command
      }
      if (command.status === 'finished' && status === 'accepted') {
        return command
      }
      return {
        ...command,
        status,
        message,
        turnId: turnId || command.turnId
      }
    })
  }
}

function appendLimited(items: unknown[], item: JsonRecord, key: string): unknown[] {
  const itemKey = String(item[key] || '')
  return [...items.filter((entry) => String(asRecord(entry)[key] || '') !== itemKey), item].slice(-100)
}

function upsertByKey(items: unknown[], item: JsonRecord, key: string): unknown[] {
  const itemKey = String(item[key] || '')
  if (!itemKey) return items
  return [...items.filter((entry) => String(asRecord(entry)[key] || '') !== itemKey), item]
}

function buildStats(state: AppState): {
  turns: number
  memories: number
  proactive: number
  events: number
  lastLatency: string
} {
  const latestTurn = asRecord(state.recentTurns[state.recentTurns.length - 1])
  const latency = Number(latestTurn.latencyMs || 0)
  return {
    turns: state.recentTurns.length,
    memories: state.recentMemoryEvents.length,
    proactive: state.proactiveInbox.length,
    events: state.events.length,
    lastLatency: latency > 0 ? `${latency}ms` : '还没有对话'
  }
}

function asRecord(value: unknown): JsonRecord {
  return value && typeof value === 'object' ? (value as JsonRecord) : {}
}

function createCommandId(): string {
  const random = window.crypto?.randomUUID?.() || Math.random().toString(36).slice(2)
  return `desktop-${Date.now()}-${random}`
}

function compact(text: string, limit: number): string {
  const clean = text.replace(/\s+/g, ' ').trim()
  return clean.length > limit ? `${clean.slice(0, Math.max(0, limit - 3)).trimEnd()}...` : clean
}

function formatTime(value?: string): string {
  if (!value) {
    return '--:--'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '--:--'
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatTurnMeta(turn: JsonRecord): string {
  const platform = String(turn.platform || 'desktop')
  const source = String(turn.source || turn.messageType || 'private')
  return `${platformLabel(platform)} / ${sourceLabel(source)}`
}

function formatLatency(turn: JsonRecord): string {
  const latency = Number(turn.latencyMs || 0)
  const recall = Number(turn.recallCount || 0)
  const parts = []
  if (latency > 0) parts.push(`${latency}ms`)
  if (recall > 0) parts.push(`${recall} 条记忆`)
  return parts.join(' / ') || statusLabel(String(turn.status || 'finished'))
}

function statusLabel(status: string): string {
  if (status === 'started') return '正在组织回复'
  if (status === 'timeout') return '这次等待超时'
  if (status === 'error') return '这次没有成功'
  if (status === 'failed') return '失败'
  if (status === 'blocked') return '已拦截'
  if (status === 'expired') return '已过期'
  if (status === 'unknown') return '未知'
  return '已完成'
}

function proactiveStatusLabel(status: string): string {
  if (status === 'ready') return '待处理'
  if (status === 'candidate_only') return '候选'
  if (status === 'claimed') return '已领取'
  if (status === 'sent') return '已发送'
  if (status === 'queued_qq') return '已排队'
  if (status === 'read_locally') return '本地已读'
  if (status === 'dismissed') return '已忽略'
  return statusLabel(status)
}

function serviceStatusLabel(status: string): string {
  if (status === 'ready') return '正常'
  if (status === 'configured') return '已配置'
  if (status === 'connecting') return '连接中'
  if (status === 'offline') return '离线'
  if (status === 'degraded') return '降级'
  if (status === 'stopping') return '停止中'
  if (status === 'unknown') return '未知'
  return status
}

function serviceLabel(value: string): string {
  if (value === 'core') return '核心'
  if (value === 'desktop_ws') return '本机连接'
  if (value === 'desktop_events') return '本机事件'
  if (value === 'memory') return '本地记忆'
  if (value === 'service') return '服务'
  return value
}

function memoryStatusLabel(value: string): string {
  if (value === 'used') return '已召回'
  if (value === 'empty') return '无匹配'
  if (value === 'memory') return '记忆'
  return value
}

function eventLabel(value: string): string {
  if (value === 'chat.turn.started') return '对话开始'
  if (value === 'chat.turn.finished') return '对话完成'
  if (value === 'memory.recall.used') return '记忆召回'
  if (value === 'proactive.candidate.ready') return '主动提醒'
  if (value === 'proactive.delivery.updated') return '提醒状态更新'
  if (value === 'desktop.event_replay.unavailable') return '事件回放不可用'
  return value
}

function platformLabel(value: string): string {
  if (value === 'desktop') return '本机'
  if (value === 'qq') return 'QQ'
  return value
}

function sourceLabel(value: string): string {
  if (value === 'xinyu_desktop_shell') return '本机端'
  if (value === 'desktop_private') return '私聊'
  if (value === 'qq_gateway') return 'QQ 网关'
  if (value === 'private') return '私聊'
  return value
}

function deliveryLabel(value: string): string {
  if (value === 'queue_owner_private') return '私聊队列'
  if (value === 'claim_ack') return '确认后发送'
  if (value === 'state_only') return '仅状态'
  if (value === 'preview_only') return '仅预览'
  if (value === 'none') return '本地'
  if (value === 'local') return '本地'
  if (!value) return '本地'
  return value
}

function commandStatusLabel(status: CommandState['status']): string {
  if (status === 'sending') return '正在发送'
  if (status === 'accepted') return '已交给核心'
  if (status === 'started') return '心玉正在想'
  if (status === 'failed') return '发送失败'
  return '已完成'
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
