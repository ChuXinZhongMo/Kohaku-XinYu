import React from 'react'
import { Activity, Bell, Brain, Check, ChevronDown, ChevronRight, Clock3, Compass, Clipboard, Download, Eye, ExternalLink, Heart, History, MessageCircle, Play, Puzzle, Radio, RefreshCw, Save, Send, ShieldAlert, Sparkles, Terminal, TimerReset, Plus, Trash2, Wifi, X } from 'lucide-react'
import { EnvironmentValve } from './EnvironmentValve'
import { SurfacePart } from './AffectiveSurfaceProvider'
import type { ApiConfigActionState, ApiConfigProfile, ApiConfigProfilePatch, ApiConfigStatus, CommandState, DesktopEvent, ExternalPluginActionState, ExternalPluginConfigPatch, ExternalPluginControl, ExternalPluginInstallRequest, ExternalPluginsStatus, GatewayStatus, ImpulseSoupState, JsonRecord, ProactiveAction, ProactiveIntent, QQActionState, QQEnvironmentStatus, QQRuntimeActionState, QQRuntimeConfig, QQRuntimeConfigPatch, SelfActionSnapshot, Snapshot, StickerActionState, StickerLibrary, StickerRecord, ThemeName, XinYuState } from './desktopTypes'
import { actionLabel, asRecord, buildStats, commandStatusLabel, compact, defaultQQRuntimeConfig, defaultQQServices, digestPressureLabel, digestResidueLabel, digestResultLabel, digestThemeLabel, eventLabel, externalPluginInstallStateLabel, externalPluginNoteLabel, formatLatency, formatTime, formatTurnMeta, isCommandRenderedByTurn, memorySummary, platformLabel, qqDetailLabel, qqDiagnosisLabel, qqServiceLabel, riskLabel, runtimeLabel, sourceLabel, statusLabel, stickerClipLabel, stickerCorrectionMoods, stickerMoodLabel, themeOptions } from './desktopModel'

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

function selfActionKindLabel(value: string): string {
  if (!value) return '暂无动作'
  if (value === 'self_code_patch_request') return '代码补丁请求'
  if (value === 'stable_memory_change_request') return '稳定记忆变更请求'
  if (value === 'replay_material_probe') return '回放材料探测'
  if (value === 'learning_repair_probe') return '学习修复探测'
  return compact(value, 34)
}

function selfActionStatusLabel(value: string): string {
  if (!value) return '未观察'
  if (value === 'prepared') return '已准备'
  if (value === 'codex_scheduled') return '已授权执行'
  if (value === 'codex_completed') return '已完成'
  if (value === 'codex_timed_out') return '执行超时'
  if (value === 'codex_failed') return '执行失败'
  if (value === 'blocked') return '已阻断'
  if (value === 'executed') return '已执行'
  if (value === 'failed') return '失败'
  return compact(value, 24)
}

function selfActionCodexLabel(value: string): string {
  if (!value) return '未请求'
  if (value === 'not_requested') return '未请求执行'
  if (value === 'scheduled') return '已授权排队'
  if (value === 'finished') return '已完成'
  if (value === 'timed_out') return '执行超时'
  if (value === 'blocked') return '已阻断'
  if (value === 'running') return '执行中'
  if (value === 'completed') return '已完成'
  if (value === 'failed') return '失败'
  return compact(value, 28)
}

function selfActionFactValue(value: unknown, fallback = '暂无'): string {
  const text = String(value || '').trim()
  if (!text || text === 'none') return fallback
  return text
}

