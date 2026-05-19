import { app } from 'electron'
import { execFile } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)

type EnvMap = Record<string, string>

type EnvLine = {
  raw: string
  key?: string
}

type ApiProfileStore = {
  version: number
  activeProfileId: string
  profiles: ApiConfigProfile[]
}

export type ApiConfigProfile = {
  id: string
  label: string
  provider: string
  model: string
  baseUrl: string
  apiKey: string
  allowInsecureHttp: boolean
  disableStreaming: boolean
  updatedAt: string
}

export type ApiConfigProfileSummary = Omit<ApiConfigProfile, 'apiKey'> & {
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
  profiles: ApiConfigProfileSummary[]
  notes: string[]
}

export type ApiConfigProfilePatch = {
  id?: unknown
  label?: unknown
  provider?: unknown
  model?: unknown
  baseUrl?: unknown
  apiKey?: unknown
  allowInsecureHttp?: unknown
  disableStreaming?: unknown
}

export type ApiConfigTestResult = {
  accepted: boolean
  ok: boolean
  checkedAt: string
  elapsedMs: number
  provider: string
  model: string
  baseUrl: string
  status: number
  replyPreview: string
  message: string
}

const LOCAL_ENV_NAME = 'xinyu.local.env'
const PROFILE_STORE_NAME = 'xinyu-api-profiles.json'

const ENV_KEYS = [
  'XINYU_API_KEY',
  'XINYU_BASE_URL',
  'XINYU_LLM_PROVIDER',
  'XINYU_LLM_MODEL',
  'XINYU_ALLOW_INSECURE_LLM_HTTP',
  'XINYU_DISABLE_STREAMING'
] as const

export function getApiConfigStatus(coreDir: string): ApiConfigStatus {
  const envPath = resolveLocalEnvPath(coreDir)
  const env = readLocalEnv(envPath).env
  const store = readProfileStore()
  const matchedActiveProfileId = matchActiveProfileId(store, env)
  return {
    ok: true,
    loadedAt: new Date().toISOString(),
    configPath: envPath,
    profilesPath: resolveProfileStorePath(),
    activeProfileId: matchedActiveProfileId,
    current: envToCurrent(envPath, env),
    profiles: store.profiles.map((profile) => summarizeProfile(profile, profile.id === matchedActiveProfileId)),
    notes: existsSync(envPath) ? [] : [`未找到 ${LOCAL_ENV_NAME}；应用资料时会自动创建。`]
  }
}

export function saveApiConfigProfile(coreDir: string, patch: ApiConfigProfilePatch): Record<string, unknown> {
  const store = readProfileStore()
  const env = readLocalEnv(resolveLocalEnvPath(coreDir)).env
  const id = safeProfileId(patch.id)
  const existing = id ? store.profiles.find((profile) => profile.id === id) : undefined
  const profile = normalizeProfilePatch(patch, existing, env)
  const nextProfiles = existing
    ? store.profiles.map((item) => (item.id === existing.id ? profile : item))
    : [...store.profiles, profile]
  writeProfileStore({ ...store, profiles: nextProfiles })
  return {
    accepted: true,
    message: existing ? 'api_profile_saved' : 'api_profile_created',
    profile: summarizeProfile(profile, false),
    status: getApiConfigStatus(coreDir)
  }
}

export async function testApiConfigProfile(coreDir: string, patch: ApiConfigProfilePatch): Promise<ApiConfigTestResult> {
  const store = readProfileStore()
  const env = readLocalEnv(resolveLocalEnvPath(coreDir)).env
  const id = safeProfileId(patch.id)
  const existing = id ? store.profiles.find((profile) => profile.id === id) : undefined
  const profile = normalizeProfilePatch(patch, existing, env)
  const started = Date.now()
  const checkedAt = new Date().toISOString()
  const baseUrl = profile.baseUrl.replace(/\/+$/, '')
  if (!baseUrl) {
    return apiConfigTestResult(profile, checkedAt, started, 0, '', 'missing_base_url')
  }
  if (!profile.model) {
    return apiConfigTestResult(profile, checkedAt, started, 0, '', 'missing_model')
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 60_000)
  try {
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'content-type': 'application/json',
        ...(profile.apiKey ? { authorization: `Bearer ${profile.apiKey}` } : {})
      },
      body: JSON.stringify({
        model: profile.model,
        messages: [
          { role: 'system', content: 'Return exactly: ok' },
          { role: 'user', content: 'ping' }
        ],
        max_tokens: 8,
        temperature: 0,
        stream: false
      })
    })
    const text = await response.text()
    let replyPreview = ''
    let errorMessage = ''
    let parsedJson = false
    try {
      const data = JSON.parse(text) as Record<string, unknown>
      parsedJson = true
      replyPreview = extractChatReplyPreview(data)
      errorMessage = extractApiErrorMessage(data)
    } catch {
      replyPreview = text.trim().slice(0, 120)
    }
    if (response.ok && !parsedJson) {
      return {
        accepted: true,
        ok: false,
        checkedAt,
        elapsedMs: Date.now() - started,
        provider: profile.provider,
        model: profile.model,
        baseUrl,
        status: response.status,
        replyPreview,
        message: 'api_test_non_json_response'
      }
    }
    if (response.ok && !replyPreview) {
      return {
        accepted: true,
        ok: false,
        checkedAt,
        elapsedMs: Date.now() - started,
        provider: profile.provider,
        model: profile.model,
        baseUrl,
        status: response.status,
        replyPreview,
        message: 'api_test_empty_reply'
      }
    }
    return {
      accepted: true,
      ok: response.ok,
      checkedAt,
      elapsedMs: Date.now() - started,
      provider: profile.provider,
      model: profile.model,
      baseUrl,
      status: response.status,
      replyPreview,
      message: response.ok ? 'api_test_ok' : compactTestMessage(errorMessage || response.statusText || 'api_test_failed')
    }
  } catch (error) {
    return apiConfigTestResult(
      profile,
      checkedAt,
      started,
      0,
      '',
      error instanceof Error && error.name === 'AbortError' ? 'api_test_timeout' : compactTestMessage(error)
    )
  } finally {
    clearTimeout(timer)
  }
}

