import { execFile } from 'node:child_process'
import { BrowserWindow, Menu, Notification, app, ipcMain, shell } from 'electron'
import { existsSync, mkdirSync, readdirSync, readFileSync, renameSync } from 'node:fs'
import { basename, dirname, extname, join, relative, resolve } from 'node:path'
import { promisify } from 'node:util'
import {
  copyNapCatWebUIToken,
  getQQEnvironmentStatus,
  getQQRuntimeConfig,
  openNapCatWebUI,
  restartQQGateway,
  setQQRuntimeConfig,
  startQQEnvironment
} from './qq_environment'
import {
  applyApiConfigProfile,
  deleteApiConfigProfile,
  getApiConfigStatus,
  restartCoreBridge,
  saveApiConfigProfile,
  testApiConfigProfile
} from './api_config'
import { XinyuGateway, type GatewayStatus, type XinYuDesktopEvent } from './xinyu_gateway'

let mainWindow: BrowserWindow | null = null
let gateway: XinyuGateway | null = null
let lastStatus: GatewayStatus | null = null
const execFileAsync = promisify(execFile)

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1560,
    height: 860,
    minWidth: 1480,
    minHeight: 720,
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

function resolveXinYuWorkspace(): string {
  const configured = process.env.XINYU_HOME || process.env.XINYU_ROOT
  if (configured && existsSync(configured)) {
    return configured
  }
  const cwd = process.cwd()
  if (cwd.endsWith('XinYu_Desktop')) {
    return dirname(cwd)
  }
  return resolve(cwd, '..')
}

function resolveXinYuCoreDir(): string {
  return join(resolveXinYuWorkspace(), 'XinYu-Core', 'examples', 'agent-apps', 'xinyu')
}

function resolveCorePython(): string {
  const coreDir = resolveXinYuCoreDir()
  const venvPython = join(coreDir, '.venv', 'Scripts', 'python.exe')
  return existsSync(venvPython) ? venvPython : 'python'
}

function readJsonFile(path: string): Record<string, unknown> {
  try {
    return JSON.parse(readFileSync(path, 'utf-8')) as Record<string, unknown>
  } catch {
    return {}
  }
}

function readJsonlTail(path: string, limit: number): Record<string, unknown>[] {
  try {
    return readFileSync(path, 'utf-8')
      .split(/\r?\n/)
      .filter((line) => line.trim())
      .slice(-Math.max(1, limit))
      .map((line) => JSON.parse(line) as Record<string, unknown>)
  } catch {
    return []
  }
}

function readImpulseSoupState(): Record<string, unknown> {
  const coreDir = resolveXinYuCoreDir()
  const contextDir = join(coreDir, 'memory', 'context')
  const statePath = join(contextDir, 'impulse_soup_state.json')
  const markdownPath = join(contextDir, 'impulse_soup_state.md')
  const tracePath = join(contextDir, 'impulse_soup_trace.jsonl')
  const state = readJsonFile(statePath)
  const summary = state.summary && typeof state.summary === 'object' ? (state.summary as Record<string, unknown>) : {}
  const thoughtlets = Array.isArray(state.thoughtlets) ? state.thoughtlets : []
  return {
    ok: existsSync(statePath),
    loadedAt: new Date().toISOString(),
    coreDir,
    statePath,
    markdownPath,
    tracePath,
    updatedAt: String(state.updated_at || ''),
    status: String(state.status || (existsSync(statePath) ? 'active' : 'missing')),
    schemaVersion: String(state.schema_version || ''),
    boundaries: state.boundaries && typeof state.boundaries === 'object' ? state.boundaries : {},
    summary,
    thoughtlets,
    traceTail: readJsonlTail(tracePath, 24)
  }
}

function parseCommandJson(stdout: string): Record<string, unknown> {
  const text = stdout.trim()
  if (!text) {
    return {}
  }
  try {
    return JSON.parse(text) as Record<string, unknown>
  } catch {
    return { stdout: text.slice(-4000) }
  }
}