function selfActionFirstValue(values: unknown[], fallback = '暂无'): string {
  for (const value of values) {
    const text = String(value || '').trim()
    if (text && text !== 'none') return text
  }
  return fallback
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
  selfActionApprovalBusy: string
  onDecideSelfActionApproval: (
    queueId: string,
    decision: 'approved' | 'denied',
    options?: { authorizeExisting?: boolean }
  ) => void
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
      <SelfActionPanel
        selfAction={props.snapshot?.selfAction}
        busy={props.selfActionApprovalBusy}
        onDecide={props.onDecideSelfActionApproval}
      />

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

function SelfActionPanel(props: {
  selfAction?: SelfActionSnapshot
  busy: string
  onDecide: (queueId: string, decision: 'approved' | 'denied', options?: { authorizeExisting?: boolean }) => void
}): JSX.Element {
  const selfAction = props.selfAction
  const queue = asRecord(selfAction?.approvalQueue)
  const handoff = asRecord(selfAction?.handoff)
  const patch = asRecord(selfAction?.patchExecutor)
  const latestEvent = asRecord(selfAction?.latestApprovalEvent)
  const pendingValue = Number(selfAction?.pendingApprovalCount ?? queue.pendingCount ?? 0)
  const pendingCount = Number.isFinite(pendingValue) ? Math.max(0, pendingValue) : 0
  const observed = Boolean(selfAction?.observed)
  const patchStatus = selfActionFactValue(patch.status, '')
  const codexStatus = selfActionFactValue(patch.codexStatus, '')
  const taskId = selfActionFirstValue([patch.taskId], '')
  const currentGoal = selfActionFirstValue([selfAction?.selectedGoalId, patch.goalId, handoff.goalId], '暂无目标')
  const patchGoal = selfActionFirstValue([patch.goalId, handoff.goalId], '')
  const selectedGoal = taskId ? selfActionFirstValue([patchGoal, currentGoal], '暂无目标') : currentGoal
  const currentActionKind = selfActionFirstValue([selfAction?.selectedActionKind, patch.actionKind, handoff.actionKind, latestEvent.actionKind], '')
  const patchActionKind = selfActionFirstValue([patch.actionKind, handoff.actionKind, latestEvent.actionKind], '')
  const actionKind = taskId ? selfActionFirstValue([patchActionKind, currentActionKind], '') : currentActionKind
  const queueId = selfActionFirstValue([queue.latestPendingQueueId, queue.latestExecutedQueueId, handoff.queueId, latestEvent.queueId], '')
  const pendingQueueId = selfActionFirstValue([queue.latestPendingQueueId, selfAction?.latestPendingQueueId], '')
  const preparedQueueId = selfActionFirstValue([patch.queueId, handoff.queueId, queue.latestApprovedQueueId, queue.latestExecutedQueueId, latestEvent.queueId], '')
  const updatedAt = selfActionFirstValue([selfAction?.updatedAt, patch.updatedAt], '')
  const pendingQueueAvailable = pendingCount > 0 && Boolean(pendingQueueId)
  const preparedAuthorizationAvailable =
    !pendingQueueAvailable &&
    actionKind === 'self_code_patch_request' &&
    patchStatus === 'prepared' &&
    codexStatus === 'not_requested' &&
    Boolean(preparedQueueId)
  const approvalTargetId = pendingQueueAvailable ? pendingQueueId : preparedQueueId
  const busy = Boolean(props.busy)
  const tone = !observed
    ? 'idle'
    : pendingCount > 0
      ? 'warn'
      : patchStatus === 'blocked' || codexStatus === 'blocked'
        ? 'blocked'
        : patchStatus === 'prepared'
          ? 'prepared'
          : 'active'
  const headline = !observed ? '未观察' : pendingCount > 0 ? `${pendingCount} 待批准` : selfActionStatusLabel(patchStatus)
  const codexLine = codexStatus === 'not_requested'
    ? '已生成本地补丁任务，但还没有请求 Codex 真正执行。'
    : codexStatus === 'scheduled'
      ? '已授权 Codex 一次性处理这项补丁请求。'
    : observed
      ? `Codex：${selfActionCodexLabel(codexStatus)}`
      : '等待后端自行动作状态。'

  return (
    <section className={`self-action-panel ${tone}`} aria-label="自行动作状态">
      <div className="self-action-head">
        <span>
          <Terminal size={15} />
          <span>自行动作</span>
        </span>
        <strong>{headline}</strong>
      </div>

      <div className="self-action-summary">
        <Clipboard size={14} />
        <span>
          <small>目标 / 动作</small>
          <strong>{compact(`${selectedGoal} / ${selfActionKindLabel(actionKind)}`, 58)}</strong>
        </span>
      </div>

      <div className="self-action-grid">
        <SelfActionFact label="队列" value={pendingCount > 0 ? `${pendingCount} 待批准` : compact(queueId || '无待批准', 30)} />
        <SelfActionFact label="交接" value={Boolean(handoff.exists) ? compact(String(handoff.queueId || '已生成'), 30) : '未生成'} />
        <SelfActionFact label="补丁任务" value={taskId ? compact(taskId, 30) : '暂无'} />
        <SelfActionFact label="Codex" value={selfActionCodexLabel(codexStatus)} />
      </div>

      <p className="self-action-note">{codexLine}</p>
      {pendingQueueAvailable || preparedAuthorizationAvailable ? (
        <div className="self-action-actions">
          <button
            type="button"
            className="approve"
            disabled={busy}
            onClick={() =>
              props.onDecide(approvalTargetId, 'approved', {
                authorizeExisting: preparedAuthorizationAvailable
              })
            }
            title="批准并授权 Codex 执行这一项"
            aria-label="批准并执行自行动作"
          >
            <Check size={13} />
            <span>{props.busy === 'approved' ? '处理中' : preparedAuthorizationAvailable ? '授权执行' : '批准执行'}</span>
          </button>
          {pendingQueueAvailable ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => props.onDecide(pendingQueueId, 'denied')}
              title="拒绝这次自行动作"
              aria-label="拒绝自行动作"
            >
              <X size={13} />
              <span>{props.busy === 'denied' ? '处理中' : '拒绝'}</span>
            </button>
          ) : null}
        </div>
      ) : null}
      {updatedAt ? (
        <small className="self-action-updated">
          <Clock3 size={12} />
          {formatTime(updatedAt)}
        </small>
      ) : null}
    </section>
  )
}

