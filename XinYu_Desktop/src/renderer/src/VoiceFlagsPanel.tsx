import React from 'react'

type FlagKey =
  | 'unified_voice'
  | 'bypass_model'
  | 'regen_pipeline'
  | 'group_social'
  | 'qq_voice_private'
  | 'qq_voice_group'

type FlagsState = Record<FlagKey, boolean>

const FLAG_SPECS: { key: FlagKey; title: string; desc: string }[] = [
  {
    key: 'unified_voice',
    title: '统一声音',
    desc: '主路 / 渲染器 / 慢推理共用同一份人格之声，厚思考薄表达，不复盘不念状态。风险最低，建议先开。'
  },
  {
    key: 'bypass_model',
    title: '旁路改模型生成',
    desc: '私聊快速旁路不再吐写死固定串，先走模型生成，失败才退回固定串。影响最直接。'
  },
  {
    key: 'regen_pipeline',
    title: '后处理重写',
    desc: '后处理里把模型原话换成固定串的步骤改为清空→模型重生成，固定串只作最后保险。'
  },
  {
    key: 'group_social',
    title: '群聊社会记忆',
    desc: '记住群里共同经历、每个群友在本群的身份和称呼；B/C 提到 A 时知道 A 是谁，按群内真实叫法称呼，不串群、不输出 QQ 号。'
  },
  {
    key: 'qq_voice_private',
    title: '私聊发语音条',
    desc: '私聊时把回复用训练好的声线说成 QQ 语音条。合成失败自动退回文字。每条要等几秒生成。'
  },
  {
    key: 'qq_voice_group',
    title: '群聊发语音条',
    desc: '群聊时也用语音条回复。注意：群里发语音可能显得吵，且每条都要等几秒生成。'
  }
]

const EMPTY_FLAGS: FlagsState = {
  unified_voice: false,
  bypass_model: false,
  regen_pipeline: false,
  group_social: false,
  qq_voice_private: false,
  qq_voice_group: false
}

function asFlags(value: unknown): FlagsState {
  const record = value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
  const flags = record.flags && typeof record.flags === 'object' ? (record.flags as Record<string, unknown>) : record
  return {
    unified_voice: Boolean(flags.unified_voice),
    bypass_model: Boolean(flags.bypass_model),
    regen_pipeline: Boolean(flags.regen_pipeline),
    group_social: Boolean(flags.group_social),
    qq_voice_private: Boolean(flags.qq_voice_private),
    qq_voice_group: Boolean(flags.qq_voice_group)
  }
}

function Toggle({ on, onClick }: { on: boolean; onClick: () => void }): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      style={{
        width: 42,
        height: 24,
        flex: '0 0 auto',
        borderRadius: 24,
        border: 'none',
        cursor: 'pointer',
        padding: 3,
        display: 'flex',
        justifyContent: on ? 'flex-end' : 'flex-start',
        background: on ? '#4f8cff' : 'rgba(39, 87, 82, 0.22)',
        transition: 'background 160ms ease'
      }}
    >
      <span
        style={{
          width: 18,
          height: 18,
          borderRadius: '50%',
          background: '#fff',
          boxShadow: '0 1px 3px rgba(0,0,0,0.25)'
        }}
      />
    </button>
  )
}

