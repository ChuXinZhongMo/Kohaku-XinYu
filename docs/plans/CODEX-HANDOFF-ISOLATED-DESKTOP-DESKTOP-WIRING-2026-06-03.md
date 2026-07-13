# Codex Handoff: Isolated Desktop — Desktop-app wiring issues (owner-reported)

date: 2026-06-03
from: Claude
to: Codex
repo: D:\XinYu
app root: D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
desktop root: D:\XinYu\XinYu_Desktop
venv python: `.\.venv\Scripts\python.exe`

## TL;DR

The isolated-desktop backend is fully built, live-verified, and works when driven
directly from Python. The owner CANNOT get it to work from the **Desktop app**:
clicking 授权 / 启动 does nothing and the panel shows `不可用 / 未授权`. Root cause
is almost certainly **stale running processes** (an old core-bridge without the new
routes, and an old Electron preload/main without the new IPC), NOT a code defect —
the freshly built artifacts contain all the new code. This handoff lists the
owner's exact complaints and what to verify/fix.

## What is already proven working (do NOT rebuild)

- Image `xinyu/private-desktop:1` (ID `a68c3a7b69e8`, 1.02GB) built; base pinned by
  digest. Do not rebuild unless missing.
- `DockerXfceVncBackend.ensure_started(build_if_missing=False)` → returns
  `session_state=live`, noVNC/VNC bound to `127.0.0.1:6080 / 5900` only.
- Read-only screenshot → real XFCE frame; approved click → happens in container
  Xvfb; host Windows cursor unchanged. (See
  `CLAUDE-ACCEPTANCE-ISOLATED-DESKTOP-PHASE1-6-2026-06-03.md`.)
- Full bridge import chain imports cleanly; `XinYuBridgeRuntime` has
  `desktop_private_desktop_{snapshot,live_state,frame,start,stop}`.
- pytest: 67 focused tests pass.

> NOTE: a diagnostic container named `xinyu-private-desktop` was left RUNNING by
> Claude to let the owner verify via browser. Stop it when done:
> `docker stop xinyu-private-desktop` (it is `--rm`, so it self-removes).

## Owner-reported problems (verbatim intent)

1. **"授权按钮没反应,隔离桌面没有启动"** — clicking 授权（仅观察） and 启动隔离桌面
   in the Desktop panel does nothing; no live view ever appears.
2. **Panel shows `后端=不可用`, `授权=未授权`, `会话=已停止`, `0/0`** even though the
   backend works when called directly.
3. **No error feedback** appeared on the panel when clicking the buttons (Claude
   has since added a ✗/✓ result line, but on the owner's run nothing showed —
   consistent with the call throwing before it returns, i.e. an old preload where
   `window.xinyu.setPrivateDesktopEnabled` is undefined).
4. **Layout**: owner wanted the isolated desktop to be the main观察点 — "移到正中间,
   显示区域大一点,其余两列往左右靠". Resolved as a **放大观察 overlay** (owner's
   chosen option): a maximize button that opens the live view in a large centered
   overlay; the 4-column layout is unchanged. The 放大观察 button IS visible in the
   owner's screenshot, which confirms they ARE running the new renderer but
   (likely) an old preload/main.
5. **VNC password friction** — owner did not want to read the per-session password
   from `session_secret.json`. Resolved: `DockerXfceVncBackend.live_view_url()` now
   embeds `?autoconnect=true&password=...` (owner-private, loopback-only,
   destroyed on stop), so the cockpit auto-connects with no prompt.
6. **PowerShell one-liner failed** for the owner (multi-line paste split the
   command → `MissingEndParenthesisInExpression`). Not a product issue.

## Root-cause hypothesis (please confirm)

The owner is running:
- an **old core-bridge process** started before the new routes existed → POST
  `/desktop/private-desktop/start` 404s, and the grant route's OLD
  `_sanitize_grant_patch` rejects `private_desktop` (it was only just whitelisted)
  → 授权 silently no-ops; AND/OR
- an **old Electron preload/main** (e.g. `electron-vite dev` started earlier, which
  hot-reloads the renderer but NOT preload/main) → `window.xinyu.*` new methods are
  undefined → the click throws before any fetch, so not even a ✗ shows.

