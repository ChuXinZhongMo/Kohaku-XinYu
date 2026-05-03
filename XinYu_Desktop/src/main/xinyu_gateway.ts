import { app } from 'electron'
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import WebSocket from 'ws'

export type XinYuDesktopEvent = {
  id?: string
  type: string
  ts?: string
  source?: string
  privacy?: string
  severity?: string
  payload?: Record<string, unknown>
}

export type XinYuSnapshot = {
  version?: number
  snapshotAt?: string
  lastEventId?: string
  services?: unknown[]
  health?: Record<string, unknown>
  eventBus?: Record<string, unknown>
  proactiveInbox?: unknown[]
  recentTurns?: unknown[]
  recentMemoryEvents?: unknown[]
  notes?: string[]
}

type GatewayOptions = {
  onEvent: (event: XinYuDesktopEvent) => void
  onStatus: (status: GatewayStatus) => void
}

export type GatewayStatus = {
  httpUrl: string
  wsUrl: string
  connected: boolean
  connecting: boolean
  lastEventId: string
  lastError: string
  snapshotAt: string
}

export type SendChatRequest = {
  text: string
  commandId: string
}

export type SendChatResponse = {
  accepted: boolean
  commandId: string
  turnId?: string
  reply?: string
  notes?: unknown[]
  error?: string
}

export type ProactiveAckAction = 'read_locally' | 'approve_qq' | 'dismiss'

export type ProactiveAckRequest = {
  candidateId: string
  action: ProactiveAckAction
}

export type ProactiveAckResponse = {
  accepted: boolean
  ackRecorded?: boolean
  candidateId: string
  action: string
  status?: string
  eventId?: string
  outboxMessageId?: string
  notes?: unknown[]
  error?: string
}

