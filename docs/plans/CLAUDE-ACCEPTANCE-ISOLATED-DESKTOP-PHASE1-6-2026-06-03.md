# Acceptance Report: XinYu Isolated Desktop Control — Phases 1–6

date: 2026-06-03
executor: Claude (Opus 4.8)
director: Codex
task: CLAUDE-TASK-XINYU-ISOLATED-DESKTOP-CONTROL-2026-06-03.md
outcome: **Phases 1–6 implemented (additive). Isolated Docker XFCE/VNC backend
built locally; full policy/control/record + plugin gate + bridge routes + Desktop
cockpit landed and tested. Host Windows desktop NOT controlled.**

## Backend chosen

`docker_xfce_vnc` — a **locally built** image (not an arbitrary prebuilt desktop
image) from `ops/private_desktop/Dockerfile`, base pinned by digest
`debian:bookworm-slim@sha256:0104b334637a5f19aa9c983a91b54c89887c0984081f2068983107a6f6c21eeb`.
Components: XFCE + Xvfb + x11vnc + noVNC/websockify + xdotool + imagemagick.
`simulated` backend is the honest offline fallback (tests + no-container path);
it always reports `simulated`, never `live`.

Docker probe: `decision=available`, Server 29.4.3, Linux engine. (WSL2 still not
installed; Hyper-V present — Docker uses its own backend.)

## Live view transport

noVNC over loopback websockify (plain HTTP), embedded in the Desktop cockpit as a
**view-only** iframe (`?autoconnect=true&view_only=true&resize=scale`). AI action
injection does NOT use the noVNC UI channel — it routes through
`external_plugin_call` → native executor → backend adapter (`docker exec xdotool`).

## Ports / loopback proof

Host ports are published **only** to `127.0.0.1`:
`-p 127.0.0.1:6080:6080` (noVNC) and `-p 127.0.0.1:5900:5900` (VNC). Nothing binds
to a LAN/public interface. Phase-0 probe confirmed these ports free on loopback.

<!-- LIVE-INTEGRATION -->
Live integration proof (Codex, 2026-06-03):

- Build: `docker build --progress=plain -t xinyu/private-desktop:1 ops/private_desktop`
  completed successfully without the Openbox speed-up. Image
  `xinyu/private-desktop:1` => ID `a68c3a7b69e8`, size `1.02GB`.
- Start: `DockerXfceVncBackend(...).ensure_started(build_if_missing=False)`
  returned `{'ok': True, 'session_state': 'live', 'live': True,
  'live_view_url': 'http://127.0.0.1:6080/vnc.html'}`.
- Loopback proof:
  ```text
  docker port xinyu-private-desktop
  5900/tcp -> 127.0.0.1:5900
  6080/tcp -> 127.0.0.1:6080

  netstat -ano | findstr 6080
  TCP    127.0.0.1:6080         0.0.0.0:0              LISTENING       15756

  netstat -ano | findstr 5900
  TCP    127.0.0.1:5900         0.0.0.0:0              LISTENING       15756
  ```
- Live frame: read-only `screenshot` completed on backend `live`, wrote
  `runtime/private_ecosystem/desktop_workspace/frames/dact-3eef730d9e7e2987.png`
  (`1280x800`, 25,800 bytes). Visual inspection showed an XFCE desktop with panel
  and desktop icons.
- Approved click: `click` at policy coordinate `(500, 500)` with `approved=True`
  completed on backend `live`, wrote after-frame
  `runtime/private_ecosystem/desktop_workspace/frames/dact-54f38714f7acf29d-after.png`
  (`1280x800`, 25,673 bytes). Container-side `xdotool getmouselocation` reported
  `x:640 y:400 screen:0 ...`, matching 0..1000 -> 1280x800 scaling.
- Host mouse proof: Windows cursor position sampled immediately before/after the
  approved click stayed `(1026, 777)` -> `(1026, 777)`. No host input or host
  screen-capture command was used; cursor sampling was read-only, and the action
  path was container-only `docker exec ... xdotool`.
- Stop/cleanup: `DockerXfceVncBackend(...).stop()` returned `{'ok': True,
  'session_state': 'stopped', 'live': False}`. After stop,
  `docker ps --filter name=xinyu-private-desktop` returned no rows, `netstat`
  showed no `6080`/`5900` listener, and
  `runtime/private_ecosystem/desktop_workspace/session_secret.json` was absent.
- Grants hygiene: live verification temporarily patched `private_desktop` as
  required by the checklist, then restored
  `memory/context/private_ecosystem_grants.json` to its pre-run SHA256
  `2DB108C7AFFD6A0CDF538A1B7721C12AAFF673B18D1725D4DF7EE97A75BA5548`.

## Capability model

New plugin `xinyu_private_desktop` (separate from `xinyu_computer_control`):
- read-only / proactive-capable: `status`, `live_view`, `screenshot`,
  `list_windows`, `observe_text`;
- proposal-only (records, never executes): `propose_click`, `propose_type`,
  `propose_hotkey`;
- approval-required single-step: `click`, `double_click`, `move_mouse`, `scroll`,
  `type_text`, `hotkey`, `clipboard_set`;
- high-risk (`shell`/`download`/`upload`/`install_package`/`network_open_external`/
  `multi_step_task`/`arbitrary_keyboard_mouse`): **unregistered** in the plugin AND
  blocked in the control layer (defense in depth). No autonomous multi-step.

## Grants

New `private_desktop` grant section, safe defaults all off:
`enabled=false, observe_only=true, single_step_actions=false, shell_enabled=false,
network_enabled=false, max_frame_rate=10, idle_shutdown_minutes=30,
workspace=isolated_desktop`. Env may enable code paths but not grant permission.
The high-risk fields are not flippable through the normal grant route.

