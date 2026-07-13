import type { ApiConfigCurrent, ApiConfigProfile, ApiConfigStatus, AppState, AsyncExplorationState, CommandState, DesktopEvent, ExternalPluginControl, ExternalPluginInstallState, ExternalPluginsStatus, GrowthCandidatePromotionItem, GrowthCandidatePromotionStatus, ImpulseSoupState, ImpulseThoughtlet, ImpulseTraceEvent, JsonRecord, KernelGovernanceStatus, KernelReviewItem, ProactiveAction, ProactiveIntent, QQEnvironmentStatus, QQRuntimeConfig, ServiceProbe, Snapshot, Stage8BlockedGate, Stage8DuplicateCluster, Stage8MemoryGovernanceStatus, Stage8PromotionDryRun, Stage8ReviewDecision, Stage12GateStatus, Stage13GateStatus, StickerLibrary, StickerRecord, ThemeName, XinYuState } from './desktopTypes'

export const themeOptions: { id: ThemeName; label: string }[] = [
  { id: 'pastel', label: '粉紫' },
  { id: 'sakura', label: '樱粉' },
  { id: 'mint', label: '薄荷' },
  { id: 'night', label: '夜灯' }
]

export const stickerMoodLabels: Record<string, string> = {
  happy: '开心',
  laugh: '大笑',
  cheer: '庆祝',
  tease: '调侃',
  ok: '收到',
  thinking: '思考',
  confused: '疑惑',
  deadpan: '无语',
  awkward: '尴尬',
  comfort: '安慰',
  tired: '疲惫',
  sleepy: '犯困',
  work: '工作',
  annoyed: '嫌弃',
  angry: '生气',
  refuse: '拒绝',
  panic: '慌张',
  plead: '拜托',
  shy: '害羞',
  cute: '可爱',
  silent: '沉默',
  proud: '得意',
  surprised: '震惊',
  sad: '难过',
  unclear: '待确认'
}
export const stickerCorrectionMoods = Object.entries(stickerMoodLabels)

export function stickerClipLabel(item: StickerRecord): string {
  const score = item.clipConfidence > 0 ? item.clipConfidence.toFixed(2) : '--'
  return `图像识别 ${item.clipMoodLabel || stickerMoodLabel(item.clipMood)} ${score}`
}

const finalProactiveStatuses = new Set([
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

export function applyProactiveInbox(current: AppState, value: unknown): AppState {
  const payload = asRecord(value)
  const proactiveInbox = Array.isArray(value) ? value : Array.isArray(payload.items) ? payload.items : []
  const proactiveHistory = Array.isArray(payload.history) ? payload.history : current.proactiveHistory
  const activeCandidateIds = new Set(proactiveInbox.map((item) => String(asRecord(item).candidateId || '')).filter(Boolean))
  const proactiveActions = Object.fromEntries(
    Object.entries(current.proactiveActions).filter(([candidateId]) => activeCandidateIds.has(candidateId))
  ) as Record<string, ProactiveAction>

  return {
    ...current,
    proactiveActions,
    proactiveInbox,
    proactiveHistory
  }
}

export function applySnapshot(current: AppState, value: unknown): AppState {
  const snapshot = asRecord(value) as Snapshot
  const proactiveInbox = Array.isArray(snapshot.proactiveInbox) ? snapshot.proactiveInbox : []
  const proactiveHistory = Array.isArray(snapshot.proactiveHistory) ? snapshot.proactiveHistory : current.proactiveHistory
  const activeCandidateIds = new Set(proactiveInbox.map((item) => String(asRecord(item).candidateId || '')).filter(Boolean))
  const proactiveActions = Object.fromEntries(
    Object.entries(current.proactiveActions).filter(([candidateId]) => activeCandidateIds.has(candidateId))
  ) as Record<string, ProactiveAction>

  return {
    ...current,
    snapshot,
    proactiveActions,
    proactiveInbox,
    proactiveHistory,
    recentTurns: Array.isArray(snapshot.recentTurns) ? snapshot.recentTurns : [],
    recentMemoryEvents: Array.isArray(snapshot.recentMemoryEvents) ? snapshot.recentMemoryEvents : []
  }
}

export function applyEvent(current: AppState, value: unknown): AppState {
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
      return updateCommand(next, commandId, 'started', '核心正在回应', String(payload.turnId || ''))
    }
  } else if (event.type === 'chat.turn.finished') {
    next.recentTurns = appendLimited(current.recentTurns, payload, 'turnId')
    const commandId = String(payload.commandId || '')
    if (commandId) {
      return updateCommand(next, commandId, 'finished', '核心已回应', String(payload.turnId || ''))
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
      next.proactiveHistory = appendLimited(current.proactiveHistory, payload, 'candidateId')
      next.proactiveInbox = current.proactiveInbox.filter((item) => String(asRecord(item).candidateId || '') !== candidateId)
    } else {
      next.proactiveInbox = upsertByKey(current.proactiveInbox, payload, 'candidateId')
    }
  }

  return next
}

