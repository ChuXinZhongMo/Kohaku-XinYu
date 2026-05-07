export type SurfacePartName = 'root' | 'portrait' | 'noise' | 'valve' | 'valveThumb' | 'ambientLight'

export type SurfaceCueKind =
  | 'quiet'
  | 'connect'
  | 'disconnect'
  | 'replying'
  | 'message'
  | 'memory'
  | 'proactive'
  | 'metabolism'
  | 'boundary'
  | 'error'

export type AffectiveSurfaceCue = {
  key: string
  kind: SurfaceCueKind
  intensity: number
}

export type AffectiveSurfaceState = {
  connection: 'online' | 'connecting' | 'offline'
  waitingReply: boolean
  moodScore: number
  proactiveCount: number
  activeCommandId?: string
  activeCommandStatus?: string
  lastEventId?: string
  lastEventType?: string
  lastEventTs?: string
}

export type AffectiveSurfaceRegistry = {
  get(part: SurfacePartName): Element | null
}

const activeAnimations = new WeakMap<Element, Animation[]>()

export function buildAffectiveSurfaceCue(state: AffectiveSurfaceState): AffectiveSurfaceCue {
  const eventKey = state.lastEventId || state.lastEventTs
  if (eventKey && state.lastEventType) {
    return {
      key: `event:${state.lastEventType}:${eventKey}`,
      kind: cueKindForEvent(state.lastEventType),
      intensity: intensityForEvent(state.lastEventType, state.moodScore)
    }
  }

  if (state.activeCommandId && state.activeCommandStatus) {
    return {
      key: `command:${state.activeCommandId}:${state.activeCommandStatus}`,
      kind: state.activeCommandStatus === 'finished' ? 'message' : 'replying',
      intensity: 0.62
    }
  }

  if (state.proactiveCount > 0) {
    return {
      key: `proactive:${state.proactiveCount}`,
      kind: 'proactive',
      intensity: 0.72
    }
  }

  if (state.connection === 'offline') {
    return { key: 'connection:offline', kind: 'disconnect', intensity: 0.44 }
  }

  if (state.connection === 'connecting') {
    return { key: 'connection:connecting', kind: 'connect', intensity: 0.36 }
  }

  return {
    key: `quiet:${state.waitingReply ? 'waiting' : 'settled'}:${Math.round(state.moodScore / 20)}`,
    kind: 'quiet',
    intensity: clamp01(state.moodScore / 120)
  }
}

export function triggerSurfaceImpulse(registry: AffectiveSurfaceRegistry, cue: AffectiveSurfaceCue): void {
  const root = registry.get('root') as HTMLElement | null
  const portrait = registry.get('portrait')
  const noise = registry.get('noise') as HTMLElement | null
  const valve = registry.get('valve')
  const valveThumb = registry.get('valveThumb')
  const ambientLight = registry.get('ambientLight') as HTMLElement | null
  const intensity = clamp01(cue.intensity)

  applySurfaceVariables(root, cue, intensity)
  if (prefersReducedMotion()) {
    return
  }

  if (cue.kind === 'disconnect') {
    playImpulse(root, [{ filter: 'saturate(1)' }, { filter: 'saturate(0.76)' }, { filter: 'saturate(0.9)' }], {
      duration: 460,
      easing: 'ease-out'
    })
    playImpulse(noise, [{ opacity: 0.05 }, { opacity: 0.24 }, { opacity: 0.12 }], pulseOptions(620))
    playImpulse(portrait, [{ filter: 'saturate(1)' }, { filter: 'saturate(0.7)' }, { filter: 'saturate(0.9)' }], {
      duration: 520,
      easing: 'ease-out'
    })
    return
  }

  if (cue.kind === 'metabolism' || cue.kind === 'boundary') {
    playImpulse(valve, valvePulseFrames(intensity), pulseOptions(520))
    playImpulse(valveThumb, valveThumbFrames(intensity), pulseOptions(520))
    playImpulse(ambientLight, ambientFrames(intensity, cue.kind), pulseOptions(680))
    return
  }

  if (cue.kind === 'replying') {
    playImpulse(root, liftFrames(3), pulseOptions(420))
    playImpulse(portrait, portraitFrames(0.6), pulseOptions(560))
    playImpulse(noise, noiseFrames(0.16 + intensity * 0.16), pulseOptions(700))
    return
  }

  if (cue.kind === 'message' || cue.kind === 'memory') {
    playImpulse(portrait, portraitFrames(0.38), pulseOptions(540))
    playImpulse(noise, noiseFrames(0.12 + intensity * 0.14), pulseOptions(820))
    playImpulse(ambientLight, ambientFrames(intensity, cue.kind), pulseOptions(720))
    return
  }

  if (cue.kind === 'proactive') {
    playImpulse(root, liftFrames(2), pulseOptions(520))
    playImpulse(portrait, portraitFrames(0.78), pulseOptions(640))
    playImpulse(ambientLight, ambientFrames(intensity, cue.kind), pulseOptions(760))
    return
  }

  if (cue.kind === 'connect') {
    playImpulse(ambientLight, ambientFrames(0.44, cue.kind), pulseOptions(620))
    playImpulse(noise, noiseFrames(0.1), pulseOptions(640))
  }
}

