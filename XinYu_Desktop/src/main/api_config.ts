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

export type ApiLlmConfig = {
  provider: string
  model: string
  baseUrl: string
  apiKey: string
  allowInsecureHttp: boolean
  disableStreaming: boolean
}

export type ApiVisionConfig = {
  enabled: boolean
  model: string
  baseUrl: string
  apiKey: string
  timeoutSeconds: number
  maxBytes: number
}

export type ApiHearingConfig = {
  enabled: boolean
  command: string
  model: string
  baseUrl: string
  apiKey: string
  language: string
  timeoutSeconds: number
  recordFormat: string
}

export type ApiTtsConfig = {
  enabled: boolean
  engine: string
  model: string
  baseUrl: string
  apiKey: string
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
}

export type ApiOtherConfig = {
  openAIApiKey: string
}

export type ApiConfigProfile = {
  id: string
  label: string
  llm: ApiLlmConfig
  vision: ApiVisionConfig
  hearing: ApiHearingConfig
  tts: ApiTtsConfig
  other: ApiOtherConfig
  updatedAt: string
}

type ApiSecretSummary = {
  hasApiKey: boolean
  apiKeyPreview: string
}

type ApiOpenAiSecretSummary = {
  hasOpenAIApiKey: boolean
  openAIApiKeyPreview: string
}

export type ApiLlmConfigSummary = Omit<ApiLlmConfig, 'apiKey'> & ApiSecretSummary
export type ApiVisionConfigSummary = Omit<ApiVisionConfig, 'apiKey'> & ApiSecretSummary
export type ApiHearingConfigSummary = Omit<ApiHearingConfig, 'apiKey'> & ApiSecretSummary
export type ApiTtsConfigSummary = Omit<ApiTtsConfig, 'apiKey'> & ApiSecretSummary
export type ApiOtherConfigSummary = ApiOpenAiSecretSummary

export type ApiConfigProfileSummary = {
  id: string
  label: string
  llm: ApiLlmConfigSummary
  vision: ApiVisionConfigSummary
  hearing: ApiHearingConfigSummary
  tts: ApiTtsConfigSummary
  other: ApiOtherConfigSummary
  updatedAt: string
  active: boolean
}