export function updateCommand(
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

export function deriveXinYuState(state: AppState): XinYuState {
  const backendState = asRecord(state.snapshot?.xinyuState)
  const backendConcerns = Array.isArray(backendState.recent_concerns)
    ? backendState.recent_concerns.map((item) => String(item || '')).filter(Boolean)
    : []
  const connection = state.gateway?.connected ? 'online' : state.gateway?.connecting ? 'connecting' : 'offline'
  const latestTurn = asRecord(state.recentTurns[state.recentTurns.length - 1])
  const latestIntent = asRecord(state.proactiveInbox[state.proactiveInbox.length - 1])
  const activeCommand = state.commands.find((command) => ['sending', 'accepted', 'started'].includes(command.status))
  const lastEvent = state.events[0]
  const hasIntent = state.proactiveInbox.length > 0
  const waitingReply = Boolean(backendState.is_waiting_for_reply) || hasIntent || Boolean(activeCommand)

  const fallbackMood =
    connection === 'offline'
      ? '核心未连接'
      : activeCommand
        ? '正在回应'
        : hasIntent
          ? '想找你'
          : '安静在场'
  const moodLabel = String(backendState.mood_tag || fallbackMood)
  const physicalSensation = compact(String(backendState.physical_sensation || '体感未校准'), 64)
  const actionResidueLabel = compact(String(backendState.action_residue_label || '暂无行动沉淀'), 64)
  const creativeProject = String(backendState.creative_writing_project || '')
  const creativeToday = numberValue(backendState.creative_writing_today_chapters, 0)
  const creativeTarget = numberValue(backendState.creative_writing_daily_target, 0)
  const creativeTotal = numberValue(backendState.creative_writing_total_chapters, 0)
  const creativePublishReady = numberValue(backendState.creative_writing_publish_ready_chapters, 0)
  const creativeMinPlatformChars = numberValue(backendState.creative_writing_min_platform_chars, 0)
  const creativeStatus = String(backendState.creative_writing_status || '')
  const creativeMode = String(backendState.creative_writing_mode || 'novel_mode')
  const creativeReferenceStatus = String(backendState.creative_writing_reference_status || '')
  const creativeReferenceSources = numberValue(backendState.creative_writing_reference_sources, 0)
  const creativeReferenceDownloads = numberValue(backendState.creative_writing_reference_downloads, 0)
  const creativeReferenceLocalFiles = numberValue(backendState.creative_writing_reference_local_files, 0)
  const creativeModeLabel = creativeMode === 'creative_engineering_mode' ? '创作工程' : '小说模式'
  const creativeStatusLabel =
    creativeStatus === 'complete' ? '今日完成' : creativeStatus === 'planning' ? '规划中' : '写作中'
  const creativeReferenceLabel =
    creativeReferenceStatus === 'collected' ? '资料已采集' : creativeReferenceStatus === 'no_sources' ? '暂无资料源' : ''
  const creativeLine =
    creativeTarget > 0
      ? compact(
          `${creativeModeLabel} · ${creativeProject || '小说写作'} ${creativeToday}/${creativeTarget} 章 · ${
            creativeStatusLabel
          } · 发布稿 ${creativePublishReady}/${creativeTotal} · ${creativeMinPlatformChars || 3200}+ 字`,
          72
        )
      : ''
  const creativeReferenceLine = creativeReferenceLabel
    ? compact(
        `参考层 ${creativeReferenceLabel} · ${creativeReferenceSources} 源 · 本地 ${creativeReferenceLocalFiles} 本 · 下载 ${creativeReferenceDownloads} · 仅安全摘要`,
        72
      )
    : ''

  const moodScore = connection === 'offline' ? 18 : connection === 'connecting' ? 42 : activeCommand ? 72 : hasIntent ? 84 : 62
  const attentionFocus = compact(
    String(
      backendState.current_attention ||
        latestIntent.focusLabel ||
        latestIntent.kind ||
        activeCommand?.textPreview ||
        latestTurn.textPreview ||
        latestTurn.replyPreview ||
        '等待新的生活信号'
    ),
    72
  )
  const recentConcern = compact(
    String(
      backendConcerns[0] ||
        latestIntent.candidatePreview ||
        latestIntent.whyNowPreview ||
        latestTurn.replyPreview ||
        latestTurn.textPreview ||
        '还没有从核心拿到最近牵挂'
    ),
    92
  )
  const waitingReason = hasIntent
    ? `${state.proactiveInbox.length} 个主动意图等待你处理`
    : activeCommand
      ? '你的上一句话正在进入核心'
      : '没有卡住的主动动作'

  const continuity = waitingReply
    ? '有未完成点'
    : latestTurn.turnId
      ? '停在上一轮对话'
      : lastEvent
        ? '停在事件流'
        : '等待开始'

  const evidence = [
    connection === 'online' ? '核心连接正常' : connection === 'connecting' ? '正在重连核心' : '桌面端暂未接上核心',
    physicalSensation,
    actionResidueLabel,
    ...(creativeLine ? [creativeLine] : []),
    ...(creativeReferenceLine ? [creativeReferenceLine] : []),
    `${state.recentMemoryEvents.length} 次记忆回声`,
    lastEvent ? eventLabel(lastEvent.type) : '暂无事件流'
  ]

  return {
    connection,
    moodLabel,
    moodScore,
    attentionFocus,
    recentConcern,
    waitingReply,
    waitingReason,
    continuity,
    lastShiftAt: state.snapshot?.snapshotAt || state.gateway?.snapshotAt || '',
    evidence,
    physicalSensation
  }
}

export function buildProactiveIntents(items: unknown[]): ProactiveIntent[] {
  return items
    .slice()
    .reverse()
    .map((item, index) => {
      const row = asRecord(item)
      const id = String(row.candidateId || row.id || `intent-${index}`)
      const delivery = deliveryLabel(String(row.deliveryLevel || row.delivery || 'local'))
      const risk = intentRisk(row)
      const trigger = proactiveTextLabel(String(row.focusLabel || row.title || row.focusKind || row.kind || '主动提醒'))
      const plannedText = proactiveTextLabel(String(row.candidatePreview || row.message || row.text || '等待核心补全内容'))
      const fullText = proactiveTextLabel(String(row.candidatePreview || row.message || row.text || row.concreteQuestion || ''))
      const reasonText = proactiveTextLabel(String(row.reason || row.whyNowPreview || ''))
      return {
        id,
        source: proactiveTextLabel(String(row.source || row.sourceType || row.origin || 'initiative')),
        trigger: compact(trigger, 54),
        plannedText: compact(plannedText, 170),
        fullText,
        reasonText,
        risk,
        riskLabel: riskLabel(risk),
        delivery,
        claimable: Boolean(row.claimable),
        status: String(row.status || ''),
        requestFamily: proactiveTextLabel(String(row.requestFamily || '')),
        requestedAction: proactiveTextLabel(String(row.requestedAction || '')),
        desktopAction: String(row.desktopAction || ''),
        evidenceHash: String(row.evidenceHash || ''),
        createdAt: String(row.createdAt || ''),
        expiresAt: String(row.expiresAt || ''),
        updatedAt: String(row.updatedAt || row.handledAt || '')
      }
    })
}

export function intentRisk(row: JsonRecord): ProactiveIntent['risk'] {
  const status = String(row.status || '')
  const delivery = String(row.deliveryLevel || row.delivery || '')
  const privacy = String(row.privacy || 'owner_private')
  if (status === 'blocked' || status === 'failed') {
    return 'blocked'
  }
  if (privacy !== 'owner_private' || delivery.includes('qq') || delivery.includes('claim')) {
    return 'review'
  }
  return 'low'
}

export function buildStats(state: AppState): {
  turns: number
  memories: number
  proactive: number
  events: number
} {
  return {
    turns: state.recentTurns.length,
    memories: state.recentMemoryEvents.length,
    proactive: state.proactiveInbox.length,
    events: state.events.length
  }
}

export function normalizeMemoryGrowthCandidates(value: unknown): GrowthCandidatePromotionStatus {
  const data = asRecord(value)
  return {
    ok: Boolean(data.ok),
    pendingApplyCount: Number(data.pendingApplyCount ?? data.pending_apply_count ?? 0),
    appliedCount: Number(data.appliedCount ?? data.applied_count ?? 0),
    ownerReviewRequiredCount: Number(data.ownerReviewRequiredCount ?? data.owner_review_required_count ?? 0),
    pendingApply: Array.isArray(data.pendingApply)
      ? data.pendingApply.map(normalizeGrowthCandidatePromotionItem)
      : Array.isArray(data.pending_apply)
        ? data.pending_apply.map(normalizeGrowthCandidatePromotionItem)
        : [],
    applied: Array.isArray(data.applied) ? data.applied.map(normalizeGrowthCandidatePromotionItem) : [],
    ownerReviewRequired: Array.isArray(data.ownerReviewRequired)
      ? data.ownerReviewRequired.map(normalizeGrowthCandidatePromotionItem)
      : Array.isArray(data.owner_review_required)
        ? data.owner_review_required.map(normalizeGrowthCandidatePromotionItem)
        : [],
    targetPath: String(data.targetPath || data.target_path || ''),
    targetMemoryLayer: String(data.targetMemoryLayer || data.target_memory_layer || ''),
    notes: stringArray(data.notes),
    error: String(data.error || '')
  }
}

function normalizeKernelReviewItem(value: unknown): KernelReviewItem {
  const row = asRecord(value)
  return {
    domain: String(row.domain || ''),
    itemId: String(row.item_id || row.itemId || ''),
    contentPreview: String(row.content_preview || row.contentPreview || ''),
    reviewStatus: String(row.review_status || row.reviewStatus || ''),
    confidence: typeof row.confidence === 'number' ? row.confidence : undefined,
    actionType: row.action_type ? String(row.action_type) : row.actionType ? String(row.actionType) : undefined,
    sourceEventId: row.source_event_id ? String(row.source_event_id) : row.sourceEventId ? String(row.sourceEventId) : undefined
  }
}

export function normalizeKernelGovernance(value: unknown): KernelGovernanceStatus {
  const data = asRecord(value)
  return {
    ok: Boolean(data.ok),
    available: Boolean(data.available),
    loadedAt: String(data.loadedAt || ''),
    selfId: String(data.self_id || data.selfId || ''),
    error: String(data.error || ''),
    pendingCount: numberValue(data.pending_count ?? data.pendingCount, 0),
    worldModelCount: numberValue(data.world_model_count ?? data.worldModelCount, 0),
    reorganizationCount: numberValue(data.reorganization_count ?? data.reorganizationCount, 0),
    beliefCount: numberValue(data.belief_count ?? data.beliefCount, 0),
    followupCount: numberValue(data.followup_count ?? data.followupCount, 0),
    writesBlocked: Boolean(data.writes_blocked ?? data.writesBlocked),
    items: Array.isArray(data.items) ? data.items.map(normalizeKernelReviewItem) : [],
    cycleCount: numberValue(data.cycle_count ?? data.cycleCount, 0),
    slowSignalCount: numberValue(data.slow_signal_count ?? data.slowSignalCount, 0),
    slowEscalationThreshold: numberValue(data.slow_escalation_threshold ?? data.slowEscalationThreshold, 3),
    reorgRecommendation: String(data.reorg_recommendation || data.reorgRecommendation || ''),
    selfStorySummary: String(data.self_story_summary || data.selfStorySummary || ''),
    grantedScopes: Array.isArray(data.granted_scopes)
      ? data.granted_scopes.map((scope) => String(scope))
      : Array.isArray(data.grantedScopes)
        ? data.grantedScopes.map((scope) => String(scope))
        : [],
    grantableScopes: Array.isArray(data.grantable_scopes)
      ? data.grantable_scopes.map((scope) => String(scope))
      : Array.isArray(data.grantableScopes)
        ? data.grantableScopes.map((scope) => String(scope))
        : []
  }
}

export function normalizeStage8MemoryGovernance(value: unknown): Stage8MemoryGovernanceStatus {
  const data = asRecord(value)
  return {
    ok: Boolean(data.ok),
    loadedAt: String(data.loadedAt || ''),
    updatedAt: String(data.updatedAt || ''),
    status: String(data.status || 'missing'),
    readyForStage9: Boolean(data.readyForStage9),
    reason: String(data.reason || ''),
    nextStep: String(data.nextStep || ''),
    stage7ReadyForStage8: Boolean(data.stage7ReadyForStage8),
    stage7Reason: String(data.stage7Reason || ''),
    candidateTotal: numberValue(data.candidateTotal, 0),
    ownerReviewRequiredCount: numberValue(data.ownerReviewRequiredCount, 0),
    privateOrOwnerScopedCount: numberValue(data.privateOrOwnerScopedCount, 0),
    duplicateClusterCount: numberValue(data.duplicateClusterCount, 0),
    learningTrialSuccessGate: String(data.learningTrialSuccessGate || ''),
    stableProfileWrite: String(data.stableProfileWrite || ''),
    ownerMemoryWrite: String(data.ownerMemoryWrite || ''),
    ownerReviewCandidateText: String(data.ownerReviewCandidateText || ''),
    stablePersonalityWrite: String(data.stablePersonalityWrite || ''),
    growthApplyMode: String(data.growthApplyMode || ''),
    stableIdentityProfileApply: String(data.stableIdentityProfileApply || ''),
    packetStatus: String(data.packetStatus || ''),
    packetPath: String(data.packetPath || ''),
    duplicateClusters: Array.isArray(data.duplicateClusters) ? data.duplicateClusters.map(normalizeStage8DuplicateCluster) : [],
    blockedGates: Array.isArray(data.blockedGates) ? data.blockedGates.map(normalizeStage8BlockedGate) : [],
    reviewInboxPendingCount: numberValue(data.reviewInboxPendingCount, 0),
    reviewInboxProcessedCount: numberValue(data.reviewInboxProcessedCount, 0),
    latestDecision: data.latestDecision ? normalizeStage8ReviewDecision(data.latestDecision) : null,
    latestDryRun: data.latestDryRun ? normalizeStage8PromotionDryRun(data.latestDryRun) : null,
    boundaries: normalizeStage8Boundaries(data.boundaries)
  }
}

function normalizeStage8DuplicateCluster(value: unknown): Stage8DuplicateCluster {
  const row = asRecord(value)
  return {
    topic: String(row.topic || ''),
    size: numberValue(row.size, 0),
    conflicts: numberValue(row.conflicts, 0),
    privateOrHiddenSamples: numberValue(row.privateOrHiddenSamples, 0),
    recommendation: String(row.recommendation || ''),
    statuses: asRecord(row.statuses)
  }
}

function normalizeStage8BlockedGate(value: unknown): Stage8BlockedGate {
  const row = asRecord(value)
  return {
    gate: String(row.gate || ''),
    status: String(row.status || ''),
    count: numberValue(row.count, 0),
    reason: String(row.reason || '')
  }
}

function normalizeStage8ReviewDecision(value: unknown): Stage8ReviewDecision {
  const row = asRecord(value)
  return {
    actionKind: String(row.actionKind || ''),
    command: String(row.command || ''),
    decidedAt: String(row.decidedAt || ''),
    decision: String(row.decision || ''),
    decisionId: String(row.decisionId || ''),
    itemId: String(row.itemId || ''),
    recordKey: String(row.recordKey || '')
  }
}

function normalizeStage8PromotionDryRun(value: unknown): Stage8PromotionDryRun {
  const row = asRecord(value)
  return {
    candidateId: String(row.candidateId || ''),
    status: String(row.status || ''),
    candidateType: String(row.candidateType || ''),
    targetMemoryLayer: String(row.targetMemoryLayer || ''),
    stableMemoryWrite: String(row.stableMemoryWrite || ''),
    applyAllowed: Boolean(row.applyAllowed),
    blockers: stringArray(row.blockers)
  }
}

function normalizeStage8Boundaries(value: unknown): Stage8MemoryGovernanceStatus['boundaries'] {
  const row = asRecord(value)
  return {
    rawOwnerTextInPacket: Boolean(row.rawOwnerTextInPacket),
    visibleReplyTextInPacket: Boolean(row.visibleReplyTextInPacket),
    candidateBodyInPacket: Boolean(row.candidateBodyInPacket),
    stableMemoryWrite: String(row.stableMemoryWrite || ''),
    consciousnessClaim: Boolean(row.consciousnessClaim)
  }
}

function normalizeGrowthCandidatePromotionItem(value: unknown): GrowthCandidatePromotionItem {
  const row = asRecord(value)
  return {
    candidateId: String(row.candidateId || row.candidate_id || ''),
    status: String(row.status || ''),
    candidateType: String(row.candidateType || row.candidate_type || ''),
    targetMemoryLayer: String(row.targetMemoryLayer || row.target_memory_layer || ''),
    targetPath: String(row.targetPath || row.target_path || ''),
    targetGate: String(row.targetGate || row.target_gate || ''),
    beforeHash: String(row.beforeHash || row.before_hash || ''),
    applyCommand: String(row.applyCommand || row.apply_command || ''),
    previewPath: String(row.previewPath || row.preview_path || ''),
    blockers: stringArray(row.blockers),
    riskFlags: stringArray(row.riskFlags || row.risk_flags),
    applyAllowed: Boolean(row.applyAllowed ?? row.apply_allowed),
    stableMemoryWrite: String(row.stableMemoryWrite || row.stable_memory_write || ''),
    stablePersonalityWrite: String(row.stablePersonalityWrite || row.stable_personality_write || ''),
    reasonPreview: String(row.reasonPreview || row.reason_preview || ''),
    candidateTextPreview: String(row.candidateTextPreview || row.candidate_text_preview || '')
  }
}

export function normalizeStickerLibrary(value: unknown): StickerLibrary {
  const data = asRecord(value)
  const countsRaw = asRecord(data.counts)
  const counts = Object.fromEntries(
    Object.entries(countsRaw).map(([key, count]) => [key, Number(count || 0)])
  ) as Record<string, number>
  const items = Array.isArray(data.items)
    ? data.items.map((item) => {
        const row = asRecord(item)
        return {
          file: String(row.file || ''),
          mood: String(row.mood || ''),
          moodLabel: String(row.moodLabel || stickerMoodLabel(row.mood)),
          ocrText: String(row.ocrText || ''),
          clipMood: String(row.clipMood || ''),
          clipMoodLabel: String(row.clipMoodLabel || stickerMoodLabel(row.clipMood)),
          clipConfidence: Number(row.clipConfidence || 0),
          confirmed: Boolean(row.confirmed),
          autoSend: Boolean(row.autoSend),
          weight: Number(row.weight || 1)
        }
      })
    : []
  return {
    assetDir: String(data.assetDir || ''),
    updatedAt: String(data.updatedAt || ''),
    total: Number(data.total || 0),
    moods: Array.isArray(data.moods) ? data.moods.map((item) => String(item || '')).filter(Boolean) : [],
    counts,
    unclear: Number(data.unclear || 0),
    confirmed: Number(data.confirmed || 0),
    unconfirmed: Number(data.unconfirmed || 0),
    ocr: Number(data.ocr || 0),
    autoSend: Number(data.autoSend || 0),
    corrections: Number(data.corrections || 0),
    referenceItems: Number(data.referenceItems || 0),
    items
  }
}

export function normalizeExternalPluginsStatus(value: unknown): ExternalPluginsStatus {
  const data = asRecord(value)
  const plugins = Array.isArray(data.plugins) ? data.plugins.map(normalizeExternalPluginControl) : []
  return {
    ok: Boolean(data.ok ?? true),
    protocol: String(data.protocol || 'xinyu.external.v1'),
    configPath: String(data.configPath || data.config_path || ''),
    plugins,
    notes: stringArray(data.notes)
  }
}

function normalizeExternalPluginControl(value: unknown): ExternalPluginControl {
  const row = asRecord(value)
  const install = normalizeExternalPluginInstall(row.install)
  const config = asRecord(row.config)
  return {
    pluginId: String(row.pluginId || row.plugin_id || ''),
    title: String(row.title || row.pluginId || row.plugin_id || ''),
    kind: String(row.kind || ''),
    transport: String(row.transport || ''),
    enabled: Boolean(row.enabled),
    proactiveEnabled: Boolean(row.proactiveEnabled ?? row.proactive_enabled),
    installed: Boolean(row.installed ?? install.installed),
    installable: Boolean(row.installable ?? install.installable),
    available: Boolean(row.available ?? (Boolean(row.enabled) && Boolean(row.installed))),
    config,
    install,
    notes: stringArray(row.notes)
  }
}

function normalizeExternalPluginInstall(value: unknown): ExternalPluginInstallState {
  const row = asRecord(value)
  return {
    installed: Boolean(row.installed),
    installable: Boolean(row.installable),
    path: String(row.path || row.installPath || ''),
    installer: String(row.installer || ''),
    missingReason: String(row.missingReason || row.missing_reason || '')
  }
}

export function normalizeApiConfigStatus(value: unknown): ApiConfigStatus {
  const data = asRecord(value)
  const currentRaw = asRecord(data.current)
  const current: ApiConfigCurrent = {
    configPath: String(currentRaw.configPath || data.configPath || ''),
    llm: normalizeApiConfigLlm(currentRaw.llm || currentRaw),
    vision: normalizeApiConfigVision(currentRaw.vision),
    hearing: normalizeApiConfigHearing(currentRaw.hearing),
    tts: normalizeApiConfigTts(currentRaw.tts),
    other: normalizeApiConfigOther(currentRaw.other)
  }
  const profiles = Array.isArray(data.profiles) ? data.profiles.map(normalizeApiConfigProfile) : []
  return {
    ok: Boolean(data.ok ?? true),
    loadedAt: String(data.loadedAt || ''),
    configPath: String(data.configPath || current.configPath || ''),
    profilesPath: String(data.profilesPath || ''),
    activeProfileId: String(data.activeProfileId || ''),
    current,
    profiles,
    notes: stringArray(data.notes)
  }
}

function normalizeApiConfigProfile(value: unknown): ApiConfigProfile {
  const row = asRecord(value)
  return {
    id: String(row.id || ''),
    label: String(row.label || '本地 API'),
    llm: normalizeApiConfigLlm(row.llm || row),
    vision: normalizeApiConfigVision(row.vision),
    hearing: normalizeApiConfigHearing(row.hearing),
    tts: normalizeApiConfigTts(row.tts),
    other: normalizeApiConfigOther(row.other),
    updatedAt: String(row.updatedAt || ''),
    active: Boolean(row.active)
  }
}

function normalizeApiConfigLlm(value: unknown) {
  const row = asRecord(value)
  return {
    provider: String(row.provider || 'ciallo'),
    model: String(row.model || 'mimo-v2.5-pro'),
    baseUrl: String(row.baseUrl || ''),
    allowInsecureHttp: Boolean(row.allowInsecureHttp),
    disableStreaming: row.disableStreaming !== false,
    hasApiKey: Boolean(row.hasApiKey),
    apiKeyPreview: String(row.apiKeyPreview || '')
  }
}

function normalizeApiConfigVision(value: unknown) {
  const row = asRecord(value)
  return {
    enabled: Boolean(row.enabled),
    model: String(row.model || 'gpt-4o-mini'),
    baseUrl: String(row.baseUrl || ''),
    timeoutSeconds: numberValue(row.timeoutSeconds, 45),
    maxBytes: numberValue(row.maxBytes, 4 * 1024 * 1024),
    hasApiKey: Boolean(row.hasApiKey),
    apiKeyPreview: String(row.apiKeyPreview || '')
  }
}

function normalizeApiConfigHearing(value: unknown) {
  const row = asRecord(value)
  return {
    enabled: row.enabled !== false,
    command: String(row.command || ''),
    model: String(row.model || 'whisper-1'),
    baseUrl: String(row.baseUrl || ''),
    language: String(row.language || 'zh'),
    timeoutSeconds: numberValue(row.timeoutSeconds, 120),
    recordFormat: String(row.recordFormat || 'mp3'),
    hasApiKey: Boolean(row.hasApiKey),
    apiKeyPreview: String(row.apiKeyPreview || '')
  }
}

function normalizeApiConfigTts(value: unknown) {
  const row = asRecord(value)
  return {
    enabled: Boolean(row.enabled),
    engine: String(row.engine || 'current'),
    model: String(row.model || 'mimo-v2.5-tts'),
    baseUrl: String(row.baseUrl || ''),
    voice: String(row.voice || 'mimo_default'),
    format: String(row.format || 'wav'),
    requestMode: String(row.requestMode || 'auto'),
    timeoutSeconds: numberValue(row.timeoutSeconds, 60),
    genieBaseUrl: String(row.genieBaseUrl || 'http://127.0.0.1:8000'),
    genieCharacter: String(row.genieCharacter || 'feibi'),
    genieSplitSentence: Boolean(row.genieSplitSentence),
    genieSampleRate: numberValue(row.genieSampleRate, 32000),
    genieChannels: numberValue(row.genieChannels, 1),
    genieSampleWidth: numberValue(row.genieSampleWidth, 2),
    hasApiKey: Boolean(row.hasApiKey),
    apiKeyPreview: String(row.apiKeyPreview || '')
  }
}

function normalizeApiConfigOther(value: unknown) {
  const row = asRecord(value)
  return {
    hasOpenAIApiKey: Boolean(row.hasOpenAIApiKey),
    openAIApiKeyPreview: String(row.openAIApiKeyPreview || '')
  }
}

export function defaultQQRuntimeConfig(): QQRuntimeConfig {
  return {
    configPath: '',
    loadedAt: '',
    requireWhitelist: true,
    allowExternalPrivate: false,
    allowGroupMessages: false,
    allowedGroupIds: [],
    groupTriggerMode: 'mention_or_prefix',
    groupShadowEnabled: false,
    groupShadowAllowedGroupIds: [],
    groupShadowMaxTextChars: 260,
    blockedUserIds: [],
    blockedGroupIds: [],
    sendReplies: true,
    ownerUserIds: [],
    whitelistUserIds: [],
    trustedUserIds: [],
    notes: []
  }
}

export function normalizeAsyncExplorationState(value: unknown): AsyncExplorationState {
  const d = asRecord(value)
  return {
    ok: Boolean(d.ok),
    loadedAt: String(d.loadedAt || ''),
    updatedAt: String(d.updatedAt || ''),
    status: String(d.status || 'missing'),
    resumeId: String(d.resumeId || ''),
    sessionKey: String(d.sessionKey || ''),
    delegationReason: String(d.delegationReason || ''),
    taskSummary: String(d.taskSummary || ''),
    failureKind: String(d.failureKind || ''),
    resultQuality: String(d.resultQuality || ''),
    ownerIntervention: String(d.ownerIntervention || ''),
    ownerVisibleResumeHint: String(d.ownerVisibleResumeHint || ''),
  }
}

export function normalizeStage12GateStatus(value: unknown): Stage12GateStatus {
  const d = asRecord(value)
  return {
    ok: Boolean(d.ok),
    loadedAt: String(d.loadedAt || ''),
    updatedAt: String(d.updatedAt || ''),
    status: String(d.status || 'missing'),
    readyForStage13: Boolean(d.readyForStage13),
    reason: String(d.reason || ''),
    liveLoopStatus: String(d.liveLoopStatus || 'missing'),
    liveLoopPassRatePct: Number(d.liveLoopPassRatePct || 0),
    liveLoopPassedCount: Number(d.liveLoopPassedCount || 0),
    liveLoopRequiredCount: Number(d.liveLoopRequiredCount || 0),
    liveLoopFailingChecks: String(d.liveLoopFailingChecks || ''),
    liveLoopFailingDetail: String(d.liveLoopFailingDetail || ''),
    gateStage11Ready: Boolean(d.gateStage11Ready),
    gateLiveLoopPass: Boolean(d.gateLiveLoopPass),
    gateFeedbackClean: Boolean(d.gateFeedbackClean),
    gatePrivacyClean: Boolean(d.gatePrivacyClean),
    gateStableClean: Boolean(d.gateStableClean),
    gateCanaryReady: Boolean(d.gateCanaryReady),
    gateShortTermClean: Boolean(d.gateShortTermClean),
    nextStep: String(d.nextStep || ''),
  }
}

export function normalizeStage13GateStatus(value: unknown): Stage13GateStatus {
  const d = asRecord(value)
  return {
    ok: Boolean(d.ok),
    loadedAt: String(d.loadedAt || ''),
    updatedAt: String(d.updatedAt || ''),
    status: String(d.status || 'missing'),
    available: Boolean(d.available),
    reason: String(d.reason || ''),
    stage12ReadyForStage13: Boolean(d.stage12ReadyForStage13),
    behaviorMode: String(d.behaviorMode || ''),
    selectedIntent: String(d.selectedIntent || ''),
    behaviorGate: String(d.behaviorGate || ''),
    memoryGovernanceStatus: String(d.memoryGovernanceStatus || ''),
    nextStep: String(d.nextStep || ''),
  }
}

export function normalizeQQRuntimeConfig(value: unknown): QQRuntimeConfig {
  const data = asRecord(value)
  const fallback = defaultQQRuntimeConfig()
  return {
    configPath: String(data.configPath || fallback.configPath),
    loadedAt: String(data.loadedAt || fallback.loadedAt),
    requireWhitelist: Boolean(data.requireWhitelist ?? fallback.requireWhitelist),
    allowExternalPrivate: Boolean(data.allowExternalPrivate ?? fallback.allowExternalPrivate),
    allowGroupMessages: Boolean(data.allowGroupMessages ?? fallback.allowGroupMessages),
    allowedGroupIds: stringArray(data.allowedGroupIds),
    groupTriggerMode: String(data.groupTriggerMode || fallback.groupTriggerMode),
    groupShadowEnabled: Boolean(data.groupShadowEnabled ?? fallback.groupShadowEnabled),
    groupShadowAllowedGroupIds: stringArray(data.groupShadowAllowedGroupIds),
    groupShadowMaxTextChars: Number(data.groupShadowMaxTextChars || fallback.groupShadowMaxTextChars),
    blockedUserIds: stringArray(data.blockedUserIds),
    blockedGroupIds: stringArray(data.blockedGroupIds),
    sendReplies: Boolean(data.sendReplies ?? fallback.sendReplies),
    ownerUserIds: stringArray(data.ownerUserIds),
    whitelistUserIds: stringArray(data.whitelistUserIds),
    trustedUserIds: stringArray(data.trustedUserIds),
    notes: stringArray(data.notes)
  }
}

export function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item || '').trim()).filter(Boolean) : []
}

