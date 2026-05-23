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

export type ApiConfigProfile = {
  id: string
  label: string
  provider: string
  model: string
  baseUrl: string
  allowInsecureHttp: boolean
  disableStreaming: boolean
  updatedAt: string
  active: boolean
  hasApiKey: boolean
  apiKeyPreview: string
}

export type ApiConfigCurrent = {
  configPath: string
  provider: string
  model: string
  baseUrl: string
  allowInsecureHttp: boolean
  disableStreaming: boolean
  hasApiKey: boolean
  apiKeyPreview: string
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
  provider?: string
  model?: string
  baseUrl?: string
  apiKey?: string
  allowInsecureHttp?: boolean
  disableStreaming?: boolean
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

export type ThemeName = 'pastel' | 'sakura' | 'mint' | 'night'
