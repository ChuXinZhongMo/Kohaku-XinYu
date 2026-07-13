export type JsonRecord = Record<string, unknown>

export type DesktopEvent = {
  id?: string
  type: string
  ts?: string
  payload?: JsonRecord
  severity?: string
}

export type Snapshot = {
  snapshotAt?: string
  xinyuState?: JsonRecord
  proactiveInbox?: unknown[]
  proactiveHistory?: unknown[]
  recentTurns?: unknown[]
  recentMemoryEvents?: unknown[]
  actionDigestState?: JsonRecord
  selfAction?: SelfActionSnapshot
  privateEcosystem?: PrivateEcosystemSnapshot
}

export type PrivateEcosystemSnapshot = {
  observed?: boolean
  enabled?: boolean
  rolloutState?: string
  updatedAt?: string
  activeGoalId?: string
  latestActionKind?: string
  latestActionStatus?: string
  counters?: {
    ticks?: number
    lowRiskExecuted?: number
    approvalQueued?: number
    memoryCandidates?: number
    sharesPrepared?: number
    sharesSent?: number
    sharesHeld?: number
    blockedHighRisk?: number
  }
  ownerPrivateShare?: {
    enabled?: boolean
    paused?: boolean
    active?: boolean
    deliveryLevel?: string
    dailyRemaining?: number
    dailyLimit?: number
    cooldownRemainingMinutes?: number
    quietHours?: string
  }
  journal?: {
    recentEvents?: number
    latestEventKind?: string
    stableMemoryWriteCount?: number
  }
  browser?: {
    engine?: string
    enabled?: boolean
    readOnly?: boolean
    allowedUrls?: string[]
    lastActionKind?: string
    lastResult?: string
    actionsTotal?: number
    actionsBlocked?: number
    artifactCount?: number
    screenshotCount?: number
    usesOwnerProfile?: boolean
  }
  computer?: {
    backend?: string
    lastActionKind?: string
    lastResult?: string
    observedCount?: number
    proposedCount?: number
    blockedCount?: number
    multiStepArbitraryControl?: string
  }
  killSwitch?: {
    sharePaused?: boolean
    shareEnabled?: boolean
  }
  boundaries?: {
    stableMemoryWrite?: string
    qqMessageEnqueuedDirectly?: boolean
    rawOwnerTextRetained?: boolean
    secretOrLocalPathRetained?: boolean
  }
  paths?: JsonRecord
}

export type PrivateBrowserGrantPatch = {
  enabled: boolean
  readOnly: boolean
  allowedUrls: string[]
}

export type MetabolismTicket = JsonRecord & {
  ticket_id?: string
  ticketId?: string
  id?: string
  status?: string
  kind?: string
  request_kind?: string
  action_kind?: string
  desire_shape?: string
  requested_seconds?: number
  approved_seconds?: number
  reason?: string
  note?: string
  created_at?: string
  updated_at?: string
  expires_at?: string
}

export type MetabolismTicketActionState = {
  kind: 'idle' | 'loading' | 'yielding' | 'maintaining'
  ticketId?: string
  message: string
}

export type SelfActionSnapshot = {
  observed?: boolean
  updatedAt?: string
  selectedGoalId?: string
  selectedActionKind?: string
  pendingApprovalCount?: number
  latestPendingQueueId?: string
  latestApprovalEvent?: JsonRecord
  approvalQueue?: JsonRecord
  gateway?: JsonRecord
  handoff?: JsonRecord
  patchExecutor?: JsonRecord
  candidateActions?: JsonRecord[]
  paths?: JsonRecord
  notes?: string[]
}

export type ImpulseThoughtlet = {
  thoughtletId: string
  lineageId: string
  parentId: string
  generation: number
  sourceKind: string
  sourceRef: string
  desireShape: string
  proposedNextAction: string
  inhibitionRule: string
  energy: number
  usefulnessScore: number
  mutationCount: number
  activationCount: number
  status: string
  evidencePreview: string
  riskFlags: string[]
  updatedAt: string
}

export type ImpulseTraceEvent = {
  observedAt: string
  status: string
  seedCount: number
  createdCount: number
  updatedCount: number
  spawnedCount: number
  activeCount: number
  lineageCount: number
  topDesireShape: string
  topEnergy: number
}

