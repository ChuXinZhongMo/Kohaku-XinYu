"""XinYu private isolated-desktop backends.

Two backends implement the ``PrivateDesktopBackend`` contract:

  * ``SimulatedDesktopBackend`` (mode="simulated") — honest, offline, no
    container. Used for tests and when no live backend is available. It NEVER
    claims a live desktop and NEVER touches the host.
  * ``DockerXfceVncBackend`` (mode="live") — a real local Linux XFCE container
    with x11vnc + noVNC/websockify, all host ports bound to 127.0.0.1. Action
    injection and frame capture go through ``docker exec`` (xdotool / imagemagick)
    inside the container only.

Neither backend controls the owner's host Windows desktop, captures the owner's
screen, or moves the owner's physical mouse.
"""
from __future__ import annotations

import json
import secrets
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote

from stores.state_service import read_json

WORKSPACE_REL = Path("runtime/private_ecosystem/desktop_workspace")
CONTAINER_NAME = "xinyu-private-desktop"
IMAGE_TAG = "xinyu/private-desktop:1"
DOCKERFILE_DIR_REL = Path("ops/private_desktop")

# Loopback-only host ports (proven free by the Phase 0 probe).
HOST_NOVNC_PORT = 6080
HOST_VNC_PORT = 5900
DISPLAY_GEOMETRY = "1280x800"
DISPLAY_W, DISPLAY_H = 1280, 800

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# A 1x1 transparent PNG: an honest placeholder frame for the simulated backend.
_SIMULATED_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082"
)


def _plane_to_pixels(x: int | None, y: int | None) -> tuple[int, int]:
    """Map a 0..1000 plane coordinate to the isolated display resolution."""
    px = int(round((max(0, min(1000, int(x or 0))) / 1000.0) * DISPLAY_W))
    py = int(round((max(0, min(1000, int(y or 0))) / 1000.0) * DISPLAY_H))
    return px, py


class SimulatedDesktopBackend:
    """Offline, honest backend. Reports ``simulated`` and never claims live."""

    mode = "simulated"

    def status(self) -> dict[str, Any]:
        return {
            "backend": "simulated",
            "session_state": "simulated",
            "display_size": DISPLAY_GEOMETRY,
            "live_view_url": "",
            "live": False,
        }

    def ensure_started(self) -> dict[str, Any]:
        return {"ok": True, "session_state": "simulated", "live": False, "notes": ["simulated_no_container"]}

    def stop(self) -> dict[str, Any]:
        return {"ok": True, "session_state": "stopped", "live": False, "notes": ["simulated_no_container"]}

    def screenshot(self) -> bytes:
        return _SIMULATED_PNG

    def click(self, x: int, y: int, button: str = "left") -> dict[str, Any]:
        return {"ok": True, "simulated": True}

    def double_click(self, x: int, y: int, button: str = "left") -> dict[str, Any]:
        return {"ok": True, "simulated": True}

    def move_mouse(self, x: int, y: int) -> dict[str, Any]:
        return {"ok": True, "simulated": True}

    def scroll(self, x: int, y: int, delta: int) -> dict[str, Any]:
        return {"ok": True, "simulated": True}

    def type_text(self, text: str) -> dict[str, Any]:
        return {"ok": True, "simulated": True}

    def hotkey(self, keys: list[str]) -> dict[str, Any]:
        return {"ok": True, "simulated": True}

    def clipboard_set(self, text: str) -> dict[str, Any]:
        return {"ok": True, "simulated": True}


