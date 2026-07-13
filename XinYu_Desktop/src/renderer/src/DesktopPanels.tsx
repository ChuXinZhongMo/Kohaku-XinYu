import React from 'react'
import { Activity, Bell, Brain, Check, ChevronDown, ChevronLeft, ChevronRight, Clock3, Compass, Clipboard, Download, Eye, ExternalLink, Heart, History, MessageCircle, Play, Puzzle, Radio, RefreshCw, Save, Send, ShieldAlert, Sparkles, Terminal, TimerReset, Plus, Trash2, Volume2, Wifi, X } from 'lucide-react'
import { createPortal } from 'react-dom'
import { EnvironmentValve } from './EnvironmentValve'
import { VoiceFlagsPanel } from './VoiceFlagsPanel'
import { SurfacePart } from './AffectiveSurfaceProvider'
import type { ApiConfigActionState, ApiConfigProfile, ApiConfigProfilePatch, ApiConfigStatus, AsyncExplorationState, CommandState, DesktopEvent, ExternalPluginActionState, ExternalPluginConfigPatch, ExternalPluginControl, ExternalPluginInstallRequest, ExternalPluginsStatus, GatewayStatus, GrowthCandidatePromotionStatus, ImpulseSoupState, JsonRecord, KernelGovernanceStatus, MetabolismTicket, MetabolismTicketActionState, ProactiveAction, ProactiveIntent, PrivateBrowserGrantPatch, PrivateEcosystemSnapshot, QQActionState, QQEnvironmentStatus, QQRuntimeActionState, QQRuntimeConfig, QQRuntimeConfigPatch, SelfActionSnapshot, Snapshot, Stage8MemoryGovernanceStatus, Stage12GateStatus, Stage13GateStatus, StickerActionState, StickerLibrary, StickerRecord, ThemeName, XinYuState } from './desktopTypes'
import { actionLabel, asRecord, buildStats, commandStatusLabel, compact, defaultQQRuntimeConfig, defaultQQServices, digestPressureLabel, digestResidueLabel, digestResultLabel, digestThemeLabel, eventLabel, externalPluginInstallStateLabel, externalPluginNoteLabel, formatLatency, formatTime, formatTurnMeta, isCommandRenderedByTurn, memorySummary, platformLabel, proactiveTextLabel, qqDetailLabel, qqDiagnosisLabel, qqServiceLabel, riskLabel, runtimeLabel, sourceLabel, statusLabel, stickerClipLabel, stickerCorrectionMoods, stickerMoodLabel, themeOptions } from './desktopModel'

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

function memoryCandidateLabel(value: string, fallback = '未标记'): string {
  if (!value) return fallback
  const labels: Record<string, string> = {
    applied_growth_log: '已写入成长日志',
    approved: '已批准',
    danger: '风险',
    'danger:medium': '中等风险',
    hidden_owner_review_required: '正文已隐藏，等待主人审查',
    'memory/people/owner.md': '主人长期记忆',
    'memory/reflection/growth_log.md': '成长日志',
    memory_immune: '记忆免疫',
    'memory_immune:observe_more': '需要继续观察',
    observe_for_repetition: '观察是否重复出现',
    owner_memory_review: '主人记忆审查',
    owner_preference: '主人偏好候选',
    owner_private: '主人私密范围',
    owner_review_required: '等待主人审查',
    post_reply_growth_candidate: '回复后的成长候选',
    'action:observe_for_repetition': '动作：观察是否重复出现',
    'scope:owner_private': '范围：主人私密'
  }
  return labels[value] || value
}

function memoryCandidateLabels(values: string[]): string {
  return values.length ? values.map((value) => memoryCandidateLabel(value)).join(' / ') : '无风险标记'
}

function kernelDomainLabel(value: string | undefined, fallback = '未知'): string {
  const text = String(value || '').trim()
  if (!text) return fallback
  const labels: Record<string, string> = {
    world_model: '世界模型',
    reorganization: '重组提案',
    belief: '信念',
    followup: '行动后续候选',
    self_model: '自我模型',
    all: '全部域',
    candidate: '候选',
    review_only: '仅审核',
    stable: '稳定',
    balanced: '平衡',
    consider_lower_slow_escalation_threshold: '建议降低慢信号阈值',
    fast_reorg_often_ineffective_review_gates: '快重组常无效',
    insufficient_data: '数据不足'
  }
  return labels[text] || text
}

function stage8Label(value: string | undefined, fallback = '暂无'): string {
  const text = String(value || '').trim()
  if (!text) return fallback
  const labels: Record<string, string> = {
    active_guarded: '受控治理中',
    blocked: '阻塞',
    blocked_owner_review_required: '需要主人审核',
    blocked_review_only: '只允许审核',
    blocked_review_only_not_auto_apply: '禁止自动写入',
    candidate_backlog_needs_consolidation_before_stable_write: '稳定写入前要先合并重复候选',
    candidate_type_not_supported_for_stable_apply: '候选类型不能直接写稳定记忆',
    collect_same_trial_explicit_success_before_profile_or_habit_promotion: '需要同类试验成功信号',
    consolidate_duplicate_candidate_clusters_before_stable_write: '先合并重复候选簇',
    consciousness_claim: '意识声明',
    corroborated_candidate_review: '证据重复，等待整理',
    duplicate_candidate_clusters: '重复候选簇',
    dry_run_only: '只生成预览',
    dry_run_or_owner_apply_confirmed_growth_log_only: '只允许干跑或主人确认的成长日志',
    false: '否',
    growth_apply_mode: '成长日志应用模式',
    hidden: '隐藏',
    learning_trial_success_gate: '学习试验门槛',
    memory_candidate: '记忆候选',
    owner_review_preview_only: '主人审核预览',
    repeated_evidence_ready_for_owner_review: '重复证据，适合进入审查',
    stable_memory_not_modified: '稳定记忆未改动',
    stable_memory_write: '稳定记忆写入',
    target_memory_layer_not_growth_log: '目标层不是成长日志',
    true: '是'
  }
  if (labels[text]) return labels[text]
  if (text.startsWith('duplicate_candidate_clusters:')) {
    return `重复候选簇 ${text.split(':')[1]} 组`
  }
  return compact(text, 48)
}

function stage8StatusCountsLabel(value: JsonRecord): string {
  const entries = Object.entries(value)
    .map(([key, count]) => `${stage8Label(key)} ${String(count)}`)
    .filter(Boolean)
  return entries.length ? entries.join(' / ') : '无状态'
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
  privateShareBusy?: boolean
  privateEcosystemBusy?: boolean
  privateEcosystemResult?: string
  onPausePrivateShare?: (paused: boolean) => void
  onSetPrivateShareEnabled?: (enabled: boolean) => void
  onSetPrivateEcosystemEnabled?: (enabled: boolean) => void
  onTickPrivateEcosystem?: () => void
  browserGrantBusy?: boolean
  browserGrantResult?: string
  onSetPrivateBrowserGrant?: (patch: PrivateBrowserGrantPatch) => void
  browserObserveBusy?: boolean
  browserObserveResult?: string
  onObservePrivateBrowser?: (url: string) => void
  privateDesktop?: Record<string, unknown>
  privateDesktopBusy?: boolean
  onStartPrivateDesktop?: () => void
  onStopPrivateDesktop?: () => void
  onObservePrivateDesktop?: () => void
  onRefreshPrivateDesktop?: () => void
  onSetPrivateDesktopEnabled?: (enabled: boolean) => void
  privateDesktopResult?: string
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
      <PrivateEcosystemPanel
        privateEcosystem={props.snapshot?.privateEcosystem}
        busy={props.privateEcosystemBusy || props.privateShareBusy}
        result={props.privateEcosystemResult}
        onPauseShare={props.onPausePrivateShare}
        onSetShareEnabled={props.onSetPrivateShareEnabled}
        onSetEnabled={props.onSetPrivateEcosystemEnabled}
        onTick={props.onTickPrivateEcosystem}
        browserGrantBusy={props.browserGrantBusy}
        browserGrantResult={props.browserGrantResult}
        onSetBrowserGrant={props.onSetPrivateBrowserGrant}
        observeBusy={props.browserObserveBusy}
        observeResult={props.browserObserveResult}
        onObserveUrl={props.onObservePrivateBrowser}
      />
      <PrivateDesktopPanel
        privateDesktop={props.privateDesktop}
        busy={props.privateDesktopBusy}
        onStart={props.onStartPrivateDesktop}
        onStop={props.onStopPrivateDesktop}
        onObserve={props.onObservePrivateDesktop}
        onRefresh={props.onRefreshPrivateDesktop}
        onSetEnabled={props.onSetPrivateDesktopEnabled}
        result={props.privateDesktopResult}
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
        <SelfActionFact label="交接" value={handoff.exists ? compact(String(handoff.queueId || '已生成'), 30) : '未生成'} />
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

function privateEcosystemRolloutLabel(value: string): string {
  if (!value || value === 'disabled') return '关闭'
  if (value === 'dry_run') return '干跑'
  if (value === 'observe_only') return '低风险观察'
  if (value === 'owner_private_share_enabled') return '可准备主人私聊'
  if (value === 'browser_read_only') return '可只读浏览'
  if (value === 'single_step_approved_actions') return '单步批准动作'
  return compact(value, 24)
}

function privateEcosystemGoalLabel(value: string): string {
  if (!value || value === 'none' || value === '暂无') return '暂无目标'
  if (value === 'observe_private_space') return '观察自己的私有空间'
  if (value === 'tend_private_journal') return '整理私有日志'
  if (value === 'reflect_recent_feedback') return '消化最近主人反馈'
  if (value === 'review_memory_pressure') return '检查记忆候选压力'
  if (value === 'explore_browser_readonly') return '只读观察主人允许的页面'
  return compact(value, 34)
}

function privateEcosystemActionLabel(value: string): string {
  if (!value || value === 'none' || value === '无') return '暂无动作'
  if (value === 'local_probe') return '本地低风险探测'
  if (value === 'browser_observe') return '只读浏览观察'
  if (value === 'owner_private_share') return '准备主人私聊候选'
  if (value === 'memory_candidate') return '生成记忆候选'
  return proactiveTextLabel(value)
}

function privateEcosystemStatusLabel(value: string): string {
  if (!value || value === 'none' || value === '无') return '暂无'
  if (value === 'completed') return '已完成'
  if (value === 'queued') return '已排队'
  if (value === 'blocked') return '已拦截'
  if (value === 'failed') return '失败'
  if (value === 'read_only_allowed') return '只读已允许'
  if (value === 'browser_grant_disabled') return '浏览授权未启用'
  if (value === 'plugin_disabled') return '插件未启用'
  if (value.startsWith('sensitive_page_blocked')) return '敏感页面已拦截'
  return compact(value, 24)
}

function privateBrowserEngineLabel(value: string): string {
  if (!value || value === 'unavailable' || value === 'none') return '未装'
  if (value === 'simulated') return '模拟'
  if (value === 'playwright') return 'Playwright'
  return compact(value, 20)
}

function parseAllowedUrls(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(/[\n,，]+/)
        .map((url) => url.trim())
        .filter(Boolean)
    )
  ).slice(0, 20)
}