export function VoiceFlagsPanel(): JSX.Element {
  const [flags, setFlags] = React.useState<FlagsState>(EMPTY_FLAGS)
  const [persist, setPersist] = React.useState(true)
  const [status, setStatus] = React.useState('')
  const [busy, setBusy] = React.useState<FlagKey | null>(null)
  const [bulkBusy, setBulkBusy] = React.useState(false)

  React.useEffect(() => {
    let active = true
    window.xinyu
      .getVoiceFlags()
      .then((value) => {
        if (active) setFlags(asFlags(value))
      })
      .catch(() => undefined)
    return () => {
      active = false
    }
  }, [])

  const refreshFromBackend = async (): Promise<void> => {
    try {
      setFlags(asFlags(await window.xinyu.getVoiceFlags()))
    } catch {
      /* leave current optimistic state if even reading fails */
    }
  }

  // One honest path for both single toggles and the bulk buttons: optimistic
  // update, send, then trust the authoritative state the backend returns. On any
  // failure, re-sync from the backend and show a clear error — no misleading
  // "looks like it worked" divergence between single and bulk.
  const persistFlags = async (partial: Partial<FlagsState>, label: string): Promise<void> => {
    setFlags((prev) => ({ ...prev, ...partial }))
    try {
      const result = await window.xinyu.setVoiceFlags({ flags: partial, persist })
      const record = result && typeof result === 'object' ? (result as Record<string, unknown>) : {}
      if (record.ok === false) {
        await refreshFromBackend()
        setStatus(`保存失败：${String(record.error || 'unknown')}（核心桥在跑新代码吗？）`)
        return
      }
      setFlags(asFlags(result))
      const tail =
        record.live === false
          ? '（已写入配置，重启核心桥后生效）'
          : record.persisted
            ? '（已写入配置，已生效）'
            : '（仅本次运行）'
      setStatus(`${label}${tail}`)
    } catch (error) {
      await refreshFromBackend()
      setStatus(`保存失败：${error instanceof Error ? error.message : String(error)}（核心桥在跑新代码吗？）`)
    }
  }

  const toggle = async (key: FlagKey): Promise<void> => {
    if (busy) return
    const next = !flags[key]
    setBusy(key)
    try {
      await persistFlags({ [key]: next }, next ? '已开启' : '已关闭')
    } finally {
      setBusy(null)
    }
  }

  const setAll = async (value: boolean): Promise<void> => {
    setBulkBusy(true)
    try {
      await persistFlags(
        { unified_voice: value, bypass_model: value, regen_pipeline: value, group_social: value },
        value ? '已全部开启' : '已全部关闭'
      )
    } finally {
      setBulkBusy(false)
    }
  }

  const bulkButtonStyle: React.CSSProperties = {
    border: '1px solid rgba(39, 87, 82, 0.2)',
    borderRadius: 7,
    background: 'rgba(255, 255, 255, 0.6)',
    padding: '4px 10px',
    fontSize: 12,
    cursor: bulkBusy ? 'default' : 'pointer',
    opacity: bulkBusy ? 0.5 : 1
  }

  return (
    <section className="system-card voice-flags-panel" style={{ display: 'grid', gap: 10 }}>
      <header style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ minWidth: 0 }}>
          <p className="label">对话行为控制</p>
          <h3 style={{ margin: '2px 0 0' }}>像不像人 · 群里认不认人</h3>
        </div>
        <div style={{ display: 'flex', gap: 6, flex: '0 0 auto' }}>
          <button type="button" style={bulkButtonStyle} disabled={bulkBusy} onClick={() => void setAll(true)}>
            全开
          </button>
          <button type="button" style={bulkButtonStyle} disabled={bulkBusy} onClick={() => void setAll(false)}>
            全关
          </button>
        </div>
      </header>
      {FLAG_SPECS.map((spec) => (
        <div key={spec.key} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <Toggle on={flags[spec.key]} onClick={() => void toggle(spec.key)} />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 13, opacity: busy === spec.key ? 0.6 : 1 }}>{spec.title}</div>
            <div style={{ fontSize: 12, lineHeight: 1.55, opacity: 0.7 }}>{spec.desc}</div>
          </div>
        </div>
      ))}
      <label style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, opacity: 0.78 }}>
        <input type="checkbox" checked={persist} onChange={(event) => setPersist(event.target.checked)} />
        写入本地配置（重启后保留）
      </label>
      {status ? (
        <div style={{ fontSize: 12, opacity: 0.7 }}>{status}</div>
      ) : null}
    </section>
  )
}
