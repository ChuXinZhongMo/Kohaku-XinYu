import React from 'react'
import {
  type AffectiveSurfaceCue,
  type AffectiveSurfaceRegistry,
  type SurfacePartName,
  triggerSurfaceImpulse
} from './affectiveSurface'
import './affective-surface.css'

type RegistryContextValue = {
  register(part: SurfacePartName, node: Element | null): void
}

type SurfacePartProps = React.HTMLAttributes<HTMLElement> & {
  name: SurfacePartName
  as?: 'div' | 'main' | 'section' | 'span'
}

const RegistryContext = React.createContext<RegistryContextValue | null>(null)

export function AffectiveSurfaceProvider(props: {
  cue: AffectiveSurfaceCue
  children: React.ReactNode
}): JSX.Element {
  const partsRef = React.useRef(new Map<SurfacePartName, Element>())
  const lastCueKeyRef = React.useRef('')

  const registry = React.useMemo<AffectiveSurfaceRegistry>(
    () => ({
      get(part) {
        return partsRef.current.get(part) || null
      }
    }),
    []
  )

  const value = React.useMemo<RegistryContextValue>(
    () => ({
      register(part, node) {
        if (node) {
          partsRef.current.set(part, node)
        } else {
          partsRef.current.delete(part)
        }
      }
    }),
    []
  )

  React.useEffect(() => {
    if (lastCueKeyRef.current === props.cue.key) {
      return
    }
    lastCueKeyRef.current = props.cue.key
    triggerSurfaceImpulse(registry, props.cue)
  }, [props.cue, registry])

  return <RegistryContext.Provider value={value}>{props.children}</RegistryContext.Provider>
}

export function useAffectiveSurfaceRegistry(): RegistryContextValue['register'] {
  const context = React.useContext(RegistryContext)
  if (!context) {
    return () => undefined
  }
  return context.register
}

export function useSurfacePartRef(part: SurfacePartName): React.RefCallback<HTMLElement> {
  const register = useAffectiveSurfaceRegistry()
  return React.useCallback(
    (node: HTMLElement | null) => {
      register(part, node)
    },
    [part, register]
  )
}

export function SurfacePart({ name, as = 'div', ...props }: SurfacePartProps): JSX.Element {
  const ref = useSurfacePartRef(name)
  return React.createElement(as, { ...props, ref })
}
