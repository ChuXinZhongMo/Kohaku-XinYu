import React from 'react'
import ReactDOM from 'react-dom/client'
import { Activity, Clock3 } from 'lucide-react'
import './style.css'
import { AffectiveSurfaceProvider, SurfacePart } from './AffectiveSurfaceProvider'
import { buildAffectiveSurfaceCue } from './affectiveSurface'
import { ImpulseObserverDialog, IntentDetailDialog, InteractionStream, IntentQueuePanel, MindStatePanel, StatusBadge, ThemeSwitcher } from './DesktopPanels'
import type { AppState, CommandState, DesktopEvent, GatewayStatus, JsonRecord, ProactiveAction, ProactiveIntent, QQActionState, QQEnvironmentStatus, QQRuntimeActionState, QQRuntimeConfig, QQRuntimeConfigPatch, ServiceProbe, Snapshot, StickerActionState, StickerLibrary, StickerRecord, ThemeName, XinYuState } from './desktopTypes'
import { actionLabel, applyEvent, applyProactiveInbox, applySnapshot, asRecord, buildProactiveIntents, buildStats, commandStatusLabel, compact, createCommandId, defaultQQRuntimeConfig, defaultQQServices, deriveXinYuState, digestPressureLabel, digestResidueLabel, digestResultLabel, digestThemeLabel, errorLabel, eventLabel, formatLatency, formatTime, formatTurnMeta, initialTheme, isCommandRenderedByTurn, memorySummary, normalizeImpulseSoupState, normalizeQQEnvironmentStatus, normalizeQQRuntimeConfig, normalizeStickerLibrary, platformLabel, qqActionResultLabel, qqDetailLabel, qqDiagnosisLabel, qqEnvironmentMessage, qqRuntimeResultLabel, qqServiceLabel, riskLabel, runtimeLabel, sourceLabel, statusLabel, stickerClipLabel, stickerCorrectionMoods, stickerMoodLabel, themeOptions, updateCommand } from './desktopModel'

const avatarSrc = './xinyu-avatar.png'

function App(): JSX.Element {
  const [input, setInput] = React.useState('')
  const [codexMode, setCodexMode] = React.useState(false)
  const [codexLocalWrite, setCodexLocalWrite] = React.useState(false)
  const [theme, setTheme] = React.useState<ThemeName>(() => initialTheme())
  const [selectedIntentId, setSelectedIntentId] = React.useState<string | null>(null)
  const [impulseObserverOpen, setImpulseObserverOpen] = React.useState(false)
  const [impulseLoading, setImpulseLoading] = React.useState(false)
  const [state, setState] = React.useState<AppState>({
    snapshot: null,
    gateway: null,
    events: [],
    commands: [],
    proactiveActions: {},
    proactiveInbox: [],
    impulseSoup: null,
    recentTurns: [],
    recentMemoryEvents: [],
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
    loadStickerLibrary()
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
    const stickerTimer = window.setInterval(loadStickerLibrary, 30_000)
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
      window.clearInterval(stickerTimer)
      window.clearInterval(impulseTimer)
      offEvent()
      offStatus()
    }
  }, [])

  const xinyuState = React.useMemo(() => deriveXinYuState(state), [state])
  const intents = React.useMemo(() => buildProactiveIntents(state.proactiveInbox), [state.proactiveInbox])
  const selectedIntent = React.useMemo(
    () => intents.find((intent) => intent.id === selectedIntentId) || null,
    [intents, selectedIntentId]
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

  async function startQQEnvironmentFromPanel(): Promise<void> {
    setState((current) => ({
      ...current,
      qqAction: { kind: 'starting', message: '正在启动 QQ 环境' }
    }))

    try {
      const result = asRecord(await window.xinyu.startQQEnvironment())
      const status = normalizeQQEnvironmentStatus(result.status || (await window.xinyu.getQQEnvironmentStatus()))
      setState((current) => ({
        ...current,
        qqEnvironment: status,
        qqAction: {
          kind: 'idle',
          message: qqActionResultLabel(String(result.message || ''), result.accepted !== false, result.error)
        }
      }))
      window.setTimeout(() => {
        void window.xinyu
          .getQQEnvironmentStatus()
          .then((value) => {
            setState((current) => ({ ...current, qqEnvironment: normalizeQQEnvironmentStatus(value) }))
          })
          .catch(() => undefined)
      }, 6000)
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
      qqAction: { kind: 'opening', message: '正在打开 NapCat WebUI' }
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
      qqAction: { kind: 'copying', message: '正在复制 WebUI token' }
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
      textPreview: compact(`${routeCodex ? 'Codex: ' : ''}${text}`, 180),
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
      setState((current) => updateCommand(current, commandId, 'failed', String(result.error || 'chat_request_failed')))
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
            item.commandId === commandId ? { ...item, status: 'failed', message: String(result.error || 'chat_request_failed') } : item
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

        <section className="presence-workspace">
          <MindStatePanel state={xinyuState} stats={stats} gateway={state.gateway} snapshot={state.snapshot} />

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
            pending={state.proactiveActions}
            actionDigest={state.snapshot?.actionDigestState}
            recentMemoryEvents={state.recentMemoryEvents}
            lastEvent={state.events[0]}
            qqEnvironment={state.qqEnvironment}
            qqAction={state.qqAction}
            qqRuntimeConfig={state.qqRuntimeConfig}
            qqRuntimeAction={state.qqRuntimeAction}
            stickerLibrary={state.stickerLibrary}
            stickerAction={state.stickerAction}
            onAck={ackProactive}
            onOpenDetail={setSelectedIntentId}
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
