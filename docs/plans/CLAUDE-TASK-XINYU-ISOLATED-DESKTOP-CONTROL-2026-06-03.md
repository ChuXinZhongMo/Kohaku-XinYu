# Claude Task: XinYu Isolated Desktop Control

date: 2026-06-03
from: Codex / architecture director
to: Claude / executor
repo: D:\XinYu
app root: D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
desktop root: D:\XinYu\XinYu_Desktop
venv python: `.\.venv\Scripts\python.exe`

## Objective

Build XinYu a full desktop workspace that the owner can watch in real time and
that XinYu can control without stealing the owner's Windows mouse, keyboard, or
active desktop session.

This supersedes the narrower "private browser monitor" direction. The target is
a complete isolated desktop: browser, terminal, file manager, simple apps, live
video/remote-desktop view, and policy-gated action injection.

Important definition:

- "XinYu desktop" means an isolated local VM/container/remote-desktop session
  owned by XinYu.
- It does not mean controlling the owner's current Windows desktop.
- It does not mean capturing the owner's screen.
- It does not mean moving the owner's physical mouse.

The owner should see something like a small remote desktop window inside XinYu
Desktop, with real-time video, cursor movement, clicks, typing, scrolling, and
gate/action status.

## GitHub Reconnaissance Summary

Use these projects as architecture references only. Do not copy code. Any
runtime dependency must pass license and supply-chain review before installation.

1. Cua (`trycua/cua`)
   - URL: https://github.com/trycua/cua
   - Why it matters: direct computer-use-agent infrastructure; sandbox API for
     screenshots, mouse, keyboard, shell, and OS images; Cua Driver claims
     background desktop control on macOS/Windows without stealing cursor/focus.
   - Useful ideas: sandbox abstraction, screenshot/mouse/keyboard API, typed
     computer server, background control boundary.
   - Caution: do not run curl/PowerShell install scripts blindly; audit first.
     Optional dependencies mention AGPL components through some extras. Keep
     XinYu's own policy chain as owner.

2. noVNC (`novnc/noVNC`)
   - URL: https://github.com/novnc/noVNC
   - Why it matters: mature HTML5/WebSocket VNC client, easy to embed in a
     browser/Electron panel, supports scaling and local cursor rendering.
   - Useful ideas: VNC display in Desktop via iframe/webview, localhost-only
     websockify bridge, view-only mode for monitoring.
   - License note: mainly MPL-2.0. OK as dependency only after review.

3. Apache Guacamole (`apache/guacamole-client`, `apache/guacamole-server`)
   - URLs:
     - https://github.com/apache/guacamole-client
     - https://github.com/apache/guacamole-server
     - https://guacamole.apache.org/
   - Why it matters: browser gateway for remote desktop protocols.
   - Useful ideas: remote-desktop gateway boundary, browser-only client,
     protocol adapter separation.
   - Caution: Java/Tomcat/guacd stack is heavier than needed for a local first
     increment.

4. Selkies (`selkies-project/selkies`)
   - URL: https://github.com/selkies-project/selkies
   - Why it matters: low-latency Linux WebRTC HTML5 remote desktop streaming for
     containers/Kubernetes/cloud/HPC.
   - Useful ideas: WebRTC desktop streaming if VNC/noVNC latency becomes a
     problem.
   - Caution: more moving parts than noVNC; use later, not first.

5. QuickDesk (`barry-ran/QuickDesk`)
   - URL: https://github.com/barry-ran/QuickDesk
   - Why it matters: AI-native remote desktop with MCP, real-time visibility,
     screenshot/click/type/drag/hotkey/clipboard tools, WebRTC streaming.
   - Useful ideas: separate remote display stream from action API, real-time
     operator visibility, event stream, device/session auth.
   - Caution: do not wire XinYu directly to MCP. Route through XinYu external
     plugin gate and grants.

