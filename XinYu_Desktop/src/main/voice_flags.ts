import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'

// frontend flag key -> env var consumed by the core bridge
const FLAG_ENV: Record<string, string> = {
  unified_voice: 'XINYU_HUMAN_VOICE_UNIFIED_PROMPT',
  bypass_model: 'XINYU_HUMAN_VOICE_BYPASS_MODEL',
  regen_pipeline: 'XINYU_HUMAN_VOICE_REGEN_PIPELINE',
  group_social: 'XINYU_GROUP_SOCIAL_ENABLED',
  qq_voice_private: 'XINYU_QQ_VOICE_REPLY_PRIVATE',
  qq_voice_group: 'XINYU_QQ_VOICE_REPLY_GROUP'
}
const TRUE_VALUES = new Set(['1', 'true', 'yes', 'on'])

function envPath(coreDir: string): string {
  return join(coreDir, 'xinyu.local.env')
}

function readEnvFile(coreDir: string): Record<string, string> {
  const path = envPath(coreDir)
  const env: Record<string, string> = {}
  if (!existsSync(path)) {
    return env
  }
  for (const raw of readFileSync(path, 'utf-8').split(/\r?\n/)) {
    const match = raw.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/)
    if (match) {
      env[match[1]] = match[2].trim().replace(/^["']|["']$/g, '')
    }
  }
  return env
}

export function readVoiceFlags(coreDir: string): Record<string, boolean> {
  const env = readEnvFile(coreDir)
  const flags: Record<string, boolean> = {}
  for (const [key, name] of Object.entries(FLAG_ENV)) {
    const value = String(process.env[name] ?? env[name] ?? '')
      .trim()
      .toLowerCase()
    flags[key] = TRUE_VALUES.has(value)
  }
  return flags
}

// Authoritative write: persist to xinyu.local.env (upsert) so the toggle always
// succeeds and survives restarts, regardless of whether the live bridge already
// has the runtime endpoint. Only the listed keys are touched.
export function writeVoiceFlags(coreDir: string, partial: Record<string, boolean>): Record<string, boolean> {
  const path = envPath(coreDir)
  const changed = new Map<string, string>()
  for (const [key, value] of Object.entries(partial || {})) {
    const name = FLAG_ENV[key]
    if (!name) {
      continue
    }
    const next = value ? '1' : '0'
    changed.set(name, next)
    process.env[name] = next
  }
  if (changed.size === 0) {
    return readVoiceFlags(coreDir)
  }

  const lines = existsSync(path) ? readFileSync(path, 'utf-8').split(/\r?\n/) : []
  const remaining = new Map(changed)
  const out: string[] = []
  for (const raw of lines) {
    const match = raw.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=/)
    const key = match ? match[1] : ''
    if (key && remaining.has(key)) {
      out.push(`${key}=${remaining.get(key)}`)
      remaining.delete(key)
    } else {
      out.push(raw)
    }
  }
  for (const [key, value] of remaining) {
    out.push(`${key}=${value}`)
  }
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, `${out.join('\n').replace(/\n+$/, '')}\n`, 'utf-8')
  return readVoiceFlags(coreDir)
}