export function deleteApiConfigProfile(coreDir: string, profileId: unknown): Record<string, unknown> {
  const id = safeProfileId(profileId)
  if (!id) {
    throw new Error('缺少 API 资料 ID')
  }
  const store = readProfileStore()
  const nextProfiles = store.profiles.filter((profile) => profile.id !== id)
  writeProfileStore({
    ...store,
    activeProfileId: store.activeProfileId === id ? '' : store.activeProfileId,
    profiles: nextProfiles
  })
  return {
    accepted: true,
    message: 'api_profile_deleted',
    profileId: id,
    status: getApiConfigStatus(coreDir)
  }
}

export async function applyApiConfigProfile(
  workspaceDir: string,
  coreDir: string,
  profileId: unknown,
  restartCore: unknown
): Promise<Record<string, unknown>> {
  const id = safeProfileId(profileId)
  if (!id) {
    throw new Error('缺少 API 资料 ID')
  }
  const store = readProfileStore()
  const profile = store.profiles.find((item) => item.id === id)
  if (!profile) {
    throw new Error(`未找到 API 资料：${id}`)
  }

  writeLocalEnv(resolveLocalEnvPath(coreDir), profileToEnvUpdates(profile))
  applyProfileToProcessEnv(profile)
  writeProfileStore({ ...store, activeProfileId: id })
  const restart = restartCore ? await restartCoreBridge(workspaceDir, coreDir, profile.allowInsecureHttp) : null
  return {
    accepted: true,
    message: restart ? 'api_profile_applied_core_restarted' : 'api_profile_applied',
    profile: summarizeProfile(profile, true),
    restart,
    status: getApiConfigStatus(coreDir)
  }
}

export async function restartCoreBridge(
  workspaceDir: string,
  coreDir: string,
  allowInsecureHttp?: boolean
): Promise<Record<string, unknown>> {
  const script = join(coreDir, 'start_xinyu_core_bridge.ps1')
  if (!existsSync(script)) {
    throw new Error(`未找到核心重启脚本：${script}`)
  }
  const args = ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, '-Port', '8765', '-ForceRestart']
  if (allowInsecureHttp) {
    args.push('-AllowInsecureLlmHttp')
  }
  const { stdout, stderr } = await execFileAsync('powershell.exe', args, {
    cwd: workspaceDir,
    encoding: 'utf-8',
    timeout: 120_000,
    windowsHide: true,
    env: {
      ...process.env,
      XINYU_ALLOW_INSECURE_LLM_HTTP: allowInsecureHttp ? '1' : '0'
    },
    maxBuffer: 1024 * 1024
  })
  return {
    accepted: true,
    message: 'core_bridge_restarted',
    stdout: String(stdout || '').slice(-3000),
    stderr: String(stderr || '').slice(-3000)
  }
}

function resolveLocalEnvPath(coreDir: string): string {
  return join(coreDir, LOCAL_ENV_NAME)
}

function resolveProfileStorePath(): string {
  return join(app.getPath('userData'), PROFILE_STORE_NAME)
}

function readProfileStore(): ApiProfileStore {
  const path = resolveProfileStorePath()
  try {
    const data = JSON.parse(readFileSync(path, 'utf-8')) as Partial<ApiProfileStore>
    return {
      version: 1,
      activeProfileId: String(data.activeProfileId || ''),
      profiles: Array.isArray(data.profiles) ? data.profiles.map(normalizeStoredProfile).filter(isApiConfigProfile) : []
    }
  } catch {
    return { version: 1, activeProfileId: '', profiles: [] }
  }
}

