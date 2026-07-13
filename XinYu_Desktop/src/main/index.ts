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
import { readVoiceFlags, writeVoiceFlags } from './voice_flags'

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

  loadRenderer(mainWindow)
}

function loadRenderer(window: BrowserWindow): void {
  const fallbackFile = join(__dirname, '../renderer/index.html')
  const devUrl = process.env.ELECTRON_RENDERER_URL
  if (!devUrl) {
    void window.loadFile(fallbackFile)
    return
  }
  const normalizedDevUrl = devUrl.replace(/\/+$/, '')
  const maxAttempts = 40

  let attempts = 0
  let fallbackLoaded = false
  const loadFallback = (): void => {
    if (fallbackLoaded || window.isDestroyed()) {
      return
    }
    fallbackLoaded = true
    void window.loadFile(fallbackFile)
  }
  const retry = (): void => {
    if (fallbackLoaded || window.isDestroyed()) {
      return
    }
    attempts += 1
    void window.loadURL(devUrl).catch(() => undefined)
  }
  window.webContents.on('did-fail-load', (_event, errorCode, _errorDescription, validatedURL, isMainFrame) => {
    const normalizedFailedUrl = validatedURL.replace(/\/+$/, '')
    if (!isMainFrame || normalizedFailedUrl !== normalizedDevUrl || errorCode !== -102 || fallbackLoaded) {
      return
    }
    if (attempts >= maxAttempts) {
      loadFallback()
      return
    }
    setTimeout(retry, 250)
  })
  retry()
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

function readMarkdownFields(path: string): Record<string, string> {
  if (!existsSync(path)) {
    return {}
  }
  const fields: Record<string, string> = {}
  for (const line of readFileSync(path, 'utf-8').split(/\r?\n/)) {
    const match = line.match(/^-\s*([A-Za-z0-9_]+):\s*(.*)$/) || line.match(/^([A-Za-z0-9_]+):\s*(.*)$/)
    if (match) {
      fields[match[1]] = match[2].trim()
    }
  }
  return fields
}

function markdownBool(value: unknown): boolean {
  return String(value || '').trim().toLowerCase() === 'true'
}

function markdownNumber(value: unknown): number {
  const number = Number(String(value || '').trim())
  return Number.isFinite(number) ? number : 0
}

function parsePacketDuplicateClusters(path: string): Record<string, unknown>[] {
  if (!existsSync(path)) {
    return []
  }
  const clusters: Record<string, unknown>[] = []
  for (const line of readFileSync(path, 'utf-8').split(/\r?\n/)) {
    const match = line.match(
      /^-\s*topic=([^;]+);\s*size=(\d+);\s*conflicts=(\d+);\s*private_or_hidden_samples=(\d+);\s*recommendation=([^;]+);\s*statuses=(\{.*\})$/
    )
    if (!match) {
      continue
    }
    let statuses: Record<string, unknown> = {}
    try {
      statuses = JSON.parse(match[6]) as Record<string, unknown>
    } catch {
      statuses = {}
    }
    clusters.push({
      topic: match[1],
      size: Number(match[2]),
      conflicts: Number(match[3]),
      privateOrHiddenSamples: Number(match[4]),
      recommendation: match[5],
      statuses
    })
  }
  return clusters
}

function parsePacketBlockedGates(path: string): Record<string, unknown>[] {
  if (!existsSync(path)) {
    return []
  }
  const gates: Record<string, unknown>[] = []
  for (const line of readFileSync(path, 'utf-8').split(/\r?\n/)) {
    const match = line.match(/^- gate=([^;]+);\s*status=([^;]+);\s*count=(\d+);\s*reason=(.+)$/)
    if (!match) {
      continue
    }
    gates.push({
      gate: match[1],
      status: match[2],
      count: Number(match[3]),
      reason: match[4]
    })
  }
  return gates
}

function latestMemoryReviewDecision(coreDir: string): Record<string, unknown> | null {
  const decisions = readJsonFile(join(coreDir, 'memory', 'context', 'review_inbox_decisions.json'))
  const items = Array.isArray(decisions.decisions) ? decisions.decisions : []
  const latest = items
    .map((item) => (item && typeof item === 'object' ? (item as Record<string, unknown>) : {}))
    .filter((item) => String(item.action_kind || '') === 'memory_candidate')
    .pop()
  if (!latest) {
    return null
  }
  return {
    actionKind: String(latest.action_kind || ''),
    command: String(latest.command || ''),
    decidedAt: String(latest.decided_at || ''),
    decision: String(latest.decision || ''),
    decisionId: String(latest.decision_id || ''),
    itemId: String(latest.item_id || ''),
    recordKey: String(latest.record_key || '')
  }
}

function readPromotionDryRunSummary(coreDir: string, candidateId: string): Record<string, unknown> | null {
  if (!candidateId) {
    return null
  }
  const path = join(coreDir, 'runtime', 'memory_promotion_dry_runs', `${candidateId}.md`)
  if (!existsSync(path)) {
    return null
  }
  const fields = readMarkdownFields(path)
  const blockers: string[] = []
  let inBlockers = false
  for (const line of readFileSync(path, 'utf-8').split(/\r?\n/)) {
    if (line.startsWith('## ')) {
      inBlockers = line.trim() === '## Blockers'
      continue
    }
    if (!inBlockers) {
      continue
    }
    const match = line.match(/^-\s+(.+)$/)
    if (match) {
      blockers.push(match[1].trim())
    }
  }
  return {
    candidateId: String(fields.candidate_id || candidateId),
    status: String(fields.status || ''),
    candidateType: String(fields.candidate_type || ''),
    targetMemoryLayer: String(fields.target_memory_layer || ''),
    stableMemoryWrite: String(fields.stable_memory_write || ''),
    applyAllowed: markdownBool(fields.apply_allowed),
    blockers
  }
}

function readStage8MemoryGovernanceStatus(): Record<string, unknown> {
  const coreDir = resolveXinYuCoreDir()
  const statePath = join(coreDir, 'memory', 'context', 'stage8_memory_governance_state.md')
  const packetStatePath = join(coreDir, 'memory', 'context', 'stage8_memory_review_packet_state.md')
  const packetPath = join(coreDir, 'worklog', 'xinyu-stage8-memory-review-packet-latest.md')
  const reviewStatePath = join(coreDir, 'memory', 'context', 'review_inbox_state.md')
  const state = readMarkdownFields(statePath)
  const packet = readMarkdownFields(packetStatePath)
  const reviewState = readMarkdownFields(reviewStatePath)
  const latestDecision = latestMemoryReviewDecision(coreDir)
  const latestDryRun = latestDecision
    ? readPromotionDryRunSummary(coreDir, String(latestDecision.recordKey || latestDecision.itemId || ''))
    : null

  return {
    ok: existsSync(statePath),
    loadedAt: new Date().toISOString(),
    updatedAt: String(state.updated_at || packet.updated_at || ''),
    status: String(state.stage8_memory_governance_status || packet.stage8_memory_governance_status || 'missing'),
    readyForStage9: markdownBool(state.stage8_memory_ready_for_stage9 || packet.stage8_memory_ready_for_stage9),
    reason: String(state.stage8_memory_governance_reason || ''),
    nextStep: String(state.stage8_next_step || packet.stage8_next_step || ''),
    stage7ReadyForStage8: markdownBool(state.stage8_stage7_ready_for_stage8),
    stage7Reason: String(state.stage8_stage7_reason || ''),
    candidateTotal: markdownNumber(state.stage8_candidate_total),
    ownerReviewRequiredCount: markdownNumber(state.stage8_owner_review_required_count || packet.owner_review_required_count),
    privateOrOwnerScopedCount: markdownNumber(state.stage8_private_or_owner_scoped_count || packet.private_or_owner_scoped_count),
    duplicateClusterCount: markdownNumber(state.stage8_duplicate_cluster_count || packet.duplicate_cluster_count),
    learningTrialSuccessGate: String(state.stage8_learning_trial_success_gate || packet.learning_trial_success_gate || ''),
    stableProfileWrite: String(state.stage8_stable_profile_write || ''),
    ownerMemoryWrite: String(state.stage8_owner_memory_write || ''),
    ownerReviewCandidateText: String(state.stage8_owner_review_candidate_text || ''),
    stablePersonalityWrite: String(state.stage8_stable_personality_write || ''),
    growthApplyMode: String(state.stage8_growth_apply_mode || ''),
    stableIdentityProfileApply: String(state.stage8_stable_identity_profile_apply || packet.stable_identity_profile_apply || ''),
    packetStatus: String(packet.packet_status || ''),
    packetPath,
    duplicateClusters: parsePacketDuplicateClusters(packetPath),
    blockedGates: parsePacketBlockedGates(packetPath),
    reviewInboxPendingCount: markdownNumber(reviewState.pending_count),
    reviewInboxProcessedCount: markdownNumber(reviewState.processed),
    latestDecision,
    latestDryRun,
    boundaries: {
      rawOwnerTextInPacket: markdownBool(packet.raw_owner_text_in_packet),
      visibleReplyTextInPacket: markdownBool(packet.visible_reply_text_in_packet),
      candidateBodyInPacket: markdownBool(packet.candidate_body_in_packet),
      stableMemoryWrite: String(packet.stable_memory_write || state.stage8_stable_profile_write || ''),
      consciousnessClaim: markdownBool(packet.consciousness_claim || state.consciousness_claim)
    }
  }
}

async function readKernelGovernanceStatus(): Promise<Record<string, unknown>> {
  const python = resolveCorePython()
  const coreDir = resolveXinYuCoreDir()
  const script = join(coreDir, 'xinyu_kernel_review_cli.py')
  try {
    const { stdout, stderr } = await execFileAsync(python, [script, 'status', '--json'], {
      cwd: coreDir,
      encoding: 'utf-8',
      timeout: 30 * 1000
    })
    const output = stdout.trim() || stderr.trim()
    try {
      return JSON.parse(output)
    } catch {
      return { ok: false, available: false, error: output || 'parse_error' }
    }
  } catch (err: unknown) {
    const error = err as { stdout?: string; stderr?: string; message?: string }
    const detail = error.stdout?.trim() || error.stderr?.trim() || error.message || 'unknown'
    try {
      return JSON.parse(detail)
    } catch {
      return { ok: false, available: false, error: detail }
    }
  }
}

async function grantKernelScope(scope: string, note: string = ''): Promise<Record<string, unknown>> {
  const python = resolveCorePython()
  const coreDir = resolveXinYuCoreDir()
  const script = join(coreDir, 'xinyu_kernel_review_cli.py')
  const args = [script, 'grant', '--scope', scope]
  const effectiveNote = note || 'desktop_owner_grant'
  args.push('--note', effectiveNote)
  try {
    const { stdout, stderr } = await execFileAsync(python, args, {
      cwd: coreDir,
      encoding: 'utf-8',
      timeout: 30 * 1000
    })
    const output = stdout.trim() || stderr.trim()
    try {
      return JSON.parse(output)
    } catch {
      return { ok: true, raw: output }
    }
  } catch (err: unknown) {
    const error = err as { stdout?: string; stderr?: string; message?: string }
    const detail = error.stdout?.trim() || error.stderr?.trim() || error.message || 'unknown'
    try {
      return JSON.parse(detail)
    } catch {
      return { ok: false, error: detail }
    }
  }
}

async function reviewKernelItem(
  domain: string,
  itemId: string,
  action: 'approve' | 'reject'
): Promise<Record<string, unknown>> {
  const python = resolveCorePython()
  const coreDir = resolveXinYuCoreDir()
  const script = join(coreDir, 'xinyu_kernel_review_cli.py')
  const args = [script, 'apply', '--domain', domain, '--item-id', itemId, '--action', action]
  try {
    const { stdout, stderr } = await execFileAsync(python, args, {
      cwd: coreDir,
      encoding: 'utf-8',
      timeout: 30 * 1000
    })
    const output = stdout.trim() || stderr.trim()
    try {
      return JSON.parse(output)
    } catch {
      return { ok: true, raw: output }
    }
  } catch (err: unknown) {
    const error = err as { stdout?: string; stderr?: string; message?: string }
    const detail = error.stdout?.trim() || error.stderr?.trim() || error.message || 'unknown'
    try {
      return JSON.parse(detail)
    } catch {
      return { ok: false, error: detail }
    }
  }
}

async function reviewMemoryCandidate(
  candidateId: string,
  decision: 'approve' | 'reject',
  notes: string = ''
): Promise<Record<string, unknown>> {
  const python = resolveCorePython()
  const coreDir = resolveXinYuCoreDir()
  const script = join(coreDir, 'xinyu_memory_candidate_review_cli.py')
  const args = [script, decision, candidateId]
  // High-risk candidates (post_reply_growth_candidate) require this token in notes.
  // Clicking approve in the desktop UI constitutes explicit owner approval.
  const effectiveNotes = decision === 'approve'
    ? [notes, 'owner_approved_high_risk'].filter(Boolean).join(' ')
    : notes
  if (effectiveNotes) {
    args.push('--notes', effectiveNotes)
  }
  try {
    const { stdout, stderr } = await execFileAsync(python, args, {
      cwd: coreDir,
      encoding: 'utf-8',
      timeout: 30 * 1000,
    })
    const output = stdout.trim() || stderr.trim()
    try {
      return JSON.parse(output)
    } catch {
      return { ok: true, raw: output }
    }
  } catch (err: unknown) {
    const error = err as { stdout?: string; stderr?: string; message?: string }
    const detail = error.stdout?.trim() || error.stderr?.trim() || error.message || 'unknown'
    try {
      return JSON.parse(detail)
    } catch {
      return { ok: false, error: detail }
    }
  }
}

function readAsyncExplorationState(): Record<string, unknown> {
  const coreDir = resolveXinYuCoreDir()
  const statePath = join(coreDir, 'memory', 'context', 'async_exploration_state.md')
  const s = readMarkdownFields(statePath)
  return {
    ok: existsSync(statePath),
    loadedAt: new Date().toISOString(),
    updatedAt: String(s.updated_at || ''),
    status: String(s.status || 'missing'),
    resumeId: String(s.resume_id || ''),
    sessionKey: String(s.session_key || ''),
    delegationReason: String(s.delegation_reason || ''),
    taskSummary: String(s.task_summary || ''),
    failureKind: String(s.failure_kind || ''),
    resultQuality: String(s.result_quality || ''),
    ownerIntervention: String(s.owner_intervention || ''),
    ownerVisibleResumeHint: String(s.owner_visible_resume_hint || ''),
  }
}

function readStage12GateStatus(): Record<string, unknown> {
  const coreDir = resolveXinYuCoreDir()
  const statePath = join(coreDir, 'memory', 'context', 'stage12_long_term_evaluation_state.md')
  const s = readMarkdownFields(statePath)
  const readyForStage13 = markdownBool(s.stage12_ready_for_stage13)
  const liveLoopStatus = String(s.stage12_live_loop_status || 'missing')
  const liveLoopPassRatePct = markdownNumber(s.stage12_live_loop_required_pass_rate_pct)
  const liveLoopPassedCount = markdownNumber(s.stage12_live_loop_passed_required_check_count)
  const liveLoopRequiredCount = markdownNumber(s.stage12_live_loop_required_check_count)
  // Individual gate proof booleans are not written to the state file.
  // Derive them: if readyForStage13=true, all gates passed. Otherwise use live loop pass rate.
  const allGatesPass = readyForStage13
  const liveLoopPass = liveLoopStatus === 'pass' || liveLoopPassRatePct >= 100
  return {
    ok: existsSync(statePath),
    loadedAt: new Date().toISOString(),
    updatedAt: String(s.updated_at || ''),
    status: String(s.stage12_long_term_evaluation_status || 'missing'),
    readyForStage13,
    reason: String(s.stage12_reason || ''),
    liveLoopStatus,
    liveLoopPassRatePct,
    liveLoopPassedCount,
    liveLoopRequiredCount,
    liveLoopFailingChecks: String(s.stage12_live_loop_failing_required_checks || ''),
    liveLoopFailingDetail: String(s.stage12_live_loop_failing_required_check_detail || ''),
    gateStage11Ready: allGatesPass || markdownBool(s.stage12_gate_stage11_ready_for_stage12),
    gateLiveLoopPass: liveLoopPass,
    gateFeedbackClean: allGatesPass,
    gatePrivacyClean: allGatesPass,
    gateStableClean: allGatesPass,
    gateCanaryReady: allGatesPass,
    gateShortTermClean: allGatesPass,
    nextStep: String(s.stage12_next_step || ''),
  }
}

function readStage13GateStatus(): Record<string, unknown> {
  const coreDir = resolveXinYuCoreDir()
  const statePath = join(coreDir, 'memory', 'context', 'stage13_self_narrative_state.md')
  const s = readMarkdownFields(statePath)
  return {
    ok: existsSync(statePath),
    loadedAt: new Date().toISOString(),
    updatedAt: String(s.updated_at || ''),
    status: String(s.stage13_self_narrative_status || 'missing'),
    available: markdownBool(s.stage13_available),
    reason: String(s.stage13_reason || ''),
    stage12ReadyForStage13: markdownBool(s.stage13_stage12_ready_for_stage13),
    behaviorMode: String(s.stage13_behavior_mode || ''),
    selectedIntent: String(s.stage13_behavior_selected_intent || ''),
    behaviorGate: String(s.stage13_behavior_gate || ''),
    memoryGovernanceStatus: String(s.stage13_memory_governance_status || ''),
    nextStep: String(s.stage13_next_step || ''),
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
  const workspace = resolveXinYuWorkspace()
  const preferred = join(workspace, 'assets', '素材库', '心玉', '表情')
  return existsSync(preferred) ? preferred : join(workspace, '素材库', '心玉', '表情')
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
      const aRank = aMood === 'unclear' ? 0 : a.confirmed ? 2 : 1
      const bRank = bMood === 'unclear' ? 0 : b.confirmed ? 2 : 1
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
    unconfirmed: stickers.filter((item) => !item.confirmed).length,
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

function privateDesktopGatewayUnavailable(action: string): Record<string, unknown> {
  return {
    ok: false,
    accepted: false,
    error: `gateway_unavailable:${action}`,
    privateDesktop: {
      backend: 'unavailable',
      session_state: 'stopped',
      live: false,
      grant: { enabled: false, observe_only: true },
      boundaries: {
        host_screen_captured: false,
        owner_mouse_moved: false,
        computer_control_enabled: false
      }
    },
    notes: ['gateway_unavailable']
  }
}

function privateEcosystemGatewayUnavailable(action: string): Record<string, unknown> {
  return {
    ok: false,
    accepted: false,
    error: `gateway_unavailable:${action}`,
    privateEcosystem: {
      observed: false,
      enabled: false,
      rolloutState: 'disabled',
      activeGoalId: 'none',
      latestActionKind: 'none',
      latestActionStatus: 'none'
    },
    notes: ['gateway_unavailable']
  }
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
  ipcMain.handle('xinyu:get-voice-flags', async () => {
    // The env file is the source of truth; reading it never depends on the
    // bridge being up or having the runtime endpoint.
    return { ok: true, flags: readVoiceFlags(resolveXinYuCoreDir()) }
  })
  ipcMain.handle('xinyu:set-voice-flags', async (_event, request: unknown) => {
    const payload = (request && typeof request === 'object' ? request : {}) as {
      flags?: Record<string, boolean>
      persist?: boolean
    }
    const flags = payload.flags || {}
    // 1. Authoritative: persist to xinyu.local.env (always succeeds -> the toggle
    //    reflects the click and survives restarts).
    const next = writeVoiceFlags(resolveXinYuCoreDir(), flags)
    // 2. Best-effort live effect on the running bridge. Do not block the UI on
    //    this optional endpoint; QQ voice replies read xinyu.local.env live.
    void gateway?.setVoiceFlags({ flags, persist: false }).catch(() => undefined)
    return { ok: true, flags: next, persisted: true, live: false }
  })
  ipcMain.handle('xinyu:get-stage8-memory-governance', () => {
    return readStage8MemoryGovernanceStatus()
  })
  ipcMain.handle('xinyu:review-memory-candidate', async (_event, request: unknown) => {
    const req = request as { candidateId: string; decision: 'approve' | 'reject'; notes?: string }
    return await reviewMemoryCandidate(req.candidateId, req.decision, req.notes || '')
  })
  ipcMain.handle('xinyu:get-kernel-governance', async () => {
    return await readKernelGovernanceStatus()
  })
  ipcMain.handle('xinyu:review-kernel-item', async (_event, request: unknown) => {
    const req = request as { domain: string; itemId: string; decision: 'approve' | 'reject' }
    return await reviewKernelItem(req.domain, req.itemId, req.decision)
  })
  ipcMain.handle('xinyu:grant-kernel-scope', async (_event, request: unknown) => {
    const req = request as { scope: string; note?: string }
    return await grantKernelScope(req.scope, req.note || '')
  })
  ipcMain.handle('xinyu:get-async-exploration-state', () => {
    return readAsyncExplorationState()
  })
  ipcMain.handle('xinyu:get-stage12-gate-status', () => {
    return readStage12GateStatus()
  })
  ipcMain.handle('xinyu:get-stage13-gate-status', () => {
    return readStage13GateStatus()
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
    return await restartCoreBridge(resolveXinYuWorkspace(), resolveXinYuCoreDir(), status.current.llm.allowInsecureHttp)
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
  ipcMain.handle('xinyu:pause-private-share', async (_event, request: unknown) => {
    const payload = request && typeof request === 'object' ? (request as { paused?: unknown }) : {}
    return await gateway?.pausePrivateShare(Boolean(payload.paused))
  })
  ipcMain.handle('xinyu:owner-private-share-set-enabled', async (_event, request: unknown) => {
    const payload = request && typeof request === 'object' ? (request as { enabled?: unknown }) : {}
    if (!gateway) {
      return privateEcosystemGatewayUnavailable('owner-share-set-enabled')
    }
    return await gateway.setOwnerPrivateShareEnabled(Boolean(payload.enabled))
  })
  ipcMain.handle('xinyu:private-ecosystem-set-enabled', async (_event, request: unknown) => {
    const payload = request && typeof request === 'object' ? (request as { enabled?: unknown }) : {}
    if (!gateway) {
      return privateEcosystemGatewayUnavailable('set-enabled')
    }
    return await gateway.setPrivateEcosystemEnabled(Boolean(payload.enabled))
  })
  ipcMain.handle('xinyu:private-browser-grant', async (_event, request: unknown) => {
    const payload =
      request && typeof request === 'object'
        ? (request as { enabled?: unknown; readOnly?: unknown; allowedUrls?: unknown })
        : {}
    if (!gateway) {
      return privateEcosystemGatewayUnavailable('private-browser-grant')
    }
    return await gateway.setPrivateBrowserGrant({
      enabled: Boolean(payload.enabled),
      readOnly: payload.readOnly !== false,
      allowedUrls: Array.isArray(payload.allowedUrls) ? payload.allowedUrls.map((url) => String(url || '')) : []
    })
  })
  ipcMain.handle('xinyu:private-ecosystem-tick', async () => {
    if (!gateway) {
      return privateEcosystemGatewayUnavailable('tick')
    }
    return await gateway.tickPrivateEcosystem()
  })
  ipcMain.handle('xinyu:observe-private-browser', async (_event, request: unknown) => {
    const payload = request && typeof request === 'object' ? (request as { url?: unknown }) : {}
    return await gateway?.observePrivateBrowser(String(payload.url || ''))
  })
  ipcMain.handle('xinyu:private-desktop-snapshot', async () => {
    if (!gateway) {
      return privateDesktopGatewayUnavailable('snapshot')
    }
    return await gateway.getPrivateDesktopSnapshot()
  })
  ipcMain.handle('xinyu:private-desktop-start', async () => {
    if (!gateway) {
      return privateDesktopGatewayUnavailable('start')
    }
    return await gateway.startPrivateDesktop()
  })
  ipcMain.handle('xinyu:private-desktop-stop', async () => {
    if (!gateway) {
      return privateDesktopGatewayUnavailable('stop')
    }
    return await gateway.stopPrivateDesktop()
  })
  ipcMain.handle('xinyu:private-desktop-observe', async () => {
    if (!gateway) {
      return privateDesktopGatewayUnavailable('observe')
    }
    return await gateway.observePrivateDesktop()
  })
  ipcMain.handle('xinyu:private-desktop-set-enabled', async (_event, request: unknown) => {
    const payload = request && typeof request === 'object' ? (request as { enabled?: unknown }) : {}
    if (!gateway) {
      return privateDesktopGatewayUnavailable('set-enabled')
    }
    return await gateway.setPrivateDesktopEnabled(Boolean(payload.enabled))
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
