import { BrowserWindow, clipboard } from 'electron'
import { execSync, spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync, readdirSync, renameSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
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
  napcatQQLoggedIn: boolean | null
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
const START_SCRIPT_CANDIDATES = [
  join(XINYU_ROOT, 'Start-XinYu-QQ.ps1'),
  join(XINYU_ROOT, 'scripts', 'Start-XinYu-QQ.ps1')
]
const NAPCAT_ROOT =
  process.env.XINYU_NAPCAT_ROOT ||
  firstExistingPath([
    join(XINYU_ROOT, 'runtime', 'deps', 'NapCatQQ', 'NapCat.44498.Shell'),
    join(XINYU_ROOT, 'NapCatQQ', 'NapCat.44498.Shell')
  ])
const NAPCAT_BAT = join(NAPCAT_ROOT, 'napcat.bat')
const NAPCAT_UTF8_LAUNCHER = join(NAPCAT_ROOT, 'start_napcat_utf8.ps1')
const NAPCAT_START_TIMEOUT_MS = 90_000
const NAPCAT_WEBUI_URL = process.env.XINYU_NAPCAT_WEBUI_URL || 'http://127.0.0.1:6099/webui/'
const NAPCAT_WEBUI_LOGIN_URL =
  process.env.XINYU_NAPCAT_WEBUI_LOGIN_URL || 'http://127.0.0.1:6099/webui/web_login'

let napCatWebUIWindow: BrowserWindow | null = null
type NapCatWebUIAuth = { token: string; credential: string; checked: boolean }
let napCatAuthCache: ({ key: string; checkedAt: number } & NapCatWebUIAuth) | null = null

function firstExistingPath(candidates: string[]): string {
  return candidates.find((candidate) => existsSync(candidate)) || candidates[0]
}

function resolveStartScriptPath(): string {
  return START_SCRIPT_CANDIDATES.find((candidate) => existsSync(candidate)) || ''
}

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

const QQ_GATEWAY_RESTART_DRAIN_SECONDS = 20
const QQ_GATEWAY_RESTART_TIMEOUT_MS = (QQ_GATEWAY_RESTART_DRAIN_SECONDS + 90) * 1000

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

  const restartArgs = [
    '-ForceRestart',
    '-RestartDrainTimeoutSeconds',
    String(QQ_GATEWAY_RESTART_DRAIN_SECONDS)
  ]

  try {
    await runPowerShellFile(script, restartArgs, XINYU_CORE_DIR, QQ_GATEWAY_RESTART_TIMEOUT_MS)
  } catch (error) {
    const timedOut = error instanceof Error && error.message === 'powershell_file_timeout'
    if (timedOut) {
      const qqGateway = await tcpProbe('qqGateway', 'QQ 网关 6199', '127.0.0.1', 6199)
      if (qqGateway.ok) {
        return {
          accepted: true,
          message: 'gateway_restarted',
          config: getQQRuntimeConfig(),
          status: await getQQEnvironmentStatus()
        }
      }
    }
    return {
      accepted: false,
      message: 'gateway_restart_failed',
      config: getQQRuntimeConfig(),
      status: await getQQEnvironmentStatus(),
      error: errorLabel(error)
    }
  }

  return {
    accepted: true,
    message: 'gateway_restarted',
    config: getQQRuntimeConfig(),
    status: await getQQEnvironmentStatus()
  }
}

export async function getQQEnvironmentStatus(): Promise<QQEnvironmentStatus> {
  const [coreBridge, qqGateway, napcatWebui, napcatReverseWs] = await Promise.all([
    tcpProbe('coreBridge', '核心 8765', '127.0.0.1', 8765),
    tcpProbe('qqGateway', 'QQ 网关 6199', '127.0.0.1', 6199),
    tcpProbe('napcatWebui', 'NapCat 网页端 6099', '127.0.0.1', 6099),
    establishedProbe()
  ])
  const services = [coreBridge, qqGateway, napcatWebui, napcatReverseWs]
  const webuiAuth = await resolveNapCatWebUIAuth(napcatWebui.ok)
  const tokenAvailable = Boolean(webuiAuth.token)
  const napcatQQLoggedIn = webuiAuth.credential ? await getNapCatQQLoggedIn(webuiAuth.credential) : null
  return {
    checkedAt: new Date().toISOString(),
    allReady: services.every((service) => service.ok),
    webuiUrl: NAPCAT_WEBUI_URL,
    webuiLoginUrl: NAPCAT_WEBUI_LOGIN_URL,
    tokenAvailable,
    napcatQQLoggedIn,
    diagnosis: qqEnvironmentDiagnosis(services, tokenAvailable, napcatQQLoggedIn),
    services,
    lastError: ''
  }
}

