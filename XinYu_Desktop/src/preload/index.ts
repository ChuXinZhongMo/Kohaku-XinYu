import { contextBridge, ipcRenderer } from 'electron'

const api = {
  getSnapshot: () => ipcRenderer.invoke('xinyu:get-snapshot'),
  getProactiveInbox: () => ipcRenderer.invoke('xinyu:get-proactive-inbox'),
  getImpulseSoupState: () => ipcRenderer.invoke('xinyu:get-impulse-soup-state'),
  getGatewayStatus: () => ipcRenderer.invoke('xinyu:get-gateway-status'),
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