function SelfActionFact(props: { label: string; value: string }): JSX.Element {
  return (
    <span className="self-action-fact" title={props.value}>
      <small>{props.label}</small>
      <strong>{props.value}</strong>
    </span>
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
      detail: '桌面主人 / 本机私有频道',
      accountLabel: '桌面主人',
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
  if (input.canCompose) return '桌面主人'
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
        title="Codex 模式"
        aria-label="Codex 模式"
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
        placeholder={props.disabled ? props.disabledReason || '当前窗口只读' : props.codexMode ? 'Codex 任务' : '今晚想让心玉接住什么？'}
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
  history: ProactiveIntent[]
  pending: Record<string, ProactiveAction>
  actionDigest?: unknown
  recentMemoryEvents: unknown[]
  lastEvent?: DesktopEvent
  apiConfig: ApiConfigStatus | null
  apiConfigAction: ApiConfigActionState
  externalPlugins: ExternalPluginsStatus | null
  externalPluginAction: ExternalPluginActionState
  qqEnvironment: QQEnvironmentStatus | null
  qqAction: QQActionState
  qqRuntimeConfig: QQRuntimeConfig | null
  qqRuntimeAction: QQRuntimeActionState
  stickerLibrary: StickerLibrary | null
  stickerAction: StickerActionState
  onAck: (candidateId: string, action: ProactiveAction) => void
  onOpenDetail: (candidateId: string) => void
  onRefreshApiConfig: () => void
  onSaveApiConfigProfile: (profile: ApiConfigProfilePatch) => void
  onTestApiConfigProfile: (profile: ApiConfigProfilePatch) => void
  onDeleteApiConfigProfile: (profileId: string) => void
  onApplyApiConfigProfile: (profileId: string) => void
  onRestartCoreBridge: () => void
  onRefreshExternalPlugins: () => void
  onSetExternalPluginConfig: (request: ExternalPluginConfigPatch) => void
  onInstallExternalPlugin: (request: ExternalPluginInstallRequest) => void
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
        <div className="intent-active-list">
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

        </div>

        {props.history.length ? (
          <div className="intent-history">
            <div className="intent-history-head">
              <History size={14} />
              <span>最近处理</span>
            </div>
            {props.history.slice(0, 4).map((intent) => (
              <HandledIntentRow key={intent.id} intent={intent} onOpenDetail={props.onOpenDetail} />
            ))}
          </div>
        ) : null}

        <section className="intent-review-rail" aria-label="主动提醒回看栏">
          <div className="intent-review-head">
            <span>
              <History size={14} />
              <span>回看栏</span>
            </span>
            <strong>{props.history.length}</strong>
          </div>
          <div className="intent-review-list">
            {!props.history.length ? <div className="empty-review">暂无已处理提醒</div> : null}
            {props.history.slice(0, 5).map((intent) => (
              <HandledIntentRow key={intent.id} intent={intent} onOpenDetail={props.onOpenDetail} />
            ))}
          </div>
        </section>
      </section>

    </aside>
  )
}

