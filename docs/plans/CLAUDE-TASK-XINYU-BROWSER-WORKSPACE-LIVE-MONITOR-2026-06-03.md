# Claude Task: XinYu Browser Workspace Live Monitor

date: 2026-06-03
from: Codex / architecture director
to: Claude / executor
repo: D:\XinYu
app root: D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
desktop root: D:\XinYu\XinYu_Desktop
venv python: `.\.venv\Scripts\python.exe`

## Objective

Build a real-time visual monitor for XinYu's own private browser workspace.

This is not a log panel. It should feel like watching a small remote desktop:
the owner can see XinYu's private browser frame, synthetic cursor/target
movement, click/type/scroll markers, and gate status in near real time.

Important boundary: this monitor shows XinYu's isolated Playwright browser
workspace. It must not capture or control the owner's Windows desktop, and it
must not move the owner's physical mouse.

The browser can be controlled without stealing the owner's mouse because
Playwright sends protocol-level commands to an isolated browser context. Desktop
only watches sanitized frames and action state.

## Current Context

- Private Ecosystem is implemented and wired.
- P0/P1 review fixes are complete:
  - autonomous browser observe routes through `external_plugin_call`;
  - grant route is hardened;
  - Desktop browser action uses the same external-plugin/native chain;
  - Edge fallback exists, but bundled Playwright Chromium should now be usable.
- `chromium-headless-shell` for Playwright build 1148 is installed locally.
- `xinyu.local.env` has `# XINYU_PRIVATE_BROWSER_CHANNEL=msedge`, so the
  engine should use bundled Chromium by default.
- Do not change live grants during this task.

## Hard Red Lines

- Do not change grants.
- Do not enable `computer_control`.
- Do not fill `private_browser.allowed_urls`.
- Do not add autonomous browser actions beyond the existing approved chain.
- Do not bypass `external_plugin_call`.
- Do not weaken bridge auth, owner-private checks, self-action approval,
  QQ claim/ack, external plugin runtime gate, or stable memory review.
- Do not capture the owner's Windows desktop.
- Do not use the owner's browser profile.
- Do not move the owner's OS mouse or keyboard focus.
- Do not return raw owner text, QQ payload body, cookies, tokens, credentials,
  form values, complete DOM, local secret paths, or full local absolute paths.
- Do not add arbitrary JS execution or stealth/anti-bot injection.
- Do not copy third-party code.
- Do not change pinned dependency versions.
- Do not modify tests or gates just to make a report green.

## Product Shape

The Desktop should gain a panel that looks like a private browser monitor:

```text
┌──────────────────────────────────────────────────────────────────────┐
│ XinYu Browser Workspace                                              │
│ Chromium headless · live · example.com · click_element               │
│ gate: approval_required · result: blocked                            │
├───────────────────────────────────────────────────────┬──────────────┤
│                                                       │ Live State   │
│  [latest private browser screenshot, refreshed 2-5fps] │ action       │
│                                                       │ result       │
│                ◎ synthetic cursor / target            │ gate reason  │
│                                                       │              │
│       red dashed marker = blocked target/action        │ Gates        │
│       blue ring = click/target                         │ browser on   │
│       arrow = scroll                                   │ plugin on    │
│                                                       │ computer off │
├───────────────────────────────────────────────────────┴──────────────┤
│ screenshot ref · frame age · private workspace only                   │
└──────────────────────────────────────────────────────────────────────┘
```

Expected behavior:

- The owner sees the latest private browser image refresh at low FPS.
- Cursor movement is visualized by a synthetic overlay from XinYu's action
  record or live-state cursor, not from Windows mouse capture.
- Clicks show a short ring pulse.
- Scrolls show an arrow/track marker.
- Fill/type shows target position and `has_input=true`, but never the text.
- Blocked actions show a red dashed marker and gate reason.
- If no browser session/frame exists, show idle/unavailable state.

## Architecture Decision

Implement a Browser Workspace Monitor, not full OS desktop control.

Do not build a Windows desktop remote-control layer in this task. Full isolated
desktop can be a later project using VM/RDP/VNC/WebRTC, but it must not be mixed
into this browser monitor work.

The first production-grade version should use:

