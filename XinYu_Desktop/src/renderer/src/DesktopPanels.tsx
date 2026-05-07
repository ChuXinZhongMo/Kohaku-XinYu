import React from 'react'
import { Activity, Bell, Brain, ChevronDown, ChevronRight, Clock3, Compass, Clipboard, Eye, ExternalLink, Heart, History, MessageCircle, Play, Radio, RefreshCw, Save, Send, ShieldAlert, Sparkles, Terminal, TimerReset, Plus, Trash2, Wifi, X } from 'lucide-react'
import { EnvironmentValve } from './EnvironmentValve'
import { SurfacePart } from './AffectiveSurfaceProvider'
import type { CommandState, DesktopEvent, GatewayStatus, ImpulseSoupState, JsonRecord, ProactiveAction, ProactiveIntent, QQActionState, QQEnvironmentStatus, QQRuntimeActionState, QQRuntimeConfig, QQRuntimeConfigPatch, Snapshot, StickerActionState, StickerLibrary, StickerRecord, ThemeName, XinYuState } from './desktopTypes'
import { actionLabel, asRecord, buildStats, commandStatusLabel, compact, defaultQQRuntimeConfig, defaultQQServices, digestPressureLabel, digestResidueLabel, digestResultLabel, digestThemeLabel, eventLabel, formatLatency, formatTime, formatTurnMeta, isCommandRenderedByTurn, memorySummary, platformLabel, qqDetailLabel, qqDiagnosisLabel, qqServiceLabel, riskLabel, runtimeLabel, sourceLabel, statusLabel, stickerClipLabel, stickerCorrectionMoods, stickerMoodLabel, themeOptions } from './desktopModel'

const avatarSrc = './xinyu-avatar.png'
const characterSrc = './xinyu-character.png'

const impulseLabelMap: Record<string, string> = {
  active: '活跃',
  completion_continuity: '完成连续性',
  compress_to_reflection: '压缩为反思',
  diagnose_locally_first: '先本地诊断',
  draft_diagnostic_plan: '草拟诊断计划',
  dormant: '休眠',
  dream_or_emotion: '梦境/情绪残留',
  dream_residue: '梦境残留',
  dream_residue_compression: '梦境残留压缩',
  expression_repair_habit: '表达修复习惯',
  extinct: '熄灭',
  no_direct_qq_v0: '禁止直接 QQ',
  never_direct_qq_v0: '禁止直接 QQ',
  no_owner_interrupt_until_diagnosis: '诊断前不打扰主人',
  prepare_owner_safe_summary: '准备安全总结',
  prepare_completion_summary: '准备完成总结',
  reflection_queue: '反思队列',
  review_open_loop: '复查开放问题',
  runtime_error: '运行错误',
  runtime_diagnostic_reflex: '运行诊断反射',
  scorer_gate_required: '必须经过评分闸门',
  self_repair_reflex: '自修复反射',
  social_presence_inhibition: '社交存在抑制',
  stabilize_expression_habit: '稳定表达习惯',
  style_repair: '表达风格修复',
  task_done: '任务完成',
  task_failed: '任务失败',
  test_expression_repair_on_shadow_examples: '影子样本测试表达修复',
  unresolved_reflection: '未解决反思',
  wait_for_owner_anchor: '等待主人锚点'
}

function impulseLabel(value: string | undefined, fallback = '暂无'): string {
  if (!value || value === 'none') {
    return fallback
  }
  return impulseLabelMap[value] || value
}

type ImpulseReadout = {
  tone: 'calm' | 'watch' | 'warn'
  title: string
  detail: string
}

function impulseReadout(soup: ImpulseSoupState | null): ImpulseReadout {
  if (!soup || !soup.ok) {
    return {
      tone: 'watch',
      title: '暂无可判读状态',
      detail: '还没有读到涌现池状态文件。'
    }
  }
  if (soup.quarantinedCount > 0) {
    return {
      tone: 'warn',
      title: '存在隔离念头',
      detail: `${soup.quarantinedCount} 条念头被隔离，优先查看触发依据和风险标记。`
    }
  }
  const diagnosticCount = soup.thoughtlets.filter(
    (item) => item.status === 'active' && ['runtime_diagnostic_reflex', 'self_repair_reflex'].includes(item.desireShape)
  ).length
  if (diagnosticCount >= Math.max(4, Math.ceil(soup.activeCount * 0.35))) {
    return {
      tone: 'watch',
      title: '诊断压力偏高',
      detail: `${diagnosticCount} 条活跃念头来自运行诊断或自修复，说明最近错误/失败信号在堆积。`
    }
  }
  if (!soup.outwardActionAllowed) {
    return {
      tone: 'calm',
      title: '内部活跃，外向阻断',
      detail: '当前念头只在本地观察和整理，不会直接向 QQ 外发。'
    }
  }
  return {
    tone: 'watch',
    title: '外向动作开放',
    detail: '有候选可能进入外向动作层，需要继续依赖评分闸门。'
  }
}

function impulseDesireGroups(soup: ImpulseSoupState | null): Array<{ key: string; label: string; count: number; topEnergy: number }> {
  const counts = new Map<string, { count: number; topEnergy: number }>()
  for (const item of soup?.thoughtlets || []) {
    if (item.status !== 'active') {
      continue
    }
    const current = counts.get(item.desireShape) || { count: 0, topEnergy: 0 }
    counts.set(item.desireShape, {
      count: current.count + 1,
      topEnergy: Math.max(current.topEnergy, item.energy)
    })
  }
  return Array.from(counts.entries())
    .map(([key, value]) => ({ key, label: impulseLabel(key), count: value.count, topEnergy: value.topEnergy }))
    .sort((a, b) => b.count - a.count || b.topEnergy - a.topEnergy)
    .slice(0, 6)
}

function riskFlagsLabel(flags: string[]): string {
  return flags.length ? flags.map((flag) => impulseLabel(flag)).join(' / ') : '无风险标记'
}

export function StatusBadge(props: { connected: boolean; connecting: boolean }): JSX.Element {
  const label = props.connected ? '在线' : props.connecting ? '连接中' : '离线'
  return (
    <span className={`status-badge ${props.connected ? 'ok' : 'warn'}`}>
      <Radio size={14} />
      {label}
    </span>
  )
}

export function ThemeSwitcher(props: { theme: ThemeName; onChange: (theme: ThemeName) => void }): JSX.Element {
  return (
    <div className="theme-switcher" aria-label="主题">
      {themeOptions.map((option) => (
        <button
          key={option.id}
          type="button"
          className={`theme-swatch theme-${option.id} ${props.theme === option.id ? 'active' : ''}`}
          onClick={() => props.onChange(option.id)}
          title={option.label}
          aria-label={option.label}
        />
      ))}
    </div>
  )
}

