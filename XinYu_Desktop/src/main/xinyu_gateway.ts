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
  environment?: Record<string, unknown>
  entropyState?: Record<string, unknown>
  activeDesires?: unknown[]
  xinyuState?: Record<string, unknown>
  eventBus?: Record<string, unknown>
  proactiveInbox?: unknown[]
  proactiveHistory?: unknown[]
  recentTurns?: unknown[]
  recentMemoryEvents?: unknown[]
  selfAction?: Record<string, unknown>
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
  codexMode?: boolean
  allowLocalWrite?: boolean
  proactiveCandidateId?: string
  proactivePreview?: string
}

export type SendChatResponse = {
  accepted: boolean
  commandId: string
  turnId?: string
  reply?: string
  notes?: unknown[]
  error?: string
}

export type ProactiveAckAction = 'read_locally' | 'approve_qq' | 'dismiss' | 'reply'

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

export type SelfActionApprovalRequest = {
  queueId: string
  decision: 'approved' | 'denied'
  reason?: string
  execute?: boolean
  authorizeCodex?: boolean
  authorizeExisting?: boolean
}

export type SelfActionApprovalResponse = {
  accepted: boolean
  queueId: string
  decision: string
  approvalId?: string
  reply?: string
  selfAction?: Record<string, unknown>
  notes?: unknown[]
  error?: string
}

export type MetabolismTicket = Record<string, unknown> & {
  ticket_id?: string
  status?: string
}

export type MetabolismTicketListResponse = {
  accepted: boolean
  tickets: MetabolismTicket[]
  notes?: unknown[]
  error?: string
}

export type MetabolismDecisionRequest = {
  ticketId: string
  seconds?: number
  note?: string
}

export type MetabolismDecisionResponse = {
  accepted: boolean
  ticket?: MetabolismTicket
  notes?: unknown[]
  error?: string
}

export type MemoryGrowthCandidatesResponse = Record<string, unknown> & {
  ok?: boolean
  pending_apply_count?: number
  applied_count?: number
  owner_review_required_count?: number
  pending_apply?: unknown[]
  applied?: unknown[]
  owner_review_required?: unknown[]
  notes?: unknown[]
  error?: string
}

export type ExternalPluginConfigPatch = {
  pluginId: string
  enabled?: boolean
  proactiveEnabled?: boolean
  config?: Record<string, unknown>
}