function resolveStickerAssetDir(): string {
  return join(resolveXinYuWorkspace(), '素材库', '心玉', '表情')
}

async function runStickerMaintenance(action: unknown): Promise<Record<string, unknown>> {
  const mode = String(action || '').trim()
  const coreDir = resolveXinYuCoreDir()
  const python = resolveCorePython()
  const script = join(coreDir, 'xinyu_sticker_import.py')
  if (!existsSync(script)) {
    throw new Error(`未找到表情导入脚本：${script}`)
  }
  const args =
    mode === 'import-pending'
      ? [script, '--use-clip', '--use-ocr', '--apply', '--json']
      : mode === 'rebuild-index'
        ? [script, '--write-semantics', '--apply', '--json']
        : []
  if (!args.length) {
    throw new Error(`不支持的表情维护动作：${mode}`)
  }
  const startedAt = new Date().toISOString()
  const { stdout, stderr } = await execFileAsync(python, args, {
    cwd: coreDir,
    encoding: 'utf-8',
    timeout: 15 * 60 * 1000,
    windowsHide: true,
    maxBuffer: 8 * 1024 * 1024
  })
  return {
    ok: true,
    action: mode,
    startedAt,
    finishedAt: new Date().toISOString(),
    result: parseCommandJson(String(stdout || '')),
    stderr: String(stderr || '').slice(-2000)
  }
}

const STICKER_IMAGE_SUFFIXES = new Set(['.avif', '.bmp', '.gif', '.jfif', '.jpeg', '.jpg', '.png', '.webp'])