6. mcp-vnc (`hrrrsn/mcp-vnc`)
   - URL: https://github.com/hrrrsn/mcp-vnc
   - Why it matters: minimal VNC screenshot/click/type/key tools for agents.
   - Useful ideas: small tool surface and VNC coordinate actions.
   - Caution: too permissive if connected directly. Use only as a design
     reference; XinYu must own policy.

7. Contop (`slopedrop/contop`)
   - URL: https://github.com/slopedrop/contop
   - Why it matters: remote desktop + live video + agent progress streaming +
     security gates.
   - Useful ideas: live video beside execution thread, dual data channels,
     audit log, destructive-action approval.
   - Caution: it targets controlling real desktops. XinYu must start with an
     isolated desktop, not the owner desktop.

Rejected or deferred:

- RustDesk: mature remote desktop, but AGPL-3.0. Do not copy or embed without
  explicit license decision.
- Direct host Windows automation MCP servers: useful references, but unsafe for
  XinYu's first full-desktop layer because they target the owner's live desktop.
- Browser-only Playwright monitor: useful foundation, but not enough for the
  owner's stated goal.

## Architecture Choice

Recommended first implementation:

```text
XinYu Core
  -> external_plugin_call gate
  -> xinyu_private_desktop native executor
  -> XinYu isolated desktop service
      -> local Linux desktop session (container/VM)
      -> VNC server on loopback only
      -> noVNC/websockify on loopback only
      -> action adapter (screenshot, mouse, keyboard, shell)
  -> Desktop cockpit embeds live noVNC view in view-only mode by default
```

Why this choice:

- It gives XinYu a complete desktop, not just a browser.
- It does not steal the owner's mouse.
- It does not capture the owner's Windows desktop.
- It is easier to secure than host automation.
- It reuses mature remote desktop primitives.
- It can later be upgraded to WebRTC/Selkies or Cua sandbox if needed.

Fallback choices:

1. If Docker/WSL2 is available:
   - use a local Linux desktop container with XFCE/Openbox + x11vnc/TigerVNC +
     noVNC/websockify;
   - bind all ports to `127.0.0.1`;
   - store state under `runtime/private_ecosystem/desktop_workspace`.

2. If Docker/WSL2 is unavailable:
   - create a documented blocked report;
   - do not fall back to controlling the owner's Windows desktop.

3. If the owner explicitly wants Windows apps later:
   - use a separate Windows VM / Windows Sandbox / Hyper-V session;
   - do not automate the host desktop;
   - keep the same external-plugin/action API.

## Hard Red Lines

- Do not control the owner's current Windows desktop.
- Do not capture the owner's desktop.
- Do not move the owner's physical mouse.
- Do not enable existing `computer_control` as a shortcut.
- Do not bypass `external_plugin_call`.
- Do not bypass bridge auth, owner-private checks, self-action approval,
  QQ outbox claim/ack, external plugin runtime gate, or stable memory review.
- Do not fill `private_browser.allowed_urls`.
- Do not change existing grants unless the task explicitly asks for a new
  isolated-desktop grant schema with safe defaults off.
- Do not expose remote desktop ports on LAN/public interfaces.
- Do not expose unauthenticated noVNC/VNC/RDP.
- Do not store remote desktop passwords, cookies, tokens, form values, raw
  screenshots with owner data, or DOM/body content in owner-visible reports.
- Do not allow arbitrary shell inside the isolated desktop without explicit
  approval or a narrow grant.
- Do not implement multi-step autonomous desktop control in the first landing.
- Do not copy third-party implementation code.
- Do not add mutable `latest` dependencies.
- Do not use AGPL components without explicit owner/license decision.

## Capability Model

Add a new plugin identity:

- `xinyu_private_desktop`

Do not overload `xinyu_computer_control`. This is a separate isolated desktop
capability provider.

Suggested capabilities:

Read-only / low-risk:

- `desktop.status`
- `desktop.live_view`
- `desktop.screenshot`
- `desktop.list_windows` if the isolated environment supports it
- `desktop.observe_text` if OCR/accessibility exists and is sanitized

Proposal-only:

- `desktop.propose_click`
- `desktop.propose_type`
- `desktop.propose_hotkey`

Approval-required single-step:

- `desktop.click`
- `desktop.double_click`
- `desktop.move_mouse`
- `desktop.scroll`
- `desktop.type_text`
- `desktop.hotkey`
- `desktop.clipboard_set`

High-risk / blocked by default:

- `desktop.shell`
- `desktop.download`
- `desktop.upload`
- `desktop.install_package`
- `desktop.network_open_external`
- `desktop.multi_step_task`
- `desktop.arbitrary_keyboard_mouse`

First landing should execute only:

- status/live-view/screenshot read-only;
- proposal-only records;
- single-step actions only when owner-approved through existing gates.

No autonomous multi-step desktop operation in this task.

## Grants

Add a new grant section with safe defaults:

```json
{
  "private_desktop": {
    "enabled": false,
    "observe_only": true,
    "single_step_actions": false,
    "shell_enabled": false,
    "network_enabled": false,
    "max_frame_rate": 10,
    "idle_shutdown_minutes": 30,
    "workspace": "isolated_desktop"
  }
}
```

Rules:

- Environment variables may enable code paths but not grant permission.
- Grant route must not allow `single_step_actions`, `shell_enabled`, or
  `network_enabled` to be turned on casually.
- Any future route that changes these high-risk fields needs a dedicated
  owner-approved mode and tests.

## Runtime Layout

Use private ecosystem runtime paths:

```text
runtime/private_ecosystem/desktop_workspace/
  state.json
  events.jsonl
  actions.jsonl
  frames/
  latest_frame.png
  novnc/
  vnc/
  container/
  logs/
memory/context/private_ecosystem_desktop_state.md
```

Never write raw VNC passwords or long-lived credentials to public reports.

## Implementation Plan

### Phase 0: Environment Probe

Add a probe module or CLI:

- `xinyu_private_desktop_environment.py`

Probe:

- Docker availability.
- WSL2 availability.
- Hyper-V availability if useful.
- Free localhost ports.
- Existing noVNC/websockify availability if already installed.
- Whether loopback bind can be enforced.

This probe is read-only. It must not install anything.

If no viable isolated desktop backend exists, report blocked and stop. Do not
automate the host desktop.

### Phase 1: Isolated Desktop Service Contract

Add:

- `xinyu_private_desktop_control.py`
- `xinyu_private_desktop_service.py`
- `xinyu_private_desktop_grants.py` if not folded into existing grants helper

Define typed records:

```python
DesktopActionRecord(
    action_id: str,
    action_kind: str,
    risk: str,
    result: str,
    coordinate_plane: str,
    target: dict,
    last_action_marker: dict,
    frame_ref: str = "",
    observed_at: str = "",
    error_code: str = "",
    notes: tuple[str, ...] = (),
)
```

Policy:

- observe-only requires `private_desktop.enabled=true` and `observe_only=true`.
- single-step requires `approved=true` or a dedicated single-step grant.
- shell/download/install/network are blocked in first landing.
- all actions append to `actions.jsonl`.
- every executed action should capture after-frame if possible.

### Phase 2: Local Desktop Backend

Implement a backend interface first:

```python
class PrivateDesktopBackend(Protocol):
    def status(self) -> dict[str, Any]: ...
    def ensure_started(self) -> dict[str, Any]: ...
    def stop(self) -> dict[str, Any]: ...
    def screenshot(self) -> bytes: ...
    def click(self, x: int, y: int, button: str = "left") -> dict[str, Any]: ...
    def move_mouse(self, x: int, y: int) -> dict[str, Any]: ...
    def scroll(self, x: int, y: int, delta: int) -> dict[str, Any]: ...
    def type_text(self, text: str) -> dict[str, Any]: ...
    def hotkey(self, keys: list[str]) -> dict[str, Any]: ...
```