export type ApiConfigCurrent = {
  configPath: string
  llm: ApiLlmConfigSummary
  vision: ApiVisionConfigSummary
  hearing: ApiHearingConfigSummary
  tts: ApiTtsConfigSummary
  other: ApiOtherConfigSummary
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
  llm?: unknown
  vision?: unknown
  hearing?: unknown
  tts?: unknown
  other?: unknown
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

type ApiConfigTestRequest = {
  url: string
  headers: Record<string, string>
  body: string
  extractReplyPreview: (data: Record<string, unknown>) => string
}

const LOCAL_ENV_NAME = 'xinyu.local.env'
const PROFILE_STORE_NAME = 'xinyu-api-profiles.json'
const DEFAULT_VISION_TIMEOUT_SECONDS = 45
const DEFAULT_VISION_MAX_BYTES = 4 * 1024 * 1024
const DEFAULT_HEARING_TIMEOUT_SECONDS = 120
const DEFAULT_TTS_TIMEOUT_SECONDS = 60
const DEFAULT_GENIE_TTS_BASE_URL = 'http://127.0.0.1:8000'
const DEFAULT_GENIE_TTS_CHARACTER = 'feibi'
const DEFAULT_GENIE_TTS_SAMPLE_RATE = 32000
const DEFAULT_GENIE_TTS_CHANNELS = 1
const DEFAULT_GENIE_TTS_SAMPLE_WIDTH = 2
const ANTHROPIC_VERSION = '2023-06-01'
const OPENAI_COMPATIBLE_RUNTIME_PROVIDERS = new Set([
  'openai',
  'openrouter',
  'gemini',
  'mimo',
  'ciallo',
  'deepseek',
  'qwen',
  'siliconflow',
  'moonshot',
  'minimax',
  'custom_openai',
  'custom-openai',
  'custom_openai_compatible',
  'custom-openai-compatible',
  'openai_compatible',
  'openai-compatible',
  'chat_completions',
  'chat-completions'
])
const NATIVE_MESSAGES_PROVIDERS = new Set([
  'message',
  'messages',
  'claude',
  'claude_messages',
  'claude-messages',
  'claude_native',
  'claude-native',
  'anthropic',
  'anthropic_messages',
  'anthropic-messages',
  'anthropic_native',
  'anthropic-native'
])

const ENV_KEYS = [
  'XINYU_API_KEY',
  'XINYU_BASE_URL',
  'XINYU_LLM_PROVIDER',
  'XINYU_LLM_MODEL',
  'XINYU_ALLOW_INSECURE_LLM_HTTP',
  'XINYU_DISABLE_STREAMING',
  'XINYU_IMAGE_VISION_ENABLED',
  'XINYU_IMAGE_VISION_MODEL',
  'XINYU_IMAGE_VISION_BASE_URL',
  'XINYU_IMAGE_VISION_API_KEY',
  'XINYU_IMAGE_VISION_TIMEOUT_SECONDS',
  'XINYU_IMAGE_VISION_MAX_BYTES',
  'XINYU_VOICE_STT_ENABLED',
  'XINYU_VOICE_STT_COMMAND',
  'XINYU_VOICE_STT_API_KEY',
  'XINYU_VOICE_STT_BASE_URL',
  'XINYU_VOICE_STT_MODEL',
  'XINYU_VOICE_STT_LANGUAGE',
  'XINYU_VOICE_STT_TIMEOUT_SECONDS',
  'XINYU_VOICE_STT_RECORD_FORMAT',
  'XINYU_TTS_ENABLED',
  'XINYU_TTS_ENGINE',
  'XINYU_TTS_BASE_URL',
  'XINYU_TTS_API_KEY',
  'XINYU_TTS_MODEL',
  'XINYU_TTS_VOICE',
  'XINYU_TTS_FORMAT',
  'XINYU_TTS_REQUEST_MODE',
  'XINYU_TTS_TIMEOUT_SECONDS',
  'XINYU_GENIE_TTS_BASE_URL',
  'XINYU_GENIE_TTS_CHARACTER',
  'XINYU_GENIE_TTS_SPLIT_SENTENCE',
  'XINYU_GENIE_TTS_SAMPLE_RATE',
  'XINYU_GENIE_TTS_CHANNELS',
  'XINYU_GENIE_TTS_SAMPLE_WIDTH',
  'XINYU_OPENAI_API_KEY'
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
    notes: existsSync(envPath) ? [] : [`未找到 ${LOCAL_ENV_NAME}，应用配置时会自动创建。`]
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
  const llm = profile.llm
  const started = Date.now()
  const checkedAt = new Date().toISOString()
  const baseUrl = llm.baseUrl.replace(/\/+$/, '')
  if (!baseUrl) {
    return apiConfigTestResult(llm, checkedAt, started, 0, '', 'missing_base_url')
  }
  if (!llm.model) {
    return apiConfigTestResult(llm, checkedAt, started, 0, '', 'missing_model')
  }
  const runtimeIssue = coreRuntimeProviderIssue(llm)

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 60_000)
  try {
    const request = buildLlmTestRequest(llm, baseUrl)
    const response = await fetch(request.url, {
      method: 'POST',
      signal: controller.signal,
      headers: request.headers,
      body: request.body
    })
    const text = await response.text()
    let replyPreview = ''
    let errorMessage = ''
    let parsedJson = false
    try {
      const data = JSON.parse(text) as Record<string, unknown>
      parsedJson = true
      replyPreview = request.extractReplyPreview(data)
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
        provider: llm.provider,
        model: llm.model,
        baseUrl,
        status: response.status,
        replyPreview,
        message: runtimeIssue || 'api_test_non_json_response'
      }
    }
    if (response.ok && !replyPreview) {
      return {
        accepted: true,
        ok: false,
        checkedAt,
        elapsedMs: Date.now() - started,
        provider: llm.provider,
        model: llm.model,
        baseUrl,
        status: response.status,
        replyPreview,
        message: runtimeIssue || 'api_test_empty_reply'
      }
    }
    return {
      accepted: true,
      ok: response.ok && !runtimeIssue,
      checkedAt,
      elapsedMs: Date.now() - started,
      provider: llm.provider,
      model: llm.model,
      baseUrl,
      status: response.status,
      replyPreview,
      message: response.ok
        ? runtimeIssue || 'api_test_ok'
        : compactTestMessage(errorMessage || response.statusText || 'api_test_failed')
    }
  } catch (error) {
    return apiConfigTestResult(
      llm,
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
    throw new Error('缺少 API 配置 ID')
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
    throw new Error('缺少 API 配置 ID')
  }
  const store = readProfileStore()
  const profile = store.profiles.find((item) => item.id === id)
  if (!profile) {
    throw new Error(`未找到 API 配置：${id}`)
  }

  const runtimeIssue = coreRuntimeProviderIssue(profile.llm)
  if (runtimeIssue) {
    return {
      accepted: false,
      message: runtimeIssue,
      profile: summarizeProfile(profile, false),
      status: getApiConfigStatus(coreDir)
    }
  }

  writeLocalEnv(resolveLocalEnvPath(coreDir), profileToEnvUpdates(profile))
  applyProfileToProcessEnv(profile)
  writeProfileStore({ ...store, activeProfileId: id })
  const restart = restartCore ? await restartCoreBridge(workspaceDir, coreDir, profile.llm.allowInsecureHttp) : null
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
      version: 3,
      activeProfileId: String(data.activeProfileId || ''),
      profiles: Array.isArray(data.profiles) ? data.profiles.map(normalizeStoredProfile).filter(isApiConfigProfile) : []
    }
  } catch {
    return { version: 3, activeProfileId: '', profiles: [] }
  }
}

function writeProfileStore(store: ApiProfileStore): void {
  const path = resolveProfileStorePath()
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, `${JSON.stringify(store, null, 2)}\n`, 'utf-8')
}

