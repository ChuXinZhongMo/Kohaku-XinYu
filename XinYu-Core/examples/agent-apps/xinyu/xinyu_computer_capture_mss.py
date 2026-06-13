"""Real screen-capture backend for XinYu computer control (mss).

Implements the ``xinyu_computer_control.CaptureBackend`` Protocol. Screen
capture of the real desktop is sensitive, so this backend is OPT-IN: it is never
auto-wired into a live tick. The caller must explicitly construct it and pass it
to ``run_computer_action(..., backend=...)``, and policy (grant enabled,
sensitive-window blocking, approval for execution) is enforced by
xinyu_computer_control BEFORE this backend is called.

mss is an optional dependency; importing this module is always safe.
"""
from __future__ import annotations

from typing import Any, Mapping

# Pillow is already available in this environment and is only used to encode the
# captured frame to PNG bytes.
_MAX_DIM = 4096


class MssCaptureBackend:
    """Capture the primary monitor (or a region) and return PNG bytes."""

    def __init__(self, *, monitor_index: int = 1) -> None:
        self._monitor_index = max(0, int(monitor_index))

    def screenshot(self, region: Mapping[str, Any] | None = None) -> bytes:
        try:
            import mss
        except Exception as exc:  # pragma: no cover - exercised only without mss
            raise RuntimeError("mss_not_installed") from exc
        try:
            from PIL import Image
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("pillow_not_installed") from exc

        with mss.mss() as sct:
            monitors = sct.monitors
            base = monitors[self._monitor_index] if self._monitor_index < len(monitors) else monitors[0]
            box = dict(base)
            if isinstance(region, Mapping) and all(k in region for k in ("left", "top", "width", "height")):
                box = {
                    "left": int(region["left"]),
                    "top": int(region["top"]),
                    "width": max(1, min(_MAX_DIM, int(region["width"]))),
                    "height": max(1, min(_MAX_DIM, int(region["height"]))),
                }
            raw = sct.grab(box)
            image = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        import io

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


def mss_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("mss") is not None