Backend selection:

- `docker_xfce_vnc` preferred on this Windows machine if Docker Desktop/WSL2 is
  installed.
- `simulated` fallback for tests only; it must honestly report simulated.

Docker backend target:

- Linux image with minimal desktop (XFCE/Openbox), VNC server, noVNC/websockify.
- Browser installed inside the isolated desktop if needed.
- Ports bound only to `127.0.0.1`.
- Random VNC/noVNC password/token per session if supported.
- Owner Desktop receives only a bridge-token-protected view URL/proxy route.

Do not use arbitrary public images without pinning. If a prebuilt image is used,
document digest, license, provenance, and supply-chain review. Prefer a local
Dockerfile under a clearly named ops/runtime path if practical.

### Phase 3: noVNC / Live View

Two acceptable implementations:

Option A: proxy noVNC through XinYu bridge.

- Desktop embeds a local bridge route.
- Bridge checks token.
- Bridge forwards to loopback noVNC.
- More work, stronger boundary.

Option B: Desktop main process fetches a generated loopback noVNC URL and
embeds it in a webview/iframe with an ephemeral token.

- Faster.
- Must bind to `127.0.0.1`.
- Must use unguessable session token.
- Must not expose VNC password in renderer-visible state if avoidable.

Default mode:

- view-only monitor.
- owner manual takeover can be added as an owner-only toggle only after the
  view-only monitor is proven.

AI action injection:

- do not use the noVNC UI channel directly from XinYu autonomy;
- route AI actions through `external_plugin_call` and backend adapter.

### Phase 4: External Plugin Registration

Update `xinyu_external_plugins.py`:

- add `xinyu_private_desktop`.
- default `enabled=false`, `proactive_enabled=false`.
- mark read-only capabilities proactive-capable only after owner grant exists.
- mark single-step capabilities `requires_approval=true`.
- mark shell/network/install/download blocked or unregistered in first landing.

Update `xinyu_bridge_external_plugin_routes.py`:

- add native executor branch through a reusable helper.
- do not let external plugin runtime define policy.
- return structured execution result with `record`, `frame_ref`, `error_code`.

### Phase 5: Bridge Routes

Add read-only routes:

- `GET /desktop/private-desktop/snapshot`
- `GET /desktop/private-desktop/live-state`
- `GET /desktop/private-desktop/frame`

Optional owner actions, only if tightly gated:

- `POST /desktop/private-desktop/start`
- `POST /desktop/private-desktop/stop`

Do not add `POST /desktop/private-desktop/action` unless it routes through the
same external-plugin call chain and has owner-private + approval behavior.

Route requirements:

- all GET routes require bridge token.
- all POST routes require bridge token and owner-private payload.
- no route may expose raw local paths, VNC password, Docker secret, or host
  desktop capture.
- frame route serves only the latest isolated desktop frame or a bridge-proxied
  stream.

### Phase 6: Desktop UI

Add `PrivateDesktopPanel`.

Visual behavior:

- main panel is a live remote desktop view.
- side rail shows:
  - backend: docker_xfce_vnc / simulated / unavailable
  - session: stopped / starting / live / error
  - display size
  - frame age / fps
  - gate status
  - last action
  - `owner desktop capture: false`
  - `os mouse control: false`
  - `computer_control: off`

Controls:

- First landing: start/stop may be allowed only as owner actions.
- No AI action buttons.
- No "grant single-step" button.
- If owner manual takeover is implemented, it must be a clearly labeled
  owner-only view-control toggle, not an autonomy grant.

UI style:

- cockpit/workbench, not marketing.
- no hero.
- no nested cards.
- stable aspect ratio for remote desktop.
- no text overflow.
- compact status tags.

### Phase 7: Optional Cua Research Branch

Do not install Cua in the first landing unless the owner explicitly asks after
review.