export function playImpulse(
  element: Element | null | undefined,
  keyframes: Keyframe[] | PropertyIndexedKeyframes,
  options: KeyframeAnimationOptions
): void {
  if (!element || typeof element.animate !== 'function') {
    return
  }

  for (const animation of activeAnimations.get(element) ?? []) {
    animation.cancel()
  }

  const next = element.animate(keyframes, options)
  activeAnimations.set(element, [next])
  const clear = (): void => {
    const remaining = (activeAnimations.get(element) ?? []).filter((animation) => animation !== next)
    if (remaining.length) {
      activeAnimations.set(element, remaining)
    } else {
      activeAnimations.delete(element)
    }
  }
  next.addEventListener('finish', clear, { once: true })
  next.addEventListener('cancel', clear, { once: true })
}

function applySurfaceVariables(root: HTMLElement | null, cue: AffectiveSurfaceCue, intensity: number): void {
  if (!root) {
    return
  }

  const warmth = cue.kind === 'boundary' || cue.kind === 'disconnect' ? 0.18 : cue.kind === 'metabolism' ? 0.86 : intensity
  const noise = cue.kind === 'quiet' ? 0.04 + intensity * 0.05 : 0.08 + intensity * 0.18
  root.style.setProperty('--affective-intensity', intensity.toFixed(3))
  root.style.setProperty('--affective-warmth', warmth.toFixed(3))
  root.style.setProperty('--affective-noise-opacity', noise.toFixed(3))
  root.style.setProperty('--affective-noise-image', 'url("./xinyu-noise.svg")')
}

function cueKindForEvent(type: string): SurfaceCueKind {
  if (type.includes('metabolism') || type.includes('yield')) {
    return type.includes('maintain') || type.includes('boundary') || type.includes('reject') ? 'boundary' : 'metabolism'
  }
  if (type === 'chat.turn.started') {
    return 'replying'
  }
  if (type === 'chat.turn.finished') {
    return 'message'
  }
  if (type.includes('memory')) {
    return 'memory'
  }
  if (type.includes('proactive')) {
    return 'proactive'
  }
  if (type.includes('failed') || type.includes('unavailable') || type.includes('error')) {
    return 'error'
  }
  return 'quiet'
}

function intensityForEvent(type: string, moodScore: number): number {
  const base = clamp01(moodScore / 100)
  if (type.includes('metabolism')) {
    return Math.max(0.72, base)
  }
  if (type.includes('proactive')) {
    return Math.max(0.62, base)
  }
  if (type === 'chat.turn.started') {
    return 0.62
  }
  if (type === 'chat.turn.finished') {
    return 0.5
  }
  if (type.includes('memory')) {
    return 0.44
  }
  return Math.max(0.32, base * 0.72)
}

function liftFrames(px: number): Keyframe[] {
  return [
    { transform: 'translateY(0)' },
    { transform: `translateY(-${px}px)`, offset: 0.45 },
    { transform: 'translateY(0)' }
  ]
}

function portraitFrames(intensity: number): Keyframe[] {
  const lift = (2 + intensity * 3).toFixed(2)
  return [
    { transform: 'translateY(0) scale(1)', filter: 'saturate(1) brightness(1)' },
    {
      transform: `translateY(-${lift}px) scale(${(1 + intensity * 0.018).toFixed(3)})`,
      filter: `saturate(${(1.04 + intensity * 0.18).toFixed(3)}) brightness(${(1.01 + intensity * 0.04).toFixed(3)})`,
      offset: 0.46
    },
    { transform: 'translateY(0) scale(1)', filter: 'saturate(1) brightness(1)' }
  ]
}

function noiseFrames(opacity: number): Keyframe[] {
  return [
    { opacity: 'var(--affective-noise-opacity)', transform: 'translate3d(0, 0, 0)' },
    { opacity: opacity.toFixed(3), transform: 'translate3d(12px, -8px, 0)', offset: 0.5 },
    { opacity: 'var(--affective-noise-opacity)', transform: 'translate3d(0, 0, 0)' }
  ]
}

function ambientFrames(intensity: number, kind: SurfaceCueKind): Keyframe[] {
  const scale = kind === 'boundary' ? 0.96 : 1.04 + intensity * 0.08
  const opacity = kind === 'disconnect' ? 0.1 : 0.26 + intensity * 0.28
  return [
    { opacity: 'var(--affective-ambient-opacity)', transform: 'scale(1)' },
    { opacity: opacity.toFixed(3), transform: `scale(${scale.toFixed(3)})`, offset: 0.48 },
    { opacity: 'var(--affective-ambient-opacity)', transform: 'scale(1)' }
  ]
}

function valvePulseFrames(intensity: number): Keyframe[] {
  return [
    { filter: 'saturate(1) brightness(1)' },
    { filter: `saturate(${(1.08 + intensity * 0.24).toFixed(3)}) brightness(1.035)`, offset: 0.42 },
    { filter: 'saturate(1) brightness(1)' }
  ]
}

function valveThumbFrames(intensity: number): Keyframe[] {
  const glow = 10 + intensity * 18
  return [
    { filter: 'brightness(1)', boxShadow: '0 12px 22px var(--app-shadow, rgba(94, 68, 105, 0.17))' },
    {
      filter: 'brightness(1.06)',
      boxShadow: `0 0 ${glow.toFixed(1)}px color-mix(in srgb, var(--app-warm, #d79abd) 34%, transparent)`,
      offset: 0.46
    },
    { filter: 'brightness(1)', boxShadow: '0 12px 22px var(--app-shadow, rgba(94, 68, 105, 0.17))' }
  ]
}

function pulseOptions(duration: number): KeyframeAnimationOptions {
  return { duration, easing: 'cubic-bezier(0.2, 0.72, 0.2, 1)' }
}

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0))
}