export function appendLimited(items: unknown[], item: JsonRecord, key: string): unknown[] {
  const itemKey = String(item[key] || '')
  return [...items.filter((entry) => String(asRecord(entry)[key] || '') !== itemKey), item].slice(-100)
}

export function upsertByKey(items: unknown[], item: JsonRecord, key: string): unknown[] {
  const itemKey = String(item[key] || '')
  if (!itemKey) return items
  return [...items.filter((entry) => String(asRecord(entry)[key] || '') !== itemKey), item]
}

export function isCommandRenderedByTurn(command: CommandState, commandIds: Set<string>, turnIds: Set<string>): boolean {
  return commandIds.has(command.commandId) || Boolean(command.turnId && turnIds.has(command.turnId))
}

export function asRecord(value: unknown): JsonRecord {
  return value && typeof value === 'object' ? (value as JsonRecord) : {}
}

export function defaultQQServices(): ServiceProbe[] {
  return [
    normalizeServiceProbe({ key: 'coreBridge', detail: 'pending' }),
    normalizeServiceProbe({ key: 'qqGateway', detail: 'pending' }),
    normalizeServiceProbe({ key: 'napcatWebui', detail: 'pending' }),
    normalizeServiceProbe({ key: 'napcatReverseWs', detail: 'pending' })
  ]
}

