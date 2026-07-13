#!/usr/bin/env bash
# XinYu isolated desktop entrypoint. Starts a headless XFCE session, an x11vnc
# server on loopback inside the container, and a noVNC/websockify HTTP bridge.
# Nothing here ever touches the host: this runs entirely inside the container.
set -euo pipefail

GEOMETRY="${XINYU_DESKTOP_GEOMETRY:-1280x800}"
DISPLAY_NUM="${XINYU_DESKTOP_DISPLAY:-:1}"
VNC_PORT="${XINYU_DESKTOP_VNC_PORT:-5900}"
NOVNC_PORT="${XINYU_DESKTOP_NOVNC_PORT:-6080}"
VNC_PASSWORD="${XINYU_DESKTOP_VNC_PASSWORD:-}"

export DISPLAY="${DISPLAY_NUM}"

# Virtual framebuffer (the isolated desktop's screen; never the host screen).
Xvfb "${DISPLAY_NUM}" -screen 0 "${GEOMETRY}x24" -nolisten tcp &
for _ in $(seq 1 50); do
  if xdpyinfo -display "${DISPLAY_NUM}" >/dev/null 2>&1; then break; fi
  sleep 0.1
done

# Lightweight window manager + desktop.
startxfce4 >/tmp/xfce.log 2>&1 &

# x11vnc with a per-session password (loopback-only at the host via -p mapping).
PW_ARGS=(-nopw)
if [ -n "${VNC_PASSWORD}" ]; then
  mkdir -p /root/.vnc
  x11vnc -storepasswd "${VNC_PASSWORD}" /root/.vnc/passwd >/dev/null 2>&1
  PW_ARGS=(-rfbauth /root/.vnc/passwd)
fi
x11vnc -display "${DISPLAY_NUM}" -forever -shared -rfbport "${VNC_PORT}" \
  "${PW_ARGS[@]}" -localhost -bg -o /tmp/x11vnc.log

# noVNC HTTP bridge -> local VNC. Served over plain HTTP on loopback only.
exec websockify --web=/usr/share/novnc "${NOVNC_PORT}" "localhost:${VNC_PORT}"
