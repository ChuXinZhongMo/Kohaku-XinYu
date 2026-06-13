"""Backend helpers for private isolated-desktop bridge routes."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _backend_status(root: Path) -> dict[str, Any]:
    # Lazy import keeps Docker probing off the import path for non-desktop work.
    try:
        from xinyu_private_desktop_service import current_status

        return current_status(root)
    except Exception:
        return {"backend": "unavailable", "session_state": "stopped", "live": False}


def _live_backend(root: Path) -> Any | None:
    try:
        from xinyu_private_desktop_service import DockerXfceVncBackend, docker_available

        if not docker_available():
            return None
        backend = DockerXfceVncBackend(root)
        if backend.status().get("live"):
            return backend
    except Exception:
        return None
    return None


def _start_backend(root: Path) -> dict[str, Any]:
    from xinyu_private_desktop_service import DockerXfceVncBackend, docker_available

    if not docker_available():
        return {"ok": False, "session_state": "unavailable", "live": False, "error_code": "docker_unavailable"}
    backend = DockerXfceVncBackend(root)
    if not backend.image_present():
        # Building the (heavy) image is an explicit, long offline op; do not block
        # the bridge for it. The owner builds once via the documented command.
        return {"ok": False, "session_state": "stopped", "live": False, "error_code": "image_not_built"}
    return backend.ensure_started(build_if_missing=False)


def _stop_backend(root: Path) -> dict[str, Any]:
    from xinyu_private_desktop_service import DockerXfceVncBackend, docker_available

    if not docker_available():
        return {"ok": True, "session_state": "unavailable", "live": False, "notes": ["docker_unavailable"]}
    return DockerXfceVncBackend(root).stop()