export function normalizeQQEnvironmentStatus(value: unknown): QQEnvironmentStatus {
  const status = asRecord(value)
  const services = Array.isArray(status.services)
    ? status.services.map((service) => normalizeServiceProbe(service))
    : defaultQQServices()
  const allReady = services.length > 0 && services.every((service) => service.ok)
  return {
    checkedAt: String(status.checkedAt || ''),
    allReady,
    webuiUrl: String(status.webuiUrl || 'http://127.0.0.1:6099/webui/'),
    webuiLoginUrl: String(status.webuiLoginUrl || 'http://127.0.0.1:6099/webui/web_login'),
    tokenAvailable: Boolean(status.tokenAvailable),
    napcatQQLoggedIn: typeof status.napcatQQLoggedIn === 'boolean' ? status.napcatQQLoggedIn : null,
    diagnosis: String(status.diagnosis || ''),
    services,
    lastError: String(status.lastError || '')
  }
}

export function normalizeImpulseSoupState(value: unknown): ImpulseSoupState {
  const raw = asRecord(value)
  const summary = asRecord(raw.summary)
  const thoughtlets = Array.isArray(raw.thoughtlets) ? raw.thoughtlets.map(normalizeImpulseThoughtlet) : []
  const traceTail = Array.isArray(raw.traceTail) ? raw.traceTail.map(normalizeImpulseTraceEvent) : []
  return {
    ok: Boolean(raw.ok),
    loadedAt: String(raw.loadedAt || ''),
    updatedAt: String(raw.updatedAt || ''),
    status: String(raw.status || 'missing'),
    schemaVersion: String(raw.schemaVersion || ''),
    statePath: String(raw.statePath || ''),
    markdownPath: String(raw.markdownPath || ''),
    tracePath: String(raw.tracePath || ''),
    thoughtletCount: numberValue(summary.thoughtlet_count, thoughtlets.length),
    activeCount: numberValue(summary.active_count, 0),
    dormantCount: numberValue(summary.dormant_count, 0),
    quarantinedCount: numberValue(summary.quarantined_count, 0),
    extinctCount: numberValue(summary.extinct_count, 0),
    lineageCount: numberValue(summary.lineage_count, 0),
    softActiveCount: numberValue(summary.soft_active_count, 0),
    topThoughtletId: String(summary.top_thoughtlet_id || 'none'),
    topDesireShape: String(summary.top_desire_shape || 'none'),
    topEnergy: numberValue(summary.top_energy, 0),
    topAction: String(summary.top_action || 'none'),
    outwardActionAllowed: Boolean(summary.outward_action_allowed),
    thoughtlets,
    traceTail
  }
}

