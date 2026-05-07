import { BrowserWindow, clipboard } from 'electron'
import { spawn } from 'node:child_process'
import { existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { Socket } from 'node:net'

export type ServiceProbe = {
  key: 'coreBridge' | 'qqGateway' | 'napcatWebui' | 'napcatReverseWs'
  label: string
  endpoint: string
  ok: boolean
  detail: string
}

export type QQEnvironmentStatus = {
  checkedAt: string
  allReady: boolean
  webuiUrl: string
  webuiLoginUrl: string
  tokenAvailable: boolean
  diagnosis: string
  services: ServiceProbe[]
  lastError: string
}

export type QQEnvironmentActionResult = {
  accepted: boolean
  message: string
  status?: QQEnvironmentStatus
  error?: string
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
  allowExternalPrivate?: unknown
  allowGroupMessages?: unknown
  allowedGroupIds?: unknown
  groupShadowEnabled?: unknown
  groupShadowAllowedGroupIds?: unknown
  blockedUserIds?: unknown
  blockedGroupIds?: unknown
  sendReplies?: unknown
}

export type QQRuntimeConfigActionResult = QQEnvironmentActionResult & {
  config?: QQRuntimeConfig
  notes?: string[]
}

const XINYU_ROOT = process.env.XINYU_ROOT || 'D:\\XinYu'
const XINYU_CORE_DIR = join(XINYU_ROOT, 'XinYu-Core', 'examples', 'agent-apps', 'xinyu')
const QQ_GATEWAY_CONFIG_PATH = join(XINYU_CORE_DIR, 'xinyu_qq_gateway.config.json')
const START_SCRIPT = join(XINYU_ROOT, 'Start-XinYu-QQ.ps1')
const NAPCAT_ROOT = process.env.XINYU_NAPCAT_ROOT || join(XINYU_ROOT, 'NapCatQQ', 'NapCat.44498.Shell')
const NAPCAT_WEBUI_URL = process.env.XINYU_NAPCAT_WEBUI_URL || 'http://127.0.0.1:6099/webui/'
const NAPCAT_WEBUI_LOGIN_URL =
  process.env.XINYU_NAPCAT_WEBUI_LOGIN_URL || 'http://127.0.0.1:6099/webui/web_login'

let napCatWebUIWindow: BrowserWindow | null = null

export function getQQRuntimeConfig(): QQRuntimeConfig {
  return normalizeQQRuntimeConfig(readQQGatewayConfig())
}

export async function setQQRuntimeConfig(patchValue: unknown): Promise<QQRuntimeConfigActionResult> {
  const patch = patchValue && typeof patchValue === 'object' ? (patchValue as QQRuntimeConfigPatch) : {}
  const raw = readQQGatewayConfig()
  const notes: string[] = []
  let changed = false

  if (hasPatchKey(patch, 'allowExternalPrivate')) {
    raw.require_whitelist = !Boolean(patch.allowExternalPrivate)
    changed = true
  }

  if (hasPatchKey(patch, 'allowedGroupIds')) {
    const nextIds = idList(patch.allowedGroupIds)
    if (booleanValue(raw.allow_group_messages, false) && !nextIds.length) {
      return {
        accepted: false,
        message: 'group_reply_scope_missing',
        config: normalizeQQRuntimeConfig(raw),
        status: await getQQEnvironmentStatus()
      }
    }
    raw.allowed_group_ids = nextIds
    changed = true
  }

  if (hasPatchKey(patch, 'groupShadowAllowedGroupIds')) {
    raw.group_shadow_allowed_group_ids = idList(patch.groupShadowAllowedGroupIds)
    changed = true
  }

  if (hasPatchKey(patch, 'blockedUserIds')) {
    const ownerIds = new Set(stringList(raw.owner_user_ids))
    const requestedIds = idList(patch.blockedUserIds)
    const nextIds = requestedIds.filter((item) => !ownerIds.has(item))
    if (nextIds.length !== requestedIds.length) {
      notes.push('owner_user_block_removed')
    }
    raw.blocked_user_ids = nextIds
    changed = true
  }

  if (hasPatchKey(patch, 'blockedGroupIds')) {
    raw.blocked_group_ids = idList(patch.blockedGroupIds)
    changed = true
  }

  if (hasPatchKey(patch, 'allowGroupMessages')) {
    const enabled = Boolean(patch.allowGroupMessages)
    if (enabled) {
      const allowedGroupIds = stringList(raw.allowed_group_ids)
      if (!allowedGroupIds.length) {
        const shadowGroupIds = stringList(raw.group_shadow_allowed_group_ids)
        if (!shadowGroupIds.length) {
          return {
            accepted: false,
            message: 'group_reply_scope_missing',
            config: normalizeQQRuntimeConfig(raw),
            status: await getQQEnvironmentStatus()
          }
        }
        raw.allowed_group_ids = shadowGroupIds
        notes.push('group_reply_scope_copied_from_shadow')
      }
      if (!String(raw.group_trigger_mode || '').trim()) {
        raw.group_trigger_mode = 'mention_or_prefix'
      }
    }
    raw.allow_group_messages = enabled
    changed = true
  }

  if (hasPatchKey(patch, 'groupShadowEnabled')) {
    raw.group_shadow_enabled = Boolean(patch.groupShadowEnabled)
    changed = true
  }

  if (hasPatchKey(patch, 'sendReplies')) {
    raw.send_replies = Boolean(patch.sendReplies)
    changed = true
  }

  if (changed) {
    writeQQGatewayConfig(raw)
  }

  const restart = await restartQQGateway()
  return {
    accepted: restart.accepted,
    message: restart.accepted ? 'runtime_config_applied' : 'runtime_config_saved_restart_failed',
    config: getQQRuntimeConfig(),
    status: restart.status,
    error: restart.error,
    notes
  }
}

export async function restartQQGateway(): Promise<QQRuntimeConfigActionResult> {
  const script = join(XINYU_CORE_DIR, 'start_xinyu_qq_gateway.ps1')
  if (!existsSync(script)) {
    return {
      accepted: false,
      message: 'gateway_start_script_missing',
      config: existsSync(QQ_GATEWAY_CONFIG_PATH) ? getQQRuntimeConfig() : undefined,
      status: await getQQEnvironmentStatus(),
      error: script
    }
  }

  try {
    await runPowerShellFile(script, ['-ForceRestart', '-RestartDrainTimeoutSeconds', '20'], XINYU_CORE_DIR, 90_000)
    return {
      accepted: true,
      message: 'gateway_restarted',
      config: getQQRuntimeConfig(),
      status: await getQQEnvironmentStatus()
    }
  } catch (error) {
    return {
      accepted: false,
      message: 'gateway_restart_failed',
      config: getQQRuntimeConfig(),
      status: await getQQEnvironmentStatus(),
      error: errorLabel(error)
    }
  }
}

export async function getQQEnvironmentStatus(): Promise<QQEnvironmentStatus> {
  const [coreBridge, qqGateway, napcatWebui, napcatReverseWs] = await Promise.all([
    tcpProbe('coreBridge', 'Core 8765', '127.0.0.1', 8765),
    tcpProbe('qqGateway', 'QQ Gateway 6199', '127.0.0.1', 6199),
    tcpProbe('napcatWebui', 'NapCat WebUI 6099', '127.0.0.1', 6099),
    establishedProbe()
  ])
  const services = [coreBridge, qqGateway, napcatWebui, napcatReverseWs]
  const tokenAvailable = Boolean(readNapCatWebUIToken())
  return {
    checkedAt: new Date().toISOString(),
    allReady: services.every((service) => service.ok),
    webuiUrl: NAPCAT_WEBUI_URL,
    webuiLoginUrl: NAPCAT_WEBUI_LOGIN_URL,
    tokenAvailable,
    diagnosis: qqEnvironmentDiagnosis(services, tokenAvailable),
    services,
    lastError: ''
  }
}

function readQQGatewayConfig(): Record<string, unknown> {
  if (!existsSync(QQ_GATEWAY_CONFIG_PATH)) {
    throw new Error(`QQ gateway config not found: ${QQ_GATEWAY_CONFIG_PATH}`)
  }
  return JSON.parse(readFileSync(QQ_GATEWAY_CONFIG_PATH, 'utf-8')) as Record<string, unknown>
}

function writeQQGatewayConfig(raw: Record<string, unknown>): void {
  const tmpPath = `${QQ_GATEWAY_CONFIG_PATH}.tmp`
  writeFileSync(tmpPath, `${JSON.stringify(raw, null, 2)}\n`, 'utf-8')
  renameSync(tmpPath, QQ_GATEWAY_CONFIG_PATH)
}

function normalizeQQRuntimeConfig(raw: Record<string, unknown>): QQRuntimeConfig {
  const requireWhitelist = booleanValue(raw.require_whitelist, true)
  const allowGroupMessages = booleanValue(raw.allow_group_messages, true)
  const allowedGroupIds = stringList(raw.allowed_group_ids)
  const groupShadowAllowedGroupIds = stringList(raw.group_shadow_allowed_group_ids)
  const notes: string[] = []
  if (allowGroupMessages && !allowedGroupIds.length) {
    notes.push('group_replies_unscoped')
  }
  if (!groupShadowAllowedGroupIds.length && booleanValue(raw.group_shadow_enabled, false)) {
    notes.push('group_shadow_unscoped')
  }
  return {
    configPath: QQ_GATEWAY_CONFIG_PATH,
    loadedAt: new Date().toISOString(),
    requireWhitelist,
    allowExternalPrivate: !requireWhitelist,
    allowGroupMessages,
    allowedGroupIds,
    groupTriggerMode: String(raw.group_trigger_mode || 'mention_or_prefix'),
    groupShadowEnabled: booleanValue(raw.group_shadow_enabled, false),
    groupShadowAllowedGroupIds,
    groupShadowMaxTextChars: numberValue(raw.group_shadow_max_text_chars, 260),
    blockedUserIds: stringList(raw.blocked_user_ids).filter((item) => !stringList(raw.owner_user_ids).includes(item)),
    blockedGroupIds: stringList(raw.blocked_group_ids),
    sendReplies: booleanValue(raw.send_replies, true),
    ownerUserIds: stringList(raw.owner_user_ids),
    whitelistUserIds: stringList(raw.whitelist_user_ids),
    trustedUserIds: stringList(raw.trusted_user_ids),
    notes
  }
}

function hasPatchKey(patch: QQRuntimeConfigPatch, key: keyof QQRuntimeConfigPatch): boolean {
  return Object.prototype.hasOwnProperty.call(patch, key)
}

function booleanValue(value: unknown, fallback: boolean): boolean {
  return typeof value === 'boolean' ? value : fallback
}

function numberValue(value: unknown, fallback: number): number {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value
        .map((item) => String(item || '').trim())
        .filter(Boolean)
        .filter((item, index, items) => items.indexOf(item) === index)
    : []
}

function idList(value: unknown): string[] {
  return stringList(value).filter((item) => /^\d{5,20}$/.test(item))
}

export async function startQQEnvironment(): Promise<QQEnvironmentActionResult> {
  if (!existsSync(START_SCRIPT)) {
    return {
      accepted: false,
      message: 'start_script_missing',
      error: START_SCRIPT,
      status: await getQQEnvironmentStatus()
    }
  }

  try {
    const child = spawn(
      'powershell.exe',
      ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', START_SCRIPT, '-NapCatConsoleWindowStyle', 'Hidden'],
      {
        cwd: XINYU_ROOT,
        detached: true,
        stdio: 'ignore',
        windowsHide: true
      }
    )
    child.unref()
    return {
      accepted: true,
      message: 'start_requested',
      status: await getQQEnvironmentStatus()
    }
  } catch (error) {
    return {
      accepted: false,
      message: 'start_failed',
      error: errorLabel(error),
      status: await getQQEnvironmentStatus()
    }
  }
}

export async function openNapCatWebUI(): Promise<QQEnvironmentActionResult> {
  try {
    const webuiWindow = getNapCatWebUIWindow()
    if (!webuiWindow.webContents.getURL()) {
      await webuiWindow.loadURL(NAPCAT_WEBUI_URL)
    }
    webuiWindow.show()
    webuiWindow.focus()
    return {
      accepted: true,
      message: 'webui_opened',
      status: await getQQEnvironmentStatus()
    }
  } catch (error) {
    return {
      accepted: false,
      message: 'webui_open_failed',
      error: errorLabel(error),
      status: await getQQEnvironmentStatus()
    }
  }
}

export async function copyNapCatWebUIToken(): Promise<QQEnvironmentActionResult> {
  const token = readNapCatWebUIToken()
  if (!token) {
    return {
      accepted: false,
      message: 'webui_token_missing',
      status: await getQQEnvironmentStatus()
    }
  }

  clipboard.writeText(token)
  return {
    accepted: true,
    message: 'webui_token_copied',
    status: await getQQEnvironmentStatus()
  }
}

function getNapCatWebUIWindow(): BrowserWindow {
  if (napCatWebUIWindow && !napCatWebUIWindow.isDestroyed()) {
    return napCatWebUIWindow
  }

  napCatWebUIWindow = new BrowserWindow({
    width: 1080,
    height: 760,
    minWidth: 820,
    minHeight: 560,
    autoHideMenuBar: true,
    backgroundColor: '#f8f8fb',
    title: 'NapCat WebUI',
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  })
  napCatWebUIWindow.setMenuBarVisibility(false)
  napCatWebUIWindow.on('closed', () => {
    napCatWebUIWindow = null
  })
  return napCatWebUIWindow
}

function qqEnvironmentDiagnosis(services: ServiceProbe[], tokenAvailable: boolean): string {
  const byKey = Object.fromEntries(services.map((service) => [service.key, service])) as Partial<
    Record<ServiceProbe['key'], ServiceProbe>
  >
  if (services.every((service) => service.ok)) {
    return 'ready'
  }
  if (!byKey.coreBridge?.ok) {
    return 'core_offline'
  }
  if (!byKey.qqGateway?.ok) {
    return 'gateway_offline'
  }
  if (!byKey.napcatWebui?.ok) {
    return 'napcat_offline'
  }
  if (!byKey.napcatReverseWs?.ok && tokenAvailable) {
    return 'napcat_login_required'
  }
  if (!byKey.napcatReverseWs?.ok) {
    return 'napcat_ws_waiting'
  }
  return 'partial'
}

function readNapCatWebUIToken(): string {
  const configPath = resolveNapCatWebUIConfigPath()
  if (!configPath || !existsSync(configPath)) {
    return ''
  }
  try {
    const data = JSON.parse(readFileSync(configPath, 'utf-8')) as Record<string, unknown>
    for (const key of ['token', 'Token', 'webuiToken', 'webui_token', 'loginToken', 'login_token']) {
      const value = String(data[key] || '').trim()
      if (value) {
        return value
      }
    }
  } catch {
    return ''
  }
  return ''
}

function resolveNapCatWebUIConfigPath(): string {
  const envPath = String(process.env.XINYU_NAPCAT_WEBUI_CONFIG || '').trim()
  if (envPath) {
    return envPath
  }
  const versionsConfig = join(NAPCAT_ROOT, 'versions', 'config.json')
  try {
    const data = JSON.parse(readFileSync(versionsConfig, 'utf-8')) as { curVersion?: unknown; baseVersion?: unknown }
    const version = String(data.curVersion || data.baseVersion || '').trim()
    if (version) {
      return join(NAPCAT_ROOT, 'versions', version, 'resources', 'app', 'napcat', 'config', 'webui.json')
    }
  } catch {
    // Fall back to the installed shell path used by the bundled NapCat build.
  }
  return join(NAPCAT_ROOT, 'versions', '9.9.26-44498', 'resources', 'app', 'napcat', 'config', 'webui.json')
}

function tcpProbe(
  key: ServiceProbe['key'],
  label: string,
  host: string,
  port: number
): Promise<ServiceProbe> {
  return new Promise((resolve) => {
    const socket = new Socket()
    let done = false

    const finish = (ok: boolean, detail: string): void => {
      if (done) {
        return
      }
      done = true
      socket.destroy()
      resolve({
        key,
        label,
        endpoint: `${host}:${port}`,
        ok,
        detail
      })
    }

    socket.setTimeout(1200)
    socket.once('connect', () => finish(true, 'tcp_ready'))
    socket.once('timeout', () => finish(false, 'tcp_timeout'))
    socket.once('error', (error: NodeJS.ErrnoException) => finish(false, error.code || error.message || 'tcp_error'))
    socket.connect(port, host)
  })
}

async function establishedProbe(): Promise<ServiceProbe> {
  const endpoint = '127.0.0.1:6199/ws'
  const command =
    "Get-NetTCPConnection -LocalPort 6199 -State Established -ErrorAction SilentlyContinue | " +
    "Where-Object { $_.RemoteAddress -eq '127.0.0.1' } | Select-Object -First 1 | ForEach-Object { 'connected' }"
  try {
    const fastOutput = await runNetstat(1200)
    let ok = hasEstablishedLocalPort(fastOutput, 6199)
    if (!ok) {
      const output = await runPowerShell(command, 8000)
      ok = output.includes('connected')
    }
    return {
      key: 'napcatReverseWs',
      label: 'NapCat -> Gateway',
      endpoint,
      ok,
      detail: ok ? 'ws_established' : 'ws_not_connected'
    }
  } catch (error) {
    return {
      key: 'napcatReverseWs',
      label: 'NapCat -> Gateway',
      endpoint,
      ok: false,
      detail: errorLabel(error)
    }
  }
}

function hasEstablishedLocalPort(output: string, port: number): boolean {
  const localPort = `127.0.0.1:${port}`
  return output
    .split(/\r?\n/)
    .some((line) => line.includes(localPort) && /\bESTABLISHED\b/i.test(line))
}

function runNetstat(timeoutMs: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn('netstat.exe', ['-ano', '-p', 'tcp'], {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe']
    })
    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill()
      reject(new Error('netstat_timeout'))
    }, timeoutMs)

    child.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString()
    })
    child.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString()
    })
    child.on('error', (error) => {
      clearTimeout(timer)
      reject(error)
    })
    child.on('close', (code) => {
      clearTimeout(timer)
      if (code && stderr.trim()) {
        reject(new Error(stderr.trim()))
        return
      }
      resolve(stdout)
    })
  })
}