export type ExternalPluginInstallRequest = {
  pluginId: string
  options?: Record<string, unknown>
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
  'replied',
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

  async getProactiveInbox(): Promise<unknown> {
    try {
      const response = await fetch(`${this.httpUrl}/desktop/proactive/inbox`, {
        headers: this.authHeaders()
      })
      const body = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok) {
        throw new Error(String(body.error || body.message || `proactive_inbox_http_${response.status}`))
      }
      const items = Array.isArray(body.items) ? body.items : []
      const history = Array.isArray(body.history) ? body.history : []
      if (this.snapshot) {
        this.snapshot = { ...this.snapshot, proactiveInbox: items, proactiveHistory: history }
      }
      this.status.lastError = ''
      this.emitStatus()
      return { items, history }
    } catch (error) {
      this.status.lastError = errorLabel(error)
      this.emitStatus()
      return {
        items: Array.isArray(this.snapshot?.proactiveInbox) ? this.snapshot.proactiveInbox : [],
        history: Array.isArray(this.snapshot?.proactiveHistory) ? this.snapshot.proactiveHistory : []
      }
    }
  }

  getStatus(): GatewayStatus {
    return { ...this.status }
  }

  async sendChat(request: SendChatRequest): Promise<SendChatResponse> {
    const text = String(request.text || '').trim()
    const commandId = String(request.commandId || '').trim()
    const codexMode = Boolean(request.codexMode)
    const allowLocalWrite = Boolean(request.allowLocalWrite)
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
          sender_name: process.env.XINYU_DESKTOP_OWNER_NAME || '你',
          text,
          command_id: commandId,
          timestamp: Math.floor(Date.now() / 1000),
          metadata: {
            is_owner_user: true,
            desktop_codex_mode: codexMode,
            owner_local_write_approved: codexMode && allowLocalWrite,
            source: 'xinyu_desktop_shell',
            desktop_shell: true,
            desktop_command_id: commandId,
            desktop_proactive_reply: Boolean(request.proactiveCandidateId),
            desktop_proactive_candidate_id: String(request.proactiveCandidateId || ''),
            desktop_proactive_preview: String(request.proactivePreview || '')
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
    if (!['read_locally', 'approve_qq', 'dismiss', 'reply'].includes(action)) {
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

  async decideSelfActionApproval(request: SelfActionApprovalRequest): Promise<SelfActionApprovalResponse> {
    const queueId = String(request.queueId || 'latest').trim() || 'latest'
    const decision = String(request.decision || '').trim() as 'approved' | 'denied'
    if (!['approved', 'denied'].includes(decision)) {
      return { accepted: false, queueId, decision, error: 'invalid_decision' }
    }
    try {
      const response = await fetch(`${this.httpUrl}/desktop/self-action/approval`, {
        method: 'POST',
        headers: {
          ...this.authHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          queueId,
          decision,
          reason: String(request.reason || ''),
          execute: request.execute !== false,
          authorizeCodex: Boolean(request.authorizeCodex),
          authorizeExisting: Boolean(request.authorizeExisting),
          decidedBy: 'owner_desktop'
        })
      })
      const body = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok) {
        return {
          accepted: false,
          queueId,
          decision,
          error: String(body.error || body.message || `self_action_approval_http_${response.status}`),
          notes: Array.isArray(body.notes) ? body.notes : []
        }
      }
      if (body.selfAction && typeof body.selfAction === 'object') {
        this.snapshot = { ...(this.snapshot || { version: 1 }), selfAction: body.selfAction as Record<string, unknown> }
      }
      return {
        accepted: Boolean(body.accepted ?? true),
        queueId: String(body.queue_id || body.queueId || queueId),
        decision: String(body.decision || decision),
        approvalId: String(body.approval_id || body.approvalId || ''),
        reply: String(body.reply || ''),
        selfAction: body.selfAction && typeof body.selfAction === 'object' ? (body.selfAction as Record<string, unknown>) : undefined,
        notes: Array.isArray(body.notes) ? body.notes : [],
        error: String(body.error || '')
      }
    } catch (error) {
      return { accepted: false, queueId, decision, error: errorLabel(error), notes: [] }
    }
  }

  async getMemoryGrowthCandidates(): Promise<MemoryGrowthCandidatesResponse> {
    try {
      const response = await fetch(`${this.httpUrl}/desktop/memory/growth-candidates`, {
        headers: this.authHeaders()
      })
      const body = (await response.json().catch(() => ({}))) as MemoryGrowthCandidatesResponse
      if (!response.ok) {
        throw new Error(String(body.error || body.message || `memory_growth_candidates_http_${response.status}`))
      }
      this.status.lastError = ''
      this.emitStatus()
      return body
    } catch (error) {
      this.status.lastError = errorLabel(error)
      this.emitStatus()
      return { ok: false, pending_apply: [], applied: [], owner_review_required: [], pending_apply_count: 0, applied_count: 0, owner_review_required_count: 0, error: errorLabel(error), notes: ['memory_growth_candidates_unavailable'] }
    }
  }

  async getExternalPlugins(): Promise<Record<string, unknown>> {
    try {
      const response = await fetch(`${this.httpUrl}/external/plugins`, {
        headers: this.authHeaders()
      })
      const body = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok) {
        throw new Error(String(body.error || body.message || `external_plugins_http_${response.status}`))
      }
      this.status.lastError = ''
      this.emitStatus()
      return body
    } catch (error) {
      this.status.lastError = errorLabel(error)
      this.emitStatus()
      return { ok: false, plugins: [], error: errorLabel(error), notes: ['external_plugins_unavailable'] }
    }
  }

  async setExternalPluginConfig(request: ExternalPluginConfigPatch): Promise<Record<string, unknown>> {
    const pluginId = String(request.pluginId || '').trim()
    if (!pluginId) {
      return { ok: false, accepted: false, error: 'missing_plugin_id' }
    }
    try {
      const response = await fetch(`${this.httpUrl}/external/plugins/config`, {
        method: 'POST',
        headers: {
          ...this.authHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          plugin_id: pluginId,
          enabled: request.enabled,
          proactive_enabled: request.proactiveEnabled,
          config: request.config || {}
        })
      })
      const body = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok) {
        return { ok: false, accepted: false, error: String(body.error || body.message || `external_plugin_config_http_${response.status}`), notes: Array.isArray(body.notes) ? body.notes : [] }
      }
      return body
    } catch (error) {
      return { ok: false, accepted: false, error: errorLabel(error), notes: [] }
    }
  }

  async installExternalPlugin(request: ExternalPluginInstallRequest): Promise<Record<string, unknown>> {
    const pluginId = String(request.pluginId || '').trim()
    if (!pluginId) {
      return { ok: false, accepted: false, error: 'missing_plugin_id' }
    }
    try {
      const response = await fetch(`${this.httpUrl}/external/plugins/install`, {
        method: 'POST',
        headers: {
          ...this.authHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          plugin_id: pluginId,
          options: request.options || {}
        })
      })
      const body = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok) {
        return { ok: false, accepted: false, error: String(body.error || body.message || `external_plugin_install_http_${response.status}`), notes: Array.isArray(body.notes) ? body.notes : [] }
      }
      return body
    } catch (error) {
      return { ok: false, accepted: false, error: errorLabel(error), notes: [] }
    }
  }

  async listMetabolismTickets(statuses = 'requested,approved,running'): Promise<MetabolismTicketListResponse> {
    const query = statuses ? `?status=${encodeURIComponent(statuses)}` : ''
    try {
      const response = await fetch(`${this.httpUrl}/life/metabolism/tickets${query}`, {
        headers: this.authHeaders()
      })
      const body = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok) {
        return {
          accepted: false,
          tickets: [],
          error: String(body.error || body.message || `metabolism_ticket_list_http_${response.status}`),
          notes: Array.isArray(body.notes) ? body.notes : []
        }
      }
      return {
        accepted: Boolean(body.accepted ?? true),
        tickets: Array.isArray(body.tickets) ? (body.tickets as MetabolismTicket[]) : [],
        notes: Array.isArray(body.notes) ? body.notes : []
      }
    } catch (error) {
      return { accepted: false, tickets: [], error: errorLabel(error), notes: [] }
    }
  }

  async yieldCompute(request: MetabolismDecisionRequest): Promise<MetabolismDecisionResponse> {
    return await this.metabolismDecision('approve', request)
  }

  async maintainBoundary(request: MetabolismDecisionRequest): Promise<MetabolismDecisionResponse> {
    return await this.metabolismDecision('reject', request)
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
          proactiveHistory: [],
          recentTurns: [],
          recentMemoryEvents: [],
          notes: ['desktop_snapshot_unavailable']
        }
      )
    }
  }

  private async metabolismDecision(
    action: 'approve' | 'reject',
    request: MetabolismDecisionRequest
  ): Promise<MetabolismDecisionResponse> {
    const ticketId = String(request.ticketId || '').trim()
    if (!ticketId) {
      return { accepted: false, error: 'missing_ticket_id', notes: [] }
    }
    const body =
      action === 'approve'
        ? {
            decision_id: createDecisionId('yield_compute'),
            approved_seconds: Number(request.seconds || 600),
            note: String(request.note || '')
          }
        : {
            decision_id: createDecisionId('maintain_boundary'),
            note: String(request.note || '')
          }
    try {
      const response = await fetch(`${this.httpUrl}/life/metabolism/tickets/${encodeURIComponent(ticketId)}/${action}`, {
        method: 'POST',
        headers: {
          ...this.authHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })
      const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok) {
        return {
          accepted: false,
          error: String(payload.error || payload.message || `metabolism_${action}_http_${response.status}`),
          notes: Array.isArray(payload.notes) ? payload.notes : []
        }
      }
      return {
        accepted: Boolean(payload.accepted ?? true),
        ticket: isRecord(payload.ticket) ? (payload.ticket as MetabolismTicket) : undefined,
        notes: Array.isArray(payload.notes) ? payload.notes : []
      }
    } catch (error) {
      return { accepted: false, error: errorLabel(error), notes: [] }
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
      this.snapshot = { version: 1, proactiveInbox: [], proactiveHistory: [], recentTurns: [], recentMemoryEvents: [] }
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
        this.snapshot.proactiveHistory = appendLimited(this.snapshot.proactiveHistory || [], payload, 20, 'candidateId')
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

function createDecisionId(prefix: string): string {
  return `${prefix}:${Date.now().toString(36)}:${Math.random().toString(36).slice(2)}`
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object')
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