function PrivateEcosystemPanel(props: {
  privateEcosystem?: PrivateEcosystemSnapshot
  busy?: boolean
  result?: string
  onPauseShare?: (paused: boolean) => void
  onSetShareEnabled?: (enabled: boolean) => void
  onSetEnabled?: (enabled: boolean) => void
  onTick?: () => void
  browserGrantBusy?: boolean
  browserGrantResult?: string
  onSetBrowserGrant?: (patch: PrivateBrowserGrantPatch) => void
  observeBusy?: boolean
  observeResult?: string
  onObserveUrl?: (url: string) => void
}): JSX.Element {
  const [observeUrl, setObserveUrl] = React.useState('')
  const [allowedUrlDraft, setAllowedUrlDraft] = React.useState('')
  const [allowedUrlDirty, setAllowedUrlDirty] = React.useState(false)
  const pe = props.privateEcosystem
  const observed = Boolean(pe?.observed)
  const counters = pe?.counters ?? {}
  const share = pe?.ownerPrivateShare ?? {}
  const journal = pe?.journal ?? {}
  const browser = pe?.browser ?? {}
  const computer = pe?.computer ?? {}
  const kill = pe?.killSwitch ?? {}
  const boundaries = pe?.boundaries ?? {}
  const grantedAllowedUrls = Array.isArray(browser.allowedUrls) ? browser.allowedUrls : []
  const grantedAllowedUrlText = grantedAllowedUrls.join('\n')

  React.useEffect(() => {
    if (!allowedUrlDirty && grantedAllowedUrlText) {
      setAllowedUrlDraft(grantedAllowedUrlText)
    }
  }, [allowedUrlDirty, grantedAllowedUrlText])

  const ecosystemEnabled = Boolean(pe?.enabled)
  const rolloutState = String(pe?.rolloutState || 'disabled')
  const activeGoalId = String(pe?.activeGoalId || 'none')
  const latestActionKind = String(pe?.latestActionKind || 'none')
  const latestActionStatus = String(pe?.latestActionStatus || 'none')
  const tickCount = Number(counters.ticks ?? 0)
  const goalLabel = privateEcosystemGoalLabel(activeGoalId)
  const visibleGoalLabel = ecosystemEnabled ? goalLabel : '等待启动'
  const latestActionLabel = privateEcosystemActionLabel(latestActionKind)
  const actionStatusLabel = privateEcosystemStatusLabel(latestActionStatus)
  const sharePaused = Boolean(kill.sharePaused ?? share.paused)
  const shareEnabled = Boolean(kill.shareEnabled ?? share.enabled)
  const heldCount = Number(counters.sharesHeld ?? 0)
  const blockedCount = Number(counters.blockedHighRisk ?? 0)
  const stableWrites = Number(journal.stableMemoryWriteCount ?? 0)
  const browserEnabled = Boolean(browser.enabled)
  const browserReadOnly = browser.readOnly !== false
  const allowedUrls = parseAllowedUrls(allowedUrlDraft)
  const browserGrantReady = allowedUrls.length > 0

  const shareLabel = !shareEnabled ? '未授权' : sharePaused ? '已暂停' : '已授权'
  const killLabel = sharePaused ? '已停止' : shareEnabled ? '可主动私聊' : '默认关闭'
  const browserLabel = `${browserEnabled ? '已授权' : '未授权'} · ${browserReadOnly ? '只读' : '非只读'}`
  const tone = !ecosystemEnabled ? 'idle' : stableWrites > 0 ? 'blocked' : sharePaused ? 'warn' : 'active'
  const headline = !ecosystemEnabled
    ? '目标未启用'
    : observed
      ? compact(visibleGoalLabel, 22)
      : '等待第一次 tick'
  const loopStatus = !ecosystemEnabled ? '目标循环未启用' : observed ? '目标循环已启用' : '已启用，未跑过'
  const loopReason = !ecosystemEnabled
    ? '现在不会自动围绕目标行动；只能由主人手动观察或手动触发。'
    : observed
      ? `最近：${latestActionLabel} / ${actionStatusLabel}；后台维护会继续低频推进。`
      : '已经授权低风险私有生态，点“推进一次”会立刻生成当前目标。'

  return (
    <section className={`self-action-panel ${tone}`} aria-label="私有生态状态">
      <div className="self-action-head">
        <span>
          <Radio size={15} />
          <span>私有生态</span>
        </span>
        <strong>{headline}</strong>
      </div>

      <div className="self-action-summary">
        <Compass size={14} />
        <span>
          <small>目标循环</small>
          <strong>{compact(`${loopStatus} / ${visibleGoalLabel}`, 58)}</strong>
        </span>
      </div>

      <div className="private-desktop-action-status" aria-label="私有生态目标状态">
        <span>
          <Activity size={13} />
          <strong>{ecosystemEnabled ? `当前目标：${visibleGoalLabel}` : '现在没有启用目标循环'}</strong>
        </span>
        <small>{loopReason}</small>
      </div>

      <div className="self-action-grid">
        <SelfActionFact label="目标循环" value={loopStatus} />
        <SelfActionFact label="阶段" value={privateEcosystemRolloutLabel(rolloutState)} />
        <SelfActionFact label="tick" value={String(tickCount)} />
        <SelfActionFact label="低风险已执行" value={String(counters.lowRiskExecuted ?? 0)} />
        <SelfActionFact label="最近动作" value={`${latestActionLabel}·${actionStatusLabel}`} />
        <SelfActionFact label="记忆候选" value={String(counters.memoryCandidates ?? 0)} />
        <SelfActionFact label="已拦截高风险" value={String(blockedCount)} />
        <SelfActionFact label="稳定记忆写入" value={stableWrites > 0 ? `异常:${stableWrites}` : '0（受阻）'} />
        <SelfActionFact label="主动私聊" value={shareLabel} />
        <SelfActionFact
          label="私聊配额"
          value={`${share.dailyRemaining ?? 0}/${share.dailyLimit ?? 0}`}
        />
        <SelfActionFact label="冷却剩余" value={`${share.cooldownRemainingMinutes ?? 0} 分`} />
        <SelfActionFact label="已发/已暂存" value={`${counters.sharesSent ?? 0} / ${heldCount}`} />
        <SelfActionFact label="浏览器" value={`${privateBrowserEngineLabel(String(browser.engine || ''))} · 拦截${browser.actionsBlocked ?? 0}`} />
        <SelfActionFact label="浏览授权" value={browserLabel} />
        <SelfActionFact label="电脑控制" value={`${computer.backend || '未装'} · 观察${computer.observedCount ?? 0}`} />
      </div>

      <p className="self-action-note">
        <ShieldAlert size={13} /> 终止开关：{killLabel}。 稳定记忆 {boundaries.stableMemoryWrite || 'blocked'}，
        QQ 直发 {boundaries.qqMessageEnqueuedDirectly ? '是（异常）' : '否'}，
        浏览器使用主人配置 {browser.usesOwnerProfile ? '是（异常）' : '否'}，
        多步任意控制 {computer.multiStepArbitraryControl || 'disabled'}。
      </p>

      {props.onSetEnabled || props.onTick ? (
        <div className="self-action-actions">
          {props.onSetEnabled ? (
            ecosystemEnabled ? (
              <button
                type="button"
                disabled={Boolean(props.busy)}
                onClick={() => props.onSetEnabled?.(false)}
                title="关闭私有生态目标循环；不会影响手动隔离桌面观察授权"
              >
                <ShieldAlert size={13} />
                <span>{props.busy ? '处理中' : '关闭目标循环'}</span>
              </button>
            ) : (
              <button
                type="button"
                className="approve"
                disabled={Boolean(props.busy)}
                onClick={() => props.onSetEnabled?.(true)}
                title="启用低风险私有生态目标循环；稳定记忆、QQ直发、桌面点击仍受阻"
              >
                <Play size={13} />
                <span>{props.busy ? '处理中' : '启动目标循环'}</span>
              </button>
            )
          ) : null}
          {props.onTick ? (
            <button
              type="button"
              className="approve"
              disabled={Boolean(props.busy) || !ecosystemEnabled}
              onClick={() => props.onTick?.()}
              title={ecosystemEnabled ? '立刻推进一次低风险目标循环' : '先启动目标循环'}
            >
              <RefreshCw size={13} />
              <span>{props.busy ? '处理中' : '推进一次'}</span>
            </button>
          ) : null}
        </div>
      ) : null}

      {props.onPauseShare && shareEnabled ? (
        <div className="self-action-actions">
          {sharePaused ? (
            <button
              type="button"
              className="approve"
              disabled={Boolean(props.busy)}
              onClick={() => props.onPauseShare?.(false)}
              title="恢复心玉的主动私聊"
            >
              <Radio size={13} />
              <span>{props.busy ? '处理中' : '恢复主动私聊'}</span>
            </button>
          ) : (
            <button
              type="button"
              disabled={Boolean(props.busy)}
              onClick={() => props.onPauseShare?.(true)}
              title="立即停止心玉的主动私聊（终止开关）"
            >
              <ShieldAlert size={13} />
              <span>{props.busy ? '处理中' : '暂停主动私聊'}</span>
            </button>
          )}
        </div>
      ) : null}

      {props.onSetShareEnabled ? (
        <div className="self-action-actions">
          {shareEnabled ? (
            <button
              type="button"
              disabled={Boolean(props.busy)}
              onClick={() => props.onSetShareEnabled?.(false)}
              title="撤销主动私聊授权；不会删除已有候选，也不会发送消息"
            >
              <ShieldAlert size={13} />
              <span>{props.busy ? '处理中' : '关闭主动私聊授权'}</span>
            </button>
          ) : (
            <button
              type="button"
              className="approve"
              disabled={Boolean(props.busy)}
              onClick={() => props.onSetShareEnabled?.(true)}
              title="只写主人授权：允许心玉准备主人私聊候选，不直接发送新入口"
            >
              <Radio size={13} />
              <span>{props.busy ? '处理中' : '启用主动私聊授权'}</span>
            </button>
          )}
        </div>
      ) : null}

      {props.onSetBrowserGrant ? (
        <div className="self-action-actions" style={{ gridTemplateColumns: '1fr', gap: 6 }}>
          <p className="self-action-note" style={{ margin: 0 }}>
            <ShieldAlert size={13} /> 只读浏览需要启用 xinyu_private_browser 插件，并在这里授权 allowed_urls；登录、支付、凭证页仍会被拦截。
          </p>
          <textarea
            value={allowedUrlDraft}
            spellCheck={false}
            rows={3}
            placeholder="每行一个允许只读观察的网址，例如 https://example.com/news"
            onChange={(event) => {
              setAllowedUrlDirty(true)
              setAllowedUrlDraft(event.currentTarget.value)
            }}
            style={{
              width: '100%',
              boxSizing: 'border-box',
              resize: 'vertical',
              borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.18)',
              padding: '6px 8px',
              background: 'rgba(0,0,0,0.16)',
              color: 'inherit',
              fontSize: 12,
              lineHeight: 1.35
            }}
          />
          <div className="self-action-actions">
            <button
              type="button"
              className="approve"
              disabled={Boolean(props.browserGrantBusy) || !browserGrantReady}
              onClick={() => props.onSetBrowserGrant?.({ enabled: true, readOnly: true, allowedUrls })}
              title={browserGrantReady ? '保存只读浏览授权和 allowed_urls' : '先填写至少一个 allowed_url'}
            >
              <Check size={13} />
              <span>{props.browserGrantBusy ? '保存中' : '保存只读授权'}</span>
            </button>
            <button
              type="button"
              disabled={Boolean(props.browserGrantBusy)}
              onClick={() => props.onSetBrowserGrant?.({ enabled: false, readOnly: true, allowedUrls })}
              title="撤销 private_browser.enabled；allowed_urls 会保留在授权文件中"
            >
              <ShieldAlert size={13} />
              <span>{props.browserGrantBusy ? '保存中' : '撤销浏览授权'}</span>
            </button>
          </div>
          {props.browserGrantResult ? <small className="self-action-updated">{props.browserGrantResult}</small> : null}
        </div>
      ) : null}

      {props.onObserveUrl ? (
        <div className="self-action-actions" style={{ display: 'flex', flexDirection: 'column', alignItems: 'stretch', gap: 6 }}>
          <input
            type="text"
            value={observeUrl}
            spellCheck={false}
            placeholder="https://… 让心玉只读观察"
            onChange={(event) => setObserveUrl(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && observeUrl.trim()) {
                props.onObserveUrl?.(observeUrl.trim())
              }
            }}
            style={{
              width: '100%',
              boxSizing: 'border-box',
              padding: '4px 8px',
              borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.18)',
              background: 'rgba(0,0,0,0.18)',
              color: 'inherit',
              fontSize: 12
            }}
          />
          <button
            type="button"
            disabled={Boolean(props.observeBusy) || !observeUrl.trim()}
            onClick={() => props.onObserveUrl?.(observeUrl.trim())}
            title="只读观察这个网页（需插件启用且已保存浏览授权；凭证/支付页会被拦截）"
          >
            <Send size={13} />
            <span>{props.observeBusy ? '观察中' : '只读观察'}</span>
          </button>
          {props.observeResult ? <small className="self-action-updated">{props.observeResult}</small> : null}
        </div>
      ) : null}

      {props.result ? <small className="self-action-updated">{props.result}</small> : null}

      {pe?.updatedAt ? (
        <small className="self-action-updated">
          <Clock3 size={12} />
          {formatTime(pe.updatedAt)}
        </small>
      ) : null}
    </section>
  )
}

function desktopActionResultLabel(value: string): string {
  if (!value || value === 'none') return '暂无'
  if (value === 'completed') return '已完成'
  if (value === 'simulated') return '模拟完成'
  if (value === 'prepared') return '已准备'
  if (value === 'proposed') return '已提出'
  if (value === 'blocked') return '已拦截'
  if (value === 'failed') return '失败'
  return compact(value, 28)
}

function desktopActionKindLabel(value: string): string {
  if (!value || value === 'none') return '暂无'
  return proactiveTextLabel(value)
}