export type ImpulseSoupState = {
  ok: boolean
  loadedAt: string
  updatedAt: string
  status: string
  schemaVersion: string
  statePath: string
  markdownPath: string
  tracePath: string
  thoughtletCount: number
  activeCount: number
  dormantCount: number
  quarantinedCount: number
  extinctCount: number
  lineageCount: number
  softActiveCount: number
  topThoughtletId: string
  topDesireShape: string
  topEnergy: number
  topAction: string
  outwardActionAllowed: boolean
  thoughtlets: ImpulseThoughtlet[]
  traceTail: ImpulseTraceEvent[]
}

export type GatewayStatus = {
  connected?: boolean
  connecting?: boolean
  httpUrl?: string
  snapshotAt?: string
}

export type GrowthCandidatePromotionItem = {
  candidateId: string
  status: string
  candidateType: string
  targetMemoryLayer: string
  targetPath: string
  targetGate: string
  beforeHash: string
  applyCommand: string
  previewPath: string
  blockers: string[]
  riskFlags: string[]
  applyAllowed: boolean
  stableMemoryWrite: string
  stablePersonalityWrite: string
  reasonPreview: string
  candidateTextPreview: string
}

export type GrowthCandidatePromotionStatus = {
  ok: boolean
  pendingApplyCount: number
  appliedCount: number
  ownerReviewRequiredCount: number
  pendingApply: GrowthCandidatePromotionItem[]
  applied: GrowthCandidatePromotionItem[]
  ownerReviewRequired: GrowthCandidatePromotionItem[]
  targetPath: string
  targetMemoryLayer: string
  notes: string[]
  error: string
}

export type Stage8DuplicateCluster = {
  topic: string
  size: number
  conflicts: number
  privateOrHiddenSamples: number
  recommendation: string
  statuses: JsonRecord
}

export type Stage8BlockedGate = {
  gate: string
  status: string
  count: number
  reason: string
}

export type Stage8ReviewDecision = {
  actionKind: string
  command: string
  decidedAt: string
  decision: string
  decisionId: string
  itemId: string
  recordKey: string
}

export type Stage8PromotionDryRun = {
  candidateId: string
  status: string
  candidateType: string
  targetMemoryLayer: string
  stableMemoryWrite: string
  applyAllowed: boolean
  blockers: string[]
}

export type KernelReviewItem = {
  domain: string
  itemId: string
  contentPreview: string
  reviewStatus: string
  confidence?: number
  actionType?: string
  sourceEventId?: string
}

export type KernelGovernanceStatus = {
  ok: boolean
  available: boolean
  loadedAt: string
  selfId: string
  error: string
  pendingCount: number
  worldModelCount: number
  reorganizationCount: number
  beliefCount: number
  followupCount: number
  writesBlocked: boolean
  items: KernelReviewItem[]
  cycleCount: number
  slowSignalCount: number
  slowEscalationThreshold: number
  reorgRecommendation: string
  selfStorySummary: string
  grantedScopes: string[]
  grantableScopes: string[]
}

export type Stage8MemoryGovernanceStatus = {
  ok: boolean
  loadedAt: string
  updatedAt: string
  status: string
  readyForStage9: boolean
  reason: string
  nextStep: string
  stage7ReadyForStage8: boolean
  stage7Reason: string
  candidateTotal: number
  ownerReviewRequiredCount: number
  privateOrOwnerScopedCount: number
  duplicateClusterCount: number
  learningTrialSuccessGate: string
  stableProfileWrite: string
  ownerMemoryWrite: string
  ownerReviewCandidateText: string
  stablePersonalityWrite: string
  growthApplyMode: string
  stableIdentityProfileApply: string
  packetStatus: string
  packetPath: string
  duplicateClusters: Stage8DuplicateCluster[]
  blockedGates: Stage8BlockedGate[]
  reviewInboxPendingCount: number
  reviewInboxProcessedCount: number
  latestDecision: Stage8ReviewDecision | null
  latestDryRun: Stage8PromotionDryRun | null
  boundaries: {
    rawOwnerTextInPacket: boolean
    visibleReplyTextInPacket: boolean
    candidateBodyInPacket: boolean
    stableMemoryWrite: string
    consciousnessClaim: boolean
  }
}

export type ApiConfigLlm = {
  provider: string
  model: string
  baseUrl: string
  allowInsecureHttp: boolean
  disableStreaming: boolean
  hasApiKey: boolean
  apiKeyPreview: string
}

export type ApiConfigVision = {
  enabled: boolean
  model: string
  baseUrl: string
  timeoutSeconds: number
  maxBytes: number
  hasApiKey: boolean
  apiKeyPreview: string
}

export type ApiConfigHearing = {
  enabled: boolean
  command: string
  model: string
  baseUrl: string
  language: string
  timeoutSeconds: number
  recordFormat: string
  hasApiKey: boolean
  apiKeyPreview: string
}