If considered later:

- inspect `libs/cua-driver` and `cua-sandbox` docs;
- avoid curl/PowerShell pipe-to-shell installers;
- pin exact release;
- verify license and optional dependencies;
- run only inside isolated workspace;
- never connect Cua Driver to the host desktop without a separate owner
  decision.

## Tests

Add tests:

- `tests/test_private_desktop_environment.py`
- `tests/test_private_desktop_control.py`
- `tests/test_private_desktop_external_plugin.py`
- `tests/test_bridge_private_desktop_routes.py`
- Desktop type tests as needed.

Required backend coverage:

1. safe defaults disabled.
2. observe blocked without grant.
3. observe allowed with isolated desktop grant.
4. click/type/hotkey blocked without approval.
5. shell/download/install/network blocked in first landing.
6. actions write typed records.
7. simulated backend reports simulated, not live.
8. frame refs are private-ecosystem relative paths only.
9. marker coordinates clamp to 0..1000.
10. no owner desktop capture appears anywhere.
11. external plugin disabled blocks runtime.
12. proactive disabled blocks proactive calls.
13. owner-private required for mutating/start/stop/action routes.
14. GET routes require bridge token.
15. live frame route cannot path-traverse.

Integration verification if Docker backend is available:

- start isolated desktop;
- verify noVNC URL bound to `127.0.0.1`;
- verify Desktop displays live view;
- perform one owner-approved single-step click inside isolated desktop;
- verify host Windows mouse position does not move;
- verify after-frame recorded;
- stop isolated desktop.

Regression:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_private_desktop_environment.py `
  tests/test_private_desktop_control.py `
  tests/test_private_desktop_external_plugin.py `
  tests/test_bridge_private_desktop_routes.py `
  tests/test_private_ecosystem_autobrowse.py `
  tests/test_bridge_private_ecosystem_routes.py `
  tests/test_private_ecosystem_external_plugins.py
```

Desktop:

```powershell
cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

## Manual Verification

Expected proof:

1. `xinyu_private_desktop_environment.py --json` reports available/unavailable
   backends honestly.
2. If backend unavailable, task stops with documented blocker.
3. If backend available, owner starts isolated desktop from Desktop or bridge.
4. Desktop shows a live remote desktop frame.
5. The view is XinYu's isolated desktop, not the host Windows desktop.
6. A single approved click/type inside the isolated desktop works.
7. The owner's physical mouse does not move.
8. `computer_control` remains off.
9. No autonomous multi-step desktop action is enabled.
10. All actions are in `runtime/private_ecosystem/desktop_workspace/actions.jsonl`.

## Acceptance Report Must Include

- GitHub references used and what was borrowed conceptually.
- Chosen backend: Docker/WSL/noVNC, simulated-only, or blocked.
- Whether live view is noVNC, frame polling, or another transport.
- Ports used and proof they bind to `127.0.0.1`.
- Files changed.
- New plugin and capabilities.
- New bridge routes.
- Tests run and results.
- Explicit statements:
  - host Windows desktop not controlled;
  - owner mouse not moved;
  - owner desktop not captured;
  - `computer_control` not enabled;
  - `private_browser.allowed_urls` not filled;
  - no `external_plugin_call` bypass;
  - no third-party code copied;
  - no AGPL dependency embedded.

## Stop Conditions

Stop and report instead of working around if:

- Docker/WSL/VM backend is unavailable and no isolated desktop can be created.
- A proposed route would require controlling the host Windows desktop.
- A remote desktop component cannot be bound to loopback.
- A third-party dependency has unclear or incompatible licensing.
- Any implementation path requires disabling existing XinYu gates.

## Rollback

All changes must be additive.

Rollback path:

- disable `xinyu_private_desktop` plugin;
- stop and remove isolated desktop runtime container/session;
- delete new private desktop modules/tests/routes/UI component;
- leave existing private browser/private ecosystem behavior unchanged.