export function MindStatePanel(props: {
  state: XinYuState
  stats: ReturnType<typeof buildStats>
  gateway: GatewayStatus | null
  snapshot: Snapshot | null
}): JSX.Element {
  return (
    <aside className="mind-panel">
      <SurfacePart name="portrait" className="portrait-stage">
        <img className="character-art" src={characterSrc} alt="心玉形象" />
        <span className={`presence-dot ${props.state.connection}`} />
      </SurfacePart>

      <section className="mind-summary">
        <p className="label">心玉频道 · {props.state.moodLabel}</p>
        <h2>心玉疗养室</h2>
        <p className="mind-summary-copy">私聊、记忆回声和主动提醒都在这里。</p>
        <div className="mood-meter" aria-hidden="true">
          <span style={{ width: `${props.state.moodScore}%` }} />
        </div>
      </section>

      <EnvironmentValve snapshot={props.snapshot} />

      <section className="vital-strip" aria-label="当前数据">
        <Vital icon={<MessageCircle size={14} />} value={props.stats.turns} label="对话" />
        <Vital icon={<Brain size={14} />} value={props.stats.memories} label="记忆" />
        <Vital icon={<Bell size={14} />} value={props.stats.proactive} label="意图" />
        <Vital icon={<Activity size={14} />} value={props.stats.events} label="事件" />
      </section>

      <section className="state-lines" aria-label="心玉状态">
        <StateLine icon={<Compass size={15} />} label="注意力" value={props.state.attentionFocus} />
        <StateLine icon={<Heart size={15} />} label="牵挂" value={props.state.recentConcern} />
        <StateLine icon={<Sparkles size={15} />} label="体感" value={props.state.physicalSensation} />
        <StateLine
          icon={<TimerReset size={15} />}
          label="等待"
          value={props.state.waitingReply ? props.state.waitingReason : '没有卡住的主动动作'}
        />
      </section>

      <section className="evidence-stack">
        <p className="label">运行状态</p>
        {props.state.evidence.slice(0, 4).map((value, index) => (
          <div className="evidence-row runtime-row" key={`${runtimeLabel(index)}-${value}`}>
            <Sparkles size={13} />
            <span>{runtimeLabel(index)}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </section>

      <footer className="endpoint-line">
        <Wifi size={14} />
        <span>{props.gateway?.httpUrl || 'http://127.0.0.1:8765'}</span>
      </footer>
    </aside>
  )
}

function Vital(props: { icon: React.ReactNode; value: number; label: string }): JSX.Element {
  return (
    <div className="vital">
      {props.icon}
      <strong>{props.value}</strong>
      <small>{props.label}</small>
    </div>
  )
}

function StateLine(props: { icon: React.ReactNode; label: string; value: string }): JSX.Element {
  return (
    <div className="state-line">
      <span>{props.icon}</span>
      <div>
        <small>{props.label}</small>
        <strong>{props.value}</strong>
      </div>
    </div>
  )
}

type ConversationTrack = {
  key: string
  label: string
  detail: string
  accountLabel: string
  avatarUrl: string
  groupKey: string
  groupLabel: string
  turns: JsonRecord[]
  canCompose: boolean
  isOwner: boolean
  isTrusted: boolean
  latestIndex: number
}

function buildConversationTracks(rawTurns: unknown[], qqRuntimeConfig: QQRuntimeConfig | null): ConversationTrack[] {
  const tracks = new Map<string, ConversationTrack>()
  for (const seed of seedConversationTracks(qqRuntimeConfig)) {
    tracks.set(seed.key, seed)
  }
  rawTurns.map(asRecord).forEach((turn, index) => {
    const key = conversationKey(turn)
    const descriptor = describeConversation(turn)
    const current = tracks.get(key)
    if (!current) {
      tracks.set(key, {
        key,
        ...descriptor,
        turns: [turn],
        latestIndex: index
      })
      return
    }
    current.turns.push(turn)
    current.label = descriptor.label
    current.detail = descriptor.detail
    current.accountLabel = descriptor.accountLabel
    current.avatarUrl = descriptor.avatarUrl || current.avatarUrl
    current.groupKey = descriptor.groupKey
    current.groupLabel = descriptor.groupLabel
    current.canCompose = current.canCompose || descriptor.canCompose
    current.isOwner = current.isOwner || descriptor.isOwner
    current.isTrusted = current.isTrusted || descriptor.isTrusted
    current.latestIndex = index
  })
  return Array.from(tracks.values()).sort(
    (a, b) =>
      Number(b.canCompose) - Number(a.canCompose) ||
      Number(b.isOwner) - Number(a.isOwner) ||
      b.latestIndex - a.latestIndex
  )
}

function seedConversationTracks(qqRuntimeConfig: QQRuntimeConfig | null): ConversationTrack[] {
  const tracks: ConversationTrack[] = [
    {
      key: 'desktop:private:owner',
      label: '桌面主人',
      detail: '桌面 owner / 本机私有频道',
      accountLabel: '桌面 owner',
      avatarUrl: '',
      groupKey: 'desktop',
      groupLabel: '桌面频道',
      turns: [],
      canCompose: true,
      isOwner: true,
      isTrusted: false,
      latestIndex: -1000
    }
  ]
  const ownerIds = new Set(qqRuntimeConfig?.ownerUserIds || [])
  const trustedIds = new Set(qqRuntimeConfig?.trustedUserIds || [])
  const whitelistIds = new Set(qqRuntimeConfig?.whitelistUserIds || [])
  for (const userId of ownerIds) {
    tracks.push(seedQQPrivateTrack(userId, 'owner'))
  }
  for (const userId of trustedIds) {
    if (!ownerIds.has(userId)) tracks.push(seedQQPrivateTrack(userId, 'trusted'))
  }
  for (const userId of whitelistIds) {
    if (!ownerIds.has(userId) && !trustedIds.has(userId)) tracks.push(seedQQPrivateTrack(userId, 'trusted'))
  }
  const groupIds = new Set([...(qqRuntimeConfig?.allowedGroupIds || []), ...(qqRuntimeConfig?.groupShadowAllowedGroupIds || [])])
  for (const groupId of groupIds) {
    tracks.push(seedQQGroupTrack(groupId))
  }
  return tracks
}

function seedQQPrivateTrack(userId: string, relation: 'owner' | 'trusted' | 'external'): ConversationTrack {
  const cleanId = userId.trim()
  const group = relation === 'owner'
    ? { key: 'qq-owner-private', label: '主人 QQ 私聊' }
    : relation === 'trusted'
      ? { key: 'qq-trusted-private', label: '可信 QQ 私聊' }
      : { key: 'qq-external-private', label: '外部 QQ 私聊' }
  const prefix = relation === 'owner' ? '主人QQ' : relation === 'trusted' ? '可信QQ' : '外部QQ'
  return {
    key: `qq:private:${cleanId}`,
    label: `${prefix} / ${cleanId}`,
    detail: `${prefix} ${cleanId} / QQ 私聊`,
    accountLabel: `${prefix} ${cleanId}`,
    avatarUrl: qqAvatarUrl(cleanId),
    groupKey: group.key,
    groupLabel: group.label,
    turns: [],
    canCompose: false,
    isOwner: relation === 'owner',
    isTrusted: relation !== 'external',
    latestIndex: relation === 'owner' ? -900 : -800
  }
}

function seedQQGroupTrack(groupId: string): ConversationTrack {
  const cleanId = groupId.trim()
  return {
    key: `qq:group:${cleanId}`,
    label: `QQ群聊 / ${cleanId}`,
    detail: `群 ${cleanId} / QQ 群聊`,
    accountLabel: `群 ${cleanId}`,
    avatarUrl: qqGroupAvatarUrl(cleanId),
    groupKey: 'qq-group',
    groupLabel: 'QQ 群聊',
    turns: [],
    canCompose: false,
    isOwner: false,
    isTrusted: false,
    latestIndex: -700
  }
}

function qqAvatarUrl(userId: string): string {
  return /^\d{4,20}$/.test(userId) ? `https://q1.qlogo.cn/g?b=qq&nk=${userId}&s=100` : ''
}

function qqGroupAvatarUrl(groupId: string): string {
  return /^\d{4,20}$/.test(groupId) ? `https://p.qlogo.cn/gh/${groupId}/${groupId}/100` : ''
}

function conversationKey(turn: JsonRecord): string {
  const sessionKind = String(turn.sessionKind || '').toLowerCase()
  const messageType = String(turn.messageType || '').toLowerCase()
  const platform = String(turn.platform || '').toLowerCase()
  const userDisplayId = String(turn.userDisplayId || '').trim()
  const groupDisplayId = String(turn.groupDisplayId || '').trim()
  if (platform === 'desktop' || sessionKind === 'desktop_private' || messageType.startsWith('desktop')) return 'desktop:private:owner'
  if ((sessionKind === 'qq_group' || messageType.startsWith('group')) && groupDisplayId) {
    return userDisplayId ? `qq:group:${groupDisplayId}:${userDisplayId}` : `qq:group:${groupDisplayId}`
  }
  if ((sessionKind === 'qq_private' || messageType.startsWith('private')) && userDisplayId) return `qq:private:${userDisplayId}`
  const sessionHash = String(turn.sessionHash || '').trim()
  if (sessionHash) return `session:${sessionHash}`
  const parts = [turn.platform, turn.messageType, turn.userHash, turn.groupHash].map((part) => String(part || '').trim()).filter(Boolean)
  return parts.length ? `fallback:${parts.join(':')}` : 'fallback:desktop-owner'
}

function describeConversation(turn: JsonRecord): Omit<ConversationTrack, 'key' | 'turns' | 'latestIndex'> {
  const sessionKind = String(turn.sessionKind || '').toLowerCase()
  const messageType = String(turn.messageType || '').toLowerCase()
  const platform = String(turn.platform || '').toLowerCase()
  const isOwner = Boolean(turn.isOwner)
  const isTrusted = Boolean(turn.isTrusted)
  const senderName = compact(String(turn.senderName || ''), 28)
  const userHash = String(turn.userHash || '').slice(0, 8)
  const groupHash = String(turn.groupHash || '').slice(0, 8)
  const userDisplayId = String(turn.userDisplayId || '').trim()
  const groupDisplayId = String(turn.groupDisplayId || '').trim()
  const avatarUrl = String(turn.avatarUrl || '').trim()
  const explicitAccount = compact(String(turn.accountLabel || ''), 42)
  const explicitLabel = compact(String(turn.sessionLabel || ''), 34)
  const canCompose = isOwner && (platform === 'desktop' || sessionKind === 'desktop_private' || messageType.startsWith('desktop'))
  let label = explicitLabel
  if (!label) {
    if (canCompose) {
      label = '桌面主人'
    } else if (messageType.startsWith('group') || sessionKind === 'qq_group') {
      label = senderName ? `QQ群聊 / ${senderName}` : `QQ群聊 / #${groupHash || 'unknown'}`
    } else if (isOwner) {
      label = senderName ? `主人QQ / ${senderName}` : '主人QQ'
    } else if (isTrusted) {
      label = senderName ? `可信QQ / ${senderName}` : `可信QQ / #${userHash || 'unknown'}`
    } else {
      label = senderName ? `外部QQ / ${senderName}` : `外部QQ / #${userHash || 'unknown'}`
    }
  }
  const relation = isOwner ? '主人' : isTrusted ? '可信联系人' : messageType.startsWith('group') || sessionKind === 'qq_group' ? '群聊成员' : '外部联系人'
  const accountLabel = explicitAccount || fallbackAccountLabel({
    canCompose,
    isOwner,
    isTrusted,
    messageType,
    sessionKind,
    userDisplayId,
    groupDisplayId,
    userHash,
    groupHash
  })
  const group = conversationGroup({
    canCompose,
    isOwner,
    isTrusted,
    messageType,
    sessionKind
  })
  return {
    label,
    detail: `${accountLabel} / ${relation} / ${formatTurnMeta(turn)}`,
    accountLabel,
    avatarUrl,
    groupKey: group.key,
    groupLabel: group.label,
    canCompose,
    isOwner,
    isTrusted
  }
}

function fallbackAccountLabel(input: {
  canCompose: boolean
  isOwner: boolean
  isTrusted: boolean
  messageType: string
  sessionKind: string
  userDisplayId: string
  groupDisplayId: string
  userHash: string
  groupHash: string
}): string {
  if (input.canCompose) return '桌面 owner'
  if (input.messageType.startsWith('group') || input.sessionKind === 'qq_group') {
    const group = input.groupDisplayId || `#${input.groupHash || 'unknown'}`
    const user = input.userDisplayId || `#${input.userHash || 'unknown'}`
    return `群 ${group} / QQ ${user}`
  }
  const prefix = input.isOwner ? '主人QQ' : input.isTrusted ? '可信QQ' : '外部QQ'
  return `${prefix} ${input.userDisplayId || `#${input.userHash || 'unknown'}`}`
}

function conversationGroup(input: {
  canCompose: boolean
  isOwner: boolean
  isTrusted: boolean
  messageType: string
  sessionKind: string
}): { key: string; label: string } {
  if (input.canCompose) return { key: 'desktop', label: '桌面频道' }
  if (input.messageType.startsWith('group') || input.sessionKind === 'qq_group') return { key: 'qq-group', label: 'QQ 群聊' }
  if (input.isOwner) return { key: 'qq-owner-private', label: '主人 QQ 私聊' }
  if (input.isTrusted) return { key: 'qq-trusted-private', label: '可信 QQ 私聊' }
  if (input.sessionKind === 'qq_private' || input.messageType.startsWith('private')) return { key: 'qq-external-private', label: '外部 QQ 私聊' }
  return { key: 'system', label: '系统频道' }
}

function preferredConversationKey(conversations: ConversationTrack[]): string {
  return conversations.find((conversation) => conversation.key === 'desktop:private:owner')?.key || conversations.find((conversation) => conversation.canCompose)?.key || conversations.find((conversation) => conversation.isOwner)?.key || conversations[0]?.key || ''
}

function turnSpeakerLabel(turn: JsonRecord): string {
  if (Boolean(turn.isOwner)) return '你'
  return compact(String(turn.senderName || turn.sessionLabel || 'QQ联系人'), 24)
}

function ConversationStrip(props: {
  conversations: ConversationTrack[]
  activeKey: string
  onSelect: (key: string) => void
}): JSX.Element | null {
  const [collapsed, setCollapsed] = React.useState<Record<string, boolean>>({})
  if (!props.conversations.length) return null
  const groups = props.conversations.reduce<Array<{ key: string; label: string; conversations: ConversationTrack[] }>>((items, conversation) => {
    let group = items.find((item) => item.key === conversation.groupKey)
    if (!group) {
      group = { key: conversation.groupKey, label: conversation.groupLabel, conversations: [] }
      items.push(group)
    }
    group.conversations.push(conversation)
    return items
  }, [])
  return (
    <nav className="conversation-channel-panel" aria-label="会话频道">
      {groups.map((group) => (
        <section className="conversation-channel-group" key={group.key}>
          <button
            type="button"
            className="conversation-group-toggle"
            onClick={() => setCollapsed((current) => ({ ...current, [group.key]: !current[group.key] }))}
            aria-expanded={!collapsed[group.key]}
          >
            {collapsed[group.key] ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
            <span>{group.label}</span>
            <small>{group.conversations.length}</small>
          </button>

          {!collapsed[group.key] ? (
            <div className="conversation-channel-list">
              {group.conversations.map((conversation) => (
                <button
                  key={conversation.key}
                  type="button"
                  className={`${conversation.key === props.activeKey ? 'active' : ''} ${conversation.canCompose ? 'compose' : conversation.isOwner ? 'owner' : conversation.isTrusted ? 'trusted' : 'external'}`}
                  onClick={() => props.onSelect(conversation.key)}
                  aria-pressed={conversation.key === props.activeKey}
                  title={conversation.detail}
                >
                  <img
                    src={conversation.avatarUrl || avatarSrc}
                    alt=""
                    onError={(event) => {
                      event.currentTarget.src = avatarSrc
                    }}
                  />
                  <span>
                    <strong>{conversation.label}</strong>
                    <small>{conversation.accountLabel}</small>
                  </span>
                  <em>{conversation.turns.length}</em>
                </button>
              ))}
            </div>
          ) : null}
        </section>
      ))}
    </nav>
  )
}

export function InteractionStream(props: {
  xinyuState: XinYuState
  turns: unknown[]
  commands: CommandState[]
  events: DesktopEvent[]
  qqRuntimeConfig: QQRuntimeConfig | null
  input: string
  codexMode: boolean
  allowLocalWrite: boolean
  sending: boolean
  onInput: (value: string) => void
  onCodexModeChange: (value: boolean) => void
  onLocalWriteChange: (value: boolean) => void
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
}): JSX.Element {
  const streamRef = React.useRef<HTMLDivElement | null>(null)
  const conversations = React.useMemo(() => buildConversationTracks(props.turns, props.qqRuntimeConfig), [props.turns, props.qqRuntimeConfig])
  const [activeConversationKey, setActiveConversationKey] = React.useState('')
  React.useEffect(() => {
    if (!conversations.length) {
      if (activeConversationKey) setActiveConversationKey('')
      return
    }
    if (!conversations.some((conversation) => conversation.key === activeConversationKey)) {
      setActiveConversationKey(preferredConversationKey(conversations))
    }
  }, [activeConversationKey, conversations])
  const activeConversation = conversations.find((conversation) => conversation.key === activeConversationKey) || conversations[0]
  const visibleTurns = activeConversation?.turns || props.turns
  const canCompose = activeConversation?.canCompose ?? true
  const visibleCommands = canCompose ? props.commands : []
  const activeLabel = activeConversation?.label || '桌面主人'

  React.useLayoutEffect(() => {
    const element = streamRef.current
    if (!element) return
    element.scrollTop = element.scrollHeight
  }, [visibleTurns, visibleCommands, activeConversationKey])

  function handleStreamWheel(event: React.WheelEvent<HTMLDivElement>): void {
    const element = streamRef.current
    if (!element || element.scrollHeight <= element.clientHeight) {
      return
    }
    const before = element.scrollTop
    element.scrollTop += event.deltaY
    if (element.scrollTop !== before) {
      event.preventDefault()
    }
  }

  return (
    <section className="interaction-panel">
      <header className="stream-head">
        <div>
          <p className="label">会话频道</p>
          <h2>{activeLabel}</h2>
        </div>
        <span className="continuity-pill">
          <History size={14} />
          {props.xinyuState.continuity}
        </span>
      </header>

      <div className="stream-body" onWheel={handleStreamWheel}>
        <ConversationStrip conversations={conversations} activeKey={activeConversationKey} onSelect={setActiveConversationKey} />

        <div className="stream-scroll" ref={streamRef}>
          <div className="presence-note">
            <Sparkles size={16} />
            <p>{canCompose ? `当前窗口：${activeLabel}，同步到 ${formatTime(props.xinyuState.lastShiftAt)}` : `只读观察：${activeLabel}，同步到 ${formatTime(props.xinyuState.lastShiftAt)}`}</p>
          </div>

          <ChatTimeline turns={visibleTurns} commands={visibleCommands} />
        </div>
        <EventRibbon events={props.events} />
      </div>

      <ChatInput
        value={props.input}
        codexMode={props.codexMode}
        allowLocalWrite={props.allowLocalWrite}
        sending={props.sending}
        disabled={!canCompose}
        disabledReason={`当前在观察 ${activeLabel}`}
        onChange={props.onInput}
        onCodexModeChange={props.onCodexModeChange}
        onLocalWriteChange={props.onLocalWriteChange}
        onSubmit={props.onSubmit}
      />
    </section>
  )
}

function ChatTimeline(props: { turns: unknown[]; commands: CommandState[] }): JSX.Element {
  const turns = props.turns.slice(-40).map(asRecord)
  const renderedCommandIds = new Set(turns.map((turn) => String(turn.commandId || '')).filter(Boolean))
  const renderedTurnIds = new Set(turns.map((turn) => String(turn.turnId || '')).filter(Boolean))
  const pendingCommands = props.commands
    .filter((command) => command.status !== 'finished')
    .filter((command) => !isCommandRenderedByTurn(command, renderedCommandIds, renderedTurnIds))
    .slice()
    .reverse()

  if (turns.length === 0 && pendingCommands.length === 0) {
    return (
      <div className="empty-conversation">
        <img src={avatarSrc} alt="" />
        <div>
          <strong>还没有这次会话的第一句话</strong>
          <span>核心接上后，聊天、主动意图和记忆回声会在这里形成连续线。</span>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-timeline">
      {turns.map((turn, index) => (
        <React.Fragment key={`${String(turn.turnId || index)}-${index}`}>
          <MessageBubble side={Boolean(turn.isOwner) ? 'owner' : 'contact'} speaker={turnSpeakerLabel(turn)} text={String(turn.textPreview || '...')} meta={formatTurnMeta(turn)} />
          <MessageBubble
            side="xinyu"
            speaker="心玉"
            text={String(turn.replyPreview || statusLabel(String(turn.status || 'finished')))}
            meta={formatLatency(turn)}
          />
        </React.Fragment>
      ))}

      {pendingCommands.map((command) => (
        <MessageBubble
          key={command.commandId}
          side="owner"
          speaker="你"
          text={command.textPreview}
          meta={commandStatusLabel(command.status)}
          pending
        />
      ))}
    </div>
  )
}

function MessageBubble(props: {
  side: 'owner' | 'contact' | 'xinyu'
  speaker: string
  text: string
  meta: string
  pending?: boolean
}): JSX.Element {
  return (
    <article className={`message-row ${props.side} ${props.pending ? 'pending' : ''}`}>
      {props.side === 'xinyu' ? <img src={avatarSrc} alt="" /> : null}
      <div className="message-bubble">
        <span>{props.speaker}</span>
        <p>{props.text}</p>
        <small>{props.meta}</small>
      </div>
    </article>
  )
}

function EventRibbon(props: { events: DesktopEvent[] }): JSX.Element {
  const events = props.events.slice(0, 5)
  return (
    <section className="event-ribbon">
      <div className="section-head">
        <Activity size={15} />
        <span>最近事件</span>
      </div>
      {!events.length ? <p className="quiet-text">等待核心事件流。</p> : null}
      <div className="event-list">
        {events.map((event) => (
          <div className={`event-row ${event.severity || ''}`} key={event.id || `${event.type}-${event.ts}`}>
            <span>{eventLabel(event.type)}</span>
            <small>{formatTime(event.ts)}</small>
          </div>
        ))}
      </div>
    </section>
  )
}

function ChatInput(props: {
  value: string
  codexMode: boolean
  allowLocalWrite: boolean
  sending: boolean
  disabled?: boolean
  disabledReason?: string
  onChange: (value: string) => void
  onCodexModeChange: (value: boolean) => void
  onLocalWriteChange: (value: boolean) => void
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
}): JSX.Element {
  const disabled = props.sending || Boolean(props.disabled)
  return (
    <form className={`composer ${props.codexMode ? 'codex-mode' : ''} ${props.disabled ? 'viewer-mode' : ''}`} onSubmit={props.onSubmit}>
      <button
        type="button"
        className={`composer-mode-button ${props.codexMode ? 'active' : ''}`}
        onClick={() => props.onCodexModeChange(!props.codexMode)}
        disabled={disabled}
        title="Codex"
        aria-label="Codex"
        aria-pressed={props.codexMode}
      >
        {props.codexMode ? <Terminal size={16} /> : <MessageCircle size={16} />}
      </button>
      <button
        type="button"
        className={`composer-mode-button write ${props.allowLocalWrite ? 'active' : ''}`}
        onClick={() => props.onLocalWriteChange(!props.allowLocalWrite)}
        disabled={disabled || !props.codexMode}
        title="允许本地落盘"
        aria-label="允许本地落盘"
        aria-pressed={props.allowLocalWrite}
      >
        <Save size={16} />
      </button>
      <input
        value={props.value}
        onChange={(event) => props.onChange(event.currentTarget.value)}
        placeholder={props.disabled ? props.disabledReason || '当前窗口只读' : props.codexMode ? 'Codex task' : '今晚想让心玉接住什么？'}
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !props.value.trim()} title="发送">
        <Send size={16} />
      </button>
    </form>
  )
}

export function IntentQueuePanel(props: {
  intents: ProactiveIntent[]
  pending: Record<string, ProactiveAction>
  actionDigest?: unknown
  recentMemoryEvents: unknown[]
  lastEvent?: DesktopEvent
  qqEnvironment: QQEnvironmentStatus | null
  qqAction: QQActionState
  qqRuntimeConfig: QQRuntimeConfig | null
  qqRuntimeAction: QQRuntimeActionState
  stickerLibrary: StickerLibrary | null
  stickerAction: StickerActionState
  onAck: (candidateId: string, action: ProactiveAction) => void
  onOpenDetail: (candidateId: string) => void
  onRefreshQQ: () => void
  onStartQQ: () => void
  onOpenNapCat: () => void
  onCopyNapCatToken: () => void
  onSetQQRuntimeConfig: (patch: QQRuntimeConfigPatch) => void
  onRestartQQGateway: () => void
  onRefreshStickerLibrary: () => void
  onRunStickerMaintenance: (action: 'import-pending' | 'rebuild-index') => void
  onMoveStickerToMood: (file: string, mood: string) => void
  onOpenStickerAssetDir: () => void
}): JSX.Element {
  return (
    <aside className="intent-panel">
      <header className="intent-head">
        <div>
          <p className="label"> </p>
          <h2>主动提醒</h2>
        </div>
        <span>{props.intents.length}</span>
      </header>

      <section className="intent-list">
        {!props.intents.length ? (
          <div className="empty-intents">
            <Bell size={18} />
            <strong>暂无候选</strong>
            <span> </span>
          </div>
        ) : null}

        {props.intents.map((intent) => (
          <IntentRow
            key={intent.id}
            intent={intent}
            pendingAction={props.pending[intent.id]}
            onAck={props.onAck}
            onOpenDetail={props.onOpenDetail}
          />
        ))}
      </section>

      <QQBridgePanel
        status={props.qqEnvironment}
        action={props.qqAction}
        runtimeConfig={props.qqRuntimeConfig}
        runtimeAction={props.qqRuntimeAction}
        onRefresh={props.onRefreshQQ}
        onStart={props.onStartQQ}
        onOpenWebUI={props.onOpenNapCat}
        onCopyToken={props.onCopyNapCatToken}
        onSetRuntimeConfig={props.onSetQQRuntimeConfig}
        onRestartGateway={props.onRestartQQGateway}
      />

      <StickerLibraryPanel
        library={props.stickerLibrary}
        action={props.stickerAction}
        onRefresh={props.onRefreshStickerLibrary}
        onRunMaintenance={props.onRunStickerMaintenance}
        onMoveStickerToMood={props.onMoveStickerToMood}
        onOpenAssetDir={props.onOpenStickerAssetDir}
      />

      <ActionDigestPanel digest={props.actionDigest} />

      <ContinuityPanel recentMemoryEvents={props.recentMemoryEvents} lastEvent={props.lastEvent} />
    </aside>
  )
}

export function ImpulseObserverDialog(props: {
  soup: ImpulseSoupState | null
  loading: boolean
  onClose: () => void
  onRefresh: () => void
}): JSX.Element {
  const soup = props.soup
  const thoughtlets = soup?.thoughtlets.slice(0, 12) || []
  const trace = soup?.traceTail.slice(-8).reverse() || []
  const activeRatio = soup && soup.thoughtletCount > 0 ? Math.round((soup.activeCount / soup.thoughtletCount) * 100) : 0
  const readout = impulseReadout(soup)
  const desireGroups = impulseDesireGroups(soup)
  return (
    <div className="impulse-observer-backdrop" onClick={props.onClose}>
      <section className="impulse-observer" onClick={(event) => event.stopPropagation()}>
        <header className="impulse-observer-head">
          <div>
            <p className="label">本地生态</p>
            <h2>涌现池</h2>
          </div>
          <div className="impulse-observer-actions">
            <button type="button" onClick={props.onRefresh} title="刷新涌现状态">
              <RefreshCw size={15} className={props.loading ? 'spin' : ''} />
            </button>
            <button type="button" onClick={props.onClose} title="关闭观察窗">
              <X size={16} />
            </button>
          </div>
        </header>

        <div className="impulse-overview">
          <div className="impulse-radar" aria-hidden="true">
            <span />
            <strong>{soup?.topEnergy ?? 0}</strong>
          </div>
          <div className="impulse-status-lines">
            <span>
              <small>最高欲望</small>
              <strong>{compact(impulseLabel(soup?.topDesireShape), 34)}</strong>
            </span>
            <span>
              <small>下一动作</small>
              <strong>{compact(impulseLabel(soup?.topAction), 34)}</strong>
            </span>
            <span>
              <small>更新时间</small>
              <strong>{formatTime(soup?.updatedAt)}</strong>
            </span>
          </div>
          <div className="impulse-safety">
            <ShieldAlert size={16} />
            <span>{soup?.outwardActionAllowed ? '外向动作已开放' : '外向动作已阻断'}</span>
          </div>
        </div>

        <section className={`impulse-readout ${readout.tone}`} aria-label="涌现池状态判读">
          <div>
            <small>状态判读</small>
            <strong>{readout.title}</strong>
            <p>{readout.detail}</p>
          </div>
          <div className="impulse-group-list" aria-label="活跃念头分类">
            {!desireGroups.length ? <span>暂无分类</span> : null}
            {desireGroups.map((group) => (
              <span key={group.key}>
                <strong>{group.label}</strong>
                <small>
                  {group.count} 条 · 最高 {group.topEnergy}
                </small>
              </span>
            ))}
          </div>
        </section>

        <section className="impulse-metrics" aria-label="涌现池指标">
          <ImpulseMetric label="念头" value={soup?.thoughtletCount || 0} />
          <ImpulseMetric label="活跃" value={soup?.activeCount || 0} />
          <ImpulseMetric label="谱系" value={soup?.lineageCount || 0} />
          <ImpulseMetric label="软意图" value={soup?.softActiveCount || 0} />
          <ImpulseMetric label="隔离" value={soup?.quarantinedCount || 0} />
        </section>

        <div className="impulse-activity-bar" aria-label="活跃念头比例">
          <span style={{ width: `${activeRatio}%` }} />
        </div>

        <div className="impulse-grid">
          <section className="impulse-section">
            <div className="section-head">
              <Brain size={15} />
              <span>念头列表</span>
            </div>
            <div className="thoughtlet-list">
              {!thoughtlets.length ? <p className="quiet-text">暂无涌现状态。</p> : null}
              {thoughtlets.map((item) => (
                <article className={`thoughtlet-row ${item.status}`} key={item.thoughtletId || item.lineageId}>
                  <div className="thoughtlet-row-head">
                    <strong>{compact(impulseLabel(item.desireShape), 34)}</strong>
                    <span>{item.energy}</span>
                  </div>
                  <div className="thoughtlet-intent-grid">
                    <span>
                      <small>意图动作</small>
                      <strong>{compact(impulseLabel(item.proposedNextAction), 48)}</strong>
                    </span>
                    <span>
                      <small>触发来源</small>
                      <strong>{compact(impulseLabel(item.sourceKind), 42)}</strong>
                    </span>
                    <span>
                      <small>抑制规则</small>
                      <strong>{compact(impulseLabel(item.inhibitionRule), 48)}</strong>
                    </span>
                    <span>
                      <small>风险标记</small>
                      <strong>{compact(riskFlagsLabel(item.riskFlags), 48)}</strong>
                    </span>
                  </div>
                  <p className="thoughtlet-evidence">
                    <small>触发依据</small>
                    <span>{compact(item.evidencePreview || item.sourceRef || '没有更具体的文本，只保留结构化意图。', 120)}</span>
                  </p>
                  <div className="thoughtlet-energy" aria-hidden="true">
                    <span style={{ width: `${Math.max(0, Math.min(100, item.energy))}%` }} />
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="impulse-section">
            <div className="section-head">
              <History size={15} />
              <span>最近循环</span>
            </div>
            <div className="impulse-trace-list">
              {!trace.length ? <p className="quiet-text">等待循环轨迹。</p> : null}
              {trace.map((event, index) => (
                <div className="impulse-trace-row" key={`${event.observedAt}-${index}`}>
                  <span>{formatTime(event.observedAt)}</span>
                  <strong>{compact(impulseLabel(event.topDesireShape), 28)}</strong>
                  <small>
                    种子 {event.seedCount} · 更新 {event.updatedCount} · 派生 {event.spawnedCount}
                  </small>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </div>
  )
}

function ImpulseMetric(props: { label: string; value: number }): JSX.Element {
  return (
    <span>
      <strong>{props.value}</strong>
      <small>{props.label}</small>
    </span>
  )
}

function StickerLibraryPanel(props: {
  library: StickerLibrary | null
  action: StickerActionState
  onRefresh: () => void
  onRunMaintenance: (action: 'import-pending' | 'rebuild-index') => void
  onMoveStickerToMood: (file: string, mood: string) => void
  onOpenAssetDir: () => void
}): JSX.Element {
  const library = props.library
  const [dragFile, setDragFile] = React.useState('')
  const [dropMood, setDropMood] = React.useState('')
  const topMoods = library
    ? Object.entries(library.counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 6)
    : []
  const focusRows =
    library?.items
      .filter((item) => item.mood === 'unclear' || !item.confirmed)
      .slice(0, 8) || []
  const recent = focusRows.length ? focusRows : library?.items.slice(0, 8) || []
  const busy = props.action.kind !== 'idle'
  function handleDrop(event: React.DragEvent<HTMLButtonElement>, mood: string): void {
    event.preventDefault()
    const file = dragFile || event.dataTransfer.getData('application/x-xinyu-sticker')
    setDropMood('')
    setDragFile('')
    if (!busy && file) {
      props.onMoveStickerToMood(file, mood)
    }
  }
  return (
    <section className="sticker-library-panel">
      <div className="section-head">
        <Sparkles size={15} />
        <span>表情库</span>
        <button type="button" onClick={props.onRefresh} disabled={busy} title="Refresh sticker index" aria-label="Refresh sticker index">
          <RefreshCw size={14} className={busy ? 'spin' : ''} />
        </button>
        <button type="button" onClick={() => props.onRunMaintenance('import-pending')} disabled={busy} title="Import pending stickers" aria-label="Import pending stickers">
          <Play size={14} />
        </button>
        <button type="button" onClick={() => props.onRunMaintenance('rebuild-index')} disabled={busy} title="Rebuild sticker index" aria-label="Rebuild sticker index">
          <Clipboard size={14} />
        </button>
        <button type="button" onClick={props.onOpenAssetDir} disabled={busy} title="Open sticker folder" aria-label="Open sticker folder">
          <ExternalLink size={14} />
        </button>
      </div>

      <div className="sticker-metrics">
        <Metric label="总数" value={library?.total || 0} />
        <Metric label="OCR" value={library?.ocr || 0} />
        <Metric label="确认" value={library?.confirmed || 0} />
        <Metric label="待看" value={library?.unclear || 0} />
      </div>

      <div className="sticker-health">
        <span>
          自动发送
          <strong>{library?.autoSend || 0}</strong>
        </span>
        <span>
          待确认
          <strong>{library?.unconfirmed || 0}</strong>
        </span>
        <span>
          纠错
          <strong>{library?.corrections || 0}</strong>
        </span>
        <span>
          参考
          <strong>{library?.referenceItems || 0}</strong>
        </span>
      </div>

      <div className="sticker-moods">
        {topMoods.map(([mood, count]) => (
          <span key={mood}>
            {stickerMoodLabel(mood)}
            <strong>{count}</strong>
          </span>
        ))}
        {!topMoods.length ? <small>等待 manifest.generated.json</small> : null}
      </div>

      <div className="sticker-correction-targets">
        {stickerCorrectionMoods.map(([mood, label]) => (
          <button
            type="button"
            key={mood}
            className={dropMood === mood ? 'is-drop-target' : ''}
            aria-label={`归到${label}`}
            aria-disabled={busy || !dragFile}
            title={`归到${label}`}
            onDragEnter={(event) => {
              event.preventDefault()
              if (!busy && dragFile) {
                setDropMood(mood)
              }
            }}
            onDragOver={(event) => {
              if (!busy && dragFile) {
                event.preventDefault()
                event.dataTransfer.dropEffect = 'move'
              }
            }}
            onDragLeave={() => {
              if (dropMood === mood) {
                setDropMood('')
              }
            }}
            onDrop={(event) => handleDrop(event, mood)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="sticker-rows">
        {recent.map((item) => (
          <div
            className={`sticker-row ${dragFile === item.file ? 'is-dragging' : ''}`}
            key={item.file}
            draggable={!busy && Boolean(item.file)}
            title={item.file}
            onDragStart={(event) => {
              event.dataTransfer.effectAllowed = 'move'
              event.dataTransfer.setData('application/x-xinyu-sticker', item.file)
              event.dataTransfer.setData('text/plain', item.file)
              setDragFile(item.file)
            }}
            onDragEnd={() => {
              setDragFile('')
              setDropMood('')
            }}
          >
            <strong>{item.moodLabel || stickerMoodLabel(item.mood)}</strong>
            <span>
              <span>{compact(item.ocrText || item.file, 46)}</span>
              <small>{stickerClipLabel(item)}</small>
            </span>
            <em>{item.mood === 'unclear' ? '待看' : item.confirmed ? '确认' : item.autoSend ? '自动' : '保留'}</em>
          </div>
        ))}
      </div>

      <footer className="sticker-foot">
        <span>{library ? formatTime(library.updatedAt) : '--:--'}</span>
        <span>{library ? `${library.corrections} 次纠错 / ${library.referenceItems} 组参考` : '未读取'}</span>
      </footer>
      {props.action.message ? <small className="qq-action-note">{props.action.message}</small> : null}
    </section>
  )
}

function Metric(props: { label: string; value: number }): JSX.Element {
  return (
    <div>
      <strong>{props.value}</strong>
      <small>{props.label}</small>
    </div>
  )
}

function QQBridgePanel(props: {
  status: QQEnvironmentStatus | null
  action: QQActionState
  runtimeConfig: QQRuntimeConfig | null
  runtimeAction: QQRuntimeActionState
  onRefresh: () => void
  onStart: () => void
  onOpenWebUI: () => void
  onCopyToken: () => void
  onSetRuntimeConfig: (patch: QQRuntimeConfigPatch) => void
  onRestartGateway: () => void
}): JSX.Element {
  const services = props.status?.services?.length ? props.status.services : defaultQQServices()
  const readyCount = services.filter((service) => service.ok).length
  const allReady = Boolean(props.status?.allReady)
  const firstBroken = services.find((service) => !service.ok)
  const busy = props.action.kind !== 'idle'
  const checkedAt = props.status?.checkedAt ? formatTime(props.status.checkedAt) : '--:--'
  const tokenAvailable = Boolean(props.status?.tokenAvailable)
  const diagnosis = qqDiagnosisLabel(props.status?.diagnosis || '', tokenAvailable)

  return (
    <section className={`qq-bridge-panel ${allReady ? 'ready' : 'warn'}`}>
      <div className="section-head qq-bridge-head">
        <span>
          <Wifi size={15} />
          <span>QQ 链路</span>
        </span>
        <strong>{`${readyCount}/${services.length}`}</strong>
      </div>

      <div className="qq-bridge-summary">
        <span>{allReady ? 'NapCat 已接入' : firstBroken ? `${qqServiceLabel(firstBroken)} 未就绪` : '正在读取状态'}</span>
        <small>{checkedAt}</small>
      </div>
      <div className={`qq-login-hint ${allReady ? 'ready' : ''}`}>
        <span>{diagnosis}</span>
        <small>{tokenAvailable ? 'token 可复制' : '未找到 token'}</small>
      </div>

      <div className="qq-service-list">
        {services.map((service) => (
          <div className={`qq-service-row ${service.ok ? 'ok' : 'warn'}`} key={service.key}>
            <span className={`qq-service-dot ${service.ok ? 'ok' : 'warn'}`} />
            <div>
              <strong>{qqServiceLabel(service)}</strong>
              <small>{service.endpoint}</small>
            </div>
            <em>{qqDetailLabel(service.detail)}</em>
          </div>
        ))}
      </div>

      <QQRuntimeControls
        config={props.runtimeConfig}
        action={props.runtimeAction}
        onSetRuntimeConfig={props.onSetRuntimeConfig}
        onRestartGateway={props.onRestartGateway}
      />

      <div className="qq-bridge-actions">
        <button type="button" onClick={props.onStart} disabled={busy} title="启动 QQ 环境" aria-label="启动 QQ 环境">
          <Play size={15} />
        </button>
        <button
          type="button"
          onClick={props.onCopyToken}
          disabled={busy || !tokenAvailable}
          title="复制 WebUI token"
          aria-label="复制 WebUI token"
        >
          <Clipboard size={15} />
        </button>
        <button
          type="button"
          onClick={props.onOpenWebUI}
          disabled={busy}
          title="打开 NapCat WebUI"
          aria-label="打开 NapCat WebUI"
        >
          <ExternalLink size={15} />
        </button>
        <button type="button" onClick={props.onRefresh} disabled={busy} title="重新检查" aria-label="重新检查">
          <RefreshCw size={15} className={props.action.kind === 'refreshing' ? 'spin' : ''} />
        </button>
      </div>

      {props.action.message ? <small className="qq-action-note">{props.action.message}</small> : null}
    </section>
  )
}

function QQRuntimeControls(props: {
  config: QQRuntimeConfig | null
  action: QQRuntimeActionState
  onSetRuntimeConfig: (patch: QQRuntimeConfigPatch) => void
  onRestartGateway: () => void
}): JSX.Element {
  const config = props.config || defaultQQRuntimeConfig()
  const busy = props.action.kind !== 'idle'
  const groupScope = !config.allowGroupMessages
    ? '关闭'
    : config.allowedGroupIds.length
      ? config.allowedGroupIds.join(', ')
      : '未限定'
  const shadowScope = !config.groupShadowEnabled
    ? '关闭'
    : config.groupShadowAllowedGroupIds.length
      ? config.groupShadowAllowedGroupIds.join(', ')
      : '未限定'
  const setList = (key: keyof Pick<QQRuntimeConfigPatch, 'allowedGroupIds' | 'groupShadowAllowedGroupIds' | 'blockedUserIds' | 'blockedGroupIds'>, ids: string[]): void => {
    props.onSetRuntimeConfig({ [key]: ids })
  }

  return (
    <div className="qq-runtime-controls">
      <div className="qq-runtime-switches">
        <RuntimeSwitch
          label="其他人私聊"
          checked={config.allowExternalPrivate}
          detail={config.allowExternalPrivate ? '开放' : '仅名单'}
          disabled={busy || !props.config}
          onToggle={() => props.onSetRuntimeConfig({ allowExternalPrivate: !config.allowExternalPrivate })}
        />
        <RuntimeSwitch
          label="群聊回复"
          checked={config.allowGroupMessages}
          detail={config.allowGroupMessages ? '可回复' : '关闭'}
          danger={config.allowGroupMessages}
          disabled={busy || !props.config}
          onToggle={() => props.onSetRuntimeConfig({ allowGroupMessages: !config.allowGroupMessages })}
        />
        <RuntimeSwitch
          label="群聊观察"
          checked={config.groupShadowEnabled}
          detail={config.groupShadowEnabled ? 'shadow' : '关闭'}
          disabled={busy || !props.config}
          onToggle={() => props.onSetRuntimeConfig({ groupShadowEnabled: !config.groupShadowEnabled })}
        />
        <RuntimeSwitch
          label="消息发送"
          checked={config.sendReplies}
          detail={config.sendReplies ? '开启' : '静默'}
          danger={!config.sendReplies}
          disabled={busy || !props.config}
          onToggle={() => props.onSetRuntimeConfig({ sendReplies: !config.sendReplies })}
        />
      </div>

      <div className="qq-runtime-scope">
        <span>
          <strong>群回复</strong>
          <em>{groupScope}</em>
        </span>
        <span>
          <strong>shadow</strong>
          <em>{shadowScope}</em>
        </span>
      </div>

      <div className="qq-runtime-lists">
        <IdListEditor
          label="回复群"
          placeholder="群号"
          ids={config.allowedGroupIds}
          disabled={busy}
          onChange={(ids) => setList('allowedGroupIds', ids)}
        />
        <IdListEditor
          label="观察群"
          placeholder="群号"
          ids={config.groupShadowAllowedGroupIds}
          disabled={busy}
          onChange={(ids) => setList('groupShadowAllowedGroupIds', ids)}
        />
        <IdListEditor
          label="群黑名单"
          placeholder="群号"
          ids={config.blockedGroupIds}
          disabled={busy}
          onChange={(ids) => setList('blockedGroupIds', ids)}
        />
        <IdListEditor
          label="用户黑名单"
          placeholder="QQ 号"
          ids={config.blockedUserIds}
          disabled={busy}
          onChange={(ids) => setList('blockedUserIds', ids)}
        />
      </div>

      <button
        type="button"
        className="qq-runtime-restart"
        onClick={props.onRestartGateway}
        disabled={busy}
        title="重启 QQ 网关"
        aria-label="重启 QQ 网关"
      >
        <TimerReset size={14} className={props.action.kind === 'restarting' ? 'spin' : ''} />
        <span>重启网关</span>
      </button>

      {props.action.message ? <small className="qq-runtime-note">{props.action.message}</small> : null}
    </div>
  )
}

function IdListEditor(props: {
  label: string
  placeholder: string
  ids: string[]
  disabled?: boolean
  onChange: (ids: string[]) => void
}): JSX.Element {
  const [value, setValue] = React.useState('')
  const normalizedIds = props.ids.filter(Boolean)

  function addValue(): void {
    const nextId = value.trim()
    if (!/^\d{5,20}$/.test(nextId) || normalizedIds.includes(nextId)) {
      setValue('')
      return
    }
    setValue('')
    props.onChange([...normalizedIds, nextId])
  }

  function removeValue(id: string): void {
    props.onChange(normalizedIds.filter((item) => item !== id))
  }

  return (
    <div className="id-list-editor">
      <div className="id-list-head">
        <strong>{props.label}</strong>
        <small>{normalizedIds.length}</small>
      </div>
      <div className="id-list-chips">
        {normalizedIds.map((id) => (
          <span key={id}>
            {id}
            <button type="button" onClick={() => removeValue(id)} disabled={props.disabled} title={`移除 ${id}`} aria-label={`移除 ${id}`}>
              <Trash2 size={10} />
            </button>
          </span>
        ))}
        {!normalizedIds.length ? <em>空</em> : null}
      </div>
      <div className="id-list-input">
        <input
          value={value}
          disabled={props.disabled}
          placeholder={props.placeholder}
          inputMode="numeric"
          onChange={(event) => setValue(event.target.value.replace(/[^\d]/g, '').slice(0, 20))}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault()
              addValue()
            }
          }}
        />
        <button type="button" onClick={addValue} disabled={props.disabled || !value.trim()} title="添加" aria-label="添加">
          <Plus size={12} />
        </button>
      </div>
    </div>
  )
}

function RuntimeSwitch(props: {
  label: string
  checked: boolean
  detail: string
  danger?: boolean
  disabled?: boolean
  onToggle: () => void
}): JSX.Element {
  return (
    <button
      type="button"
      className={`runtime-switch ${props.checked ? 'is-on' : 'is-off'} ${props.danger ? 'is-danger' : ''}`}
      aria-pressed={props.checked}
      disabled={props.disabled}
      onClick={props.onToggle}
      title={props.label}
    >
      <span>
        <strong>{props.label}</strong>
        <small>{props.detail}</small>
      </span>
      <i aria-hidden="true" />
    </button>
  )
}

function IntentRow(props: {
  intent: ProactiveIntent
  pendingAction?: ProactiveAction
  onAck: (candidateId: string, action: ProactiveAction) => void
  onOpenDetail: (candidateId: string) => void
}): JSX.Element {
  const disabled = Boolean(props.pendingAction)
  return (
    <article
      className={`intent-row risk-${props.intent.risk} ${props.intent.claimable ? '' : 'not-claimable'}`}
      role="button"
      tabIndex={0}
      onClick={(event) => {
        if ((event.target as HTMLElement).closest('button')) return
        props.onOpenDetail(props.intent.id)
      }}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          props.onOpenDetail(props.intent.id)
        }
      }}
    >
      <div className="intent-meta">
        <span>{props.intent.source}</span>
        <strong>{props.intent.trigger}</strong>
      </div>
      <p>{props.intent.plannedText}</p>
      <div className="intent-foot">
        <span className="risk-label">
          <ShieldAlert size={13} />
          {props.intent.riskLabel}
        </span>
        <span>{props.intent.delivery}</span>
      </div>
      <div className="intent-actions">
        <button disabled={disabled} onClick={() => props.onAck(props.intent.id, 'read_locally')} title="只在本地读过">
          <Eye size={14} />
        </button>
        <button
          disabled={disabled || !props.intent.claimable}
          onClick={() => props.onAck(props.intent.id, 'approve_qq')}
          title={props.intent.claimable ? '同意发送到 QQ' : '本地预览不能直接发 QQ'}
        >
          <Send size={14} />
        </button>
        <button disabled={disabled} onClick={() => props.onAck(props.intent.id, 'dismiss')} title="忽略">
          <X size={14} />
        </button>
      </div>
      {props.pendingAction ? <small className="pending-action">{actionLabel(props.pendingAction)}</small> : null}
    </article>
  )
}

export function IntentDetailDialog(props: {
  intent: ProactiveIntent
  pendingAction?: ProactiveAction
  onClose: () => void
  onAck: (candidateId: string, action: ProactiveAction) => void
  onReply: (intent: ProactiveIntent, text: string) => void
}): JSX.Element {
  const disabled = Boolean(props.pendingAction)
  const text = props.intent.fullText || props.intent.plannedText
  const [replyText, setReplyText] = React.useState('')

  return (
    <div className="intent-dialog-backdrop" onClick={props.onClose}>
      <section
        className="intent-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="intent-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="intent-dialog-head">
          <div>
            <p className="label">主动预览</p>
            <h3 id="intent-dialog-title">{props.intent.trigger}</h3>
          </div>
          <button type="button" onClick={props.onClose} title="Close">
            <X size={16} />
          </button>
        </header>

        <div className="intent-dialog-body">
          <div className="intent-dialog-message">{text}</div>
          <dl className="intent-dialog-facts">
            <div>
              <dt>来源</dt>
              <dd>{props.intent.source}</dd>
            </div>
            <div>
              <dt>投递</dt>
              <dd>{props.intent.delivery}</dd>
            </div>
            <div>
              <dt>状态</dt>
              <dd>{props.intent.status || 'pending'}</dd>
            </div>
            <div>
              <dt>动作</dt>
              <dd>{props.intent.requestedAction || 'owner_ack'}</dd>
            </div>
            <div>
              <dt>创建</dt>
              <dd>{formatTime(props.intent.createdAt)}</dd>
            </div>
            <div>
              <dt>过期</dt>
              <dd>{formatTime(props.intent.expiresAt)}</dd>
            </div>
          </dl>
        </div>

        <footer className="intent-dialog-actions">
          <form
            className="intent-reply-form"
            onSubmit={(event) => {
              event.preventDefault()
              props.onReply(props.intent, replyText)
            }}
          >
            <textarea
              value={replyText}
              onChange={(event) => setReplyText(event.currentTarget.value)}
              placeholder="直接回复这条主动提醒..."
              disabled={disabled}
            />
            <button type="submit" disabled={disabled || !replyText.trim()}>
              <Send size={15} />
              回复
            </button>
          </form>
          <button
            type="button"
            disabled={disabled}
            onClick={() => props.onAck(props.intent.id, 'read_locally')}
          >
            <Eye size={15} />
            本地已读
          </button>
          <button
            type="button"
            disabled={disabled || !props.intent.claimable}
            onClick={() => props.onAck(props.intent.id, 'approve_qq')}
          >
            <Send size={15} />
            发送到 QQ
          </button>
          <button type="button" disabled={disabled} onClick={() => props.onAck(props.intent.id, 'dismiss')}>
            <X size={15} />
            忽略
          </button>
        </footer>
      </section>
    </div>
  )
}

function ActionDigestPanel(props: { digest?: unknown }): JSX.Element {
  const digest = asRecord(props.digest)
  const recent = Array.isArray(digest.recent) ? digest.recent.map((item) => asRecord(item)) : []
  const latest = recent.length ? recent[recent.length - 1] : {}
  const seedDetail = asRecord(latest.seed_detail)
  const lastDigest = asRecord(digest.last_digest)
  const seedIds = Array.isArray(lastDigest.dream_seed_ids)
    ? lastDigest.dream_seed_ids.map((item) => String(item || '')).filter(Boolean)
    : []
  const reflectionIds = Array.isArray(lastDigest.reflection_item_ids)
    ? lastDigest.reflection_item_ids.map((item) => String(item || '')).filter(Boolean)
    : []
  const seedId = String(latest.seed_id || seedIds[seedIds.length - 1] || '')
  const reflectionItemId = String(latest.reflection_item_id || reflectionIds[reflectionIds.length - 1] || '')
  const consumedAt = String(seedDetail.consumed_at || '')
  const updatedAt = String(digest.updated_at || latest.created_at || '')
  const digestedCount = Number(digest.digested_count || 0)
  const result = String(latest.result || 'unknown')
  const pressure = String(latest.pressure || 'unknown')
  const theme = digestThemeLabel(String(seedDetail.theme || (seedId ? '行动经验已进入沉淀' : '暂无行动经验沉淀')))
  const residue = digestResidueLabel(String(seedDetail.residue || ''), result, pressure)
  const dreamState = seedId ? (consumedAt && consumedAt !== 'none' ? '已被梦境消费' : '等待梦境输出') : '暂无梦种'

  return (
    <section className="action-digest-panel">
      <div className="section-head action-digest-head">
        <span>
          <History size={15} />
          <span>经历沉淀</span>
        </span>
        <strong>{digestedCount}</strong>
      </div>

      <div className="action-digest-summary">
        <strong>{dreamState}</strong>
        <small>{formatTime(updatedAt)}</small>
      </div>

      <div className="action-digest-flow">
        <span>
          <small>梦种</small>
          <strong>{compact(seedId || '等待行动', 28)}</strong>
        </span>
        <span>
          <small>反思</small>
          <strong>{compact(reflectionItemId || '未排队', 24)}</strong>
        </span>
      </div>

      <div className="action-digest-facts">
        <span>{digestResultLabel(result)}</span>
        <span>{digestPressureLabel(pressure)}</span>
      </div>

      <p className="action-digest-theme">{compact(theme, 64)}</p>
      <p className="action-digest-residue">{compact(residue, 120)}</p>
    </section>
  )
}

function ContinuityPanel(props: { recentMemoryEvents: unknown[]; lastEvent?: DesktopEvent }): JSX.Element {
  const latestMemory = asRecord(props.recentMemoryEvents[props.recentMemoryEvents.length - 1])
  return (
    <section className="continuity-panel">
      <div className="section-head">
        <Brain size={15} />
        <span>记忆回声</span>
      </div>
      <div className="continuity-row">
        <small>最近记忆</small>
        <strong>{memorySummary(latestMemory)}</strong>
      </div>
      <div className="continuity-row">
        <small>事件流</small>
        <strong>{props.lastEvent ? eventLabel(props.lastEvent.type) : '暂无事件'}</strong>
      </div>
      <div className="continuity-row">
        <small>详情</small>
        <strong>{props.recentMemoryEvents.length ? '已有可见回声' : '等待下一次写回'}</strong>
      </div>
    </section>
  )
}