export type ApiConfigTts = {
  enabled: boolean
  engine: string
  model: string
  baseUrl: string
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
  hasApiKey: boolean
  apiKeyPreview: string
}

export type ApiConfigOther = {
  hasOpenAIApiKey: boolean
  openAIApiKeyPreview: string
}

export type ApiConfigProfile = {
  id: string
  label: string
  llm: ApiConfigLlm
  vision: ApiConfigVision
  hearing: ApiConfigHearing
  tts: ApiConfigTts
  other: ApiConfigOther
  updatedAt: string
  active: boolean
}

export type ApiConfigCurrent = {
  configPath: string
  llm: ApiConfigLlm
  vision: ApiConfigVision
  hearing: ApiConfigHearing
  tts: ApiConfigTts
  other: ApiConfigOther
}

export type ApiConfigStatus = {
  ok: boolean
  loadedAt: string
  configPath: string
  profilesPath: string
  activeProfileId: string
  current: ApiConfigCurrent
  profiles: ApiConfigProfile[]
  notes: string[]
}

export type ApiConfigProfilePatch = {
  id?: string
  label?: string
  llm?: {
    provider?: string
    model?: string
    baseUrl?: string
    apiKey?: string
    allowInsecureHttp?: boolean
    disableStreaming?: boolean
  }
  vision?: {
    enabled?: boolean
    model?: string
    baseUrl?: string
    apiKey?: string
    timeoutSeconds?: number
    maxBytes?: number
  }
  hearing?: {
    enabled?: boolean
    command?: string
    model?: string
    baseUrl?: string
    apiKey?: string
    language?: string
    timeoutSeconds?: number
    recordFormat?: string
  }
  tts?: {
    enabled?: boolean
    engine?: string
    model?: string
    baseUrl?: string
    apiKey?: string
    voice?: string
    format?: string
    requestMode?: string
    timeoutSeconds?: number
    genieBaseUrl?: string
    genieCharacter?: string
    genieSplitSentence?: boolean
    genieSampleRate?: number
    genieChannels?: number
    genieSampleWidth?: number
  }
  other?: {
    openAIApiKey?: string
  }
}

export type ApiConfigActionState = {
  kind: 'idle' | 'loading' | 'saving' | 'testing' | 'applying' | 'restarting' | 'deleting'
  message: string
}

export type ExternalPluginInstallState = {
  installed: boolean
  installable: boolean
  path: string
  installer: string
  missingReason: string
}

export type ExternalPluginControl = {
  pluginId: string
  title: string
  kind: string
  transport: string
  enabled: boolean
  proactiveEnabled: boolean
  installed: boolean
  installable: boolean
  available: boolean
  config: JsonRecord
  install: ExternalPluginInstallState
  notes: string[]
}

export type ExternalPluginsStatus = {
  ok: boolean
  protocol: string
  configPath: string
  plugins: ExternalPluginControl[]
  notes: string[]
}

export type ExternalPluginActionState = {
  kind: 'idle' | 'loading' | 'saving' | 'installing'
  pluginId?: string
  message: string
}

export type ExternalPluginConfigPatch = {
  pluginId: string
  enabled?: boolean
  proactiveEnabled?: boolean
  config?: JsonRecord
}

export type ExternalPluginInstallRequest = {
  pluginId: string
  options?: JsonRecord
}

export type ServiceProbe = {
  key: 'coreBridge' | 'qqGateway' | 'napcatWebui' | 'napcatReverseWs'
  label: string
  endpoint: string
  ok: boolean
  detail: string
}

export type QQEnvironmentStatus = {
  checkedAt?: string
  allReady?: boolean
  webuiUrl?: string
  webuiLoginUrl?: string
  tokenAvailable?: boolean
  napcatQQLoggedIn?: boolean | null
  diagnosis?: string
  services?: ServiceProbe[]
  lastError?: string
}

export type QQActionState = {
  kind: 'idle' | 'starting' | 'opening' | 'copying' | 'refreshing'
  message: string
}

export type QQRuntimeConfig = {
  configPath: string
  loadedAt: string
  requireWhitelist: boolean
  allowExternalPrivate: boolean
  allowGroupMessages: boolean
  allowedGroupIds: string[]
  groupTriggerMode: string
  groupShadowEnabled: boolean
  groupShadowAllowedGroupIds: string[]
  groupShadowMaxTextChars: number
  blockedUserIds: string[]
  blockedGroupIds: string[]
  sendReplies: boolean
  ownerUserIds: string[]
  whitelistUserIds: string[]
  trustedUserIds: string[]
  notes: string[]
}