const DEFAULT_HTTP_URL = 'http://127.0.0.1:8765'
const DEFAULT_WS_URL = 'ws://127.0.0.1:8766/desktop/events'
const FINAL_PROACTIVE_STATUSES = new Set([
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

export class XinyuGateway {
  private readonly httpUrl = trimTrailingSlash(process.env.XINYU_DESKTOP_HTTP_URL || DEFAULT_HTTP_URL)
  private readonly wsUrl = process.env.XINYU_DESKTOP_WS_URL || DEFAULT_WS_URL
  private readonly token = resolveBridgeToken()
  private readonly statePath = join(app.getPath('userData'), 'xinyu-desktop-state.json')
  private readonly options: GatewayOptions
  private ws: WebSocket | null = null
  private reconnectTimer: NodeJS.Timeout | null = null
  private reconnectAttempts = 0
  private snapshot: XinYuSnapshot | null = null
  private status: GatewayStatus = {
    httpUrl: this.httpUrl,
    wsUrl: this.wsUrl,
    connected: false,
    connecting: false,
    lastEventId: '',
    lastError: '',
    snapshotAt: ''
  }

  constructor(options: GatewayOptions) {
    this.options = options
    this.status.lastEventId = this.readLastEventId()
  }

  async start(): Promise<void> {
    await this.hydrate()
    this.connect()
  }

  stop(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.removeAllListeners()
      this.ws.close()
      this.ws = null
    }
  }

  async getSnapshot(): Promise<XinYuSnapshot> {
    return await this.hydrate()
  }

  getStatus(): GatewayStatus {
    return { ...this.status }
  }

  async sendChat(request: SendChatRequest): Promise<SendChatResponse> {
    const text = String(request.text || '').trim()
    const commandId = String(request.commandId || '').trim()
    if (!text) {
      return { accepted: false, commandId, error: 'empty_text' }
    }
    if (!commandId) {
      return { accepted: false, commandId, error: 'missing_command_id' }
    }

    try {
      const response = await fetch(`${this.httpUrl}/chat`, {
        method: 'POST',
        headers: {
          ...this.authHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          platform: 'desktop',
          adapter: 'xinyu_desktop_shell',
          message_type: 'desktop_private',
          session_id: 'desktop:private:owner',
          user_id: process.env.XINYU_DESKTOP_OWNER_USER_ID || 'desktop-owner',
          sender_name: 'Owner',
          text,
          command_id: commandId,
          timestamp: Math.floor(Date.now() / 1000),
          metadata: {
            is_owner_user: true,
            source: 'xinyu_desktop_shell',
            desktop_shell: true,
            desktop_command_id: commandId
          }
        })
      })
      const body = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok) {
        return {
          accepted: false,
          commandId,
          error: String(body.error || body.message || `chat_http_${response.status}`),
          notes: Array.isArray(body.notes) ? body.notes : []
        }
      }
      return {
        accepted: Boolean(body.accepted ?? true),
        commandId: String(body.command_id || commandId),
        turnId: String(body.turn_id || ''),
        reply: String(body.reply || ''),
        notes: Array.isArray(body.notes) ? body.notes : []
      }
    } catch (error) {
      return { accepted: false, commandId, error: errorLabel(error), notes: [] }
    }
  }

  async ackProactive(request: ProactiveAckRequest): Promise<ProactiveAckResponse> {
    const candidateId = String(request.candidateId || '').trim()
    const action = String(request.action || '').trim() as ProactiveAckAction
    if (!candidateId) {
      return { accepted: false, candidateId, action, error: 'missing_candidate_id' }
    }
    if (!['read_locally', 'approve_qq', 'dismiss'].includes(action)) {
      return { accepted: false, candidateId, action, error: 'invalid_action' }
    }

    try {
      const response = await fetch(`${this.httpUrl}/desktop/proactive/ack`, {
        method: 'POST',
        headers: {
          ...this.authHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ candidateId, action })
      })
      const body = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok) {
        return {
          accepted: false,
          candidateId,
          action,
          error: String(body.error || body.message || `proactive_ack_http_${response.status}`),
          notes: Array.isArray(body.notes) ? body.notes : []
        }
      }
      return {
        accepted: Boolean(body.accepted ?? true),
        ackRecorded: Boolean(body.ack_recorded),
        candidateId: String(body.candidateId || candidateId),
        action: String(body.action || action),
        status: String(body.status || ''),
        eventId: String(body.eventId || ''),
        outboxMessageId: String(body.outboxMessageId || ''),
        notes: Array.isArray(body.notes) ? body.notes : []
      }
    } catch (error) {
      return { accepted: false, candidateId, action, error: errorLabel(error), notes: [] }
    }
  }

  private async hydrate(): Promise<XinYuSnapshot> {
    try {
      const response = await fetch(`${this.httpUrl}/desktop/snapshot`, {
        headers: this.authHeaders()
      })
      if (!response.ok) {
        throw new Error(`snapshot_http_${response.status}`)
      }
      const snapshot = (await response.json()) as XinYuSnapshot
      this.snapshot = snapshot
      const lastEventId = String(snapshot.lastEventId || this.status.lastEventId || '')
      this.updateLastEventId(lastEventId)
      this.status.snapshotAt = String(snapshot.snapshotAt || new Date().toISOString())
      this.status.lastError = ''
      this.emitStatus()
      return snapshot
    } catch (error) {
      this.status.lastError = errorLabel(error)
      this.emitStatus()
      return (
        this.snapshot || {
          version: 1,
          snapshotAt: new Date().toISOString(),
          lastEventId: this.status.lastEventId,
          services: [],
          proactiveInbox: [],
          recentTurns: [],
          recentMemoryEvents: [],
          notes: ['desktop_snapshot_unavailable']
        }
      )
    }
  }

  private connect(): void {
    if (this.ws || this.status.connecting) {
      return
    }
    this.status.connecting = true
    this.emitStatus()

    const url = new URL(this.wsUrl)
    if (this.status.lastEventId) {
      url.searchParams.set('since', this.status.lastEventId)
    }
    if (this.token) {
      url.searchParams.set('token', this.token)
    }

    const ws = new WebSocket(url)
    this.ws = ws

    ws.on('open', () => {
      this.reconnectAttempts = 0
      this.status.connected = true
      this.status.connecting = false
      this.status.lastError = ''
      this.emitStatus()
    })

    ws.on('message', (raw) => {
      this.handleMessage(raw.toString())
    })

    ws.on('error', (error) => {
      this.status.lastError = errorLabel(error)
      this.emitStatus()
    })

    ws.on('close', () => {
      if (this.ws === ws) {
        this.ws = null
      }
      this.status.connected = false
      this.status.connecting = false
      this.emitStatus()
      this.scheduleReconnect()
    })
  }

  private handleMessage(raw: string): void {
    let event: XinYuDesktopEvent
    try {
      event = JSON.parse(raw) as XinYuDesktopEvent
    } catch {
      return
    }

    if (event.type === 'desktop.event_replay.unavailable') {
      void this.hydrate()
    }

    if (event.id && !event.type.startsWith('desktop.event_stream.')) {
      this.updateLastEventId(event.id)
    }

    this.mergeEvent(event)
    this.options.onEvent(event)
    this.emitStatus()
  }

  private mergeEvent(event: XinYuDesktopEvent): void {
    if (!this.snapshot) {
      this.snapshot = { version: 1, proactiveInbox: [], recentTurns: [], recentMemoryEvents: [] }
    }
    const payload = event.payload || {}
    if (event.type === 'chat.turn.finished') {
      this.snapshot.recentTurns = appendLimited(this.snapshot.recentTurns, payload, 100, 'turnId')
    } else if (event.type === 'memory.recall.used') {
      this.snapshot.recentMemoryEvents = appendLimited(
        this.snapshot.recentMemoryEvents,
        { eventId: event.id, ts: event.ts, ...payload },
        100,
        'eventId'
      )
    } else if (event.type === 'proactive.candidate.ready') {
      this.snapshot.proactiveInbox = upsertByKey(this.snapshot.proactiveInbox, payload, 'candidateId')
    } else if (event.type === 'proactive.delivery.updated') {
      const status = String(payload.status || '')
      const candidateId = String(payload.candidateId || '')
      if (candidateId && FINAL_PROACTIVE_STATUSES.has(status)) {
        this.snapshot.proactiveInbox = (this.snapshot.proactiveInbox || []).filter(
          (item) => recordString(item, 'candidateId') !== candidateId
        )
      } else {
        this.snapshot.proactiveInbox = upsertByKey(this.snapshot.proactiveInbox, payload, 'candidateId')
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return
    }
    const delay = Math.min(30000, 1000 * 2 ** Math.min(5, this.reconnectAttempts++))
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, delay)
  }

  private authHeaders(): Record<string, string> {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {}
  }

  private readLastEventId(): string {
    try {
      if (!existsSync(this.statePath)) {
        return ''
      }
      const data = JSON.parse(readFileSync(this.statePath, 'utf-8')) as { lastEventId?: string }
      return String(data.lastEventId || '')
    } catch {
      return ''
    }
  }

  private updateLastEventId(eventId: string): void {
    if (!eventId || eventId === this.status.lastEventId) {
      return
    }
    this.status.lastEventId = eventId
    try {
      mkdirSync(dirname(this.statePath), { recursive: true })
      writeFileSync(this.statePath, JSON.stringify({ lastEventId: eventId }, null, 2), 'utf-8')
    } catch {
      // Non-critical. The stream still works; the next start will hydrate.
    }
  }

  private emitStatus(): void {
    this.options.onStatus(this.getStatus())
  }
}

function resolveBridgeToken(): string {
  const envToken = String(process.env.XINYU_BRIDGE_TOKEN || '').trim()
  if (envToken) {
    return envToken
  }
  try {
    return readFileSync('D:\\XinYu\\.xinyu_bridge_token', 'utf-8').trim()
  } catch {
    return ''
  }
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

function errorLabel(error: unknown): string {
  return error instanceof Error ? `${error.name}: ${error.message}` : String(error)
}

function appendLimited(items: unknown[] | undefined, item: Record<string, unknown>, limit: number, key: string): unknown[] {
  const withoutDuplicate = (items || []).filter((entry) => recordString(entry, key) !== String(item[key] || ''))
  return [...withoutDuplicate, item].slice(-limit)
}

function upsertByKey(items: unknown[] | undefined, item: Record<string, unknown>, key: string): unknown[] {
  const itemKey = String(item[key] || '')
  if (!itemKey) {
    return items || []
  }
  return [...(items || []).filter((entry) => recordString(entry, key) !== itemKey), item]
}

function recordString(value: unknown, key: string): string {
  if (!value || typeof value !== 'object') {
    return ''
  }
  return String((value as Record<string, unknown>)[key] || '')
}