function runPowerShell(command: string, timeoutMs: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn('powershell.exe', ['-NoProfile', '-Command', command], {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe']
    })
    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill()
      reject(new Error('powershell_timeout'))
    }, timeoutMs)

    child.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString()
    })
    child.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString()
    })
    child.on('error', (error) => {
      clearTimeout(timer)
      reject(error)
    })
    child.on('close', (code) => {
      clearTimeout(timer)
      if (code && stderr.trim()) {
        reject(new Error(stderr.trim()))
        return
      }
      resolve(stdout.trim())
    })
  })
}

function runPowerShellFile(script: string, args: string[], cwd: string, timeoutMs: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn(
      'powershell.exe',
      ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, ...args],
      {
        cwd,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe']
      }
    )
    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill()
      reject(new Error('powershell_file_timeout'))
    }, timeoutMs)

    child.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString()
    })
    child.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString()
    })
    child.on('error', (error) => {
      clearTimeout(timer)
      reject(error)
    })
    child.on('close', (code) => {
      clearTimeout(timer)
      if (code) {
        reject(new Error((stderr || stdout || `powershell_file_exit_${code}`).trim()))
        return
      }
      resolve(stdout.trim())
    })
  })
}

function errorLabel(error: unknown): string {
  if (error && typeof error === 'object' && 'code' in error) {
    return String((error as { code?: unknown }).code || '')
  }
  return error instanceof Error ? `${error.name}: ${error.message}` : String(error)
}