export type QQRuntimeConfigPatch = {
  allowExternalPrivate?: boolean
  allowGroupMessages?: boolean
  allowedGroupIds?: string[]
  groupShadowEnabled?: boolean
  groupShadowAllowedGroupIds?: string[]
  blockedUserIds?: string[]
  blockedGroupIds?: string[]
  sendReplies?: boolean
}

export type QQRuntimeActionState = {
  kind: 'idle' | 'loading' | 'applying' | 'restarting'
  message: string
}

export type StickerRecord = {
  file: string
  mood: string
  moodLabel: string
  ocrText: string
  clipMood: string
  clipMoodLabel: string
  clipConfidence: number
  confirmed: boolean
  autoSend: boolean
  weight: number
}

export type StickerLibrary = {
  assetDir: string
  updatedAt: string
  total: number
  moods: string[]
  counts: Record<string, number>
  unclear: number
  confirmed: number
  unconfirmed: number
  ocr: number
  autoSend: number
  corrections: number
  referenceItems: number
  items: StickerRecord[]
}

export type StickerActionState = {
  kind: 'idle' | 'refreshing' | 'importing' | 'indexing' | 'opening' | 'moving'
  message: string
}

export type CommandState = {
  commandId: string
  textPreview: string
  kind?: 'chat' | 'codex'
  localWrite?: boolean
  status: 'sending' | 'accepted' | 'started' | 'finished' | 'failed'
  message: string
  turnId?: string
}

export type ProactiveAction = 'read_locally' | 'approve_qq' | 'dismiss' | 'reply'

export type AppState = {
  snapshot: Snapshot | null
  gateway: GatewayStatus | null
  events: DesktopEvent[]
  commands: CommandState[]
  proactiveActions: Record<string, ProactiveAction>
  proactiveInbox: unknown[]
  proactiveHistory: unknown[]
  impulseSoup: ImpulseSoupState | null
  recentTurns: unknown[]
  recentMemoryEvents: unknown[]
  memoryGrowthCandidates: GrowthCandidatePromotionStatus | null
  stage8MemoryGovernance: Stage8MemoryGovernanceStatus | null
  kernelGovernance: KernelGovernanceStatus | null
  asyncExploration: AsyncExplorationState | null
  stage12Gate: Stage12GateStatus | null
  stage13Gate: Stage13GateStatus | null
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
}

export type XinYuState = {
  connection: 'online' | 'connecting' | 'offline'
  moodLabel: string
  moodScore: number
  attentionFocus: string
  recentConcern: string
  physicalSensation: string
  waitingReply: boolean
  waitingReason: string
  continuity: string
  lastShiftAt: string
  evidence: string[]
}

export type ProactiveIntent = {
  id: string
  source: string
  trigger: string
  plannedText: string
  fullText: string
  reasonText: string
  risk: 'low' | 'review' | 'blocked'
  riskLabel: string
  delivery: string
  claimable: boolean
  status: string
  requestFamily: string
  requestedAction: string
  desktopAction: string
  evidenceHash: string
  createdAt: string
  expiresAt: string
  updatedAt: string
}

export type AsyncExplorationState = {
  ok: boolean
  loadedAt: string
  updatedAt: string
  status: string
  resumeId: string
  sessionKey: string
  delegationReason: string
  taskSummary: string
  failureKind: string
  resultQuality: string
  ownerIntervention: string
  ownerVisibleResumeHint: string
}

export type Stage12GateStatus = {
  ok: boolean
  loadedAt: string
  updatedAt: string
  status: string
  readyForStage13: boolean
  reason: string
  liveLoopStatus: string
  liveLoopPassRatePct: number
  liveLoopPassedCount: number
  liveLoopRequiredCount: number
  liveLoopFailingChecks: string
  liveLoopFailingDetail: string
  gateStage11Ready: boolean
  gateLiveLoopPass: boolean
  gateFeedbackClean: boolean
  gatePrivacyClean: boolean
  gateStableClean: boolean
  gateCanaryReady: boolean
  gateShortTermClean: boolean
  nextStep: string
}

export type Stage13GateStatus = {
  ok: boolean
  loadedAt: string
  updatedAt: string
  status: string
  available: boolean
  reason: string
  stage12ReadyForStage13: boolean
  behaviorMode: string
  selectedIntent: string
  behaviorGate: string
  memoryGovernanceStatus: string
  nextStep: string
}

export type ThemeName = 'pastel' | 'sakura' | 'mint' | 'night'