export function SystemControlPanel(props: {
  apiConfig: ApiConfigStatus | null
  apiConfigAction: ApiConfigActionState
  externalPlugins: ExternalPluginsStatus | null
  externalPluginAction: ExternalPluginActionState
  qqEnvironment: QQEnvironmentStatus | null
  qqAction: QQActionState
  qqRuntimeConfig: QQRuntimeConfig | null
  qqRuntimeAction: QQRuntimeActionState
  stickerLibrary: StickerLibrary | null
  stickerAction: StickerActionState
  actionDigest?: unknown
  recentMemoryEvents: unknown[]
  lastEvent?: DesktopEvent
  onRefreshApiConfig: () => void
  onSaveApiConfigProfile: (profile: ApiConfigProfilePatch) => void
  onTestApiConfigProfile: (profile: ApiConfigProfilePatch) => void
  onDeleteApiConfigProfile: (profileId: string) => void
  onApplyApiConfigProfile: (profileId: string) => void
  onRestartCoreBridge: () => void
  onRefreshExternalPlugins: () => void
  onSetExternalPluginConfig: (request: ExternalPluginConfigPatch) => void
  onInstallExternalPlugin: (request: ExternalPluginInstallRequest) => void
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
    <aside className="system-panel">
      <header className="system-head">
        <div>
          <p className="label">系统控制</p>
          <h2>API / 插件 / QQ / 表情</h2>
        </div>
      </header>

      <ApiConfigPanel
        status={props.apiConfig}
        action={props.apiConfigAction}
        onRefresh={props.onRefreshApiConfig}
        onSaveProfile={props.onSaveApiConfigProfile}
        onTestProfile={props.onTestApiConfigProfile}
        onDeleteProfile={props.onDeleteApiConfigProfile}
        onApplyProfile={props.onApplyApiConfigProfile}
        onRestartCore={props.onRestartCoreBridge}
      />

      <ExternalPluginControlPanel
        status={props.externalPlugins}
        action={props.externalPluginAction}
        onRefresh={props.onRefreshExternalPlugins}
        onSetConfig={props.onSetExternalPluginConfig}
        onInstall={props.onInstallExternalPlugin}
      />

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
        <button type="button" onClick={props.onRefresh} disabled={busy} title="刷新表情索引" aria-label="刷新表情索引">
          <RefreshCw size={14} className={busy ? 'spin' : ''} />
        </button>
        <button type="button" onClick={() => props.onRunMaintenance('import-pending')} disabled={busy} title="导入待分类表情" aria-label="导入待分类表情">
          <Play size={14} />
        </button>
        <button type="button" onClick={() => props.onRunMaintenance('rebuild-index')} disabled={busy} title="重建表情索引" aria-label="重建表情索引">
          <Clipboard size={14} />
        </button>
        <button type="button" onClick={props.onOpenAssetDir} disabled={busy} title="打开表情目录" aria-label="打开表情目录">
          <ExternalLink size={14} />
        </button>
      </div>

      <div className="sticker-metrics">
        <Metric label="总数" value={library?.total || 0} />
        <Metric label="文字识别" value={library?.ocr || 0} />
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

type ApiConfigDraft = {
  label: string
  provider: string
  model: string
  baseUrl: string
  apiKey: string
  allowInsecureHttp: boolean
  disableStreaming: boolean
}

function ApiConfigPanel(props: {
  status: ApiConfigStatus | null
  action: ApiConfigActionState
  onRefresh: () => void
  onSaveProfile: (profile: ApiConfigProfilePatch) => void
  onTestProfile: (profile: ApiConfigProfilePatch) => void
  onDeleteProfile: (profileId: string) => void
  onApplyProfile: (profileId: string) => void
  onRestartCore: () => void
}): JSX.Element {
  const profiles = props.status?.profiles || []
  const activeProfileId = props.status?.activeProfileId || ''
  const [selectedId, setSelectedId] = React.useState(() => activeProfileId || profiles[0]?.id || '__new__')
  const selected = profiles.find((profile) => profile.id === selectedId) || null
  const [draft, setDraft] = React.useState<ApiConfigDraft>(() => apiDraftFromStatus(props.status))
  const [draftDirty, setDraftDirty] = React.useState(false)
  const [draftSourceId, setDraftSourceId] = React.useState('__new__')
  const didInitSelection = React.useRef(Boolean(props.status))
  const busy = props.action.kind !== 'idle'
  const current = props.status?.current
  const sourceId = selected?.id || '__new__'

  React.useEffect(() => {
    if (!props.status) {
      return
    }
    if (!didInitSelection.current) {
      didInitSelection.current = true
      setSelectedId(activeProfileId || profiles[0]?.id || '__new__')
      return
    }
    if (selectedId === '__new__' || profiles.some((profile) => profile.id === selectedId)) {
      return
    }
    setSelectedId(activeProfileId || profiles[0]?.id || '__new__')
  }, [activeProfileId, profiles, props.status, selectedId])

  React.useEffect(() => {
    if (draftDirty && draftSourceId === sourceId) {
      return
    }
    setDraft(selected ? apiDraftFromProfile(selected) : apiBlankDraft())
    setDraftSourceId(sourceId)
    setDraftDirty(false)
  }, [draftDirty, draftSourceId, props.status, selected, sourceId])

  function updateDraft(patch: Partial<ApiConfigDraft>): void {
    setDraftDirty(true)
    setDraft((currentDraft) => ({ ...currentDraft, ...patch }))
  }

  function draftToPatch(): ApiConfigProfilePatch {
    return {
      id: selected?.id,
      label: draft.label,
      provider: draft.provider,
      model: draft.model,
      baseUrl: draft.baseUrl,
      apiKey: draft.apiKey.trim() || undefined,
      allowInsecureHttp: draft.allowInsecureHttp,
      disableStreaming: draft.disableStreaming
    }
  }

  function saveProfile(): void {
    setDraftDirty(false)
    props.onSaveProfile(draftToPatch())
  }

  function testProfile(): void {
    props.onTestProfile(draftToPatch())
  }

  function selectProfile(nextId: string): void {
    setSelectedId(nextId)
    const nextProfile = profiles.find((profile) => profile.id === nextId)
    setDraft(nextProfile ? apiDraftFromProfile(nextProfile) : apiBlankDraft())
    setDraftSourceId(nextProfile?.id || '__new__')
    setDraftDirty(false)
  }

  const currentText = current ? `${current.provider} / ${current.model}` : '未加载'
  const keyText = selected?.apiKeyPreview || current?.apiKeyPreview || '暂无密钥'

  return (
    <section className={`api-config-panel ${activeProfileId ? 'ready' : 'warn'}`}>
      <div className="section-head api-config-head">
        <span>
          <Terminal size={15} />
          <span>API 快捷配置</span>
        </span>
        <strong>{profiles.length}</strong>
      </div>

      <div className="api-current-line">
        <span>{compact(currentText, 42)}</span>
        <small>{current?.hasApiKey ? current.apiKeyPreview : '暂无密钥'}</small>
      </div>

      <div className="api-profile-select">
        <select value={selectedId} disabled={busy} onChange={(event) => selectProfile(event.currentTarget.value)}>
          <option value="__new__">新资料</option>
          {profiles.map((profile) => (
            <option value={profile.id} key={profile.id}>
              {profile.active ? '* ' : ''}
              {profile.label}
            </option>
          ))}
        </select>
        <button type="button" onClick={props.onRefresh} disabled={busy} title="刷新 API 资料" aria-label="刷新 API 资料">
          <RefreshCw size={14} className={props.action.kind === 'loading' ? 'spin' : ''} />
        </button>
      </div>

      <div className="api-config-grid">
        <label>
          <span>名称</span>
          <input value={draft.label} disabled={busy} onChange={(event) => updateDraft({ label: event.currentTarget.value })} />
        </label>
        <label>
          <span>提供方</span>
          <input value={draft.provider} disabled={busy} onChange={(event) => updateDraft({ provider: event.currentTarget.value })} />
        </label>
        <label>
          <span>模型</span>
          <input value={draft.model} disabled={busy} onChange={(event) => updateDraft({ model: event.currentTarget.value })} />
        </label>
        <label>
          <span>基础地址</span>
          <input value={draft.baseUrl} disabled={busy} onChange={(event) => updateDraft({ baseUrl: event.currentTarget.value })} />
        </label>
        <label className="api-key-field">
          <span>密钥</span>
          <input
            value={draft.apiKey}
            disabled={busy}
            type="password"
            placeholder={selected?.hasApiKey || current?.hasApiKey ? `${keyText} · 留空则保留` : '粘贴 API 密钥'}
            onChange={(event) => updateDraft({ apiKey: event.currentTarget.value })}
          />
          <small>{draft.apiKey.trim() ? '新密钥会覆盖已保存密钥' : selected?.hasApiKey ? '留空则保留已保存密钥' : '留空则在创建时使用当前环境密钥'}</small>
        </label>
      </div>

      <div className="api-runtime-flags">
        <RuntimeSwitch
          label="连接方式"
          checked={draft.allowInsecureHttp}
          detail={draft.allowInsecureHttp ? '明文连接' : '安全连接'}
          danger={draft.allowInsecureHttp}
          disabled={busy}
          onToggle={() => updateDraft({ allowInsecureHttp: !draft.allowInsecureHttp })}
        />
        <RuntimeSwitch
          label="流式"
          checked={!draft.disableStreaming}
          detail={draft.disableStreaming ? '关闭' : '开启'}
          disabled={busy}
          onToggle={() => updateDraft({ disableStreaming: !draft.disableStreaming })}
        />
      </div>

      <div className="api-config-actions">
        <button type="button" onClick={saveProfile} disabled={busy || !draft.label.trim()} title="保存 API 资料" aria-label="保存 API 资料">
          <Save size={14} />
          <span>保存</span>
        </button>
        <button
          type="button"
          onClick={testProfile}
          disabled={busy || !draft.baseUrl.trim() || !draft.model.trim()}
          title="测试 API 资料"
          aria-label="测试 API 资料"
        >
          <Radio size={14} className={props.action.kind === 'testing' ? 'spin' : ''} />
          <span>测试</span>
        </button>
        <button
          type="button"
          onClick={() => selected && props.onApplyProfile(selected.id)}
          disabled={busy || !selected}
          title="应用资料并重启核心"
          aria-label="应用资料并重启核心"
        >
          <Play size={14} />
          <span>应用</span>
        </button>
        <button
          type="button"
          onClick={() => selected && props.onDeleteProfile(selected.id)}
          disabled={busy || !selected}
          title="删除 API 资料"
          aria-label="删除 API 资料"
        >
          <Trash2 size={14} />
          <span>删除</span>
        </button>
        <button type="button" onClick={props.onRestartCore} disabled={busy} title="重启核心桥接" aria-label="重启核心桥接">
          <TimerReset size={14} className={props.action.kind === 'restarting' ? 'spin' : ''} />
          <span>重启</span>
        </button>
      </div>

      {props.action.message ? <small className="api-action-note">{props.action.message}</small> : null}
    </section>
  )
}

type ExternalPluginDraft = {
  baseUrl: string
  sessionId: string
  creatureId: string
  installPath: string
  installSourcePath: string
  downloadUrl: string
}

function ExternalPluginControlPanel(props: {
  status: ExternalPluginsStatus | null
  action: ExternalPluginActionState
  onRefresh: () => void
  onSetConfig: (request: ExternalPluginConfigPatch) => void
  onInstall: (request: ExternalPluginInstallRequest) => void
}): JSX.Element {
  const plugins = React.useMemo(() => {
    const order = new Map([
      ['codex', 0],
      ['kohaku_terrarium', 1],
      ['mcp_gateway', 2]
    ])
    return (props.status?.plugins || []).slice().sort((a, b) => (order.get(a.pluginId) ?? 99) - (order.get(b.pluginId) ?? 99))
  }, [props.status?.plugins])
  const installedCount = plugins.filter((plugin) => plugin.installed).length
  const enabledCount = plugins.filter((plugin) => plugin.enabled).length
  const busy = props.action.kind !== 'idle'

  return (
    <section className={`external-plugin-panel ${plugins.length && installedCount === plugins.length ? 'ready' : 'warn'}`}>
      <div className="section-head external-plugin-head">
        <span>
          <Puzzle size={15} />
          <span>插件总控制集</span>
        </span>
        <strong>{plugins.length}</strong>
      </div>

      <div className="external-plugin-summary">
        <span>
          启用 <strong>{enabledCount}</strong> / 安装 <strong>{installedCount}</strong>
        </span>
        <small>{props.status?.protocol || 'xinyu.external.v1'}</small>
      </div>

      <div className="external-plugin-list">
        {!plugins.length ? <p className="external-plugin-empty">暂无外部插件状态</p> : null}
        {plugins.map((plugin) => (
          <ExternalPluginRow
            key={plugin.pluginId}
            plugin={plugin}
            busy={busy}
            actionPluginId={props.action.pluginId}
            onRefresh={props.onRefresh}
            onSetConfig={props.onSetConfig}
            onInstall={props.onInstall}
          />
        ))}
      </div>

      {props.status?.notes?.length ? <small className="external-plugin-note">{compact(props.status.notes.map(externalPluginNoteLabel).join(' · '), 120)}</small> : null}
      {props.action.message ? <small className="external-plugin-note">{props.action.message}</small> : null}
    </section>
  )
}

function ExternalPluginRow(props: {
  plugin: ExternalPluginControl
  busy: boolean
  actionPluginId?: string
  onRefresh: () => void
  onSetConfig: (request: ExternalPluginConfigPatch) => void
  onInstall: (request: ExternalPluginInstallRequest) => void
}): JSX.Element {
  const [draft, setDraft] = React.useState<ExternalPluginDraft>(() => externalPluginDraftFromControl(props.plugin))
  const [dirty, setDirty] = React.useState(false)
  const installBusy = props.busy && props.actionPluginId === props.plugin.pluginId
  const canEditConfig = props.plugin.pluginId === 'kohaku_terrarium'

  React.useEffect(() => {
    if (dirty) {
      return
    }
    setDraft(externalPluginDraftFromControl(props.plugin))
  }, [dirty, props.plugin])

  function updateDraft(patch: Partial<ExternalPluginDraft>): void {
    setDirty(true)
    setDraft((current) => ({ ...current, ...patch }))
  }

  async function savePluginConfig(patch: Partial<Pick<ExternalPluginConfigPatch, 'enabled' | 'proactiveEnabled'>> = {}): Promise<void> {
    const configPatch = externalPluginConfigPatchFromDraft(props.plugin, draft)
    await Promise.resolve(
      props.onSetConfig({
        pluginId: props.plugin.pluginId,
        enabled: patch.enabled ?? props.plugin.enabled,
        proactiveEnabled: patch.proactiveEnabled ?? props.plugin.proactiveEnabled,
        config: configPatch
      })
    )
    setDirty(false)
  }

  async function saveCurrentDraft(): Promise<void> {
    await savePluginConfig()
  }

  async function toggleEnabled(): Promise<void> {
    await savePluginConfig({ enabled: !props.plugin.enabled })
  }

  async function toggleProactive(): Promise<void> {
    await savePluginConfig({ proactiveEnabled: !props.plugin.proactiveEnabled })
  }

  async function installPlugin(): Promise<void> {
    if (canEditConfig) {
      await saveCurrentDraft()
    }
    await Promise.resolve(
      props.onInstall({
        pluginId: props.plugin.pluginId,
        options: externalPluginInstallOptionsFromDraft(props.plugin, draft)
      })
    )
  }

  const pluginState = props.plugin.installed ? '已安装' : externalPluginInstallStateLabel(props.plugin.install.missingReason) || '未安装'
  const runtimeState = props.plugin.available ? '可调用' : props.plugin.enabled ? '等待安装' : '已关闭'
  const installLabel = props.plugin.installed ? '已安装' : '安装'
  const installReady = canEditConfig
    ? Boolean(draft.installSourcePath.trim() || draft.downloadUrl.trim() || props.plugin.installed)
    : Boolean(props.plugin.installable || props.plugin.installed)
  const installHint = canEditConfig
    ? draft.installSourcePath.trim() || draft.downloadUrl.trim()
      ? '可直接安装插件'
      : '请填写源路径或下载地址'
    : props.plugin.installed
      ? '已经安装'
      : externalPluginInstallStateLabel(props.plugin.install.missingReason) || '安装插件'

  return (
    <article className={`external-plugin-row ${props.plugin.available ? 'ready' : 'warn'}`}>
      <div className="external-plugin-row-head">
        <div className="external-plugin-title">
          <strong>{props.plugin.title}</strong>
          <small>{`${props.plugin.kind} / ${props.plugin.transport}`}</small>
        </div>
        <div className="external-plugin-badges">
          <span className={`external-plugin-pill ${props.plugin.enabled ? 'on' : 'off'}`}>{props.plugin.enabled ? '启用' : '关闭'}</span>
          <span className={`external-plugin-pill ${props.plugin.installed ? 'ok' : 'warn'}`}>{pluginState}</span>
        </div>
      </div>

      <div className="external-plugin-summary-line">
        <span>{runtimeState}</span>
        <small>{compact(props.plugin.install.path || props.plugin.install.installer || '未配置安装路径', 72)}</small>
      </div>

      <div className="external-plugin-switches">
        <RuntimeSwitch
          label="启用"
          checked={props.plugin.enabled}
          detail={props.plugin.installed ? '可运行' : '待安装'}
          disabled={props.busy}
          onToggle={() => {
            void toggleEnabled()
          }}
        />
        <RuntimeSwitch
          label="主动"
          checked={props.plugin.proactiveEnabled}
          detail={props.plugin.proactiveEnabled ? '可主动调用' : '手动触发'}
          disabled={props.busy}
          onToggle={() => {
            void toggleProactive()
          }}
        />
      </div>

      <div className="external-plugin-config">
        {canEditConfig ? (
          <>
            <label>
              <span>基础地址</span>
              <input value={draft.baseUrl} disabled={props.busy} onChange={(event) => updateDraft({ baseUrl: event.currentTarget.value })} />
            </label>
            <label>
              <span>会话</span>
              <input value={draft.sessionId} disabled={props.busy} onChange={(event) => updateDraft({ sessionId: event.currentTarget.value })} />
            </label>
            <label>
              <span>个体</span>
              <input value={draft.creatureId} disabled={props.busy} onChange={(event) => updateDraft({ creatureId: event.currentTarget.value })} />
            </label>
            <label>
              <span>安装路径</span>
              <input value={draft.installPath} disabled={props.busy} onChange={(event) => updateDraft({ installPath: event.currentTarget.value })} />
            </label>
            <label className="external-plugin-wide">
              <span>源路径</span>
              <input value={draft.installSourcePath} disabled={props.busy} onChange={(event) => updateDraft({ installSourcePath: event.currentTarget.value })} />
            </label>
            <label className="external-plugin-wide">
              <span>下载地址</span>
              <input value={draft.downloadUrl} disabled={props.busy} onChange={(event) => updateDraft({ downloadUrl: event.currentTarget.value })} />
            </label>
          </>
        ) : (
          <div className="external-plugin-readonly">
            <span>
              <strong>安装器</strong>
              <em>{compact(props.plugin.install.installer || '内置', 48)}</em>
            </span>
            <span>
              <strong>路径</strong>
              <em>{compact(props.plugin.install.path || '未安装', 48)}</em>
            </span>
          </div>
        )}
      </div>

      <div className="external-plugin-actions">
        {canEditConfig ? (
          <button type="button" onClick={() => void saveCurrentDraft()} disabled={props.busy || !dirty} title="保存插件配置" aria-label="保存插件配置">
            <Save size={14} />
            <span>保存</span>
          </button>
        ) : null}
        <button
          type="button"
          onClick={() => void installPlugin()}
          disabled={props.busy || !installReady}
          title={installHint}
          aria-label={installHint}
        >
          <Download size={14} className={installBusy && !props.plugin.installed ? 'spin' : ''} />
          <span>{installLabel}</span>
        </button>
        <button type="button" onClick={props.onRefresh} disabled={props.busy} title="刷新插件状态" aria-label="刷新插件状态">
          <RefreshCw size={14} className={props.busy ? 'spin' : ''} />
          <span>刷新</span>
        </button>
      </div>

      {props.plugin.notes.length ? <small className="external-plugin-note">{compact(props.plugin.notes.map(externalPluginNoteLabel).join(' · '), 96)}</small> : null}
    </article>
  )
}

function externalPluginDraftFromControl(plugin: ExternalPluginControl): ExternalPluginDraft {
  const config = plugin.config || {}
  return {
    baseUrl: String(config.base_url || config.baseUrl || ''),
    sessionId: String(config.session_id || config.sessionId || ''),
    creatureId: String(config.creature_id || config.creatureId || ''),
    installPath: String(config.install_path || config.installPath || plugin.install.path || ''),
    installSourcePath: String(config.install_source_path || config.installSourcePath || ''),
    downloadUrl: String(config.download_url || config.downloadUrl || '')
  }
}

function externalPluginConfigPatchFromDraft(plugin: ExternalPluginControl, draft: ExternalPluginDraft): JsonRecord {
  if (plugin.pluginId === 'kohaku_terrarium') {
    return {
      base_url: draft.baseUrl.trim(),
      session_id: draft.sessionId.trim(),
      creature_id: draft.creatureId.trim(),
      install_path: draft.installPath.trim(),
      install_source_path: draft.installSourcePath.trim(),
      download_url: draft.downloadUrl.trim()
    }
  }
  return {}
}

function externalPluginInstallOptionsFromDraft(plugin: ExternalPluginControl, draft: ExternalPluginDraft): JsonRecord {
  if (plugin.pluginId === 'kohaku_terrarium') {
    return {
      install_path: draft.installPath.trim(),
      source_path: draft.installSourcePath.trim(),
      download_url: draft.downloadUrl.trim()
    }
  }
  return {}
}

function apiDraftFromStatus(status: ApiConfigStatus | null): ApiConfigDraft {
  const current = status?.current
  return {
    label: current?.provider ? `${current.provider} ${current.model}`.trim() : '本地 API',
    provider: current?.provider || 'ciallo',
    model: current?.model || 'mimo-v2.5-pro',
    baseUrl: current?.baseUrl || '',
    apiKey: '',
    allowInsecureHttp: Boolean(current?.allowInsecureHttp),
    disableStreaming: current?.disableStreaming !== false
  }
}

function apiBlankDraft(): ApiConfigDraft {
  return {
    label: '',
    provider: 'openai',
    model: '',
    baseUrl: '',
    apiKey: '',
    allowInsecureHttp: false,
    disableStreaming: true
  }
}

function apiDraftFromProfile(profile: ApiConfigProfile): ApiConfigDraft {
  return {
    label: profile.label,
    provider: profile.provider,
    model: profile.model,
    baseUrl: profile.baseUrl,
    apiKey: '',
    allowInsecureHttp: profile.allowInsecureHttp,
    disableStreaming: profile.disableStreaming
  }
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
        <small>{tokenAvailable ? '网页端口令可复制' : '未找到网页端口令'}</small>
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
          title="复制网页端口令"
          aria-label="复制网页端口令"
        >
          <Clipboard size={15} />
        </button>
        <button
          type="button"
          onClick={props.onOpenWebUI}
          disabled={busy}
          title="打开 NapCat 网页端"
          aria-label="打开 NapCat 网页端"
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
          detail={config.groupShadowEnabled ? '观察' : '关闭'}
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
          <strong>观察</strong>
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

function HandledIntentRow(props: { intent: ProactiveIntent; onOpenDetail: (candidateId: string) => void }): JSX.Element {
  return (
    <article
      className={`intent-row intent-row-handled risk-${props.intent.risk}`}
      role="button"
      tabIndex={0}
      onClick={() => props.onOpenDetail(props.intent.id)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          props.onOpenDetail(props.intent.id)
        }
      }}
    >
      <div className="intent-meta">
        <span>{handledIntentLabel(props.intent)}</span>
        <strong>{props.intent.trigger}</strong>
      </div>
      <p>{props.intent.plannedText}</p>
      <div className="intent-foot">
        <span>{formatTime(props.intent.updatedAt || props.intent.createdAt)}</span>
        <span>{props.intent.delivery}</span>
      </div>
    </article>
  )
}

function handledIntentLabel(intent: ProactiveIntent): string {
  if (intent.desktopAction === 'read_locally') return '本地已读'
  if (intent.desktopAction === 'dismiss') return '已忽略'
  if (intent.desktopAction === 'reply') return '已回复'
  if (intent.desktopAction === 'approve_qq') return '已排队 QQ'
  if (intent.status === 'answered' || intent.status === 'replied') return '已回复'
  if (intent.status === 'dismissed') return '已忽略'
  if (intent.status === 'read_locally') return '本地已读'
  if (intent.status === 'queued_qq') return '已排队 QQ'
  return intent.status || '已处理'
}

function intentStatusLabel(value: string): string {
  if (!value || value === 'pending') return '待处理'
  if (value === 'sent') return '已发送'
  if (value === 'answered' || value === 'replied') return '已回复'
  if (value === 'failed') return '已失败'
  if (value === 'expired') return '已过期'
  if (value === 'blocked') return '已阻止'
  if (value === 'read_locally') return '本地已读'
  if (value === 'dismissed') return '已忽略'
  if (value === 'queued_qq') return '已排队 QQ'
  if (value === 'none') return '未处理'
  return compact(value, 40)
}

function intentRequestedActionLabel(value: string): string {
  if (!value || value === 'owner_ack' || value === 'claim_ack') return '确认后发送'
  if (value === 'read_locally') return '只在本地读过'
  if (value === 'approve_qq') return '同意发送到 QQ'
  if (value === 'state_only') return '仅状态'
  if (value === 'preview_only') return '仅预览'
  if (value === 'none' || value === 'local') return '本地'
  return compact(value, 40)
}

function isHandledIntent(intent: ProactiveIntent): boolean {
  return (
    Boolean(intent.desktopAction) ||
    ['sent', 'answered', 'failed', 'expired', 'blocked', 'none', 'read_locally', 'replied', 'dismissed', 'queued_qq'].includes(
      intent.status
    )
  )
}

export function IntentDetailDialog(props: {
  intent: ProactiveIntent
  pendingAction?: ProactiveAction
  onClose: () => void
  onAck: (candidateId: string, action: ProactiveAction) => void
  onReply: (intent: ProactiveIntent, text: string) => void
}): JSX.Element {
  const handled = isHandledIntent(props.intent)
  const disabled = Boolean(props.pendingAction) || handled
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
          <button type="button" onClick={props.onClose} title="关闭">
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
              <dd>{intentStatusLabel(props.intent.status)}</dd>
            </div>
            <div>
              <dt>动作</dt>
              <dd>{intentRequestedActionLabel(props.intent.requestedAction)}</dd>
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
  const route = asRecord(latestMemory.route)
  const selectedExperts = memoryRouteList(latestMemory.selectedExperts || route.selectedExperts)
  const currentTurnFacts = memoryRouteList(latestMemory.currentTurnFacts || route.currentTurnFacts)
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
      <div className="continuity-row">
        <small>记忆专家</small>
        <strong>{selectedExperts.length ? selectedExperts.slice(0, 4).join(' + ') : '等待路由'}</strong>
      </div>
      <div className="continuity-row">
        <small>当前事实</small>
        <strong>{currentTurnFacts.length ? currentTurnFacts.slice(0, 3).join(' / ') : '当前消息优先'}</strong>
      </div>
    </section>
  )
}

function memoryRouteList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value.map((item) => String(item || '').trim()).filter(Boolean)
}
