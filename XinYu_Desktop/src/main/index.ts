import { BrowserWindow, Menu, Notification, app, ipcMain } from 'electron'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { XinyuGateway, type GatewayStatus, type XinYuDesktopEvent } from './xinyu_gateway'

let mainWindow: BrowserWindow | null = null
let gateway: XinyuGateway | null = null
let lastStatus: GatewayStatus | null = null

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 900,
    minHeight: 620,
    autoHideMenuBar: true,
    backgroundColor: '#080b10',
    title: '心玉',
    icon: resolveWindowIcon(),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  })
  mainWindow.setMenuBarVisibility(false)

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    void mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    void mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

function resolveWindowIcon(): string {
  const builtIcon = join(__dirname, '../renderer/xinyu-avatar.png')
  if (existsSync(builtIcon)) {
    return builtIcon
  }
  return join(process.cwd(), 'src/renderer/public/xinyu-avatar.png')
}

function sendToRenderer(channel: string, payload: unknown): void {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return
  }
  mainWindow.webContents.send(channel, payload)
}

function handleCoreEvent(event: XinYuDesktopEvent): void {
  sendToRenderer('xinyu:core-event', event)
  if (event.type === 'proactive.candidate.ready' && Notification.isSupported()) {
    const focused = Boolean(mainWindow && !mainWindow.isDestroyed() && mainWindow.isFocused())
    if (!focused) {
    const preview = String(event.payload?.candidatePreview || '心玉有一条主动提醒。')
      new Notification({
        title: '心玉',
        body: preview.slice(0, 160)
      }).show()
    }
  }
}

function handleGatewayStatus(status: GatewayStatus): void {
  lastStatus = status
  sendToRenderer('xinyu:gateway-status', status)
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null)
  createWindow()
  gateway = new XinyuGateway({
    onEvent: handleCoreEvent,
    onStatus: handleGatewayStatus
  })
  void gateway.start()

  ipcMain.handle('xinyu:get-snapshot', async () => {
    return await gateway?.getSnapshot()
  })
  ipcMain.handle('xinyu:get-gateway-status', () => {
    return gateway?.getStatus() || lastStatus
  })
  ipcMain.handle('xinyu:send-chat', async (_event, request: unknown) => {
    const payload = request && typeof request === 'object' ? (request as { text?: unknown; commandId?: unknown }) : {}
    return await gateway?.sendChat({
      text: String(payload.text || ''),
      commandId: String(payload.commandId || '')
    })
  })
  ipcMain.handle('xinyu:ack-proactive', async (_event, request: unknown) => {
    const payload =
      request && typeof request === 'object' ? (request as { candidateId?: unknown; action?: unknown }) : {}
    return await gateway?.ackProactive({
      candidateId: String(payload.candidateId || ''),
      action: String(payload.action || '') as 'read_locally' | 'approve_qq' | 'dismiss'
    })
  })
  ipcMain.handle('xinyu:start-service', async (_event, name: string) => {
    return {
      accepted: false,
      service: String(name || ''),
      notes: ['service_control_not_implemented_in_v0']
    }
  })

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('before-quit', () => {
  gateway?.stop()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
