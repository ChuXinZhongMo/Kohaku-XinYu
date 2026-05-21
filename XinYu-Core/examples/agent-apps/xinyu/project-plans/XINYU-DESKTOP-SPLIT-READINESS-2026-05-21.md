# XinYu Desktop Split Readiness

Date: 2026-05-21

Purpose: document safe split boundaries for the Desktop renderer and CSS after backend closeout stayed green. This note is readiness evidence only; it does not redesign the UI.

## Validation

- Backend full pytest: `786 passed`.
- Runtime readiness smoke: `ok`.
- Desktop typecheck: `npm run typecheck` passed.
- Desktop build: `npm run build` passed.
- Desktop build output remains untracked by Git.

## Current Desktop Surface

Main files:

- `XinYu_Desktop/src/renderer/src/DesktopPanels.tsx` - about 102 KB; primary component backlog.
- `XinYu_Desktop/src/renderer/src/main.tsx` - about 41 KB; app orchestration, state loading, and event wiring.
- `XinYu_Desktop/src/renderer/src/desktopModel.ts` - about 42 KB; model normalization and label formatting.
- `XinYu_Desktop/src/renderer/src/style.css` - about 48 KB; main renderer layout and shared component styling.

Already split CSS:

- `styles/shell.css`
- `styles/qq-panels.css`
- `styles/sticker-panel.css`
- `affective-surface.css`
- `environment-valve.css`

## Safe Split Order

1. `DesktopPanels.tsx`
   - Extract read-only display panels first.
   - Keep action dispatch callbacks in the parent until component props are pinned.
   - Candidate files:
     - `components/MindStatePanel.tsx`
     - `components/InteractionStream.tsx`
     - `components/IntentQueuePanel.tsx`
     - `components/SystemControlPanel.tsx`

2. `style.css`
   - Move styles by already visible surface boundaries.
   - Preserve import order from broad shell styles to narrower component styles.
   - Candidate files:
     - `styles/presence-workspace.css`
     - `styles/mind-panel.css`
     - `styles/interaction-panel.css`
     - `styles/system-panel.css`

3. `main.tsx`
   - Extract data loading hooks only after panel props are stable.
   - Candidate files:
     - `hooks/useQQEnvironment.ts`
     - `hooks/useDesktopSnapshot.ts`
     - `hooks/useProactiveInbox.ts`

4. `desktopModel.ts`
   - Extract only pure label/format helpers with direct tests.
   - Do not split normalization paths until tests cover each payload shape.

## Guardrails

- Do not change visual design during split-only work.
- Do not add new app state while moving components.
- Keep `npm run typecheck` and `npm run build` green after every slice.
- If a split touches backend-facing API types, run backend full pytest afterward.

## Next Desktop Action

When Desktop splitting begins, start with one read-only component extraction from `DesktopPanels.tsx`, run `npm run typecheck`, run `npm run build`, and commit the slice separately.