function readQQGatewayConfig(): Record<string, unknown> {
  if (!existsSync(QQ_GATEWAY_CONFIG_PATH)) {
    throw new Error(`QQ 网关配置未找到：${QQ_GATEWAY_CONFIG_PATH}`)
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

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

export async function startQQEnvironment(): Promise<QQEnvironmentActionResult> {
  const status = await getQQEnvironmentStatus()
  const byKey = Object.fromEntries(status.services.map((service) => [service.key, service])) as Partial<
    Record<ServiceProbe['key'], ServiceProbe>
  >
  const coreUp = Boolean(byKey.coreBridge?.ok)
  const gatewayUp = Boolean(byKey.qqGateway?.ok)
  const napcatUp = Boolean(byKey.napcatWebui?.ok)

  if (coreUp && gatewayUp && !napcatUp) {
    try {
      const probe = await ensureNapCatRunning()
      return {
        accepted: probe.ok,
        message: probe.ok ? 'napcat_started' : 'start_failed',
        error: probe.ok ? undefined : 'NapCat 6099 未就绪',
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

  const startScript = resolveStartScriptPath()
  if (!startScript) {
    return {
      accepted: false,
      message: 'start_script_missing',
      error: START_SCRIPT_CANDIDATES.join(' | '),
      status
    }
  }

  try {
    const child = spawn(
      'powershell.exe',
      ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', startScript, '-NapCatConsoleWindowStyle', 'Hidden'],
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
      status
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
    const webuiReady = await ensureNapCatRunning()
    if (!webuiReady.ok) {
      return {
        accepted: false,
        message: 'webui_open_failed',
        error: 'NapCat 6099 未就绪，自动拉起失败',
        status: await getQQEnvironmentStatus()
      }
    }
    const auth = await resolveNapCatWebUIAuth(true)
    if (auth.checked && auth.token && !auth.credential) {
      return {
        accepted: false,
        message: 'webui_token_invalid',
        error: 'configured token was rejected by running NapCat',
        status: await getQQEnvironmentStatus()
      }
    }
    const webuiWindow = getNapCatWebUIWindow()
    await webuiWindow.loadURL(auth.token ? buildNapCatWebUILoginUrl(auth.token) : NAPCAT_WEBUI_LOGIN_URL)
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
  const webuiReady = await tcpProbe('napcatWebui', 'NapCat 网页端 6099', '127.0.0.1', 6099)
  const auth = await resolveNapCatWebUIAuth(webuiReady.ok)
  if (!auth.token) {
    return {
      accepted: false,
      message: 'webui_token_missing',
      status: await getQQEnvironmentStatus()
    }
  }
  if (webuiReady.ok && auth.checked && !auth.credential) {
    return {
      accepted: false,
      message: 'webui_token_invalid',
      error: 'configured token was rejected by running NapCat',
      status: await getQQEnvironmentStatus()
    }
  }

  clipboard.writeText(auth.token)
  return {
    accepted: true,
    message: 'webui_token_copied',
    status: await getQQEnvironmentStatus()
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function napCatBootProcessRunning(): boolean {
  try {
    const output = execSync('tasklist /FI "IMAGENAME eq NapCatWinBootMain.exe" /NH', {
      encoding: 'utf8',
      windowsHide: true
    })
    return output.toLowerCase().includes('napcatwinbootmain.exe')
  } catch {
    return false
  }
}

function startNapCatProcess(): void {
  const launcher = existsSync(NAPCAT_BAT) ? NAPCAT_BAT : NAPCAT_UTF8_LAUNCHER
  if (!existsSync(launcher)) {
    throw new Error(`napcat launcher not found: ${launcher}`)
  }
  // NapCatWinBootMain needs a real console; hidden PowerShell spawn often fails silently.
  const child = spawn('C:\\Windows\\System32\\cmd.exe', ['/k', launcher], {
    cwd: NAPCAT_ROOT,
    detached: true,
    stdio: 'ignore',
    windowsHide: false
  })
  child.unref()
}

async function waitForTcpProbe(
  key: ServiceProbe['key'],
  label: string,
  host: string,
  port: number,
  timeoutMs: number,
  intervalMs = 2000
): Promise<ServiceProbe> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const probe = await tcpProbe(key, label, host, port)
    if (probe.ok) {
      return probe
    }
    await delay(intervalMs)
  }
  return tcpProbe(key, label, host, port)
}

async function ensureNapCatRunning(timeoutMs = NAPCAT_START_TIMEOUT_MS): Promise<ServiceProbe> {
  const probe = await tcpProbe('napcatWebui', 'NapCat 网页端 6099', '127.0.0.1', 6099)
  if (probe.ok) {
    return probe
  }
  if (!napCatBootProcessRunning()) {
    startNapCatProcess()
  }
  return waitForTcpProbe('napcatWebui', 'NapCat 网页端 6099', '127.0.0.1', 6099, timeoutMs)
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
    title: 'NapCat 网页端',
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

function qqEnvironmentDiagnosis(services: ServiceProbe[], tokenAvailable: boolean, napcatQQLoggedIn: boolean | null): string {
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
  if (!byKey.napcatReverseWs?.ok && napcatQQLoggedIn === false) {
    return 'napcat_qq_login_required'
  }
  if (!byKey.napcatReverseWs?.ok && tokenAvailable) {
    return 'napcat_login_required'
  }
  if (!byKey.napcatReverseWs?.ok) {
    return 'napcat_ws_waiting'
  }
  return 'partial'
}

async function resolveNapCatWebUIAuth(validateWithRunningWebUI: boolean): Promise<NapCatWebUIAuth> {
  const candidates = readNapCatWebUITokenCandidates()
  const key = candidates.join('\n')
  if (!validateWithRunningWebUI) {
    return { token: candidates[0] || '', credential: '', checked: false }
  }
  if (napCatAuthCache && napCatAuthCache.key === key && Date.now() - napCatAuthCache.checkedAt < 30_000) {
    return { token: napCatAuthCache.token, credential: napCatAuthCache.credential, checked: napCatAuthCache.checked }
  }

  let checked = false
  for (const token of candidates) {
    const result = await getNapCatWebUICredential(token)
    checked ||= result.checked
    if (result.credential) {
      napCatAuthCache = { key, checkedAt: Date.now(), token, credential: result.credential, checked: true }
      return { token, credential: result.credential, checked: true }
    }
  }

  const fallback = { token: candidates[0] || '', credential: '', checked }
  napCatAuthCache = { key, checkedAt: Date.now(), ...fallback }
  return fallback
}

async function getNapCatWebUICredential(token: string): Promise<{ credential: string; checked: boolean }> {
  try {
    const hash = createHash('sha256').update(`${token}.napcat`).digest('hex')
    const login = await postNapCatApi('/auth/login', { hash })
    return { credential: String(asRecord(login.data).Credential || '').trim(), checked: true }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error || '')
    return { credential: '', checked: message.startsWith('napcat_api_http_') }
  }
}

async function getNapCatQQLoggedIn(credential: string): Promise<boolean | null> {
  try {
    const status = await postNapCatApi('/QQLogin/CheckLoginStatus', {}, credential)
    const data = asRecord(status.data)
    return typeof data.isLogin === 'boolean' ? data.isLogin : null
  } catch {
    return null
  }
}

async function postNapCatApi(path: string, body: Record<string, unknown>, credential = ''): Promise<Record<string, unknown>> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  }
  if (credential) {
    headers.Authorization = `Bearer ${credential}`
  }
  const response = await fetch(`http://127.0.0.1:6099/api${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(3000)
  })
  if (!response.ok) {
    throw new Error(`napcat_api_http_${response.status}`)
  }
  return (await response.json()) as Record<string, unknown>
}

function readNapCatWebUITokenCandidates(): string[] {
  const candidates = [
    process.env.NAPCAT_WEBUI_SECRET_KEY,
    readNapCatWebUITokenFromConfig(),
    ...readNapCatWebUITokenCandidatesFromLogs()
  ]
  return candidates
    .map((value) => String(value || '').trim())
    .filter(Boolean)
    .filter(isNapCatWebUITokenCandidate)
    .filter((value, index, items) => items.indexOf(value) === index)
}

function isNapCatWebUITokenCandidate(value: string): boolean {
  return /^[\x21-\x7e]{6,256}$/.test(value)
}

function readNapCatWebUITokenFromConfig(): string {
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

function readNapCatWebUITokenCandidatesFromLogs(): string[] {
  const configPath = resolveNapCatWebUIConfigPath()
  if (!configPath) {
    return []
  }
  const logsPath = join(dirname(configPath), '..', 'logs')
  if (!existsSync(logsPath)) {
    return []
  }
  try {
    return readdirSync(logsPath, { withFileTypes: true })
      .filter((entry) => entry.isFile())
      .map((entry) => {
        const path = join(logsPath, entry.name)
        return { path, mtimeMs: statSync(path).mtimeMs }
      })
      .sort((left, right) => right.mtimeMs - left.mtimeMs)
      .slice(0, 5)
      .flatMap((entry) => readNapCatWebUITokenCandidatesFromLog(entry.path))
  } catch {
    return []
  }
}

function readNapCatWebUITokenCandidatesFromLog(path: string): string[] {
  try {
    return readFileSync(path, 'utf-8')
      .split(/\r?\n/)
      .slice(-500)
      .map((line) => {
        const match = line.match(/WebUi Token:\s*(\S+)/i) || line.match(/WebUI Token\b.*?(\S+)$/i)
        return match ? match[1] : ''
      })
      .filter(Boolean)
  } catch {
    return []
  }
}

function buildNapCatWebUILoginUrl(token: string): string {
  if (!token) {
    return NAPCAT_WEBUI_LOGIN_URL
  }
  try {
    const url = new URL(NAPCAT_WEBUI_LOGIN_URL)
    url.searchParams.set('token', token)
    return url.toString()
  } catch {
    const joiner = NAPCAT_WEBUI_LOGIN_URL.includes('?') ? '&' : '?'
    return `${NAPCAT_WEBUI_LOGIN_URL}${joiner}token=${encodeURIComponent(token)}`
  }
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
      label: 'NapCat → 网关',
      endpoint,
      ok,
      detail: ok ? 'ws_established' : 'ws_not_connected'
    }
  } catch (error) {
    return {
      key: 'napcatReverseWs',
      label: 'NapCat → 网关',
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