function writeProfileStore(store: ApiProfileStore): void {
  const path = resolveProfileStorePath()
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, `${JSON.stringify(store, null, 2)}\n`, 'utf-8')
}

function normalizeStoredProfile(value: unknown): ApiConfigProfile | null {
  if (!value || typeof value !== 'object') {
    return null
  }
  const raw = value as Record<string, unknown>
  const id = safeProfileId(raw.id)
  if (!id) {
    return null
  }
  return {
    id,
    label: safeText(raw.label, id),
    provider: safeText(raw.provider, 'ciallo'),
    model: safeText(raw.model, 'mimo-v2.5-pro'),
    baseUrl: safeText(raw.baseUrl, ''),
    apiKey: safeText(raw.apiKey, ''),
    allowInsecureHttp: Boolean(raw.allowInsecureHttp),
    disableStreaming: raw.disableStreaming !== false,
    updatedAt: safeText(raw.updatedAt, '')
  }
}

function isApiConfigProfile(value: ApiConfigProfile | null): value is ApiConfigProfile {
  return value !== null
}

function normalizeProfilePatch(
  patch: ApiConfigProfilePatch,
  existing: ApiConfigProfile | undefined,
  env: EnvMap
): ApiConfigProfile {
  const now = new Date().toISOString()
  const label = safeText(patch.label, existing?.label || '本地 API')
  const apiKeyPatch = typeof patch.apiKey === 'string' ? patch.apiKey.trim() : ''
  return {
    id: existing?.id || makeProfileId(label),
    label,
    provider: safeText(patch.provider, existing?.provider || env.XINYU_LLM_PROVIDER || 'ciallo'),
    model: safeText(patch.model, existing?.model || env.XINYU_LLM_MODEL || 'mimo-v2.5-pro'),
    baseUrl: safeText(patch.baseUrl, existing?.baseUrl || env.XINYU_BASE_URL || ''),
    apiKey: apiKeyPatch || existing?.apiKey || env.XINYU_API_KEY || '',
    allowInsecureHttp: Boolean(patch.allowInsecureHttp ?? existing?.allowInsecureHttp ?? env.XINYU_ALLOW_INSECURE_LLM_HTTP === '1'),
    disableStreaming: Boolean(patch.disableStreaming ?? existing?.disableStreaming ?? env.XINYU_DISABLE_STREAMING !== '0'),
    updatedAt: now
  }
}

function readLocalEnv(path: string): { lines: EnvLine[]; env: EnvMap } {
  if (!existsSync(path)) {
    return { lines: [], env: {} }
  }
  const lines = readFileSync(path, 'utf-8').split(/\r?\n/).map(parseEnvLine)
  return {
    lines,
    env: lines.reduce<EnvMap>((acc, line) => {
      if (!line.key) {
        return acc
      }
      const match = line.raw.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/)
      if (!match) {
        return acc
      }
      acc[line.key] = unquoteEnvValue(match[2] || '')
      return acc
    }, {})
  }
}

function parseEnvLine(raw: string): EnvLine {
  const match = raw.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=/)
  return match ? { raw, key: match[1] } : { raw }
}

function writeLocalEnv(path: string, updates: EnvMap): void {
  const existing = readLocalEnv(path)
  const remaining = new Set(Object.keys(updates))
  const nextLines = existing.lines.length
    ? existing.lines.map((line) => {
        if (!line.key || !remaining.has(line.key)) {
          return line.raw
        }
        remaining.delete(line.key)
        return `${line.key}=${quoteEnvValue(updates[line.key])}`
      })
    : ['# XinYu local API configuration', '# Managed by XinYu Desktop API Profile panel.', '']

  for (const key of ENV_KEYS) {
    if (remaining.has(key)) {
      nextLines.push(`${key}=${quoteEnvValue(updates[key] || '')}`)
      remaining.delete(key)
    }
  }

  for (const key of remaining) {
    nextLines.push(`${key}=${quoteEnvValue(updates[key] || '')}`)
  }

  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, `${nextLines.join('\n').replace(/\n+$/, '')}\n`, 'utf-8')
}

function profileToEnvUpdates(profile: ApiConfigProfile): EnvMap {
  return {
    XINYU_API_KEY: profile.apiKey,
    XINYU_BASE_URL: profile.baseUrl,
    XINYU_LLM_PROVIDER: profile.provider,
    XINYU_LLM_MODEL: profile.model,
    XINYU_ALLOW_INSECURE_LLM_HTTP: profile.allowInsecureHttp ? '1' : '0',
    XINYU_DISABLE_STREAMING: profile.disableStreaming ? '1' : '0'
  }
}