## New bridge routes

- `GET /desktop/private-desktop/snapshot` (bridge token)
- `GET /desktop/private-desktop/live-state` (bridge token)
- `GET /desktop/private-desktop/frame` (bridge token; latest frame or a strictly
  validated `^[A-Za-z0-9_-]+\.png$` id — cannot path-traverse; returns a base64
  data URL, never a raw host path)
- `POST /desktop/private-desktop/start` (bridge token + owner-private)
- `POST /desktop/private-desktop/stop` (bridge token + owner-private)

No `POST .../action` route was added; AI actions go through `external_plugin_call`.

## Files changed (additive)

App (`XinYu-Core/examples/agent-apps/xinyu/`):
- `xinyu_private_desktop_control.py` (new — policy + typed records + snapshot)
- `xinyu_private_desktop_service.py` (new — backend Protocol + simulated + docker)
- `xinyu_bridge_private_desktop_routes.py` (new — bridge routes)
- `ops/private_desktop/Dockerfile`, `ops/private_desktop/entrypoint.sh` (new)
- `xinyu_private_ecosystem_grants.py` (+`private_desktop` section, `desktop_grant`)
- `xinyu_external_plugins.py` (+`xinyu_private_desktop` spec, control default, install)
- `xinyu_bridge_external_plugin_routes.py` (+desktop native executor branch)
- `xinyu_core_bridge.py` (+5 delegators, +import)
- `xinyu_bridge_http.py` (+3 GET routes, +2 POST routes, token/dispatch)
- `xinyu_status.py` (+`private_desktop` status check — grant/boundary visibility;
  reads grants + workspace state only, no Docker call, stays fast)
- tests: `tests/test_private_desktop_control.py`,
  `tests/test_private_desktop_external_plugin.py`,
  `tests/test_bridge_private_desktop_routes.py`

Desktop (`XinYu_Desktop/`):
- `src/main/xinyu_gateway.ts` (+snapshot field, +3 methods)
- `src/main/index.ts` (+3 IPC handlers)
- `src/preload/index.ts`, `src/renderer/src/global.d.ts` (+3 bridge methods)
- `src/renderer/src/DesktopPanels.tsx` (+`PrivateDesktopPanel`)
- `src/renderer/src/main.tsx` (+state, +handlers, +10s refresh)

## Tests run and results

```
pytest -q tests/test_private_desktop_environment.py \
  tests/test_private_desktop_control.py \
  tests/test_private_desktop_external_plugin.py \
  tests/test_bridge_private_desktop_routes.py \
  tests/test_private_ecosystem_autobrowse.py \
  tests/test_bridge_private_ecosystem_routes.py \
  tests/test_private_ecosystem_external_plugins.py
=> 65 passed
```
New-module subset: 35 passed. Required backend coverage 1–15 are covered (safe
defaults disabled; observe blocked without grant; observe allowed with grant;
single-step blocked without approval; high-risk blocked; typed records; simulated
reports simulated; frame refs are private-ecosystem relative paths; markers clamp
0..1000; no owner desktop capture; plugin disabled blocks runtime; proactive
disabled blocks proactive; owner-private required for start/stop; GET routes
require token; frame route cannot path-traverse). Unit tests force the simulated
backend (`docker_available=False`) — they never touch real Docker.

Desktop: `npm run typecheck` ✓, `npm run build` ✓.

## GitHub references — borrowed conceptually only (no code, nothing embedded)

- noVNC (MPL-2.0): HTML5 VNC client for the loopback live view.
- Apache Guacamole: remote-desktop gateway boundary concept.
- QuickDesk / Contop / Selkies: separate display stream from action API; live view
  beside execution; audit log; destructive-action approval (future WebRTC option).
- mcp-vnc: minimal VNC tool surface (reference only; XinYu owns policy).
- trycua/cua: sandbox abstraction (deferred; AGPL-tinged extras; not installed).
- RustDesk: rejected (AGPL-3.0).
No third-party implementation code copied; no AGPL component embedded.

## Explicit safety statements

- Host Windows desktop **NOT** controlled.
- Owner physical mouse **NOT** moved.
- Owner desktop/screen **NOT** captured (frames come from the isolated Xvfb only).
- `computer_control` **NOT** enabled (separate plugin; stays off).
- `private_browser.allowed_urls` **NOT** filled.
- No `external_plugin_call` bypass (AI actions go through the full gate chain).
- No third-party code copied; no AGPL dependency embedded.
- No `latest`/unpinned dependency (base image pinned by digest).
- All remote-desktop ports bind `127.0.0.1` only; no LAN/public exposure.

## Known limitations / honest follow-ups

- `idle_shutdown_minutes` (default 30) is a **declared** grant field but is NOT yet
  auto-enforced — there is no background reaper, by design (no autonomous loop in
  this landing, and GET routes stay read-only). The owner stops the container
  explicitly (cockpit/`stop` route) or a future autonomy tick can call
  `DockerXfceVncBackend.stop()` on idle. Until then, a started container keeps
  running until stopped.
- Live view default is **view-only**. Owner manual takeover is intentionally not
  wired yet (the task gates it behind "after the view-only monitor is proven").
- The noVNC iframe prompts for the per-session VNC password (kept out of
  renderer-visible state); the password lives only in the loopback workspace
  `session_secret.json` and is removed on stop.
- `clipboard_set` is recorded/policy-gated but is a no-op inside the container in
  this landing (xdotool cannot set the X clipboard directly); it never fails open.

## Rollback

Disable the `xinyu_private_desktop` plugin; `docker stop xinyu-private-desktop`;
`docker rmi xinyu/private-desktop:1`; delete the new modules/tests/routes/UI and
the `ops/private_desktop` dir; existing private browser/ecosystem behavior is
untouched.
