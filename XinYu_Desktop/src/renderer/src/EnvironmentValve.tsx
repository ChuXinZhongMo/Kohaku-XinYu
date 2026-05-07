import React from 'react'
import './environment-valve.css'

type JsonRecord = Record<string, unknown>

type EnvironmentValveProps = {
  snapshot?: unknown
}

export function EnvironmentValve(props: EnvironmentValveProps): JSX.Element {
  const snapshot = asRecord(props.snapshot)
  const state = asRecord(snapshot.xinyuState)
  const entropy = asRecord(snapshot.entropyState)
  const selfChoice = asRecord(snapshot.selfChoiceState || snapshot.selfChoice)
  const affectBand = asRecord(selfChoice.affect_band)
  const activeDesires = asArray(snapshot.activeDesires).map(asRecord)
  const proactiveCount = asArray(snapshot.proactiveInbox).length
  const memoryEchoes = Number(state.recent_memory_echoes || asArray(snapshot.recentMemoryEvents).length || 0)
  const activeDesire = activeDesires[0] || {}
  const chosenAction = String(activeDesire.chosen_action || '').trim()

  const waiting = Boolean(state.is_waiting_for_reply)
  const metabolismStatus = String(state.metabolism_ticket_status || '').trim()
  const entropyLevel = clamp01(Number(entropy.entropy_level ?? entropy.entropyLevel ?? state.entropy_level ?? 0))
  const entropyBand = String(entropy.entropy_band || state.entropy_band || '').trim()
  const fatigueBand = String(affectBand.fatigue || '').trim()
  const fatigue = fatigueValue(fatigueBand)
  const moodScore = clamp01(Number(state.mood_score ?? state.energy ?? 0) / 100)
  const physicalPressure = String(state.physical_pressure || '').trim()
  const load = clamp(metabolismStatus ? 0.76 : moodScore || entropyLevel || (waiting ? 0.64 : 0.38), 0.08, 0.92)
  const clarity = clamp01(1 - Math.max(entropyLevel, fatigue * 0.82, waiting ? 0.26 : 0.12))
  const status = deriveStatus({
    waiting,
    metabolismStatus,
    entropyLevel,
    entropyBand,
    fatigue,
    fatigueBand,
    physicalPressure,
    chosenAction,
    proactiveCount,
    memoryEchoes
  })
  const style = {
    '--environment-load': load.toFixed(3)
  } as React.CSSProperties

  return (
    <section className="environment-valve" style={style} aria-label="环境状态">
      <div className="environment-valve__top">
        <span>环境状态</span>
        <strong>{status.title}</strong>
      </div>

      <div className="environment-valve__bar" aria-hidden="true">
        <span />
      </div>

      <div className="environment-valve__meta">
        <span>负载 {Math.round(load * 100)}</span>
        <span>清晰 {Math.round(clarity * 100)}</span>
        <span>{status.detail}</span>
      </div>

      <div className="environment-valve__reason">{status.reason}</div>
    </section>
  )
}

function deriveStatus(input: {
  waiting: boolean
  metabolismStatus: string
  entropyLevel: number
  entropyBand: string
  fatigue: number
  fatigueBand: string
  physicalPressure: string
  chosenAction: string
  proactiveCount: number
  memoryEchoes: number
}): { title: string; detail: string; reason: string } {
  if (input.metabolismStatus) {
    return {
      title: `代谢 ${input.metabolismStatus}`,
      detail: '代谢票据',
      reason: `原因：activeDesire 带有代谢票据，状态为 ${input.metabolismStatus}。`
    }
  }
  if (input.chosenAction === 'request_metabolism_window') {
    return {
      title: '请求代谢',
      detail: '生命内核',
      reason: '原因：activeDesires 判断当前需要代谢窗口。'
    }
  }
  if (input.waiting) {
    const suffix = input.proactiveCount ? `主动提醒 ${input.proactiveCount} 个` : '有未完成对话'
    return { title: '等待回应', detail: '未完成事项', reason: `原因：${suffix}。` }
  }
  if (input.entropyLevel >= 0.66 || ['fracture', 'terminal'].includes(input.entropyBand)) {
    return {
      title: '噪声偏高',
      detail: '熵值偏高',
      reason: `原因：entropyState=${input.entropyBand || 'high'}，熵值 ${Math.round(input.entropyLevel * 100)}。`
    }
  }
  if (input.fatigue >= 0.62) {
    return {
      title: '负载偏高',
      detail: '疲劳偏高',
      reason: `原因：SelfChoice fatigue=${input.fatigueBand || 'high'}。`
    }
  }
  if (input.physicalPressure === 'high') {
    return {
      title: '压力偏高',
      detail: '体感压力',
      reason: '原因：xinyuState.physical_pressure=high。'
    }
  }
  if (input.memoryEchoes > 0) {
    return {
      title: '稳定',
      detail: '记忆回声',
      reason: `原因：最近有 ${input.memoryEchoes} 次记忆回声，但未触发高负载。`
    }
  }
  return { title: '稳定', detail: '只读状态', reason: '原因：没有待处理意图、代谢票据或高负载信号。' }
}

function fatigueValue(value: string): number {
  if (value === 'exhausted' || value === 'heavy') {
    return 0.82
  }
  if (value === 'tired') {
    return 0.66
  }
  if (value === 'clear') {
    return 0.18
  }
  return 0
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function asRecord(value: unknown): JsonRecord {
  return value && typeof value === 'object' ? (value as JsonRecord) : {}
}

function clamp01(value: number): number {
  return clamp(value, 0, 1)
}

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min
  }
  return Math.min(max, Math.max(min, value))
}
