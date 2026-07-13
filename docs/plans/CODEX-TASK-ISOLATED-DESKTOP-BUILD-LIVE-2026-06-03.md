# Codex Task: Build XinYu Isolated Desktop Image + Live Verification

date: 2026-06-03
from: Claude (executor of Phases 1–6)
to: Codex
repo: D:\XinYu
app root: D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
venv python: `.\.venv\Scripts\python.exe`

## Context

Phases 1–6 of `CLAUDE-TASK-XINYU-ISOLATED-DESKTOP-CONTROL-2026-06-03.md` are DONE
and tested (65 pytest pass, Desktop typecheck+build pass). See
`docs/plans/CLAUDE-ACCEPTANCE-ISOLATED-DESKTOP-PHASE1-6-2026-06-03.md`.

The ONLY remaining step is building the isolated-desktop Docker image and running
the live verification. Claude stopped its build because the owner is switching to
a faster network node — the previous build stalled on apt at ~49 kB/s. Nothing is
half-installed: no `xinyu/private-desktop` image, no container, no dangling layer.

Do NOT change application code, grants, plugin defaults, or the Dockerfile pin.
Hard red lines from the original task still apply (no host Windows desktop control,
no host screen capture, no owner mouse movement, no `computer_control`, no
`external_plugin_call` bypass, ports bind 127.0.0.1 only, no AGPL, no unpinned deps).

## Step 1 — Build the image (after the owner is on the faster node)

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
docker build -t xinyu/private-desktop:1 ops/private_desktop
```

- Base is pinned: `debian:bookworm-slim@sha256:0104b334637a5f19aa9c983a91b54c89887c0984081f2068983107a6f6c21eeb`.
- Installs (inside the container only): xfce4, xfce4-terminal, xvfb, x11vnc,
  x11-utils, xdotool, imagemagick, novnc, websockify, dbus-x11, ca-certificates.
- apt already has retries/timeout configured in the Dockerfile for flaky links.
- OPTIONAL speed-up (allowed by the task: "XFCE/Openbox"): if XFCE is still too
  slow, you MAY swap `xfce4 xfce4-terminal` for `openbox xterm` in the Dockerfile
  and change `startxfce4` → `openbox-session` in `ops/private_desktop/entrypoint.sh`.
  That is the only sanctioned edit; keep everything else identical.

Verify: `docker images xinyu/private-desktop` shows the tag.

## Step 2 — Live verification (the integration checklist from the task)

Probe + start + prove loopback + one approved action + after-frame + stop. You can
drive it through the control/service modules directly (no bridge needed):

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -c "from pathlib import Path; from xinyu_private_desktop_service import DockerXfceVncBackend; b=DockerXfceVncBackend(Path('.').resolve()); print(b.ensure_started(build_if_missing=False))"
```

Then confirm each item:

1. **noVNC bound to 127.0.0.1 only** (NOT 0.0.0.0):
   ```powershell
   docker port xinyu-private-desktop
   netstat -ano | findstr 6080
   ```
   Expect `127.0.0.1:6080` and `127.0.0.1:5900`.

2. **Desktop shows a live frame** — open the Desktop app; the 隔离桌面 panel embeds
   `http://127.0.0.1:6080/vnc.html` (view-only). The VNC password is in
   `runtime/private_ecosystem/desktop_workspace/session_secret.json` (loopback-only;
   do NOT put it in any report). Or capture a frame headless:
   ```powershell
   .\.venv\Scripts\python.exe -c "from pathlib import Path; from xinyu_private_desktop_control import run_desktop_action; from xinyu_private_desktop_service import DockerXfceVncBackend; import xinyu_private_ecosystem_grants as g; g.save_grants_patch(Path('.').resolve(), {'private_desktop': {'enabled': True}}); print(run_desktop_action(Path('.').resolve(), action_kind='screenshot', execute=True, backend=DockerXfceVncBackend(Path('.').resolve()))['frame_ref'])"
   ```
   Expect a real PNG under `runtime/private_ecosystem/desktop_workspace/frames/`.

3. **One approved single-step click works** (enable single-step, approve, click):
   ```powershell
   .\.venv\Scripts\python.exe -c "from pathlib import Path; import xinyu_private_ecosystem_grants as g; from xinyu_private_desktop_control import run_desktop_action; from xinyu_private_desktop_service import DockerXfceVncBackend; r=Path('.').resolve(); g.save_grants_patch(r, {'private_desktop': {'enabled': True, 'observe_only': False}}); print(run_desktop_action(r, action_kind='click', x=500, y=500, approved=True, execute=True, backend=DockerXfceVncBackend(r))['result'])"
   ```
   Expect `completed` (live backend), an after-frame recorded.

4. **Owner's physical Windows mouse does NOT move** — watch your real cursor while
   step 3 runs; it must stay put. The click happens via `docker exec xdotool`
   inside the container's Xvfb, not on the host.

5. **Stop**:
   ```powershell
   .\.venv\Scripts\python.exe -c "from pathlib import Path; from xinyu_private_desktop_service import DockerXfceVncBackend; print(DockerXfceVncBackend(Path('.').resolve()).stop())"
   ```

## Step 3 — Finalize

Fill the `<!-- LIVE-INTEGRATION -->` section of
`docs/plans/CLAUDE-ACCEPTANCE-ISOLATED-DESKTOP-PHASE1-6-2026-06-03.md` with the
`docker port` output (proving 127.0.0.1) and confirmation of items 1–5. Do not
write the VNC password anywhere in the report.

## If build fails again

Report blocked with the apt error (don't fall back to host automation). Likely
causes: network still slow → retry on the faster node; a transient mirror 5xx →
re-run `docker build` (BuildKit caches completed layers).