class DockerXfceVncBackend:
    """Real isolated Linux desktop via Docker. Host ports bind to 127.0.0.1 only."""

    mode = "live"

    def __init__(self, root: Path, *, docker: str | None = None) -> None:
        self.root = Path(root)
        self.docker = docker or shutil.which("docker") or "docker"
        self._password = ""

    # -- low-level docker helpers ------------------------------------------------
    def _run(self, args: list[str], *, timeout: int = 30, capture_bytes: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.docker, *args],
            capture_output=True,
            text=not capture_bytes,
            timeout=timeout,
            creationflags=_NO_WINDOW,
        )

    def _container_field(self, fmt: str) -> str:
        try:
            proc = self._run(["inspect", "--format", fmt, CONTAINER_NAME], timeout=15)
        except (OSError, subprocess.SubprocessError):
            return ""
        return (proc.stdout or "").strip() if proc.returncode == 0 else ""

    def _running(self) -> bool:
        return self._container_field("{{.State.Running}}") == "true"

    def _exists(self) -> bool:
        return bool(self._container_field("{{.Id}}"))

    def image_present(self) -> bool:
        try:
            proc = self._run(["image", "inspect", IMAGE_TAG], timeout=15)
        except (OSError, subprocess.SubprocessError):
            return False
        return proc.returncode == 0

    def build_image(self, *, timeout: int = 30 * 60) -> dict[str, Any]:
        context = self.root / DOCKERFILE_DIR_REL
        try:
            proc = self._run(["build", "-t", IMAGE_TAG, str(context)], timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error_code": "image_build_timeout"}
        except (OSError, subprocess.SubprocessError) as exc:
            return {"ok": False, "error_code": f"image_build_error:{type(exc).__name__}"}
        return {
            "ok": proc.returncode == 0,
            "error_code": "" if proc.returncode == 0 else "image_build_failed",
            "stderr_tail": (proc.stderr or "")[-1500:],
        }

    # -- backend contract --------------------------------------------------------
    def status(self) -> dict[str, Any]:
        running = self._running()
        return {
            "backend": "docker_xfce_vnc",
            "session_state": "live" if running else ("stopped" if self._exists() else "stopped"),
            "display_size": DISPLAY_GEOMETRY,
            "live_view_url": self.live_view_url() if running else "",
            "image_present": self.image_present(),
            "container_present": self._exists(),
            "live": running,
        }

    def live_view_url(self) -> str:
        # Loopback-only noVNC. The one-time session password is embedded so the
        # owner cockpit auto-connects without a manual prompt. This URL is only
        # ever returned to the owner-private cockpit over the loopback bridge; the
        # password is a single-session secret destroyed on stop.
        base = f"http://127.0.0.1:{HOST_NOVNC_PORT}/vnc.html"
        pw = self.session_password()
        if pw:
            return f"{base}?autoconnect=true&password={quote(pw, safe='')}"
        return base

    def ensure_started(self, *, build_if_missing: bool = True) -> dict[str, Any]:
        if self._running():
            return {"ok": True, "session_state": "live", "live": True, "live_view_url": self.live_view_url()}
        if not self.image_present():
            if not build_if_missing:
                return {"ok": False, "session_state": "stopped", "live": False, "error_code": "image_not_built"}
            built = self.build_image()
            if not built.get("ok"):
                return {"ok": False, "session_state": "error", "live": False, "error_code": built.get("error_code", "image_build_failed")}
        # Remove any stale stopped container with the same name.
        if self._exists():
            self._run(["rm", "-f", CONTAINER_NAME], timeout=30)
        self._password = secrets.token_urlsafe(12)
        try:
            proc = self._run(
                [
                    "run", "-d", "--rm",
                    "--name", CONTAINER_NAME,
                    "--shm-size", "512m",
                    "-p", f"127.0.0.1:{HOST_NOVNC_PORT}:6080",
                    "-p", f"127.0.0.1:{HOST_VNC_PORT}:5900",
                    "-e", f"XINYU_DESKTOP_GEOMETRY={DISPLAY_GEOMETRY}",
                    "-e", f"XINYU_DESKTOP_VNC_PASSWORD={self._password}",
                    IMAGE_TAG,
                ],
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "session_state": "error", "live": False, "error_code": "container_start_timeout"}
        except (OSError, subprocess.SubprocessError) as exc:
            return {"ok": False, "session_state": "error", "live": False, "error_code": f"container_start_error:{type(exc).__name__}"}
        if proc.returncode != 0:
            return {
                "ok": False,
                "session_state": "error",
                "live": False,
                "error_code": "container_start_failed",
                "stderr_tail": (proc.stderr or "")[-800:],
            }
        self._persist_session_secret()
        return {"ok": True, "session_state": "live", "live": True, "live_view_url": self.live_view_url()}

    def stop(self) -> dict[str, Any]:
        if not self._exists():
            return {"ok": True, "session_state": "stopped", "live": False, "notes": ["no_container"]}
        try:
            self._run(["stop", "-t", "5", CONTAINER_NAME], timeout=30)
        except (OSError, subprocess.SubprocessError):
            pass
        self._clear_session_secret()
        return {"ok": True, "session_state": "stopped", "live": False}

    def _exec(self, argv: list[str], *, timeout: int = 15, capture_bytes: bool = False) -> subprocess.CompletedProcess:
        return self._run(["exec", "-e", "DISPLAY=:1", CONTAINER_NAME, *argv], timeout=timeout, capture_bytes=capture_bytes)

    def screenshot(self) -> bytes:
        proc = self._exec(["import", "-window", "root", "png:-"], timeout=20, capture_bytes=True)
        data = proc.stdout if isinstance(proc.stdout, (bytes, bytearray)) else b""
        if proc.returncode != 0 or not data:
            raise RuntimeError("desktop_screenshot_failed")
        return bytes(data)

    def _xdotool(self, args: list[str]) -> dict[str, Any]:
        proc = self._exec(["xdotool", *args], timeout=15)
        return {"ok": proc.returncode == 0, "error_code": "" if proc.returncode == 0 else "xdotool_failed"}

    def click(self, x: int, y: int, button: str = "left") -> dict[str, Any]:
        px, py = _plane_to_pixels(x, y)
        btn = {"left": "1", "middle": "2", "right": "3"}.get(button, "1")
        return self._xdotool(["mousemove", str(px), str(py), "click", btn])

    def double_click(self, x: int, y: int, button: str = "left") -> dict[str, Any]:
        px, py = _plane_to_pixels(x, y)
        btn = {"left": "1", "middle": "2", "right": "3"}.get(button, "1")
        return self._xdotool(["mousemove", str(px), str(py), "click", "--repeat", "2", btn])

    def move_mouse(self, x: int, y: int) -> dict[str, Any]:
        px, py = _plane_to_pixels(x, y)
        return self._xdotool(["mousemove", str(px), str(py)])

    def scroll(self, x: int, y: int, delta: int) -> dict[str, Any]:
        px, py = _plane_to_pixels(x, y)
        button = "4" if int(delta) >= 0 else "5"
        repeat = max(1, min(10, abs(int(delta)) or 1))
        return self._xdotool(["mousemove", str(px), str(py), "click", "--repeat", str(repeat), button])

    def type_text(self, text: str) -> dict[str, Any]:
        return self._xdotool(["type", "--clearmodifiers", "--", str(text)])

    def hotkey(self, keys: list[str]) -> dict[str, Any]:
        combo = "+".join(k for k in keys if k)
        if not combo:
            return {"ok": False, "error_code": "empty_hotkey"}
        return self._xdotool(["key", "--clearmodifiers", combo])

    def clipboard_set(self, text: str) -> dict[str, Any]:
        # xdotool cannot set the clipboard directly; use xfce's clipman via type
        # into a known buffer is unreliable, so this stays a no-op success record
        # in the first landing (the action is policy-gated and recorded anyway).
        return {"ok": True, "notes": ["clipboard_set_recorded_only"]}

    # -- session secret (never written to public reports / state markdown) -------
    def _persist_session_secret(self) -> None:
        path = self.root / WORKSPACE_REL / "session_secret.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"vnc_password": self._password}, ensure_ascii=False), encoding="utf-8")

    def _clear_session_secret(self) -> None:
        path = self.root / WORKSPACE_REL / "session_secret.json"
        try:
            path.unlink()
        except OSError:
            pass

    def session_password(self) -> str:
        if self._password:
            return self._password
        data = read_json(self.root / WORKSPACE_REL / "session_secret.json", default={})
        return str(data.get("vnc_password", "")) if isinstance(data, dict) else ""


def docker_available(docker: str | None = None) -> bool:
    exe = docker or shutil.which("docker")
    if not exe:
        return False
    try:
        proc = subprocess.run([exe, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=20, creationflags=_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and bool((proc.stdout or "").strip())


def select_backend(root: Path, *, prefer_live: bool = True) -> Any:
    """Return a Docker backend when Docker is usable, else the honest simulated
    backend. Never returns a host-automation backend."""
    if prefer_live and docker_available():
        return DockerXfceVncBackend(Path(root))
    return SimulatedDesktopBackend()


def active_backend(root: Path) -> Any:
    """Backend for executing capability calls: the live Docker backend ONLY when
    its container is already running (started via the owner start route); else
    the honest simulated backend. This keeps per-call capability execution from
    implicitly building images or spinning up containers."""
    if docker_available():
        backend = DockerXfceVncBackend(Path(root))
        if backend.status().get("live"):
            return backend
    return SimulatedDesktopBackend()


def current_status(root: Path) -> dict[str, Any]:
    """Real backend status for the cockpit snapshot (no container side effects)."""
    if docker_available():
        return DockerXfceVncBackend(Path(root)).status()
    return SimulatedDesktopBackend().status()