function normalizeStoredProfile(value: unknown): ApiConfigProfile | null {
  const raw = asRecord(value)
  const id = safeProfileId(raw.id)
  if (!id) {
    return null
  }
  const llm = normalizeStoredLlm(raw.llm && typeof raw.llm === 'object' ? raw.llm : raw)
  const other = normalizeStoredOther(raw.other)
  const vision = normalizeStoredVision(raw.vision, llm)
  const hearing = normalizeStoredHearing(raw.hearing, llm, other)
  return {
    id,
    label: safeText(raw.label, id),
    llm,
    vision,
    hearing,
    tts: normalizeStoredTts(raw.tts, llm, hearing, other),
    other,
    updatedAt: safeText(raw.updatedAt, '')
  }
}

function normalizeStoredLlm(value: unknown): ApiLlmConfig {
  const raw = asRecord(value)
  return {
    provider: safeText(raw.provider, 'ciallo'),
    model: safeText(raw.model, 'mimo-v2.5-pro'),
    baseUrl: stripTrailingSlash(safeText(raw.baseUrl, '')),
    apiKey: safeText(raw.apiKey, ''),
    allowInsecureHttp: safeBool(raw.allowInsecureHttp, false),
    disableStreaming: safeBool(raw.disableStreaming, true)
  }
}

function normalizeStoredVision(value: unknown, llm: ApiLlmConfig): ApiVisionConfig {
  const raw = asRecord(value)
  return {
    enabled: safeBool(raw.enabled, false),
    model: safeText(raw.model, llm.model || 'gpt-4o-mini'),
    baseUrl: stripTrailingSlash(safeText(raw.baseUrl, llm.baseUrl || 'https://api.openai.com/v1')),
    apiKey: safeText(raw.apiKey, llm.apiKey),
    timeoutSeconds: safeInteger(raw.timeoutSeconds, DEFAULT_VISION_TIMEOUT_SECONDS, 1, 3600),
    maxBytes: safeInteger(raw.maxBytes, DEFAULT_VISION_MAX_BYTES, 1024, 64 * 1024 * 1024)
  }
}

function normalizeStoredHearing(value: unknown, llm: ApiLlmConfig, other: ApiOtherConfig): ApiHearingConfig {
  const raw = asRecord(value)
  return {
    enabled: safeBool(raw.enabled, true),
    command: safeText(raw.command, ''),
    model: safeText(raw.model, 'whisper-1'),
    baseUrl: stripTrailingSlash(safeText(raw.baseUrl, llm.baseUrl || 'https://api.openai.com/v1')),
    apiKey: safeText(raw.apiKey, other.openAIApiKey || llm.apiKey),
    language: safeText(raw.language, 'zh'),
    timeoutSeconds: safeInteger(raw.timeoutSeconds, DEFAULT_HEARING_TIMEOUT_SECONDS, 1, 3600),
    recordFormat: safeText(raw.recordFormat, 'mp3')
  }
}

function normalizeStoredOther(value: unknown): ApiOtherConfig {
  const raw = asRecord(value)
  return {
    openAIApiKey: safeText(raw.openAIApiKey, '')
  }
}

