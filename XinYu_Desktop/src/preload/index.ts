import { contextBridge, ipcRenderer } from 'electron'

const api = {
  getSnapshot: () => ipcRenderer.invoke('xinyu:get-snapshot'),
  getGatewayStatus: () => ipcRenderer.invoke('xinyu:get-gateway-status'),
  sendChat: (request: { text: string; commandId: string }) => ipcRenderer.invoke('xinyu:send-chat', request),
  ackProactive: (request: { candidateId: string; action: 'read_locally' | 'approve_qq' | 'dismiss' }) =>
    ipcRenderer.invoke('xinyu:ack-proactive', request),
  startService: (name: string) => ipcRenderer.invoke('xinyu:start-service', name),
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