function normalizeImpulseThoughtlet(value: unknown): ImpulseThoughtlet {
  const row = asRecord(value)
  const riskFlags = Array.isArray(row.risk_flags) ? row.risk_flags.map((item) => String(item || '')).filter(Boolean) : []
  return {
    thoughtletId: String(row.thoughtlet_id || ''),
    lineageId: String(row.lineage_id || ''),
    parentId: String(row.parent_id || 'none'),
    generation: numberValue(row.generation, 0),
    sourceKind: String(row.source_kind || 'unknown'),
    sourceRef: String(row.source_ref || ''),
    desireShape: String(row.desire_shape || 'none'),
    proposedNextAction: String(row.proposed_next_action || 'none'),
    inhibitionRule: String(row.inhibition_rule || 'none'),
    energy: numberValue(row.energy, 0),
    usefulnessScore: numberValue(row.usefulness_score, 0),
    mutationCount: numberValue(row.mutation_count, 0),
    activationCount: numberValue(row.activation_count, 0),
    status: String(row.status || 'unknown'),
    evidencePreview: String(row.evidence_preview || ''),
    riskFlags,
    updatedAt: String(row.updated_at || '')
  }
}

function normalizeImpulseTraceEvent(value: unknown): ImpulseTraceEvent {
  const row = asRecord(value)
  return {
    observedAt: String(row.observed_at || ''),
    status: String(row.status || 'unknown'),
    seedCount: numberValue(row.seed_count, 0),
    createdCount: numberValue(row.created_count, 0),
    updatedCount: numberValue(row.updated_count, 0),
    spawnedCount: numberValue(row.spawned_count, 0),
    activeCount: numberValue(row.active_count, 0),
    lineageCount: numberValue(row.lineage_count, 0),
    topDesireShape: String(row.top_desire_shape || 'none'),
    topEnergy: numberValue(row.top_energy, 0)
  }
}

