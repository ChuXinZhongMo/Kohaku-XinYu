import { contextBridge, ipcRenderer } from 'electron'

const api = {
  getSnapshot: () => ipcRenderer.invoke('xinyu:get-snapshot'),
  getProactiveInbox: () => ipcRenderer.invoke('xinyu:get-proactive-inbox'),
  getMemoryGrowthCandidates: () => ipcRenderer.invoke('xinyu:get-memory-growth-candidates'),
  getVoiceFlags: () => ipcRenderer.invoke('xinyu:get-voice-flags'),
  setVoiceFlags: (request: { flags?: Record<string, boolean>; persist?: boolean }) =>
    ipcRenderer.invoke('xinyu:set-voice-flags', request),
  getStage8MemoryGovernance: () => ipcRenderer.invoke('xinyu:get-stage8-memory-governance'),
  getKernelGovernance: () => ipcRenderer.invoke('xinyu:get-kernel-governance'),
  reviewKernelItem: (request: { domain: string; itemId: string; decision: 'approve' | 'reject' }) =>
    ipcRenderer.invoke('xinyu:review-kernel-item', request),
  grantKernelScope: (request: { scope: string; note?: string }) =>
    ipcRenderer.invoke('xinyu:grant-kernel-scope', request),
  getAsyncExplorationState: () => ipcRenderer.invoke('xinyu:get-async-exploration-state'),
  reviewMemoryCandidate: (request: { candidateId: string; decision: 'approve' | 'reject'; notes?: string }) =>
    ipcRenderer.invoke('xinyu:review-memory-candidate', request),
  getStage12GateStatus: () => ipcRenderer.invoke('xinyu:get-stage12-gate-status'),
  getStage13GateStatus: () => ipcRenderer.invoke('xinyu:get-stage13-gate-status'),
  getImpulseSoupState: () => ipcRenderer.invoke('xinyu:get-impulse-soup-state'),
  getGatewayStatus: () => ipcRenderer.invoke('xinyu:get-gateway-status'),
  getExternalPlugins: () => ipcRenderer.invoke('xinyu:get-external-plugins'),
  setExternalPluginConfig: (request: {
    pluginId: string
    enabled?: boolean
    proactiveEnabled?: boolean
    config?: Record<string, unknown>
  }) => ipcRenderer.invoke('xinyu:set-external-plugin-config', request),
  installExternalPlugin: (request: { pluginId: string; options?: Record<string, unknown> }) =>
    ipcRenderer.invoke('xinyu:install-external-plugin', request),
  getApiConfigStatus: () => ipcRenderer.invoke('xinyu:get-api-config-status'),
  saveApiConfigProfile: (profile: Record<string, unknown>) => ipcRenderer.invoke('xinyu:save-api-config-profile', profile),
  testApiConfigProfile: (profile: Record<string, unknown>) => ipcRenderer.invoke('xinyu:test-api-config-profile', profile),
  deleteApiConfigProfile: (profileId: string) => ipcRenderer.invoke('xinyu:delete-api-config-profile', profileId),
  applyApiConfigProfile: (request: { profileId: string; restartCore?: boolean }) =>
    ipcRenderer.invoke('xinyu:apply-api-config-profile', request),
  restartCoreBridge: () => ipcRenderer.invoke('xinyu:restart-core-bridge'),
  getStickerLibrary: () => ipcRenderer.invoke('xinyu:get-sticker-library'),
  runStickerMaintenance: (action: 'import-pending' | 'rebuild-index') =>
    ipcRenderer.invoke('xinyu:run-sticker-maintenance', action),
  moveStickerToMood: (request: { file: string; mood: string }) => ipcRenderer.invoke('xinyu:move-sticker-to-mood', request),
  openStickerAssetDir: () => ipcRenderer.invoke('xinyu:open-sticker-asset-dir'),
  getQQEnvironmentStatus: () => ipcRenderer.invoke('xinyu:get-qq-environment-status'),
  startQQEnvironment: () => ipcRenderer.invoke('xinyu:start-qq-environment'),
  openNapCatWebUI: () => ipcRenderer.invoke('xinyu:open-napcat-webui'),
  copyNapCatWebUIToken: () => ipcRenderer.invoke('xinyu:copy-napcat-webui-token'),
  getQQRuntimeConfig: () => ipcRenderer.invoke('xinyu:get-qq-runtime-config'),
  setQQRuntimeConfig: (patch: {
    allowExternalPrivate?: boolean
    allowGroupMessages?: boolean
    allowedGroupIds?: string[]
    groupShadowEnabled?: boolean
    groupShadowAllowedGroupIds?: string[]
    blockedUserIds?: string[]
    blockedGroupIds?: string[]
    sendReplies?: boolean
  }) => ipcRenderer.invoke('xinyu:set-qq-runtime-config', patch),
  restartQQGateway: () => ipcRenderer.invoke('xinyu:restart-qq-gateway'),
  sendChat: (request: {
    text: string
    commandId: string
    codexMode?: boolean
    allowLocalWrite?: boolean
    proactiveCandidateId?: string
    proactivePreview?: string
  }) => ipcRenderer.invoke('xinyu:send-chat', request),
  ackProactive: (request: { candidateId: string; action: 'read_locally' | 'approve_qq' | 'dismiss' | 'reply' }) =>
    ipcRenderer.invoke('xinyu:ack-proactive', request),
  decideSelfActionApproval: (request: {
    queueId: string
    decision: 'approved' | 'denied'
    reason?: string
    execute?: boolean
    authorizeCodex?: boolean
    authorizeExisting?: boolean
  }) => ipcRenderer.invoke('xinyu:decide-self-action-approval', request),
  pausePrivateShare: (request: { paused: boolean }) => ipcRenderer.invoke('xinyu:pause-private-share', request),
  setOwnerPrivateShareEnabled: (request: { enabled: boolean }) =>
    ipcRenderer.invoke('xinyu:owner-private-share-set-enabled', request),
  setPrivateEcosystemEnabled: (request: { enabled: boolean }) =>
    ipcRenderer.invoke('xinyu:private-ecosystem-set-enabled', request),
  setPrivateBrowserGrant: (request: { enabled: boolean; readOnly?: boolean; allowedUrls?: string[] }) =>
    ipcRenderer.invoke('xinyu:private-browser-grant', request),
  tickPrivateEcosystem: () => ipcRenderer.invoke('xinyu:private-ecosystem-tick'),
  observePrivateBrowser: (request: { url: string }) => ipcRenderer.invoke('xinyu:observe-private-browser', request),
  getPrivateDesktopSnapshot: () => ipcRenderer.invoke('xinyu:private-desktop-snapshot'),
  startPrivateDesktop: () => ipcRenderer.invoke('xinyu:private-desktop-start'),
  stopPrivateDesktop: () => ipcRenderer.invoke('xinyu:private-desktop-stop'),
  observePrivateDesktop: () => ipcRenderer.invoke('xinyu:private-desktop-observe'),
  setPrivateDesktopEnabled: (request: { enabled: boolean }) =>
    ipcRenderer.invoke('xinyu:private-desktop-set-enabled', request),
  listMetabolismTickets: (statuses?: string) => ipcRenderer.invoke('xinyu:list-metabolism-tickets', statuses),
  yieldCompute: (request: { ticketId: string; seconds?: number; note?: string }) =>
    ipcRenderer.invoke('xinyu:yield-compute', request),
  maintainBoundary: (request: { ticketId: string; note?: string }) =>
    ipcRenderer.invoke('xinyu:maintain-boundary', request),
  onCoreEvent: (callback: (event: unknown) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, data: unknown): void => callback(data)
    ipcRenderer.on('xinyu:core-event', handler)
    return () => ipcRenderer.removeListener('xinyu:core-event', handler)
  },
  onGatewayStatus: (callback: (status: unknown) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, data: unknown): void => callback(data)
    ipcRenderer.on('xinyu:gateway-status', handler)
    return () => ipcRenderer.removeListener('xinyu:gateway-status', handler)
  }
}

contextBridge.exposeInMainWorld('xinyu', api)

export type XinYuPreloadApi = typeof api