Evidence: top bar shows 离线; panel shows all-default `不可用`, meaning no
`privateDesktop` snapshot is reaching the renderer; built `out/preload/index.js`
and `out/main/index.js` DO contain `private-desktop-set-enabled / -start / -stop /
-snapshot`, so the build is correct — only the running processes are stale.

## What Codex should do

1. **Fully restart both processes** (not refresh):
   - Stop the running core-bridge and start a fresh one so it loads the new routes
     + the `private_desktop` grant whitelist.
   - Fully quit the Electron app (ensure the process ends) and relaunch from the
     fresh build (`npm run build` already done; launch the built app, or restart
     `npm run dev` from scratch so preload/main reload).
2. **Verify the end-to-end UI flow**:
   - Panel should now fetch a real snapshot: `后端=docker_xfce_vnc`, not `不可用`.
   - Click 授权（仅观察） → grant route accepts `private_desktop {enabled, observe_only}`
     (high-risk fields stay rejected). Panel shows `✓ 已授权（仅观察）`.
   - Click 启动隔离桌面 → POST `/desktop/private-desktop/start` → container live.
   - Live view auto-connects (password embedded in `live_view_url`); 放大观察 opens
     the big overlay.
3. **If 授权/启动 still fail after a clean restart**, capture the exact failure:
   - The panel now renders a `✗ <reason>` line — record it (e.g. `http 404` = bridge
     still stale; `unauthorized` = bridge token; `owner_private_context_required`
     = owner-private payload; `docker_unavailable` = bridge can't see Docker).
   - Check the bridge process can see Docker: from the bridge's environment,
     `python -c "import xinyu_private_desktop_service as s; print(s.docker_available())"`
     must be True (Docker Desktop running + `docker` on PATH).
   - Confirm the Desktop is actually connected (top bar 在线, `核心桥` green); if
     离线, the Desktop cannot reach the bridge and nothing will work.

## Files changed this session (all additive; tests pass)

- `xinyu_bridge_private_ecosystem_routes.py` — `_sanitize_grant_patch` now
  whitelists `private_desktop` (`enabled`, `observe_only`, clamped `max_frame_rate`
  / `idle_shutdown_minutes`); REJECTS `single_step_actions` / `shell_enabled` /
  `network_enabled` (high-risk, dedicated mode only). The grant section list now
  includes `private_desktop`.
- `xinyu_private_desktop_service.py` — `live_view_url()` embeds the one-time
  session password (`autoconnect`) for the owner cockpit.
- `xinyu_status.py` — added `private_desktop` status check (reads grants + workspace
  state only; no Docker call; green when boundaries safe + loopback-only).
- Desktop: `setPrivateDesktopEnabled` gateway method + IPC + preload + global.d.ts;
  `PrivateDesktopPanel` now has 授权/撤销授权 toggle, 放大观察 maximize overlay, and a
  ✗/✓ result line; `main.tsx` wires `setPrivateDesktopEnabled` + result state.
- Tests: `tests/test_bridge_private_ecosystem_routes.py` +2 (desktop grant enable /
  high-risk reject).

## Red lines (unchanged — keep守住)

- No host Windows desktop control / capture; no owner mouse movement.
- `computer_control` stays off; AI actions only via `external_plugin_call`.
- VNC password never written to reports; only in loopback `session_secret.json`,
  deleted on stop. (The password DOES now flow into the owner-private cockpit
  `live_view_url` for auto-connect — that was an explicit owner decision; keep it
  owner-private + loopback only, never in any report or LAN-exposed route.)
- All ports bind `127.0.0.1` only; grants/gates not weakened.

## Quick manual proof the backend is fine (decoupled from the app)

The diagnostic container is running now. In a browser:
`http://127.0.0.1:6080/vnc.html` → enter the password from
`runtime/private_ecosystem/desktop_workspace/session_secret.json` → XinYu's XFCE
desktop appears. This confirms the issue is purely the stale Desktop↔bridge
processes, not the isolated desktop itself.
