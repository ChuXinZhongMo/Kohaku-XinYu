import React from 'react'
import ReactDOM from 'react-dom/client'
import { Activity, Clock3 } from 'lucide-react'
import './style.css'
import { AffectiveSurfaceProvider, SurfacePart } from './AffectiveSurfaceProvider'
import { buildAffectiveSurfaceCue } from './affectiveSurface'
import { AutonomyGatePanel, ImpulseObserverDialog, IntentDetailDialog, InteractionStream, IntentQueuePanel, MindStatePanel, StatusBadge, SystemControlPanel, ThemeSwitcher } from './DesktopPanels'
import type { ApiConfigProfilePatch, AppState, AsyncExplorationState, CommandState, DesktopEvent, ExternalPluginConfigPatch, ExternalPluginInstallRequest, GatewayStatus, JsonRecord, MetabolismTicket, MetabolismTicketActionState, PrivateBrowserGrantPatch, ProactiveAction, ProactiveIntent, QQActionState, QQEnvironmentStatus, QQRuntimeActionState, QQRuntimeConfig, QQRuntimeConfigPatch, ServiceProbe, Snapshot, StickerActionState, StickerLibrary, StickerRecord, Stage12GateStatus, Stage13GateStatus, ThemeName, XinYuState } from './desktopTypes'
import { actionLabel, apiConfigActionLabel, applyEvent, applyProactiveInbox, applySnapshot, asRecord, buildProactiveIntents, buildStats, chatErrorLabel, commandStatusLabel, compact, createCommandId, defaultQQRuntimeConfig, defaultQQServices, deriveXinYuState, digestPressureLabel, digestResidueLabel, digestResultLabel, digestThemeLabel, errorLabel, eventLabel, externalPluginActionLabel, formatLatency, formatTime, formatTurnMeta, initialTheme, isCommandRenderedByTurn, memorySummary, normalizeApiConfigStatus, normalizeAsyncExplorationState, normalizeExternalPluginsStatus, normalizeImpulseSoupState, normalizeKernelGovernance, normalizeMemoryGrowthCandidates, normalizeQQEnvironmentStatus, normalizeQQRuntimeConfig, normalizeStage8MemoryGovernance, normalizeStage12GateStatus, normalizeStage13GateStatus, normalizeStickerLibrary, platformLabel, proactiveAckResultLabel, qqActionResultLabel, qqDetailLabel, qqDiagnosisLabel, qqEnvironmentMessage, qqRuntimeResultLabel, qqServiceLabel, riskLabel, runtimeLabel, sourceLabel, statusLabel, stickerClipLabel, stickerCorrectionMoods, stickerMoodLabel, themeOptions, updateCommand } from './desktopModel'

const avatarSrc = './xinyu-avatar.png'

type ExtendedXinYuApi = Window['xinyu'] & {
  setOwnerPrivateShareEnabled?: (request: { enabled: boolean }) => Promise<unknown>
  setPrivateBrowserGrant?: (request: { enabled: boolean; readOnly?: boolean; allowedUrls?: string[] }) => Promise<unknown>
}

function xinyuApi(): ExtendedXinYuApi {
  return window.xinyu as ExtendedXinYuApi
}

function privateEcosystemGoalText(value: string): string {
  if (value === 'observe_private_space') return '观察自己的私有空间'
  if (value === 'tend_private_journal') return '整理私有日志'
  if (value === 'reflect_recent_feedback') return '消化最近主人反馈'
  if (value === 'review_memory_pressure') return '检查记忆候选压力'
  if (value === 'explore_browser_readonly') return '只读观察主人允许的页面'
  return value && value !== 'none' ? compact(value, 32) : '暂无目标'
}

function privateEcosystemActionText(value: string): string {
  if (value === 'local_probe') return '本地低风险探测'
  if (value === 'browser_observe') return '只读浏览观察'
  if (value === 'owner_private_share') return '准备主人私聊候选'
  if (value === 'memory_candidate') return '生成记忆候选'
  return value && value !== 'none' ? compact(value, 32) : '暂无动作'
}

function privateEcosystemStatusText(value: string): string {
  const text = String(value || '').trim()
  const labels: Record<string, string> = {
    blocked: '已拦截',
    completed: '已完成',
    failed: '失败',
    none: '暂无',
    prepared: '已准备',
    queued: '已排队',
    simulated: '模拟完成'
  }
  return labels[text] || compact(text || '暂无', 48)
}

function privateBrowserResultText(value: string): string {
  const text = String(value || '').trim()
  if (!text) return '暂无结果'
  if (text === 'read_only_allowed') return '只读观察已允许'
  if (text === 'browser_grant_disabled') return '浏览授权未启用'
  if (text === 'plugin_disabled') return '插件未启用，请先启用 xinyu_private_browser'
  if (text === 'grant_failed') return '授权写入失败'
  if (text === 'browser_engine_unavailable') return '浏览器引擎不可用'
  if (text === 'high_risk_browser_action_blocked') return '高风险浏览动作已拦截'
  if (text === 'approval_required') return '动作需要逐次批准'
  if (text.startsWith('sensitive_page_blocked')) return '敏感页面已拦截'
  if (text.startsWith('private_browser_grant_http_')) return '浏览授权接口返回错误'
  return compact(text, 72)
}

function privateDesktopResultText(value: string): string {
  const text = String(value || '').trim()
  const labels: Record<string, string> = {
    blocked: '已拦截',
    completed: '已完成',
    failed: '失败',
    live: '运行中',
    ok: '完成',
    prepared: '已准备',
    simulated: '模拟完成',
    starting: '启动中',
    stopped: '已停止'
  }
  return labels[text] || compact(text || '失败', 72)
}

function desktopInternalErrorText(value: unknown): string {
  const text = value instanceof Error ? errorLabel(value) : String(value || '').trim()
  if (!text) return '未知错误'
  if (text.includes('preload_missing')) return '桌面接口未加载，请重启 Desktop'
  if (text.startsWith('gateway_unavailable')) return '核心网关不可用'
  if (text === 'grant_failed') return '授权写入失败'
  return compact(text, 72)
}

function metabolismTicketId(ticket: MetabolismTicket): string {
  return String(ticket.ticket_id || ticket.ticketId || ticket.id || '').trim()
}

function normalizeMetabolismTickets(value: unknown): MetabolismTicket[] {
  const payload = asRecord(value)
  const rawTickets = Array.isArray(value) ? value : Array.isArray(payload.tickets) ? payload.tickets : []
  return rawTickets.map((ticket) => asRecord(ticket) as MetabolismTicket)
}

function upsertMetabolismTicket(current: MetabolismTicket[], ticket: unknown): MetabolismTicket[] {
  const next = asRecord(ticket) as MetabolismTicket
  const ticketId = metabolismTicketId(next)
  if (!ticketId) return current
  return [next, ...current.filter((item) => metabolismTicketId(item) !== ticketId)]
}

function metabolismActionResultText(action: 'yield' | 'maintain', accepted: boolean, detail = ''): string {
  const label = action === 'yield' ? '让出计算' : '守住边界'
  if (accepted) return `${label}已提交`
  const mapped = detail === 'missing_ticket_id' ? '缺少票据 ID' : privateEcosystemStatusText(detail)
  return `${label}失败：${mapped}`
}