function PrivateDesktopPanel(props: {
  privateDesktop?: Record<string, unknown>
  busy?: boolean
  onStart?: () => void
  onStop?: () => void
  onObserve?: () => void
  onRefresh?: () => void
  onSetEnabled?: (enabled: boolean) => void
  result?: string
}): JSX.Element {
  const [zoomed, setZoomed] = React.useState(false)
  const dialogRef = React.useRef<HTMLDivElement | null>(null)
  const dialogTitleId = React.useId()
  const pd = props.privateDesktop ?? {}
  const grant = (pd.grant as Record<string, unknown>) ?? {}
  const boundaries = (pd.boundaries as Record<string, unknown>) ?? {}
  const backend = String(pd.backend || 'unavailable')
  const sessionState = String(pd.session_state || 'stopped')
  const live = sessionState === 'live'
  const liveUrl = String(pd.live_view_url || '')
  const displaySize = String(pd.display_size || '—')
  const frameAge = pd.frame_age_seconds
  const enabled = Boolean(grant.enabled)
  const observeOnly = Boolean(grant.observe_only)
  const singleStep = Boolean(grant.single_step_actions)
  const lastAction = String(pd.last_action_kind || 'none')
  const lastResult = String(pd.last_result || 'none')
  const actionsExecuted = Number(pd.actions_executed ?? 0)
  const actionsBlocked = Number(pd.actions_blocked ?? 0)

  const backendLabel =
    backend === 'docker_xfce_vnc' ? '隔离桌面(docker)' : backend === 'simulated' ? '模拟(未起容器)' : '不可用'
  const sessionLabel =
    sessionState === 'live' ? '运行中' : sessionState === 'starting' ? '启动中' : sessionState === 'error' ? '错误' : '已停止'
  const gateLabel = !enabled ? '未授权' : observeOnly ? '仅观察' : grant.single_step_actions ? '单步(已授权)' : '单步(需逐次批准)'
  const tone = !enabled ? 'idle' : live ? 'active' : 'warn'
  const actionStatus = !enabled
    ? '没动：隔离桌面未授权'
    : !live
      ? '没动：隔离桌面未启动'
      : observeOnly
        ? '可见动作：只读观察'
        : singleStep
          ? '可执行：单步动作已授权'
          : '等授权：单步动作需逐次批准'
  const actionReason = !enabled
    ? '先授权后才能观察隔离桌面。'
    : !live
      ? '启动后才能看到实时画面和执行只读观察。'
      : observeOnly
        ? '当前安全边界只允许截图、状态、窗口列表等只读动作，不会点鼠标或输入。'
        : singleStep
          ? '允许单步动作，但仍禁止 shell、下载、安装和外网。'
          : '只读观察可用；点击、输入等动作还需要主人逐次批准。'

  // View-only live monitor over loopback noVNC. Owner-only, bridge-token gated.
  // liveUrl already carries autoconnect + the one-time session password, so we
  // only append the view-only/scaling flags with the correct separator.
  const embedUrl = live && liveUrl
    ? `${liveUrl}${liveUrl.includes('?') ? '&' : '?'}view_only=true&resize=scale`
    : ''
  const stoppedMessage = '隔离桌面已停止 · 由主人启动后显示实时画面'
  const unavailableMessage = !enabled
    ? '未授权隔离桌面（默认关闭）'
    : live
      ? '运行中，但暂无实时画面地址'
      : stoppedMessage
  const previewMessage = zoomed && embedUrl ? '弹窗观察中' : unavailableMessage
  const modalMessage = !enabled ? '未授权隔离桌面（默认关闭）— 先点「授权（仅观察）」再启动' : unavailableMessage

  React.useEffect(() => {
    if (!zoomed) {
      return
    }
    const previousOverflow = document.body.style.overflow
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        setZoomed(false)
      }
    }
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', handleKeyDown)
    window.requestAnimationFrame(() => dialogRef.current?.focus())
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [zoomed])

  return (
    <section className={`self-action-panel ${tone}`} aria-label="隔离桌面状态">
      <div className="self-action-head">
        <span>
          <Eye size={15} />
          <span>隔离桌面</span>
        </span>
        <strong>{backendLabel}</strong>
      </div>

      <div className="private-desktop-stage">
        {embedUrl && !zoomed ? (
          <iframe
            title="心玉隔离桌面实时画面"
            src={embedUrl}
            sandbox="allow-scripts allow-same-origin"
            className="private-desktop-frame"
          />
        ) : (
          <div className="private-desktop-empty">
            {previewMessage}
          </div>
        )}
        <button
          type="button"
          className="private-desktop-zoom-btn"
          disabled={!embedUrl}
          onClick={() => embedUrl && setZoomed(true)}
          title={embedUrl ? '弹窗观察（实时画面居中放大）' : '没有实时画面地址，先授权并启动隔离桌面'}
          aria-label={embedUrl ? '弹窗观察隔离桌面' : '隔离桌面暂无实时画面'}
        >
          <ExternalLink size={12} />
          <span>{embedUrl ? '弹窗观察' : '暂无画面'}</span>
        </button>
      </div>

      <div className="private-desktop-action-status" aria-label="隔离桌面行动状态">
        <span>
          <Activity size={13} />
          <strong>{actionStatus}</strong>
        </span>
        <small>
          最近：{desktopActionKindLabel(lastAction)} / {desktopActionResultLabel(lastResult)}；{actionReason}
        </small>
      </div>

      <div className="self-action-grid">
        <SelfActionFact label="后端" value={backendLabel} />
        <SelfActionFact label="会话" value={sessionLabel} />
        <SelfActionFact label="分辨率" value={displaySize} />
        <SelfActionFact label="画面延迟" value={frameAge == null ? '—' : `${frameAge}s`} />
        <SelfActionFact label="授权" value={gateLabel} />
        <SelfActionFact
          label="最近动作"
          value={`${desktopActionKindLabel(lastAction)}·${desktopActionResultLabel(lastResult)}`}
        />
        <SelfActionFact label="已执行/拦截" value={`${actionsExecuted} / ${actionsBlocked}`} />
        <SelfActionFact label="帧数" value={String(pd.frame_count ?? 0)} />
      </div>

      <p className="self-action-note">
        <ShieldAlert size={13} /> 主人桌面捕获 {boundaries.host_screen_captured ? '是（异常）' : 'false'}，
        操作系统鼠标控制 {boundaries.owner_mouse_moved ? '是（异常）' : 'false'}，
        computer_control {boundaries.computer_control_enabled ? 'on（异常）' : 'off'}，
        端口仅 127.0.0.1。shell/下载/安装/网络在本期禁用。
      </p>

      <div className="self-action-actions">
        {props.onSetEnabled ? (
          enabled ? (
            <button
              type="button"
              disabled={Boolean(props.busy) || live}
              onClick={() => props.onSetEnabled?.(false)}
              title={live ? '请先停止隔离桌面再撤销授权' : '撤销隔离桌面授权（仅观察）'}
            >
              <ShieldAlert size={13} />
              <span>撤销授权</span>
            </button>
          ) : (
            <button
              type="button"
              className="approve"
              disabled={Boolean(props.busy)}
              onClick={() => props.onSetEnabled?.(true)}
              title="授权心玉的隔离桌面（仅观察；单步/ shell / 网络仍关闭）"
            >
              <Eye size={13} />
              <span>{props.busy ? '处理中' : '授权（仅观察）'}</span>
            </button>
          )
        ) : null}
        {live ? (
          <button
            type="button"
            disabled={Boolean(props.busy)}
            onClick={() => props.onStop?.()}
            title="停止并移除心玉的隔离桌面容器"
          >
            <X size={13} />
            <span>{props.busy ? '处理中' : '停止隔离桌面'}</span>
          </button>
        ) : (
          <button
            type="button"
            className="approve"
            disabled={Boolean(props.busy) || !enabled}
            onClick={() => props.onStart?.()}
            title={enabled ? '启动心玉的隔离桌面（需已构建镜像）' : '请先在授权里启用 private_desktop'}
          >
            <Play size={13} />
            <span>{props.busy ? '处理中' : '启动隔离桌面'}</span>
          </button>
        )}
        {props.onObserve ? (
          <button
            type="button"
            className="approve"
            disabled={Boolean(props.busy) || !enabled || !live}
            onClick={() => props.onObserve?.()}
            title={enabled && live ? '执行一次只读观察并刷新画面' : '需要先授权并启动隔离桌面'}
            aria-label="观察一次隔离桌面"
          >
            <Eye size={13} />
            <span>{props.busy ? '观察中' : '观察一次'}</span>
          </button>
        ) : null}
        {props.onRefresh ? (
          <button type="button" disabled={Boolean(props.busy)} onClick={() => props.onRefresh?.()} title="刷新隔离桌面状态">
            <RefreshCw size={13} />
            <span>刷新</span>
          </button>
        ) : null}
      </div>

      {props.result ? <small className="self-action-updated">{props.result}</small> : null}

      {pd.updated_at ? (
        <small className="self-action-updated">
          <Clock3 size={12} />
          {formatTime(String(pd.updated_at))}
        </small>
      ) : null}

      {zoomed
        ? createPortal(
            <div className="private-desktop-modal-backdrop" onMouseDown={() => setZoomed(false)} role="presentation">
              <div
                ref={dialogRef}
                className="private-desktop-dialog"
                role="dialog"
                aria-modal="true"
                aria-labelledby={dialogTitleId}
                tabIndex={-1}
                onMouseDown={(event) => event.stopPropagation()}
              >
                <header className="private-desktop-dialog-head">
                  <span>
                    <Eye size={15} />
                    <strong id={dialogTitleId}>隔离桌面</strong>
                    <small>{sessionLabel} · {displaySize}</small>
                  </span>
                  <button type="button" onClick={() => setZoomed(false)} title="关闭弹窗观察" aria-label="关闭弹窗观察">
                    <X size={16} />
                  </button>
                </header>
                <div className="private-desktop-dialog-frame">
                  {embedUrl ? (
                    <iframe
                      title="心玉隔离桌面实时画面（弹窗）"
                      src={embedUrl}
                      sandbox="allow-scripts allow-same-origin"
                      className="private-desktop-frame"
                    />
                  ) : (
                    <div className="private-desktop-empty">
                      {modalMessage}
                    </div>
                  )}
                </div>
              </div>
            </div>,
            document.body
          )
        : null}
    </section>
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
  if (turn.isOwner) return '你'
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
          <MessageBubble side={turn.isOwner ? 'owner' : 'contact'} speaker={turnSpeakerLabel(turn)} text={String(turn.textPreview || '...')} meta={formatTurnMeta(turn)} />
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
  feedback: Record<string, string>
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
  onSaveApiConfigProfile: (profile: ApiConfigProfilePatch) => Promise<string | null>
  onTestApiConfigProfile: (profile: ApiConfigProfilePatch) => void
  onDeleteApiConfigProfile: (profileId: string) => void
  onApplyApiConfigProfile: (profileId: string) => Promise<void>
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
          <p className="label">队列</p>
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
            <span>新的主动预览、只读提醒和需确认动作会出现在这里。</span>
          </div>
        ) : null}

          {props.intents.map((intent) => (
          <IntentRow
            key={intent.id}
            intent={intent}
            pendingAction={props.pending[intent.id]}
            feedback={props.feedback[intent.id]}
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
  metabolismTickets: MetabolismTicket[]
  metabolismAction: MetabolismTicketActionState
  memoryGrowthCandidates: GrowthCandidatePromotionStatus | null
  stage8MemoryGovernance: Stage8MemoryGovernanceStatus | null
  kernelGovernance: KernelGovernanceStatus | null
  actionDigest?: unknown
  recentMemoryEvents: unknown[]
  lastEvent?: DesktopEvent
  onRefreshApiConfig: () => void
  onSaveApiConfigProfile: (profile: ApiConfigProfilePatch) => Promise<string | null>
  onTestApiConfigProfile: (profile: ApiConfigProfilePatch) => void
  onDeleteApiConfigProfile: (profileId: string) => void
  onApplyApiConfigProfile: (profileId: string) => Promise<void>
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
  onRefreshMetabolismTickets: () => void
  onYieldCompute: (ticketId: string, seconds: number) => void
  onMaintainBoundary: (ticketId: string) => void
  onReviewMemoryCandidate?: (candidateId: string, decision: 'approve' | 'reject') => void
  reviewMemoryCandidateBusy?: string
  onReviewKernelItem?: (domain: string, itemId: string, decision: 'approve' | 'reject') => void
  reviewKernelItemBusy?: string
  onGrantKernelScope?: (scope: string) => void
  grantKernelScopeBusy?: string
}): JSX.Element {
  return (
    <aside className="system-panel">
      <header className="system-head">
        <div>
          <p className="label">系统控制</p>
          <h2>API / 插件 / QQ / 记忆</h2>
        </div>
      </header>

      <VoiceFlagsPanel />

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

      <MetabolismTicketsPanel
        tickets={props.metabolismTickets}
        action={props.metabolismAction}
        onRefresh={props.onRefreshMetabolismTickets}
        onYieldCompute={props.onYieldCompute}
        onMaintainBoundary={props.onMaintainBoundary}
      />

      <Stage8MemoryGovernancePanel status={props.stage8MemoryGovernance} />

      <KernelGovernancePanel
        status={props.kernelGovernance}
        onReviewItem={props.onReviewKernelItem}
        reviewBusy={props.reviewKernelItemBusy}
        onGrantScope={props.onGrantKernelScope}
        grantScopeBusy={props.grantKernelScopeBusy}
      />

      <MemoryGrowthCandidatePanel
        status={props.memoryGrowthCandidates}
        onReviewCandidate={props.onReviewMemoryCandidate}
        reviewBusy={props.reviewMemoryCandidateBusy}
      />

      <ActionDigestPanel digest={props.actionDigest} />

      <ContinuityPanel recentMemoryEvents={props.recentMemoryEvents} lastEvent={props.lastEvent} />
    </aside>
  )
}

function metabolismTicketId(ticket: MetabolismTicket): string {
  return String(ticket.ticket_id || ticket.ticketId || ticket.id || '').trim()
}

function metabolismTicketStatusLabel(value: string): string {
  const text = String(value || '').trim()
  const labels: Record<string, string> = {
    approved: '已批准',
    cancelled: '已取消',
    completed: '已完成',
    expired: '已过期',
    failed: '失败',
    rejected: '已守边界',
    requested: '请求中',
    running: '让渡中',
    yielded: '已让出计算'
  }
  return labels[text] || compact(text || '未知', 24)
}

function metabolismTicketKindLabel(ticket: MetabolismTicket): string {
  const value = String(ticket.kind || ticket.request_kind || ticket.action_kind || ticket.desire_shape || '').trim()
  const labels: Record<string, string> = {
    async_exploration: '异步探索',
    creative_writing: '创作写作',
    deep_research: '深度研究',
    desire_drive: '欲望驱动',
    memory_consolidation: '记忆整理',
    metabolism_window: '计算让渡窗口',
    private_ecosystem_tick: '私有生态推进',
    self_repair: '自修复',
    yield_compute: '让出计算'
  }
  return labels[value] || compact(value || '代谢票据', 28)
}

function metabolismTicketSeconds(ticket: MetabolismTicket): number {
  const seconds = Number(ticket.requested_seconds || ticket.approved_seconds || ticket.duration_seconds || ticket.seconds || 600)
  if (!Number.isFinite(seconds) || seconds <= 0) return 600
  return Math.max(60, Math.min(7200, Math.round(seconds)))
}

function metabolismSecondsLabel(seconds: number): string {
  if (seconds >= 3600) return `${Math.round(seconds / 3600)} 小时`
  return `${Math.max(1, Math.round(seconds / 60))} 分`
}

function metabolismTicketReason(ticket: MetabolismTicket): string {
  return compact(
    String(ticket.reason || ticket.note || ticket.summary || ticket.description || ticket.request_reason || '核心请求一个可控计算窗口。'),
    86
  )
}

function metabolismTicketTime(ticket: MetabolismTicket): string {
  const time = String(ticket.expires_at || ticket.updated_at || ticket.created_at || '')
  return time ? formatTime(time) : '暂无时间'
}

function metabolismSecondOptions(defaultSeconds: number): number[] {
  return Array.from(new Set([defaultSeconds, 300, 600, 1200, 1800, 3600])).sort((a, b) => a - b)
}

function MetabolismTicketsPanel(props: {
  tickets: MetabolismTicket[]
  action: MetabolismTicketActionState
  onRefresh: () => void
  onYieldCompute: (ticketId: string, seconds: number) => void
  onMaintainBoundary: (ticketId: string) => void
}): JSX.Element {
  const [secondsByTicket, setSecondsByTicket] = React.useState<Record<string, number>>({})
  const busy = props.action.kind !== 'idle'
  const activeCount = props.tickets.filter((ticket) => !['completed', 'cancelled', 'expired', 'rejected', 'yielded'].includes(String(ticket.status || ''))).length
  const tone = props.action.message.startsWith('失败') ? 'blocked' : activeCount ? 'warn' : 'idle'
  const headline = busy ? '处理中' : activeCount ? `${activeCount} 张待决策` : '暂无请求'

  return (
    <section className={`self-action-panel ${tone}`} aria-label="计算代谢票据">
      <div className="self-action-head">
        <span>
          <TimerReset size={15} />
          <span>计算代谢</span>
        </span>
        <strong>{headline}</strong>
      </div>

      <div className="self-action-summary">
        <Activity size={14} />
        <span>
          <small>票据队列</small>
          <strong>{props.tickets.length ? `后端已返回 ${props.tickets.length} 张票据` : '等待核心请求计算窗口'}</strong>
        </span>
      </div>

      <div className="self-action-actions">
        <button type="button" onClick={props.onRefresh} disabled={busy} title="刷新代谢票据">
          <RefreshCw size={13} className={props.action.kind === 'loading' ? 'spin' : ''} />
          <span>{props.action.kind === 'loading' ? '刷新中' : '刷新票据'}</span>
        </button>
      </div>

      {!props.tickets.length ? (
        <p className="self-action-note">暂无需要主人决策的计算让渡票据；这里会显示请求原因、时长和边界动作。</p>
      ) : null}

      <div style={{ display: 'grid', gap: 7 }}>
        {props.tickets.slice(0, 6).map((ticket, index) => {
          const ticketId = metabolismTicketId(ticket)
          const defaultSeconds = metabolismTicketSeconds(ticket)
          const selectedSeconds = secondsByTicket[ticketId] || defaultSeconds
          const rowBusy = Boolean(ticketId && props.action.ticketId === ticketId && props.action.kind !== 'idle')
          const status = String(ticket.status || 'requested')
          const closed = ['completed', 'cancelled', 'expired', 'rejected', 'yielded'].includes(status)
          const disabled = busy || !ticketId || closed
          const options = metabolismSecondOptions(defaultSeconds)
          return (
            <article className="evidence-row runtime-row" key={ticketId || `metabolism-ticket-${index}`}>
              <TimerReset size={13} />
              <span title={ticketId}>{compact(metabolismTicketKindLabel(ticket), 36)}</span>
              <strong>{rowBusy ? '提交中' : metabolismTicketStatusLabel(status)}</strong>
              <small>{metabolismTicketReason(ticket)}</small>
              <small>
                请求 {metabolismSecondsLabel(defaultSeconds)} · {metabolismTicketTime(ticket)}
              </small>
              <div
                className="self-action-actions"
                style={{ gridColumn: '2 / -1', gridTemplateColumns: 'minmax(0, 0.9fr) repeat(2, minmax(0, 1fr))' }}
              >
                <select
                  value={selectedSeconds}
                  disabled={busy || closed}
                  aria-label="让渡计算时长"
                  onChange={(event) =>
                    setSecondsByTicket((current) => ({ ...current, [ticketId]: Number(event.currentTarget.value) }))
                  }
                  style={{
                    minWidth: 0,
                    borderRadius: 8,
                    border: '1px solid rgba(255,255,255,0.18)',
                    padding: '0 6px',
                    background: 'rgba(0,0,0,0.12)',
                    color: 'inherit',
                    fontSize: 12,
                    fontWeight: 800
                  }}
                >
                  {options.map((seconds) => (
                    <option value={seconds} key={seconds}>
                      {metabolismSecondsLabel(seconds)}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="approve"
                  disabled={disabled}
                  onClick={() => props.onYieldCompute(ticketId, selectedSeconds)}
                  title={closed ? '这张票据已经结束' : '批准这个计算让渡窗口'}
                >
                  <Play size={13} />
                  <span>让出计算</span>
                </button>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => props.onMaintainBoundary(ticketId)}
                  title={closed ? '这张票据已经结束' : '拒绝这张票据并守住边界'}
                >
                  <ShieldAlert size={13} />
                  <span>守住边界</span>
                </button>
              </div>
            </article>
          )
        })}
      </div>

      {props.action.message ? <small className="self-action-updated">{props.action.message}</small> : null}
    </section>
  )
}

const KERNEL_GRANT_SCOPES = ['world_model', 'reorganization', 'belief', 'self_model'] as const

function KernelGovernancePanel(props: {
  status: KernelGovernanceStatus | null
  onReviewItem?: (domain: string, itemId: string, decision: 'approve' | 'reject') => void
  reviewBusy?: string
  onGrantScope?: (scope: string) => void
  grantScopeBusy?: string
}): JSX.Element {
  const { status, onReviewItem, reviewBusy, onGrantScope, grantScopeBusy } = props
  const items = status?.items || []
  const reviewable = items.filter((item) => item.reviewStatus === 'candidate' || item.reviewStatus === 'review_only')
  const headline = status?.ok === false
    ? '读取失败'
    : !status?.available
      ? '内核不可用'
      : reviewable.length > 0
        ? `${reviewable.length} 条待审核`
        : '无待审核'
  const tone = !status || status.ok === false
    ? 'blocked'
    : reviewable.length > 0
      ? 'warn'
      : status.writesBlocked
        ? 'prepared'
        : 'active'

  return (
    <section className={`stage8-governance-panel self-action-panel ${tone}`} aria-label="认知内核审核">
      <div className="self-action-head">
        <span>
          <Brain size={15} />
          <span>认知内核 · 主人审核</span>
        </span>
        <strong>{headline}</strong>
      </div>

      <p className="self-action-note">
        审核世界模型、重组提案、信念变更与行动后续候选。批准后写入运行时 Self 或标记后续候选；拒绝则丢弃待审项。这不等同于 Stage8 稳定记忆写入。
      </p>

      <div className="self-action-grid">
        <SelfActionFact label="待审" value={String(status?.pendingCount ?? 0)} />
        <SelfActionFact label="世界模型" value={String(status?.worldModelCount ?? 0)} />
        <SelfActionFact label="重组" value={String(status?.reorganizationCount ?? 0)} />
        <SelfActionFact label="信念" value={String(status?.beliefCount ?? 0)} />
        <SelfActionFact label="后续候选" value={String(status?.followupCount ?? 0)} />
        <SelfActionFact label="慢信号" value={`${status?.slowSignalCount ?? 0}/${status?.slowEscalationThreshold ?? 3}`} />
        <SelfActionFact label="重组建议" value={kernelDomainLabel(status?.reorgRecommendation, '暂无')} />
      </div>

      {status?.selfStorySummary ? (
        <p className="self-action-note">自我叙事摘要：{compact(status.selfStorySummary, 160)}</p>
      ) : null}

      {status?.error ? <p className="self-action-note">{compact(status.error, 120)}</p> : null}

      <div className="kernel-grant-strip">
        <small>域授权：将 review_only 降级为 candidate，仍需逐条批准。</small>
        {KERNEL_GRANT_SCOPES.map((scope) => {
          const granted = status?.grantedScopes?.includes(scope)
          return (
            <span key={`kernel-grant-${scope}`} className="kernel-grant-chip">
              {granted ? (
                <strong>
                  <Check size={11} />
                  {kernelDomainLabel(scope)}
                </strong>
              ) : onGrantScope ? (
                <button
                  type="button"
                  className="memory-review-approve"
                  disabled={grantScopeBusy === scope}
                  onClick={() => onGrantScope(scope)}
                  title={`授权 ${kernelDomainLabel(scope)} 域进入候选审核`}
                >
                  <ShieldAlert size={11} />
                  {grantScopeBusy === scope ? '授权中' : `授权${kernelDomainLabel(scope)}`}
                </button>
              ) : (
                <small>{kernelDomainLabel(scope)}</small>
              )}
            </span>
          )
        })}
      </div>

      {reviewable.slice(0, 4).map((item) => {
        const busyKey = `${item.domain}:${item.itemId}`
        return (
          <div className="evidence-row runtime-row memory-review-row" key={`kernel-review-${busyKey}`}>
            <ShieldAlert size={13} />
            <span>{compact(item.itemId, 24)}</span>
            <strong>{kernelDomainLabel(item.domain)}</strong>
            <small>{compact(item.contentPreview, 72)}</small>
            <small>{kernelDomainLabel(item.reviewStatus)}</small>
            {typeof item.confidence === 'number' ? <small>置信 {Math.round(item.confidence * 100)}%</small> : null}
            {onReviewItem ? (
              <small className="memory-review-actions">
                <button
                  type="button"
                  disabled={reviewBusy === busyKey}
                  className="memory-review-approve"
                  onClick={() => onReviewItem(item.domain, item.itemId, 'approve')}
                  title="批准这条内核变更"
                >
                  <Check size={11} />
                  {reviewBusy === busyKey ? '处理中' : '批准'}
                </button>
                <button
                  type="button"
                  disabled={reviewBusy === busyKey}
                  className="memory-review-reject"
                  onClick={() => onReviewItem(item.domain, item.itemId, 'reject')}
                  title="拒绝这条内核变更"
                >
                  <X size={11} />
                  拒绝
                </button>
              </small>
            ) : null}
          </div>
        )
      })}
    </section>
  )
}

function Stage8MemoryGovernancePanel(props: { status: Stage8MemoryGovernanceStatus | null }): JSX.Element {
  const status = props.status
  const latestDecision = status?.latestDecision
  const latestDryRun = status?.latestDryRun
  const blockers = latestDryRun?.blockers || []
  const blockedGates = status?.blockedGates || []
  const duplicateClusters = status?.duplicateClusters || []
  const rawHidden = !status?.boundaries.rawOwnerTextInPacket && !status?.boundaries.visibleReplyTextInPacket && !status?.boundaries.candidateBodyInPacket
  const tone = !status || status.ok === false
    ? 'blocked'
    : status.readyForStage9
      ? 'active'
      : status.ownerReviewRequiredCount > 0
        ? 'warn'
        : status.duplicateClusterCount > 0 || status.learningTrialSuccessGate === 'blocked'
          ? 'blocked'
          : 'prepared'
  const headline = !status
    ? '读取中'
    : status.ok === false
      ? '读取失败'
      : status.readyForStage9
        ? '可进阶段 9'
        : status.ownerReviewRequiredCount > 0
          ? `${status.ownerReviewRequiredCount} 待审核`
          : status.duplicateClusterCount > 0
            ? `${status.duplicateClusterCount} 组待合并`
            : '继续观察'
  const latestDecisionLine = latestDecision
    ? `已记录你的批准：${compact(latestDecision.itemId, 34)}；${latestDryRun?.stableMemoryWrite === 'dry_run_only' ? '只生成干跑预览，没有写稳定记忆。' : '仍需通过写入边界。'}`
    : '最近没有可显示的记忆候选批准记录。'
  const dryRunTarget = latestDryRun
    ? `${memoryCandidateLabel(latestDryRun.candidateType || latestDecision?.actionKind || 'memory_candidate')} / ${memoryCandidateLabel(
        latestDryRun.targetMemoryLayer || 'memory/reflection/growth_log.md'
      )}`
    : '暂无'

  return (
    <section className={`stage8-governance-panel self-action-panel ${tone}`} aria-label="第八阶段记忆治理">
      <div className="self-action-head">
        <span>
          <ShieldAlert size={15} />
          <span>记忆治理 · 阶段 8</span>
        </span>
        <strong>{headline}</strong>
      </div>

      <p className="self-action-note">{latestDecisionLine}</p>

      <div className="self-action-grid">
        <SelfActionFact label="状态" value={stage8Label(status?.status)} />
        <SelfActionFact label="阶段 9" value={status?.readyForStage9 ? '已放行' : '未放行'} />
        <SelfActionFact label="主人审核" value={String(status?.ownerReviewRequiredCount ?? 0)} />
        <SelfActionFact label="重复候选" value={String(status?.duplicateClusterCount ?? 0)} />
        <SelfActionFact label="学习门槛" value={stage8Label(status?.learningTrialSuccessGate)} />
        <SelfActionFact label="稳定写入" value={stage8Label(status?.boundaries.stableMemoryWrite || status?.stableProfileWrite)} />
      </div>

      <div className="stage8-decision-strip">
        <SelfActionFact label="最近批准" value={latestDecision ? stage8Label(latestDecision.decision) : '暂无'} />
        <SelfActionFact label="候选目标" value={dryRunTarget} />
        <SelfActionFact label="干跑写入" value={stage8Label(latestDryRun?.stableMemoryWrite)} />
        <SelfActionFact label="原文边界" value={rawHidden ? '隐藏' : '需要检查'} />
      </div>

      {blockers.length ? (
        <div className="stage8-blockers">
          {blockers.slice(0, 3).map((blocker) => (
            <span key={blocker}>
              <ShieldAlert size={12} />
              {stage8Label(blocker)}
            </span>
          ))}
        </div>
      ) : null}

      <p className="self-action-note">
        下一步：{stage8Label(status?.nextStep, '等待状态刷新')}
        {status && status.reviewInboxPendingCount > status.ownerReviewRequiredCount
          ? `；另有 ${status.reviewInboxPendingCount} 条普通审核项，不是当前稳定记忆写入闸门。`
          : ''}
      </p>

      {blockedGates.slice(0, 2).map((gate) => (
        <div className="evidence-row runtime-row stage8-gate-row" key={`${gate.gate}-${gate.status}`}>
          <ShieldAlert size={13} />
          <span>{stage8Label(gate.gate)}</span>
          <strong>{stage8Label(gate.status)}</strong>
          <small>{stage8Label(gate.reason)}</small>
        </div>
      ))}

      {duplicateClusters.slice(0, 4).map((cluster) => (
        <div className="evidence-row runtime-row stage8-cluster-row" key={cluster.topic}>
          <Clipboard size={13} />
          <span>{compact(cluster.topic, 24)}</span>
          <strong>{cluster.size} 条</strong>
          <small>{stage8Label(cluster.recommendation)}</small>
          <small>{stage8StatusCountsLabel(asRecord(cluster.statuses))}</small>
        </div>
      ))}
    </section>
  )
}

function MemoryGrowthCandidatePanel(props: {
  status: GrowthCandidatePromotionStatus | null
  onReviewCandidate?: (candidateId: string, decision: 'approve' | 'reject') => void
  reviewBusy?: string
}): JSX.Element {
  const { status, onReviewCandidate, reviewBusy } = props
  const pending = status?.pendingApply || []
  const applied = status?.applied || []
  const ownerReview = status?.ownerReviewRequired || []
  const headline = status?.ok === false
    ? '读取失败'
    : ownerReview.length > 0
      ? `${ownerReview.length} 条待主人审核`
      : pending.length > 0
        ? `${status?.pendingApplyCount ?? pending.length} 条待应用`
        : '无待应用'
  const copyCommand = (command: string): void => {
    if (!command) return
    void navigator.clipboard?.writeText(command).catch(() => undefined)
  }
  return (
    <section className="memory-growth-panel" aria-label="记忆审查">
      <div className="self-action-head">
        <span>
          <Brain size={15} />
          <span>记忆审查</span>
        </span>
        <strong>{headline}</strong>
      </div>
      <p className="self-action-note">
        这里只显示可审查摘要：成长日志候选需要主人确认后才能写入；主人记忆候选只显示编号和风险标签，正文默认隐藏。
      </p>
      <div className="self-action-grid">
        <SelfActionFact label="待应用" value={String(status?.pendingApplyCount ?? pending.length)} />
        <SelfActionFact label="已应用" value={String(status?.appliedCount ?? applied.length)} />
        <SelfActionFact label="待审查" value={String(status?.ownerReviewRequiredCount ?? ownerReview.length)} />
        <SelfActionFact label="目标" value={compact(memoryCandidateLabel(status?.targetMemoryLayer || 'memory/reflection/growth_log.md'), 38)} />
        <SelfActionFact label="写入" value={status?.ownerReviewRequiredCount ? stage8Label('blocked_owner_review_required') : status?.pendingApplyCount ? '待确认' : '已清洁'} />
      </div>
      {status?.error ? <p className="self-action-note">{compact(status.error, 120)}</p> : null}
      {ownerReview.slice(0, 3).map((item) => (
        <div className="evidence-row runtime-row memory-review-row" key={`owner-review-${item.candidateId}`}>
          <ShieldAlert size={13} />
          <span>{compact(item.candidateId, 28)}</span>
          <strong>待审核</strong>
          <small>{compact(memoryCandidateLabel(item.candidateType || item.targetGate || 'owner_review_required'), 40)}</small>
          <small>{compact(memoryCandidateLabel(item.targetMemoryLayer || 'memory/reflection/growth_log.md'), 32)}</small>
          {item.riskFlags.length ? <small>{compact(memoryCandidateLabels(item.riskFlags), 72)}</small> : null}
          <small>正文已隐藏</small>
          {onReviewCandidate ? (
            <small className="memory-review-actions">
              <button
                type="button"
                disabled={reviewBusy === item.candidateId}
                className="memory-review-approve"
                onClick={() => onReviewCandidate(item.candidateId, 'approve')}
                title="批准这条候选进入成长日志预览（仍需 apply 才能写入稳定记忆）"
              >
                <Check size={11} />
                {reviewBusy === item.candidateId ? '处理中' : '批准'}
              </button>
              <button
                type="button"
                disabled={reviewBusy === item.candidateId}
                className="memory-review-reject"
                onClick={() => onReviewCandidate(item.candidateId, 'reject')}
                title="拒绝这条候选"
              >
                <X size={11} />
                拒绝
              </button>
            </small>
          ) : null}
        </div>
      ))}
      {pending.slice(0, 4).map((item) => (
        <div className="evidence-row runtime-row" key={item.candidateId}>
          <Clipboard size={13} />
          <span>{compact(item.candidateId, 34)}</span>
          <strong>{compact(memoryCandidateLabel(item.status || 'approved'), 24)}</strong>
          <small>{compact(memoryCandidateLabel(item.reasonPreview || item.candidateTextPreview || item.targetMemoryLayer), 96)}</small>
          {item.beforeHash ? <small>校验：{compact(item.beforeHash, 24)}</small> : null}
          {item.applyCommand ? (
            <small className="memory-apply-command-row">
              <code>{compact(item.applyCommand, 80)}</code>
              <button type="button" onClick={() => copyCommand(item.applyCommand)} title="复制应用命令">
                <Clipboard size={11} />
                <span>复制</span>
              </button>
            </small>
          ) : null}
        </div>
      ))}
      {!pending.length && applied[0] ? (
        <p className="self-action-note">最近已应用：{compact(applied[0].candidateId, 64)}</p>
      ) : null}
    </section>
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
  llm: {
    provider: string
    model: string
    baseUrl: string
    apiKey: string
    allowInsecureHttp: boolean
    disableStreaming: boolean
  }
  vision: {
    enabled: boolean
    model: string
    baseUrl: string
    apiKey: string
    timeoutSeconds: number
    maxBytes: number
  }
  hearing: {
    enabled: boolean
    command: string
    model: string
    baseUrl: string
    apiKey: string
    language: string
    timeoutSeconds: number
    recordFormat: string
  }
  tts: {
    enabled: boolean
    engine: string
    model: string
    baseUrl: string
    apiKey: string
    voice: string
    format: string
    requestMode: string
    timeoutSeconds: number
    genieBaseUrl: string
    genieCharacter: string
    genieSplitSentence: boolean
    genieSampleRate: number
    genieChannels: number
    genieSampleWidth: number
  }
  other: {
    openAIApiKey: string
  }
}

type ApiSectionId = 'llm' | 'vision' | 'hearing' | 'tts' | 'other'
const API_NEW_PROFILE_ID = '__new__'
const API_PROVIDER_OPTIONS = [
  { value: 'ciallo', label: 'Ciallo / MiMo 兼容' },
  { value: 'mimo', label: 'MiMo 兼容' },
  { value: 'openai', label: 'OpenAI 兼容' },
  { value: 'openrouter', label: 'OpenRouter 兼容' },
  { value: 'gemini', label: 'Gemini 兼容' },
  { value: 'deepseek', label: 'DeepSeek 兼容' },
  { value: 'qwen', label: '通义千问兼容' },
  { value: 'siliconflow', label: '硅基流动兼容' },
  { value: 'moonshot', label: 'Moonshot 兼容' },
  { value: 'minimax', label: 'MiniMax 兼容' },
  { value: 'custom_openai_compatible', label: '自定义 OpenAI 兼容' },
  { value: 'message', label: 'Claude Messages（仅测试）' }
] as const

function ApiConfigPanel(props: {
  status: ApiConfigStatus | null
  action: ApiConfigActionState
  onRefresh: () => void
  onSaveProfile: (profile: ApiConfigProfilePatch) => Promise<string | null>
  onTestProfile: (profile: ApiConfigProfilePatch) => void
  onDeleteProfile: (profileId: string) => void
  onApplyProfile: (profileId: string) => Promise<void>
  onRestartCore: () => void
}): JSX.Element {
  const profiles = props.status?.profiles || []
  const activeProfileId = props.status?.activeProfileId || ''
  const preferredProfileId = activeProfileId || profiles[0]?.id || API_NEW_PROFILE_ID
  const [selectedId, setSelectedId] = React.useState(() => preferredProfileId)
  const [activeSection, setActiveSection] = React.useState<ApiSectionId>('llm')
  const selected = selectedId === API_NEW_PROFILE_ID ? null : profiles.find((profile) => profile.id === selectedId) || null
  const [draft, setDraft] = React.useState<ApiConfigDraft>(() => apiDraftFromStatus(props.status))
  const [draftDirty, setDraftDirty] = React.useState(false)
  const [draftSourceId, setDraftSourceId] = React.useState(API_NEW_PROFILE_ID)
  const didInitSelection = React.useRef(Boolean(props.status))
  const userSelectedNew = React.useRef(false)
  const busy = props.action.kind !== 'idle'
  const current = props.status?.current
  const sourceId = selected?.id || API_NEW_PROFILE_ID

  React.useEffect(() => {
    if (!props.status) {
      return
    }
    if (!didInitSelection.current) {
      didInitSelection.current = true
      setSelectedId(preferredProfileId)
      return
    }
    if (
      selectedId === API_NEW_PROFILE_ID &&
      !draftDirty &&
      activeProfileId &&
      !userSelectedNew.current
    ) {
      setSelectedId(activeProfileId)
      return
    }
    if (selectedId === API_NEW_PROFILE_ID || profiles.some((profile) => profile.id === selectedId)) {
      return
    }
    userSelectedNew.current = false
    setSelectedId(preferredProfileId)
  }, [activeProfileId, draftDirty, preferredProfileId, profiles, props.status, selectedId])

  React.useEffect(() => {
    if (draftDirty && draftSourceId === sourceId) {
      return
    }
    setDraft(selected ? apiDraftFromProfile(selected) : apiDraftFromStatus(props.status))
    setDraftSourceId(sourceId)
    setDraftDirty(false)
  }, [draftDirty, draftSourceId, props.status, selected, sourceId])

  function updateDraft(patch: Partial<ApiConfigDraft>): void {
    setDraftDirty(true)
    setDraft((currentDraft) => ({ ...currentDraft, ...patch }))
  }

  function updateDraftSection<K extends ApiSectionId>(section: K, patch: Partial<ApiConfigDraft[K]>): void {
    setDraftDirty(true)
    setDraft((currentDraft) => ({
      ...currentDraft,
      [section]: {
        ...currentDraft[section],
        ...patch
      }
    }))
  }

  function draftToPatch(): ApiConfigProfilePatch {
    return {
      id: selected?.id,
      label: draft.label,
      llm: {
        provider: draft.llm.provider,
        model: draft.llm.model,
        baseUrl: draft.llm.baseUrl,
        apiKey: draft.llm.apiKey.trim() || undefined,
        allowInsecureHttp: draft.llm.allowInsecureHttp,
        disableStreaming: draft.llm.disableStreaming
      },
      vision: {
        enabled: draft.vision.enabled,
        model: draft.vision.model,
        baseUrl: draft.vision.baseUrl,
        apiKey: draft.vision.apiKey.trim() || undefined,
        timeoutSeconds: draft.vision.timeoutSeconds,
        maxBytes: draft.vision.maxBytes
      },
      hearing: {
        enabled: draft.hearing.enabled,
        command: draft.hearing.command,
        model: draft.hearing.model,
        baseUrl: draft.hearing.baseUrl,
        apiKey: draft.hearing.apiKey.trim() || undefined,
        language: draft.hearing.language,
        timeoutSeconds: draft.hearing.timeoutSeconds,
        recordFormat: draft.hearing.recordFormat
      },
      tts: {
        enabled: draft.tts.enabled,
        engine: draft.tts.engine,
        model: draft.tts.model,
        baseUrl: draft.tts.baseUrl,
        apiKey: draft.tts.apiKey.trim() || undefined,
        voice: draft.tts.voice,
        format: draft.tts.format,
        requestMode: draft.tts.requestMode,
        timeoutSeconds: draft.tts.timeoutSeconds,
        genieBaseUrl: draft.tts.genieBaseUrl,
        genieCharacter: draft.tts.genieCharacter,
        genieSplitSentence: draft.tts.genieSplitSentence,
        genieSampleRate: draft.tts.genieSampleRate,
        genieChannels: draft.tts.genieChannels,
        genieSampleWidth: draft.tts.genieSampleWidth
      },
      other: {
        openAIApiKey: draft.other.openAIApiKey.trim() || undefined
      }
    }
  }

  async function saveProfile(): Promise<string | null> {
    const savedId = await props.onSaveProfile(draftToPatch())
    if (!savedId) {
      return null
    }
    userSelectedNew.current = false
    setSelectedId(savedId)
    setDraftSourceId(savedId)
    setDraftDirty(false)
    return savedId
  }

  function testProfile(): void {
    props.onTestProfile(draftToPatch())
  }

  async function applyProfile(): Promise<void> {
    let profileId = selected?.id || ''
    if (draftDirty || !profileId) {
      const savedId = await saveProfile()
      if (!savedId) {
        return
      }
      profileId = savedId
    }
    if (!profileId) {
      return
    }
    await props.onApplyProfile(profileId)
  }

  function selectProfile(nextId: string): void {
    setSelectedId(nextId)
    userSelectedNew.current = nextId === API_NEW_PROFILE_ID
    const nextProfile = profiles.find((profile) => profile.id === nextId)
    setDraft(nextProfile ? apiDraftFromProfile(nextProfile) : apiDraftFromStatus(props.status))
    setDraftSourceId(nextProfile?.id || API_NEW_PROFILE_ID)
    setDraftDirty(false)
  }

  const activeProfileLabel = profiles.find((profile) => profile.active)?.label || ''
  const currentText = current ? `${current.llm.provider} / ${current.llm.model}` : '未加载'
  const currentSecretText = current?.llm.hasApiKey ? current.llm.apiKeyPreview : '无 LLM 密钥'
  const currentMetaText = activeProfileLabel
    ? `活跃：${compact(activeProfileLabel, 18)} · ${currentSecretText}`
    : currentSecretText
  const llmSecret = selected?.llm || current?.llm
  const visionSecret = selected?.vision || current?.vision
  const hearingSecret = selected?.hearing || current?.hearing
  const ttsSecret = selected?.tts || current?.tts
  const otherSecret = selected?.other || current?.other
  const ttsEngine = draft.tts.engine === 'genie' ? 'genie' : 'current'
  const sectionCards = [
    {
      id: 'llm' as const,
      icon: <Brain size={14} />,
      label: 'LLM',
      summary: `${draft.llm.provider || '未填'} / ${draft.llm.model || '未填模型'}`,
      ready: Boolean(draft.llm.baseUrl)
    },
    {
      id: 'vision' as const,
      icon: <Eye size={14} />,
      label: '视觉',
      summary: draft.vision.enabled ? draft.vision.model || '未填模型' : '未启用',
      ready: Boolean(draft.vision.enabled)
    },
    {
      id: 'hearing' as const,
      icon: <Radio size={14} />,
      label: '听觉',
      summary: draft.hearing.enabled ? `${draft.hearing.model || '未填模型'} / ${draft.hearing.language || '未填语言'}` : '未启用',
      ready: Boolean(draft.hearing.enabled)
    },
    {
      id: 'tts' as const,
      icon: <Volume2 size={14} />,
      label: 'TTS',
      summary: draft.tts.enabled
        ? ttsEngine === 'genie'
          ? `Genie / ${draft.tts.genieCharacter || '未填角色'}`
          : `${draft.tts.model || '未填模型'} / ${draft.tts.voice || '未填音色'}`
        : '已关闭',
      ready: Boolean(draft.tts.enabled)
    },
    {
      id: 'other' as const,
      icon: <Puzzle size={14} />,
      label: '其他',
      summary: draft.other.openAIApiKey ? '将覆盖共享密钥' : otherSecret?.hasOpenAIApiKey ? otherSecret.openAIApiKeyPreview : '未配置',
      ready: Boolean(draft.other.openAIApiKey || otherSecret?.hasOpenAIApiKey)
    }
  ]
  const providerKnown = API_PROVIDER_OPTIONS.some((option) => option.value === draft.llm.provider)
  const providerHelp =
    draft.llm.provider === 'message'
      ? '这个接口只用于 Claude Messages /v1/messages 连通性测试；当前 core 主运行时还不能应用它。'
      : draft.llm.provider === 'custom_openai_compatible'
        ? '用于任何真实支持 /chat/completions 的服务；不要填 Claude Messages 原生接口。'
        : '应用到 core 时会按 /chat/completions 协议调用。'

  return (
    <section className={`api-config-panel ${activeProfileId ? 'ready' : 'warn'}`}>
      <div className="section-head api-config-head">
        <span>
          <Terminal size={15} />
          <span>API 配置中心</span>
        </span>
        <strong>{profiles.length}</strong>
      </div>

      <div className="api-current-line">
        <span>{compact(currentText, 42)}</span>
        <small>{compact(currentMetaText, 42)}</small>
      </div>

      <div className="api-profile-select">
        <select value={selectedId} disabled={busy} onChange={(event) => selectProfile(event.currentTarget.value)}>
          <option value={API_NEW_PROFILE_ID}>从当前配置新建</option>
          {profiles.map((profile) => (
            <option value={profile.id} key={profile.id}>
              {profile.active ? '* ' : ''}
              {profile.label} · {profile.llm.model}
            </option>
          ))}
        </select>
        <button type="button" onClick={props.onRefresh} disabled={busy} title="刷新 API 配置" aria-label="刷新 API 配置">
          <RefreshCw size={14} className={props.action.kind === 'loading' ? 'spin' : ''} />
        </button>
      </div>

      <div className="api-profile-name">
        <label>
          <span>配置名称</span>
          <input value={draft.label} disabled={busy} onChange={(event) => updateDraft({ label: event.currentTarget.value })} />
        </label>
      </div>

      <div className="api-section-tabs">
        {sectionCards.map((card) => (
          <button
            key={card.id}
            type="button"
            className={`api-section-tab ${activeSection === card.id ? 'active' : ''} ${card.ready ? 'ready' : 'idle'}`}
            onClick={() => setActiveSection(card.id)}
            disabled={busy}
            aria-pressed={activeSection === card.id}
          >
            <span>
              {card.icon}
              <strong>{card.label}</strong>
            </span>
            <small>{compact(card.summary, 30)}</small>
          </button>
        ))}
      </div>

      {activeSection === 'llm' ? (
        <>
          <div className="api-config-grid">
            <label>
              <span>提供方</span>
              <select
                value={providerKnown ? draft.llm.provider : 'custom_openai_compatible'}
                disabled={busy}
                onChange={(event) => updateDraftSection('llm', { provider: event.currentTarget.value })}
              >
                {API_PROVIDER_OPTIONS.map((option) => (
                  <option value={option.value} key={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <small>{providerKnown ? providerHelp : `当前未知提供方 ${draft.llm.provider}；应用前请选择“自定义 OpenAI 兼容”。`}</small>
            </label>
            <label>
              <span>模型</span>
              <input value={draft.llm.model} disabled={busy} onChange={(event) => updateDraftSection('llm', { model: event.currentTarget.value })} />
            </label>
            <label className="full">
              <span>基础地址</span>
              <input value={draft.llm.baseUrl} disabled={busy} onChange={(event) => updateDraftSection('llm', { baseUrl: event.currentTarget.value })} />
            </label>
            <label className="api-key-field">
              <span>密钥</span>
              <input
                value={draft.llm.apiKey}
                disabled={busy}
                type="password"
                placeholder={apiSecretPlaceholder(llmSecret?.hasApiKey, llmSecret?.apiKeyPreview, '粘贴 LLM API 密钥')}
                onChange={(event) => updateDraftSection('llm', { apiKey: event.currentTarget.value })}
              />
              <small>{apiSecretHint(draft.llm.apiKey, Boolean(llmSecret?.hasApiKey), '新密钥会覆盖已保存密钥', '留空则沿用当前环境密钥')}</small>
            </label>
          </div>

          <div className="api-runtime-flags">
            <RuntimeSwitch
              label="HTTP"
              checked={draft.llm.allowInsecureHttp}
              detail={draft.llm.allowInsecureHttp ? '明文连接' : '安全连接'}
              danger={draft.llm.allowInsecureHttp}
              disabled={busy}
              onToggle={() => updateDraftSection('llm', { allowInsecureHttp: !draft.llm.allowInsecureHttp })}
            />
            <RuntimeSwitch
              label="流式输出"
              checked={!draft.llm.disableStreaming}
              detail={draft.llm.disableStreaming ? '关闭' : '开启'}
              disabled={busy}
              onToggle={() => updateDraftSection('llm', { disableStreaming: !draft.llm.disableStreaming })}
            />
          </div>
        </>
      ) : null}

      {activeSection === 'vision' ? (
        <>
          <div className="api-runtime-flags api-runtime-flags-single">
            <RuntimeSwitch
              label="视觉启用"
              checked={draft.vision.enabled}
              detail={draft.vision.enabled ? '图像理解已接入' : '当前关闭'}
              disabled={busy}
              onToggle={() => updateDraftSection('vision', { enabled: !draft.vision.enabled })}
            />
          </div>

          <div className="api-config-grid">
            <label>
              <span>模型</span>
              <input value={draft.vision.model} disabled={busy} onChange={(event) => updateDraftSection('vision', { model: event.currentTarget.value })} />
            </label>
            <label>
              <span>超时（秒）</span>
              <input
                type="number"
                min={1}
                value={draft.vision.timeoutSeconds}
                disabled={busy}
                onChange={(event) => updateDraftSection('vision', { timeoutSeconds: parseDraftNumber(event.currentTarget.value, draft.vision.timeoutSeconds) })}
              />
            </label>
            <label className="full">
              <span>基础地址</span>
              <input value={draft.vision.baseUrl} disabled={busy} onChange={(event) => updateDraftSection('vision', { baseUrl: event.currentTarget.value })} />
            </label>
            <label>
              <span>最大字节数</span>
              <input
                type="number"
                min={1024}
                value={draft.vision.maxBytes}
                disabled={busy}
                onChange={(event) => updateDraftSection('vision', { maxBytes: parseDraftNumber(event.currentTarget.value, draft.vision.maxBytes) })}
              />
            </label>
            <label className="api-key-field">
              <span>密钥</span>
              <input
                value={draft.vision.apiKey}
                disabled={busy}
                type="password"
                placeholder={apiSecretPlaceholder(visionSecret?.hasApiKey, visionSecret?.apiKeyPreview, '粘贴视觉 API 密钥')}
                onChange={(event) => updateDraftSection('vision', { apiKey: event.currentTarget.value })}
              />
              <small>{apiSecretHint(draft.vision.apiKey, Boolean(visionSecret?.hasApiKey), '新密钥会覆盖已保存密钥', '留空则沿用当前环境密钥')}</small>
            </label>
          </div>
        </>
      ) : null}

      {activeSection === 'hearing' ? (
        <>
          <div className="api-runtime-flags api-runtime-flags-single">
            <RuntimeSwitch
              label="听觉启用"
              checked={draft.hearing.enabled}
              detail={draft.hearing.enabled ? '语音转文字已接入' : '当前关闭'}
              disabled={busy}
              onToggle={() => updateDraftSection('hearing', { enabled: !draft.hearing.enabled })}
            />
          </div>

          <div className="api-config-grid">
            <label className="full">
              <span>命令通道</span>
              <input value={draft.hearing.command} disabled={busy} onChange={(event) => updateDraftSection('hearing', { command: event.currentTarget.value })} />
            </label>
            <label>
              <span>模型</span>
              <input value={draft.hearing.model} disabled={busy} onChange={(event) => updateDraftSection('hearing', { model: event.currentTarget.value })} />
            </label>
            <label>
              <span>语言</span>
              <input value={draft.hearing.language} disabled={busy} onChange={(event) => updateDraftSection('hearing', { language: event.currentTarget.value })} />
            </label>
            <label className="full">
              <span>基础地址</span>
              <input value={draft.hearing.baseUrl} disabled={busy} onChange={(event) => updateDraftSection('hearing', { baseUrl: event.currentTarget.value })} />
            </label>
            <label>
              <span>超时（秒）</span>
              <input
                type="number"
                min={1}
                value={draft.hearing.timeoutSeconds}
                disabled={busy}
                onChange={(event) => updateDraftSection('hearing', { timeoutSeconds: parseDraftNumber(event.currentTarget.value, draft.hearing.timeoutSeconds) })}
              />
            </label>
            <label>
              <span>录音格式</span>
              <input value={draft.hearing.recordFormat} disabled={busy} onChange={(event) => updateDraftSection('hearing', { recordFormat: event.currentTarget.value })} />
            </label>
            <label className="api-key-field">
              <span>密钥</span>
              <input
                value={draft.hearing.apiKey}
                disabled={busy}
                type="password"
                placeholder={apiSecretPlaceholder(hearingSecret?.hasApiKey, hearingSecret?.apiKeyPreview, '粘贴听觉 API 密钥')}
                onChange={(event) => updateDraftSection('hearing', { apiKey: event.currentTarget.value })}
              />
              <small>{apiSecretHint(draft.hearing.apiKey, Boolean(hearingSecret?.hasApiKey), '新密钥会覆盖已保存密钥', '留空则沿用当前环境密钥')}</small>
            </label>
          </div>
        </>
      ) : null}
      {activeSection === 'tts' ? (
        <>
          <div className="api-runtime-flags">
            <RuntimeSwitch
              label="TTS"
              checked={draft.tts.enabled}
              detail={draft.tts.enabled ? '本地播放开启' : '本地播放关闭'}
              disabled={busy}
              onToggle={() => updateDraftSection('tts', { enabled: !draft.tts.enabled })}
            />
            <div className="api-engine-choice" role="group" aria-label="语音引擎">
              <button
                type="button"
                className={ttsEngine === 'current' ? 'active' : ''}
                aria-pressed={ttsEngine === 'current'}
                disabled={busy}
                onClick={() => updateDraftSection('tts', { engine: 'current' })}
              >
                <strong>当前接口</strong>
                <small>OpenAI / MiMo</small>
              </button>
              <button
                type="button"
                className={ttsEngine === 'genie' ? 'active' : ''}
                aria-pressed={ttsEngine === 'genie'}
                disabled={busy}
                onClick={() => updateDraftSection('tts', { engine: 'genie' })}
              >
                <strong>Genie-TTS</strong>
                <small>{draft.tts.genieCharacter || 'feibi'}</small>
              </button>
            </div>
          </div>

          {ttsEngine === 'genie' ? (
            <>
              <div className="api-runtime-flags api-runtime-flags-single">
                <RuntimeSwitch
                  label="分句"
                  checked={draft.tts.genieSplitSentence}
                  detail={draft.tts.genieSplitSentence ? '开启' : '关闭'}
                  disabled={busy}
                  onToggle={() => updateDraftSection('tts', { genieSplitSentence: !draft.tts.genieSplitSentence })}
                />
              </div>
              <div className="api-config-grid">
                <label className="full">
                  <span>Genie 地址</span>
                  <input
                    value={draft.tts.genieBaseUrl}
                    disabled={busy}
                    onChange={(event) => updateDraftSection('tts', { genieBaseUrl: event.currentTarget.value })}
                  />
                </label>
                <label>
                  <span>角色</span>
                  <input
                    value={draft.tts.genieCharacter}
                    disabled={busy}
                    onChange={(event) => updateDraftSection('tts', { genieCharacter: event.currentTarget.value })}
                  />
                </label>
                <label>
                  <span>超时（秒）</span>
                  <input
                    type="number"
                    min={1}
                    value={draft.tts.timeoutSeconds}
                    disabled={busy}
                    onChange={(event) => updateDraftSection('tts', { timeoutSeconds: parseDraftNumber(event.currentTarget.value, draft.tts.timeoutSeconds) })}
                  />
                </label>
                <label>
                  <span>采样率</span>
                  <input
                    type="number"
                    min={8000}
                    value={draft.tts.genieSampleRate}
                    disabled={busy}
                    onChange={(event) => updateDraftSection('tts', { genieSampleRate: parseDraftNumber(event.currentTarget.value, draft.tts.genieSampleRate) })}
                  />
                </label>
                <label>
                  <span>声道</span>
                  <input
                    type="number"
                    min={1}
                    max={8}
                    value={draft.tts.genieChannels}
                    disabled={busy}
                    onChange={(event) => updateDraftSection('tts', { genieChannels: parseDraftNumber(event.currentTarget.value, draft.tts.genieChannels) })}
                  />
                </label>
                <label>
                  <span>采样宽度</span>
                  <input
                    type="number"
                    min={1}
                    max={4}
                    value={draft.tts.genieSampleWidth}
                    disabled={busy}
                    onChange={(event) => updateDraftSection('tts', { genieSampleWidth: parseDraftNumber(event.currentTarget.value, draft.tts.genieSampleWidth) })}
                  />
                </label>
              </div>
            </>
          ) : (
            <div className="api-config-grid">
              <label>
                <span>模型</span>
                <input value={draft.tts.model} disabled={busy} onChange={(event) => updateDraftSection('tts', { model: event.currentTarget.value })} />
              </label>
              <label>
                <span>音色</span>
                <input value={draft.tts.voice} disabled={busy} onChange={(event) => updateDraftSection('tts', { voice: event.currentTarget.value })} />
              </label>
              <label className="full">
                <span>基础地址</span>
                <input value={draft.tts.baseUrl} disabled={busy} onChange={(event) => updateDraftSection('tts', { baseUrl: event.currentTarget.value })} />
              </label>
              <label>
                <span>请求模式</span>
                <select value={draft.tts.requestMode} disabled={busy} onChange={(event) => updateDraftSection('tts', { requestMode: event.currentTarget.value })}>
                  <option value="auto">自动</option>
                  <option value="chat_audio">聊天音频</option>
                  <option value="audio_speech">语音生成</option>
                </select>
              </label>
              <label>
                <span>格式</span>
                <input value={draft.tts.format} disabled={busy} onChange={(event) => updateDraftSection('tts', { format: event.currentTarget.value })} />
              </label>
              <label>
                <span>超时（秒）</span>
                <input
                  type="number"
                  min={1}
                  value={draft.tts.timeoutSeconds}
                  disabled={busy}
                  onChange={(event) => updateDraftSection('tts', { timeoutSeconds: parseDraftNumber(event.currentTarget.value, draft.tts.timeoutSeconds) })}
                />
              </label>
              <label className="api-key-field">
                <span>密钥</span>
                <input
                  value={draft.tts.apiKey}
                  disabled={busy}
                  type="password"
                  placeholder={apiSecretPlaceholder(ttsSecret?.hasApiKey, ttsSecret?.apiKeyPreview, '粘贴 TTS API 密钥')}
                  onChange={(event) => updateDraftSection('tts', { apiKey: event.currentTarget.value })}
                />
                <small>{apiSecretHint(draft.tts.apiKey, Boolean(ttsSecret?.hasApiKey), '新密钥会覆盖已保存密钥', '留空则沿用当前环境密钥')}</small>
              </label>
            </div>
          )}
        </>
      ) : null}

      {activeSection === 'other' ? (
        <div className="api-config-grid">
          <label className="api-key-field">
            <span>共享 OpenAI Key</span>
            <input
              value={draft.other.openAIApiKey}
              disabled={busy}
              type="password"
              placeholder={
                otherSecret?.hasOpenAIApiKey
                  ? `${otherSecret.openAIApiKeyPreview} · 留空则保留`
                  : '粘贴共享 OpenAI / 备用密钥'
              }
              onChange={(event) => updateDraftSection('other', { openAIApiKey: event.currentTarget.value })}
            />
            <small>{apiSecretHint(draft.other.openAIApiKey, Boolean(otherSecret?.hasOpenAIApiKey), '新密钥会覆盖已保存密钥', '留空则沿用当前环境密钥')}</small>
          </label>
        </div>
      ) : null}

      <div className="api-config-actions">
        <button type="button" onClick={() => void saveProfile()} disabled={busy || !draft.label.trim()} title="保存 API 配置" aria-label="保存 API 配置">
          <Save size={14} />
          <span>保存</span>
        </button>
        <button
          type="button"
          onClick={testProfile}
          disabled={busy || !draft.llm.baseUrl.trim() || !draft.llm.model.trim()}
          title="测试 LLM"
          aria-label="测试 LLM"
        >
          <Radio size={14} className={props.action.kind === 'testing' ? 'spin' : ''} />
          <span>测试 LLM</span>
        </button>
        <button
          type="button"
          onClick={() => void applyProfile()}
          disabled={busy || (!selected && !draft.label.trim())}
          title="应用并重启核心"
          aria-label="应用并重启核心"
        >
          <Play size={14} />
          <span>应用</span>
        </button>
        <button
          type="button"
          onClick={() => selected && props.onDeleteProfile(selected.id)}
          disabled={busy || !selected}
          title="删除 API 配置"
          aria-label="删除 API 配置"
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
    label: current?.llm.provider ? `${current.llm.provider} ${current.llm.model}`.trim() : '本地 API',
    llm: {
      provider: current?.llm.provider || 'ciallo',
      model: current?.llm.model || 'mimo-v2.5-pro',
      baseUrl: current?.llm.baseUrl || '',
      apiKey: '',
      allowInsecureHttp: Boolean(current?.llm.allowInsecureHttp),
      disableStreaming: current?.llm.disableStreaming !== false
    },
    vision: {
      enabled: Boolean(current?.vision.enabled),
      model: current?.vision.model || 'gpt-4o-mini',
      baseUrl: current?.vision.baseUrl || '',
      apiKey: '',
      timeoutSeconds: current?.vision.timeoutSeconds || 45,
      maxBytes: current?.vision.maxBytes || 4 * 1024 * 1024
    },
    hearing: {
      enabled: current?.hearing.enabled !== false,
      command: current?.hearing.command || '',
      model: current?.hearing.model || 'whisper-1',
      baseUrl: current?.hearing.baseUrl || '',
      apiKey: '',
      language: current?.hearing.language || 'zh',
      timeoutSeconds: current?.hearing.timeoutSeconds || 120,
      recordFormat: current?.hearing.recordFormat || 'mp3'
    },
    tts: {
      enabled: Boolean(current?.tts.enabled),
      engine: current?.tts.engine || 'current',
      model: current?.tts.model || 'mimo-v2.5-tts',
      baseUrl: current?.tts.baseUrl || current?.hearing.baseUrl || '',
      apiKey: '',
      voice: current?.tts.voice || 'mimo_default',
      format: current?.tts.format || 'wav',
      requestMode: current?.tts.requestMode || 'auto',
      timeoutSeconds: current?.tts.timeoutSeconds || 60,
      genieBaseUrl: current?.tts.genieBaseUrl || 'http://127.0.0.1:8000',
      genieCharacter: current?.tts.genieCharacter || 'feibi',
      genieSplitSentence: Boolean(current?.tts.genieSplitSentence),
      genieSampleRate: current?.tts.genieSampleRate || 32000,
      genieChannels: current?.tts.genieChannels || 1,
      genieSampleWidth: current?.tts.genieSampleWidth || 2
    },
    other: {
      openAIApiKey: ''
    }
  }
}

function apiBlankDraft(): ApiConfigDraft {
  return {
    label: '',
    llm: {
      provider: 'message',
      model: '',
      baseUrl: '',
      apiKey: '',
      allowInsecureHttp: false,
      disableStreaming: true
    },
    vision: {
      enabled: false,
      model: 'gpt-4o-mini',
      baseUrl: '',
      apiKey: '',
      timeoutSeconds: 45,
      maxBytes: 4 * 1024 * 1024
    },
    hearing: {
      enabled: true,
      command: '',
      model: 'whisper-1',
      baseUrl: '',
      apiKey: '',
      language: 'zh',
      timeoutSeconds: 120,
      recordFormat: 'mp3'
    },
    tts: {
      enabled: false,
      engine: 'current',
      model: 'mimo-v2.5-tts',
      baseUrl: '',
      apiKey: '',
      voice: 'mimo_default',
      format: 'wav',
      requestMode: 'auto',
      timeoutSeconds: 60,
      genieBaseUrl: 'http://127.0.0.1:8000',
      genieCharacter: 'feibi',
      genieSplitSentence: false,
      genieSampleRate: 32000,
      genieChannels: 1,
      genieSampleWidth: 2
    },
    other: {
      openAIApiKey: ''
    }
  }
}

function apiDraftFromProfile(profile: ApiConfigProfile): ApiConfigDraft {
  return {
    label: profile.label,
    llm: {
      provider: profile.llm.provider,
      model: profile.llm.model,
      baseUrl: profile.llm.baseUrl,
      apiKey: '',
      allowInsecureHttp: profile.llm.allowInsecureHttp,
      disableStreaming: profile.llm.disableStreaming
    },
    vision: {
      enabled: profile.vision.enabled,
      model: profile.vision.model,
      baseUrl: profile.vision.baseUrl,
      apiKey: '',
      timeoutSeconds: profile.vision.timeoutSeconds,
      maxBytes: profile.vision.maxBytes
    },
    hearing: {
      enabled: profile.hearing.enabled,
      command: profile.hearing.command,
      model: profile.hearing.model,
      baseUrl: profile.hearing.baseUrl,
      apiKey: '',
      language: profile.hearing.language,
      timeoutSeconds: profile.hearing.timeoutSeconds,
      recordFormat: profile.hearing.recordFormat
    },
    tts: {
      enabled: profile.tts.enabled,
      engine: profile.tts.engine || 'current',
      model: profile.tts.model,
      baseUrl: profile.tts.baseUrl,
      apiKey: '',
      voice: profile.tts.voice,
      format: profile.tts.format,
      requestMode: profile.tts.requestMode,
      timeoutSeconds: profile.tts.timeoutSeconds,
      genieBaseUrl: profile.tts.genieBaseUrl || 'http://127.0.0.1:8000',
      genieCharacter: profile.tts.genieCharacter || 'feibi',
      genieSplitSentence: profile.tts.genieSplitSentence,
      genieSampleRate: profile.tts.genieSampleRate || 32000,
      genieChannels: profile.tts.genieChannels || 1,
      genieSampleWidth: profile.tts.genieSampleWidth || 2
    },
    other: {
      openAIApiKey: ''
    }
  }
}

function apiSecretPlaceholder(hasSecret: boolean | undefined, preview: string | undefined, createText: string): string {
  return hasSecret && preview ? `${preview} · 留空则保留` : createText
}

function apiSecretHint(nextValue: string, hasStored: boolean, replaceText: string, fallbackText: string): string {
  if (nextValue.trim()) {
    return replaceText
  }
  return hasStored ? '留空则保留已保存密钥' : fallbackText
}

function parseDraftNumber(value: string, fallback: number): number {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : fallback
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
  const qqLoginState =
    props.status?.napcatQQLoggedIn === true
      ? 'QQ 已登录'
      : props.status?.napcatQQLoggedIn === false
        ? 'QQ 未登录'
        : tokenAvailable
          ? '网页端口令可复制'
          : '未找到网页端口令'
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
        <small>{qqLoginState}</small>
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
          title="打开 NapCat 网页端（未启动时会自动拉起）"
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
  feedback?: string
  onAck: (candidateId: string, action: ProactiveAction) => void
  onOpenDetail: (candidateId: string) => void
}): JSX.Element {
  const disabled = Boolean(props.pendingAction)
  const localOnlyNote = props.intent.claimable ? '' : '仅桌面可见，不能直接发 QQ'
  const actionNote = props.pendingAction ? actionLabel(props.pendingAction) : props.feedback || localOnlyNote
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
        <span>{proactiveTextLabel(props.intent.source)}</span>
        <strong>{proactiveTextLabel(props.intent.trigger)}</strong>
      </div>
      <p>{proactiveTextLabel(props.intent.plannedText)}</p>
      <div className="intent-foot">
        <span className="risk-label">
          <ShieldAlert size={13} />
          {props.intent.riskLabel}
        </span>
        <span>{props.intent.claimable ? proactiveTextLabel(props.intent.delivery) : '仅桌面可见'}</span>
      </div>
      <div className="intent-actions">
        <button
          type="button"
          disabled={disabled}
          onClick={() => props.onAck(props.intent.id, 'read_locally')}
          title="只在本地读过"
          aria-label="只在本地读过"
        >
          <Eye size={14} />
        </button>
        <button
          type="button"
          className={props.intent.claimable ? '' : 'unavailable'}
          disabled={disabled}
          onClick={() => (props.intent.claimable ? props.onAck(props.intent.id, 'approve_qq') : props.onOpenDetail(props.intent.id))}
          title={props.intent.claimable ? '同意发送到 QQ' : '这条仅桌面可见，不能直接发 QQ；点击查看详情'}
          aria-label={props.intent.claimable ? '同意发送到 QQ' : '不能直接发 QQ，查看详情'}
        >
          <Send size={14} />
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => props.onAck(props.intent.id, 'dismiss')}
          title="忽略"
          aria-label="忽略"
        >
          <X size={14} />
        </button>
      </div>
      {actionNote ? <small className="intent-action-note">{actionNote}</small> : null}
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
        <strong>{proactiveTextLabel(props.intent.trigger)}</strong>
      </div>
      <p>{proactiveTextLabel(props.intent.plannedText)}</p>
      <div className="intent-foot">
        <span>{formatTime(props.intent.updatedAt || props.intent.createdAt)}</span>
        <span>{proactiveTextLabel(props.intent.delivery)}</span>
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
  feedback?: string
  onClose: () => void
  onAck: (candidateId: string, action: ProactiveAction) => void
  onReply: (intent: ProactiveIntent, text: string) => void
}): JSX.Element {
  const handled = isHandledIntent(props.intent)
  const disabled = Boolean(props.pendingAction) || handled
  const text = props.intent.fullText || props.intent.plannedText
  const actionNote = props.pendingAction
    ? actionLabel(props.pendingAction)
    : props.feedback || (!props.intent.claimable ? '这条仅桌面可见，不能直接发送到 QQ。' : '')
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
            <h3 id="intent-dialog-title">{proactiveTextLabel(props.intent.trigger)}</h3>
          </div>
          <button type="button" onClick={props.onClose} title="关闭" aria-label="关闭主动提醒详情">
            <X size={16} />
          </button>
        </header>

        <div className="intent-dialog-body">
          <div className="intent-dialog-message">{proactiveTextLabel(text)}</div>
          <dl className="intent-dialog-facts">
            <div>
              <dt>来源</dt>
              <dd>{proactiveTextLabel(props.intent.source)}</dd>
            </div>
            <div>
              <dt>投递</dt>
              <dd>{proactiveTextLabel(props.intent.delivery)}</dd>
            </div>
            <div>
              <dt>状态</dt>
              <dd>{intentStatusLabel(proactiveTextLabel(props.intent.status))}</dd>
            </div>
            <div>
              <dt>动作</dt>
              <dd>{intentRequestedActionLabel(proactiveTextLabel(props.intent.requestedAction))}</dd>
            </div>
            {props.intent.reasonText ? (
              <div>
                <dt>原因</dt>
                <dd>{compact(proactiveTextLabel(props.intent.reasonText), 72)}</dd>
              </div>
            ) : null}
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
            title="只在本地读过"
          >
            <Eye size={15} />
            本地已读
          </button>
          <button
            type="button"
            disabled={disabled || !props.intent.claimable}
            onClick={() => props.onAck(props.intent.id, 'approve_qq')}
            title={props.intent.claimable ? '同意发送到 QQ' : '这条仅桌面可见，不能直接发 QQ'}
          >
            <Send size={15} />
            {props.intent.claimable ? '发送到 QQ' : '不能发 QQ'}
          </button>
          <button type="button" disabled={disabled} onClick={() => props.onAck(props.intent.id, 'dismiss')} title="忽略">
            <X size={15} />
            忽略
          </button>
          {actionNote ? <small className="intent-dialog-note">{actionNote}</small> : null}
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

type GateCell = { label: string; ok: boolean | null; detail?: string }

function GateCellView({ cell }: { cell: GateCell }): JSX.Element {
  const tone = cell.ok === true ? 'gate-ok' : cell.ok === false ? 'gate-fail' : 'gate-unknown'
  return (
    <div className={`gate-cell ${tone}`} title={cell.detail || cell.label}>
      <span className="gate-icon">{cell.ok === true ? <Check size={11} /> : cell.ok === false ? <X size={11} /> : <Clock3 size={11} />}</span>
      <span className="gate-label">{cell.label}</span>
    </div>
  )
}

export function AutonomyGatePanel(props: {
  stage12: Stage12GateStatus | null
  stage13: Stage13GateStatus | null
  qqEnvironment: QQEnvironmentStatus | null
  stage8: Stage8MemoryGovernanceStatus | null
  asyncExploration: AsyncExplorationState | null
  kernelGovernance: KernelGovernanceStatus | null
}): JSX.Element {
  const { stage12, stage13, qqEnvironment, stage8, asyncExploration, kernelGovernance } = props

  const services: GateCell[] = (qqEnvironment?.services || []).map((s) => ({
    label: qqServiceLabel(s),
    ok: s.ok,
    detail: s.detail || s.endpoint,
  }))

  const s12cells: GateCell[] = stage12
    ? [
        { label: 'Stage11→12', ok: stage12.gateStage11Ready },
        { label: '实时循环', ok: stage12.gateLiveLoopPass, detail: stage12.liveLoopFailingDetail || stage12.liveLoopFailingChecks },
        { label: '反馈消费', ok: stage12.gateFeedbackClean },
        { label: '短期记忆', ok: stage12.gateShortTermClean },
        { label: '隐私边界', ok: stage12.gatePrivacyClean },
        { label: '稳定记忆', ok: stage12.gateStableClean },
        { label: '金丝雀', ok: stage12.gateCanaryReady },
      ]
    : []

  const s13ready = stage13?.available ?? null
  const s8blocked = stage8 ? stage8.ownerReviewRequiredCount > 0 || stage8.duplicateClusterCount > 0 : null

  const s12StatusLabel = stage12
    ? stage12.readyForStage13
      ? '已就绪'
      : `${stage12.liveLoopPassedCount}/${stage12.liveLoopRequiredCount} 通过`
    : '—'

  const s12StatusTone = stage12
    ? stage12.readyForStage13
      ? 'status-ok'
      : 'status-fail'
    : 'status-unknown'

  return (
    <div className="autonomy-gate-panel">
      <div className="gate-section">
        <span className="gate-section-label">
          <Radio size={12} /> 服务
        </span>
        <div className="gate-cells">
          {services.length ? services.map((c) => <GateCellView key={c.label} cell={c} />) : <span className="gate-empty">等待刷新</span>}
        </div>
      </div>

      <div className="gate-section">
        <span className="gate-section-label">
          <Brain size={12} /> Stage12
          <span className={`gate-summary ${s12StatusTone}`}>{s12StatusLabel}</span>
        </span>
        {stage12 && stage12.readyForStage13 ? null : (
          <div className="gate-cells">
            {s12cells.map((c) => <GateCellView key={c.label} cell={c} />)}
          </div>
        )}
        {stage12 && !stage12.readyForStage13 && stage12.liveLoopFailingDetail && stage12.liveLoopFailingDetail !== 'none' ? (
          <div className="gate-blocker">{compact(stage12.liveLoopFailingDetail, 120)}</div>
        ) : null}
      </div>

      <div className="gate-section">
        <span className="gate-section-label">
          <Sparkles size={12} /> Stage13
          <GateCellView cell={{ label: s13ready ? '可用' : '等待 Stage12', ok: s13ready }} />
        </span>
        {stage13 && !stage13.available ? (
          <div className="gate-blocker">{compact(stage13.reason, 100)}</div>
        ) : null}
      </div>

      <div className="gate-section">
        <span className="gate-section-label">
          <Compass size={12} /> 探索循环
          {asyncExploration && asyncExploration.ok ? (
            <GateCellView cell={{
              label: asyncExploration.status === 'delegated_to_codex' ? '等待 Codex' :
                     asyncExploration.status === 'completed' ? '已完成' :
                     asyncExploration.status === 'missing' ? '无挂起探索' : asyncExploration.status,
              ok: asyncExploration.status === 'completed' ? true :
                  asyncExploration.status === 'delegated_to_codex' ? null : null,
              detail: asyncExploration.taskSummary || asyncExploration.delegationReason,
            }} />
          ) : (
            <span className="gate-empty">无挂起探索</span>
          )}
        </span>
        {asyncExploration && asyncExploration.resumeId && asyncExploration.resumeId !== 'none' ? (
          <div className="gate-blocker" style={{color:'var(--app-text)'}}>
            {compact(asyncExploration.resumeId, 40)} · {compact(asyncExploration.taskSummary, 60)}
          </div>
        ) : null}
      </div>

      <div className="gate-section">
        <span className="gate-section-label">
          <ShieldAlert size={12} /> Stage8 记忆治理
          {s8blocked === true ? (
            <span className="gate-summary status-fail">
              待审核 {stage8?.ownerReviewRequiredCount ?? 0} · 重复簇 {stage8?.duplicateClusterCount ?? 0}
            </span>
          ) : s8blocked === false ? (
            <span className="gate-summary status-ok">治理清洁</span>
          ) : null}
        </span>
      </div>

      <div className="gate-section">
        <span className="gate-section-label">
          <Brain size={12} /> 认知内核
          {kernelGovernance && kernelGovernance.pendingCount > 0 ? (
            <span className="gate-summary status-fail">待审 {kernelGovernance.pendingCount}</span>
          ) : kernelGovernance?.available ? (
            <span className="gate-summary status-ok">审核清洁</span>
          ) : null}
        </span>
        {kernelGovernance?.available ? (
          <div className="gate-blocker" style={{ color: 'var(--app-text)' }}>
            慢信号 {kernelGovernance.slowSignalCount}/{kernelGovernance.slowEscalationThreshold}
            {' · '}
            {kernelDomainLabel(kernelGovernance.reorgRecommendation, '重组建议暂无')}
            {' · '}
            周期 {kernelGovernance.cycleCount}
            {kernelGovernance.grantedScopes.length
              ? ` · 已授权 ${kernelGovernance.grantedScopes.map((scope) => kernelDomainLabel(scope)).join(' / ')}`
              : ''}
          </div>
        ) : kernelGovernance?.error ? (
          <div className="gate-blocker">{compact(kernelGovernance.error, 100)}</div>
        ) : (
          <span className="gate-empty">等待刷新</span>
        )}
      </div>
    </div>
  )
}

