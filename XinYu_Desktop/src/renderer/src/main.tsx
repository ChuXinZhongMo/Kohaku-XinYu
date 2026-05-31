import React from 'react'
import ReactDOM from 'react-dom/client'
import { Activity, Clock3 } from 'lucide-react'
import './style.css'
import { AffectiveSurfaceProvider, SurfacePart } from './AffectiveSurfaceProvider'
import { buildAffectiveSurfaceCue } from './affectiveSurface'
import { AutonomyGatePanel, ImpulseObserverDialog, IntentDetailDialog, InteractionStream, IntentQueuePanel, MindStatePanel, StatusBadge, SystemControlPanel, ThemeSwitcher } from './DesktopPanels'
import type { ApiConfigProfilePatch, AppState, AsyncExplorationState, CommandState, DesktopEvent, ExternalPluginConfigPatch, ExternalPluginInstallRequest, GatewayStatus, JsonRecord, ProactiveAction, ProactiveIntent, QQActionState, QQEnvironmentStatus, QQRuntimeActionState, QQRuntimeConfig, QQRuntimeConfigPatch, ServiceProbe, Snapshot, StickerActionState, StickerLibrary, StickerRecord, Stage12GateStatus, Stage13GateStatus, ThemeName, XinYuState } from './desktopTypes'
import { actionLabel, apiConfigActionLabel, applyEvent, applyProactiveInbox, applySnapshot, asRecord, buildProactiveIntents, buildStats, chatErrorLabel, commandStatusLabel, compact, createCommandId, defaultQQRuntimeConfig, defaultQQServices, deriveXinYuState, digestPressureLabel, digestResidueLabel, digestResultLabel, digestThemeLabel, errorLabel, eventLabel, externalPluginActionLabel, formatLatency, formatTime, formatTurnMeta, initialTheme, isCommandRenderedByTurn, memorySummary, normalizeApiConfigStatus, normalizeAsyncExplorationState, normalizeExternalPluginsStatus, normalizeImpulseSoupState, normalizeMemoryGrowthCandidates, normalizeQQEnvironmentStatus, normalizeQQRuntimeConfig, normalizeStage8MemoryGovernance, normalizeStage12GateStatus, normalizeStage13GateStatus, normalizeStickerLibrary, platformLabel, qqActionResultLabel, qqDetailLabel, qqDiagnosisLabel, qqEnvironmentMessage, qqRuntimeResultLabel, qqServiceLabel, riskLabel, runtimeLabel, sourceLabel, statusLabel, stickerClipLabel, stickerCorrectionMoods, stickerMoodLabel, themeOptions, updateCommand } from './desktopModel'

const avatarSrc = './xinyu-avatar.png'

function App(): JSX.Element {
  const [input, setInput] = React.useState('')
  const [codexMode, setCodexMode] = React.useState(false)
  const [codexLocalWrite, setCodexLocalWrite] = React.useState(false)
  const [theme, setTheme] = React.useState<ThemeName>(() => initialTheme())
  const [selectedIntentId, setSelectedIntentId] = React.useState<string | null>(null)
  const [impulseObserverOpen, setImpulseObserverOpen] = React.useState(false)
  const [impulseLoading, setImpulseLoading] = React.useState(false)
  const [selfActionApprovalBusy, setSelfActionApprovalBusy] = React.useState('')
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
    loadAsyncExploration()
    loadStage12Gate()
    loadStage13Gate()
    loadImpulseSoup()
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
    const impulseTimer = window.setInterval(loadImpulseSoup, 5_000)
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
      window.clearInterval(impulseTimer)
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
      setState((current) => ({
        ...current,
        gateway: asRecord(gateway) as GatewayStatus,
        apiConfig: normalizeApiConfigStatus(result.status || {}),
        apiConfigAction: { kind: 'idle', message: apiConfigActionLabel(String(result.message || 'api_profile_applied'), true, result.error) }
      }))
    } catch (error) {
      setState((current) => ({
        ...current,
        apiConfigAction: { kind: 'idle', message: `应用失败：${compact(errorLabel(error), 72)}` }
      }))
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
      if (resultMessage === 'start_requested' && !status.allReady) {
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
      setState((current) => {
        const { [intent.id]: _removed, ...rest } = current.proactiveActions
        return { ...current, proactiveActions: rest }
      })
      return
    }
    setSelectedIntentId(null)
  }

  async function ackProactive(candidateId: string, action: ProactiveAction): Promise<void> {
    if (!candidateId || state.proactiveActions[candidateId]) {
      return
    }
    const intent = intents.find((item) => item.id === candidateId)
    if (action === 'approve_qq' && intent && !intent.claimable) {
      return
    }

    setState((current) => ({
      ...current,
      proactiveActions: { ...current.proactiveActions, [candidateId]: action }
    }))

    const result = asRecord(await window.xinyu.ackProactive({ candidateId, action }))
    if (result.accepted === false) {
      setState((current) => {
        const { [candidateId]: _removed, ...rest } = current.proactiveActions
        return { ...current, proactiveActions: rest }
      })
      return
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
        />

        <section className="presence-workspace">
          <MindStatePanel
            state={xinyuState}
            stats={stats}
            gateway={state.gateway}
            snapshot={state.snapshot}
            selfActionApprovalBusy={selfActionApprovalBusy}
            onDecideSelfActionApproval={decideSelfActionApproval}
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
            memoryGrowthCandidates={state.memoryGrowthCandidates}
            stage8MemoryGovernance={state.stage8MemoryGovernance}
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
          />
        </section>

        {selectedIntent ? (
          <IntentDetailDialog
            intent={selectedIntent}
            pendingAction={state.proactiveActions[selectedIntent.id]}
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