function App(): JSX.Element {
  const [input, setInput] = React.useState('')
  const [codexMode, setCodexMode] = React.useState(false)
  const [codexLocalWrite, setCodexLocalWrite] = React.useState(false)
  const [theme, setTheme] = React.useState<ThemeName>(() => initialTheme())
  const [selectedIntentId, setSelectedIntentId] = React.useState<string | null>(null)
  const [impulseObserverOpen, setImpulseObserverOpen] = React.useState(false)
  const [impulseLoading, setImpulseLoading] = React.useState(false)
  const [selfActionApprovalBusy, setSelfActionApprovalBusy] = React.useState('')
  const [privateShareBusy, setPrivateShareBusy] = React.useState(false)
  const [privateEcosystemBusy, setPrivateEcosystemBusy] = React.useState(false)
  const [privateEcosystemResult, setPrivateEcosystemResult] = React.useState('')
  const [browserGrantBusy, setBrowserGrantBusy] = React.useState(false)
  const [browserGrantResult, setBrowserGrantResult] = React.useState('')
  const [browserObserveBusy, setBrowserObserveBusy] = React.useState(false)
  const [browserObserveResult, setBrowserObserveResult] = React.useState('')
  const [privateDesktop, setPrivateDesktop] = React.useState<Record<string, unknown> | undefined>(undefined)
  const [privateDesktopBusy, setPrivateDesktopBusy] = React.useState(false)
  const [privateDesktopResult, setPrivateDesktopResult] = React.useState('')
  const [metabolismTickets, setMetabolismTickets] = React.useState<MetabolismTicket[]>([])
  const [metabolismAction, setMetabolismAction] = React.useState<MetabolismTicketActionState>({ kind: 'idle', message: '' })
  const [reviewCandidateBusy, setReviewCandidateBusy] = React.useState('')
  const [reviewKernelItemBusy, setReviewKernelItemBusy] = React.useState('')
  const [grantKernelScopeBusy, setGrantKernelScopeBusy] = React.useState('')
  const [proactiveFeedback, setProactiveFeedback] = React.useState<Record<string, string>>({})
  const [state, setState] = React.useState<AppState>({
    snapshot: null,
    gateway: null,
    events: [],
    commands: [],
    proactiveActions: {},
    proactiveInbox: [],
    proactiveHistory: [],
    impulseSoup: null,
    recentTurns: [],
    recentMemoryEvents: [],
    memoryGrowthCandidates: null,
    stage8MemoryGovernance: null,
    kernelGovernance: null,
    asyncExploration: null,
    stage12Gate: null,
    stage13Gate: null,
    apiConfig: null,
    apiConfigAction: { kind: 'idle', message: '' },
    externalPlugins: null,
    externalPluginAction: { kind: 'idle', message: '' },
    qqEnvironment: null,
    qqAction: { kind: 'idle', message: '' },
    qqRuntimeConfig: null,
    qqRuntimeAction: { kind: 'idle', message: '' },
    stickerLibrary: null,
    stickerAction: { kind: 'idle', message: '' }
  })

  React.useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('xinyu.desktop.theme', theme)
  }, [theme])

  React.useEffect(() => {
    let mounted = true
    const loadQQEnvironment = (): void => {
      window.xinyu
        .getQQEnvironmentStatus()
        .then((status) => {
          if (!mounted) return
          setState((current) => ({ ...current, qqEnvironment: normalizeQQEnvironmentStatus(status) }))
        })
        .catch((error) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            qqAction:
              current.qqAction.kind === 'idle'
                ? { kind: 'idle', message: `QQ 检查失败：${compact(errorLabel(error), 72)}` }
                : current.qqAction
          }))
        })
    }
    const loadQQRuntimeConfig = (): void => {
      window.xinyu
        .getQQRuntimeConfig()
        .then((config) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            qqRuntimeConfig: normalizeQQRuntimeConfig(config),
            qqRuntimeAction:
              current.qqRuntimeAction.kind === 'loading' ? { kind: 'idle', message: '' } : current.qqRuntimeAction
          }))
        })
        .catch((error) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            qqRuntimeAction:
              current.qqRuntimeAction.kind === 'idle'
                ? { kind: 'idle', message: `QQ 设置读取失败：${compact(errorLabel(error), 72)}` }
                : current.qqRuntimeAction
          }))
        })
    }
    const loadApiConfig = (): void => {
      window.xinyu
        .getApiConfigStatus()
        .then((config) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            apiConfig: normalizeApiConfigStatus(config),
            apiConfigAction:
              current.apiConfigAction.kind === 'loading' ? { kind: 'idle', message: '' } : current.apiConfigAction
          }))
        })
        .catch((error) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            apiConfigAction:
              current.apiConfigAction.kind === 'idle'
                ? { kind: 'idle', message: `API 资料读取失败：${compact(errorLabel(error), 72)}` }
                : current.apiConfigAction
          }))
        })
    }
    const loadExternalPlugins = (): void => {
      window.xinyu
        .getExternalPlugins()
        .then((plugins) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            externalPlugins: normalizeExternalPluginsStatus(plugins),
            externalPluginAction: current.externalPluginAction.kind === 'loading' ? { kind: 'idle', message: '' } : current.externalPluginAction
          }))
        })
        .catch((error) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            externalPluginAction:
              current.externalPluginAction.kind === 'idle'
                ? { kind: 'idle', message: `外部插件读取失败：${compact(errorLabel(error), 72)}` }
                : current.externalPluginAction
          }))
        })
    }
    const loadStickerLibrary = (): void => {
      window.xinyu
        .getStickerLibrary()
        .then((library) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            stickerLibrary: normalizeStickerLibrary(library),
            stickerAction: { kind: 'idle', message: '' }
          }))
        })
        .catch((error) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            stickerAction: { kind: 'idle', message: `表情库读取失败：${compact(errorLabel(error), 72)}` }
          }))
        })
    }
    const loadMemoryGrowthCandidates = (): void => {
      window.xinyu
        .getMemoryGrowthCandidates()
        .then((value) => {
          if (!mounted) return
          setState((current) => ({ ...current, memoryGrowthCandidates: normalizeMemoryGrowthCandidates(value) }))
        })
        .catch((error) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            memoryGrowthCandidates: normalizeMemoryGrowthCandidates({ ok: false, error: errorLabel(error) })
          }))
        })
    }
    const loadStage8MemoryGovernance = (): void => {
      window.xinyu
        .getStage8MemoryGovernance()
        .then((value) => {
          if (!mounted) return
          setState((current) => ({ ...current, stage8MemoryGovernance: normalizeStage8MemoryGovernance(value) }))
        })
        .catch((error) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            stage8MemoryGovernance: normalizeStage8MemoryGovernance({ ok: false, status: 'unavailable', reason: errorLabel(error) })
          }))
        })
    }
    const loadKernelGovernance = (): void => {
      window.xinyu
        .getKernelGovernance()
        .then((value) => {
          if (!mounted) return
          setState((current) => ({ ...current, kernelGovernance: normalizeKernelGovernance(value) }))
        })
        .catch((error) => {
          if (!mounted) return
          setState((current) => ({
            ...current,
            kernelGovernance: normalizeKernelGovernance({ ok: false, available: false, error: errorLabel(error) })
          }))
        })
    }
    const loadAsyncExploration = (): void => {
      window.xinyu
        .getAsyncExplorationState()
        .then((value) => {
          if (!mounted) return
          setState((current) => ({ ...current, asyncExploration: normalizeAsyncExplorationState(value) }))
        })
        .catch(() => {
          if (!mounted) return
          setState((current) => ({ ...current, asyncExploration: normalizeAsyncExplorationState({ ok: false, status: 'unavailable' }) }))
        })
    }
    const loadStage12Gate = (): void => {
      window.xinyu
        .getStage12GateStatus()
        .then((value) => {
          if (!mounted) return
          setState((current) => ({ ...current, stage12Gate: normalizeStage12GateStatus(value) }))
        })
        .catch(() => {
          if (!mounted) return
          setState((current) => ({ ...current, stage12Gate: normalizeStage12GateStatus({ ok: false, status: 'unavailable' }) }))
        })
    }
    const loadStage13Gate = (): void => {
      window.xinyu
        .getStage13GateStatus()
        .then((value) => {
          if (!mounted) return
          setState((current) => ({ ...current, stage13Gate: normalizeStage13GateStatus(value) }))
        })
        .catch(() => {
          if (!mounted) return
          setState((current) => ({ ...current, stage13Gate: normalizeStage13GateStatus({ ok: false, status: 'unavailable' }) }))
        })
    }
    const loadImpulseSoup = (): void => {
      window.xinyu
        .getImpulseSoupState()
        .then((soup) => {
          if (!mounted) return
          setState((current) => ({ ...current, impulseSoup: normalizeImpulseSoupState(soup) }))
        })
        .catch(() => {
          if (!mounted) return
          setState((current) => ({ ...current, impulseSoup: normalizeImpulseSoupState({ ok: false, status: 'missing' }) }))
        })
    }
    const loadMetabolismTickets = (): void => {
      window.xinyu
        .listMetabolismTickets('requested,approved,running')
        .then((value) => {
          if (!mounted) return
          const result = asRecord(value)
          setMetabolismTickets(normalizeMetabolismTickets(result))
          if (result.accepted === false) {
            setMetabolismAction((current) =>
              current.kind === 'idle'
                ? { kind: 'idle', message: `代谢票据读取失败：${compact(String(result.error || '接口不可用'), 72)}` }
                : current
            )
          }
        })
        .catch((error) => {
          if (!mounted) return
          setMetabolismAction((current) =>
            current.kind === 'idle'
              ? { kind: 'idle', message: `代谢票据读取失败：${compact(errorLabel(error), 72)}` }
              : current
          )
        })
    }

    window.xinyu.getSnapshot().then((snapshot) => {
      if (!mounted) return
      setState((current) => applySnapshot(current, snapshot))
    })
    window.xinyu.getProactiveInbox().then((items) => {
      if (!mounted) return
      setState((current) => applyProactiveInbox(current, items))
    })
    window.xinyu.getGatewayStatus().then((gateway) => {
      if (!mounted) return
      setState((current) => ({ ...current, gateway: asRecord(gateway) as GatewayStatus }))
    })
    loadQQEnvironment()
    loadQQRuntimeConfig()
    loadApiConfig()
    loadExternalPlugins()
    loadStickerLibrary()
    loadMemoryGrowthCandidates()
    loadStage8MemoryGovernance()
    loadKernelGovernance()
    loadAsyncExploration()
    loadStage12Gate()
    loadStage13Gate()
    loadImpulseSoup()
    loadMetabolismTickets()
    const snapshotTimer = window.setInterval(() => {
      window.xinyu.getSnapshot().then((snapshot) => {
        if (!mounted) return
        setState((current) => applySnapshot(current, snapshot))
      })
    }, 60_000)
    const proactiveTimer = window.setInterval(() => {
      window.xinyu.getProactiveInbox().then((items) => {
        if (!mounted) return
        setState((current) => applyProactiveInbox(current, items))
      })
    }, 5_000)
    const qqTimer = window.setInterval(loadQQEnvironment, 15_000)
    const qqRuntimeTimer = window.setInterval(loadQQRuntimeConfig, 30_000)
    const apiConfigTimer = window.setInterval(loadApiConfig, 30_000)
    const externalPluginTimer = window.setInterval(loadExternalPlugins, 30_000)
    const stickerTimer = window.setInterval(loadStickerLibrary, 30_000)
    const memoryGrowthTimer = window.setInterval(loadMemoryGrowthCandidates, 30_000)
    const stage8MemoryTimer = window.setInterval(loadStage8MemoryGovernance, 30_000)
    const kernelGovernanceTimer = window.setInterval(loadKernelGovernance, 30_000)
    const impulseTimer = window.setInterval(loadImpulseSoup, 5_000)
    const metabolismTimer = window.setInterval(loadMetabolismTickets, 20_000)
    const offEvent = window.xinyu.onCoreEvent((event) => {
      setState((current) => applyEvent(current, event))
    })
    const offStatus = window.xinyu.onGatewayStatus((gateway) => {
      setState((current) => ({ ...current, gateway: asRecord(gateway) as GatewayStatus }))
    })
    return () => {
      mounted = false
      window.clearInterval(snapshotTimer)
      window.clearInterval(proactiveTimer)
      window.clearInterval(qqTimer)
      window.clearInterval(qqRuntimeTimer)
      window.clearInterval(apiConfigTimer)
      window.clearInterval(externalPluginTimer)
      window.clearInterval(stickerTimer)
      window.clearInterval(memoryGrowthTimer)
      window.clearInterval(stage8MemoryTimer)
      window.clearInterval(kernelGovernanceTimer)
      window.clearInterval(impulseTimer)
      window.clearInterval(metabolismTimer)
      offEvent()
      offStatus()
    }
  }, [])

  const xinyuState = React.useMemo(() => deriveXinYuState(state), [state])
  const intents = React.useMemo(() => buildProactiveIntents(state.proactiveInbox), [state.proactiveInbox])
  const proactiveHistory = React.useMemo(() => buildProactiveIntents(state.proactiveHistory), [state.proactiveHistory])
  const selectedIntent = React.useMemo(
    () =>
      intents.find((intent) => intent.id === selectedIntentId) ||
      proactiveHistory.find((intent) => intent.id === selectedIntentId) ||
      null,
    [intents, proactiveHistory, selectedIntentId]
  )
  const stats = React.useMemo(() => buildStats(state), [state])
  const connected = xinyuState.connection === 'online'
  const activeCommand = state.commands.find((command) => ['sending', 'accepted', 'started'].includes(command.status))
  const sending = Boolean(activeCommand)
  const latestEvent = state.events[0]
  const surfaceCue = React.useMemo(
    () =>
      buildAffectiveSurfaceCue({
        connection: xinyuState.connection,
        waitingReply: xinyuState.waitingReply,
        moodScore: xinyuState.moodScore,
        proactiveCount: intents.length,
        activeCommandId: activeCommand?.commandId,
        activeCommandStatus: activeCommand?.status,
        lastEventId: latestEvent?.id,
        lastEventType: latestEvent?.type,
        lastEventTs: latestEvent?.ts
      }),
    [
      activeCommand?.commandId,
      activeCommand?.status,
      intents.length,
      latestEvent?.id,
      latestEvent?.ts,
      latestEvent?.type,
      xinyuState.connection,
      xinyuState.moodScore,
      xinyuState.waitingReply
    ]
  )

  React.useEffect(() => {
    if (selectedIntentId && !selectedIntent) {
      setSelectedIntentId(null)
    }
  }, [selectedIntent, selectedIntentId])

  async function refreshApiConfig(): Promise<void> {
    setState((current) => ({
      ...current,
      apiConfigAction: { kind: 'loading', message: '正在读取 API 资料' }
    }))
    try {
      const status = normalizeApiConfigStatus(await window.xinyu.getApiConfigStatus())
      setState((current) => ({
        ...current,
        apiConfig: status,
        apiConfigAction: { kind: 'idle', message: 'API 资料已刷新' }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        apiConfigAction: { kind: 'idle', message: `API 资料刷新失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function saveApiConfigProfileFromPanel(profile: ApiConfigProfilePatch): Promise<string | null> {
    setState((current) => ({
      ...current,
      apiConfigAction: { kind: 'saving', message: '正在保存 API 资料' }
    }))
    try {
      const result = asRecord(await window.xinyu.saveApiConfigProfile(profile))
      const savedProfile = asRecord(result.profile)
      const savedProfileId = String(savedProfile.id || '')
      setState((current) => ({
        ...current,
        apiConfig: normalizeApiConfigStatus(result.status || {}),
        apiConfigAction: { kind: 'idle', message: apiConfigActionLabel(String(result.message || 'api_profile_saved'), true, result.error) }
      }))
      return savedProfileId || null
    } catch (error) {
      setState((current) => ({
        ...current,
        apiConfigAction: { kind: 'idle', message: `保存失败：${compact(errorLabel(error), 72)}` }
      }))
      return null
    }
  }

  async function testApiConfigProfileFromPanel(profile: ApiConfigProfilePatch): Promise<void> {
    setState((current) => ({
      ...current,
      apiConfigAction: { kind: 'testing', message: '正在测试 API 资料' }
    }))
    try {
      const result = asRecord(await window.xinyu.testApiConfigProfile(profile))
      const ok = Boolean(result.ok)
      const status = Number(result.status || 0)
      const elapsed = Number(result.elapsedMs || 0)
      const replyPreview = compact(String(result.replyPreview || ''), 36)
      const detail = ok
        ? `API 测试通过：响应码 ${status}, ${elapsed}ms${replyPreview ? `，${replyPreview}` : ''}`
        : `API 测试失败：${status ? `响应码 ${status}, ` : ''}${compact(apiConfigActionLabel(String(result.message || 'api_test_failed'), false, result.error), 72)}`
      setState((current) => ({
        ...current,
        apiConfigAction: { kind: 'idle', message: detail }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        apiConfigAction: { kind: 'idle', message: `API 测试失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function deleteApiConfigProfileFromPanel(profileId: string): Promise<void> {
    if (!profileId) {
      return
    }
    setState((current) => ({
      ...current,
      apiConfigAction: { kind: 'deleting', message: '正在删除 API 资料' }
    }))
    try {
      const result = asRecord(await window.xinyu.deleteApiConfigProfile(profileId))
      setState((current) => ({
        ...current,
        apiConfig: normalizeApiConfigStatus(result.status || {}),
        apiConfigAction: { kind: 'idle', message: apiConfigActionLabel(String(result.message || 'api_profile_deleted'), true, result.error) }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        apiConfigAction: { kind: 'idle', message: `删除失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function applyApiConfigProfileFromPanel(profileId: string): Promise<void> {
    if (!profileId) {
      return
    }
    setState((current) => ({
      ...current,
      apiConfigAction: { kind: 'applying', message: '正在应用 API 资料并重启核心' }
    }))
    try {
      const result = asRecord(await window.xinyu.applyApiConfigProfile({ profileId, restartCore: true }))
      const gateway = await window.xinyu.getGatewayStatus().catch(() => null)
      const accepted = result.accepted !== false
      setState((current) => ({
        ...current,
        gateway: asRecord(gateway) as GatewayStatus,
        apiConfig: normalizeApiConfigStatus(result.status || {}),
        apiConfigAction: {
          kind: 'idle',
          message: apiConfigActionLabel(String(result.message || 'api_profile_applied'), accepted, result.error)
        }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        apiConfigAction: { kind: 'idle', message: `应用失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function refreshMetabolismTickets(): Promise<void> {
    setMetabolismAction({ kind: 'loading', message: '正在刷新代谢票据' })
    try {
      const result = asRecord(await window.xinyu.listMetabolismTickets('requested,approved,running'))
      const tickets = normalizeMetabolismTickets(result)
      setMetabolismTickets(tickets)
      setMetabolismAction({
        kind: 'idle',
        message:
          result.accepted === false
            ? `刷新失败：${compact(String(result.error || '代谢票据接口不可用'), 72)}`
            : `已刷新 ${tickets.length} 张代谢票据`
      })
    } catch (error) {
      setMetabolismAction({ kind: 'idle', message: `刷新失败：${compact(errorLabel(error), 72)}` })
    }
  }

  async function refreshMetabolismTicketsQuietly(): Promise<void> {
    try {
      const result = asRecord(await window.xinyu.listMetabolismTickets('requested,approved,running'))
      setMetabolismTickets(normalizeMetabolismTickets(result))
    } catch {
      // Keep the decision result visible; the next timer/manual refresh can retry.
    }
  }

  async function yieldComputeFromPanel(ticketId: string, seconds: number): Promise<void> {
    if (!ticketId || metabolismAction.kind !== 'idle') {
      return
    }
    setMetabolismAction({ kind: 'yielding', ticketId, message: '正在提交让出计算' })
    try {
      const result = asRecord(await window.xinyu.yieldCompute({ ticketId, seconds, note: 'desktop_owner_yield_compute' }))
      const accepted = result.accepted !== false
      if (result.ticket) {
        setMetabolismTickets((current) => upsertMetabolismTicket(current, result.ticket))
      }
      setMetabolismAction({
        kind: 'idle',
        message: metabolismActionResultText('yield', accepted, String(result.error || result.message || ''))
      })
      await refreshMetabolismTicketsQuietly()
    } catch (error) {
      setMetabolismAction({ kind: 'idle', message: `让出计算失败：${compact(errorLabel(error), 72)}` })
    }
  }

  async function maintainBoundaryFromPanel(ticketId: string): Promise<void> {
    if (!ticketId || metabolismAction.kind !== 'idle') {
      return
    }
    setMetabolismAction({ kind: 'maintaining', ticketId, message: '正在提交守住边界' })
    try {
      const result = asRecord(await window.xinyu.maintainBoundary({ ticketId, note: 'desktop_owner_maintain_boundary' }))
      const accepted = result.accepted !== false
      if (result.ticket) {
        setMetabolismTickets((current) => upsertMetabolismTicket(current, result.ticket))
      }
      setMetabolismAction({
        kind: 'idle',
        message: metabolismActionResultText('maintain', accepted, String(result.error || result.message || ''))
      })
      await refreshMetabolismTicketsQuietly()
    } catch (error) {
      setMetabolismAction({ kind: 'idle', message: `守住边界失败：${compact(errorLabel(error), 72)}` })
    }
  }

  async function grantKernelScopeFromPanel(scope: string): Promise<void> {
    if (!scope || grantKernelScopeBusy) return
    setGrantKernelScopeBusy(scope)
    try {
      await window.xinyu.grantKernelScope({ scope, note: 'desktop_owner_grant' })
      const status = await window.xinyu.getKernelGovernance()
      setState((current) => ({
        ...current,
        kernelGovernance: normalizeKernelGovernance(status)
      }))
    } catch {
      // ignore
    } finally {
      setGrantKernelScopeBusy('')
    }
  }

  async function reviewKernelItemFromPanel(domain: string, itemId: string, decision: 'approve' | 'reject'): Promise<void> {
    const busyKey = `${domain}:${itemId}`
    if (!domain || !itemId || reviewKernelItemBusy) return
    setReviewKernelItemBusy(busyKey)
    try {
      await window.xinyu.reviewKernelItem({ domain, itemId, decision })
      const status = await window.xinyu.getKernelGovernance()
      setState((current) => ({
        ...current,
        kernelGovernance: normalizeKernelGovernance(status)
      }))
    } catch {
      // ignore
    } finally {
      setReviewKernelItemBusy('')
    }
  }

  async function reviewMemoryCandidateFromPanel(candidateId: string, decision: 'approve' | 'reject'): Promise<void> {
    if (!candidateId || reviewCandidateBusy) return
    setReviewCandidateBusy(candidateId)
    try {
      await window.xinyu.reviewMemoryCandidate({ candidateId, decision })
      const candidates = await window.xinyu.getMemoryGrowthCandidates()
      setState((current) => ({
        ...current,
        memoryGrowthCandidates: normalizeMemoryGrowthCandidates(candidates)
      }))
    } catch {
      // ignore
    } finally {
      setReviewCandidateBusy('')
    }
  }

  async function restartCoreBridgeFromPanel(): Promise<void> {
    setState((current) => ({
      ...current,
      apiConfigAction: { kind: 'restarting', message: '正在重启核心桥接' }
    }))
    try {
      const result = asRecord(await window.xinyu.restartCoreBridge())
      const status = normalizeApiConfigStatus(await window.xinyu.getApiConfigStatus())
      setState((current) => ({
        ...current,
        apiConfig: status,
        apiConfigAction: { kind: 'idle', message: apiConfigActionLabel(String(result.message || 'core_bridge_restarted'), true, result.error) }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        apiConfigAction: { kind: 'idle', message: `重启失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  function externalPluginsStatusFromResult(value: unknown) {
    const result = asRecord(value)
    const nested = asRecord(result.status)
    return normalizeExternalPluginsStatus(Array.isArray(result.plugins) ? result : nested.plugins ? nested : result)
  }

  async function refreshExternalPlugins(): Promise<void> {
    setState((current) => ({
      ...current,
      externalPluginAction: { kind: 'loading', message: '正在读取外部插件' }
    }))
    try {
      const status = normalizeExternalPluginsStatus(await window.xinyu.getExternalPlugins())
      setState((current) => ({
        ...current,
        externalPlugins: status,
        externalPluginAction: { kind: 'idle', message: '外部插件已刷新' }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        externalPluginAction: { kind: 'idle', message: `外部插件刷新失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function setExternalPluginConfigFromPanel(request: ExternalPluginConfigPatch): Promise<void> {
    if (!request.pluginId) {
      return
    }
    setState((current) => ({
      ...current,
      externalPluginAction: { kind: 'saving', pluginId: request.pluginId, message: '正在保存外部插件配置' }
    }))
    try {
      const result = asRecord(await window.xinyu.setExternalPluginConfig(request))
      setState((current) => ({
        ...current,
        externalPlugins: externalPluginsStatusFromResult(result),
        externalPluginAction: {
          kind: 'idle',
          message: externalPluginActionLabel(String(result.message || 'external_plugin_config_saved'), true, result.error)
        }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        externalPluginAction: { kind: 'idle', pluginId: request.pluginId, message: `外部插件保存失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function installExternalPluginFromPanel(request: ExternalPluginInstallRequest): Promise<void> {
    if (!request.pluginId) {
      return
    }
    setState((current) => ({
      ...current,
      externalPluginAction: { kind: 'installing', pluginId: request.pluginId, message: '正在安装外部插件' }
    }))
    try {
      const result = asRecord(await window.xinyu.installExternalPlugin(request))
      setState((current) => ({
        ...current,
        externalPlugins: externalPluginsStatusFromResult(result),
        externalPluginAction: {
          kind: 'idle',
          pluginId: request.pluginId,
          message: externalPluginActionLabel(
            String(result.message || result.error_code || (result.ok === false ? 'external_plugin_install_failed' : 'external_plugin_installed')),
            result.ok !== false,
            result.error
          )
        }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        externalPluginAction: { kind: 'idle', pluginId: request.pluginId, message: `外部插件安装失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function refreshQQEnvironment(): Promise<void> {
    setState((current) => ({
      ...current,
      qqAction: { kind: 'refreshing', message: '正在检查 QQ 链路' }
    }))

    try {
      const status = normalizeQQEnvironmentStatus(await window.xinyu.getQQEnvironmentStatus())
      setState((current) => ({
        ...current,
        qqEnvironment: status,
        qqAction: { kind: 'idle', message: qqEnvironmentMessage(status) }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        qqAction: { kind: 'idle', message: `检查失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function refreshStickerLibrary(): Promise<void> {
    setState((current) => ({
      ...current,
      stickerAction: { kind: 'refreshing', message: '正在读取表情索引' }
    }))
    try {
      const library = normalizeStickerLibrary(await window.xinyu.getStickerLibrary())
      setState((current) => ({
        ...current,
        stickerLibrary: library,
        stickerAction: { kind: 'idle', message: `已读取 ${library.total} 张表情` }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        stickerAction: { kind: 'idle', message: `读取失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function refreshImpulseSoup(): Promise<void> {
    setImpulseLoading(true)
    try {
      const soup = normalizeImpulseSoupState(await window.xinyu.getImpulseSoupState())
      setState((current) => ({ ...current, impulseSoup: soup }))
    } finally {
      setImpulseLoading(false)
    }
  }

  async function runStickerMaintenanceFromPanel(action: 'import-pending' | 'rebuild-index'): Promise<void> {
    const actionKind = action === 'import-pending' ? 'importing' : 'indexing'
    const actionText = action === 'import-pending' ? '正在整理待分类' : '正在重建索引'
    setState((current) => ({
      ...current,
      stickerAction: { kind: actionKind, message: actionText }
    }))
    try {
      const result = asRecord(await window.xinyu.runStickerMaintenance(action))
      const commandResult = asRecord(result.result)
      const moved = Number(commandResult.moved || commandResult.indexed || 0)
      const planned = Number(commandResult.planned || 0)
      const library = normalizeStickerLibrary(await window.xinyu.getStickerLibrary())
      setState((current) => ({
        ...current,
        stickerLibrary: library,
        stickerAction: {
          kind: 'idle',
          message:
            action === 'import-pending'
              ? `已整理 ${moved || planned} 张表情`
              : `已重建 ${moved || planned} 条索引`
        }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        stickerAction: { kind: 'idle', message: `操作失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function moveStickerToMoodFromPanel(file: string, mood: string): Promise<void> {
    const moodLabel = stickerMoodLabel(mood)
    setState((current) => ({
      ...current,
      stickerAction: { kind: 'moving', message: `正在归到${moodLabel}` }
    }))
    try {
      const result = asRecord(await window.xinyu.moveStickerToMood({ file, mood }))
      const library = normalizeStickerLibrary(await window.xinyu.getStickerLibrary())
      setState((current) => ({
        ...current,
        stickerLibrary: library,
        stickerAction: {
          kind: 'idle',
          message: Boolean(result.moved) ? `已归到${moodLabel}` : `已经在${moodLabel}`
        }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        stickerAction: { kind: 'idle', message: `调整失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function openStickerAssetDirFromPanel(): Promise<void> {
    setState((current) => ({
      ...current,
      stickerAction: { kind: 'opening', message: '正在打开表情目录' }
    }))
    try {
      await window.xinyu.openStickerAssetDir()
      setState((current) => ({
        ...current,
        stickerAction: { kind: 'idle', message: '已打开表情目录' }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        stickerAction: { kind: 'idle', message: `打开失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  function scheduleQQEnvironmentRefreshes(attempts = 12, intervalMs = 5000): void {
    let remaining = attempts
    const refreshOnce = (): void => {
      if (remaining <= 0) return
      remaining -= 1
      void window.xinyu
        .getQQEnvironmentStatus()
        .then((value) => {
          const status = normalizeQQEnvironmentStatus(value)
          setState((current) => ({
            ...current,
            qqEnvironment: status,
            qqAction:
              current.qqAction.kind === 'idle' && current.qqAction.message.startsWith('启动已提交')
                ? { kind: 'idle', message: `启动已提交，${qqEnvironmentMessage(status)}` }
                : current.qqAction
          }))
          if (!status.allReady && remaining > 0) {
            window.setTimeout(refreshOnce, intervalMs)
          }
        })
        .catch(() => {
          if (remaining > 0) {
            window.setTimeout(refreshOnce, intervalMs)
          }
        })
    }
    window.setTimeout(refreshOnce, intervalMs)
  }

  async function startQQEnvironmentFromPanel(): Promise<void> {
    setState((current) => ({
      ...current,
      qqAction: { kind: 'starting', message: '正在启动 QQ 环境' }
    }))

    try {
      const result = asRecord(await window.xinyu.startQQEnvironment())
      const status = normalizeQQEnvironmentStatus(result.status || (await window.xinyu.getQQEnvironmentStatus()))
      const resultMessage = String(result.message || '')
      const actionMessage =
        resultMessage === 'start_requested'
          ? `启动已提交，${qqEnvironmentMessage(status)}`
          : qqActionResultLabel(resultMessage, result.accepted !== false, result.error)
      setState((current) => ({
        ...current,
        qqEnvironment: status,
        qqAction: {
          kind: 'idle',
          message: actionMessage
        }
      }))
      if ((resultMessage === 'start_requested' || resultMessage === 'napcat_started') && !status.allReady) {
        scheduleQQEnvironmentRefreshes()
      }
    } catch (error) {
      setState((current) => ({
        ...current,
        qqAction: { kind: 'idle', message: `启动失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function openNapCatWebUIFromPanel(): Promise<void> {
    setState((current) => ({
      ...current,
      qqAction: { kind: 'opening', message: '正在打开 NapCat 网页端' }
    }))

    try {
      const result = asRecord(await window.xinyu.openNapCatWebUI())
      const status = normalizeQQEnvironmentStatus(result.status || (await window.xinyu.getQQEnvironmentStatus()))
      setState((current) => ({
        ...current,
        qqEnvironment: status,
        qqAction: {
          kind: 'idle',
          message: qqActionResultLabel(String(result.message || ''), result.accepted !== false, result.error)
        }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        qqAction: { kind: 'idle', message: `打开失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function copyNapCatWebUITokenFromPanel(): Promise<void> {
    setState((current) => ({
      ...current,
      qqAction: { kind: 'copying', message: '正在复制网页端口令' }
    }))

    try {
      const result = asRecord(await window.xinyu.copyNapCatWebUIToken())
      const status = normalizeQQEnvironmentStatus(result.status || (await window.xinyu.getQQEnvironmentStatus()))
      setState((current) => ({
        ...current,
        qqEnvironment: status,
        qqAction: {
          kind: 'idle',
          message: qqActionResultLabel(String(result.message || ''), result.accepted !== false, result.error)
        }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        qqAction: { kind: 'idle', message: `复制失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function setQQRuntimeConfigFromPanel(patch: QQRuntimeConfigPatch): Promise<void> {
    setState((current) => ({
      ...current,
      qqRuntimeAction: { kind: 'applying', message: '正在应用 QQ 设置' }
    }))

    try {
      const result = asRecord(await window.xinyu.setQQRuntimeConfig(patch))
      const nextState: Partial<AppState> = {
        qqRuntimeConfig: normalizeQQRuntimeConfig(result.config || {}),
        qqRuntimeAction: {
          kind: 'idle',
          message: qqRuntimeResultLabel(String(result.message || ''), result.accepted !== false, result.error)
        }
      }
      if (result.status) {
        nextState.qqEnvironment = normalizeQQEnvironmentStatus(result.status)
      }
      setState((current) => ({ ...current, ...nextState }))
    } catch (error) {
      setState((current) => ({
        ...current,
        qqRuntimeAction: { kind: 'idle', message: `应用失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function restartQQGatewayFromPanel(): Promise<void> {
    setState((current) => ({
      ...current,
      qqRuntimeAction: { kind: 'restarting', message: '正在重启 QQ 网关' }
    }))

    try {
      const result = asRecord(await window.xinyu.restartQQGateway())
      const nextState: Partial<AppState> = {
        qqRuntimeConfig: normalizeQQRuntimeConfig(result.config || {}),
        qqRuntimeAction: {
          kind: 'idle',
          message: qqRuntimeResultLabel(String(result.message || ''), result.accepted !== false, result.error)
        }
      }
      if (result.status) {
        nextState.qqEnvironment = normalizeQQEnvironmentStatus(result.status)
      }
      setState((current) => ({ ...current, ...nextState }))
    } catch (error) {
      setState((current) => ({
        ...current,
        qqRuntimeAction: { kind: 'idle', message: `重启失败：${compact(errorLabel(error), 72)}` }
      }))
    }
  }

  async function submitChat(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const text = input.trim()
    if (!text || sending) {
      return
    }

    const commandId = createCommandId()
    const routeCodex = codexMode
    const allowLocalWrite = routeCodex && codexLocalWrite
    const command: CommandState = {
      commandId,
      textPreview: compact(`${routeCodex ? 'Codex：' : ''}${text}`, 180),
      kind: routeCodex ? 'codex' : 'chat',
      localWrite: allowLocalWrite,
      status: 'sending',
      message: '正在交给核心'
    }

    setInput('')
    setState((current) => ({
      ...current,
      commands: [command, ...current.commands].slice(0, 12)
    }))

    const result = asRecord(await window.xinyu.sendChat({ text, commandId, codexMode: routeCodex, allowLocalWrite }))
    if (result.accepted === false) {
      setInput((current) => current || text)
      setState((current) => updateCommand(current, commandId, 'failed', chatErrorLabel(String(result.error || 'chat_request_failed'))))
      return
    }

    setState((current) => updateCommand(current, commandId, 'accepted', '核心已接收', String(result.turnId || '')))
  }

  async function replyToProactive(intent: ProactiveIntent, text: string): Promise<void> {
    const replyText = text.trim()
    if (!replyText || sending || state.proactiveActions[intent.id]) {
      return
    }

    const commandId = createCommandId()
    const command: CommandState = {
      commandId,
      textPreview: compact(`回复主动提醒：${replyText}`, 180),
      status: 'sending',
      message: '正在交给核心'
    }
    setState((current) => ({
      ...current,
      commands: [command, ...current.commands].slice(0, 12),
      proactiveActions: { ...current.proactiveActions, [intent.id]: 'reply' }
    }))

    const result = asRecord(
      await window.xinyu.sendChat({
        text: replyText,
        commandId,
        proactiveCandidateId: intent.id,
        proactivePreview: intent.fullText || intent.plannedText
      })
    )
    if (result.accepted === false) {
      setProactiveFeedback((current) => ({
        ...current,
        [intent.id]: `回复失败：${chatErrorLabel(String(result.error || 'chat_request_failed'))}`
      }))
      setState((current) => {
        const { [intent.id]: _removed, ...rest } = current.proactiveActions
        return {
          ...current,
          proactiveActions: rest,
          commands: current.commands.map((item) =>
            item.commandId === commandId ? { ...item, status: 'failed', message: chatErrorLabel(String(result.error || 'chat_request_failed')) } : item
          )
        }
      })
      return
    }

    setState((current) => updateCommand(current, commandId, 'accepted', '核心已接收', String(result.turnId || '')))
    const ack = asRecord(await window.xinyu.ackProactive({ candidateId: intent.id, action: 'reply' }))
    if (ack.accepted === false) {
      setProactiveFeedback((current) => ({
        ...current,
        [intent.id]: proactiveAckResultLabel('reply', false, ack.error || ack.message, Array.isArray(ack.notes) ? ack.notes : [])
      }))
      setState((current) => {
        const { [intent.id]: _removed, ...rest } = current.proactiveActions
        return { ...current, proactiveActions: rest }
      })
      return
    }
    setProactiveFeedback((current) => ({ ...current, [intent.id]: proactiveAckResultLabel('reply', true) }))
    const handledAt = new Date().toISOString()
    setState((current) => {
      const { [intent.id]: _removed, ...rest } = current.proactiveActions
      const rawIntent = current.proactiveInbox.find((item) => String(asRecord(item).candidateId || asRecord(item).id || '') === intent.id)
      const handledItem = {
        ...asRecord(rawIntent),
        candidateId: intent.id,
        status: 'replied',
        desktopAction: 'reply',
        updatedAt: handledAt,
        handledAt
      }
      return {
        ...current,
        proactiveActions: rest,
        proactiveInbox: current.proactiveInbox.filter((item) => String(asRecord(item).candidateId || asRecord(item).id || '') !== intent.id),
        proactiveHistory: [handledItem, ...current.proactiveHistory.filter((item) => String(asRecord(item).candidateId || asRecord(item).id || '') !== intent.id)].slice(0, 20)
      }
    })
    const inbox = await window.xinyu.getProactiveInbox().catch(() => null)
    if (inbox) {
      setState((current) => applyProactiveInbox(current, inbox))
    }
    setSelectedIntentId(null)
  }

  async function ackProactive(candidateId: string, action: ProactiveAction): Promise<void> {
    if (!candidateId || state.proactiveActions[candidateId]) {
      return
    }
    const intent = intents.find((item) => item.id === candidateId)
    if (action === 'approve_qq' && intent && !intent.claimable) {
      setProactiveFeedback((current) => ({
        ...current,
        [candidateId]: proactiveAckResultLabel(action, false, 'desktop_proactive_candidate_not_qq_claimable')
      }))
      setSelectedIntentId(candidateId)
      return
    }

    setProactiveFeedback((current) => {
      const { [candidateId]: _removed, ...rest } = current
      return rest
    })
    setState((current) => ({
      ...current,
      proactiveActions: { ...current.proactiveActions, [candidateId]: action }
    }))

    let result: JsonRecord
    try {
      result = asRecord(await window.xinyu.ackProactive({ candidateId, action }))
    } catch (error) {
      setProactiveFeedback((current) => ({
        ...current,
        [candidateId]: proactiveAckResultLabel(action, false, errorLabel(error))
      }))
      setState((current) => {
        const { [candidateId]: _removed, ...rest } = current.proactiveActions
        return { ...current, proactiveActions: rest }
      })
      return
    }

    const notes = Array.isArray(result.notes) ? result.notes : []
    if (result.accepted === false) {
      setProactiveFeedback((current) => ({
        ...current,
        [candidateId]: proactiveAckResultLabel(action, false, result.error || result.message, notes)
      }))
      setState((current) => {
        const { [candidateId]: _removed, ...rest } = current.proactiveActions
        return { ...current, proactiveActions: rest }
      })
      return
    }

    const handledAt = new Date().toISOString()
    const fallbackStatus =
      action === 'approve_qq' ? 'queued_qq' : action === 'dismiss' ? 'dismissed' : action === 'read_locally' ? 'read_locally' : 'replied'
    setProactiveFeedback((current) => ({
      ...current,
      [candidateId]: proactiveAckResultLabel(action, true)
    }))
    setState((current) => {
      const { [candidateId]: _removed, ...rest } = current.proactiveActions
      const rawIntent = current.proactiveInbox.find((item) => String(asRecord(item).candidateId || asRecord(item).id || '') === candidateId)
      const handledItem = {
        ...asRecord(rawIntent),
        candidateId,
        status: String(result.status || fallbackStatus),
        desktopAction: action,
        updatedAt: handledAt,
        handledAt
      }
      return {
        ...current,
        proactiveActions: rest,
        proactiveInbox: current.proactiveInbox.filter((item) => String(asRecord(item).candidateId || asRecord(item).id || '') !== candidateId),
        proactiveHistory: [handledItem, ...current.proactiveHistory.filter((item) => String(asRecord(item).candidateId || asRecord(item).id || '') !== candidateId)].slice(0, 20)
      }
    })

    const inbox = await window.xinyu.getProactiveInbox().catch(() => null)
    if (inbox) {
      setState((current) => applyProactiveInbox(current, inbox))
    }
    setSelectedIntentId((current) => (current === candidateId ? null : current))
  }

  async function decideSelfActionApproval(
    queueId: string,
    decision: 'approved' | 'denied',
    options: { authorizeExisting?: boolean } = {}
  ): Promise<void> {
    if (!queueId || selfActionApprovalBusy) {
      return
    }
    setSelfActionApprovalBusy(decision)
    try {
      const result = asRecord(
        await window.xinyu.decideSelfActionApproval({
          queueId,
          decision,
          execute: decision === 'approved',
          authorizeCodex: decision === 'approved',
          authorizeExisting: Boolean(options.authorizeExisting)
        })
      )
      if (result.selfAction && typeof result.selfAction === 'object') {
        setState((current) => ({
          ...current,
          snapshot: {
            ...(current.snapshot || {}),
            selfAction: result.selfAction as Snapshot['selfAction']
          }
        }))
      }
      const snapshot = await window.xinyu.getSnapshot()
      setState((current) => applySnapshot(current, snapshot))
    } finally {
      setSelfActionApprovalBusy('')
    }
  }

  async function pausePrivateShare(paused: boolean): Promise<void> {
    if (privateShareBusy) {
      return
    }
    setPrivateShareBusy(true)
    try {
      await window.xinyu.pausePrivateShare({ paused })
      const snapshot = await window.xinyu.getSnapshot()
      setState((current) => applySnapshot(current, snapshot))
    } finally {
      setPrivateShareBusy(false)
    }
  }

  async function setOwnerPrivateShareEnabled(enabled: boolean): Promise<void> {
    if (privateShareBusy) {
      return
    }
    setPrivateShareBusy(true)
    setPrivateEcosystemResult(enabled ? '正在写入主动私聊授权' : '正在撤销主动私聊授权')
    try {
      const api = xinyuApi()
      if (typeof api.setOwnerPrivateShareEnabled !== 'function') {
        throw new Error('preload_missing_owner_private_share_grant; restart Desktop')
      }
      const result = asRecord(await api.setOwnerPrivateShareEnabled({ enabled }))
      const ok = result.accepted !== false && result.ok !== false
      const privateEcosystem = result.privateEcosystem
      if (privateEcosystem && typeof privateEcosystem === 'object') {
        setState((current) => ({
          ...current,
          snapshot: {
            ...(current.snapshot || {}),
            privateEcosystem: privateEcosystem as Snapshot['privateEcosystem']
          }
        }))
      } else {
        await refreshDesktopSnapshotState()
      }
      setPrivateEcosystemResult(
        ok
          ? enabled
            ? '已启用主动私聊授权；仍只会进入受控候选/队列'
            : '已关闭主动私聊授权'
          : `主动私聊授权失败：${desktopInternalErrorText(String(result.error || 'grant_failed'))}`
      )
    } catch (error) {
      setPrivateEcosystemResult(`主动私聊授权失败：${desktopInternalErrorText(error)}`)
    } finally {
      setPrivateShareBusy(false)
    }
  }

  async function refreshDesktopSnapshotState(): Promise<void> {
    const snapshot = await window.xinyu.getSnapshot()
    setState((current) => applySnapshot(current, snapshot))
  }

  async function tickPrivateEcosystem(): Promise<void> {
    if (privateEcosystemBusy) {
      return
    }
    setPrivateEcosystemBusy(true)
    setPrivateEcosystemResult('正在推进目标循环')
    try {
      if (typeof window.xinyu.tickPrivateEcosystem !== 'function') {
        throw new Error('preload_missing_private_ecosystem_tick; restart Desktop')
      }
      const result = asRecord(await window.xinyu.tickPrivateEcosystem())
      const ok = Boolean(result.accepted)
      const goal = privateEcosystemGoalText(String(result.goalId || 'none'))
      const action = privateEcosystemActionText(String(result.actionKind || 'none'))
      const status = privateEcosystemStatusText(String(result.actionStatus || result.error || (ok ? 'completed' : 'failed')))
      setPrivateEcosystemResult(ok ? `已推进：${goal} / ${action} / ${status}` : `推进失败：${status}`)
      const privateEcosystem = result.privateEcosystem
      if (privateEcosystem && typeof privateEcosystem === 'object') {
        setState((current) => ({
          ...current,
          snapshot: {
            ...(current.snapshot || {}),
            privateEcosystem: privateEcosystem as Snapshot['privateEcosystem']
          }
        }))
      } else {
        await refreshDesktopSnapshotState()
      }
    } catch (error) {
      setPrivateEcosystemResult(`推进失败：${desktopInternalErrorText(error)}`)
    } finally {
      setPrivateEcosystemBusy(false)
    }
  }

  async function setPrivateEcosystemEnabled(enabled: boolean): Promise<void> {
    if (privateEcosystemBusy) {
      return
    }
    setPrivateEcosystemBusy(true)
    setPrivateEcosystemResult(enabled ? '正在启动目标循环' : '正在关闭目标循环')
    try {
      if (typeof window.xinyu.setPrivateEcosystemEnabled !== 'function') {
        throw new Error('preload_missing_private_ecosystem_set_enabled; restart Desktop')
      }
      const result = asRecord(await window.xinyu.setPrivateEcosystemEnabled({ enabled }))
      const ok = Boolean(result.accepted)
      const privateEcosystem = result.privateEcosystem
      if (privateEcosystem && typeof privateEcosystem === 'object') {
        setState((current) => ({
          ...current,
          snapshot: {
            ...(current.snapshot || {}),
            privateEcosystem: privateEcosystem as Snapshot['privateEcosystem']
          }
        }))
      }
      if (!ok) {
        setPrivateEcosystemResult(`目标循环授权失败：${privateEcosystemStatusText(String(result.error || 'failed'))}`)
        await refreshDesktopSnapshotState()
        return
      }
      if (!enabled) {
        setPrivateEcosystemResult('已关闭目标循环')
        await refreshDesktopSnapshotState()
        return
      }
      setPrivateEcosystemResult('已启动目标循环，正在生成当前目标')
      if (typeof window.xinyu.tickPrivateEcosystem !== 'function') {
        await refreshDesktopSnapshotState()
        return
      }
      const tick = asRecord(await window.xinyu.tickPrivateEcosystem())
      const tickOk = Boolean(tick.accepted)
      const goal = privateEcosystemGoalText(String(tick.goalId || 'none'))
      const action = privateEcosystemActionText(String(tick.actionKind || 'none'))
      const status = privateEcosystemStatusText(String(tick.actionStatus || tick.error || (tickOk ? 'completed' : 'failed')))
      setPrivateEcosystemResult(
        tickOk ? `已启动并生成目标：${goal} / ${action} / ${status}` : `已启动；首次推进失败：${status}`
      )
      const tickSnapshot = tick.privateEcosystem
      if (tickSnapshot && typeof tickSnapshot === 'object') {
        setState((current) => ({
          ...current,
          snapshot: {
            ...(current.snapshot || {}),
            privateEcosystem: tickSnapshot as Snapshot['privateEcosystem']
          }
        }))
      } else {
        await refreshDesktopSnapshotState()
      }
    } catch (error) {
      setPrivateEcosystemResult(`目标循环操作失败：${desktopInternalErrorText(error)}`)
    } finally {
      setPrivateEcosystemBusy(false)
    }
  }

  async function setPrivateBrowserGrant(patch: PrivateBrowserGrantPatch): Promise<void> {
    if (browserGrantBusy) {
      return
    }
    setBrowserGrantBusy(true)
    setBrowserGrantResult(patch.enabled ? '正在保存只读浏览授权' : '正在撤销浏览授权')
    try {
      const api = xinyuApi()
      if (typeof api.setPrivateBrowserGrant !== 'function') {
        throw new Error('preload_missing_private_browser_grant; restart Desktop')
      }
      const result = asRecord(
        await api.setPrivateBrowserGrant({
          enabled: patch.enabled,
          readOnly: patch.readOnly,
          allowedUrls: patch.allowedUrls
        })
      )
      const ok = result.accepted !== false && result.ok !== false
      const privateEcosystem = result.privateEcosystem
      if (privateEcosystem && typeof privateEcosystem === 'object') {
        setState((current) => ({
          ...current,
          snapshot: {
            ...(current.snapshot || {}),
            privateEcosystem: privateEcosystem as Snapshot['privateEcosystem']
          }
        }))
      } else {
        await refreshDesktopSnapshotState()
      }
      setBrowserGrantResult(
        ok
          ? patch.enabled
            ? `已保存只读浏览授权：${patch.allowedUrls.length} 个 allowed_url`
            : '已撤销只读浏览授权'
          : `浏览授权失败：${privateBrowserResultText(String(result.error || result.message || 'grant_failed'))}`
      )
    } catch (error) {
      setBrowserGrantResult(`浏览授权失败：${desktopInternalErrorText(error)}`)
    } finally {
      setBrowserGrantBusy(false)
    }
  }

  async function observePrivateBrowser(url: string): Promise<void> {
    const target = url.trim()
    if (!target || browserObserveBusy) {
      return
    }
    setBrowserObserveBusy(true)
    setBrowserObserveResult('')
    try {
      const result = asRecord(await window.xinyu.observePrivateBrowser({ url: target }))
      const ok = Boolean(result.accepted)
      const detail = String(result.result || result.reason || result.error || (ok ? 'read_only_allowed' : 'blocked'))
      setBrowserObserveResult(ok ? `只读观察已提交：${privateBrowserResultText(detail)}` : `只读观察失败：${privateBrowserResultText(detail)}`)
      const snapshot = await window.xinyu.getSnapshot()
      setState((current) => applySnapshot(current, snapshot))
    } finally {
      setBrowserObserveBusy(false)
    }
  }

  async function refreshPrivateDesktop(): Promise<void> {
    if (typeof window.xinyu.getPrivateDesktopSnapshot !== 'function') {
      setPrivateDesktopResult('隔离桌面接口未加载，请重启 Desktop')
      return
    }
    try {
      const result = asRecord(await window.xinyu.getPrivateDesktopSnapshot())
      const snap = result.privateDesktop
      if (snap && typeof snap === 'object') {
        setPrivateDesktop(snap as Record<string, unknown>)
      }
      if (result.ok === false || result.accepted === false) {
        setPrivateDesktopResult(`隔离桌面快照失败：${privateDesktopResultText(String(result.error || 'failed'))}`)
      }
    } catch (error) {
      setPrivateDesktopResult(`隔离桌面快照失败：${desktopInternalErrorText(error)}`)
    }
  }

  async function setPrivateDesktopEnabled(enabled: boolean): Promise<void> {
    if (privateDesktopBusy) {
      return
    }
    setPrivateDesktopBusy(true)
    setPrivateDesktopResult('')
    try {
      if (typeof window.xinyu.setPrivateDesktopEnabled !== 'function') {
        throw new Error('preload_missing_private_desktop_set_enabled; restart Desktop')
      }
      const result = asRecord(await window.xinyu.setPrivateDesktopEnabled({ enabled }))
      const ok = Boolean(result.accepted)
      setPrivateDesktopResult(
        ok
          ? enabled
            ? '已授权（仅观察）'
            : '已撤销授权'
          : `授权失败：${privateDesktopResultText(String(result.error || 'failed'))}`
      )
      await refreshPrivateDesktop()
    } catch (error) {
      setPrivateDesktopResult(`授权失败：${desktopInternalErrorText(error)}`)
    } finally {
      setPrivateDesktopBusy(false)
    }
  }

  async function controlPrivateDesktop(action: 'start' | 'stop'): Promise<void> {
    if (privateDesktopBusy) {
      return
    }
    setPrivateDesktopBusy(true)
    setPrivateDesktopResult('')
    try {
      const method = action === 'start' ? window.xinyu.startPrivateDesktop : window.xinyu.stopPrivateDesktop
      if (typeof method !== 'function') {
        throw new Error(`preload_missing_private_desktop_${action}; restart Desktop`)
      }
      const result = asRecord(await method())
      const ok = Boolean(result.accepted)
      const detail = privateDesktopResultText(String(result.error || result.sessionState || (ok ? 'ok' : 'failed')))
      setPrivateDesktopResult(
        ok
          ? `${action === 'start' ? '已启动' : '已停止'} ${detail}`
          : `${action === 'start' ? '启动失败' : '停止失败'}：${detail}`
      )
      const snap = result.privateDesktop
      if (snap && typeof snap === 'object') {
        setPrivateDesktop(snap as Record<string, unknown>)
      }
    } catch (error) {
      setPrivateDesktopResult(`${action === 'start' ? '启动失败' : '停止失败'}：${desktopInternalErrorText(error)}`)
    } finally {
      setPrivateDesktopBusy(false)
      await refreshPrivateDesktop()
    }
  }

  async function observePrivateDesktop(): Promise<void> {
    if (privateDesktopBusy) {
      return
    }
    setPrivateDesktopBusy(true)
    setPrivateDesktopResult('正在观察隔离桌面')
    try {
      if (typeof window.xinyu.observePrivateDesktop !== 'function') {
        throw new Error('preload_missing_private_desktop_observe; restart Desktop')
      }
      const result = asRecord(await window.xinyu.observePrivateDesktop())
      const ok = Boolean(result.accepted)
      const detail = String(result.result || result.error || (ok ? 'completed' : 'failed'))
      const detailLabel = detail === 'completed' ? '已刷新画面' : privateDesktopResultText(detail)
      setPrivateDesktopResult(ok ? `已观察：${detailLabel}` : `观察失败：${detailLabel}`)
      const snap = result.privateDesktop
      if (snap && typeof snap === 'object') {
        setPrivateDesktop(snap as Record<string, unknown>)
      }
    } catch (error) {
      setPrivateDesktopResult(`观察失败：${desktopInternalErrorText(error)}`)
    } finally {
      setPrivateDesktopBusy(false)
      await refreshPrivateDesktop()
    }
  }

  React.useEffect(() => {
    void refreshPrivateDesktop()
    const timer = setInterval(() => void refreshPrivateDesktop(), 10000)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <AffectiveSurfaceProvider cue={surfaceCue}>
      <SurfacePart name="root" as="main" className="app-shell">
        <SurfacePart name="ambientLight" as="span" className="affective-ambient-light" aria-hidden="true" />
        <SurfacePart name="noise" as="span" className="affective-noise" aria-hidden="true" />
        <header className="topbar">
          <div className="brand-lockup">
            <img src={avatarSrc} alt="心玉" />
            <div>
              <h1>心玉</h1>
              <p>私有频道</p>
            </div>
          </div>

          <div className="topbar-status">
            <ThemeSwitcher theme={theme} onChange={setTheme} />
            <button
              type="button"
              className="impulse-open-button"
              onClick={() => {
                setImpulseObserverOpen(true)
                void refreshImpulseSoup()
              }}
              title="打开涌现池观察窗"
            >
              <Activity size={14} />
              <span>{state.impulseSoup?.activeCount ?? 0}</span>
            </button>
            <StatusBadge connected={connected} connecting={xinyuState.connection === 'connecting'} />
            <span className="sync-stamp">
              <Clock3 size={14} />
              {formatTime(state.snapshot?.snapshotAt || state.gateway?.snapshotAt)}
            </span>
          </div>
        </header>

        <AutonomyGatePanel
          stage12={state.stage12Gate}
          stage13={state.stage13Gate}
          qqEnvironment={state.qqEnvironment}
          stage8={state.stage8MemoryGovernance}
          asyncExploration={state.asyncExploration}
          kernelGovernance={state.kernelGovernance}
        />

        <section className="presence-workspace">
          <MindStatePanel
            state={xinyuState}
            stats={stats}
            gateway={state.gateway}
            snapshot={state.snapshot}
            selfActionApprovalBusy={selfActionApprovalBusy}
            onDecideSelfActionApproval={decideSelfActionApproval}
            privateShareBusy={privateShareBusy}
            privateEcosystemBusy={privateEcosystemBusy}
            privateEcosystemResult={privateEcosystemResult}
            onPausePrivateShare={pausePrivateShare}
            onSetPrivateShareEnabled={(enabled) => void setOwnerPrivateShareEnabled(enabled)}
            onSetPrivateEcosystemEnabled={(enabled) => void setPrivateEcosystemEnabled(enabled)}
            onTickPrivateEcosystem={() => void tickPrivateEcosystem()}
            browserGrantBusy={browserGrantBusy}
            browserGrantResult={browserGrantResult}
            onSetPrivateBrowserGrant={(patch) => void setPrivateBrowserGrant(patch)}
            browserObserveBusy={browserObserveBusy}
            browserObserveResult={browserObserveResult}
            onObservePrivateBrowser={observePrivateBrowser}
            privateDesktop={privateDesktop}
            privateDesktopBusy={privateDesktopBusy}
            onStartPrivateDesktop={() => void controlPrivateDesktop('start')}
            onStopPrivateDesktop={() => void controlPrivateDesktop('stop')}
            onObservePrivateDesktop={() => void observePrivateDesktop()}
            onRefreshPrivateDesktop={() => void refreshPrivateDesktop()}
            onSetPrivateDesktopEnabled={(enabled) => void setPrivateDesktopEnabled(enabled)}
            privateDesktopResult={privateDesktopResult}
          />

          <InteractionStream
            xinyuState={xinyuState}
            commands={state.commands}
            turns={state.recentTurns}
            events={state.events}
            qqRuntimeConfig={state.qqRuntimeConfig}
            input={input}
            codexMode={codexMode}
            allowLocalWrite={codexLocalWrite}
            sending={sending}
            onInput={setInput}
            onCodexModeChange={(next) => {
              setCodexMode(next)
              if (!next) {
                setCodexLocalWrite(false)
              }
            }}
            onLocalWriteChange={setCodexLocalWrite}
            onSubmit={submitChat}
          />

          <IntentQueuePanel
            intents={intents}
            history={proactiveHistory}
            pending={state.proactiveActions}
            feedback={proactiveFeedback}
            actionDigest={state.snapshot?.actionDigestState}
            recentMemoryEvents={state.recentMemoryEvents}
            lastEvent={state.events[0]}
            apiConfig={state.apiConfig}
            apiConfigAction={state.apiConfigAction}
            externalPlugins={state.externalPlugins}
            externalPluginAction={state.externalPluginAction}
            qqEnvironment={state.qqEnvironment}
            qqAction={state.qqAction}
            qqRuntimeConfig={state.qqRuntimeConfig}
            qqRuntimeAction={state.qqRuntimeAction}
            stickerLibrary={state.stickerLibrary}
            stickerAction={state.stickerAction}
            onAck={ackProactive}
            onOpenDetail={setSelectedIntentId}
            onRefreshApiConfig={refreshApiConfig}
            onSaveApiConfigProfile={saveApiConfigProfileFromPanel}
            onTestApiConfigProfile={testApiConfigProfileFromPanel}
            onDeleteApiConfigProfile={deleteApiConfigProfileFromPanel}
            onApplyApiConfigProfile={applyApiConfigProfileFromPanel}
            onRestartCoreBridge={restartCoreBridgeFromPanel}
            onRefreshExternalPlugins={refreshExternalPlugins}
            onSetExternalPluginConfig={setExternalPluginConfigFromPanel}
            onInstallExternalPlugin={installExternalPluginFromPanel}
            onRefreshQQ={refreshQQEnvironment}
            onStartQQ={startQQEnvironmentFromPanel}
            onOpenNapCat={openNapCatWebUIFromPanel}
            onCopyNapCatToken={copyNapCatWebUITokenFromPanel}
            onSetQQRuntimeConfig={setQQRuntimeConfigFromPanel}
            onRestartQQGateway={restartQQGatewayFromPanel}
            onRefreshStickerLibrary={refreshStickerLibrary}
            onRunStickerMaintenance={runStickerMaintenanceFromPanel}
            onMoveStickerToMood={moveStickerToMoodFromPanel}
            onOpenStickerAssetDir={openStickerAssetDirFromPanel}
          />

          <SystemControlPanel
            apiConfig={state.apiConfig}
            apiConfigAction={state.apiConfigAction}
            externalPlugins={state.externalPlugins}
            externalPluginAction={state.externalPluginAction}
            qqEnvironment={state.qqEnvironment}
            qqAction={state.qqAction}
            qqRuntimeConfig={state.qqRuntimeConfig}
            qqRuntimeAction={state.qqRuntimeAction}
            stickerLibrary={state.stickerLibrary}
            stickerAction={state.stickerAction}
            metabolismTickets={metabolismTickets}
            metabolismAction={metabolismAction}
            memoryGrowthCandidates={state.memoryGrowthCandidates}
            stage8MemoryGovernance={state.stage8MemoryGovernance}
            kernelGovernance={state.kernelGovernance}
            actionDigest={state.snapshot?.actionDigestState}
            recentMemoryEvents={state.recentMemoryEvents}
            lastEvent={state.events[0]}
            onRefreshApiConfig={refreshApiConfig}
            onSaveApiConfigProfile={saveApiConfigProfileFromPanel}
            onTestApiConfigProfile={testApiConfigProfileFromPanel}
            onDeleteApiConfigProfile={deleteApiConfigProfileFromPanel}
            onApplyApiConfigProfile={applyApiConfigProfileFromPanel}
            onRestartCoreBridge={restartCoreBridgeFromPanel}
            onRefreshExternalPlugins={refreshExternalPlugins}
            onSetExternalPluginConfig={setExternalPluginConfigFromPanel}
            onInstallExternalPlugin={installExternalPluginFromPanel}
            onRefreshQQ={refreshQQEnvironment}
            onStartQQ={startQQEnvironmentFromPanel}
            onOpenNapCat={openNapCatWebUIFromPanel}
            onCopyNapCatToken={copyNapCatWebUITokenFromPanel}
            onSetQQRuntimeConfig={setQQRuntimeConfigFromPanel}
            onRestartQQGateway={restartQQGatewayFromPanel}
            onRefreshStickerLibrary={refreshStickerLibrary}
            onRunStickerMaintenance={runStickerMaintenanceFromPanel}
            onMoveStickerToMood={moveStickerToMoodFromPanel}
            onOpenStickerAssetDir={openStickerAssetDirFromPanel}
            onRefreshMetabolismTickets={() => void refreshMetabolismTickets()}
            onYieldCompute={(ticketId, seconds) => void yieldComputeFromPanel(ticketId, seconds)}
            onMaintainBoundary={(ticketId) => void maintainBoundaryFromPanel(ticketId)}
            onReviewMemoryCandidate={reviewMemoryCandidateFromPanel}
            reviewMemoryCandidateBusy={reviewCandidateBusy}
            onReviewKernelItem={reviewKernelItemFromPanel}
            reviewKernelItemBusy={reviewKernelItemBusy}
            onGrantKernelScope={grantKernelScopeFromPanel}
            grantKernelScopeBusy={grantKernelScopeBusy}
          />
        </section>

        {selectedIntent ? (
          <IntentDetailDialog
            intent={selectedIntent}
            pendingAction={state.proactiveActions[selectedIntent.id]}
            feedback={proactiveFeedback[selectedIntent.id]}
            onClose={() => setSelectedIntentId(null)}
            onAck={ackProactive}
            onReply={replyToProactive}
          />
        ) : null}

        {impulseObserverOpen ? (
          <ImpulseObserverDialog
            soup={state.impulseSoup}
            loading={impulseLoading}
            onClose={() => setImpulseObserverOpen(false)}
            onRefresh={refreshImpulseSoup}
          />
        ) : null}
      </SurfacePart>
    </AffectiveSurfaceProvider>
  )
}


ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