function normalizeStoredTts(value: unknown, llm: ApiLlmConfig, hearing: ApiHearingConfig, other: ApiOtherConfig): ApiTtsConfig {
  const raw = asRecord(value)
  const model = safeText(raw.model, defaultTtsModel(llm.model))
  return {
    enabled: safeBool(raw.enabled, false),
    engine: safeTtsEngine(raw.engine, 'current'),
    model,
    baseUrl: stripTrailingSlash(safeText(raw.baseUrl, hearing.baseUrl || llm.baseUrl || 'https://api.openai.com/v1')),
    apiKey: safeText(raw.apiKey, hearing.apiKey || other.openAIApiKey || llm.apiKey),
    voice: safeText(raw.voice, defaultTtsVoice(model)),
    format: safeText(raw.format, 'wav'),
    requestMode: safeText(raw.requestMode, 'auto'),
    timeoutSeconds: safeInteger(raw.timeoutSeconds, DEFAULT_TTS_TIMEOUT_SECONDS, 1, 3600),
    genieBaseUrl: stripTrailingSlash(safeText(raw.genieBaseUrl, DEFAULT_GENIE_TTS_BASE_URL)),
    genieCharacter: safeText(raw.genieCharacter, DEFAULT_GENIE_TTS_CHARACTER),
    genieSplitSentence: safeBool(raw.genieSplitSentence, false),
    genieSampleRate: safeInteger(raw.genieSampleRate, DEFAULT_GENIE_TTS_SAMPLE_RATE, 8000, 192000),
    genieChannels: safeInteger(raw.genieChannels, DEFAULT_GENIE_TTS_CHANNELS, 1, 8),
    genieSampleWidth: safeInteger(raw.genieSampleWidth, DEFAULT_GENIE_TTS_SAMPLE_WIDTH, 1, 4)
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
  const envFallback = configFromEnv(env)
  const llmPatch = asRecord(patch.llm)
  const visionPatch = asRecord(patch.vision)
  const hearingPatch = asRecord(patch.hearing)
  const ttsPatch = asRecord(patch.tts)
  const otherPatch = asRecord(patch.other)
  const label = safeText(
    patch.label,
    existing?.label || `${existing?.llm.provider || envFallback.llm.provider} ${existing?.llm.model || envFallback.llm.model}`.trim() || '本地 API'
  )

  return {
    id: existing?.id || makeProfileId(label),
    label,
    llm: {
      provider: safeText(llmPatch.provider ?? patch.provider, existing?.llm.provider || envFallback.llm.provider),
      model: safeText(llmPatch.model ?? patch.model, existing?.llm.model || envFallback.llm.model),
      baseUrl: stripTrailingSlash(safeText(llmPatch.baseUrl ?? patch.baseUrl, existing?.llm.baseUrl || envFallback.llm.baseUrl)),
      apiKey: mergeSecret(llmPatch.apiKey ?? patch.apiKey, existing?.llm.apiKey || envFallback.llm.apiKey),
      allowInsecureHttp: safeBool(
        llmPatch.allowInsecureHttp ?? patch.allowInsecureHttp,
        existing?.llm.allowInsecureHttp ?? envFallback.llm.allowInsecureHttp
      ),
      disableStreaming: safeBool(
        llmPatch.disableStreaming ?? patch.disableStreaming,
        existing?.llm.disableStreaming ?? envFallback.llm.disableStreaming
      )
    },
    vision: {
      enabled: safeBool(visionPatch.enabled, existing?.vision.enabled ?? envFallback.vision.enabled),
      model: safeText(visionPatch.model, existing?.vision.model || envFallback.vision.model),
      baseUrl: stripTrailingSlash(safeText(visionPatch.baseUrl, existing?.vision.baseUrl || envFallback.vision.baseUrl)),
      apiKey: mergeSecret(visionPatch.apiKey, existing?.vision.apiKey || envFallback.vision.apiKey),
      timeoutSeconds: safeInteger(
        visionPatch.timeoutSeconds,
        existing?.vision.timeoutSeconds ?? envFallback.vision.timeoutSeconds,
        1,
        3600
      ),
      maxBytes: safeInteger(visionPatch.maxBytes, existing?.vision.maxBytes ?? envFallback.vision.maxBytes, 1024, 64 * 1024 * 1024)
    },
    hearing: {
      enabled: safeBool(hearingPatch.enabled, existing?.hearing.enabled ?? envFallback.hearing.enabled),
      command: safeText(hearingPatch.command, existing?.hearing.command || envFallback.hearing.command),
      model: safeText(hearingPatch.model, existing?.hearing.model || envFallback.hearing.model),
      baseUrl: stripTrailingSlash(safeText(hearingPatch.baseUrl, existing?.hearing.baseUrl || envFallback.hearing.baseUrl)),
      apiKey: mergeSecret(hearingPatch.apiKey, existing?.hearing.apiKey || envFallback.hearing.apiKey),
      language: safeText(hearingPatch.language, existing?.hearing.language || envFallback.hearing.language),
      timeoutSeconds: safeInteger(
        hearingPatch.timeoutSeconds,
        existing?.hearing.timeoutSeconds ?? envFallback.hearing.timeoutSeconds,
        1,
        3600
      ),
      recordFormat: safeText(hearingPatch.recordFormat, existing?.hearing.recordFormat || envFallback.hearing.recordFormat)
    },
    tts: {
      enabled: safeBool(ttsPatch.enabled, existing?.tts.enabled ?? envFallback.tts.enabled),
      engine: safeTtsEngine(ttsPatch.engine, existing?.tts.engine || envFallback.tts.engine),
      model: safeText(ttsPatch.model, existing?.tts.model || envFallback.tts.model),
      baseUrl: stripTrailingSlash(safeText(ttsPatch.baseUrl, existing?.tts.baseUrl || envFallback.tts.baseUrl)),
      apiKey: mergeSecret(ttsPatch.apiKey, existing?.tts.apiKey || envFallback.tts.apiKey),
      voice: safeText(ttsPatch.voice, existing?.tts.voice || envFallback.tts.voice),
      format: safeText(ttsPatch.format, existing?.tts.format || envFallback.tts.format),
      requestMode: safeText(ttsPatch.requestMode, existing?.tts.requestMode || envFallback.tts.requestMode),
      timeoutSeconds: safeInteger(ttsPatch.timeoutSeconds, existing?.tts.timeoutSeconds ?? envFallback.tts.timeoutSeconds, 1, 3600),
      genieBaseUrl: stripTrailingSlash(safeText(ttsPatch.genieBaseUrl, existing?.tts.genieBaseUrl || envFallback.tts.genieBaseUrl)),
      genieCharacter: safeText(ttsPatch.genieCharacter, existing?.tts.genieCharacter || envFallback.tts.genieCharacter),
      genieSplitSentence: safeBool(
        ttsPatch.genieSplitSentence,
        existing?.tts.genieSplitSentence ?? envFallback.tts.genieSplitSentence
      ),
      genieSampleRate: safeInteger(
        ttsPatch.genieSampleRate,
        existing?.tts.genieSampleRate ?? envFallback.tts.genieSampleRate,
        8000,
        192000
      ),
      genieChannels: safeInteger(ttsPatch.genieChannels, existing?.tts.genieChannels ?? envFallback.tts.genieChannels, 1, 8),
      genieSampleWidth: safeInteger(
        ttsPatch.genieSampleWidth,
        existing?.tts.genieSampleWidth ?? envFallback.tts.genieSampleWidth,
        1,
        4
      )
    },
    other: {
      openAIApiKey: mergeSecret(otherPatch.openAIApiKey, existing?.other.openAIApiKey || envFallback.other.openAIApiKey)
    },
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
    : ['# XinYu local API configuration', '# Managed by XinYu Desktop API center.', '']

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
    XINYU_API_KEY: profile.llm.apiKey,
    XINYU_BASE_URL: profile.llm.baseUrl,
    XINYU_LLM_PROVIDER: profile.llm.provider,
    XINYU_LLM_MODEL: profile.llm.model,
    XINYU_ALLOW_INSECURE_LLM_HTTP: profile.llm.allowInsecureHttp ? '1' : '0',
    XINYU_DISABLE_STREAMING: profile.llm.disableStreaming ? '1' : '0',
    XINYU_IMAGE_VISION_ENABLED: profile.vision.enabled ? '1' : '0',
    XINYU_IMAGE_VISION_MODEL: profile.vision.model,
    XINYU_IMAGE_VISION_BASE_URL: profile.vision.baseUrl,
    XINYU_IMAGE_VISION_API_KEY: profile.vision.apiKey,
    XINYU_IMAGE_VISION_TIMEOUT_SECONDS: String(profile.vision.timeoutSeconds),
    XINYU_IMAGE_VISION_MAX_BYTES: String(profile.vision.maxBytes),
    XINYU_VOICE_STT_ENABLED: profile.hearing.enabled ? '1' : '0',
    XINYU_VOICE_STT_COMMAND: profile.hearing.command,
    XINYU_VOICE_STT_API_KEY: profile.hearing.apiKey,
    XINYU_VOICE_STT_BASE_URL: profile.hearing.baseUrl,
    XINYU_VOICE_STT_MODEL: profile.hearing.model,
    XINYU_VOICE_STT_LANGUAGE: profile.hearing.language,
    XINYU_VOICE_STT_TIMEOUT_SECONDS: String(profile.hearing.timeoutSeconds),
    XINYU_VOICE_STT_RECORD_FORMAT: profile.hearing.recordFormat,
    XINYU_TTS_ENABLED: profile.tts.enabled ? '1' : '0',
    XINYU_TTS_ENGINE: profile.tts.engine,
    XINYU_TTS_BASE_URL: profile.tts.baseUrl,
    XINYU_TTS_API_KEY: profile.tts.apiKey,
    XINYU_TTS_MODEL: profile.tts.model,
    XINYU_TTS_VOICE: profile.tts.voice,
    XINYU_TTS_FORMAT: profile.tts.format,
    XINYU_TTS_REQUEST_MODE: profile.tts.requestMode,
    XINYU_TTS_TIMEOUT_SECONDS: String(profile.tts.timeoutSeconds),
    XINYU_GENIE_TTS_BASE_URL: profile.tts.genieBaseUrl,
    XINYU_GENIE_TTS_CHARACTER: profile.tts.genieCharacter,
    XINYU_GENIE_TTS_SPLIT_SENTENCE: profile.tts.genieSplitSentence ? '1' : '0',
    XINYU_GENIE_TTS_SAMPLE_RATE: String(profile.tts.genieSampleRate),
    XINYU_GENIE_TTS_CHANNELS: String(profile.tts.genieChannels),
    XINYU_GENIE_TTS_SAMPLE_WIDTH: String(profile.tts.genieSampleWidth),
    XINYU_OPENAI_API_KEY: profile.other.openAIApiKey
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
  const config = configFromEnv(env)
  return {
    configPath: path,
    llm: summarizeLlm(config.llm),
    vision: summarizeVision(config.vision),
    hearing: summarizeHearing(config.hearing),
    tts: summarizeTts(config.tts),
    other: summarizeOther(config.other)
  }
}

function summarizeProfile(profile: ApiConfigProfile, active: boolean): ApiConfigProfileSummary {
  return {
    id: profile.id,
    label: profile.label,
    llm: summarizeLlm(profile.llm),
    vision: summarizeVision(profile.vision),
    hearing: summarizeHearing(profile.hearing),
    tts: summarizeTts(profile.tts),
    other: summarizeOther(profile.other),
    updatedAt: profile.updatedAt,
    active
  }
}

function summarizeLlm(config: ApiLlmConfig): ApiLlmConfigSummary {
  return {
    provider: config.provider,
    model: config.model,
    baseUrl: config.baseUrl,
    allowInsecureHttp: config.allowInsecureHttp,
    disableStreaming: config.disableStreaming,
    hasApiKey: Boolean(config.apiKey),
    apiKeyPreview: maskSecret(config.apiKey)
  }
}

function summarizeVision(config: ApiVisionConfig): ApiVisionConfigSummary {
  return {
    enabled: config.enabled,
    model: config.model,
    baseUrl: config.baseUrl,
    timeoutSeconds: config.timeoutSeconds,
    maxBytes: config.maxBytes,
    hasApiKey: Boolean(config.apiKey),
    apiKeyPreview: maskSecret(config.apiKey)
  }
}

function summarizeHearing(config: ApiHearingConfig): ApiHearingConfigSummary {
  return {
    enabled: config.enabled,
    command: config.command,
    model: config.model,
    baseUrl: config.baseUrl,
    language: config.language,
    timeoutSeconds: config.timeoutSeconds,
    recordFormat: config.recordFormat,
    hasApiKey: Boolean(config.apiKey),
    apiKeyPreview: maskSecret(config.apiKey)
  }
}

function summarizeTts(config: ApiTtsConfig): ApiTtsConfigSummary {
  return {
    enabled: config.enabled,
    engine: config.engine,
    model: config.model,
    baseUrl: config.baseUrl,
    voice: config.voice,
    format: config.format,
    requestMode: config.requestMode,
    timeoutSeconds: config.timeoutSeconds,
    genieBaseUrl: config.genieBaseUrl,
    genieCharacter: config.genieCharacter,
    genieSplitSentence: config.genieSplitSentence,
    genieSampleRate: config.genieSampleRate,
    genieChannels: config.genieChannels,
    genieSampleWidth: config.genieSampleWidth,
    hasApiKey: Boolean(config.apiKey),
    apiKeyPreview: maskSecret(config.apiKey)
  }
}

function summarizeOther(config: ApiOtherConfig): ApiOtherConfigSummary {
  return {
    hasOpenAIApiKey: Boolean(config.openAIApiKey),
    openAIApiKeyPreview: maskSecret(config.openAIApiKey)
  }
}

function matchActiveProfileId(store: ApiProfileStore, env: EnvMap): string {
  const current = configFromEnv(env)
  const active = store.activeProfileId ? store.profiles.find((profile) => profile.id === store.activeProfileId) : undefined
  if (active && profilesMatch(active, current)) {
    return active.id
  }
  const exact = store.profiles.find((profile) => profilesMatch(profile, current))
  return exact?.id || ''
}

function profilesMatch(
  profile: ApiConfigProfile,
  current: {
    llm: ApiLlmConfig
    vision: ApiVisionConfig
    hearing: ApiHearingConfig
    tts: ApiTtsConfig
    other: ApiOtherConfig
  }
): boolean {
  return (
    profile.llm.provider === current.llm.provider &&
    profile.llm.model === current.llm.model &&
    profile.llm.baseUrl === current.llm.baseUrl &&
    profile.llm.apiKey === current.llm.apiKey &&
    profile.llm.allowInsecureHttp === current.llm.allowInsecureHttp &&
    profile.llm.disableStreaming === current.llm.disableStreaming &&
    profile.vision.enabled === current.vision.enabled &&
    profile.vision.model === current.vision.model &&
    profile.vision.baseUrl === current.vision.baseUrl &&
    profile.vision.apiKey === current.vision.apiKey &&
    profile.vision.timeoutSeconds === current.vision.timeoutSeconds &&
    profile.vision.maxBytes === current.vision.maxBytes &&
    profile.hearing.enabled === current.hearing.enabled &&
    profile.hearing.command === current.hearing.command &&
    profile.hearing.model === current.hearing.model &&
    profile.hearing.baseUrl === current.hearing.baseUrl &&
    profile.hearing.apiKey === current.hearing.apiKey &&
    profile.hearing.language === current.hearing.language &&
    profile.hearing.timeoutSeconds === current.hearing.timeoutSeconds &&
    profile.hearing.recordFormat === current.hearing.recordFormat &&
    profile.tts.enabled === current.tts.enabled &&
    profile.tts.engine === current.tts.engine &&
    profile.tts.model === current.tts.model &&
    profile.tts.baseUrl === current.tts.baseUrl &&
    profile.tts.apiKey === current.tts.apiKey &&
    profile.tts.voice === current.tts.voice &&
    profile.tts.format === current.tts.format &&
    profile.tts.requestMode === current.tts.requestMode &&
    profile.tts.timeoutSeconds === current.tts.timeoutSeconds &&
    profile.tts.genieBaseUrl === current.tts.genieBaseUrl &&
    profile.tts.genieCharacter === current.tts.genieCharacter &&
    profile.tts.genieSplitSentence === current.tts.genieSplitSentence &&
    profile.tts.genieSampleRate === current.tts.genieSampleRate &&
    profile.tts.genieChannels === current.tts.genieChannels &&
    profile.tts.genieSampleWidth === current.tts.genieSampleWidth &&
    profile.other.openAIApiKey === current.other.openAIApiKey
  )
}

function configFromEnv(env: EnvMap): {
  llm: ApiLlmConfig
  vision: ApiVisionConfig
  hearing: ApiHearingConfig
  tts: ApiTtsConfig
  other: ApiOtherConfig
} {
  const llm: ApiLlmConfig = {
    provider: safeText(env.XINYU_LLM_PROVIDER, 'ciallo'),
    model: safeText(env.XINYU_LLM_MODEL, 'mimo-v2.5-pro'),
    baseUrl: stripTrailingSlash(safeText(env.XINYU_BASE_URL, '')),
    apiKey: safeText(env.XINYU_API_KEY, ''),
    allowInsecureHttp: env.XINYU_ALLOW_INSECURE_LLM_HTTP === '1',
    disableStreaming: env.XINYU_DISABLE_STREAMING !== '0'
  }
  const other: ApiOtherConfig = {
    openAIApiKey: safeText(env.XINYU_OPENAI_API_KEY || env.OPENAI_API_KEY, '')
  }
  const vision: ApiVisionConfig = {
    enabled: env.XINYU_IMAGE_VISION_ENABLED === '1',
    model: safeText(env.XINYU_IMAGE_VISION_MODEL, llm.model || 'gpt-4o-mini'),
    baseUrl: stripTrailingSlash(safeText(env.XINYU_IMAGE_VISION_BASE_URL, llm.baseUrl || 'https://api.openai.com/v1')),
    apiKey: safeText(env.XINYU_IMAGE_VISION_API_KEY || llm.apiKey || other.openAIApiKey, ''),
    timeoutSeconds: safeInteger(env.XINYU_IMAGE_VISION_TIMEOUT_SECONDS, DEFAULT_VISION_TIMEOUT_SECONDS, 1, 3600),
    maxBytes: safeInteger(env.XINYU_IMAGE_VISION_MAX_BYTES, DEFAULT_VISION_MAX_BYTES, 1024, 64 * 1024 * 1024)
  }
  const hearing: ApiHearingConfig = {
    enabled: env.XINYU_VOICE_STT_ENABLED !== '0',
    command: safeText(env.XINYU_VOICE_STT_COMMAND, ''),
    model: safeText(env.XINYU_VOICE_STT_MODEL, 'whisper-1'),
    baseUrl: stripTrailingSlash(
      safeText(env.XINYU_VOICE_STT_BASE_URL || env.OPENAI_BASE_URL, llm.baseUrl || 'https://api.openai.com/v1')
    ),
    apiKey: safeText(env.XINYU_VOICE_STT_API_KEY || other.openAIApiKey || llm.apiKey, ''),
    language: safeText(env.XINYU_VOICE_STT_LANGUAGE, 'zh'),
    timeoutSeconds: safeInteger(env.XINYU_VOICE_STT_TIMEOUT_SECONDS, DEFAULT_HEARING_TIMEOUT_SECONDS, 1, 3600),
    recordFormat: safeText(env.XINYU_VOICE_STT_RECORD_FORMAT, 'mp3')
  }
  const ttsModel = safeText(env.XINYU_TTS_MODEL, defaultTtsModel(llm.model))
  const tts: ApiTtsConfig = {
    enabled: env.XINYU_TTS_ENABLED === '1',
    engine: safeTtsEngine(env.XINYU_TTS_ENGINE, 'current'),
    model: ttsModel,
    baseUrl: stripTrailingSlash(
      safeText(env.XINYU_TTS_BASE_URL || env.OPENAI_BASE_URL, hearing.baseUrl || llm.baseUrl || 'https://api.openai.com/v1')
    ),
    apiKey: safeText(env.XINYU_TTS_API_KEY || hearing.apiKey || other.openAIApiKey || llm.apiKey, ''),
    voice: safeText(env.XINYU_TTS_VOICE, defaultTtsVoice(ttsModel)),
    format: safeText(env.XINYU_TTS_FORMAT, 'wav'),
    requestMode: safeText(env.XINYU_TTS_REQUEST_MODE, 'auto'),
    timeoutSeconds: safeInteger(env.XINYU_TTS_TIMEOUT_SECONDS, DEFAULT_TTS_TIMEOUT_SECONDS, 1, 3600),
    genieBaseUrl: stripTrailingSlash(safeText(env.XINYU_GENIE_TTS_BASE_URL, DEFAULT_GENIE_TTS_BASE_URL)),
    genieCharacter: safeText(env.XINYU_GENIE_TTS_CHARACTER, DEFAULT_GENIE_TTS_CHARACTER),
    genieSplitSentence: safeBool(env.XINYU_GENIE_TTS_SPLIT_SENTENCE, false),
    genieSampleRate: safeInteger(env.XINYU_GENIE_TTS_SAMPLE_RATE, DEFAULT_GENIE_TTS_SAMPLE_RATE, 8000, 192000),
    genieChannels: safeInteger(env.XINYU_GENIE_TTS_CHANNELS, DEFAULT_GENIE_TTS_CHANNELS, 1, 8),
    genieSampleWidth: safeInteger(env.XINYU_GENIE_TTS_SAMPLE_WIDTH, DEFAULT_GENIE_TTS_SAMPLE_WIDTH, 1, 4)
  }
  return { llm, vision, hearing, tts, other }
}

function buildLlmTestRequest(llm: ApiLlmConfig, baseUrl: string): ApiConfigTestRequest {
  if (isAnthropicMessagesProvider(llm.provider)) {
    return buildAnthropicTestRequest(llm, baseUrl)
  }
  return buildOpenAiTestRequest(llm, baseUrl)
}

function buildOpenAiTestRequest(llm: ApiLlmConfig, baseUrl: string): ApiConfigTestRequest {
  return {
    url: `${baseUrl}/chat/completions`,
    headers: {
      'content-type': 'application/json',
      ...(llm.apiKey ? { authorization: `Bearer ${llm.apiKey}` } : {})
    },
    body: JSON.stringify({
      model: llm.model,
      messages: [
        { role: 'system', content: 'Return exactly: ok' },
        { role: 'user', content: 'ping' }
      ],
      max_tokens: 512,
      temperature: 0,
      stream: false
    }),
    extractReplyPreview: extractChatReplyPreview
  }
}

function buildAnthropicTestRequest(llm: ApiLlmConfig, baseUrl: string): ApiConfigTestRequest {
  const headers: Record<string, string> = {
    'content-type': 'application/json',
    accept: 'application/json',
    'anthropic-version': ANTHROPIC_VERSION
  }
  if (llm.apiKey) {
    headers['x-api-key'] = llm.apiKey
    headers.authorization = `Bearer ${llm.apiKey}`
  }
  return {
    url: appendAnthropicMessagesEndpoint(baseUrl),
    headers,
    body: JSON.stringify({
      model: llm.model,
      system: 'Return exactly: ok',
      messages: [{ role: 'user', content: 'ping' }],
      max_tokens: 8,
      temperature: 0
    }),
    extractReplyPreview: extractAnthropicReplyPreview
  }
}

function appendAnthropicMessagesEndpoint(baseUrl: string): string {
  const trimmed = baseUrl.replace(/\/+$/, '')
  const lower = trimmed.toLowerCase()
  if (lower.endsWith('/messages')) {
    return trimmed
  }
  if (lower.endsWith('/v1')) {
    return `${trimmed}/messages`
  }
  return `${trimmed}/v1/messages`
}

function isAnthropicMessagesProvider(provider: string): boolean {
  const text = normalizeProviderId(provider)
  return NATIVE_MESSAGES_PROVIDERS.has(text) || text.includes('anthropic_messages') || text.includes('claude_messages')
}

function normalizeProviderId(provider: string): string {
  return String(provider || '').trim().toLowerCase().replace(/\s+/g, '_')
}

function coreRuntimeProviderIssue(llm: ApiLlmConfig): string {
  const provider = normalizeProviderId(llm.provider)
  if (!provider) {
    return 'missing_provider'
  }
  if (isAnthropicMessagesProvider(provider)) {
    return 'native_messages_provider_not_supported_by_core_runtime'
  }
  if (!OPENAI_COMPATIBLE_RUNTIME_PROVIDERS.has(provider)) {
    return 'unknown_provider_select_custom_openai_compatible_or_known_provider'
  }
  return ''
}

function apiConfigTestResult(
  llm: ApiLlmConfig,
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
    provider: llm.provider,
    model: llm.model,
    baseUrl: llm.baseUrl.replace(/\/+$/, ''),
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
  const record = message as Record<string, unknown>
  return safeText(record.content || record.reasoning_content || record.reasoning, '').slice(0, 120)
}

function extractAnthropicReplyPreview(data: Record<string, unknown>): string {
  const content = data.content
  if (Array.isArray(content)) {
    const parts: string[] = []
    for (const item of content) {
      if (typeof item === 'string') {
        parts.push(item)
        continue
      }
      if (item && typeof item === 'object') {
        const text = safeText((item as Record<string, unknown>).text, '')
        if (text) {
          parts.push(text)
        }
      }
    }
    return parts.join('\n').trim().slice(0, 120)
  }
  return safeText(content || data.text || data.reply, '').slice(0, 120)
}

function extractApiErrorMessage(data: Record<string, unknown>): string {
  const error = data.error
  if (typeof error === 'string') {
    return error
  }
  if (!error || typeof error !== 'object') {
    return safeText(data.message, '')
  }
  return safeText((error as Record<string, unknown>).message, '')
}

function compactTestMessage(value: unknown): string {
  return safeText(value, 'api_test_failed').replace(/\s+/g, ' ').trim().slice(0, 220) || 'api_test_failed'
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function safeText(value: unknown, fallback: string): string {
  const text = String(value ?? '').trim()
  return text || fallback
}

function mergeSecret(value: unknown, fallback: string): string {
  if (typeof value === 'string') {
    const text = value.trim()
    return text || fallback
  }
  return fallback
}

function safeBool(value: unknown, fallback: boolean): boolean {
  if (typeof value === 'boolean') {
    return value
  }
  const text = String(value ?? '').trim().toLowerCase()
  if (['1', 'true', 'yes', 'on'].includes(text)) {
    return true
  }
  if (['0', 'false', 'no', 'off'].includes(text)) {
    return false
  }
  return fallback
}

function safeTtsEngine(value: unknown, fallback: string): string {
  const text = String(value ?? '').trim().toLowerCase()
  if (text === 'genie' || text === 'current') {
    return text
  }
  return fallback === 'genie' ? 'genie' : 'current'
}

function safeInteger(value: unknown, fallback: number, min: number, max: number): number {
  const number = Number(String(value ?? '').trim())
  if (!Number.isFinite(number)) {
    return fallback
  }
  return Math.min(max, Math.max(min, Math.round(number)))
}

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

function defaultTtsModel(llmModel: string): string {
  const normalized = llmModel.trim().toLowerCase()
  if (normalized.startsWith('mimo-')) {
    return 'mimo-v2.5-tts'
  }
  return 'tts-1'
}

function defaultTtsVoice(model: string): string {
  return model.trim().toLowerCase().startsWith('mimo-') ? 'mimo_default' : 'alloy'
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