function numberValue(value: unknown, fallback: number): number {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

export function normalizeServiceProbe(value: unknown): ServiceProbe {
  const row = asRecord(value)
  const key = serviceProbeKey(String(row.key || ''))
  return {
    key,
    label: String(row.label || defaultQQServiceLabel(key)),
    endpoint: String(row.endpoint || defaultQQServiceEndpoint(key)),
    ok: Boolean(row.ok),
    detail: String(row.detail || '')
  }
}

export function serviceProbeKey(value: string): ServiceProbe['key'] {
  if (value === 'qqGateway' || value === 'napcatWebui' || value === 'napcatReverseWs') {
    return value
  }
  return 'coreBridge'
}

export function defaultQQServiceLabel(key: ServiceProbe['key']): string {
  if (key === 'coreBridge') return '核心桥'
  if (key === 'qqGateway') return 'QQ 网关'
  if (key === 'napcatWebui') return 'NapCat 网页端'
  return 'NapCat 反向连接'
}

export function defaultQQServiceEndpoint(key: ServiceProbe['key']): string {
  if (key === 'coreBridge') return '127.0.0.1:8765'
  if (key === 'qqGateway') return '127.0.0.1:6199'
  if (key === 'napcatWebui') return '127.0.0.1:6099'
  return '127.0.0.1:6199/ws'
}

export function qqServiceLabel(service: ServiceProbe): string {
  return defaultQQServiceLabel(service.key) || service.label
}

export function qqDetailLabel(detail: string): string {
  if (detail === 'tcp_ready') return '端口可用'
  if (detail === 'ws_established') return '已接入'
  if (detail === 'ws_not_connected') return '未接入'
  if (detail === 'tcp_timeout') return '超时'
  if (detail === 'pending') return '未检查'
  if (detail.includes('ECONNREFUSED')) return '未启动'
  if (detail.includes('powershell_timeout')) return '检测超时'
  if (!detail) return '未知'
  return compact(detail, 26)
}

export function qqEnvironmentMessage(status: QQEnvironmentStatus): string {
  if (status.allReady) {
    return 'QQ 链路已就绪'
  }
  if (status.diagnosis) {
    return qqDiagnosisLabel(status.diagnosis, Boolean(status.tokenAvailable))
  }
  const broken = status.services?.find((service) => !service.ok)
  return broken ? `${qqServiceLabel(broken)} 未就绪` : 'QQ 状态已更新'
}

export function qqDiagnosisLabel(value: string, tokenAvailable: boolean): string {
  if (value === 'ready') return 'QQ 已接入'
  if (value === 'core_offline') return '核心未启动'
  if (value === 'gateway_offline') return 'QQ 网关未启动'
  if (value === 'napcat_offline') return 'NapCat 未启动'
  if (value === 'napcat_qq_login_required') return 'NapCat QQ 未登录'
  if (value === 'napcat_login_required') return tokenAvailable ? '需要网页端登录或确认 QQ 在线' : '需要登录 NapCat 网页端'
  if (value === 'napcat_ws_waiting') return '等待 NapCat 连接网关'
  if (value === 'partial') return '链路部分可用'
  return '正在读取 QQ 状态'
}

export function qqActionResultLabel(message: string, accepted: boolean, error?: unknown): string {
  const errorText = error ? `：${compact(String(error), 58)}` : ''
  if (!accepted) {
    if (message === 'start_script_missing') return `启动脚本缺失${errorText}`
    if (message === 'webui_open_failed') return `网页端打开失败${errorText}`
    if (message === 'webui_token_missing') return '未找到网页端口令'
    if (message === 'webui_token_invalid') return '网页端口令和运行中的 NapCat 不匹配，请重启 NapCat 后再试'
    if (message === 'start_failed') return `启动失败${errorText}`
    return `操作失败${errorText}`
  }
  if (message === 'start_requested') return '已提交 QQ 环境启动，请稍候刷新状态'
  if (message === 'napcat_started') return 'NapCat 已启动'
  if (message === 'webui_opened') return '已在桌面窗口打开 NapCat 网页端'
  if (message === 'webui_token_copied') return '网页端口令已复制'
  if (message === 'webui_token_missing') return '未找到网页端口令'
  return message || '操作已提交'
}

export function qqRuntimeResultLabel(message: string, accepted: boolean, error?: unknown): string {
  const errorText = error ? `：${compact(String(error), 58)}` : ''
  if (!accepted) {
    if (message === 'group_reply_scope_missing') return '群回复缺少群号范围'
    if (message === 'gateway_start_script_missing') return `网关脚本缺失${errorText}`
    if (message === 'gateway_restart_failed') return `网关重启失败${errorText}`
    if (message === 'runtime_config_saved_restart_failed') return `设置已写入，重启失败${errorText}`
    return `操作失败${errorText}`
  }
  if (message === 'runtime_config_applied') return '设置已应用，网关已重启'
  if (message === 'gateway_restarted') return 'QQ 网关已重启'
  return message || '设置已更新'
}

export function apiConfigActionLabel(message: string, accepted: boolean, error?: unknown): string {
  if (message === 'api_test_non_json_response') return 'API 返回的不是 JSON'
  if (message === 'api_test_empty_reply') return 'API 没有返回可用回复'
  const errorText = error ? `：${compact(String(error), 58)}` : ''
  if (accepted) {
    if (message === 'api_profile_saved') return 'API 资料已保存'
    if (message === 'api_profile_created') return 'API 资料已创建'
    if (message === 'api_test_ok') return 'API 测试通过'
    if (message === 'api_test_timeout') return 'API 测试超时'
    if (message === 'api_profile_deleted') return 'API 资料已删除'
    if (message === 'api_profile_applied') return 'API 资料已应用'
    if (message === 'api_profile_applied_core_restarted') return 'API 资料已应用，核心已重启'
    if (message === 'core_bridge_restarted') return '核心桥接已重启'
    return message || 'API 资料已更新'
  }
  if (message === 'missing_api_profile_id') return '缺少 API 资料 ID'
  if (message === 'missing_base_url') return '缺少基础地址'
  if (message === 'missing_model') return '缺少模型名称'
  if (message === 'missing_provider') return '缺少提供方'
  if (message === 'native_messages_provider_not_supported_by_core_runtime') {
    return '这个 Claude Messages 接口只能测试连通性，当前不能应用到主运行时'
  }
  if (message === 'unknown_provider_select_custom_openai_compatible_or_known_provider') {
    return '未知提供方：请选择已知提供方，或选择“自定义 OpenAI 兼容”'
  }
  if (message === 'api_test_failed') return `API 测试失败${errorText}`
  if (message === 'api_profile_not_found') return `未找到 API 资料${errorText}`
  if (message.startsWith('api_profile_not_found:')) return `未找到 API 资料：${compact(message.slice('api_profile_not_found:'.length), 36)}${errorText}`
  if (message === 'core_bridge_start_script_not_found') return `未找到核心重启脚本${errorText}`
  if (message.startsWith('core_bridge_start_script_not_found:')) {
    return `未找到核心重启脚本：${compact(message.slice('core_bridge_start_script_not_found:'.length), 72)}${errorText}`
  }
  return message ? `API 操作失败：${compact(message, 72)}${errorText}` : `API 操作失败${errorText}`
}

export function externalPluginInstallStateLabel(value: string): string {
  if (!value) return ''
  if (value === 'builtin') return '内置'
  if (value === 'npm_missing') return '缺少 npm'
  if (value === 'codex_cli_missing') return '缺少 Codex 命令'
  if (value === 'install_source_missing') return '缺少安装源'
  if (value === 'kohaku_missing') return '未找到 Kohaku Terrarium'
  if (value === 'unknown_plugin') return '未知插件'
  return value
}

export function externalPluginNoteLabel(value: string): string {
  if (!value) return ''
  if (value === 'external_plugin_status') return '外部插件状态已更新'
  if (value === 'already_installed') return '已经安装'
  if (value === 'codex_installer_missing') return '未找到 Codex 安装器'
  if (value === 'codex_install_command_finished') return 'Codex 安装命令已完成'
  if (value === 'kohaku_install_source_required') return 'Kohaku 需要安装源'
  if (value === 'kohaku_installed') return 'Kohaku 已安装'
  if (value === 'plugin_has_no_installer') return '该插件没有可用安装器'
  return externalPluginInstallStateLabel(value)
}

export function externalPluginActionLabel(message: string, accepted: boolean, error?: unknown): string {
  const errorText = error ? `：${compact(String(error), 58)}` : ''
  if (accepted) {
    if (message === 'external_plugin_config_saved') return '插件配置已保存'
    if (message === 'external_plugin_installed') return '插件已安装'
    if (message === 'external_plugin_install_failed') return `插件安装失败${errorText}`
    if (message === 'already_installed') return '已经安装'
    if (message === 'kohaku_installed') return 'Kohaku 已安装'
    return message || '插件状态已更新'
  }
  if (message === 'missing_plugin_id') return '缺少插件 ID'
  if (message === 'npm_missing') return '缺少 npm'
  if (message === 'codex_cli_missing') return '缺少 Codex 命令'
  if (message === 'install_source_missing') return '缺少安装源'
  if (message === 'kohaku_missing') return '未找到 Kohaku Terrarium'
  if (message === 'unknown_plugin') return '未知插件'
  if (message === 'no_installer') return '该插件没有可用安装器'
  return message ? `插件操作失败：${compact(message, 72)}${errorText}` : `插件操作失败${errorText}`
}

export function chatErrorLabel(value: string): string {
  if (!value) return ''
  if (value === 'chat_request_failed') return '发送失败'
  if (value === 'empty_text') return '内容不能为空'
  if (value === 'missing_command_id') return '缺少命令 ID'
  if (value === 'missing_candidate_id') return '缺少候选 ID'
  if (value === 'invalid_action') return '无效操作'
  return compact(value, 72)
}

export function errorLabel(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  return String(error || '未知错误')
}

export function initialTheme(): ThemeName {
  const saved = window.localStorage.getItem('xinyu.desktop.theme')
  return themeOptions.some((option) => option.id === saved) ? (saved as ThemeName) : 'pastel'
}

export function createCommandId(): string {
  const random = window.crypto?.randomUUID?.() || Math.random().toString(36).slice(2)
  return `desktop-${Date.now()}-${random}`
}

export function compact(text: string, limit: number): string {
  const clean = text.replace(/\s+/g, ' ').trim()
  return clean.length > limit ? `${clean.slice(0, Math.max(0, limit - 3)).trimEnd()}...` : clean
}

export function formatTime(value?: string): string {
  if (!value) {
    return '--:--'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '--:--'
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function formatTurnMeta(turn: JsonRecord): string {
  const platform = String(turn.platform || 'desktop')
  const source = String(turn.source || turn.messageType || 'private')
  return `${platformLabel(platform)} / ${sourceLabel(source)}`
}

export function formatLatency(turn: JsonRecord): string {
  const latency = Number(turn.latencyMs || 0)
  const recall = Number(turn.recallCount || 0)
  const parts = []
  if (latency > 0) parts.push(`${latency}ms`)
  if (recall > 0) parts.push(`${recall} 条记忆`)
  return parts.join(' / ') || statusLabel(String(turn.status || 'finished'))
}

export function memorySummary(memory: JsonRecord): string {
  const itemCount = Number(memory.itemCount || 0)
  const route = asRecord(memory.route)
  const experts = stringArray(memory.selectedExperts || route.selectedExperts)
  if (itemCount > 0) {
    if (experts.length > 0) {
      return `${itemCount} 条 / ${experts.slice(0, 3).join(' + ')}`
    }
    return `${itemCount} 条被召回`
  }
  return String(memory.eventId || memory.turnId || '暂无记忆回声')
}

export function statusLabel(status: string): string {
  if (status === 'started') return '正在组织回复'
  if (status === 'timeout') return '这次等待超时'
  if (status === 'error') return '这次没有成功'
  if (status === 'failed') return '失败'
  if (status === 'blocked') return '已阻止'
  if (status === 'expired') return '已过期'
  if (status === 'unknown') return '未知'
  return '已完成'
}

export function digestResultLabel(result: string): string {
  if (result === 'success') return '已完成'
  if (result === 'failure' || result === 'error') return '执行失败'
  if (result === 'timeout') return '执行超时'
  if (result === 'blocked' || result === 'blocked_by_boundary') return '边界拦住'
  if (!result || result === 'unknown') return '结果未知'
  return compact(result, 18)
}

export function digestPressureLabel(pressure: string): string {
  if (pressure === 'high') return '高负载'
  if (pressure === 'medium') return '中负载'
  if (pressure === 'low') return '低负载'
  if (!pressure || pressure === 'unknown') return '负载未知'
  return compact(pressure, 18)
}

export function digestThemeLabel(value: string): string {
  const text = value.trim()
  const lowered = text.toLowerCase()
  if (lowered.includes('codex_delegate')) return 'Codex 委派'
  if (lowered.includes('status_probe')) return '状态检查'
  if (lowered.includes('log_scan')) {
    const target = text.match(/log_scan:([^\s;]+)/)?.[1] || ''
    return target && target !== 'none' ? `${target} 日志扫描` : '日志扫描'
  }
  if (lowered.includes('local action pressure')) return '本地行动'
  return compact(text || '行动经验正在沉淀', 36)
}

export function digestResidueLabel(value: string, result: string, pressure: string): string {
  const text = value.trim()
  const lowered = text.toLowerCase()
  const summary = `${digestResultLabel(result)}，${digestPressureLabel(pressure)}`
  if (!text) return `等待下一次本地行动留下可读残留。`
  if (lowered.includes('codex_delegate')) return `Codex 委派：${summary}`
  if (lowered.includes('status_probe')) return `状态检查：${summary}`
  if (lowered.includes('log_scan')) {
    const target = text.match(/log_scan:([^\s;]+)/)?.[1] || ''
    return `${target && target !== 'none' ? `${target} 日志扫描` : '日志扫描'}：${summary}`
  }
  return compact(text, 120)
}

export function eventLabel(value: string): string {
  if (value === 'chat.turn.started') return '对话开始'
  if (value === 'chat.turn.finished') return '对话完成'
  if (value === 'memory.recall.used') return '记忆召回'
  if (value === 'proactive.candidate.ready') return '主动意图'
  if (value === 'proactive.delivery.updated') return '意图回流'
  if (value === 'desktop.event_replay.unavailable') return '事件回放不可用'
  if (value === 'desktop.event_stream.ready') return '事件流就绪'
  return value
}

export function platformLabel(value: string): string {
  if (value === 'desktop') return '本机'
  if (value === 'qq') return 'QQ'
  return value
}

const proactiveExactLabels: Record<string, string> = {
  active: '进行中',
  answered: '已回复',
  blocked: '已阻止',
  candidate_only: '仅候选',
  claim_ack: '确认后发送',
  codex_followup: '代码任务跟进',
  completion: '完成提醒',
  desktop_inbox: '桌面提醒',
  external_private: '外部私聊',
  failed: '失败',
  group_context: '群聊上下文',
  initiative: '主动提醒',
  initiative_lifecycle: '主动性生命周期',
  initiative_orchestrator: '主动编排器',
  local: '本地',
  local_review: '本地确认',
  low_owner_private: '低风险主人私聊',
  memory_review: '记忆审查',
  none: '本地',
  normal: '普通',
  owner_action: '主人动作',
  owner_decision: '需要主人决定',
  owner_private: '主人私聊',
  owner_replied: '主人已回复',
  owner_review: '等待你确认',
  pending: '待处理',
  preview_only: '仅预览',
  promise_followup: '承诺跟进',
  queue_owner_private: '主人私聊队列',
  ready: '就绪',
  report_completion: '完成回报',
  replied: '已回复',
  runtime_error: '运行状态提醒',
  screenshot: '截图观察',
  self_thought: '自发想法',
  state_only: '仅桌面可见',
  status: '状态检查',
  system_internal: '系统内部',
  task_done: '任务有结果',
  task_failed: '任务失败',
  live_view: '实时画面',
  list_windows: '窗口列表',
  observe_text: '文字观察',
  click: '点击',
  double_click: '双击',
  move_mouse: '移动鼠标',
  scroll: '滚动',
  type_text: '输入文字',
  hotkey: '快捷键',
  clipboard_set: '设置剪贴板',
  unknown: '未知',
  urgency_score: '紧急度评分',
  utility_score: '价值评分',
  xinyu_proactive_request_loop: '主动提醒循环'
}

function proactiveReasonLabel(value: string): string {
  const trimmed = value.trim()
  if (!trimmed || (!trimmed.includes(';') && !trimmed.includes('/') && !trimmed.includes('='))) {
    return ''
  }

  const labels: string[] = []
  const push = (label: string): void => {
    if (label && !labels.includes(label)) {
      labels.push(label)
    }
  }

  const parts = trimmed.split(';').map((part) => part.trim()).filter(Boolean)
  const head = parts.shift() || ''
  head
    .split(/[/:,]/)
    .map((token) => token.trim())
    .filter(Boolean)
    .forEach((token) => {
      if (/^\d+$/.test(token)) return
      const label = proactiveExactLabels[token]
      if (label && !['价值评分', '紧急度评分'].includes(label)) {
        push(label)
      }
    })

  for (const part of parts) {
    const [rawKey, rawValue = ''] = part.split('=').map((item) => item.trim())
    const key = proactiveExactLabels[rawKey] || rawKey
    const label = proactiveExactLabels[rawValue] || rawValue
    if (rawKey === 'gate' || rawKey === 'restraint') {
      push(label)
    } else if (label) {
      push(`${key}：${label}`)
    }
  }

  return labels.join(' · ')
}

export function proactiveTextLabel(value: string): string {
  if (!value) return value
  if (proactiveExactLabels[value]) return proactiveExactLabels[value]
  const reasonLabel = proactiveReasonLabel(value)
  if (reasonLabel) return reasonLabel
  const phraseTranslated = value
    .replace(/A delegated task finished\./g, '后台任务已经完成。')
    .replace(/A delegated task failed or timed out\./g, '后台任务失败或超时。')
    .replace(/A runtime subsystem reported an error\./g, '运行状态需要检查。')
    .replace(/background code task finished/g, '后台代码任务已完成')
    .replace(/Integrate the result or keep it as a report-only completion\./g, '根据主人选择，整合结果或仅保留报告。')
  const translated = phraseTranslated
    .split(':')
    .map((part) => proactiveExactLabels[part] || part)
    .join('：')
  if (translated !== value) return translated
  return value
}

export function sourceLabel(value: string): string {
  if (value === 'xinyu_desktop_shell') return '桌面端'
  if (value === 'desktop_private') return '私聊'
  if (value === 'qq_gateway') return 'QQ 网关'
  if (value === 'private') return '私聊'
  return value
}

export function deliveryLabel(value: string): string {
  if (value === 'queue_owner_private') return '私聊队列'
  if (value === 'claim_ack') return '确认后发送'
  if (value === 'state_only') return '仅桌面可见'
  if (value === 'preview_only') return '仅预览'
  if (value === 'none') return '本地'
  if (value === 'local') return '本地'
  if (!value) return '本地'
  return value
}

export function riskLabel(value: ProactiveIntent['risk']): string {
  if (value === 'blocked') return '已阻止'
  if (value === 'review') return '需要把关'
  return '低风险'
}

export function runtimeLabel(index: number): string {
  return ['连接', '体感', '行动', '记忆'][index] || '状态'
}

export function actionLabel(action: ProactiveAction): string {
  if (action === 'reply') return '正在回复'
  if (action === 'approve_qq') return '正在送到 QQ'
  if (action === 'read_locally') return '正在标记已读'
  return '正在忽略'
}

export function proactiveAckResultLabel(action: ProactiveAction, accepted: boolean, error?: unknown, notes?: unknown[]): string {
  if (accepted) {
    if (action === 'approve_qq') return '已排队发送到 QQ'
    if (action === 'read_locally') return '已标记本地已读'
    if (action === 'reply') return '已记录回复'
    return '已忽略'
  }

  const noteText = (Array.isArray(notes) ? notes : [])
    .map((note) => String(note || '').trim())
    .filter(Boolean)
    .join(', ')
  const code = String(error || noteText || 'unknown').trim()
  if (code.includes('desktop_proactive_candidate_not_qq_claimable')) return '这条仅桌面可见，不能直接发送到 QQ'
  if (code.includes('missing_candidate_id')) return '缺少提醒 ID'
  if (code.includes('invalid_action')) return '未知按钮动作'
  if (code.includes('candidate_not_found') || code.includes('not_found')) return '这条提醒已经不在队列里，请刷新'
  if (code.includes('missing_owner_user_id')) return '缺少主人 QQ ID，不能发送'
  if (code.includes('missing_candidate_message')) return '提醒内容为空，不能发送'
  if (code.includes('desktop_qq_enqueue_failed')) return '发送到 QQ 队列失败'
  return `操作失败：${compact(proactiveTextLabel(code), 72)}`
}

export function stickerMoodLabel(value: unknown): string {
  const mood = String(value || 'unclear').trim()
  return stickerMoodLabels[mood] || mood || stickerMoodLabels.unclear
}

export function commandStatusLabel(status: CommandState['status']): string {
  if (status === 'sending') return '正在发送'
  if (status === 'accepted') return '核心已接收'
  if (status === 'started') return '心玉正在想'
  if (status === 'failed') return '发送失败'
  return '已完成'
}