- Persistent private Playwright browser session, if safe to introduce.
- Screenshot polling or frame artifact serving for the monitor.
- External-plugin policy chain for any browser action.
- Sanitized live-state snapshot for UI overlay and gate status.

If a persistent session is too risky to land safely in one increment, implement
the monitor over the latest screenshot artifacts first, but still design the API
so it can be upgraded to a live session without changing the Desktop contract.

## Backend Implementation

### 1. Browser Session Manager

Add a small session manager instead of scattering long-lived Playwright state
through routes.

Suggested file:

- `xinyu_private_browser_session.py`

Responsibilities:

- Own one isolated Playwright private browser session.
- Use `runtime/private_ecosystem/browser_profile`.
- Use bundled Chromium by default; Edge only if `_effective_channel` says it is
  needed.
- Keep `chromium_sandbox=True`.
- No open CDP port.
- No `remote-allow-origins=*`.
- No `--disable-web-security`.
- No arbitrary JS.
- No stealth scripts.
- Thread-safe enough for bridge worker-thread calls.
- Expose a small typed API:

```python
class PrivateBrowserSessionManager:
    def ensure_open(self, root: Path) -> BrowserEngine: ...
    def current_frame(self, root: Path) -> BrowserLiveFrame: ...
    def current_state(self, root: Path) -> BrowserLiveState: ...
    def close_idle(self, root: Path, *, idle_seconds: int = 900) -> None: ...
    def close(self) -> None: ...
```

Do not start this session just to render Desktop. `live-frame` may return idle
if there is no session. Browser actions may start it only after all existing
plugin/grant/policy gates pass.

If the existing `run_browser_action(..., engine=...)` expects a ready engine,
wire the session manager into the native executor path only after
`run_private_ecosystem_native_call` has allowed the action.

### 2. Live Frame Store

Add a frame store that makes the latest frame available to Desktop without
returning unsafe files.

Suggested file:

- `xinyu_private_browser_live.py`

Runtime paths:

- `runtime/private_ecosystem/browser_live/latest.png`
- `runtime/private_ecosystem/browser_live/state.json`
- `runtime/private_ecosystem/browser_live/frames.jsonl` optional, capped/TTL

Frame record fields:

```json
{
  "frame_id": "bfrm-...",
  "captured_at": "...",
  "source": "private_browser",
  "engine": "live|simulated|unavailable",
  "browser": "chromium|edge|unknown",
  "url_redacted": "https://example.com/path",
  "url_host": "example.com",
  "screenshot_ref": "runtime/private_ecosystem/browser_live/latest.png",
  "width": 1280,
  "height": 720,
  "last_action_id": "bact-...",
  "marker": {
    "type": "pointer|click|target|scroll|text|none",
    "x": 0,
    "y": 0,
    "coordinate_plane": "viewport_0_1000",
    "blocked": false
  }
}
```

Sanitization:

- Store only relative refs under `runtime/private_ecosystem`.
- Strip URL query and fragment.
- Clamp marker coordinates to 0..1000.
- Never store form values.
- Never store DOM content in live-state.
- Add TTL cleanup for old live frames if multiple frames are kept.

### 3. Frame Capture Behavior

Capture a screenshot:

- after successful `navigate_readonly`;
- after `screenshot`;
- after approved single-step browser actions, if any are allowed by existing
  policy;
- optionally on a timer while a session is live, but keep rate low.

Recommended first version:

- Desktop polls `/desktop/private-browser/live-frame` every 500-1000ms.
- Backend captures on demand only if a session already exists.
- Rate-limit capture to no more than 5 FPS per runtime.
- If no live session exists, return idle; do not open a browser for the poll.

This keeps monitoring passive. The monitor should never create capability.

### 4. External Plugin Native Executor Integration

The policy chain remains:

```text
external_plugin_runtime_allowed
-> evaluate_external_call / prepare_external_call
-> run_private_ecosystem_native_call
-> _execute_private_ecosystem_native
-> run_browser_action
-> Playwright/session engine
-> browser live frame update
```

The session manager may be used only after the chain allows execution.

Update `_execute_private_ecosystem_native` so browser actions use the managed
private session where appropriate. Avoid reopening a fresh browser for every
single frame if a safe persistent session is active.

