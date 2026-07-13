# Acceptance Report: XinYu Isolated Desktop Control — Phase 0 (BLOCKED)

date: 2026-06-03
executor: Claude (Opus 4.8)
director: Codex
task: CLAUDE-TASK-XINYU-ISOLATED-DESKTOP-CONTROL-2026-06-03.md
outcome: **BLOCKED at Phase 0 — no isolated desktop backend available. Stopped per
Stop Conditions. Did NOT fall back to host Windows automation.**

## What was done

Phase 0 (read-only environment probe) only. Implementation Phases 1–6 were NOT
started because no isolated desktop backend exists on this machine, and the task
mandates: "If no viable isolated desktop backend exists, report blocked and stop.
Do not automate the host desktop."

## Probe result (read-only, installed nothing)

Command: `.\.venv\Scripts\python.exe xinyu_private_desktop_environment.py --json`

- decision: **blocked_no_isolated_backend**
- backends_available: **[]**
- docker: cli_present=false, service_state=absent, usable=false
- wsl: launcher_present=true, lxss_manager_present=false, vmcompute_present=false,
  usable=false (note: WSL2 not installed; `wsl --install` needs admin + reboot)
- hyperv: vmms_state=absent, vmcompute_present=false, usable=false
- windows_sandbox: present=false
- novnc: websockify_module=false, vncdotool_module=false, novnc_dir_present=false
- loopback_bind_ok: true
- free_candidate_ports: 5900/5901/6080/6081 all free
- boundaries: host_windows_desktop_controlled=false, host_screen_captured=false,
  owner_mouse_moved=false, computer_control_enabled=false,
  falls_back_to_host_automation=false

Interpretation: the OS could host an isolated desktop later (loopback binding
works, target ports are free), but there is currently no virtualization/container
backend installed to run one in.

## GitHub references — borrowed conceptually only (no code, nothing installed)

- noVNC (MPL-2.0): HTML5 VNC client for the future live view (loopback websockify).
- Apache Guacamole: remote-desktop gateway boundary concept.
- Selkies / QuickDesk / Contop: WebRTC streaming + separate display/action
  channels + live-view-beside-execution (future, if VNC latency is a problem).
- mcp-vnc: minimal VNC tool surface (reference only; XinYu owns policy).
- trycua/cua: sandbox abstraction (deferred; AGPL-tinged extras; not installed).
- RustDesk: rejected (AGPL-3.0).
No third-party code was copied; no AGPL component embedded; no dependency installed.

## Chosen backend

None — **blocked**. (Preferred when unblocked: `docker_xfce_vnc` — a local Linux
XFCE/Openbox + TigerVNC/x11vnc + noVNC/websockify container, all ports bound to
127.0.0.1, state under runtime/private_ecosystem/desktop_workspace.)

## Live view transport

N/A (no backend). Planned: noVNC over loopback websockify, view-only by default.

## Ports / loopback proof

Probe confirms `loopback_bind_ok=true` and candidate ports 5900/5901/6080/6081 are
free on 127.0.0.1. Nothing is bound (no backend started).

## Files changed (additive)

- `xinyu_private_desktop_environment.py` (new — read-only probe + CLI)
- `tests/test_private_desktop_environment.py` (new — 4 tests)

## New plugin / capabilities

None yet. `xinyu_private_desktop` plugin, `private_desktop` grant schema, bridge
routes, and `PrivateDesktopPanel` are deferred until a backend exists (per the
task's gating: build the backend only "if Docker/WSL2 is available").

## New bridge routes

None yet (deferred).

## Tests run and results

`pytest -q tests/test_private_desktop_environment.py` → **4 passed**.
(Probe well-formed + read-only; never implies host control; blocked when no
backend; each backend reports a usable bool.)

## Explicit safety statements

- Host Windows desktop NOT controlled.
- Owner mouse NOT moved.
- Owner desktop NOT captured.
- `computer_control` NOT enabled.
- `private_browser.allowed_urls` NOT filled.
- No `external_plugin_call` bypass (nothing executed).
- No third-party code copied.
- No AGPL dependency embedded.
- No grants changed; nothing installed.

## Blocker and smallest owner action to unblock

Blocker: no virtualization/container backend (Docker / WSL2 / Hyper-V) is installed.

Smallest owner action (one of), then re-run the probe:
1. Install **Docker Desktop** (uses the WSL2 backend) — admin + network + reboot; or
2. Run **`wsl --install`** in an elevated PowerShell, reboot, install a distro
   (e.g. Ubuntu) — admin + network + reboot.

Both require administrator rights, internet access (note: this machine's network
has been blocking some CDNs — the Playwright browser CDN failed repeatedly), and a
reboot. The probe and XinYu will not perform these installs automatically and will
not substitute host-desktop control.

## Stop condition hit

"Docker/WSL/VM backend is unavailable and no isolated desktop can be created" →
stopped and reported, as instructed. Will resume at Phase 1 once the owner
provisions a backend and the probe reports `decision=available`.

## Rollback

Delete `xinyu_private_desktop_environment.py` and
`tests/test_private_desktop_environment.py`. No other state touched.