function applyProfileToProcessEnv(profile: ApiConfigProfile): void {
  for (const [key, value] of Object.entries(profileToEnvUpdates(profile))) {
    if (value) {
      process.env[key] = value
    } else {
      delete process.env[key]
    }
  }
}

function envToCurrent(path: string, env: EnvMap): ApiConfigCurrent {
  const key = env.XINYU_API_KEY || ''
  return {
    configPath: path,
    provider: env.XINYU_LLM_PROVIDER || 'ciallo',
    model: env.XINYU_LLM_MODEL || 'mimo-v2.5-pro',
    baseUrl: env.XINYU_BASE_URL || '',
    allowInsecureHttp: env.XINYU_ALLOW_INSECURE_LLM_HTTP === '1',
    disableStreaming: env.XINYU_DISABLE_STREAMING !== '0',
    hasApiKey: Boolean(key),
    apiKeyPreview: maskSecret(key)
  }
}

function summarizeProfile(profile: ApiConfigProfile, active: boolean): ApiConfigProfileSummary {
  return {
    id: profile.id,
    label: profile.label,
    provider: profile.provider,
    model: profile.model,
    baseUrl: profile.baseUrl,
    allowInsecureHttp: profile.allowInsecureHttp,
    disableStreaming: profile.disableStreaming,
    updatedAt: profile.updatedAt,
    active,
    hasApiKey: Boolean(profile.apiKey),
    apiKeyPreview: maskSecret(profile.apiKey)
  }
}

function matchActiveProfileId(store: ApiProfileStore, env: EnvMap): string {
  const current = {
    provider: env.XINYU_LLM_PROVIDER || 'ciallo',
    model: env.XINYU_LLM_MODEL || 'mimo-v2.5-pro',
    baseUrl: env.XINYU_BASE_URL || '',
    apiKey: env.XINYU_API_KEY || '',
    allowInsecureHttp: env.XINYU_ALLOW_INSECURE_LLM_HTTP === '1',
    disableStreaming: env.XINYU_DISABLE_STREAMING !== '0'
  }
  const exact = store.profiles.find(
    (profile) =>
      profile.provider === current.provider &&
      profile.model === current.model &&
      profile.baseUrl === current.baseUrl &&
      profile.apiKey === current.apiKey &&
      profile.allowInsecureHttp === current.allowInsecureHttp &&
      profile.disableStreaming === current.disableStreaming
  )
  if (exact) {
    return exact.id
  }
  return ''
}

function apiConfigTestResult(
  profile: ApiConfigProfile,
  checkedAt: string,
  started: number,
  status: number,
  replyPreview: string,
  message: unknown
): ApiConfigTestResult {
  return {
    accepted: true,
    ok: false,
    checkedAt,
    elapsedMs: Date.now() - started,
    provider: profile.provider,
    model: profile.model,
    baseUrl: profile.baseUrl.replace(/\/+$/, ''),
    status,
    replyPreview,
    message: compactTestMessage(message)
  }
}

function extractChatReplyPreview(data: Record<string, unknown>): string {
  const choices = Array.isArray(data.choices) ? data.choices : []
  const first = choices[0]
  if (!first || typeof first !== 'object') {
    return ''
  }
  const message = (first as Record<string, unknown>).message
  if (!message || typeof message !== 'object') {
    return ''
  }
  return safeText((message as Record<string, unknown>).content, '').slice(0, 120)
}

function extractApiErrorMessage(data: Record<string, unknown>): string {
  const error = data.error
  if (!error || typeof error !== 'object') {
    return ''
  }
  return safeText((error as Record<string, unknown>).message, '')
}

function compactTestMessage(value: unknown): string {
  return safeText(value, 'api_test_failed').replace(/\s+/g, ' ').trim().slice(0, 220) || 'api_test_failed'
}

function safeText(value: unknown, fallback: string): string {
  const text = String(value ?? '').trim()
  return text || fallback
}

function safeProfileId(value: unknown): string {
  const text = String(value ?? '').trim()
  return /^[a-zA-Z0-9_-]{1,80}$/.test(text) ? text : ''
}

function makeProfileId(label: string): string {
  const stem = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 36)
  const suffix = Date.now().toString(36)
  return `${stem || 'api'}-${suffix}`
}

function maskSecret(value: string): string {
  const text = String(value || '').trim()
  if (!text) {
    return ''
  }
  const tail = text.slice(-4)
  return `****${tail}`
}

function unquoteEnvValue(value: string): string {
  const trimmed = value.trim()
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1)
  }
  return trimmed
}

function quoteEnvValue(value: string): string {
  const text = String(value || '')
  if (!text || /^[A-Za-z0-9_./:@%+=,;?&-]+$/.test(text)) {
    return text
  }
  return JSON.stringify(text)
}