Do not route computer control into this monitor.

### 5. Live State Snapshot

Add a sanitized live-state builder.

Suggested function:

```python
build_private_browser_live_state(root: Path) -> dict[str, Any]
```

Output:

```json
{
  "ok": true,
  "observed": true,
  "session": "live|idle|unavailable",
  "updated_at": "...",
  "engine": "live|simulated|unavailable",
  "browser": "chromium|edge|unknown",
  "url_host": "example.com",
  "url_redacted": "https://example.com/path",
  "action_kind": "navigate_readonly|snapshot_dom|screenshot|click_element|fill|scroll|none",
  "result": "completed|blocked|held|prepared|simulated|idle",
  "gate_reason": "read_only_allowed|approval_required|plugin_disabled|...",
  "risk": "read_only|approval_required|high_blocked|unknown",
  "cursor": {
    "type": "pointer|click|target|text|scroll|none",
    "x": 0,
    "y": 0,
    "coordinate_plane": "viewport_0_1000",
    "blocked": false
  },
  "last_action": {
    "action_id": "bact-...",
    "kind": "click_element",
    "result": "blocked",
    "reason": "approval_required",
    "has_input": false,
    "screenshot_ref": "runtime/private_ecosystem/browser_live/latest.png"
  },
  "gates": {
    "private_browser_enabled": true,
    "private_browser_plugin_enabled": false,
    "private_browser_proactive_enabled": false,
    "allowed_urls_count": 0,
    "computer_control_enabled": false
  },
  "boundaries": {
    "workspace": "private_browser",
    "owner_desktop_capture": false,
    "os_mouse_control": false,
    "raw_dom_returned": false,
    "stable_memory_write": "blocked"
  }
}
```

### 6. HTTP Routes

Add two read-only routes:

- `GET /desktop/private-browser/live-state`
- `GET /desktop/private-browser/live-frame`

Requirements:

- Bridge token required.
- Include both in Desktop GET routing.
- No POST route in this task.
- No owner-private payload required for these GET routes, same rationale as
  `/desktop/snapshot`: token is the Desktop owner credential and output is
  sanitized.
- `live-state` returns JSON.
- `live-frame` returns PNG bytes or `204 No Content` when no frame is available.
- `live-frame` must not trigger navigation, click, fill, type, or grant change.
- `live-frame` must not serve arbitrary paths. It may serve only the known
  latest frame path under `runtime/private_ecosystem/browser_live`.

If the existing HTTP helper only sends JSON, add a minimal binary response
helper carefully and only for this route.

### 7. Desktop Gateway / IPC

Wire Desktop main/preload/renderer without adding execution controls.

Likely files:

- `XinYu_Desktop/src/main/xinyu_gateway.ts`
- `XinYu_Desktop/src/main/index.ts`
- `XinYu_Desktop/src/preload/index.ts`
- `XinYu_Desktop/src/renderer/src/global.d.ts`
- `XinYu_Desktop/src/renderer/src/main.tsx`
- `XinYu_Desktop/src/renderer/src/DesktopPanels.tsx` or new component file
- `XinYu_Desktop/src/renderer/src/desktopTypes.ts`

Gateway functions:

```ts
getPrivateBrowserLiveState(): Promise<PrivateBrowserLiveState>
getPrivateBrowserLiveFrame(): Promise<Blob | ArrayBuffer | string>
```

Prefer returning an object URL or data URL to renderer only after token-auth
fetch succeeds in the main process, following existing Desktop security
patterns.

## Desktop UI

Add `BrowserLiveMonitorPanel`.

Preferred structure:

- Header/status row:
  - "XinYu Browser Workspace"
  - session: live/idle/unavailable
  - browser: Chromium headless / Edge fallback / unknown
  - host
  - action kind
  - result
  - gate reason

- Main monitor viewport:
  - show latest PNG frame;
  - fixed aspect ratio, e.g. 16:9;
  - dark neutral background when idle;
  - overlay marker in container coordinates mapped from 0..1000;
  - marker types:
    - pointer: small dot/crosshair;
    - click: ring pulse;
    - target/text: small rectangle/caret marker;
    - scroll: arrow;
    - blocked: red dashed marker/ring.