const STICKER_MOOD_LABELS: Record<string, string> = {
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

function assertInside(base: string, target: string): void {
  const baseResolved = resolve(base)
  const targetResolved = resolve(target)
  const rel = relative(baseResolved, targetResolved)
  if (rel.startsWith('..') || resolve(rel) === rel) {
    throw new Error('表情路径超出资源目录')
  }
}

function safeStickerRelativePath(value: unknown): string {
  const relPath = String(value || '').replace(/\\/g, '/').trim()
  if (!relPath || relPath.includes('\0') || relPath.startsWith('/') || /^[a-zA-Z]:/.test(relPath)) {
    throw new Error('表情文件路径无效')
  }
  if (relPath.split('/').some((part) => !part || part === '.' || part === '..')) {
    throw new Error('表情文件路径无效')
  }
  return relPath
}

function dedupeStickerDestination(path: string): string {
  if (!existsSync(path)) {
    return path
  }
  const suffix = extname(path)
  const stem = basename(path, suffix)
  const dir = dirname(path)
  for (let index = 2; index < 1000; index += 1) {
    const candidate = join(dir, `${stem}-${index}${suffix}`)
    if (!existsSync(candidate)) {
      return candidate
    }
  }
  throw new Error('无法分配表情目标路径')
}

async function moveStickerToMood(request: unknown): Promise<Record<string, unknown>> {
  const payload = request && typeof request === 'object' ? (request as { file?: unknown; mood?: unknown }) : {}
  const relFile = safeStickerRelativePath(payload.file)
  const targetMood = String(payload.mood || '').trim()
  const targetLabel = STICKER_MOOD_LABELS[targetMood]
  if (!targetLabel) {
    throw new Error(`不支持的表情分组：${targetMood}`)
  }

  const assetDir = resolveStickerAssetDir()
  const source = resolve(assetDir, relFile)
  assertInside(assetDir, source)
  if (!existsSync(source)) {
    throw new Error(`未找到表情文件：${relFile}`)
  }
  if (!STICKER_IMAGE_SUFFIXES.has(extname(source).toLowerCase())) {
    throw new Error('不支持的表情图片类型')
  }

  const targetDir = resolve(assetDir, targetLabel)
  assertInside(assetDir, targetDir)
  mkdirSync(targetDir, { recursive: true })
  if (resolve(dirname(source)) === targetDir) {
    const maintenance = await runStickerMaintenance('rebuild-index')
    return {
      ok: true,
      moved: false,
      note: 'already_in_target_mood',
      file: relFile,
      mood: targetMood,
      moodLabel: targetLabel,
      maintenance
    }
  }

  const destination = dedupeStickerDestination(join(targetDir, basename(source)))
  assertInside(assetDir, destination)
  renameSync(source, destination)
  const maintenance = await runStickerMaintenance('rebuild-index')
  return {
    ok: true,
    moved: true,
    file: relative(assetDir, destination).replace(/\\/g, '/'),
    previousFile: relFile,
    mood: targetMood,
    moodLabel: targetLabel,
    maintenance
  }
}

function stickerMoodLabel(value: unknown): string {
  const mood = String(value || 'unclear').trim()
  return STICKER_MOOD_LABELS[mood] || mood || STICKER_MOOD_LABELS.unclear
}

function readStickerLibrarySummary(): Record<string, unknown> {
  const assetDir = resolveStickerAssetDir()
  const manifest = readJsonFile(join(assetDir, 'manifest.generated.json'))
  const corrections = readJsonFile(join(assetDir, 'corrections.generated.json'))
  const referenceIndex = readJsonFile(join(assetDir, 'reference_index.generated.json'))
  const stickers = Array.isArray(manifest.stickers) ? (manifest.stickers as Record<string, unknown>[]) : []
  const moods = existsSync(assetDir)
    ? readdirSync(assetDir, { withFileTypes: true })
        .filter((entry) => entry.isDirectory() && !entry.name.startsWith('.'))
        .map((entry) => entry.name)
        .sort((a, b) => a.localeCompare(b))
    : []
  const counts = stickers.reduce<Record<string, number>>((acc, item) => {
    const mood = String(item.mood || 'unclear')
    acc[mood] = (acc[mood] || 0) + 1
    return acc
  }, {})
  const correctionItems = Array.isArray(corrections.items) ? corrections.items : []
  const referenceItems = Array.isArray(referenceIndex.items) ? referenceIndex.items : []
  const sortedItems = stickers
    .slice()
    .sort((a, b) => {
      const aMood = String(a.mood || '')
      const bMood = String(b.mood || '')
      const aRank = aMood === 'unclear' ? 0 : Boolean(a.confirmed) ? 2 : 1
      const bRank = bMood === 'unclear' ? 0 : Boolean(b.confirmed) ? 2 : 1
      if (aRank !== bRank) {
        return aRank - bRank
      }
      return String(a.file || '').localeCompare(String(b.file || ''))
    })
  return {
    assetDir,
    updatedAt: String(manifest.updated_at || ''),
    total: stickers.length,
    moods,
    counts,
    unclear: counts.unclear || 0,
    confirmed: stickers.filter((item) => Boolean(item.confirmed)).length,
    unconfirmed: stickers.filter((item) => !Boolean(item.confirmed)).length,
    ocr: stickers.filter((item) => String(item.ocr_text || '').trim()).length,
    autoSend: stickers.filter((item) => Boolean(item.auto_send)).length,
    corrections: correctionItems.length,
    referenceItems: referenceItems.length,
    items: sortedItems.slice(0, 240).map((item) => ({
      file: String(item.file || ''),
      mood: String(item.mood || ''),
      moodLabel: stickerMoodLabel(item.mood),
      ocrText: String(item.ocr_text || ''),
      clipMood: String(item.clip_mood || ''),
      clipMoodLabel: stickerMoodLabel(item.clip_mood),
      clipConfidence: Number(item.clip_confidence || 0),
      confirmed: Boolean(item.confirmed),
      autoSend: Boolean(item.auto_send),
      weight: Number(item.weight || 1)
    }))
  }
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
  ipcMain.handle('xinyu:get-proactive-inbox', async () => {
    return await gateway?.getProactiveInbox()
  })
  ipcMain.handle('xinyu:get-memory-growth-candidates', async () => {
    return await gateway?.getMemoryGrowthCandidates()
  })
  ipcMain.handle('xinyu:get-impulse-soup-state', () => {
    return readImpulseSoupState()
  })
  ipcMain.handle('xinyu:get-gateway-status', () => {
    return gateway?.getStatus() || lastStatus
  })
  ipcMain.handle('xinyu:get-external-plugins', async () => {
    return await gateway?.getExternalPlugins()
  })
  ipcMain.handle('xinyu:set-external-plugin-config', async (_event, request: unknown) => {
    const payload =
      request && typeof request === 'object'
        ? (request as { pluginId?: unknown; enabled?: unknown; proactiveEnabled?: unknown; config?: unknown })
        : {}
    return await gateway?.setExternalPluginConfig({
      pluginId: String(payload.pluginId || ''),
      enabled: typeof payload.enabled === 'boolean' ? payload.enabled : undefined,
      proactiveEnabled: typeof payload.proactiveEnabled === 'boolean' ? payload.proactiveEnabled : undefined,
      config: payload.config && typeof payload.config === 'object' ? (payload.config as Record<string, unknown>) : {}
    })
  })
  ipcMain.handle('xinyu:install-external-plugin', async (_event, request: unknown) => {
    const payload =
      request && typeof request === 'object' ? (request as { pluginId?: unknown; options?: unknown }) : {}
    return await gateway?.installExternalPlugin({
      pluginId: String(payload.pluginId || ''),
      options: payload.options && typeof payload.options === 'object' ? (payload.options as Record<string, unknown>) : {}
    })
  })
  ipcMain.handle('xinyu:get-api-config-status', () => {
    return getApiConfigStatus(resolveXinYuCoreDir())
  })
  ipcMain.handle('xinyu:save-api-config-profile', (_event, profile: unknown) => {
    return saveApiConfigProfile(resolveXinYuCoreDir(), profile && typeof profile === 'object' ? profile : {})
  })
  ipcMain.handle('xinyu:test-api-config-profile', async (_event, profile: unknown) => {
    return await testApiConfigProfile(resolveXinYuCoreDir(), profile && typeof profile === 'object' ? profile : {})
  })
  ipcMain.handle('xinyu:delete-api-config-profile', (_event, profileId: unknown) => {
    return deleteApiConfigProfile(resolveXinYuCoreDir(), profileId)
  })
  ipcMain.handle('xinyu:apply-api-config-profile', async (_event, request: unknown) => {
    const payload =
      request && typeof request === 'object' ? (request as { profileId?: unknown; restartCore?: unknown }) : {}
    return await applyApiConfigProfile(resolveXinYuWorkspace(), resolveXinYuCoreDir(), payload.profileId, payload.restartCore)
  })
  ipcMain.handle('xinyu:restart-core-bridge', async () => {
    const status = getApiConfigStatus(resolveXinYuCoreDir())
    return await restartCoreBridge(resolveXinYuWorkspace(), resolveXinYuCoreDir(), status.current.allowInsecureHttp)
  })
  ipcMain.handle('xinyu:get-sticker-library', () => {
    return readStickerLibrarySummary()
  })
  ipcMain.handle('xinyu:run-sticker-maintenance', async (_event, action: unknown) => {
    return await runStickerMaintenance(action)
  })
  ipcMain.handle('xinyu:move-sticker-to-mood', async (_event, request: unknown) => {
    return await moveStickerToMood(request)
  })
  ipcMain.handle('xinyu:open-sticker-asset-dir', async () => {
    const assetDir = String(readStickerLibrarySummary().assetDir || '')
    if (!assetDir || !existsSync(assetDir)) {
      throw new Error('未找到表情资源目录')
    }
    const error = await shell.openPath(assetDir)
    return { ok: !error, assetDir, error }
  })
  ipcMain.handle('xinyu:get-qq-environment-status', async () => {
    return await getQQEnvironmentStatus()
  })
  ipcMain.handle('xinyu:start-qq-environment', async () => {
    return await startQQEnvironment()
  })
  ipcMain.handle('xinyu:open-napcat-webui', async () => {
    return await openNapCatWebUI()
  })
  ipcMain.handle('xinyu:copy-napcat-webui-token', async () => {
    return await copyNapCatWebUIToken()
  })
  ipcMain.handle('xinyu:get-qq-runtime-config', () => {
    return getQQRuntimeConfig()
  })
  ipcMain.handle('xinyu:set-qq-runtime-config', async (_event, patch: unknown) => {
    return await setQQRuntimeConfig(patch)
  })
  ipcMain.handle('xinyu:restart-qq-gateway', async () => {
    return await restartQQGateway()
  })
  ipcMain.handle('xinyu:send-chat', async (_event, request: unknown) => {
    const payload =
      request && typeof request === 'object'
        ? (request as {
            text?: unknown
            commandId?: unknown
            codexMode?: unknown
            allowLocalWrite?: unknown
            proactiveCandidateId?: unknown
            proactivePreview?: unknown
          })
        : {}
    return await gateway?.sendChat({
      text: String(payload.text || ''),
      commandId: String(payload.commandId || ''),
      codexMode: Boolean(payload.codexMode),
      allowLocalWrite: Boolean(payload.allowLocalWrite),
      proactiveCandidateId: String(payload.proactiveCandidateId || ''),
      proactivePreview: String(payload.proactivePreview || '')
    })
  })
  ipcMain.handle('xinyu:ack-proactive', async (_event, request: unknown) => {
    const payload =
      request && typeof request === 'object' ? (request as { candidateId?: unknown; action?: unknown }) : {}
    return await gateway?.ackProactive({
      candidateId: String(payload.candidateId || ''),
      action: String(payload.action || '') as 'read_locally' | 'approve_qq' | 'dismiss' | 'reply'
    })
  })
  ipcMain.handle('xinyu:decide-self-action-approval', async (_event, request: unknown) => {
    const payload =
      request && typeof request === 'object'
        ? (request as {
            queueId?: unknown
            decision?: unknown
            reason?: unknown
            execute?: unknown
            authorizeCodex?: unknown
            authorizeExisting?: unknown
          })
        : {}
    const decision = String(payload.decision || '') === 'denied' ? 'denied' : 'approved'
    return await gateway?.decideSelfActionApproval({
      queueId: String(payload.queueId || 'latest'),
      decision,
      reason: String(payload.reason || ''),
      execute: payload.execute !== false,
      authorizeCodex: Boolean(payload.authorizeCodex),
      authorizeExisting: Boolean(payload.authorizeExisting)
    })
  })
  ipcMain.handle('xinyu:list-metabolism-tickets', async (_event, statuses: unknown) => {
    return await gateway?.listMetabolismTickets(String(statuses || 'requested,approved,running'))
  })
  ipcMain.handle('xinyu:yield-compute', async (_event, request: unknown) => {
    const payload =
      request && typeof request === 'object'
        ? (request as { ticketId?: unknown; seconds?: unknown; note?: unknown })
        : {}
    const seconds = Number(payload.seconds || 600)
    return await gateway?.yieldCompute({
      ticketId: String(payload.ticketId || ''),
      seconds: Number.isFinite(seconds) ? seconds : 600,
      note: String(payload.note || '')
    })
  })
  ipcMain.handle('xinyu:maintain-boundary', async (_event, request: unknown) => {
    const payload =
      request && typeof request === 'object' ? (request as { ticketId?: unknown; note?: unknown }) : {}
    return await gateway?.maintainBoundary({
      ticketId: String(payload.ticketId || ''),
      note: String(payload.note || '')
    })
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