- Side rail:
  - browser grant enabled;
  - plugin enabled;
  - proactive enabled;
  - allowed URLs count;
  - computer control off;
  - owner desktop capture false.

- Footer:
  - frame age;
  - screenshot ref tail;
  - "private browser workspace" boundary.

UI constraints:

- Read-only. No buttons for click/type/navigate.
- No hero page.
- No marketing copy.
- No card inside card.
- Do not use large decorative gradients/orbs.
- Keep text compact and scannable.
- Avoid text overflow at narrow widths.
- Follow existing Desktop visual style.
- Poll live state/frame at 500-1000ms while panel is visible.
- Pause polling when panel is hidden/unmounted.
- If frame fetch fails, keep last good frame and show stale/unavailable state.

## Privacy And Safety Details

Frame route:

- Only returns PNG bytes from the private browser live frame.
- Does not expose local absolute path.
- Does not expose DOM.
- Does not expose cookies or browser storage.

State route:

- URL query and fragment removed.
- Form values never returned.
- `fill`/`type` only surface `has_input`.
- Artifact refs are relative and private-ecosystem-scoped.
- Bad JSONL lines are skipped.
- Missing files produce idle state, not bridge failure.

Browser session:

- Uses isolated profile only.
- Does not bind open CDP.
- Does not create remote debugging ports.
- Does not disable sandbox or web security.
- Does not use owner profile.

## Tests

Add backend tests:

- `tests/test_private_browser_live_state.py`
- `tests/test_bridge_private_browser_live_routes.py`

Minimum coverage:

1. Empty runtime returns idle/unavailable without error.
2. Latest action with screenshot produces live state.
3. URL query/fragment are stripped.
4. Fill/type value is not leaked.
5. Marker coordinates clamp to 0..1000.
6. `live-frame` requires bridge token at HTTP routing level.
7. `live-frame` serves only the known private live PNG.
8. Path traversal is impossible or rejected.
9. `live-frame` does not trigger `run_browser_action`.
10. Browser action through native executor updates live-state/frame after a
    read-only loopback page action.
11. No owner desktop capture appears in state.
12. `computer_control_enabled` remains false in boundary snapshot when grants
    are unchanged.

Desktop verification:

- `npm run typecheck`
- `npm run build`

Python verification:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_private_browser_live_state.py `
  tests/test_bridge_private_browser_live_routes.py `
  tests/test_private_ecosystem_autobrowse.py `
  tests/test_bridge_private_ecosystem_routes.py `
  tests/test_private_ecosystem_external_plugins.py `
  tests/test_private_browser_engine_playwright.py
```

Also run a bridge import sanity:

```powershell
.\.venv\Scripts\python.exe -c "import xinyu_bridge_http, xinyu_core_bridge; print('bridge import OK')"
```

## Manual Verification

Use a loopback page only. Do not browse external sites for verification.

Expected manual proof:

1. Start or restart Core Bridge.
2. Open Desktop.
3. Browser workspace panel shows idle if no private browser session exists.
4. Trigger a policy-gated read-only browser action through existing route/helper.
5. Panel shows a Chromium headless frame.
6. Marker overlays last target/action.
7. Gate status matches action result.
8. No Windows mouse movement occurs.
9. Owner desktop is not captured.

## Acceptance Report Must Include

- Files changed.
- New routes.
- Whether persistent session manager was landed or latest-frame polling was used.
- Browser binary actually used: bundled Chromium vs Edge fallback.
- Proof `effective_channel=''` if using bundled Chromium.
- Frame route behavior when no session exists.
- Sanitization coverage.
- Test results.
- Explicit statements:
  - grants unchanged;
  - `computer_control` not enabled;
  - `allowed_urls` not filled;
  - no new execution buttons;
  - no OS mouse/desktop control;
  - no `external_plugin_call` bypass.

## Rollback

All changes should be additive.

Rollback path:

- Remove new live monitor backend modules and tests.
- Remove new bridge routes and runtime delegators.
- Remove Desktop live monitor component and IPC/gateway additions.
- Keep existing private browser/external plugin behavior unchanged.

